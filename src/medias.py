"""Médias d'une rubrique : images (fichiers téléversés ou liens), vidéos et liens externes.

Sources : data/curated/medias.csv (géré depuis l'espace administrateur) et assets/uploads/<rubrique>/.
"""
from __future__ import annotations

import re

import pandas as pd
import streamlit as st

from src.utils import ASSETS, CURATED

UPLOADS = ASSETS / "uploads"
EXT_IMG = (".jpg", ".jpeg", ".png", ".webp", ".gif")


def slug(t: str) -> str:
    import unicodedata
    t = unicodedata.normalize("NFKD", t).encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z0-9]+", "_", t).strip("_")


def medias(rubrique: str) -> pd.DataFrame:
    p = CURATED / "medias.csv"
    d = pd.read_csv(p) if p.exists() else pd.DataFrame(columns=["rubrique", "titre", "type", "url", "credit"])
    return d[d.rubrique == rubrique]


def _youtube_id(url: str) -> str | None:
    m = re.search(r"(?:youtu\.be/|v=|/embed/|/shorts/)([A-Za-z0-9_-]{11})", url or "")
    return m.group(1) if m else None


def galerie(rubrique: str, colonnes: int = 3) -> None:
    """Affiche images téléversées, images par lien, vidéos (intégrées si lien YouTube direct) et liens."""
    dossier = UPLOADS / slug(rubrique)
    fichiers = sorted(p for p in dossier.glob("*") if p.suffix.lower() in EXT_IMG) if dossier.exists() else []
    d = medias(rubrique)
    imgs = d[d.type == "image"]
    if fichiers or len(imgs):
        st.markdown("#### 🖼️ Images")
        cols = st.columns(colonnes)
        i = 0
        for p in fichiers:
            with cols[i % colonnes]:
                st.image(str(p), caption=p.stem.replace("_", " "), use_container_width=True)
            i += 1
        for r in imgs.itertuples():
            with cols[i % colonnes]:
                st.image(r.url, caption=f"{r.titre}" + (f" — {r.credit}" if isinstance(r.credit, str) and r.credit else ""),
                         use_container_width=True)
            i += 1
    vids = d[d.type == "video"]
    if len(vids):
        st.markdown("#### 🎬 Vidéos")
        integ = [r for r in vids.itertuples() if _youtube_id(r.url)]
        if integ:
            cols = st.columns(min(colonnes, 2))
            for j, r in enumerate(integ):
                with cols[j % len(cols)]:
                    st.video(r.url)
                    st.caption(r.titre)
        for r in vids.itertuples():
            if not _youtube_id(r.url):
                st.markdown(f"▶️ [{r.titre}]({r.url})")
    liens = d[d.type == "lien"]
    if len(liens):
        st.markdown("#### 🔗 Pour en savoir plus")
        for r in liens.itertuples():
            st.markdown(f"- [{r.titre}]({r.url})")
    st.caption("Les administrateurs peuvent ajouter des images, des vidéos et des liens depuis la page 🔐 Administration.")
