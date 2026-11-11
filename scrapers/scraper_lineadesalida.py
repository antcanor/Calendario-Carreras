"""Scraper de lineadesalida.net.

El listado paginado da título, fecha, miniatura y enlace; la ficha de cada carrera
añade la localidad exacta, el reglamento y el enlace de inscripción.
"""

import re
import time
from urllib.parse import urljoin

from scrapers.comun import (carrera, crear_sesion, descargar, distancia_km, guardar_csv,
                            normalizar_ubicacion, precio_euros, texto)

URL_LISTADO = "https://lineadesalida.net/proximas-carreras"
RUTA_CSV = 'data/lineadesalida_completo.csv'
ORIGEN = 'LINEADESALIDA'
MAX_PAGINAS = 30
PAUSA_FICHA = 1  # segundos entre fichas, para no saturar la web
PAUSA_PAGINA = 2


def primer_dia(valor):
    """Fecha 'dd/mm/aaaa' de un texto del listado. En pruebas de varios días
    ('06 y 07/03/2027') devuelve el primero."""
    completa = re.search(r'(\d{1,2})/(\d{1,2})/(\d{4})', valor)
    if not completa:
        return ''
    dia, mes, anio = completa.groups()
    varios_dias = re.match(r'\s*(\d{1,2})\s*(?:y|-|al)\s*$', valor[:completa.start()])
    if varios_dias:
        dia = varios_dias.group(1)
    return f"{dia}/{mes}/{anio}"


def leer_tarjeta(tarjeta):
    """Datos que ya vienen en el listado. Devuelve None si la tarjeta no enlaza a una carrera."""
    enlace = tarjeta.find('a', href=True)
    if not enlace:
        return None

    datos = [texto(dato) for dato in tarjeta.select('li small')]
    con_fecha = next((dato for dato in datos if re.search(r'\d{1,2}/\d{1,2}/\d{4}', dato)), '')
    lugar = next((dato for dato in datos if dato and dato != con_fecha), '')
    fecha = primer_dia(con_fecha)

    fondo = tarjeta.select_one('.card')
    imagen = re.search(r"url\(\s*['\"]?([^'\")]+)", fondo.get('style', '')) if fondo else None

    return {
        'url': urljoin(URL_LISTADO, enlace['href']),
        'titulo': texto(tarjeta.find('h3')),
        'fecha': fecha,
        'lugar': lugar,
        'imagen': urljoin(URL_LISTADO, imagen.group(1).strip()) if imagen else '',
    }


def valor_de(ficha, etiqueta):
    """Valor que sigue a una etiqueta de la ficha ('Lugar', 'Fecha'...)."""
    nodo = ficha.find(lambda el: el.name == 'div' and not el.find('div') and texto(el).lower() == etiqueta)
    return texto(nodo.find_next_sibling('div')) if nodo else ''


def leer_pruebas(ficha):
    """Pruebas de la tabla 'Modalidades' de la ficha y el tipo de la principal.

    Cada fila trae el nombre, etiquetas (tipo, distancia en K o en metros...) y el precio actual,
    que la web sustituye por las plazas libres cuando no lo muestra.
    """
    pruebas = []
    tipos = []
    for fila in ficha.select('tr.v2-event-row'):
        celdas = fila.find_all('td', recursive=False)
        if len(celdas) < 3:
            continue
        nombre = texto(celdas[1].find('div'))
        etiquetas = celdas[1].select('.badge')
        if etiquetas:
            tipos.append(texto(etiquetas[0]))
        con_distancia = next((etiqueta for etiqueta in etiquetas if etiqueta.select_one('.bi-signpost-split')), None)
        km = distancia_km(texto(con_distancia), sin_unidad='m') if con_distancia else distancia_km(nombre)
        precio = precio_euros(texto(celdas[2]))
        if precio is None:
            # La celda muestra plazas libres: el precio está en el desglose de tramos de la fila siguiente
            desglose = fila.find_next_sibling('tr')
            tramos = desglose.select('.v2-tramo-card') if desglose and 'v2-collapse-row' in (desglose.get('class') or []) else []
            vigente = next((tramo for tramo in tramos if 'tramo-activo' in tramo.get('class', [])), tramos[-1] if tramos else None)
            precio = precio_euros(texto(vigente.find('span'))) if vigente else None
        pruebas.append({'km': km, 'precios': [precio]})

    # El icono de la ficha distingue las carreras de montaña aunque la prueba figure como 'Carrera a pie'
    de_montana = any('montana' in (icono.get('src') or '') for icono in ficha.select('img[src*="/icons/"]'))
    return pruebas, ('Carrera de montaña' if de_montana else (tipos[0] if tipos else ''))


def leer_ficha(sesion, url):
    """Detalles de la ficha: lugar, fecha, reglamento, inscripción, pruebas y modalidad. {} si no se puede leer."""
    ficha = descargar(sesion, url)
    if not ficha:
        return {}

    detalle = {'lugar': valor_de(ficha, 'lugar'), 'fecha': valor_de(ficha, 'fecha')}
    detalle['pruebas'], detalle['modalidad'] = leer_pruebas(ficha)
    for boton in ficha.find_all('a', href=True):
        etiqueta = texto(boton).lower()
        if 'reglamento' in etiqueta and 'url_ficha' not in detalle:
            detalle['url_ficha'] = urljoin(url, boton['href'])
        elif 'invitado' in etiqueta and 'url_inscripcion' not in detalle:
            detalle['url_inscripcion'] = urljoin(url, boton['href'])
    return detalle


def obtener_todas_las_carreras():
    sesion = crear_sesion()
    carreras = []
    urls_vistas = set()

    for pagina in range(1, MAX_PAGINAS + 1):
        url_pagina = URL_LISTADO if pagina == 1 else f"{URL_LISTADO}?page={pagina}"
        print(f"📄 Página {pagina} ({url_pagina})...")

        listado = descargar(sesion, url_pagina)
        contenedor = listado.find('div', id='todasCarrerasDiv') if listado else None
        tarjetas = contenedor.select('div.col.d-flex.justify-content-center') if contenedor else []
        if not tarjetas:
            print("   Sin más carreras: fin del listado.")
            break

        nuevas = 0
        for tarjeta in tarjetas:
            try:
                base = leer_tarjeta(tarjeta)
                if not base or base['url'] in urls_vistas:
                    continue
                urls_vistas.add(base['url'])
                nuevas += 1

                detalle = leer_ficha(sesion, base['url'])
                time.sleep(PAUSA_FICHA)

                item = carrera(
                    titulo=base['titulo'],
                    fecha=base['fecha'] or detalle.get('fecha', ''),
                    ubicacion=normalizar_ubicacion(detalle.get('lugar') or base['lugar']),
                    origen=ORIGEN,
                    imagen=base['imagen'],
                    modalidad=detalle.get('modalidad', ''),
                    pruebas=detalle.get('pruebas'),
                    url_ficha=detalle.get('url_ficha', ''),
                    # Sin botón de invitado (inscripción cerrada) enlazamos a la página de la carrera
                    url_inscripcion=detalle.get('url_inscripcion') or base['url'],
                )
                if item:
                    carreras.append(item)
                else:
                    print(f"   ⚠️ Sin título o fecha: {base['url']}")
            except Exception as error:
                print(f"   ⚠️ Error leyendo una carrera: {error}")

        if nuevas == 0:
            break  # la web repite la última página cuando se pide una que no existe
        time.sleep(PAUSA_PAGINA)

    print(f"   {len(carreras)} carreras leídas.")
    return carreras


def ejecucion():
    """Descarga y guarda el CSV. Devuelve True si se han obtenido carreras."""
    return guardar_csv(obtener_todas_las_carreras(), RUTA_CSV)


if __name__ == "__main__":
    ejecucion()
