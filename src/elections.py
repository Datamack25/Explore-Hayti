"""Élections en Haïti : chargement des données, score d'intégrité (type filtrage LCB-FT/PPE),
analyse de faisabilité des programmes (/100), statistiques historiques (250 ans).

Toutes les données vérifiées sont dans data/curated/elections_*.csv (modifiables depuis l'espace Administration) ;
les données collectées par le bouton de mise à jour sont dans data/live/elections_*.csv.
"""
from __future__ import annotations

import re
import unicodedata
from datetime import date

import numpy as np
import pandas as pd
import streamlit as st

from src.utils import CURATED, LIVE

DATE_PREMIER_TOUR = date(2027, 7, 18)
DATE_SECOND_TOUR = date(2027, 10, 4)
DATE_CALENDRIER = date(2026, 10, 28)  # publication du calendrier en vigueur


def _read(nom: str, dossier=CURATED, **kw) -> pd.DataFrame:
    p = dossier / f"{nom}.csv"
    if not p.exists():
        return pd.DataFrame()
    return pd.read_csv(p, **kw)


@st.cache_data(show_spinner=False)
def candidats() -> pd.DataFrame:
    c = _read("elections_candidats", dtype=str).fillna("")
    for col in ("niveau_ppe", "exp_executif", "exp_legislatif", "exp_local", "exp_judiciaire", "niveau_allegation"):
        c[col] = pd.to_numeric(c[col], errors="coerce").fillna(0).astype(int)
    c["age"] = c.naissance.map(_age)
    # Programmes : texte saisi (curated) ou collecté sur le site du candidat (live)
    prog = _read("elections_programmes", dtype=str).fillna("")
    live = _read("elections_programmes_textes", LIVE, dtype=str).fillna("")
    if not live.empty:
        prog = pd.concat([prog[prog.texte.str.len() > 0], live], ignore_index=True).drop_duplicates("candidat_id")
    textes = dict(zip(prog.candidat_id, prog.texte)) if not prog.empty else {}
    c["texte_programme"] = c.id.map(textes).fillna("")
    men = mentions()
    if not men.empty:
        c = c.merge(men, left_on="id", right_on="candidat_id", how="left").drop(columns="candidat_id")
    for col, v in (("nb_articles", 0), ("tonalite_moy", 0.0)):
        c[col] = pd.to_numeric(c[col], errors="coerce").fillna(v) if col in c else v
    return c


def _age(s: str) -> float:
    m = re.match(r"(\d{4})-(\d{2})-(\d{2})", str(s))
    if not m:
        return np.nan
    n = date(int(m[1]), int(m[2]), int(m[3]))
    t = date.today()
    return t.year - n.year - ((t.month, t.day) < (n.month, n.day))


@st.cache_data(show_spinner=False)
def sanctions() -> pd.DataFrame:
    return _read("elections_sanctions", dtype=str).fillna("")


@st.cache_data(show_spinner=False)
def organismes() -> pd.DataFrame:
    return _read("elections_organismes").fillna("")


@st.cache_data(show_spinner=False)
def calendrier() -> pd.DataFrame:
    c = _read("elections_calendrier").fillna("")
    c["debut"] = pd.to_datetime(c.debut)
    c["fin"] = pd.to_datetime(c.fin.replace("", np.nan)).fillna(c.debut)
    return c.sort_values("debut")


@st.cache_data(show_spinner=False)
def chefs_etat() -> pd.DataFrame:
    c = _read("elections_chefs_etat")
    c["debut"] = pd.to_datetime(c.debut)
    c["fin_effective"] = pd.to_datetime(c.fin).fillna(pd.Timestamp(date.today()))
    c["duree_ans"] = (c.fin_effective - c.debut).dt.days / 365.25
    c["siecle"] = np.where(c.debut.dt.year < 1900, "XIXe (1801-1899)",
                           np.where(c.debut.dt.year < 2000, "XXe (1900-1999)", "XXIe (2000-2026)"))
    c["fin_violente"] = c.fin_categorie.isin(["Mort violente", "Renversé – exil"]).astype(int)
    return c


@st.cache_data(show_spinner=False)
def historique() -> pd.DataFrame:
    return _read("elections_historique")


@st.cache_data(show_spinner=False)
def resultats_detail() -> pd.DataFrame:
    return _read("elections_resultats_detail")


@st.cache_data(show_spinner=False)
def evenements_250() -> pd.DataFrame:
    return _read("elections_250_ans")


@st.cache_data(show_spinner=False)
def criteres() -> pd.DataFrame:
    return _read("elections_criteres_faisabilite")


@st.cache_data(show_spinner=False)
def veille() -> pd.DataFrame:
    return _read("elections_actualites", LIVE)


@st.cache_data(show_spinner=False)
def mentions() -> pd.DataFrame:
    return _read("elections_mentions", LIVE)


@st.cache_data(show_spinner=False)
def screening() -> pd.DataFrame:
    return _read("elections_screening", LIVE)


def vider_cache() -> None:
    for f in (candidats, sanctions, organismes, calendrier, chefs_etat, historique, resultats_detail,
              evenements_250, criteres, veille, mentions, screening):
        f.clear()


# ---------------------------------------------------------------- score d'intégrité (méthode LCB-FT / PPE)
POIDS_AUTORITE = {"ONU": 40, "États-Unis": 25, "Union européenne": 20, "Canada": 15, "Royaume-Uni": 15}
LIB_PPE = {0: "Non PPE connue", 1: "PPE locale / parlementaire / magistrat", 2: "PPE nationale (ministre, président d'assemblée)",
           3: "PPE de premier rang (chef de l'État ou du gouvernement)"}
LIB_ALLEG = {0: "Aucune procédure publique connue", 1: "Sanction ou allégation publique",
             2: "Mise en cause formelle (instruction, rapport ONU)", 3: "Condamnation définitive"}


def _autorites(s: str) -> list[str]:
    out = []
    for a in [x.strip() for x in str(s).split(";") if x.strip()]:
        out.append("États-Unis" if a.startswith("États-Unis") else a)
    return out


def score_integrite(r: pd.Series, screening_df: pd.DataFrame | None = None) -> dict:
    """Score de risque 0-100 (plus élevé = plus de signaux de risque), décomposé.

    Il ne s'agit PAS d'un jugement de culpabilité : une sanction est une mesure administrative étrangère,
    une allégation n'est pas une condamnation.
    """
    aut = _autorites(r.sanctions_autorites)
    if screening_df is not None and not screening_df.empty:
        s = screening_df[(screening_df.candidat_id == r.id) & (screening_df.score_similarite >= 0.92)]
        for liste in s.liste.unique():
            nom = {"OFAC SDN": "États-Unis", "ONU": "ONU", "Canada LMES": "Canada"}.get(liste)
            if nom and nom not in aut:
                aut.append(nom)
    sanc = min(50, sum(POIDS_AUTORITE.get(a, 10) for a in aut))
    jud = {0: 0, 1: 10, 2: 20, 3: 30}[int(r.niveau_allegation)]
    ppe = {0: 0, 1: 4, 2: 7, 3: 10}[int(r.niveau_ppe)]
    transp = (5 if not r.site_web else 0) + (5 if not r.texte_programme else 0)
    total = sanc + jud + ppe + transp
    niveau = "Faible" if total < 20 else "Modéré" if total < 40 else "Élevé" if total < 60 else "Très élevé"
    return {"Sanctions internationales": sanc, "Procédures / allégations": jud, "Exposition politique (PPE)": ppe,
            "Transparence (site, programme)": transp, "total": total, "niveau": niveau, "autorites": aut}


COULEUR_NIVEAU = {"Faible": "#0ca30c", "Modéré": "#fab219", "Élevé": "#ec835a", "Très élevé": "#d03b3b"}


def tableau_integrite(c: pd.DataFrame) -> pd.DataFrame:
    scr = screening()
    rows = []
    for _, r in c.iterrows():
        s = score_integrite(r, scr)
        rows.append({"id": r.id, "Candidat": r.nom, "Parti": r.sigle or r.parti, **{k: v for k, v in s.items() if k != "autorites"},
                     "Autorités de sanction": ", ".join(s["autorites"]) or "—"})
    return pd.DataFrame(rows).sort_values("total", ascending=False)


def eligibilite(r: pd.Series) -> list[tuple[str, str, str]]:
    """Liste de contrôle (art. 135 de la Constitution + décret électoral 2026). Statut : ok / ? / !"""
    age = r.age
    items = [
        ("Haïtien d'origine, sans autre nationalité", "?", "À vérifier par le CEP (pièces d'état civil)"),
        ("35 ans révolus", "ok" if age == age and age >= 35 else "?", f"{int(age)} ans" if age == age else "Date de naissance non publiée"),
        ("Résidence en Haïti 5 ans consécutifs", "?", r.residence or "Non communiquée"),
        ("Décharge de gestion (anciens gestionnaires de fonds publics)",
         "!" if r.exp_executif else "ok" if not (r.exp_legislatif or r.exp_local) else "?",
         "Requise : a géré des fonds publics" if r.exp_executif else "À vérifier"),
        ("Conformité fiscale (DGI) et déclaration de patrimoine (ULCC)", "?", "Pièces du dossier CEP"),
        ("Aucune sanction du Conseil de sécurité de l'ONU", "ok" if "ONU" not in str(r.sanctions_autorites) else "!",
         "Aucune sanction ONU identifiée" if "ONU" not in str(r.sanctions_autorites) else "Sanction ONU"),
        ("Sanctions étrangères (non éliminatoires depuis le décret du 6 oct. 2026)",
         "!" if r.sanctions_autorites else "ok", r.sanctions_autorites or "Aucune identifiée"),
        ("Aucune condamnation pour fraude", "ok" if r.niveau_allegation < 3 else "!", LIB_ALLEG[int(r.niveau_allegation)]),
    ]
    return items


# ---------------------------------------------------------------- faisabilité des programmes
def _norm(t: str) -> str:
    t = unicodedata.normalize("NFKC", str(t or "")).lower()
    return re.sub(r"\s+", " ", t)


PROMESSES_IRREALISTES = [r"gratuit(e|s)? pour tous", r"en \d{1,3} jours", r"z[ée]ro (gang|corruption|chômage|faim)",
                         r"éradiquer (totalement|complètement)", r"(dès|en) (la|une) première année.{0,40}(tous|toutes|totalement)",
                         r"\b100 ?% des\b", r"emploi pour tous", r"fin (de la|des) (faim|pauvreté|insécurité) en"]
FINANCEMENT = ["financé par", "financement", "recettes", "budget", "fiscal", "dgi", "douane", "bailleurs", "ppp",
               "partenariat public-privé", "emprunt", "obligations diaspora", "fonds", "réallocation", "économies"]


def analyser_programme(texte: str, crit: pd.DataFrame | None = None) -> dict:
    """Score de faisabilité /100 d'un programme au regard de la situation d'Haïti.

    Méthode transparente (pas de boîte noire) :
    - couverture de chaque critère : mots-clés pondérés, saturation (1 - e^-n/3) ;
    - modulation par la précision (chiffres, échéances) et le financement explicite ;
    - pénalité pour promesses irréalistes au vu des contraintes (recettes ≈ 5 % du PIB, insécurité…).
    """
    crit = crit if crit is not None else criteres()
    t = _norm(texte)
    if len(t) < 200:
        return {"evaluable": False, "total": np.nan, "details": pd.DataFrame(), "remarques": ["Texte trop court (< 200 caractères)."]}
    nb_mots = max(1, len(t.split()))
    chiffres = len(re.findall(r"\b\d+[\d\s.,]*\s?(%|millions?|milliards?|gourdes|htg|usd|dollars|km|mw|écoles|policiers)", t))
    echeances = len(re.findall(r"\b(20[2-3]\d|d'ici|en \d+ ans|par an|chaque année|trimestre|semestre)\b", t))
    financement = sum(t.count(m) for m in FINANCEMENT)
    irreal = [p for p in PROMESSES_IRREALISTES if re.search(p, t)]
    precision = min(1.0, (chiffres + echeances) / max(6, nb_mots / 120))
    fin = min(1.0, financement / 5)
    rows, total = [], 0.0
    for c in crit.itertuples():
        mots = [m.strip() for m in str(c.mots_cles).split(",") if m.strip()]
        n = sum(len(re.findall(rf"(?<![a-zà-ÿ]){re.escape(m)}", t)) for m in mots)
        couverture = 1 - np.exp(-n / 3)
        if c.critere.startswith("Financement"):
            note = 0.35 * couverture + 0.65 * fin
        elif c.critere.startswith("Précision"):
            note = 0.3 * couverture + 0.7 * precision
        elif c.critere.startswith("Réalisme"):
            note = max(0.0, 0.5 + 0.5 * couverture - 0.25 * len(irreal))
        else:
            note = couverture * (0.75 + 0.25 * precision)
        pts = round(float(c.poids) * note, 1)
        total += pts
        rows.append({"Critère": c.critere, "Poids": int(c.poids), "Occurrences": n, "Note (0-1)": round(note, 2),
                     "Points": pts, "Contrainte Haïti": c.contrainte_haiti})
    penalite = min(15, 5 * len(irreal))
    total = max(0.0, min(100.0, total - penalite))
    rem = []
    if chiffres < 3:
        rem.append("Peu de mesures chiffrées : la faisabilité est difficile à vérifier.")
    if financement == 0:
        rem.append("Aucune source de financement explicite, alors que les recettes publiques sont ≈ 5 % du PIB.")
    if irreal:
        rem.append(f"{len(irreal)} promesse(s) jugée(s) irréaliste(s) dans un mandat de 5 ans (−{penalite} pts).")
    faibles = [r["Critère"] for r in rows if r["Note (0-1)"] < 0.25]
    if faibles:
        rem.append("Angles morts : " + ", ".join(faibles) + ".")
    return {"evaluable": True, "total": round(total, 1), "details": pd.DataFrame(rows), "remarques": rem,
            "indicateurs": {"mesures chiffrées": chiffres, "échéances": echeances, "mentions de financement": financement,
                            "mots": nb_mots}}


def niveau_faisabilite(score: float) -> str:
    if score != score:
        return "Non évaluable"
    return "Solide" if score >= 70 else "Plausible" if score >= 50 else "Fragile" if score >= 30 else "Peu crédible"


EXEMPLE_PROGRAMME = """EXEMPLE FICTIF — programme d'un candidat imaginaire, pour tester l'outil.
Sécurité : porter les effectifs de la PNH de 15 000 à 22 000 policiers d'ici 2030 (1 400 recrues par an), en coordination avec
la Force de répression des gangs ; créer 4 tribunaux spécialisés contre le kidnapping et le blanchiment ; programme DDR pour les
mineurs enrôlés. Budget : 180 millions USD par an, financé par une hausse des recettes douanières (numérisation de la douane,
+1,5 % du PIB en 3 ans), la réallocation de 10 % des dépenses de fonctionnement et un fonds des bailleurs.
Institutions : élections locales en 2028, décentralisation budgétaire de 15 % vers les communes, publication trimestrielle des
dépenses publiques, renforcement de l'ULCC, de l'UCREF et de la CSCCA.
Économie : 300 MW d'électricité solaire d'ici 2031 en partenariat public-privé, réhabilitation de 600 km de routes nationales,
crédit agricole pour 50 000 exploitations dans l'Artibonite, le Nord et le Sud ; obligations diaspora de 200 millions USD.
Social : cantines scolaires pour 1 million d'enfants, soins de santé primaire dans les 10 départements, programme d'urgence
alimentaire ciblant les zones en phase IPC 4. Indicateurs de suivi publiés chaque semestre."""


# ---------------------------------------------------------------- 250 ans de vie politique
def stats_chefs(c: pd.DataFrame) -> dict:
    c = c[c.ordre > 0]
    return {"nb": len(c), "duree_moy": c.duree_ans.mean(), "duree_med": c.duree_ans.median(),
            "fin_mandat": int((c.fin_categorie == "Fin de mandat").sum()),
            "violentes": int((c.fin_categorie == "Mort violente").sum()),
            "renverses": int(c.fin_categorie.str.startswith("Renversé").sum())}


def croissance_par_dirigeant(chefs: pd.DataFrame, pib: pd.DataFrame) -> pd.DataFrame:
    """Croissance annuelle moyenne du PIB/hab. réel (Banque mondiale, USD constants) pendant chaque exercice (≥ 1 an)."""
    if pib.empty:
        return pd.DataFrame()
    s = pib.set_index("annee").valeur
    rows = []
    for r in chefs.itertuples():
        a0, a1 = r.debut.year, r.fin_effective.year
        if a1 - a0 < 1 or a0 < s.index.min() or a0 > s.index.max():
            continue
        a1 = min(a1, int(s.index.max()))
        if a0 not in s or a1 not in s or a1 <= a0:
            continue
        g = (s[a1] / s[a0]) ** (1 / (a1 - a0)) - 1
        rows.append({"Dirigeant": r.nom, "Début": a0, "Fin": a1, "Croissance annuelle moy. PIB/hab. (%)": round(100 * g, 2),
                     "PIB/hab. début (USD 2015)": round(s[a0]), "PIB/hab. fin (USD 2015)": round(s[a1]),
                     "Fin de l'exercice": r.fin_categorie})
    return pd.DataFrame(rows)


def instabilite_par_decennie(c: pd.DataFrame) -> pd.DataFrame:
    c = c[c.ordre > 0].copy()
    c["decennie"] = (c.debut.dt.year // 10) * 10
    g = c.groupby("decennie").agg(chefs=("nom", "count"), renverses=("fin_violente", "sum")).reset_index()
    full = pd.DataFrame({"decennie": range(1800, 2030, 10)})
    return full.merge(g, how="left").fillna(0)
