from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Tuple

import dash
from dash import html, dcc
import pandas as pd
import plotly.graph_objects as go

from config import DB_PATH


def _fetch_mois_lum(db_path: Path, year: int = 2024) -> pd.DataFrame:
    """Lecture brute de 'mois, lum'."""
    sql = "SELECT mois, lum FROM caracteristiques WHERE an = ?"
    with sqlite3.connect(str(db_path)) as conn:
        df = pd.read_sql_query(sql, conn, params=(year,))
    return df


def _split_counts_jour_nuit(df: pd.DataFrame) -> Tuple[pd.Series, pd.Series]:
    """Compte mensuel jour/nuit (sans typage poussé)."""
    mois = pd.to_numeric(df["mois"], errors="coerce")
    lum = pd.to_numeric(df["lum"], errors="coerce")
    ok = mois.between(1, 12) & lum.between(1, 5)
    df = df[ok].copy()

    jour = df[lum.isin([1, 2])]
    nuit = df[lum.isin([3, 4, 5])]

    idx = range(1, 13)
    s_jour = pd.to_numeric(jour["mois"]).value_counts().reindex(idx, fill_value=0).sort_index()
    s_nuit = pd.to_numeric(nuit["mois"]).value_counts().reindex(idx, fill_value=0).sort_index()
    return s_jour, s_nuit


def _build_lines(s_jour: pd.Series, s_nuit: pd.Series) -> go.Figure:
    """Deux courbes simples (stylage par défaut Plotly)."""
    x = list(range(1, 13))
    fig = go.Figure()
    fig.add_scatter(x=x, y=s_jour.values, mode="lines+markers", name="Jour")
    fig.add_scatter(x=x, y=s_nuit.values, mode="lines+markers", name="Nuit")
    fig.update_xaxes(title="Mois")
    fig.update_yaxes(title="Nombre d'accidents", rangemode="tozero")
    return fig


def graphiquecourbe_layout(app: dash.Dash) -> html.Div:
    df = _fetch_mois_lum(Path(DB_PATH), year=2024)
    s_jour, s_nuit = _split_counts_jour_nuit(df)
    fig = _build_lines(s_jour, s_nuit)
    return html.Div(dcc.Graph(id="line-jour-nuit", figure=fig, config={"displayModeBar": False}),
                    style={"marginTop": "18px"})
