"""Fonctions utilitaires partagées (normalisation de noms, chemins)."""
from __future__ import annotations

import re
import unicodedata
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
RAW = DATA / "raw"
PROCESSED = DATA / "processed"
CURATED = DATA / "curated"
LIVE = DATA / "live"
GEO = DATA / "geo"
ASSETS = ROOT / "assets"


def norm(txt: str) -> str:
    """Normalise un nom de lieu : minuscules, sans accents ni ponctuation.

    « Grande'Anse » -> « grandeanse », « Les Cayes » -> « cayes »,
    « Croix-Des-Bouquets » -> « croixdesbouquets ».
    """
    if txt is None:
        return ""
    s = unicodedata.normalize("NFKD", str(txt))
    s = "".join(c for c in s if not unicodedata.combining(c)).lower()
    s = re.sub(r"^(les|le|la|l')\s*", "", s.strip())
    s = re.sub(r"[^a-z0-9]", "", s)
    return s


# Alias fréquents (orthographes alternatives -> nom CNIGS normalisé)
ALIAS_COMMUNES = {
    "cayes": "cayes",
    "lescayes": "cayes",
    "caphaitien": "caphaitien",
    "leogane": "leogane",
    "deschapelles": "verrettes",
    "damien": "tabarre",
    "limonade": "limonade",
    "grandanse": "grandeanse",
    "fortliberte": "fortliberte",
}
