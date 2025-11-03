# src/pages/histogramme.py — v2 (corrigée, niveau ESIEE)
import sqlite3
from pathlib import Path

import pandas as pd
import dash
from dash import html, dcc, Input, Output
import plotly.express as px

try:
    from config import DB_PATH
    DB_FILE = Path(DB_PATH)
except Exception:
    DB_FILE = Path("data/accidents.sqlite")


def _split_single_column(df_raw: pd.DataFrame) -> pd.DataFrame:
    """Gère le cas où la table 'usagers' a été importée comme une seule colonne CSV."""
    col = df_raw.columns[0]
    df = df_raw[col].astype(str).str.split(",", expand=True)
    df = df.apply(lambda s: s.str.strip().str.strip('"').str.strip("'"))
    first = df.iloc[0].str.lower().tolist()
    if any(("an_nais" in v) or ("catu" in v) or ("grav" in v) for v in first):
        df.columns = [v.strip() for v in df.iloc[0]]
        df = df.iloc[1:].reset_index(drop=True)
    else:
        df.columns = [f"c{i}" for i in range(df.shape[1])]
    return df


def _load_usagers(year: int = 2024) -> pd.DataFrame:
    """Charge la table usagers et tente d’en extraire les colonnes utiles."""
    if not DB_FILE.exists():
        return pd.DataFrame(columns=["age", "catu", "grav"])

    with sqlite3.connect(DB_FILE) as conn:
        df = pd.read_sql_query("SELECT * FROM usagers", conn)

    # Si table à une seule colonne => split manuel
    if df.shape[1] == 1:
        df = _split_single_column(df)

    cols = {c.lower(): c for c in df.columns}
    an_nais_col = cols.get("an_nais")
    catu_col = cols.get("catu")
    grav_col = cols.get("grav")

    # Calcul âge si possible
    if an_nais_col:
        an_nais = pd.to_numeric(df[an_nais_col], errors="coerce")
        age = year - an_nais
    else:
        age = pd.Series([], dtype="float64")

    out = pd.DataFrame({
        "age": age,
        "catu": pd.to_numeric(df[catu_col], errors="coerce") if catu_col else pd.NA,
        "grav": pd.to_numeric(df[grav_col], errors="coerce") if grav_col else pd.NA,
    })
    return out


def _make_hist(df: pd.DataFrame, min_age: int) -> pd.DataFrame:
    ages = pd.to_numeric(df["age"], errors="coerce")
    ages = ages[(ages >= min_age) & (ages <= 100)]
    edges = list(range(0, 105, 5))
    labels = [f"{edges[i]}-{edges[i+1]}" for i in range(len(edges) - 1)]
    bins = pd.cut(ages, bins=edges, right=True, include_lowest=True, labels=labels)
    out = bins.value_counts(sort=False).reindex(labels).fillna(0).astype(int).reset_index()
    out.columns = ["Tranche d'âge", "Nombre d'accidents"]
    return out


def _build_fig(df_hist: pd.DataFrame, y_label: str, hover_label: str):
    fig = px.bar(df_hist, x="Tranche d'âge", y="Nombre d'accidents",
                 labels={"Tranche d'âge": "Âge", "Nombre d'accidents": y_label})
    fig.update_traces(hovertemplate=f"%{{x}} ans<br>{hover_label} : %{{y:,}}")
    fig.update_layout(plot_bgcolor="white", paper_bgcolor="white", bargap=0)
    fig.update_xaxes(showgrid=False)
    fig.update_yaxes(showgrid=True, gridcolor="#e5e7eb", tickformat=",d", rangemode="tozero")
    return fig


def histogramme_layout(app: dash.Dash):
    base = _load_usagers(2024)
    init = base[base["catu"] == 1] if "catu" in base.columns else base
    df_hist = _make_hist(init, min_age=14)

    controls = html.Div(
        dcc.Dropdown(
            id="hist-population",
            options=[
                {"label": "Conducteurs uniquement", "value": "conducteurs"},
                {"label": "Occupants de véhicules (conducteurs et passagers)", "value": "occupants"},
                {"label": "Personnes décédées", "value": "decedes"},
            ],
            value="conducteurs", clearable=False, searchable=False,
        ),
        style={"maxWidth": "420px", "margin": "0 auto 10px auto"},
    )

    graph = dcc.Graph(
        id="hist-age-graph",
        figure=_build_fig(df_hist, "Nombre d'accidents", "accidents"),
        config={"displayModeBar": False},
        style={"height": "440px"},
    )

    return html.Div(
        [html.H4("Histogramme des accidents par âge", style={"textAlign": "center", "marginBottom": "10px"}),
         controls,
         html.Div(graph, style={"maxWidth": "1000px", "margin": "0 auto"})]
    )


@dash.callback(
    Output("hist-age-graph", "figure"),
    Input("hist-population", "value"),
)
def _update_hist(pop: str):
    df = _load_usagers(2024)
    if pop == "conducteurs":
        d = df[df["catu"] == 1] if "catu" in df.columns else df
        y_label, hover = "Nombre d'accidents", "accidents"
        h = _make_hist(d, 14)
    elif pop == "occupants":
        d = df[df["catu"].isin([1, 2])] if "catu" in df.columns else df
        y_label, hover = "Nombre d'accidents", "accidents"
        h = _make_hist(d, 0)
    else:  # décédés
        d = df[df["grav"] == 2] if "grav" in df.columns else df.iloc[0:0]
        y_label, hover = "Nombre de décès", "victimes"
        h = _make_hist(d, 0)
    return _build_fig(h, y_label, hover)
