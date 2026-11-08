"""Gouvernance électronique : données, pyramide institutionnelle, carte à calques, figures pour les exports."""
from __future__ import annotations

import html as H
import json

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
import plotly.graph_objects as go  # noqa: E402
from matplotlib.collections import PolyCollection  # noqa: E402

from src.rapports import _png  # noqa: E402
from src.utils import CURATED, GEO, PROCESSED  # noqa: E402

CHEFS_LIEUX = {"HT01": "Port-au-Prince", "HT02": "Jacmel", "HT03": "Cap-Haïtien", "HT04": "Fort-Liberté", "HT05": "Gonaïves",
               "HT06": "Hinche", "HT07": "Les Cayes", "HT08": "Jérémie", "HT09": "Port-de-Paix", "HT10": "Miragoâne"}
NOM_DEP = {"HT01": "Ouest", "HT02": "Sud-Est", "HT03": "Nord", "HT04": "Nord-Est", "HT05": "Artibonite", "HT06": "Centre",
           "HT07": "Sud", "HT08": "Grand'Anse", "HT09": "Nord-Ouest", "HT10": "Nippes"}
COUL_TYPE = {"Frontière terrestre": "#d03b3b", "Port": "#2a78d6", "Aéroport": "#6250d6", "Axe routier": "#eb6834",
             "Zone économique": "#1baf7a"}
COUL_PHASE = {"Reprendre": "#d03b3b", "Tenir": "#eda100", "Construire": "#1baf7a"}
COUL_REL = {"Rapport": "#2a78d6", "Contrôle": "#d03b3b", "Coordination sécurité": "#eb6834", "Commandement": "#52514e",
            "Planification": "#1baf7a", "Retour / financement": "#6250d6"}


# ------------------------------------------------------------------ données
def acteurs() -> pd.DataFrame:
    return pd.read_csv(CURATED / "gouvernance_acteurs.csv")


def relations() -> pd.DataFrame:
    return pd.read_csv(CURATED / "gouvernance_relations.csv")


def points_controle() -> pd.DataFrame:
    return pd.read_csv(CURATED / "points_controle.csv")


def plan_departements() -> pd.DataFrame:
    return pd.read_csv(CURATED / "plan_securite_departements.csv")


def plan_mesures() -> pd.DataFrame:
    return pd.read_csv(CURATED / "plan_securite_mesures.csv")


def geo_departements() -> dict:
    return json.loads((GEO / "departements.geojson").read_text(encoding="utf-8"))


def communes_maillage() -> pd.DataFrame:
    """146 communes + nombre de sections communales (base du quadrillage)."""
    c = pd.read_csv(PROCESSED / "communes.csv")
    s = pd.read_csv(PROCESSED / "sections_communales.csv")
    n = s.groupby("adm2_pcode").size().rename("nb_sections")
    c = c.merge(n, left_on="adm2_pcode", right_index=True, how="left")
    c["nb_sections"] = c.nb_sections.fillna(0).astype(int)
    c["departement"] = c.adm1_pcode.map(NOM_DEP)
    return c[["adm2_pcode", "commune", "adm1_pcode", "departement", "population", "nb_sections", "lat", "lon"]]


def chefs_lieux() -> pd.DataFrame:
    c = communes_maillage()
    rows = []
    for p, nom in CHEFS_LIEUX.items():
        m = c[(c.adm1_pcode == p) & (c.commune.str.lower().str.replace("les ", "") == nom.lower().replace("les ", ""))]
        if len(m):
            r = m.iloc[0]
            rows.append({"adm1_pcode": p, "departement": NOM_DEP[p], "chef_lieu": nom, "lat": r.lat, "lon": r.lon})
    return pd.DataFrame(rows)


def quadrillage() -> pd.DataFrame:
    """Tableau du maillage par département : qui fait quoi, combien d'unités."""
    c = communes_maillage()
    g = c.groupby(["adm1_pcode", "departement"]).agg(communes=("commune", "size"), sections=("nb_sections", "sum"),
                                                     population=("population", "sum")).reset_index()
    pc = points_controle().groupby("adm1_pcode").size().rename("points_controle")
    g = g.merge(pc, left_on="adm1_pcode", right_index=True, how="left").fillna({"points_controle": 0})
    g["chef_lieu"] = g.adm1_pcode.map(CHEFS_LIEUX)
    g["delegue"] = 1
    g["direction_pnh"] = 1
    g["bed_cep"] = 1
    g["points_focaux_numeriques"] = g.communes + g.sections  # 1 par mairie + 1 par CASEC
    g["points_controle"] = g.points_controle.astype(int)
    return g[["departement", "chef_lieu", "population", "communes", "sections", "delegue", "direction_pnh", "bed_cep",
              "points_focaux_numeriques", "points_controle"]].sort_values("population", ascending=False)


# ------------------------------------------------------------------ pyramide (HTML interactif)
def pyramide_html(a: pd.DataFrame, r: pd.DataFrame, hauteur: int = 720) -> str:
    noms = dict(zip(a.id, a.sigle))
    data = []
    for _, x in a.iterrows():
        sort = r[r.source == x.id]
        entre = r[r.cible == x.id]
        data.append({
            "id": x.id, "niv": int(x.niveau), "etage": x.etage, "acteur": x.acteur, "sigle": x.sigle, "nb": str(x.nombre),
            "role": x.role, "rapporte": x.rapporte_a, "controle": x.controle_par, "base": x.base_legale,
            "out": [f"{t.type} → {noms.get(t.cible, t.cible)} : {t.contenu} ({t.frequence}, {t.canal})" for t in sort.itertuples()],
            "in": [f"{t.type} ← {noms.get(t.source, t.source)} : {t.contenu} ({t.frequence})" for t in entre.itertuples()],
        })
    etages = (a[a.niveau > 0].groupby("niveau").agg(etage=("etage", "first"), sigles=("sigle", lambda s: " · ".join(s)))
              .reset_index().sort_values("niveau"))
    n = len(etages)
    lignes = []
    for i, e in enumerate(etages.itertuples()):
        larg = 34 + 66 * i / max(n - 1, 1)
        lignes.append(f"<button class='lv' data-n='{e.niveau}' style='width:{larg:.0f}%;"
                      f"background:hsl(228,{85 - i * 6}%,{24 + i * 5}%)'><span class='e'>{H.escape(e.etage)}</span>"
                      f"<span class='s'>{H.escape(e.sigles)}</span></button>")
    transv = a[a.niveau == 0]
    piliers = "".join(f"<button class='pil' data-id='{t.id}'><b>{H.escape(t.sigle)}</b><small>{H.escape(t.famille)}</small></button>"
                      for t in transv.itertuples())
    return f"""<!doctype html><html><head><meta charset="utf-8">
<style>
:root{{--ink:#0b0b0b;--ink2:#52514e;--line:#e6e5e0;--card:#fff;--bg:transparent}}
@media (prefers-color-scheme:dark){{:root{{--ink:#f0efec;--ink2:#c3c2b7;--line:#383835;--card:#1f1f1d}}}}
*{{box-sizing:border-box}} body{{margin:0;font-family:'Source Sans 3',Arial,sans-serif;color:var(--ink);background:var(--bg)}}
.wrap{{display:grid;grid-template-columns:minmax(0,1.25fr) minmax(0,1fr);gap:16px}}
@media (max-width:760px){{.wrap{{grid-template-columns:1fr}}}}
.pyr{{display:flex;flex-direction:column;align-items:center;gap:6px}}
.lv{{border:0;color:#fff;padding:10px 12px;cursor:pointer;clip-path:polygon(4% 0,96% 0,100% 100%,0 100%);text-align:center;
    transition:transform .15s, filter .15s;min-height:58px}}
.lv:hover,.lv.on{{transform:scale(1.02);filter:brightness(1.15)}}
.lv .e{{display:block;font-weight:700;font-size:14px}} .lv .s{{display:block;font-size:12px;opacity:.9}}
.arrow{{font-size:12px;color:var(--ink2);text-align:center;margin:4px 0}}
.pils{{display:flex;flex-wrap:wrap;gap:6px;justify-content:center;margin-top:10px}}
.pil{{border:1px solid var(--line);background:var(--card);color:var(--ink);border-radius:10px;padding:6px 10px;cursor:pointer;
     display:flex;flex-direction:column;align-items:center;border-top:4px solid #D21034}}
.pil small{{color:var(--ink2);font-size:11px}} .pil.on{{outline:2px solid #00209F}}
.panel{{border:1px solid var(--line);border-radius:14px;background:var(--card);padding:14px;max-height:{hauteur - 20}px;overflow:auto}}
.card{{border-bottom:1px solid var(--line);padding:8px 0}} .card:last-child{{border:0}}
.card h4{{margin:0 0 4px;font-size:15px}} .tag{{display:inline-block;background:#eef2ff;color:#00209F;border-radius:999px;padding:0 8px;font-size:11px;font-weight:700;margin-right:4px}}
.k{{color:var(--ink2);font-size:12.5px;margin:2px 0}} ul{{margin:4px 0 0 16px;padding:0;font-size:12.5px}}
.leg{{font-size:12px;color:var(--ink2);margin-top:8px;text-align:center}}
</style></head><body><div class="wrap">
<div><div class="arrow">▲ décisions et instructions descendent · rapports et données remontent ▲</div>
<div class="pyr">{''.join(lignes)}</div>
<div class="leg">Organes transversaux (contrôlent ou sécurisent tous les étages) :</div>
<div class="pils">{piliers}</div></div>
<div class="panel" id="p"><b>Cliquez sur un étage de la pyramide ou sur un organe transversal</b>
<p class="k">Chaque fiche indique le rôle, à qui l'acteur rend compte, qui le contrôle, la base légale et les flux d'information entrants et sortants.</p></div>
</div>
<script>
const A={json.dumps(data, ensure_ascii=False)};
const esc=s=>String(s).replace(/[&<>]/g,c=>({{'&':'&amp;','<':'&lt;','>':'&gt;'}}[c]));
function fiche(x){{return `<div class="card"><h4>${{esc(x.acteur)}}</h4><span class="tag">${{esc(x.sigle)}}</span><span class="tag">${{esc(x.nb)}}</span>
<p class="k">${{esc(x.role)}}</p><p class="k"><b>Rend compte à :</b> ${{esc(x.rapporte)}}</p><p class="k"><b>Contrôlé par :</b> ${{esc(x.controle)}}</p>
<p class="k"><b>Base légale :</b> ${{esc(x.base)}}</p>
${{x.out.length?'<p class="k"><b>Flux sortants</b></p><ul>'+x.out.map(o=>'<li>'+esc(o)+'</li>').join('')+'</ul>':''}}
${{x.in.length?'<p class="k"><b>Flux entrants</b></p><ul>'+x.in.map(o=>'<li>'+esc(o)+'</li>').join('')+'</ul>':''}}</div>`}}
const P=document.getElementById('p');
function off(){{document.querySelectorAll('.on').forEach(e=>e.classList.remove('on'))}}
document.querySelectorAll('.lv').forEach(b=>b.onclick=()=>{{off();b.classList.add('on');
 const L=A.filter(x=>x.niv==+b.dataset.n);P.innerHTML='<b>'+esc(L[0].etage)+'</b>'+L.map(fiche).join('');}});
document.querySelectorAll('.pil').forEach(b=>b.onclick=()=>{{off();b.classList.add('on');P.innerHTML=fiche(A.find(x=>x.id==b.dataset.id));}});
document.querySelector('.lv:last-child').click();
</script></body></html>"""


def sankey_relations(a: pd.DataFrame, r: pd.DataFrame) -> go.Figure:
    ids = list(dict.fromkeys(list(r.source) + list(r.cible)))
    lab = dict(zip(a.id, a.sigle))
    idx = {k: i for i, k in enumerate(ids)}
    coul = [COUL_REL.get(t, "#8a8984") for t in r.type]
    rgba = [f"rgba({int(c[1:3], 16)},{int(c[3:5], 16)},{int(c[5:7], 16)},0.45)" for c in coul]
    fig = go.Figure(go.Sankey(
        arrangement="snap",
        node=dict(label=[lab.get(i, i) for i in ids], pad=14, thickness=16, color="#00209F", line=dict(width=0)),
        link=dict(source=[idx[s] for s in r.source], target=[idx[c] for c in r.cible], value=[1] * len(r), color=rgba,
                  customdata=r.type + " — " + r.contenu + " (" + r.frequence + ")",
                  hovertemplate="%{source.label} → %{target.label}<br>%{customdata}<extra></extra>")))
    fig.update_layout(height=560, margin=dict(l=4, r=4, t=10, b=10), hovermode=False)
    return fig


# ------------------------------------------------------------------ carte à calques (folium)
def carte_calques(mode: str = "gouvernance", calques: tuple = ()):
    """mode : 'gouvernance' (maillage administratif) ou 'securite' (phases par département)."""
    import folium
    from folium.plugins import Fullscreen

    m = folium.Map(location=[18.95, -72.7], zoom_start=8, tiles=None, control_scale=True)
    folium.TileLayer("https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png",
                     attr="© OpenStreetMap contributors © CARTO", name="Fond clair").add_to(m)
    folium.TileLayer("https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
                     attr="Imagery © Esri", name="Satellite").add_to(m)
    geo = geo_departements()
    pdep = plan_departements().set_index("adm1_pcode")

    def style(f):
        p = f["id"]
        if mode == "securite" and p in pdep.index:
            c = COUL_PHASE.get(pdep.loc[p, "phase_proposee"], "#cde2fb")
            return {"fillColor": c, "color": "white", "weight": 1.5, "fillOpacity": 0.45}
        return {"fillColor": "#9ec5f4", "color": "#00209F", "weight": 1.2, "fillOpacity": 0.18}

    def popup_dep(p):
        if mode == "securite" and p in pdep.index:
            x = pdep.loc[p]
            return (f"<b>{H.escape(NOM_DEP[p])}</b> — phase proposée : <b>{x.phase_proposee}</b><br>"
                    f"Zone prioritaire (gouv. Andrésol) : {x.priorite_andresol}<br><b>Points chauds :</b> {H.escape(x.points_chauds_et_axes)}<br>"
                    f"<b>Sécurité :</b> {H.escape(x.securite_mesures_territoriales)}<br><b>Projets (programme Etzer) :</b> "
                    f"{H.escape(x.programme_etzer_projets_localises)}")
        q = quadrillage().set_index("departement")
        d = NOM_DEP[p].replace("Grand'Anse", "Grand'Anse")
        x = q.loc[d] if d in q.index else None
        if x is None:
            return NOM_DEP[p]
        return (f"<b>Département {H.escape(d)}</b> — chef-lieu {x.chef_lieu}<br>{int(x.communes)} communes · {int(x.sections)} sections "
                f"communales<br>1 délégué · 1 Conseil départemental · 1 direction PNH · 1 BED<br>"
                f"{int(x.points_focaux_numeriques)} points focaux numériques à former")

    g_dep = folium.FeatureGroup(name="Départements", show=True)
    for f in geo["features"]:
        folium.GeoJson(f, style_function=style, tooltip=NOM_DEP.get(f["id"], f["id"]),
                       popup=folium.Popup(popup_dep(f["id"]), max_width=380)).add_to(g_dep)
    g_dep.add_to(m)

    cl = chefs_lieux()
    c = communes_maillage()
    if "rapports" in calques:
        g_f = folium.FeatureGroup(name="Flux de rapports (commune → chef-lieu → MICT)", show=True)
        pap = cl[cl.adm1_pcode == "HT01"].iloc[0]
        for r in c.itertuples():
            ch = cl[cl.adm1_pcode == r.adm1_pcode]
            if len(ch) and not np.isnan(r.lat):
                folium.PolyLine([(r.lat, r.lon), (ch.iloc[0].lat, ch.iloc[0].lon)], color="#2a78d6", weight=1, opacity=0.55).add_to(g_f)
        for r in cl.itertuples():
            if r.adm1_pcode != "HT01":
                folium.PolyLine([(r.lat, r.lon), (pap.lat, pap.lon)], color="#D21034", weight=3.5, opacity=0.8,
                                tooltip=f"{r.departement} → MICT / Centre national (Port-au-Prince)").add_to(g_f)
        g_f.add_to(m)
    if "communes" in calques:
        g_c = folium.FeatureGroup(name="Mairies, BEC, commissariats (146 communes)", show=True)
        for r in c.dropna(subset=["lat"]).itertuples():
            folium.CircleMarker((r.lat, r.lon), radius=3 + min(r.nb_sections, 12) * 0.4, color="#00209F", weight=1,
                                fill=True, fill_opacity=0.8,
                                tooltip=f"{r.commune} ({r.departement}) — {r.nb_sections} sections communales (CASEC/ASEC)",
                                popup=f"<b>{H.escape(r.commune)}</b><br>Mairie + Assemblée municipale<br>BEC (CEP) · commissariat PNH<br>"
                                      f"{r.nb_sections} CASEC/ASEC · {int(r.population):,} hab.".replace(",", " ")).add_to(g_c)
        g_c.add_to(m)
    if "chefs" in calques:
        g_l = folium.FeatureGroup(name="Chefs-lieux (délégué, BED, direction PNH)", show=True)
        for r in cl.itertuples():
            folium.Marker((r.lat, r.lon), icon=folium.Icon(color="darkblue", icon="star"),
                          tooltip=f"★ {r.chef_lieu} — chef-lieu {r.departement}",
                          popup=f"<b>{r.chef_lieu}</b><br>Délégué départemental · Conseil départemental<br>"
                                f"Direction départementale PNH · BED (CEP)").add_to(g_l)
        g_l.add_to(m)
    if "controle" in calques:
        ICON = {"Frontière terrestre": ("red", "flag"), "Port": ("blue", "anchor"), "Aéroport": ("purple", "plane"),
                "Axe routier": ("orange", "road"), "Zone économique": ("green", "briefcase")}
        for typ, sous in points_controle().groupby("type"):
            g = folium.FeatureGroup(name=f"Points de contrôle : {typ}", show=True)
            col, ic = ICON.get(typ, ("gray", "info-sign"))
            for r in sous.itertuples():
                folium.Marker((r.lat, r.lon), icon=folium.Icon(color=col, icon=ic, prefix="fa"),
                              tooltip=f"{r.nom}",
                              popup=folium.Popup(f"<b>{H.escape(r.nom)}</b><br><i>{typ}</i><br><b>Institutions :</b> {H.escape(r.institutions)}"
                                                 f"<br><b>Flux suivis :</b> {H.escape(r.flux_suivis)}<br><b>Programme Etzer :</b> "
                                                 f"{H.escape(str(r.mesure_programme_etzer))}", max_width=340)).add_to(g)
            g.add_to(m)
    folium.LayerControl(collapsed=False).add_to(m)
    Fullscreen().add_to(m)
    return m


# ------------------------------------------------------------------ figures matplotlib (exports)
def fig_pyramide(a: pd.DataFrame) -> bytes:
    et = a[a.niveau > 0].groupby("niveau").agg(etage=("etage", "first"), sigles=("sigle", lambda s: " · ".join(s))).reset_index()
    n = len(et)
    fig, ax = plt.subplots(figsize=(10, 6.4))
    ax.axis("off")
    for i, e in enumerate(et.itertuples()):
        y0, y1 = n - i - 1, n - i - 0.08
        w0, w1 = 0.36 + 0.64 * (i + 1) / n, 0.36 + 0.64 * i / n
        col = plt.cm.Blues(0.95 - i * 0.12)
        ax.add_patch(plt.Polygon([(-w0, y0), (w0, y0), (w1, y1), (-w1, y1)], color=col))
        ax.text(0, (y0 + y1) / 2 + 0.13, e.etage, ha="center", va="center", color="white" if i < 4 else "#0b0b0b",
                fontsize=11, fontweight="bold")
        ax.text(0, (y0 + y1) / 2 - 0.2, e.sigles, ha="center", va="center", color="white" if i < 4 else "#0b0b0b", fontsize=8.5)
    tr = a[a.niveau == 0]
    for j, t in enumerate(tr.itertuples()):
        ax.text(1.28, n - 0.5 - j * (n / max(len(tr), 1)), f"{t.sigle}\n{t.famille}", ha="center", va="center", fontsize=8.5,
                bbox=dict(boxstyle="round,pad=0.4", fc="white", ec="#D21034", lw=1.4))
    ax.annotate("", xy=(-1.12, n - 0.2), xytext=(-1.12, 0.2), arrowprops=dict(arrowstyle="->", color="#2a78d6", lw=2))
    ax.text(-1.2, n / 2, "rapports et données remontent", rotation=90, ha="center", va="center", fontsize=9, color="#2a78d6")
    ax.set_xlim(-1.3, 1.55)
    ax.set_ylim(-0.1, n + 0.1)
    ax.set_title("Pyramide de gouvernance électronique — Haïti (Constitution 1987 amendée, décrets 2006)", fontsize=12)
    return _png(fig)


def fig_carte(mode: str = "gouvernance", titre: str = "") -> bytes:
    geo = geo_departements()
    pdep = plan_departements().set_index("adm1_pcode")
    fig, ax = plt.subplots(figsize=(10, 7))
    polys, cols = [], []
    for f in geo["features"]:
        g = f["geometry"]
        parts = g["coordinates"] if g["type"] == "MultiPolygon" else [g["coordinates"]]
        for p in parts:
            polys.append(np.array(p[0]))
            cols.append(COUL_PHASE.get(pdep.loc[f["id"], "phase_proposee"], "#cde2fb") if mode == "securite" else "#dce9fb")
    ax.add_collection(PolyCollection(polys, facecolors=cols, edgecolors="white", linewidths=0.8, alpha=0.85))
    cl = chefs_lieux()
    c = communes_maillage().dropna(subset=["lat"])
    if mode == "gouvernance":
        for r in c.itertuples():
            ch = cl[cl.adm1_pcode == r.adm1_pcode]
            if len(ch):
                ax.plot([r.lon, ch.iloc[0].lon], [r.lat, ch.iloc[0].lat], color="#2a78d6", lw=0.4, alpha=0.6)
        pap = cl[cl.adm1_pcode == "HT01"].iloc[0]
        for r in cl.itertuples():
            ax.plot([r.lon, pap.lon], [r.lat, pap.lat], color="#D21034", lw=1.6, alpha=0.8)
        ax.scatter(c.lon, c.lat, s=6 + c.nb_sections * 1.5, color="#00209F", zorder=3, label="Mairies (taille = nb de sections)")
    pc = points_controle()
    for typ, s in pc.groupby("type"):
        ax.scatter(s.lon, s.lat, s=60 if typ == "Frontière terrestre" else 46, marker="D" if typ != "Frontière terrestre" else "^",
                   color=COUL_TYPE.get(typ, "#888"), edgecolor="#0b0b0b" if typ == "Frontière terrestre" else "white",
                   linewidths=0.8, zorder=4, label=typ)
    ax.scatter(cl.lon, cl.lat, s=140, marker="*", color="#0b0b0b", zorder=5, label="Chefs-lieux")
    for r in cl.itertuples():
        ax.text(r.lon + 0.04, r.lat + 0.04, r.chef_lieu, fontsize=8, color="#0b0b0b", zorder=6)
    if mode == "securite":
        from matplotlib.patches import Patch
        h, lab = ax.get_legend_handles_labels()
        h += [Patch(color=v, label=f"Phase : {k}") for k, v in COUL_PHASE.items()]
        ax.legend(handles=h, loc="center left", bbox_to_anchor=(1.0, 0.5), fontsize=8, frameon=False)
    else:
        ax.legend(loc="center left", bbox_to_anchor=(1.0, 0.5), fontsize=8, frameon=False)
    ax.set_xlim(-74.55, -71.55)
    ax.set_ylim(17.95, 20.15)
    ax.set_aspect("equal")
    ax.grid(False)
    ax.set_xticks([])
    ax.set_yticks([])
    for s in ax.spines.values():
        s.set_visible(False)
    ax.set_title(titre or "Calque territorial : maillage administratif, flux de rapports et points de contrôle")
    return _png(fig)
