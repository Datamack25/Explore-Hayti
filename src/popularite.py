"""Popularité en ligne des candidats et probabilité d'élection (simulation Monte-Carlo du scrutin à deux tours).

Signaux (collectés par scripts/update_popularite.py et scripts/update_elections.py) :
- presse : articles des 60 derniers jours (Google Actualités + médias haïtiens) et leur tonalité ;
- GDELT : volume mondial d'articles en ligne sur 90 jours, tonalité moyenne, dynamique sur 14 jours ;
- Wikipédia : pages vues sur 30 jours (fr, en, ht) = curiosité du public ;
- réseaux sociaux accessibles sans contrat : Reddit, Bluesky, YouTube (si une clé est fournie).

Méthode : indice de popularité = somme pondérée de z-scores (log), puis parts de « voix en ligne » par softmax, puis
10 000 tirages de Dirichlet pour simuler le 1er tour (élu si > 50 % ou 25 points d'avance) et le 2e tour.
Limite majeure : la notoriété en ligne n'est pas une intention de vote (pas de sondage publié, ≈ 40 % d'internautes,
diaspora sur-représentée en ligne mais sans vote organisé). Module en Python pur (utilisable par les scripts).
"""
from __future__ import annotations

import re
import unicodedata
from collections import Counter

import numpy as np
import pandas as pd

from src.utils import CURATED, LIVE

F_SIGNAUX = LIVE / "elections_popularite_signaux.csv"
F_HISTO = LIVE / "elections_popularite_historique.csv"

SIGNAUX = {  # colonne : (libellé, poids par défaut, transformation log)
    "presse_60j": ("Presse (60 jours)", 0.25, True),
    "gdelt_90j": ("Médias en ligne mondiaux (GDELT, 90 j)", 0.20, True),
    "wiki_30j": ("Curiosité du public (Wikipédia, 30 j)", 0.20, True),
    "social_30j": ("Réseaux sociaux (Reddit, Bluesky, YouTube)", 0.15, True),
    "tonalite": ("Tonalité des contenus", 0.10, False),
    "dynamique": ("Dynamique (14 derniers jours)", 0.10, True),
}


def charger_signaux() -> pd.DataFrame:
    c = pd.read_csv(CURATED / "elections_candidats.csv", dtype=str).fillna("")[["id", "nom", "sigle", "sanctions_autorites"]]
    s = pd.read_csv(F_SIGNAUX) if F_SIGNAUX.exists() else pd.DataFrame(columns=["candidat_id"])
    m = LIVE / "elections_mentions.csv"
    men = pd.read_csv(m) if m.exists() else pd.DataFrame(columns=["candidat_id", "nb_articles", "tonalite_moy"])
    d = c.merge(s, left_on="id", right_on="candidat_id", how="left").drop(columns="candidat_id", errors="ignore")
    d = d.merge(men[["candidat_id", "nb_articles", "tonalite_moy"]], left_on="id", right_on="candidat_id", how="left").drop(
        columns="candidat_id", errors="ignore")
    d["presse_60j"] = pd.to_numeric(d.nb_articles, errors="coerce").fillna(0)
    for col in ("gdelt_90j", "gdelt_ton", "gdelt_14j", "gdelt_14j_avant", "wiki_30j", "reddit_30j", "bluesky_30j", "youtube_30j"):
        d[col] = pd.to_numeric(d[col], errors="coerce").fillna(0) if col in d else 0.0
    d["social_30j"] = d.reddit_30j + d.bluesky_30j + d.youtube_30j
    # tonalité : moyenne presse (-1..1) et GDELT (≈ -10..10, ramenée à -1..1)
    t_presse = pd.to_numeric(d.tonalite_moy, errors="coerce").fillna(0)
    d["tonalite"] = (0.5 * t_presse + 0.5 * (d.gdelt_ton / 10).clip(-1, 1)).round(3)
    d["dynamique"] = (d.gdelt_14j + 1) / (d.gdelt_14j_avant + 1)
    return d


def a_des_donnees(d: pd.DataFrame) -> bool:
    return bool((d[["presse_60j", "gdelt_90j", "wiki_30j", "social_30j"]].sum(axis=1) > 0).sum() >= 2)


def _z(x: pd.Series) -> pd.Series:
    sd = x.std(ddof=0)
    return (x - x.mean()) / sd if sd > 0 else x * 0


def indice(d: pd.DataFrame, poids: dict | None = None) -> pd.DataFrame:
    poids = poids or {k: v[1] for k, v in SIGNAUX.items()}
    tot = sum(poids.values()) or 1
    out = d.copy()
    out["indice"] = 0.0
    for k, (lib, _, log) in SIGNAUX.items():
        x = np.log1p(out[k].clip(lower=0)) if log else out[k]
        out[f"z_{k}"] = _z(x)
        out[f"contrib_{k}"] = poids[k] / tot * out[f"z_{k}"]
        out["indice"] += out[f"contrib_{k}"]
    # indice affiché sur 0-100
    lo, hi = out.indice.min(), out.indice.max()
    out["indice_100"] = (100 * (out.indice - lo) / (hi - lo)).round(0) if hi > lo else 50.0
    return out


def simuler(d: pd.DataFrame, temperature: float = 0.6, concentration: float = 40, n: int = 10000,
            seed: int = 0) -> pd.DataFrame:
    """Probabilités d'être élu et de se qualifier pour le 2e tour."""
    rng = np.random.default_rng(seed)
    sc = d.indice.values / max(temperature, 0.05)
    parts = np.exp(sc - sc.max())
    parts /= parts.sum()
    tirages = rng.dirichlet(np.maximum(parts * concentration, 1e-3), size=n)
    k = len(parts)
    elu, qualif = np.zeros(k), np.zeros(k)
    ordre = np.argsort(-tirages, axis=1)
    a, b = ordre[:, 0], ordre[:, 1]
    va, vb = tirages[np.arange(n), a], tirages[np.arange(n), b]
    direct = (va > 0.5) | (va - vb >= 0.25)
    np.add.at(elu, a[direct], 1)
    r = ~direct
    np.add.at(qualif, a[r], 1)
    np.add.at(qualif, b[r], 1)
    # 2e tour : report des voix incertain (bruit de 8 points autour du rapport de forces)
    pa = va[r] / (va[r] + vb[r]) + rng.normal(0, 0.08, r.sum())
    gagnant = np.where(pa > 0.5, a[r], b[r])
    np.add.at(elu, gagnant, 1)
    out = d.copy()
    out["part_1er_tour"] = (100 * tirages.mean(axis=0)).round(1)
    out["part_bas"] = (100 * np.percentile(tirages, 10, axis=0)).round(1)
    out["part_haut"] = (100 * np.percentile(tirages, 90, axis=0)).round(1)
    out["proba_qualif_2e_tour"] = (100 * qualif / n).round(1)
    out["proba_elu"] = (100 * elu / n).round(1)
    out["proba_victoire_1er_tour"] = (100 * np.bincount(a[direct], minlength=k) / n).round(1)
    return out.sort_values("proba_elu", ascending=False)


# ---------------------------------------------------------------- explications
MOTS_VIDES = set("""le la les de des du un une et en au aux a à pour par sur dans avec son sa ses ce cet cette qui que quoi est sont
ont été être plus pas ne se il elle ils elles leur leurs nous vous haiti haïti ayiti hayti the of and to in for on is with at by from as
an be has have will his her its after says said new news contre entre selon après avant lors fait faire veut deux""".split())


def _tokens(t: str) -> list[str]:
    t = unicodedata.normalize("NFKC", str(t).lower())
    return [w for w in re.findall(r"[a-zàâçéèêëîïôûùüÿœ'-]{4,}", t) if w not in MOTS_VIDES]


def expliquer(r: pd.Series, d: pd.DataFrame, articles: pd.DataFrame) -> dict:
    """Pourquoi ce candidat est (ou n'est pas) populaire en ligne : moteurs, thèmes, mots, tonalité, dynamique."""
    contrib = {SIGNAUX[k][0]: r[f"contrib_{k}"] for k in SIGNAUX}
    forts = [k for k, v in sorted(contrib.items(), key=lambda x: -x[1]) if v > 0.05][:3]
    faibles = [k for k, v in sorted(contrib.items(), key=lambda x: x[1]) if v < -0.05][:2]
    rang = int((d.indice > r.indice).sum()) + 1
    a = articles[articles.candidats.fillna("").str.contains(r.id, regex=False)] if not articles.empty else pd.DataFrame()
    themes, mots, part_neg, part_sanc, sources = [], [], 0.0, 0.0, []
    if len(a):
        themes = [f"{t} ({n})" for t, n in a.theme.value_counts().head(3).items()]
        noms = set(_tokens(r.nom))
        cnt = Counter(w for t in a.titre for w in _tokens(t) if w not in noms)
        mots = [w for w, _ in cnt.most_common(8)]
        part_neg = float((a.tonalite == "Négatif").mean())
        part_sanc = float(a.sanction_citee.astype(str).str.lower().eq("true").mean()) if "sanction_citee" in a else 0.0
        sources = list(a.source.value_counts().head(3).index)
    phrases = []
    niveau = "parmi les plus visibles" if rang <= 3 else "dans la moyenne" if rang <= len(d) / 2 else "peu visible en ligne"
    phrases.append(f"{r.nom} est {rang}ᵉ sur {len(d)} à l'indice de popularité en ligne ({r.indice_100:.0f}/100) : {niveau}.")
    if forts:
        phrases.append("Ce qui porte sa visibilité : " + ", ".join(forts).lower() + ".")
    if faibles:
        phrases.append("Ce qui la freine : " + ", ".join(faibles).lower() + ".")
    if r.presse_60j:
        phrases.append(f"{int(r.presse_60j)} articles de presse en 60 jours" + (f", surtout sur : {', '.join(themes)}" if themes else "") + ".")
    if r.wiki_30j:
        phrases.append(f"{int(r.wiki_30j):,} consultations de sa page Wikipédia en 30 jours".replace(",", " ") + " (curiosité du public).")
    if r.dynamique >= 1.5:
        phrases.append(f"Dynamique en hausse : {r.dynamique:.1f} fois plus de couverture sur les 14 derniers jours que sur les 14 précédents.")
    elif r.dynamique <= 0.67 and r.gdelt_14j_avant > 0:
        phrases.append("Couverture en baisse sur les 14 derniers jours.")
    if part_neg >= 0.4:
        phrases.append(f"Attention : {100 * part_neg:.0f} % des articles ont une tonalité négative — une forte notoriété peut refléter "
                       "une controverse plutôt qu'un soutien.")
    if part_sanc >= 0.2 or r.sanctions_autorites:
        phrases.append("Une partie de la couverture porte sur les sanctions internationales, ce qui gonfle la notoriété sans "
                       "indiquer d'adhésion.")
    if mots:
        phrases.append("Mots les plus associés dans les titres : " + ", ".join(mots) + ".")
    if sources:
        phrases.append("Principales sources : " + ", ".join(sources) + ".")
    return {"texte": phrases, "forts": forts, "faibles": faibles, "themes": themes, "mots": mots, "articles": a}


def enregistrer_historique(sim: pd.DataFrame, date_str: str) -> None:
    h = sim[["id", "nom", "indice_100", "part_1er_tour", "proba_qualif_2e_tour", "proba_elu"]].assign(date=date_str)
    if F_HISTO.exists():
        old = pd.read_csv(F_HISTO)
        h = pd.concat([old[old.date != date_str], h], ignore_index=True)
    h.to_csv(F_HISTO, index=False)
