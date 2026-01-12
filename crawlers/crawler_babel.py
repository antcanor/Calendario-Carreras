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

    # Hacemos la petición a la web
    response = requests.get(url_objetivo, headers=headers)

    # Si la respuesta es 200 (OK), procedemos
    if response.status_code == 200:
        print("✅ Conexión exitosa. Analizando HTML...")

        # Convertimos el texto HTML en un objeto "Soup" que podemos navegar
        soup = BeautifulSoup(response.text, 'html.parser')

        lista_carreras = []

        # --- AQUÍ EMPIEZA LA MAGIA (Adaptar según la web real) ---
        # Buscamos todos los elementos que contienen una carrera.
        # NOTA: Debes cambiar 'div' y 'card-event' por lo que veas al hacer "Inspeccionar elemento"
        # Este es un ejemplo genérico de cómo suelen estructurarse:
        carreras = soup.find_all('div', class_='row p-3')

        for carrera in carreras:
            try:

                imagen, datos = carrera.find_all('div', recursive=False)

                #IMAGEN
                img_tag = imagen.find('img')
                img_url = ""
                if img_tag:
                    src = img_tag.get('src')
                    if src:
                        if src.startswith('http'):
                            img_url = src
                        else:
                            # Unimos la URL base con la ruta relativa correctamente
                            img_url = url_base + src.lstrip('/')


                # Extraer Título (buscamos la etiqueta h5 o a)
                titulo = datos.find('h3').text.strip()

                # Extraer Fecha (buscamos un span o div con clase fecha)
                # A veces la fecha está dentro de un <small> o <span>
                fecha = datos.find('span').text.strip()

                # Extraer Lugar (si existe)
                lugar = "Murcia"  # Valor por defecto si no lo encontramos
                lugar_tag = datos.find('div', class_='col-7 mb-4 text-end')
                if lugar_tag:
                    lugar = lugar_tag.text.strip()


                enlace_ficha = ""
                enlace_inscripcion = ""
                botones = datos.find_all('a')

                for btn in botones:
                    href = btn.get('href')
                    texto_btn = btn.get_text(strip=True).upper()

                    if href:
                        # Aseguramos que el enlace sea absoluto
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
                    'ubicacion': lugar,
                    "imagen": img_url,
                    "url_ficha": enlace_ficha,
                    "url_inscripcion": enlace_inscripcion,
                    'origen': 'BABELSPORT'  # Para saber de qué web vino
                }

                lista_carreras.append(carrera)
                print(f"  -> Encontrada: {titulo} ({fecha})")

            except AttributeError:
                # Si falta algún dato en una tarjeta, saltamos a la siguiente para no romper el programa
                continue

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
        print(f"\n🎉 ¡Éxito! Se han guardado {len(datos)} carreras en 'babelsport_completo.csv'")
    else:
        print("\n⚠️ No se encontraron datos. Revisa los selectores HTML.")