"""Chargement des données (avec cache Streamlit) et fusion base historique + données à jour."""
from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import streamlit as st

from src.indicateurs import INDICATEURS_CLES
from src.utils import CURATED, GEO, LIVE, PROCESSED


def _read(path: Path, **kw) -> pd.DataFrame:
    if not path.exists():
        return pd.DataFrame()
    return pd.read_csv(path, **kw)


@st.cache_data(show_spinner=False)
def communes() -> pd.DataFrame:
    return _read(PROCESSED / "communes.csv")


@st.cache_data(show_spinner=False)
def departements() -> pd.DataFrame:
    return _read(PROCESSED / "departements.csv")


@st.cache_data(show_spinner=False)
def sections() -> pd.DataFrame:
    return _read(PROCESSED / "sections_communales.csv")


@st.cache_data(show_spinner=False)
def localites() -> pd.DataFrame:
    return _read(PROCESSED / "localites.csv")


@st.cache_data(show_spinner=False)
def ecoles() -> pd.DataFrame:
    return _read(PROCESSED / "ecoles.csv")


@st.cache_data(show_spinner=False)
def institutions() -> pd.DataFrame:
    """Annuaire : liste de base + institutions OpenStreetMap (si la mise à jour a tourné)."""
    base = _read(PROCESSED / "institutions.csv")
    edu = etablissements_education_osm()
    if not edu.empty:
        edu = edu[edu.type != "Bâtiment scolaire"].assign(
            categorie=lambda d: d.type.map(lambda t: "Université / Enseignement supérieur"
                                           if t in ("Université", "Institut / collège supérieur") else "École"),
            sous_type=lambda d: d.type + " – " + d.secteur, precision_localisation="point GPS (OpenStreetMap)")
    osm = _read(LIVE / "osm_institutions.csv")
    if not osm.empty:
        osm = osm.assign(precision_localisation="point GPS (OpenStreetMap)")
    morceaux = [x for x in (base, edu, osm) if not x.empty]
    out = pd.concat(morceaux, ignore_index=True)
    if "osm_id" in out:  # l'export HOT et la mise à jour Overpass peuvent contenir les mêmes objets
        out["_k"] = out.osm_id.astype(str).str.replace("way/", "w").str.replace("node/", "n").str.replace("relation/", "r")
        out = pd.concat([out[out.osm_id.isna()], out[out.osm_id.notna()].drop_duplicates("_k", keep="last")]).drop(columns="_k")
    return out.reset_index(drop=True)


@st.cache_data(show_spinner=False)
def etablissements_education_osm() -> pd.DataFrame:
    """7 364 établissements d'enseignement OpenStreetMap (export HOT, oct. 2026), points GPS sur tout le pays."""
    return _read(PROCESSED / "etablissements_education_osm.csv")


@st.cache_data(show_spinner=False)
def osm_institutions() -> pd.DataFrame:
    return _read(LIVE / "osm_institutions.csv")


@st.cache_data(show_spinner=False)
def universites() -> pd.DataFrame:
    return _read(PROCESSED / "universites.csv")


@st.cache_data(show_spinner=False)
def wb() -> pd.DataFrame:
    """Indicateurs Banque mondiale : base HDX (1960-2022) + valeurs récentes de l'API si disponibles."""
    base = _read(PROCESSED / "wb_indicateurs.csv")
    live = _read(LIVE / "wb_live.csv")
    if not live.empty:
        live = live.assign(source="Banque mondiale – API (mise à jour)")
        base = (pd.concat([base, live], ignore_index=True)
                .sort_values("source")  # « Banque mondiale – API » passe avant « – WDI »
                .drop_duplicates(subset=["code", "annee"], keep="first"))
        base["themes"] = base.groupby("code")["themes"].transform(lambda s: s.ffill().bfill())
    base["libelle"] = base.apply(lambda r: INDICATEURS_CLES.get(r.code, (r.indicateur_en,))[0], axis=1)
    return base.sort_values(["code", "annee"]).reset_index(drop=True)


def serie(code: str) -> pd.DataFrame:
    d = wb()
    return d[d.code == code].dropna(subset=["valeur"]).sort_values("annee")


def derniere_valeur(code: str) -> tuple[float | None, int | None]:
    s = serie(code)
    if s.empty:
        return None, None
    r = s.iloc[-1]
    return float(r.valeur), int(r.annee)


@st.cache_data(show_spinner=False)
def indicateurs_actuels() -> pd.DataFrame:
    return _read(CURATED / "indicateurs_actuels.csv")


@st.cache_data(show_spinner=False)
def ipc_historique() -> pd.DataFrame:
    return _read(PROCESSED / "ipc_historique.csv")


@st.cache_data(show_spinner=False)
def ipc_live() -> pd.DataFrame:
    return _read(LIVE / "ipc_live.csv")


@st.cache_data(show_spinner=False)
def covid() -> pd.DataFrame:
    return _read(PROCESSED / "covid19_2020.csv")


@st.cache_data(show_spinner=False)
def organisations() -> pd.DataFrame:
    return _read(PROCESSED / "organisations_humanitaires_2020.csv")


@st.cache_data(show_spinner=False)
def actualites() -> pd.DataFrame:
    return _read(LIVE / "actualites.csv")


@st.cache_data(show_spinner=False)
def journal() -> pd.DataFrame:
    return _read(LIVE / "journal_mises_a_jour.csv")


@st.cache_data(show_spinner=False)
def geojson(niveau: str = "communes") -> dict:
    with open(GEO / f"{niveau}.geojson", encoding="utf-8") as f:
        return json.load(f)


def tous_les_csv() -> dict[str, Path]:
    """Inventaire de tous les CSV de la plateforme (pour l'explorateur)."""
    out = {}
    for dossier, label in ((PROCESSED, "Données traitées"), (CURATED, "Données vérifiées"), (LIVE, "Données à jour")):
        for p in sorted(dossier.glob("*.csv")):
            out[f"{label} › {p.stem}"] = p
    return out


def vider_cache() -> None:
    st.cache_data.clear()


@st.cache_data(show_spinner=False)
def richesses() -> pd.DataFrame:
    return _read(CURATED / "richesses.csv")


@st.cache_data(show_spinner=False)
def liens_utiles() -> pd.DataFrame:
    return _read(CURATED / "liens_utiles.csv")


@st.cache_data(show_spinner=False, ttl=900)
def actualites_enrichies() -> pd.DataFrame:
    """Actualités avec thème et tonalité (recalculés si le fichier vient d'une ancienne version)."""
    from src.veille import etiquette, priorite, theme, tonalite
    d = _read(LIVE / "actualites.csv")
    if d.empty:
        return d
    if "resume" not in d:
        d["resume"] = ""
    if "theme" not in d:
        d["theme"] = [theme(t, r) for t, r in zip(d.titre, d.resume.fillna(""))]
        d["score_tonalite"] = [tonalite(t, r) for t, r in zip(d.titre, d.resume.fillna(""))]
        d["tonalite"] = d.score_tonalite.map(etiquette)
        d["priorite"] = [priorite(s, t) for s, t in zip(d.score_tonalite, d.theme)]
    return d.sort_values("date", ascending=False).reset_index(drop=True)


@st.cache_data(show_spinner=False)
def indice_developpement():
    from src.developpement import calculer
    return calculer(wb())
