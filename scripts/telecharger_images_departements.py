"""Télécharge les photos des 10 départements (36 images, Wikipédia / Wikimedia Commons, licences libres).

Usage :  python scripts/telecharger_images_departements.py            # seulement les images manquantes
         python scripts/telecharger_images_departements.py --forcer   # tout retélécharger
Résultat : assets/img/departements/*.jpg + credits.csv (auteur, licence, lien de chaque image).
Liste des images : data/curated/images_departements.csv (modifiable depuis l'espace Administration).
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.images_dep import DOSSIER, telecharger_tout  # noqa: E402


def main(forcer: bool = False) -> None:
    ok, ko = telecharger_tout(forcer=forcer)
    print(f"{ok} image(s) disponibles, {ko} échec(s) — dossier : {DOSSIER}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--forcer", action="store_true")
    main(ap.parse_args().forcer)
