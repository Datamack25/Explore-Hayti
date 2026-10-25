"""Modèles d'apprentissage automatique (scikit-learn), légers et explicables.

1. Typologie des communes ........ K-means sur indicateurs standardisés + ACP pour la visualisation
2. Indice de vulnérabilité ....... score composite pondéré (0-100), pondérations ajustables
3. Communes similaires ............ plus proches voisins (distance euclidienne standardisée)
4. Prévisions ..................... lissage exponentiel de Holt (tendance amortie) + intervalle par bootstrap des résidus
5. Années de rupture .............. Isolation Forest sur les variations annuelles de plusieurs indicateurs
"""
from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.cluster import KMeans
from sklearn.decomposition import PCA
from sklearn.ensemble import IsolationForest
from sklearn.metrics import silhouette_score
from sklearn.neighbors import NearestNeighbors
from sklearn.preprocessing import StandardScaler

VARIABLES_COMMUNES = {
    "densite_hab_km2": "Densité (hab/km²)",
    "part_enfants_pct": "Part d'enfants (%)",
    "ratio_hommes_femmes": "Hommes pour 100 femmes",
    "part_urbaine_localites_pct": "Part de localités urbaines (%)",
    "nb_localites": "Nombre de localités",
    "population": "Population",
}


def _matrice(df: pd.DataFrame, cols: list[str]) -> np.ndarray:
    X = df[cols].copy()
    for c in ("densite_hab_km2", "population", "nb_localites"):
        if c in X:
            X[c] = np.log1p(X[c])  # variables très asymétriques
    X = X.fillna(X.median())
    return StandardScaler().fit_transform(X)


def nommer_groupes(out: pd.DataFrame, cols: list[str]) -> dict[int, str]:
    """Donne un nom lisible à chaque groupe d'après son profil médian (densité, jeunesse, masculinité, taille)."""
    ref = out[cols].median()
    prof = out.groupby("groupe_id")[cols].median()
    noms: dict[int, str] = {}
    for g, r in prof.iterrows():
        if "densite_hab_km2" in cols:
            d = r["densite_hab_km2"]
            base = ("Urbain dense" if d > 3000 else "Urbain / périurbain" if d > 800
                    else "Bourgs et campagnes" if d > 300 else "Rural dispersé")
        elif "part_urbaine_localites_pct" in cols:
            base = "Plutôt urbain" if r["part_urbaine_localites_pct"] > ref["part_urbaine_localites_pct"] else "Plutôt rural"
        else:
            base = "Groupe"
        traits = []
        for c, hi, lo in (("part_enfants_pct", "jeune", "moins jeune"), ("ratio_hommes_femmes", "masculin", "féminisé"),
                          ("population", "très peuplé", "peu peuplé"),
                          ("part_urbaine_localites_pct", "habitat groupé autour du bourg", None),
                          ("nb_localites", "nombreuses localités", "peu de localités")):
            sd = out[c].std() if c in cols else 0
            if c in cols and sd:
                z = (r[c] - ref[c]) / sd
                lab = hi if z > 0 else lo
                if lab == "habitat groupé autour du bourg" and base.startswith("Urbain"):
                    continue  # redondant
                if abs(z) > 0.3 and lab:
                    traits.append((abs(z), lab))
        traits.sort(reverse=True)
        noms[g] = (base, [t for _, t in traits])
    final: dict[int, str] = {}
    for g, (base, tr) in noms.items():
        n = base + (" · " + tr[0] if tr else "")
        doublon = sum(1 for b2, t2 in noms.values() if b2 + (" · " + t2[0] if t2 else "") == n) > 1
        if doublon and len(tr) > 1:
            n += ", " + tr[1]
        final[g] = n
    vus: dict[str, int] = {}
    for g in sorted(final):
        vus[final[g]] = vus.get(final[g], 0) + 1
        if vus[final[g]] > 1:
            final[g] = f"{final[g]} ({vus[final[g]]})"
    return final


def typologie(df: pd.DataFrame, cols: list[str], k: int = 4, seed: int = 42) -> tuple[pd.DataFrame, dict]:
    X = _matrice(df, cols)
    km = KMeans(n_clusters=k, n_init=20, random_state=seed).fit(X)
    pca = PCA(n_components=2, random_state=seed).fit(X)
    xy = pca.transform(X)
    out = df.copy()
    out["groupe_id"] = km.labels_
    out["acp1"], out["acp2"] = xy[:, 0], xy[:, 1]
    # nommer les groupes d'après leur profil moyen
    out["groupe"] = out["groupe_id"].map(nommer_groupes(out, cols))
    infos = {
        "silhouette": float(silhouette_score(X, km.labels_)) if k > 1 else float("nan"),
        "variance_acp": pca.explained_variance_ratio_.tolist(),
        "profils": out.groupby("groupe")[cols].median().round(1),
        "taille": out.groupby("groupe").size(),
    }
    return out, infos


def choisir_k(df: pd.DataFrame, cols: list[str], kmax: int = 8) -> pd.DataFrame:
    X = _matrice(df, cols)
    rows = []
    for k in range(2, kmax + 1):
        km = KMeans(n_clusters=k, n_init=10, random_state=0).fit(X)
        rows.append({"k": k, "silhouette": silhouette_score(X, km.labels_), "inertie": km.inertia_})
    return pd.DataFrame(rows)


def indice_vulnerabilite(df: pd.DataFrame, poids: dict[str, float]) -> pd.DataFrame:
    """Score 0-100 : plus il est élevé, plus la commune cumule de fragilités relatives.

    poids : {colonne: poids} — un poids négatif signifie « plus la valeur est haute, moins on est vulnérable ».
    Chaque variable est ramenée en rang centile (robuste aux valeurs extrêmes).
    """
    out = df.copy()
    total = sum(abs(w) for w in poids.values()) or 1
    score = np.zeros(len(out))
    for col, w in poids.items():
        r = out[col].rank(pct=True).fillna(0.5).to_numpy()
        score += (r if w > 0 else 1 - r) * abs(w)
    out["indice_vulnerabilite"] = (100 * score / total).round(1)
    out["rang_vulnerabilite"] = out["indice_vulnerabilite"].rank(ascending=False, method="min").astype(int)
    return out


def communes_similaires(df: pd.DataFrame, cols: list[str], pcode: str, n: int = 5) -> pd.DataFrame:
    X = _matrice(df, cols)
    nn = NearestNeighbors(n_neighbors=n + 1).fit(X)
    i = int(np.where(df.adm2_pcode.to_numpy() == pcode)[0][0])
    dist, idx = nn.kneighbors(X[i:i + 1])
    res = df.iloc[idx[0][1:]].copy()
    res["distance"] = dist[0][1:].round(2)
    return res


def holt(y: np.ndarray, horizon: int, alpha: float, beta: float, phi: float = 0.9) -> tuple[np.ndarray, np.ndarray]:
    """Lissage de Holt à tendance amortie. Renvoie (ajustement, prévision)."""
    level, trend = y[0], (y[1] - y[0]) if len(y) > 1 else 0.0
    fitted = [y[0]]
    for t in range(1, len(y)):
        prev_level = level
        level = alpha * y[t] + (1 - alpha) * (level + phi * trend)
        trend = beta * (level - prev_level) + (1 - beta) * phi * trend
        fitted.append(level + phi * trend)
    fc, damp = [], 0.0
    for h in range(1, horizon + 1):
        damp += phi ** h
        fc.append(level + damp * trend)
    return np.array(fitted), np.array(fc)


def prevoir(s: pd.DataFrame, horizon: int = 8, n_boot: int = 300, seed: int = 0) -> tuple[pd.DataFrame, dict]:
    """Prévision avec choix automatique des paramètres (erreur de prévision à 1 an minimale)."""
    s = s.dropna(subset=["valeur"]).sort_values("annee")
    y = s.valeur.to_numpy(dtype=float)
    best = None
    for a in np.linspace(0.1, 0.9, 9):
        for b in np.linspace(0.05, 0.5, 6):
            for phi in (0.8, 0.9, 0.98):
                fit, _ = holt(y, 1, a, b, phi)
                err = np.mean((y[1:] - fit[:-1]) ** 2)
                if best is None or err < best[0]:
                    best = (err, a, b, phi)
    _, a, b, phi = best
    fit, fc = holt(y, horizon, a, b, phi)
    resid = y[1:] - fit[:-1]
    rng = np.random.default_rng(seed)
    sims = np.empty((n_boot, horizon))
    for i in range(n_boot):
        noise = rng.choice(resid, size=horizon, replace=True).cumsum() * 0.7
        sims[i] = fc + noise
    last = int(s.annee.max())
    out = pd.DataFrame({"annee": np.arange(last + 1, last + 1 + horizon), "prevision": fc,
                        "bas": np.percentile(sims, 10, axis=0), "haut": np.percentile(sims, 90, axis=0)})
    rmse = float(np.sqrt(np.mean(resid[-10:] ** 2))) if len(resid) else float("nan")
    return out, {"alpha": round(a, 2), "beta": round(b, 2), "phi": phi, "rmse_10_dernieres_annees": rmse}


def annees_de_rupture(wide: pd.DataFrame, contamination: float = 0.1) -> pd.DataFrame:
    """wide : index = année, colonnes = indicateurs. Détecte les années atypiques sur les variations."""
    chg = wide.sort_index().pct_change(fill_method=None).replace([np.inf, -np.inf], np.nan)
    chg = chg.dropna(axis=1, thresh=int(0.7 * len(chg))).dropna(axis=0, thresh=max(2, int(0.6 * chg.shape[1])))
    chg = chg.fillna(chg.median())
    X = StandardScaler().fit_transform(chg)
    iso = IsolationForest(contamination=contamination, random_state=0, n_estimators=300).fit(X)
    out = pd.DataFrame({"annee": chg.index, "score_anomalie": -iso.score_samples(X), "atypique": iso.predict(X) == -1})
    # indicateur qui contribue le plus (plus grand écart standardisé)
    z = pd.DataFrame(X, index=chg.index, columns=chg.columns)
    out["indicateur_principal"] = z.abs().idxmax(axis=1).to_numpy()
    out["variation_principale_pct"] = [100 * chg.loc[a, c] for a, c in zip(out.annee, out.indicateur_principal)]
    return out.sort_values("score_anomalie", ascending=False)
