"""Exports professionnels du module Élections : fiche candidat (PDF, PNG, HTML) et rapport complet (PDF, HTML, PNG)."""
from __future__ import annotations

import base64
import html as H
from datetime import date

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from src import elections as E
from src.rapports import BLEU, GRID, INK, INK2, ROUGE, RapportPDF, _png
from src.ui import SERIES

COUL_FIN = {"Fin de mandat": "#0ca30c", "Intérim achevé": SERIES[0], "Mort en fonction": "#8a8984",
            "Démission – exil": "#eda100", "Renversé – exil": "#eb6834", "Mort violente": "#d03b3b",
            "Déporté ou exilé": SERIES[6], "En fonction": INK}
SYMB = {"ok": "✓", "?": "?", "!": "!"}


# ---------------------------------------------------------------- figures matplotlib
def fig_integrite(s: dict, nom: str) -> bytes:
    comp = [k for k in s if k not in ("total", "niveau", "autorites")]
    maxi = {"Sanctions internationales": 50, "Procédures / allégations": 30, "Exposition politique (PPE)": 10,
            "Transparence (site, programme)": 10}
    fig, ax = plt.subplots(figsize=(7.5, 2.8))
    for i, k in enumerate(comp):
        ax.barh(i, maxi[k], color="#f0efec", height=0.55)
        ax.barh(i, s[k], color=E.COULEUR_NIVEAU[s["niveau"]], height=0.55)
        ax.text(maxi[k] + 0.8, i, f"{s[k]} / {maxi[k]}", va="center", fontsize=9, color=INK2)
    ax.set_yticks(range(len(comp)), comp)
    ax.invert_yaxis()
    ax.set_xlim(0, 58)
    ax.grid(False)
    ax.set_xticks([])
    ax.spines[["bottom", "left"]].set_visible(False)
    ax.set_title(f"Score de risque d'intégrité : {s['total']} / 100 ({s['niveau']}) — {nom}")
    return _png(fig)


def fig_faisabilite(det: pd.DataFrame, total: float, nom: str) -> bytes:
    lab = det["Critère"].tolist()
    v = (det["Points"] / det["Poids"]).tolist()
    ang = np.linspace(0, 2 * np.pi, len(lab), endpoint=False).tolist()
    fig = plt.figure(figsize=(6.5, 5.2))
    ax = fig.add_subplot(111, polar=True)
    ax.plot(ang + ang[:1], v + v[:1], color=BLEU, lw=2)
    ax.fill(ang + ang[:1], v + v[:1], color=BLEU, alpha=0.18)
    ax.set_xticks(ang, [l.replace(" & ", " &\n").replace(" : ", "\n") for l in lab], fontsize=8)
    ax.set_ylim(0, 1)
    ax.set_yticks([0.25, 0.5, 0.75, 1], ["", "", "", ""])
    ax.set_title(f"Faisabilité du programme : {total:.0f} / 100 — {nom}", pad=22)
    return _png(fig)


def fig_calendrier(cal: pd.DataFrame) -> bytes:
    d = cal[cal.debut >= "2025-01-01"].reset_index(drop=True)
    fig, ax = plt.subplots(figsize=(10, 0.36 * len(d) + 1.2))
    for i, r in d.iterrows():
        col = "#c3c2b7" if r.statut == "Abandonné" else ROUGE if "TOUR" in r.etape else BLEU if r.statut.startswith(
            "Prévu") or r.statut.startswith("À venir") else SERIES[0]
        larg = max(4, (r.fin - r.debut).days)
        ax.barh(i, larg, left=r.debut, color=col, height=0.6)
        ax.text(r.debut + pd.Timedelta(days=larg + 6), i, r.etape[:80], va="center", fontsize=7.5, color=INK2)
    ax.axvline(pd.Timestamp(date.today()), color=INK, lw=1, ls="--")
    ax.text(pd.Timestamp(date.today()), -0.9, " aujourd'hui", fontsize=8)
    ax.set_yticks([])
    ax.invert_yaxis()
    ax.set_xlim(pd.Timestamp("2025-10-01"), pd.Timestamp("2028-09-30"))
    ax.set_title("Calendrier électoral 2025-2027 (gris : calendriers abandonnés)")
    return _png(fig)


def fig_risques(t: pd.DataFrame) -> bytes:
    t = t.sort_values("total")
    fig, ax = plt.subplots(figsize=(8, 0.33 * len(t) + 1))
    ax.barh(t.Candidat, t.total, color=[E.COULEUR_NIVEAU[n] for n in t.niveau], height=0.62)
    for i, v in enumerate(t.total):
        ax.text(v + 0.8, i, str(v), va="center", fontsize=8, color=INK2)
    ax.set_xlim(0, 100)
    ax.grid(axis="y", visible=False)
    ax.set_title("Score de risque d'intégrité par candidat (0-100)")
    return _png(fig)


def fig_participation(hist: pd.DataFrame, tend: dict | None = None) -> bytes:
    d = hist[(hist.annee >= 1988) & hist.participation_pct.notna()]
    fig, ax = plt.subplots(figsize=(8, 3.6))
    ax.plot(d.annee, d.participation_pct, "o-", color=BLEU, lw=2, label="Participation (%)")
    ax.bar(d.annee, d.score_vainqueur_pct, color=SERIES[1], alpha=0.35, width=1.6, label="Score du vainqueur / candidat en tête (%)")
    if tend:
        ax.errorbar([2027], [tend["prevision"]], yerr=[[tend["prevision"] - tend["bas"]], [tend["haut"] - tend["prevision"]]],
                    fmt="D", color=ROUGE, capsize=4, label="Tendance 2027 (ML, indicatif)")
    ax.set_ylim(0, 100)
    ax.legend(frameon=False, fontsize=8, loc="upper right")
    ax.set_title("Participation et score du vainqueur aux présidentielles (1988-2016)")
    return _png(fig)


def fig_chefs(chefs: pd.DataFrame) -> bytes:
    d = chefs.reset_index(drop=True)
    regs = list(dict.fromkeys(d.sort_values("debut").regime))
    fig, ax = plt.subplots(figsize=(11, 4.4))
    for r in d.itertuples():
        ax.barh(regs.index(r.regime), max(60, (r.fin_effective - r.debut).days), left=r.debut,
                color=COUL_FIN.get(r.fin_categorie, "#999"), height=0.7, edgecolor="white", linewidth=0.4)
    for k, v in COUL_FIN.items():
        ax.barh(0, 0, color=v, label=k)
    ax.set_yticks(range(len(regs)), regs, fontsize=8)
    ax.invert_yaxis()
    ax.grid(axis="y", visible=False)
    ax.legend(ncol=4, fontsize=7, frameon=False, loc="upper center", bbox_to_anchor=(0.5, -0.08))
    ax.set_title(f"{len(d) - 1} chefs d'État depuis 1804, par régime : durée et fin de chaque exercice")
    return _png(fig)


def fig_decennies(dec: pd.DataFrame) -> bytes:
    fig, ax = plt.subplots(figsize=(10, 3.2))
    ax.bar(dec.decennie, dec.chefs, width=8, color=SERIES[0], label="Chefs d'État arrivés au pouvoir")
    ax.bar(dec.decennie, dec.renverses, width=8, color=SERIES[1], label="dont renversés ou morts de mort violente")
    ax.legend(frameon=False, fontsize=8)
    ax.grid(axis="x", visible=False)
    ax.set_title("Instabilité politique par décennie (1800-2026)")
    return _png(fig)


def fig_croissance(g: pd.DataFrame) -> bytes:
    g = g.sort_values("Début")
    fig, ax = plt.subplots(figsize=(8, 0.35 * len(g) + 1))
    v = g["Croissance annuelle moy. PIB/hab. (%)"]
    ax.barh(g.Dirigeant + " (" + g["Début"].astype(str) + "-" + g["Fin"].astype(str) + ")", v,
            color=[SERIES[2] if x >= 0 else SERIES[7] for x in v], height=0.6)
    ax.axvline(0, color=INK2, lw=0.8)
    ax.invert_yaxis()
    ax.grid(axis="y", visible=False)
    ax.set_title("Croissance annuelle moyenne du PIB par habitant réel sous chaque dirigeant")
    return _png(fig)


def carte_png(r: pd.Series, s: dict, analyse: dict) -> bytes:
    """Carte de profil 16:9 à partager."""
    fig = plt.figure(figsize=(16, 9))
    ax = fig.add_axes([0, 0, 1, 1])
    ax.axis("off")
    ax.add_patch(plt.Rectangle((0, 0.955), 0.5, 0.045, color=BLEU, transform=ax.transAxes))
    ax.add_patch(plt.Rectangle((0.5, 0.955), 0.5, 0.045, color=ROUGE, transform=ax.transAxes))
    ax.text(0.04, 0.87, "ÉLECTIONS HAÏTI 2027 · FICHE CANDIDAT", fontsize=13, color=INK2, fontweight="bold", transform=ax.transAxes)
    ax.text(0.04, 0.79, r.nom, fontsize=40, fontweight="bold", color=INK, transform=ax.transAxes)
    ax.text(0.04, 0.73, f"{r.parti} ({r.sigle})" if r.sigle else r.parti, fontsize=18, color=BLEU, transform=ax.transAxes)
    lignes = [("Profession", r.profession), ("Fonctions passées", r.fonctions_passees), ("Ancrage", r.departement_ancrage or "Non documenté"),
              ("Résidence", r.residence), ("Âge", f"{int(r.age)} ans" if r.age == r.age else "Non publié"),
              ("Sanctions", r.sanctions_autorites or "Aucune identifiée"), ("Programme", r.programme_statut)]
    y = 0.63
    for k, v in lignes:
        ax.text(0.04, y, k.upper(), fontsize=11, color=INK2, fontweight="bold", transform=ax.transAxes)
        ax.text(0.20, y, str(v)[:95], fontsize=14, color=INK, transform=ax.transAxes)
        y -= 0.075
    for x0, titre, val, sous, col in ((0.66, "RISQUE D'INTÉGRITÉ", f"{s['total']}", f"/ 100 · {s['niveau']}", E.COULEUR_NIVEAU[s["niveau"]]),
                                      (0.66, "FAISABILITÉ DU PROGRAMME",
                                       f"{analyse['total']:.0f}" if analyse.get("evaluable") else "—",
                                       "/ 100" if analyse.get("evaluable") else "programme non publié", BLEU)):
        yy = 0.55 if "RISQUE" in titre else 0.25
        ax.add_patch(plt.Rectangle((x0, yy - 0.05), 0.3, 0.25, fill=False, ec=GRID, lw=1.5, transform=ax.transAxes))
        ax.add_patch(plt.Rectangle((x0, yy + 0.19), 0.3, 0.008, color=col, transform=ax.transAxes))
        ax.text(x0 + 0.015, yy + 0.14, titre, fontsize=12, color=INK2, fontweight="bold", transform=ax.transAxes)
        ax.text(x0 + 0.015, yy + 0.02, val, fontsize=52, color=col, fontweight="bold", transform=ax.transAxes)
        ax.text(x0 + 0.115, yy + 0.04, sous, fontsize=14, color=INK2, transform=ax.transAxes)
    ax.text(0.04, 0.04, f"Ayiti Data Hub · {date.today():%d/%m/%Y} · 1er tour prévu le 18 juillet 2027 · Score de risque ≠ jugement "
                        "de culpabilité · Sources : CEP, Haiti Policy House, presse", fontsize=10, color="#8a8984", transform=ax.transAxes)
    return _png(fig)


# ---------------------------------------------------------------- fiche candidat
def fiche_pdf(r: pd.Series, s: dict, analyse: dict, elig: list, sanc: pd.DataFrame, presse: pd.DataFrame) -> bytes:
    pdf = RapportPDF(f"Fiche candidat — {r.nom}")
    pdf.couverture(f"{r.parti}" + (f" ({r.sigle})" if r.sigle else "") + f"\nÉlection présidentielle · 1er tour prévu le "
                   f"{E.DATE_PREMIER_TOUR:%d/%m/%Y}", image=carte_png(r, s, analyse))
    pdf.section("1. Identité et parcours")
    pdf.tableau(pd.DataFrame([("Nom (usage)", r.nom), ("Nom au CEP", r.nom_cep or "—"), ("Parti / regroupement", r.parti),
                              ("Statut", r.statut_inscription), ("Naissance", f"{r.naissance} · {r.lieu_naissance}".strip(" ·") or "Non publiée"),
                              ("Ancrage", r.departement_ancrage or "Non documenté"), ("Résidence", r.residence),
                              ("Profession", r.profession), ("Site internet", r.site_web or "Non identifié")],
                             columns=["Rubrique", "Information"]), [50, 128])
    pdf.paragraphe(f"Fonctions passées : {r.fonctions_passees}")
    pdf.paragraphe(f"Exposition politique : {E.LIB_PPE[int(r.niveau_ppe)]}.")
    pdf.section("2. Intégrité, sanctions et procédures")
    pdf.figure(fig_integrite(s, r.nom))
    pdf.paragraphe(f"Procédures / allégations : {E.LIB_ALLEG[int(r.niveau_allegation)]}. {r.allegations}")
    if len(sanc):
        pdf.tableau(sanc[["autorite", "regime", "date", "motif_officiel_resume"]].rename(columns={
            "autorite": "Autorité", "regime": "Régime", "date": "Date", "motif_officiel_resume": "Motif"}), [32, 48, 18, 80])
    pdf.paragraphe("Avertissement : une sanction est une mesure administrative d'un État ou d'une organisation, une allégation n'est "
                   "pas une condamnation. Ce score mesure des signaux de risque publics (méthode inspirée du filtrage LCB-FT des PPE).")
    pdf.section("3. Éligibilité (art. 135 de la Constitution et décret électoral)")
    pdf.tableau(pd.DataFrame([(SYMB[e], a, b) for a, e, b in elig], columns=["", "Condition", "Constat"]), [8, 90, 80])
    pdf.section("4. Programme et faisabilité")
    if analyse.get("evaluable"):
        pdf.figure(fig_faisabilite(analyse["details"], analyse["total"], r.nom), largeur=140)
        pdf.tableau(analyse["details"][["Critère", "Poids", "Points"]], [110, 30, 38])
        for x in analyse["remarques"]:
            pdf.paragraphe(x, puce=True)
    else:
        pdf.paragraphe(f"Programme : {r.programme_statut}. Le score de faisabilité sera calculé dès la publication du programme "
                       "(bouton de mise à jour ou saisie dans l'espace Administration).")
        if r.orientations_connues:
            pdf.paragraphe(f"Orientations connues : {r.orientations_connues}.")
    if len(presse):
        pdf.section("5. Revue de presse récente")
        for p in presse.head(12).itertuples():
            pdf.lien(f"{str(p.date)[:10]} · {p.source} — {p.titre}", p.lien)
    pdf.section("Sources")
    for u in (r.source_1, r.source_2):
        if u:
            pdf.lien(u, u)
    return bytes(pdf.output())


CSS_HTML = """
:root{--bleu:#00209F;--rouge:#D21034;--ink:#0b0b0b;--ink2:#52514e;--grid:#e6e5e0;--bg:#fcfcfb;--card:#fff}
@media (prefers-color-scheme:dark){:root{--ink:#f0efec;--ink2:#c3c2b7;--grid:#383835;--bg:#151514;--card:#1f1f1d}}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--ink);font:15px/1.55 'Source Sans 3',Arial,sans-serif}
.band{height:6px;background:linear-gradient(90deg,var(--bleu) 0 50%,var(--rouge) 50% 100%)}
main{max-width:1050px;margin:0 auto;padding:28px 16px 60px}h1,h2{font-family:Fraunces,Georgia,serif;letter-spacing:-.01em}
h1{font-size:2.2rem;margin:.2rem 0}h2{color:var(--bleu);border-bottom:1px solid var(--grid);padding-bottom:.3rem;margin-top:2rem}
.eyebrow{text-transform:uppercase;letter-spacing:.14em;font-size:.78rem;font-weight:700;color:var(--ink2)}
.kpis{display:grid;grid-template-columns:repeat(auto-fit,minmax(170px,1fr));gap:12px;margin:18px 0}
.kpi{background:var(--card);border:1px solid var(--grid);border-radius:14px;padding:12px 14px}
.kpi .l{font-size:.78rem;text-transform:uppercase;color:var(--ink2);font-weight:700}.kpi .v{font:700 1.8rem Fraunces,Georgia,serif}
table{width:100%;border-collapse:collapse;font-size:.92rem;background:var(--card)}td,th{padding:7px 9px;border-bottom:1px solid var(--grid);text-align:left;vertical-align:top}
th{background:rgba(0,32,159,.06)}img{max-width:100%;border-radius:10px;border:1px solid var(--grid);background:#fff}
.note{border-left:4px solid var(--bleu);padding:.6rem .9rem;background:rgba(0,32,159,.05);border-radius:0 10px 10px 0;font-size:.92rem}
.b{display:inline-block;padding:.05rem .5rem;border-radius:999px;font-size:.8rem;font-weight:700;color:#fff}
a{color:var(--bleu)}footer{color:var(--ink2);font-size:.82rem;margin-top:2.5rem;border-top:1px solid var(--grid);padding-top:.7rem}
"""


def _img(png: bytes, alt: str) -> str:
    return f"<img alt='{H.escape(alt)}' src='data:image/png;base64,{base64.b64encode(png).decode()}'/>"


def _table(df: pd.DataFrame) -> str:
    return df.to_html(index=False, escape=True, border=0, na_rep="—")


def _page(titre: str, corps: str) -> str:
    return (f"<!doctype html><html lang='fr'><head><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'>"
            f"<title>{H.escape(titre)}</title><link rel='preconnect' href='https://fonts.googleapis.com'>"
            "<link href='https://fonts.googleapis.com/css2?family=Fraunces:opsz,wght@9..144,700&family=Source+Sans+3:wght@400;700&display=swap' rel='stylesheet'>"
            f"<style>{CSS_HTML}</style></head><body><div class='band'></div><main>{corps}"
            f"<footer>Ayiti Data Hub · généré le {date.today():%d/%m/%Y} · Les scores de risque mesurent des signaux publics et ne "
            "constituent pas un jugement de culpabilité.</footer></main></body></html>")


def fiche_html(r: pd.Series, s: dict, analyse: dict, elig: list, sanc: pd.DataFrame, presse: pd.DataFrame) -> str:
    e = H.escape
    col = E.COULEUR_NIVEAU[s["niveau"]]
    fz = f"{analyse['total']:.0f} / 100" if analyse.get("evaluable") else "Non évaluable"
    corps = (f"<div class='eyebrow'>Élections Haïti · 1er tour le {E.DATE_PREMIER_TOUR:%d/%m/%Y}</div><h1>{e(r.nom)}</h1>"
             f"<p style='color:var(--bleu);font-size:1.15rem;margin:0'>{e(r.parti)} {('(' + e(r.sigle) + ')') if r.sigle else ''}</p>"
             f"<div class='kpis'><div class='kpi'><div class='l'>Risque d'intégrité</div><div class='v' style='color:{col}'>{s['total']}</div>"
             f"<span class='b' style='background:{col}'>{s['niveau']}</span></div><div class='kpi'><div class='l'>Faisabilité programme</div>"
             f"<div class='v'>{fz}</div></div><div class='kpi'><div class='l'>Exposition politique</div><div style='font-weight:700'>"
             f"{e(E.LIB_PPE[int(r.niveau_ppe)])}</div></div><div class='kpi'><div class='l'>Sanctions</div><div style='font-weight:700'>"
             f"{e(r.sanctions_autorites or 'Aucune identifiée')}</div></div></div>"
             "<h2>Identité et parcours</h2>" + _table(pd.DataFrame(
                 [("Profession", r.profession), ("Fonctions passées", r.fonctions_passees), ("Naissance", f"{r.naissance} {r.lieu_naissance}".strip() or "Non publiée"),
                  ("Ancrage", r.departement_ancrage or "Non documenté"), ("Résidence", r.residence), ("Statut CEP", r.statut_inscription),
                  ("Site internet", r.site_web or "Non identifié")], columns=["Rubrique", "Information"]))
             + "<h2>Intégrité et sanctions</h2>" + _img(fig_integrite(s, r.nom), "Score d'intégrité")
             + f"<p>{e(E.LIB_ALLEG[int(r.niveau_allegation)])}. {e(r.allegations)}</p>"
             + (_table(sanc[["autorite", "regime", "date", "motif_officiel_resume", "source"]]) if len(sanc) else "")
             + "<h2>Éligibilité</h2>" + _table(pd.DataFrame([(SYMB[x], a, b) for a, x, b in elig], columns=["", "Condition", "Constat"]))
             + "<h2>Programme et faisabilité</h2>")
    if analyse.get("evaluable"):
        corps += _img(fig_faisabilite(analyse["details"], analyse["total"], r.nom), "Faisabilité") + _table(
            analyse["details"]) + "<ul>" + "".join(f"<li>{e(x)}</li>" for x in analyse["remarques"]) + "</ul>"
    else:
        corps += f"<div class='note'>{e(r.programme_statut)} — le score sera calculé dès la publication du programme.</div>"
    if len(presse):
        corps += "<h2>Revue de presse</h2><ul>" + "".join(
            f"<li>{e(str(p.date)[:10])} · {e(p.source)} — <a href='{e(p.lien)}'>{e(p.titre)}</a></li>" for p in presse.head(15).itertuples()) + "</ul>"
    corps += "<h2>Sources</h2><ul>" + "".join(f"<li><a href='{e(u)}'>{e(u)}</a></li>" for u in (r.source_1, r.source_2) if u) + "</ul>"
    return _page(f"Fiche candidat — {r.nom}", corps)


# ---------------------------------------------------------------- rapport complet
def figures_rapport(c, integ, cal, hist, chefs, dec, croiss, tend) -> dict[str, bytes]:
    imgs = {"01_calendrier.png": fig_calendrier(cal), "02_risques_candidats.png": fig_risques(integ),
            "03_participation.png": fig_participation(hist, tend), "04_chefs_etat_1804_2026.png": fig_chefs(chefs),
            "05_instabilite_decennies.png": fig_decennies(dec)}
    if not croiss.empty:
        imgs["06_croissance_par_dirigeant.png"] = fig_croissance(croiss)
    return imgs


def rapport_pdf(c, integ, cal, hist, det, chefs, stats, dec, croiss, tend, org, ml_txt: list[str]) -> tuple[bytes, dict]:
    imgs = figures_rapport(c, integ, cal, hist, chefs, dec, croiss, tend)
    pdf = RapportPDF("Élections en Haïti 2026-2027")
    jours = (E.DATE_PREMIER_TOUR - date.today()).days
    from src.rapports import infographie
    couv = infographie([("1er tour", f"{E.DATE_PREMIER_TOUR:%d/%m/%Y}", f"J-{jours}"), ("2e tour", f"{E.DATE_SECOND_TOUR:%d/%m/%Y}", "+ élections locales"),
                        ("Candidatures", str(len(c)), "liste provisoire"), ("Sanctionnés", str(int((c.sanctions_autorites != '').sum())), "États-Unis, Canada, UE"),
                        ("Chefs d'État", str(stats["nb"]), "depuis 1804"), ("Mandats achevés", str(stats["fin_mandat"]), "fin normale")],
                       "Élections en Haïti 2026-2027", "Candidats · intégrité · programmes · 250 ans d'histoire")
    pdf.couverture(f"Candidats, intégrité, faisabilité des programmes et 250 ans d'histoire politique\n1er tour prévu le "
                   f"{E.DATE_PREMIER_TOUR:%d/%m/%Y} (J-{jours}) · 2e tour le {E.DATE_SECOND_TOUR:%d/%m/%Y}", image=couv)
    pdf.section("1. Synthèse")
    pdf.chiffres([("1er tour", f"{E.DATE_PREMIER_TOUR:%d/%m/%Y}"), ("Candidatures", str(len(c))),
                  ("Candidats sanctionnés", str(int((c.sanctions_autorites != '').sum()))), ("Programmes publiés", str(int((c.texte_programme != '').sum()))),
                  ("Chefs d'État depuis 1804", str(stats["nb"])), ("Mandats achevés", str(stats["fin_mandat"]))])
    for t in ["Le CEP a publié le 28 octobre 2026 un troisième calendrier : campagne du 15 avril au 17 juillet 2027, 1er tour le 18 juillet, "
              "2e tour et élections locales le 4 octobre 2027.",
              f"{len(c)} candidatures à la présidence sont signalées (liste provisoire, inscriptions closes le 31 octobre 2026) ; la liste "
              "définitive dépend de l'examen des dossiers par le CEP.",
              "Le décret du 6 octobre 2026 a retiré la règle qui écartait les personnes sanctionnées par des États étrangers ; seules les "
              "sanctions du Conseil de sécurité de l'ONU restent éliminatoires.",
              f"Depuis 1804, seuls {stats['fin_mandat']} chefs d'État sur {stats['nb']} ont achevé normalement leur exercice ; "
              f"{stats['renverses']} ont été renversés et {stats['violentes']} sont morts de mort violente."]:
        pdf.paragraphe(t, puce=True)
    pdf.section("2. Calendrier électoral")
    pdf.figure(imgs["01_calendrier.png"])
    pdf.tableau(cal[cal.debut >= "2025-01-01"].assign(Date=lambda d: d.debut.dt.strftime("%d/%m/%Y"))[["Date", "etape", "statut"]]
                .rename(columns={"etape": "Étape", "statut": "Statut"}), [24, 124, 30])
    pdf.section("3. Les candidats")
    pdf.tableau(c[["nom", "sigle", "profession", "sanctions_autorites"]].rename(columns={
        "nom": "Candidat", "sigle": "Parti", "profession": "Profession", "sanctions_autorites": "Sanctions"}), [46, 30, 60, 42])
    pdf.section("4. Intégrité et sanctions (méthode LCB-FT)")
    pdf.figure(imgs["02_risques_candidats.png"])
    pdf.paragraphe("Score de 0 à 100 : sanctions internationales (50 pts max ; ONU 40, États-Unis 25, UE 20, Canada 15), procédures et "
                   "allégations (30), exposition politique (10), transparence (10). Il mesure des signaux publics, pas une culpabilité.")
    pdf.section("5. Faisabilité des programmes")
    pdf.tableau(det, [60, 30, 30, 58])
    pdf.paragraphe("Grille sur 100 points : sécurité (20), financement (20), précision (15), gouvernance (15), économie (10), social (10), "
                   "calendrier (5), territoires et diaspora (5). Aucun programme complet n'est publié à ce jour : les scores apparaîtront "
                   "après publication.")
    pdf.section("6. Historique des élections présidentielles")
    pdf.figure(imgs["03_participation.png"])
    pdf.tableau(hist.assign(annee=hist.annee.astype(str)).fillna("—")[["annee", "type", "vainqueur", "score_vainqueur_pct", "participation_pct", "issue"]].rename(columns={
        "annee": "Année", "type": "Type", "vainqueur": "Vainqueur", "score_vainqueur_pct": "Score %", "participation_pct": "Partic. %",
        "issue": "Issue"}), [13, 38, 38, 15, 15, 59], max_lignes=40)
    pdf.section("7. 250 ans de vie politique (1776-2026)")
    pdf.figure(imgs["04_chefs_etat_1804_2026.png"])
    pdf.figure(imgs["05_instabilite_decennies.png"])
    if "06_croissance_par_dirigeant.png" in imgs:
        pdf.figure(imgs["06_croissance_par_dirigeant.png"], "Banque mondiale, PIB par habitant en USD constants de 2015.")
    pdf.section("8. Machine learning — principaux enseignements")
    for t in ml_txt:
        pdf.paragraphe(t, puce=True)
    pdf.section("9. Organismes impliqués")
    pdf.tableau(org[["sigle", "nom", "categorie"]].rename(columns={"sigle": "Sigle", "nom": "Organisme", "categorie": "Rôle"}),
                [26, 92, 60], max_lignes=40)
    return bytes(pdf.output()), imgs


def rapport_html(c, integ, cal, hist, det, chefs, stats, imgs: dict, org, ml_txt) -> str:
    jours = (E.DATE_PREMIER_TOUR - date.today()).days
    k = "".join(f"<div class='kpi'><div class='l'>{a}</div><div class='v'>{b}</div></div>" for a, b in (
        ("1er tour", f"{E.DATE_PREMIER_TOUR:%d/%m/%Y}"), ("Compte à rebours", f"J-{jours}"), ("Candidatures", len(c)),
        ("Candidats sanctionnés", int((c.sanctions_autorites != "").sum())), ("Chefs d'État depuis 1804", stats["nb"])))
    corps = (f"<div class='eyebrow'>Ayiti Data Hub · rapport</div><h1>Élections en Haïti 2026-2027</h1><div class='kpis'>{k}</div>"
             "<h2>Calendrier</h2>" + _img(imgs["01_calendrier.png"], "Calendrier")
             + "<h2>Candidats</h2>" + _table(c[["nom", "parti", "profession", "fonctions_passees", "sanctions_autorites"]].rename(columns={
                 "nom": "Candidat", "parti": "Parti", "profession": "Profession", "fonctions_passees": "Fonctions passées",
                 "sanctions_autorites": "Sanctions"}))
             + "<h2>Intégrité</h2>" + _img(imgs["02_risques_candidats.png"], "Risques") + _table(integ.drop(columns="id"))
             + "<h2>Faisabilité des programmes</h2>" + _table(det)
             + "<h2>Historique des élections</h2>" + _img(imgs["03_participation.png"], "Participation") + _table(hist)
             + "<h2>250 ans de chefs d'État</h2>" + _img(imgs["04_chefs_etat_1804_2026.png"], "Chefs d'État")
             + _img(imgs["05_instabilite_decennies.png"], "Instabilité")
             + (_img(imgs["06_croissance_par_dirigeant.png"], "Croissance") if "06_croissance_par_dirigeant.png" in imgs else "")
             + _table(chefs[["nom", "titre", "debut", "fin", "mode_accession", "fin_categorie", "destin"]].assign(
                 debut=lambda d: d.debut.dt.strftime("%d/%m/%Y")))
             + "<h2>Machine learning</h2><ul>" + "".join(f"<li>{H.escape(t)}</li>" for t in ml_txt) + "</ul>"
             + "<h2>Organismes impliqués</h2>" + _table(org))
    return _page("Élections en Haïti 2026-2027", corps)
