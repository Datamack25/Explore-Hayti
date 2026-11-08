"""Correction globale du « blanc sur blanc » en thème sombre.

À appeler une fois en haut de Accueil.py (et de chaque page si elles sont
lancées seules) :

    from src.theme_fix import appliquer_contraste
    appliquer_contraste()

Tout bloc HTML maison qui a un fond clair reçoit un texte sombre. Les cartes
Folium sont dans des iframes : pour leur légende, utiliser
src/legende_carte.py.
"""
import streamlit as st

_CSS = """
<style>
[style*="background:white"], [style*="background: white"],
[style*="background:#fff"], [style*="background: #fff"],
[style*="background-color:white"], [style*="background-color: white"],
[style*="background-color:#fff"], [style*="background-color: #fff"],
[style*="rgba(255,255,255,0.9"], [style*="rgba(255, 255, 255, 0.9"],
.carte-claire, .legende-claire {
  color: #1f2937 !important;
}
[style*="background:white"] *, [style*="background: white"] *,
[style*="background:#fff"] *, [style*="background: #fff"] *,
[style*="background-color:white"] *, [style*="background-color: white"] *,
[style*="background-color:#fff"] *, [style*="background-color: #fff"] *,
.carte-claire *, .legende-claire * {
  color: #1f2937 !important;
}
/* Infobulles et popups Leaflet affichées hors iframe */
.leaflet-popup-content, .leaflet-tooltip { color: #1f2937 !important; }
</style>
"""


def appliquer_contraste() -> None:
    st.markdown(_CSS, unsafe_allow_html=True)
