from __future__ import annotations
import sqlite3
from pathlib import Path

import dash
import dash_bootstrap_components as dbc
from dash import html, dcc, Input, Output
import pandas as pd

from config import DB_PATH, DEPT_GEOJSON
from ..utils.data_utils import load_geojson_departments
from ..components.map_choropleth import BASE_COLOR_MAP

YEAR = 2024  # L'année des données utilisées pour l'analyse


# Fonction pour récupérer les codes des départements métropolitains (01..95, sauf 20, puis 2A, 2B)
def _codes_metropole() -> list[str]:
    """
    Liste ordonnée des départements métropolitains :
    01..95 (sauf 20) puis 2A et 2B à la fin.
    """
    codes = [f"{i:02d}" for i in range(1, 96) if i != 20]
    codes += ["2A", "2B"]
    return codes

# Fonction pour récupérer l'ensemble des départements (Métropole + DOM)
def _codes_101() -> list[str]:
    """
    Ensemble /101 = Métropole (96) + DOM (971..976).
    Utilisé pour le classement et la part du total.
    """
    codes = _codes_metropole()
    codes += [str(i) for i in range(971, 977)]  # Ajouter les DOM (971..976)
    return codes

# Dictionnaire de secours pour les noms des départements
FALLBACK_NAMES = {
    "2A": "Corse-du-Sud",
    "2B": "Haute-Corse",
    "971": "Guadeloupe",
    "972": "Martinique",
    "973": "Guyane",
    "974": "La Réunion",
    "976": "Mayotte",
}


# Fonction pour normaliser les codes des départements (ex: gérer les cas 201/202 -> 2A/2B et ajout de zéros pour les autres)
def _normalize_dep_series(s: pd.Series) -> pd.Series:
    """Gère 201/202 -> 2A/2B et zéro-padding ailleurs (01, 02, ...)."""
    s = s.astype(str).str.strip().str.upper()  # Convertir en majuscules et enlever les espaces
    s = s.replace({"201": "2A", "202": "2B"})  # Remplacer les codes de la Corse
    s = s.where(s.isin(["2A", "2B"]), s.str.zfill(2))  # Appliquer le zéro-padding pour les autres départements
    return s


# Fonction pour charger le nombre d'accidents par département pour une année donnée
def _load_dep_counts(db_file: Path, year: int = YEAR) -> pd.DataFrame:
    """Retourne dep, n (nb d'accidents) pour l'année donnée."""
    with sqlite3.connect(db_file) as conn:
        q = """
        SELECT dep AS dep, COUNT(*) AS n
        FROM caracteristiques
        WHERE an = ?
        GROUP BY dep
        """
        df = pd.read_sql_query(q, conn, params=[year])
    df["dep"] = _normalize_dep_series(df["dep"])  # Normaliser les codes des départements
    return df


# Fonction pour créer la liste des options de départements pour le dropdown
def _dropdown_options(geojson: dict, ordered_codes: list[str]) -> list[dict]:
    """
    Construit la liste déroulante STRICTEMENT dans l'ordre fourni.
    Assure 2A/2B via noms de secours si absents du GeoJSON.
    """
    names = {}
    # Récupérer les noms des départements depuis le GeoJSON
    for f in geojson.get("features", []):
        code = str(f["properties"].get("code", "")).strip().upper()
        nom = f["properties"].get("nom", "")
        if code:
            names[code] = nom
    # Ajouter les noms de secours pour les départements 2A et 2B si non présents
    names.setdefault("2A", "Corse-du-Sud")
    names.setdefault("2B", "Haute-Corse")

    # Créer la liste des options du dropdown
    opts = []
    for code in ordered_codes:
        label = f"{code} - {names.get(code, 'Département')}"
        opts.append({"label": label, "value": code})
    return opts


# Fonction qui définit le layout de la page avec le dropdown et les KPIs de chaque département
def infos_departement_layout(app: dash.Dash) -> dbc.Card:
    db_file = Path(DB_PATH)
    geojson = load_geojson_departments(Path(DEPT_GEOJSON))  # Charger les départements du GeoJSON

    counts = _load_dep_counts(db_file, YEAR)  # Charger les comptes d'accidents par département

    codes96_list = _codes_metropole()  # Liste des départements métropolitains
    codes101_set = set(_codes_101())  # Ensemble des départements Métropole + DOM

    # Trier les départements pour affichage
    all_codes_sorted = sorted(codes101_set, key=lambda x: x.replace("A", "0A").replace("B", "0B"))
    all_codes_df = pd.DataFrame({"dep": all_codes_sorted})
    depc_all = all_codes_df.merge(counts, on="dep", how="left")  # Joindre les données d'accidents
    depc_all["n"] = depc_all["n"].fillna(0).astype(int)  # Remplir les valeurs manquantes par 0

    total_all = int(depc_all["n"].sum())  # Total des accidents
    nb_dep_all = 101  # Nombre total de départements

    # Trier les départements par nombre d'accidents et ajouter un rang
    depc96 = depc_all[depc_all["dep"].isin(codes96_list)].copy()
    if not depc96.empty:
        q = depc96["n"].quantile([0.0, 0.2, 0.4, 0.6, 0.8, 1.0]).values
    else:
        q = [0, 0, 0, 0, 0, 0]

    # Classifier les départements selon leur nombre d'accidents
    labels = ["Très faible", "Faible", "Moyen", "Élevé", "Très élevé"]
    depc_all["class_label"] = pd.cut(
        depc_all["n"], bins=q, labels=labels, include_lowest=True, duplicates="drop"
    )

    depc_all = depc_all.sort_values("n", ascending=False).reset_index(drop=True)  # Trier par nombre d'accidents
    depc_all["rang"] = depc_all["n"].rank(method="min", ascending=False).astype(int)  # Ajouter un rang par département

    # Sauvegarder les données dans l'app pour pouvoir les utiliser dans les callbacks
    app.server.depc_all = depc_all
    app.server.total_all = total_all
    app.server.nb_dep_all = nb_dep_all

    # Créer le dropdown pour sélectionner un département
    dropdown = dcc.Dropdown(
        id="dep-info-dropdown",
        options=_dropdown_options(geojson, codes96_list),
        placeholder="Choisir un département…",
        clearable=False,
        searchable=True,
        style={"width": "100%"},
        value="75",  # Valeur par défaut (Paris)
    )

    # Style des éléments KPI
    kpi_style = {
        "display": "flex",
        "flexDirection": "column",
        "alignItems": "center",
        "justifyContent": "center",
        "padding": "6px 8px",
        "minHeight": "64px",
        "borderRadius": "10px",
        "backgroundColor": "var(--bs-light)",
        "border": "1px solid #eee",
    }

    # Contenu de la carte avec le dropdown et les KPIs
    content = dbc.Card(
        [
            dbc.CardBody(
                [
                    dropdown,
                    html.Div(
                        dbc.Row(
                            [
                                # Quatre colonnes pour afficher les KPIs (intensité, nb d'accidents, part du total, classement)
                                dbc.Col(
                                    html.Div([html.Small("Intensité"), html.Div(id="kpi-intensite", className="fw-bold")], style=kpi_style),
                                    md=3,
                                ),
                                dbc.Col(
                                    html.Div([html.Small("Nombre d'accidents"), html.Div(id="kpi-nb", className="fw-bold")], style=kpi_style),
                                    md=3,
                                ),
                                dbc.Col(
                                    html.Div([html.Small("Part du total"), html.Div(id="kpi-part", className="fw-bold")], style=kpi_style),
                                    md=3,
                                ),
                                dbc.Col(
                                    html.Div([html.Small("Classement"), html.Div(id="kpi-rang", className="fw-bold")], style=kpi_style),
                                    md=3,
                                ),
                            ],
                            className="g-2 mt-3",
                        )
                    ),
                ]
            ),
        ],
        className="mb-3",
        style={
            "backgroundColor": "#ffffff",
            "border": "1px solid #e5e7eb",
            "borderRadius": "12px",
            "boxShadow": "0 2px 10px rgba(0,0,0,0.06)",
            "padding": "16px",
            "width": "100%",
            "maxWidth": "1040px",
            "boxSizing": "border-box",
        },
    )

    # Callback pour mettre à jour les KPIs en fonction du département sélectionné
    @app.callback(
        Output("kpi-intensite", "children"),
        Output("kpi-nb", "children"),
        Output("kpi-part", "children"),
        Output("kpi-rang", "children"),
        Input("dep-info-dropdown", "value"),
        prevent_initial_call=False,
    )
    def _update(dep_code: str):
        """
        Met à jour les KPIs en fonction du département sélectionné.
        """
        df_all = app.server.depc_all
        total_all = app.server.total_all
        nb_dep_all = app.server.nb_dep_all

        # Récupérer les données du département sélectionné
        row = df_all.loc[df_all["dep"] == dep_code]
        if row.empty:
            return "—", "—", "—", f"— / {nb_dep_all}"

        # Calculer les KPIs pour le département
        n = int(row["n"].values[0])
        part = (n / total_all * 100.0) if total_all > 0 else 0.0
        intensite = str(row["class_label"].values[0]) if "class_label" in row else "—"
        rang = int(row["rang"].values[0])

        # Afficher l'intensité avec une couleur spécifique
        color = BASE_COLOR_MAP.get(intensite, "#eceff1")
        badge = html.Span(intensite, style={"padding": "2px 6px", "borderRadius": "6px", "backgroundColor": color})

        return badge, f"{n:,}".replace(",", " "), f"{part:.1f}%", f"{rang} / {nb_dep_all}"

    return content
