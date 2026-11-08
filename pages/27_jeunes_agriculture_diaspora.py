import urllib.parse
from datetime import date

import pandas as pd
import plotly.express as px
import streamlit as st

from src import admin
from src import gouvernance as G
from src.exports_doc import panneau_exports
from src.ui import SERIES, analyse_box, entete, kpis, note, pied, setup
from src.utils import CURATED

setup("Jeunes agriculteurs & diaspora", "🌱")
entete("Jeunes agriculteurs, éleveurs et diaspora",
       "Recenser les jeunes qui se lancent dans l'agriculture et l'élevage (souvent visibles sur Facebook), les relier aux "
       "filières de leur département et à la diaspora.")

F_REC = CURATED / "jeunes_agri_recensement.csv"
F_OFF = CURATED / "diaspora_offres.csv"
FIL = pd.read_csv(CURATED / "agri_filieres_departements.csv")
MEC = pd.read_csv(CURATED / "diaspora_mecanismes.csv")
COM = G.communes_maillage()
DEPS = sorted(COM.departement.unique())
FILIERES = ["Riz", "Maïs / sorgho", "Haricot", "Tubercules (igname, patate, manioc)", "Banane", "Maraîchage (légumes)", "Café",
            "Cacao", "Mangue / fruits", "Vétiver", "Canne à sucre", "Aviculture (poules, œufs)", "Caprins / ovins (cabris, moutons)",
            "Bovins (lait, viande)", "Porcins", "Apiculture (miel)", "Pêche / aquaculture", "Transformation agroalimentaire", "Autre"]
BESOINS = ["Semences / intrants", "Financement", "Formation technique", "Vétérinaire", "Irrigation / eau", "Matériel", "Transport",
           "Accès au marché / acheteurs", "Stockage / froid", "Titre foncier"]


def lire(p):
    return pd.read_csv(p) if p.exists() else pd.DataFrame()


REC, OFF = lire(F_REC), lire(F_OFF)
kpis([
    {"lab": "Jeunes recensés", "val": str(len(REC)), "sub": "avec leur consentement", "style": "accent"},
    {"lab": "Offres de la diaspora", "val": str(len(OFF)), "sub": "parrainages, achats, expertise"},
    {"lab": "Transferts de la diaspora", "val": "≈5 Md USD", "sub": "2025, ≈20 % du PIB (BRH, via ICI Haïti)"},
    {"lab": "Producteurs à financer", "val": "300 000", "sub": "crédit de campagne en 2033 (programme Etzer)"},
    {"lab": "Terres irriguées", "val": "+60 000 ha", "sub": "d'ici 2033 (programme Etzer)", "style": "alert"},
])

t_rec, t_trouver, t_fil, t_parc, t_dia, t_foire, t_exp = st.tabs([
    "📝 Recensement", "🔎 Les trouver sur les réseaux", "🌾 Filières par département", "🪜 Parcours d'intégration",
    "🤝 Diaspora", "🎪 Foire Agri-Diaspora", "📥 Exports"])

# ------------------------------------------------------------------ recensement
with t_rec:
    note("On enregistre seulement des <b>pages publiques</b> et des personnes qui <b>acceptent</b> d'être recensées. Chaque fiche "
         "arrive avec le statut « à vérifier » ; l'administrateur la valide (vérification par le CASEC ou un agronome communal) "
         "depuis l'espace Administration → fichier <i>jeunes_agri_recensement</i>. Pas de numéro de téléphone personnel : le "
         "contact passe par la page publique.")
    c4, c5 = st.columns(2)
    dep = c4.selectbox("Département *", DEPS)
    com = c5.selectbox("Commune *", sorted(COM[COM.departement == dep].commune))
    with st.form("rec", clear_on_submit=True):
        c1, c2, c3 = st.columns(3)
        nom = c1.text_input("Nom de la ferme ou de la page *")
        plat = c2.selectbox("Plateforme", ["Facebook", "Instagram", "TikTok", "WhatsApp (groupe public)", "YouTube", "Autre"])
        lien = c3.text_input("Lien public (https://…)")
        c6, c7, c8 = st.columns(3)
        fil = c6.selectbox("Filière *", FILIERES)
        act = c7.selectbox("Activité", ["Agriculture", "Élevage", "Pêche", "Transformation", "Mixte"])
        taille = c8.text_input("Taille (ex. 2 ha, 40 cabris, 500 poules)")
        bes = st.multiselect("Besoins principaux", BESOINS)
        ok = st.checkbox("La personne a accepté d'être recensée et d'être contactée via sa page publique *")
        if st.form_submit_button("Ajouter au recensement", type="primary"):
            if not (nom and ok):
                st.error("Le nom et le consentement sont obligatoires.")
            elif lien and not lien.startswith("http"):
                st.error("Le lien doit commencer par http.")
            else:
                ligne = pd.DataFrame([{"date": date.today().isoformat(), "nom_ou_page": nom.strip(), "plateforme": plat,
                                       "lien_public": lien.strip(), "departement": dep, "commune": com, "filiere": fil,
                                       "activite": act, "taille": taille.strip(), "besoins": " ; ".join(bes),
                                       "consentement": "oui", "statut": "à vérifier"}])
                REC = pd.concat([REC, ligne], ignore_index=True)
                st.success("Fiche ajoutée : " + admin.enregistrer(F_REC, REC.to_csv(index=False).encode("utf-8"),
                                                        f"Recensement : {nom} ({com})") + ".")
    if len(REC):
        f1, f2 = st.columns(2)
        fd = f1.multiselect("Filtrer par département", DEPS)
        ff = f2.multiselect("Filtrer par filière", FILIERES)
        masque = pd.Series(True, index=REC.index)
        if fd:
            masque &= REC.departement.isin(fd)
        if ff:
            masque &= REC.filiere.isin(ff)
        v = REC[masque]
        st.dataframe(v, hide_index=True, use_container_width=True, column_config={"lien_public": st.column_config.LinkColumn("lien")})
        a, b = st.columns(2)
        a.plotly_chart(px.bar(v.groupby("departement").size().rename("jeunes").reset_index(), x="jeunes", y="departement",
                              orientation="h", title="Jeunes recensés par département", color_discrete_sequence=[SERIES[2]]),
                       use_container_width=True)
        b.plotly_chart(px.bar(v.groupby("filiere").size().rename("jeunes").reset_index().sort_values("jeunes"), x="jeunes",
                              y="filiere", orientation="h", title="Par filière", color_discrete_sequence=[SERIES[3]]),
                       use_container_width=True)
    else:
        st.info("Aucun jeune recensé pour l'instant. Utilisez l'onglet « Les trouver sur les réseaux » pour repérer les pages, "
                "puis ajoutez-les ici avec leur accord.")

# ------------------------------------------------------------------ recherche sur les réseaux
with t_trouver:
    st.markdown("Liens de recherche prêts à l'emploi, par commune, en créole et en français. Ils ouvrent la recherche publique "
                "de chaque réseau : rien n'est collecté automatiquement.")
    c1, c2 = st.columns(2)
    d2 = c1.selectbox("Département", DEPS, key="d2")
    c2_ = c2.selectbox("Commune", ["(tout le département)"] + sorted(COM[COM.departement == d2].commune), key="c2")
    lieu = d2 if c2_.startswith("(") else c2_
    mots = [f"jèn agrikiltè {lieu}", f"elvaj kabrit {lieu}", f"fèm poul {lieu}", f"ferme avicole {lieu}", f"agriculture {lieu} Haïti",
            f"pwodiksyon lokal {lieu}", f"jardin lakou {lieu}", f"apikilti {lieu}"]

    def liens(q):
        e = urllib.parse.quote(q)
        return (f"[Facebook](https://www.facebook.com/search/top/?q={e}) · [Pages FB](https://www.facebook.com/search/pages/?q={e}) · "
                f"[TikTok](https://www.tiktok.com/search?q={e}) · [YouTube](https://www.youtube.com/results?search_query={e}) · "
                f"[Instagram #](https://www.instagram.com/explore/tags/{urllib.parse.quote(q.split()[0] + q.split()[1])}/)")
    for q in mots:
        st.markdown(f"- **{q}** — {liens(q)}")
    analyse_box("Méthode de recensement en 5 étapes", [
        "**Repérer** : recherche par commune et par filière ; groupes Facebook d'agriculteurs ; pages des marchés communaux.",
        "**Vérifier** : la page montre-t-elle une activité réelle et récente (photos de la ferme, des animaux, des récoltes) ?",
        "**Contacter** par message sur la page ; présenter Ayiti Data Hub et le but du recensement.",
        "**Recueillir l'accord** avant toute inscription ; enregistrer seulement ce qui est utile (filière, taille, besoins).",
        "**Faire valider** par le CASEC de la section ou l'agronome communal (BAC du MARNDR) : statut « vérifié ».",
    ])

# ------------------------------------------------------------------ filières
with t_fil:
    st.dataframe(FIL.drop(columns=["adm1_pcode"]), hide_index=True, use_container_width=True)
    res = pd.read_csv(CURATED / "ressources_haiti.csv") if (CURATED / "ressources_haiti.csv").exists() else pd.DataFrame()
    if len(res):
        agri = res[res.categorie.isin(["Agriculture", "Pêche & mer"])]
        fig = px.scatter_map(agri, lat="lat", lon="lon", hover_name="nom", color="sous_categorie", zoom=6.6,
                                center={"lat": 18.95, "lon": -72.7}, height=520, map_style="carto-positron",
                                title="Bassins de production connus (agriculture et pêche)")
        fig.update_layout(margin=dict(l=0, r=0, t=40, b=0), legend=dict(orientation="v", y=1, x=1.01))
        st.plotly_chart(fig, use_container_width=True)

# ------------------------------------------------------------------ parcours
with t_parc:
    etapes = [
        ("1. Recensé", "Fiche créée avec consentement (cette page).", "Ayiti Data Hub"),
        ("2. Vérifié", "Visite ou appel du CASEC / agronome communal ; statut « vérifié ».", "CASEC, BAC (MARNDR)"),
        ("3. Formé", "Itinéraire technique, santé animale, gestion simple ; mentorat d'un expert de la diaspora.",
         "MARNDR, écoles d'agronomie, experts diaspora"),
        ("4. Financé", "Semences et engrais subventionnés, crédit de campagne, warrantage, assurance récolte ; parrainage diaspora.",
         "Programme public (ex. plan de relance agricole du programme Etzer), IMF, diaspora"),
        ("5. Relié au marché", "Achats publics prioritaires (cantines scolaires, hôpitaux, forces de sécurité), marchés couverts, "
                               "ZES agro-industrielles, export vers la diaspora.", "Collectivités, ZES, acheteurs diaspora"),
        ("6. Suivi", "Rapport du CASEC (rubrique agriculture) : récoltes, prix, pertes ; mise à jour de la fiche.", "CASEC → mairie → MICT"),
    ]
    cols = st.columns(3)
    for i, (t, d, qui) in enumerate(etapes):
        cols[i % 3].markdown(f"<div class='ay-card' style='margin-bottom:.8rem;border-top:4px solid {SERIES[i % 6]}'><h4>{t}</h4>"
                             f"<p>{d}</p><p style='margin-top:.4rem'><span class='ay-badge'>{qui}</span></p></div>",
                             unsafe_allow_html=True)
    analyse_box("Lien avec le programme d'Etzer Émile (priorité « Produire et créer des emplois »)", [
        "Plan national de relance agricole **par filière et par département** dans les 100 premiers jours ; semences certifiées et engrais subventionnés.",
        "**Un vétérinaire public par département** et des agents communautaires dans chaque section communale.",
        "Achats publics prioritaires de la production nationale ; **titres fonciers au nom des deux conjoints**.",
        "50 000 emplois temporaires (travaux à forte main-d'œuvre) et prêts sans intérêt pour 5 000 PME.",
    ])

# ------------------------------------------------------------------ diaspora
with t_dia:
    st.dataframe(MEC, hide_index=True, use_container_width=True, column_config={"source": st.column_config.LinkColumn("source")})
    st.markdown("#### Proposer une offre (membre de la diaspora)")
    with st.form("off", clear_on_submit=True):
        c1, c2, c3 = st.columns(3)
        n = c1.text_input("Nom ou organisation *")
        vp = c2.text_input("Ville, pays")
        to = c3.selectbox("Type d'offre", MEC.mecanisme.tolist())
        c4, c5, c6 = st.columns(3)
        fo = c4.selectbox("Filière", ["Toutes"] + FILIERES)
        do = c5.selectbox("Département visé", ["Tous"] + DEPS)
        mt = c6.number_input("Montant indicatif (USD)", 0, 1_000_000, 0, step=50)
        de = st.text_area("Description")
        cp = st.text_input("Contact public (page, site ou adresse professionnelle)")
        okd = st.checkbox("J'accepte que cette offre soit visible sur la plateforme *")
        if st.form_submit_button("Publier l'offre", type="primary"):
            if not (n and okd):
                st.error("Le nom et l'accord sont obligatoires.")
            else:
                OFF = pd.concat([OFF, pd.DataFrame([{"date": date.today().isoformat(), "nom": n, "ville_pays": vp, "type_offre": to,
                                                     "filiere": fo, "departement_cible": do, "montant_usd": mt, "description": de,
                                                     "contact_public": cp, "consentement": "oui", "statut": "à vérifier"}])],
                                ignore_index=True)
                st.success("Offre publiée : " + admin.enregistrer(F_OFF, OFF.to_csv(index=False).encode("utf-8"), f"Offre diaspora : {n}") + ".")
    st.markdown("#### Mises en relation suggérées")
    if len(OFF) and len(REC):
        paires = []
        for o in OFF.itertuples():
            m = REC[((REC.filiere == o.filiere) | (o.filiere == "Toutes")) & ((REC.departement == o.departement_cible) | (o.departement_cible == "Tous"))]
            for j in m.itertuples():
                paires.append({"offre": f"{o.nom} — {o.type_offre}", "jeune": j.nom_ou_page, "commune": j.commune,
                               "filiere": j.filiere, "besoins": j.besoins})
        st.dataframe(pd.DataFrame(paires), hide_index=True, use_container_width=True) if paires else st.info("Aucune correspondance pour l'instant.")
    else:
        st.info("Les correspondances apparaîtront dès qu'il y aura au moins une offre et un jeune recensé (même filière et même département).")

# ------------------------------------------------------------------ foire
with t_foire:
    note("Inspirée des rendez-vous existants avec la diaspora : <b>Journée nationale de la diaspora</b> (15e édition en avril 2026, "
         "ministère du Tourisme et MHAVE), <b>Semaine de la diaspora</b> (14e édition en République dominicaine) et foires du MHAVE "
         "à New York. L'idée : une édition agricole qui met en vitrine les jeunes recensés.")
    c1, c2 = st.columns(2)
    with c1:
        analyse_box("Format", [
            "**Une édition physique par an**, dans un département différent (rotation), pendant la période des congés de la diaspora.",
            "**Une plateforme en ligne permanente** : les stands virtuels sont les fiches vérifiées de cette page.",
            "**Contrats signés sur place** : pré-achat de récolte, parrainage d'intrants, mission d'expertise, part de coopérative.",
            "**Visites de fermes** (agrotourisme) et dégustations : café, cacao, mangue, miel, clairin.",
        ])
    with c2:
        st.dataframe(pd.DataFrame({
            "jour": ["Jour 1", "Jour 2", "Jour 3"],
            "programme": ["Ouverture ; stands des jeunes par filière ; rencontres avec les autorités locales (mairie, CASEC, délégué)",
                          "Rendez-vous d'affaires diaspora ↔ jeunes ; atelier crédit et assurance récolte ; concours du meilleur produit",
                          "Visites de fermes ; signatures ; bilan public (contrats, montants, jeunes financés)"]}),
            hide_index=True, use_container_width=True)
    rot = FIL[["departement", "filieres"]].copy()
    rot.insert(0, "édition", [f"{2027 + i}" for i in range(len(rot))])
    st.markdown("#### Rotation proposée des éditions")
    st.dataframe(rot, hide_index=True, use_container_width=True)

# ------------------------------------------------------------------ exports
with t_exp:
    def blocs():
        b = [("h1", "1. Filières par département"), ("table", FIL.drop(columns=["adm1_pcode"])),
             ("h1", "2. Parcours d'intégration des jeunes"), ("ul", [f"**{t}** — {d} ({q})" for t, d, q in etapes]),
             ("h1", "3. Mécanismes d'intégration de la diaspora"), ("table", MEC.drop(columns=["source"])),
             ("h1", "4. Foire Agri-Diaspora"), ("table", rot)]
        if len(REC):
            b += [("h1", "5. Jeunes recensés"), ("table", REC.drop(columns=["consentement"]))]
        if len(OFF):
            b += [("h1", "6. Offres de la diaspora"), ("table", OFF.drop(columns=["consentement"]))]
        return b

    panneau_exports("agri", "Jeunes agriculteurs, éleveurs et diaspora", "Recensement, filières, parcours d'intégration et Foire Agri-Diaspora",
                    blocs, {"filieres": FIL, "mecanismes_diaspora": MEC, "recensement": REC, "offres_diaspora": OFF},
                    sources="voteetzer.ht/priorite/emplois ; ICI Haïti (avril 2026) ; HaitiLibre ; ressources_haiti.csv (Ayiti Data Hub).")

pied("<a href='https://voteetzer.ht/priorite/emplois'>voteetzer.ht (emplois)</a> ; "
     "<a href='https://www.icihaiti.com/en/news-47379-the-ministry-of-tourism-salutes-the-exceptional-contribution-of-the-haitian-diaspora.html'>ICI Haïti</a> ; "
     "<a href='https://webdisk.haitilibre.com/en/news-47319-haiti-dr-launch-of-the-14th-edition-of-diaspora-week.html'>HaitiLibre</a>.")
