import plotly.graph_objects as go
import streamlit as st

from src import data as D
from src import territoire as T
from src.charts import MAP_STYLE, fond_haiti
from src.ui import SERIES, entete, fmt, kpis, note, pied, setup

setup("Routes & transports", "🛣️")
entete("Routes, aéroports et ports", "Le réseau routier national, les aéroports et les ports du pays.")

osm = T.routes_osm()
sch = T.routes_schematiques()
tr = T.transports()

if osm:
    gj, source = osm, "OpenStreetMap (tracé réel)"
else:
    gj, source = sch, "tracé schématique entre villes (en attendant la mise à jour OpenStreetMap)"
lg = T.longueur_km(gj)
kpis([
    {"lab": "Réseau représenté", "val": f"{fmt(lg.km.sum())} km", "sub": source, "style": "accent"},
    {"lab": "Aéroports", "val": str(tr.type.str.contains("Aéroport", na=False).sum()), "sub": "dont 2 internationaux"},
    {"lab": "Ports", "val": str((tr.type == "Port").sum())},
])
if not osm:
    note("Ce tracé relie les villes traversées par chaque route nationale : il donne l'orientation générale, pas le tracé "
         "exact. La mise à jour (page 🔄) télécharge le vrai réseau OpenStreetMap (autoroutes, nationales, départementales).",
         "warn")

couleur_classe = {"Autoroute": SERIES[7], "Route nationale principale": SERIES[1], "Route nationale": SERIES[0],
                  "Route départementale": "#86b6ef"}
fig = go.Figure()
if osm:
    for cl, col in couleur_classe.items():
        lats, lons = [], []
        for f in gj["features"]:
            if f["properties"].get("classe") == cl:
                c = f["geometry"]["coordinates"]
                lons += [p[0] for p in c] + [None]
                lats += [p[1] for p in c] + [None]
        if lats:
            fig.add_trace(go.Scattermap(lat=lats, lon=lons, mode="lines", name=cl,
                                        line=dict(width=3 if "nationale" in cl.lower() else 1.5, color=col), hoverinfo="name"))
else:
    for i, f in enumerate(gj["features"]):
        c = f["geometry"]["coordinates"]
        p = f["properties"]
        fig.add_trace(go.Scattermap(lat=[x[1] for x in c], lon=[x[0] for x in c], mode="lines+markers",
                                    name=f"{p['ref']} – {p['nom']}" if p["ref"] != "—" else p["nom"],
                                    line=dict(width=3, color=SERIES[i % 8]), marker=dict(size=6),
                                    hovertemplate=p["villes"] + "<extra></extra>"))
for typ, sym, col in [("Aéroport", "airport", SERIES[6]), ("Port", "harbor", SERIES[3])]:
    sub = tr[tr.type.str.contains(typ, na=False)].dropna(subset=["lat"])
    fig.add_trace(go.Scattermap(lat=sub.lat, lon=sub.lon, mode="markers", name=typ + "s", text=sub.nom,
                                marker=dict(size=13, color=col), hovertemplate="<b>%{text}</b><extra></extra>"))
fond_haiti(fig, D.geojson("communes"))
fig.update_layout(map=dict(style=MAP_STYLE, zoom=6.9, center=dict(lat=18.95, lon=-72.75)), height=620,
                  margin=dict(l=0, r=0, t=0, b=0), legend=dict(y=0.02, x=0.01, bgcolor="rgba(255,255,255,.85)"))
st.plotly_chart(fig, use_container_width=True)

a, b = st.columns(2)
with a:
    st.markdown("**Routes**")
    if osm:
        st.dataframe(lg.groupby("classe").km.sum().round(0).reset_index().sort_values("km", ascending=False),
                     hide_index=True, use_container_width=True)
        st.dataframe(lg[lg.ref != ""].groupby("ref").km.sum().round(0).reset_index().sort_values("km", ascending=False).head(25),
                     hide_index=True, use_container_width=True)
    else:
        st.dataframe(lg[["ref", "nom", "villes", "km"]].round(0), hide_index=True, use_container_width=True)
        st.caption("Longueur à vol d'oiseau entre villes successives (sous-estime la distance réelle).")
with b:
    st.markdown("**Aéroports et ports**")
    st.dataframe(tr[["nom", "type", "code", "commune", "remarque"]].fillna(""), hide_index=True, use_container_width=True, height=420)

st.markdown("**Distances depuis Port-au-Prince**")
pap = T.localiser_ville("Port-au-Prince")
villes = ["Cap-Haïtien", "Gonaïves", "Les Cayes", "Jacmel", "Jérémie", "Hinche", "Port-de-Paix", "Fort-Liberté", "Miragoâne"]
rows = []
for v in villes:
    c = T.localiser_ville(v)
    if c:
        d = T.haversine(pap, c)
        rows.append({"ville": v, "distance_km_vol_oiseau": round(d), "route_estimee_km": round(d * 1.35)})
st.dataframe(rows, hide_index=True, use_container_width=True)
st.caption("Distance routière estimée = vol d'oiseau × 1,35 (coefficient de détour usuel en relief montagneux).")
pied("Routes nationales : liste vérifiée + OpenStreetMap (ODbL) ; aéroports/ports : Natural Earth, OpenStreetMap, sources publiques.")
