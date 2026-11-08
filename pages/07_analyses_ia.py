import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from src import assistant
from src import data as D
from src.analyse import analyser_departements, analyser_serie
from src.charts import MAP_STYLE, barres_h, choropleth
from src.indicateurs import INDICATEURS_CLES
from src.ml import (VARIABLES_COMMUNES, annees_de_rupture, choisir_k, indice_vulnerabilite, prevoir, typologie)
from src.ui import SEQ_ORANGE, SERIES, analyse_box, entete, note, pied, setup

setup("Analyses & machine learning", "🤖")
entete("Analyses & machine learning",
       "Des modèles simples et explicables pour faire parler les données : typologie des communes, vulnérabilité, prévisions, ruptures.")

com = D.communes()
t1, t2, t3, t4, t5 = st.tabs(["🧩 Typologie des communes", "⚠️ Indice de vulnérabilité", "🔮 Prévisions",
                              "💥 Années de rupture", "💬 Assistant d'analyse"])

# ------------------------------------------------------------------ 1. Typologie
with t1:
    st.markdown("Le **K-means** regroupe les communes qui se ressemblent le plus sur les variables choisies "
                "(standardisées, log pour les variables très asymétriques). L'**ACP** les projette sur un plan pour les visualiser.")
    a, b = st.columns([2, 1])
    vars_ = a.multiselect("Variables", list(VARIABLES_COMMUNES), default=list(VARIABLES_COMMUNES)[:4],
                          format_func=VARIABLES_COMMUNES.get)
    k = b.slider("Nombre de groupes", 2, 7, 4)
    if len(vars_) >= 2:
        with st.expander("Comment choisir le nombre de groupes ? (score de silhouette)"):
            sk = choisir_k(com, vars_)
            fig = px.line(sk, x="k", y="silhouette", markers=True, labels={"k": "nombre de groupes", "silhouette": "silhouette"})
            fig.update_traces(line_width=2, marker_size=9)
            fig.update_layout(height=260)
            st.plotly_chart(fig, use_container_width=True)
            st.caption("Plus la silhouette est élevée, plus les groupes sont nets.")
        res, info = typologie(com, vars_, k)
        groupes = sorted(res.groupe.unique())
        cmap = {g: SERIES[i] for i, g in enumerate(groupes)}
        c1, c2 = st.columns([3, 2])
        with c1:
            fig = px.choropleth_map(res, geojson=D.geojson("communes"), locations="adm2_pcode", featureidkey="id",
                                    color="groupe", color_discrete_map=cmap, hover_name="commune",
                                    hover_data={"adm2_pcode": False, "departement": True, "population": True},
                                    map_style=MAP_STYLE, zoom=6.4, center={"lat": 18.95, "lon": -72.8}, opacity=0.85)
            fig.update_traces(marker_line_color="white", marker_line_width=0.6)
            fig.update_layout(height=520, margin=dict(l=0, r=0, t=0, b=0), legend=dict(title="", y=0.02, x=0.01,
                              bgcolor="rgba(255,255,255,.85)"))
            st.plotly_chart(fig, use_container_width=True)
        with c2:
            fig = px.scatter(res, x="acp1", y="acp2", color="groupe", color_discrete_map=cmap, hover_name="commune",
                             labels={"acp1": f"Axe 1 ({100 * info['variance_acp'][0]:.0f} %)",
                                     "acp2": f"Axe 2 ({100 * info['variance_acp'][1]:.0f} %)", "groupe": ""})
            fig.update_traces(marker=dict(size=9, line=dict(color="white", width=1.5)))
            fig.update_layout(height=520, hovermode="closest", legend=dict(y=-0.25))
            st.plotly_chart(fig, use_container_width=True)
        st.markdown(f"**Profil médian de chaque groupe** — silhouette = {info['silhouette']:.2f}")
        prof = info["profils"].rename(columns=VARIABLES_COMMUNES)
        prof.insert(0, "communes", info["taille"])
        st.dataframe(prof, use_container_width=True)
        st.download_button("⬇️ Communes et groupes (CSV)", res[["adm2_pcode", "commune", "departement", "groupe"] + vars_]
                           .to_csv(index=False).encode("utf-8"), "typologie_communes.csv")

# ------------------------------------------------------------------ 2. Vulnérabilité
with t2:
    st.markdown("Un **indice composite (0-100)** qui classe les communes selon le cumul de facteurs de fragilité relative. "
                "Vous réglez vous-même le poids de chaque facteur : l'indice est transparent et reproductible.")
    note("Les données communales disponibles sont démographiques et territoriales : l'indice mesure une <b>pression "
         "démographique et un isolement relatifs</b>, pas la pauvreté. Ajoutez d'autres CSV par commune (santé, revenus, "
         "accès à l'eau…) dans data/processed pour l'enrichir.", "warn")
    c = st.columns(4)
    w1 = c[0].slider("Part d'enfants (plus = plus vulnérable)", 0.0, 3.0, 2.0, 0.5)
    w2 = c[1].slider("Faible densité / isolement", 0.0, 3.0, 1.0, 0.5)
    w3 = c[2].slider("Peu de localités urbaines", 0.0, 3.0, 1.5, 0.5)
    w4 = c[3].slider("Population totale (charge)", 0.0, 3.0, 0.5, 0.5)
    poids = {"part_enfants_pct": w1, "densite_hab_km2": -w2, "part_urbaine_localites_pct": -w3, "population": w4}
    poids = {k: v for k, v in poids.items() if v != 0}
    if poids:
        vi = indice_vulnerabilite(com, poids)
        a, b = st.columns([3, 2])
        with a:
            st.plotly_chart(choropleth(vi, D.geojson("communes"), "indice_vulnerabilite", "Indice (0-100)",
                                       hover=["departement", "rang_vulnerabilite"], scale=SEQ_ORANGE),
                            use_container_width=True)
        with b:
            top = vi.nsmallest(15, "rang_vulnerabilite")
            st.plotly_chart(barres_h(top, "indice_vulnerabilite", "commune", "15 communes au score le plus élevé", "",
                                     color=SERIES[1]), use_container_width=True)
        dv = vi.groupby("departement").indice_vulnerabilite.mean().round(1).sort_values(ascending=False)
        analyse_box("Lecture", [f"Département au score moyen le plus élevé : **{dv.index[0]}** ({dv.iloc[0]}).",
                                f"Le plus faible : **{dv.index[-1]}** ({dv.iloc[-1]}).",
                                f"Commune n°1 : **{top.iloc[0].commune}** ({top.iloc[0].departement}).",
                                "Croisez avec la carte IPC (page Humanitaire) pour prioriser une intervention."])
        st.download_button("⬇️ Indice par commune (CSV)", vi[["adm2_pcode", "commune", "departement", "indice_vulnerabilite",
                                                             "rang_vulnerabilite"]].to_csv(index=False).encode("utf-8"),
                           "indice_vulnerabilite.csv")

# ------------------------------------------------------------------ 3. Prévisions
with t3:
    st.markdown("Prévision par **lissage exponentiel de Holt à tendance amortie** ; paramètres choisis automatiquement "
                "en minimisant l'erreur de prévision à un an. La zone colorée est un intervalle de 80 % obtenu par bootstrap des erreurs passées.")
    wb = D.wb()
    dispo = [c for c in INDICATEURS_CLES if c in set(wb.code) and len(D.serie(c)) >= 15]
    a, b, c3 = st.columns([3, 1, 1])
    code = a.selectbox("Indicateur", dispo, index=dispo.index("SP.POP.TOTL") if "SP.POP.TOTL" in dispo else 0,
                       format_func=lambda c: INDICATEURS_CLES[c][0])
    h = b.slider("Horizon (années)", 3, 15, 8)
    debut = c3.number_input("Apprendre depuis", 1960, 2015, 1990, 5)
    s = D.serie(code)
    s = s[s.annee >= debut]
    fc, par = prevoir(s, h)
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=list(fc.annee) + list(fc.annee[::-1]), y=list(fc.haut) + list(fc.bas[::-1]), fill="toself",
                             fillcolor="rgba(42,120,214,0.15)", line=dict(width=0), name="Intervalle 80 %", hoverinfo="skip"))
    fig.add_trace(go.Scatter(x=s.annee, y=s.valeur, mode="lines", name="Observé", line=dict(color="#0b0b0b", width=2)))
    fig.add_trace(go.Scatter(x=fc.annee, y=fc.prevision, mode="lines+markers", name="Prévision",
                             line=dict(color=SERIES[0], width=2, dash="dash"), marker=dict(size=8)))
    act = D.indicateurs_actuels()
    lien = {"NY.GDP.MKTP.KD.ZG": "Croissance du PIB réel", "FP.CPI.TOTL.ZG": "Inflation (prix à la consommation)"}
    if code in lien:
        r = act[act.indicateur == lien[code]].copy()
        r["annee"] = pd.to_numeric(r.periode, errors="coerce")
        r = r.dropna(subset=["annee"])
        fig.add_trace(go.Scatter(x=r.annee, y=r.valeur, mode="markers", name="FMI (récent)",
                                 marker=dict(size=11, color=SERIES[1], symbol="diamond", line=dict(color="white", width=2))))
    fig.update_layout(title=INDICATEURS_CLES[code][0], height=460, yaxis_title=INDICATEURS_CLES[code][2])
    st.plotly_chart(fig, use_container_width=True)
    st.caption(f"Paramètres : α = {par['alpha']}, β = {par['beta']}, φ = {par['phi']} · erreur moyenne (RMSE) "
               f"sur 10 ans : {par['rmse_10_dernieres_annees']:,.2f}. Une prévision statistique prolonge les tendances passées : "
               "elle ne peut pas anticiper un choc politique, sécuritaire ou climatique.")
    st.dataframe(fc.round(2), hide_index=True, use_container_width=True)

# ------------------------------------------------------------------ 4. Ruptures
with t4:
    st.markdown("Une **Isolation Forest** examine simultanément les variations annuelles de plusieurs indicateurs et repère les "
                "années qui sortent de l'ordinaire — sans qu'on lui indique les crises connues.")
    wb = D.wb()
    defaut = ["NY.GDP.MKTP.KD.ZG", "FP.CPI.TOTL.ZG", "NY.GDP.PCAP.KD", "NE.IMP.GNFS.ZS", "NE.EXP.GNFS.ZS",
              "DT.ODA.ODAT.CD", "PA.NUS.FCRF", "BX.TRF.PWKR.CD.DT"]
    dispo = [c for c in INDICATEURS_CLES if c in set(wb.code) and len(D.serie(c)) >= 20]
    sel = st.multiselect("Indicateurs analysés", dispo, default=[c for c in defaut if c in dispo],
                         format_func=lambda c: INDICATEURS_CLES[c][0])
    cont = st.slider("Part d'années considérées atypiques", 0.05, 0.25, 0.12, 0.01)
    if len(sel) >= 3:
        wide = wb[wb.code.isin(sel) & (wb.annee >= 1971)].pivot_table(index="annee", columns="code", values="valeur")
        rup = annees_de_rupture(wide, cont)
        rup["indicateur_principal"] = rup.indicateur_principal.map(lambda c: INDICATEURS_CLES.get(c, (c,))[0])
        fig = go.Figure(go.Bar(x=rup.sort_values("annee").annee, y=rup.sort_values("annee").score_anomalie,
                               marker=dict(color=[SERIES[7] if x else "#b7d3f6" for x in rup.sort_values("annee").atypique],
                                           cornerradius=3),
                               hovertemplate="%{x} : score %{y:.2f}<extra></extra>"))
        fig.update_layout(title="Score d'anomalie par année (rouge = année atypique)", height=360, hovermode="closest")
        st.plotly_chart(fig, use_container_width=True)
        top = rup[rup.atypique].sort_values("annee")
        st.dataframe(top[["annee", "score_anomalie", "indicateur_principal", "variation_principale_pct"]].round(2),
                     hide_index=True, use_container_width=True)
        connus = {1986, 1991, 1992, 1993, 1994, 2004, 2008, 2010, 2016, 2019, 2020, 2021}
        trouves = sorted(set(top.annee.astype(int)) & connus)
        if trouves:
            analyse_box("Lecture", [f"Années détectées qui correspondent à des crises connues : {', '.join(map(str, trouves))}.",
                                    "Les autres années signalées méritent une recherche historique (chocs de prix, aide, change…)."])

# ------------------------------------------------------------------ 5. Assistant
with t5:
    st.markdown("Générez un **rapport d'analyse** à partir des données de la plateforme. Il est produit par des règles "
                "statistiques (toujours disponible) et peut être reformulé par un modèle de langage si vous en configurez un.")
    sujet = st.selectbox("Sujet du rapport", ["Panorama démographique", "Économie : indicateurs clés", "Un indicateur au choix"])
    if sujet == "Panorama démographique":
        pts = analyser_departements(D.departements())
    elif sujet == "Économie : indicateurs clés":
        pts = []
        for c in ["NY.GDP.PCAP.KD", "FP.CPI.TOTL.ZG", "BX.TRF.PWKR.DT.GD.ZS", "PA.NUS.FCRF"]:
            s = D.serie(c)
            if len(s):
                pts.append(f"**{INDICATEURS_CLES[c][0]}** — " + analyser_serie(s, INDICATEURS_CLES[c][0], INDICATEURS_CLES[c][2])[0])
        a = D.indicateurs_actuels()
        for _, r in a[a.theme == "Économie"].iterrows():
            pts.append(f"{r.indicateur} {r.periode} : {r.valeur} {r.unite} ({r.statut}, {r.source}).")
    else:
        wb = D.wb()
        dispo = [c for c in INDICATEURS_CLES if c in set(wb.code)]
        c = st.selectbox("Indicateur", dispo, format_func=lambda x: INDICATEURS_CLES[x][0], key="rap_ind")
        pts = analyser_serie(D.serie(c), INDICATEURS_CLES[c][0], INDICATEURS_CLES[c][2])
    analyse_box(sujet, pts)
    texte = f"# {sujet}\n\n" + "\n".join(f"- {p}" for p in pts).replace("**", "") + "\n\nSource : Ayiti Data Hub\n"
    st.download_button("⬇️ Télécharger le rapport (Markdown)", texte.encode("utf-8"), "rapport_ayiti.md")

    mode = assistant.disponible()
    st.divider()
    if mode:
        q = st.text_area("Posez une question sur ces données", "Quels sont les enseignements principaux et les limites de ces chiffres ?")
        if st.button("Demander à l'assistant"):
            with st.spinner("Analyse en cours…"):
                st.markdown(assistant.demander(q, texte))
    else:
        note("Assistant conversationnel non configuré. Pour l'activer, ajoutez <code>ANTHROPIC_API_KEY</code> ou "
             "<code>OLLAMA_URL</code> (modèle local, gratuit) dans les secrets Streamlit — voir le README.")

pied("Calculs réalisés dans la plateforme avec scikit-learn à partir des données CNIGS, HDX, Banque mondiale, FMI.")
