"""Collecte des signaux de popularité en ligne des candidats (bouton « Mettre à jour » de l'onglet Popularité).

Sources gratuites, sans compte :
- GDELT DOC 2.0 (médias en ligne du monde entier) : volume d'articles 90 jours + tonalité moyenne ;
- Wikipédia (API Wikimedia des pages vues) : consultations sur 30 jours en français, anglais et créole ;
- Reddit et Bluesky (recherche publique) : publications des 30 derniers jours ;
- YouTube (facultatif) : vidéos des 30 derniers jours si la variable YOUTUBE_API_KEY est définie (clé gratuite Google Cloud).
Facebook, X (Twitter), TikTok et WhatsApp, très utilisés en Haïti, n'ont pas d'API publique gratuite : ils ne sont pas couverts.

Résultats : data/live/elections_popularite_signaux.csv + historique des probabilités (elections_popularite_historique.csv)
Usage :  python scripts/update_popularite.py [--avec-presse]   (--avec-presse relance d'abord la veille de presse électorale)
"""
from __future__ import annotations

import argparse
import os
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import quote

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from scripts.maj_commun import LIVE, get, journaliser  # noqa: E402
from src import popularite as P  # noqa: E402
from src.utils import CURATED  # noqa: E402

AUJ = datetime.now(timezone.utc)
GDELT = "https://api.gdeltproject.org/api/v2/doc/doc"
WIKI_PV = "https://wikimedia.org/api/rest_v1/metrics/pageviews/per-article/{p}/all-access/user/{t}/daily/{a}/{b}"


def _secret(nom: str) -> str:
    v = os.environ.get(nom, "")
    if not v:
        try:
            import tomllib
            f = Path(__file__).resolve().parents[1] / ".streamlit" / "secrets.toml"
            v = tomllib.loads(f.read_text()).get(nom, "") if f.exists() else ""
        except Exception:
            v = ""
    return v


def gdelt(nom: str) -> dict:
    out = {"gdelt_90j": 0, "gdelt_14j": 0, "gdelt_14j_avant": 0, "gdelt_ton": 0.0}
    q = f'"{nom}"'
    try:
        js = get(GDELT, params={"query": q, "mode": "timelinevolraw", "timespan": "3months", "format": "json"},
                 tries=2, timeout=40).json()
        data = pd.DataFrame(js["timeline"][0]["data"])
        data["date"] = pd.to_datetime(data.date.str[:8])
        out["gdelt_90j"] = int(data.value.sum())
        lim = pd.Timestamp(AUJ.date()) - pd.Timedelta(days=14)
        out["gdelt_14j"] = int(data[data.date >= lim].value.sum())
        out["gdelt_14j_avant"] = int(data[(data.date < lim) & (data.date >= lim - pd.Timedelta(days=14))].value.sum())
    except Exception as e:
        print(f"    GDELT volume {nom} : {str(e)[:80]}")
    time.sleep(5.5)  # GDELT limite à une requête toutes les 5 secondes
    if out["gdelt_90j"]:
        try:
            js = get(GDELT, params={"query": q, "mode": "timelinetone", "timespan": "3months", "format": "json"},
                     tries=2, timeout=40).json()
            v = [x["value"] for x in js["timeline"][0]["data"] if x.get("value")]
            out["gdelt_ton"] = round(sum(v) / len(v), 2) if v else 0.0
        except Exception as e:
            print(f"    GDELT tonalité {nom} : {str(e)[:80]}")
        time.sleep(5.5)
    return out


def titre_wiki(projet: str, nom: str) -> str:
    """Cherche la page Wikipédia du candidat ; n'accepte que si le titre contient le nom de famille et un prénom."""
    try:
        js = get(f"https://{projet}/w/api.php", params={"action": "query", "list": "search", "srsearch": nom, "format": "json",
                                                       "srlimit": 3}, tries=1, timeout=20).json()
        toks = [t.lower() for t in nom.replace("-", " ").split() if len(t) > 2]
        for r in js["query"]["search"]:
            t = r["title"].lower()
            if toks and toks[-1] in t and any(x in t for x in toks[:-1]):
                return r["title"]
    except Exception:
        pass
    return ""


def wikipedia(nom: str, forces: dict) -> tuple[int, str]:
    a, b = (AUJ - timedelta(days=31)).strftime("%Y%m%d"), (AUJ - timedelta(days=1)).strftime("%Y%m%d")
    total, pages = 0, []
    for projet in ("fr.wikipedia.org", "en.wikipedia.org", "ht.wikipedia.org"):
        t = forces.get(projet) or titre_wiki(projet, nom)
        if not t:
            continue
        try:
            js = get(WIKI_PV.format(p=projet, t=quote(t.replace(" ", "_"), safe=""), a=a, b=b), tries=1, timeout=20).json()
            n = sum(i["views"] for i in js.get("items", []))
            total += n
            pages.append(f"{projet.split('.')[0]}:{t}")
        except Exception:
            pass
    return total, " | ".join(pages)


def reddit(nom: str) -> int:
    try:
        js = get("https://www.reddit.com/search.json", params={"q": f'"{nom}"', "sort": "new", "t": "month", "limit": 100},
                 tries=1, timeout=20).json()
        return len(js.get("data", {}).get("children", []))
    except Exception:
        return 0


def bluesky(nom: str) -> int:
    depuis = (AUJ - timedelta(days=30)).strftime("%Y-%m-%dT%H:%M:%SZ")
    for base in ("https://api.bsky.app", "https://public.api.bsky.app"):
        try:
            js = get(f"{base}/xrpc/app.bsky.feed.searchPosts", params={"q": f'"{nom}"', "since": depuis, "limit": 100},
                     tries=1, timeout=20).json()
            return len(js.get("posts", []))
        except Exception:
            continue
    return 0


def youtube(nom: str, cle: str) -> int:
    if not cle:
        return 0
    try:
        js = get("https://www.googleapis.com/youtube/v3/search", params={
            "part": "id", "q": f'"{nom}"', "type": "video", "maxResults": 50, "key": cle,
            "publishedAfter": (AUJ - timedelta(days=30)).strftime("%Y-%m-%dT%H:%M:%SZ")}, tries=1, timeout=20).json()
        return int(js.get("pageInfo", {}).get("totalResults", 0))
    except Exception:
        return 0


def main(avec_presse: bool = False) -> int:
    if avec_presse:
        from scripts import update_elections
        update_elections.main(sans_sanctions=True)
    c = pd.read_csv(CURATED / "elections_candidats.csv", dtype=str).fillna("")
    cfg_f = CURATED / "elections_popularite_config.csv"
    cfg = pd.read_csv(cfg_f, dtype=str).fillna("").set_index("candidat_id") if cfg_f.exists() else pd.DataFrame()
    cle_yt = _secret("YOUTUBE_API_KEY")
    rows = []
    for r in c.itertuples():
        conf = cfg.loc[r.id] if r.id in cfg.index else {}
        req = (conf.get("requete") if len(conf) else "") or r.nom
        forces = {"fr.wikipedia.org": conf.get("wiki_fr", "") if len(conf) else "",
                  "en.wikipedia.org": conf.get("wiki_en", "") if len(conf) else ""}
        print(f"  {r.nom}")
        w, pages = wikipedia(r.nom, forces)
        rows.append({"candidat_id": r.id, **gdelt(req), "wiki_30j": w, "wiki_pages": pages, "reddit_30j": reddit(req),
                     "bluesky_30j": bluesky(req), "youtube_30j": youtube(req, cle_yt),
                     "date_maj": AUJ.strftime("%Y-%m-%d %H:%M")})
    s = pd.DataFrame(rows)
    s.to_csv(P.F_SIGNAUX, index=False)
    d = P.charger_signaux()
    n_ok = int((s[["gdelt_90j", "wiki_30j", "reddit_30j", "bluesky_30j", "youtube_30j"]].sum(axis=1) > 0).sum())
    if P.a_des_donnees(d):
        P.enregistrer_historique(P.simuler(P.indice(d)), AUJ.strftime("%Y-%m-%d"))
    journaliser("Élections – popularité en ligne", "ok" if n_ok else "échec", n_ok,
                f"GDELT, Wikipédia, Reddit, Bluesky{', YouTube' if cle_yt else ' (YouTube : pas de clé)'} · "
                f"{n_ok}/{len(s)} candidats avec signal")
    return 0


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--avec-presse", action="store_true")
    sys.exit(main(ap.parse_args().avec_presse))
