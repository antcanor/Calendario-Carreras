import requests
from bs4 import BeautifulSoup
import pandas as pd
import time

# --- CONFIGURACIÓN ---
url_base = "https://lineadesalida.net/"
# URL inicial (sin número de página)
url_inicial = "https://lineadesalida.net/proximas-carreras"

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
}


def obtener_detalle_carrera(url_carrera):
    """
    Función auxiliar para entrar en la ficha de la carrera y sacar detalles.
    Devuelve un diccionario o None si falla.
    """
    try:
        response = requests.get(url_carrera, headers=headers)
        if response.status_code != 200:
            return None

        soup = BeautifulSoup(response.text, 'html.parser')

        evento = soup.find('div', class_='row mt-3')
        if not evento: return None

        # 1. IMAGEN
        img_tag = evento.find('img')
        img_url = ""
        if img_tag:
            src = img_tag.get('src')
            if src:
                if src.startswith('http'):
                    img_url = src
                else:
                    img_url = url_base + src.lstrip('/')

        # 2. TÍTULO
        titulo = evento.find('h3').text.strip()

        # 3. DATOS (Lugar, Fecha, Hora) 
        divs_encontrados = evento.find_all('div', class_="col-12 col-md mb-1 text-center")
        

        lugar = "Murcia"
        fecha = "Desconocida"

        textos_limpios = [d.get_text(strip=True) for d in divs_encontrados]

        if len(textos_limpios) >= 3:

            lugar = textos_limpios[0].split(':')[-1].strip()
            fecha = textos_limpios[1].split(':')[-1].strip()

        # 4. ENLACE FICHA
        enlace_ficha = ""
        reglamento = soup.find('div', class_="row px-2 py-3")
        if reglamento:
            btn = reglamento.find('a')
            if btn:
                href = btn.get('href')
                if href:
                    if not href.startswith('http'):
                        href = url_base + href.lstrip('/')
                    enlace_ficha = href

        # 5. ENLACE INSCRIPCIÓN
        enlace_inscripcion = f"{url_carrera}/invitado"

        return {
            'titulo': titulo,
            'fecha': fecha,
            'ubicacion': lugar,
            "imagen": img_url,
            "url_ficha": enlace_ficha,
            "url_inscripcion": enlace_inscripcion,
            'origen': 'LINEADESALIDA'
        }

    except Exception as e:
        print(f"⚠️ Error leyendo detalle: {e}")
        return None


def obtener_todas_las_carreras():
    lista_carreras = []
    pagina = 1

    while True:

        # Si es la pagina 1, la URL es la base. Si es la 2, añadimos el parámetro.
        if pagina == 1:
            url_actual = url_inicial
        else:
            url_actual = f"{url_inicial}?page={pagina}"
            

        print(f"\n📄 Escaneando PÁGINA {pagina} ({url_actual})...")

        response = requests.get(url_actual, headers=headers)

        if response.status_code != 200:
            print("⛔ Fin de la paginación o error de red.")
            break

        soup = BeautifulSoup(response.text, 'html.parser')
        portada = soup.find('div', {"id": "todasCarrerasDiv"})
        if not portada:
            print("⛔ No se encontró el div 'todasCarrerasDiv'. Fin.")
            break

        carreras = portada.find_all('div', class_='col d-flex justify-content-center')

        # Si no hay items en esta página, hemos terminado
        if not carreras:
            print("⛔ Página vacía. Hemos terminado.")
            break
  
        nuevas_carreras_en_pagina = 0
        for carrera in carreras:
            try:
                # Sacar URL de la pagina de detalle
                enlace_tag = carrera.find('a')
                if not enlace_tag: continue

                url_relativa = enlace_tag['href']
                url_final = url_base + url_relativa.lstrip('/')

                # Llamada a la función de detalle
                detalle = obtener_detalle_carrera(url_final)

                if detalle:
                    lista_carreras.append(detalle)
                    nuevas_carreras_en_pagina += 1

                # ¡VITAL! Esperar 1 segundo entre carrera y carrera para no ser baneado
                time.sleep(1)

            except Exception as e:
                print(f"   ❌ Error en item: {e}")
                continue

        if nuevas_carreras_en_pagina == 0:
            print("⚠️ No se pudieron extraer carreras válidas de esta página.")
            

        pagina += 1

        # Pausa extra al cambiar de página
        time.sleep(2)
    
    print(f"\n🎉 Se han encontrado un total de {len(lista_carreras)} carreras.")

    return lista_carreras

def ejecucion():
    datos = obtener_todas_las_carreras()

    if datos:
        df = pd.DataFrame(datos)
        cols = ['fecha', 'titulo', 'ubicacion', 'url_inscripcion', 'url_ficha', 'imagen', 'origen']
        df = df[cols]
        df.to_csv('data/lineadesalida_completo.csv', index=False, encoding='utf-8-sig')
        print(f"📂 Datos guardados en 'data/lineadesalida_completo.csv'")
        print(f"\n🎉 ¡Éxito Total! Se han guardado {len(datos)} carreras.")
    else:
        print("\n⚠️ No se encontraron datos. Revisa los selectores HTML.")
