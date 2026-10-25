"""Assistant d'analyse optionnel (modèle de langage).

Désactivé par défaut. Pour l'activer, ajouter dans .streamlit/secrets.toml (ou les secrets
de Streamlit Cloud) l'une des options suivantes :

    ANTHROPIC_API_KEY = "sk-ant-..."            # API Claude
    # ou un serveur local Ollama (gratuit, hors ligne) :
    OLLAMA_URL = "http://localhost:11434"
    OLLAMA_MODEL = "mistral"

Le modèle ne reçoit QUE les chiffres calculés par la plateforme (contexte) : il reformule
et commente, il n'invente pas de données.
"""
from __future__ import annotations

import requests
import streamlit as st

CONSIGNE = (
    "Tu es un analyste spécialiste d'Haïti. Réponds en français, de façon factuelle et nuancée, "
    "uniquement à partir des données fournies dans le contexte. Si une information manque, dis-le. "
    "Cite les années et les sources indiquées."
)


def disponible() -> str | None:
    try:
        if st.secrets.get("ANTHROPIC_API_KEY"):
            return "anthropic"
        if st.secrets.get("OLLAMA_URL"):
            return "ollama"
    except Exception:  # pas de fichier secrets
        return None
    return None


def demander(question: str, contexte: str) -> str:
    mode = disponible()
    prompt = f"Contexte (données de la plateforme) :\n{contexte}\n\nQuestion : {question}"
    if mode == "anthropic":
        r = requests.post(
            "https://api.anthropic.com/v1/messages",
            headers={"x-api-key": st.secrets["ANTHROPIC_API_KEY"], "anthropic-version": "2023-06-01",
                     "content-type": "application/json"},
            json={"model": st.secrets.get("ANTHROPIC_MODEL", "claude-sonnet-5-5"), "max_tokens": 1200,
                  "system": CONSIGNE, "messages": [{"role": "user", "content": prompt}]},
            timeout=90,
        )
        r.raise_for_status()
        return "".join(b.get("text", "") for b in r.json().get("content", []))
    if mode == "ollama":
        r = requests.post(f"{st.secrets['OLLAMA_URL'].rstrip('/')}/api/generate",
                          json={"model": st.secrets.get("OLLAMA_MODEL", "mistral"),
                                "prompt": f"{CONSIGNE}\n\n{prompt}", "stream": False}, timeout=180)
        r.raise_for_status()
        return r.json().get("response", "")
    return "Assistant non configuré (voir src/assistant.py)."
