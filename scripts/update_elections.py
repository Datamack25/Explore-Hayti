"""Mise à jour du module Élections (bouton de l'application + action GitHub).

1. Veille de presse : Google Actualités (FR, EN, créole) + flux des médias haïtiens déjà collectés,
   requêtes générales (« élections Haïti CEP »…) et une requête par candidat.
   -> data/live/elections_actualites.csv  (thème, tonalité, candidats cités)
   -> data/live/elections_mentions.csv    (nombre d'articles et tonalité moyenne par candidat)
2. Filtrage des sanctions (méthode LCB-FT) : listes officielles publiques et gratuites
   OFAC SDN (États-Unis), liste consolidée du Conseil de sécurité de l'ONU, LMES (Canada).
   Correspondance approchée des noms (similarité ≥ 0,85) -> data/live/elections_screening.csv
3. Programmes : si un site internet est renseigné pour un candidat, le texte de la page est récupéré
   -> data/live/elections_programmes_textes.csv (puis noté automatiquement /100 dans l'application)
4. Alerte calendrier : signale dans le journal les articles qui évoquent un nouveau calendrier du CEP.

Usage :  python scripts/update_elections.py [--sans-sanctions]
"""
from __future__ import annotations

import argparse
import csv
import io
import re
import sys
import unicodedata
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone
from difflib import SequenceMatcher
from pathlib import Path
from urllib.parse import quote_plus

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from scripts.maj_commun import LIVE, get, journaliser  # noqa: E402
from scripts.update_news import parse_flux  # noqa: E402
from src.utils import CURATED  # noqa: E402
from src.veille import etiquette, theme, tonalite  # noqa: E402

F_ACTU = LIVE / "elections_actualites.csv"
F_MENT = LIVE / "elections_mentions.csv"
F_SCR = LIVE / "elections_screening.csv"
F_PROG = LIVE / "elections_programmes_textes.csv"
GN = "https://news.google.com/rss/search?q={q}&hl={hl}&gl=HT&ceid=HT:{ceid}"
REQUETES = [("élections Haïti CEP", "fr", "fr"), ("candidat présidentielle Haïti", "fr", "fr"),
            ("Haiti election CEP candidates", "en", "en"), ("eleksyon Ayiti KEP", "fr", "fr"),
            ("Haïti calendrier électoral 2027", "fr", "fr"), ("Hayti élections", "fr", "fr")]
MOTIF_ELEC = re.compile(r"élect|elect|eleksyon|scrutin|\bcep\b|\bkep\b|candidat|présidentiel|presidential|vote|électeur|campagne", re.I)
MOTIF_CAL = re.compile(r"calendrier|calendar|report|postpone|nouvelle date|new date", re.I)


def _n(s: str) -> str:
    s = unicodedata.normalize("NFKD", str(s)).encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z ]", " ", s).split()


def _sim(a: str, b: str) -> float:
    """Similarité de noms insensible à l'ordre des mots (Jean Michel / Michel Jean)."""
    ta, tb = sorted(_n(a)), sorted(_n(b))
    if not ta or not tb:
        return 0.0
    return SequenceMatcher(None, " ".join(ta), " ".join(tb)).ratio()


def candidats() -> pd.DataFrame:
    return pd.read_csv(CURATED / "elections_candidats.csv", dtype=str).fillna("")


def alias(r) -> list[str]:
    noms = {r.nom, r.nom_cep} - {""}
    toks = r.nom.split()
    if len(toks) >= 2:
        noms.add(f"{toks[0]} {toks[-1]}")
    return sorted(noms)


# ---------------------------------------------------------------- 1. presse
def veille(c: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for q, hl, ceid in REQUETES:
        try:
            rows += parse_flux(get(GN.format(q=quote_plus(q), hl=hl, ceid=ceid), tries=2, timeout=25).content,
                               "Google Actualités", hl, "Recherche")
        except Exception as e:
            print(f"  ! {q} : {str(e)[:100]}")
    for r in c.itertuples():
        q = f'"{r.nom}" Haïti'
        try:
            rows += parse_flux(get(GN.format(q=quote_plus(q), hl="fr", ceid="fr"), tries=1, timeout=20).content,
                               "Google Actualités", "fr", "Candidat")
        except Exception:
            pass
    # articles déjà collectés par la veille générale de la plateforme
    gen = LIVE / "actualites.csv"
    if gen.exists():
        g = pd.read_csv(gen)
        g = g[(g.titre.fillna("") + " " + g.resume.fillna("")).str.contains(MOTIF_ELEC)]
        rows += g[["date", "titre", "resume", "source", "url"]].assign(langue="", origine="Veille générale", flux="").to_dict("records")
    if not rows:
        return pd.DataFrame()
    df = pd.DataFrame(rows).rename(columns={"url": "lien"})
    df["resume"] = df.resume.fillna("")
    txt = df.titre + " " + df.resume
    df = df[txt.str.contains(MOTIF_ELEC) | (df.origine == "Candidat")]
    txt = (df.titre + " " + df.resume).map(lambda t: " ".join(_n(t)))
    ids = []
    for t in txt:
        trouves = [r.id for r in c.itertuples() if any(" ".join(_n(a)) in t for a in alias(r) if len(_n(a)) >= 2)]
        ids.append(";".join(trouves))
    df["candidats"] = ids
    df["theme"] = [theme(a, b) for a, b in zip(df.titre, df.resume)]
    df["score_tonalite"] = [tonalite(a, b) for a, b in zip(df.titre, df.resume)]
    df["tonalite"] = df.score_tonalite.map(etiquette)
    df["sanction_citee"] = (df.titre + " " + df.resume).str.contains(r"sanction|ofac|gel des avoirs|blacklist", case=False)
    df["collecte_utc"] = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M")
    if F_ACTU.exists():
        df = pd.concat([df, pd.read_csv(F_ACTU)], ignore_index=True)
    df["cle"] = df.titre.str.lower().str.replace(r"[^a-z0-9]", "", regex=True).str[:90]
    df = df.sort_values("date", ascending=False).drop_duplicates("cle").drop(columns="cle").head(2000)
    df.to_csv(F_ACTU, index=False)
    return df


def mentions(df: pd.DataFrame, c: pd.DataFrame) -> None:
    lim = (datetime.now(timezone.utc) - timedelta(days=60)).strftime("%Y-%m-%d")
    rows = []
    for r in c.itertuples():
        d = df[df.candidats.fillna("").str.contains(rf"(^|;){re.escape(r.id)}($|;)")]
        d60 = d[d.date.astype(str) >= lim]
        rows.append({"candidat_id": r.id, "nb_articles": len(d60), "nb_articles_total": len(d),
                     "tonalite_moy": round(d60.score_tonalite.mean(), 2) if len(d60) else 0.0,
                     "articles_sanctions": int(d.sanction_citee.sum()) if len(d) else 0,
                     "date_maj": datetime.now(timezone.utc).strftime("%Y-%m-%d")})
    pd.DataFrame(rows).to_csv(F_MENT, index=False)


# ---------------------------------------------------------------- 2. sanctions
def liste_ofac() -> list[tuple[str, str]]:
    t = get("https://www.treasury.gov/ofac/downloads/sdn.csv", tries=2, timeout=90).text
    out = []
    for row in csv.reader(io.StringIO(t)):
        if len(row) > 3 and row[2].strip('" ').lower() == "individual":
            nom = row[1]
            if "," in nom:  # « MARTELLY, Joseph Michel » -> « Joseph Michel MARTELLY »
                a, b = nom.split(",", 1)
                nom = f"{b.strip()} {a.strip()}"
            out.append((nom, row[3]))
    return out


def liste_onu() -> list[tuple[str, str]]:
    root = ET.fromstring(get("https://scsanctions.un.org/resources/xml/en/consolidated.xml", tries=2, timeout=90).content)
    out = []
    for ind in root.iter("INDIVIDUAL"):
        nom = " ".join(filter(None, [ind.findtext(t) for t in ("FIRST_NAME", "SECOND_NAME", "THIRD_NAME")]))
        out.append((nom, ind.findtext("UN_LIST_TYPE") or ""))
    return out


def liste_canada() -> list[tuple[str, str]]:
    url = ("https://www.international.gc.ca/world-monde/assets/office_docs/international_relations-relations_internationales/"
           "sanctions/sema-lmes.xml")
    root = ET.fromstring(get(url, tries=2, timeout=90).content)
    out = []
    for rec in root.iter("record"):
        nom = f"{rec.findtext('GivenName') or ''} {rec.findtext('LastName') or ''}".strip()
        if nom:
            out.append((nom, rec.findtext("Country") or ""))
    return out


def filtrage(c: pd.DataFrame) -> int:
    listes = {}
    for nom, f in (("OFAC SDN", liste_ofac), ("ONU", liste_onu), ("Canada LMES", liste_canada)):
        try:
            listes[nom] = f()
            print(f"  {nom} : {len(listes[nom])} personnes")
        except Exception as e:
            print(f"  ! {nom} : {str(e)[:100]}")
    if not listes:
        return -1
    rows = []
    for r in c.itertuples():
        jetons = {t for a in alias(r) for t in _n(a) if len(t) >= 4}
        for liste, entrees in listes.items():
            pool = [(n, p) for n, p in entrees if jetons & set(_n(n))]  # pré-filtre : au moins un mot du nom en commun
            best = max(((max(_sim(a, n) for a in alias(r)), n, p) for n, p in pool), default=(0, "", ""))
            if best[0] >= 0.85:
                rows.append({"candidat_id": r.id, "candidat": r.nom, "liste": liste, "nom_liste": best[1],
                             "programme": best[2], "score_similarite": round(best[0], 3),
                             "date_controle": datetime.now(timezone.utc).strftime("%Y-%m-%d")})
    pd.DataFrame(rows, columns=["candidat_id", "candidat", "liste", "nom_liste", "programme", "score_similarite",
                                "date_controle"]).to_csv(F_SCR, index=False)
    return len(rows)


# ---------------------------------------------------------------- 3. programmes
def programmes(c: pd.DataFrame) -> int:
    rows = []
    for r in c[c.site_web != ""].itertuples():
        try:
            h = get(r.site_web, tries=1, timeout=30).text
            h = re.sub(r"(?is)<(script|style|nav|footer).*?</\1>", " ", h)
            t = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", h)).strip()
            if len(t) > 300:
                rows.append({"candidat_id": r.id, "url_programme": r.site_web,
                             "date_collecte": datetime.now(timezone.utc).strftime("%Y-%m-%d"), "texte": t[:60000]})
        except Exception as e:
            print(f"  ! site de {r.nom} : {str(e)[:80]}")
    if rows:
        pd.DataFrame(rows).to_csv(F_PROG, index=False)
    return len(rows)


def main(sans_sanctions: bool = False) -> int:
    c = candidats()
    print("== Élections : veille de presse ==")
    df = veille(c)
    if df.empty:
        journaliser("Élections – presse", "échec", 0, "aucune source joignable")
    else:
        mentions(df, c)
        recents = df[df.collecte_utc == df.collecte_utc.max()]
        cal = recents[recents.titre.str.contains(MOTIF_CAL) & recents.titre.str.contains(r"cep|élection|election", case=False)]
        msg = f"{int((df.candidats.fillna('') != '').sum())} articles citent un candidat"
        if len(cal):
            msg += f" · ALERTE calendrier possible : « {cal.titre.iloc[0][:120]} » — vérifier data/curated/elections_calendrier.csv"
        journaliser("Élections – presse", "ok", len(df), msg)
    if not sans_sanctions:
        print("== Élections : filtrage des listes de sanctions ==")
        n = filtrage(c)
        journaliser("Élections – listes de sanctions", "échec" if n < 0 else "ok", max(n, 0),
                    "OFAC SDN, ONU, Canada LMES" if n >= 0 else "listes injoignables")
    print("== Élections : programmes en ligne ==")
    n = programmes(c)
    journaliser("Élections – programmes", "ok", n, f"{n} programme(s) récupéré(s) sur les sites des candidats")
    return 0


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--sans-sanctions", action="store_true")
    sys.exit(main(ap.parse_args().sans_sanctions))
