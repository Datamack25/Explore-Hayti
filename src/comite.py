"""Comité des sages : 10 personnages fictifs (noms modifiables) qui analysent les plans et les actualités.

Méthode (inspirée de Delphi) : chaque sage évalue seul le texte avec sa grille de critères ; le leader fait la synthèse,
sépare consensus et désaccords, tranche et garde l'avis minoritaire. Le classement des actualités par sage utilise
un modèle TF-IDF + similarité cosinus (scikit-learn). Si un modèle de langage est configuré (src/assistant.py), chaque
sage peut aussi rédiger un avis libre à partir des mêmes éléments.
"""
from __future__ import annotations

import re
import unicodedata

import numpy as np
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from src.utils import CURATED, LIVE

LEADER = "S10"


def sages() -> pd.DataFrame:
    return pd.read_csv(CURATED / "comite_sages.csv")


def criteres() -> pd.DataFrame:
    return pd.read_csv(CURATED / "comite_criteres.csv")


def norm(t: str) -> str:
    t = unicodedata.normalize("NFKD", str(t)).encode("ascii", "ignore").decode().lower()
    return re.sub(r"[’']", " ", t)


def _contient(texte_norm: str, mots: str) -> list[str]:
    trouves = []
    for m in str(mots).split(";"):
        m2 = norm(m).strip()
        if m2 and re.search(r"(?<![a-z])" + re.escape(m2), texte_norm):
            trouves.append(m.strip())
    return trouves


def _profil(s) -> str:
    return " ".join([str(s.domaine), str(s.mission), str(s.mots_cles).replace(";", " ")])


# ------------------------------------------------------------------ analyse d'un plan
def analyser(texte: str, S: pd.DataFrame | None = None, C: pd.DataFrame | None = None, frontiere: bool = False) -> dict:
    """Évalue un texte de plan. `frontiere=True` ajoute les critères propres à la frontière."""
    S = sages() if S is None else S
    C = criteres() if C is None else C
    if "portee" in C and not frontiere:
        C = C[C.portee != "frontiere"]
    tn = norm(texte)
    vec = TfidfVectorizer(preprocessor=norm, ngram_range=(1, 2), min_df=1)
    M = vec.fit_transform([_profil(s) for s in S.itertuples()] + [texte])
    pert = cosine_similarity(M[-1], M[:-1]).ravel()
    avis = []
    for i, s in enumerate(S.itertuples()):
        cs = C[C.sage_id == s.id]
        couverts, manques = [], []
        for c in cs.itertuples():
            (couverts if _contient(tn, c.mots_detection) else manques).append(c)
        tot = sum(c.importance for c in cs.itertuples()) or 1
        score = round(10 * sum(c.importance for c in couverts) / tot, 1)
        verdict = "Favorable" if score >= 7.5 else "Favorable sous conditions" if score >= 5 else "Réservé"
        avis.append({"id": s.id, "nom": s.nom, "titre": s.titre, "domaine": s.domaine, "score": score, "verdict": verdict,
                     "pertinence": round(float(pert[i]) * 100, 0),
                     "forces": [c.critere for c in couverts],
                     "recommandations": [(c.critere, c.recommandation, int(c.importance)) for c in
                                         sorted(manques, key=lambda c: -c.importance)],
                     "inspiration": s.meilleures_pratiques, "poids": float(s.poids)})
    return {"avis": avis, "synthese": synthese(avis, S)}


def synthese(avis: list[dict], S: pd.DataFrame) -> dict:
    exp = [a for a in avis if a["id"] != LEADER]
    lead = next((a for a in avis if a["id"] == LEADER), None)
    w = np.array([a["poids"] for a in exp])
    sc = np.array([a["score"] for a in exp])
    moy = float((w * sc).sum() / w.sum())
    if lead:
        moy = (moy * 9 + lead["score"]) / 10
    decision = "ADOPTER" if moy >= 7 else "ADOPTER SOUS CONDITIONS" if moy >= 5 else "REVOIR LE PLAN"
    prio = sorted([(a["nom"], a["titre"], r[0], r[1], r[2]) for a in avis for r in a["recommandations"]],
                  key=lambda x: (-x[4], x[0]))
    favorables = [a["titre"] for a in exp if a["verdict"] == "Favorable"]
    reserves = [a for a in exp if a["verdict"] == "Réservé"]
    mino = [a for a in exp if abs(a["score"] - moy) >= 3]
    nom_leader = S.loc[S.id == LEADER, "nom"].iloc[0] if (S.id == LEADER).any() else "Le leader"
    texte = (f"{nom_leader} : « Note globale {moy:.1f}/10. Décision : {decision.lower()}. "
             + (f"Points forts reconnus par {', '.join(favorables)}. " if favorables else "")
             + (f"Réserves sérieuses de {', '.join(a['titre'] for a in reserves)} : on ne lance pas sans y répondre. " if reserves else "")
             + (f"Je retiens d'abord : {prio[0][3]} " if prio else "")
             + "Chaque recommandation a un responsable et une date ; nous réexaminons le plan dans 90 jours. »")
    return {"note": round(moy, 1), "decision": decision, "priorites": prio[:8], "minoritaires": mino, "texte": texte}


# ------------------------------------------------------------------ actualités (ML : TF-IDF + similarité cosinus)
def actualites() -> pd.DataFrame:
    p = LIVE / "actualites.csv"
    return pd.read_csv(p) if p.exists() else pd.DataFrame()


def router_actualites(A: pd.DataFrame, S: pd.DataFrame | None = None, C: pd.DataFrame | None = None) -> pd.DataFrame:
    S = sages() if S is None else S
    C = criteres() if C is None else C
    if A.empty:
        return A
    txt = (A.titre.fillna("") + " " + A.get("resume", pd.Series("", index=A.index)).fillna("") + " "
           + A.get("theme", pd.Series("", index=A.index)).fillna("")).tolist()
    exp = S[S.id != LEADER]
    vec = TfidfVectorizer(preprocessor=norm, analyzer="char_wb", ngram_range=(4, 5), sublinear_tf=True)
    M = vec.fit_transform([_profil(s) for s in exp.itertuples()] + txt)
    sim = cosine_similarity(M[len(exp):], M[:len(exp)])
    rows = []
    for i, r in enumerate(A.itertuples()):
        j = int(np.argmax(sim[i]))
        s = exp.iloc[j] if sim[i, j] > 0 else S[S.id == LEADER].iloc[0]
        tn = norm(txt[i])
        cs = C[C.sage_id == s.id]
        touches = [c for c in cs.itertuples() if _contient(tn, c.mots_detection)]
        c0 = touches[0] if touches else (cs.sort_values("importance", ascending=False).iloc[0] if len(cs) else None)
        second = exp.iloc[int(np.argsort(sim[i])[-2])].titre if len(exp) > 1 and sim[i].max() > 0 else ""
        rows.append({"date": r.date, "titre": r.titre, "source": getattr(r, "source", ""), "url": getattr(r, "url", ""),
                     "tonalite": getattr(r, "tonalite", ""), "sage": s.nom, "role": s.titre,
                     "pertinence_pct": round(float(sim[i].max()) * 100, 0), "deuxieme_avis": second,
                     "lecture": (f"Sujet de {str(s.domaine).lower()}"
                                 + (f" ; touche : {', '.join(c.critere.lower() for c in touches)}" if touches else "") + "."),
                     "proposition": c0.recommandation if c0 is not None else ""})
    return pd.DataFrame(rows)


def consigne_sage(s) -> str:
    return (f"Tu joues {s.nom}, {s.titre} ({s.domaine}) dans un comité des sages consultatif sur Haïti (personnage fictif). "
            f"Ta mission : {s.mission} Inspirations : {s.meilleures_pratiques}. Réponds en français, en 6 lignes maximum : "
            "1) ce qui est solide, 2) ce qui manque, 3) deux propositions concrètes et réalistes avec ressources locales. "
            "Ne donne aucune consigne de vote et n'invente aucun chiffre.")


def textes_plans() -> dict[str, str]:
    """Textes des plans de la plateforme, reconstitués à partir de leurs fichiers CSV."""
    from src import frontiere as F

    def lignes(nom):
        p = CURATED / nom
        return pd.read_csv(p).fillna("").astype(str).agg(" ; ".join, axis=1).tolist() if p.exists() else []

    m = pd.read_csv(CURATED / "plan_securite_mesures.csv").fillna("")
    return {
        "Frontière : 20 postes (Ayiti Data Hub)": F.texte_plan(),
        "Programme d'Etzer Émile – sécurité": "\n".join(m[m.source.str.contains("Etzer")].astype(str).agg(" ; ".join, axis=1)),
        "Gouvernement de transition (M. Andrésol) – sécurité": "\n".join(m[m.source.str.contains("Andrésol")].astype(str).agg(" ; ".join, axis=1)),
        "Plan de sécurité territorial (projection par département)": "\n".join(lignes("plan_securite_departements.csv")),
        "Gouvernance électronique": "\n".join(lignes("gouvernance_acteurs.csv") + lignes("gouvernance_relations.csv")),
        "Processus électoral (améliorations)": "\n".join(lignes("elections_processus.csv")),
        "Jeunes agriculteurs & diaspora": "\n".join(lignes("agri_filieres_departements.csv") + lignes("diaspora_mecanismes.csv")),
    }
