# Calendario-Carreras

This repository contains a web application that aggregates and displays a unified calendar of upcoming running races in the Murcia region of Spain. It automatically scrapes data from various sources, merges them, removes duplicates, and presents them in a clean, user-friendly web interface.

## How It Works

The project operates through a multi-step, automated pipeline:

1.  **Scraping**: Individual Python scripts (`crawlers/`) connect to different race calendar websites (`alcanzatumeta.es`, `babelsport.com`, `lineadesalida.net`). They parse the HTML to extract race details such as title, date, location, image, and registration links.
2.  **Data Aggregation**: The results from each crawler are initially saved as separate `.csv` files in the `data/` directory.
3.  **Fusion & Deduplication**: The `fusionar_carreras.py` script reads all `.csv` files, standardizes the data (especially date formats), and merges them into a single dataset. It then implements an intelligent deduplication algorithm using `thefuzz` library to identify and merge duplicate race entries by comparing their titles.
4.  **Database Storage**: The final, clean, and unique list of races is stored in a SQLite database file, `carreras.db`, replacing the old data.
5.  **Web Display**: A Flask application (`app.py`) reads the race data from `carreras.db`. It selects only the upcoming races, formats the dates for display, and renders them on a web page using the `index.html` template.
6.  **Automation**: A GitHub Actions workflow (`.github/workflows/actualizar.yml`) is configured to run the entire data pipeline (`main.py`) automatically every day. It then commits the updated `carreras.db` file back to the repository, ensuring the race calendar is always up-to-date.

## Technology Stack

*   **Backend**: Python
*   **Data Scraping**: Beautiful Soup, Requests
*   **Data Processing**: Pandas, TheFuzz
*   **Database**: SQLite
*   **Frontend**: HTML, Bootstrap
*   **Automation**: GitHub Actions
*   **Deployment**: Vercel

## Local Setup and Usage

To run this project on your local machine, follow these steps:

1.  **Clone the repository:**
    ```sh
    git clone https://github.com/antcanor/Calendario-Carreras.git
    cd Calendario-Carreras
    ```

2.  **Install the required dependencies:**
    ```sh
    pip install -r requirements.txt
    ```

3.  **Run the data pipeline:**
    This command executes all crawlers and the fusion script to build the `carreras.db` database.
    ```sh
    python main.py
    ```

4.  **Start the Flask web server:**
    ```sh
    python app.py
    ```

5.  Open your web browser and navigate to `http://127.0.0.1:5000` to see the race calendar.
