"""Añade coordenadas a las carreras para poder mostrarlas en un mapa.

Uso:
    python geocodificar_carreras.py          # simulación: no modifica Turso
    python geocodificar_carreras.py --write  # guarda las coordenadas encontradas

Variables necesarias en .env:
    TURSO_DATABASE_URL
    TURSO_AUTH_TOKEN
    NOMINATIM_USER_AGENT=CalendarioCarrerasMurcia/1.0 (tu-email@dominio.com)
"""

import argparse
import os
import time
from datetime import date

import libsql_client
import requests
from dotenv import load_dotenv


NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"
PAUSA_ENTRE_CONSULTAS = 1.1  # La política pública de Nominatim limita a 1 petición/segundo.


def asegurar_columnas(client):
    """Crea los campos del mapa una única vez; ignora el error si ya existen."""
    for columna in ("latitud REAL", "longitud REAL"):
        try:
            client.execute(f"ALTER TABLE carreras ADD COLUMN {columna}")
            print(f"✓ Columna creada: {columna.split()[0]}")
        except Exception as error:
            if "duplicate column" not in str(error).lower():
                raise


def buscar_coordenadas(ubicacion, user_agent):
    lugar = ubicacion.strip()

    if "/" in lugar:
        nombre, provincia = (parte.strip() for parte in lugar.split("/", 1))
        consulta = f"{nombre}, {provincia}, España"
    else:
        nombre = lugar
        consulta = f"{lugar}, Región de Murcia, España"

    respuesta = requests.get(
        NOMINATIM_URL,
        params={"q": consulta, "format": "jsonv2", "limit": 1, "countrycodes": "es"},
        headers={"User-Agent": user_agent, "Accept-Language": "es"},
        timeout=20,
    )
    respuesta.raise_for_status()
    resultados = respuesta.json()

    if (not resultados and '/' in lugar)  or (not resultados):
        # Fallback: si la provincia concreta no da resultado, prueba solo con el nombre + España
        respuesta = requests.get(
            NOMINATIM_URL,
            params={"q": f"{nombre}, España", "format": "jsonv2", "limit": 1, "countrycodes": "es"},
            headers={"User-Agent": user_agent, "Accept-Language": "es"},
            timeout=20,
        )
        respuesta.raise_for_status()
        resultados = respuesta.json()

    if not resultados:
        return None
    return float(resultados[0]["lat"]), float(resultados[0]["lon"])

def main():
    parser = argparse.ArgumentParser(description="Geocodifica ubicaciones de carreras en Turso.")
    parser.add_argument("--write", action="store_true", help="Guarda las coordenadas en Turso.")
    args = parser.parse_args()

    load_dotenv()
    turso_url = os.getenv("TURSO_DATABASE_URL")
    turso_token = os.getenv("TURSO_AUTH_TOKEN")
    user_agent = os.getenv("NOMINATIM_USER_AGENT")

    if not turso_url or not turso_token:
        raise SystemExit("Faltan TURSO_DATABASE_URL o TURSO_AUTH_TOKEN en .env.")
    if not user_agent:
        raise SystemExit("Añade NOMINATIM_USER_AGENT a .env con el nombre de la app y un email de contacto.")

    client = libsql_client.create_client_sync(turso_url, auth_token=turso_token)
    try:
        columnas = {fila[1] for fila in client.execute("PRAGMA table_info(carreras)").rows}
        faltan_columnas = {"latitud", "longitud"} - columnas
        if faltan_columnas:
            if not args.write:
                raise SystemExit(
                    "Faltan las columnas de coordenadas. Ejecuta primero con --write para crearlas; "
                    "la simulación no modifica Turso."
                )
            asegurar_columnas(client)
        pendientes = client.execute(
            "SELECT titulo, ubicacion FROM carreras "
            "WHERE fecha >= ? AND ubicacion IS NOT NULL AND ubicacion != '' "
            "AND (latitud IS NULL OR longitud IS NULL)",
            [date.today().isoformat()],
        ).rows
        cache = {}
        actualizadas = 0

        print(f"{'Guardando' if args.write else 'Simulando'} {len(pendientes)} carreras pendientes.")
        for titulo, ubicacion in pendientes:
            lugar = str(ubicacion).strip()
            if lugar not in cache:
                try:
                    cache[lugar] = buscar_coordenadas(lugar, user_agent)
                except requests.RequestException as error:
                    print(f"✗ No se pudo localizar '{lugar}': {error}")
                    cache[lugar] = None
                time.sleep(PAUSA_ENTRE_CONSULTAS)

            coordenadas = cache[lugar]
            if not coordenadas:
                print(f"? Sin resultado: {titulo} — {lugar}")
                continue

            latitud, longitud = coordenadas
            print(f"{'✓' if args.write else '·'} {titulo} — {lugar}: {latitud:.5f}, {longitud:.5f}")
            if args.write:
                client.execute(
                    "UPDATE carreras SET latitud = ?, longitud = ? WHERE titulo = ?",
                    [latitud, longitud, titulo],
                )
                actualizadas += 1

        print(f"Terminado. {actualizadas} carreras actualizadas." if args.write else "Simulación terminada. Ejecuta con --write para guardar.")
    finally:
        client.close()


if __name__ == "__main__":
    main()
