import dash
import dash_bootstrap_components as dbc
from src.pages.carte_choroplethe import layout


external_stylesheets = [dbc.themes.BOOTSTRAP]
app = dash.Dash(__name__, external_stylesheets=external_stylesheets, suppress_callback_exceptions=True)
app.title = "Dashboard - Accidents (SQLite)"

app.layout = layout(app)

if __name__ == "__main__":
    app.run(debug=True)   # Dash v3
