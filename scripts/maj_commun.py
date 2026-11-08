"""Outils communs aux scripts de mise à jour : requêtes HTTP robustes et journal."""
from __future__ import annotations

import csv
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.utils import LIVE  # noqa: E402

LIVE.mkdir(parents=True, exist_ok=True)
JOURNAL = LIVE / "journal_mises_a_jour.csv"
UA = {"User-Agent": "AyitiDataHub/1.0 (plateforme de données ouvertes sur Haïti; github)"}


def get(url: str, params: dict | None = None, tries: int = 3, timeout: int = 60, **kw) -> requests.Response:
    last = None
    for i in range(tries):
        try:
            r = requests.get(url, params=params, headers=UA, timeout=timeout, **kw)
            if r.status_code == 429:
                time.sleep(5 * (i + 1))
                continue
            r.raise_for_status()
            return r
        except requests.RequestException as e:  # réseau, 5xx…
            last = e
            time.sleep(2 * (i + 1))
    raise RuntimeError(f"Échec après {tries} tentatives : {url} ({last})")


def post(url: str, data: dict, tries: int = 3, timeout: int = 180) -> requests.Response:
    last = None
    for i in range(tries):
        try:
            r = requests.post(url, data=data, headers=UA, timeout=timeout)
            if r.status_code in (429, 504):
                time.sleep(10 * (i + 1))
                continue
            r.raise_for_status()
            return r
        except requests.RequestException as e:
            last = e
            time.sleep(5 * (i + 1))
    raise RuntimeError(f"Échec après {tries} tentatives : {url} ({last})")


def journaliser(source: str, statut: str, lignes: int = 0, message: str = "") -> None:
    neuf = not JOURNAL.exists()
    with open(JOURNAL, "a", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        if neuf:
            w.writerow(["date_utc", "source", "statut", "lignes", "message"])
        w.writerow([datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M"), source, statut, lignes, message[:300]])
    print(f"[{statut}] {source} : {lignes} lignes {('– ' + message) if message else ''}")
