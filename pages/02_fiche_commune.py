import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from streamlit_folium import st_folium

from src import data as D
from src.analyse import analyser_commune
from src.charts import carte_points
from src.ml import VARIABLES_COMMUNES, communes_similaires
from src.ui import SERIES, analyse_box, entete, fmt, kpis, note, pied, setup

setup("Fiche commune", "🏘️")
entete("Fiche commune", "Le profil détaillé de chacune des 140 communes : population, localités, écoles, institutions.")

com, sec, loc, ec, inst = D.communes(), D.sections(), D.localites(), D.ecoles(), D.institutions()

c1, c2 = st.columns(2)
dep = c1.selectbox("Département", sorted(com.departement.unique()),
                   index=sorted(com.departement.unique()).index("Ouest"))
liste = com[com.departement == dep].sort_values("commune")
nom = c2.selectbox("Commune", liste.commune.tolist())
c = com[(com.commune == nom) & (com.departement == dep)].iloc[0]
pc = c.adm2_pcode

st.markdown(f"## {c.commune} <span class='ay-badge'>{pc}</span><span class='ay-badge'>{c.departement}</span>",
            unsafe_allow_html=True)
kpis([
    {"lab": "Population 2022", "val": fmt(c.population), "style": "accent"},
    {"lab": "Densité", "val": fmt(c.densite_hab_km2), "sub": "hab/km²"},
    {"lab": "Superficie", "val": fmt(c.superficie_km2, 1), "sub": "km²"},
    {"lab": "Sections communales", "val": str(int((sec.adm2_pcode == pc).sum()))},
    {"lab": "Localités", "val": str(int(c.nb_localites)), "sub": f"{int(c.nb_villes)} villes · {int(c.nb_quartiers)} quartiers"},
    {"lab": "Établissements (OSM)", "val": str(int(c.nb_etab_education_osm)),
     "sub": f"{int(c.nb_superieur_osm)} supérieurs" + (f" · {int(c.nb_ecoles)} écoles MENFP 2022" if c.couverture_ecoles_2022 else "")},
])

analyse_box("Analyse automatique", analyser_commune(c, com))

st.markdown("### Structure de la population")
g1, g2 = st.columns(2)
with g1:
    cats = ["Filles", "Garçons", "Femmes adultes", "Hommes adultes"]
    vals = [c.filles, c.garcons, c.femmes_adultes, c.hommes_adultes]
    fig = go.Figure()
    fig.add_bar(y=["Enfants", "Adultes"], x=[-c.filles, -c.femmes_adultes], orientation="h", name="Femmes",
                marker=dict(color=SERIES[0], cornerradius=4), customdata=[c.filles, c.femmes_adultes],
                hovertemplate="%{y} – femmes : %{customdata:,.0f}<extra></extra>")
    fig.add_bar(y=["Enfants", "Adultes"], x=[c.garcons, c.hommes_adultes], orientation="h", name="Hommes",
                marker=dict(color=SERIES[1], cornerradius=4),
                hovertemplate="%{y} – hommes : %{x:,.0f}<extra></extra>")
    m = max(vals) * 1.1
    fig.update_layout(barmode="relative", title="Pyramide simplifiée (femmes ◀ ▶ hommes)", height=300,
                      xaxis=dict(range=[-m, m], tickvals=[-m / 1.1, -m / 2.2, 0, m / 2.2, m / 1.1],
                                 ticktext=[fmt(m / 1.1), fmt(m / 2.2), "0", fmt(m / 2.2), fmt(m / 1.1)]),
                      hovermode="closest", bargap=0.35)
    st.plotly_chart(fig, use_container_width=True)
with g2:
    dc = com[com.departement == dep].sort_values("population")
    cols = [SERIES[1] if x == pc else "#b7d3f6" for x in dc.adm2_pcode]
    fig = go.Figure(go.Bar(x=dc.population, y=dc.commune, orientation="h", marker=dict(color=cols, cornerradius=4),
                           hovertemplate="%{y} : %{x:,.0f} hab.<extra></extra>"))
    fig.update_layout(title=f"Position dans le département ({dep})", height=max(300, 22 * len(dc) + 70),
                      hovermode="closest")
    st.plotly_chart(fig, use_container_width=True)

st.markdown("### Carte de la commune")
lc = loc[loc.adm2_pcode == pc].assign(categorie=lambda d: d.type)
ic = inst[(inst.adm2_pcode == pc)]
ic = ic.assign(categorie=ic.categorie.fillna("Autre"))
pts = pd.concat([lc, ic], ignore_index=True)
if not pts.empty:
    geo = D.geojson("communes")
    one = {"type": "FeatureCollection", "features": [f for f in geo["features"] if f["id"] == pc]}
    couleurs = {"Hameau": "#cde2fb", "Village": "#86b6ef", "Lieu-dit": "#9ec5f4", "Quartier": "#6250d6",
                "Ville": "#0d366b", "Grande ville": "#0d366b", "Capitale": "#0d366b"}
    from src.charts import COULEUR_CATEGORIE
    couleurs.update(COULEUR_CATEGORIE)
    m = carte_points(pts, "categorie", ["nom", "type", "sous_type", "section_communale", "precision_localisation"],
                     geo_communes=one, zoom=11, centre=(c.lat, c.lon), cluster=False, couleurs=couleurs)
    st_folium(m, height=520, use_container_width=True, returned_objects=[])

t1, t2, t3, t4 = st.tabs(["Sections communales", "Localités", "Écoles", "Institutions"])
with t1:
    s = sec[sec.adm2_pcode == pc][["adm3_pcode", "section_communale", "superficie_km2", "nb_localites"]]
    st.dataframe(s, hide_index=True, use_container_width=True)
with t2:
    st.dataframe(lc[["nom", "type", "section_communale", "lat", "lon"]].sort_values("type"), hide_index=True,
                 use_container_width=True)
with t3:
    eo = D.etablissements_education_osm()
    eo = eo[eo.adm2_pcode == pc]
    if len(eo):
        st.markdown(f"**OpenStreetMap : {len(eo)} objets** (points GPS)")
        st.dataframe(eo[["nom", "type", "secteur", "section_communale", "lat", "lon"]], hide_index=True, use_container_width=True)
    e = ec[ec.adm2_pcode == pc]
    if len(e):
        st.markdown(f"**Cartographie MENFP 2022 : {len(e)} écoles**")
    if e.empty:
        note("Aucune école dans la cartographie 2022 pour cette commune (zone non couverte). "
             "La mise à jour OpenStreetMap ajoute les écoles géolocalisées.", "warn")
    else:
        st.dataframe(e[["nom", "secteur", "categorie_deduite"]], hide_index=True, use_container_width=True)
with t4:
    st.dataframe(ic[["nom", "categorie", "sous_type", "precision_localisation", "source"]], hide_index=True,
                 use_container_width=True)

st.markdown("### 🤖 Communes les plus semblables")
st.caption("Algorithme des plus proches voisins sur 6 variables standardisées : " + ", ".join(VARIABLES_COMMUNES.values()))
sim = communes_similaires(com, list(VARIABLES_COMMUNES), pc, n=5)
st.dataframe(sim[["commune", "departement", "population", "densite_hab_km2", "part_enfants_pct", "distance"]],
             hide_index=True, use_container_width=True)

# Export
st.markdown("### ⬇️ Exporter la fiche")
fiche = pd.DataFrame({"indicateur": c.index, "valeur": c.values})
rapport = (f"# Fiche commune — {c.commune} ({pc})\n\nDépartement : {c.departement}\n\n## Analyse\n\n"
           + "\n".join(f"- {p}" for p in analyser_commune(c, com)).replace("**", "")
           + "\n\n## Données\n\n| Indicateur | Valeur |\n|---|---|\n"
           + "\n".join(f"| {k} | {v} |" for k, v in zip(fiche.indicateur, fiche.valeur))
           + "\n\nSource : Ayiti Data Hub\n")
e1, e2 = st.columns(2)
e1.download_button("Fiche (CSV)", fiche.to_csv(index=False).encode("utf-8"), f"fiche_{pc}.csv", "text/csv")
e2.download_button("Rapport (Markdown)", rapport.encode("utf-8"), f"rapport_{pc}.md", "text/markdown")

pied("CNIGS, HDX (population 2022), OpenStreetMap, MENFP (écoles 2022).")
