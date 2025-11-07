from __future__ import annotations
import sqlite3
from pathlib import Path

import pandas as pd
import dash
from dash import html, dcc, Input, Output
import plotly.express as px

try:
    from config import DB_PATH
    DB_FILE = Path(DB_PATH)
except Exception:
    DB_FILE = Path("data/accidents.sqlite")

YEAR = 2024   # L'année des données utilisées pour l'analyse


# Fonction pour charger les données d'âge des usagers et leurs catégories
def load_age_base(year: int = YEAR) -> pd.DataFrame:
    """
    Lit directement SQLite :
      - usagers(num_acc, catu, grav, an_nais)
      - caracteristiques(an) pour filtrer sur l'année.
    Retourne un DataFrame avec les colonnes: age, catu, grav.
    """
    if not DB_FILE.exists():
        return pd.DataFrame(columns=["age", "catu", "grav"])

    # Requête SQL pour récupérer l'année de naissance, la catégorie (conducteur/passager), et la gravité
    sql = """
        SELECT u.an_nais, u.catu, u.grav
        FROM usagers u
        JOIN caracteristiques c ON c.num_acc = u.num_acc
        WHERE c.an = ?
    """
    with sqlite3.connect(DB_FILE) as conn:
        df = pd.read_sql_query(sql, conn, params=[year])

    # Calcul de l'âge en fonction de l'année de naissance
    an_nais = pd.to_numeric(df.get("an_nais"), errors="coerce")
    age = year - an_nais

    out = pd.DataFrame({
        "age": age,
        "catu": pd.to_numeric(df.get("catu"), errors="coerce"),
        "grav": pd.to_numeric(df.get("grav"), errors="coerce"),
    })

    # Filtrer les âges valides entre 0 et 100
    out = out[(out["age"] >= 0) & (out["age"] <= 100)]
    return out.reset_index(drop=True)


# Fonction pour créer un histogramme des âges des usagers
def make_age_histogram(df: pd.DataFrame, min_age: int = 0) -> pd.DataFrame:
    """
    Crée un histogramme des âges des usagers à partir des données filtrées
    en fonction de l'âge minimum spécifié.
    """
    ages = pd.to_numeric(df.get("age", pd.Series(dtype="float64")), errors="coerce")
    ages = ages[(ages >= min_age) & (ages <= 100)]  # Filtrer les âges valides

    # Définir les intervalles d'âges
    edges = list(range(0, 105, 5))
    labels = [f"{edges[i]}-{edges[i+1]}" for i in range(len(edges) - 1)]
    
    # Créer les tranches d'âge et compter le nombre d'accidents dans chaque tranche
    bins = pd.cut(ages, bins=edges, right=True, include_lowest=True, labels=labels)
    counts = bins.value_counts(sort=False).reindex(labels).fillna(0).astype(int).reset_index()
    counts.columns = ["Tranche d'âge", "Nombre d'accidents"]
    return counts


# Fonction pour construire le graphique de type histogramme
def build_hist_figure(df_hist: pd.DataFrame, y_label: str, hover_label: str):
    """
    Crée une figure de type histogramme avec les données d'accidents par tranche d'âge.
    """
    fig = px.bar(
        df_hist,
        x="Tranche d'âge",  # Tranches d'âge sur l'axe X
        y="Nombre d'accidents",  # Nombre d'accidents sur l'axe Y
        labels={"Tranche d'âge": "Âge", "Nombre d'accidents": y_label},
    )
    # Mise en place de l'hover pour afficher des informations détaillées
    fig.update_traces(hovertemplate=f"%{{x}} ans<br>{hover_label} : %{{y:,}}")
    
    # Mise à jour du layout du graphique
    fig.update_layout(plot_bgcolor="white", paper_bgcolor="white", bargap=0,
                      margin=dict(l=30, r=30, t=40, b=40))
    # Configuration des axes X et Y
    fig.update_xaxes(showgrid=False)
    fig.update_yaxes(showgrid=True, gridcolor="#e5e7eb", zeroline=True,
                     rangemode="tozero", tickformat=",d")
    return fig


# Fonction pour définir le layout de la page avec le graphique d'histogramme
def histogramme_layout(app: dash.Dash):
    """
    Définit le layout de la page avec un graphique représentant les accidents
    par tranche d'âge, ainsi qu'un dropdown pour sélectionner la population à analyser.
    """
    # Charger les données de base
    base = load_age_base(YEAR)
    init = base[base["catu"] == 1] if "catu" in base.columns else base
    df_hist = make_age_histogram(init, min_age=14)

    # Dropdown pour choisir entre le conducteur et les personnes décédées
    dropdown = html.Div(
        dcc.Dropdown(
            id="hist-population",
            options=[
                {"label": "Âge du conducteur", "value": "conducteurs"},
                {"label": "Personnes décédées", "value": "decedes"},
            ],
            value="conducteurs",
            clearable=False,
            searchable=False,
        ),
        style={"maxWidth": "420px", "margin": "0 auto 10px auto"},
    )

    # Création du graphique d'histogramme
    graph = dcc.Graph(
        id="hist-age-graph",
        figure=build_hist_figure(df_hist, "Nombre d'accidents", "accidents"),
        config={"displayModeBar": False},
        style={"height": "440px"},
    )

    # Retourner la mise en page complète avec le dropdown et le graphique
    return html.Div(
        [
            dropdown,
            html.Div(graph, style={"maxWidth": "1000px", "margin": "0 auto"}),
        ]
    )


# Callback pour mettre à jour l'histogramme en fonction de la population sélectionnée
@dash.callback(
    Output("hist-age-graph", "figure"),
    Input("hist-population", "value"),
)
def update_histogram(pop: str):
    """
    Met à jour le graphique de l'histogramme en fonction de la population sélectionnée (conducteurs ou décédés).
    """
    df = load_age_base(YEAR)
    pop = (pop or "").lower()

    # Filtrer les données en fonction de la population choisie (conducteurs ou décédés)
    if pop == "conducteurs":
        df = df[df["catu"] == 1]
        y_label, hover = "Nombre d'accidents", "accidents"
    elif pop == "decedes":
        df = df[df["grav"] == 2]
        y_label, hover = "Nombre de décès", "victimes"
    else:
        y_label, hover = "Nombre d'accidents", "accidents"

    # Créer l'histogramme et le mettre à jour
    df_hist = make_age_histogram(df, min_age=14)
    return build_hist_figure(df_hist, y_label, hover)
