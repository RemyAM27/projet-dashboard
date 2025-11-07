from __future__ import annotations

import sqlite3
from pathlib import Path

import dash
from dash import html, dcc
import pandas as pd
import plotly.graph_objects as go

from config import DB_PATH

# Liste des mois en français pour l'axe X des graphiques
MONTHS_FR = ["janv.", "févr.", "mars", "avr.", "mai", "juin",
             "juil.", "août", "sept.", "oct.", "nov.", "déc."]

# Fonction pour récupérer le nombre d'accidents par mois pour une année donnée
def _fetch_mois(db_path: Path, year: int = 2024) -> pd.Series:
    """
    Lit la colonne 'mois' pour l'année demandée et retourne
    une série d'effectifs indexée 1..12, représentant les mois de l'année.
    """
    sql = "SELECT mois FROM caracteristiques WHERE an = ?"
    with sqlite3.connect(str(db_path)) as conn:
        df = pd.read_sql_query(sql, conn, params=(year,))

    # Convertir la colonne 'mois' en numérique et gérer les erreurs de conversion
    df["mois"] = pd.to_numeric(df["mois"], errors="coerce")
    # Filtrer les mois entre 1 et 12 inclus
    df = df[df["mois"].between(1, 12)]
    # Créer un index de 1 à 12 pour les mois
    idx = pd.Index(range(1, 13), name="mois")
    # Compter les occurrences de chaque mois, combler les mois manquants avec 0
    s_total = df["mois"].value_counts().reindex(idx, fill_value=0).sort_index()
    return s_total


# Fonction pour créer un graphique en ligne avec les données d'accidents par mois
def _build_line_total(s_total: pd.Series) -> go.Figure:
    x = list(range(1, 13))  # Mois de 1 à 12 pour l'axe X
    grid_color = "#e5e7eb"  # Couleur de la grille

    fig = go.Figure()
    # Ajouter la courbe des accidents sur le graphique
    fig.add_scatter(
        x=x, y=s_total.values,
        mode="lines+markers",  # Mode ligne avec marqueurs
        name="Accidents",  # Nom de la courbe
        line=dict(width=2, color="#f97316"),  # Style de la ligne
        marker=dict(size=6)  # Style des marqueurs
    )

    # Ajouter une ligne verticale pour marquer le mois de juin (mois 6)
    fig.add_vline(x=6, line_dash="dot", line_width=1, line_color="#9ca3af")

    # Mise à jour du layout du graphique
    fig.update_layout(
        margin=dict(l=30, r=20, t=10, b=40),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        paper_bgcolor="white",
        plot_bgcolor="white",
        hovermode="x unified",
        transition={"duration": 0},
    )
    # Mise à jour de l'axe X
    fig.update_xaxes(
        title="Mois",
        tickmode="array", tickvals=x, ticktext=MONTHS_FR,  # Mois en français
        showline=True, linecolor="#000", linewidth=1,
        showgrid=True, gridcolor=grid_color, gridwidth=1
    )
    # Mise à jour de l'axe Y
    fig.update_yaxes(
        title="Nombre d'accidents",
        tickformat=",d",  # Format des nombres avec des virgules
        showline=True, linecolor="#000", linewidth=1,
        rangemode="tozero",  # L'axe commence à zéro
        showgrid=True, gridcolor=grid_color, gridwidth=1, zeroline=False
    )
    return fig


# Fonction pour créer un graphique vide lorsque les données sont indisponibles
def _build_empty_figure() -> go.Figure:
    fig = go.Figure()
    # Ajouter un texte d'annotation pour signaler l'absence de données
    fig.add_annotation(
        text="Données indisponibles (colonne 'mois')",
        x=0.5, y=0.5, xref="paper", yref="paper", showarrow=False
    )
    fig.update_layout(paper_bgcolor="white", plot_bgcolor="white",
                      margin=dict(l=30, r=20, t=10, b=40))
    return fig


# Fonction pour définir le layout de la page avec le graphique de ligne des accidents mensuels
def graphiquecourbe_layout(app: dash.Dash) -> html.Div:
    try:
        # Récupérer les données d'accidents mensuels
        s_total = _fetch_mois(Path(DB_PATH), year=2024)
        fig = _build_line_total(s_total)  # Créer le graphique
    except Exception:
        # Si une erreur survient, afficher un graphique vide
        fig = _build_empty_figure()

    # Conteneur pour le graphique et le dropdown
    card = html.Div(
        [
            dcc.Graph(
                id="line-accidents-mensuels",
                figure=fig,
                config={
                    "displayModeBar": False,  # Masquer la barre d'outils
                    "scrollZoom": False,
                    "doubleClick": False,
                    "displaylogo": False  # Masquer le logo de Plotly
                },
                style={"height": "440px", "width": "100%"},
            ),
        ],
        style={
            "backgroundColor": "#ffffff",
            "border": "1px solid #e5e7eb",
            "borderRadius": "12px",
            "boxShadow": "0 2px 10px rgba(0,0,0,0.06)",
            "padding": "16px",
            "width": "100%",
            "maxWidth": "1040px",
            "marginLeft": "0.5%",
            "boxSizing": "border-box",
            "overflow": "hidden",
        },
    )

    # Retourner la mise en page complète avec le graphique
    return html.Div(
        [card],
        style={
            "display": "flex",
            "justifyContent": "flex-start",
            "alignItems": "flex-start",
            "marginTop": "18px",
            "marginBottom": "24px",
            "width": "100%",
        },
    )
