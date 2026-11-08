"""Composants d'interface réutilisables : fil d'actualités, cartes « richesses », liens."""
from __future__ import annotations

import html

import pandas as pd
import streamlit as st

ICONE_TON = {"Positif": "🌱", "Neutre": "•", "Négatif": "⚠️"}
ICONE_THEME = {"Économie": "💼", "Politique": "🏛️", "Tourisme": "🏝️", "Culture": "🎨", "Sport": "⚽",
               "Éducation & science": "🎓", "Santé": "🩺", "Environnement": "🌿", "Diaspora": "🌍",
               "Agriculture": "🌾", "Sécurité": "🛡️", "Humanitaire": "🤝", "Société": "📰"}

CSS_FIL = """
<style>
.ay-news { display:flex; flex-direction:column; gap:.55rem; }
.ay-item { border:1px solid #e6e5e0; border-radius:12px; padding:.6rem .75rem; background:#fff; }
.ay-item a { color:#0b0b0b; font-weight:600; text-decoration:none; line-height:1.3; }
.ay-item a:hover { color:#00209F; text-decoration:underline; }
.ay-meta { font-size:.78rem; color:#8a8984; margin-top:.25rem; }
.ay-tag { display:inline-block; font-size:.72rem; font-weight:700; padding:.05rem .45rem; border-radius:999px;
  background:#eef2ff; color:#00209F; margin-right:.3rem; }
.ay-tag.pos { background:#e8f6e8; color:#0a6b0a; }
.ay-tag.neg { background:#fdeeee; color:#9b2c2c; }
@media (prefers-color-scheme: dark) { .ay-item { background:#1f1f1d; border-color:#383835; } .ay-item a { color:#f0efec; } }
</style>
"""


def filtrer_actualites(d: pd.DataFrame, regard_positif: bool = True, themes: list[str] | None = None,
                       recherche: str = "") -> pd.DataFrame:
    if d.empty:
        return d
    if themes:
        d = d[d.theme.isin(themes)]
    if recherche:
        d = d[d.titre.str.contains(recherche, case=False, na=False)]
    if regard_positif:
        # d'abord les nouvelles positives et les thèmes valorisants, puis le reste, chacun par date
        d = d.assign(_p=(d.priorite > 0.2).astype(int)).sort_values(["_p", "date"], ascending=[False, False])
        d = d.drop(columns="_p")
    return d


def fil_actualites(d: pd.DataFrame, n: int = 20) -> None:
    st.markdown(CSS_FIL, unsafe_allow_html=True)
    if d.empty:
        st.info("Aucune actualité pour ce filtre. Les actualités sont rafraîchies toutes les 6 heures.")
        return
    items = []
    for r in d.head(n).itertuples():
        ton = getattr(r, "tonalite", "Neutre")
        cls = "pos" if ton == "Positif" else "neg" if ton == "Négatif" else ""
        th = getattr(r, "theme", "Société")
        date = str(r.date)[:10]
        items.append(
            f"<div class='ay-item'><span class='ay-tag'>{ICONE_THEME.get(th, '📰')} {html.escape(th)}</span>"
            f"<span class='ay-tag {cls}'>{ICONE_TON.get(ton, '')} {ton}</span><br>"
            f"<a href='{html.escape(str(r.url))}' target='_blank' rel='noopener'>{html.escape(str(r.titre))}</a>"
            f"<div class='ay-meta'>{date} · {html.escape(str(r.source))}</div></div>")
    st.markdown(f"<div class='ay-news'>{''.join(items)}</div>", unsafe_allow_html=True)


def cartes_richesses(r: pd.DataFrame, n: int = 6, colonnes: int = 3) -> None:
    cols = st.columns(colonnes)
    for i, x in enumerate(r.head(n).itertuples()):
        with cols[i % colonnes]:
            with st.container(border=True):
                st.markdown(f"**{x.ressource}** · <span style='color:#8a8984'>{x.categorie}</span>", unsafe_allow_html=True)
                st.markdown(f"<span style='font-size:1.05rem;color:#00209F;font-weight:700'>{x.chiffre_cle}</span>",
                            unsafe_allow_html=True)
                st.caption(x.description)
                if isinstance(x.url, str) and x.url:
                    st.markdown(f"[Source : {x.source}]({x.url})")


def liens(l: pd.DataFrame, colonnes: int = 3) -> None:
    cols = st.columns(colonnes)
    for i, (cat, sub) in enumerate(l.groupby("categorie", sort=False)):
        with cols[i % colonnes]:
            st.markdown(f"**{cat}**")
            for x in sub.itertuples():
                st.markdown(f"- [{x.nom}]({x.url}) — <span style='color:#8a8984'>{x.description}</span>",
                            unsafe_allow_html=True)
