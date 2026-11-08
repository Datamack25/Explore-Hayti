"""Habillage visuel : CSS, cartes KPI en HTML, en-têtes, thème Plotly."""
from __future__ import annotations

import base64
from functools import lru_cache

import plotly.graph_objects as go
import plotly.io as pio
import streamlit as st

from src.utils import ASSETS

# Palette catégorielle validée (ordre fixe, jamais recyclé)
SERIES = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300", "#6250d6", "#e34948"]
# Rampe séquentielle bleue (choroplèthes)
SEQ_BLEU = ["#cde2fb", "#9ec5f4", "#6da7ec", "#3987e5", "#256abf", "#184f95", "#0d366b"]
SEQ_ORANGE = ["#fde4d8", "#f8b99c", "#f19066", "#eb6834", "#c4501f", "#963b15", "#6b290d"]
DIVERGENT = ["#184f95", "#3987e5", "#9ec5f4", "#f0efec", "#f3a7a6", "#e34948", "#a32a29"]
STATUT = {"bon": "#0ca30c", "alerte": "#fab219", "serieux": "#ec835a", "critique": "#d03b3b"}
# Couleurs de marque (habillage uniquement, pas les données)
BLEU_HAITI = "#00209F"
ROUGE_HAITI = "#D21034"
INK = "#0b0b0b"
INK2 = "#52514e"
MUTED = "#8a8984"
GRID = "#e6e5e0"
SURFACE = "#fcfcfb"

pio.templates["ayiti"] = go.layout.Template(
    layout=dict(
        font=dict(family="Source Sans 3, Source Sans Pro, Arial, sans-serif", size=13, color=INK2),
        title=dict(font=dict(family="Fraunces, Georgia, serif", size=17, color=INK), x=0, xanchor="left"),
        colorway=SERIES,
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        xaxis=dict(showgrid=False, linecolor=GRID, ticks="outside", tickcolor=GRID, zeroline=False),
        yaxis=dict(gridcolor=GRID, zeroline=False, linecolor="rgba(0,0,0,0)"),
        legend=dict(orientation="h", y=-0.18, x=0, title_text=""),
        hoverlabel=dict(bgcolor="white", font_size=13, bordercolor=GRID),
        margin=dict(l=10, r=10, t=50, b=10),
        hovermode="x unified",
    )
)
pio.templates.default = "plotly+ayiti"

CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Fraunces:opsz,wght@9..144,500;9..144,700&family=Source+Sans+3:wght@400;600;700&display=swap');
html, body, [class*="css"], .stMarkdown, .stText { font-family: 'Source Sans 3', sans-serif; }
h1, h2, h3, .ay-hero h1 { font-family: 'Fraunces', Georgia, serif !important; letter-spacing: -0.01em; }
.block-container { padding-top: 1.6rem; max-width: 1300px; }
.ay-band { height: 6px; border-radius: 3px; margin: 0 0 1rem 0;
  background: linear-gradient(90deg, #00209F 0 50%, #D21034 50% 100%); }
.ay-hero { position: relative; border-radius: 18px; overflow: hidden; min-height: 300px; margin-bottom: 1.4rem;
  background-size: cover; background-position: center; display: flex; align-items: flex-end; }
.ay-hero::after { content: ""; position: absolute; inset: 0;
  background: linear-gradient(180deg, rgba(0,20,80,0.05) 20%, rgba(0,14,60,0.82) 100%); }
.ay-hero .inner { position: relative; z-index: 2; padding: 1.8rem 2rem; color: #fff; }
.ay-hero h1 { color: #fff !important; font-size: 2.6rem; margin: 0 0 .3rem 0; line-height: 1.05; }
.ay-hero p { color: #e8ecff; font-size: 1.1rem; margin: 0; max-width: 760px; }
.ay-eyebrow { text-transform: uppercase; letter-spacing: .14em; font-size: .78rem; font-weight: 700; color: #ffd6dc; }
.ay-kpis { display: grid; grid-template-columns: repeat(auto-fit, minmax(145px, 1fr)); gap: .8rem; margin: .4rem 0 1.2rem 0; }
.ay-kpi { background: var(--ay-card, #fff); border: 1px solid #e6e5e0; border-radius: 14px; padding: .9rem 1rem; }
.ay-kpi .lab { font-size: .82rem; color: #52514e; font-weight: 600; text-transform: uppercase; letter-spacing: .04em; }
.ay-kpi .val { font-family: 'Fraunces', Georgia, serif; font-size: 1.85rem; color: #0b0b0b; line-height: 1.15; margin-top: .15rem; }
.ay-kpi .sub { font-size: .82rem; color: #8a8984; margin-top: .1rem; }
.ay-kpi.accent { border-top: 4px solid #00209F; }
.ay-kpi.alert { border-top: 4px solid #D21034; }
.ay-card { border: 1px solid #e6e5e0; border-radius: 14px; padding: 1rem 1.1rem; height: 100%; background: #fff; }
.ay-card h4 { margin: 0 0 .35rem 0; font-family: 'Fraunces', serif; }
.ay-card p { margin: 0; color: #52514e; font-size: .95rem; }
.ay-note { background: #f5f7ff; border-left: 4px solid #00209F; padding: .7rem 1rem; border-radius: 0 10px 10px 0;
  color: #1f2a55; font-size: .93rem; margin: .4rem 0 1rem 0; }
.ay-warn { background: #fff6f0; border-left: 4px solid #ec835a; padding: .7rem 1rem; border-radius: 0 10px 10px 0;
  color: #5a2a14; font-size: .93rem; margin: .4rem 0 1rem 0; }
.ay-analysis { background: #fbfbf9; border: 1px solid #e6e5e0; border-radius: 14px; padding: 1rem 1.2rem; }
.ay-analysis li { margin-bottom: .3rem; }
.ay-badge { display: inline-block; padding: .1rem .55rem; border-radius: 999px; font-size: .78rem; font-weight: 600;
  background: #eef2ff; color: #00209F; margin-right: .3rem; }
.ay-foot { color: #8a8984; font-size: .82rem; margin-top: 2rem; border-top: 1px solid #e6e5e0; padding-top: .8rem; }
@media (prefers-color-scheme: dark) {
  .ay-kpi, .ay-card { background: #1f1f1d; border-color: #383835; }
  .ay-kpi .val { color: #f0efec; } .ay-kpi .lab { color: #c3c2b7; }
  .ay-card p { color: #c3c2b7; } .ay-analysis { background: #1f1f1d; border-color: #383835; }
  .ay-note { background: #1b2140; color: #dfe5ff; } .ay-warn { background: #3a2216; color: #ffe1d1; }
}
@media (max-width: 640px) { .ay-hero h1 { font-size: 1.8rem; } .ay-hero .inner { padding: 1.2rem; } }
</style>
"""


def setup(titre: str, icone: str = "🇭🇹") -> None:
    st.set_page_config(page_title=f"{titre} · Ayiti Data Hub", page_icon=icone, layout="wide")
    st.markdown(CSS, unsafe_allow_html=True)
    with st.sidebar:
        st.markdown("### 🇭🇹 Ayiti Data Hub")
        st.caption("Toutes les données sur Haïti, réunies en un seul endroit.")


@lru_cache(maxsize=16)
def image_b64(nom: str) -> str:
    p = ASSETS / "img" / nom
    return base64.b64encode(p.read_bytes()).decode() if p.exists() else ""


def hero(titre: str, sous_titre: str, image: str, eyebrow: str = "Ayiti Data Hub") -> None:
    b64 = image_b64(image)
    st.markdown(
        f"""<div class="ay-hero" style="background-image:url('data:image/jpeg;base64,{b64}')">
        <div class="inner"><div class="ay-eyebrow">{eyebrow}</div><h1>{titre}</h1><p>{sous_titre}</p></div></div>""",
        unsafe_allow_html=True,
    )


def entete(titre: str, sous_titre: str = "") -> None:
    st.markdown('<div class="ay-band"></div>', unsafe_allow_html=True)
    st.title(titre)
    if sous_titre:
        st.markdown(f"<p style='color:#52514e;font-size:1.05rem;margin-top:-.6rem'>{sous_titre}</p>", unsafe_allow_html=True)


def kpis(items: list[dict]) -> None:
    """items : [{'lab':..., 'val':..., 'sub':..., 'style':'accent'|'alert'|''}]"""
    html = "".join(
        f"<div class='ay-kpi {i.get('style', '')}'><div class='lab'>{i['lab']}</div>"
        f"<div class='val'>{i['val']}</div><div class='sub'>{i.get('sub', '')}</div></div>"
        for i in items
    )
    st.markdown(f"<div class='ay-kpis'>{html}</div>", unsafe_allow_html=True)


def note(txt: str, kind: str = "note") -> None:
    st.markdown(f"<div class='ay-{kind}'>{txt}</div>", unsafe_allow_html=True)


def _md_gras(t: str) -> str:
    import re
    return re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", t)


def analyse_box(titre: str, points: list[str]) -> None:
    li = "".join(f"<li>{_md_gras(p)}</li>" for p in points)
    st.markdown(f"<div class='ay-analysis'><b>🧠 {titre}</b><ul style='margin:.5rem 0 0 0'>{li}</ul></div>",
                unsafe_allow_html=True)


def pied(sources: str) -> None:
    st.markdown(f"<div class='ay-foot'>Sources : {sources}</div>", unsafe_allow_html=True)


def fmt(x, dec: int = 0, suffix: str = "") -> str:
    """Format français : 11 402 531 · 3,5 % · 1,2 Md."""
    if x is None or x != x:
        return "–"
    ax = abs(x)
    if ax >= 1e9:
        s = f"{x / 1e9:,.1f} Md"
    elif ax >= 1e6:
        s = f"{x / 1e6:,.2f} M"
    elif ax >= 1e4:
        s = f"{x:,.0f}"
    else:
        s = f"{x:,.{dec}f}"
    return s.replace(",", " ").replace(".", ",") + suffix


DIAPORAMA_DEFAUT = [
    ("cap_haitien.jpg", "Cap-Haïtien — cathédrale Notre-Dame et place d'Armes"),
    ("marche_en_fer.jpg", "Port-au-Prince — le Marché en Fer (1891)"),
    ("delmas.jpg", "Delmas — Ouest"),
    ("villa.jpg", "Architecture contemporaine en pierre"),
    ("ouanaminthe.jpg", "Ouanaminthe — Nord-Est"),
    ("ferrier.jpg", "Ferrier — Nord-Est"),
]


def hero_diaporama(titre: str, sous_titre: str, eyebrow: str = "Ayiti Data Hub", hauteur: int = 360,
                   intervalle_s: int = 6) -> None:
    """Bannière d'accueil : photos qui défilent en fondu + date et heure en direct (Haïti et heure du visiteur).

    Les images ajoutées par l'administrateur dans la rubrique « Accueil » (assets/uploads/accueil/) s'ajoutent au diaporama.
    """
    import html as _h
    import json

    import streamlit.components.v1 as components

    diapos = [(f"data:image/jpeg;base64,{image_b64(n)}", c) for n, c in DIAPORAMA_DEFAUT if image_b64(n)]
    up = ASSETS / "uploads" / "accueil"
    if up.exists():
        for p in sorted(up.iterdir()):
            if p.suffix.lower() in (".jpg", ".jpeg", ".png", ".webp"):
                mime = "png" if p.suffix.lower() == ".png" else "webp" if p.suffix.lower() == ".webp" else "jpeg"
                diapos.append((f"data:image/{mime};base64,{base64.b64encode(p.read_bytes()).decode()}",
                               p.stem.replace("_", " ").capitalize()))
    slides = "".join(f"<div class='s{' on' if i == 0 else ''}' style=\"background-image:url('{src}')\"></div>"
                     for i, (src, _) in enumerate(diapos))
    points = "".join(f"<button class='d{' on' if i == 0 else ''}' aria-label='Photo {i + 1}' data-i='{i}'></button>"
                     for i in range(len(diapos)))
    legendes = json.dumps([c for _, c in diapos], ensure_ascii=False)
    page = f"""<!doctype html><html><head><meta charset="utf-8">
<link href="https://fonts.googleapis.com/css2?family=Fraunces:opsz,wght@9..144,700&family=Source+Sans+3:wght@400;600;700&display=swap" rel="stylesheet">
<style>
*{{box-sizing:border-box;margin:0;padding:0}} body{{background:transparent;font-family:'Source Sans 3',Arial,sans-serif}}
.h{{position:relative;height:{hauteur}px;border-radius:18px;overflow:hidden;background:#0d1b4c}}
.s{{position:absolute;inset:0;background-size:cover;background-position:center;opacity:0;transform:scale(1.06);
   transition:opacity 1.4s ease, transform {intervalle_s + 2}s linear}}
.s.on{{opacity:1;transform:scale(1)}}
.h::after{{content:"";position:absolute;inset:0;background:linear-gradient(180deg,rgba(0,20,80,.10) 15%,rgba(0,14,60,.85) 100%)}}
.in{{position:absolute;z-index:2;left:0;right:0;bottom:0;padding:1.6rem 2rem;color:#fff}}
.eb{{text-transform:uppercase;letter-spacing:.14em;font-size:.78rem;font-weight:700;color:#ffd6dc}}
h1{{font-family:'Fraunces',Georgia,serif;font-size:2.7rem;line-height:1.05;margin:.25rem 0 .35rem}}
p{{color:#e8ecff;font-size:1.08rem;max-width:780px;line-height:1.45}}
.clk{{position:absolute;z-index:3;top:16px;right:16px;background:rgba(0,14,60,.55);backdrop-filter:blur(6px);
     border:1px solid rgba(255,255,255,.25);border-radius:12px;padding:.55rem .85rem;color:#fff;text-align:right;min-width:210px}}
.clk .t{{font-family:'Fraunces',Georgia,serif;font-size:1.65rem;line-height:1}}
.clk .dt{{font-size:.85rem;color:#e8ecff;margin-top:.2rem}}
.clk .lo{{font-size:.75rem;color:#c9d2ff;margin-top:.3rem;border-top:1px solid rgba(255,255,255,.2);padding-top:.3rem}}
.cap{{position:absolute;z-index:3;top:16px;left:16px;background:rgba(0,0,0,.45);color:#fff;font-size:.8rem;
     padding:.25rem .6rem;border-radius:999px}}
.dots{{position:absolute;z-index:3;right:18px;bottom:16px;display:flex;gap:6px}}
.d{{width:9px;height:9px;border-radius:50%;border:0;background:rgba(255,255,255,.45);cursor:pointer}} .d.on{{background:#fff;width:22px;border-radius:5px}}
.band{{position:absolute;z-index:3;left:0;right:0;top:0;height:5px;background:linear-gradient(90deg,#00209F 0 50%,#D21034 50% 100%)}}
@media (max-width:640px){{h1{{font-size:1.8rem}} .in{{padding:1rem}} .clk{{min-width:0;padding:.4rem .6rem}} .clk .t{{font-size:1.2rem}} .cap{{display:none}}}}
</style></head><body>
<div class="h" id="h">{slides}<div class="band"></div>
 <div class="cap" id="cap"></div>
 <div class="clk"><div class="t" id="t">--:--</div><div class="dt" id="dt"></div><div class="lo" id="lo"></div></div>
 <div class="in"><div class="eb">{_h.escape(eyebrow)}</div><h1>{_h.escape(titre)}</h1><p>{_h.escape(sous_titre)}</p></div>
 <div class="dots">{points}</div></div>
<script>
const S=[...document.querySelectorAll('.s')],D=[...document.querySelectorAll('.d')],L={legendes};let i=0,tm;
function go(n){{S[i].classList.remove('on');D[i].classList.remove('on');i=(n+S.length)%S.length;
 S[i].classList.add('on');D[i].classList.add('on');document.getElementById('cap').textContent='📷 '+L[i];}}
function auto(){{clearInterval(tm);tm=setInterval(()=>go(i+1),{intervalle_s * 1000});}}
D.forEach(b=>b.onclick=()=>{{go(+b.dataset.i);auto();}});
const H=document.getElementById('h');H.onmouseenter=()=>clearInterval(tm);H.onmouseleave=auto;
document.getElementById('cap').textContent='📷 '+L[0];auto();
function tick(){{const n=new Date();
 const o={{timeZone:'America/Port-au-Prince'}};
 document.getElementById('t').textContent=n.toLocaleTimeString('fr-FR',{{...o,hour:'2-digit',minute:'2-digit',second:'2-digit'}});
 const ds=n.toLocaleDateString('fr-FR',{{...o,weekday:'long',day:'numeric',month:'long',year:'numeric'}});
 document.getElementById('dt').textContent=ds.charAt(0).toUpperCase()+ds.slice(1)+' · heure d\u2019Haïti';
 const tz=Intl.DateTimeFormat().resolvedOptions().timeZone||'';
 document.getElementById('lo').textContent='Chez vous : '+n.toLocaleTimeString('fr-FR',{{hour:'2-digit',minute:'2-digit'}})+(tz?' ('+tz.split('/').pop().replace('_',' ')+')':'');}}
tick();setInterval(tick,1000);
</script></body></html>"""
    components.html(page, height=hauteur + 6)
