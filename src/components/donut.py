from __future__ import annotations
import sqlite3
from pathlib import Path

import dash
from dash import html, dcc, Input, Output
import plotly.graph_objects as go
import pandas as pd

from config import DB_PATH

YEAR = 2024
MAJORITY = 18
GRAV_MAPPING = {1: "Indemne", 4: "Léger", 3: "Hospitalisé", 2: "Tué"}
ORDER = ["Indemne", "Léger", "Hospitalisé", "Tué"]
COLORS = {"Indemne": "#94A3B8", "Léger": "#34D399", "Hospitalisé": "#F59E0B", "Tué": "#EF4444"}

def _normalize_to_100(values):
    r = [round(v, 1) for v in values]
    diff = round(100.0 - sum(r), 1)
    if abs(diff) >= 0.1:
        res = [v - round(v, 1) for v in values]
        idx = res.index(max(res)) if diff > 0 else res.index(min(res))
        r[idx] = round(r[idx] + diff, 1)
    return r

def _read_counts(db: Path, profile: str) -> pd.DataFrame:
    cond = ["c.an = ?"]; params = [YEAR]
    p = (profile or "").lower()
    if p == "conducteur":  cond.append("u.catu = 1")
    if p == "passagers":   cond.append("u.catu = 2")
    if p == "majeur":      cond += ["u.an_nais IS NOT NULL", "u.an_nais <= ?"]; params.append(YEAR - MAJORITY)
    if p == "mineur":      cond += ["u.an_nais IS NOT NULL", "u.an_nais > ?"];  params.append(YEAR - MAJORITY)

    sql = f"""
        SELECT u.grav AS grav, COUNT(*) AS n
        FROM usagers u
        JOIN caracteristiques c ON c.num_acc = u.num_acc
        WHERE {' AND '.join(cond)}
        GROUP BY u.grav
        ORDER BY u.grav
    """
    with sqlite3.connect(db) as conn:
        df = pd.read_sql_query(sql, conn, params=params)
    if df.empty: return pd.DataFrame({"label": [], "n": []})
    df["label"] = pd.to_numeric(df["grav"], errors="coerce").map(GRAV_MAPPING)
    df = df.groupby("label", as_index=False)["n"].sum()
    df["label"] = pd.Categorical(df["label"], categories=ORDER, ordered=True)
    return df.sort_values("label").reset_index(drop=True)

def _figure(df: pd.DataFrame) -> go.Figure:
    if df.empty:
        fig = go.Figure(go.Pie(labels=["Aucune donnée"], values=[1], hole=0.6, textinfo="none"))
        fig.update_layout(margin=dict(l=40, r=40, t=20, b=40))
        return fig
    total = int(df["n"].sum())
    pct = _normalize_to_100((df["n"] / total * 100.0).tolist())
    colors = [COLORS[l] for l in df["label"]]
    pie = go.Pie(
        labels=df["label"], values=pct, customdata=df["n"].astype(int),
        hole=0.55, sort=False, marker=dict(colors=colors),
        textinfo="label+value", texttemplate="%{label}<br>%{value:.1f}%",
        hovertemplate="<b>%{label}</b><br>%{customdata:,} cas • %{value:.1f}%<extra></extra>",
        showlegend=False,
    )
    fig = go.Figure(pie)
    fig.add_annotation(x=0.5, y=0.5,
                       text=f"<b>{total:,}</b><br><span style='font-size:12px;color:#6b7280'>victimes</span>",
                       showarrow=False, align="center")
    fig.update_layout(margin=dict(l=40, r=40, t=20, b=40), paper_bgcolor="#fff", plot_bgcolor="#fff")
    return fig

def donut_layout(app: dash.Dash) -> html.Div:
    dropdown = html.Div(
        dcc.Dropdown(
            id="donut-prof",
            options=[
                {"label": "Conducteur", "value": "conducteur"},
                {"label": "Passagers",  "value": "passagers"},
                {"label": "Majeur",     "value": "majeur"},
                {"label": "Mineur",     "value": "mineur"},
            ],
            value="conducteur", clearable=False, searchable=False
        ),
        style={"maxWidth": "520px", "margin": "6px auto 12px auto"},
    )
    graph = dcc.Graph(id="donut-graph",
                      figure=_figure(_read_counts(Path(DB_PATH), "conducteur")),
                      config={"displayModeBar": False}, style={"height": "420px"})
    card = html.Div([dropdown, html.Div(graph, style={"maxWidth": "1100px", "margin": "0 auto"})],
                    style={"background": "white", "border": "1px solid #e5e7eb", "borderRadius": "12px", "padding": "10px"})
    @app.callback(Output("donut-graph", "figure"), Input("donut-prof", "value"))
    def _update(v): return _figure(_read_counts(Path(DB_PATH), v))
    return card
