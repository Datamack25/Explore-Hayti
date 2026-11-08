"""Récupère les jeux de données humanitaires les plus récents sur HDX (Humanitarian Data Exchange, API CKAN, sans clé).

- IPC : insécurité alimentaire aiguë (fichier national « long » le plus récent)
- Population : statistiques administratives (si une version plus récente que 2022 est publiée)

Usage :  python scripts/update_hdx.py
Résultats : data/live/ipc_live.csv, data/live/hdx_catalogue_haiti.csv
"""
from __future__ import annotations

import io
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from scripts.maj_commun import LIVE, get, journaliser  # noqa: E402

CKAN = "https://data.humdata.org/api/3/action"


def chercher(q: str, rows: int = 20) -> list[dict]:
    r = get(f"{CKAN}/package_search", params={"q": q, "fq": "groups:hti", "rows": rows, "sort": "metadata_modified desc"})
    return r.json()["result"]["results"]


def ressource_csv(pkg: dict, motif: str) -> str | None:
    for res in pkg.get("resources", []):
        nom = (res.get("name") or "").lower()
        if motif in nom and (res.get("format") or "").lower() == "csv":
            return res["url"]
    return None


def maj_ipc() -> None:
    try:
        url = None
        for p in chercher("ipc acute food insecurity haiti"):
            url = ressource_csv(p, "national_long_latest") or ressource_csv(p, "national_long")
            if url:
                break
        if not url:
            journaliser("HDX – IPC", "échec", 0, "ressource introuvable")
            return
        txt = get(url).text
        df = pd.read_csv(io.StringIO(txt))
        if str(df.iloc[0, 0]).startswith("#"):
            df = df.iloc[1:]  # ligne de balises HXL
        df.to_csv(LIVE / "ipc_live.csv", index=False)
        journaliser("HDX – IPC", "ok", len(df), url.split("/")[-1])
    except Exception as e:
        journaliser("HDX – IPC", "échec", 0, str(e))


def catalogue() -> None:
    """Inventaire des jeux de données récents sur Haïti (pour repérer de nouvelles sources)."""
    try:
        rows = []
        for p in chercher("haiti", rows=100):
            rows.append({"titre": p.get("title"), "organisation": (p.get("organization") or {}).get("title"),
                         "mis_a_jour": (p.get("metadata_modified") or "")[:10],
                         "url": f"https://data.humdata.org/dataset/{p.get('name')}"})
        pd.DataFrame(rows).to_csv(LIVE / "hdx_catalogue_haiti.csv", index=False)
        journaliser("HDX – catalogue", "ok", len(rows))
    except Exception as e:
        journaliser("HDX – catalogue", "échec", 0, str(e))


if __name__ == "__main__":
    maj_ipc()
    catalogue()
