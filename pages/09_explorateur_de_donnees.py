import pandas as pd
import plotly.express as px
import streamlit as st

from src import data as D
from src.ui import SERIES, entete, fmt, note, pied, setup
from src.utils import CURATED

setup("Explorateur de données", "🗂️")
entete("Explorateur de données", "Tous les fichiers CSV de la plateforme : consulter, filtrer, représenter, télécharger.")

fichiers = D.tous_les_csv()
choix = st.selectbox("Fichier", list(fichiers))
df = pd.read_csv(fichiers[choix])
st.caption(f"`{fichiers[choix].relative_to(fichiers[choix].parents[2])}` · {fmt(len(df))} lignes · {df.shape[1]} colonnes")

with st.expander("🔎 Filtrer", expanded=False):
    filtres = st.multiselect("Colonnes à filtrer", df.columns.tolist())
    for c in filtres:
        if pd.api.types.is_numeric_dtype(df[c]):
            lo, hi = float(df[c].min()), float(df[c].max())
            if lo < hi:
                a, b = st.slider(c, lo, hi, (lo, hi))
                df = df[df[c].between(a, b)]
        else:
            vals = st.multiselect(c, sorted(df[c].dropna().astype(str).unique())[:500])
            if vals:
                df = df[df[c].astype(str).isin(vals)]
    q = st.text_input("Recherche plein texte")
    if q:
        mask = df.astype(str).apply(lambda s: s.str.contains(q, case=False, na=False)).any(axis=1)
        df = df[mask]

st.dataframe(df, hide_index=True, use_container_width=True, height=420)
st.download_button("⬇️ Télécharger (CSV)", df.to_csv(index=False).encode("utf-8"), fichiers[choix].name)

st.markdown("### 📊 Graphique rapide")
num = df.select_dtypes("number").columns.tolist()
cat = [c for c in df.columns if c not in num]
if num:
    a, b, c, d = st.columns(4)
    kind = a.selectbox("Type", ["Barres", "Ligne", "Nuage de points", "Histogramme"])
    x = b.selectbox("Axe X", df.columns.tolist(), index=0)
    y = c.selectbox("Valeur", num, index=0)
    color = d.selectbox("Couleur (≤ 8 groupes)", ["(aucune)"] + [k for k in cat if df[k].nunique() <= 8])
    col = None if color == "(aucune)" else color
    dd = df.head(3000)
    if kind == "Barres":
        g = dd.groupby([x] + ([col] if col else []))[y].sum().reset_index().sort_values(y, ascending=False).head(40)
        fig = px.bar(g, x=x, y=y, color=col, color_discrete_sequence=SERIES)
        fig.update_traces(marker_line_color="white", marker_line_width=2)
    elif kind == "Ligne":
        fig = px.line(dd.sort_values(x), x=x, y=y, color=col, color_discrete_sequence=SERIES)
        fig.update_traces(line_width=2)
    elif kind == "Nuage de points":
        fig = px.scatter(dd, x=x, y=y, color=col, color_discrete_sequence=SERIES)
        fig.update_traces(marker=dict(size=9, line=dict(color="white", width=1)))
    else:
        fig = px.histogram(dd, x=y, color=col, color_discrete_sequence=SERIES)
    fig.update_layout(height=420, hovermode="closest")
    st.plotly_chart(fig, use_container_width=True)
else:
    note("Ce fichier n'a pas de colonne numérique à représenter.")

st.markdown("### 📚 Sources et licences")
src = pd.read_csv(CURATED / "sources.csv")
st.dataframe(src, hide_index=True, use_container_width=True, column_config={"url": st.column_config.LinkColumn("lien")})
pied("Voir le tableau ci-dessus.")
