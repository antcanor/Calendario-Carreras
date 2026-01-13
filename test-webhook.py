import requests

# PEGA TU URL DE MAKE AQUÍ
url = "https://hook.eu1.make.com/url"

datos_falsos = {
    "titulo": "Carrera de Prueba",
    "fecha": "2026-05-20",
    "ubicacion": "Murcia Centro",
    "imagen": "https://img.freepik.com/foto-gratis/silueta-hombre-joven-fitness-correr-sunrise_1150-14615.jpg?semt=ais_hybrid&w=740&q=80", # Una imagen falsa cualquiera
    "link": "http://google.com"
}

requests.post(url, json=datos_falsos)
print("Datos enviados.")