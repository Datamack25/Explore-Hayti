import plotly.express as px
import streamlit as st

from src import data as D
from src.analyse import analyser_departements, analyser_serie
from src.charts import barres_h, serie_temporelle
from src.ui import SEQ_BLEU, SERIES, analyse_box, entete, fmt, kpis, pied, setup

setup("Population & territoire", "👥")
entete("Population & territoire", "Répartition de la population 2022 par département et commune, densité, structure par âge et sexe.")

dep, com = D.departements(), D.communes()
tot = dep.population.sum()
kpis([
    {"lab": "Population 2022", "val": fmt(tot), "style": "accent"},
    {"lab": "Femmes", "val": f"{100 * dep.femmes.sum() / tot:.1f} %"},
    {"lab": "Enfants (< 18 ans)", "val": f"{100 * dep.enfants.sum() / tot:.1f} %"},
    {"lab": "Densité moyenne", "val": fmt(tot / dep.superficie_km2.sum()), "sub": "hab/km²"},
    {"lab": "Commune la plus peuplée", "val": com.loc[com.population.idxmax(), "commune"],
     "sub": fmt(com.population.max()) + " hab."},
])
analyse_box("Ce que disent les données", analyser_departements(dep))

a, b = st.columns(2)
with a:
    fig = px.treemap(com, path=["departement", "commune"], values="population", color="densite_hab_km2",
                     color_continuous_scale=SEQ_BLEU, range_color=(0, 3000),
                     labels={"densite_hab_km2": "hab/km²", "population": "habitants"},
                     title="Où vivent les Haïtiens ? (taille = population, couleur = densité)")
    fig.update_traces(marker=dict(line=dict(color="white", width=2)), hovertemplate="<b>%{label}</b><br>%{value:,.0f} hab.<extra></extra>")
    fig.update_layout(height=520, margin=dict(t=50, l=0, r=0, b=0))
    st.plotly_chart(fig, use_container_width=True)
with b:
    st.plotly_chart(barres_h(dep, "population", "departement", "Population par département (2022)", "hab."),
                    use_container_width=True)
    st.plotly_chart(barres_h(dep, "densite_hab_km2", "departement", "Densité par département", "hab/km²", color=SERIES[2]),
                    use_container_width=True)

st.markdown("### Jeunesse et équilibre femmes-hommes des communes")
focus = st.selectbox("Mettre en évidence un département", sorted(com.departement.unique()),
                     index=sorted(com.departement.unique()).index("Ouest"))
cs = com.assign(groupe=lambda d: d.departement.where(d.departement == focus, "Autres départements"))
cs = cs.sort_values("groupe", key=lambda s: s != "Autres départements")  # le focus est dessiné au-dessus
fig = px.scatter(cs, x="part_enfants_pct", y="ratio_hommes_femmes", size="population", color="groupe",
                 hover_name="commune", hover_data={"departement": True, "groupe": False}, size_max=45,
                 color_discrete_map={focus: SERIES[0], "Autres départements": "#c3c2b7"},
                 labels={"part_enfants_pct": "Part d'enfants (%)", "ratio_hommes_femmes": "Hommes pour 100 femmes",
                         "groupe": ""})
fig.update_traces(marker=dict(line=dict(color="white", width=1.5), opacity=0.85))
fig.add_hline(y=100, line=dict(color="#c3c2b7", dash="dot"))
fig.update_layout(height=520, hovermode="closest")
st.plotly_chart(fig, use_container_width=True)
st.caption("Chaque bulle est une commune (taille = population). Au-dessus de la ligne pointillée : plus d'hommes que de femmes, "
           "typique des zones rurales d'où les femmes migrent vers les villes.")

st.markdown("### Évolution longue (Banque mondiale)")
c1, c2 = st.columns(2)
for col, code, unite in [(c1, "SP.POP.TOTL", "hab."), (c2, "SP.URB.TOTL.IN.ZS", "%")]:
    s = D.serie(code)
    if len(s):
        col.plotly_chart(serie_temporelle(s, s.libelle.iloc[0], unite, evenements=False), use_container_width=True)
        with col:
            analyse_box("Analyse", analyser_serie(s, s.libelle.iloc[0], unite)[:3])

st.markdown("### Tableau des communes")
st.dataframe(com[["adm2_pcode", "commune", "departement", "population", "femmes", "hommes", "enfants", "superficie_km2",
                  "densite_hab_km2", "part_enfants_pct", "ratio_hommes_femmes", "nb_localites"]]
             .sort_values("population", ascending=False), hide_index=True, use_container_width=True, height=420)
pied("HDX/OCHA – statistiques de population 2022 (projections IHSI), CNIGS (superficies), Banque mondiale.")
