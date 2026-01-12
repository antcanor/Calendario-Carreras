from flask import Flask, render_template
import sqlite3
from datetime import datetime

app = Flask(__name__)


def obtener_conexion():
    # Conecta a la base de datos y configura para recibir diccionarios
    conn = sqlite3.connect('carreras.db')
    conn.row_factory = sqlite3.Row
    return conn


@app.route('/')
def inicio():
    conn = obtener_conexion()

    # Consulta SQL: Dame todas las carreras futuras ordenadas por fecha
    # (Usamos date('now') para no mostrar carreras pasadas)

    carreras = conn.execute('SELECT * FROM carreras WHERE fecha >= date("now") ORDER BY fecha ASC').fetchall()
    conn.close()

    # Formateamos la fecha para que se vea bonita en la web (opcional)
    # Convertimos los objetos sqlite a una lista de diccionarios modificable
    lista_carreras = []
    for carrera in carreras:
        c = dict(carrera)
        # Convertir YYYY-MM-DD a algo como "18 Ene" si quieres
        fecha_obj = datetime.strptime(c['fecha'], '%Y-%m-%d')
        c['fecha_bonita'] = fecha_obj.strftime('%d/%m/%Y')
        lista_carreras.append(c)

    return render_template('index.html', carreras=lista_carreras)


if __name__ == '__main__':
    app.run(debug=True)