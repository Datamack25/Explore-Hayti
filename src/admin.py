"""Espace administrateur : authentification, édition des données, téléversements, sauvegarde GitHub.

Configuration (Streamlit Cloud → Settings → Secrets, ou .streamlit/secrets.toml en local) :

    ADMIN_PASSWORD = "un-mot-de-passe-solide"
    # facultatif : enregistrer les modifications directement dans le dépôt GitHub
    GITHUB_TOKEN = "github_pat_..."          # jeton « fine-grained » avec droit Contents: Read and write
    GITHUB_REPO  = "votre-compte/ayiti-data-hub"
    GITHUB_BRANCH = "main"

Sans GITHUB_TOKEN, les modifications sont écrites sur le serveur : elles sont immédiates mais, sur Streamlit
Community Cloud, perdues au prochain redémarrage. Avec le jeton, chaque modification est aussi validée (commit)
dans le dépôt, donc permanente.
"""
from __future__ import annotations

import base64
import hmac
from pathlib import Path

import requests
import streamlit as st

from src.utils import ROOT


def _secret(cle: str, defaut: str | None = None) -> str | None:
    try:
        return st.secrets.get(cle, defaut)
    except Exception:
        return defaut


def configure() -> bool:
    return bool(_secret("ADMIN_PASSWORD"))


def connecte() -> bool:
    return bool(st.session_state.get("admin_ok"))


def formulaire_connexion() -> bool:
    if connecte():
        return True
    if not configure():
        st.warning("Aucun mot de passe administrateur n'est configuré. Ajoutez `ADMIN_PASSWORD` dans les secrets "
                   "Streamlit (voir README) pour activer cet espace.")
        return False
    with st.form("connexion"):
        mdp = st.text_input("Mot de passe administrateur", type="password")
        if st.form_submit_button("Se connecter", type="primary"):
            if hmac.compare_digest(mdp, str(_secret("ADMIN_PASSWORD"))):
                st.session_state["admin_ok"] = True
                st.rerun()
            st.error("Mot de passe incorrect.")
    return False


def github_actif() -> bool:
    return bool(_secret("GITHUB_TOKEN") and _secret("GITHUB_REPO"))


def enregistrer(chemin: Path, contenu: bytes, message: str) -> str:
    """Écrit le fichier localement et, si configuré, le valide dans le dépôt GitHub (API Contents)."""
    chemin.parent.mkdir(parents=True, exist_ok=True)
    chemin.write_bytes(contenu)
    if not github_actif():
        return "enregistré sur le serveur (temporaire sur Streamlit Cloud : configurez GITHUB_TOKEN pour le rendre permanent)"
    rel = chemin.relative_to(ROOT).as_posix()
    repo, branche = _secret("GITHUB_REPO"), _secret("GITHUB_BRANCH", "main")
    url = f"https://api.github.com/repos/{repo}/contents/{rel}"
    h = {"Authorization": f"Bearer {_secret('GITHUB_TOKEN')}", "Accept": "application/vnd.github+json"}
    sha = None
    r = requests.get(url, headers=h, params={"ref": branche}, timeout=30)
    if r.status_code == 200:
        sha = r.json().get("sha")
    body = {"message": message, "content": base64.b64encode(contenu).decode(), "branch": branche}
    if sha:
        body["sha"] = sha
    r = requests.put(url, headers=h, json=body, timeout=60)
    if r.status_code in (200, 201):
        return f"enregistré et validé dans GitHub ({rel})"
    return f"enregistré sur le serveur, mais échec GitHub ({r.status_code} : {r.text[:150]})"


def supprimer(chemin: Path, message: str) -> str:
    if chemin.exists():
        chemin.unlink()
    if not github_actif():
        return "supprimé du serveur"
    rel = chemin.relative_to(ROOT).as_posix()
    repo, branche = _secret("GITHUB_REPO"), _secret("GITHUB_BRANCH", "main")
    url = f"https://api.github.com/repos/{repo}/contents/{rel}"
    h = {"Authorization": f"Bearer {_secret('GITHUB_TOKEN')}", "Accept": "application/vnd.github+json"}
    r = requests.get(url, headers=h, params={"ref": branche}, timeout=30)
    if r.status_code != 200:
        return "supprimé du serveur (absent de GitHub)"
    r = requests.delete(url, headers=h, json={"message": message, "sha": r.json()["sha"], "branch": branche}, timeout=30)
    return "supprimé du serveur et de GitHub" if r.status_code == 200 else f"échec GitHub ({r.status_code})"


def lancer_action_github(mode: str = "complet") -> str:
    """Déclenche le workflow de mise à jour sur GitHub Actions (nécessite GITHUB_TOKEN avec droit Actions)."""
    if not github_actif():
        return "GITHUB_TOKEN / GITHUB_REPO non configurés."
    repo, branche = _secret("GITHUB_REPO"), _secret("GITHUB_BRANCH", "main")
    r = requests.post(f"https://api.github.com/repos/{repo}/actions/workflows/mise-a-jour-donnees.yml/dispatches",
                      headers={"Authorization": f"Bearer {_secret('GITHUB_TOKEN')}", "Accept": "application/vnd.github+json"},
                      json={"ref": branche, "inputs": {"mode": mode}}, timeout=30)
    return "Mise à jour lancée sur GitHub Actions (résultat dans quelques minutes)." if r.status_code == 204 \
        else f"Échec ({r.status_code} : {r.text[:150]})"
