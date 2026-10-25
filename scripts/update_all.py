"""Lance toutes les mises à jour à la suite. Chaque source est indépendante : un échec n'arrête pas les autres.

Usage :
    python scripts/update_all.py            # complet (hebdomadaire)
    python scripts/update_all.py --rapide   # actualités + HDX seulement (toutes les 6 h)
    python scripts/update_all.py --sans-osm
Appelé par le bouton « Mettre à jour » de l'application et par l'action GitHub planifiée.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts import update_hdx, update_news, update_osm, update_routes, update_world_bank  # noqa: E402


def main(sans_osm: bool = False, rapide: bool = False) -> None:
    print("== Actualités (médias haïtiens, diaspora, international) ==")
    update_news.main()
    print("== HDX (IPC, catalogue) ==")
    update_hdx.maj_ipc()
    update_hdx.catalogue()
    if rapide:
        print("Mode rapide terminé.")
        return
    print("== Banque mondiale ==")
    update_world_bank.main()
    if not sans_osm:
        print("== OpenStreetMap (institutions) ==")
        update_osm.main()
        print("== OpenStreetMap (routes, aéroports, ports) ==")
        update_routes.main()
    print("Terminé.")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--sans-osm", action="store_true")
    ap.add_argument("--rapide", action="store_true")
    a = ap.parse_args()
    main(a.sans_osm, a.rapide)
