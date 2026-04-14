# Calendario de Carreras (Murcia)

Este proyecto agrega y muestra un calendario unificado de próximas carreras (principalmente en la región de Murcia). El sistema **scrapea** varias webs, **normaliza y elimina duplicados**, guarda el resultado en una **base de datos en Turso** y el **frontend en Astro** lo consume directamente desde allí.

## Cómo funciona (flujo actual)

1. **Scraping (Python)**
   - En `scrapers/` hay scripts que obtienen carreras desde distintas fuentes (por ejemplo: `alcanzatumeta.es`, `babelsport.com`, `lineadesalida.net`).
   - Cada scraper extrae datos como: título, fecha, ubicación, imagen y enlaces (inscripción/ficha).

2. **Agregación temporal (CSVs)**
   - Los scrapers guardan resultados intermedios en ficheros `.csv` dentro de `data/`.

3. **Fusión y deduplicación**
   - `fusionar_carreras.py` lee los CSVs, estandariza datos (especialmente fechas) y deduplica usando coincidencia aproximada de títulos (librería `thefuzz`).

4. **Persistencia en base de datos (Turso)**
   - El resultado final se inserta/actualiza en la tabla `carreras` en **Turso** (libSQL).
   - Variables de entorno necesarias:
     - `TURSO_DATABASE_URL`
     - `TURSO_AUTH_TOKEN`

5. **Frontend (Astro) consumiendo Turso**
   - El frontend está en `front/`.
   - La página `front/src/pages/index.astro` se conecta a Turso con `@libsql/client` y ejecuta una consulta tipo:
     - “dame carreras con `fecha >= hoy` ordenadas por fecha”.

6. **Automatización y despliegue**
   - El pipeline puede ejecutarse de forma automática (por ejemplo, con GitHub Actions).
   - Cuando hay cambios, el script puede avisar a Vercel mediante un webhook para reconstruir la web:
     - `VERCEL_URL` (webhook)

## Publicación automática en Instagram (Make)

Además del calendario, el proyecto puede **publicar carreras en Instagram**:

- El script `instagram.py`:
  1. Se conecta a Turso.
  2. Busca la próxima carrera futura **no publicada** (`publicada = 0`), ordenada por fecha.
  3. Envía los datos (título, fecha, ubicación, imagen, link) a un **webhook de Make**.
  4. Si el envío va bien, marca la carrera como publicada (`publicada = 1`) en la base de datos.

Variables de entorno:
- `WEBHOOK_URL` (webhook de Make)
- `TURSO_DATABASE_URL`
- `TURSO_AUTH_TOKEN`

## Stack tecnológico

- **Scraping/ETL**: Python, Requests, BeautifulSoup, Pandas, TheFuzz
- **Base de datos**: Turso (libSQL)
- **Frontend**: Astro (carpeta `front/`)
- **Automatización**: GitHub Actions
- **Despliegue**: Vercel
- **Automatización Instagram**: Make (webhook) + `instagram.py`

## Ejecución local

### 1) Requisitos
- Python instalado
- Node.js + npm (para el frontend Astro)
- Credenciales de Turso y (opcionalmente) webhook de Make / Vercel

### 2) Backend / Pipeline (Python)

Instalar dependencias:
```sh
pip install -r requirements.txt
```

Configurar variables de entorno (por ejemplo en un `.env` local) y ejecutar:
```sh
python main.py
```

Esto ejecuta scrapers + fusión/deduplicación + actualización en **Turso**.

### 3) Publicación en Instagram (opcional)

Con las variables configuradas (`WEBHOOK_URL`, `TURSO_DATABASE_URL`, `TURSO_AUTH_TOKEN`):
```sh
python instagram.py
```

### 4) Frontend (Astro)

```sh
cd front
npm install
npm run dev
```

Luego abre `http://localhost:4321`.
