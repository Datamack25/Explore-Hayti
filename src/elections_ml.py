"""Machine learning appliqué aux élections : profils de candidats (K-means + ACP), candidats proches,
facteurs d'instabilité des chefs d'État (forêt aléatoire), durée au pouvoir (Kaplan-Meier),
tendance de participation (régression + bootstrap), similarité des programmes (TF-IDF).

Petits jeux de données : les résultats sont exploratoires et toujours accompagnés de leur limite.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.cluster import KMeans
from sklearn.decomposition import PCA
from sklearn.ensemble import RandomForestClassifier
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.model_selection import StratifiedKFold, cross_val_score
from sklearn.preprocessing import StandardScaler

VARS_PROFIL = ["niveau_ppe", "exp_executif", "exp_legislatif", "exp_local", "exp_judiciaire", "risque", "notoriete"]
LIB_VARS = {"niveau_ppe": "Exposition politique", "exp_executif": "Exécutif", "exp_legislatif": "Législatif",
            "exp_local": "Élu local", "exp_judiciaire": "Justice", "risque": "Score de risque", "notoriete": "Présence médiatique"}


def matrice_profils(c: pd.DataFrame, integ: pd.DataFrame) -> pd.DataFrame:
    m = c[["id", "nom", "sigle", "niveau_ppe", "exp_executif", "exp_legislatif", "exp_local", "exp_judiciaire", "nb_articles"]].copy()
    m = m.merge(integ[["id", "total"]].rename(columns={"total": "risque"}), on="id")
    m["notoriete"] = np.log1p(m.nb_articles)
    return m


def profils(m: pd.DataFrame, k: int = 4, seed: int = 42) -> tuple[pd.DataFrame, dict, float]:
    X = StandardScaler().fit_transform(m[VARS_PROFIL].astype(float))
    k = min(k, len(m) - 1)
    km = KMeans(n_clusters=k, n_init=20, random_state=seed).fit(X)
    p = PCA(n_components=2, random_state=seed).fit(X)
    xy = p.transform(X)
    out = m.assign(groupe=km.labels_, x=xy[:, 0], y=xy[:, 1])
    # nom de chaque groupe = sa caractéristique la plus marquée (centre standardisé), sans doublon
    Z = pd.DataFrame(X, columns=VARS_PROFIL).assign(groupe=km.labels_).groupby("groupe").mean()
    lib = {"risque": "Profils à signaux de risque élevés", "exp_executif": "Anciens responsables de l'exécutif",
           "niveau_ppe": "Personnalités politiques de premier plan", "exp_legislatif": "Parlementaires",
           "exp_local": "Élus locaux", "exp_judiciaire": "Profils issus de la justice", "notoriete": "Fortes présences médiatiques"}
    noms, pris = {}, set()
    for g in Z.max(axis=1).sort_values(ascending=False).index:
        z = Z.loc[g]
        if z.max() < 0.3:
            n = "Nouveaux venus / profils peu documentés"
        else:
            n = next((lib[v] for v in z.sort_values(ascending=False).index if lib[v] not in pris), "Autres profils")
        while n in pris:
            n += " (2)"
        pris.add(n)
        noms[g] = n
    out["profil"] = out.groupe.map(noms)
    return out, noms, float(p.explained_variance_ratio_.sum())


def proches(m: pd.DataFrame, cid: str, n: int = 3) -> pd.DataFrame:
    X = StandardScaler().fit_transform(m[VARS_PROFIL].astype(float))
    i = m.index[m.id == cid][0]
    pos = list(m.index).index(i)
    sim = cosine_similarity(X[pos:pos + 1], X)[0]
    d = m.assign(similarite=sim)
    return d[d.id != cid].sort_values("similarite", ascending=False).head(n)


def facteurs_instabilite(chefs: pd.DataFrame, seed: int = 0) -> dict:
    """Quels facteurs sont associés à une fin de pouvoir violente ou à un renversement ?"""
    d = chefs[(chefs.ordre > 0) & (chefs.fin_categorie != "En fonction")].copy()
    acc = d.mode_accession.str.replace(r" sous occupation", "", regex=True)
    acc = acc.where(acc.isin(acc.value_counts()[lambda s: s >= 3].index), "Autre")
    X = pd.concat([pd.get_dummies(acc, prefix="Accès"), pd.get_dummies(d.regime, prefix="Régime"),
                   pd.get_dummies(d.siecle, prefix="Siècle")], axis=1).astype(int)
    y = d.fin_violente.values
    rf = RandomForestClassifier(n_estimators=400, max_depth=4, random_state=seed, class_weight="balanced")
    cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=seed)
    scores = cross_val_score(rf, X, y, cv=cv, scoring="balanced_accuracy")
    rf.fit(X, y)
    imp = (pd.DataFrame({"Facteur": [x.replace("_", " : ", 1) for x in X.columns], "Importance": rf.feature_importances_})
           .sort_values("Importance", ascending=False).head(10))
    taux = (d.assign(acces=acc).groupby("acces").fin_violente.agg(["mean", "count"])
            .rename(columns={"mean": "Taux de fin violente ou renversement", "count": "Chefs d'État"}).sort_values(
                "Taux de fin violente ou renversement", ascending=False).reset_index().rename(columns={"acces": "Mode d'accession"}))
    return {"importances": imp, "precision": float(scores.mean()), "ecart": float(scores.std()), "n": len(d),
            "base": float(max(y.mean(), 1 - y.mean())), "taux": taux}


def kaplan_meier(chefs: pd.DataFrame, groupe: str = "siecle") -> pd.DataFrame:
    """Probabilité de rester au pouvoir au-delà de t années (les dirigeants en fonction sont censurés)."""
    d = chefs[chefs.ordre > 0]
    rows = []
    for g, s in d.groupby(groupe):
        t = s.duree_ans.values
        e = (s.fin_categorie != "En fonction").values.astype(int)
        surv, temps = 1.0, [0.0]
        survs = [1.0]
        for u in np.sort(np.unique(t[e == 1])):
            n_risque = (t >= u).sum()
            n_evt = ((t == u) & (e == 1)).sum()
            surv *= 1 - n_evt / n_risque
            temps.append(u)
            survs.append(surv)
        rows += [{"groupe": g, "annees": a, "survie": b} for a, b in zip(temps, survs)]
    return pd.DataFrame(rows)


def tendance_participation(hist: pd.DataFrame, annee_cible: int = 2027, n_boot: int = 2000, seed: int = 0) -> dict:
    d = hist[(hist.annee >= 1990) & hist.participation_pct.notna() & ~hist.type.str.contains("annulée|prévue", case=False)]
    x, y = d.annee.values.astype(float), d.participation_pct.values.astype(float)
    a, b = np.polyfit(x, y, 1)
    rng = np.random.default_rng(seed)
    preds = []
    for _ in range(n_boot):
        i = rng.integers(0, len(x), len(x))
        if len(np.unique(x[i])) < 2:
            continue
        aa, bb = np.polyfit(x[i], y[i], 1)
        preds.append(aa * annee_cible + bb)
    preds = np.clip(np.array(preds), 3, 95)
    return {"donnees": d[["annee", "participation_pct", "vainqueur"]], "pente": a, "prevision": float(np.clip(a * annee_cible + b, 3, 95)),
            "bas": float(np.percentile(preds, 10)), "haut": float(np.percentile(preds, 90)), "x": x, "y": y, "a": a, "b": b}


def similarite_programmes(c: pd.DataFrame) -> pd.DataFrame:
    d = c[c.texte_programme.str.len() > 200]
    if len(d) < 2:
        return pd.DataFrame()
    v = TfidfVectorizer(max_features=3000, ngram_range=(1, 2), sublinear_tf=True).fit_transform(d.texte_programme)
    s = cosine_similarity(v)
    return pd.DataFrame(s, index=d.nom, columns=d.nom).round(2)
