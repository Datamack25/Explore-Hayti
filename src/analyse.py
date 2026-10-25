"""Générateur d'analyses automatiques en français (règles statistiques, sans IA externe).

Chaque fonction renvoie une liste de phrases prêtes à afficher. Une couche optionnelle
(src/assistant.py) peut reformuler avec un modèle de langage si une clé API est configurée.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from src.ui import fmt


def _pct(a: float, b: float) -> float:
    return 100 * (b - a) / abs(a) if a not in (0, None) and a == a else float("nan")


def tcam(v0: float, v1: float, n: int) -> float:
    """Taux de croissance annuel moyen."""
    if v0 is None or v0 <= 0 or v1 <= 0 or n <= 0:
        return float("nan")
    return 100 * ((v1 / v0) ** (1 / n) - 1)


def analyser_serie(s: pd.DataFrame, libelle: str, unite: str = "") -> list[str]:
    s = s.dropna(subset=["valeur"]).sort_values("annee")
    if len(s) < 3:
        return [f"Pas assez de points pour analyser « {libelle} »."]
    a0, a1 = int(s.annee.iloc[0]), int(s.annee.iloc[-1])
    v0, v1 = s.valeur.iloc[0], s.valeur.iloc[-1]
    imax, imin = s.valeur.idxmax(), s.valeur.idxmin()
    est_taux = unite.strip().startswith("%") or "%" in libelle
    pts = [f"**Dernière valeur** : {fmt(v1, 2)} {unite} en {a1} (série disponible depuis {a0}, {len(s)} observations)."]
    if est_taux:
        pts.append(f"Écart sur la période : {v1 - v0:+.1f} points ({fmt(v0, 1)} → {fmt(v1, 1)}).")
    else:
        t = tcam(v0, v1, a1 - a0)
        if t == t:
            pts.append(f"Évolution {a0}–{a1} : {_pct(v0, v1):+.0f} %, soit un taux de croissance annuel moyen de {t:+.2f} %.")
    pts.append(f"**Maximum** : {fmt(s.valeur[imax], 2)} {unite} en {int(s.annee[imax])} · "
               f"**minimum** : {fmt(s.valeur[imin], 2)} {unite} en {int(s.annee[imin])}.")
    rec = s[s.annee >= a1 - 9]
    if len(rec) >= 4:
        pente = np.polyfit(rec.annee, rec.valeur, 1)[0]
        sens = "hausse" if pente > 0 else "baisse"
        moy = rec.valeur.mean()
        pts.append(f"Tendance des 10 dernières années : **{sens}** d'environ {fmt(abs(pente), 2)} {unite} par an "
                   f"(moyenne de la décennie : {fmt(moy, 2)} {unite}).")
        vol = rec.valeur.std() / abs(moy) * 100 if moy else float("nan")
        if vol == vol and vol > 50:
            pts.append(f"Série **très volatile** sur la décennie (coefficient de variation ≈ {vol:.0f} %).")
    if len(s) >= 6:
        d = s.set_index("annee").valeur.diff()
        an_choc = int(d.abs().idxmax())
        pts.append(f"Plus forte variation annuelle : {d[an_choc]:+,.2f} {unite} en {an_choc}.".replace(",", " "))
    return pts


def analyser_commune(c: pd.Series, communes: pd.DataFrame) -> list[str]:
    n = len(communes)
    dep = communes[communes.departement == c.departement]
    rang_pop = int(communes.population.rank(ascending=False)[c.name])
    rang_dens = int(communes.densite_hab_km2.rank(ascending=False)[c.name])
    pts = [
        f"**{c.commune}** compte {fmt(c.population)} habitants (2022), soit le **{rang_pop}ᵉ rang** sur {n} communes "
        f"et {100 * c.population / dep.population.sum():.1f} % de la population du département {c.departement}.",
        f"Densité de {fmt(c.densite_hab_km2)} hab/km² ({rang_dens}ᵉ rang national) sur {fmt(c.superficie_km2, 1)} km².",
    ]
    med = communes.part_enfants_pct.median()
    comp = "au-dessus" if c.part_enfants_pct > med else "en dessous"
    pts.append(f"Les enfants représentent {c.part_enfants_pct:.1f} % de la population, {comp} de la médiane nationale ({med:.1f} %).")
    pts.append(f"Rapport de masculinité : {c.ratio_hommes_femmes:.0f} hommes pour 100 femmes.")
    pts.append(f"Le territoire compte {int(c.nb_localites)} localités recensées "
               f"(dont {int(c.nb_villes)} villes et {int(c.nb_quartiers)} quartiers).")
    if c.get("couverture_ecoles_2022", False):
        dmed = communes.loc[communes.couverture_ecoles_2022.astype(bool), "ecoles_pour_1000_enfants"].median()
        pts.append(f"{int(c.nb_ecoles)} établissements scolaires recensés en 2022 ({c.part_ecoles_publiques_pct:.0f} % publics), "
                   f"soit {c.ecoles_pour_1000_enfants:.2f} écoles pour 1 000 enfants (médiane des communes couvertes : {dmed:.2f}).")
    elif "nb_ecoles_osm" not in c:
        pts.append("La cartographie scolaire 2022 ne couvre pas cette commune : lancez la mise à jour OpenStreetMap "
                   "pour obtenir les écoles géolocalisées.")
    if "nb_ecoles_osm" in c:
        med = communes.ecoles_osm_pour_1000_enfants.median()
        pts.append(f"OpenStreetMap recense **{int(c.nb_etab_education_osm)} établissements d'enseignement** géolocalisés "
                   f"({int(c.nb_ecoles_osm)} écoles et jardins d'enfants, {int(c.nb_superieur_osm)} établissements supérieurs), "
                   f"soit {c.ecoles_osm_pour_1000_enfants:.2f} pour 1 000 enfants (médiane nationale : {med:.2f}). "
                   "La cartographie OSM est collaborative et peut être incomplète.")
    return pts


def analyser_departements(dep: pd.DataFrame) -> list[str]:
    d = dep.sort_values("population", ascending=False)
    tot = d.population.sum()
    top = d.iloc[0]
    pts = [f"Population totale estimée (2022) : **{fmt(tot)}** habitants répartis dans 10 départements.",
           f"L'**{top.departement}** concentre {100 * top.population / tot:.1f} % de la population "
           f"({fmt(top.population)} hab.) avec une densité de {fmt(top.densite_hab_km2)} hab/km².",
           f"Le département le moins peuplé est **{d.iloc[-1].departement}** ({fmt(d.iloc[-1].population)} hab.)."]
    dd = dep.sort_values("densite_hab_km2")
    pts.append(f"La densité varie de {fmt(dd.iloc[0].densite_hab_km2)} hab/km² ({dd.iloc[0].departement}) "
               f"à {fmt(dd.iloc[-1].densite_hab_km2)} hab/km² ({dd.iloc[-1].departement}).")
    e = dep.sort_values("part_enfants_pct")
    pts.append(f"Part d'enfants : de {e.iloc[0].part_enfants_pct:.1f} % ({e.iloc[0].departement}) "
               f"à {e.iloc[-1].part_enfants_pct:.1f} % ({e.iloc[-1].departement}).")
    return pts


def correlation_texte(a: pd.DataFrame, b: pd.DataFrame, la: str, lb: str) -> str:
    m = a[["annee", "valeur"]].merge(b[["annee", "valeur"]], on="annee", suffixes=("_a", "_b")).dropna()
    if len(m) < 6:
        return "Pas assez d'années communes pour mesurer un lien."
    r = m.valeur_a.corr(m.valeur_b)
    force = "très forte" if abs(r) > .8 else "forte" if abs(r) > .6 else "modérée" if abs(r) > .4 else "faible"
    sens = "positive" if r > 0 else "négative"
    return (f"Corrélation {force} et {sens} (r = {r:.2f}) entre « {la} » et « {lb} » sur {len(m)} années "
            f"({int(m.annee.min())}–{int(m.annee.max())}). Une corrélation n'indique pas une causalité.")
