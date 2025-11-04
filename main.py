import sys
import subprocess
import sqlite3
from pathlib import Path

import dash
from dash import html
import dash_bootstrap_components as dbc

from src.pages.carte_choroplethe import layout as carte_layout
from src.pages.histogramme import histogramme_layout


# ==========================================================
#        Préparation automatique des données au démarrage
# ==========================================================

ROOT = Path(__file__).resolve().parent
DATA_DIR = ROOT / "data"
DB_PATH = DATA_DIR / "accidents.sqlite"
CLEANED_DIR = DATA_DIR / "cleaned"
SENTINEL = DATA_DIR / ".prepared"


def _db_has_tables(db_file: Path) -> bool:
    """Vérifie si la base SQLite existe et contient au moins une table."""
    if not db_file.exists() or db_file.stat().st_size == 0:
        return False
    try:
        with sqlite3.connect(db_file) as conn:
            cur = conn.execute("SELECT name FROM sqlite_master WHERE type='table' LIMIT 1;")
            return cur.fetchone() is not None
    except Exception:
        return False


def _run(cmd: list[str]) -> None:
    """Exécute une commande Python (script interne)."""
    subprocess.run(cmd, cwd=str(ROOT), check=True)


def ensure_data_ready() -> None:
    """
    Prépare les données si nécessaire :
    - Téléchargement (get_data.py)
    - Nettoyage (clean_data.py)
    - Conversion en base SQLite (to_sqlite.py)
    """
    if _db_has_tables(DB_PATH) and SENTINEL.exists():
        print("✅ Base déjà prête — aucune préparation nécessaire.")
        return

    DATA_DIR.mkdir(parents=True, exist_ok=True)
    utils_dir = ROOT / "src" / "utils"

    print("⚙️  Préparation initiale des données en cours...\n")

    _run([sys.executable, str(utils_dir / "get_data.py")])
    _run([sys.executable, str(utils_dir / "clean_data.py")])
    _run([
        sys.executable, str(utils_dir / "to_sqlite.py"),
        "--input", str(CLEANED_DIR),
        "--db", str(DB_PATH),
        "--overwrite",
    ])

    SENTINEL.write_text(
        "Données préparées automatiquement par main.py\n"
        "Les scripts src/utils/get_data.py, src/utils/clean_data.py et src/utils/to_sqlite.py ont été exécutés avec succès.\n"
        "Supprimez ce fichier si vous souhaitez forcer une régénération complète.\n",
        encoding="utf-8",
    )

    print("✅ Préparation terminée — la base SQLite est prête.\n")


# Lance la préparation avant de construire l'application Dash
try:
    ensure_data_ready()
except Exception as e:
    print(" Préparation des données ignorée (erreur non bloquante) :", e)
    print("   Lancez les scripts de src/utils si besoin, puis relancez l'app.")



# ==========================================================
#                      Application Dash
# ==========================================================

external_stylesheets = [dbc.themes.BOOTSTRAP]
app = dash.Dash(
    __name__,
    external_stylesheets=external_stylesheets,
    suppress_callback_exceptions=True,
)
app.title = "Dashboard - Accidents (SQLite)"


app.layout = dbc.Container(
    [
        # ---- Titre principal ----
        html.H3(
            "Dashboard – Accidents de la route (2024)",
            className="mt-3 mb-4 text-center",
            style={"color": "#b91c1c"},
        ),

        # ---- Disposition principale : carte + histogramme ----
        dbc.Row(
            [
                # Colonne gauche : carte + filtres + légende
                dbc.Col(
                    html.Div(carte_layout(app)),
                    width=8,
                    style={"paddingRight": "10px"},
                ),

                # Colonne droite : histogramme
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

        html.Br(),
        html.Br(),
    ],
    fluid=True,
)


# ==========================================================
#                         Lancement
# ==========================================================
if __name__ == "__main__":
    app.run(debug=True)
