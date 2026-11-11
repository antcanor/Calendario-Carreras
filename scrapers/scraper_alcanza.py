"""Scraper de alcanzatumeta.es.

El calendario tiene una tarjeta <article class="atmc-card"> por carrera con título, fecha,
lugar, cartel y modalidad; la ficha de cada carrera añade sus pruebas con distancia y cuotas.
"""

import time
from urllib.parse import urljoin

from scrapers.comun import (carrera, crear_sesion, descargar, distancia_km, guardar_csv,
                            normalizar_ubicacion, precio_euros, texto)

URL_CALENDARIO = "https://www.alcanzatumeta.es/calendario.php"
RUTA_CSV = 'data/alcanzatumeta_completo.csv'
ORIGEN = 'ALCANZATUMETA'
PAUSA_FICHA = 0.5  # segundos entre fichas, para no saturar la web


def leer_pruebas(sesion, url_ficha):
    """Pruebas de la ficha: distancia y cuotas vigentes de cada una. [] si no se puede leer."""
    ficha = descargar(sesion, url_ficha)
    if not ficha:
        return []

    pruebas = []
    for prueba in ficha.select('.atmc-races .atmc-race-body'):
        nombre = texto(prueba.find('h3'))
        km = distancia_km(texto(prueba.select_one('.atmc-race-km'))) or distancia_km(nombre)
        # Cuotas del tramo vigente; si no hay desglose, el 'Desde X €' de la cabecera
        precios = [precio_euros(texto(cuota)) for cuota in prueba.select('.atmc-race-fees li.is-now strong')]
        if not precios:
            precios = [precio_euros(texto(prueba.select_one('.atmc-race-fee')))]
        pruebas.append({'km': km, 'precios': precios})
    return pruebas


def leer_tarjeta(sesion, tarjeta):
    enlace_titulo = tarjeta.select_one('h3 a')
    fecha = tarjeta.select_one('time[datetime]')
    imagen = tarjeta.select_one('.atmc-poster img')
    url_ficha = urljoin(URL_CALENDARIO, enlace_titulo['href']) if enlace_titulo and enlace_titulo.get('href') else ''

    url_inscripcion = ''
    for boton in tarjeta.select('.atmc-actions a[href]'):
        if 'inscrib' in texto(boton).lower():
            url_inscripcion = urljoin(URL_CALENDARIO, boton['href'])
            break

    pruebas = []
    if url_ficha:
        pruebas = leer_pruebas(sesion, url_ficha)
        time.sleep(PAUSA_FICHA)

    return carrera(
        titulo=texto(tarjeta.select_one('h3')),
        fecha=fecha['datetime'] if fecha else '',
        ubicacion=normalizar_ubicacion(texto(tarjeta.select_one('.atmc-where'))),
        origen=ORIGEN,
        imagen=urljoin(URL_CALENDARIO, imagen['src']) if imagen and imagen.get('src') else '',
        url_ficha=url_ficha,
        url_inscripcion=url_inscripcion,
        modalidad=tarjeta.get('data-modality', ''),
        pruebas=pruebas,
    )


def obtener_carreras():
    print(f"🔄 Conectando con {URL_CALENDARIO}...")
    sesion = crear_sesion()
    pagina = descargar(sesion, URL_CALENDARIO)
    if not pagina:
        return []

    tarjetas = pagina.select('article.atmc-card')
    print(f"   {len(tarjetas)} tarjetas; leyendo la ficha de cada carrera...")
    carreras = []
    for tarjeta in tarjetas:
        try:
            item = leer_tarjeta(sesion, tarjeta)
        except Exception as error:
            print(f"   ⚠️ Error leyendo una tarjeta: {error}")
            continue
        if item:
            carreras.append(item)

    print(f"   {len(carreras)} carreras leídas de {len(tarjetas)} tarjetas.")
    return carreras


def ejecucion():
    """Descarga y guarda el CSV. Devuelve True si se han obtenido carreras."""
    return guardar_csv(obtener_carreras(), RUTA_CSV)


if __name__ == "__main__":
    ejecucion()
