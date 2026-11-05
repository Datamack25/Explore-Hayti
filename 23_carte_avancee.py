"""Page : Carte avancée (rues, satellite, relief, rivières, mornes, ressources sourcées)."""
import streamlit as st

from carte_avancee import afficher_carte_avancee

# Langue : reprend celle choisie ailleurs dans l'app si elle est stockée dans la session
langue = st.session_state.get("langue", "fr")
if langue not in ("fr", "en"):
    langue = "fr"

afficher_carte_avancee(langue)
