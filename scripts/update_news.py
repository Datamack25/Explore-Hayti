"""Veille d'actualités sur Haïti : médias haïtiens, diaspora et presse internationale.

Les sources sont listées dans data/curated/sources_actualites.csv (modifiable : ajouter une ligne = une source).
Les recherches utilisent les trois graphies « Haïti », « Ayiti » et « Hayti ».
Chaque article reçoit un thème (économie, politique, tourisme, culture…) et une tonalité (positif / neutre / négatif)
pour permettre à la plateforme de mettre en avant ce qui va bien.

Usage :  python scripts/update_news.py
Résultat : data/live/actualites.csv (historique glissant, dédoublonné, 1 500 articles max)
"""
from __future__ import annotations

import html
import os
import re
import sys
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from scripts.maj_commun import LIVE, get, journaliser  # noqa: E402
from src.utils import CURATED  # noqa: E402
from src.veille import etiquette, priorite, theme, tonalite  # noqa: E402

FICHIER = LIVE / "actualites.csv"
MAX_ARTICLES = 1500
MOTIF_HAITI = re.compile(r"ha[iï]ti|ayiti|hayti|port-au-prince|pòtoprens|cap-ha[iï]tien|jacmel|gona[iï]ves", re.I)
DC = "{http://purl.org/dc/elements/1.1/}"
ATOM = "{http://www.w3.org/2005/Atom}"


def _texte(x: str | None) -> str:
    x = html.unescape(re.sub(r"<[^>]+>", " ", x or ""))
    return re.sub(r"\s+", " ", x).strip()


def _date(d: str | None) -> str:
    if not d:
        return ""
    try:
        return parsedate_to_datetime(d).astimezone(timezone.utc).strftime("%Y-%m-%d %H:%M")
    except Exception:
        try:
            return datetime.fromisoformat(d.replace("Z", "+00:00")).strftime("%Y-%m-%d %H:%M")
        except Exception:
            return d[:16]


def parse_flux(contenu: bytes, source: str, langue: str, origine: str) -> list[dict]:
    """Analyse un flux RSS 2.0 ou Atom."""
    root = ET.fromstring(contenu)
    rows = []
    items = list(root.iter("item")) or list(root.iter(f"{ATOM}entry"))
    for it in items:
        titre = _texte(it.findtext("title") or it.findtext(f"{ATOM}title"))
        lien = it.findtext("link") or ""
        if not lien:
            l = it.find(f"{ATOM}link")
            lien = l.get("href") if l is not None else ""
        resume = _texte(it.findtext("description") or it.findtext(f"{ATOM}summary"))[:400]
        date = _date(it.findtext("pubDate") or it.findtext(f"{DC}date") or it.findtext(f"{ATOM}updated"))
        src_item = it.findtext("source") or source  # Google Actualités indique le média d'origine
        if not titre or not lien:
            continue
        rows.append({"date": date, "titre": titre, "resume": resume, "source": src_item.strip(), "flux": source,
                     "langue": langue, "origine": origine, "url": lien.strip()})
    return rows


def via_api_reliefweb() -> list[dict]:
    params = {"appname": os.environ.get("RELIEFWEB_APPNAME", "ayiti-data-hub"),
              "filter[field]": "country.iso3", "filter[value]": "hti", "sort[]": "date.created:desc", "limit": 40,
              "fields[include][]": ["title", "url_alias", "date.created", "source.shortname"]}
    js = get("https://api.reliefweb.int/v2/reports", params=params, tries=1, timeout=30).json()
    out = []
    for it in js.get("data", []):
        f = it.get("fields", {})
        out.append({"date": (f.get("date", {}).get("created") or "")[:16].replace("T", " "), "titre": f.get("title"),
                    "resume": "", "source": ", ".join(s.get("shortname", "") for s in f.get("source", [])),
                    "flux": "ReliefWeb API", "langue": "en", "origine": "International",
                    "url": f.get("url_alias") or f"https://reliefweb.int/node/{it.get('id')}"})
    return out


def enrichir(df: pd.DataFrame) -> pd.DataFrame:
    df["theme"] = [theme(t, r) for t, r in zip(df.titre, df.resume.fillna(""))]
    df["score_tonalite"] = [tonalite(t, r) for t, r in zip(df.titre, df.resume.fillna(""))]
    df["tonalite"] = df.score_tonalite.map(etiquette)
    df["priorite"] = [priorite(s, t) for s, t in zip(df.score_tonalite, df.theme)]
    df["parle_d_haiti"] = (df.titre + " " + df.resume.fillna("")).str.contains(MOTIF_HAITI)
    return df


def main() -> int:
    sources = pd.read_csv(CURATED / "sources_actualites.csv")
    sources = sources[sources.actif == 1]
    rows, ok, ko = [], [], []
    for s in sources.itertuples():
        try:
            r = parse_flux(get(s.url, tries=2, timeout=30).content, s.nom, s.langue, s.origine)
            rows += r
            ok.append(f"{s.nom} ({len(r)})")
        except Exception as e:
            ko.append(s.nom)
            print(f"  ! {s.nom} : {str(e)[:120]}")
    try:
        rows += via_api_reliefweb()
    except Exception:
        pass
    if not rows:
        journaliser("Actualités (multi-sources)", "échec", 0, f"{len(ko)} sources injoignables")
        return 1
    df = pd.DataFrame(rows)
    df = enrichir(df)
    # les médias haïtiens parlent d'Haïti par définition ; pour l'international on vérifie le sujet
    df = df[(df.origine != "International") | df.parle_d_haiti]
    df["collecte_utc"] = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M")
    if FICHIER.exists():
        ancien = pd.read_csv(FICHIER)
        df = pd.concat([df, ancien], ignore_index=True)
    df["cle"] = df.titre.str.lower().str.replace(r"[^a-z0-9àâçéèêëîïôûùüÿœ]", "", regex=True).str[:90]
    df = (df.sort_values("date", ascending=False).drop_duplicates("cle").drop_duplicates("url")
          .drop(columns=["cle"]).head(MAX_ARTICLES))
    df.to_csv(FICHIER, index=False)
    journaliser("Actualités (multi-sources)", "ok" if not ko else "partiel", len(df),
                f"{len(ok)} sources lues, {len(ko)} injoignables : {', '.join(ko)[:150]}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
