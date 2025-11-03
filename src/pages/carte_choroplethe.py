from __future__ import annotations
import dash
from dash import html, dcc
import dash_bootstrap_components as dbc
import pandas as pd
from pathlib import Path
from config import DB_PATH, DEPT_GEOJSON
from ..utils.data_utils import load_accidents, load_geojson_departments
from ..components.map_choropleth import (
    build_map_figure, prepare_dep_classes, BASE_COLOR_MAP, CLASS_CODE_ORDER
)

# ---------- Helpers ----------
def _fmt(n):
    try:
        return f"{int(round(n)):,}".replace(",", " ")
    except Exception:
        return str(n)

def _legend_row(color, label):
    return html.Div(
        [
            html.Span(style={
                "display": "inline-block", "width": "14px", "height": "14px",
                "backgroundColor": color, "borderRadius": "3px", "marginRight": "8px",
                "border": "1px solid rgba(0,0,0,0.15)"
            }),
            html.Span(label),
        ],
        style={"display": "flex", "alignItems": "center", "marginBottom": "6px", "fontSize": "14px"},
    )

# ---------- Layout principal ----------
def layout(app: dash.Dash):
    # --- Données ---
    df = load_accidents(Path(DB_PATH), year=2024)
    geojson = load_geojson_departments(Path(DEPT_GEOJSON))
    depc, (b1, b2, b3, b4) = prepare_dep_classes(df)

    depc["accidents"] = pd.to_numeric(depc["accidents"], errors="coerce").fillna(0).astype(int)
    depc["dep"] = depc["dep"].astype(str)

    # --- Carte ---
    fig_map = build_map_figure(depc, geojson, selected_codes=CLASS_CODE_ORDER)
    map_graph = dcc.Graph(
        id="map-accidents",
        figure=fig_map,
        style={"height": "80vh", "width": "100%"},
        config={"displayModeBar": False},
    )

    # --- Légende (sans “Exceptionnel”) ---
    legend_rows = [
        _legend_row(BASE_COLOR_MAP["Très faible"], f"Très faible (≤ {_fmt(b1)})"),
        _legend_row(BASE_COLOR_MAP["Faible"], f"Faible ({_fmt(b1)} – {_fmt(b2)})"),
        _legend_row(BASE_COLOR_MAP["Moyen"], f"Moyen ({_fmt(b2)} – {_fmt(b3)})"),
        _legend_row(BASE_COLOR_MAP["Élevé"], f"Élevé ({_fmt(b3)} – {_fmt(b4)})"),
        _legend_row(BASE_COLOR_MAP["Très élevé"], f"Très élevé (> {_fmt(b4)})"),
    ]

    legend_card = dbc.Card(
        dbc.CardBody(
            [html.H6("Échelle d’intensité — accidents 2024",
                     className="mb-3", style={"textAlign": "center", "fontWeight": "600"})] + legend_rows
        ),
        style={
            "borderRadius": "12px",
            "padding": "12px",
            "boxShadow": "0 2px 6px rgba(0,0,0,0.1)",
            "width": "230px",
            "backgroundColor": "white",
        },
    )

    # --- Titre au-dessus de la carte ---
    map_title = html.H4(
        "Répartition des accidents de la route en France (2024)",
        style={
            "textAlign": "center",
            "color": "#2c3e50",
            "fontWeight": "600",
            "marginBottom": "18px",
            "fontSize": "22px",
        },
    )

    # --- Bloc carte + titre ---
    map_with_title = html.Div(
        [map_title, map_graph],
        style={
            "display": "flex",
            "flexDirection": "column",
            "alignItems": "center",
            "justifyContent": "flex-start",
            "width": "100%",
        },
    )

    # --- Colonne 1 : LÉGENDE (collée à gauche) ---
    legend_col = html.Div(
        legend_card,
        style={
            "flex": "0 0 240px",
            "padding": "0 12px 0 16px",
            "display": "flex",
            "alignItems": "center",
            "height": "82vh",
        },
    )

    # --- Colonne 2 : CARTE + TITRE ---
    map_col = html.Div(
        map_with_title,
        style={
            "flex": "0 0 700px",
            "padding": "0",
            "display": "block",
        },
    )

    # --- Colonne droite vide (pour les graphes futurs) ---
    right_col = html.Div(
        [],
        style={
            "flex": "1 1 auto",
            "backgroundColor": "#f9f9f9",
            "minHeight": "82vh",
            "borderLeft": "2px solid #e0e0e0",
        },
    )

    # --- Ligne principale ---
    row = html.Div(
        [legend_col, map_col, right_col],
        style={
            "display": "flex",
            "gap": "0",
            "justifyContent": "flex-start",
            "alignItems": "flex-start",
            "width": "100%",
            "marginTop": "280px",  # ⬇️⬇️ descente forte du bloc complet
        },
    )

    # --- Page complète ---
    page = html.Div(
        [row],
        style={
            "backgroundColor": "#fafafa",
            "minHeight": "100vh",
            "margin": "0",
            "padding": "0",
        },
    )

    return page
