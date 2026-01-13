import sqlite3


def modificacion_linea():
    conn = sqlite3.connect('carreras.db')
    cursor = conn.cursor()
    titulo= "El Buitre%"
    fecha_corte = "2026-01-31"

    #print(f"🔄 Actualizando carreras a partir del {fecha_corte}...")

    #cursor.execute('UPDATE carreras SET publicada=1 WHERE fecha <= ?', (fecha_corte,))
    cursor.execute('UPDATE carreras SET publicada=0 WHERE titulo like ?', (titulo,))

    # 2. Es importante ver cuántas filas ha tocado para saber si funcionó
    filas_afectadas = cursor.rowcount

    conn.commit()
    conn.close()

    print(f"✅ Hecho. Se han marcado como publicadas {filas_afectadas} carreras.")


modificacion_linea()