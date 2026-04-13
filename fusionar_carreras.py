import pandas as pd
from thefuzz import fuzz
import os
import numpy as np
import libsql_client
from dotenv import load_dotenv
import requests

load_dotenv()
IMAGEN_DEFECTO_URL_ALCANZA = 'https://www.alcanzatumeta.es/assets/images/no_image.png'


def limpiar_datos_json(dato):
    if pd.isna(dato) or dato is None:
        return None
    if isinstance(dato, (np.integer, np.floating)):
        if np.isnan(dato) or np.isinf(dato):
            return None
        return float(dato) if isinstance(dato, np.floating) else int(dato)
    return str(dato) if dato != '' else None


def fusionar_datos():
    print("🔄 Iniciando proceso de fusión...")

    # --- 1. CONFIGURACIÓN TURSO ---
    turso_url = os.getenv('TURSO_DATABASE_URL')
    turso_token = os.getenv('TURSO_AUTH_TOKEN')

    if not turso_url or not turso_token:
        print("❌ Faltan las credenciales de Turso en las variables de entorno.")
        return

    # --- 2. LISTA Y CARGA DE ARCHIVOS CSV ---
    archivos = [
        'data/alcanzatumeta_completo.csv',
        'data/lineadesalida_completo.csv',
        'data/babelsport_completo.csv'
    ]
    dfs = []

    for archivo in archivos:
        if os.path.exists(archivo):
            try:
                df = pd.read_csv(archivo)
                df.columns = df.columns.str.lower().str.strip()
                if 'titulo' in df.columns and 'fecha' in df.columns:
                    print(f"   ✅ Cargado: {archivo} ({len(df)} carreras)")
                    dfs.append(df)
            except Exception as e:
                print(f"   ❌ Error leyendo {archivo}: {e}")

    if not dfs:
        print("❌ No se han cargado datos.")
        return

    # --- 3. UNIFICACIÓN Y LIMPIEZA ---
    df_master = pd.concat(dfs, ignore_index=True)
    df_master['fecha_dt'] = pd.to_datetime(df_master['fecha'], dayfirst=True, errors='coerce')
    df_master = df_master.dropna(subset=['fecha_dt'])
    df_master = df_master.sort_values(by='fecha_dt')

    # --- 4. DEDUPLICACIÓN INTELIGENTE ---
    carreras_unicas = []
    for fecha, grupo in df_master.groupby('fecha_dt'):
        lista_dia = grupo.to_dict('records')
        while lista_dia:
            candidata = lista_dia.pop(0)
            carreras_unicas.append(candidata)
            indices_a_borrar = []
            for i, otra in enumerate(lista_dia):
                if fuzz.token_sort_ratio(str(candidata['titulo']), str(otra['titulo'])) > 70:
                    indices_a_borrar.append(i)
            for index in sorted(indices_a_borrar, reverse=True):
                del lista_dia[index]

    # --- 5. PREPARACIÓN FINAL ---
    df_final = pd.DataFrame(carreras_unicas)
    df_final['fecha'] = df_final['fecha_dt'].dt.strftime('%Y-%m-%d')

    print("\n💾 Guardando en base de datos (Turso)...")

    contador_nuevas = 0
    contador_actualizadas = 0
    errores_db = 0

    # --- 6. CONEXIÓN A TURSO ---
    try:
        # Nos conectamos directamente a la nube
        client = libsql_client.create_client_sync(turso_url, auth_token=turso_token)
        print("   ✅ Conectado a Turso (Modo Remoto)")
    except Exception as e:
        print(f"   ❌ Error conectando a Turso: {e}")
        return

    # --- 7. INSERCIÓN / ACTUALIZACIÓN ---
    for index, fila in df_final.iterrows():
        titulo = limpiar_datos_json(fila['titulo'])
        fecha = limpiar_datos_json(fila['fecha'])
        ubicacion = limpiar_datos_json(fila.get('ubicacion', ''))
        url_inscripcion = limpiar_datos_json(fila.get('url_inscripcion', ''))
        url_ficha = limpiar_datos_json(fila.get('url_ficha', ''))
        imagen = limpiar_datos_json(fila.get('imagen', ''))
        origen = limpiar_datos_json(fila.get('origen', ''))

        try:
            # Comprobamos si existe (Nota: pasamos la variable entre corchetes [titulo])
            resultado = client.execute("SELECT imagen FROM carreras WHERE titulo = ?", [titulo])

            if len(resultado.rows) == 0:
                # CASO 1: ES NUEVA
                client.execute("""
                    INSERT INTO carreras (fecha, titulo, ubicacion, url_inscripcion, url_ficha, imagen, origen, publicada) 
                    VALUES (?, ?, ?, ?, ?, ?, ?, 0)
                """, [fecha, titulo, ubicacion, url_inscripcion, url_ficha, imagen, origen])
                contador_nuevas += 1

            else:
                # CASO 2: YA EXISTE
                fila_db = resultado.rows[0]
                imagen_actual_db = fila_db[0]

                if imagen_actual_db == IMAGEN_DEFECTO_URL_ALCANZA:
                    client.execute("""
                        UPDATE carreras 
                        SET fecha = ?, ubicacion = ?, url_ficha = ?, imagen = ?, origen = ?, url_inscripcion = ? 
                        WHERE titulo = ?
                    """, [fecha, ubicacion, url_ficha, imagen, origen, url_inscripcion, titulo])
                else:
                    client.execute("""
                        UPDATE carreras 
                        SET fecha = ?, ubicacion = ?, url_ficha = ?, origen = ?, url_inscripcion = ? 
                        WHERE titulo = ?
                    """, [fecha, ubicacion, url_ficha, origen, url_inscripcion, titulo])

                contador_actualizadas += 1

        except Exception as e:
            print(f"   ⚠️ Error guardando '{titulo}': {e}")
            errores_db += 1

    # Cerramos la conexión
    client.close()

    print(f"\n📊 Resumen de Sincronización:")
    print(f"   ✨ Nuevas insertadas: {contador_nuevas}")
    print(f"   🔄 Existentes actualizadas: {contador_actualizadas}")

    if contador_nuevas > 0 or contador_actualizadas > 0:
        print("\n🚀 Avisando a Vercel para que actualice la página web...")
        vercel_webhook_url = os.getenv('VERCEL_URL')
        
        try:
            respuesta = requests.post(vercel_webhook_url)
            if respuesta.status_code in [200, 201]:
                print("   ✅ Vercel está reconstruyendo la web. Estará lista en 1 minuto.")
            else:
                print(f"   ⚠️ Error avisando a Vercel: {respuesta.status_code}")
        except Exception as e:
            print(f"   ⚠️ Fallo de conexión con Vercel: {e}")
    else:
        print("\n💤 No hay cambios. No hace falta actualizar la web.")


if __name__ == "__main__":
    fusionar_datos()