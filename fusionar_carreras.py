"""Fusiona los CSV de los scrapers, elimina duplicados y sincroniza la tabla `carreras` de Turso.

Uso:
    python fusionar_carreras.py            # sincroniza Turso y avisa a Vercel si hay cambios
    python fusionar_carreras.py --dry-run  # solo muestra lo que haría; no escribe nada
"""

import argparse
import os
import time
from datetime import date

import libsql_client
import pandas as pd
import requests
from dotenv import load_dotenv
from thefuzz import fuzz

from geocodificar_carreras import PAUSA_ENTRE_CONSULTAS, buscar_coordenadas
from scrapers.comun import COLUMNAS, interpretar_fecha, normalizar_ubicacion, sin_acentos

load_dotenv()

ARCHIVOS = [
    'data/alcanzatumeta_completo.csv',
    'data/lineadesalida_completo.csv',
    'data/babelsport_completo.csv',
]
IMAGEN_DEFECTO_URL_ALCANZA = 'https://www.alcanzatumeta.es/assets/images/no_image.png'
UMBRAL_DUPLICADO = 70
CAMPOS_DB = ['fecha', 'ubicacion', 'url_inscripcion', 'url_ficha', 'imagen', 'origen']
# Columnas que la fusión crea si faltan en la tabla `carreras`
COLUMNAS_NUEVAS = {
    'latitud': 'REAL', 'longitud': 'REAL',
    'modalidad': 'TEXT',     # Running, Trail, Cross, Senderismo, Marcha nórdica, Híbrida...
    'distancias': 'TEXT',    # km de cada prueba, ordenados y separados por comas: '5,10,21.097'
    'precio_min': 'REAL',    # cuota vigente más barata y más cara entre todas las pruebas, en euros
    'precio_max': 'REAL',
}
CAMPOS_PRUEBAS = ['modalidad', 'distancias', 'precio_min', 'precio_max']
CAMPOS_PRECIO = ('precio_min', 'precio_max')


def a_texto(campo, valor):
    """Valor de la base como texto comparable con el del CSV (27.0 -> '27')."""
    if valor is None:
        return ''
    if campo in CAMPOS_PRECIO:
        return f"{float(valor):.2f}".rstrip('0').rstrip('.')
    return str(valor)


def a_sql(campo, valor):
    """Valor del CSV listo para guardar: '' -> NULL y los precios como número."""
    if valor == '' and campo != 'origen':
        return None
    return float(valor) if campo in CAMPOS_PRECIO else valor


def imagen_real(url):
    return bool(url) and url != IMAGEN_DEFECTO_URL_ALCANZA


def clave_titulo(titulo):
    """Título sin acentos, mayúsculas, signos ni año, para comparar entre fuentes."""
    limpio = ''.join(c if c.isalnum() else ' ' for c in sin_acentos(titulo).lower())
    return ' '.join(palabra for palabra in limpio.split() if not (len(palabra) == 4 and palabra.startswith('20') and palabra.isdigit()))


def es_la_misma(titulo_a, titulo_b):
    return fuzz.token_sort_ratio(clave_titulo(titulo_a), clave_titulo(titulo_b)) > UMBRAL_DUPLICADO


def es_la_misma_en_db(fila, item):
    """Una fila de la base es la misma carrera si coincide el día y se parece el título o comparte enlace."""
    if fila['fecha'] != item['fecha']:
        return False
    return (es_la_misma(fila['titulo'], item['titulo'])
            or any(item[campo] and item[campo] == fila[campo] for campo in ('url_inscripcion', 'url_ficha')))


def cargar_carreras(archivos):
    """Lee los CSV y devuelve las carreras con fecha válida, ya normalizadas."""
    carreras = []
    for archivo in archivos:
        if not os.path.exists(archivo):
            print(f"   ⚠️ No existe {archivo}")
            continue
        try:
            df = pd.read_csv(archivo, dtype=str, keep_default_na=False)
        except Exception as error:
            print(f"   ❌ Error leyendo {archivo}: {error}")
            continue
        df.columns = df.columns.str.lower().str.strip()
        if not {'titulo', 'fecha'} <= set(df.columns):
            print(f"   ❌ {archivo} no tiene columnas 'titulo' y 'fecha'")
            continue

        validas = 0
        for fila in df.to_dict('records'):
            dia = interpretar_fecha(fila.get('fecha'))
            titulo = ' '.join(str(fila.get('titulo', '')).split())
            if not dia or not titulo:
                continue
            item = {columna: str(fila.get(columna, '') or '').strip() for columna in COLUMNAS}
            item.update(titulo=titulo, fecha=dia.isoformat(), ubicacion=normalizar_ubicacion(item['ubicacion']))
            if not imagen_real(item['imagen']):
                item['imagen'] = ''
            for campo in CAMPOS_PRECIO:
                try:
                    item[campo] = a_texto(campo, float(item[campo])) if item[campo] else ''
                except ValueError:
                    item[campo] = ''
            carreras.append(item)
            validas += 1
        print(f"   ✅ {archivo}: {validas} carreras ({len(df) - validas} descartadas sin fecha o título)")
    return carreras


def deduplicar(carreras):
    """Agrupa las carreras del mismo día con título parecido y se queda con la más completa,
    rellenando lo que le falte con los datos de las otras fuentes."""
    por_fecha = {}
    for item in carreras:
        por_fecha.setdefault(item['fecha'], []).append(item)

    unicas = []
    for fecha in sorted(por_fecha):
        pendientes = por_fecha[fecha]
        while pendientes:
            grupo = [pendientes.pop(0)]
            resto = []
            for otra in pendientes:
                (grupo if es_la_misma(grupo[0]['titulo'], otra['titulo']) else resto).append(otra)
            pendientes = resto

            # max() devuelve la primera en caso de empate: se respeta el orden de las fuentes
            mejor = dict(max(grupo, key=lambda c: sum(bool(c[campo]) for campo in ('imagen', 'url_inscripcion', 'url_ficha', 'ubicacion'))))
            for otra in grupo:
                for campo in ('imagen', 'url_inscripcion', 'url_ficha', 'ubicacion', 'distancias', 'precio_min', 'precio_max'):
                    if not mejor[campo] and otra[campo]:
                        mejor[campo] = otra[campo]
                # 'Running' es el valor por defecto: si otra fuente concreta más, vale la suya
                if mejor['modalidad'] in ('', 'Running') and otra['modalidad'] not in ('', 'Running'):
                    mejor['modalidad'] = otra['modalidad']
            if len(grupo) > 1:
                otras = ', '.join(f"'{c['titulo']}' ({c['origen']})" for c in grupo if c['titulo'] != mejor['titulo'] or c['origen'] != mejor['origen'])
                print(f"   ⇄ {fecha}: '{mejor['titulo']}' ({mejor['origen']}) agrupa a {otras}")
            unicas.append(mejor)
    return unicas


def asegurar_columnas(client, dry_run):
    """Crea las columnas que falten (mapa, modalidad, distancias y precios) y devuelve las que existen."""
    columnas = {fila[1] for fila in client.execute('PRAGMA table_info(carreras)').rows}
    for nombre, tipo in COLUMNAS_NUEVAS.items():
        if nombre in columnas:
            continue
        if dry_run:
            print(f"   (simulación) Se crearía la columna '{nombre}' ({tipo}); sus datos no se comparan todavía.")
            continue
        client.execute(f'ALTER TABLE carreras ADD COLUMN {nombre} {tipo}')
        columnas.add(nombre)
        print(f"   🧱 Columna creada: {nombre} ({tipo})")
    return columnas


def localizar_nuevas(ubicaciones, coordenadas, dry_run):
    """Añade a `coordenadas` las ubicaciones que todavía no están geocodificadas."""
    nuevas = sorted(ubicaciones - set(coordenadas))
    if not nuevas:
        return
    user_agent = os.getenv('NOMINATIM_USER_AGENT')
    if dry_run:
        print(f"   (simulación) Se geocodificarían {len(nuevas)} ubicaciones nuevas: {', '.join(nuevas)}")
        return
    if not user_agent:
        print('   ⚠️ Falta NOMINATIM_USER_AGENT; no se geocodifican ubicaciones nuevas.')
        return
    print(f'   Localizando {len(nuevas)} ubicaciones nuevas...')
    for ubicacion in nuevas:
        try:
            resultado = buscar_coordenadas(ubicacion, user_agent)
            if resultado:
                coordenadas[ubicacion] = resultado
            print(f"      {'OK' if resultado else 'Sin resultado'}: {ubicacion}")
        except requests.RequestException as error:
            print(f'      Error localizando {ubicacion}: {error}')
        time.sleep(PAUSA_ENTRE_CONSULTAS)


def avisar_a_vercel():
    webhook = os.getenv('VERCEL_URL')
    if not webhook:
        print("   ⚠️ Falta VERCEL_URL; no se avisa a Vercel.")
        return
    try:
        respuesta = requests.post(webhook, timeout=30)
        if respuesta.status_code in (200, 201):
            print("   ✅ Vercel está reconstruyendo la web.")
        else:
            print(f"   ⚠️ Error avisando a Vercel: {respuesta.status_code}")
    except requests.RequestException as error:
        print(f"   ⚠️ Fallo de conexión con Vercel: {error}")


def fusionar_datos(archivos=None, dry_run=False):
    """Devuelve True si la sincronización termina sin errores."""
    print(f"🔄 Iniciando fusión{' (simulación: no se escribe nada)' if dry_run else ''}...")

    turso_url = os.getenv('TURSO_DATABASE_URL')
    turso_token = os.getenv('TURSO_AUTH_TOKEN')
    if not turso_url or not turso_token:
        print("❌ Faltan las credenciales de Turso en las variables de entorno.")
        return False

    carreras = cargar_carreras(ARCHIVOS if archivos is None else archivos)
    if not carreras:
        print("❌ No se han cargado datos.")
        return False
    carreras = deduplicar(carreras)
    print(f"   {len(carreras)} carreras únicas tras eliminar duplicados.")

    try:
        client = libsql_client.create_client_sync(turso_url, auth_token=turso_token)
        columnas = asegurar_columnas(client, dry_run)
    except Exception as error:
        print(f"   ❌ Error conectando a Turso: {error}")
        return False

    hoy = date.today().isoformat()
    nuevas = actualizadas = renombradas = eliminadas = errores = 0
    try:
        # Campos que se sincronizan: los de siempre más los de pruebas que ya existan en la tabla
        campos = CAMPOS_DB + [campo for campo in CAMPOS_PRUEBAS if campo in columnas]
        filas = client.execute(f"SELECT titulo, {', '.join(campos)}, latitud, longitud, publicada FROM carreras").rows
        en_db = {}
        for fila in filas:
            registro = {campo: a_texto(campo, valor) for campo, valor in zip(campos, fila[1:])}
            registro.update(titulo=fila[0], latitud=fila[-3], longitud=fila[-2], publicada=int(fila[-1] or 0))
            en_db[fila[0]] = registro

        # Coordenadas ya conocidas, indexadas por la ubicación normalizada
        coordenadas = {}
        for fila in en_db.values():
            if fila['ubicacion'] and fila['latitud'] is not None and fila['longitud'] is not None:
                coordenadas.setdefault(normalizar_ubicacion(fila['ubicacion']), (float(fila['latitud']), float(fila['longitud'])))
        localizar_nuevas({c['ubicacion'] for c in carreras if c['fecha'] >= hoy and c['ubicacion']}, coordenadas, dry_run)

        titulos_actuales = {c['titulo'] for c in carreras}
        vistas_en_db = set()

        for item in carreras:
            titulo = item['titulo']
            try:
                existente = en_db.get(titulo)
                titulo_anterior = None
                # Filas de la base que son esta misma carrera con un título que ya no usa ninguna fuente
                # (la web lo ha retocado, o se guardó en su día con el nombre de otra fuente)
                antiguas = [
                    fila for fila in en_db.values()
                    if fila['titulo'] not in titulos_actuales and fila['titulo'] not in vistas_en_db and es_la_misma_en_db(fila, item)
                ]
                if existente is None and antiguas:
                    existente = antiguas.pop(0)
                    titulo_anterior = existente['titulo']

                # Las que sobran son duplicados: se borran conservando si ya se publicó en Instagram
                publicada = max([existente['publicada'] if existente else 0] + [fila['publicada'] for fila in antiguas])
                for duplicada in antiguas:
                    vistas_en_db.add(duplicada['titulo'])
                    if not dry_run:
                        client.execute('DELETE FROM carreras WHERE titulo = ?', [duplicada['titulo']])
                    eliminadas += 1
                    print(f"   🧹 Duplicada eliminada: '{duplicada['titulo']}' (es '{titulo}')")

                latitud, longitud = coordenadas.get(item['ubicacion'], (None, None))

                if existente is None:
                    if not dry_run:
                        client.execute(
                            f"INSERT INTO carreras (titulo, {', '.join(campos)}, publicada, latitud, longitud) "
                            f"VALUES (?, {', '.join('?' for _ in campos)}, 0, ?, ?)",
                            [titulo] + [a_sql(campo, item[campo]) for campo in campos] + [latitud, longitud],
                        )
                    nuevas += 1
                    print(f"   ✨ Nueva: {item['fecha']} · {titulo}")
                    continue

                vistas_en_db.add(existente['titulo'])
                final = dict(item)
                # Manda el cartel que publica ahora la fuente (las webs los resuben con otra URL y la antigua
                # deja de funcionar). El guardado solo se conserva si la fuente no trae ninguno.
                if not final['imagen'] and imagen_real(existente['imagen']):
                    final['imagen'] = existente['imagen']
                # Distancias y precios: si la fuente deja de mostrarlos (inscripción cerrada), se conservan
                for campo in CAMPOS_PRUEBAS:
                    if campo in campos and final[campo] == '' and existente[campo] != '':
                        final[campo] = existente[campo]
                # Si la carrera no ha cambiado de sitio se quedan sus coordenadas. Si ha cambiado y el sitio nuevo
                # no se ha podido localizar, se queda sin ellas: heredar las del sitio anterior la pintaría en
                # otro pueblo y, de ahí, todas las carreras de esa localidad.
                misma_ubicacion = normalizar_ubicacion(existente['ubicacion']) == final['ubicacion']
                if misma_ubicacion and existente['latitud'] is not None:
                    latitud, longitud = existente['latitud'], existente['longitud']

                cambios = [campo for campo in campos if final[campo] != existente[campo]]
                if (latitud, longitud) != (existente['latitud'], existente['longitud']):
                    cambios.append('coordenadas')
                if titulo_anterior:
                    cambios.append('titulo')
                if publicada != existente['publicada']:
                    cambios.append('publicada')
                if not cambios:
                    continue

                if not dry_run:
                    client.execute(
                        f"UPDATE carreras SET titulo = ?, {', '.join(f'{campo} = ?' for campo in campos)}, "
                        "latitud = ?, longitud = ?, publicada = ? WHERE titulo = ?",
                        [titulo] + [a_sql(campo, final[campo]) for campo in campos] + [latitud, longitud, publicada, existente['titulo']],
                    )
                actualizadas += 1
                if titulo_anterior:
                    renombradas += 1
                    print(f"   ✏️ Renombrada: '{titulo_anterior}' → '{titulo}'")
                elif 'fecha' in cambios:
                    print(f"   📅 Cambia de fecha: {titulo} ({existente['fecha']} → {final['fecha']})")
            except Exception as error:
                print(f"   ⚠️ Error guardando '{titulo}': {error}")
                errores += 1

        # Carreras futuras que siguen en la base pero ya no publica ninguna fuente (canceladas, renombradas o movidas)
        huerfanas = sorted(
            (fila['fecha'], fila['titulo'], fila['origen']) for fila in en_db.values()
            if fila['fecha'] >= hoy and fila['titulo'] not in titulos_actuales and fila['titulo'] not in vistas_en_db
        )
        if huerfanas:
            print(f"\n   ℹ️ {len(huerfanas)} carreras futuras de la base ya no aparecen en ninguna fuente (no se borran):")
            for fecha, titulo, origen in huerfanas:
                print(f"      {fecha} · {titulo} ({origen})")
    finally:
        client.close()

    print(f"\n📊 Resumen{' (simulación)' if dry_run else ''}: {nuevas} nuevas, {actualizadas} actualizadas "
          f"({renombradas} renombradas), {eliminadas} duplicadas eliminadas, {errores} errores.")

    if dry_run:
        return errores == 0
    if nuevas or actualizadas or eliminadas:
        print("\n🚀 Avisando a Vercel para que actualice la página web...")
        avisar_a_vercel()
    else:
        print("\n💤 No hay cambios. No hace falta actualizar la web.")
    return errores == 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Fusiona los CSV de los scrapers y sincroniza Turso.")
    parser.add_argument('--dry-run', action='store_true', help="Muestra los cambios sin escribir en Turso ni avisar a Vercel.")
    raise SystemExit(0 if fusionar_datos(dry_run=parser.parse_args().dry_run) else 1)
