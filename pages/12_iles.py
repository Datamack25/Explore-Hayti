import plotly.graph_objects as go
import streamlit as st

from src import data as D
from src import territoire as T
from src.charts import MAP_STYLE
from src.ui import SERIES, entete, fmt, kpis, pied, setup

setup("Les îles", "🏝️")
entete("Les îles d'Haïti", "La Gonâve, la Tortue, l'Île-à-Vache, les Cayemites, les Arcadins… et Navase.")

il = T.iles()
hab = il.population_2022.sum()
kpis([
    {"lab": "Îles et archipels", "val": str(len(il)), "style": "accent"},
    {"lab": "Habitants (îles-communes)", "val": fmt(hab), "sub": "population 2022"},
    {"lab": "Plus grande île", "val": "La Gonâve", "sub": f"{fmt(il.superficie_km2.max(), 0)} km²"},
])

geo = D.geojson("communes")
pcs = {p for x in il.pcodes for p in str(x).split(";") if p}
feat = {"type": "FeatureCollection", "features": [f for f in geo["features"] if f["id"] in pcs]}
fig = go.Figure()
fig.add_trace(go.Choroplethmap(geojson=feat, locations=[f["id"] for f in feat["features"]],
                               z=[1] * len(feat["features"]), featureidkey="id", showscale=False,
                               colorscale=[[0, SERIES[0]], [1, SERIES[0]]], marker_opacity=0.55, marker_line_color="white",
                               text=[f["properties"]["commune"] for f in feat["features"]], hovertemplate="%{text}<extra></extra>"))
fig.add_trace(go.Scattermap(lat=il.lat, lon=il.lon, mode="markers+text", text=il.ile, textposition="top center",
                            marker=dict(size=12, color=SERIES[1]), hovertemplate="<b>%{text}</b><extra></extra>",
                            textfont=dict(size=12, color="#0b0b0b")))
fig.update_layout(map=dict(style=MAP_STYLE, zoom=6.4, center=dict(lat=18.95, lon=-73.3)), height=560,
                  margin=dict(l=0, r=0, t=0, b=0), showlegend=False)
st.plotly_chart(fig, use_container_width=True)

for x in il.itertuples():
    with st.container(border=True):
        a, b = st.columns([3, 2])
        a.markdown(f"#### {x.ile}")
        a.markdown(x.description)
        a.caption(f"Département : {x.departement} · communes : {x.communes}")
        if x.population_2022 == x.population_2022 and x.population_2022:
            b.metric("Population 2022", fmt(x.population_2022))
            b.metric("Superficie", f"{fmt(x.superficie_km2, 1)} km²")
            b.caption(f"{int(x.localites)} localités recensées")
        else:
            b.caption("Pas de commune propre dans le découpage CNIGS 2018 (îlots ou île rattachée).")

st.dataframe(il.drop(columns=["pcodes"]), hide_index=True, use_container_width=True)
pied("CNIGS (communes insulaires), HDX (population 2022), geoBoundaries.")
