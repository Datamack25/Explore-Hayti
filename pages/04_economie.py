import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from src import data as D
from src.analyse import analyser_serie, correlation_texte
from src.charts import serie_temporelle
from src.indicateurs import INDICATEURS_CLES, THEMES_FICHIERS
from src.ui import DIVERGENT, SERIES, analyse_box, entete, fmt, kpis, note, pied, setup

setup("Économie & finances", "📈")
entete("Économie & finances", "Plus de 600 indicateurs de la Banque mondiale depuis 1960, complétés par les chiffres récents du FMI.")

wb = D.wb()
act = D.indicateurs_actuels()


def recent(ind: str) -> pd.DataFrame:
    d = act[act.indicateur == ind].copy()
    d["annee"] = pd.to_numeric(d.periode, errors="coerce")
    return d.dropna(subset=["annee"])[["annee", "valeur"]]


# --- Tableau de bord
items = []
for code, lab, suf in [("NY.GDP.MKTP.CD", "PIB", " USD"), ("NY.GDP.PCAP.CD", "PIB / habitant", " USD"),
                       ("FP.CPI.TOTL.ZG", "Inflation", " %"), ("BX.TRF.PWKR.DT.GD.ZS", "Transferts diaspora", " % PIB"),
                       ("PA.NUS.FCRF", "Taux de change", " HTG/USD"), ("DT.ODA.ODAT.CD", "Aide reçue", " USD")]:
    v, a = D.derniere_valeur(code)
    items.append({"lab": lab, "val": fmt(v, 1) + suf if v is not None else "–", "sub": f"Banque mondiale · {a}" if a else ""})
kpis(items)

LIEN_RECENT = {"NY.GDP.MKTP.KD.ZG": "Croissance du PIB réel", "FP.CPI.TOTL.ZG": "Inflation (prix à la consommation)"}

tab1, tab2, tab3, tab4 = st.tabs(["📊 Explorer un indicateur", "⚖️ Comparer", "🔗 Corrélations", "📋 Catalogue"])

with tab1:
    c1, c2 = st.columns([1, 2])
    mode = c1.radio("Sélection", ["Indicateurs clés (FR)", "Tous les indicateurs"], horizontal=False)
    if mode == "Indicateurs clés (FR)":
        dispo = [c for c in INDICATEURS_CLES if c in set(wb.code)]
        themes = sorted({INDICATEURS_CLES[c][1] for c in dispo})
        th = c2.selectbox("Thème", themes, index=themes.index("Croissance & revenus") if "Croissance & revenus" in themes else 0)
        opts = [c for c in dispo if INDICATEURS_CLES[c][1] == th]
        code = c2.selectbox("Indicateur", opts, format_func=lambda c: INDICATEURS_CLES[c][0])
        unite = INDICATEURS_CLES[code][2]
    else:
        th = c2.selectbox("Fichier thématique", list(THEMES_FICHIERS), format_func=THEMES_FICHIERS.get)
        sub = wb[wb.themes.fillna("").str.contains(th)].drop_duplicates("code")
        code = c2.selectbox("Indicateur", sub.code.tolist(), format_func=lambda c: sub.set_index("code").loc[c, "libelle"])
        unite = ""
    s = D.serie(code)
    lib = s.libelle.iloc[0] if len(s) else code
    rec = recent(LIEN_RECENT[code]) if code in LIEN_RECENT else None
    if rec is not None and len(s):
        rec = pd.concat([s[s.annee == s.annee.max()][["annee", "valeur"]], rec[rec.annee > s.annee.max()]])
    st.plotly_chart(serie_temporelle(s, lib, unite, actuels=rec), use_container_width=True)
    a, b = st.columns([3, 2])
    with a:
        analyse_box("Analyse automatique", analyser_serie(s, lib, unite))
    with b:
        st.caption(f"Code : `{code}` · source : {s.source.iloc[-1] if len(s) else '–'}")
        st.dataframe(s[["annee", "valeur"]].sort_values("annee", ascending=False), hide_index=True, height=260,
                     use_container_width=True)
        st.download_button("⬇️ Série (CSV)", s.to_csv(index=False).encode("utf-8"), f"{code}.csv")

with tab2:
    note("Pour comparer des grandeurs d'unités différentes, les séries sont <b>indexées (base 100)</b> sur une année commune "
         "— jamais de double axe.")
    dispo = [c for c in INDICATEURS_CLES if c in set(wb.code)]
    choix = st.multiselect("Indicateurs (jusqu'à 4)", dispo, default=["NY.GDP.PCAP.KD", "BX.TRF.PWKR.CD.DT", "DT.ODA.ODAT.CD"],
                           format_func=lambda c: INDICATEURS_CLES[c][0], max_selections=4)
    if choix:
        data = pd.concat([D.serie(c).assign(lib=INDICATEURS_CLES[c][0]) for c in choix])
        communs = sorted(set.intersection(*[set(D.serie(c).annee) for c in choix]))
        if communs:
            base = st.select_slider("Année de base (= 100)", communs, value=communs[0])
            data = data.merge(data[data.annee == base][["lib", "valeur"]].rename(columns={"valeur": "v0"}), on="lib")
            data["indice"] = 100 * data.valeur / data.v0
            fig = px.line(data[data.annee >= base], x="annee", y="indice", color="lib", color_discrete_sequence=SERIES,
                          labels={"annee": "", "indice": f"indice (base 100 = {base})", "lib": ""})
            fig.update_traces(line_width=2)
            fig.add_hline(y=100, line=dict(color="#c3c2b7", width=1))
            fig.update_layout(height=450)
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Ces indicateurs n'ont pas d'année commune.")
        st.markdown("**Petits multiples (valeurs réelles)**")
        cols = st.columns(min(2, len(choix)))
        for i, c in enumerate(choix):
            s = D.serie(c)
            f = go.Figure(go.Scatter(x=s.annee, y=s.valeur, mode="lines", line=dict(color=SERIES[i], width=2)))
            f.update_layout(title=INDICATEURS_CLES[c][0], height=260, yaxis_title=INDICATEURS_CLES[c][2])
            cols[i % len(cols)].plotly_chart(f, use_container_width=True)

with tab3:
    dispo = [c for c in INDICATEURS_CLES if c in set(wb.code) and len(D.serie(c)) >= 15]
    defaut = [c for c in ["NY.GDP.PCAP.KD", "FP.CPI.TOTL.ZG", "BX.TRF.PWKR.DT.GD.ZS", "SP.URB.TOTL.IN.ZS",
                          "NE.IMP.GNFS.ZS", "SP.DYN.LE00.IN", "AG.LND.FRST.ZS", "FS.AST.PRVT.GD.ZS"] if c in dispo]
    sel = st.multiselect("Indicateurs de la matrice", dispo, default=defaut, format_func=lambda c: INDICATEURS_CLES[c][0])
    if len(sel) >= 2:
        wide = wb[wb.code.isin(sel)].pivot_table(index="annee", columns="code", values="valeur")
        corr = wide.corr(min_periods=10).rename(index=lambda c: INDICATEURS_CLES[c][0], columns=lambda c: INDICATEURS_CLES[c][0])
        fig = px.imshow(corr, color_continuous_scale=DIVERGENT[::-1], zmin=-1, zmax=1, text_auto=".2f", aspect="auto",
                        title="Matrice de corrélation (Pearson, années communes)")
        fig.update_layout(height=120 + 55 * len(sel), hovermode="closest")
        st.plotly_chart(fig, use_container_width=True)
        a, b = st.columns(2)
        x = a.selectbox("Indicateur A", sel, format_func=lambda c: INDICATEURS_CLES[c][0])
        y = b.selectbox("Indicateur B", sel, index=1, format_func=lambda c: INDICATEURS_CLES[c][0])
        m = D.serie(x)[["annee", "valeur"]].merge(D.serie(y)[["annee", "valeur"]], on="annee", suffixes=("_a", "_b"))
        fig = px.scatter(m, x="valeur_a", y="valeur_b", color="annee", color_continuous_scale=["#cde2fb", "#0d366b"],
                         hover_data=["annee"], labels={"valeur_a": INDICATEURS_CLES[x][0], "valeur_b": INDICATEURS_CLES[y][0]})
        fig.update_traces(marker=dict(size=10, line=dict(color="white", width=1.5)))
        fig.update_layout(height=420, hovermode="closest")
        st.plotly_chart(fig, use_container_width=True)
        st.markdown("🧠 " + correlation_texte(D.serie(x), D.serie(y), INDICATEURS_CLES[x][0], INDICATEURS_CLES[y][0]))

with tab4:
    cat = wb.groupby(["code", "libelle", "themes"]).agg(debut=("annee", "min"), fin=("annee", "max"),
                                                       points=("valeur", "size")).reset_index()
    q = st.text_input("Filtrer (mot anglais ou français, ex. debt, inflation, remittances)")
    if q:
        cat = cat[cat.libelle.str.contains(q, case=False) | cat.code.str.contains(q, case=False)]
    st.dataframe(cat, hide_index=True, use_container_width=True, height=460)
    st.download_button("⬇️ Toutes les séries (CSV long)", wb.to_csv(index=False).encode("utf-8"), "banque_mondiale_haiti.csv")

st.markdown("### 📰 Chiffres récents (2024-2027)")
st.dataframe(act[act.theme.isin(["Économie", "Finances publiques", "Secteur extérieur"])]
             [["indicateur", "periode", "valeur", "unite", "statut", "source", "url"]],
             hide_index=True, use_container_width=True,
             column_config={"url": st.column_config.LinkColumn("lien")})
pied("Banque mondiale – World Development Indicators (via HDX, puis API), FMI (WEO avril 2026), BRH, DG Trésor.")
