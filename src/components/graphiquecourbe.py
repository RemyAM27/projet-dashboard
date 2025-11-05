from __future__ import annotations

import sqlite3
from pathlib import Path

import dash
from dash import html, dcc
import pandas as pd
import plotly.graph_objects as go

from config import DB_PATH

MONTHS_FR = ["janv.", "févr.", "mars", "avr.", "mai", "juin",
             "juil.", "août", "sept.", "oct.", "nov.", "déc."]


def _fetch_mois(db_path: Path, year: int = 2024) -> pd.Series:
    """
    Lit la colonne 'mois' pour l'année demandée et retourne
    une série d'effectifs indexée 1..12.
    """
    sql = "SELECT mois FROM caracteristiques WHERE an = ?"
    with sqlite3.connect(str(db_path)) as conn:
        df = pd.read_sql_query(sql, conn, params=(year,))

    df["mois"] = pd.to_numeric(df["mois"], errors="coerce")
    df = df[df["mois"].between(1, 12)]
    idx = pd.Index(range(1, 13), name="mois")
    s_total = df["mois"].value_counts().reindex(idx, fill_value=0).sort_index()
    return s_total


def _build_line_total(s_total: pd.Series) -> go.Figure:
    x = list(range(1, 13))
    grid_color = "#e5e7eb"

    fig = go.Figure()
    fig.add_scatter(
        x=x, y=s_total.values,
        mode="lines+markers",
        name="Accidents",
        line=dict(width=2, color="#f97316"),   
        marker=dict(size=6)
    )

    fig.add_vline(x=6, line_dash="dot", line_width=1, line_color="#9ca3af")

    fig.update_layout(
        margin=dict(l=30, r=20, t=10, b=40),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        paper_bgcolor="white",
        plot_bgcolor="white",
        hovermode="x unified",
        transition={"duration": 0},
    )
    fig.update_xaxes(
        title="Mois",
        tickmode="array", tickvals=x, ticktext=MONTHS_FR,
        showline=True, linecolor="#000", linewidth=1,
        showgrid=True, gridcolor=grid_color, gridwidth=1
    )
    fig.update_yaxes(
        title="Nombre d'accidents",
        tickformat=",d",
        showline=True, linecolor="#000", linewidth=1,
        rangemode="tozero",
        showgrid=True, gridcolor=grid_color, gridwidth=1, zeroline=False
    )
    return fig


def _build_empty_figure() -> go.Figure:
    fig = go.Figure()
    fig.add_annotation(
        text="Données indisponibles (colonne 'mois')",
        x=0.5, y=0.5, xref="paper", yref="paper", showarrow=False
    )
    fig.update_layout(paper_bgcolor="white", plot_bgcolor="white",
                      margin=dict(l=30, r=20, t=10, b=40))
    return fig


def graphiquecourbe_layout(app: dash.Dash) -> html.Div:
    try:
        s_total = _fetch_mois(Path(DB_PATH), year=2024)
        fig = _build_line_total(s_total)
    except Exception:
        fig = _build_empty_figure()

    card = html.Div(
        [
            dcc.Graph(
                id="line-accidents-mensuels",
                figure=fig,
                config={
                    "displayModeBar": False,
                    "scrollZoom": False,
                    "doubleClick": False,
                    "displaylogo": False
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
