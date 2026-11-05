"""Carte avancée : rues, satellite, relief, rivières, mornes et ressources sourcées (src/carte_avancee.py)."""
import streamlit as st

from src.carte_avancee import afficher_carte_avancee
from src.ui import entete, pied, setup

setup("Carte avancée", "🛰️")
entete("Carte avancée d'Haïti",
       "Rues, vue satellite, relief et mornes, rivières et lacs — avec les richesses et ressources localisées et sourcées.")

langue = st.session_state.get("langue", "fr")
afficher_carte_avancee(langue if langue in ("fr", "en") else "fr")

pied("© contributeurs OpenStreetMap (ODbL) · OpenTopoMap (CC-BY-SA) · Esri World Imagery · CARTO · "
     "BME, inventaire CGS/HaitiLibre, EMX, AVSF, ONU Haïti/OIT, INCAH, Wikipédia (détail par ligne dans le tableau).")
