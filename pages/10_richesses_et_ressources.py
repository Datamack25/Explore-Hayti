import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from src import data as D
from src import territoire as T
from src.charts import MAP_STYLE, fond_haiti, serie_temporelle
from src.composants import cartes_richesses
from src.ui import SERIES, analyse_box, entete, fmt, kpis, note, pied, setup

setup("Richesses & ressources", "💎")
entete("Richesses & ressources d'Haïti",
       "Agriculture d'exception, sous-sol prometteur, mer, patrimoine, culture vivante, diaspora et jeunesse : "
       "les atouts du pays, chiffrés et sourcés.")

r = D.richesses()
kpis([
    {"lab": "Vétiver", "val": "> 2/3", "sub": "de l'huile mondiale", "style": "accent"},
    {"lab": "Potentiel minier", "val": "≈ 20 Md USD", "sub": "or, cuivre, argent (estim. 2012)", "style": "accent"},
    {"lab": "Littoral", "val": "≈ 1 500 km", "sub": f"{len(T.communes_cotieres())} communes côtières"},
    {"lab": "Patrimoine UNESCO", "val": "2", "sub": "Citadelle (1982) · soup joumou (2021)"},
    {"lab": "Diaspora", "val": "4,1 Md USD", "sub": "transferts 2024"},
    {"lab": "Jeunesse", "val": "42 %", "sub": "de moins de 18 ans"},
])

cats = ["Toutes"] + sorted(r.categorie.unique())
c = st.radio("Catégorie", cats, horizontal=True)
rr = r if c == "Toutes" else r[r.categorie == c]
cartes_richesses(rr, n=len(rr))

st.markdown("### 🗺️ Où se trouvent les richesses ?")
rows = []
for x in r.itertuples():
    for com in str(x.communes).split(";") if isinstance(x.communes, str) else []:
        loc = T.localiser_ville(com)
        if loc:
            rows.append({"ressource": x.ressource, "categorie": x.categorie, "commune": com, "lat": loc[0], "lon": loc[1]})
P = pd.DataFrame(rows)
if len(P):
    cats_ = sorted(P.categorie.unique())
    cmap = {k: SERIES[i % 8] for i, k in enumerate(cats_)}
    fig = go.Figure()
    for k in cats_:
        s = P[P.categorie == k]
        fig.add_trace(go.Scattermap(lat=s.lat, lon=s.lon, mode="markers", name=k, text=s.ressource + " — " + s.commune,
                                    marker=dict(size=13, color=cmap[k]), hovertemplate="%{text}<extra></extra>"))
    fond_haiti(fig, D.geojson("communes"))
    fig.update_layout(map=dict(style=MAP_STYLE, zoom=6.8, center=dict(lat=18.95, lon=-72.75)), height=520,
                      margin=dict(l=0, r=0, t=0, b=0), legend=dict(y=0.02, x=0.01, bgcolor="rgba(255,255,255,.85)"))
    st.plotly_chart(fig, use_container_width=True)
    st.caption("Points placés sur la ville principale des communes citées par les sources (localisation indicative).")

st.markdown("### 📊 Ce que disent les séries longues")
a, b = st.columns(2)
for col, code, unite, titre in [(a, "ST.INT.ARVL", "arrivées", "Tourisme international : arrivées"),
                                (b, "BX.TRF.PWKR.CD.DT", "USD", "Transferts de la diaspora")]:
    s = D.serie(code)
    if len(s):
        col.plotly_chart(serie_temporelle(s, titre, unite, evenements=False), use_container_width=True)
a, b = st.columns(2)
for col, code, unite, titre in [(a, "AG.LND.FRST.ZS", "%", "Couverture forestière (% du territoire)"),
                                (b, "NV.AGR.TOTL.ZS", "% PIB", "Agriculture, valeur ajoutée (% du PIB)")]:
    s = D.serie(code)
    if len(s):
        col.plotly_chart(serie_temporelle(s, titre, unite, evenements=False, color=SERIES[5]), use_container_width=True)

cacao = pd.DataFrame({"annee": [2016, 2020, 2022, 2023], "valeur": [9.65, 10.84, 3.23, 4.48]})
fig = px.bar(cacao, x="annee", y="valeur", labels={"annee": "", "valeur": "millions USD"},
             title="Exportations de cacao (BRH, millions USD)")
fig.update_traces(marker_color=SERIES[3], marker_cornerradius=4, text=cacao.valeur, textposition="outside")
fig.update_layout(height=320, hovermode="closest", xaxis=dict(type="category"))
st.plotly_chart(fig, use_container_width=True)

analyse_box("Lecture", [
    "Haïti détient des **niches mondiales** (vétiver, mangue Francisque, cacao fin) qui valorisent l'agriculture paysanne.",
    "Le **sous-sol du Nord** (or, cuivre) représente un potentiel important, encore peu exploité et à encadrer "
    "(environnement, retombées locales).",
    "La **diaspora** est la première source de devises du pays, devant les exportations et l'aide.",
    "Le **patrimoine** (Citadelle, Jacmel, carnaval, peinture, musique) et ~1 500 km de côtes fondent un fort potentiel "
    "touristique, aujourd'hui freiné par la situation sécuritaire.",
])
note("Les montants proviennent de sources datées (indiquées sur chaque carte) ; l'estimation minière de 2012 est un ordre "
     "de grandeur, non une réserve certifiée.", "warn")
pied("BRH, Le Nouvelliste, Premium Beauty News, NBC News, UNESCO, World Atlas, Banque mondiale, HDX.")
