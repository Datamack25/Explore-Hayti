"""Frontière haïtiano-dominicaine : 20 postes, budget sur 5 ans (Monte Carlo), placement optimal par machine learning."""
from __future__ import annotations

import json
from functools import lru_cache

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
from matplotlib.collections import PolyCollection  # noqa: E402
from shapely.geometry import box, mapping, shape  # noqa: E402
from shapely.ops import unary_union  # noqa: E402
from sklearn.cluster import KMeans  # noqa: E402

from src.rapports import _png  # noqa: E402
from src.utils import CURATED, GEO, PROCESSED  # noqa: E402

COUL_NIV = {"Grand poste (guichet unique)": "#D21034", "Poste secondaire": "#eb6834", "Base de surveillance": "#00209F"}
ANNEES = [f"Année {i}" for i in range(1, 6)]
# Repères chiffrés (sources dans la page)
EXPORTS_RD_2025 = 1064.22e6       # exportations dominicaines vers Haïti, janv.-nov. 2025 (HaitiLibre)
REGIME_NATIONAL_2025 = 749.07e6   # dont régime national (hors zones franches), janv.-nov. 2025
RECETTES_FRONTIERE_HTG = 11.2e9   # recettes des 5 bureaux frontaliers, oct. 2019 - janv. 2025 (Le Nouvelliste)
HTG_USD = 131.0


def postes() -> pd.DataFrame:
    return pd.read_csv(CURATED / "postes_frontaliers.csv")


def budget_hyp() -> pd.DataFrame:
    return pd.read_csv(CURATED / "budget_frontiere.csv")


def ressources_locales() -> pd.DataFrame:
    return pd.read_csv(CURATED / "ressources_locales_frontiere.csv")


# ------------------------------------------------------------------ géométrie
@lru_cache(maxsize=1)
def ligne_frontiere():
    com = json.loads((GEO / "communes.geojson").read_text(encoding="utf-8"))
    U = unary_union([shape(f["geometry"]).buffer(0.0005) for f in com["features"]]).buffer(-0.0005)
    if U.geom_type == "MultiPolygon":  # île principale seulement, sans les trous entre communes
        U = max(U.geoms, key=lambda g: g.area)
    U = shape(mapping(U)).exterior
    cote = unary_union([shape(f["geometry"]) for f in json.loads((GEO / "trait_de_cote.geojson").read_text(encoding="utf-8"))["features"]])
    return U.difference(cote.buffer(0.01)).intersection(box(-72.1, 17.9, -71.5, 20.0))


def _km(lat1, lon1, lat2, lon2):
    lat1, lon1, lat2, lon2 = map(np.asarray, (lat1, lon1, lat2, lon2))
    dx = (lon2 - lon1) * 111.32 * np.cos(np.radians((lat1 + lat2) / 2))
    dy = (lat2 - lat1) * 110.57
    return np.hypot(dx, dy)


@lru_cache(maxsize=1)
def echantillon_frontiere(pas_km: float = 1.0) -> pd.DataFrame:
    """Points tous les ~1 km le long de la frontière terrestre, pondérés par la population voisine."""
    B = ligne_frontiere()
    parts = list(B.geoms) if hasattr(B, "geoms") else [B]
    pts = []
    for ln in parts:
        if ln.geom_type != "LineString" or ln.length < 0.002:
            continue
        n = max(2, int(ln.length * 111 / pas_km))
        for d in np.linspace(0, ln.length, n):
            p = ln.interpolate(d)
            pts.append((p.y, p.x))
    e = pd.DataFrame(pts, columns=["lat", "lon"]).drop_duplicates()
    c = pd.read_csv(PROCESSED / "communes.csv").dropna(subset=["lat"])
    D = _km(e.lat.values[:, None], e.lon.values[:, None], c.lat.values[None, :], c.lon.values[None, :])
    e["poids"] = (np.exp(-D / 10.0) * c.population.values[None, :]).sum(axis=1)
    e["poids"] = e.poids / e.poids.sum()
    return e.reset_index(drop=True)


def longueur_km() -> float:
    e = echantillon_frontiere()
    return float(len(e))  # ~1 point par km


# ------------------------------------------------------------------ machine learning : placement optimal
def placement_ml(k: int = 20, seed: int = 42) -> pd.DataFrame:
    """K-moyennes pondérées par la population riveraine sur les points de la frontière ; centres ramenés sur la ligne."""
    e = echantillon_frontiere()
    X = np.c_[e.lat.values * 110.57, e.lon.values * 111.32 * np.cos(np.radians(18.9))]
    km = KMeans(n_clusters=k, n_init=10, random_state=seed).fit(X, sample_weight=e.poids.values)
    out = []
    for j in range(k):
        m = km.labels_ == j
        sous = e[m]
        cy, cx = km.cluster_centers_[j]
        d = np.hypot(X[m, 0] - cy, X[m, 1] - cx)
        p = sous.iloc[int(np.argmin(d))]
        out.append({"ml_id": f"ML{j + 1}", "lat": p.lat, "lon": p.lon, "poids_population": round(float(sous.poids.sum()) * 100, 1),
                    "longueur_couverte_km": int(m.sum())})
    return pd.DataFrame(out).sort_values("lat", ascending=False).reset_index(drop=True)


def evaluer(lat: np.ndarray, lon: np.ndarray) -> dict:
    """Distance moyenne (pondérée par la population) et distance maximale d'un point de la frontière au poste le plus proche."""
    e = echantillon_frontiere()
    D = _km(e.lat.values[:, None], e.lon.values[:, None], np.asarray(lat)[None, :], np.asarray(lon)[None, :]).min(axis=1)
    return {"distance_moyenne_ponderee_km": round(float((D * e.poids).sum()), 1), "distance_max_km": round(float(D.max()), 1),
            "frontiere_a_moins_de_15_km_pct": round(float((D <= 15).mean() * 100), 0)}


def comparer_scenarios(k_ml: int = 20) -> pd.DataFrame:
    p = postes()
    terre = p[~p.nom.str.contains("garde-côtes")]
    ml = placement_ml(k_ml)
    sc = {
        "Aujourd'hui : 5 postes officiels": p[p.niveau.str.startswith("Grand")],
        "Proposition : 5 grands + 8 secondaires": p[p.niveau != "Base de surveillance"],
        "Proposition complète : 20 points (dont bases)": terre,
        f"Machine learning : {k_ml} points optimaux": ml,
    }
    return pd.DataFrame([{"scenario": n, "points": len(d), **evaluer(d.lat.values, d.lon.values)} for n, d in sc.items()])


# ------------------------------------------------------------------ budget
def _rec(unite: str) -> bool:
    return unite.endswith("/an") or unite == "an"


def budget_annuel(h: pd.DataFrame, colonne: str = "cout_unitaire_median", maintenance_pct: float = 5.0) -> pd.DataFrame:
    rows = []
    for r in h.itertuples():
        pct = [float(x) for x in str(r.phasage_annuel_pct).split(";")]
        tot = r.quantite * getattr(r, colonne)
        vals = [tot * p / 100 for p in pct]  # récurrent : % du régime plein ; ponctuel : part du total
        rows.append({"poste_budgetaire": r.poste_budgetaire, "nature": r.nature, "part_locale_pct": r.part_locale_pct,
                     **dict(zip(ANNEES, vals))})
    b = pd.DataFrame(rows)
    inv = b[b.nature == "Investissement"][ANNEES].sum().cumsum().shift(1).fillna(0)
    b = pd.concat([b, pd.DataFrame([{"poste_budgetaire": f"Maintenance ({maintenance_pct:.0f} % du capital installé)",
                                     "nature": "Fonctionnement", "part_locale_pct": 80,
                                     **dict(zip(ANNEES, inv.values * maintenance_pct / 100))}])], ignore_index=True)
    b["Total 5 ans"] = b[ANNEES].sum(axis=1)
    return b


def monte_carlo(h: pd.DataFrame, n: int = 5000, seed: int = 0) -> np.ndarray:
    """Coût total sur 5 ans : coûts unitaires tirés selon une loi triangulaire (bas, médian, haut), maintenance incluse."""
    rng = np.random.default_rng(seed)
    tot = np.zeros(n)
    inv = np.zeros((n, 5))
    for r in h.itertuples():
        pct = np.array([float(x) for x in str(r.phasage_annuel_pct).split(";")]) / 100
        lo, mo, hi = r.cout_unitaire_bas, r.cout_unitaire_median, r.cout_unitaire_haut
        u = rng.triangular(lo, mo, hi, n) if hi > lo else np.full(n, mo)
        par_an = (u * r.quantite)[:, None] * pct[None, :]
        tot += par_an.sum(axis=1)
        if r.nature == "Investissement":
            inv += par_an
    cumul = np.cumsum(inv, axis=1)[:, :-1]  # capital installé à la fin des années 1 à 4
    tot += cumul.sum(axis=1) * 0.05
    return tot


def recettes(taux_effectif: float, part_cible: float, annees: int = 5) -> pd.DataFrame:
    """Recettes douanières supplémentaires si une plus grande part du commerce du régime national passe par les postes."""
    flux = REGIME_NATIONAL_2025 / 11 * 12
    base_usd = RECETTES_FRONTIERE_HTG / HTG_USD / (64 / 12)
    part_base = min(base_usd / (flux * taux_effectif), part_cible)
    parts = np.linspace(part_base, part_cible, annees + 1)[1:]
    return pd.DataFrame({"annee": ANNEES[:annees], "part_formalisee_pct": (parts * 100).round(0),
                         "recettes_totales_usd": parts * flux * taux_effectif,
                         "recettes_supplementaires_usd": (parts - part_base) * flux * taux_effectif,
                         "recettes_actuelles_usd": base_usd})


def comparaison_etzer(total_5ans: float) -> pd.DataFrame:
    return pd.DataFrame({
        "dimension": ["Nombre de points de passage", "Calendrier", "Technologie", "Forces", "Recettes et corruption", "Budget",
                      "Ressources locales", "Diplomatie", "Gouvernance locale"],
        "Plan 20 postes (Ayiti Data Hub)": [
            "5 grands postes modernisés + 8 postes secondaires + 7 bases de surveillance",
            "5 ans : année 1 grands postes, années 2-3 secondaires et bases, années 4-5 consolidation",
            "Scanners aux 5 grands postes, biométrie, SYDONIA relié, drones et capteurs entre les postes",
            "≈1 120 agents : DIE, AGD, PNH (POLIFRONT), FAd'H, MARNDR, informatique",
            "Fonds frontière alimenté par les recettes ; tableau de bord recettes par poste ; rotation des agents",
            f"≈{total_5ans / 1e6:,.0f} M USD sur 5 ans (scénario médian)".replace(",", " "),
            "Matériaux, main-d'œuvre, uniformes, repas, logiciels : part locale chiffrée ligne par ligne",
            "Chaque poste négocié avec son vis-à-vis dominicain (commission mixte)",
            "Comité frontalier dans chaque commune (mairie, CASEC, commerçants, PNH)",
        ],
        "Programme Etzer Émile": [
            "Reprise du contrôle des ports, aéroports et postes frontaliers ; pas de nouveaux postes chiffrés",
            "100 premiers jours (reprise, scanners), cibles 2029 et 2033",
            "Scanners, contrôle biométrique, surveillance douanière renforcée",
            "Unité mixte antitrafic ; FAd'H pour frontières, garde-côtes et espace aérien ; PNH à 26 000 agents en 2033",
            "Interconnexion DGI-Douanes-BRH-UCREF ; parquet financier ; 25 000 armes saisies d'ici 2033",
            "Programme total 30 Md USD dont 15 Md pour les infrastructures ; enveloppe frontière non chiffrée",
            "« Contenu local » parmi les 5 règles des grands projets",
            "Coopération régionale contre le trafic d'armes, partenariats (dont États-Unis)",
            "Décentralisation : équipe technique dans les 146 communes en 2033",
        ],
    })


# ------------------------------------------------------------------ cartes et figures
def carte(ml: pd.DataFrame | None = None):
    import folium
    from folium.plugins import Fullscreen

    m = folium.Map(location=[18.85, -71.95], zoom_start=9, tiles=None)
    folium.TileLayer("https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png", attr="© OpenStreetMap © CARTO",
                     name="Fond clair").add_to(m)
    folium.TileLayer("https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
                     attr="Imagery © Esri", name="Satellite").add_to(m)
    folium.GeoJson(mapping(ligne_frontiere()), name="Frontière terrestre",
                   style_function=lambda f: {"color": "#0b0b0b", "weight": 3, "dashArray": "6 4"}).add_to(m)
    ICON = {"Grand poste (guichet unique)": ("red", "building"), "Poste secondaire": ("orange", "flag"),
            "Base de surveillance": ("darkblue", "shield")}
    for niv, sous in postes().groupby("niveau"):
        g = folium.FeatureGroup(name=niv, show=True)
        col, ic = ICON[niv]
        for r in sous.itertuples():
            folium.Marker((r.lat, r.lon), icon=folium.Icon(color=col, icon=ic, prefix="fa"), tooltip=f"{r.id} · {r.nom}",
                          popup=folium.Popup(f"<b>{r.id} — {r.nom}</b><br><i>{niv}</i> · {r.statut}<br>Commune : {r.commune} "
                                             f"({r.departement})<br>Vis-à-vis RD : {r.province_rd_vis_a_vis}<br>{r.mission}<br>"
                                             f"Effectif : {r.effectif} · ouverture : année {r.annee_ouverture}", max_width=320)).add_to(g)
            folium.Circle((r.lat, r.lon), radius=15000, color=COUL_NIV[niv], weight=0.6, fill=True, fill_opacity=0.04).add_to(g)
        g.add_to(m)
    if ml is not None:
        g = folium.FeatureGroup(name="Points optimaux (machine learning)", show=True)
        for r in ml.itertuples():
            folium.CircleMarker((r.lat, r.lon), radius=6, color="#1baf7a", fill=True, fill_opacity=0.9,
                                tooltip=f"{r.ml_id} : {r.poids_population} % de la population riveraine, {r.longueur_couverte_km} km").add_to(g)
        g.add_to(m)
    folium.LayerControl(collapsed=False).add_to(m)
    Fullscreen().add_to(m)
    return m


def fig_carte(ml: pd.DataFrame | None = None) -> bytes:
    geo = json.loads((GEO / "departements.geojson").read_text(encoding="utf-8"))
    fig, ax = plt.subplots(figsize=(7.5, 8.5))
    polys = []
    for f in geo["features"]:
        g = f["geometry"]
        for p in (g["coordinates"] if g["type"] == "MultiPolygon" else [g["coordinates"]]):
            polys.append(np.array(p[0]))
    ax.add_collection(PolyCollection(polys, facecolors="#eef3fb", edgecolors="#c9d6ea", linewidths=0.6))
    B = ligne_frontiere()
    for ln in (B.geoms if hasattr(B, "geoms") else [B]):
        if ln.geom_type == "LineString":
            x, y = ln.xy
            ax.plot(x, y, color="#0b0b0b", lw=1.6, ls="--")
    p = postes()
    for niv, s in p.groupby("niveau"):
        ax.scatter(s.lon, s.lat, s=90 if niv.startswith("Grand") else 55, marker={"Grand": "s", "Poste": "^", "Base": "o"}[niv.split()[0]],
                   color=COUL_NIV[niv], edgecolor="white", zorder=4, label=niv)
        for r in s.itertuples():
            ax.text(r.lon + 0.025, r.lat, r.id, fontsize=7.5, va="center", zorder=5)
    if ml is not None:
        ax.scatter(ml.lon, ml.lat, s=22, color="#1baf7a", zorder=3, label="Points optimaux (ML)")
    ax.set_xlim(-72.25, -71.5)
    ax.set_ylim(17.98, 19.75)
    ax.set_aspect("equal")
    ax.set_xticks([])
    ax.set_yticks([])
    ax.grid(False)
    for s in ax.spines.values():
        s.set_visible(False)
    ax.legend(loc="lower left", fontsize=8, frameon=True)
    ax.set_title("Frontière : 20 postes proposés")
    return _png(fig)


def fig_budget(b: pd.DataFrame) -> bytes:
    fig, ax = plt.subplots(figsize=(9, 4.2))
    bas = np.zeros(5)
    for nat, col in (("Investissement", "#2a78d6"), ("Fonctionnement", "#eb6834")):
        v = b[b.nature == nat][ANNEES].sum().values / 1e6
        ax.bar(ANNEES, v, bottom=bas, color=col, label=nat, width=0.6)
        bas += v
    for i, t in enumerate(bas):
        ax.text(i, t + 0.5, f"{t:,.1f}".replace(",", " ").replace(".", ","), ha="center", fontsize=9)
    ax.set_ylabel("millions USD")
    ax.legend(frameon=False)
    ax.set_title("Budget de la frontière par année (scénario médian)")
    return _png(fig)


# ------------------------------------------------------------------ gestion des postes
GESTION = [
    ("Guichet unique", "Dans chaque grand poste, DIE (immigration), AGD (douane), PNH-POLIFRONT, MARNDR (contrôle vétérinaire et "
     "phytosanitaire) et MSPP travaillent dans le même bâtiment, avec un chef de poste unique responsable devant une Autorité "
     "nationale des frontières rattachée à la Primature."),
    ("Effectifs", "Grand poste : ≈120 agents (DIE 20, AGD 35, PNH 40, MARNDR/MSPP 10, informatique et administration 15). "
     "Poste secondaire : ≈30 agents. Base de surveillance : ≈40 militaires ou garde-côtes. Total ≈1 120 agents."),
    ("Intégrité", "Vetting à l'entrée, rotation des agents tous les 6 à 12 mois, primes de zone frontalière, paiement sans "
     "espèces (mobile ou banque), caméras aux guichets, inspection inopinée et ligne de signalement anonyme."),
    ("Recettes", "Toutes les déclarations passent par SYDONIA ; recettes publiées poste par poste chaque mois dans le tableau de "
     "bord de gouvernance ; une part (ex. 20 %) alimente un Fonds frontière audité par la CSCCA."),
    ("Petit commerce", "Régime simplifié pour les petits commerçants et les madan sara (seuil de valeur, taxe forfaitaire, carte "
     "de commerçant frontalier) pour qu'ils aient intérêt à passer par le poste."),
    ("Entre les postes", "Bases FAd'H : patrouilles, drones et capteurs sur les passages informels repérés avec les habitants ; "
     "garde-côtes à Fort-Liberté, Belle-Anse et sur l'Étang Saumâtre."),
    ("Comités frontaliers", "Dans chaque commune frontalière : mairie, CASEC, commerçants, femmes, jeunes, PNH. Réunion mensuelle, "
     "remontée des problèmes, contrôle citoyen ; communication en créole sur les radios communautaires."),
    ("Diplomatie", "Chaque poste est ouvert avec son vis-à-vis dominicain dans le cadre d'une commission mixte binationale ; "
     "horaires harmonisés, échange de données sur les armes et les marchandises sensibles."),
    ("Indicateurs", "Publiés chaque trimestre : recettes, temps de passage, saisies (armes, munitions, drogue), incidents, "
     "plaintes, part de contenu local dans les dépenses."),
    ("Calendrier", "Année 1 : modernisation des 5 grands postes (pilote à Ouanaminthe), système d'information, formation. "
     "Années 2-3 : 8 postes secondaires, 7 bases, pistes d'accès. Années 4-5 : consolidation et évaluation indépendante."),
]


def texte_plan() -> str:
    p, b, r = postes(), budget_hyp(), ressources_locales()
    parts = ["Plan frontière : 20 postes le long de la frontière avec la République dominicaine (RD), sur 5 ans."]
    parts += [f"{x.id} {x.nom} ({x.niveau}, {x.commune}, {x.departement}, vis-à-vis {x.province_rd_vis_a_vis}) : {x.mission}. "
              f"Effectif {x.effectif} agents, ouverture année {x.annee_ouverture}." for x in p.itertuples()]
    parts += [f"{t} : {d}" for t, d in GESTION]
    parts += [f"Budget : {x.poste_budgetaire}, {x.quantite} {x.unite}, coût médian {x.cout_unitaire_median:.0f} USD, "
              f"part locale {x.part_locale_pct} %." for x in b.itertuples()]
    parts += [f"Ressource locale : {x.ressource} pour {x.usage} ; origine {x.origine} ; acteurs {x.acteurs_locaux}." for x in r.itertuples()]
    return "\n".join(parts)
