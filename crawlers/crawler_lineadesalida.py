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

        # Contenedor principal de datos
        datos = soup.find('div', class_='row mt-3')
        if not datos: return None

        # 1. IMAGEN
        img_tag = datos.find('img')
        img_url = ""
        if img_tag:
            src = img_tag.get('src')
            if src:
                if src.startswith('http'):
                    img_url = src
                else:
                    img_url = url_base + src.lstrip('/')

        # 2. TÍTULO
        titulo = datos.find('h3').text.strip()

        # 3. DATOS (Lugar, Fecha, Hora) - Método Seguro con split
        # Buscamos los divs con esa clase específica
        divs_encontrados = datos.find_all('div', class_="col-12 col-md mb-1 text-center")

        # Valores por defecto
        lugar = "Desconocido"
        fecha = "Desconocida"


        # Extraemos texto limpio de cada uno
        textos_limpios = [d.get_text(strip=True) for d in divs_encontrados]

        # Asignamos según posición (Asumiendo orden: Lugar, Fecha, Hora)
        if len(textos_limpios) >= 3:
            # Usamos split(':') para romper "Lugar : Murcia" en ["Lugar ", " Murcia"]
            # [-1] coge la última parte (" Murcia") y strip() quita los espacios
            lugar = textos_limpios[0].split(':')[-1].strip()
            fecha = textos_limpios[1].split(':')[-1].strip()

        # 4. REGLAMENTO
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

        # 5. INSCRIPCIÓN (Construida manualmente como en tu script)
        enlace_inscripcion = url_carrera + "/invitado"

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
        # --- LÓGICA DE PAGINACIÓN ---
        # Si es la pagina 1, la URL es la base. Si es la 2, añadimos el parámetro.
        # NOTA: Comprueba en el navegador si la paginación es /page/2 o ?page=2
        # Aquí asumo formato query string ?page=X que es común en estos listados
        if pagina == 1:
            url_actual = url_inicial
        else:
            url_actual = f"{url_inicial}?page={pagina}"
            # OJO: Si la web usa /proximas-carreras/page/2, cambia esta línea.

        print(f"\n📄 Escaneando PÁGINA {pagina} ({url_actual})...")

        response = requests.get(url_actual, headers=headers)

        if response.status_code != 200:
            print("⛔ Fin de la paginación o error de red.")
            break

        soup = BeautifulSoup(response.text, 'html.parser')

        # Buscar el contenedor de la lista
        portada = soup.find('div', {"id": "todasCarrerasDiv"})
        if not portada:
            print("⛔ No se encontró el div 'todasCarrerasDiv'. Fin.")
            break

        items = portada.find_all('div', class_='col d-flex justify-content-center')

        # Si no hay items en esta página, hemos terminado
        if not items:
            print("⛔ Página vacía. Hemos terminado.")
            break

        print(f"   -> Encontradas {len(items)} carreras en el listado. Procesando...")

        # --- BUCLE INTERNO (CARRERAS DE LA PÁGINA) ---
        nuevas_carreras_en_pagina = 0
        for item in items:
            try:
                # Sacar URL del enlace
                enlace_tag = item.find('a')
                if not enlace_tag: continue

                url_relativa = enlace_tag['href']
                url_final = url_base + url_relativa.lstrip('/')

                print(f"   🔎 Analizando: {url_final} ...")

                # LLAMADA A LA FUNCIÓN DE DETALLE
                detalle = obtener_detalle_carrera(url_final)

                if detalle:
                    lista_carreras.append(detalle)
                    nuevas_carreras_en_pagina += 1
                    # print(f"      ✅ {detalle['titulo']}")

                # ¡VITAL! Esperar 1 segundo entre carrera y carrera para no ser baneado
                time.sleep(1)

            except Exception as e:
                print(f"   ❌ Error en item: {e}")
                continue

        if nuevas_carreras_en_pagina == 0:
            print("⚠️ No se pudieron extraer carreras válidas de esta página.")
            # Opcional: break si crees que si falla una página fallan todas las siguientes

        pagina += 1
        # Pausa extra al cambiar de página
        time.sleep(2)

    return lista_carreras

def ejecucion():
    datos = obtener_todas_las_carreras()

    if datos:
        df = pd.DataFrame(datos)
        # Reordenar columnas para que quede bonito
        cols = ['fecha', 'titulo', 'ubicacion', 'url_inscripcion', 'url_ficha', 'imagen', 'origen']
        # Nos aseguramos de que existan las columnas antes de reordenar
        df = df[cols]

        df.to_csv('data/lineadesalida_completo.csv', index=False, encoding='utf-8-sig')
        print(f"\n🎉 ¡Éxito Total! Se han guardado {len(datos)} carreras.")
    else:
        print("\n⚠️ No se encontraron datos.")
