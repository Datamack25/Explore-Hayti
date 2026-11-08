import html as H

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from src import admin, assistant
from src import comite as CO
from src.exports_doc import panneau_exports
from src.ui import SERIES, analyse_box, entete, kpis, note, pied, setup
from src.utils import CURATED

setup("Comité des sages", "🧓")
entete("Le Comité des sages",
       "Dix personnages fictifs, aux noms modifiables, qui analysent les plans et les actualités, chacun avec sa grille, "
       "puis une synthèse ferme du leader.")

if "sages" not in st.session_state:
    st.session_state.sages = CO.sages()
S = st.session_state.sages
C = CO.criteres()
LLM = assistant.disponible()
kpis([
    {"lab": "Membres", "val": str(len(S)), "sub": "9 experts + 1 leader", "style": "accent"},
    {"lab": "Critères d'analyse", "val": str(len(C)), "sub": "modifiables (comite_criteres.csv)"},
    {"lab": "Méthode", "val": "Delphi", "sub": "avis indépendants puis synthèse"},
    {"lab": "Rédaction libre", "val": "Activée" if LLM else "Désactivée", "sub": "modèle de langage (optionnel)",
     "style": "" if LLM else "alert"},
])
note("Les membres sont des <b>personnages fictifs</b> : toute ressemblance avec une personne réelle serait fortuite. Le comité "
     "est un outil d'aide à la réflexion : il vérifie qu'un texte répond à des critères, il ne remplace ni l'expertise réelle "
     "ni le débat public, et il ne donne aucune consigne de vote.")

t_mem, t_plan, t_act, t_meth, t_exp = st.tabs(["👥 Les 10 sages", "📑 Analyser un plan", "📰 Analyser l'actualité",
                                                "📚 Méthode & meilleures pratiques", "📥 Exports"])

# ------------------------------------------------------------------ membres
with t_mem:
    cols = st.columns(2)
    for i, s in enumerate(S.itertuples()):
        bord = "#D21034" if s.id == CO.LEADER else SERIES[i % 6]
        cols[i % 2].markdown(
            f"<div class='ay-card' style='margin-bottom:.8rem;border-top:4px solid {bord}'><h4>{H.escape(s.nom)}</h4>"
            f"<p><span class='ay-badge'>{H.escape(s.titre)}</span><span class='ay-badge'>{H.escape(s.domaine)}</span></p>"
            f"<p style='margin-top:.4rem'>{H.escape(s.mission)}</p>"
            f"<p style='margin-top:.4rem;font-size:.85rem'><b>S'inspire de :</b> {H.escape(s.meilleures_pratiques)}</p></div>",
            unsafe_allow_html=True)
    st.markdown("#### ✏️ Modifier les noms et les rôles")
    ed = st.data_editor(S[["id", "nom", "titre", "domaine", "mission", "meilleures_pratiques", "poids"]], hide_index=True,
                        use_container_width=True, disabled=["id"], key="ed_sages")
    a, b = st.columns(2)
    if a.button("Appliquer pour cette session"):
        for c in ["nom", "titre", "domaine", "mission", "meilleures_pratiques", "poids"]:
            S[c] = ed[c].values
        st.session_state.sages = S
        st.rerun()
    if b.button("💾 Enregistrer définitivement (administrateur)", disabled=not admin.connecte()):
        for c in ["nom", "titre", "domaine", "mission", "meilleures_pratiques", "poids"]:
            S[c] = ed[c].values
        st.success("comite_sages.csv " + admin.enregistrer(CURATED / "comite_sages.csv", S.to_csv(index=False).encode("utf-8"),
                                                          "Comité des sages : mise à jour des membres") + ".")
    if not admin.connecte():
        st.caption("Pour enregistrer pour tout le monde, connectez-vous dans Administration. Les mots-clés de chaque sage et les "
                   "critères se modifient aussi dans Administration (comite_sages, comite_criteres).")

# ------------------------------------------------------------------ analyse d'un plan
with t_plan:
    plans = CO.textes_plans()
    choix = st.selectbox("Plan à analyser", list(plans) + ["Texte libre (coller un plan, un programme, un article…)"])
    if choix.startswith("Texte libre"):
        texte = st.text_area("Texte à analyser", height=220)
        fichier = st.file_uploader("…ou un fichier .txt / .md", type=["txt", "md"])
        if fichier:
            texte = fichier.getvalue().decode("utf-8", "ignore")
    else:
        texte = plans[choix]
        with st.expander("Voir le texte analysé"):
            st.text(texte[:6000] + ("…" if len(texte) > 6000 else ""))
    front = st.checkbox("Ajouter les critères propres à la frontière (accord avec la RD, contrôle sanitaire, petit commerce, migrants)",
                        value=choix.startswith("Frontière"))
    if texte and texte.strip():
        r = CO.analyser(texte, S, C, frontiere=front)
        s = r["synthese"]
        coul = {"ADOPTER": "#0ca30c", "ADOPTER SOUS CONDITIONS": "#eda100", "REVOIR LE PLAN": "#d03b3b"}[s["decision"]]
        st.markdown(f"<div class='ay-card' style='border-top:6px solid {coul}'><h4>🧭 Synthèse du leader — {s['decision']} "
                    f"({s['note']}/10)</h4><p>{H.escape(s['texte'])}</p></div>", unsafe_allow_html=True)
        note("La note mesure si le <b>texte disponible</b> traite les critères de chaque sage. Un programme résumé en quelques lignes "
             "obtient mécaniquement une note basse : comparez des textes de longueur et de détail semblables."
             + (" La grille a été écrite en même temps que le plan frontière : sa note est favorable par construction."
                if choix.startswith("Frontière") else ""), "warn")
        av = pd.DataFrame(r["avis"])
        fig = go.Figure(go.Bar(x=av.score, y=av.titre, orientation="h", text=av.score, marker_color=[
            {"Favorable": "#0ca30c", "Favorable sous conditions": "#eda100", "Réservé": "#d03b3b"}[v] for v in av.verdict]))
        fig.update_layout(height=420, xaxis_range=[0, 10], xaxis_title="note /10", yaxis=dict(autorange="reversed"), hovermode=False)
        st.plotly_chart(fig, use_container_width=True)
        if s["priorites"]:
            st.markdown("#### Recommandations prioritaires")
            st.dataframe(pd.DataFrame(s["priorites"], columns=["sage", "rôle", "critère manquant", "recommandation", "importance"]),
                         hide_index=True, use_container_width=True)
        if s["minoritaires"]:
            st.markdown("#### Avis minoritaires (écart d'au moins 3 points avec la moyenne)")
            for a in s["minoritaires"]:
                st.markdown(f"- **{a['nom']}** ({a['titre']}) : {a['score']}/10 — {a['verdict']}")
        st.markdown("#### Avis de chaque sage")
        for a in r["avis"]:
            with st.expander(f"{a['nom']} — {a['titre']} : {a['score']}/10 ({a['verdict']})"):
                st.markdown("**Ce qui est traité :** " + (", ".join(a["forces"]) or "—"))
                for crit, rec, imp in a["recommandations"]:
                    st.markdown(f"- {'🔴' if imp == 3 else '🟠' if imp == 2 else '🟡'} **{crit}** — {rec}")
                st.caption(f"Pertinence du texte pour ce domaine : {a['pertinence']:.0f} % · s'inspire de : {a['inspiration']}")
                if LLM and st.button("✍️ Rédiger l'avis complet", key=f"llm_{a['id']}"):
                    sg = S[S.id == a["id"]].iloc[0]
                    with st.spinner("Rédaction…"):
                        st.write(assistant.demander(CO.consigne_sage(sg) + "\n\nAnalyse ce plan.", texte[:8000]))
        st.session_state["derniere_analyse"] = (choix, r)

# ------------------------------------------------------------------ actualités
with t_act:
    A = CO.actualites()
    if A.empty:
        st.info("Aucune actualité chargée. Lancez la mise à jour (page Actualités & mises à jour).")
    else:
        Rt = CO.router_actualites(A, S, C)
        st.markdown("Chaque article est attribué au sage dont le domaine est le plus proche (modèle **TF-IDF + similarité cosinus**, "
                    "scikit-learn) ; le sage propose une piste d'amélioration liée à sa grille.")
        cnt = Rt.groupby("role").size().sort_values()
        st.plotly_chart(go.Figure(go.Bar(x=cnt.values, y=cnt.index, orientation="h", marker_color=SERIES[0])).update_layout(
            height=320, title="Articles par sage", hovermode=False), use_container_width=True)
        qui = st.selectbox("Fil d'un sage", ["Tous"] + S.titre.tolist())
        v = Rt if qui == "Tous" else Rt[Rt.role == qui]
        for r in v.itertuples():
            st.markdown(f"<div class='ay-card' style='margin-bottom:.6rem'><h4 style='font-size:1rem'>"
                        f"<a href='{H.escape(str(r.url))}' target='_blank'>{H.escape(str(r.titre))}</a></h4>"
                        f"<p><span class='ay-badge'>{H.escape(r.sage)} · {H.escape(r.role)}</span>"
                        f"<span class='ay-badge'>{H.escape(str(r.source))} · {H.escape(str(r.date))}</span>"
                        f"<span class='ay-badge'>{H.escape(str(r.tonalite))}</span></p>"
                        f"<p style='margin-top:.3rem'>{H.escape(r.lecture)} <b>Proposition :</b> {H.escape(r.proposition)}</p>"
                        f"<p style='font-size:.8rem'>Deuxième regard : {H.escape(str(r.deuxieme_avis))}</p></div>", unsafe_allow_html=True)
        st.dataframe(Rt, hide_index=True, use_container_width=True, column_config={"url": st.column_config.LinkColumn("lien")})

# ------------------------------------------------------------------ méthode
with t_meth:
    c1, c2 = st.columns(2)
    with c1:
        analyse_box("Comment le comité travaille", [
            "**1. Avis indépendants** : chaque sage applique seul sa grille (critères, mots-clés, importance 1 à 3).",
            "**2. Notation** : part des critères traités, pondérée par leur importance (note sur 10).",
            "**3. Synthèse du leader** : moyenne pondérée, décision (adopter, adopter sous conditions, revoir), recommandations "
            "prioritaires, avis minoritaires conservés.",
            "**4. Suivi** : chaque recommandation reçoit un responsable et une date ; réexamen à 90 jours.",
            "**5. Actualité** : classement automatique des articles par domaine (TF-IDF), lecture et proposition du sage concerné.",
        ])
    with c2:
        st.dataframe(S[["nom", "titre", "meilleures_pratiques"]], hide_index=True, use_container_width=True)
    st.markdown("#### Grille complète")
    st.dataframe(C, hide_index=True, use_container_width=True)
    if not LLM:
        st.caption("Pour que chaque sage rédige un avis libre, configurez un modèle de langage (ANTHROPIC_API_KEY ou un serveur "
                   "Ollama local) : voir src/assistant.py.")

# ------------------------------------------------------------------ exports
with t_exp:
    choix_e = st.selectbox("Plan à inclure dans le rapport", list(CO.textes_plans()), key="exp_plan")

    def blocs():
        r = CO.analyser(CO.textes_plans()[choix_e], S, C, frontiere=choix_e.startswith("Frontière"))
        av = pd.DataFrame([{"sage": a["nom"], "rôle": a["titre"], "note": a["score"], "verdict": a["verdict"],
                            "traité": ", ".join(a["forces"]), "à améliorer": " ; ".join(x[1] for x in a["recommandations"])}
                           for a in r["avis"]])
        b = [("h1", "1. Les membres du comité"), ("table", S[["nom", "titre", "domaine", "mission"]]),
             ("h1", f"2. Analyse : {choix_e}"), ("p", r["synthese"]["texte"]), ("table", av)]
        if r["synthese"]["priorites"]:
            b += [("h2", "Recommandations prioritaires"),
                  ("table", pd.DataFrame(r["synthese"]["priorites"], columns=["sage", "rôle", "critère", "recommandation", "importance"]))]
        A2 = CO.actualites()
        if not A2.empty:
            b += [("h1", "3. Lecture de l'actualité"),
                  ("table", CO.router_actualites(A2, S, C)[["date", "titre", "role", "lecture", "proposition"]])]
        b += [("note", "Personnages fictifs. La note mesure la couverture des critères dans le texte disponible, pas la valeur d'un plan "
                       "ni d'un candidat.")]
        return b

    panneau_exports("comite", "Avis du Comité des sages", "Analyse des plans et de l'actualité", blocs,
                    {"membres": S, "criteres": C}, sources="Plans et données de la plateforme Ayiti Data Hub ; actualités collectées.")

pied("Méthode Delphi ; exemples de bonnes pratiques cités dans chaque fiche (Rwanda, Estonie, Malaisie, Colombie, Éthiopie, Brésil, "
     "Israël, Inde, Kenya, Maurice, Botswana).")
