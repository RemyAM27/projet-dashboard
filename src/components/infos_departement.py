from __future__ import annotations
import sqlite3
from pathlib import Path

import dash
import dash_bootstrap_components as dbc
from dash import html, dcc, Input, Output
import pandas as pd

from config import DB_PATH, DEPT_GEOJSON
from ..utils.data_utils import load_geojson_departments
from ..components.map_choropleth import BASE_COLOR_MAP

YEAR = 2024


def _codes_metropole() -> list[str]:
    """
    Liste ordonnée des départements métropolitains :
    01..95 (sauf 20) puis 2A et 2B à la fin.
    """
    codes = [f"{i:02d}" for i in range(1, 96) if i != 20]
    codes += ["2A", "2B"]
    return codes

def _codes_101() -> list[str]:
    """
    Ensemble /101 = Métropole (96) + DOM (971..976).
    Utilisé pour le classement et la part du total.
    """
    codes = _codes_metropole()
    codes += [str(i) for i in range(971, 977)]
    return codes

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
    """Gère 201/202 -> 2A/2B et zéro-padding ailleurs (01, 02, ...)."""
    s = s.astype(str).str.strip().str.upper()
    s = s.replace({"201": "2A", "202": "2B"})
    s = s.where(s.isin(["2A", "2B"]), s.str.zfill(2))
    return s


def _load_dep_counts(db_file: Path, year: int = YEAR) -> pd.DataFrame:
    """Retourne dep, n (nb d'accidents) pour l'année donnée."""
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


def _dropdown_options(geojson: dict, ordered_codes: list[str]) -> list[dict]:
    """
    Construit la liste déroulante STRICTEMENT dans l'ordre fourni.
    Assure 2A/2B via noms de secours si absents du GeoJSON.
    """
    names = {}
    for f in geojson.get("features", []):
        code = str(f["properties"].get("code", "")).strip().upper()
        nom = f["properties"].get("nom", "")
        if code:
            names[code] = nom
    names.setdefault("2A", "Corse-du-Sud")
    names.setdefault("2B", "Haute-Corse")

    opts = []
    for code in ordered_codes:
        label = f"{code} - {names.get(code, 'Département')}"
        opts.append({"label": label, "value": code})
    return opts


def infos_departement_layout(app: dash.Dash) -> dbc.Card:
    db_file = Path(DB_PATH)
    geojson = load_geojson_departments(Path(DEPT_GEOJSON))

    counts = _load_dep_counts(db_file, YEAR) 


    codes96_list = _codes_metropole()   
    codes101_set = set(_codes_101())  


    all_codes_sorted = sorted(codes101_set, key=lambda x: x.replace("A", "0A").replace("B", "0B"))
    all_codes_df = pd.DataFrame({"dep": all_codes_sorted})
    depc_all = all_codes_df.merge(counts, on="dep", how="left")
    depc_all["n"] = depc_all["n"].fillna(0).astype(int)

    total_all = int(depc_all["n"].sum())
    nb_dep_all = 101


    depc96 = depc_all[depc_all["dep"].isin(codes96_list)].copy()
    if not depc96.empty:
        q = depc96["n"].quantile([0.0, 0.2, 0.4, 0.6, 0.8, 1.0]).values
    else:
        q = [0, 0, 0, 0, 0, 0]

    labels = ["Très faible", "Faible", "Moyen", "Élevé", "Très élevé"]
    depc_all["class_label"] = pd.cut(
        depc_all["n"], bins=q, labels=labels, include_lowest=True, duplicates="drop"
    )

    depc_all = depc_all.sort_values("n", ascending=False).reset_index(drop=True)
    depc_all["rang"] = depc_all["n"].rank(method="min", ascending=False).astype(int)


    app.server.depc_all = depc_all
    app.server.total_all = total_all
    app.server.nb_dep_all = nb_dep_all


    dropdown = dcc.Dropdown(
        id="dep-info-dropdown",
        options=_dropdown_options(geojson, codes96_list),
        placeholder="Choisir un département…",
        clearable=False,
        searchable=True,
        style={"width": "100%"},
        value="75", 
    )


    kpi_style = {
        "display": "flex",
        "flexDirection": "column",
        "alignItems": "center",
        "justifyContent": "center",
        "padding": "6px 8px",
        "minHeight": "64px",
        "borderRadius": "10px",
        "backgroundColor": "var(--bs-light)",
        "border": "1px solid #eee",
    }


    content = dbc.Card(
        [
            dbc.CardBody(
                [
                    dropdown,
                    html.Div(
                        dbc.Row(
                            [
                                dbc.Col(
                                    html.Div([html.Small("Intensité"), html.Div(id="kpi-intensite", className="fw-bold")], style=kpi_style),
                                    md=3,
                                ),
                                dbc.Col(
                                    html.Div([html.Small("Nombre d'accidents"), html.Div(id="kpi-nb", className="fw-bold")], style=kpi_style),
                                    md=3,
                                ),
                                dbc.Col(
                                    html.Div([html.Small("Part du total"), html.Div(id="kpi-part", className="fw-bold")], style=kpi_style),
                                    md=3,
                                ),
                                dbc.Col(
                                    html.Div([html.Small("Classement"), html.Div(id="kpi-rang", className="fw-bold")], style=kpi_style),
                                    md=3,
                                ),
                            ],
                            className="g-2 mt-3",
                        )
                    ),
                ]
            ),
        ],
        className="mb-3",
        style={
            "backgroundColor": "#ffffff",
            "border": "1px solid #e5e7eb",
            "borderRadius": "12px",
            "boxShadow": "0 2px 10px rgba(0,0,0,0.06)",
            "padding": "16px",
            "width": "100%",
            "maxWidth": "1040px",
            "boxSizing": "border-box",
        },
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
        df_all = app.server.depc_all
        total_all = app.server.total_all
        nb_dep_all = app.server.nb_dep_all


        row = df_all.loc[df_all["dep"] == dep_code]
        if row.empty:
            return "—", "—", "—", f"— / {nb_dep_all}"

        n = int(row["n"].values[0])
        part = (n / total_all * 100.0) if total_all > 0 else 0.0
        intensite = str(row["class_label"].values[0]) if "class_label" in row else "—"
        rang = int(row["rang"].values[0])

        color = BASE_COLOR_MAP.get(intensite, "#eceff1")
        badge = html.Span(intensite, style={"padding": "2px 6px", "borderRadius": "6px", "backgroundColor": color})

        return badge, f"{n:,}".replace(",", " "), f"{part:.1f}%", f"{rang} / {nb_dep_all}"

    return content


