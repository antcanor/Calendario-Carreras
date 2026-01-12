import pandas as pd
from thefuzz import fuzz
import os
import sqlite3


def fusionar_datos():
    print("🔄 Iniciando proceso de fusión...")

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

                # Si se parecen más de un 80%, es duplicada
                if ratio > 80:
                    print(f"   ✂️ Eliminando duplicado: '{otra['titulo']}' (== '{candidata['titulo']}')")
                    indices_a_borrar.append(i)

            # Borramos los duplicados encontrados de la lista pendiente
            for index in sorted(indices_a_borrar, reverse=True):
                del lista_dia[index]

    # 5. CREACIÓN DEL DATAFRAME FINAL
    df_final = pd.DataFrame(carreras_unicas)

    # Recuperamos el formato de fecha bonito (opcional: o dejarlo ISO YYYY-MM-DD)
    # Aquí lo guardamos como YYYY-MM-DD que es mejor para bases de datos
    df_final['fecha'] = df_final['fecha_dt'].dt.strftime('%Y-%m-%d')

    # Seleccionamos las columnas finales en orden limpio
    columnas_finales = ['fecha', 'titulo', 'ubicacion', 'url_inscripcion', 'url_ficha', 'imagen', 'origen']
    # Nos aseguramos de que existan antes de filtrar
    columnas_existentes = [c for c in columnas_finales if c in df_final.columns]
    df_final = df_final[columnas_existentes]

    print("💾 Guardando en base de datos SQL...")

    # 1. Conectamos (si no existe el archivo carreras.db, lo crea solo)
    conexion = sqlite3.connect('carreras.db')

    # 2. Guardamos el DataFrame en una tabla llamada 'carreras'
    # if_exists='replace' borra la tabla vieja y crea una nueva limpia cada vez
    df_final.to_sql('carreras', conexion, if_exists='replace', index=False)

    conexion.close()

    print(f"\n🎉 ¡PROCESO TERMINADO!")
    print(f"📉 Base de datos actualizada: 'carreras.db' con {len(df_final)} carreras.")