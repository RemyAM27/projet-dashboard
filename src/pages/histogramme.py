# src/pages/histogramme.py — final (niveau ESIEE)
from __future__ import annotations
import sqlite3
from pathlib import Path
from typing import List, Optional


import pandas as pd
import dash
from dash import html, dcc, Input, Output
import plotly.express as px


try:
    from config import DB_PATH
    DB_FILE = Path(DB_PATH)
except Exception:
    DB_FILE = Path("data/accidents.sqlite")

YEAR = 2024  # année d'étude

# --------------------- Lecture base ---------------------
def load_age_base(year: int = YEAR) -> pd.DataFrame:
    """
    Lit directement SQLite :
      - usagers(num_acc, catu, grav, an_nais)
      - caracteristiques(an) pour filtrer sur l'année.
    Retourne un DF avec colonnes: age, catu, grav.
    """
    if not DB_FILE.exists():
        return pd.DataFrame(columns=["age", "catu", "grav"])

    sql = """
        SELECT u.an_nais, u.catu, u.grav
        FROM usagers u
        JOIN caracteristiques c ON c.num_acc = u.num_acc
        WHERE c.an = ?
    """
    with sqlite3.connect(DB_FILE) as conn:
        df = pd.read_sql_query(sql, conn, params=[year])

    # calcul d'âge simple
    an_nais = pd.to_numeric(df.get("an_nais"), errors="coerce")
    age = year - an_nais

    out = pd.DataFrame({
        "age": age,
        "catu": pd.to_numeric(df.get("catu"), errors="coerce"),
        "grav": pd.to_numeric(df.get("grav"), errors="coerce"),
    })
    # bornes plausibles d'âge
    out = out[(out["age"] >= 0) & (out["age"] <= 100)]
    return out.reset_index(drop=True)

# --------------------- Préparation histogramme ---------------------
def make_age_histogram(df: pd.DataFrame, min_age: int = 0) -> pd.DataFrame:
    ages = pd.to_numeric(df.get("age", pd.Series(dtype="float64")), errors="coerce")
    ages = ages[(ages >= min_age) & (ages <= 100)]
    edges = list(range(0, 105, 5))
    labels = [f"{edges[i]}-{edges[i+1]}" for i in range(len(edges) - 1)]
    bins = pd.cut(ages, bins=edges, right=True, include_lowest=True, labels=labels)
    counts = bins.value_counts(sort=False).reindex(labels).fillna(0).astype(int).reset_index()
    counts.columns = ["Tranche d'âge", "Nombre d'accidents"]
    return counts

def build_hist_figure(df_hist: pd.DataFrame, y_label: str, hover_label: str):
    fig = px.bar(
        df_hist,
        x="Tranche d'âge",
        y="Nombre d'accidents",
        labels={"Tranche d'âge": "Âge", "Nombre d'accidents": y_label},
    )
    fig.update_traces(hovertemplate=f"%{{x}} ans<br>{hover_label} : %{{y:,}}")
    fig.update_layout(plot_bgcolor="white", paper_bgcolor="white", bargap=0,
                      margin=dict(l=30, r=30, t=40, b=40))
    fig.update_xaxes(showgrid=False)
    fig.update_yaxes(showgrid=True, gridcolor="#e5e7eb", zeroline=True,
                     rangemode="tozero", tickformat=",d")
    return fig

# --------------------- Layout + Callback ---------------------
def histogramme_layout(app: dash.Dash):
    base = load_age_base(YEAR)
    init = base[base["catu"] == 1] if "catu" in base.columns else base
    df_hist = make_age_histogram(init, min_age=14)

    dropdown = html.Div(
        dcc.Dropdown(
            id="hist-population",
            options=[
                {"label": "Conducteurs uniquement", "value": "conducteurs"},
                {"label": "Occupants de véhicules (conducteurs et passagers)", "value": "occupants"},
                {"label": "Personnes décédées", "value": "decedes"},
            ],
            value="conducteurs",
            clearable=False,
            searchable=False,
        ),
        style={"maxWidth": "420px", "margin": "0 auto 10px auto"},
    )

    graph = dcc.Graph(
        id="hist-age-graph",
        figure=build_hist_figure(df_hist, "Nombre d'accidents", "accidents"),
        config={"displayModeBar": False},
        style={"height": "440px"},
    )


    return html.Div(
        [
            html.H4(
                "Histogramme des accidents par âge",
                style={"textAlign": "center", "color": "#2c3e50", "fontWeight": 600, "marginBottom": "10px"},
            ),
            dropdown,
            html.Div(graph, style={"maxWidth": "1000px", "margin": "0 auto"}),
        ]
    )

@dash.callback(
    Output("hist-age-graph", "figure"),
    Input("hist-population", "value"),
)
def update_histogram(pop: str):
    df = load_age_base(YEAR)
    pop = (pop or "").lower()

    if pop == "conducteurs":
        df = df[df["catu"] == 1]
        y_label, hover = "Nombre d'accidents", "accidents"
    elif pop == "occupants":
        df = df[df["catu"].isin([1, 2])]
        y_label, hover = "Nombre d'accidents", "accidents"
    elif pop == "decedes":
        df = df[df["grav"] == 2]
        y_label, hover = "Nombre de décès", "victimes"
    else:
        y_label, hover = "Nombre d'accidents", "accidents"

    df_hist = make_age_histogram(df, min_age=14)
    return build_hist_figure(df_hist, y_label, hover)
