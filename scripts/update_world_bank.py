"""Télécharge les valeurs les plus récentes des indicateurs Banque mondiale pour Haïti (API v2, sans clé).

Usage :
    python scripts/update_world_bank.py          # indicateurs clés (~65)
    python scripts/update_world_bank.py --tous   # tous les indicateurs du catalogue (~600, plus long)
Résultat : data/live/wb_live.csv  (code, indicateur_en, annee, valeur, date_maj)
"""
from __future__ import annotations

import argparse
import sys
from datetime import date
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from scripts.maj_commun import LIVE, get, journaliser  # noqa: E402
from src.indicateurs import INDICATEURS_CLES  # noqa: E402
from src.utils import PROCESSED  # noqa: E402

API = "https://api.worldbank.org/v2/country/HTI/indicator/{code}"


def parse(payload) -> list[dict]:
    """Réponse API : [métadonnées, [ {indicator:{id,value}, date, value, ...}, ... ]]"""
    if not isinstance(payload, list) or len(payload) < 2 or not payload[1]:
        return []
    out = []
    for o in payload[1]:
        if o.get("value") is None:
            continue
        out.append({"code": o["indicator"]["id"], "indicateur_en": o["indicator"]["value"],
                    "annee": int(o["date"]), "valeur": float(o["value"])})
    return out


MIROIRS = {  # repli si l'API est inaccessible : miroirs GitHub des séries Banque mondiale (datahub.io)
    "SP.POP.TOTL": ("Population, total", "https://raw.githubusercontent.com/datasets/population/main/data/population.csv"),
    "NY.GDP.MKTP.CD": ("GDP (current US$)", "https://raw.githubusercontent.com/datasets/gdp/main/data/gdp.csv"),
}


def via_miroirs() -> list[dict]:
    import io
    rows = []
    for code, (lib, url) in MIROIRS.items():
        try:
            d = pd.read_csv(io.StringIO(get(url).text))
            d = d[d["Country Code"] == "HTI"]
            rows += [{"code": code, "indicateur_en": lib, "annee": int(a), "valeur": float(v)} for a, v in zip(d.Year, d.Value)]
        except Exception as e:
            print(f"  ! miroir {code} : {e}")
    return rows


def main(tous: bool = False) -> int:
    codes = list(INDICATEURS_CLES)
    if tous:
        cat = pd.read_csv(PROCESSED / "wb_catalogue.csv")
        codes = sorted(set(codes) | set(cat.code))
    rows, erreurs = [], 0
    for i, code in enumerate(codes, 1):
        try:
            r = get(API.format(code=code), params={"format": "json", "per_page": 200, "date": "1960:2030"})
            rows += parse(r.json())
        except Exception as e:  # un indicateur en échec ne bloque pas les autres
            erreurs += 1
            print(f"  ! {code} : {e}")
        if i % 20 == 0:
            print(f"  {i}/{len(codes)} indicateurs…")
        if i == 3 and not rows:  # API manifestement inaccessible : inutile d'insister
            print("  API Banque mondiale inaccessible → miroirs GitHub")
            erreurs = len(codes)
            break
    source = "API"
    if not rows:
        rows, source = via_miroirs(), "miroir GitHub"
    if not rows:
        journaliser("Banque mondiale (API)", "échec", 0, f"{erreurs} erreurs, aucune donnée")
        return 1
    df = pd.DataFrame(rows).sort_values(["code", "annee"])
    df["date_maj"] = date.today().isoformat()
    ancien = LIVE / "wb_live.csv"
    if ancien.exists():  # on conserve les séries déjà téléchargées pour les codes non rafraîchis
        old = pd.read_csv(ancien)
        df = pd.concat([df, old[~old.code.isin(df.code)]], ignore_index=True)
    df.to_csv(ancien, index=False)
    recent = int(df.annee.max())
    journaliser(f"Banque mondiale ({source})", "ok" if source == "API" else "partiel", len(df),
                f"{df.code.nunique()} indicateurs, jusqu'à {recent}")
    return 0


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--tous", action="store_true")
    sys.exit(main(ap.parse_args().tous))
