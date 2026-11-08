import pandas as pd
import streamlit as st
import streamlit.components.v1 as components
from streamlit_folium import st_folium

from src import gouvernance as G
from src.exports_doc import panneau_exports
from src.ui import analyse_box, entete, kpis, note, pied, setup

setup("Gouvernance électronique", "🏛️")
entete("Gouvernance électronique : la pyramide et le calque territorial",
       "Qui fait quoi, qui rend compte à qui, qui contrôle qui — de la section communale au sommet de l'État, "
       "sur la base de la Constitution de 1987 amendée et des décrets de décentralisation de 2006.")

A, R, PC = G.acteurs(), G.relations(), G.points_controle()
Q = G.quadrillage()
kpis([
    {"lab": "Départements", "val": "10", "sub": "délégué + Conseil + BED + direction PNH", "style": "accent"},
    {"lab": "Arrondissements", "val": "42", "sub": "vice-délégués"},
    {"lab": "Communes", "val": "146", "sub": f"{Q.communes.sum()} dans les limites CNIGS cartographiées"},
    {"lab": "Sections communales", "val": f"{Q.sections.sum()}", "sub": "CASEC + ASEC"},
    {"lab": "Points focaux à former", "val": f"{Q.points_focaux_numeriques.sum()}", "sub": "1 par mairie + 1 par CASEC", "style": "alert"},
    {"lab": "Points de contrôle", "val": f"{len(PC)}", "sub": "frontières, ports, aéroports, axes"},
])
note("Cette architecture est une <b>proposition</b> d'Ayiti Data Hub. Elle numérise les circuits que la Constitution et les décrets "
     "de 2006 prévoient déjà ; elle ne crée aucun pouvoir nouveau. Un nouveau projet de Constitution étant en discussion, les "
     "niveaux et les circuits sont stockés dans des fichiers CSV modifiables (data/curated/gouvernance_*.csv). Les numéros "
     "d'articles sont à vérifier sur le texte publié au <i>Moniteur</i>.")

t_pyr, t_map, t_rel, t_quad, t_pc, t_garde, t_exp = st.tabs([
    "🔺 Pyramide", "🗺️ Calque sur la carte", "🔀 Relations & flux", "📐 Quadrillage", "🚧 Points de contrôle",
    "🛡️ Garde-fous & feuille de route", "📥 Exports"])

with t_pyr:
    st.markdown("Cliquez sur un étage ou sur un organe transversal pour voir son rôle, à qui il rend compte, qui le contrôle, "
                "sa base légale et ses flux d'information.")
    components.html(G.pyramide_html(A, R), height=760, scrolling=True)
    with st.expander("Tableau complet des acteurs"):
        st.dataframe(A.drop(columns=["id"]), hide_index=True, use_container_width=True,
                     column_config={"source": st.column_config.LinkColumn("source")})

with t_map:
    st.markdown("Activez ou masquez les calques en haut à droite de la carte. Cliquez sur un département, une mairie ou un point "
                "de contrôle pour afficher sa fiche.")
    choix = st.multiselect("Calques à charger", ["Flux de rapports", "Mairies (146 communes)", "Chefs-lieux", "Points de contrôle"],
                           default=["Flux de rapports", "Chefs-lieux", "Points de contrôle"])
    cle = {"Flux de rapports": "rapports", "Mairies (146 communes)": "communes", "Chefs-lieux": "chefs", "Points de contrôle": "controle"}
    st_folium(G.carte_calques("gouvernance", tuple(cle[c] for c in choix)), height=640, use_container_width=True, returned_objects=[])
    st.caption("Traits bleus : rapports mensuels commune → chef-lieu (délégué). Traits rouges : synthèses départementales → MICT et "
               "Centre national de gouvernance électronique (Port-au-Prince). Les sections communales n'ont pas de coordonnées "
               "dans les données CNIGS : leur nombre apparaît dans la fiche de chaque mairie.")

with t_rel:
    st.plotly_chart(G.sankey_relations(A, R), use_container_width=True)
    typ = st.multiselect("Type de relation", sorted(R.type.unique()), default=sorted(R.type.unique()))
    lab = dict(zip(A.id, A.sigle))
    rr = R[R.type.isin(typ)].assign(de=lambda d: d.source.map(lab), vers=lambda d: d.cible.map(lab))
    st.dataframe(rr[["de", "vers", "type", "contenu", "frequence", "canal", "base_legale"]], hide_index=True, use_container_width=True)
    analyse_box("Les trois circuits", [
        "**Circuit administratif (montant)** : CASEC → mairie → vice-délégué → délégué → MICT → Primature. Fréquence : hebdomadaire "
        "à la base, mensuelle au-dessus.",
        "**Circuit sécurité** : commissariat → direction départementale PNH → MJSP → centre national d'opérations ; FAd'H → "
        "ministère de la Défense. Les forces voient les incidents et les zones, pas les données nominatives.",
        "**Circuit de contrôle (transversal)** : CSCCA (comptes), OPC (abus et accès aux données), ULCC/UCREF (corruption, "
        "financement des gangs), Parlement. Chaque organe a un accès en lecture, journalisé.",
    ])

with t_quad:
    st.markdown("#### Maillage par département")
    st.dataframe(Q, hide_index=True, use_container_width=True,
                 column_config={"population": st.column_config.NumberColumn(format="%d")})
    st.markdown("#### Trois rôles à chaque niveau")
    c1, c2, c3 = st.columns(3)
    c1.markdown("<div class='ay-card'><h4>✍️ Responsable légal</h4><p>Signe et engage sa responsabilité : CASEC, maire, "
                "vice-délégué, délégué.</p></div>", unsafe_allow_html=True)
    c2.markdown("<div class='ay-card'><h4>📱 Point focal numérique</h4><p>Saisit et synchronise les rapports ; agent formé et "
                "payé sur le FGDCT.</p></div>", unsafe_allow_html=True)
    c3.markdown("<div class='ay-card'><h4>🚔 Référent sécurité</h4><p>Commissariat ou sous-commissariat PNH de la zone ; "
                "valide les incidents.</p></div>", unsafe_allow_html=True)
    st.markdown("#### Le rapport hebdomadaire d'un CASEC (7 rubriques, en créole et en français)")
    st.dataframe(pd.DataFrame({
        "rubrique": ["Sécurité", "État civil", "Santé", "Agriculture & élevage", "Catastrophes", "Conflits fonciers", "Finances locales"],
        "exemples de champs": ["incidents, routes coupées, présence armée", "naissances, décès déclarés", "cas signalés, centre de santé ouvert ?",
                               "semis, récoltes, prix au marché, maladies animales", "inondations, glissements, familles touchées",
                               "litiges ouverts / réglés", "recettes du marché, dépenses"],
        "canal": ["appli hors ligne · SMS/USSD · radio"] * 7}), hide_index=True, use_container_width=True)

with t_pc:
    typ = st.multiselect("Type", sorted(PC.type.unique()), default=sorted(PC.type.unique()), key="typ_pc")
    p = PC[PC.type.isin(typ)].assign(departement=lambda d: d.adm1_pcode.map(G.NOM_DEP))
    st.dataframe(p[["nom", "type", "departement", "commune", "institutions", "flux_suivis", "mesure_programme_etzer", "source"]],
                 hide_index=True, use_container_width=True, column_config={"source": st.column_config.LinkColumn("source")})
    analyse_box("Qui entre, qui sort, quoi entre, quoi sort", [
        "**Personnes** : DIE aux aéroports, ports et 5 postes frontaliers officiels (Ouanaminthe, Thomassique, Belladère, Malpasse, Anse-à-Pitres). On enregistre les flux ; on ne restreint pas la "
        "sortie ou le retour des Haïtiens (Constitution, art. 41-1).",
        "**Marchandises** : AGD (SYDONIA), APN, DGI. Alertes automatiques sur les écarts entre volumes déclarés et observés, et sur "
        "les produits sensibles (armes, munitions, carburant).",
        "**Argent** : UCREF reçoit les signalements liés au commerce illicite et au financement des gangs.",
    ])

with t_garde:
    c1, c2 = st.columns(2)
    with c1:
        analyse_box("Garde-fous indispensables", [
            "**Séparation des données** : statistiques et incidents pour la sécurité ; données nominatives seulement sur réquisition "
            "judiciaire, journalisée.",
            "**Loi sur la protection des données personnelles** à adopter avant le module « mobilité » (art. 49 : secret de la "
            "correspondance).",
            "**Contrôle externe** : journaux d'accès audités par l'OPC et la CSCCA.",
            "**Interdiction du profilage** politique ou religieux, inscrite dans le texte de création.",
            "**Hébergement souverain et chiffré**, copie de secours hors de Port-au-Prince ; interopérabilité de type X-Road.",
        ])
    with c2:
        st.dataframe(pd.DataFrame({
            "phase": ["0-6 mois", "6-18 mois", "18-36 mois"],
            "contenu": ["Cadre juridique, référentiel territorial, pilote dans 1 département (rapports + projets)",
                        "4-5 départements ; population/état civil, sécurité et crises ; formation des points focaux",
                        "Couverture nationale ; douanes et DIE branchées ; tableau de bord public"],
        }), hide_index=True, use_container_width=True)

with t_exp:
    st.markdown("Le document exporté reprend la pyramide, la carte, le quadrillage, les relations et les points de contrôle.")

    def blocs():
        lab = dict(zip(A.id, A.sigle))
        return [
            ("h1", "1. La pyramide institutionnelle"),
            ("img", G.fig_pyramide(A), "Pyramide : étages territoriaux et organes transversaux"),
            ("table", A[["etage", "acteur", "sigle", "nombre", "rapporte_a", "controle_par", "base_legale"]]),
            ("h1", "2. Le calque territorial"),
            ("img", G.fig_carte("gouvernance"), "Maillage, flux de rapports et points de contrôle"),
            ("h1", "3. Le quadrillage par département"),
            ("table", Q),
            ("h1", "4. Relations et flux d'information"),
            ("table", R.assign(source=R.source.map(lab), cible=R.cible.map(lab))[["source", "cible", "type", "contenu", "frequence", "canal"]]),
            ("h1", "5. Points de contrôle des flux"),
            ("table", PC.assign(departement=PC.adm1_pcode.map(G.NOM_DEP))[["nom", "type", "departement", "institutions", "flux_suivis"]]),
            ("h1", "6. Garde-fous"),
            ("ul", ["Séparation des données ; accès nominatif sur réquisition judiciaire, journalisé.",
                    "Loi sur la protection des données personnelles avant le module mobilité.",
                    "Journaux d'accès audités par l'OPC et la CSCCA.", "Interdiction du profilage politique ou religieux.",
                    "Hébergement souverain, chiffré, avec copie de secours hors de Port-au-Prince."]),
        ]

    panneau_exports("gouv", "Gouvernance électronique d'Haïti", "Pyramide, calque territorial, relations et points de contrôle",
                    blocs, {"acteurs": A, "relations": R, "points_controle": PC, "quadrillage": Q},
                    sources="Constitution de 1987 amendée ; décrets du 1er février 2006 ; CNIGS/HDX (limites) ; programme d'Etzer Émile "
                            "(voteetzer.ht) ; presse haïtienne.")

pied("Constitution de 1987 amendée ; décrets de décentralisation du 1er février 2006 ; projet de décret électoral (CEP, avril 2026) ; "
     "CNIGS / HDX (limites administratives) ; voteetzer.ht (projets localisés).")
