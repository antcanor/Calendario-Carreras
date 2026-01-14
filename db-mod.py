import sqlite3


def modificacion_linea():
    conn = sqlite3.connect('carreras.db')
    cursor = conn.cursor()
    titulo= "TotalEnergies%"
    fecha_corte = "2026-03-13"
    fecha_corte2 = "2026-03-15"
    imagen="https://www.tiempoabatir.com/files/eventos/mx/1639395147_9001197326.png"
    #print(f"🔄 Actualizando carreras a partir del {fecha_corte}...")

    #cursor.execute('UPDATE carreras SET publicada=1 WHERE fecha <= ?', (fecha_corte,))
    #cursor.execute('UPDATE carreras SET imagen=? WHERE titulo like ?', (imagen,titulo,))
    cursor.execute('DELETE FROM carreras WHERE fecha > ?', (fecha_corte2, ))
    # 2. Es importante ver cuántas filas ha tocado para saber si funcionó
    filas_afectadas = cursor.rowcount

    conn.commit()
    conn.close()

    print(f"✅ Hecho. Se han marcado como publicadas {filas_afectadas} carreras.")


modificacion_linea()