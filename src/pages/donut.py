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

def _read_counts(db: Path) -> pd.DataFrame:
    sql = """
        SELECT u.grav AS grav, COUNT(*) AS n
        FROM usagers u
        JOIN caracteristiques c ON c.num_acc = u.num_acc
        WHERE c.an = ?
        GROUP BY u.grav
    """
    with sqlite3.connect(db) as conn:
        df = pd.read_sql_query(sql, conn, params=[YEAR])
    if df.empty:
        return pd.DataFrame({"label": [], "n": []})
    df["label"] = pd.to_numeric(df["grav"], errors="coerce").map(GRAV_MAPPING)
    df = df.groupby("label", as_index=False)["n"].sum()
    df["label"] = pd.Categorical(df["label"], categories=ORDER, ordered=True)
    return df.sort_values("label")

def _figure(df: pd.DataFrame) -> go.Figure:
    if df.empty:
        return go.Figure(go.Pie(labels=["Aucune donnée"], values=[1], hole=0.6))
    total = int(df["n"].sum())
    pie = go.Pie(
        labels=df["label"], values=df["n"],
        hole=0.55, sort=False, textinfo="label+percent"
    )
    fig = go.Figure(pie)
    fig.add_annotation(x=0.5, y=0.5, text=f"<b>{total:,}</b>", showarrow=False)
    fig.update_layout(margin=dict(l=30, r=30, t=20, b=30))
    return fig

def donut_layout(app: dash.Dash) -> html.Div:
    df = _read_counts(Path(DB_PATH))
    return html.Div(
        dcc.Graph(id="donut-graph", figure=_figure(df), config={"displayModeBar": False}),
        style={"backgroundColor": "white", "border": "1px solid #e5e7eb", "borderRadius": "12px", "padding": "10px"}
    )
