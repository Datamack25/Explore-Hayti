"""Télécharge depuis OpenStreetMap (Overpass) les couches naturelles de la Carte avancée.

Usage :  python scripts/update_carte.py
Résultats : data/live/osm_cache/rivieres.json, lacs.json, sommets.json, mines.json
Licence : © contributeurs OpenStreetMap, ODbL.
"""
from __future__ import annotations

import json
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from scripts.maj_commun import LIVE, journaliser, post  # noqa: E402
from scripts.update_osm import SERVEURS  # noqa: E402

CACHE = LIVE / "osm_cache"
ZONE = 'area["ISO3166-1"="HT"][admin_level=2]->.h;'

REQUETES = {
    "rivieres": f'[out:json][timeout:180];{ZONE}(way["waterway"="river"](area.h););out tags geom;',
    "lacs": (f'[out:json][timeout:120];{ZONE}('
             'way["natural"="water"]["water"~"lake|reservoir|lagoon"](area.h);'
             'relation["natural"="water"]["water"~"lake|reservoir|lagoon"](area.h););out tags geom;'),
    "sommets": f'[out:json][timeout:90];{ZONE}(node["natural"~"peak|volcano"]["name"](area.h););out tags;',
    "mines": (f'[out:json][timeout:90];{ZONE}('
              'nwr["landuse"="quarry"](area.h);nwr["industrial"="mine"](area.h);'
              'nwr["man_made"~"mineshaft|adit"](area.h););out tags center;'),
}


def telecharger(nom: str) -> int:
    """Télécharge une couche et l'enregistre ; renvoie le nombre d'éléments."""
    err = ""
    for url in SERVEURS:
        try:
            d = post(url, {"data": REQUETES[nom]}, tries=2, timeout=300).json()
            d["_maj"] = datetime.now().strftime("%Y-%m-%d %H:%M")
            CACHE.mkdir(parents=True, exist_ok=True)
            (CACHE / f"{nom}.json").write_text(json.dumps(d), encoding="utf-8")
            return len(d.get("elements", []))
        except Exception as e:
            err = str(e)
    raise RuntimeError(err)


def main() -> bool:
    ok = True
    for nom in REQUETES:
        try:
            n = telecharger(nom)
            journaliser(f"OSM carte avancée – {nom}", "ok", n)
        except Exception as e:  # une couche en échec n'arrête pas les autres
            ok = False
            journaliser(f"OSM carte avancée – {nom}", "erreur", 0, str(e))
    return ok


if __name__ == "__main__":
    main()
