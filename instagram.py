import requests
import urllib.parse
import os
import libsql_client
from dotenv import load_dotenv

# Cargamos las variables del .env local (importante para las pruebas)
load_dotenv()

# --- CONFIGURACIÓN ---
WEBHOOK_URL = os.getenv("WEBHOOK_URL")
TURSO_URL = os.getenv('TURSO_DATABASE_URL')
TURSO_TOKEN = os.getenv('TURSO_AUTH_TOKEN')

def publicar_pendientes():
    if not WEBHOOK_URL:
        print("❌ ERROR: No encuentro la URL del Webhook")
        return

    if not TURSO_URL or not TURSO_TOKEN:
        print("❌ ERROR: Variables TURSO_DATABASE_URL o TURSO_AUTH_TOKEN no configuradas")
        return

    print("🔄 Iniciando proceso de publicación...")

    try:
        # 1. Conexión a Turso (Modo Remoto)
        client = libsql_client.create_client_sync(TURSO_URL, auth_token=TURSO_TOKEN)
        
        # 2. Buscamos carreras NO publicadas (0) y FUTURAS (>= hoy)
        # LIMIT 1 nos asegura que solo cogemos la más inminente para no saturar las redes
        query = """
            SELECT * FROM carreras 
            WHERE publicada = 0 AND fecha >= date('now') 
            ORDER BY fecha ASC 
            LIMIT 1
        """
        resultado = client.execute(query)

        if len(resultado.rows) == 0:
            print("💤 No hay carreras nuevas pendientes de publicar.")
            client.close()
            return

        # Transformamos la fila de Turso en un diccionario igual que hacía Supabase
        fila = resultado.rows[0]
        carrera = dict(zip(resultado.columns, fila))

        print(f"✨ Encontrada para publicar: {carrera['titulo']}")

        # 3. Limpieza de URL para la imagen
        url_sucia = carrera.get('imagen')
        url_limpia = urllib.parse.quote(url_sucia, safe=':/') if url_sucia else None

        # 4. Preparamos los datos para enviar a Make
        datos_payload = {
            "titulo": carrera['titulo'],
            "fecha": carrera['fecha'],
            "ubicacion": carrera['ubicacion'],
            "imagen": url_limpia,
            "link": carrera['url_inscripcion']
        }

        # 5. Enviamos la señal a Make (Webhook)
        response = requests.post(WEBHOOK_URL, json=datos_payload)

        # Make puede devolver 200 (OK) o 201 (Creado), ambos son éxito
        if response.status_code in [200, 201]:
            print("✅ Enviado a Make correctamente.")

            # 6. MARCAR COMO PUBLICADA EN LA DB
            # Usamos una consulta SQL UPDATE normal
            client.execute("UPDATE carreras SET publicada = 1 WHERE titulo = ?", [carrera['titulo']])
            print("💾 Base de datos actualizada (publicada = 1).")
        else:
            print(f"❌ Error en Make: {response.status_code} - {response.text}")

        # Cerramos la conexión elegantemente
        client.close()

    except Exception as e:
        print(f"❌ Error de conexión o ejecución: {e}")

if __name__ == "__main__":
    publicar_pendientes()