import requests
from bs4 import BeautifulSoup
import pandas as pd

# 1. URL objetivo
url_objetivo = "https://www.alcanzatumeta.es/calendario.php"
url_base = "https://www.alcanzatumeta.es/"  # Para corregir enlaces relativos

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
}


def limpiar_fecha(fecha_texto):
    """
    Convierte '29 May 26' -> '2026-05-29'
    """
    if not fecha_texto:
        return None

    # Diccionario bilingüe (Español/Inglés) para asegurar que pilla todo
    meses = {
        'jan': '01', 'ene': '01', 'enero': '01',
        'feb': '02', 'febrero': '02',
        'mar': '03', 'marzo': '03',
        'apr': '04', 'abr': '04', 'abril': '04',
        'may': '05', 'mayo': '05',
        'jun': '06', 'junio': '06',
        'jul': '07', 'julio': '07',
        'aug': '08', 'ago': '08', 'agosto': '08',
        'sep': '09', 'septiembre': '09',
        'oct': '10', 'octubre': '10',
        'nov': '11', 'noviembre': '11',
        'dec': '12', 'dic': '12', 'diciembre': '12'
    }

    try:
        # 1. Limpieza básica: minúsculas y quitar puntos (ej: "29 May. 26")
        texto = fecha_texto.lower().replace('.', '').strip()

        # 2. Separar por espacios
        partes = texto.split()

        # Esperamos 3 partes: ['29', 'may', '26']
        if len(partes) == 3:
            dia = partes[0].zfill(2)  # "29"
            mes_txt = partes[1][0:3]  # "may" (cogemos las 3 primeras letras)
            anio = partes[2]  # "26"

            # Convertir año corto a largo: '26' -> '2026'
            if len(anio) == 2:
                anio = f"20{anio}"

            # Traducir mes a número
            mes_numero = meses.get(mes_txt, '00')  # '00' si falla

            if mes_numero == '00':
                return fecha_texto  # Devolvemos original si no entendemos el mes

            return f"{dia}-{mes_numero}-{anio}"

        return fecha_texto  # Si el formato no es de 3 partes, lo devolvemos tal cual

    except Exception:
        return fecha_texto


def obtener_carreras():
    print(f"🔄 Conectando con {url_objetivo}...")

    try:
        response = requests.get(url_objetivo, headers=headers)
    except requests.exceptions.RequestException as e:
        print(f"❌ Error de conexión: {e}")
        return []

    if response.status_code == 200:
        print("✅ Conexión exitosa. Analizando HTML...")

        soup = BeautifulSoup(response.text, 'html.parser')
        filas = soup.find_all('tr')

        carreras_extraidas = []

        for fila in filas:
            celdas = fila.find_all('td')

            # --- FILTRO DE SEGURIDAD ---
            # Si la fila tiene menos de 5 celdas, seguramente es un encabezado o separador.
            # La saltamos para evitar errores.
            if len(celdas) < 5:
                continue

            try:
                # 4. DATOS PRINCIPALES (Columna 3)
                # Extraemos esto primero porque si no hay título, no nos interesa la fila
                evento = celdas[3]

                # Buscamos la etiqueta strong de forma segura
                titulo = evento.find('strong')

                if not titulo:
                    continue

                titulo = titulo.get_text(strip=True)

                # 1. FECHA (Corrección para quitar el timestamp oculto)
                celda_fecha = celdas[0]

                # Buscamos si hay un span dentro (que es donde está el timestamp oculto)
                span_oculto = celda_fecha.find('span')
                if span_oculto:
                    # .decompose() elimina la etiqueta del árbol HTML temporalmente
                    span_oculto.decompose()

                    # Ahora extraemos el texto limpio (el span ya no existe)
                fecha_texto = celda_fecha.get_text(strip=True)
                fecha_texto = limpiar_fecha(fecha_texto)

                # 2. IMAGEN
                img_tag = celdas[1].find('img')
                img_url = ""
                if img_tag:
                    src = img_tag.get('src')
                    if src:
                        if src.startswith('http'):
                            img_url = src
                        else:
                            # Unimos la URL base con la ruta relativa correctamente
                            img_url = url_base + src.lstrip('/')

                # 3. TIPO. No lo usamos, pero lo dejamos por si acaso
                tipo = celdas[2].get_text(strip=True)

                # C. UBICACIÓN (CORREGIDO: Usando lista de textos)
                # stripped_strings devuelve una lista: ['Título', 'Ubicación', 'Texto Botón 1'...]
                textos_limpios = list(evento.stripped_strings)

                ubicacion = "Murcia"  # Valor por defecto

                # Normalmente el índice 0 es el título y el 1 la ubicación
                if len(textos_limpios) > 1:
                    posible_ubicacion = textos_limpios[1]

                    # Verificamos que no nos hayamos comido la ubicación y estemos leyendo un botón
                    palabras_prohibidas = ["FICHA DE EVENTO", "INSCRIBIRSE", "LISTADO DE INSCRITOS", "LISTA DE ESPERA"]
                    es_boton = any(p in posible_ubicacion.upper() for p in palabras_prohibidas)

                    if not es_boton:
                        ubicacion = posible_ubicacion

                # 6. ENLACES
                enlace_ficha = ""
                enlace_inscripcion = ""
                botones = evento.find_all('a')

                for btn in botones:
                    href = btn.get('href')
                    texto_btn = btn.get_text(strip=True).upper()

                    if href:
                        # Aseguramos que el enlace sea absoluto
                        if not href.startswith('http'):
                            href = url_base + href.lstrip('/')

                        if "FICHA" in texto_btn:
                            enlace_ficha = href
                        elif "INSCRIBIRSE" in texto_btn:
                            enlace_inscripcion = href

                # Guardamos
                carrera = {
                    "fecha": fecha_texto,
                    "titulo": titulo,
                    "ubicacion": ubicacion,
                    "imagen": img_url,
                    "url_ficha": enlace_ficha,
                    "url_inscripcion": enlace_inscripcion,
                    "origen": "ALCANZATUMETA"
                }
                carreras_extraidas.append(carrera)

            except Exception as e:
                # Si una fila concreta falla, imprimimos el error pero NO paramos el programa
                print(f"⚠️ Error leyendo una fila: {e}")
                continue

        # --- RESULTADO EN CONSOLA ---
        print(f"\n🎉 Se han encontrado {len(carreras_extraidas)} carreras.")
        return carreras_extraidas

    else:
        print(f"❌ Error al conectar: {response.status_code}")
        return []


def ejecucion():
    datos = obtener_carreras()

    if datos:
        # Guardar en un CSV
        df = pd.DataFrame(datos)
        cols = ['fecha', 'titulo', 'ubicacion', 'url_inscripcion', 'url_ficha', 'imagen', 'origen']
        df = df[cols]
        df.to_csv('data/alcanzatumeta_completo.csv', index=False, encoding='utf-8-sig')
        print(f"📂 Datos guardados en 'alcanzatumeta_completo.csv'")
    else:
        print("\n⚠️ No se encontraron datos. Revisa los selectores HTML.")