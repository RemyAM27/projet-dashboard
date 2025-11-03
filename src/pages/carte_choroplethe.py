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

MAP_BLOCK_H   = "60vh"
FR_CENTER     = {"lat": 46.4, "lon": 2.0}
MAP_INIT_ZOOM = 4.75

def _fmt(n):
    try:
        return f"{int(round(n)):,}".replace(",", " ")
    except Exception:
        return str(n)

def _legend_row(color, label):
    return html.Div(
        [
            html.Span(style={
                "display": "inline-block", "width": "14px", "height": "14px",
                "backgroundColor": color, "marginRight": "8px",
                "border": "1px solid rgba(0,0,0,0.15)", "borderRadius": "3px"
            }),
            html.Span(label),
        ],
        style={"marginBottom": "5px", "fontSize": "14px"}
    )

def layout(app: dash.Dash):
    global_bg = dcc.Markdown(
        """
        <style>
          html, body, #_dash-app-content, ._dash-app-content {
            background: #ffffff !important; margin: 0 !important;
          }
        </style>
        """,
        dangerously_allow_html=True
    )

    df = load_accidents(Path(DB_PATH), year=2024)
    geojson = load_geojson_departments(Path(DEPT_GEOJSON))
    depc, (b1, b2, b3, b4) = prepare_dep_classes(df)
    allowed_codes = [c for c in CLASS_CODE_ORDER if c != "ex"]

    base_fig = build_map_figure(depc, geojson, selected_codes=allowed_codes)
    base_fig.update_layout(
        margin=dict(l=0, r=0, t=0, b=0),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        autosize=True,
        height=600,
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

    # Graph sans dcc.Loading pour éviter les écrans de chargement
    map_graph = dcc.Graph(
        id="map-accidents",
        figure=base_fig,
        style={"height": MAP_BLOCK_H, "width": "100%", "padding": "0", "margin": "0"},
        config={
            "displayModeBar": False,
            "scrollZoom": False,
            "doubleClick": False,
        },
        clear_on_unhover=False,
    )

    legend = html.Div([
        html.H6("Échelle d’intensité (2024)", style={"textAlign": "center", "fontWeight": "600"}),
        _legend_row(BASE_COLOR_MAP["Très faible"], f"Très faible (≤ {_fmt(b1)})"),
        _legend_row(BASE_COLOR_MAP["Faible"],      f"Faible ({_fmt(b1)} – {_fmt(b2)})"),
        _legend_row(BASE_COLOR_MAP["Moyen"],       f"Moyen ({_fmt(b2)} – {_fmt(b3)})"),
        _legend_row(BASE_COLOR_MAP["Élevé"],       f"Élevé ({_fmt(b3)} – {_fmt(b4)})"),
        _legend_row(BASE_COLOR_MAP["Très élevé"],  f"Très élevé (> {_fmt(b4)})"),
    ], style={"padding": "10px", "width": "230px"})

    filter_labels = [{"label": CODE_TO_KEY[c], "value": c} for c in allowed_codes]
    filter_block = html.Div([
        html.H6("Filtrer par intensité", style={"textAlign": "center", "marginBottom": "8px"}),
        dcc.Checklist(
            id="classe-filter",
            options=filter_labels,
            value=allowed_codes[:],
            labelStyle={"display": "block", "marginBottom": "6px"}
        ),
        html.Div([
            dbc.Button("Appliquer", id="apply-filter", color="primary", size="sm", className="me-2"),
            dbc.Button("Réinitialiser", id="reset-filter", color="secondary", size="sm", outline=True)
        ], style={"textAlign": "center", "marginTop": "8px"})
    ], style={"width": "230px"})

    left_panel = html.Div(
        [legend, html.Div(style={"height": "12px"}), filter_block],
        style={
            "width": "260px",
            "padding": "0 10px 0 20px",
            "display": "flex", "flexDirection": "column",
            "alignItems": "center", "justifyContent": "center",
            "height": MAP_BLOCK_H,
        },
    )

    map_card = html.Div(
        [map_graph],
        style={
            "backgroundColor": "#ffffff",
            "border": "1px solid #e5e7eb",
            "borderRadius": "12px",
            "boxShadow": "0 2px 10px rgba(0,0,0,0.06)",
            "padding": "8px",
            "width": "700px",
        }
    )

    map_title = html.H4(
        "Répartition des accidents de la route en France (2024)",
        style={"textAlign": "center", "color": "#2c3e50", "fontWeight": "600", "marginBottom": "18px"}
    )
    map_col = html.Div(
        [map_title, map_card],
        style={"flex": "0 0 700px", "padding": "0", "display": "flex", "flexDirection": "column", "alignItems": "center"},
    )

    right_col = html.Div([], style={
        "flex": "1 1 auto",
        "backgroundColor": "transparent",
        "minHeight": "82vh",
        "borderLeft": "0",
    })

    layout_row = html.Div(
        [left_panel, map_col, right_col],
        style={
            "display": "flex",
            "justifyContent": "flex-start",
            "alignItems": "flex-start",
            "marginTop": "120px",
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

    # ------------ Callbacks ------------
    # 1) Callback serveur : uniquement pour Appliquer / Réinitialiser (pas de relayoutData ici)
    @app.callback(
        Output("store-mapbase", "data"),
        Output("classe-filter", "value"),
        Input("apply-filter", "n_clicks"),
        Input("reset-filter", "n_clicks"),
        State("classe-filter", "value"),
        State("store-depc", "data"),
        State("store-geojson", "data"),
        prevent_initial_call=True,
    )
    def update_map_store(n_apply, n_reset, selected, depc_data, geojson_data):
        if not depc_data or not geojson_data:
            return dash.no_update, dash.no_update

        ctx = dash.callback_context
        trig = ctx.triggered[0]["prop_id"].split(".")[0] if ctx.triggered else ""

        if trig == "reset-filter":
            selected = [c for c in CLASS_CODE_ORDER if c != "ex"]

        depc_df = pd.DataFrame(depc_data)
        fig = build_map_figure(depc_df, geojson_data, selected_codes=selected)
        fig.update_layout(
            margin=dict(l=0, r=0, t=0, b=0),
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            autosize=True,
            height=600,
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
        return fig.to_dict(), selected

    # 2) Clientside callback : remet instantanément la figure de base si l’utilisateur tente de pan/zoom
    app.clientside_callback(
        """
        function(relayoutData, figDict) {
            // Si l'utilisateur tente de déplacer/zoomer, on ramène la figure de base côté client
            if (relayoutData && (
                relayoutData['mapbox.center'] !== undefined ||
                relayoutData['mapbox.zoom'] !== undefined ||
                relayoutData['mapbox._derived'] !== undefined
            )) {
                return figDict;
            }
            // sinon: sur chargement initial ou changement de filtre, on affiche figDict tel quel
            return figDict;
        }
        """,
        Output("map-accidents", "figure"),
        Input("map-accidents", "relayoutData"),
        State("store-mapbase", "data"),
    )

    return page
