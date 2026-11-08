"""Photos de personnalités : fichier téléversé par l'administrateur, sinon image libre de Wikipédia (Wikimedia Commons).

L'image Wikipédia est récupérée via l'API publique REST (résumé de page) et affichée avec son crédit.
"""
from __future__ import annotations

import urllib.parse

import requests
import streamlit as st

from src.medias import EXT_IMG, UPLOADS, slug


def photo_locale(nom: str):
    d = UPLOADS / "contributions"
    for ext in EXT_IMG:
        p = d / f"{slug(nom)}{ext}"
        if p.exists():
            return p
    return None


UA = {"User-Agent": "AyitiDataHub/1.0 (plateforme de données sur Haïti)"}


def _resume(lang: str, titre: str):
    r = requests.get(f"https://{lang}.wikipedia.org/api/rest_v1/page/summary/{urllib.parse.quote(titre.replace(' ', '_'))}",
                     headers=UA, timeout=6)
    if r.status_code != 200:
        return None, None
    js = r.json()
    if js.get("type") == "disambiguation":
        return None, None
    return (js.get("thumbnail") or {}).get("source"), (js.get("content_urls") or {}).get("desktop", {}).get("page")


def _chercher(lang: str, nom: str) -> str | None:
    r = requests.get(f"https://{lang}.wikipedia.org/w/api.php", headers=UA, timeout=6,
                     params={"action": "query", "list": "search", "srsearch": nom, "srlimit": 1, "format": "json"})
    hits = r.json().get("query", {}).get("search", []) if r.status_code == 200 else []
    return hits[0]["title"] if hits else None


@st.cache_data(show_spinner=False, ttl=7 * 24 * 3600)
def photo_wikipedia(titre: str, nom: str = "") -> tuple[str | None, str | None]:
    """(url de la photo, url de la page) : titre Wikipédia donné, sinon recherche par nom (FR puis EN)."""
    page_trouvee = None
    for lang in ("fr", "en"):
        try:
            if titre:
                img, page = _resume(lang, titre)
                page_trouvee = page_trouvee or page
                if img:
                    return img, page
            if nom:
                t = _chercher(lang, nom)
                if t:
                    img, page = _resume(lang, t)
                    page_trouvee = page_trouvee or page
                    if img:
                        return img, page
        except Exception:
            pass
    return None, page_trouvee


def initiales(nom: str, couleur: str = "#00209F", hauteur: int = 120) -> str:
    ini = "".join(m[0] for m in nom.replace("-", " ").split()[:2]).upper()
    return (f"<div style='width:100%;height:{hauteur}px;border-radius:12px;background:{couleur};display:flex;"
            f"align-items:center;justify-content:center;color:white;font-family:Fraunces,serif;font-size:2.2rem;"
            f"opacity:.9'>{ini}</div>")


def vignette(src: str, credit: str = "", hauteur: int = 260) -> str:
    """Photo recadrée à hauteur fixe (cartes alignées), visage privilégié en haut de l'image."""
    cap = f"<div style='font-size:.7rem;color:#8a8984;margin-top:.2rem'>{credit}</div>" if credit else ""
    return (f"<img src='{src}' alt='' loading='lazy' style='width:100%;height:{hauteur}px;object-fit:cover;"
            f"object-position:50% 20%;border-radius:12px;display:block'/>{cap}")


def fichier_en_data_uri(p) -> str:
    import base64
    ext = p.suffix.lower().strip(".")
    mime = {"jpg": "jpeg", "jpeg": "jpeg", "png": "png", "webp": "webp", "gif": "gif"}.get(ext, "jpeg")
    return f"data:image/{mime};base64,{base64.b64encode(p.read_bytes()).decode()}"
