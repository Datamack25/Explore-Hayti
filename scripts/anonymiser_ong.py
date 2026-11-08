"""Transforme la base de contacts ONG (2020) en liste d'ORGANISATIONS uniquement.

La base d'origine contient des noms et adresses e-mail de personnes : ce sont des
données personnelles qui ne doivent PAS être publiées sur GitHub. Ce script ne garde
que le nom de l'organisation, sa catégorie et le nombre de contacts recensés.

Usage :  python scripts/anonymiser_ong.py chemin/vers/Base_de_donnees_ONG.csv
Le fichier brut ne doit pas être ajouté au dépôt (voir .gitignore).
"""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.utils import PROCESSED  # noqa: E402

ONU = ("UNICEF", "PAM", "WFP", "MINUSTAH", "MINUJUSTH", "BINUH", "OIM", "IOM", "PNUD", "UNDP", "OCHA", "OPS", "OMS",
       "FAO", "UNFPA", "OHCHR", "UNHCR", "HCR", "UNEP", "PNUE", "ONU", "UNOPS", "UNESCO", "ONUSIDA", "UN WOMEN", "ONU FEMMES")
BAILLEURS = ("USAID", "OFDA", "ECHO", "DFID", "BANQUE MONDIALE", "BID", "COOPÉRATION", "COOPERATION", "AMBASSADE",
             "UNION EUROPÉENNE", "UNION EUROPEENNE", "JICA", "AFD", "GAC", "CANADA")
CROIX_ROUGE = ("CROIX ROUGE", "CROIX-ROUGE", "RED CROSS", "FICR", "IFRC", "CICR", "ICRC")
ETAT = ("DINEPA", "DIRECTION", "MINIST", "GOUVERNEMENT", "PROTECTION CIVILE", "MAIRIE", "MSPP", "MENFP", "CNSA",
        "MARNDR", "MPCE", "MTPTC", "DPC", "IBESR", "UCP")


def categorie(org: str) -> str:
    u = org.upper()
    if any(k in u for k in CROIX_ROUGE):
        return "Mouvement Croix-Rouge"
    if any(k == u or u.startswith(k + " ") or u.startswith(k + "/") or f"({k})" in u for k in ONU):
        return "Système des Nations unies"
    if any(k in u for k in BAILLEURS):
        return "Bailleur / coopération"
    if any(k in u for k in ETAT):
        return "Institution publique haïtienne"
    return "ONG / société civile"


def main(src: str) -> None:
    d = pd.read_csv(src, encoding="latin1", skiprows=1)
    org = d["Organisation"].fillna("").astype(str).str.strip()
    org = org[org != ""]
    norm = org.str.upper().str.replace(r"\s+", " ", regex=True)
    out = (pd.DataFrame({"organisation": norm})
           .groupby("organisation").size().rename("nb_contacts_2020").reset_index()
           .sort_values("nb_contacts_2020", ascending=False))
    out["organisation"] = out["organisation"].map(
        lambda s: s if (len(s) <= 6 or "/" in s and len(s) <= 12) else s.title().replace("Onu", "ONU"))
    out["categorie"] = out["organisation"].map(categorie)
    out["source"] = "Base de données ONG – AVL (19/08/2020), agrégée sans données personnelles"
    PROCESSED.mkdir(parents=True, exist_ok=True)
    out.to_csv(PROCESSED / "organisations_humanitaires_2020.csv", index=False, encoding="utf-8")
    print(f"✓ {len(out)} organisations écrites (aucun nom ni e-mail conservé)")
    print(out.categorie.value_counts().to_string())


if __name__ == "__main__":
    main(sys.argv[1])
