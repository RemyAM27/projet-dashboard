from __future__ import annotations
from typing import Dict, List, Tuple
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

# Style de la carte (utilisé pour Mapbox)
MAPBOX_STYLE = "white-bg"
CENTER_FR = {"lat": 46.4, "lon": 2.0}  # Centre de la carte sur la France
ZOOM_FR = 4.45  # Zoom initial pour la carte de la France

# Carte de couleurs de base pour les différentes catégories d'intensité d'accidents
BASE_COLOR_MAP: Dict[str, str] = {
    "Très faible": "#e9f7ef",
    "Faible":      "#b9e4c9",
    "Moyen":       "#ffe29a",
    "Élevé":       "#ffb870",
    "Très élevé":  "#d13a34",
    "_DIM_":       "#eceff1",  # Couleur pour les départements non sélectionnés
}

# Ordre des catégories pour l'affichage
CLASS_CODE_ORDER = ["tf", "fa", "mo", "el", "te"]
# Mapping des codes aux labels de catégories
CODE_TO_KEY = {
    "tf": "Très faible",
    "fa": "Faible",
    "mo": "Moyen",
    "el": "Élevé",
    "te": "Très élevé",
}

# Fonction pour arrondir les valeurs aux multiples de 10
def _round10(x: float) -> int:
    try:
        return int(round(float(x) / 10.0) * 10)  # Arrondir à 10 près
    except Exception:
        return int(x)

# Fonction pour arrondir de manière monotone, pour éviter que les valeurs suivantes soient plus petites que les précédentes
def _monotonic_rounds(vals):
    r = [_round10(v) for v in vals]
    for i in range(1, len(r)):
        if r[i] <= r[i - 1]:
            r[i] = r[i - 1] + 10  # S'assurer que les valeurs restent croissantes
    return r

# Fonction pour normaliser les codes des départements (gestion des codes comme 201/202 -> 2A/2B)
def _normalize_dep_series(s: pd.Series) -> pd.Series:
    s = s.astype(str).str.strip().str.upper()  # Convertir en majuscules et enlever les espaces
    s = s.replace({"201": "2A", "202": "2B"})  # Remplacer 201 par 2A et 202 par 2B
    s = s.where(s.isin(["2A", "2B"]), s.str.zfill(2))  # Ajouter des zéros devant les départements
    return s

# Fonction pour préparer les classes des départements en fonction du nombre d'accidents
def prepare_dep_classes(df: pd.DataFrame) -> Tuple[pd.DataFrame, Tuple[int, int, int, int]]:
    dep = df.dropna(subset=["dep", "Num_Acc"]).copy()  # Enlever les lignes avec des valeurs manquantes
    dep["dep"] = _normalize_dep_series(dep["dep"])  # Normaliser les codes des départements

    # Compter le nombre d'accidents par département
    depc = (
        dep.groupby("dep", as_index=False)
        .agg(accidents=("Num_Acc", "nunique"))
    )

    depc["rank"] = depc["accidents"].rank(ascending=False, method="min").astype(int)  # Classement des départements
    total = depc["accidents"].sum()  # Total des accidents
    depc["share"] = (depc["accidents"] / total * 100.0).round(1)  # Part de chaque département dans le total

    # Définir les seuils de gravité pour les départements
    if not depc.empty and depc["accidents"].nunique() > 1:
        q1, q2, q3, q4 = depc["accidents"].quantile([0.2, 0.4, 0.6, 0.8]).tolist()  # Quantiles des accidents
        b1, b2, b3, b4 = _monotonic_rounds([q1, q2, q3, q4])  # Arrondir les quantiles de manière monotone

        def lab(v: float) -> str:
            """Retourner la catégorie de gravité en fonction du nombre d'accidents"""
            if v <= b1: return "Très faible"
            if v <= b2: return "Faible"
            if v <= b3: return "Moyen"
            if v <= b4: return "Élevé"
            return "Très élevé"

        depc["classe"] = depc["accidents"].apply(lab)  # Appliquer la classification sur le nombre d'accidents
    else:
        b1 = b2 = b3 = b4 = int(depc["accidents"].max()) if not depc.empty else 0  # Cas où il n'y a qu'une seule valeur
        depc["classe"] = "Moyen"  # Si les données sont trop homogènes, on les classe comme "Moyen"

    # Mapper les labels de classes aux codes de couleurs
    depc["classe_code"] = depc["classe"].map({
        "Très faible": "tf",
        "Faible":      "fa",
        "Moyen":       "mo",
        "Élevé":       "el",
        "Très élevé":  "te",
    }).fillna("tf")  # Remplacer les valeurs manquantes par "Très faible"
    depc["classe_label"] = depc["classe"]

    return depc, (b1, b2, b3, b4)

# Fonction pour construire la figure de la carte choroplèthe
def build_map_figure(
    depc: pd.DataFrame,
    geojson: dict,
    *,
    selected_codes: List[str] | None = None,
) -> go.Figure:
    """
    Crée une carte choroplèthe interactive avec Plotly.
    Utilise les données des départements et les codes sélectionnés.
    """
    allowed = {
        str(f["properties"].get("code", "")).strip().upper()
        for f in geojson.get("features", [])
    }  # Récupérer les codes des départements autorisés à partir du GeoJSON

    data = depc.copy()  # Copier les données des départements
    data = data[data["dep"].isin(allowed)].copy()  # Filtrer les départements autorisés

    # Déterminer les codes sélectionnés
    if selected_codes is None:
        sel = set(CLASS_CODE_ORDER)  # Si aucun code n'est sélectionné, prendre tous les codes
    else:
        sel = set(map(str, selected_codes))  # Sinon, prendre les codes sélectionnés

    # Fonction pour récupérer le label à partir du code
    def _code_to_key(c: str) -> str:
        return CODE_TO_KEY.get(c, c)

    # Ajouter une colonne "visible_label" pour déterminer la visibilité des départements sur la carte
    data["visible_label"] = data["classe_code"].apply(
        lambda c: _code_to_key(c) if str(c) in sel else "_DIM_"  # Si le département est sélectionné, le rendre visible
    )

    # Créer la carte choroplèthe avec Plotly Express
    color_map = {**BASE_COLOR_MAP}
    color_map.setdefault("_DIM_", BASE_COLOR_MAP["_DIM_"])  # Couleur par défaut pour les départements non sélectionnés
    order_labels = [CODE_TO_KEY[c] for c in CLASS_CODE_ORDER] + ["_DIM_"]  # Ordre des labels

    fig = px.choropleth_mapbox(
        data,
        geojson=geojson,
        locations="dep",
        featureidkey="properties.code",  # Clé du GeoJSON pour identifier les départements
        color="visible_label",  # Utiliser la visibilité des labels pour colorier les départements
        category_orders={"visible_label": order_labels},  # Ordre des catégories
        color_discrete_map=color_map,  # Mapper les couleurs aux catégories
        custom_data=["dep", "accidents", "rank", "share", "classe_label", "classe_code", "visible_label"],
        mapbox_style=MAPBOX_STYLE,
        zoom=ZOOM_FR,
        center=CENTER_FR,
        opacity=1.0,
    )

    # Mise en forme du graphique
    fig.update_traces(
        marker_line_width=1.0,
        marker_line_color="rgba(32,33,36,0.95)",  # Bordure des départements
        hovertemplate=(  # Formatage de l'affichage lors du survol
            "%{customdata[4]} — %{location}<br>"
            "%{customdata[1]:,} accidents"
            "<extra></extra>"
        ),
        selector=dict(type="choroplethmapbox"),
    )

    # Mise à jour du layout du graphique
    fig.update_layout(
        margin=dict(l=0, r=0, t=10, b=0),
        showlegend=False,
        mapbox=dict(style=MAPBOX_STYLE, zoom=ZOOM_FR, center=CENTER_FR),
        paper_bgcolor="#fff",
        plot_bgcolor="#fff",
    )
    return fig
