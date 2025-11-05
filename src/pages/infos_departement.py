# src/pages/infos_departement.py
from __future__ import annotations
import sqlite3
from pathlib import Path

import dash
import dash_bootstrap_components as dbc
from dash import html, dcc, Input, Output
import pandas as pd

from config import DB_PATH, DEPT_GEOJSON
from ..utils.data_utils import load_geojson_departments

YEAR = 2024

def _codes_101() -> list[str]:
    base = [f"{i:02d}" for i in range(1, 96) if i != 20]
    base += ["2A", "2B"]
    base += [str(i) for i in range(971, 977)]
    return base

FALLBACK_NAMES = {
    "2A": "Corse-du-Sud",
    "2B": "Haute-Corse",
    "971": "Guadeloupe",
    "972": "Martinique",
    "973": "Guyane",
    "974": "La Réunion",
    "976": "Mayotte",
}

def _normalize_dep_series(s: pd.Series) -> pd.Series:
    s = s.astype(str).str.strip().str.upper()
    s = s.replace({"201": "2A", "202": "2B"})
    s = s.where(s.isin(["2A", "2B"]), s.str.zfill(2))
    return s

def _load_dep_counts(db_file: Path, year: int = YEAR) -> pd.DataFrame:
    with sqlite3.connect(db_file) as conn:
        q = """
        SELECT dep AS dep, COUNT(*) AS n
        FROM caracteristiques
        WHERE an = ?
        GROUP BY dep
        """
        df = pd.read_sql_query(q, conn, params=[year])
    df["dep"] = _normalize_dep_series(df["dep"])
    return df

def _dropdown_options(geojson: dict, allowed_codes: set[str]) -> list[dict]:
    names = {}
    for f in geojson.get("features", []):
        code = str(f["properties"].get("code", "")).strip().upper()
        nom = f["properties"].get("nom", "")
        if code:
            names[code] = nom
    names.update({k: v for k, v in FALLBACK_NAMES.items() if k not in names})

    def _sort_key(x: str) -> str:
        return x.replace("A", "0A").replace("B", "0B")

    opts = []
    for code in sorted(allowed_codes, key=_sort_key):
        opts.append({"label": f"{code} - {names.get(code, 'Département')}", "value": code})
    return opts

def infos_departement_layout(app: dash.Dash) -> dbc.Card:
    db_file = Path(DB_PATH)
    geojson = load_geojson_departments(Path(DEPT_GEOJSON))
    depc = _load_dep_counts(db_file, YEAR)

    allowed_101 = set(_codes_101())
    depc = depc[depc["dep"].isin(allowed_101)].copy()

    total = int(depc["n"].sum())
    nb_dep = 101

    # 5 classes (quantiles)
    q = depc["n"].quantile([0.0, 0.2, 0.4, 0.6, 0.8, 1.0]).values
    labels = ["Très faible", "Faible", "Moyen", "Élevé", "Très élevé"]
    depc["class_label"] = pd.cut(depc["n"], bins=q, labels=labels, include_lowest=True, duplicates="drop")

    # Classement
    depc = depc.sort_values("n", ascending=False).reset_index(drop=True)
    depc["rang"] = depc["n"].rank(method="min", ascending=False).astype(int)

    app.server.depc_df = depc
    app.server.dept_total = total
    app.server.nb_dep = nb_dep

    dropdown = dcc.Dropdown(
        id="dep-info-dropdown",
        options=_dropdown_options(geojson, allowed_101),
        placeholder="Choisir un département…",
        clearable=False,
        searchable=True,
        style={"width": "100%"},
        value="75" if "75" in depc["dep"].values else sorted(allowed_101)[0],
    )

    kpi_box = {"textAlign": "center", "padding": "8px"}

    content = dbc.Card(
        [
            html.H5("Infos département (2024)", style={"textAlign": "center", "marginBottom": "10px"}),
            dbc.CardBody(
                [
                    dropdown,
                    html.Div(
                        dbc.Row(
                            [
                                dbc.Col(html.Div([html.Small("Intensité"), html.Div(id="kpi-intensite", className="fw-bold")], style=kpi_box), md=3),
                                dbc.Col(html.Div([html.Small("Nombre d'accidents"), html.Div(id="kpi-nb", className="fw-bold")], style=kpi_box), md=3),
                                dbc.Col(html.Div([html.Small("Part du total"), html.Div(id="kpi-part", className="fw-bold")], style=kpi_box), md=3),
                                dbc.Col(html.Div([html.Small("Classement"), html.Div(id="kpi-rang", className="fw-bold")], style=kpi_box), md=3),
                            ],
                            className="g-2 mt-3",
                        )
                    ),
                ]
            ),
        ],
        className="mb-3",
    )

    @app.callback(
        Output("kpi-intensite", "children"),
        Output("kpi-nb", "children"),
        Output("kpi-part", "children"),
        Output("kpi-rang", "children"),
        Input("dep-info-dropdown", "value"),
        prevent_initial_call=False,
    )
    def _update(dep_code: str):
        df = app.server.depc_df
        total = app.server.dept_total
        nb_dep = app.server.nb_dep

        row = df.loc[df["dep"] == dep_code]
        if row.empty:
            return "—", "—", "—", "—"

        n = int(row["n"].values[0])
        part = (n / total * 100.0) if total > 0 else 0.0
        intensite = str(row["class_label"].values[0]) if "class_label" in row else "—"
        rang = int(row["rang"].values[0])
        return intensite, f"{n:,}".replace(",", " "), f"{part:.1f}%", f"{rang} / {nb_dep}"

    return content


