"""Ayiti Data Hub — tableau de bord d'accueil (contenu de la page d'accueil)."""
import pandas as pd
import streamlit as st

from src import data as D
from src import territoire as T
from src.analyse import analyser_serie  # noqa: F401  (utilisé par d'autres pages)
from src.charts import carte_haiti, graphique_developpement
from src.composants import cartes_richesses, fil_actualites, filtrer_actualites, liens
from src.developpement import lecture
from src.ui import analyse_box, fmt, hero_diaporama, image_b64, kpis, note, pied, setup

setup("Accueil")

hero_diaporama("Ayiti Data Hub",
               "Une terre de culture, d'histoire et de ressources. Territoire, population, écoles, économie, tourisme : "
               "les données sur Haïti réunies en un seul endroit, analysées et mises à jour en continu.",
               eyebrow="Haïti · Ayiti · Hayti")

com, dep = D.communes(), D.departements()

# ------------------------------------------------------------------ Carte + fil d'actualités
gauche, droite = st.columns([3, 2], gap="medium")
with gauche:
    st.markdown("### 🗺️ Haïti en un coup d'œil")
    couches = st.multiselect("Afficher sur la carte",
                             ["Tourisme & patrimoine", "Îles", "Aéroports", "Ports", "Universités publiques",
                              "Hôpitaux de référence", "Écoles & universités (OSM)"],
                             default=["Tourisme & patrimoine", "Îles", "Aéroports"], label_visibility="collapsed")
    pts = []
    if "Tourisme & patrimoine" in couches:
        pts.append(T.sites_touristiques()[["nom", "commune", "lat", "lon"]].assign(categorie="Tourisme & patrimoine"))
    if "Îles" in couches:
        pts.append(T.iles().rename(columns={"ile": "nom", "communes": "commune"})[["nom", "commune", "lat", "lon"]]
                   .assign(categorie="Îles"))
    tr = T.transports()
    if "Aéroports" in couches:
        pts.append(tr[tr.type.str.contains("Aéroport", na=False)][["nom", "commune", "lat", "lon"]].assign(categorie="Aéroports"))
    if "Ports" in couches:
        pts.append(tr[tr.type == "Port"][["nom", "commune", "lat", "lon"]].assign(categorie="Ports"))
    inst = D.institutions()
    if "Universités publiques" in couches:
        u = inst[(inst.categorie == "Université / Enseignement supérieur") & inst.sous_type.str.startswith("Public")]
        pts.append(u.drop_duplicates("commune")[["nom", "commune", "lat", "lon"]].assign(categorie="Universités publiques"))
    if "Hôpitaux de référence" in couches:
        pts.append(inst[inst.categorie == "Santé"][["nom", "commune", "lat", "lon"]].assign(categorie="Hôpitaux de référence"))
    if "Écoles & universités (OSM)" in couches:
        e = D.etablissements_education_osm()
        pts.append(e[e.type != "Bâtiment scolaire"][["nom", "commune", "lat", "lon"]].assign(categorie="Écoles & universités (OSM)"))
    P = pd.concat(pts, ignore_index=True).dropna(subset=["lat"]) if pts else None
    st.plotly_chart(carte_haiti(com, D.geojson("communes"), P, hauteur=600), use_container_width=True,
                    config={"displaylogo": False, "scrollZoom": True})
    st.caption("Couleur des communes : population 2022 (plus foncé = plus peuplé). Survolez un point pour son nom ; "
               "molette pour zoomer.")

with droite:
    st.markdown("### 📰 Dernières nouvelles d'Haïti")
    news = D.actualites_enrichies()
    f1, f2 = st.columns([1, 1])
    positif = f1.toggle("Regard positif d'abord", value=True,
                        help="Met en avant culture, tourisme, sport, innovation, réussites… sans masquer le reste.")
    themes_dispo = sorted(news.theme.unique()) if len(news) else []
    choix = f2.multiselect("Thèmes", themes_dispo, placeholder="Tous les thèmes", label_visibility="collapsed")
    with st.container(height=560):
        fil_actualites(filtrer_actualites(news, positif, choix), n=40)
    if len(news):
        maj = news.get("collecte_utc", pd.Series(["–"])).max()
        st.caption(f"{len(news)} articles · dernière collecte : {maj} UTC · sources : médias haïtiens, diaspora, "
                   "presse internationale (recherches « Haïti », « Ayiti », « Hayti »).")
    st.page_link("pages/08_actualites_et_mises_a_jour.py", label="Toutes les actualités et sources →")

# ------------------------------------------------------------------ Indice de développement
st.markdown("### 📈 Trajectoire de développement d'Haïti — indice multifactoriel")
ind, det = D.indice_developpement()
if not ind.empty:
    a, b = st.columns([3, 2], gap="medium")
    with a:
        st.plotly_chart(graphique_developpement(ind), use_container_width=True)
    with b:
        analyse_box("Ce que montre l'indice", lecture(ind))
        with st.expander(f"Méthode et {len(det)} indicateurs utilisés"):
            st.markdown("Six dimensions — **économique, politique & institutions, social, culture & ouverture, population, "
                        "nature & environnement**. Chaque indicateur est ramené sur 0-100 par rapport aux meilleures et "
                        "pires années d'Haïti depuis 1990 ; une dimension est la moyenne de ses indicateurs, l'indice "
                        "global la moyenne des dimensions. Les dimensions qui ne reposent que sur 1 ou 2 indicateurs "
                        "s'enrichiront à la prochaine mise à jour Banque mondiale (espérance de vie, scolarisation, Internet…).")
            st.dataframe(det, hide_index=True, use_container_width=True)
        st.page_link("pages/07_analyses_ia.py", label="Analyses détaillées et prévisions →")

# ------------------------------------------------------------------ Chiffres clés
st.markdown("### 🔢 Chiffres clés")
act = D.indicateurs_actuels()


def _act(ind_: str, per: str | None = None):
    d = act[act.indicateur == ind_]
    if per:
        d = d[d.periode.astype(str) == per]
    return d.iloc[-1] if len(d) else None


pop, an = D.derniere_valeur("SP.POP.TOTL")
r_tr, r_ies = _act("Transferts sans contrepartie (diaspora)"), _act("Institutions d'enseignement supérieur reconnues", "2026")
kpis([
    {"lab": "Population", "val": fmt(pop) if pop else fmt(dep.population.sum()), "sub": f"Banque mondiale · {an}" if an else "2022",
     "style": "accent"},
    {"lab": "Communes", "val": "140", "sub": f"570 sections · {fmt(len(D.localites()))} localités"},
    {"lab": "Littoral", "val": "≈ 1 500 km", "sub": f"{len(T.communes_cotieres())} communes côtières"},
    {"lab": "Moins de 18 ans", "val": f"{100 * dep.enfants.sum() / dep.population.sum():.0f} %", "sub": "un pays jeune"},
    {"lab": "Diaspora", "val": fmt(float(r_tr.valeur) * 1e6) + " USD" if r_tr is not None else "–", "sub": "transferts 2024"},
    {"lab": "Enseignement supérieur", "val": str(int(r_ies.valeur)) if r_ies is not None else "–", "sub": "IES reconnues 2026"},
])
note("Situation difficile mais pays plein d'atouts : la plateforme montre aussi bien les défis (sécurité alimentaire, "
     "déplacements, croissance négative depuis 2019) que les richesses et les réussites. Détails dans les pages "
     "<b>Humanitaire</b> et <b>Économie</b>.")

# ------------------------------------------------------------------ Richesses
st.markdown("### 💎 Ayiti, terre de richesses")
cartes_richesses(D.richesses(), n=6)
st.page_link("pages/10_richesses_et_ressources.py", label="Toutes les richesses et ressources →")

# ------------------------------------------------------------------ Navigation
st.markdown("### 🧭 Explorer la plateforme")
pages = [
    ("pages/01_carte_interactive.py", "🗺️ Carte interactive", "Indicateurs par commune et département."),
    ("pages/02_fiche_commune.py", "🏘️ Fiche commune", "Profil complet des 140 communes."),
    ("pages/03_institutions.py", "🏫 Écoles, universités & institutions", "Annuaire sur tout le territoire."),
    ("pages/04_economie.py", "📈 Économie & finances", "612 indicateurs depuis 1960."),
    ("pages/05_population.py", "👥 Population & territoire", "Démographie et densité."),
    ("pages/06_humanitaire.py", "🆘 Humanitaire", "IPC, déplacés, santé."),
    ("pages/07_analyses_ia.py", "🤖 Analyses & ML", "Typologie, vulnérabilité, prévisions."),
    ("pages/10_richesses_et_ressources.py", "💎 Richesses & ressources", "Agriculture, mines, mer, culture, diaspora."),
    ("pages/11_bien_vivre_et_tourisme.py", "🌴 Bien vivre & tourisme", "Où il fait bon vivre, sites à visiter."),
    ("pages/12_iles.py", "🏝️ Les îles", "Gonâve, Tortue, Île-à-Vache, Cayemites…"),
    ("pages/13_routes_et_transports.py", "🛣️ Routes & transports", "Routes nationales, aéroports, ports."),
    ("pages/14_rapports_pdf_et_images.py", "📄 Rapports PDF & images", "Générer des rapports sur tous les aspects."),
    ("pages/15_sport.py", "⚽ Sport", "Trophées, JO, Coupes du monde 1974 et 2026."),
    ("pages/16_konpa_et_musique.py", "🎶 Konpa & musique", "70 ans de konpa, patrimoine UNESCO."),
    ("pages/17_gastronomie.py", "🍲 Gastronomie", "Soup joumou, griot, djon djon, kremas…"),
    ("pages/18_histoire_et_solidarite.py", "📜 Histoire & solidarité", "1804 et les peuples qu'Haïti a aidés."),
    ("pages/21_contributions_au_monde.py", "🌟 Contributions au monde", "Médecine, sciences, lettres, arts, tech."),
    ("pages/19_diaspora.py", "🌍 Diaspora", "Où vivent et travaillent les Haïtiens du monde."),
    ("pages/20_administration.py", "🔐 Administration", "Mettre à jour données, images et vidéos."),
]
cols = st.columns(4)
for i, (path, title, desc) in enumerate(pages):
    with cols[i % 4]:
        with st.container(border=True):
            st.page_link(path, label=title)
            st.caption(desc)

st.markdown("### 📷 Ayiti en images")
imgs = [("marche_en_fer.jpg", "Port-au-Prince — le Marché en Fer (1891)"),
        ("cap_haitien.jpg", "Cap-Haïtien — cathédrale Notre-Dame et place d'Armes"),
        ("delmas.jpg", "Delmas"), ("ouanaminthe.jpg", "Ouanaminthe — Nord-Est"),
        ("ferrier.jpg", "Ferrier — Nord-Est"), ("villa.jpg", "Architecture contemporaine en pierre")]
g = st.columns(6)
for i, (img, cap) in enumerate(imgs):
    with g[i]:
        st.markdown(f"<img src='data:image/jpeg;base64,{image_b64(img)}' style='width:100%;height:120px;"
                    f"object-fit:cover;border-radius:10px'/>", unsafe_allow_html=True)
        st.caption(cap)

st.markdown("### 🔗 Pour aller plus loin")
liens(D.liens_utiles())

pied("CNIGS, HDX/OCHA, OpenStreetMap, Banque mondiale, FMI, IPC, OIM, MENFP, UNESCO, Natural Earth, médias haïtiens "
     "et internationaux. Chaque actualité et chaque chiffre renvoie à sa source.")
