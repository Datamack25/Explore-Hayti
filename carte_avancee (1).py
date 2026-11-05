"""
Haïti Explorer — Carte avancée
-------------------------------
Fonds : Rues (OSM), Satellite (Esri) + étiquettes, Relief/Mornes (OpenTopoMap),
Topographie (Esri), Clair (Carto).
Couches : rivières & lacs (OpenStreetMap en direct), sommets/mornes (OSM + CSV),
mines & carrières OSM, ressources sourcées (CSV) par catégorie.
Bouton « Actualiser depuis Internet » : recharge les données OSM (Overpass).

Utilisation dans l'app existante :
    from carte_avancee import afficher_carte_avancee
    afficher_carte_avancee(langue="fr")        # dans l'onglet Carte

Ou en autonome :  streamlit run carte_avancee.py
"""
from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

import folium
import pandas as pd
import requests
import streamlit as st
from folium import plugins
from streamlit_folium import st_folium

DATA = Path(__file__).parent / "data"
CACHE = DATA / "osm_cache"
CACHE.mkdir(parents=True, exist_ok=True)

CENTRE_HAITI = (18.95, -72.70)
OVERPASS = [
    "https://overpass-api.de/api/interpreter",
    "https://overpass.kumi.systems/api/interpreter",
]

# Couleur + icône Font Awesome par catégorie de ressource
STYLE_CAT = {
    "Mines":             ("#b45309", "gem"),
    "Agriculture":       ("#15803d", "leaf"),
    "Pêche & mer":       ("#0369a1", "fish"),
    "Énergie & eau":     ("#7c3aed", "bolt"),
    "Nature & tourisme": ("#be185d", "tree"),
}

TXT = {
    "fr": {
        "titre": "Carte avancée d'Haïti",
        "fond": "Fond de carte",
        "couches": "Couches à afficher",
        "riv": "Rivières & lacs (OSM)",
        "som": "Sommets & mornes",
        "mas": "Massifs & plaines",
        "osm_mines": "Mines & carrières (OSM)",
        "cat": "Catégories de ressources",
        "maj": "Actualiser depuis Internet",
        "maj_ok": "Données OpenStreetMap actualisées",
        "maj_ko": "Service OSM indisponible — dernière copie locale utilisée",
        "rech": "Rechercher une ressource ou une commune",
        "tab": "Tableau des ressources (sources)",
        "dl": "Télécharger le CSV",
        "maj_le": "Données OSM du",
        "aucune": "jamais chargées",
        "approx": "Les positions « zone » sont indicatives (rayon indiqué).",
    },
    "en": {
        "titre": "Advanced map of Haiti",
        "fond": "Base map",
        "couches": "Layers",
        "riv": "Rivers & lakes (OSM)",
        "som": "Peaks & mornes",
        "mas": "Ranges & plains",
        "osm_mines": "Mines & quarries (OSM)",
        "cat": "Resource categories",
        "maj": "Refresh from the Internet",
        "maj_ok": "OpenStreetMap data refreshed",
        "maj_ko": "OSM service unavailable — using last local copy",
        "rech": "Search a resource or commune",
        "tab": "Resource table (sources)",
        "dl": "Download CSV",
        "maj_le": "OSM data from",
        "aucune": "never loaded",
        "approx": "“Zone” positions are indicative (radius shown).",
    },
}

FONDS = {
    "Satellite": None,  # géré à part (imagerie + étiquettes)
    "Rues (OpenStreetMap)": ("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png",
                             "© OpenStreetMap contributors"),
    "Relief & mornes (OpenTopoMap)": ("https://{s}.tile.opentopomap.org/{z}/{x}/{y}.png",
                                      "© OpenTopoMap (CC-BY-SA), © OpenStreetMap"),
    "Topographie (Esri)": ("https://server.arcgisonline.com/ArcGIS/rest/services/World_Topo_Map/MapServer/tile/{z}/{y}/{x}",
                           "Tiles © Esri"),
    "Clair (Carto)": ("https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png",
                      "© OpenStreetMap, © CARTO"),
}
ESRI_IMG = "https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}"
ESRI_LABELS = "https://server.arcgisonline.com/ArcGIS/rest/services/Reference/World_Boundaries_and_Places/MapServer/tile/{z}/{y}/{x}"
ESRI_ROADS = "https://server.arcgisonline.com/ArcGIS/rest/services/Reference/World_Transportation/MapServer/tile/{z}/{y}/{x}"

# ---------------------------------------------------------------- OSM / Overpass
REQUETES = {
    "rivieres": """[out:json][timeout:120];
area["ISO3166-1"="HT"][admin_level=2]->.h;
(way["waterway"="river"](area.h););
out tags geom;""",
    "lacs": """[out:json][timeout:90];
area["ISO3166-1"="HT"][admin_level=2]->.h;
(way["natural"="water"]["water"~"lake|reservoir|lagoon"](area.h);
 relation["natural"="water"]["water"~"lake|reservoir|lagoon"](area.h););
out tags geom;""",
    "sommets": """[out:json][timeout:60];
area["ISO3166-1"="HT"][admin_level=2]->.h;
(node["natural"~"peak|volcano"]["name"](area.h););
out tags;""",
    "mines": """[out:json][timeout:60];
area["ISO3166-1"="HT"][admin_level=2]->.h;
(nwr["landuse"="quarry"](area.h);
 nwr["industrial"="mine"](area.h);
 nwr["man_made"~"mineshaft|adit"](area.h););
out tags center;""",
}


def _telecharger(nom: str) -> dict | None:
    for url in OVERPASS:
        try:
            r = requests.post(url, data={"data": REQUETES[nom]}, timeout=150)
            if r.ok:
                d = r.json()
                d["_maj"] = datetime.now().strftime("%Y-%m-%d %H:%M")
                (CACHE / f"{nom}.json").write_text(json.dumps(d), encoding="utf-8")
                return d
        except Exception:
            continue
    return None


@st.cache_data(ttl=7 * 24 * 3600, show_spinner=False)
def charger_osm(nom: str) -> dict:
    """Copie locale si elle existe, sinon téléchargement (cache 7 jours)."""
    f = CACHE / f"{nom}.json"
    if f.exists():
        return json.loads(f.read_text(encoding="utf-8"))
    return _telecharger(nom) or {"elements": [], "_maj": None}


def actualiser_osm() -> bool:
    ok = all(_telecharger(n) is not None for n in REQUETES)
    charger_osm.clear()
    return ok


@st.cache_data(show_spinner=False)
def charger_csv() -> tuple[pd.DataFrame, pd.DataFrame]:
    res = pd.read_csv(DATA / "ressources_haiti.csv")
    rel = pd.read_csv(DATA / "reliefs_haiti.csv")
    return res, rel


# ---------------------------------------------------------------- construction
def _popup_ressource(r: pd.Series, lang: str) -> str:
    desc = r["description_en"] if lang == "en" else r["description_fr"]
    src = (f'<a href="{r.source_url}" target="_blank">{r.source_nom}</a>'
           if isinstance(r.source_url, str) and r.source_url else str(r.source_nom))
    return f"""<div style="font-family:system-ui;width:260px">
<b style="font-size:14px">{r.nom}</b><br>
<span style="color:#666">{r.sous_categorie} · {r.commune} ({r.departement})</span>
<p style="margin:6px 0">{desc}</p>
<small><b>Statut :</b> {r.statut}<br><b>Précision :</b> {r.precision}<br>
<b>Source :</b> {src}<br><b>Mis à jour :</b> {r.maj}</small></div>"""


def construire_carte(fond: str, couches: set[str], cats: list[str],
                     res: pd.DataFrame, rel: pd.DataFrame, lang: str) -> folium.Map:
    m = folium.Map(location=CENTRE_HAITI, zoom_start=8, tiles=None,
                   control_scale=True, min_zoom=6, max_bounds=True)

    # Tous les fonds sont ajoutés ; celui choisi est ajouté en dernier = visible
    ordre = [f for f in FONDS if f != fond] + [fond]
    for nom in ordre:
        if nom == "Satellite":
            folium.TileLayer(ESRI_IMG, attr="Imagery © Esri, Maxar, Earthstar",
                             name="Satellite", max_zoom=19).add_to(m)
        else:
            url, attr = FONDS[nom]
            folium.TileLayer(url, attr=attr, name=nom, max_zoom=18).add_to(m)

    # Étiquettes + routes par-dessus (utiles surtout en satellite)
    folium.TileLayer(ESRI_ROADS, attr="© Esri", name="Routes (surcouche)",
                     overlay=True, show=(fond == "Satellite"), opacity=0.9).add_to(m)
    folium.TileLayer(ESRI_LABELS, attr="© Esri", name="Noms des lieux (surcouche)",
                     overlay=True, show=(fond == "Satellite")).add_to(m)

    # Rivières
    if "riv" in couches:
        g = folium.FeatureGroup(name="Rivières", show=True)
        for el in charger_osm("rivieres").get("elements", []):
            pts = [(p["lat"], p["lon"]) for p in el.get("geometry", [])]
            if len(pts) < 2:
                continue
            nom = el.get("tags", {}).get("name", "Rivière")
            folium.PolyLine(pts, color="#0ea5e9", weight=2.5, opacity=0.9,
                            tooltip=nom).add_to(g)
        g.add_to(m)
        gl = folium.FeatureGroup(name="Lacs & étangs", show=True)
        for el in charger_osm("lacs").get("elements", []):
            geom = el.get("geometry")
            if not geom and el.get("members"):
                for mb in el["members"]:
                    if mb.get("role") == "outer" and mb.get("geometry"):
                        geom = mb["geometry"]
                        break
            if not geom or len(geom) < 3:
                continue
            folium.Polygon([(p["lat"], p["lon"]) for p in geom], color="#0284c7",
                           fill=True, fill_color="#38bdf8", fill_opacity=0.55, weight=1,
                           tooltip=el.get("tags", {}).get("name", "Lac")).add_to(gl)
        gl.add_to(m)

    # Sommets & mornes
    if "som" in couches:
        g = folium.FeatureGroup(name="Sommets & mornes", show=True)
        vus = set()
        for _, r in rel[rel.type.isin(["Sommet", "Morne"])].iterrows():
            alt = f" – {int(r.altitude_m)} m" if pd.notna(r.altitude_m) else ""
            folium.Marker((r.lat, r.lon), tooltip=f"▲ {r.nom}{alt}",
                          popup=f"<b>{r.nom}</b>{alt}<br>{r.massif}<br>{r.note}",
                          icon=folium.DivIcon(html=f'<div style="font-size:18px;color:#78350f;'
                                              f'text-shadow:0 0 3px #fff">▲</div>')).add_to(g)
            vus.add(r.nom.lower())
        for el in charger_osm("sommets").get("elements", []):
            t = el.get("tags", {})
            nom = t.get("name", "")
            if nom.lower() in vus:
                continue
            ele = t.get("ele", "")
            folium.CircleMarker((el["lat"], el["lon"]), radius=3, color="#92400e",
                                fill=True, fill_opacity=1,
                                tooltip=f"▲ {nom}" + (f" – {ele} m" if ele else "")).add_to(g)
        g.add_to(m)

    if "mas" in couches:
        g = folium.FeatureGroup(name="Massifs & plaines", show=True)
        for _, r in rel[rel.type.isin(["Massif", "Plaine / plateau"])].iterrows():
            coul = "#57534e" if r.type == "Massif" else "#166534"
            folium.Marker((r.lat, r.lon), tooltip=r.note,
                          icon=folium.DivIcon(icon_size=(160, 20), icon_anchor=(80, 10), html=
                              f'<div style="font:italic 600 12px Georgia;color:{coul};'
                              f'text-align:center;text-shadow:0 0 3px #fff,0 0 3px #fff;'
                              f'white-space:nowrap">{r.nom}</div>')).add_to(g)
        g.add_to(m)

    if "osm_mines" in couches:
        g = folium.FeatureGroup(name="Mines & carrières (OSM)", show=True)
        for el in charger_osm("mines").get("elements", []):
            lat = el.get("lat") or el.get("center", {}).get("lat")
            lon = el.get("lon") or el.get("center", {}).get("lon")
            if lat is None:
                continue
            t = el.get("tags", {})
            folium.CircleMarker((lat, lon), radius=4, color="#57534e", fill=True,
                                fill_color="#a8a29e", fill_opacity=0.9,
                                tooltip=t.get("name", "Carrière / mine (OSM)")
                                + (f" · {t['resource']}" if "resource" in t else "")).add_to(g)
        g.add_to(m)

    # Ressources sourcées par catégorie
    for cat in cats:
        coul, icone = STYLE_CAT.get(cat, ("#334155", "info-sign"))
        g = folium.FeatureGroup(name=f"● {cat}", show=True)
        for _, r in res[res.categorie == cat].iterrows():
            if str(r.precision).startswith("zone"):
                km = "".join(c for c in str(r.precision) if c.isdigit()) or "5"
                folium.Circle((r.lat, r.lon), radius=int(km) * 1000, color=coul,
                              weight=1, fill=True, fill_opacity=0.08).add_to(g)
            folium.Marker((r.lat, r.lon), tooltip=f"{r.nom}",
                          popup=folium.Popup(_popup_ressource(r, lang), max_width=300),
                          icon=folium.Icon(color="white", icon_color=coul,
                                           icon=icone, prefix="fa")).add_to(g)
        g.add_to(m)

    # Outils
    plugins.Fullscreen(position="topleft").add_to(m)
    plugins.MiniMap(toggle_display=True, zoom_level_offset=-5).add_to(m)
    plugins.MeasureControl(primary_length_unit="kilometers",
                           primary_area_unit="hectares").add_to(m)
    plugins.MousePosition(position="bottomleft", separator=" | ",
                          prefix="Lat/Lon :", num_digits=4).add_to(m)
    plugins.LocateControl(position="topleft").add_to(m)
    folium.LayerControl(collapsed=False, position="topright").add_to(m)

    # Légende
    lignes = "".join(f'<div><span style="color:{STYLE_CAT[c][0]};font-size:16px">●</span> {c}</div>'
                     for c in cats if c in STYLE_CAT)
    legende = f"""<div style="position:fixed;bottom:28px;right:10px;z-index:9999;
background:rgba(255,255,255,.93);padding:8px 12px;border-radius:8px;
font:12px system-ui;box-shadow:0 1px 4px rgba(0,0,0,.3)">
<b>Légende</b>{lignes}
<div><span style="color:#0ea5e9">━</span> Rivières</div>
<div><span style="color:#78350f">▲</span> Sommets / mornes</div></div>"""
    m.get_root().html.add_child(folium.Element(legende))
    return m


# ---------------------------------------------------------------- interface
def afficher_carte_avancee(langue: str = "fr") -> None:
    T = TXT.get(langue, TXT["fr"])
    res, rel = charger_csv()

    st.subheader(f"🗺️ {T['titre']}")
    c1, c2, c3 = st.columns([1.3, 2.4, 1.3])
    with c1:
        fond = st.radio(T["fond"], list(FONDS), index=0)
    with c2:
        opts = {"riv": T["riv"], "som": T["som"], "mas": T["mas"], "osm_mines": T["osm_mines"]}
        sel = st.multiselect(T["couches"], list(opts), default=["riv", "som", "mas"],
                             format_func=opts.get)
        cats = st.multiselect(T["cat"], list(STYLE_CAT), default=list(STYLE_CAT))
    with c3:
        if st.button(f"🔄 {T['maj']}", width="stretch"):
            with st.spinner("OpenStreetMap…"):
                ok = actualiser_osm()
            (st.success(T["maj_ok"]) if ok else st.warning(T["maj_ko"]))
        d = charger_osm("rivieres").get("_maj")
        st.caption(f"{T['maj_le']} : {d or T['aucune']}")
        q = st.text_input(T["rech"], "")

    vue = res[res.categorie.isin(cats)]
    if q:
        ql = q.lower()
        vue = vue[vue.apply(lambda r: ql in " ".join(map(str, r.values)).lower(), axis=1)]

    carte = construire_carte(fond, set(sel), cats, vue, rel, langue)
    st_folium(carte, height=680, use_container_width=True, returned_objects=[])
    st.caption(T["approx"])

    with st.expander(f"📋 {T['tab']} ({len(vue)})"):
        st.dataframe(vue[["nom", "categorie", "sous_categorie", "departement", "commune",
                          "statut", "precision", "source_nom", "source_url"]],
                     width="stretch", hide_index=True,
                     column_config={"source_url": st.column_config.LinkColumn("Lien")})
        st.download_button(T["dl"], vue.to_csv(index=False).encode("utf-8"),
                           "ressources_haiti.csv", "text/csv")


if __name__ == "__main__":
    st.set_page_config(page_title="Haïti Explorer – Carte", layout="wide")
    lg = st.sidebar.radio("Langue / Language", ["fr", "en"])
    afficher_carte_avancee(lg)
