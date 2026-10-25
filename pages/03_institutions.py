import pandas as pd
import plotly.express as px
import streamlit as st
from streamlit_folium import st_folium

from src import data as D
from src.charts import COULEUR_CATEGORIE, barres_h, carte_points, choropleth
from src.ui import SEQ_ORANGE, SERIES, entete, fmt, kpis, note, pied, setup

setup("Écoles, universités & institutions", "🏫")
entete("Écoles, universités & institutions",
       "Consultez les établissements scolaires, l'enseignement supérieur, la santé et les administrations, sur tout le territoire.")

com, ec, uni, inst, osm = D.communes(), D.ecoles(), D.universites(), D.institutions(), D.osm_institutions()
edu = D.etablissements_education_osm()

kpis([
    {"lab": "Établissements (OpenStreetMap)", "val": fmt((edu.type != "Bâtiment scolaire").sum()),
     "sub": f"points GPS · {edu.adm2_pcode.nunique()} communes · tout le pays", "style": "accent"},
    {"lab": "Écoles (cartographie 2022)", "val": fmt(len(ec)), "sub": f"{ec.adm2_pcode.nunique()} communes couvertes"},
    {"lab": "Écoles publiques", "val": f"{100 * (ec.secteur == 'Public').mean():.0f} %", "sub": "des écoles recensées"},
    {"lab": "Enseignement supérieur", "val": fmt(len(uni)), "sub": f"{(uni.statut == 'Public').sum()} publiques · {(uni.statut == 'Privé').sum()} privées"},
    {"lab": "Hôpitaux de référence", "val": str((inst.categorie == "Santé").sum()), "sub": "liste de base"},
    {"lab": "Mairies", "val": "140", "sub": "une par commune"},
])

t_rech, t_ecoles, t_uni, t_osm = st.tabs(["🔎 Recherche globale", "🏫 Écoles", "🎓 Universités & IES", "📍 OpenStreetMap"])

# ------------------------------------------------------------------ Recherche globale
with t_rech:
    tout = pd.concat([
        ec.assign(categorie="École", sous_type=ec.secteur + " – " + ec.categorie_deduite, source="MENFP – cartographie 2022"),
        inst,
    ], ignore_index=True)
    f1, f2, f3, f4 = st.columns([2, 1, 1, 1])
    q = f1.text_input("Rechercher un nom (ex. lycée, Quisqueya, hôpital, mairie…)")
    cats = f2.multiselect("Catégorie", sorted(tout.categorie.dropna().unique()), placeholder="Toutes")
    deps = f3.multiselect("Département", sorted(com.departement.unique()), placeholder="Tous")
    comms = f4.multiselect("Commune", sorted(com[com.departement.isin(deps)].commune) if deps else sorted(com.commune), placeholder="Toutes")
    r = tout
    if q:
        r = r[r.nom.str.contains(q, case=False, na=False) | r.get("sigle", pd.Series("", index=r.index)).fillna("").str.contains(q, case=False)]
    if cats:
        r = r[r.categorie.isin(cats)]
    if deps:
        r = r[r.departement.isin(deps)]
    if comms:
        r = r[r.commune.isin(comms)]
    st.markdown(f"**{fmt(len(r))} résultats**")
    st.dataframe(r[["nom", "categorie", "sous_type", "commune", "departement", "precision_localisation", "source"]],
                 hide_index=True, use_container_width=True, height=380)
    st.download_button("⬇️ Télécharger la sélection (CSV)", r.to_csv(index=False).encode("utf-8"), "institutions_selection.csv")
    if len(r) > 6000:
        st.info("Affinez la recherche (département, commune, catégorie ou nom) pour afficher les résultats sur la carte.")
    if 0 < len(r) <= 6000:
        import numpy as np
        P = r.dropna(subset=["lat", "lon"]).copy()
        approx = P.precision_localisation.fillna("") == "commune"
        rng = np.random.default_rng(2)
        P.loc[approx, "lat"] += rng.normal(0, 0.007, approx.sum())
        P.loc[approx, "lon"] += rng.normal(0, 0.007, approx.sum())
        cols = dict(COULEUR_CATEGORIE)
        m = carte_points(P, "categorie", ["nom", "sous_type", "commune", "precision_localisation"], zoom=8, couleurs=cols)
        st_folium(m, height=560, use_container_width=True, returned_objects=[])
        st.caption("Les établissements sans coordonnées GPS sont placés (avec un léger décalage) au centre de leur commune.")

# ------------------------------------------------------------------ Écoles
with t_ecoles:
    st.markdown("#### 🌍 Tout le pays — établissements d'enseignement OpenStreetMap")
    st.caption(f"Export HOT/OpenStreetMap du 5 octobre 2026 : {fmt(len(edu))} objets géolocalisés, dont "
               f"{fmt((edu.type == 'Bâtiment scolaire').sum())} bâtiments scolaires (souvent sans nom) affichés à part.")
    a, b = st.columns([3, 2])
    with a:
        fig = choropleth(com, D.geojson("communes"), "ecoles_osm_pour_1000_enfants", "Écoles OSM / 1 000 enfants",
                         hover=["departement", "nb_ecoles_osm", "nb_superieur_osm", "enfants"], scale=SEQ_ORANGE, height=500)
        st.plotly_chart(fig, use_container_width=True)
    with b:
        k = edu.groupby(["type"]).size().reset_index(name="n")
        st.plotly_chart(barres_h(k, "n", "type", "Établissements par type", "", height=250), use_container_width=True)
        s2 = edu[edu.type != "Bâtiment scolaire"].secteur.value_counts().reset_index()
        s2.columns = ["secteur", "n"]
        st.plotly_chart(barres_h(s2, "n", "secteur", "Secteur (quand il est renseigné)", "", color=SERIES[1], height=250),
                        use_container_width=True)
    ft = st.multiselect("Types à afficher sur la carte", sorted(edu.type.unique()),
                        default=["Université", "Institut / collège supérieur", "École", "Préscolaire"])
    fd = st.selectbox("Département", ["Tout le pays"] + sorted(com.departement.unique()), key="edu_dep")
    E = edu[edu.type.isin(ft)]
    if fd != "Tout le pays":
        E = E[E.departement == fd]
    cmap = {"École": SERIES[1], "Préscolaire": SERIES[4], "Université": SERIES[0],
            "Institut / collège supérieur": SERIES[6], "Bâtiment scolaire": "#b7b5ae"}
    m = carte_points(E.rename(columns={"type": "categorie"}).assign(type=E.type), "categorie",
                     ["nom", "type", "secteur", "commune", "section_communale"], zoom=8 if fd == "Tout le pays" else 9,
                     centre=(E.lat.mean(), E.lon.mean()) if fd != "Tout le pays" and len(E) else None, couleurs=cmap)
    st_folium(m, height=560, use_container_width=True, returned_objects=[])
    st.dataframe(E[["nom", "type", "secteur", "commune", "departement", "section_communale", "lat", "lon"]],
                 hide_index=True, use_container_width=True, height=300)
    st.download_button("⬇️ Établissements OSM (CSV)", E.to_csv(index=False).encode("utf-8"), "etablissements_osm.csv")
    note("OpenStreetMap est une carte collaborative : elle couvre tout le territoire mais reste incomplète (beaucoup "
         "d'écoles rurales ne sont pas encore cartographiées) et le secteur public/privé n'est renseigné que pour ~30 % "
         "des points. Chacun peut contribuer sur openstreetmap.org.")
    st.divider()
    st.markdown("#### 🗂️ Cartographie scolaire 2022 (MENFP)")
    note("La cartographie scolaire 2022 (MENFP/HDX) couvre la <b>Grand'Anse, les Nippes, le Sud et 8 communes de l'Ouest</b> — "
         "les zones touchées par le séisme du 14 août 2021 — mais elle est plus exhaustive qu'OpenStreetMap dans ces zones "
         "(4 122 écoles contre 2 817 points OSM dans les mêmes communes).", "warn")
    cc = com[com.couverture_ecoles_2022]
    a, b = st.columns([3, 2])
    with a:
        fig = choropleth(cc, D.geojson("communes"), "ecoles_pour_1000_enfants", "Écoles / 1 000 enfants",
                         hover=["departement", "nb_ecoles", "enfants"], scale=SEQ_ORANGE, height=470)
        fig.update_layout(map=dict(center=dict(lat=18.45, lon=-73.4), zoom=7.6))
        st.plotly_chart(fig, use_container_width=True)
    with b:
        dd = ec.groupby(["departement", "secteur"]).size().reset_index(name="n")
        fig = px.bar(dd, x="n", y="departement", color="secteur", orientation="h", barmode="stack",
                     color_discrete_map={"Public": SERIES[0], "Non public": SERIES[1]},
                     labels={"n": "écoles", "departement": "", "secteur": ""}, title="Écoles par secteur")
        fig.update_traces(marker_line_color="white", marker_line_width=2)
        fig.update_layout(height=260, hovermode="closest")
        st.plotly_chart(fig, use_container_width=True)
        cat = ec.categorie_deduite.value_counts().reset_index()
        cat.columns = ["categorie", "n"]
        st.plotly_chart(barres_h(cat, "n", "categorie", "Type d'établissement (déduit du nom)", "écoles", height=320),
                        use_container_width=True)
    st.caption("Le type est déduit automatiquement du nom (Lycée, Collège, École nationale…) : c'est une classification indicative.")
    tc = cc.sort_values("ecoles_pour_1000_enfants")[["commune", "departement", "nb_ecoles", "nb_ecoles_publiques",
                                                     "enfants", "ecoles_pour_1000_enfants"]]
    st.markdown("**Communes couvertes, de la moins à la mieux dotée (écoles / 1 000 enfants)**")
    st.dataframe(tc, hide_index=True, use_container_width=True)

# ------------------------------------------------------------------ Universités
with t_uni:
    a, b = st.columns(2)
    with a:
        comp = uni.composante.value_counts().reset_index()
        comp.columns = ["composante", "n"]
        st.plotly_chart(barres_h(comp, "n", "composante", "Composantes de l'enseignement supérieur (liste MENFP)", "IES"),
                        use_container_width=True)
    with b:
        from src.utils import CURATED
        ies = pd.read_csv(CURATED / "ies_privees_par_departement_2026.csv")
        st.plotly_chart(barres_h(ies, "institutions_privees", "departement",
                                 "IES privées reconnues par département (2026)", "IES", color=SERIES[1]),
                        use_container_width=True)
    act = D.indicateurs_actuels()
    tr = act[act.indicateur == "Institutions d'enseignement supérieur reconnues"]
    if len(tr):
        fig = px.line(tr, x="periode", y="valeur", markers=True, title="Institutions d'enseignement supérieur reconnues",
                      labels={"periode": "", "valeur": "institutions"})
        fig.update_traces(line_width=2, marker_size=9)
        fig.update_layout(height=280)
        st.plotly_chart(fig, use_container_width=True)
    note("Les deux tiers des IES privées sont dans l'Ouest (région de Port-au-Prince). Le réseau public couvre chaque "
         "département grâce aux 10 Universités publiques en région (UPR) et aux écoles de droit et d'infirmières de l'UEH.")
    f1, f2 = st.columns(2)
    st_f = f1.multiselect("Statut", ["Public", "Privé"], default=["Public", "Privé"])
    qq = f2.text_input("Rechercher une université ou un sigle")
    u = uni[uni.statut.isin(st_f)]
    if qq:
        u = u[u.nom.str.contains(qq, case=False) | u.sigle.fillna("").str.contains(qq, case=False)]
    st.dataframe(u[["nom", "sigle", "statut", "composante", "commune", "departement", "precision_localisation"]],
                 hide_index=True, use_container_width=True, height=420)
    st.caption("Liste : MENFP, institutions reconnues (via Le Scientifique, 2023 et 2026). La commune n'est renseignée que "
               "lorsqu'elle est indiquée par la source ou par le nom de l'institution ; « à vérifier » signale une localisation "
               "probable mais non confirmée.")

# ------------------------------------------------------------------ OSM
with t_osm:
    if osm.empty:
        note("Les écoles et universités OpenStreetMap sont déjà intégrées (onglet Écoles). Pour les autres institutions : "
             "aucune donnée OpenStreetMap encore téléchargée. Allez dans <b>🔄 Actualités & mises à jour</b> et cliquez sur "
             "« Mettre à jour maintenant », ou laissez l'action GitHub hebdomadaire s'en charger. Vous obtiendrez des milliers "
             "d'écoles, universités, hôpitaux, cliniques, pharmacies, commissariats, tribunaux, banques, bibliothèques… avec "
             "leurs coordonnées GPS, rattachés automatiquement à leur commune.")
    else:
        k = osm.groupby(["categorie", "type"]).size().reset_index(name="n").sort_values("n", ascending=False)
        st.plotly_chart(px.treemap(k, path=["categorie", "type"], values="n", title="Institutions OpenStreetMap par type",
                                   color="categorie", color_discrete_map=COULEUR_CATEGORIE), use_container_width=True)
        par_dep = osm.groupby(["departement", "categorie"]).size().reset_index(name="n")
        fig = px.bar(par_dep, x="n", y="departement", color="categorie", orientation="h", color_discrete_map=COULEUR_CATEGORIE,
                     labels={"n": "", "departement": ""}, title="Par département")
        fig.update_layout(hovermode="closest")
        st.plotly_chart(fig, use_container_width=True)
        st.dataframe(osm, hide_index=True, use_container_width=True)

pied("MENFP (cartographie des institutions scolaires 2022 via HDX ; liste des IES reconnues), OpenStreetMap (ODbL), CNIGS.")
