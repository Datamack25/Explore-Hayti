import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from src import data as D
from src import territoire as T
from src.charts import MAP_STYLE, fond_haiti, barres_h, choropleth
from src.ui import SERIES, analyse_box, entete, note, pied, setup

setup("Bien vivre & tourisme", "🌴")
entete("Où il fait bon vivre et que visiter",
       "Un indice « cadre de vie » par commune et les plus beaux sites du pays : plages, montagnes, cascades, patrimoine.")

t1, t2 = st.tabs(["🏡 Cadre de vie par commune", "🏝️ Sites à découvrir"])

with t1:
    st.markdown("L'indice combine **cinq composantes** que vous pouvez pondérer. Il compare les communes entre elles "
                "(0-100) à partir des données disponibles.")
    c = st.columns(5)
    p = {"services": c[0].slider("Services (universités, hôpitaux, écoles)", 0.0, 3.0, 1.0, 0.5),
         "accessibilite": c[1].slider("Accessibilité (aéroport, chef-lieu)", 0.0, 3.0, 1.0, 0.5),
         "nature": c[2].slider("Nature (mer, sites)", 0.0, 3.0, 1.0, 0.5),
         "confort": c[3].slider("Densité équilibrée", 0.0, 3.0, 1.0, 0.5),
         "dynamisme": c[4].slider("Vie urbaine", 0.0, 3.0, 0.7, 0.5)}
    p = {k: v for k, v in p.items() if v > 0}
    if p:
        cv = T.indice_cadre_de_vie(p)
        a, b = st.columns([3, 2])
        with a:
            st.plotly_chart(choropleth(cv, D.geojson("communes"), "indice_cadre_de_vie", "Cadre de vie (0-100)",
                                       hover=["departement", "rang", "littoral"],
                                       scale=["#e8f6e8", "#a8dca8", "#5fbf6a", "#1baf7a", "#0a7a52", "#05543a"]),
                            use_container_width=True)
        with b:
            top = cv.nsmallest(15, "rang")
            st.plotly_chart(barres_h(top, "indice_cadre_de_vie", "commune", "15 communes les mieux placées", "/100",
                                     color=SERIES[2]), use_container_width=True)
        dep = cv.groupby("departement").indice_cadre_de_vie.mean().sort_values(ascending=False).round(1)
        analyse_box("Lecture", [
            f"Les communes les mieux placées : **{', '.join(top.commune.head(5))}** — souvent des villes côtières "
            "dotées d'universités publiques, d'un hôpital de référence et d'un aéroport.",
            f"Département au meilleur score moyen : **{dep.index[0]}** ({dep.iloc[0]}/100).",
            "Les communes de montagne fraîches (Kenscoff, Furcy) et les petites villes côtières (Port-Salut, Abricots, "
            "Côteaux) offrent une grande qualité de vie naturelle même avec moins de services.",
        ])
        note("⚠️ La sécurité n'entre pas dans l'indice faute de données communales fiables et à jour. Avant tout déplacement "
             "ou installation, consultez les avis officiels (lien dans « Pour aller plus loin » sur l'accueil).", "warn")
        st.dataframe(cv.sort_values("rang")[["rang", "commune", "departement", "indice_cadre_de_vie", "littoral",
                                             "sites_touristiques", "universites", "hopitaux_ref", "km_aeroport",
                                             "km_chef_lieu", "densite_hab_km2", "population"]],
                     hide_index=True, use_container_width=True, height=380)
        st.download_button("⬇️ Indice cadre de vie (CSV)", cv[["adm2_pcode", "commune", "departement", "indice_cadre_de_vie",
                                                               "rang"]].to_csv(index=False).encode("utf-8"), "cadre_de_vie.csv")

with t2:
    s = T.sites_touristiques()
    types = sorted(s.type.unique())
    sel = st.multiselect("Type de site", types, placeholder="Tous les types")
    ss = s[s.type.isin(sel)] if sel else s
    groupes = {"Plage": "Plages & îles", "Île & plage": "Plages & îles", "Plage & stations": "Plages & îles",
               "Île & histoire": "Plages & îles"}
    ss = ss.assign(famille=ss.type.map(lambda t: groupes.get(t, "Nature" if t.startswith("Nature") or t == "Montagne"
                                                              else "Patrimoine & culture")))
    cmap = {"Plages & îles": SERIES[0], "Nature": SERIES[5], "Patrimoine & culture": SERIES[1]}
    fig = go.Figure()
    for f, sub in ss.groupby("famille"):
        fig.add_trace(go.Scattermap(lat=sub.lat, lon=sub.lon, mode="markers", name=f, text=sub.nom,
                                    customdata=sub[["commune", "description"]],
                                    marker=dict(size=14, color=cmap[f]),
                                    hovertemplate="<b>%{text}</b> (%{customdata[0]})<br>%{customdata[1]}<extra></extra>"))
    fond_haiti(fig, D.geojson("communes"))
    fig.update_layout(map=dict(style=MAP_STYLE, zoom=6.8, center=dict(lat=18.95, lon=-72.75)), height=540,
                      margin=dict(l=0, r=0, t=0, b=0), legend=dict(y=0.02, x=0.01, bgcolor="rgba(255,255,255,.85)"))
    st.plotly_chart(fig, use_container_width=True)
    cols = st.columns(3)
    for i, x in enumerate(ss.itertuples()):
        with cols[i % 3]:
            with st.container(border=True):
                badge = " · 🏛️ UNESCO" if x.unesco == "oui" else ""
                st.markdown(f"**{x.nom}**{badge}  \n<span style='color:#8a8984'>{x.type} · {x.commune} ({x.departement})</span>",
                            unsafe_allow_html=True)
                st.caption(x.description)
                st.markdown(f"[En savoir plus ↗](https://www.google.com/search?q={x.nom.replace(' ', '+')}+Ha%C3%AFti)")
    s_wb = D.serie("ST.INT.ARVL")
    if len(s_wb):
        fig = px.area(s_wb, x="annee", y="valeur", labels={"annee": "", "valeur": "arrivées"},
                      title="Arrivées de touristes internationaux (Banque mondiale)")
        fig.update_traces(line_color=SERIES[0], line_width=2, fillcolor="rgba(42,120,214,0.15)")
        fig.update_layout(height=300)
        st.plotly_chart(fig, use_container_width=True)
    note("Royal Caribbean a suspendu les escales à Labadee depuis avril 2025 (réexamen prévu en juin 2027) et plusieurs pays "
         "déconseillent actuellement les voyages en Haïti : ces sites sont présentés pour leur valeur et leur potentiel.", "warn")
pied("Sélection de sites : Wikipedia (Tourism in Haiti), UNESCO, connaissances générales ; indice calculé dans la plateforme "
     "(CNIGS, HDX, MENFP, Natural Earth).")
