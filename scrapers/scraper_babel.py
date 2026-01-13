import requests
from bs4 import BeautifulSoup
import pandas as pd
import time

# 1. Configuración Inicial
# URL de la web que queremos leer (Pondremos una de ejemplo)
url_objetivo = "https://www.babelsport.com/eventos-proximos/"
url_base = "https://www.babelsport.com/"

# IMPORTANTE: Usamos un "User-Agent" para parecer un navegador real.
# Si no pones esto, muchas webs bloquean el script pensando que es un robot malicioso.
headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
}


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

        lista_carreras = []
        carreras = soup.find_all('div', class_='row p-3')

        for carrera in carreras:
            try:

                imagen, evento = carrera.find_all('div', recursive=False)

                # 1. EXTRAEMOS IMAGEN
                img_tag = imagen.find('img')
                img_url = ""
                if img_tag:
                    src = img_tag.get('src')
                    if src:
                        if src.startswith('http'):
                            img_url = src
                        else:
                            img_url = url_base + src.lstrip('/')


                # 2. EXTRAEMOS DATOS DEL EVENTO
                # 2.1. Extraer Título
                titulo = evento.find('h3').text.strip()

                # 2.2. Extraer Fecha
                fecha = evento.find('span').text.strip()

                # 2.3. Extraemos Ubicación
                ubicacion = "Murcia" 
                lugar_tag = evento.find('div', class_='col-7 mb-4 text-end')
                if lugar_tag:
                    ubicacion = lugar_tag.text.strip()

                # 3. ENLACES
                enlace_ficha = ""
                enlace_inscripcion = ""
                botones = evento.find_all('a')

                for btn in botones:
                    href = btn.get('href')
                    texto_btn = btn.get_text(strip=True).upper()

                    if href:
                        
                        if not href.startswith('http'):
                            href = url_base + href.lstrip('/')

                        if "REGLAMENTO" in texto_btn:
                            enlace_ficha = href
                        elif "INSCRÍBETE" in texto_btn:
                            enlace_inscripcion = href

                # Guardamos en un diccionario
                carrera = {
                    'titulo': titulo,
                    'fecha': fecha,
                    'ubicacion': ubicacion,
                    "imagen": img_url,
                    "url_ficha": enlace_ficha,
                    "url_inscripcion": enlace_inscripcion,
                    'origen': 'BABELSPORT'  
                }

                lista_carreras.append(carrera)

            except Exception as e:
                # Si falta algún dato en una tarjeta, saltamos a la siguiente para no romper el programa
                print(f"⚠️ Error leyendo una fila: {e}")
                continue

        # --- RESULTADO EN CONSOLA ---
        print(f"\n🎉 Se han encontrado {len(carreras_extraidas)} carreras.")
        return lista_carreras

    else:
        print(f"❌ Error al conectar: {response.status_code}")
        return []


def ejecucion():
    datos = obtener_carreras()

    if datos:
        # Guardar en un Excel/CSV para verlos
        df = pd.DataFrame(datos)
        cols = ['fecha', 'titulo', 'ubicacion', 'url_inscripcion', 'url_ficha', 'imagen', 'origen']
        df = df[cols]
        df.to_csv('data/babelsport_completo.csv', index=False, encoding='utf-8-sig')
        print(f"📂 Datos guardados en 'babelsport_completo.csv'")
    else:
        print("\n⚠️ No se encontraron datos. Revisa los selectores HTML.")