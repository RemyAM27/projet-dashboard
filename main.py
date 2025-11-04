import os
import sys
import subprocess
import sqlite3
from pathlib import Path
from functools import partial

import dash
from dash import html
import dash_bootstrap_components as dbc

from src.pages.carte_choroplethe import layout as carte_layout
from src.pages.histogramme import histogramme_layout
from src.pages.donut import donut_layout   # <-- ajout

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
    """Exécute un script Python enfant dans le dossier racine du projet."""
    subprocess.run(cmd, cwd=str(ROOT), check=True)


def _bind_db_env(db_path: Path) -> None:
    """Expose le chemin de la base via variable d'env (optionnel mais pratique)."""
    os.environ["ACCIDENTS_DB_PATH"] = str(db_path)


def ensure_data_ready() -> None:
    """
    Prépare les données si nécessaire :
    - Téléchargement (get_data.py)
    - Nettoyage (clean_data.py)
    - Conversion en base SQLite (to_sqlite.py)
    """
    if _db_has_tables(DB_PATH) and SENTINEL.exists():
        print("✅ Base déjà prête — aucune préparation nécessaire.")
        _bind_db_env(DB_PATH)
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
        "Scripts exécutés : src/utils/get_data.py, src/utils/clean_data.py, src/utils/to_sqlite.py\n"
        "Supprimez ce fichier pour forcer une régénération complète.\n",
        encoding="utf-8",
    )

    _bind_db_env(DB_PATH)
    print("✅ Préparation terminée — la base SQLite est prête.\n")


# Lance la préparation avant de construire l'application Dash
try:
    ensure_data_ready()
except Exception as e:
    print("Préparation des données ignorée (erreur non bloquante) :", e)
    print("Lancez les scripts de src/utils si besoin, puis relancez l'app.")
    if DB_PATH.exists():
        _bind_db_env(DB_PATH)


# ==========================================================
#         Helpers spécifiques pour la courbe Jour/Nuit
# ==========================================================

def _detect_table_yearcol(conn: sqlite3.Connection) -> tuple[str, str | None]:
    """
    Retourne (table, col_annee) qui contient au moins 'mois' et 'lum'.
    col_annee peut être 'an', 'annee' ou 'year', ou None si absent.
    """
    tables = [r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table';")]
    # On priorise les noms classiques des BAAC
    preferred = ["caracteristiques", "accidents", "acc", "acc_caracteristiques"]
    ordered = preferred + [t for t in tables if t not in preferred]

    for t in ordered:
        cols = {r[1].lower() for r in conn.execute(f"PRAGMA table_info('{t}');").fetchall()}
        if {"mois", "lum"}.issubset(cols):
            year_col = "an" if "an" in cols else ("annee" if "annee" in cols else ("year" if "year" in cols else None))
            return t, year_col
    raise RuntimeError("Aucune table avec colonnes 'mois' et 'lum' trouvée dans la base.")


def _load_accidents_mois_lum(db_path: Path, year: int = 2024):
    """
    Charge uniquement les colonnes nécessaires à la page courbe :
    - 'mois' (1..12)
    - 'lum'  (codes BAAC)
    Si l'année demandée est absente, on bascule sur l'année la plus récente disponible.
    """
    import pandas as pd

    with sqlite3.connect(db_path) as conn:
        table, year_col = _detect_table_yearcol(conn)

        if year_col:
            sql = f"SELECT mois, lum FROM {table} WHERE {year_col} = ?"
            df = pd.read_sql_query(sql, conn, params=(year,))
            if df.empty:
                # Repli : dernière année dispo
                y = pd.read_sql_query(f"SELECT MAX({year_col}) AS y FROM {table}", conn)["y"].iat[0]
                if pd.notna(y):
                    df = pd.read_sql_query(sql, conn, params=(int(y),))
        else:
            # Pas de colonne d'année : on prend tout
            df = pd.read_sql_query(f"SELECT mois, lum FROM {table}", conn)

    # Mise en forme défensive
    for col in ("mois", "lum"):
        if col not in df.columns:
            df[col] = None
    df["mois"] = pd.to_numeric(df["mois"], errors="coerce").astype("Int64")
    df["lum"] = pd.to_numeric(df["lum"], errors="coerce").astype("Int64")
    df = df.dropna(subset=["mois", "lum"])

    return df


# ==========================================================
#              Imports des pages (après préparation)
# ==========================================================
from src.pages.carte_choroplethe import layout as carte_layout
from src.pages.histogramme import histogramme_layout

# On remplace la fonction utilisée dans la page 'graphiquecourbe' pour garantir
# la présence de 'mois' et 'lum', indépendamment de l'implémentation interne.
import src.pages.graphiquecourbe as courbe_page
courbe_page.load_accidents = partial(_load_accidents_mois_lum, DB_PATH)
graphiquecourbe_layout = courbe_page.graphiquecourbe_layout

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

        # ---- Disposition principale : carte à gauche / histogramme + donut à droite ----
        dbc.Row(
            [
                dbc.Col(
                    html.Div(carte_layout(app)),
                    width=8,
                    style={"paddingRight": "10px"},
                ),

                # Colonne droite : histogramme puis donut (empilés)
                dbc.Col(
                    html.Div(
                        [
                            html.Div(  # carte blanche histogramme
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
                            html.Div(style={"height": "12px"}),  # petit espace

                            html.Div(  # carte blanche donut
                                donut_layout(app),
                                style={
                                    "backgroundColor": "#ffffff",
                                    "border": "1px solid #e5e7eb",
                                    "borderRadius": "12px",
                                    "boxShadow": "0 2px 10px rgba(0,0,0,0.06)",
                                    "padding": "10px",
                                    "height": "fit-content",
                                },
                            ),
                        ]
                    ),
                    width=4,
                ),
            ],
            justify="center",
            align="start",
            className="g-0",
        ),

        # ---- Rangée 2 : courbe Jour/Nuit (pleine largeur) ----
        dbc.Row(
            [
                dbc.Col(
                    html.Div(
                        graphiquecourbe_layout(app),
                        style={
                            "backgroundColor": "#ffffff",
                            "border": "1px solid #e5e7eb",
                            "borderRadius": "12px",
                            "boxShadow": "0 2px 10px rgba(0,0,0,0.06)",
                            "padding": "10px",
                        },
                    ),
                    width=12,
                )
            ],
            className="mt-3",
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
