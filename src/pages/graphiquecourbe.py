from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Tuple

import dash
from dash import html, dcc
import pandas as pd
import plotly.graph_objects as go

from config import DB_PATH

MONTHS_FR = ["janv.", "févr.", "mars", "avr.", "mai", "juin",
             "juil.", "août", "sept.", "oct.", "nov.", "déc."]


def _fetch_mois_lum(db_path: Path, year: int = 2024) -> pd.DataFrame:
    sql = "SELECT mois, lum FROM caracteristiques WHERE an = ?"
    with sqlite3.connect(str(db_path)) as conn:
        df = pd.read_sql_query(sql, conn, params=(year,))
    df["mois"] = pd.to_numeric(df["mois"], errors="coerce")
    df["lum"] = pd.to_numeric(df["lum"], errors="coerce")
    df = df[df["mois"].between(1, 12) & df["lum"].between(1, 5)]
    df["mois"] = df["mois"].astype(int)
    df["lum"] = df["lum"].astype(int)
    return df


def _series_jour_nuit(df: pd.DataFrame) -> Tuple[pd.Series, pd.Series]:
    idx = pd.Index(range(1, 13), name="mois")
    jour = df[df["lum"].isin([1, 2])]
    nuit = df[df["lum"].isin([3, 4, 5])]
    s_jour = jour["mois"].value_counts().reindex(idx, fill_value=0).sort_index()
    s_nuit = nuit["mois"].value_counts().reindex(idx, fill_value=0).sort_index()
    return s_jour, s_nuit


def _build_lines(s_jour: pd.Series, s_nuit: pd.Series) -> go.Figure:
    x = list(range(1, 13))
    fig = go.Figure()
    fig.add_scatter(x=x, y=s_jour.values, mode="lines+markers", name="Jour",
                    line=dict(width=2, color="#f97316"), marker=dict(size=6))
    fig.add_scatter(x=x, y=s_nuit.values, mode="lines+markers", name="Nuit",
                    line=dict(width=2, color="#2563eb"), marker=dict(size=6))

    fig.add_vline(x=6, line_dash="dot", line_width=1, line_color="#9ca3af")  # repère visuel

    fig.update_layout(
        margin=dict(l=30, r=20, t=10, b=40),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        paper_bgcolor="white",
        plot_bgcolor="white",
        hovermode="x unified",
        transition={"duration": 0},
    )
    fig.update_xaxes(tickmode="array", tickvals=x, ticktext=MONTHS_FR, title="Mois",
                     showline=True, linecolor="#000", linewidth=1)
    fig.update_yaxes(title="Nombre d'accidents", rangemode="tozero",
                     showline=True, linecolor="#000", linewidth=1, tickformat=",d")
    return fig


def graphiquecourbe_layout(app: dash.Dash) -> html.Div:
    df = _fetch_mois_lum(Path(DB_PATH), year=2024)
    s_jour, s_nuit = _series_jour_nuit(df)
    fig = _build_lines(s_jour, s_nuit)

    card = html.Div(
        [
            html.H5(
                "Comparaison Jour/Nuit (mensuelle)",
                style={"textAlign": "center", "color": "#2c3e50",
                       "fontWeight": 600, "marginBottom": "10px", "marginTop": "6px"},
            ),
            dcc.Graph(
                id="line-jour-nuit",
                figure=fig,
                config={"displayModeBar": False, "scrollZoom": False, "doubleClick": False, "displaylogo": False},
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

    return html.Div([card], style={
        "display": "flex", "justifyContent": "flex-start", "alignItems": "flex-start",
        "marginTop": "18px", "marginBottom": "24px", "width": "100%",
    })
