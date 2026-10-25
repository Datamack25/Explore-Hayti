"""Télécharge depuis OpenStreetMap (API Overpass, gratuite) les institutions de tout le territoire haïtien :
écoles, universités, hôpitaux, cliniques, pharmacies, police, tribunaux, mairies, banques, bibliothèques…

Chaque point est rattaché automatiquement à sa commune et à son département (P-codes) par
intersection avec les contours communaux.

Usage :  python scripts/update_osm.py
Résultat : data/live/osm_institutions.csv
Licence des données : © contributeurs OpenStreetMap, ODbL.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from scripts.maj_commun import LIVE, journaliser, post  # noqa: E402
from src.utils import GEO, PROCESSED  # noqa: E402

SERVEURS = ["https://overpass-api.de/api/interpreter",
            "https://overpass.kumi.systems/api/interpreter",
            "https://maps.mail.ru/osm/tools/overpass/api/interpreter"]

# tag OSM -> (catégorie plateforme, type en français)
TYPES = {
    ("amenity", "school"): ("École", "École"),
    ("amenity", "kindergarten"): ("École", "Préscolaire"),
    ("amenity", "college"): ("Université / Enseignement supérieur", "Institut / collège supérieur"),
    ("amenity", "university"): ("Université / Enseignement supérieur", "Université"),
    ("amenity", "hospital"): ("Santé", "Hôpital"),
    ("amenity", "clinic"): ("Santé", "Clinique / centre de santé"),
    ("amenity", "doctors"): ("Santé", "Cabinet médical"),
    ("amenity", "pharmacy"): ("Santé", "Pharmacie"),
    ("healthcare", "centre"): ("Santé", "Centre de santé"),
    ("amenity", "police"): ("Sécurité & justice", "Police"),
    ("amenity", "courthouse"): ("Sécurité & justice", "Tribunal"),
    ("amenity", "prison"): ("Sécurité & justice", "Prison"),
    ("amenity", "fire_station"): ("Sécurité & justice", "Pompiers"),
    ("amenity", "townhall"): ("Administration locale", "Mairie / hôtel de ville"),
    ("office", "government"): ("Administration de l'État", "Bureau gouvernemental"),
    ("amenity", "embassy"): ("Administration de l'État", "Ambassade"),
    ("office", "diplomatic"): ("Administration de l'État", "Représentation diplomatique"),
    ("amenity", "bank"): ("Finance", "Banque"),
    ("amenity", "bureau_de_change"): ("Finance", "Bureau de change"),
    ("amenity", "money_transfer"): ("Finance", "Transfert d'argent"),
    ("amenity", "library"): ("Culture & services", "Bibliothèque"),
    ("tourism", "museum"): ("Culture & services", "Musée"),
    ("amenity", "post_office"): ("Culture & services", "Bureau de poste"),
    ("amenity", "marketplace"): ("Culture & services", "Marché"),
    ("amenity", "community_centre"): ("Culture & services", "Centre communautaire"),
    ("office", "ngo"): ("Culture & services", "ONG"),
}


def requete() -> str:
    parts = "".join(f'nwr["{k}"="{v}"](area.ht);' for (k, v) in TYPES)
    return f'[out:json][timeout:300];area["ISO3166-1"="HT"][admin_level=2]->.ht;({parts});out center tags;'


def classer(tags: dict) -> tuple[str, str] | None:
    for (k, v), res in TYPES.items():
        if tags.get(k) == v:
            return res
    return None


def rattacher(df: pd.DataFrame) -> pd.DataFrame:
    """Ajoute adm2_pcode / commune / departement par point-dans-polygone."""
    from shapely.geometry import Point, shape
    from shapely.strtree import STRtree

    geo = json.load(open(GEO / "communes.geojson", encoding="utf-8"))
    polys = [shape(f["geometry"]) for f in geo["features"]]
    ids = [f["id"] for f in geo["features"]]
    tree = STRtree(polys)
    pcs = []
    for lat, lon in zip(df.lat, df.lon):
        pt, found = Point(lon, lat), None
        for i in tree.query(pt):
            if polys[i].contains(pt):
                found = ids[i]
                break
        if found is None:  # point en mer / sur la frontière : commune la plus proche
            found = ids[int(tree.nearest(pt))]
        pcs.append(found)
    df["adm2_pcode"] = pcs
    com = pd.read_csv(PROCESSED / "communes.csv")[["adm2_pcode", "commune", "departement"]]
    return df.merge(com, on="adm2_pcode", how="left")


def parse(payload: dict) -> pd.DataFrame:
    rows = []
    for el in payload.get("elements", []):
        tags = el.get("tags", {})
        cl = classer(tags)
        if not cl:
            continue
        lat = el.get("lat") or el.get("center", {}).get("lat")
        lon = el.get("lon") or el.get("center", {}).get("lon")
        if lat is None or lon is None:
            continue
        nom = tags.get("name") or tags.get("name:fr") or tags.get("name:ht") or f"{cl[1]} (sans nom)"
        rows.append({"nom": nom, "categorie": cl[0], "type": cl[1], "sous_type": cl[1],
                     "operateur": tags.get("operator", ""), "statut_osm": tags.get("operator:type", ""),
                     "telephone": tags.get("phone", tags.get("contact:phone", "")),
                     "site_web": tags.get("website", tags.get("contact:website", "")),
                     "lat": round(float(lat), 6), "lon": round(float(lon), 6),
                     "osm_id": f"{el['type']}/{el['id']}",
                     "source": "OpenStreetMap (ODbL)"})
    return pd.DataFrame(rows)


def main() -> int:
    q = requete()
    payload, err = None, ""
    for url in SERVEURS:
        try:
            payload = post(url, {"data": q}, tries=2, timeout=400).json()
            break
        except Exception as e:
            err = str(e)
            print(f"  ! {url} : {e}")
    if payload is None:
        journaliser("OpenStreetMap (Overpass)", "échec", 0, err)
        return 1
    df = parse(payload)
    if df.empty:
        journaliser("OpenStreetMap (Overpass)", "échec", 0, "réponse vide")
        return 1
    df = rattacher(df).drop_duplicates(subset=["osm_id"])
    df.to_csv(LIVE / "osm_institutions.csv", index=False)
    resume = ", ".join(f"{k} : {v}" for k, v in df.categorie.value_counts().items())
    journaliser("OpenStreetMap (Overpass)", "ok", len(df), resume)
    return 0


if __name__ == "__main__":
    sys.exit(main())
