import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from src import data as D
from src.ui import SERIES, STATUT, entete, fmt, kpis, note, pied, setup

setup("Humanitaire & sécurité alimentaire", "🆘")
entete("Humanitaire & sécurité alimentaire", "Insécurité alimentaire (IPC), déplacements de population, santé et acteurs présents.")

act = D.indicateurs_actuels()


def v(ind):
    d = act[act.indicateur == ind]
    return d.iloc[-1] if len(d) else None


r3, r4, idp = v("Personnes en phase IPC 3+ (crise ou pire)"), v("Personnes en phase IPC 4 (urgence)"), v("Personnes déplacées internes")
kpis([
    {"lab": "Phase IPC 3+ (crise ou pire)", "val": fmt(r3.valeur) if r3 is not None else "–",
     "sub": f"{r3.periode} · 52 % de la population analysée" if r3 is not None else "", "style": "alert"},
    {"lab": "Phase IPC 4 (urgence)", "val": fmt(r4.valeur) if r4 is not None else "–", "sub": r4.periode if r4 is not None else "", "style": "alert"},
    {"lab": "Personnes déplacées internes", "val": "≈ " + fmt(idp.valeur) if idp is not None else "–",
     "sub": f"{idp.periode} · ~80 % hors de Port-au-Prince" if idp is not None else "", "style": "alert"},
])

st.markdown("### Insécurité alimentaire aiguë (IPC)")
ipc = D.ipc_historique()
live = D.ipc_live()
a, b = st.columns(2)
with a:
    h = ipc[ipc.phase.astype(str).str.fullmatch(r"\d")].copy().sort_values("phase")
    if len(h):
        h["phase_lab"] = "Phase " + h.phase.astype(str)
        h["pct"] = 100 * h.pourcentage.astype(float)
        couleurs = {"Phase 1": "#c9e7c9", "Phase 2": STATUT["alerte"], "Phase 3": STATUT["serieux"],
                    "Phase 4": STATUT["critique"], "Phase 5": "#7a1c1c"}
        fig = px.bar(h, x="pct", y=["Mars-juin 2023"] * len(h), color="phase_lab", orientation="h",
                     color_discrete_map=couleurs, text=h.pct.round(0).astype(int).astype(str) + " %",
                     labels={"pct": "% de la population", "y": "", "phase_lab": ""},
                     title=f"Répartition par phase IPC – {h.date_analyse.iloc[0]} (projection)")
        fig.update_traces(marker_line_color="white", marker_line_width=2, textposition="inside")
        fig.update_layout(height=230, hovermode="closest", barmode="stack", yaxis_visible=False)
        st.plotly_chart(fig, use_container_width=True)
        st.caption("Phase 1 minimale · 2 stress · 3 crise · 4 urgence · 5 catastrophe/famine. "
                   "Les phases 3 à 5 nécessitent une action urgente.")
with b:
    evo = pd.DataFrame({"periode": ["mars-juin 2023", "sept. 2025 (proj.)", "mars-juin 2026 (proj.)"],
                        "phase3plus": [float(ipc[ipc.phase.astype(str) == "3+"].nombre.iloc[0]) if (ipc.phase.astype(str) == "3+").any() else None,
                                       5_910_000, 5_830_000]})
    fig = go.Figure(go.Bar(x=evo.periode, y=evo.phase3plus, marker=dict(color=STATUT["critique"], cornerradius=4),
                           text=[fmt(x) for x in evo.phase3plus], textposition="outside",
                           hovertemplate="%{x} : %{y:,.0f} personnes<extra></extra>"))
    fig.update_layout(title="Personnes en phase IPC 3 ou plus", height=330, hovermode="closest", yaxis_title="personnes")
    st.plotly_chart(fig, use_container_width=True)
note("Zones en phase 4 (urgence) en 2026 selon l'IPC : Nord-Ouest (2 zones), Artibonite (3 zones hors Gonaïves), Bas-Plateau, "
     "camps de déplacés, île de la Gonâve, arrondissement de Belle-Anse, quartiers pauvres de Port-au-Prince et Cité Soleil. "
     "L'ouragan Melissa (oct. 2025) a frappé le Sud, la Grand'Anse et les Nippes.", "warn")
if not live.empty:
    st.markdown("**Dernières données IPC téléchargées (HDX)**")
    st.dataframe(live, hide_index=True, use_container_width=True)

st.markdown("### 🦠 COVID-19 : la situation en juillet 2020 (archive)")
cov = D.covid()
car = cov[cov.pays.isin(["Haiti", "Dominican Republic", "Jamaica", "Cuba", "Trinidad and Tobago", "Bahamas", "Guyana",
                         "Suriname", "Barbados", "Belize"])].copy()
car["pays"] = car.pays.replace({"Haiti": "Haïti", "Dominican Republic": "Rép. dominicaine", "Jamaica": "Jamaïque",
                                "Trinidad and Tobago": "Trinité-et-Tobago", "Guyana": "Guyana", "Belize": "Belize"})
a, b = st.columns(2)
with a:
    d = car.sort_values("cas_confirmes")
    fig = go.Figure(go.Bar(x=d.cas_confirmes, y=d.pays, orientation="h",
                           marker=dict(color=[SERIES[1] if p == "Haïti" else "#b7d3f6" for p in d.pays], cornerradius=4),
                           hovertemplate="%{y} : %{x:,.0f} cas<extra></extra>"))
    fig.update_layout(title="Cas confirmés – Caraïbes (27 juillet 2020)", height=380, xaxis_type="log", hovermode="closest")
    st.plotly_chart(fig, use_container_width=True)
with b:
    d = car.sort_values("deces_pour_100_cas")
    fig = go.Figure(go.Bar(x=d.deces_pour_100_cas, y=d.pays, orientation="h",
                           marker=dict(color=[SERIES[1] if p == "Haïti" else "#b7d3f6" for p in d.pays], cornerradius=4),
                           hovertemplate="%{y} : %{x:.2f} décès pour 100 cas<extra></extra>"))
    fig.update_layout(title="Létalité apparente (décès pour 100 cas)", height=380, hovermode="closest")
    st.plotly_chart(fig, use_container_width=True)
st.caption("Jeu de données « country_wise_latest » (Johns Hopkins, via Kaggle), arrêté fin juillet 2020 : utile comme archive, "
           "pas comme situation actuelle. Les faibles chiffres reflètent aussi un dépistage limité.")

st.markdown("### 🤝 Organisations humanitaires présentes (2020)")
org = D.organisations()
if org.empty:
    st.info("Fichier non disponible.")
else:
    a, b = st.columns([3, 2])
    with a:
        fig = px.treemap(org.head(80), path=["categorie", "organisation"], values="nb_contacts_2020", color="categorie",
                         color_discrete_sequence=SERIES, title="80 premières organisations (taille = nombre de contacts recensés)")
        fig.update_traces(marker=dict(line=dict(color="white", width=2)))
        fig.update_layout(height=520, margin=dict(t=50, l=0, r=0, b=0))
        st.plotly_chart(fig, use_container_width=True)
    with b:
        k = org.groupby("categorie").agg(organisations=("organisation", "size"), contacts=("nb_contacts_2020", "sum")).reset_index()
        st.dataframe(k.sort_values("organisations", ascending=False), hide_index=True, use_container_width=True)
        note("La base d'origine contenait des noms et e-mails de personnes : seule la liste des organisations est conservée "
             "(aucune donnée personnelle publiée).")
    st.dataframe(org[["organisation", "categorie", "nb_contacts_2020"]], hide_index=True, use_container_width=True, height=300)

pied("IPC (analyses 2023 et projection mars-juin 2026), OIM/DTM via Reuters (sept. 2026), Johns Hopkins CSSE (COVID-19, 2020), "
     "base ONG AVL (2020, agrégée).")
