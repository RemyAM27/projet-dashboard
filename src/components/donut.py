from __future__ import annotations
import sqlite3
from pathlib import Path

import dash
from dash import html, dcc, Input, Output
import plotly.graph_objects as go
import pandas as pd

from config import DB_PATH

# Définition des constantes utilisées dans le code
YEAR = 2024  # L'année des données que nous analysons
MAJORITY = 18  # L'âge de la majorité pour la classification
GRAV_MAPPING = {1: "Indemne", 4: "Léger", 3: "Hospitalisé", 2: "Tué"}  # Mapping des codes de gravité
ORDER = ["Indemne", "Léger", "Hospitalisé", "Tué"]  # Ordre d'affichage des catégories
COLORS = {"Indemne": "#94A3B8", "Léger": "#34D399", "Hospitalisé": "#F59E0B", "Tué": "#EF4444"}  # Couleurs associées à chaque catégorie

# Fonction pour normaliser les valeurs à 100% (pourcentage total)
def _normalize_to_100(values):
    # Arrondi les valeurs à 1 décimale
    r = [round(v, 1) for v in values]
    # Calculer la différence par rapport à 100
    diff = round(100.0 - sum(r), 1)
    # Si la différence est significative, ajuster la valeur la plus élevée ou la plus faible
    if abs(diff) >= 0.1:
        res = [v - round(v, 1) for v in values]
        idx = res.index(max(res)) if diff > 0 else res.index(min(res))
        r[idx] = round(r[idx] + diff, 1)
    return r

# Fonction pour lire et compter les gravités des usagers dans la base de données
def _read_counts(db: Path, profile: str) -> pd.DataFrame:
    # Définir les conditions de filtrage pour la requête SQL
    cond = ["c.an = ?"]; params = [YEAR]
    p = (profile or "").lower()  # Filtrer par type d'usager (conducteur, passager, majeur, mineur)
    if p == "conducteur":  cond.append("u.catu = 1")
    if p == "passagers":   cond.append("u.catu = 2")
    if p == "majeur":      cond += ["u.an_nais IS NOT NULL", "u.an_nais <= ?"]; params.append(YEAR - MAJORITY)
    if p == "mineur":      cond += ["u.an_nais IS NOT NULL", "u.an_nais > ?"];  params.append(YEAR - MAJORITY)

    # Requête SQL pour compter les accidents par gravité
    sql = f"""
        SELECT u.grav AS grav, COUNT(*) AS n
        FROM usagers u
        JOIN caracteristiques c ON c.num_acc = u.num_acc
        WHERE {' AND '.join(cond)}
        GROUP BY u.grav
        ORDER BY u.grav
    """
    # Exécution de la requête et lecture des résultats dans un DataFrame
    with sqlite3.connect(db) as conn:
        df = pd.read_sql_query(sql, conn, params=params)
    
    # Si le DataFrame est vide, retourner un DataFrame vide avec des colonnes définies
    if df.empty: return pd.DataFrame({"label": [], "n": []})
    
    # Mapper les codes de gravité aux labels correspondants
    df["label"] = pd.to_numeric(df["grav"], errors="coerce").map(GRAV_MAPPING)
    # Regrouper les données par label et sommer les comptages
    df = df.groupby("label", as_index=False)["n"].sum()
    # Classer les labels selon l'ordre défini
    df["label"] = pd.Categorical(df["label"], categories=ORDER, ordered=True)
    # Trier les résultats par label
    return df.sort_values("label").reset_index(drop=True)

# Fonction pour générer la figure du donut avec les données
def _figure(df: pd.DataFrame) -> go.Figure:
    # Si les données sont vides, afficher un message "Aucune donnée" dans un donut vide
    if df.empty:
        fig = go.Figure(go.Pie(labels=["Aucune donnée"], values=[1], hole=0.6, textinfo="none"))
        fig.update_layout(margin=dict(l=40, r=40, t=20, b=40))
        return fig
    
    # Calcul des pourcentages en normalisant les données à 100%
    total = int(df["n"].sum())
    pct = _normalize_to_100((df["n"] / total * 100.0).tolist())
    # Définir les couleurs à utiliser pour chaque catégorie
    colors = [COLORS[l] for l in df["label"]]
    
    # Création du graphique en donut avec Plotly
    pie = go.Pie(
        labels=df["label"], values=pct, customdata=df["n"].astype(int),
        hole=0.55, sort=False, marker=dict(colors=colors),
        textinfo="label+value", texttemplate="%{label}<br>%{value:.1f}%",
        hovertemplate="<b>%{label}</b><br>%{customdata:,} cas • %{value:.1f}%<extra></extra>",
        showlegend=False,
    )
    fig = go.Figure(pie)
    
    # Ajouter une annotation au centre du donut pour afficher le total des victimes
    fig.add_annotation(x=0.5, y=0.5,
                       text=f"<b>{total:,}</b><br><span style='font-size:12px;color:#6b7280'>victimes</span>",
                       showarrow=False, align="center")
    fig.update_layout(margin=dict(l=40, r=40, t=20, b=40), paper_bgcolor="#fff", plot_bgcolor="#fff")
    return fig

# Fonction qui définit le layout de la page avec le graphique et le dropdown de sélection
def donut_layout(app: dash.Dash) -> html.Div:
    # Création du dropdown pour sélectionner le type d'usager (conducteur, passager, majeur, mineur)
    dropdown = html.Div(
        dcc.Dropdown(
            id="donut-prof",
            options=[
                {"label": "Conducteur", "value": "conducteur"},
                {"label": "Passagers",  "value": "passagers"},
                {"label": "Majeur",     "value": "majeur"},
                {"label": "Mineur",     "value": "mineur"},
            ],
            value="conducteur", clearable=False, searchable=False
        ),
        style={"maxWidth": "520px", "margin": "6px auto 12px auto"},
    )
    
    # Création du graphique donut initial avec les données pour "conducteur"
    graph = dcc.Graph(id="donut-graph",
                      figure=_figure(_read_counts(Path(DB_PATH), "conducteur")),

                      config={"displayModeBar": False}, style={"height": "420px"})
    
    # Conteneur principal pour le dropdown et le graphique
    card = html.Div([dropdown, html.Div(graph, style={"maxWidth": "1100px", "margin": "0 auto"})],
                    style={"background": "white", "border": "1px solid #e5e7eb", "borderRadius": "12px", "padding": "10px"})

    # Callback pour mettre à jour le graphique en fonction de la sélection du dropdown
    @app.callback(Output("donut-graph", "figure"), Input("donut-prof", "value"))
    def _update(v): return _figure(_read_counts(Path(DB_PATH), v))

    return card
