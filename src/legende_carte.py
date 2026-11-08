"""Légende de carte Folium toujours lisible (texte sombre sur fond clair).

La légende est dessinée à l'intérieur de la carte (iframe) : le thème sombre
de Streamlit ne peut donc plus la rendre blanche sur blanc.

    from src.legende_carte import ajouter_legende, LEGENDE_RESSOURCES
    ajouter_legende(m, LEGENDE_RESSOURCES)
"""
from __future__ import annotations

import html

from branca.element import Element

LEGENDE_RESSOURCES = [
    ("point", "#c2410c", "Mines"),
    ("point", "#15803d", "Agriculture"),
    ("point", "#0369a1", "Pêche & mer"),
    ("point", "#7c3aed", "Énergie & eau"),
    ("point", "#be185d", "Nature & tourisme"),
    ("ligne", "#2563eb", "Rivières"),
    ("triangle", "#7c2d12", "Sommets / mornes"),
]


def _symbole(forme: str, couleur: str) -> str:
    if forme == "ligne":
        return f'<span style="display:inline-block;width:18px;height:3px;background:{couleur};vertical-align:middle;border-radius:2px"></span>'
    if forme == "triangle":
        return f'<span style="display:inline-block;width:0;height:0;border-left:7px solid transparent;border-right:7px solid transparent;border-bottom:12px solid {couleur};vertical-align:middle"></span>'
    return f'<span style="display:inline-block;width:12px;height:12px;border-radius:50%;background:{couleur};border:1px solid rgba(0,0,0,.25);vertical-align:middle"></span>'


def ajouter_legende(carte, elements=LEGENDE_RESSOURCES, titre: str = "Légende", position: str = "bottomleft"):
    vertical, horizontal = ("bottom", "left") if position == "bottomleft" else ("top", "right")
    lignes = "".join(
        f'<div style="display:flex;align-items:center;gap:8px;margin:4px 0;color:#1f2937 !important">'
        f'<span style="width:18px;text-align:center">{_symbole(f, c)}</span>'
        f'<span style="color:#1f2937 !important">{html.escape(t)}</span></div>'
        for f, c, t in elements
    )
    bloc = f"""
    <div style="position:absolute;{vertical}:24px;{horizontal}:12px;z-index:9999;
                background:rgba(255,255,255,.96);color:#1f2937 !important;
                padding:10px 14px;border-radius:10px;box-shadow:0 2px 10px rgba(0,0,0,.35);
                font:14px/1.3 system-ui,-apple-system,'Segoe UI',sans-serif;min-width:170px">
      <div style="font-weight:700;margin-bottom:6px;color:#111827 !important">{html.escape(titre)}</div>
      {lignes}
    </div>"""
    carte.get_root().html.add_child(Element(bloc))
    return carte
