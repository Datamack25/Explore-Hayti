import io
import subprocess
import sys
import zipfile
from datetime import date

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from src import data as D
from src import elections as E
from src import elections_export as X
from src import elections_ml as ML
from src import popularite as POP
from src.charts import choropleth
from src.ui import BLEU_HAITI, ROUGE_HAITI, SERIES, analyse_box, entete, kpis, note, pied, setup
from src.utils import ROOT

setup("Élections 2026-2027", "🗳️")
entete("Élections en Haïti 2026-2027",
       "Candidats, organismes, intégrité, faisabilité des programmes, historique des scrutins et 250 ans de vie politique.")

c = E.candidats()
integ = E.tableau_integrite(c)
cal = E.calendrier()
hist = E.historique()
chefs = E.chefs_etat()
crit = E.criteres()
sanc = E.sanctions()
org = E.organismes()
presse = E.veille()
scr = E.screening()
stats = E.stats_chefs(chefs)
analyses = {r.id: E.analyser_programme(r.texte_programme, crit) for r in c.itertuples()}
c["score_faisabilite"] = c.id.map(lambda i: analyses[i]["total"])
c = c.merge(integ[["id", "total", "niveau"]].rename(columns={"total": "score_risque", "niveau": "niveau_risque"}), on="id")
jours = (E.DATE_PREMIER_TOUR - date.today()).days
URL_COL = st.column_config.LinkColumn

(t_bord, t_cand, t_fiche, t_prog, t_integ, t_pop, t_org, t_hist, t_250, t_ml, t_exp) = st.tabs([
    "🗳️ Tableau de bord", "👥 Candidats", "🪪 Fiche candidat", "📋 Programmes & faisabilité", "⚖️ Intégrité & sanctions", "📈 Popularité",
    "🏛️ Organismes", "📊 Historique des élections", "🕰️ 250 ans", "🤖 Machine learning", "📤 Exports & mise à jour"])

# ======================================================================= 1. TABLEAU DE BORD
with t_bord:
    kpis([
        {"lab": "1er tour", "val": "18 juil.", "sub": f"2027 · J-{jours} · présidentielle et législatives", "style": "accent"},
        {"lab": "2e tour", "val": "4 oct.", "sub": "2027 · + élections locales", "style": "accent"},
        {"lab": "Candidatures", "val": str(len(c)), "sub": "présidence · liste provisoire"},
        {"lab": "Candidats sanctionnés", "val": str(int((c.sanctions_autorites != "").sum())), "sub": "États-Unis, Canada, UE", "style": "alert"},
        {"lab": "Programmes publiés", "val": str(int((c.texte_programme != "").sum())), "sub": f"sur {len(c)} candidats"},
        {"lab": "Sans élection", "val": f"{date.today().year - 2016} ans", "sub": "dernière présidentielle : nov. 2016", "style": "alert"},
    ])
    note(f"<b>Calendrier en vigueur</b> (CEP, {E.DATE_CALENDRIER:%d/%m/%Y}) : campagne du 15 avril au 17 juillet 2027, "
         "<b>1er tour le 18 juillet 2027</b>, 2e tour et collectivités territoriales le <b>4 octobre 2027</b>. C'est le troisième "
         "calendrier depuis novembre 2025 (30 août 2026, puis 13 décembre 2026, abandonnés).")
    d = cal.copy()
    d["fin_aff"] = d.fin + pd.Timedelta(days=4)
    fig = px.timeline(d, x_start="debut", x_end="fin_aff", y="etape", color="statut",
                      color_discrete_map={"Réalisé": SERIES[0], "Abandonné": "#c3c2b7", "Prévu": ROUGE_HAITI,
                                          "À venir (date non publiée)": SERIES[3]},
                      hover_data={"fin_aff": False, "categorie": True, "statut": True})
    fig.add_vline(x=pd.Timestamp(date.today()).timestamp() * 1000, line_dash="dash", line_color="#52514e",
                  annotation_text="aujourd'hui")
    fig.update_yaxes(autorange="reversed", title=None)
    fig.update_layout(height=640, hovermode="closest", title="Chronologie du processus électoral (2021-2027)", xaxis_title=None)
    st.plotly_chart(fig, width="stretch")
    a, b = st.columns([3, 2])
    with a:
        dd = D.departements()
        anc = c[c.departement_ancrage != ""].groupby("departement_ancrage").nom.agg(["count", lambda s: ", ".join(s)])
        anc.columns = ["candidats", "noms"]
        m = dd[["adm1_pcode", "departement"]].merge(anc, left_on="departement", right_index=True, how="left").fillna(
            {"candidats": 0, "noms": "—"})
        st.markdown("##### Ancrage territorial connu des candidats")
        st.plotly_chart(choropleth(m, D.geojson("departements"), "candidats", "Candidats", key="adm1_pcode", nom="departement",
                                   hover=["noms"], height=420), width="stretch")
        st.caption(f"{len(c) - int(m.candidats.sum())} candidats sans ancrage documenté publiquement.")
    with b:
        st.markdown("##### Dernières nouvelles électorales")
        if presse.empty:
            st.info("Cliquez sur « Mettre à jour » (onglet 📤) pour charger la revue de presse électorale.")
        else:
            for p in presse.head(9).itertuples():
                st.markdown(f"<span class='ay-badge'>{p.tonalite}</span> **[{p.titre}]({p.lien})**  \n"
                            f"<small>{str(p.date)[:10]} · {p.source}</small>", unsafe_allow_html=True)
    analyse_box("Points clés", [
        "Le **décret du 6 octobre 2026** a retiré l'exclusion des candidats sanctionnés par des États étrangers ; seules les "
        "sanctions du Conseil de sécurité de l'ONU restent éliminatoires.",
        "Conditions d'inscription : **2 millions de gourdes** de frais, 30 000 membres pour un parti, 150 000 signatures pour un "
        "indépendant, CIN valide, quitus fiscal, déclaration de patrimoine.",
        "Plus de **906 800 nouveaux électeurs** inscrits (sept. 2026) pour ≈ 5,8 millions de détenteurs de la CIN ; plusieurs "
        "communes de l'Ouest (Carrefour, Cité Soleil, Croix-des-Bouquets) n'avaient aucun centre d'inscription ouvert.",
        "≈ **1,5 million de déplacés internes** : leur inscription et le vote de la diaspora restent des enjeux non résolus.",
    ])

# ======================================================================= 2. CANDIDATS
with t_cand:
    f1, f2, f3 = st.columns(3)
    q = f1.text_input("Rechercher (nom, parti, profession)", "")
    fs = f2.selectbox("Sanctions", ["Tous", "Sanctionnés", "Non sanctionnés"])
    fp = f3.multiselect("Exposition politique", list(E.LIB_PPE.values()), placeholder="Tous les profils")
    v = c.copy()
    if q:
        v = v[(v.nom + v.parti + v.profession + v.fonctions_passees).str.contains(q, case=False)]
    if fs != "Tous":
        v = v[(v.sanctions_autorites != "") == (fs == "Sanctionnés")]
    if fp:
        v = v[v.niveau_ppe.map(E.LIB_PPE).isin(fp)]
    st.dataframe(v[["nom", "parti", "sigle", "profession", "fonctions_passees", "departement_ancrage", "residence",
                    "sanctions_autorites", "score_risque", "niveau_risque", "programme_statut", "nb_articles", "source_1"]],
                 hide_index=True, width="stretch", height=520,
                 column_config={"nom": "Candidat", "parti": "Parti / regroupement", "sigle": "Sigle", "profession": "Profession",
                                "fonctions_passees": st.column_config.TextColumn("Fonctions passées", width="large"),
                                "departement_ancrage": "Ancrage", "residence": "Résidence", "sanctions_autorites": "Sanctions",
                                "score_risque": st.column_config.ProgressColumn("Risque /100", min_value=0, max_value=100, format="%d"),
                                "niveau_risque": "Niveau", "programme_statut": "Programme",
                                "nb_articles": st.column_config.NumberColumn("Articles (60 j)", format="%d"),
                                "source_1": URL_COL("Source", display_text="ouvrir")})
    st.download_button("⬇️ Télécharger la liste (CSV)", v.drop(columns=["texte_programme"]).to_csv(index=False).encode("utf-8-sig"),
                       "candidats_presidentielle_haiti.csv", "text/csv", on_click="ignore")
    st.markdown("##### Comparer des candidats")
    choix = st.multiselect("Candidats à comparer", c.nom.tolist(), default=c.sort_values("score_risque", ascending=False).nom.head(4).tolist())
    if choix:
        cc = c[c.nom.isin(choix)]
        dims = {"Exécutif": "exp_executif", "Législatif": "exp_legislatif", "Élu local": "exp_local", "Justice": "exp_judiciaire",
                "Exposition politique": "niveau_ppe", "Risque /100": "score_risque", "Présence médiatique": "nb_articles"}
        mx = {k: max(1, c[v_].max()) for k, v_ in dims.items()}
        fig = go.Figure()
        for i, r in enumerate(cc.itertuples()):
            vals = [getattr(r, v_) / mx[k] for k, v_ in dims.items()]
            fig.add_trace(go.Scatterpolar(r=vals + vals[:1], theta=list(dims) + list(dims)[:1], name=r.nom, fill="toself",
                                          opacity=0.55, line_color=SERIES[i % 8]))
        fig.update_layout(height=470, polar=dict(radialaxis=dict(visible=False, range=[0, 1])), hovermode="closest")
        st.plotly_chart(fig, width="stretch")
        st.caption("Valeurs normalisées (1 = maximum parmi les candidats). L'expérience n'est pas un gage de compétence et le risque "
                   "n'est pas un verdict : ces axes décrivent des profils.")
    note("Liste provisoire établie à partir des publications du CEP relayées par la presse (16 inscrits au 19/10/2026, 18 signalés "
         "au 25/10/2026). Les inscriptions ont été closes le 31 octobre 2026 : le CEP publiera la liste définitive après examen des "
         "dossiers. Toute ligne est modifiable dans 🔐 Administration (<code>elections_candidats.csv</code>).", "warn")

# ======================================================================= 3. FICHE CANDIDAT
with t_fiche:
    nom = st.selectbox("Choisir un candidat", c.sort_values("nom").nom.tolist(),
                       index=sorted(c.nom).index("Michel Joseph Martelly") if "Michel Joseph Martelly" in set(c.nom) else 0)
    r = c[c.nom == nom].iloc[0]
    s = E.score_integrite(r, scr)
    an = analyses[r.id]
    elig = E.eligibilite(r)
    sc = sanc[sanc.candidat_id == r.id]
    pr = presse[presse.candidats.fillna("").str.contains(r.id, regex=False)] if not presse.empty else pd.DataFrame()
    st.markdown(f"<div class='ay-card' style='border-top:5px solid {BLEU_HAITI}'><div class='ay-eyebrow' style='color:#52514e'>"
                f"Candidat à la présidence · {r.statut_inscription}</div><h2 style='margin:.2rem 0'>{r.nom}</h2>"
                f"<p style='font-size:1.1rem;color:{BLEU_HAITI}'>{r.parti}{' (' + r.sigle + ')' if r.sigle else ''}</p></div>",
                unsafe_allow_html=True)
    kpis([
        {"lab": "Risque d'intégrité", "val": f"{s['total']} / 100", "sub": s["niveau"], "style": "alert" if s["total"] >= 40 else "accent"},
        {"lab": "Faisabilité programme", "val": f"{an['total']:.0f} / 100" if an["evaluable"] else "—",
         "sub": E.niveau_faisabilite(an["total"]) if an["evaluable"] else r.programme_statut},
        {"lab": "Âge", "val": f"{int(r.age)} ans" if r.age == r.age else "—", "sub": r.lieu_naissance or "naissance non publiée"},
        {"lab": "Exposition politique", "val": f"Niveau {r.niveau_ppe}", "sub": E.LIB_PPE[int(r.niveau_ppe)]},
        {"lab": "Presse (60 j)", "val": str(int(r.nb_articles)), "sub": f"tonalité moyenne {r.tonalite_moy:+.2f}"},
    ])
    f_id, f_int, f_prog, f_pr = st.tabs(["Identité & parcours", "Intégrité & éligibilité", "Programme", "Presse & sources"])
    with f_id:
        a, b = st.columns(2)
        a.markdown(f"**Profession** : {r.profession}  \n**Fonctions passées** : {r.fonctions_passees}  \n"
                   f"**Nom enregistré au CEP** : {r.nom_cep or '—'}")
        b.markdown(f"**Naissance** : {r.naissance or 'non publiée'} {('· ' + r.lieu_naissance) if r.lieu_naissance else ''}  \n"
                   f"**Ancrage territorial** : {r.departement_ancrage or 'non documenté'}  \n**Résidence** : {r.residence}  \n"
                   f"**Site internet** : {('[' + r.site_web + '](' + r.site_web + ')') if r.site_web else 'non identifié'}")
        exp = {"Exécutif": r.exp_executif, "Législatif": r.exp_legislatif, "Élu local": r.exp_local, "Justice": r.exp_judiciaire}
        st.markdown(" ".join(f"<span class='ay-badge' style='{'' if v_ else 'opacity:.35'}'>{k}</span>" for k, v_ in exp.items()),
                    unsafe_allow_html=True)
        prox = ML.proches(ML.matrice_profils(c, integ), r.id)
        st.caption("Profils les plus proches (machine learning, similarité cosinus) : " +
                   ", ".join(f"{x.nom} ({x.similarite:.2f})" for x in prox.itertuples()))
    with f_int:
        a, b = st.columns([3, 2])
        with a:
            comp = [k for k in s if k not in ("total", "niveau", "autorites")]
            fig = go.Figure(go.Bar(x=[s[k] for k in comp], y=comp, orientation="h", marker_color=E.COULEUR_NIVEAU[s["niveau"]],
                                   text=[s[k] for k in comp], textposition="outside"))
            fig.update_layout(height=260, xaxis=dict(range=[0, 55], title="points"), yaxis=dict(autorange="reversed"),
                              title=f"Score de risque : {s['total']} / 100 ({s['niveau']})", hovermode="closest")
            st.plotly_chart(fig, width="stretch")
            st.markdown(f"**Procédures / allégations** : {E.LIB_ALLEG[int(r.niveau_allegation)]}. {r.allegations}")
            if len(sc):
                st.dataframe(sc[["autorite", "regime", "date", "motif_officiel_resume", "statut", "source"]], hide_index=True,
                             width="stretch", column_config={"source": URL_COL("Source", display_text="ouvrir")})
            hits = scr[scr.candidat_id == r.id] if not scr.empty else pd.DataFrame()
            if len(hits):
                st.warning(f"Filtrage automatique : {len(hits)} correspondance(s) sur les listes officielles à examiner.")
                st.dataframe(hits, hide_index=True, width="stretch")
        with b:
            st.markdown("**Éligibilité (art. 135 + décret 2026)**")
            ic = {"ok": "✅", "?": "🔎", "!": "⚠️"}
            for lab, st_, txt in elig:
                st.markdown(f"{ic[st_]} **{lab}**  \n<small>{txt}</small>", unsafe_allow_html=True)
        note("Le score de risque reprend la logique du filtrage LCB-FT des personnes politiquement exposées (PPE) : il mesure des "
             "<b>signaux publics</b> (sanctions, procédures, exposition, transparence). Une sanction est une mesure administrative "
             "étrangère et une allégation n'est pas une condamnation : la présomption d'innocence s'applique.")
    with f_prog:
        if an["evaluable"]:
            st.metric("Faisabilité", f"{an['total']:.0f} / 100", E.niveau_faisabilite(an["total"]))
            st.dataframe(an["details"], hide_index=True, width="stretch")
            for x in an["remarques"]:
                st.markdown(f"- {x}")
        else:
            st.info(f"**{r.programme_statut}** — le score sera calculé automatiquement dès que le programme sera publié : renseignez "
                    "le site du candidat (Administration › elections_candidats › site_web) puis cliquez sur « Mettre à jour », ou "
                    "collez le texte dans l'onglet 📋.")
        if r.orientations_connues:
            st.markdown(f"**Orientations connues** : {r.orientations_connues}")
    with f_pr:
        if len(pr):
            for p in pr.head(20).itertuples():
                st.markdown(f"- {str(p.date)[:10]} · *{p.source}* — [{p.titre}]({p.lien}) <span class='ay-badge'>{p.tonalite}</span>",
                            unsafe_allow_html=True)
        else:
            st.caption("Aucun article collecté pour ce candidat : lancez la mise à jour (onglet 📤).")
        st.markdown("**Sources de la fiche** : " + " · ".join(f"[{u.split('/')[2]}]({u})" for u in (r.source_1, r.source_2) if u))
    st.markdown("##### 📥 Exporter la fiche")
    e1, e2, e3 = st.columns(3)
    base = r.id + f"_{date.today():%Y%m%d}"
    if e1.button("📄 Préparer le PDF", key="fpdf"):
        st.session_state["fiche_pdf"] = (r.id, X.fiche_pdf(r, s, an, elig, sc, pr))
    if st.session_state.get("fiche_pdf", ("",))[0] == r.id:
        e1.download_button("⬇️ PDF", st.session_state["fiche_pdf"][1], f"fiche_{base}.pdf", "application/pdf", type="primary",
                           on_click="ignore")
    if e2.button("🖼️ Préparer l'image PNG", key="fpng"):
        st.session_state["fiche_png"] = (r.id, X.carte_png(r, s, an))
    if st.session_state.get("fiche_png", ("",))[0] == r.id:
        e2.download_button("⬇️ PNG", st.session_state["fiche_png"][1], f"fiche_{base}.png", "image/png", type="primary", on_click="ignore")
        st.image(st.session_state["fiche_png"][1], width="stretch")
    e3.download_button("🌐 Télécharger la fiche HTML", X.fiche_html(r, s, an, elig, sc, pr).encode("utf-8"), f"fiche_{base}.html",
                       "text/html", on_click="ignore")

# ======================================================================= 4. PROGRAMMES & FAISABILITÉ
with t_prog:
    st.markdown("#### Grille de faisabilité (sur 100) au regard de la situation d'Haïti")
    act = D.indicateurs_actuels()

    def _ind(nom_):
        x = act[act.indicateur == nom_]
        return x.iloc[-1] if len(x) else None

    rp, ipc, dep_ = _ind("Recettes publiques"), _ind("Personnes en phase IPC 3+ (crise ou pire)"), _ind("Personnes déplacées internes")
    kpis([{"lab": "Recettes publiques", "val": f"{rp.valeur:.1f} % du PIB" if rp is not None else "≈ 5 %", "sub": "FMI · capacité de financement"},
          {"lab": "Insécurité alimentaire", "val": f"{ipc.valeur / 1e6:.1f} M" if ipc is not None else "≈ 5,8 M", "sub": "phase IPC 3+"},
          {"lab": "Déplacés internes", "val": f"{dep_.valeur / 1e6:.1f} M" if dep_ is not None else "≈ 1,5 M", "sub": "OIM"},
          {"lab": "Élus nationaux", "val": "0", "sub": "depuis janvier 2023", "style": "alert"}])
    st.dataframe(crit[["critere", "poids", "question", "contrainte_haiti"]], hide_index=True, width="stretch",
                 column_config={"critere": "Critère", "poids": st.column_config.NumberColumn("Points", format="%d"),
                                "question": "Question posée", "contrainte_haiti": "Contrainte haïtienne"})
    tab = c[["nom", "sigle", "programme_statut", "score_faisabilite"]].assign(
        niveau=c.score_faisabilite.map(E.niveau_faisabilite)).sort_values("score_faisabilite", ascending=False)
    st.dataframe(tab, hide_index=True, width="stretch",
                 column_config={"nom": "Candidat", "sigle": "Parti", "programme_statut": "Programme",
                                "score_faisabilite": st.column_config.ProgressColumn("Faisabilité /100", min_value=0, max_value=100,
                                                                                    format="%.0f"), "niveau": "Appréciation"})
    st.markdown("#### 🧪 Analyseur de programme")
    st.caption("Collez un programme (ou un extrait) : l'outil le note sur 100 selon la grille ci-dessus. Méthode transparente : "
               "mots-clés par critère, mesures chiffrées, échéances, sources de financement, promesses irréalistes.")
    a, b = st.columns([2, 1])
    cible = b.selectbox("Rattacher au candidat (facultatif)", ["—"] + c.nom.tolist())
    if b.button("Charger un exemple fictif"):
        st.session_state["txt_prog"] = E.EXEMPLE_PROGRAMME
    texte = a.text_area("Texte du programme", key="txt_prog", height=230)
    if texte:
        res = E.analyser_programme(texte, crit)
        if not res["evaluable"]:
            st.warning(res["remarques"][0])
        else:
            x1, x2 = st.columns([1, 2])
            x1.metric("Score de faisabilité", f"{res['total']:.0f} / 100", E.niveau_faisabilite(res["total"]))
            x1.json(res["indicateurs"])
            det = res["details"]
            fig = go.Figure(go.Scatterpolar(r=list(det.Points / det.Poids) + [det.Points.iloc[0] / det.Poids.iloc[0]],
                                            theta=list(det["Critère"]) + [det["Critère"].iloc[0]], fill="toself",
                                            line_color=BLEU_HAITI))
            fig.update_layout(height=380, polar=dict(radialaxis=dict(range=[0, 1], visible=False)), hovermode="closest")
            x2.plotly_chart(fig, width="stretch")
            st.dataframe(det, hide_index=True, width="stretch")
            for x in res["remarques"]:
                st.markdown(f"- {x}")
            if cible != "—":
                cid = c[c.nom == cible].id.iloc[0]
                ligne = pd.DataFrame([{"candidat_id": cid, "url_programme": "", "date_collecte": f"{date.today()}", "texte": texte}])
                st.download_button("💾 Ligne à importer dans elections_programmes.csv", ligne.to_csv(index=False).encode("utf-8-sig"),
                                   f"programme_{cid}.csv", "text/csv", on_click="ignore")
    st.markdown("#### 🎚️ Évaluation experte")
    st.caption("Notez vous-même un programme critère par critère (0 à 10) ; la note est pondérée sur 100 et peut compléter l'analyse "
               "automatique.")
    cols = st.columns(4)
    notes = {k.critere: cols[i % 4].slider(k.critere, 0, 10, 5, key=f"exp_{i}") for i, k in enumerate(crit.itertuples())}
    tot = sum(crit.set_index("critere").poids[k] * v / 10 for k, v in notes.items())
    st.metric("Note experte", f"{tot:.0f} / 100", E.niveau_faisabilite(tot))

# ======================================================================= 5. INTÉGRITÉ & SANCTIONS
with t_integ:
    kpis([{"lab": "Candidats sanctionnés", "val": str(int((c.sanctions_autorites != "").sum())), "sub": "par au moins un État ou l'UE",
           "style": "alert"},
          {"lab": "Mesures recensées", "val": str(len(sanc)), "sub": "États-Unis, Canada, UE"},
          {"lab": "Mises en cause formelles", "val": str(int((c.niveau_allegation >= 2).sum())), "sub": "instruction, rapport ONU"},
          {"lab": "PPE de premier rang", "val": str(int((c.niveau_ppe == 3).sum())), "sub": "anciens chefs d'État / de gouvernement"}])
    fig = px.bar(integ.sort_values("total"), x=["Sanctions internationales", "Procédures / allégations", "Exposition politique (PPE)",
                                               "Transparence (site, programme)"], y="Candidat", orientation="h",
                 color_discrete_sequence=[SERIES[7], SERIES[1], SERIES[6], "#c3c2b7"])
    fig.update_layout(height=620, title="Décomposition du score de risque d'intégrité (0-100)", xaxis_title="points",
                      yaxis_title=None, hovermode="y unified", legend_title_text="")
    st.plotly_chart(fig, width="stretch")
    st.markdown("##### Registre des sanctions")
    st.dataframe(sanc, hide_index=True, width="stretch", column_config={"source": URL_COL("Source", display_text="ouvrir")})
    st.markdown("##### Filtrage automatique sur les listes officielles")
    if scr.empty:
        st.info("Le filtrage OFAC SDN (États-Unis), Conseil de sécurité de l'ONU et LMES (Canada) s'exécute avec le bouton de mise à "
                "jour complète (onglet 📤). Correspondance approchée des noms, insensible à l'ordre des prénoms.")
    else:
        st.dataframe(scr, hide_index=True, width="stretch",
                     column_config={"score_similarite": st.column_config.ProgressColumn("Similarité", min_value=0, max_value=1)})
        st.caption("Une similarité ≥ 0,92 est intégrée au score ; entre 0,85 et 0,92 : alerte à examiner manuellement (homonymes).")
    analyse_box("Méthode (inspirée du filtrage LCB-FT)", [
        "**Sanctions** (50 pts max) : ONU 40 · États-Unis 25 · Union européenne 20 · Canada 15, cumulables.",
        "**Procédures** (30) : sanction ou allégation publique 10 · mise en cause formelle 20 · condamnation définitive 30.",
        "**Exposition politique** (10) : PPE locale 4 · nationale 7 · chef de l'État ou du gouvernement 10.",
        "**Transparence** (10) : pas de site internet identifié +5 · pas de programme publié +5.",
        "Seuils : < 20 faible · 20-39 modéré · 40-59 élevé · ≥ 60 très élevé. Le score n'est pas un verdict de culpabilité.",
    ])

# ======================================================================= 5 bis. POPULARITÉ
with t_pop:
    st.markdown("#### 📈 Popularité en ligne et probabilité d'être élu")
    note("Indice calculé à partir de <b>ce qui se dit en ligne</b> : presse (60 j), médias mondiaux GDELT (90 j), consultations "
         "Wikipédia (30 j), Reddit, Bluesky et YouTube (si une clé <code>YOUTUBE_API_KEY</code> est fournie). Facebook, X, TikTok "
         "et WhatsApp, très utilisés en Haïti, n'ont pas d'API publique gratuite. La probabilité vient d'une <b>simulation de 10 000 "
         "scrutins à deux tours</b> (élu au 1er tour si > 50 % ou 25 points d'avance).")
    pc1, pc2 = st.columns([1, 2])
    avec_presse = pc2.toggle("Relancer aussi la veille de presse électorale", value=True, key="pop_presse")
    if pc1.button("🔄 Mettre à jour la popularité", type="primary", key="pop_maj"):
        cmd = [sys.executable, str(ROOT / "scripts" / "update_popularite.py")] + (["--avec-presse"] if avec_presse else [])
        with st.status("Collecte des signaux (≈ 3 à 5 min : GDELT limite à une requête toutes les 5 s)…", expanded=True) as stt:
            p_ = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True, timeout=1500)
            st.code(((p_.stdout or "") + (p_.stderr or ""))[-4000:], language="text")
            stt.update(label="Mise à jour terminée" if p_.returncode == 0 else "Terminée avec erreurs",
                       state="complete" if p_.returncode == 0 else "error")
        E.vider_cache()
        D.vider_cache()
        st.rerun()
    sig = POP.charger_signaux()
    if not POP.a_des_donnees(sig):
        st.info("Aucun signal collecté pour l'instant : cliquez sur « 🔄 Mettre à jour la popularité ». Les probabilités "
                "s'afficheront ensuite (et leur évolution à chaque mise à jour).")
    else:
        with st.expander("⚙️ Réglages du modèle (pondérations et incertitude)"):
            cols = st.columns(3)
            poids = {k: cols[i % 3].slider(v[0], 0.0, 1.0, v[1], 0.05, key=f"pw_{k}") for i, (k, v) in enumerate(POP.SIGNAUX.items())}
            q1, q2 = st.columns(2)
            temp = q1.slider("Contraste entre candidats (température)", 0.2, 2.0, 0.6, 0.1,
                             help="Plus la valeur est basse, plus l'écart de popularité se traduit en écart de voix.")
            conc = q2.slider("Certitude du modèle", 5, 200, 40, 5,
                             help="Plus la valeur est basse, plus les résultats simulés sont dispersés (prudence).")
        idx = POP.indice(sig, poids)
        sim = POP.simuler(idx, temp, conc)
        top = sim.iloc[0]
        kpis([{"lab": "En tête de la simulation", "val": top.nom, "sub": f"{top.proba_elu:.0f} % de chances d'être élu", "style": "accent"},
              {"lab": "Victoire dès le 1er tour", "val": f"{sim.proba_victoire_1er_tour.sum():.0f} %", "sub": "tous candidats confondus"},
              {"lab": "Signaux collectés", "val": f"{int(sig[['presse_60j', 'gdelt_90j', 'social_30j']].sum().sum()):,}".replace(",", " "),
               "sub": "articles et publications"},
              {"lab": "Pages Wikipédia vues", "val": f"{int(sig.wiki_30j.sum()):,}".replace(",", " "), "sub": "30 derniers jours"}])
        fig = go.Figure()
        s_ = sim.sort_values("proba_elu")
        fig.add_trace(go.Bar(y=s_.nom, x=s_.proba_elu, orientation="h", name="Probabilité d'être élu (%)", marker_color=BLEU_HAITI,
                             text=s_.proba_elu.map(lambda v: f"{v:.0f} %"), textposition="outside"))
        fig.add_trace(go.Bar(y=s_.nom, x=s_.proba_qualif_2e_tour, orientation="h", name="Probabilité d'aller au 2e tour (%)",
                             marker_color=SERIES[1], opacity=0.55))
        fig.update_layout(height=640, barmode="group", title="Probabilités issues de la popularité en ligne (10 000 simulations)",
                          xaxis=dict(range=[0, 105], title="%"), hovermode="y unified", legend_title_text="")
        st.plotly_chart(fig, width="stretch")
        st.dataframe(sim[["nom", "sigle", "indice_100", "part_1er_tour", "part_bas", "part_haut", "proba_qualif_2e_tour", "proba_elu",
                          "presse_60j", "gdelt_90j", "wiki_30j", "social_30j", "tonalite", "dynamique"]],
                     hide_index=True, width="stretch",
                     column_config={"nom": "Candidat", "sigle": "Parti",
                                    "indice_100": st.column_config.ProgressColumn("Indice /100", min_value=0, max_value=100, format="%d"),
                                    "part_1er_tour": st.column_config.NumberColumn("Part 1er tour (%)", format="%.1f"),
                                    "part_bas": st.column_config.NumberColumn("bas (P10)", format="%.1f"),
                                    "part_haut": st.column_config.NumberColumn("haut (P90)", format="%.1f"),
                                    "proba_qualif_2e_tour": st.column_config.NumberColumn("2e tour (%)", format="%.0f"),
                                    "proba_elu": st.column_config.NumberColumn("Élu (%)", format="%.1f"),
                                    "presse_60j": "Presse", "gdelt_90j": "GDELT", "wiki_30j": "Wikipédia", "social_30j": "Réseaux",
                                    "tonalite": st.column_config.NumberColumn("Tonalité", format="%+.2f"),
                                    "dynamique": st.column_config.NumberColumn("Dynamique ×", format="%.1f")})
        st.markdown("##### 🧠 Pourquoi ce candidat est-il populaire ?")
        choix_p = st.selectbox("Candidat à analyser", sim.nom.tolist(), key="pop_cand")
        rp_ = idx[idx.nom == choix_p].iloc[0]
        ex = POP.expliquer(rp_, idx, presse)
        a, b = st.columns([3, 2])
        with a:
            analyse_box(f"Analyse automatique — {choix_p}", ex["texte"])
        with b:
            cc_ = pd.DataFrame({"Signal": [POP.SIGNAUX[k][0] for k in POP.SIGNAUX],
                                "Contribution": [rp_[f"contrib_{k}"] for k in POP.SIGNAUX]}).sort_values("Contribution")
            fig = go.Figure(go.Bar(x=cc_.Contribution, y=cc_.Signal, orientation="h",
                                   marker_color=[SERIES[2] if v >= 0 else SERIES[7] for v in cc_.Contribution]))
            fig.update_layout(height=320, title="Moteurs de l'indice (écart à la moyenne)", hovermode="closest", yaxis_title=None)
            st.plotly_chart(fig, width="stretch")
        if len(ex["articles"]):
            with st.expander(f"Les {min(15, len(ex['articles']))} articles les plus récents qui le citent"):
                for x in ex["articles"].head(15).itertuples():
                    st.markdown(f"- {str(x.date)[:10]} · *{x.source}* — [{x.titre}]({x.lien}) <span class='ay-badge'>{x.tonalite}</span>",
                                unsafe_allow_html=True)
        if POP.F_HISTO.exists():
            h = pd.read_csv(POP.F_HISTO)
            if h.date.nunique() >= 2:
                fig = px.line(h, x="date", y="proba_elu", color="nom", markers=True, color_discrete_sequence=SERIES,
                              labels={"proba_elu": "Probabilité d'être élu (%)", "date": "", "nom": ""})
                fig.update_layout(height=420, title="Évolution à chaque mise à jour (réglages par défaut)")
                st.plotly_chart(fig, width="stretch")
            else:
                st.caption("La courbe d'évolution apparaîtra après la deuxième mise à jour.")
        st.download_button("⬇️ Télécharger les probabilités (CSV)", sim.drop(columns=[c_ for c_ in sim.columns if c_.startswith(("z_", "contrib_"))])
                           .to_csv(index=False).encode("utf-8-sig"), f"popularite_{date.today():%Y%m%d}.csv", "text/csv", on_click="ignore")
    note("<b>À lire avant d'interpréter.</b> Ce n'est pas un sondage : aucun sondage d'intentions de vote n'est publié à ce jour. "
         "La notoriété en ligne mesure qu'on parle d'un candidat, pas qu'on vote pour lui : une controverse ou des sanctions "
         "augmentent la visibilité. Environ 4 Haïtiens sur 10 utilisent Internet, la diaspora est sur-représentée en ligne et son vote "
         "n'est pas organisé, et les campagnes de terrain (radio, réseaux locaux, partis) échappent à ces mesures. Les "
         "probabilités sont donc un <b>indicateur de visibilité relative</b>, à recouper avec les sondages dès leur parution.", "warn")

# ======================================================================= 6. ORGANISMES
with t_org:
    cats = st.multiselect("Catégories", sorted(org.categorie.unique()), placeholder="Toutes les catégories")
    o = org[org.categorie.isin(cats)] if cats else org
    fig = px.treemap(org.assign(n=1), path=[px.Constant("Processus électoral"), "categorie", "sigle"], values="n",
                     hover_data={"nom": True, "role": True}, color="categorie", color_discrete_sequence=SERIES)
    fig.update_traces(hovertemplate="<b>%{label}</b><br>%{customdata[0]}<br>%{customdata[1]}<extra></extra>")
    fig.update_layout(height=430, margin=dict(l=0, r=0, t=10, b=0))
    st.plotly_chart(fig, width="stretch")
    cols = st.columns(3)
    for i, x in enumerate(o.itertuples()):
        with cols[i % 3]:
            st.markdown(f"<div class='ay-card' style='margin-bottom:.8rem'><span class='ay-badge'>{x.categorie}</span>"
                        f"<h4>{x.sigle}</h4><p><b>{x.nom}</b><br>{x.role}{('<br><i>' + x.responsable_connu + '</i>') if x.responsable_connu else ''}"
                        f"<br><a href='{x.lien}' target='_blank'>site</a></p></div>", unsafe_allow_html=True)

# ======================================================================= 7. HISTORIQUE DES ÉLECTIONS
with t_hist:
    det_res = E.resultats_detail()
    mod = hist[hist.annee >= 1988]
    kpis([{"lab": "Présidentielles au suffrage direct", "val": str(int(hist.type.str.contains("Suffrage universel").sum())),
           "sub": "depuis 1950"},
          {"lab": "Participation record", "val": f"{mod.participation_pct.max():.0f} %", "sub": "2000 (chiffre officiel contesté)"},
          {"lab": "Participation 2016", "val": "≈ 21 %", "sub": "la plus faible de l'ère démocratique", "style": "alert"},
          {"lab": "Scrutins annulés", "val": str(int(hist.type.str.contains("annulée").sum())), "sub": "1987, 2015"}])
    fig = go.Figure()
    fig.add_trace(go.Bar(x=mod.annee, y=mod.score_vainqueur_pct, name="Score du vainqueur / candidat en tête (%)",
                         marker_color=SERIES[1], opacity=0.55, customdata=mod[["vainqueur"]], hovertemplate="%{customdata[0]} : %{y} %"))
    fig.add_trace(go.Scatter(x=mod.annee, y=mod.participation_pct, name="Participation (%)", mode="lines+markers",
                             line=dict(color=BLEU_HAITI, width=3)))
    fig.update_layout(height=400, title="Participation et score du vainqueur (1988-2016)", yaxis=dict(range=[0, 100], title="%"))
    st.plotly_chart(fig, width="stretch")
    an_ = st.selectbox("Résultats détaillés", sorted(det_res.annee.unique(), reverse=True))
    rr = det_res[det_res.annee == an_]
    a, b = st.columns([2, 3])
    fig = px.bar(rr.sort_values("pct"), x="pct", y="candidat", color="tour", orientation="h", text="pct",
                 color_discrete_sequence=SERIES, labels={"pct": "% des voix", "candidat": ""})
    fig.update_layout(height=320, hovermode="closest", legend_title_text="")
    a.plotly_chart(fig, width="stretch")
    b.markdown("**Ce qui leur est arrivé**")
    for x in rr.itertuples():
        b.markdown(f"- **{x.candidat}** ({x.parti}, {x.pct:.1f} %{' · élu' if x.elu else ''}) — {x.destin}")
    st.markdown("##### Tous les scrutins présidentiels (1807-2027)")
    st.dataframe(hist, hide_index=True, width="stretch",
                 column_config={"annee": st.column_config.NumberColumn("Année", format="%d"),
                                "voix_vainqueur": st.column_config.NumberColumn("Voix", format="%d"),
                                "score_vainqueur_pct": st.column_config.NumberColumn("Score %", format="%.1f"),
                                "participation_pct": st.column_config.NumberColumn("Participation %", format="%.0f")})
    st.caption("Les chiffres des scrutins antérieurs à 2006 sont arrondis (colonne « fiabilité ») ; ceux de 1957-1985 sont issus de "
               "régimes autoritaires et ne reflètent pas une compétition libre.")

# ======================================================================= 8. 250 ANS
with t_250:
    st.markdown("#### 250 ans de vie politique (1776-2026)")
    kpis([{"lab": "Chefs d'État depuis 1804", "val": str(stats["nb"]), "sub": "y compris juntes et transitions"},
          {"lab": "Exercice moyen", "val": f"{stats['duree_moy']:.1f} ans", "sub": f"médiane {stats['duree_med']:.1f} an(s)"},
          {"lab": "Mandats achevés", "val": str(stats["fin_mandat"]), "sub": "fin normale de mandat", "style": "accent"},
          {"lab": "Renversés", "val": str(stats["renverses"]), "sub": "coups d'État, insurrections", "style": "alert"},
          {"lab": "Morts violentes", "val": str(stats["violentes"]), "sub": "assassinat, exécution, lynchage", "style": "alert"}])
    d = chefs.assign(fin_aff=chefs.fin_effective, debut_txt=chefs.debut.dt.strftime("%d/%m/%Y"))
    fig = px.timeline(d, x_start="debut", x_end="fin_aff", y="regime", color="fin_categorie", color_discrete_map=X.COUL_FIN,
                      hover_name="nom", hover_data={"titre": True, "debut_txt": True, "mode_accession": True, "destin": True,
                                                    "fin_aff": False, "regime": False, "fin_categorie": False})
    ev = E.evenements_250()
    for x in ev[ev.annee.isin([1804, 1825, 1915, 1934, 1957, 1986, 2010, 2021])].itertuples():
        fig.add_vline(x=pd.Timestamp(f"{x.annee}-01-01").timestamp() * 1000, line_width=0.6, line_dash="dot", line_color="#8a8984")
    fig.update_layout(height=470, title="Chefs d'État par régime et fin de leur exercice (survolez une barre)", hovermode="closest",
                      legend_title_text="Fin de l'exercice", xaxis_title=None, yaxis_title=None)
    fig.update_xaxes(range=["1775-01-01", "2028-01-01"])
    st.plotly_chart(fig, width="stretch")
    a, b = st.columns(2)
    dec = E.instabilite_par_decennie(chefs)
    fig = go.Figure([go.Bar(x=dec.decennie, y=dec.chefs, name="Chefs d'État arrivés au pouvoir", marker_color=SERIES[0]),
                     go.Bar(x=dec.decennie, y=dec.renverses, name="dont renversés ou morts violemment", marker_color=SERIES[1])])
    fig.update_layout(height=360, barmode="overlay", title="Instabilité par décennie")
    a.plotly_chart(fig, width="stretch")
    fc = chefs[chefs.ordre > 0].fin_categorie.value_counts().reset_index()
    fig = px.pie(fc, names="fin_categorie", values="count", hole=0.55, color="fin_categorie", color_discrete_map=X.COUL_FIN)
    fig.update_layout(height=360, title="Comment se terminent les exercices du pouvoir", legend_title_text="")
    b.plotly_chart(fig, width="stretch")
    st.markdown("##### Comment le pays a évolué sous chaque dirigeant (1960-2022)")
    pib = D.serie("NY.GDP.PCAP.KD")
    croiss = E.croissance_par_dirigeant(chefs, pib)
    if not pib.empty:
        fig = go.Figure()
        for i, x in enumerate(chefs[chefs.fin_effective.dt.year >= 1960].itertuples()):
            fig.add_vrect(x0=max(x.debut.year, 1960), x1=min(x.fin_effective.year, 2023), fillcolor=SERIES[i % 2], opacity=0.07,
                          line_width=0, annotation_text=x.nom.split(" (")[0].split()[-1] if (x.duree_ans >= 3) else "",
                          annotation_position="top left", annotation_font_size=10)
        fig.add_trace(go.Scatter(x=pib.annee, y=pib.valeur, mode="lines", line=dict(color=BLEU_HAITI, width=3), name="PIB/hab."))
        esp = D.serie("SP.DYN.LE00.IN")
        if not esp.empty:
            fig.add_trace(go.Scatter(x=esp.annee, y=esp.valeur, mode="lines", line=dict(color=SERIES[1], width=2, dash="dot"),
                                     name="Espérance de vie (ans)", yaxis="y2"))
        fig.update_layout(height=430, title="PIB par habitant réel (USD 2015) et espérance de vie, par présidence",
                          yaxis=dict(title="USD constants 2015"), yaxis2=dict(overlaying="y", side="right", showgrid=False, title="ans"))
        st.plotly_chart(fig, width="stretch")
        if not croiss.empty:
            fig = px.bar(croiss.sort_values("Début"), x="Croissance annuelle moy. PIB/hab. (%)", y="Dirigeant", orientation="h",
                         color="Fin de l'exercice", color_discrete_map=X.COUL_FIN, hover_data=["Début", "Fin"])
            fig.update_layout(height=520, yaxis=dict(autorange="reversed", title=None), hovermode="closest",
                              title="Croissance annuelle moyenne du PIB/hab. pendant chaque exercice")
            st.plotly_chart(fig, width="stretch")
            st.caption("Lecture : corrélation, pas causalité — les chocs (embargo 1991-1994, séisme 2010, insécurité) pèsent autant que "
                       "les politiques. Source : Banque mondiale.")
    st.markdown("##### Grands moments (1776-2026)")
    th = st.multiselect("Catégories ", sorted(ev.categorie.unique()), placeholder="Toutes")
    e_ = ev[ev.categorie.isin(th)] if th else ev
    coul = {"Positive": "#0ca30c", "Négative": "#d03b3b", "Neutre": "#8a8984"}
    fig = go.Figure(go.Scatter(x=e_.annee, y=e_.categorie, mode="markers", marker=dict(size=13, color=e_.portee.map(coul),
                                                                                         line=dict(color="white", width=1.5)),
                               text=e_.evenement, hovertemplate="<b>%{x}</b><br>%{text}<extra></extra>"))
    fig.update_layout(height=300, hovermode="closest", xaxis=dict(range=[1770, 2030]))
    st.plotly_chart(fig, width="stretch")
    with st.expander(f"Liste complète des {len(chefs)} chefs d'État et gouvernants (1801-2026)"):
        st.dataframe(chefs[["nom", "titre", "debut", "fin", "duree_ans", "mode_accession", "fin_categorie", "destin", "regime"]],
                     hide_index=True, width="stretch",
                     column_config={"debut": st.column_config.DateColumn("Début", format="DD/MM/YYYY"),
                                    "duree_ans": st.column_config.NumberColumn("Durée (ans)", format="%.1f")})

# ======================================================================= 9. MACHINE LEARNING
with t_ml:
    st.markdown("#### 1. Typologie des candidats (K-means + ACP)")
    mat = ML.matrice_profils(c, integ)
    k = st.slider("Nombre de profils", 2, 6, 4)
    prof, noms_g, var = ML.profils(mat, k)
    fig = px.scatter(prof, x="x", y="y", color="profil", text="nom", size=prof.risque + 8, color_discrete_sequence=SERIES,
                     hover_data={"x": False, "y": False, "risque": True, "sigle": True})
    fig.update_traces(textposition="top center", textfont_size=10)
    fig.update_layout(height=520, hovermode="closest", xaxis_title="Axe 1 (ACP)", yaxis_title="Axe 2 (ACP)", legend_title_text="")
    st.plotly_chart(fig, width="stretch")
    st.caption(f"Variables : {', '.join(ML.LIB_VARS.values())}. Les deux axes résument {100 * var:.0f} % de l'information. "
               "Taille des points : score de risque.")
    st.markdown("#### 2. Qu'est-ce qui précède une chute du pouvoir ? (forêt aléatoire, 1804-2026)")
    fi = ML.facteurs_instabilite(chefs)
    a, b = st.columns(2)
    fig = px.bar(fi["importances"].sort_values("Importance"), x="Importance", y="Facteur", orientation="h",
                 color_discrete_sequence=[SERIES[0]])
    fig.update_layout(height=380, hovermode="closest", yaxis_title=None)
    a.plotly_chart(fig, width="stretch")
    b.dataframe(fi["taux"], hide_index=True, width="stretch",
                column_config={"Taux de fin violente ou renversement": st.column_config.ProgressColumn(min_value=0, max_value=1, format="percent")})
    b.caption(f"Précision équilibrée en validation croisée : {100 * fi['precision']:.0f} % (± {100 * fi['ecart']:.0f}) sur "
              f"{fi['n']} exercices, contre {100 * fi['base']:.0f} % pour une prédiction naïve. Petit échantillon : à lire comme une "
              "tendance historique.")
    st.markdown("#### 3. Durée au pouvoir par siècle (Kaplan-Meier)")
    km = ML.kaplan_meier(chefs, "siecle")
    fig = px.line(km, x="annees", y="survie", color="groupe", line_shape="hv", color_discrete_sequence=SERIES,
                  labels={"annees": "Années au pouvoir", "survie": "Probabilité d'être encore au pouvoir", "groupe": ""})
    fig.update_layout(height=380, hovermode="x unified", yaxis_tickformat=".0%")
    st.plotly_chart(fig, width="stretch")
    st.markdown("#### 4. Tendance de la participation (régression + bootstrap)")
    tend = ML.tendance_participation(hist)
    fig = go.Figure([go.Scatter(x=tend["x"], y=tend["y"], mode="markers+text", text=[str(int(v)) for v in tend["x"]],
                                textposition="top center", marker=dict(size=11, color=BLEU_HAITI), name="Observé"),
                     go.Scatter(x=[1990, 2027], y=[tend["a"] * 1990 + tend["b"], tend["prevision"]], mode="lines",
                                line=dict(dash="dash", color="#8a8984"), name="Tendance"),
                     go.Scatter(x=[2027], y=[tend["prevision"]], mode="markers", marker=dict(size=14, color=ROUGE_HAITI, symbol="diamond"),
                                error_y=dict(type="data", symmetric=False, array=[tend["haut"] - tend["prevision"]],
                                             arrayminus=[tend["prevision"] - tend["bas"]]), name="2027 (tendanciel)")])
    fig.update_layout(height=380, yaxis=dict(range=[0, 100], title="Participation (%)"), hovermode="closest")
    st.plotly_chart(fig, width="stretch")
    st.caption(f"Prolongement de la tendance 1990-2016 : ≈ {tend['prevision']:.0f} % en 2027 (intervalle bootstrap 80 % : "
               f"{tend['bas']:.0f}-{tend['haut']:.0f} %). Un modèle de tendance ne peut pas anticiper l'effet de la sécurité ou d'une "
               "forte mobilisation.")
    sim = ML.similarite_programmes(c)
    st.markdown("#### 5. Proximité des programmes (TF-IDF)")
    if sim.empty:
        st.info("Disponible dès que deux programmes au moins seront publiés (collecte automatique par le bouton de mise à jour).")
    else:
        st.plotly_chart(px.imshow(sim, color_continuous_scale="Blues", text_auto=True), width="stretch")
    ml_txt = [f"Typologie : {k} profils de candidats — " + "; ".join(sorted(set(noms_g.values()))) + ".",
              f"Facteurs d'instabilité : le facteur le plus discriminant est « {fi['importances'].Facteur.iloc[0]} » "
              f"(précision équilibrée {100 * fi['precision']:.0f} %).",
              f"Participation : la tendance 1990-2016 prolongée donne ≈ {tend['prevision']:.0f} % en 2027 "
              f"({tend['bas']:.0f}-{tend['haut']:.0f} %)."]
    st.session_state["ml_txt"] = ml_txt

# ======================================================================= 10. EXPORTS & MISE À JOUR
with t_exp:
    st.markdown("#### 🔄 Mettre à jour les données électorales")
    note("Le bouton collecte la <b>presse électorale</b> (Google Actualités FR/EN/créole + médias haïtiens, une recherche par "
         "candidat), compte les <b>mentions</b> et leur tonalité, <b>filtre les candidats sur les listes de sanctions officielles</b> "
         "(OFAC, ONU, Canada), récupère les <b>programmes</b> publiés sur les sites des candidats et signale tout article évoquant "
         "un nouveau calendrier du CEP. L'action GitHub le relance automatiquement toutes les 6 heures.")
    a, b = st.columns([1, 2])
    complet = b.toggle("Inclure le filtrage des listes de sanctions (≈ 1 à 3 min)", value=True)
    if a.button("🔄 Mettre à jour maintenant", type="primary"):
        cmd = [sys.executable, str(ROOT / "scripts" / "update_elections.py")] + ([] if complet else ["--sans-sanctions"])
        with st.status("Mise à jour électorale en cours…", expanded=True) as status:
            p = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True, timeout=900)
            st.code((p.stdout or "") + (p.stderr or "")[-3000:], language="text")
            status.update(label="Mise à jour terminée" if p.returncode == 0 else "Terminée avec erreurs",
                          state="complete" if p.returncode == 0 else "error")
        E.vider_cache()
        D.vider_cache()
        st.rerun()
    j = D.journal()
    if not j.empty:
        st.dataframe(j[j.source.str.startswith("Élections")].iloc[::-1].head(12), hide_index=True, width="stretch")
    st.divider()
    st.markdown("#### 📤 Rapport complet")
    st.caption("PDF professionnel (couverture, synthèse, calendrier, candidats, intégrité, faisabilité, historique, 250 ans, machine "
               "learning, organismes), version HTML autonome et tous les graphiques en PNG.")
    if st.button("📄 Générer le rapport (PDF + HTML + images)", type="primary"):
        with st.spinner("Création du rapport…"):
            tend_ = ML.tendance_participation(hist)
            dec_ = E.instabilite_par_decennie(chefs)
            croiss_ = E.croissance_par_dirigeant(chefs, D.serie("NY.GDP.PCAP.KD"))
            det_ = c[["nom", "sigle", "programme_statut", "score_faisabilite"]].assign(
                score_faisabilite=c.score_faisabilite.map(lambda x: "—" if x != x else f"{x:.0f}")).rename(columns={
                    "nom": "Candidat", "sigle": "Parti", "programme_statut": "Programme", "score_faisabilite": "Score /100"})
            ml_txt = st.session_state.get("ml_txt", [])
            pdf, imgs = X.rapport_pdf(c, integ, cal, hist, det_, chefs, stats, dec_, croiss_, tend_, org, ml_txt)
            htm = X.rapport_html(c.drop(columns=["texte_programme"]), integ, cal, hist, det_, chefs, stats, imgs, org, ml_txt)
        st.session_state["rap_elec"] = (pdf, htm, imgs)
    if "rap_elec" in st.session_state:
        pdf, htm, imgs = st.session_state["rap_elec"]
        nomf = f"elections_haiti_{date.today():%Y%m%d}"
        st.success(f"Rapport prêt : PDF {len(pdf) // 1024} Ko · {len(imgs)} graphiques.")
        x1, x2, x3 = st.columns(3)
        x1.download_button("⬇️ PDF", pdf, f"{nomf}.pdf", "application/pdf", type="primary", on_click="ignore")
        x2.download_button("🌐 HTML", htm.encode("utf-8"), f"{nomf}.html", "text/html", on_click="ignore")
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
            for k_, v_ in imgs.items():
                z.writestr(k_, v_)
        x3.download_button("🖼️ Graphiques (ZIP de PNG)", buf.getvalue(), f"{nomf}_graphiques.zip", "application/zip", on_click="ignore")
        cols = st.columns(3)
        for i, (k_, v_) in enumerate(imgs.items()):
            with cols[i % 3]:
                st.image(v_, width="stretch")
                st.download_button(f"PNG · {k_}", v_, k_, "image/png", key=f"pe_{k_}", on_click="ignore")
    st.divider()
    st.markdown("#### 🗂️ Jeux de données (CSV)")
    from src.utils import CURATED, LIVE
    fichiers = sorted(CURATED.glob("elections_*.csv")) + sorted(LIVE.glob("elections_*.csv"))
    cols = st.columns(3)
    for i, p in enumerate(fichiers):
        cols[i % 3].download_button(f"⬇️ {p.name}", p.read_bytes(), p.name, "text/csv", key=f"csv_{p.name}", on_click="ignore")
    st.caption("Les fichiers « curated » se modifient dans 🔐 Administration (enregistrement GitHub possible) ; les fichiers « live » "
               "sont produits par la mise à jour.")

pied("CEP (cephaiti.ht), Haiti Policy House (Election Tracker), Le Nouvelliste, Juno7, Haitian Times, HaitiLibre, Listín Diario, "
     "Acento, Infobae/EFE, Wikipédia, IFES ElectionGuide, Banque mondiale, OFAC, ONU, Affaires mondiales Canada. "
     "Données au 4 novembre 2026, à mettre à jour avec le bouton 🔄.")
