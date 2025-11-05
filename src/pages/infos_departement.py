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

def _load_dep_counts(db_file: Path, year: int = YEAR) -> pd.DataFrame:
    with sqlite3.connect(db_file) as conn:
        q = """
        SELECT dep AS dep, COUNT(*) AS n
        FROM caracteristiques
        WHERE an = ?
        GROUP BY dep
        """
        df = pd.read_sql_query(q, conn, params=[year])
    df["dep"] = df["dep"].astype(str)
    return df

def _dropdown_options_from_geojson(geojson: dict) -> list[dict]:
    opts = []
    for f in geojson.get("features", []):
        code = str(f["properties"].get("code", "")).strip().upper()
        nom = f["properties"].get("nom", "")
        if code:
            opts.append({"label": f"{code} - {nom}", "value": code})
    # tri simple par code
    opts.sort(key=lambda x: x["value"])
    return opts

def infos_departement_layout(app: dash.Dash) -> dbc.Card:
    db_file = Path(DB_PATH)
    geojson = load_geojson_departments(Path(DEPT_GEOJSON))
    depc = _load_dep_counts(db_file, YEAR)

    total = int(depc["n"].sum())

    dropdown = dcc.Dropdown(
        id="dep-info-dropdown",
        options=_dropdown_options_from_geojson(geojson),
        placeholder="Choisir un département…",
        clearable=False,
        searchable=True,
        style={"width": "100%"},
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
                                dbc.Col(html.Div([html.Small("Nombre d'accidents"), html.Div(id="kpi-nb", className="fw-bold")], style=kpi_box), md=6),
                                dbc.Col(html.Div([html.Small("Part du total"), html.Div(id="kpi-part", className="fw-bold")], style=kpi_box), md=6),
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
        Output("kpi-nb", "children"),
        Output("kpi-part", "children"),
        Input("dep-info-dropdown", "value"),
        prevent_initial_call=False,
    )
    def _update(dep_code: str):
        if not dep_code:
            return "—", "—"
        row = depc.loc[depc["dep"] == str(dep_code)]
        if row.empty:
            return "—", "—"
        n = int(row["n"].values[0])
        part = (n / total * 100.0) if total > 0 else 0.0
        return f"{n:,}".replace(",", " "), f"{part:.1f}%"

    return content


