"""Télécharge le réseau routier principal, les aéroports et les ports d'Haïti depuis OpenStreetMap (Overpass).

Usage :  python scripts/update_routes.py
Résultats : data/live/routes_osm.geojson (lignes), data/live/transports_osm.csv (aéroports, ports, gares routières)
Licence : © contributeurs OpenStreetMap, ODbL.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from scripts.maj_commun import LIVE, journaliser, post  # noqa: E402
from scripts.update_osm import SERVEURS, rattacher  # noqa: E402

CLASSES = {"motorway": "Autoroute", "trunk": "Route nationale principale", "primary": "Route nationale",
           "secondary": "Route départementale"}

Q_ROUTES = ('[out:json][timeout:300];area["ISO3166-1"="HT"][admin_level=2]->.ht;'
            'way["highway"~"^(motorway|trunk|primary|secondary)$"](area.ht);out tags geom;')
Q_TRANSPORTS = ('[out:json][timeout:200];area["ISO3166-1"="HT"][admin_level=2]->.ht;('
                'nwr["aeroway"="aerodrome"](area.ht);nwr["harbour"="yes"](area.ht);nwr["industrial"="port"](area.ht);'
                'nwr["landuse"="port"](area.ht);nwr["amenity"="ferry_terminal"](area.ht);nwr["amenity"="bus_station"](area.ht);'
                ');out center tags;')


def _requete(q: str) -> dict:
    err = ""
    for url in SERVEURS:
        try:
            return post(url, {"data": q}, tries=2, timeout=400).json()
        except Exception as e:
            err = str(e)
    raise RuntimeError(err)


def parse_routes(payload: dict) -> dict:
    feats = []
    for el in payload.get("elements", []):
        if el.get("type") != "way" or "geometry" not in el:
            continue
        t = el.get("tags", {})
        coords = [[round(p["lon"], 5), round(p["lat"], 5)] for p in el["geometry"]]
        if len(coords) < 2:
            continue
        feats.append({"type": "Feature", "geometry": {"type": "LineString", "coordinates": coords},
                      "properties": {"ref": t.get("ref", ""), "nom": t.get("name", ""),
                                     "classe": CLASSES.get(t.get("highway"), t.get("highway")),
                                     "revetement": t.get("surface", ""), "osm_id": el["id"]}})
    return {"type": "FeatureCollection", "features": feats}


def parse_transports(payload: dict) -> pd.DataFrame:
    rows = []
    for el in payload.get("elements", []):
        t = el.get("tags", {})
        lat = el.get("lat") or el.get("center", {}).get("lat")
        lon = el.get("lon") or el.get("center", {}).get("lon")
        if lat is None:
            continue
        if t.get("aeroway") == "aerodrome":
            typ = "Aéroport / aérodrome"
        elif t.get("amenity") == "ferry_terminal":
            typ = "Terminal de ferry"
        elif t.get("amenity") == "bus_station":
            typ = "Gare routière"
        else:
            typ = "Port"
        rows.append({"nom": t.get("name") or t.get("name:fr") or f"{typ} (sans nom)", "type": typ,
                     "code_iata": t.get("iata", ""), "lat": float(lat), "lon": float(lon),
                     "osm_id": f"{el['type']}/{el['id']}", "source": "OpenStreetMap (ODbL)"})
    return pd.DataFrame(rows)


def main() -> int:
    code = 0
    try:
        gj = parse_routes(_requete(Q_ROUTES))
        json.dump(gj, open(LIVE / "routes_osm.geojson", "w", encoding="utf-8"))
        journaliser("OpenStreetMap – routes", "ok", len(gj["features"]))
    except Exception as e:
        journaliser("OpenStreetMap – routes", "échec", 0, str(e))
        code = 1
    try:
        df = parse_transports(_requete(Q_TRANSPORTS))
        if not df.empty:
            df = rattacher(df)
            df.to_csv(LIVE / "transports_osm.csv", index=False)
        journaliser("OpenStreetMap – aéroports & ports", "ok", len(df))
    except Exception as e:
        journaliser("OpenStreetMap – aéroports & ports", "échec", 0, str(e))
        code = 1
    return code


if __name__ == "__main__":
    sys.exit(main())
