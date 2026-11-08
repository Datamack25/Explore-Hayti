import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from streamlit_folium import st_folium

from src import gouvernance as G
from src.exports_doc import panneau_exports
from src.ui import SERIES, analyse_box, entete, kpis, note, pied, setup

setup("Plan de sécurité territorial", "🛡️")
entete("Plan de sécurité sur le territoire",
       "Ce que le gouvernement de transition (Mario Andrésol) a engagé, ce que propose le programme du candidat Etzer Émile, "
       "et comment l'ensemble se projette département par département.")

M, D, PC = G.plan_mesures(), G.plan_departements(), G.points_controle()
kpis([
    {"lab": "Policiers PNH", "val": "13 000 → 26 000", "sub": "programme Etzer : 19 000 en 2029, 26 000 en 2033", "style": "accent"},
    {"lab": "Territoire sous contrôle", "val": "85 % → 100 %", "sub": "cibles 2029 → 2033 (programme Etzer)"},
    {"lab": "Armes illégales", "val": "25 000", "sub": "saisies et détruites d'ici 2033"},
    {"lab": "Avoirs des gangs gelés", "val": "≥150 M USD", "sub": "d'ici 2033"},
    {"lab": "Déplacés internes", "val": "≈1,5 M", "sub": "mai 2026 ; cible 90 % retournés en 2033", "style": "alert"},
])
note("<b>Lecture.</b> Les mesures et chiffres viennent des sources citées : programme publié par la campagne d'Etzer Émile "
     "(voteetzer.ht) et presse haïtienne pour l'action de Mario Andrésol. La <b>phase proposée par département</b> "
     "(reprendre / tenir / construire) et la répartition territoriale des mesures nationales sont une <b>projection d'Ayiti Data "
     "Hub</b>, pas des engagements des intéressés. Présenter un programme n'est pas le soutenir : les autres candidats peuvent "
     "être ajoutés de la même façon dans data/curated/plan_securite_mesures.csv.")
note("L'entretien de Mario Andrésol diffusé par le média « Marche Long » n'a pas pu être retrouvé en ligne : les éléments du "
     "plan Andrésol proviennent des comptes rendus publics (Le Placentin, Le Nouvelliste, HaitiLibre). Si vous avez le lien, "
     "ajoutez ses mesures dans le CSV.", "warn")

t_map, t_dep, t_mes, t_cal, t_crit, t_exp = st.tabs([
    "🗺️ Carte des phases", "📍 Par département", "⚖️ Mesures comparées", "🗓️ 100 jours · 2029 · 2033", "🔎 Lecture critique", "📥 Exports"])

with t_map:
    st.markdown("**Rouge : reprendre** (zones prioritaires citées par le gouvernement, axes coupés) · **orange : tenir** "
                "(portes d'entrée et corridors à sécuriser) · **vert : construire** (départements où l'effort porte sur les "
                "infrastructures et la présence de l'État).")
    st_folium(G.carte_calques("securite", ("chefs", "controle")), height=640, use_container_width=True, returned_objects=[])

with t_dep:
    dep = st.selectbox("Département", D.departement.tolist())
    x = D[D.departement == dep].iloc[0]
    coul = G.COUL_PHASE[x.phase_proposee]
    st.markdown(f"<div class='ay-card' style='border-top:5px solid {coul}'><h4>{dep} — phase proposée : {x.phase_proposee}</h4>"
                f"<p>Zone citée comme prioritaire par le gouvernement (M. Andrésol, févr. 2026) : <b>{x.priorite_andresol}</b></p></div>",
                unsafe_allow_html=True)
    c1, c2 = st.columns(2)
    with c1:
        st.markdown("##### 🎯 Points chauds et axes")
        st.write(x.points_chauds_et_axes)
        st.markdown("##### 🛡️ Mesures de sécurité territoriales")
        st.write(x.securite_mesures_territoriales)
    with c2:
        st.markdown("##### 🏗️ Projets localisés dans le programme d'Etzer Émile")
        st.write(x.programme_etzer_projets_localises)
        st.markdown("##### 💎 Atouts à protéger")
        st.write(x.atouts_a_proteger)
    pcd = PC[PC.adm1_pcode == x.adm1_pcode]
    if len(pcd):
        st.markdown("##### 🚧 Points de contrôle du département")
        st.dataframe(pcd[["nom", "type", "institutions", "mesure_programme_etzer"]], hide_index=True, use_container_width=True)
    st.dataframe(D, hide_index=True, use_container_width=True)

with t_mes:
    src = st.multiselect("Source", M.source.unique().tolist(), default=M.source.unique().tolist())
    st.dataframe(M[M.source.isin(src)], hide_index=True, use_container_width=True,
                 column_config={"url": st.column_config.LinkColumn("lien")})
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=["2026", "2029", "2033"], y=[13000, 19000, 26000], mode="lines+markers+text",
                             text=["≈13 000", "19 000", "26 000"], textposition="top center", line=dict(color=SERIES[0], width=3),
                             name="Agents PNH"))
    fig.update_layout(title="Effectifs de la PNH visés par le programme d'Etzer Émile", height=340, yaxis_title="agents",
                      yaxis_range=[0, 30000], hovermode="x")
    st.plotly_chart(fig, use_container_width=True)
    analyse_box("Ce qui converge entre les deux approches", [
        "**Reconquête progressive** : maillage policier et coordination locale (Andrésol) ↔ « reprendre, tenir, construire » avec "
        "présence permanente après chaque reprise (Etzer).",
        "**Routes nationales** : réouverture des axes Sud et Nord promise pour février 2026 ↔ RN1-RN3 praticables sans escorte en 2029.",
        "**FAd'H** : nouvelle doctrine, promotion Makandal, 1 200 soldats formés ↔ génie militaire, frontières, garde-côtes.",
        "**Différence principale** : le programme Etzer chiffre des cibles 2029/2033 et ajoute justice, renseignement financier et "
        "lutte anticorruption ; les comptes rendus du plan Andrésol ne donnent ni budget ni échéancier détaillé.",
    ])

with t_cal:
    ordre = {"100 jours": 0, "1re année": 1, "6 mois": 1, "2029": 2, "2033": 3}

    def phase(e):
        for k in ["100 jours", "6 mois", "1re année", "2029", "2033"]:
            if k in str(e):
                return k
        return "Continu / autre"

    cal = M[M.source.str.contains("Etzer")].assign(premiere_echeance=lambda d: d.echeance.map(phase))
    for k in ["100 jours", "6 mois", "1re année", "2029", "2033", "Continu / autre"]:
        s = cal[cal.premiere_echeance == k]
        if len(s):
            st.markdown(f"#### {k}")
            for r in s.itertuples():
                st.markdown(f"- **{r.axe}** — {r.mesure} · *cible : {r.cible}*")

with t_crit:
    c1, c2 = st.columns(2)
    with c1:
        analyse_box("Points forts", [
            "Cibles chiffrées et datées, donc **vérifiables** (programme Etzer).",
            "Approche complète : police, armée, justice, argent des gangs, réinsertion, déplacés.",
            "Le plan du gouvernement s'appuie sur un **cadre de coopération avec le PNUD** (5 axes) et un comité de suivi au ministère de la Défense.",
        ])
    with c2:
        analyse_box("Points d'attention", [
            "Le programme Etzer **ne chiffre pas l'enveloppe** de la sécurité (seuls la part du budget de la justice et les avoirs gelés le sont).",
            "Doubler la PNH en 7 ans suppose recrutement, vetting et formation à un rythme jamais atteint.",
            "Côté gouvernement, la presse relève **l'écart entre annonces et terrain** et l'absence de calendrier détaillé.",
            "Dans les deux cas, le résultat dépend de l'appui international et de la capacité de la justice à juger.",
        ])
    note("Cette page présente des plans ; elle ne recommande aucun candidat. Toute autre plateforme électorale peut être "
         "ajoutée avec la même grille (mesure, échéance, cible, indicateur, source).")

with t_exp:
    def blocs():
        return [
            ("note", "Phases par département et répartition territoriale : projection d'Ayiti Data Hub à partir des sources citées."),
            ("h1", "1. Carte des phases (reprendre / tenir / construire)"),
            ("img", G.fig_carte("securite", "Plan de sécurité : phases proposées par département et points de contrôle"), ""),
            ("h1", "2. Projection par département"),
            ("table", D.drop(columns=["adm1_pcode"])),
            ("h1", "3. Mesures : gouvernement (M. Andrésol) et programme d'Etzer Émile"),
            ("table", M.drop(columns=["url"])),
            ("h1", "4. Points de contrôle"),
            ("table", PC.assign(departement=PC.adm1_pcode.map(G.NOM_DEP))[["nom", "type", "departement", "institutions", "mesure_programme_etzer"]]),
        ]

    panneau_exports("secu", "Plan de sécurité territorial d'Haïti", "Gouvernement de transition (M. Andrésol) et programme d'Etzer Émile, projetés sur les 10 départements",
                    blocs, {"mesures": M, "departements": D, "points_controle": PC},
                    sources="voteetzer.ht/priorite/securite ; Le Placentin (4 févr. 2026) ; Le Nouvelliste (janv. et mars 2026) ; HaitiLibre (mars 2026).")

pied("<a href='https://voteetzer.ht/priorite/securite'>voteetzer.ht</a> ; "
     "<a href='https://leplacentin.com/post/04-02-2026-securite-publique-entre-promesses-et-realite-le-plan-de-mario-andresol-peine-a-convaincre'>Le Placentin</a> ; "
     "<a href='https://lenouvelliste.com/en/article/265683/fadh-new-military-doctrine-deployment-of-the-makandal-class-and-training-of-1200-soldiers'>Le Nouvelliste</a> ; "
     "<a href='https://mail.haitilibre.com/en/news-47164-2026-2027-action-plan-of-the-haitian-ministry-of-defense.html'>HaitiLibre</a>.")
