import pandas as pd
import streamlit as st
from streamlit_folium import st_folium

from src import data as D
from src.charts import carte_points, choropleth
from src.ui import SEQ_ORANGE, entete, fmt, note, pied, setup

setup("Carte interactive", "🗺️")
entete("Carte interactive d'Haïti", "Choisissez un indicateur : la carte se recolore par commune ou par département.")

com, dep = D.communes(), D.departements()

METRIQUES = {
    "Population (2022)": ("population", "habitants", None),
    "Densité (hab/km²)": ("densite_hab_km2", "hab/km²", None),
    "Part des enfants (%)": ("part_enfants_pct", "%", None),
    "Hommes pour 100 femmes": ("ratio_hommes_femmes", "H/100 F", None),
    "Superficie (km²)": ("superficie_km2", "km²", None),
    "Nombre de localités": ("nb_localites", "localités", None),
    "Écoles OSM pour 1 000 enfants (tout le pays)": ("ecoles_osm_pour_1000_enfants", "écoles / 1 000 enfants", "orange"),
    "Établissements d'enseignement OSM": ("nb_etab_education_osm", "établissements", "orange"),
    "Écoles recensées 2022": ("nb_ecoles", "écoles", "orange"),
    "Écoles pour 1 000 enfants (2022)": ("ecoles_pour_1000_enfants", "écoles / 1 000 enfants", "orange"),
    "Part d'écoles publiques (%)": ("part_ecoles_publiques_pct", "%", "orange"),
}

c1, c2, c3 = st.columns([2, 1, 1])
metr = c1.selectbox("Indicateur", list(METRIQUES), index=1)
niveau = c2.radio("Niveau", ["Communes", "Départements"], horizontal=True)
deps = ["Tout le pays"] + sorted(com.departement.unique())
filtre = c3.selectbox("Zoom département", deps)

col, unite, rampe = METRIQUES[metr]
scale = SEQ_ORANGE if rampe == "orange" else None
log = col in ("population", "densite_hab_km2") and niveau == "Communes"

if niveau == "Communes":
    d = com if filtre == "Tout le pays" else com[com.departement == filtre]
    d = d.copy()
    plot_col = col
    if log:
        import numpy as np
        d["_log"] = np.log10(d[col])
        plot_col = "_log"
    fig = choropleth(d, D.geojson("communes"), plot_col, metr + (" (échelle log)" if log else ""),
                     hover=["departement", col, "population"], scale=scale)
    if log:
        fig.update_coloraxes(colorbar=dict(tickvals=[3, 4, 5, 6], ticktext=["1 000", "10 000", "100 000", "1 000 000"]))
    if filtre != "Tout le pays":
        fig.update_layout(map=dict(center=dict(lat=d.lat.mean(), lon=d.lon.mean()), zoom=8.3))
else:
    if col not in dep.columns:
        st.info("Indicateur disponible seulement au niveau communal.")
        st.stop()
    fig = choropleth(dep, D.geojson("departements"), col, metr, key="adm1_pcode", nom="departement",
                     hover=["population", "chef_lieu"], scale=scale)

st.plotly_chart(fig, use_container_width=True, config={"displaylogo": False})
if "ecoles" in col and "osm" not in col:
    note("La cartographie scolaire 2022 ne couvre que la Grand'Anse, les Nippes, le Sud et 8 communes de l'Ouest : "
         "les communes grisées ne sont pas renseignées (et non « sans école »).", "warn")

# Classement
src = com if niveau == "Communes" else dep
nomcol = "commune" if niveau == "Communes" else "departement"
if filtre != "Tout le pays" and niveau == "Communes":
    src = src[src.departement == filtre]
r = src[[nomcol, "departement", col]].dropna().sort_values(col, ascending=False) if niveau == "Communes" \
    else src[[nomcol, col]].dropna().sort_values(col, ascending=False)
a, b = st.columns(2)
a.markdown(f"**▲ Valeurs les plus élevées** — {metr}")
a.dataframe(r.head(10), hide_index=True, use_container_width=True)
b.markdown("**▼ Valeurs les plus faibles**")
b.dataframe(r.tail(10).iloc[::-1], hide_index=True, use_container_width=True)

st.divider()
st.subheader("📍 Carte des lieux et institutions")
st.caption("Cochez les couches dans le coin de la carte. Les marqueurs se regroupent automatiquement ; zoomez pour les détailler.")
loc, inst = D.localites(), D.institutions()
couches = st.multiselect("Couches", ["Villes et grandes villes", "Villages", "Quartiers", "Universités", "Santé",
                                     "Mairies", "Écoles (OpenStreetMap)", "Institutions OpenStreetMap"],
                         default=["Villes et grandes villes", "Universités", "Santé", "Mairies"])
pts = []
if "Villes et grandes villes" in couches:
    pts.append(loc[loc.type.isin(["Ville", "Grande ville", "Capitale"])].assign(categorie="Villes"))
if "Villages" in couches:
    pts.append(loc[loc.type == "Village"].assign(categorie="Villages"))
if "Quartiers" in couches:
    pts.append(loc[loc.type == "Quartier"].assign(categorie="Quartiers"))
base = inst[inst.precision_localisation != "point GPS (OpenStreetMap)"]
base = base[base.source.fillna("").str.startswith("OpenStreetMap") == False]  # noqa: E712
if "Universités" in couches:
    pts.append(base[base.categorie == "Université / Enseignement supérieur"])
if "Santé" in couches:
    pts.append(base[base.categorie == "Santé"])
if "Mairies" in couches:
    pts.append(base[base.categorie == "Administration locale"])
if "Écoles (OpenStreetMap)" in couches:
    e = D.etablissements_education_osm()
    pts.append(e[e.type != "Bâtiment scolaire"].assign(categorie="École", sous_type=e.type))
if "Institutions OpenStreetMap" in couches:
    osm = D.osm_institutions()
    if osm.empty:
        st.info("Aucune donnée OpenStreetMap encore téléchargée : lancez la mise à jour (page 🔄).")
    else:
        pts.append(osm)
if filtre != "Tout le pays":
    pts = [p[p.departement == filtre] for p in pts]

if pts:
    P = pd.concat(pts, ignore_index=True)
    # léger décalage pour les points positionnés au centre de la commune (sinon superposés)
    approx = P.get("precision_localisation", pd.Series(index=P.index, dtype=str)).fillna("") == "commune"
    if approx.any():
        import numpy as np
        rng = np.random.default_rng(1)
        P.loc[approx, "lat"] += rng.normal(0, 0.006, approx.sum())
        P.loc[approx, "lon"] += rng.normal(0, 0.006, approx.sum())
    couleurs = {"Villes": "#0d366b", "Villages": "#86b6ef", "Quartiers": "#6250d6"}
    from src.charts import COULEUR_CATEGORIE
    couleurs.update(COULEUR_CATEGORIE)
    zoom = 8 if filtre == "Tout le pays" else 9
    centre = (P.lat.mean(), P.lon.mean()) if filtre != "Tout le pays" else None
    m = carte_points(P, "categorie", ["nom", "type", "sous_type", "commune", "departement", "precision_localisation"],
                     geo_communes=D.geojson("communes"), zoom=zoom, centre=centre, couleurs=couleurs)
    st_folium(m, height=620, use_container_width=True, returned_objects=[])
    st.caption(f"{fmt(len(P))} points affichés. Les institutions sans coordonnées GPS sont placées au centre de leur commune "
               "(précision indiquée dans l'info-bulle).")

pied("geoBoundaries (contours), CNIGS (P-codes), HDX (population 2022), OpenStreetMap (localités), MENFP (écoles, IES).")
