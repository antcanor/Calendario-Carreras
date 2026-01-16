import pandas as pd
from thefuzz import fuzz
import os
from supabase import create_client, Client
import numpy as np

IMAGEN_DEFECTO_URL_ALCANZA = 'https://www.alcanzatumeta.es/assets/images/no_image.png'

def limpiar_datos_json(dato):
    """Convierte valores de pandas/numpy que no son JSON compatible a valores válidos"""
    if pd.isna(dato) or dato is None:
        return None
    if isinstance(dato, (np.integer, np.floating)):
        if np.isnan(dato) or np.isinf(dato):
            return None
        return float(dato) if isinstance(dato, np.floating) else int(dato)
    return str(dato) if dato != '' else None


def fusionar_datos():
    print("🔄 Iniciando proceso de fusión...")

    # CONFIGURACIÓN SUPABASE
    supabase_url = os.getenv('SUPABASE_URL')
    supabase_key = os.getenv('SUPABASE_KEY')
    supabase: Client = None
    
    if supabase_url and supabase_key:
        try:
            supabase = create_client(supabase_url, supabase_key)
            print("   ✅ Conectado a Supabase")
        except Exception as e:
            print(f"   ⚠️ No se pudo conectar a Supabase: {e}")
    else:
        print("   ⚠️ Variables SUPABASE_URL o SUPABASE_KEY no configuradas")

    # 1. LISTA DE TUS ARCHIVOS CSV
    # Añade aquí los nombres de todos los CSV que generan tus otros scripts
    archivos = [
        'data/alcanzatumeta_completo.csv',
        'data/lineadesalida_completo.csv',
        'data/babelsport_completo.csv'
    ]

    dfs = []

    # 2. CARGA DE DATOS
    for archivo in archivos:
        if os.path.exists(archivo):
            try:
                df = pd.read_csv(archivo)
                # Normalizamos nombres de columnas a minúsculas para evitar líos (Titulo vs titulo)
                df.columns = df.columns.str.lower().str.strip()

                # Verificamos que tenga las columnas clave
                if 'titulo' in df.columns and 'fecha' in df.columns:
                    print(f"   ✅ Cargado: {archivo} ({len(df)} carreras)")
                    dfs.append(df)
                else:
                    print(f"   ⚠️ Saltado {archivo}: No tiene columnas 'titulo' o 'fecha'")
            except Exception as e:
                print(f"   ❌ Error leyendo {archivo}: {e}")
        else:
            print(f"   ⚠️ No encontrado: {archivo}")

    if not dfs:
        print("❌ No se han cargado datos. Revisa los nombres de los archivos.")
        return

    # 3. UNIFICACIÓN
    df_master = pd.concat(dfs, ignore_index=True)

    # --- LIMPIEZA DE FECHAS ---
    # Convertimos tus fechas "18-01-2026" a objetos de fecha reales para poder ordenar.
    # dayfirst=True es vital para tu formato DD-MM-YYYY
    df_master['fecha_dt'] = pd.to_datetime(df_master['fecha'], dayfirst=True, errors='coerce')

    # Eliminamos las que no tengan fecha válida
    df_master = df_master.dropna(subset=['fecha_dt'])

    # Ordenamos cronológicamente
    df_master = df_master.sort_values(by='fecha_dt')

    print(f"\n📊 Total de carreras brutas: {len(df_master)}")

    # 4. ALGORITMO DE DEDUPLICACIÓN INTELIGENTE
    carreras_unicas = []

    # Agrupamos por fecha (solo comparamos carreras del mismo día)
    for fecha, grupo in df_master.groupby('fecha_dt'):

        lista_dia = grupo.to_dict('records')

        while lista_dia:
            # Cogemos la primera carrera como referencia
            candidata = lista_dia.pop(0)
            carreras_unicas.append(candidata)

            indices_a_borrar = []

            # La comparamos con el resto de carreras de ESE día
            for i, otra in enumerate(lista_dia):
                ratio = fuzz.token_sort_ratio(str(candidata['titulo']), str(otra['titulo']))

                # Si se parecen más de un 70%, es duplicada
                if ratio > 70:
                    print(f"   ✂️ Eliminando duplicado: '{otra['titulo']}' (== '{candidata['titulo']}')")
                    indices_a_borrar.append(i)

            # Borramos los duplicados encontrados de la lista pendiente
            for index in sorted(indices_a_borrar, reverse=True):
                del lista_dia[index]

    # 5. CREACIÓN DEL DATAFRAME FINAL
    df_final = pd.DataFrame(carreras_unicas)


    # Aquí lo guardamos como YYYY-MM-DD que es mejor para bases de datos
    df_final['fecha'] = df_final['fecha_dt'].dt.strftime('%Y-%m-%d')

    # Seleccionamos las columnas finales en orden limpio
    columnas_finales = ['fecha', 'titulo', 'ubicacion', 'url_inscripcion', 'url_ficha', 'imagen', 'origen']
    # Nos aseguramos de que existan antes de filtrar
    columnas_existentes = [c for c in columnas_finales if c in df_final.columns]
    df_final = df_final[columnas_existentes]

    print("💾 Guardando en base de datos...")

    contador_nuevas = 0
    contador_actualizadas = 0
    errores_supabase = 0

    for index, fila in df_final.iterrows():
        # Datos que vienen del scraper

        # Preparar datos para Supabase (diccionario) - LIMPIAMOS VALORES NaN
        datos_supabase = {
            'fecha': limpiar_datos_json(fila['fecha']),
            'titulo': limpiar_datos_json(fila['titulo']),
            'ubicacion': limpiar_datos_json(fila.get('ubicacion', '')),
            'url_inscripcion': limpiar_datos_json(fila.get('url_inscripcion', '')),
            'url_ficha': limpiar_datos_json(fila.get('url_ficha', '')),
            'imagen': limpiar_datos_json(fila.get('imagen', '')),
            'origen': limpiar_datos_json(fila.get('origen', '')),
            'publicada': 0
        }
        
        # A. Comprobamos si existe
        if supabase:
            try:
                resp = supabase.table('carreras').select('*').eq('titulo', fila['titulo']).maybe_single().execute()
                existe = resp.data if hasattr(resp, 'data') else None
            except Exception as e:
                print(f"   ⚠️ Error comprobando existencia en Supabase '{fila['titulo']}': {e}")
                existe = None
        else:
            existe = None

        if existe is None:
            # --- CASO 1: ES NUEVA ---
            # Insertamos en Supabase
            if supabase:
                try:
                    supabase.table('carreras').insert(datos_supabase).execute()
                    contador_nuevas += 1
                except Exception as e:
                    print(f"   ⚠️ Error insertando en Supabase '{fila['titulo']}': {e}")
                    errores_supabase += 1
        else:
            # --- CASO 2: YA EXISTE (Actualizamos) ---
            # Actualizamos en Supabase (sin alterar 'publicada')
            if supabase:
                try:
                    if 'imagen' in existe and existe['imagen'] == IMAGEN_DEFECTO_URL_ALCANZA:
                        supabase.table('carreras').update({
                            'fecha': datos_supabase['fecha'],
                            'ubicacion': datos_supabase['ubicacion'],
                            'url_ficha': datos_supabase['url_ficha'],
                            'imagen': datos_supabase['imagen'],
                            'origen': datos_supabase['origen'],
                            'url_inscripcion': datos_supabase['url_inscripcion']
                        }).eq('titulo', datos_supabase['titulo']).execute()
                        contador_actualizadas += 1
                    else:
                        supabase.table('carreras').update({
                            'fecha': datos_supabase['fecha'],
                            'ubicacion': datos_supabase['ubicacion'],
                            'url_ficha': datos_supabase['url_ficha'],
                            'origen': datos_supabase['origen'],
                            'url_inscripcion': datos_supabase['url_inscripcion']
                        }).eq('titulo', datos_supabase['titulo']).execute()
                        contador_actualizadas += 1
                except Exception as e:
                    print(f"   ⚠️ Error actualizando en Supabase '{fila['titulo']}': {e}")
                    errores_supabase += 1

    print(f"📊 Resumen de Sincronización:")
    print(f"   ✨ Nuevas insertadas: {contador_nuevas}")
    print(f"   🔄 Existentes revisadas/actualizadas: {contador_actualizadas}")
    if supabase:
        if errores_supabase > 0:
            print(f"   ⚠️ Errores en Supabase: {errores_supabase}")
        else:
            print(f"   ✅ Supabase sincronizado correctamente")
    print(f"   ✅ Base de datos lista.")