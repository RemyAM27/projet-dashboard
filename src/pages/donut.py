from __future__ import annotations
import sqlite3
from pathlib import Path

import dash
from dash import html, dcc
import plotly.graph_objects as go
import pandas as pd

from config import DB_PATH

YEAR = 2024
GRAV_MAPPING = {1: "Indemne", 4: "Léger", 3: "Hospitalisé", 2: "Tué"}
ORDER = ["Indemne", "Léger", "Hospitalisé", "Tué"]
COLORS = {"Indemne": "#94A3B8", "Léger": "#34D399", "Hospitalisé": "#F59E0B", "Tué": "#EF4444"}

def _read_counts(db: Path) -> pd.DataFrame:
    sql = """
        SELECT u.grav AS grav, COUNT(*) AS n
        FROM usagers u
        JOIN caracteristiques c ON c.num_acc = u.num_acc
        WHERE c.an = ?
        GROUP BY u.grav
        ORDER BY u.grav
    """
    with sqlite3.connect(db) as conn:
        df = pd.read_sql_query(sql, conn, params=[YEAR])
    if df.empty:
        return pd.DataFrame({"label": [], "n": []})
    df["label"] = pd.to_numeric(df["grav"], errors="coerce").map(GRAV_MAPPING)
    df = df.groupby("label", as_index=False)["n"].sum()
    df["label"] = pd.Categorical(df["label"], categories=ORDER, ordered=True)
    return df.sort_values("label").reset_index(drop=True)

def _figure(df: pd.DataFrame) -> go.Figure:
    if df.empty:
        fig = go.Figure(go.Pie(labels=["Aucune donnée"], values=[1], hole=0.6, textinfo="none"))
        fig.update_layout(margin=dict(l=30, r=30, t=20, b=30))
        return fig
    total = int(df["n"].sum())
    colors = [COLORS.get(l, "#CBD5E1") for l in df["label"]]
    pie = go.Pie(
        labels=df["label"], values=df["n"], hole=0.55, sort=False,
        marker=dict(colors=colors, line=dict(width=1, color="rgba(255,255,255,0.95)")),
        textinfo="label+percent",
        hovertemplate="<b>%{label}</b><br>%{value:,} cas • %{percent:.1%}<extra></extra>",
        showlegend=False,
    )
    fig = go.Figure(pie)
    fig.add_annotation(x=0.5, y=0.5, text=f"<b>{total:,}</b><br><span style='font-size:12px;color:#6b7280'>victimes</span>",
                       showarrow=False, align="center")
    fig.update_layout(margin=dict(l=40, r=40, t=20, b=40), paper_bgcolor="#fff", plot_bgcolor="#fff")
    return fig

def donut_layout(app: dash.Dash) -> html.Div:
    df = _read_counts(Path(DB_PATH))
    return html.Div(
        dcc.Graph(id="donut-graph", figure=_figure(df), config={"displayModeBar": False}, style={"height": "420px"}),
        style={"backgroundColor": "white", "border": "1px solid #e5e7eb", "borderRadius": "12px", "padding": "10px"}
    )
