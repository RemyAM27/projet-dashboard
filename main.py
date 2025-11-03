import sys
import subprocess
import sqlite3
from pathlib import Path

import dash
from dash import html
import dash_bootstrap_components as dbc

from src.pages.carte_choroplethe import layout as carte_layout
from src.pages.histogramme import histogramme_layout


# -------- Préparation des données (1ère exécution) --------
ROOT = Path(__file__).resolve().parent
DATA_DIR = ROOT / "data"
DB_PATH = DATA_DIR / "accidents.sqlite"
CLEANED_DIR = DATA_DIR / "cleaned"
SENTINEL = DATA_DIR / ".prepared"


def _db_has_tables(db_file: Path) -> bool:
    if not db_file.exists() or db_file.stat().st_size == 0:
        return False
    try:
        with sqlite3.connect(db_file) as conn:
            cur = conn.execute("SELECT name FROM sqlite_master WHERE type='table' LIMIT 1;")
            return cur.fetchone() is not None
    except Exception:
        return False


def _run(cmd: list[str]) -> None:
    subprocess.run(cmd, cwd=str(ROOT), check=True)


def ensure_data_ready() -> None:
    if _db_has_tables(DB_PATH) and SENTINEL.exists():
        return

    DATA_DIR.mkdir(parents=True, exist_ok=True)

    _run([sys.executable, "get_data.py"])
    _run([sys.executable, "clean_data.py"])
    _run([
        sys.executable, "to_sqlite.py",
        "--input", str(CLEANED_DIR),
        "--db", str(DB_PATH),
        "--overwrite"
    ])

    SENTINEL.write_text("ok", encoding="utf-8")


# Lance la préparation avant de construire l'app
ensure_data_ready()


# ----------------------- Dash app -------------------------
external_stylesheets = [dbc.themes.BOOTSTRAP]
app = dash.Dash(__name__, external_stylesheets=external_stylesheets, suppress_callback_exceptions=True)
app.title = "Dashboard - Accidents (SQLite)"

app.layout = dbc.Container(
    [
        html.H3(
            "Dashboard – Accidents de la route (2024)",
            className="mt-3 mb-4 text-center",
            style={"color": "#b91c1c"},
        ),

        dbc.Row(
            [
                dbc.Col(
                    html.Div(carte_layout(app)),
                    width=8,
                    style={"paddingRight": "10px"},
                ),
                dbc.Col(
                    html.Div(
                        histogramme_layout(app),
                        style={
                            "backgroundColor": "#ffffff",
                            "border": "1px solid #e5e7eb",
                            "borderRadius": "12px",
                            "boxShadow": "0 2px 10px rgba(0,0,0,0.06)",
                            "padding": "10px",
                            "height": "fit-content",
                        },
                    ),
                    width=4,
                ),
            ],
            justify="center",
            align="start",
            className="g-0",
        ),

        html.Br(), html.Br(),
    ],
    fluid=True,
)

if __name__ == "__main__":
    app.run(debug=True)
