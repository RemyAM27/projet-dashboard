import os
import sys
import subprocess
import sqlite3
from pathlib import Path

import dash
from dash import html
import dash_bootstrap_components as dbc


from src.components.carte_choroplethe import layout as carte_layout
from src.components.histogramme import histogramme_layout
from src.components.donut import donut_layout
from src.components.infos_departement import infos_departement_layout
from src.components.graphiquecourbe import graphiquecourbe_layout


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


def _bind_db_env(db_path: Path) -> None:
    os.environ["ACCIDENTS_DB_PATH"] = str(db_path)


def ensure_data_ready() -> None:
    if _db_has_tables(DB_PATH) and SENTINEL.exists():
        _bind_db_env(DB_PATH)
        return

    DATA_DIR.mkdir(parents=True, exist_ok=True)
    utils_dir = ROOT / "src" / "utils"

    print("Préparation initiale des données en cours...\n")

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
    print("Préparation terminée — la base SQLite est prête.\n")


try:
    ensure_data_ready()
except Exception as e:
    print("Préparation des données ignorée (erreur non bloquante) :", e)
    print("Lancez les scripts de src/utils si besoin, puis relancez l'app.")
    if DB_PATH.exists():
        _bind_db_env(DB_PATH)



CARD_STYLE = {
    "backgroundColor": "#ffffff",
    "border": "1px solid #e5e7eb",
    "borderRadius": "12px",
    "boxShadow": "0 2px 10px rgba(0,0,0,0.06)",
    "padding": "12px",
}

TITLE_STYLE = {
    "fontSize": "1.15rem",
    "fontWeight": "600",
    "color": "#1f2937",      
    "marginBottom": "8px",
}

def _get_total_accidents_2024(db_path: Path) -> int:
    """Compte le nombre total d'accidents (lignes) en 2024 dans la table caractéristiques."""
    with sqlite3.connect(db_path) as conn:
        tables = [r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table';")]
        cand = "caracteristiques" if "caracteristiques" in tables else None
        if cand is None:
            for t in tables:
                cols = {r[1].lower() for r in conn.execute(f"PRAGMA table_info('{t}')")}
                if "num_acc" in cols and ("an" in cols or "annee" in cols or "year" in cols):
                    cand = t
                    break
        if cand is None:
            return 0

        cols = {r[1].lower() for r in conn.execute(f"PRAGMA table_info('{cand}')")}
        ycol = "an" if "an" in cols else ("annee" if "annee" in cols else "year")
        row = conn.execute(f"SELECT COUNT(*) FROM {cand} WHERE {ycol} = 2024").fetchone()
        return int(row[0]) if row else 0


def _intro_paragraphs(total_2024: int) -> list:
    """
    Génère les paragraphes de présentation du dashboard (niveau professionnel).
    """
    txt = [
        "Ce tableau de bord présente une analyse complète des accidents de la route survenus en France en 2024, à partir des données officielles de la Sécurité routière.",
        "L’objectif est de visualiser et de comprendre la répartition spatiale et temporelle des accidents, ainsi que les profils les plus concernés.",
        "La carte illustre l’intensité des accidents par département, tandis que les graphiques mettent en évidence la répartition par âge des conducteurs, la gravité des victimes selon leur profil, et l’évolution mensuelle du nombre total d’accidents.",
        f"Le jeu de données recense environ {total_2024:,} accidents corporels sur le territoire français en 2024.".replace(",", " "),
    ]
    return [html.P(t) for t in txt]


external_stylesheets = [dbc.themes.BOOTSTRAP]
app = dash.Dash(
    __name__,
    external_stylesheets=external_stylesheets,
    suppress_callback_exceptions=True,
    meta_tags=[{"name": "viewport", "content": "width=device-width, initial-scale=1"}],
)
app.title = "Accidents de la route"



total_2024 = _get_total_accidents_2024(DB_PATH)

app.layout = dbc.Container(fluid=True, className="px-2", children=[
    html.H3(
        "Dashboard – Accidents de la route en France (2024)",
        className="text-center my-2",
        style={"color": "#b91c1c"}
    ),

    # À gauche : Intro / À droite : Infos département
    dbc.Row(className="gx-2", children=[
        dbc.Col(
            dbc.Card(
                dbc.CardBody([
                    html.H5("À propos du dashboard", style=TITLE_STYLE),
                    *(_intro_paragraphs(total_2024))
                ]),
                className="h-100 shadow-sm",
                style=CARD_STYLE
            ),
            xs=12, md=12, lg=7, className="mb-2"
        ),
        dbc.Col(
            dbc.Card(
                dbc.CardBody([
                    html.H5("Informations par département", style=TITLE_STYLE),
                    infos_departement_layout(app)
                ]),
                className="h-100 shadow-sm",
                style=CARD_STYLE
            ),
            xs=12, md=12, lg=5, className="mb-2"
        ),
    ]),

    # Carte + Histogramme
    dbc.Row(className="gx-2", children=[
        dbc.Col(
            dbc.Card(
                dbc.CardBody([
                    html.H5("Accidents de la route en France", style=TITLE_STYLE),
                    html.Div(carte_layout(app), style={"minHeight": "48vh"})
                ]),
                className="h-100 shadow-sm",
                style=CARD_STYLE
            ),
            xs=12, md=12, lg=8, className="mb-2"
        ),
        dbc.Col(
            dbc.Card(
                dbc.CardBody([
                    html.H5("Histogramme des accidents par âge", style=TITLE_STYLE),
                    histogramme_layout(app)
                ]),
                className="h-100 shadow-sm",
                style=CARD_STYLE
            ),
            xs=12, md=12, lg=4, className="mb-2"
        ),
    ]),

    #Donut + Courbe
    dbc.Row(className="gx-2 pb-2", children=[
        dbc.Col(
            dbc.Card(
                dbc.CardBody([
                    html.H5("Gravité des victimes selon le profil", style=TITLE_STYLE),
                    donut_layout(app)
                ]),
                className="h-100 shadow-sm",
                style=CARD_STYLE
            ),
            xs=12, md=12, lg=5, className="mb-2"
        ),
        dbc.Col(
            dbc.Card(
                dbc.CardBody([
                    html.H5("Nombre d'accidents par mois", style=TITLE_STYLE),
                    graphiquecourbe_layout(app)
                ]),
                className="h-100 shadow-sm",
                style=CARD_STYLE
            ),
            xs=12, md=12, lg=7, className="mb-2"
        ),
    ]),
])


if __name__ == "__main__":
    app.run(debug=True)
