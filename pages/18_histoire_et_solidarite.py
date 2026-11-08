import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from src.medias import galerie
from src.ui import SERIES, analyse_box, entete, kpis, pied, setup
from src.utils import CURATED

setup("Histoire & solidarité", "📜")
entete("Histoire d'Haïti et solidarité avec le monde",
       "Première république noire libre (1804), Haïti a aidé de nombreux peuples à conquérir leur liberté.")

ch = pd.read_csv(CURATED / "histoire_chronologie.csv")
so = pd.read_csv(CURATED / "histoire_solidarite.csv")

kpis([
    {"lab": "Indépendance", "val": "1er janv. 1804", "sub": "première république noire libre", "style": "accent"},
    {"lab": "Peuples aidés", "val": str(len(so)), "sub": "exemples documentés", "style": "accent"},
    {"lab": "Nations libérées avec Bolívar", "val": "6", "sub": "grâce à l'aide de Pétion (1815-1816)"},
    {"lab": "Site UNESCO", "val": "Citadelle", "sub": "Parc national historique (1982)"},
])

t1, t2 = st.tabs(["🌍 Les pays qu'Haïti a aidés", "🕰️ Grandes dates"])
with t1:
    fig = go.Figure()
    hx, hy = -72.3, 18.9
    for r in so.itertuples():
        fig.add_trace(go.Scattergeo(lon=[hx, r.lon], lat=[hy, r.lat], mode="lines",
                                    line=dict(width=1.2, color=SERIES[1]), opacity=0.45, hoverinfo="skip", showlegend=False))
    etiq = ("<b>" + so.pays_court + "</b><br>" + so.fait_court) if "fait_court" in so else so.pays
    pos = so.position_etiquette.fillna("bottom center") if "position_etiquette" in so else "bottom center"
    fig.add_trace(go.Scattergeo(lon=so.lon, lat=so.lat, mode="markers+text", text=etiq, textposition=pos,
                                textfont=dict(size=11, color="#0b0b0b", family="Source Sans 3, Arial"),
                                customdata=so[["pays", "annee", "aide", "comment"]],
                                marker=dict(size=12, color=SERIES[1], line=dict(color="white", width=1.5)),
                                hovertemplate="<b>%{customdata[0]}</b> · %{customdata[1]}<br>%{customdata[2]}<extra></extra>",
                                showlegend=False))
    fig.add_trace(go.Scattergeo(lon=[hx], lat=[hy], mode="markers+text", text=["<b>HAÏTI</b>"], textposition="top center",
                                textfont=dict(size=13, color="#00209F"),
                                marker=dict(size=18, color="#00209F", symbol="star", line=dict(color="white", width=1)),
                                showlegend=False, hoverinfo="skip"))
    fig.update_geos(projection_type="natural earth", showcountries=True, countrycolor="#d6d5d0", showland=True,
                    landcolor="#f3f2ee", showocean=True, oceancolor="#eef4fd", lataxis_range=[-25, 62], lonaxis_range=[-120, 55])
    fig.update_layout(height=640, margin=dict(l=0, r=0, t=0, b=0))
    st.plotly_chart(fig, use_container_width=True, config={"scrollZoom": True})
    st.caption("Chaque point indique le pays aidé, la date et la nature de l'aide ; survolez-le pour le détail, molette pour zoomer.")
    for r in so.sort_values("annee").itertuples():
        with st.container(border=True):
            a, b = st.columns([3, 1])
            a.markdown(f"#### {r.pays} · {r.annee}")
            a.markdown(f"**Comment :** {r.comment}")
            a.markdown(f"**Résultat :** {r.resultat}")
            b.markdown(f"<span class='ay-badge'>{r.aide}</span>", unsafe_allow_html=True)
            b.caption(f"Dirigeant : {r.dirigeant_haitien}")
            b.markdown(f"[Source]({r.url})")
    analyse_box("Un héritage universel", [
        "En 1804, Haïti prouve au monde qu'un peuple réduit en esclavage peut conquérir sa liberté et fonder un État.",
        "Pétion n'a demandé à Bolívar qu'une seule contrepartie à son aide : **l'abolition de l'esclavage**.",
        "La constitution de 1816 fait d'Haïti une **terre d'asile** pour tout Africain ou Indien.",
        "Cette solidarité a été payée cher : isolement diplomatique et « dette de l'indépendance » imposée par la France en 1825.",
    ])
with t2:
    th = st.multiselect("Thèmes", sorted(ch.theme.unique()), placeholder="Tous les thèmes")
    cc = ch[ch.theme.isin(th)] if th else ch
    fig = go.Figure(go.Scatter(x=cc.annee, y=[1] * len(cc), mode="markers", marker=dict(size=14, color=SERIES[0],
                               line=dict(color="white", width=2)), text=cc.evenement, customdata=cc[["date"]],
                               hovertemplate="<b>%{customdata[0]}</b><br>%{text}<extra></extra>"))
    fig.update_layout(height=150, yaxis=dict(visible=False), hovermode="closest", margin=dict(l=10, r=10, t=10, b=10))
    st.plotly_chart(fig, use_container_width=True)
    for r in cc.itertuples():
        st.markdown(f"**{r.date}** <span class='ay-badge'>{r.theme}</span>  \n{r.evenement}", unsafe_allow_html=True)
galerie("Histoire")
pied("Kansas City Defender, Wikipedia (Pétion, Boyer, République d'Haïti 1806-1820), Journal of Inter-American Studies, UNESCO.")
