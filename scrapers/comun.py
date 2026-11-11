"""Utilidades compartidas por los scrapers: descarga, limpieza y guardado."""

import re
import unicodedata
from datetime import date, datetime

import pandas as pd
import requests
from bs4 import BeautifulSoup
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

COLUMNAS = ['fecha', 'titulo', 'ubicacion', 'url_inscripcion', 'url_ficha', 'imagen', 'origen',
            'modalidad', 'distancias', 'precio_min', 'precio_max']
TIMEOUT = 30
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
    "Accept-Language": "es-ES,es;q=0.9",
}

MESES = {
    'ene': 1, 'jan': 1, 'feb': 2, 'mar': 3, 'abr': 4, 'apr': 4, 'may': 5, 'jun': 6,
    'jul': 7, 'ago': 8, 'aug': 8, 'sep': 9, 'set': 9, 'oct': 10, 'nov': 11, 'dic': 12, 'dec': 12,
}

PROVINCIAS = {
    'a coruna', 'alava', 'albacete', 'alicante', 'almeria', 'asturias', 'avila', 'badajoz', 'baleares',
    'barcelona', 'bizkaia', 'burgos', 'caceres', 'cadiz', 'cantabria', 'castellon', 'ceuta', 'ciudad real',
    'cordoba', 'cuenca', 'gipuzkoa', 'girona', 'granada', 'guadalajara', 'huelva', 'huesca', 'illes balears',
    'jaen', 'la rioja', 'las palmas', 'leon', 'lleida', 'lugo', 'madrid', 'malaga', 'melilla', 'murcia',
    'navarra', 'ourense', 'palencia', 'pontevedra', 'salamanca', 'santa cruz de tenerife', 'segovia',
    'sevilla', 'soria', 'tarragona', 'teruel', 'toledo', 'valencia', 'valladolid', 'vizcaya', 'zamora', 'zaragoza',
}
_MINUSCULAS = {'de', 'del', 'la', 'las', 'los', 'el', 'y', 'en'}


def sin_acentos(texto):
    return ''.join(c for c in unicodedata.normalize('NFD', str(texto)) if unicodedata.category(c) != 'Mn')


def crear_sesion():
    """Sesión con cabeceras de navegador y reintentos ante errores temporales."""
    sesion = requests.Session()
    sesion.headers.update(HEADERS)
    reintentos = Retry(total=3, backoff_factor=2, status_forcelist=[429, 500, 502, 503, 504], allowed_methods=["GET"])
    adaptador = HTTPAdapter(max_retries=reintentos)
    sesion.mount('https://', adaptador)
    sesion.mount('http://', adaptador)
    return sesion


def descargar(sesion, url):
    """Devuelve la página como BeautifulSoup, o None si no se pudo descargar."""
    try:
        respuesta = sesion.get(url, timeout=TIMEOUT)
        respuesta.raise_for_status()
    except requests.RequestException as error:
        print(f"   ❌ No se pudo descargar {url}: {error}")
        return None
    # Pasamos los bytes para que BeautifulSoup detecte la codificación declarada en la página
    return BeautifulSoup(respuesta.content, 'html.parser')


def texto(elemento):
    """Texto de un elemento sin saltos ni espacios repetidos ('' si no existe)."""
    return ' '.join(elemento.get_text(' ', strip=True).split()) if elemento else ''


def interpretar_fecha(valor):
    """Acepta '2026-11-14', '14/11/2026', '14-11-2026', '14 de Noviembre de 2026' o '14 Nov 26'."""
    if isinstance(valor, datetime):
        return valor.date()
    if isinstance(valor, date):
        return valor
    cadena = sin_acentos(valor or '').lower().replace('.', ' ').strip()
    if not cadena:
        return None
    try:
        coincidencia = re.match(r'(\d{4})-(\d{1,2})-(\d{1,2})', cadena)
        if coincidencia:
            anio, mes, dia = map(int, coincidencia.groups())
            return date(anio, mes, dia)
        coincidencia = re.match(r'(\d{1,2})[/-](\d{1,2})[/-](\d{2,4})$', cadena)
        if coincidencia:
            dia, mes, anio = map(int, coincidencia.groups())
            return date(anio + 2000 if anio < 100 else anio, mes, dia)
        coincidencia = re.match(r'(\d{1,2})\s+(?:de\s+)?([a-z]+)\s+(?:de\s+)?(\d{2,4})$', cadena)
        if coincidencia and coincidencia.group(2)[:3] in MESES:
            anio = int(coincidencia.group(3))
            return date(anio + 2000 if anio < 100 else anio, MESES[coincidencia.group(2)[:3]], int(coincidencia.group(1)))
    except ValueError:
        pass
    return None


def _capitalizar(nombre):
    palabras = []
    for indice, palabra in enumerate(nombre.split()):
        if indice > 0 and palabra.lower() in _MINUSCULAS:
            palabras.append(palabra.lower())
        elif palabra.isupper() or palabra.islower():
            palabras.append(palabra.capitalize())
        else:
            palabras.append(palabra)
    return ' '.join(palabras)


def normalizar_ubicacion(valor, provincia=None):
    """Unifica la ubicación de todas las fuentes: 'Cieza' si es de Murcia, 'Monóvar (Alicante)' si no.

    Entiende los formatos 'Cieza / MURCIA', 'Cieza, Murcia', 'Cieza (Murcia)' y 'Cieza'.
    """
    lugar = ' '.join(str(valor or '').split())
    if not lugar or lugar.lower() == 'nan':
        return ''
    if not provincia:
        entre_parentesis = re.match(r'^(.*\S)\s*\(([^()]+)\)$', lugar)
        if '/' in lugar:
            lugar, provincia = (parte.strip() for parte in lugar.rsplit('/', 1))
        elif entre_parentesis and sin_acentos(entre_parentesis.group(2)).lower() in PROVINCIAS:
            lugar, provincia = entre_parentesis.group(1), entre_parentesis.group(2)
        elif ',' in lugar and sin_acentos(lugar.rsplit(',', 1)[1]).strip().lower() in PROVINCIAS:
            lugar, provincia = (parte.strip() for parte in lugar.rsplit(',', 1))
    # 'Algar, El' -> 'El Algar'; 'Hoya, La (la Hoya)' -> 'La Hoya'
    invertido = re.match(r'^(.*?),\s*(el|la|los|las)\b\s*(.*)$', lugar, re.IGNORECASE)
    if invertido:
        lugar = f"{invertido.group(2)} {invertido.group(1)} {invertido.group(3)}".strip()
    repetido = re.match(r'^(.*\S)\s*\(([^()]+)\)$', lugar)
    if repetido and repetido.group(1).lower() == repetido.group(2).lower():
        lugar = repetido.group(1)
    lugar = _capitalizar(lugar)
    if not lugar:
        return _capitalizar(provincia or '')
    if provincia and sin_acentos(provincia).strip().lower() != 'murcia':
        return f"{lugar} ({_capitalizar(provincia.strip())})"
    return lugar


def distancia_km(valor, sin_unidad=None):
    """Kilómetros de un texto como '26K', '21,1 km', '4.500 m' o 'Media Maratón' (None si no hay).

    `sin_unidad='m'` interpreta un número suelto ('16000') como metros.
    """
    cadena = sin_acentos(valor or '').lower()
    en_km = re.search(r'(\d+(?:[.,]\d+)?)\s*(?:kms?|k|kilometros)\b', cadena)
    if en_km:
        return round(float(en_km.group(1).replace(',', '.')), 3)
    en_metros = re.search(r'(\d{1,3}(?:\.\d{3})+|\d+)\s*(?:m|mts?|metros)\b', cadena)
    if en_metros:
        return round(int(en_metros.group(1).replace('.', '')) / 1000, 3)
    if sin_unidad == 'm' and re.fullmatch(r'\d+', cadena.strip()):
        return round(int(cadena) / 1000, 3)
    if 'media maraton' in cadena or 'medio maraton' in cadena:
        return 21.097
    if re.search(r'\bmaraton\b', cadena):
        return 42.195
    if re.search(r'\bmilla\b', cadena):
        return 1.609
    return None


def distancias_del_titulo(titulo):
    """Distancias que aparecen en un título: 'Media Maratón, 10K y 5K Archena' -> [10.0, 5.0, 21.097]."""
    cadena = sin_acentos(titulo or '').lower()
    kms = [round(float(numero.replace(',', '.')), 3) for numero in re.findall(r'(\d+(?:[.,]\d+)?)\s*(?:kms?|k)\b', cadena)]
    if 'media maraton' in cadena or 'medio maraton' in cadena:
        kms.append(21.097)
    elif re.search(r'\bmaraton\b', cadena):
        kms.append(42.195)
    return kms


def precio_euros(valor):
    """Importe de un texto como 'Desde 27,00 €' o '20.00 €' (None si no hay; 0 si es gratis)."""
    cadena = sin_acentos(valor or '').lower()
    importe = re.search(r'(\d+(?:[.,]\d{1,2})?)\s*(?:€|eur)', cadena)
    if importe:
        return float(importe.group(1).replace(',', '.'))
    if 'gratis' in cadena or 'gratuit' in cadena:
        return 0.0
    return None


def _numero(valor):
    return f"{valor:.3f}".rstrip('0').rstrip('.')


def resumir_pruebas(pruebas):
    """Resume las pruebas de una carrera [{'km': 26.0, 'precios': [27.0, 31.0]}, ...] en los
    campos del CSV: distancias en km ordenadas ('4.5,14,26') y precio mínimo y máximo vigentes."""
    distancias = sorted({prueba['km'] for prueba in pruebas if prueba.get('km')})
    precios = [precio for prueba in pruebas for precio in prueba.get('precios', []) if precio is not None]
    return {
        'distancias': ','.join(_numero(km) for km in distancias),
        'precio_min': _numero(min(precios)) if precios else '',
        'precio_max': _numero(max(precios)) if precios else '',
    }


_MODALIDADES = [
    # (modalidad, palabras que la delatan en el texto de la fuente o en el título)
    ('Marcha nórdica', ['marcha nordica', 'nordic']),
    ('Trail', ['trail', 'montana', 'cxm', 'vertical', 'ultra trail']),
    ('Híbrida', ['hibrid', 'hyrox', 'obstaculo', 'metcon', 'crossfit']),
    ('Natación', ['natacion', 'travesia a nado', 'aguas abiertas']),
    ('Triatlón / duatlón', ['triatlon', 'duatlon', 'acuatlon']),
    ('Ciclismo', ['ciclis', 'btt', 'mtb', 'cicloturis']),
    ('Senderismo', ['senderis', 'caminata', 'via ferrata']),
    ('Cross', ['campo a traves']),
    ('Running', ['running', 'carrera a pie', 'asfalto', 'ruta']),
]


def _clasificar(valor):
    cadena = sin_acentos(valor or '').lower()
    for modalidad, palabras in _MODALIDADES:
        if any(palabra in cadena for palabra in palabras):
            return modalidad
    return ''


def normalizar_modalidad(de_la_fuente, titulo=''):
    """Modalidad con un vocabulario común a todas las fuentes. Manda lo que diga la fuente; si no
    lo dice o es genérico ('Carrera a pie', 'Otros'), se afina con el título. Por defecto, 'Running'."""
    modalidad = _clasificar(de_la_fuente)
    if modalidad in ('', 'Running'):
        modalidad = _clasificar(titulo) or modalidad
    return modalidad or 'Running'


def carrera(titulo, fecha, ubicacion, origen, imagen='', url_ficha='', url_inscripcion='',
            modalidad='', pruebas=None):
    """Construye una carrera con el formato común. Devuelve None si falta el título o la fecha.

    `pruebas` es la lista de pruebas de la carrera: [{'km': 10.0, 'precios': [8.0, 12.0]}, ...].
    """
    titulo = ' '.join(str(titulo or '').split())
    dia = interpretar_fecha(fecha)
    if not titulo or not dia:
        return None
    resumen = resumir_pruebas(pruebas or [])
    if not resumen['distancias']:
        # Sin distancias en la ficha, al menos las que anuncie el título ('... 10K y 5K')
        resumen['distancias'] = resumir_pruebas([{'km': km} for km in distancias_del_titulo(titulo)])['distancias']
    return {
        'modalidad': normalizar_modalidad(modalidad, titulo),
        **resumen,
        'fecha': dia.strftime('%d-%m-%Y'),
        'titulo': titulo,
        'ubicacion': ubicacion or '',
        'url_inscripcion': url_inscripcion or '',
        'url_ficha': url_ficha or '',
        'imagen': imagen or '',
        'origen': origen,
    }


def guardar_csv(carreras, ruta):
    """Guarda el CSV de una fuente. Si no hay carreras NO se toca el archivo y devuelve False."""
    vistas = set()
    unicas = []
    for item in carreras:
        clave = (item['titulo'], item['fecha'])
        if clave not in vistas:
            vistas.add(clave)
            unicas.append(item)

    if not unicas:
        print(f"   ⚠️ 0 carreras: no se actualiza '{ruta}'. Puede que la web haya cambiado su HTML.")
        return False

    pd.DataFrame(unicas)[COLUMNAS].to_csv(ruta, index=False, encoding='utf-8-sig')
    sin_lugar = sum(1 for item in unicas if not item['ubicacion'])
    sin_imagen = sum(1 for item in unicas if not item['imagen'])
    con_distancia = sum(1 for item in unicas if item['distancias'])
    con_precio = sum(1 for item in unicas if item['precio_min'] != '')
    print(f"   📂 {len(unicas)} carreras guardadas en '{ruta}' ({sin_lugar} sin ubicación, {sin_imagen} sin cartel, "
          f"{con_distancia} con distancia, {con_precio} con precio)")
    return True
