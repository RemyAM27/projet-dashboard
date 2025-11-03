# src/pages/histogramme.py — v1 (corrigée, basique mais robuste)
import sqlite3
from pathlib import Path

import pandas as pd
import dash
from dash import html, dcc
import plotly.express as px

try:
    from config import DB_PATH
    DB_FILE = Path(DB_PATH)
except Exception:
    DB_FILE = Path("data/accidents.sqlite")


def _split_single_column(df_raw: pd.DataFrame) -> pd.DataFrame:
    """Cas fichier à une seule colonne texte type 'csv dans une cellule'."""
    col = df_raw.columns[0]
    df = df_raw[col].astype(str).str.split(",", expand=True)
    df = df.apply(lambda s: s.str.strip().str.strip('"').str.strip("'"))
    first = df.iloc[0].str.lower().tolist()
    # Si la première ligne ressemble à un en-tête, on l’utilise
    if any(("an_nais" in v) or ("catu" in v) or ("grav" in v) or ("num" in v and "acc" in v) for v in first):
        df.columns = [v.strip() for v in df.iloc[0]]
        df = df.iloc[1:].reset_index(drop=True)
    else:
        df.columns = [f"c{i}" for i in range(df.shape[1])]
    return df


def _load_usagers(year: int = 2024) -> pd.DataFrame:
    """Version simple : on calcule l’âge si on trouve an_nais ; sinon, tableau vide."""
    if not DB_FILE.exists():
        return pd.DataFrame(columns=["age", "catu"])

    with sqlite3.connect(DB_FILE) as conn:
        df = pd.read_sql_query("SELECT * FROM usagers", conn)

    if df.shape[1] == 1:
        df = _split_single_column(df)

    cols = {c.lower(): c for c in df.columns}
    an_nais_col = cols.get("an_nais")
    catu_col = cols.get("catu")

    out = pd.DataFrame()
    if an_nais_col is not None:
        an_nais = pd.to_numeric(df[an_nais_col], errors="coerce")
        out["age"] = year - an_nais
    else:
        out["age"] = pd.Series([], dtype="float64")

    out["catu"] = pd.to_numeric(df[catu_col], errors="coerce") if catu_col else pd.Series([], dtype="float64")
    return out


def _empty_hist() -> pd.DataFrame:
    edges = list(range(0, 105, 5))
    labels = [f"{edges[i]}-{edges[i+1]}" for i in range(len(edges) - 1)]
    return pd.DataFrame({"Tranche d'âge": labels, "Nombre d'accidents": [0] * len(labels)})


def _make_hist_conducteurs(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty or "age" not in df.columns:
        return _empty_hist()
    d = df
    if "catu" in df.columns:
        d = d[d["catu"] == 1]
    ages = pd.to_numeric(d["age"], errors="coerce")
    ages = ages[(ages >= 14) & (ages <= 100)]
    if ages.empty:
        return _empty_hist()

    edges = list(range(0, 105, 5))
    labels = [f"{edges[i]}-{edges[i+1]}" for i in range(len(edges) - 1)]
    bins = pd.cut(ages, bins=edges, right=True, include_lowest=True, labels=labels)
    out = bins.value_counts(sort=False).reindex(labels).fillna(0).astype(int).reset_index()
    out.columns = ["Tranche d'âge", "Nombre d'accidents"]
    return out


def histogramme_layout(app: dash.Dash):
    base = _load_usagers(2024)
    data = _make_hist_conducteurs(base)
    fig = px.bar(
        data, x="Tranche d'âge", y="Nombre d'accidents",
        labels={"Tranche d'âge": "Âge", "Nombre d'accidents": "Nombre d'accidents"},
    )
    fig.update_layout(plot_bgcolor="white", paper_bgcolor="white", bargap=0)

    return html.Div(
        [
            html.H4("Histogramme des accidents par âge", style={"textAlign": "center"}),
            html.Div(dcc.Graph(id="hist-age-graph", figure=fig), style={"maxWidth": "1000px", "margin": "0 auto"}),
        ]
    )
