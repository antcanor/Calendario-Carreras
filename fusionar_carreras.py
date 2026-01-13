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

    print("💾 Guardando en base de datos SQL...")

    #Conectamos (si no existe el archivo carreras.db, lo crea solo)
    conn = sqlite3.connect('carreras.db')
    cursor = conn.cursor()
    # 1. CREAR TABLA SI NO EXISTE
    # (Añadimos la columna 'publicada' por defecto en 0)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS carreras (
            fecha TEXT,
            titulo TEXT PRIMARY KEY,
            ubicacion TEXT,
            url_inscripcion TEXT,
            url_ficha TEXT,
            imagen TEXT,
            origen TEXT,
            publicada INTEGER DEFAULT 0
        )
    ''')
    conn.commit()
    # 2. PROCESAR CADA CARRERA UNA A UNA
    contador_nuevas = 0
    contador_actualizadas = 0

    for index, fila in df_final.iterrows():
        # Datos que vienen del scraper
        datos_nuevos = (
            fila['fecha'],
            fila['titulo'], # Este es el ID (WHERE)
            fila['ubicacion'],
            fila['url_ficha'],
            fila['imagen'],
            fila['origen'],
            fila['url_inscripcion']
        )
        # A. Comprobamos si existe
        cursor.execute("SELECT * FROM carreras WHERE titulo = ?", (fila['titulo'],))
        existe = cursor.fetchone()

        if not existe:
            # --- CASO 1: ES NUEVA ---
            # Insertamos todo. 
            cursor.execute('''
                    INSERT INTO carreras (fecha, titulo, ubicacion, url_ficha, imagen, origen, url_inscripcion)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                ''', datos_nuevos)
            contador_nuevas += 1
        else:
            # --- CASO 2: YA EXISTE (Actualizamos) ---
            # Actualizamos todos los campos MENOS 'publicada' y 'url_inscripcion' y imagen si ya estaba puesta
            # Así, si ya la publicaste en Instagram (publicada=1), ese dato NO SE PIERDE.

            # Opcional: Podríamos comprobar si algo cambió para no escribir por gusto,
            # pero SQLite es rápido, así que sobrescribimos para asegurar que está al día.
            cursor.execute('''
                    UPDATE carreras 
                    SET fecha=?, url_inscripcion=?, ubicacion=?, url_ficha=?, imagen=?, origen=?
                    WHERE titulo=?
                ''', datos_nuevos)

            # (Truco: Rowcount aquí no siempre es fiable en updates silenciosos, pero asumimos actualización)
            contador_actualizadas += 1
    conn.commit()
    conn.close()

    print(f"📊 Resumen de Sincronización:")
    print(f"   ✨ Nuevas insertadas: {contador_nuevas}")
    print(f"   🔄 Existentes revisadas/actualizadas: {contador_actualizadas}")
    print(f"   ✅ Base de datos 'carreras.db' lista.")