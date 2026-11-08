"""Photos depuis Internet pour la Galerie des départements.

- Sélection de belles photos par lieu (data/images_lieux.csv) qui remplace les
  images trouvées automatiquement (parfois des photos de catastrophes).
- Recherche de photos libres de droits sur Wikimedia Commons.
- Ajout / remplacement de photos par l'administrateur (data/photos_ajoutees.csv,
  fichiers enregistrés dans assets/img/departements/ajouts).
- Téléchargement des photos (une par une ou album ZIP).
"""
from __future__ import annotations

import html
import io
import re
import zipfile
from datetime import datetime
from pathlib import Path
from urllib.parse import quote, unquote, urlparse

import pandas as pd
import requests

RACINE = Path(__file__).resolve().parent.parent
CSV_CHOIX = RACINE / "data" / "images_lieux.csv"
CSV_AJOUTS = RACINE / "data" / "photos_ajoutees.csv"
DOSSIER_AJOUTS = RACINE / "assets" / "img" / "departements" / "ajouts"
COLS_AJOUTS = ["departement", "legende", "image_url", "page", "auteur", "licence", "fichier_local", "ajoute_le"]

API_COMMONS = "https://commons.wikimedia.org/w/api.php"
ENTETES = {"User-Agent": "ExploreHayti/1.0 (application Streamlit educative sur Haiti)"}
EXT_OK = (".jpg", ".jpeg", ".png", ".webp")


# ---------------------------------------------------------------- lecture
def _lire(path: Path, cols: list[str] | None = None) -> pd.DataFrame:
    if path.exists():
        try:
            return pd.read_csv(path, dtype=str).fillna("")
        except Exception:
            pass
    return pd.DataFrame(columns=cols or [])


def photos_choisies() -> dict[str, dict]:
    """Photos sélectionnées à la main, indexées par légende (nom du lieu)."""
    df = _lire(CSV_CHOIX)
    if df.empty or "lieu" not in df:
        return {}
    return {r["lieu"].strip(): r.to_dict() for _, r in df.iterrows()}


def photos_ajoutees() -> pd.DataFrame:
    return _lire(CSV_AJOUTS, COLS_AJOUTS)


def chemin_ajout(nom: str) -> Path | None:
    if not nom:
        return None
    p = DOSSIER_AJOUTS / nom
    return p if p.exists() else None


# ---------------------------------------------------------------- recherche
def _texte(v: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "", html.unescape(v or ""))).strip()


def rechercher_commons(requete: str, n: int = 12) -> list[dict]:
    """Cherche des photos sur Wikimedia Commons (licences libres uniquement)."""
    params = {
        "action": "query", "format": "json", "generator": "search",
        "gsrsearch": f"{requete} filetype:bitmap", "gsrnamespace": 6, "gsrlimit": n,
        "prop": "imageinfo", "iiprop": "url|mime|extmetadata", "iiurlwidth": 640,
    }
    r = requests.get(API_COMMONS, params=params, headers=ENTETES, timeout=20)
    r.raise_for_status()
    pages = r.json().get("query", {}).get("pages", {})
    sortie = []
    for pg in sorted(pages.values(), key=lambda p: p.get("index", 0)):
        info = (pg.get("imageinfo") or [{}])[0]
        if info.get("mime") not in ("image/jpeg", "image/png", "image/webp"):
            continue
        meta = info.get("extmetadata", {})
        sortie.append({
            "titre": pg.get("title", "").removeprefix("File:").removeprefix("Fichier:"),
            "miniature": info.get("thumburl") or info.get("url"),
            "image_url": info.get("url"),
            "page": info.get("descriptionurl"),
            "auteur": _texte(meta.get("Artist", {}).get("value", "")) or "Auteur sur la page source",
            "licence": _texte(meta.get("LicenseShortName", {}).get("value", "")) or "Licence sur la page source",
            "description": _texte(meta.get("ImageDescription", {}).get("value", ""))[:160],
        })
    return sortie


def infos_depuis_lien(lien: str) -> dict:
    """Accepte un lien de page Commons (…/wiki/File:…) ou un lien direct vers une image."""
    lien = lien.strip()
    m = re.search(r"commons\.wikimedia\.org/wiki/(?:File|Fichier):(.+)$", lien)
    if m:
        nom = unquote(m.group(1)).split("?")[0].split("#")[0]
        res = [x for x in rechercher_commons(f'intitle:"{Path(nom).stem}"', n=5) if x["titre"].replace(" ", "_") == nom.replace(" ", "_")]
        if res:
            return res[0]
        return {"titre": nom, "image_url": f"https://commons.wikimedia.org/wiki/Special:FilePath/{quote(nom)}",
                "page": lien, "auteur": "Auteur sur la page source", "licence": "Licence sur la page source"}
    return {"titre": Path(urlparse(lien).path).name, "image_url": lien, "page": lien,
            "auteur": "", "licence": ""}


# ---------------------------------------------------------------- téléchargement
def telecharger(url: str) -> bytes:
    r = requests.get(url, headers=ENTETES, timeout=30)
    r.raise_for_status()
    if not r.headers.get("Content-Type", "").startswith("image/"):
        raise ValueError("Le lien ne pointe pas vers une image.")
    return r.content


def _nom_fichier(dep: str, legende: str, url: str) -> str:
    ext = Path(urlparse(url).path).suffix.lower()
    ext = ext if ext in EXT_OK else ".jpg"
    base = re.sub(r"[^a-z0-9]+", "_", f"{dep}_{legende}".lower().encode("ascii", "ignore").decode()).strip("_")
    return f"{base[:60]}{ext}"


def ajouter_photo(departement: str, legende: str, image_url: str, page: str, auteur: str, licence: str) -> str:
    """Télécharge la photo dans le projet et l'enregistre pour ce lieu (remplace l'ancienne)."""
    donnees = telecharger(image_url)
    DOSSIER_AJOUTS.mkdir(parents=True, exist_ok=True)
    nom = _nom_fichier(departement, legende, image_url)
    (DOSSIER_AJOUTS / nom).write_bytes(donnees)
    df = photos_ajoutees()
    df = df[~((df.departement == departement) & (df.legende == legende))]
    ligne = dict(departement=departement, legende=legende, image_url=image_url, page=page, auteur=auteur,
                 licence=licence, fichier_local=nom, ajoute_le=datetime.now().strftime("%Y-%m-%d %H:%M"))
    df = pd.concat([df, pd.DataFrame([ligne])], ignore_index=True)[COLS_AJOUTS]
    CSV_AJOUTS.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(CSV_AJOUTS, index=False)
    return nom


def retirer_photo(departement: str, legende: str) -> None:
    df = photos_ajoutees()
    garde = ~((df.departement == departement) & (df.legende == legende))
    for nom in df.loc[~garde, "fichier_local"]:
        p = chemin_ajout(nom)
        if p:
            p.unlink(missing_ok=True)
    df[garde].to_csv(CSV_AJOUTS, index=False)


def album_zip(elements: list[dict]) -> tuple[bytes, int]:
    """elements : dicts avec 'nom', et 'chemin' (fichier local) ou 'url'. Renvoie (zip, nb d'images)."""
    buf, n = io.BytesIO(), 0
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        credits = ["departement;legende;auteur;licence;source"]
        for e in elements:
            try:
                data = Path(e["chemin"]).read_bytes() if e.get("chemin") else telecharger(e["url"])
            except Exception:
                continue
            z.writestr(e["nom"], data)
            credits.append(";".join(str(e.get(k, "")).replace(";", ",") for k in ("departement", "legende", "auteur", "licence", "page")))
            n += 1
        z.writestr("CREDITS.csv", "\n".join(credits))
    return buf.getvalue(), n


# ---------------------------------------------------------------- affichage
def carte_html(image_url: str, lien: str, legende: str, credit: str = "") -> str:
    """Photo cliquable (ouvre la source dans un nouvel onglet) avec légende lisible."""
    l, i = html.escape(lien or image_url, quote=True), html.escape(image_url, quote=True)
    return f"""
<a href="{l}" target="_blank" rel="noopener" style="display:block;text-decoration:none;border-radius:12px;overflow:hidden;
   border:1px solid rgba(128,128,128,.35);margin-bottom:4px">
  <img src="{i}" alt="{html.escape(legende, quote=True)}" loading="lazy"
       style="width:100%;height:220px;object-fit:cover;display:block">
</a>
<div style="font-size:.9rem;line-height:1.35;margin-bottom:2px"><strong>{html.escape(legende)}</strong></div>
<div style="font-size:.75rem;opacity:.75;margin-bottom:4px">{html.escape(credit)}</div>"""


def carte_sans_photo(legende: str, lien: str) -> str:
    return f"""
<a href="{html.escape(lien, quote=True)}" target="_blank" rel="noopener"
   style="display:flex;flex-direction:column;justify-content:center;gap:6px;height:220px;padding:18px;border-radius:12px;
   text-decoration:none;background:linear-gradient(135deg,#1e3a5f,#12324a 60%,#0f5257);color:#e7eef8;margin-bottom:4px">
  <span style="font-size:26px">📍</span>
  <span style="font-size:1.05rem;font-weight:700;color:#ffffff">{html.escape(legende)}</span>
  <span style="font-size:.85rem;color:#8fd3ff">Voir les photos ↗</span>
</a>"""
