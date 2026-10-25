import subprocess
import sys

import pandas as pd
import streamlit as st

from src import data as D
from src.utils import ROOT
from src.ui import entete, note, pied, setup

setup("Actualités & mises à jour", "🔄")
entete("Actualités & mises à jour", "Les chiffres les plus récents, leurs sources, et la mise à jour automatique des données.")

st.markdown("### 🔄 Mettre à jour les données")
note("Mises à jour <b>automatiques</b> par l'action GitHub : <b>toutes les 6 heures</b> pour les actualités (médias haïtiens, "
     "diaspora, presse internationale — recherches « Haïti », « Ayiti », « Hayti ») et l'IPC ; <b>chaque lundi</b> pour la "
     "Banque mondiale, OpenStreetMap (écoles, universités, santé, police, banques…), les routes, aéroports et ports. "
     "Les sources d'actualités se gèrent dans <code>data/curated/sources_actualites.csv</code>.")
c1, c2 = st.columns([1, 2])
mode = c2.radio("Étendue", ["Actualités seulement (rapide)", "Tout sauf OpenStreetMap", "Complet (1 à 6 minutes)"],
                horizontal=True)
if c1.button("🔄 Mettre à jour maintenant", type="primary"):
    opt = {"Actualités seulement (rapide)": ["--rapide"], "Tout sauf OpenStreetMap": ["--sans-osm"]}.get(mode, [])
    cmd = [sys.executable, str(ROOT / "scripts" / "update_all.py")] + opt
    with st.status("Mise à jour en cours…", expanded=True) as status:
        p = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True, timeout=900)
        st.code((p.stdout or "") + (p.stderr or ""), language="text")
        status.update(label="Mise à jour terminée" if p.returncode == 0 else "Mise à jour terminée avec erreurs",
                      state="complete" if p.returncode == 0 else "error")
    D.vider_cache()
    st.success("Les pages utilisent désormais les nouvelles données.")
st.caption("Sur Streamlit Community Cloud, les fichiers téléchargés par ce bouton sont temporaires (perdus au redémarrage) : "
           "c'est l'action GitHub qui les enregistre durablement dans le dépôt.")

st.markdown("### 📒 Journal des mises à jour")
j = D.journal()
if j.empty:
    st.info("Aucune mise à jour encore effectuée.")
else:
    st.dataframe(j.iloc[::-1].head(30), hide_index=True, use_container_width=True)

st.markdown("### 📌 Chiffres récents vérifiés (avec sources)")
act = D.indicateurs_actuels()
th = st.multiselect("Thèmes", sorted(act.theme.unique()), default=sorted(act.theme.unique()))
st.dataframe(act[act.theme.isin(th)][["theme", "indicateur", "periode", "valeur", "unite", "statut", "source", "url", "date_collecte"]],
             hide_index=True, use_container_width=True, column_config={"url": st.column_config.LinkColumn("lien")})
st.caption("Pour ajouter un chiffre : une ligne dans data/curated/indicateurs_actuels.csv (thème, indicateur, période, valeur, "
           "unité, statut, source, lien, date de collecte). Il apparaît aussitôt dans la plateforme.")

st.markdown("### 📰 Toutes les actualités sur Haïti")
from src.composants import fil_actualites, filtrer_actualites  # noqa: E402
news = D.actualites_enrichies()
if news.empty:
    st.info("Lancez la mise à jour pour charger les actualités.")
else:
    f1, f2, f3, f4 = st.columns([1, 2, 2, 2])
    pos = f1.toggle("Positif d'abord", value=True)
    th = f2.multiselect("Thèmes", sorted(news.theme.unique()), placeholder="Tous les thèmes")
    ton = f3.multiselect("Tonalité", ["Positif", "Neutre", "Négatif"], placeholder="Toutes")
    q = f4.text_input("Rechercher", placeholder="mot-clé…")
    n = filtrer_actualites(news, pos, th, q)
    if ton:
        n = n[n.tonalite.isin(ton)]
    import plotly.express as px  # noqa: E402
    k = news.groupby(["theme", "tonalite"]).size().reset_index(name="articles")
    fig = px.bar(k, x="articles", y="theme", color="tonalite", orientation="h",
                 color_discrete_map={"Positif": "#0ca30c", "Neutre": "#c3c2b7", "Négatif": "#d03b3b"},
                 category_orders={"tonalite": ["Positif", "Neutre", "Négatif"]}, labels={"theme": "", "tonalite": ""},
                 title="Articles par thème et tonalité")
    fig.update_traces(marker_line_color="white", marker_line_width=1.5)
    fig.update_layout(height=360, hovermode="closest")
    a, b = st.columns([3, 2])
    with a:
        st.caption(f"{len(n)} articles affichés sur {len(news)}")
        with st.container(height=640):
            fil_actualites(n, n=150)
    with b:
        st.plotly_chart(fig, use_container_width=True)
        srcs = news.source.value_counts().head(15).reset_index()
        srcs.columns = ["source", "articles"]
        st.dataframe(srcs, hide_index=True, use_container_width=True)
    st.download_button("⬇️ Actualités (CSV)", n.to_csv(index=False).encode("utf-8"), "actualites_haiti.csv")
    with st.expander("Sources d'actualités suivies"):
        st.dataframe(pd.read_csv(ROOT / "data" / "curated" / "sources_actualites.csv"), hide_index=True,
                     use_container_width=True, column_config={"url": st.column_config.LinkColumn("flux")})

hdx = ROOT / "data" / "live" / "hdx_catalogue_haiti.csv"
if hdx.exists():
    st.markdown("### 🗃️ Jeux de données récents sur HDX (pistes d'enrichissement)")
    st.dataframe(pd.read_csv(hdx), hide_index=True, use_container_width=True,
                 column_config={"url": st.column_config.LinkColumn("lien")})

pied("Banque mondiale, HDX/OCHA, ReliefWeb, OpenStreetMap, FMI, IPC, OIM, MENFP.")
