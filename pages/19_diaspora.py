import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from src import data as D
from src.charts import barres_h, serie_temporelle
from src.medias import galerie
from src.ui import SERIES, analyse_box, entete, fmt, kpis, note, pied, setup
from src.utils import CURATED

setup("Diaspora", "🌍")
entete("La diaspora haïtienne dans le monde", "Où vivent les Haïtiens de l'étranger, que font-ils, et ce qu'ils apportent au pays.")

pa = pd.read_csv(CURATED / "diaspora_pays.csv")
vi = pd.read_csv(CURATED / "diaspora_villes.csv")
em = pd.read_csv(CURATED / "diaspora_emploi_usa.csv")
tot = pa.personnes.sum()
kpis([
    {"lab": "Diaspora estimée", "val": "1,5 à 3 M", "sub": f"somme des estimations par pays : {fmt(tot)}", "style": "accent"},
    {"lab": "1er pays d'accueil", "val": "États-Unis", "sub": f"{fmt(pa.personnes.max())} (ascendance)"},
    {"lab": "Pays recensés", "val": str(len(pa))},
    {"lab": "Transferts 2024", "val": "4,1 Md USD", "sub": "≈ 16-19 % du PIB", "style": "accent"},
])
note("Les chiffres mélangent des définitions différentes (personnes nées en Haïti, ascendance déclarée, estimations "
     "communautaires) et des années différentes : ils donnent des ordres de grandeur, non un total exact.", "warn")

st.markdown("### 🗺️ Où vit la diaspora")
niveau = st.radio("Afficher", ["Pays", "Grandes villes"], horizontal=True)
fig = go.Figure()
if niveau == "Pays":
    taille = 8 + 40 * np.sqrt(pa.personnes / pa.personnes.max())
    fig.add_trace(go.Scattergeo(lon=pa.lon, lat=pa.lat, text=pa.pays, mode="markers",
                                marker=dict(size=taille, color=SERIES[0], opacity=0.75, line=dict(color="white", width=1.5)),
                                customdata=np.stack([pa.personnes.map(fmt), pa.nature, pa.annee.astype(str)], axis=1),
                                hovertemplate="<b>%{text}</b><br>%{customdata[0]} personnes<br>%{customdata[1]} (%{customdata[2]})<extra></extra>"))
else:
    v = vi.copy()
    v["taille"] = np.where(v.personnes.notna(), 8 + 34 * np.sqrt(v.personnes.fillna(0) / v.personnes.max()), 9)
    fig.add_trace(go.Scattergeo(lon=v.lon, lat=v.lat, text=v.ville, mode="markers",
                                marker=dict(size=v.taille, color=SERIES[1], opacity=0.8, line=dict(color="white", width=1.5)),
                                customdata=np.stack([v.personnes.map(lambda x: fmt(x) if x == x else "n.c."), v.pays, v.nature.fillna("")], axis=1),
                                hovertemplate="<b>%{text}</b> (%{customdata[1]})<br>%{customdata[0]} – %{customdata[2]}<extra></extra>"))
if niveau == "Pays":
    POS = {"États-Unis": "middle right", "République dominicaine": "middle right", "Cuba": "middle left",
           "Bahamas": "top left", "France (outre-mer)": "bottom right", "Mexique": "middle left", "Canada": "top center",
           "Brésil": "middle right", "Chili": "middle right", "France (métropole)": "middle left",
           "Guyana": "bottom right", "Venezuela": "bottom left"}
    e = pa[pa.pays.isin(POS)]
    fig.add_trace(go.Scattergeo(lon=e.lon, lat=e.lat, mode="text", textposition=[POS[x] for x in e.pays],
                                text=["  <b>" + n + "</b> " + fmt(v) + "  " for n, v in zip(e.pays.str.replace("République dominicaine", "Rép. dominicaine"), e.personnes)],
                                textfont=dict(size=11, color="#0b0b0b"), hoverinfo="skip"))
else:
    POSV = {"Miami (aire métropolitaine)": "middle left", "New York (aire métropolitaine)": "middle right",
            "Boston (aire métropolitaine)": "top right", "Grand Montréal": "top left", "Orlando (aire métropolitaine)": "bottom left",
            "Atlanta (aire métropolitaine)": "middle left"}
    e = vi[vi.ville.isin(POSV)]
    fig.add_trace(go.Scattergeo(lon=e.lon, lat=e.lat, mode="text", textposition=[POSV[x] for x in e.ville],
                                text=["  <b>" + n.split(" (")[0] + "</b> " + fmt(v) + "  " for n, v in zip(e.ville, e.personnes)],
                                textfont=dict(size=11, color="#0b0b0b"), hoverinfo="skip"))
fig.add_trace(go.Scattergeo(lon=[-72.3], lat=[18.9], text=["Haïti"], mode="markers+text", textposition="bottom center",
                            marker=dict(size=14, color="#D21034", symbol="star"), textfont=dict(color="#D21034", size=12), hoverinfo="text"))
fig.update_geos(projection_type="natural earth", showcountries=True, countrycolor="#d6d5d0", showland=True,
                landcolor="#f3f2ee", showocean=True, oceancolor="#eef4fd", lataxis_range=[-45, 60], lonaxis_range=[-125, 25])
fig.update_layout(height=520, margin=dict(l=0, r=0, t=0, b=0), showlegend=False)
st.plotly_chart(fig, use_container_width=True)

a, b = st.columns(2)
with a:
    st.plotly_chart(barres_h(pa.head(12), "personnes", "pays", "Principaux pays d'accueil", "personnes"), use_container_width=True)
with b:
    vv = vi.dropna(subset=["personnes"])
    st.plotly_chart(barres_h(vv, "personnes", "ville", "Grandes communautés urbaines", "personnes", color=SERIES[1]),
                    use_container_width=True)

st.markdown("### 💼 Que font les Haïtiens des États-Unis ? (2024)")
occ = em[em.unite == "% des actifs occupés"]
c1, c2 = st.columns([3, 2])
with c1:
    st.plotly_chart(barres_h(occ, "valeur", "indicateur", "Répartition des actifs occupés par grands métiers", "%",
                             color=SERIES[2]), use_container_width=True)
    st.caption("Les catégories se recoupent partiellement (la santé inclut des métiers de service et des métiers qualifiés).")
with c2:
    autres = em[em.unite != "% des actifs occupés"]
    st.dataframe(autres[["indicateur", "valeur", "unite", "annee"]], hide_index=True, use_container_width=True)
analyse_box("Ce qu'apporte la diaspora", [
    "Près d'**un actif haïtien sur cinq aux États-Unis travaille dans la santé** (aides-soignants, infirmiers, techniciens) : "
    "la diaspora est un pilier des hôpitaux et maisons de retraite de Floride, New York et Boston.",
    "**70 %** des Haïtiens des États-Unis sont actifs, plus que la moyenne des immigrés (68 %) et des natifs (63 %).",
    "Les **transferts** (4,5 milliards USD depuis les États-Unis en 2024, 4,1 Md USD au total selon la BRH) sont la première "
    "source de devises d'Haïti.",
    "Au-delà de l'argent : investissements, entreprises, médecins et enseignants en mission, artistes et sportifs (dont de "
    "nombreux Grenadiers nés à l'étranger).",
])
s = D.serie("BX.TRF.PWKR.CD.DT")
if len(s):
    st.plotly_chart(serie_temporelle(s, "Transferts de fonds reçus par Haïti (Banque mondiale)", "USD", evenements=True),
                    use_container_width=True)
st.dataframe(pa[["pays", "personnes", "annee", "nature", "source", "url"]], hide_index=True, use_container_width=True,
             column_config={"url": st.column_config.LinkColumn("lien")})
galerie("Diaspora")
pied("Wikipedia (Haitians, Haitian diaspora), Migration Policy Institute (2024), BRH, Banque mondiale.")
