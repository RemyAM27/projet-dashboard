from __future__ import annotations
import dash
from dash import html, dcc
import pandas as pd
from pathlib import Path
from config import DB_PATH, DEPT_GEOJSON
from ..utils.data_utils import load_accidents, load_geojson_departments
from ..components.map_choropleth import build_map_figure, prepare_dep_classes, CLASS_CODE_ORDER

def layout(app: dash.Dash):
    # --- Données ---
    df = load_accidents(Path(DB_PATH), year=2024)
    geojson = load_geojson_departments(Path(DEPT_GEOJSON))
    depc, _ = prepare_dep_classes(df)

    # --- Nettoyage des types ---
    depc["accidents"] = pd.to_numeric(depc["accidents"], errors="coerce").fillna(0).astype(int)
    depc["dep"] = depc["dep"].astype(str)

    # --- Carte ---
    fig_map = build_map_figure(depc, geojson, selected_codes=CLASS_CODE_ORDER)
    map_graph = dcc.Graph(
        id="map-accidents",
        figure=fig_map,
        style={"height": "95vh", "width": "100%"},
        config={"displayModeBar": False}
    )

    # --- Page ---
    page = html.Div(
        [map_graph],
        style={"margin": "0 auto", "maxWidth": "1200px", "padding": "20px"}
    )

    return page
