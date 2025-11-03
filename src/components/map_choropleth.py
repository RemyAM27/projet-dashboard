from __future__ import annotations
from typing import Dict, List, Tuple
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

# Style carte
MAPBOX_STYLE = "white-bg"
CENTER_FR = {"lat": 46.4, "lon": 2.0}
ZOOM_FR = 4.45

# Couleurs (comme ton ancien projet)
BASE_COLOR_MAP: Dict[str, str] = {
    "Très faible": "#e9f7ef",
    "Faible":      "#b9e4c9",
    "Moyen":       "#ffe29a",
    "Élevé":       "#ffb870",
    "Très élevé":  "#d13a34",
    "Exceptionnel":"#6a1b9a",
    "_DIM_":       "#eceff1",
}
CLASS_CODE_ORDER = ["tf","fa","mo","el","te","ex"]
CODE_TO_KEY = {"tf":"Très faible","fa":"Faible","mo":"Moyen","el":"Élevé","te":"Très élevé","ex":"Exceptionnel"}

def _round10(x: float) -> int:
    try:
        return int(round(float(x) / 10.0) * 10)
    except Exception:
        return int(x)

def _monotonic_rounds(vals):
    r = [_round10(v) for v in vals]
    for i in range(1, len(r)):
        if r[i] <= r[i-1]:
            r[i] = r[i-1] + 10
    return r

def prepare_dep_classes(df: pd.DataFrame) -> Tuple[pd.DataFrame, Tuple[int,int,int,int]]:
    """
    Agrège par département en comptant les ACCIDENTS DISTINCTS (nunique Num_Acc),
    calcule les quantiles 20/40/60/80 (arrondis, monotones) pour les classes,
    renvoie (depc, (b1,b2,b3,b4)).
    """
    dep = df.dropna(subset=["dep", "Num_Acc"]).copy()
    depc = (dep.groupby("dep", as_index=False)
              .agg(accidents=("Num_Acc","nunique")))
    depc["rank"] = depc["accidents"].rank(ascending=False, method="min").astype(int)
    total = depc["accidents"].sum()
    depc["share"] = depc["accidents"] / total * 100.0

    base_df = depc.copy()
    exc = base_df["accidents"] > 10_000
    exc_df, base_df = base_df[exc].copy(), base_df[~exc].copy()

    if not base_df.empty:
        q1, q2, q3, q4 = base_df["accidents"].quantile([0.2,0.4,0.6,0.8]).tolist()
        b1, b2, b3, b4 = _monotonic_rounds([q1, q2, q3, q4])
        def lab(v):
            if v<=b1: return "Très faible"
            if v<=b2: return "Faible"
            if v<=b3: return "Moyen"
            if v<=b4: return "Élevé"
            return "Très élevé"
        base_df["classe"] = base_df["accidents"].apply(lab)
    else:
        b1=b2=b3=b4=0
        base_df["classe"] = []

    if not exc_df.empty:
        exc_df["classe"] = "Exceptionnel"

    depc = pd.concat([base_df, exc_df], ignore_index=True)
    depc["classe_code"]  = depc["classe"].map({
        "Très faible":"tf","Faible":"fa","Moyen":"mo","Élevé":"el","Très élevé":"te","Exceptionnel":"ex"
    }).fillna("na")
    depc["classe_label"] = depc["classe"]
    return depc, (b1,b2,b3,b4)

def build_map_figure(
    depc: pd.DataFrame,
    geojson: dict,
    *,
    selected_codes: List[str] | None = None,
) -> go.Figure:
    """Construit la figure mapbox avec catégories discrètes + contours nets."""
    sel = set(map(str, (selected_codes or CLASS_CODE_ORDER)))
    def _code_to_key(c): return CODE_TO_KEY.get(c, c)
    data = depc.copy()
    data["visible_label"] = data["classe_code"].apply(lambda c: _code_to_key(c) if str(c) in sel else "_DIM_")

    color_map = {**BASE_COLOR_MAP}
    color_map.setdefault("_DIM_", BASE_COLOR_MAP["_DIM_"])
    order_labels = [CODE_TO_KEY[c] for c in CLASS_CODE_ORDER] + ["_DIM_"]

    fig = px.choropleth_mapbox(
        data,
        geojson=geojson,
        locations="dep",
        featureidkey="properties.code",
        color="visible_label",
        category_orders={"visible_label": order_labels},
        color_discrete_map=color_map,
        custom_data=["dep","accidents","rank","share","classe_label","classe_code","visible_label"],
        mapbox_style=MAPBOX_STYLE,
        zoom=ZOOM_FR,
        center=CENTER_FR,
        opacity=1.0,
    )
    fig.update_traces(
        marker_line_width=1.0,
        marker_line_color="rgba(32,33,36,0.95)",
        hovertemplate="%{customdata[4]} — %{location}<br>%{customdata[1]:,} accidents<extra></extra>",
        selector=dict(type="choroplethmapbox")
    )
    fig.update_layout(
        margin=dict(l=0, r=0, t=10, b=0),
        showlegend=False,
        mapbox=dict(style=MAPBOX_STYLE, zoom=ZOOM_FR, center=CENTER_FR),
        paper_bgcolor="#fff", plot_bgcolor="#fff"
    )
    return fig
