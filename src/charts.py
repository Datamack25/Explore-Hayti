"""Graphiques réutilisables : choroplèthes Plotly, cartes Leaflet (Folium), séries temporelles."""
from __future__ import annotations

import folium
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from folium.plugins import Fullscreen, MarkerCluster

from src.indicateurs import EVENEMENTS
from src.ui import GRID, INK2, MUTED, SEQ_BLEU, SERIES

import os
MAP_STYLE = os.environ.get("AYITI_MAP_STYLE", "carto-positron")  # « white-bg » = sans fond de carte (hors ligne)
CENTRE_HAITI = {"lat": 18.95, "lon": -72.75}

COULEUR_CATEGORIE = {
    "Université / Enseignement supérieur": SERIES[0],
    "Santé": SERIES[7],
    "Administration locale": SERIES[2],
    "Administration de l'État": SERIES[6],
    "École": SERIES[1],
    "Sécurité & justice": SERIES[3],
    "Finance": SERIES[5],
    "Culture & services": SERIES[4],
}


def choropleth(df: pd.DataFrame, geo: dict, col: str, label: str, key: str = "adm2_pcode",
               nom: str = "commune", scale: list[str] | None = None, hover: list[str] | None = None,
               height: int = 560, diverging_mid: float | None = None) -> go.Figure:
    """Carte choroplèthe (fond de carte clair, rampe séquentielle à une teinte)."""
    hd = {c: True for c in (hover or [])}
    hd[key] = False
    fig = px.choropleth_map(
        df, geojson=geo, locations=key, featureidkey="id", color=col,
        color_continuous_scale=scale or SEQ_BLEU, hover_name=nom, hover_data=hd,
        labels={col: label}, map_style=MAP_STYLE, zoom=6.9, center=CENTRE_HAITI, opacity=0.85,
        color_continuous_midpoint=diverging_mid,
    )
    fig.update_traces(marker_line_width=0.6, marker_line_color="white")
    fig.update_layout(height=height, margin=dict(l=0, r=0, t=0, b=0),
                      coloraxis_colorbar=dict(title=dict(text=label, side="right"), thickness=12, len=0.75))
    return fig


def carte_points(points: pd.DataFrame, couleur_col: str = "categorie", popup_cols: list[str] | None = None,
                 geo_communes: dict | None = None, zoom: int = 8, cluster: bool = True,
                 centre: tuple[float, float] | None = None, couleurs: dict | None = None) -> folium.Map:
    """Carte Leaflet interactive avec regroupement des marqueurs (gère des milliers de points)."""
    c = centre or (CENTRE_HAITI["lat"], CENTRE_HAITI["lon"])
    m = folium.Map(location=c, zoom_start=zoom, tiles=None, control_scale=True)
    folium.TileLayer("https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png", name="Fond clair",
                     attr="© OpenStreetMap contributors © CARTO", subdomains="abcd", max_zoom=19).add_to(m)
    folium.TileLayer("OpenStreetMap", name="OpenStreetMap").add_to(m)
    Fullscreen(position="topright").add_to(m)
    if geo_communes:
        folium.GeoJson(geo_communes, name="Communes",
                       style_function=lambda f: {"color": "#6d6c68", "weight": 0.6, "fillOpacity": 0.02},
                       tooltip=folium.GeoJsonTooltip(fields=["commune", "departement"],
                                                     aliases=["Commune", "Département"])).add_to(m)
    couleurs = couleurs or COULEUR_CATEGORIE
    groupes: dict[str, folium.FeatureGroup] = {}
    pts = points.dropna(subset=["lat", "lon"])
    for cat, sub in pts.groupby(couleur_col):
        fg = folium.FeatureGroup(name=f"{cat} ({len(sub)})")
        target = MarkerCluster(disableClusteringAtZoom=13).add_to(fg) if cluster and len(sub) > 40 else fg
        col = couleurs.get(cat, SERIES[len(groupes) % len(SERIES)])
        for r in sub.itertuples():
            html = "<br>".join(f"<b>{k}</b> : {getattr(r, k)}" for k in (popup_cols or []) if pd.notna(getattr(r, k, None)))
            folium.CircleMarker([r.lat, r.lon], radius=6, color="white", weight=1.5, fill=True,
                                fill_color=col, fill_opacity=0.9,
                                tooltip=str(getattr(r, "nom", cat)),
                                popup=folium.Popup(html, max_width=320) if html else None).add_to(target)
        fg.add_to(m)
        groupes[cat] = fg
    folium.LayerControl(collapsed=False).add_to(m)
    return m


def serie_temporelle(df: pd.DataFrame, titre: str, unite: str = "", evenements: bool = True,
                     actuels: pd.DataFrame | None = None, color: str = SERIES[0]) -> go.Figure:
    """Ligne avec événements historiques annotés et, en option, points « données actuelles »."""
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=df.annee, y=df.valeur, mode="lines", name="Banque mondiale",
                             line=dict(color=color, width=2),
                             hovertemplate="%{x} : %{y:,.2f} " + unite + "<extra></extra>"))
    if actuels is not None and not actuels.empty:
        fig.add_trace(go.Scatter(x=actuels.annee, y=actuels.valeur, mode="markers+lines", name="Données récentes / FMI",
                                 line=dict(color=SERIES[1], width=2, dash="dot"),
                                 marker=dict(size=9, color=SERIES[1], line=dict(color="white", width=2)),
                                 hovertemplate="%{x} : %{y:,.2f} " + unite + "<extra>récent</extra>"))
    if evenements and not df.empty:
        y0, y1 = df.annee.min(), df.annee.max()
        for an, lab in EVENEMENTS:
            if y0 <= an <= y1:
                fig.add_vline(x=an, line=dict(color=GRID, width=1, dash="dot"))
                fig.add_annotation(x=an, y=1.0, yref="paper", text=lab, showarrow=False, textangle=-90,
                                   xanchor="right", yanchor="top", font=dict(size=10, color=MUTED))
    fig.update_layout(title=titre, height=430, yaxis_title=unite, showlegend=actuels is not None and not actuels.empty)
    return fig


def barres_h(df: pd.DataFrame, x: str, y: str, titre: str, unite: str = "", color: str = SERIES[0],
             height: int | None = None, highlight: str | None = None) -> go.Figure:
    d = df.sort_values(x)
    cols = [SERIES[1] if (highlight and v == highlight) else color for v in d[y]]
    fig = go.Figure(go.Bar(x=d[x], y=d[y], orientation="h", marker=dict(color=cols, cornerradius=4),
                           hovertemplate="%{y} : %{x:,.1f} " + unite + "<extra></extra>"))
    fig.update_layout(title=titre, height=height or max(320, 26 * len(d) + 80), hovermode="closest",
                      xaxis=dict(showgrid=True, gridcolor=GRID), yaxis=dict(showgrid=False), bargap=0.25)
    return fig


def style_axes(fig: go.Figure) -> go.Figure:
    fig.update_xaxes(tickfont=dict(color=INK2))
    fig.update_yaxes(tickfont=dict(color=INK2))
    return fig


def graphique_developpement(ind: pd.DataFrame, hauteur: int = 400, dims_visibles: bool = True) -> go.Figure:
    """Indice composite de développement : une ligne épaisse (global) + les 6 dimensions en fin."""
    from src.developpement import COULEURS_DIM, DIMENSIONS
    fig = go.Figure()
    if dims_visibles:
        for d in DIMENSIONS:
            if d in ind:
                fig.add_trace(go.Scatter(x=ind.annee, y=ind[d], name=d, mode="lines",
                                         line=dict(color=COULEURS_DIM[d], width=1.5), opacity=0.75,
                                         hovertemplate=d + " : %{y:.0f}<extra></extra>"))
    fig.add_trace(go.Scatter(x=ind.annee, y=ind["Indice global"], name="Indice global", mode="lines+markers",
                             line=dict(color="#0b0b0b", width=3), marker=dict(size=5),
                             hovertemplate="Indice global : %{y:.0f}/100<extra></extra>"))
    for an, lab in EVENEMENTS:
        if ind.annee.min() <= an <= ind.annee.max():
            fig.add_vline(x=an, line=dict(color=GRID, width=1, dash="dot"))
    fig.add_hrect(y0=0, y1=33, fillcolor="#d03b3b", opacity=0.04, line_width=0)
    fig.add_hrect(y0=66, y1=100, fillcolor="#0ca30c", opacity=0.05, line_width=0)
    fig.update_layout(height=hauteur, yaxis=dict(range=[0, 102], title="0 = pire année · 100 = meilleure année"),
                      legend=dict(orientation="h", y=-0.22), margin=dict(l=10, r=10, t=30, b=10))
    return fig


def carte_haiti(com: pd.DataFrame, geo: dict, points: pd.DataFrame | None = None, col: str = "population",
                hauteur: int = 560) -> go.Figure:
    """Carte d'accueil : communes (choroplèthe discrète) + points d'intérêt."""
    import numpy as np
    d = com.copy()
    d["_v"] = np.log10(d[col].clip(lower=1))
    fig = px.choropleth_map(d, geojson=geo, locations="adm2_pcode", featureidkey="id", color="_v",
                            color_continuous_scale=["#eef4fd", "#b7d3f6", "#6da7ec", "#2a78d6", "#184f95"],
                            hover_name="commune", hover_data={"_v": False, "adm2_pcode": False, "departement": True,
                                                              col: ":,.0f"},
                            map_style=MAP_STYLE, zoom=6.85, center=CENTRE_HAITI, opacity=0.7)
    fig.update_traces(marker_line_width=0.5, marker_line_color="white")
    fig.update_coloraxes(showscale=False)
    if points is not None and len(points):
        for i, (cat, sub) in enumerate(points.groupby("categorie")):
            fig.add_trace(go.Scattermap(lat=sub.lat, lon=sub.lon, mode="markers", name=cat,
                                        marker=dict(size=11, color=COULEUR_POI.get(cat, SERIES[i % 8])),
                                        text=sub.nom, customdata=sub[["commune"]].fillna(""),
                                        hovertemplate="<b>%{text}</b><br>%{customdata[0]}<extra>" + cat + "</extra>"))
    fig.update_layout(height=hauteur, margin=dict(l=0, r=0, t=0, b=0),
                      legend=dict(orientation="h", y=0.01, x=0.01, bgcolor="rgba(255,255,255,0.85)", font=dict(size=11)))
    return fig


COULEUR_POI = {"Tourisme & patrimoine": SERIES[1], "Aéroports": SERIES[6], "Universités publiques": SERIES[2],
               "Hôpitaux de référence": SERIES[7], "Îles": SERIES[0], "Ports": SERIES[3],
               "Écoles & universités (OSM)": SERIES[4]}


def fond_haiti(fig: go.Figure, geo: dict) -> go.Figure:
    """Ajoute le contour clair des communes sous une carte à points (lisible même sans fond de carte)."""
    ids = [f["id"] for f in geo["features"]]
    fig.add_trace(go.Choroplethmap(geojson=geo, locations=ids, z=[0] * len(ids), featureidkey="id", showscale=False,
                                   colorscale=[[0, "#eef1f6"], [1, "#eef1f6"]], marker_opacity=0.6,
                                   marker_line_color="#c9ccd3", marker_line_width=0.5, hoverinfo="skip",
                                   showlegend=False))
    # le fond passe en premier plan de dessin (sous les autres couches)
    fig.data = (fig.data[-1],) + fig.data[:-1]
    return fig
