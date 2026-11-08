import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from src.medias import galerie
from src.ui import SERIES, analyse_box, entete, kpis, pied, setup
from src.utils import CURATED

setup("Konpa & musique", "🎶")
entete("Le konpa, cœur battant d'Haïti", "De Nemours Jean-Baptiste (1955) à la reconnaissance de l'UNESCO (2025) : 70 ans de konpa.")

k = pd.read_csv(CURATED / "konpa.csv")
kpis([
    {"lab": "Naissance", "val": "1955", "sub": "Nemours Jean-Baptiste", "style": "accent"},
    {"lab": "Patrimoine UNESCO", "val": "2025", "sub": "compas haïtien", "style": "accent"},
    {"lab": "Plus ancien orchestre", "val": "1948", "sub": "Septentrional (Cap-Haïtien)"},
    {"lab": "Ambassadeur mondial", "val": "Tabou Combo", "sub": "fondé en 1968"},
])

st.markdown("### 🕰️ Chronologie")
coul = {"Naissance": SERIES[1], "Groupe": SERIES[0], "Courant": SERIES[2], "Reconnaissance": SERIES[3]}
fig = go.Figure()
for i, (t, s) in enumerate(k.groupby("type")):
    fig.add_trace(go.Scatter(x=s.annee, y=[t] * len(s), mode="markers+text", name=t, text=s.titre.str.slice(0, 26),
                             textposition="top center", textfont=dict(size=10),
                             marker=dict(size=16, color=coul.get(t, SERIES[i]), line=dict(color="white", width=2)),
                             customdata=s[["titre"]], hovertemplate="<b>%{x}</b> – %{customdata[0]}<extra></extra>"))
fig.update_layout(height=360, showlegend=False, hovermode="closest", xaxis=dict(dtick=10), margin=dict(l=10, r=10, t=20, b=10))
st.plotly_chart(fig, use_container_width=True)

for r in k.itertuples():
    with st.container(border=True):
        st.markdown(f"**{r.annee} — {r.titre}** <span class='ay-badge'>{r.type}</span>", unsafe_allow_html=True)
        st.markdown(r.description)
        st.markdown(f"[En savoir plus]({r.lien})")

analyse_box("Pourquoi le konpa compte", [
    "Le konpa est la **bande-son de la vie haïtienne** : fêtes, carnavals, bals, mariages — en Haïti comme dans la diaspora.",
    "Il a fortement influencé le **zouk** des Antilles françaises et circule en Afrique, en Amérique latine et jusqu'au Japon.",
    "Sa reconnaissance par l'UNESCO (2025) et son ouverture aux Latin Grammy (2026) consacrent son rayonnement mondial.",
    "Autres trésors musicaux : rara, twoubadou, musique racine (Boukman Eksperyans, RAM), jazz haïtien, rap kreyòl.",
])
galerie("Konpa")
pied("Wikipedia (Compas, Nemours Jean-Baptiste, Tabou Combo, Septentrional), UNESCO.")
