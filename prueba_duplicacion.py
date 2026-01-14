import pandas as pd
from thefuzz import fuzz
import sqlite3
import os

def probar_duplicacion():
    print("🔄 Iniciando proceso de fusión...")
    # 1. LISTA DE TUS ARCHIVOS db

    db = "carreras.db"
    conn = sqlite3.connect(db)
    query = "SELECT * FROM carreras"
    df_master = pd.read_sql_query(query, conn)
    conn.close()
    print(f"\n📊 Total de carreras brutas: {len(df_master)}")

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

    #imprimir carreras finales
    print("\n🏁 Carreras finales después de deduplicación:")
    for index, row in df_final.iterrows():
        print(f" - {row['fecha']}: {row['titulo']}")
    print("💾 Proceso de fusión y deduplicación completado.")

probar_duplicacion()
