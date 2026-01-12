# Importamos las funciones de tus otros scripts
# (asegúrate de que los archivos .py estén en la misma carpeta)
from crawlers import crawler_lineadesalida, crawler_babel, crawler_alcanza
import fusionar_carreras  # El script de arriba


def ejecutar_todo():
    print("🚀 INICIANDO ACTUALIZACIÓN DEL CALENDARIO DE MURCIA 🚀")

    # Paso 1: Ejecutar Crawlers
    print("\n--- 1. Descargando FAMU ---")
    crawler_alcanza.ejecucion()  # O como se llame tu función principal

    print("\n--- 2. Descargando Linea de Salida ---")
    crawler_lineadesalida.ejecucion()

    print("\n--- 3. Descargando Babelsport ---")
    crawler_babel.ejecucion()

    # Paso 2: Fusionar
    print("\n--- 4. Fusionando y Limpiando ---")
    fusionar_carreras.fusionar_datos()

    print("\n✅ ¡TODO LISTO! Base de datos actualizada.")


if __name__ == "__main__":
    ejecutar_todo()