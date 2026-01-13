import requests
from bs4 import BeautifulSoup
import pandas as pd
import time

# 1. Configuración Inicial
# URL de la web que queremos leer (Pondremos una de ejemplo)
url_objetivo = "https://www.alcanzatumeta.es/calendario.php"

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
        items = soup.find_all('tr', role_='row')

        for item in items:
            try:
                # Extraer Título (buscamos la etiqueta h5 o a)
                titulo = item.find('strong').text.strip()

                # Extraer Fecha (buscamos un span o div con clase fecha)
                # A veces la fecha está dentro de un <small> o <span>
                fecha = item.find('span', style_='display: none').text.strip()

                # Extraer Lugar (si existe)
                lugar = "Murcia"  # Valor por defecto si no lo encontramos
                '''lugar_tag = item.find('p', class_='location')
                if lugar_tag:
                    lugar = lugar_tag.text.strip()
'''
                # Guardamos en un diccionario
                carrera = {
                    'titulo': titulo,
                    'fecha': fecha,

                    'origen': 'ALCANZATUMETA'  # Para saber de qué web vino
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


# --- EJECUCIÓN ---
if __name__ == "__main__":
    datos = obtener_carreras()

    if datos:
        # Guardar en un Excel/CSV para verlos
        df = pd.DataFrame(datos)
        df.to_csv('proximas_carreras_murcia.csv', index=False, encoding='utf-8-sig')
        print(f"\n🎉 ¡Éxito! Se han guardado {len(datos)} carreras en 'proximas_carreras_murcia.csv'")
    else:
        print("\n⚠️ No se encontraron datos. Revisa los selectores HTML.")