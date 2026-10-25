"""Ayiti Data Hub — point d'entrée et menu de navigation.

Lancer :  streamlit run Accueil.py

Les noms de fichiers des pages sont volontairement en ASCII (sans emoji ni accent) pour éviter les caractères
illisibles après décompression sous Windows ; les icônes et titres affichés sont définis ici.
"""
import streamlit as st


def P(fichier: str, titre: str, icone: str, defaut: bool = False) -> st.Page:
    return st.Page(f"pages/{fichier}", title=titre, icon=icone, default=defaut)


navigation = st.navigation({
    "": [P("00_accueil.py", "Accueil", "🏠", defaut=True)],
    "Territoire & population": [
        P("01_carte_interactive.py", "Carte interactive", "🗺️"),
        P("02_fiche_commune.py", "Fiche commune", "🏘️"),
        P("05_population.py", "Population & territoire", "👥"),
        P("12_iles.py", "Les îles", "🏝️"),
        P("13_routes_et_transports.py", "Routes & transports", "🛣️"),
    ],
    "Institutions & société": [
        P("03_institutions.py", "Écoles, universités & institutions", "🏫"),
        P("06_humanitaire.py", "Humanitaire", "🆘"),
        P("19_diaspora.py", "Diaspora", "🌍"),
    ],
    "Économie & richesses": [
        P("04_economie.py", "Économie & finances", "📈"),
        P("10_richesses_et_ressources.py", "Richesses & ressources", "💎"),
        P("11_bien_vivre_et_tourisme.py", "Bien vivre & tourisme", "🌴"),
    ],
    "Culture & histoire": [
        P("18_histoire_et_solidarite.py", "Histoire & solidarité", "📜"),
        P("21_contributions_au_monde.py", "Contributions au monde", "🌟"),
        P("15_sport.py", "Sport", "⚽"),
        P("16_konpa_et_musique.py", "Konpa & musique", "🎶"),
        P("17_gastronomie.py", "Gastronomie", "🍲"),
    ],
    "Analyses & outils": [
        P("07_analyses_ia.py", "Analyses & machine learning", "🤖"),
        P("14_rapports_pdf_et_images.py", "Rapports PDF & images", "📄"),
        P("08_actualites_et_mises_a_jour.py", "Actualités & mises à jour", "🔄"),
        P("09_explorateur_de_donnees.py", "Explorateur de données", "🗂️"),
        P("20_administration.py", "Administration", "🔐"),
    ],
}, expanded=True)
navigation.run()
