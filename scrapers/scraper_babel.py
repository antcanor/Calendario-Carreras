"""Scraper de babelsport.com: una tarjeta <article class="bs-event-card"> por carrera."""

from urllib.parse import urljoin

from scrapers.comun import carrera, crear_sesion, descargar, guardar_csv, normalizar_ubicacion, texto

URL_EVENTOS = "https://www.babelsport.com/eventos-proximos/"
RUTA_CSV = 'data/babelsport_completo.csv'
ORIGEN = 'BABELSPORT'


def leer_tarjeta(tarjeta):
    fecha = tarjeta.select_one('time[datetime]')
    imagen = tarjeta.select_one('.bs-card-image img')

    lugar = tarjeta.select_one('.bs-location')
    if lugar:
        for icono in lugar.select('[aria-hidden]'):
            icono.decompose()  # el símbolo ⌖ que precede a la localidad

    url_ficha = ''
    url_inscripcion = ''
    for boton in tarjeta.select('.bs-card-actions a[href]'):
        etiqueta = texto(boton).lower()
        if 'reglamento' in etiqueta:
            url_ficha = urljoin(URL_EVENTOS, boton['href'])
        elif 'inscr' in etiqueta or 'bs-enroll' in (boton.get('class') or []):
            url_inscripcion = urljoin(URL_EVENTOS, boton['href'])

    return carrera(
        titulo=texto(tarjeta.select_one('h3')),
        fecha=fecha['datetime'] if fecha else '',
        ubicacion=normalizar_ubicacion(texto(lugar)),
        origen=ORIGEN,
        imagen=urljoin(URL_EVENTOS, imagen['src']) if imagen and imagen.get('src') else '',
        url_ficha=url_ficha,
        url_inscripcion=url_inscripcion,
    )


def obtener_carreras():
    print(f"🔄 Conectando con {URL_EVENTOS}...")
    pagina = descargar(crear_sesion(), URL_EVENTOS)
    if not pagina:
        return []

    tarjetas = pagina.select('article.bs-event-card')
    carreras = []
    for tarjeta in tarjetas:
        try:
            item = leer_tarjeta(tarjeta)
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
