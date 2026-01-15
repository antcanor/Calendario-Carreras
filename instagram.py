import sqlite3
import requests
import urllib.parse
import os
from supabase import create_client, Client
from dotenv import load_dotenv
load_dotenv()

# --- CONFIGURACIÓN ---
# ¡PEGA AQUÍ TU URL DE MAKE!
WEBHOOK_URL = os.getenv("WEBHOOK_URL")
# CONFIGURACIÓN SUPABASE
supabase_url = os.getenv('SUPABASE_URL')
supabase_key = os.getenv('SUPABASE_KEY')
supabase: Client = None

def conexionSupabase():
    global supabase
    if supabase_url and supabase_key:
        try:
            supabase = create_client(supabase_url, supabase_key)
            print("   ✅ Conectado a Supabase")
        except Exception as e:
            print(f"   ⚠️ No se pudo conectar a Supabase: {e}")
    else:
        print("   ⚠️ Variables SUPABASE_URL o SUPABASE_KEY no configuradas")


def publicar_pendientes():

    if not WEBHOOK_URL:
        print("❌ ERROR: No encuentro la URL del Webhook")
        return
 

    # 1. Buscamos carreras NO publicadas (publicada = 0) y que sean FUTURAS
    # LIMIT 1: Importante para no saturar Instagram (publicamos de 1 en 1 cada día)
    if supabase is None:
        conexionSupabase()

    if supabase:
        print("🔄 Iniciando proceso de publicación...")
        carrera = supabase.table('carreras').select('*').eq('publicada', 0).gte('fecha', 'now()').order('fecha', desc=False).limit(1).maybe_single().execute().data
    else:
        print("❌ ERROR: No hay conexión a Supabase")
        return

    if not carrera:
        print("💤 No hay carreras nuevas pendientes de publicar.")
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
            supabase.table('carreras').update({'publicada': 1}).eq('titulo', carrera['titulo']).execute()
        else:
            print(f"❌ Error en Make: {response.text}")

    except Exception as e:
        print(f"❌ Error de conexión: {e}")


if __name__ == "__main__":
    publicar_pendientes()