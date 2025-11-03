import dash
from dash import html
import dash_bootstrap_components as dbc

from src.pages.carte_choroplethe import layout as carte_layout
from src.pages.histogramme import histogramme_layout

external_stylesheets = [dbc.themes.BOOTSTRAP]
app = dash.Dash(__name__, external_stylesheets=external_stylesheets, suppress_callback_exceptions=True)
app.title = "Dashboard - Accidents (SQLite)"

app.layout = dbc.Container(
    [
        html.H3("Dashboard – Accidents de la route (2024)", className="mt-3 mb-4 text-center", style={"color": "#b91c1c"}   ),

        # === Ligne principale : carte à gauche, histogramme à droite ===
        dbc.Row(
            [
                dbc.Col(
                    html.Div(carte_layout(app)),
                    width=8,  # carte = ~2/3 de la largeur
                    style={"paddingRight": "10px"}
                ),
                dbc.Col(
                    html.Div(
                        histogramme_layout(app),
                        style={
                            "backgroundColor": "#ffffff",
                            "border": "1px solid #e5e7eb",
                            "borderRadius": "12px",
                            "boxShadow": "0 2px 10px rgba(0,0,0,0.06)",
                            "padding": "10px",
                            "height": "fit-content"
                        }
                    ),
                    width=4,  # histogramme = ~1/3
                ),
            ],
            justify="center",
            align="start",
            className="g-0",
        ),

        html.Br(), html.Br(),
    ],
    fluid=True,
)

if __name__ == "__main__":
    app.run(debug=True)
