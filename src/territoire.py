"""Territoire : localisation des villes, îles, routes, transports, sites touristiques, littoral,
et indice « cadre de vie » par commune."""
from __future__ import annotations

import json
import math
from functools import lru_cache

import numpy as np
import pandas as pd

from src.utils import ALIAS_COMMUNES, CURATED, GEO, LIVE, PROCESSED, norm


@lru_cache(maxsize=1)
def _communes() -> pd.DataFrame:
    return pd.read_csv(PROCESSED / "communes.csv")


@lru_cache(maxsize=1)
def _localites() -> pd.DataFrame:
    return pd.read_csv(PROCESSED / "localites.csv")


def pcode_commune(nom: str) -> str | None:
    if not isinstance(nom, str) or not nom.strip():
        return None
    com = _communes()
    k = ALIAS_COMMUNES.get(norm(nom), norm(nom))
    idx = {norm(c): p for c, p in zip(com.commune, com.adm2_pcode)}
    if k in idx:
        return idx[k]
    for key, p in idx.items():
        if k and (k in key or key in k):
            return p
    return None


def localiser_ville(nom: str) -> tuple[float, float] | None:
    """Coordonnées de la ville (point OSM de type ville) sinon centre de la commune."""
    loc = _localites()
    k = norm(nom)
    villes = loc[loc.type.isin(["Capitale", "Grande ville", "Ville"])]
    m = villes[villes.nom.map(norm) == k]
    if len(m):
        return float(m.iloc[0].lat), float(m.iloc[0].lon)
    pc = pcode_commune(nom)
    if pc:
        # chef-lieu : la ville / le bourg de la commune
        sub = loc[(loc.adm2_pcode == pc) & loc.type.isin(["Capitale", "Grande ville", "Ville", "Village"])]
        sub = sub[sub.nom.map(norm).str.contains(k[:5])] if len(sub[sub.nom.map(norm).str.contains(k[:5])]) else sub
        if len(sub):
            return float(sub.iloc[0].lat), float(sub.iloc[0].lon)
        c = _communes()[_communes().adm2_pcode == pc].iloc[0]
        return float(c.lat), float(c.lon)
    return None


def haversine(a: tuple[float, float], b: tuple[float, float]) -> float:
    la1, lo1, la2, lo2 = map(math.radians, (*a, *b))
    h = math.sin((la2 - la1) / 2) ** 2 + math.cos(la1) * math.cos(la2) * math.sin((lo2 - lo1) / 2) ** 2
    return 2 * 6371 * math.asin(math.sqrt(h))


def _avec_commune(df: pd.DataFrame, col: str = "commune") -> pd.DataFrame:
    com = _communes()[["adm2_pcode", "commune", "departement", "lat", "lon"]]
    df = df.copy()
    df["adm2_pcode"] = df[col].map(pcode_commune)
    return df.merge(com.rename(columns={"commune": "commune_cnigs", "departement": "dep_cnigs",
                                        "lat": "lat_c", "lon": "lon_c"}), on="adm2_pcode", how="left")


def sites_touristiques() -> pd.DataFrame:
    s = _avec_commune(pd.read_csv(CURATED / "sites_touristiques.csv"))
    coords = [localiser_ville(c) if isinstance(c, str) else None for c in s.commune]
    s["lat"] = [c[0] if c else la for c, la in zip(coords, s.lat_c)]
    s["lon"] = [c[1] if c else lo for c, lo in zip(coords, s.lon_c)]
    s["precision_localisation"] = "ville / commune"
    return s


def transports() -> pd.DataFrame:
    t = _avec_commune(pd.read_csv(CURATED / "transports.csv"))
    for i, r in t.iterrows():
        if pd.isna(r.lat):
            c = localiser_ville(r.commune)
            if c:
                t.at[i, "lat"], t.at[i, "lon"] = c
    osm = LIVE / "transports_osm.csv"
    if osm.exists():
        o = pd.read_csv(osm).rename(columns={"code_iata": "code"})
        o["remarque"] = "OpenStreetMap"
        t = pd.concat([t, o], ignore_index=True)
    return t


def routes_schematiques() -> dict:
    """Tracé schématique des routes nationales (villes reliées) – remplacé par OSM après mise à jour."""
    r = pd.read_csv(CURATED / "routes_nationales.csv")
    feats = []
    for row in r.itertuples():
        pts = [localiser_ville(v) for v in row.villes.split(";")]
        pts = [p for p in pts if p]
        if len(pts) >= 2:
            feats.append({"type": "Feature", "properties": {"ref": row.route, "nom": row.nom, "remarque": row.remarque,
                                                           "villes": row.villes.replace(";", " → ")},
                          "geometry": {"type": "LineString", "coordinates": [[lo, la] for la, lo in pts]}})
    return {"type": "FeatureCollection", "features": feats}


def routes_osm() -> dict | None:
    p = LIVE / "routes_osm.geojson"
    if p.exists():
        return json.load(open(p, encoding="utf-8"))
    return None


def longueur_km(gj: dict) -> pd.DataFrame:
    rows = []
    for f in gj["features"]:
        c = f["geometry"]["coordinates"]
        km = sum(haversine((c[i][1], c[i][0]), (c[i + 1][1], c[i + 1][0])) for i in range(len(c) - 1))
        rows.append({**f["properties"], "km": km})
    return pd.DataFrame(rows)


@lru_cache(maxsize=1)
def communes_cotieres() -> set[str]:
    """Communes touchant la mer : intersection avec le trait de côte Natural Earth (1:10 M)."""
    from shapely.geometry import shape
    from shapely.ops import unary_union
    g = json.load(open(GEO / "communes.geojson", encoding="utf-8"))
    cote = unary_union([shape(f["geometry"]) for f in json.load(open(GEO / "trait_de_cote.geojson", encoding="utf-8"))["features"]])
    return {f["id"] for f in g["features"] if shape(f["geometry"]).buffer(0.008).intersects(cote)}


def iles() -> pd.DataFrame:
    i = pd.read_csv(CURATED / "iles.csv")
    com = _communes()
    rows = []
    for r in i.itertuples():
        pcs = [pcode_commune(c) for c in str(r.communes).split(";")] if isinstance(r.communes, str) else []
        sub = com[com.adm2_pcode.isin([p for p in pcs if p])]
        rows.append({"ile": r.ile, "departement": r.departement, "communes": r.communes if isinstance(r.communes, str) else "—",
                     "population_2022": int(sub.population.sum()) if len(sub) else None,
                     "superficie_km2": round(float(sub.superficie_km2.sum()), 1) if len(sub) else None,
                     "localites": int(sub.nb_localites.sum()) if len(sub) else None,
                     "lat": r.lat, "lon": r.lon, "description": r.description, "pcodes": ";".join(p for p in pcs if p)})
    return pd.DataFrame(rows)


def indice_cadre_de_vie(poids: dict[str, float] | None = None) -> pd.DataFrame:
    """Indice 0-100 « où il fait bon vivre » à partir des données disponibles.

    Composantes (rangs centiles) :
      services   : universités + hôpitaux de référence + écoles/1000 enfants (si couvert)
      accessibilite : proximité d'un aéroport et du chef-lieu départemental
      nature     : littoral + sites touristiques/naturels dans la commune
      confort    : densité « équilibrée » (ni désert, ni surpeuplement)
      dynamisme  : nombre de villes/quartiers (vie urbaine, commerces)
    La sécurité n'est pas mesurée faute de données communales fiables : consulter les avis officiels.
    """
    poids = poids or {"services": 1.0, "accessibilite": 1.0, "nature": 1.0, "confort": 1.0, "dynamisme": 0.7}
    com = _communes().copy()
    inst = pd.read_csv(PROCESSED / "institutions.csv")
    uni = inst[inst.categorie == "Université / Enseignement supérieur"].groupby("adm2_pcode").size()
    san = inst[inst.categorie == "Santé"].groupby("adm2_pcode").size()
    com["universites"] = com.adm2_pcode.map(uni).fillna(0)
    com["hopitaux_ref"] = com.adm2_pcode.map(san).fillna(0)
    ec = (com.ecoles_osm_pour_1000_enfants if "ecoles_osm_pour_1000_enfants" in com else com.ecoles_pour_1000_enfants).rank(pct=True)
    com["c_services"] = (com.universites.rank(pct=True) + com.hopitaux_ref.rank(pct=True) + ec.fillna(0.5)) / 3

    tr = transports()
    aer = tr[tr.type.str.contains("Aéroport", na=False)].dropna(subset=["lat"])
    deps = pd.read_csv(PROCESSED / "departements.csv")
    chefs = {r.adm1_pcode: localiser_ville(r.chef_lieu) for r in deps.itertuples()}
    d_aer, d_chef = [], []
    for r in com.itertuples():
        p = (r.lat, r.lon)
        d_aer.append(min(haversine(p, (a.lat, a.lon)) for a in aer.itertuples()) if len(aer) else np.nan)
        c = chefs.get(r.adm1_pcode)
        d_chef.append(haversine(p, c) if c else np.nan)
    com["km_aeroport"], com["km_chef_lieu"] = np.round(d_aer, 1), np.round(d_chef, 1)
    com["c_accessibilite"] = (1 - com.km_aeroport.rank(pct=True) + 1 - com.km_chef_lieu.rank(pct=True)) / 2

    cot = communes_cotieres()
    sites = sites_touristiques().groupby("adm2_pcode").size()
    com["littoral"] = com.adm2_pcode.isin(cot)
    com["sites_touristiques"] = com.adm2_pcode.map(sites).fillna(0)
    com["c_nature"] = (com.littoral.astype(float) * 0.6 + com.sites_touristiques.rank(pct=True) * 0.4)

    ld = np.log10(com.densite_hab_km2)
    com["c_confort"] = np.exp(-((ld - np.log10(600)) ** 2) / (2 * 0.35 ** 2))  # optimum ≈ 600 hab/km²
    com["c_dynamisme"] = (com.nb_villes + com.nb_quartiers).rank(pct=True)

    tot = sum(poids.values()) or 1
    com["indice_cadre_de_vie"] = (100 * sum(com[f"c_{k}"] * w for k, w in poids.items()) / tot).round(1)
    com["rang"] = com.indice_cadre_de_vie.rank(ascending=False, method="min").astype(int)
    return com
