"""Actualiza el calendario: ejecuta los scrapers, fusiona y sincroniza Turso.

Uso:
    python main.py            # actualización completa
    python main.py --dry-run  # descarga y muestra los cambios, sin escribir en Turso
"""

import argparse
import sys

import fusionar_carreras
from scrapers import scraper_alcanza, scraper_babel, scraper_lineadesalida

FUENTES = [
    ('Alcanza tu Meta', scraper_alcanza),
    ('Línea de Salida', scraper_lineadesalida),
    ('Babelsport', scraper_babel),
]


def ejecutar_todo(dry_run=False):
    print("🚀 INICIANDO ACTUALIZACIÓN DEL CALENDARIO DE MURCIA 🚀")

    archivos = []
    fallidas = []
    for numero, (nombre, scraper) in enumerate(FUENTES, start=1):
        print(f"\n--- {numero}. Descargando {nombre} ---")
        try:
            correcto = scraper.ejecucion()
        except Exception as error:
            print(f"   ❌ Error inesperado: {error}")
            correcto = False
        # Solo se fusionan las fuentes descargadas ahora: un CSV antiguo metería datos caducados
        if correcto:
            archivos.append(scraper.RUTA_CSV)
        else:
            fallidas.append(nombre)

    print(f"\n--- {len(FUENTES) + 1}. Fusionando y limpiando ---")
    fusion_correcta = bool(archivos) and fusionar_carreras.fusionar_datos(archivos=archivos, dry_run=dry_run)

    if fallidas:
        print(f"\n❌ Fuentes sin datos: {', '.join(fallidas)}. Revisa si la web ha cambiado su HTML.")
    if not fusion_correcta:
        print("\n❌ La fusión no se ha completado.")
    if fallidas or not fusion_correcta:
        return False

    print("\n✅ ¡TODO LISTO!" + (" (simulación)" if dry_run else " Base de datos actualizada."))
    return True


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Actualiza el calendario de carreras.")
    parser.add_argument('--dry-run', action='store_true', help="No escribe en Turso ni avisa a Vercel.")
    # Código de salida 1 si algo falla, para que GitHub Actions marque la ejecución en rojo
    sys.exit(0 if ejecutar_todo(dry_run=parser.parse_args().dry_run) else 1)
