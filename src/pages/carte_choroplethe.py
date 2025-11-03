from __future__ import annotations
import dash
from dash import html, dcc, Input, Output, State
import dash_bootstrap_components as dbc
import pandas as pd
from pathlib import Path
from config import DB_PATH, DEPT_GEOJSON
from ..utils.data_utils import load_accidents, load_geojson_departments
from ..components.map_choropleth import (
    build_map_figure, prepare_dep_classes,
    BASE_COLOR_MAP, CLASS_CODE_ORDER, CODE_TO_KEY
)

# Réglages
MAP_BLOCK_H = "72vh"
FR_CENTER = {"lat": 46.4, "lon": 2.0}
MAP_INIT_ZOOM = 4.75


def _fmt(n):
    try:
        return f"{int(round(n)):,}".replace(",", " ")
    except Exception:
        return str(n)


def _legend_row(color, label):
    return html.Div(
        [
            html.Span(
                style={
                    "display": "inline-block",
                    "width": "12px",
                    "height": "12px",
                    "backgroundColor": color,
                    "marginRight": "8px",
                    "border": "1px solid rgba(0,0,0,0.15)",
                    "borderRadius": "3px",
                }
            ),
            html.Span(label),
        ],
        style={"display": "flex", "alignItems": "center", "marginBottom": "6px", "fontSize": "14px"},
    )


def layout(app: dash.Dash):
    global_bg = dcc.Markdown(
        """
        <style>
          html, body, #_dash-app-content, ._dash-app-content {
            background: #ffffff !important;
            margin: 0 !important;
          }
        </style>
        """,
        dangerously_allow_html=True,
    )

    # Données
    df = load_accidents(Path(DB_PATH), year=2024)
    geojson = load_geojson_departments(Path(DEPT_GEOJSON))
    depc, (b1, b2, b3, b4) = prepare_dep_classes(df)
    allowed_codes = [c for c in CLASS_CODE_ORDER if c != "ex"]

    # Figure de base
    base_fig = build_map_figure(depc, geojson, selected_codes=allowed_codes)
    base_fig.update_layout(
        margin=dict(l=0, r=0, t=0, b=0),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        autosize=True,
        height=720,
        dragmode=False,
        mapbox=dict(
            zoom=MAP_INIT_ZOOM,
            center=FR_CENTER,
            style="white-bg",
            bearing=0,
            pitch=0,
            uirevision="map-fixed-v1",
        ),
        transition={"duration": 0},
    )

    # Graph (hover activé, gestes bloqués)
    map_graph = dcc.Graph(
        id="map-accidents",
        figure=base_fig,
        style={"height": MAP_BLOCK_H, "width": "100%", "padding": "0", "margin": "0"},
        config={
            "displayModeBar": False,
            "scrollZoom": False,
            "doubleClick": False,
            "modeBarButtonsToRemove": [
                "zoom", "pan", "select", "lasso2d",
                "zoomIn2d", "zoomOut2d", "autoScale2d", "resetScale2d"
            ],
        },
    )

    # Colonne de gauche (légende + filtres) — bien alignée, sans marges qui débordent
    side_panel = html.Div(
        [
            html.Div("   Echelle d’intensité", style={"textAlign": "center", "fontWeight": 600, "marginBottom": "8px"}),
            _legend_row(BASE_COLOR_MAP["Très faible"], f"Très faible (≤ {_fmt(b1)})"),
            _legend_row(BASE_COLOR_MAP["Faible"],      f"Faible ({_fmt(b1)} – {_fmt(b2)})"),
            _legend_row(BASE_COLOR_MAP["Moyen"],       f"Moyen ({_fmt(b2)} – {_fmt(b3)})"),
            _legend_row(BASE_COLOR_MAP["Élevé"],       f"Élevé ({_fmt(b3)} – {_fmt(b4)})"),
            _legend_row(BASE_COLOR_MAP["Très élevé"],  f"Très élevé (> {_fmt(b4)})"),

            html.Div("Filtrer par intensité", style={"textAlign": "center", "marginTop": "14px", "marginBottom": "8px", "fontWeight": 600}),
            dcc.Checklist(
                id="classe-filter",
                options=[{"label": CODE_TO_KEY[c], "value": c} for c in allowed_codes],
                value=allowed_codes[:],
                labelStyle={"display": "block", "marginBottom": "6px"},
                inputStyle={"marginRight": "6px"},
                style={"display": "grid", "rowGap": "6px", "paddingLeft": "2px"}
            ),
            html.Div(
                [
                    dbc.Button("Appliquer", id="apply-filter", color="primary", size="sm", className="me-2"),
                    dbc.Button("Réinitialiser", id="reset-filter", color="secondary", size="sm", outline=True),
                ],
                style={"textAlign": "center", "marginTop": "10px"},
            ),
        ],
        style={
            "flex": "0 0 240px",
            "width": "240px",
            "boxSizing": "border-box",
        },
    )

    # Carte et panneau côte à côte dans la même carte blanche
    map_card = html.Div(
        [
            html.H5(
                "Accidents de la route en France",
                style={"textAlign": "center", "color": "#2c3e50", "fontWeight": 600, "marginBottom": "10px"},
            ),
            html.Div(
                [side_panel, html.Div(map_graph, style={"flex": "1 1 auto", "minWidth": "520px"})],
                style={
                    "display": "flex",
                    "alignItems": "flex-start",
                    "gap": "16px",
                    "width": "100%",
                    "boxSizing": "border-box",
                },
            ),
        ],
        style={
            "backgroundColor": "#ffffff",
            "border": "1px solid #e5e7eb",
            "borderRadius": "12px",
            "boxShadow": "0 2px 10px rgba(0,0,0,0.06)",
            "padding": "16px",
            "width": "100%",
            "maxWidth": "1040px",   # largeur confortable
            "marginLeft": "0,5%",     # décale vers la gauche
            "boxSizing": "border-box",
            "overflow": "hidden",   # empêche tout débordement qui ferait “sauter” la bordure
        },
    )

    layout_row = html.Div(
        [map_card],
        style={
            "display": "flex",
            "justifyContent": "flex-start",
            "alignItems": "flex-start",
            "marginTop": "80px",
            "marginBottom": "40px",
            "width": "100%",
        },
    )

    stores = [
        dcc.Store(id="store-depc", data=depc.to_dict("records")),
        dcc.Store(id="store-geojson", data=geojson),
        dcc.Store(id="store-mapbase", data=base_fig.to_dict()),
    ]

    page = html.Div([global_bg, *stores, layout_row],
                    style={"backgroundColor": "#ffffff", "minHeight": "100vh", "margin": "0", "padding": "0"})

    # Callback (pas de relayoutData → pas de spinner au drag)
    @app.callback(
        Output("map-accidents", "figure"),
        Output("classe-filter", "value"),
        Output("store-mapbase", "data"),
        Input("apply-filter", "n_clicks"),
        Input("reset-filter", "n_clicks"),
        State("classe-filter", "value"),
        State("store-depc", "data"),
        State("store-geojson", "data"),
        State("store-mapbase", "data"),
        prevent_initial_call=True,
    )
    def update_map(n_apply, n_reset, selected, depc_data, geojson_data, base_fig_dict):
        if not depc_data or not geojson_data:
            return dash.no_update, selected, base_fig_dict

        ctx = dash.callback_context
        trig = ctx.triggered[0]["prop_id"].split(".")[0] if ctx.triggered else ""
        if trig == "reset-filter":
            selected = [c for c in CLASS_CODE_ORDER if c != "ex"]

        depc_df = pd.DataFrame(depc_data)
        new_fig = build_map_figure(depc_df, geojson_data, selected_codes=selected)
        new_fig.update_layout(
            margin=dict(l=0, r=0, t=0, b=0),
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            autosize=True,
            height=720,
            dragmode=False,
            mapbox=dict(
                zoom=MAP_INIT_ZOOM,
                center=FR_CENTER,
                style="white-bg",
                bearing=0,
                pitch=0,
                uirevision="map-fixed-v1",
            ),
            transition={"duration": 0},
        )
        return new_fig, selected, new_fig.to_dict()

    return page
