import sqlite3
import requests
import urllib.parse
import os


# --- CONFIGURACIÓN ---
# ¡PEGA AQUÍ TU URL DE MAKE!
WEBHOOK_URL = os.getenv("WEBHOOK_URL")


def publicar_pendientes():

    if not WEBHOOK_URL:
        print("❌ ERROR: No encuentro la URL del Webhook")
        return

    conn = sqlite3.connect('carreras.db')
    conn.row_factory = sqlite3.Row  # Para acceder por nombre de columna
    cursor = conn.cursor()

    # 1. Buscamos carreras NO publicadas (publicada = 0) y que sean FUTURAS
    # LIMIT 1: Importante para no saturar Instagram (publicamos de 1 en 1 cada día)
    cursor.execute("""
        SELECT * FROM carreras 
        WHERE (publicada = 0 OR publicada IS NULL) 
        AND fecha >= date('now')
        ORDER BY fecha ASC 
        LIMIT 1
    """)

    carrera = cursor.fetchone()

    if not carrera:
        print("💤 No hay carreras nuevas pendientes de publicar.")
        conn.close()
        return

    print(f"✨ Encontrada para publicar: {carrera['titulo']}")

    url_sucia = carrera['imagen']

    # Esta función convierte 'Unión' en 'Uni%C3%B3n' respetando los ':' y '/'
    if url_sucia:
        url_limpia = urllib.parse.quote(url_sucia, safe=':/')
    else:
        url_limpia = None

    # 2. Preparamos los datos para enviar a Make
    datos_payload = {
        "titulo": carrera['titulo'],
        "fecha": carrera['fecha'],
        "ubicacion": carrera['ubicacion'],
        "imagen": url_limpia,
        "link": carrera['url_inscripcion']
    }

    try:
        # 3. Enviamos la señal a Make (Webhook)
        response = requests.post(WEBHOOK_URL, json=datos_payload)

        if response.status_code == 200:
            print("✅ Enviado a Make correctamente.")

            # 4. MARCAR COMO PUBLICADA EN LA DB
            # Usamos el título o URL como identificador
            cursor.execute("UPDATE carreras SET publicada = 1 WHERE url_inscripcion = ?", (carrera['url_inscripcion'],))
            conn.commit()
            print("💾 Base de datos actualizada (publicada=1).")

        else:
            print(f"❌ Error en Make: {response.text}")

    except Exception as e:
        print(f"❌ Error de conexión: {e}")

    conn.close()


if __name__ == "__main__":
    publicar_pendientes()