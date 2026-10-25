"""Indice composite de développement d'Haïti dans le temps (multifactoriel).

Six dimensions, chacune moyenne d'indicateurs ramenés sur 0-100 :
  0  = pire valeur observée pour Haïti depuis 1990
  100 = meilleure valeur observée pour Haïti depuis 1990
C'est donc une TRAJECTOIRE propre au pays (progrès / recul), pas un classement international.
Les indicateurs absents des fichiers sont ignorés automatiquement ; ils s'ajoutent dès que la mise à jour
Banque mondiale les télécharge (espérance de vie, scolarisation, électricité, Internet…).
"""
from __future__ import annotations

import numpy as np
import pandas as pd

# code: (libellé, sens) — sens +1 : plus = mieux ; -1 : plus = moins bien
DIMENSIONS: dict[str, dict[str, tuple[str, int]]] = {
    "Économique": {
        "NY.GDP.PCAP.KD": ("PIB par habitant (USD constants)", 1),
        "NE.GDI.TOTL.ZS": ("Investissement (% du PIB)", 1),
        "FS.AST.PRVT.GD.ZS": ("Crédit au secteur privé (% du PIB)", 1),
        "FP.CPI.TOTL.ZG": ("Inflation", -1),
        "BX.TRF.PWKR.CD.DT": ("Transferts de la diaspora (USD)", 1),
    },
    "Politique & institutions": {
        "IQ.CPA.PUBS.XQ": ("CPIA – gestion du secteur public", 1),
        "IQ.CPA.ECON.XQ": ("CPIA – gestion économique", 1),
        "IQ.CPA.TRAN.XQ": ("CPIA – transparence et redevabilité", 1),
        "IQ.CPA.PROP.XQ": ("CPIA – droits de propriété et gouvernance", 1),
        "IQ.CPA.BREG.XQ": ("CPIA – environnement des affaires", 1),
    },
    "Social": {
        "SP.DYN.LE00.IN": ("Espérance de vie", 1),
        "SP.DYN.IMRT.IN": ("Mortalité infantile", -1),
        "SE.PRM.ENRR": ("Scolarisation primaire", 1),
        "SE.SEC.ENRR": ("Scolarisation secondaire", 1),
        "EG.ELC.ACCS.ZS": ("Accès à l'électricité", 1),
        "EG.ELC.ACCS.RU.ZS": ("Accès à l'électricité en zone rurale", 1),
        "SH.H2O.BASW.ZS": ("Accès à l'eau potable", 1),
        "FX.OWN.TOTL.ZS": ("Inclusion financière (compte)", 1),
    },
    "Culture & ouverture": {
        "ST.INT.ARVL": ("Arrivées de touristes", 1),
        "ST.INT.RCPT.CD": ("Recettes touristiques", 1),
        "IT.NET.USER.ZS": ("Utilisateurs d'Internet", 1),
        "IT.CEL.SETS.P2": ("Abonnements mobiles", 1),
        "TG.VAL.TOTL.GD.ZS": ("Ouverture commerciale", 1),
    },
    "Population": {
        "SP.URB.TOTL.IN.ZS": ("Urbanisation", 1),
        "SP.RUR.TOTL.ZS": ("Population rurale (%)", -1),
        "SP.DYN.TFRT.IN": ("Fécondité (transition démographique)", -1),
        "SP.POP.GROW": ("Croissance démographique", -1),
    },
    "Nature & environnement": {
        "AG.LND.FRST.ZS": ("Couverture forestière", 1),
        "AG.YLD.CREL.KG": ("Rendement céréalier", 1),
        "IQ.CPA.ENVR.XQ": ("CPIA – politiques environnementales", 1),
        "VC.IDP.NWDS": ("Déplacements dus aux catastrophes", -1),
    },
}

COULEURS_DIM = {  # palette catégorielle validée, ordre fixe
    "Économique": "#2a78d6", "Politique & institutions": "#eb6834", "Social": "#1baf7a",
    "Culture & ouverture": "#eda100", "Population": "#e87ba4", "Nature & environnement": "#008300",
}


def calculer(wb: pd.DataFrame, debut: int = 1990) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Renvoie (indice par année et dimension, détail des indicateurs utilisés)."""
    codes = {c: (d, lab, s) for d, inds in DIMENSIONS.items() for c, (lab, s) in inds.items()}
    sub = wb[wb.code.isin(codes) & (wb.annee >= debut)]
    wide = sub.pivot_table(index="annee", columns="code", values="valeur").sort_index()
    if wide.empty:
        return pd.DataFrame(), pd.DataFrame()
    # séries volatiles (inflation, croissance) : moyenne mobile 3 ans
    for c in wide.columns:
        if c in ("FP.CPI.TOTL.ZG", "NY.GDP.MKTP.KD.ZG"):
            wide[c] = wide[c].rolling(3, min_periods=1).mean()
    # comblement raisonnable des trous (interpolation, puis prolongement de 3 ans max)
    wide = wide.interpolate(limit_area="inside").ffill(limit=3).bfill(limit=3)
    norm = pd.DataFrame(index=wide.index)
    det = []
    for c in wide.columns:
        d, lab, s = codes[c]
        v = wide[c]
        lo, hi = v.min(), v.max()
        if pd.isna(lo) or hi == lo:
            continue
        x = 100 * (v - lo) / (hi - lo)
        norm[c] = x if s > 0 else 100 - x
        det.append({"dimension": d, "code": c, "indicateur": lab, "sens": "↑ mieux" if s > 0 else "↓ mieux",
                    "premiere_annee": int(sub[sub.code == c].annee.min()), "derniere_annee": int(sub[sub.code == c].annee.max())})
    det = pd.DataFrame(det)
    out = pd.DataFrame(index=wide.index)
    for d in DIMENSIONS:
        cols = [c for c in det[det.dimension == d].code] if len(det) else []
        if cols:
            out[d] = norm[cols].mean(axis=1, skipna=True)
    out["Indice global"] = out[list(c for c in DIMENSIONS if c in out)].mean(axis=1, skipna=True)
    out = out.dropna(how="all").round(1)
    out.index.name = "annee"
    return out.reset_index(), det


def lecture(ind: pd.DataFrame) -> list[str]:
    if ind.empty:
        return ["Données insuffisantes."]
    g = ind.dropna(subset=["Indice global"])
    a0, a1 = int(g.annee.iloc[0]), int(g.annee.iloc[-1])
    v0, v1 = g["Indice global"].iloc[0], g["Indice global"].iloc[-1]
    best = g.loc[g["Indice global"].idxmax()]
    pts = [f"Indice global : **{v1:.0f}/100** en {a1} (contre {v0:.0f} en {a0}) ; meilleure année : "
           f"**{int(best.annee)}** ({best['Indice global']:.0f}/100)."]
    dims = [c for c in DIMENSIONS if c in ind]
    last = ind.iloc[-1]
    fortes = sorted(((last[d], d) for d in dims if pd.notna(last[d])), reverse=True)
    if fortes:
        pts.append(f"Points forts récents : **{fortes[0][1]}** ({fortes[0][0]:.0f}/100)"
                   + (f" et **{fortes[1][1]}** ({fortes[1][0]:.0f}/100)." if len(fortes) > 1 else "."))
        pts.append(f"Dimension la plus en recul : **{fortes[-1][1]}** ({fortes[-1][0]:.0f}/100).")
    # progression sur 20 ans par dimension
    ref = ind[ind.annee == max(a0, a1 - 20)]
    if len(ref):
        prog = [(last[d] - ref.iloc[0][d], d) for d in dims if pd.notna(last[d]) and pd.notna(ref.iloc[0][d])]
        prog.sort(reverse=True)
        if prog and prog[0][0] > 0:
            pts.append(f"Plus forte progression sur ~20 ans : **{prog[0][1]}** ({prog[0][0]:+.0f} points).")
    pts.append("Lecture : 100 = meilleure situation observée pour Haïti depuis 1990, 0 = la plus difficile. "
               "L'indice montre la trajectoire du pays, pas un classement mondial.")
    return pts
