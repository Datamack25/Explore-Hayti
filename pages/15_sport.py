import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from src.medias import galerie
from src.ui import SERIES, analyse_box, entete, kpis, pied, setup
from src.utils import CURATED

setup("Sport", "⚽")
entete("Haïti et le sport", "Trophées, participations et grandes victoires : des JO de 1924 à la Coupe du monde 2026.")

p = pd.read_csv(CURATED / "sport_palmares.csv")
f = pd.read_csv(CURATED / "sport_figures.csv")

kpis([
    {"lab": "Médailles olympiques", "val": "2", "sub": "bronze 1924 (tir) · argent 1928 (Silvio Cator)", "style": "accent"},
    {"lab": "Champion CONCACAF", "val": "1973", "sub": "seule équipe caribéenne titrée", "style": "accent"},
    {"lab": "Titres caribéens", "val": "2", "sub": "1979 · 2007 (+ CCCF 1957)"},
    {"lab": "Coupes du monde (hommes)", "val": "2", "sub": "1974 · 2026"},
    {"lab": "Coupe du monde féminine", "val": "2023", "sub": "première qualification"},
    {"lab": "Meilleur classement FIFA", "val": "38e", "sub": "janvier 2013"},
])

st.markdown("### 🏆 Frise des exploits")
couleurs = {"Trophée": SERIES[3], "Médaille": SERIES[1], "Participation": SERIES[0], "Podium": SERIES[2], "Record": SERIES[6]}
symb = {"Trophée": "star", "Médaille": "circle", "Participation": "diamond", "Podium": "triangle-up", "Record": "square"}
fig = go.Figure()
types = list(couleurs)
for i, t in enumerate(types):
    s = p[p.type == t]
    if len(s):
        fig.add_trace(go.Scatter(x=s.annee, y=[t] * len(s), mode="markers", name=t,
                                 marker=dict(size=18, color=couleurs[t], symbol=symb[t], line=dict(color="white", width=2)),
                                 customdata=s[["competition", "resultat", "equipe_athlete"]],
                                 hovertemplate="<b>%{x} – %{customdata[0]}</b><br>%{customdata[1]}<br>%{customdata[2]}<extra></extra>"))
fig.update_layout(height=330, hovermode="closest", showlegend=False, xaxis=dict(dtick=10, showgrid=True),
                  yaxis=dict(categoryorder="array", categoryarray=types[::-1]), margin=dict(l=10, r=10, t=10, b=10))
st.plotly_chart(fig, use_container_width=True)

c1, c2 = st.columns([3, 2])
with c1:
    sp = st.multiselect("Sport", sorted(p.sport.unique()), placeholder="Tous les sports")
    pp = p[p.sport.isin(sp)] if sp else p
    for r in pp.sort_values("annee", ascending=False).itertuples():
        with st.container(border=True):
            ic = {"Trophée": "🏆", "Médaille": "🥇", "Participation": "🌍", "Podium": "🥈", "Record": "📈"}.get(r.type, "•")
            st.markdown(f"**{ic} {r.annee} — {r.competition}** · {r.resultat}  \n"
                        f"<span style='color:#8a8984'>{r.sport} · {r.equipe_athlete}</span>", unsafe_allow_html=True)
            st.markdown(r.description)
            st.caption(f"Source : [{r.source}]({r.url})")
with c2:
    st.markdown("### ⭐ Grandes figures")
    for r in f.itertuples():
        with st.container(border=True):
            st.markdown(f"**{r.nom}** · <span style='color:#8a8984'>{r.sport} ({r.epoque})</span>", unsafe_allow_html=True)
            st.caption(r.fait_marquant)
            st.markdown(f"[En savoir plus]({r.lien})")

analyse_box("À retenir", [
    "Haïti est la **seule nation caribéenne championne de la CONCACAF** (1973), titre qui lui ouvre la Coupe du monde 1974.",
    "Le but d'Emmanuel Sanon contre l'Italie en 1974 reste l'un des moments les plus célèbres de l'histoire du football caribéen.",
    "En 2026, 52 ans après, les Grenadiers retrouvent la Coupe du monde et marquent à nouveau (Lenny Joseph, Wilson Isidore).",
    "Les Grenadières, emmenées par Melchie Dumornay, incarnent la montée en puissance du football féminin haïtien.",
])
galerie("Sport")
pied("Wikipedia (Haiti national football team, Haiti at the Olympics), Concacaf, FIFA, La Presse.")
