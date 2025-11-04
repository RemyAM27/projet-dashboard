import sqlite3
from pathlib import Path
from typing import Optional

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
    col = df_raw.columns[0]
    df = df_raw[col].astype(str).str.split(",", expand=True)
    df = df.apply(lambda s: s.str.strip().str.strip('"').str.strip("'"))
    first = df.iloc[0].str.lower().tolist()
    if any(("num" in v and "acc" in v) or "catu" in v or "grav" in v or "an_nais" in v for v in first):
        df.columns = [v.strip() for v in df.iloc[0]]
        df = df.iloc[1:].reset_index(drop=True)
    else:
        df.columns = [f"c{i}" for i in range(df.shape[1])]
    return df


def _guess_an_nais(df: pd.DataFrame) -> Optional[str]:
    best, score = None, -1
    for c in df.columns:
        s = pd.to_numeric(df[c], errors="coerce")
        sc = ((s >= 1900) & (s <= 2010)).sum()
        if sc > score:
            best, score = c, sc
    return best


def _guess_catu(df: pd.DataFrame) -> Optional[str]:
    best, score = None, -1
    for c in df.columns:
        s = pd.to_numeric(df[c], errors="coerce")
        sc = s.isin([1, 2, 3]).sum()
        if sc > score:
            best, score = c, sc
    return best


def _guess_grav(df: pd.DataFrame) -> Optional[str]:
    best, score = None, -1
    for c in df.columns:
        s = pd.to_numeric(df[c], errors="coerce")
        sc = s.isin([1, 2, 3, 4]).sum()
        if sc > score:
            best, score = c, sc
    return best


def load_age_base(year: int = 2024) -> pd.DataFrame:
    if not DB_FILE.exists():
        return pd.DataFrame(columns=["age", "catu", "grav"])

    with sqlite3.connect(DB_FILE) as conn:
        df_u = pd.read_sql_query("SELECT * FROM usagers", conn)

    if df_u.shape[1] == 1:
        df_u = _split_single_column(df_u)

    cols_lower = {c.lower(): c for c in df_u.columns}
    an_nais_col = cols_lower.get("an_nais") or _guess_an_nais(df_u)
    catu_col = cols_lower.get("catu") or _guess_catu(df_u)
    grav_col = cols_lower.get("grav") or _guess_grav(df_u)

    out = pd.DataFrame()
    if an_nais_col is not None:
        an_nais = pd.to_numeric(df_u[an_nais_col], errors="coerce")
        out["age"] = year - an_nais
    else:
        out["age"] = pd.NA

    out["catu"] = pd.to_numeric(df_u[catu_col], errors="coerce") if catu_col else pd.NA
    out["grav"] = pd.to_numeric(df_u[grav_col], errors="coerce") if grav_col else pd.NA
    return out[["age", "catu", "grav"]]


def _make_hist(df: pd.DataFrame, min_age: int) -> pd.DataFrame:
    ages = pd.to_numeric(df.get("age", pd.Series(dtype="float64")), errors="coerce")
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
    fig.update_layout(plot_bgcolor="white", paper_bgcolor="white", bargap=0,
                      margin=dict(l=30, r=30, t=40, b=40))
    fig.update_xaxes(showgrid=False)
    fig.update_yaxes(showgrid=True, gridcolor="#e5e7eb", tickformat=",d", rangemode="tozero")
    return fig


def histogramme_layout(app: dash.Dash):
    base = load_age_base(2024)
    init = base[base["catu"] == 1] if "catu" in base.columns and base["catu"].notna().any() else base
    df_hist = _make_hist(init, min_age=14)

    dropdown = html.Div(
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

    graph = dcc.Loading(
        type="default",
        children=dcc.Graph(
            id="hist-age-graph",
            figure=_build_fig(df_hist, "Nombre d'accidents", "accidents"),
            config={"displayModeBar": False},
            style={"height": "440px"},
        ),
    )

    return html.Div(
        [
            html.H4("Histogramme des accidents par âge", style={"textAlign": "center", "marginBottom": "10px"}),
            dropdown,
            html.Div(graph, style={"maxWidth": "1000px", "margin": "0 auto"}),
        ]
    )


@dash.callback(
    Output("hist-age-graph", "figure"),
    Input("hist-population", "value"),
)
def update_histogram(pop: str):
    df = load_age_base(2024)
    pop = (pop or "").lower()

    if pop == "conducteurs" and "catu" in df.columns and df["catu"].notna().any():
        df = df[df["catu"] == 1]
        y_label, hover = "Nombre d'accidents", "accidents"
        min_age = 14
    elif pop == "occupants" and "catu" in df.columns and df["catu"].notna().any():
        df = df[df["catu"].isin([1, 2])]
        y_label, hover = "Nombre d'accidents", "accidents"
        min_age = 0
    elif pop == "decedes" and "grav" in df.columns and df["grav"].notna().any():
        df = df[df["grav"] == 2]
        y_label, hover = "Nombre de décès", "victimes"
        min_age = 0
    else:
        y_label, hover = "Nombre d'accidents", "accidents"
        min_age = 0

    return _build_fig(_make_hist(df, min_age), y_label, hover)


