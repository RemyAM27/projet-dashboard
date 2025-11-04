from __future__ import annotations

import sqlite3
from pathlib import Path

import dash
from dash import html, dcc
import pandas as pd
import plotly.graph_objects as go

from config import DB_PATH


def _fetch_mois(db_path: Path, year: int = 2024) -> pd.DataFrame:
    """Lecture minimale : uniquement la colonne 'mois' pour une année."""
    sql = "SELECT mois FROM caracteristiques WHERE an = ?"
    with sqlite3.connect(str(db_path)) as conn:
        df = pd.read_sql_query(sql, conn, params=(year,))
    return df


def _count_total_by_month(df: pd.DataFrame) -> pd.Series:
    """Compte très simple : total par mois, sans autre filtrage."""
    s = pd.to_numeric(df["mois"], errors="coerce").value_counts()
    s = s.reindex(range(1, 13), fill_value=0).sort_index()
    return s


def _build_total_line(s_total: pd.Series) -> go.Figure:
    """Figure minimale : une seule courbe 'Total' (aucun stylage)."""
    x = list(range(1, 13))
    fig = go.Figure()
    fig.add_scatter(x=x, y=s_total.values, mode="lines+markers", name="Total")
    fig.update_xaxes(title="Mois")
    fig.update_yaxes(title="Nombre d'accidents", rangemode="tozero")
    return fig


def graphiquecourbe_layout(app: dash.Dash) -> html.Div:
    df = _fetch_mois(Path(DB_PATH), year=2024)
    s_total = _count_total_by_month(df)
    fig = _build_total_line(s_total)

    return html.Div(
        dcc.Graph(id="line-jour-nuit", figure=fig, config={"displayModeBar": False}),
        style={"marginTop": "18px"},
    )
