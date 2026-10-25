"""Construit toutes les tables propres de data/processed et data/geo
à partir des fichiers bruts (data/raw) et des listes vérifiées (data/curated).

Usage :  python scripts/build_data.py
Toutes les tables sont reliées par les P-codes officiels du CNIGS :
  HT01 (département)  ->  HT0111 (commune)  ->  HT0111-01 (section communale)
"""
from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.utils import ALIAS_COMMUNES, CURATED, GEO, PROCESSED, RAW, norm  # noqa: E402

PROCESSED.mkdir(parents=True, exist_ok=True)
GEO.mkdir(parents=True, exist_ok=True)


def save(df: pd.DataFrame, name: str) -> None:
    df.to_csv(PROCESSED / name, index=False, encoding="utf-8")
    print(f"  ✓ {name:<40} {len(df):>6} lignes")


# ---------------------------------------------------------------- 1. Admin
print("1. Découpage administratif")
adm = pd.read_excel(RAW / "admin" / "hti_adminboundaries_tabulardata.xlsx", sheet_name=None)
dep = adm["ADM1"].rename(columns={"ADM1_PCODE": "adm1_pcode", "ADM1_FR": "departement",
                                   "ADM1_EN": "departement_en", "ADM1_HT": "departement_ht",
                                   "AREA_SQKM": "superficie_km2"})
dep = dep[["adm1_pcode", "departement", "departement_en", "departement_ht", "superficie_km2"]]
com = adm["ADM2"].rename(columns={"ADM2_PCODE": "adm2_pcode", "ADM2_FR": "commune", "ADM2_HT": "commune_ht",
                                   "ADM1_PCODE": "adm1_pcode", "ADM1_FR": "departement",
                                   "AREA_SQKM": "superficie_km2"})
com = com[["adm2_pcode", "commune", "commune_ht", "adm1_pcode", "departement", "superficie_km2"]]
sec = adm["ADM3"].rename(columns={"ADM3_PCODE": "adm3_pcode", "ADM3_FR": "section_communale",
                                   "ADM2_PCODE": "adm2_pcode", "ADM2_FR": "commune",
                                   "ADM1_PCODE": "adm1_pcode", "ADM1_FR": "departement",
                                   "AREA_SQKM": "superficie_km2"})
sec = sec[["adm3_pcode", "section_communale", "adm2_pcode", "commune", "adm1_pcode", "departement", "superficie_km2"]]

CHEF_LIEU = {"HT01": "Port-au-Prince", "HT02": "Jacmel", "HT03": "Cap-Haïtien", "HT04": "Fort-Liberté",
             "HT05": "Gonaïves", "HT06": "Hinche", "HT07": "Cayes", "HT08": "Jérémie",
             "HT09": "Port-de-Paix", "HT10": "Miragoâne"}
dep["chef_lieu"] = dep["adm1_pcode"].map(CHEF_LIEU)

# index nom normalisé -> pcode commune
COMMUNE_IDX = {norm(r.commune): r.adm2_pcode for r in com.itertuples()}


def commune_pcode(name: str | float) -> str | None:
    if not isinstance(name, str) or not name.strip():
        return None
    k = norm(name)
    k = ALIAS_COMMUNES.get(k, k)
    if k in COMMUNE_IDX:
        return COMMUNE_IDX[k]
    for key, pc in COMMUNE_IDX.items():  # correspondance partielle
        if k and (k in key or key in k):
            return pc
    return None


# ---------------------------------------------------------------- 2. Population
print("2. Population 2022")
p2 = pd.read_csv(RAW / "population" / "hti_admpop_adm2_2022.csv").rename(columns=lambda c: c.strip())
p2 = p2.rename(columns={"adm2code": "adm2_pcode", "Population": "population", "Femmes": "femmes",
                        "Hommes": "hommes", "Enfants": "enfants", "Adultes": "adultes", "Filles": "filles",
                        "Garcons": "garcons", "Femmes adultes": "femmes_adultes", "Hommes adultes": "hommes_adultes"})
popcols = ["population", "femmes", "hommes", "enfants", "adultes", "filles", "garcons", "femmes_adultes", "hommes_adultes"]
com = com.merge(p2[["adm2_pcode"] + popcols], on="adm2_pcode", how="left")
dep = dep.merge(com.groupby("adm1_pcode")[popcols].sum().reset_index(), on="adm1_pcode", how="left")
for df in (com, dep):
    df["densite_hab_km2"] = (df["population"] / df["superficie_km2"]).round(1)
    df["part_enfants_pct"] = (100 * df["enfants"] / df["population"]).round(1)
    df["ratio_hommes_femmes"] = (100 * df["hommes"] / df["femmes"]).round(1)

# ---------------------------------------------------------------- 3. Localités
print("3. Localités (OpenStreetMap / CNIGS)")
loc = pd.read_excel(RAW / "localites" / "haiti_ville_infos.xlsx")
TYPE_FR = {"hamlet": "Hameau", "village": "Village", "locality": "Lieu-dit", "suburb": "Quartier",
           "town": "Ville", "city": "Grande ville", "national_capital": "Capitale", "island": "Île",
           "region": "Région", "farm": "Habitation"}
loc = pd.DataFrame({
    "nom": loc["NAME"], "adm4_pcode": loc["ADMN4_PCODE"], "type": loc["TYPE"].map(TYPE_FR).fillna(loc["TYPE"]),
    "population_osm": loc["POPULATION"].replace(0, np.nan), "lat": loc["POINT_Y"], "lon": loc["POINT_X"],
    "adm3_pcode": loc["ADM3_PCODE"], "section_communale": loc["ADM3_FR"], "adm2_pcode": loc["ADM2_PCODE"],
    "commune": loc["ADM2_FR"], "adm1_pcode": loc["ADM1_PCODE"], "departement": loc["ADM1_FR"],
    "osm_id": loc["osm_id"],
})
save(loc, "localites.csv")
agg = loc.groupby("adm2_pcode").agg(nb_localites=("nom", "size"),
                                    nb_villes=("type", lambda s: s.isin(["Ville", "Grande ville", "Capitale"]).sum()),
                                    nb_quartiers=("type", lambda s: (s == "Quartier").sum())).reset_index()
com = com.merge(agg, on="adm2_pcode", how="left")
com[["nb_localites", "nb_villes", "nb_quartiers"]] = com[["nb_localites", "nb_villes", "nb_quartiers"]].fillna(0).astype(int)
com["part_urbaine_localites_pct"] = (100 * (com["nb_villes"] + com["nb_quartiers"]) / com["nb_localites"].replace(0, np.nan)).round(1).fillna(0)
sec = sec.merge(loc.groupby("adm3_pcode").size().rename("nb_localites").reset_index(), on="adm3_pcode", how="left")
sec["nb_localites"] = sec["nb_localites"].fillna(0).astype(int)

# ---------------------------------------------------------------- 4. Géographie
print("4. Contours géographiques (geoBoundaries) + P-codes")
from shapely.geometry import Point, mapping, shape  # noqa: E402
from shapely.strtree import STRtree  # noqa: E402

g3 = json.load(open(RAW / "geo" / "hti_ADM3.geojson", encoding="utf-8"))
polys = [shape(f["geometry"]) for f in g3["features"]]
tree = STRtree(polys)
votes: list[Counter] = [Counter() for _ in polys]
for r in loc.itertuples():
    pt = Point(r.lon, r.lat)
    for i in tree.query(pt):
        if polys[i].contains(pt):
            votes[i][r.adm2_pcode] += 1
            break
features, used = [], set()
for i, f in enumerate(g3["features"]):
    pc = votes[i].most_common(1)[0][0] if votes[i] else commune_pcode(f["properties"]["shapeName"])
    if pc is None or pc in used:
        pc = commune_pcode(f["properties"]["shapeName"]) or pc
    used.add(pc)
    row = com.loc[com.adm2_pcode == pc]
    props = {"adm2_pcode": pc, "commune": row.commune.iloc[0] if len(row) else f["properties"]["shapeName"],
             "departement": row.departement.iloc[0] if len(row) else ""}
    features.append({"type": "Feature", "id": pc, "properties": props,
                     "geometry": mapping(polys[i].simplify(0.0015, preserve_topology=True))})
missing = set(com.adm2_pcode) - used
print(f"  communes cartographiées : {len(used)}/140 (manquantes : {sorted(missing)})")
json.dump({"type": "FeatureCollection", "features": features}, open(GEO / "communes.geojson", "w", encoding="utf-8"))

# centroïdes de communes (point intérieur au polygone)
cent = {}
for f, p in zip(features, polys):
    rp = p.representative_point()
    cent[f["id"]] = (round(rp.y, 5), round(rp.x, 5))
com["lat"] = com.adm2_pcode.map(lambda c: cent.get(c, (np.nan, np.nan))[0])
com["lon"] = com.adm2_pcode.map(lambda c: cent.get(c, (np.nan, np.nan))[1])
# repli : moyenne des localités
fb = loc.groupby("adm2_pcode")[["lat", "lon"]].mean()
com["lat"] = com["lat"].fillna(com.adm2_pcode.map(fb["lat"]))
com["lon"] = com["lon"].fillna(com.adm2_pcode.map(fb["lon"]))

g1 = json.load(open(RAW / "geo" / "hti_ADM1.geojson", encoding="utf-8"))
DEP_BY_NAME = {"ouest": "HT01", "sudest": "HT02", "nord": "HT03", "nordest": "HT04", "artibonite": "HT05",
               "centre": "HT06", "sud": "HT07", "grandeanse": "HT08", "nordouest": "HT09", "nippes": "HT10"}
f1 = []
for f in g1["features"]:
    n = norm(f["properties"]["shapeName"].replace("Département", "").replace("Department", "")
             .replace("de l'", "").replace("de la", "").replace("des ", "").replace("du ", ""))
    pc = DEP_BY_NAME.get(n)
    name = dep.loc[dep.adm1_pcode == pc, "departement"].iloc[0]
    f1.append({"type": "Feature", "id": pc, "properties": {"adm1_pcode": pc, "departement": name},
               "geometry": mapping(shape(f["geometry"]).simplify(0.002, preserve_topology=True))})
json.dump({"type": "FeatureCollection", "features": f1}, open(GEO / "departements.geojson", "w", encoding="utf-8"))
print(f"  départements cartographiés : {len(f1)}/10")

# ---------------------------------------------------------------- 5. Écoles
print("5. Écoles (cartographie 2022)")
ec = pd.read_excel(RAW / "ecoles" / "haiti-2022-cartographie-des-institutions-scolaires.xls", header=None, skiprows=3)
ec = ec.iloc[:, 1:7]
ec.columns = ["departement_src", "adm1_pcode", "commune", "adm2_pcode", "nom", "secteur"]
ec = ec.dropna(subset=["nom"])
ec["nom"] = ec["nom"].astype(str).str.replace(r"\s+", " ", regex=True).str.strip()
ec["secteur"] = (ec["secteur"].astype(str).str.strip().str.upper().str.replace("-", " ")
                 .map(lambda s: "Public" if s == "PUBLIQUE" else ("Non public" if "NON" in s else s.title())))


def categorie_ecole(n: str) -> str:
    u = norm(n)
    if any(k in u for k in ("universit", "facult", "institutsuperieur")):
        return "Supérieur"
    if any(k in u for k in ("lycee", "lyce")):
        return "Lycée (secondaire)"
    if any(k in u for k in ("kindergarten", "jardin", "prescol", "maternelle", "kindergaten", "garderie")):
        return "Préscolaire"
    if any(k in u for k in ("centredeformation", "professionnel", "technique", "formationprof", "metier")):
        return "Formation professionnelle"
    if u.startswith(("ecolenationale", "ecolecommunale")) or str(n).upper().startswith(("EN ", "E.N.", "E N ")):
        return "École nationale / communale"
    if any(k in u for k in ("college", "institution", "institut", "academ", "complexe")):
        return "Collège / Institution"
    if any(k in u for k in ("presbyt", "episcopal", "adventist", "baptist", "evangel", "catholi", "saint", "sacrecoeur",
                            "notredame", "eglise", "mission", "methodist", "wesley")):
        return "École confessionnelle"
    if "ecole" in u or "ec" == u[:2]:
        return "École fondamentale"
    return "Autre / non déterminé"


ec["categorie_deduite"] = ec["nom"].map(categorie_ecole)
ec = ec.merge(com[["adm2_pcode", "commune", "departement", "lat", "lon"]].rename(columns={"commune": "commune_cnigs"}),
              on="adm2_pcode", how="left")
ec["commune"] = ec["commune_cnigs"].fillna(ec["commune"])
ec = ec.drop(columns=["commune_cnigs", "departement_src"])
ec["precision_localisation"] = "commune"
save(ec[["nom", "secteur", "categorie_deduite", "commune", "adm2_pcode", "departement", "adm1_pcode",
         "lat", "lon", "precision_localisation"]], "ecoles.csv")
ea = ec.groupby("adm2_pcode").agg(nb_ecoles=("nom", "size"),
                                  nb_ecoles_publiques=("secteur", lambda s: (s == "Public").sum())).reset_index()
com = com.merge(ea, on="adm2_pcode", how="left")
# Le fichier 2022 ne couvre que certaines communes : on garde NaN (= non couvert) au lieu de 0.
com["couverture_ecoles_2022"] = com["nb_ecoles"].notna()
com["part_ecoles_publiques_pct"] = (100 * com.nb_ecoles_publiques / com.nb_ecoles).round(1)
com["ecoles_pour_1000_enfants"] = (1000 * com.nb_ecoles / com.enfants).round(2)
dep = dep.merge(com.groupby("adm1_pcode")[["nb_localites"]].sum().reset_index(), on="adm1_pcode", how="left")
cov = com[com.couverture_ecoles_2022].groupby("adm1_pcode").agg(
    nb_ecoles=("nb_ecoles", "sum"), nb_ecoles_publiques=("nb_ecoles_publiques", "sum"),
    communes_couvertes=("adm2_pcode", "size"), enfants_couverts=("enfants", "sum")).reset_index()
dep = dep.merge(cov, on="adm1_pcode", how="left")
dep["communes_couvertes"] = dep["communes_couvertes"].fillna(0).astype(int)
dep["ecoles_pour_1000_enfants"] = (1000 * dep.nb_ecoles / dep.enfants_couverts).round(2)

# ---------------------------------------------------------------- 6. Institutions (annuaire)
print("6. Annuaire des institutions")
inst = []
uni = pd.read_csv(CURATED / "universites.csv")
for r in uni.itertuples():
    pc = commune_pcode(r.commune)
    inst.append({"nom": r.nom, "sigle": r.sigle if isinstance(r.sigle, str) else "", "categorie": "Université / Enseignement supérieur",
                 "sous_type": f"{r.statut} – {r.composante}", "adm2_pcode": pc,
                 "departement_declare": r.departement if isinstance(r.departement, str) else "",
                 "precision_localisation": "commune" if pc else (r.precision_localisation if isinstance(r.precision_localisation, str) else "non précisée"),
                 "source": "MENFP – liste des IES reconnues (via Le Scientifique, 2023/2026)"})
san = pd.read_csv(CURATED / "sante_reference.csv")
for r in san.itertuples():
    inst.append({"nom": r.nom, "sigle": "", "categorie": "Santé", "sous_type": r.type,
                 "adm2_pcode": commune_pcode(r.commune), "departement_declare": r.departement,
                 "precision_localisation": "commune", "source": "Liste de référence (à compléter par OpenStreetMap)"})
for r in com.itertuples():
    inst.append({"nom": f"Mairie de {r.commune}", "sigle": "", "categorie": "Administration locale",
                 "sous_type": "Mairie (commune)", "adm2_pcode": r.adm2_pcode, "departement_declare": r.departement,
                 "precision_localisation": "commune", "source": "CNIGS – découpage communal"})
for r in dep.itertuples():
    inst.append({"nom": f"Délégation départementale – {r.departement}", "sigle": "", "categorie": "Administration de l'État",
                 "sous_type": "Délégation / chef-lieu", "adm2_pcode": commune_pcode(r.chef_lieu),
                 "departement_declare": r.departement, "precision_localisation": "commune", "source": "CNIGS"})
inst = pd.DataFrame(inst)
inst = inst.merge(com[["adm2_pcode", "commune", "departement", "lat", "lon"]], on="adm2_pcode", how="left")
inst["departement"] = inst["departement"].fillna(inst["departement_declare"])
inst = inst.drop(columns=["departement_declare"])
save(inst, "institutions.csv")
save(uni.assign(adm2_pcode=uni.commune.map(commune_pcode)), "universites.csv")

# ---------------------------------------------------------------- 7. Banque mondiale
print("7. Indicateurs Banque mondiale (1960-2022)")
frames = []
for f in sorted((RAW / "banque_mondiale").glob("*_hti.csv")):
    d = pd.read_csv(f, skiprows=[1])
    d["theme"] = f.stem.replace("_hti", "")
    frames.append(d)
wb = pd.concat(frames)
wb = wb.rename(columns={"Year": "annee", "Indicator Name": "indicateur_en", "Indicator Code": "code", "Value": "valeur"})
themes = wb.groupby("code")["theme"].apply(lambda s: ";".join(sorted(set(s))))
wb = wb.drop_duplicates(subset=["code", "annee"])[["code", "indicateur_en", "annee", "valeur"]]
wb["themes"] = wb["code"].map(themes)
wb["source"] = "Banque mondiale – WDI (fichiers HDX)"
wb = wb.sort_values(["code", "annee"])
save(wb, "wb_indicateurs.csv")
cat = wb.groupby(["code", "indicateur_en", "themes"]).agg(premiere_annee=("annee", "min"), derniere_annee=("annee", "max"),
                                                         nb_points=("valeur", "size")).reset_index()
save(cat, "wb_catalogue.csv")

# ---------------------------------------------------------------- 8. IPC, COVID, organisations
print("8. Sécurité alimentaire, santé, organisations")
ipc = pd.read_csv(RAW / "ipc" / "ipc_hti_national_long_latest.csv", skiprows=[1])
ipc.columns = ["date_analyse", "pays", "population_totale", "periode", "debut", "fin", "phase", "nombre", "pourcentage"]
ipc["source"] = "IPC (HDX)"
save(ipc, "ipc_historique.csv")

cov = pd.read_csv(RAW / "autres" / "covid19_country_wise_2020.csv")
cov = cov.rename(columns={"Country/Region": "pays", "Confirmed": "cas_confirmes", "Deaths": "deces", "Recovered": "gueris",
                          "Active": "actifs", "Deaths / 100 Cases": "deces_pour_100_cas", "WHO Region": "region_oms"})
save(cov[["pays", "cas_confirmes", "deces", "gueris", "actifs", "deces_pour_100_cas", "region_oms"]], "covid19_2020.csv")

org_src = PROCESSED / "organisations_humanitaires_2020.csv"
if not org_src.exists():
    print("  (organisations : fichier agrégé absent – lancer scripts/anonymiser_ong.py)")

# ---------------------------------------------------------------- 9. Sauvegarde finale
save(dep, "departements.csv")
save(com, "communes.csv")
save(sec, "sections_communales.csv")
if (RAW / "osm" / "hotosm_hti_education_facilities.gpkg").exists():
    print("10. Établissements d'enseignement OpenStreetMap (HOT)")
    from scripts.integrer_education_osm import main as integrer_osm
    integrer_osm()
print("Terminé.")
