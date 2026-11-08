import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from streamlit_folium import st_folium

from src import comite as CO
from src import frontiere as F
from src.exports_doc import panneau_exports
from src.ui import SERIES, analyse_box, entete, fmt, kpis, note, pied, setup

setup("Frontière : 20 postes", "🚧")
entete("La frontière en 20 postes",
       "5 grands postes modernisés, 8 postes secondaires, 7 bases de surveillance ; gestion, ressources locales "
       "(« grès kochon kwit kochon »), budget sur 5 ans, comparaison avec le programme d'Etzer Émile et placement par machine learning.")

P, H, RL = F.postes(), F.budget_hyp(), F.ressources_locales()
B = F.budget_annuel(H)
tot = B["Total 5 ans"].sum()
part_loc = (B["Total 5 ans"] * B.part_locale_pct / 100).sum() / tot * 100
kpis([
    {"lab": "Points de passage", "val": "5 → 20", "sub": "5 grands · 8 secondaires · 7 bases", "style": "accent"},
    {"lab": "Frontière terrestre", "val": "≈380 km", "sub": "≈100 passages réels (OIM, 2016)"},
    {"lab": "Agents", "val": f"{P.effectif.sum():,}".replace(",", " "), "sub": "DIE, AGD, PNH, FAd'H, MARNDR"},
    {"lab": "Budget 5 ans", "val": f"{tot / 1e6:,.0f} M USD".replace(",", " "), "sub": "scénario médian"},
    {"lab": "Part dépensée localement", "val": f"{part_loc:.0f} %", "sub": "matériaux, main-d'œuvre, services", "style": "alert"},
])
note("Les 5 postes officiels actuels sont Ouanaminthe, Thomassique, Belladère, Malpasse et Anse-à-Pitres (bureaux de douane "
     "frontaliers cités par Le Nouvelliste). Les 15 autres emplacements, les effectifs et le budget sont des <b>propositions "
     "d'Ayiti Data Hub</b> ; les coordonnées sont approximatives et toutes les hypothèses sont modifiables "
     "(data/curated/postes_frontaliers.csv et budget_frontiere.csv).")

t_map, t_list, t_gest, t_loc, t_bud, t_etz, t_ml, t_com, t_exp = st.tabs([
    "🗺️ Carte", "📋 Les 20 postes", "⚙️ Gestion", "🌿 Ressources locales", "💰 Budget 5 ans", "⚖️ Comparaison Etzer",
    "🤖 Machine learning", "🧓 Avis du comité", "📥 Exports"])

with t_map:
    voir_ml = st.toggle("Afficher aussi les points optimaux calculés par machine learning", value=False)
    st_folium(F.carte(F.placement_ml(20) if voir_ml else None), height=680, use_container_width=True, returned_objects=[])
    st.caption("Cercles : rayon de 15 km autour de chaque poste. Trait noir pointillé : frontière terrestre (limites CNIGS).")

with t_list:
    niv = st.multiselect("Niveau", P.niveau.unique().tolist(), default=P.niveau.unique().tolist())
    st.dataframe(P[P.niveau.isin(niv)], hide_index=True, use_container_width=True)
    c = P.groupby(["departement", "niveau"]).size().unstack(fill_value=0)
    st.dataframe(c, use_container_width=True)

with t_gest:
    cols = st.columns(2)
    for i, (t, d) in enumerate(F.GESTION):
        cols[i % 2].markdown(f"<div class='ay-card' style='margin-bottom:.8rem'><h4>{t}</h4><p>{d}</p></div>", unsafe_allow_html=True)

with t_loc:
    st.markdown("**« Grès kochon kwit kochon »** : le système doit se construire et se financer d'abord avec ce que le pays a déjà — "
                "ses matériaux, ses bras, ses entreprises, ses recettes et sa diaspora.")
    st.dataframe(RL, hide_index=True, use_container_width=True)
    pl = B[["poste_budgetaire", "Total 5 ans", "part_locale_pct"]].assign(
        local_musd=lambda d: d["Total 5 ans"] * d.part_locale_pct / 100 / 1e6, importe_musd=lambda d: d["Total 5 ans"] * (100 - d.part_locale_pct) / 100 / 1e6)
    fig = go.Figure()
    fig.add_bar(y=pl.poste_budgetaire.str.slice(0, 55), x=pl.local_musd, name="Dépensé en Haïti", orientation="h", marker_color=SERIES[2])
    fig.add_bar(y=pl.poste_budgetaire.str.slice(0, 55), x=pl.importe_musd, name="Importé", orientation="h", marker_color="#b9b8b3")
    fig.update_layout(barmode="stack", height=520, title=f"Où va l'argent : {part_loc:.0f} % dépensé en Haïti", xaxis_title="millions USD",
                      yaxis=dict(autorange="reversed"), hovermode="y unified")
    st.plotly_chart(fig, use_container_width=True)

with t_bud:
    st.markdown("Modifiez les hypothèses (quantités, coûts bas / médian / haut, part locale, phasage par année en %) : tout se recalcule.")
    Hm = st.data_editor(H.drop(columns=["reference"]), use_container_width=True, num_rows="fixed", key="hyp_budget")
    Hm["reference"] = H.reference
    Bm = F.budget_annuel(Hm)
    tm = Bm["Total 5 ans"].sum()
    fig = go.Figure()
    for nat, col in (("Investissement", SERIES[0]), ("Fonctionnement", SERIES[1])):
        fig.add_bar(x=F.ANNEES, y=Bm[Bm.nature == nat][F.ANNEES].sum().values / 1e6, name=nat, marker_color=col)
    fig.update_layout(barmode="stack", title=f"Budget par année — total {tm / 1e6:,.0f} M USD sur 5 ans".replace(",", " "),
                      yaxis_title="millions USD", height=380)
    st.plotly_chart(fig, use_container_width=True)
    st.dataframe(Bm.assign(**{a: (Bm[a] / 1e6).round(2) for a in F.ANNEES + ["Total 5 ans"]}), hide_index=True, use_container_width=True)
    st.caption("Montants en millions USD. La maintenance (5 % par an du capital déjà installé) est ajoutée automatiquement.")

    st.markdown("#### Incertitude (simulation de Monte Carlo, 5 000 tirages)")
    mc = F.monte_carlo(Hm)
    p10, p50, p90 = np.percentile(mc, [10, 50, 90]) / 1e6
    hfig = go.Figure(go.Histogram(x=mc / 1e6, nbinsx=50, marker_color=SERIES[0]))
    for v, lab in ((p10, "P10"), (p50, "P50"), (p90, "P90")):
        hfig.add_vline(x=v, line_dash="dash", annotation_text=f"{lab} {v:.0f}")
    hfig.update_layout(height=320, xaxis_title="coût total sur 5 ans (M USD)", yaxis_title="tirages", showlegend=False, hovermode=False)
    st.plotly_chart(hfig, use_container_width=True)
    st.markdown(f"Dans 80 % des cas, le coût total se situe entre **{p10:.0f} et {p90:.0f} M USD** (médiane {p50:.0f}).")

    st.markdown("#### Le plan peut-il se financer lui-même ?")
    c1, c2 = st.columns(2)
    taux = c1.slider("Taux effectif de taxation des importations formalisées (%)", 5, 25, 12) / 100
    cible = c2.slider("Part du commerce du régime national qui passe réellement par les postes en année 5 (%)", 20, 90, 60) / 100
    R = F.recettes(taux, cible)
    cout = Bm[F.ANNEES].sum().values
    rf = go.Figure()
    rf.add_bar(x=F.ANNEES, y=cout / 1e6, name="Coût du plan", marker_color=SERIES[1])
    rf.add_bar(x=F.ANNEES, y=R.recettes_supplementaires_usd / 1e6, name="Recettes douanières supplémentaires", marker_color=SERIES[2])
    rf.update_layout(barmode="group", height=360, yaxis_title="millions USD")
    st.plotly_chart(rf, use_container_width=True)
    solde = R.recettes_supplementaires_usd.sum() - cout.sum()
    analyse_box("Lecture", [
        f"Recettes actuelles estimées des 5 bureaux frontaliers : **≈{F.RECETTES_FRONTIERE_HTG / F.HTG_USD / (64 / 12) / 1e6:.0f} M USD par an** "
        "(11,2 milliards de gourdes d'octobre 2019 à janvier 2025).",
        f"Exportations dominicaines vers Haïti : **{F.EXPORTS_RD_2025 / 1e6:,.0f} M USD** de janvier à novembre 2025, dont "
        f"{F.REGIME_NATIONAL_2025 / 1e6:,.0f} M au régime national.".replace(",", " "),
        f"Avec ces hypothèses, le solde sur 5 ans (recettes supplémentaires − coût) est de **{solde / 1e6:+,.0f} M USD**.".replace(",", " "),
        "Hypothèse forte : la hausse des recettes dépend de l'intégrité des agents et de la fin de la contrebande entre les postes.",
    ])

with t_etz:
    st.dataframe(F.comparaison_etzer(tot), hide_index=True, use_container_width=True)
    analyse_box("En résumé", [
        "**Convergences** : scanners, biométrie, reprise rapide des postes existants, rôle des FAd'H aux frontières et sur les côtes, "
        "interconnexion des données douanières et fiscales.",
        f"**Ce que le plan 20 postes ajoute** : un maillage chiffré (15 nouveaux points), un budget ligne par ligne (≈{tot / 1e6:.0f} M USD "
        "sur 5 ans), une part locale mesurée, des comités frontaliers et un régime pour le petit commerce.",
        f"**Ordre de grandeur** : {tot / 1e6:.0f} M USD représentent ≈{tot / 15e9 * 100:.1f} % de l'enveloppe infrastructures (15 Md USD) "
        "et ≈" + f"{tot / 30e9 * 100:.2f}" + " % du programme total (30 Md USD) annoncés par la campagne d'Etzer Émile.",
        "Cette comparaison décrit deux documents ; elle ne juge pas un candidat.",
    ])

with t_ml:
    st.markdown("**Méthode** : la frontière est découpée en points tous les ~1 km. Chaque point reçoit un poids selon la population "
                "qui vit à proximité (décroissance sur ~10 km). Un algorithme de **k-moyennes pondérées** (scikit-learn) cherche les "
                "k emplacements qui minimisent la distance entre les habitants de la frontière et le poste le plus proche.")
    k = st.slider("Nombre de points à placer (k)", 5, 30, 20)
    ml = F.placement_ml(k)
    sc = F.comparer_scenarios(k)
    st.dataframe(sc, hide_index=True, use_container_width=True)
    a, b = st.columns([3, 2])
    with a:
        st_folium(F.carte(ml), height=560, use_container_width=True, returned_objects=[], key="ml_map")
    with b:
        st.dataframe(ml, hide_index=True, use_container_width=True, height=540)
    analyse_box("Ce que dit le modèle", [
        f"Avec 5 postes, un habitant de la frontière est en moyenne à **{sc.iloc[0].distance_moyenne_ponderee_km} km** d'un poste ; "
        f"avec le plan proposé, **{sc.iloc[2].distance_moyenne_ponderee_km} km**.",
        "Le modèle ignore le relief, les routes et l'emplacement des marchés : il sert à repérer les trous du maillage, pas à "
        "choisir seul un site. Le choix final se fait avec les habitants, le génie et le vis-à-vis dominicain.",
    ])

with t_com:
    r = CO.analyser(F.texte_plan(), frontiere=True)
    s = r["synthese"]
    note(f"<b>{s['decision']}</b> — note {s['note']}/10. {s['texte']}")
    note("Biais à garder en tête : la grille du comité a été écrite en même temps que ce plan ; une note élevée signifie que le texte "
         "répond aux critères, pas que le plan réussira.", "warn")
    st.dataframe(pd.DataFrame([{"sage": a["nom"], "rôle": a["titre"], "note": a["score"], "verdict": a["verdict"],
                                "à améliorer": " ; ".join(x[1] for x in a["recommandations"][:2])} for a in r["avis"]]),
                 hide_index=True, use_container_width=True)
    try:
        st.page_link("pages/30_comite_des_sages.py", label="Ouvrir le Comité des sages", icon="🧓")
    except Exception:  # page lancée seule (hors menu)
        pass

with t_exp:
    def blocs():
        rr = CO.analyser(F.texte_plan(), frontiere=True)
        return [
            ("note", "Emplacements (hors 5 postes existants), effectifs et budget : propositions d'Ayiti Data Hub, hypothèses modifiables."),
            ("h1", "1. Carte des 20 postes"), ("img", F.fig_carte(), ""),
            ("table", P[["id", "nom", "niveau", "commune", "departement", "province_rd_vis_a_vis", "statut", "effectif", "annee_ouverture"]]),
            ("h1", "2. Gestion"), ("ul", [f"**{t}** — {d}" for t, d in F.GESTION]),
            ("h1", "3. Ressources locales (« grès kochon kwit kochon »)"), ("table", RL),
            ("h1", "4. Budget sur 5 ans (millions USD, scénario médian)"), ("img", F.fig_budget(B), ""),
            ("table", B.assign(**{a: (B[a] / 1e6).round(2) for a in F.ANNEES + ["Total 5 ans"]}).drop(columns=["nature"])),
            ("p", f"Total : {tot / 1e6:.0f} M USD ; part dépensée en Haïti : {part_loc:.0f} %."),
            ("h1", "5. Comparaison avec le programme d'Etzer Émile"), ("table", F.comparaison_etzer(tot)),
            ("h1", "6. Machine learning : couverture de la frontière"), ("table", F.comparer_scenarios(20)),
            ("h1", "7. Avis du comité des sages"), ("p", rr["synthese"]["texte"]),
        ]

    panneau_exports("front", "La frontière en 20 postes", "Gestion, ressources locales, budget sur 5 ans et comparaison", blocs,
                    {"postes": P, "budget_hypotheses": H, "budget_annuel": B, "ressources_locales": RL,
                     "comparaison_etzer": F.comparaison_etzer(tot), "scenarios_ml": F.comparer_scenarios(20)},
                    sources="Le Nouvelliste (bureaux frontaliers, recettes) ; HaitiLibre (exportations RD 2025) ; OIM (2016) ; "
                            "TradeMark Africa (scanners) ; voteetzer.ht ; CNIGS/HDX (limites).")

pied("<a href='https://lenouvelliste.com/en/article/253400/a-closer-look-at-the-porous-haiti-dominican-republic-border'>Le Nouvelliste</a> ; "
     "<a href='https://mail.haitilibre.com/en/news-46471-haiti-economy-dominican-exports-to-haiti-exceed-one-billion-usd-2025.html'>HaitiLibre</a> ; "
     "<a href='https://reliefweb.int/report/haiti/iom-haiti-border-monitoring-situation-report-3-march-2016'>OIM</a> ; "
     "<a href='https://trademarkafrica.com/x-ray-cargo-scanners-worth-usd-2-65-million-set-to-improve-efficiency-and-revenue-collection-at-tunduma-osbp/'>TradeMark Africa</a> ; "
     "<a href='https://voteetzer.ht/priorite/infrastructures'>voteetzer.ht</a>.")
