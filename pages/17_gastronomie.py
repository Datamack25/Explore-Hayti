import urllib.parse

import pandas as pd
import streamlit as st

from src.medias import galerie
from src.ui import analyse_box, entete, kpis, pied, setup
from src.utils import CURATED

setup("Gastronomie", "🍲")
entete("La gastronomie haïtienne", "Soup joumou, griot, diri ak djon djon, pikliz, kremas… une cuisine de liberté et de partage.")

g = pd.read_csv(CURATED / "gastronomie.csv")
kpis([
    {"lab": "Patrimoine UNESCO", "val": "Soup joumou", "sub": "inscrite en 2021", "style": "accent"},
    {"lab": "Spécialités présentées", "val": str(len(g))},
    {"lab": "Rhum Barbancourt", "val": "1862", "sub": "année de fondation"},
    {"lab": "Le plat de fête", "val": "Griot", "sub": "avec bannann peze et pikliz"},
])

cats = ["Toutes"] + sorted(g.categorie.unique())
c = st.radio("Catégorie", cats, horizontal=True)
gg = g if c == "Toutes" else g[g.categorie == c]
cols = st.columns(3)
for i, r in enumerate(gg.itertuples()):
    with cols[i % 3]:
        with st.container(border=True):
            badge = " · 🏛️ UNESCO" if isinstance(r.patrimoine, str) and r.patrimoine else ""
            st.markdown(f"#### {r.plat}{badge}")
            st.markdown(f"<span style='color:#8a8984'>{r.categorie} · {r.region}</span>", unsafe_allow_html=True)
            st.markdown(r.description)
            st.caption(f"Ingrédients : {r.ingredients}")
            q = urllib.parse.quote_plus(f"recette {r.plat} haïtien")
            st.markdown(f"[🎬 Vidéos de recette](https://www.youtube.com/results?search_query={q}) · "
                        f"[🖼️ Photos](https://www.google.com/search?tbm=isch&q={urllib.parse.quote_plus(r.plat + ' Haiti')})")

analyse_box("Une cuisine qui raconte l'histoire", [
    "La **soup joumou**, interdite aux esclaves sous la colonie, est dégustée chaque 1er janvier pour célébrer l'indépendance de 1804.",
    "La cuisine haïtienne mêle héritages **taïno, africains, français et espagnols** : épices, piment bouc, agrumes, manioc (kasav).",
    "Ses produits phares s'exportent : rhum Barbancourt, café, cacao, mangue Francisque, vétiver pour la parfumerie.",
])
galerie("Gastronomie")
pied("UNESCO (soupe joumou), connaissances culinaires générales ; liens vers des recherches de recettes en ligne.")
