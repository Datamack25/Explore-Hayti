"""Intègre l'export OpenStreetMap (HOT / oex) des établissements d'enseignement : 7 366 points GPS sur tout le pays,
déjà rattachés aux P-codes. Comble la couverture partielle de la cartographie scolaire 2022 (4 départements).

Usage :  python scripts/integrer_education_osm.py [chemin.gpkg]
Produit : data/processed/etablissements_education_osm.csv
Complète : data/processed/communes.csv et departements.csv (colonnes *_osm)
Licence : © contributeurs OpenStreetMap, ODbL.
"""
from __future__ import annotations

import sqlite3
import struct
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from shapely import wkb

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.utils import PROCESSED, RAW  # noqa: E402

GPKG = RAW / "osm" / "hotosm_hti_education_facilities.gpkg"

TYPE = {"school": "École", "kindergarten": "Préscolaire", "college": "Institut / collège supérieur",
        "university": "Université"}


def geom_point(blob: bytes) -> tuple[float, float]:
    """GeoPackage binary -> (lat, lon) du point ou du centroïde."""
    flags = blob[3]
    env = (flags >> 1) & 0b111
    taille_env = {0: 0, 1: 32, 2: 48, 3: 48, 4: 64}.get(env, 0)
    g = wkb.loads(blob[8 + taille_env:])
    p = g if g.geom_type == "Point" else g.representative_point()
    return round(p.y, 6), round(p.x, 6)


def secteur(op: str | None) -> str:
    o = op.lower() if isinstance(op, str) else ""
    if not o:
        return "Non renseigné"
    if any(k in o for k in ("relig", "congreg", "congr")):
        return "Confessionnel"
    if any(k in o for k in ("communaut", "community", "ngo")):
        return "Communautaire / ONG"
    if o.startswith(("public", "government_facility-public", "government", "publique")):
        return "Public"
    if any(k in o for k in ("private", "privé", "prive")):
        return "Privé"
    return "Autre"


def main(src: Path = GPKG) -> pd.DataFrame:
    con = sqlite3.connect(src)
    d = pd.read_sql("select geom, id, name, name_fr, name_ht, amenity, building, operator_type, capacity_persons, addr_city, "
                    "adm1_pcode, adm2_pcode, adm3_pcode, adm3_name from education_facilities", con)
    # objets sans « amenity » mais tagués building=school… : bâtiments scolaires (souvent cartographiés après
    # les séismes, parfois sans nom) — conservés à part pour ne pas créer de doublons dans les comptages
    bat = d.amenity.isna() & d.building.isin(TYPE)
    d.loc[bat, "amenity"] = "batiment"
    d = d[d.amenity.isin(list(TYPE) + ["batiment"])].copy()
    ll = d.geom.map(geom_point)
    d["lat"], d["lon"] = [x[0] for x in ll], [x[1] for x in ll]
    d["type"] = d.amenity.map({**TYPE, "batiment": "Bâtiment scolaire"})
    d["secteur"] = d.operator_type.map(secteur)
    d["nom"] = d.name.fillna(d.name_fr).fillna(d.name_ht)
    d["nom_renseigne"] = d.nom.notna()
    d["nom"] = d.nom.fillna(d.type + " (sans nom dans OSM)")
    com = pd.read_csv(PROCESSED / "communes.csv")
    d = d.merge(com[["adm2_pcode", "commune", "departement"]], on="adm2_pcode", how="left")
    out = d[["nom", "type", "secteur", "operator_type", "capacity_persons", "commune", "adm2_pcode", "departement",
             "adm1_pcode", "adm3_name", "lat", "lon", "nom_renseigne", "id"]].rename(
        columns={"id": "osm_id", "adm3_name": "section_communale", "capacity_persons": "capacite"})
    out["source"] = "OpenStreetMap / HOT (export oex du 05/10/2026, ODbL)"
    out.to_csv(PROCESSED / "etablissements_education_osm.csv", index=False)

    # agrégats par commune et département
    g = out.groupby("adm2_pcode")
    agg = pd.DataFrame({"nb_etab_education_osm": g.size(),
                        "nb_ecoles_osm": g.type.apply(lambda s: s.isin(["École", "Préscolaire"]).sum()),
                        "nb_superieur_osm": g.type.apply(lambda s: s.isin(["Université", "Institut / collège supérieur"]).sum()),
                        "nb_batiments_scolaires_osm": g.type.apply(lambda s: (s == "Bâtiment scolaire").sum())})
    agg["nb_etab_education_osm"] -= agg["nb_batiments_scolaires_osm"]
    com = com.drop(columns=[c for c in com.columns if c.endswith("_osm")], errors="ignore").merge(
        agg, left_on="adm2_pcode", right_index=True, how="left")
    for c in agg.columns:
        com[c] = com[c].fillna(0).astype(int)
    com["ecoles_osm_pour_1000_enfants"] = (1000 * com.nb_ecoles_osm / com.enfants).round(2)
    com.to_csv(PROCESSED / "communes.csv", index=False)
    dep = pd.read_csv(PROCESSED / "departements.csv")
    dep = dep.drop(columns=[c for c in dep.columns if c.endswith("_osm")], errors="ignore").merge(
        com.groupby("adm1_pcode")[list(agg.columns)].sum(), left_on="adm1_pcode", right_index=True, how="left")
    dep["ecoles_osm_pour_1000_enfants"] = (1000 * dep.nb_ecoles_osm / dep.enfants).round(2)
    dep.to_csv(PROCESSED / "departements.csv", index=False)
    print(f"✓ {len(out)} établissements · {out.adm2_pcode.nunique()} communes · "
          f"{(com.nb_etab_education_osm == 0).sum()} communes sans point OSM")
    print(out.type.value_counts().to_string())
    return out


if __name__ == "__main__":
    main(Path(sys.argv[1]) if len(sys.argv) > 1 else GPKG)
