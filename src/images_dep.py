"""Images des 10 départements : catalogue (data/curated/images_departements.csv), téléchargement depuis
Wikipédia / Wikimedia Commons (licences libres), crédits enregistrés dans assets/img/departements/credits.csv.

Le téléchargement se fait avec :  python scripts/telecharger_images_departements.py
Tant qu'une image n'est pas téléchargée, l'application l'affiche directement depuis Wikimedia (lien).
"""
from __future__ import annotations

import csv
import re
import time
import urllib.parse
from pathlib import Path

import pandas as pd
import requests

from src.utils import ASSETS, CURATED

DOSSIER = ASSETS / "img" / "departements"
CREDITS = DOSSIER / "credits.csv"
UA = {"User-Agent": "AyitiDataHub/1.0 (plateforme de données ouvertes sur Haïti; contact via GitHub)"}
LARGEUR = 1280


def catalogue() -> pd.DataFrame:
    return pd.read_csv(CURATED / "images_departements.csv")


def credits() -> pd.DataFrame:
    return pd.read_csv(CREDITS) if CREDITS.exists() else pd.DataFrame(columns=["fichier", "titre_fichier", "auteur", "licence", "page"])


def chemin_local(fichier: str) -> Path | None:
    p = DOSSIER / fichier
    return p if p.exists() and p.stat().st_size > 2000 else None


def _resume(lang: str, titre: str) -> dict | None:
    r = requests.get(f"https://{lang}.wikipedia.org/api/rest_v1/page/summary/{urllib.parse.quote(titre.replace(' ', '_'))}",
                     headers=UA, timeout=15)
    if r.status_code != 200:
        return None
    js = r.json()
    return None if js.get("type") == "disambiguation" else js


def _chercher(lang: str, q: str) -> str | None:
    r = requests.get(f"https://{lang}.wikipedia.org/w/api.php", headers=UA, timeout=15,
                     params={"action": "query", "list": "search", "srsearch": q, "srlimit": 1, "format": "json"})
    hits = r.json().get("query", {}).get("search", []) if r.status_code == 200 else []
    return hits[0]["title"] if hits else None


def trouver_image(titre: str) -> dict | None:
    """Renvoie {'source', 'page', 'fichier_commons'} pour l'image principale de l'article (FR puis EN, puis recherche)."""
    essais = [("fr", titre), ("en", titre)]
    for lang, t in essais:
        js = _resume(lang, t)
        if not js or not (js.get("originalimage") or js.get("thumbnail")):
            t2 = _chercher(lang, f"{titre} Haïti" if lang == "fr" else f"{titre} Haiti")
            js = _resume(lang, t2) if t2 else None
        if js and (js.get("originalimage") or js.get("thumbnail")):
            src = (js.get("originalimage") or js.get("thumbnail"))["source"]
            nom = urllib.parse.unquote(src.split("/")[-1])
            nom = re.sub(r"^\d+px-", "", nom)
            return {"source": src, "page": (js.get("content_urls") or {}).get("desktop", {}).get("page", ""),
                    "fichier_commons": nom, "miniature": (js.get("thumbnail") or {}).get("source", src)}
    return None


def _info_commons(nom_fichier: str) -> dict:
    r = requests.get("https://commons.wikimedia.org/w/api.php", headers=UA, timeout=20, params={
        "action": "query", "titles": f"File:{nom_fichier}", "prop": "imageinfo", "iiprop": "url|extmetadata",
        "iiurlwidth": LARGEUR, "format": "json"})
    pages = r.json().get("query", {}).get("pages", {}) if r.status_code == 200 else {}
    for p in pages.values():
        ii = (p.get("imageinfo") or [{}])[0]
        md = ii.get("extmetadata", {})
        auteur = re.sub(r"<[^>]+>", "", md.get("Artist", {}).get("value", "")).strip()
        return {"url": ii.get("thumburl") or ii.get("url"), "auteur": auteur[:120],
                "licence": md.get("LicenseShortName", {}).get("value", ""), "page": ii.get("descriptionurl", "")}
    return {}


def telecharger_tout(forcer: bool = False, journal=print) -> tuple[int, int]:
    """Télécharge toutes les images du catalogue absentes. Renvoie (réussites, échecs)."""
    DOSSIER.mkdir(parents=True, exist_ok=True)
    cat = catalogue()
    cred = credits()
    ok = ko = 0
    for r in cat.itertuples():
        dest = DOSSIER / r.fichier
        if dest.exists() and not forcer:
            ok += 1
            continue
        try:
            im = trouver_image(r.titre_wikipedia)
            if not im:
                journal(f"  - aucune image pour « {r.titre_wikipedia} »")
                ko += 1
                continue
            info = _info_commons(im["fichier_commons"])
            url = info.get("url") or im["source"]
            data = requests.get(url, headers=UA, timeout=60).content
            if len(data) < 2000:
                raise RuntimeError("fichier trop petit")
            dest.write_bytes(data)
            cred = cred[cred.fichier != r.fichier]
            cred = pd.concat([cred, pd.DataFrame([{"fichier": r.fichier, "titre_fichier": im["fichier_commons"],
                                                   "auteur": info.get("auteur", ""), "licence": info.get("licence", ""),
                                                   "page": info.get("page") or im["page"]}])], ignore_index=True)
            journal(f"  ✓ {r.departement} — {r.legende} ({info.get('licence', '?')})")
            ok += 1
            time.sleep(0.5)  # politesse envers les serveurs Wikimedia
        except Exception as e:  # une image en échec n'arrête pas les autres
            journal(f"  ! {r.titre_wikipedia} : {e}")
            ko += 1
    cred.to_csv(CREDITS, index=False, quoting=csv.QUOTE_MINIMAL)
    return ok, ko
