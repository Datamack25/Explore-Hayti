import html as H
import json

import folium
import pandas as pd
import streamlit as st
import streamlit.components.v1 as components
from streamlit_folium import st_folium

from src import gouvernance as G
from src.exports_doc import panneau_exports
from src.utils import CURATED
from src.ui import analyse_box, entete, kpis, note, pied, setup

setup("Processus électoral", "🗳️")
entete("Comment fonctionnent les élections en Haïti",
       "De la carte d'identité au résultat définitif : chaque étape, ses acteurs, ses faiblesses et ce qui pourrait l'améliorer.")

E = pd.read_csv(CURATED / "elections_processus.csv")
kpis([
    {"lab": "Étapes", "val": str(len(E)), "sub": "du cadre légal au contentieux", "style": "accent"},
    {"lab": "Nouveaux inscrits", "val": "906 800+", "sub": "au 21 sept. 2026 (Haiti Policy House)"},
    {"lab": "Partis approuvés", "val": "316 / 320", "sub": "juillet 2026"},
    {"lab": "1er tour prévu", "val": "18 juil. 2027", "sub": "calendrier CEP n° 3 (oct. 2026)", "style": "alert"},
    {"lab": "Mode de vote", "val": "Papier", "sub": "dépouillement manuel ; tabulation centralisée"},
])

t_flux, t_carte, t_mode, t_amel, t_spec, t_exp = st.tabs([
    "🔁 Les 10 étapes", "🗺️ Organisation sur le territoire", "🖥️ Manuel ou électronique ?", "🛠️ Améliorations", "🌍 Diaspora & déplacés", "📥 Exports"])

with t_flux:
    data = E.to_dict("records")
    cartes = "".join(f"<button class='st' data-i='{i}'><span class='n'>{r['ordre']}</span>{H.escape(r['etape'])}</button>"
                     for i, r in enumerate(data))
    components.html(f"""<!doctype html><html><head><meta charset="utf-8"><style>
:root{{--ink:#0b0b0b;--ink2:#52514e;--line:#e6e5e0;--card:#fff}}
@media (prefers-color-scheme:dark){{:root{{--ink:#f0efec;--ink2:#c3c2b7;--line:#383835;--card:#1f1f1d}}}}
body{{margin:0;font-family:'Source Sans 3',Arial,sans-serif;color:var(--ink)}}
.flow{{display:grid;grid-template-columns:repeat(5,minmax(0,1fr));gap:8px}}
@media (max-width:760px){{.flow{{grid-template-columns:repeat(2,minmax(0,1fr))}}}}
.st{{position:relative;border:1px solid var(--line);background:var(--card);color:var(--ink);border-radius:12px;padding:10px 8px 10px 38px;
    text-align:left;cursor:pointer;font-size:13.5px;font-weight:600;min-height:58px}}
.st .n{{position:absolute;left:8px;top:10px;width:22px;height:22px;border-radius:50%;background:#00209F;color:#fff;
       display:flex;align-items:center;justify-content:center;font-size:12px}}
.st.on{{outline:2px solid #D21034}} .st.on .n{{background:#D21034}}
.d{{margin-top:12px;border:1px solid var(--line);border-radius:14px;background:var(--card);padding:14px}}
.d h3{{margin:0 0 6px;font-family:Fraunces,Georgia,serif}} .g{{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:10px}}
@media (max-width:760px){{.g{{grid-template-columns:1fr}}}}
.b{{border-left:4px solid #00209F;padding:4px 10px;font-size:13.5px}} .b.r{{border-color:#ec835a}} .b.v{{border-color:#1baf7a}}
.b b{{display:block;font-size:11.5px;text-transform:uppercase;letter-spacing:.05em;color:var(--ink2)}}
</style></head><body><div class="flow">{cartes}</div><div class="d" id="d"></div><script>
const E={json.dumps(data, ensure_ascii=False)};const e=s=>String(s).replace(/[&<>]/g,c=>({{'&':'&amp;','<':'&lt;','>':'&gt;'}}[c]));
function show(i){{document.querySelectorAll('.st').forEach(b=>b.classList.toggle('on',+b.dataset.i===i));const x=E[i];
document.getElementById('d').innerHTML=`<h3>${{x.ordre}}. ${{e(x.etape)}}</h3><p>${{e(x.description)}}</p><div class="g">
<div class="b"><b>Acteurs</b>${{e(x.acteurs)}}</div><div class="b"><b>Document clé</b>${{e(x.document_cle)}}</div>
<div class="b r"><b>Faiblesses observées</b>${{e(x.faiblesses)}}</div><div class="b v"><b>Amélioration proposée</b>${{e(x.amelioration_proposee)}}</div></div>`;}}
document.querySelectorAll('.st').forEach(b=>b.onclick=()=>show(+b.dataset.i));show(0);
</script></body></html>""", height=470, scrolling=True)
    st.dataframe(E, hide_index=True, use_container_width=True, column_config={"source": st.column_config.LinkColumn("source")})

with t_carte:
    st.markdown("**CEP** (Port-au-Prince) → **10 BED** (bureaux électoraux départementaux, aux chefs-lieux) → **BEC** (bureaux "
                "électoraux communaux) → **centres de vote** → **bureaux de vote**. Les procès-verbaux remontent en sens inverse "
                "jusqu'au **centre de tabulation des votes**.")
    m = folium.Map(location=[18.95, -72.7], zoom_start=8, tiles=None)
    folium.TileLayer("https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png", attr="© OpenStreetMap © CARTO").add_to(m)
    cl, c = G.chefs_lieux(), G.communes_maillage().dropna(subset=["lat"])
    pap = cl[cl.adm1_pcode == "HT01"].iloc[0]
    for r in c.itertuples():
        ch = cl[cl.adm1_pcode == r.adm1_pcode].iloc[0]
        folium.PolyLine([(r.lat, r.lon), (ch.lat, ch.lon)], color="#6250d6", weight=1, opacity=0.5).add_to(m)
        folium.CircleMarker((r.lat, r.lon), radius=4, color="#6250d6", fill=True, fill_opacity=0.9,
                            tooltip=f"BEC {r.commune} — {r.nb_sections} sections communales").add_to(m)
    for r in cl.itertuples():
        folium.PolyLine([(r.lat, r.lon), (pap.lat, pap.lon)], color="#D21034", weight=3, opacity=0.8).add_to(m)
        folium.Marker((r.lat, r.lon), icon=folium.Icon(color="darkblue", icon="inbox", prefix="fa"),
                      tooltip=f"BED {r.departement} ({r.chef_lieu})").add_to(m)
    folium.Marker((pap.lat + 0.03, pap.lon + 0.05), icon=folium.Icon(color="red", icon="star", prefix="fa"),
                  tooltip="CEP + centre de tabulation des votes (Port-au-Prince)").add_to(m)
    st_folium(m, height=560, use_container_width=True, returned_objects=[])

with t_mode:
    st.dataframe(pd.DataFrame({
        "critère": ["Coût", "Électricité / réseau", "Confiance du public", "Vitesse des résultats", "Vérifiabilité (recomptage)",
                    "Risque de fraude", "Faisabilité 2027"],
        "Manuel actuel (papier + PV transportés)": ["Faible", "Inutile", "Faible (opacité de la tabulation)", "Lente (jours)",
                                                   "Oui (bulletins)", "PV perdus ou écartés", "Oui"],
        "Hybride proposé (papier + photo du PV + biométrie)": ["Moyen (tablettes)", "Batterie + envoi différé", "Élevée (PV publiés)",
                                                             "Rapide (heures)", "Oui (papier conservé)", "Réduit (double canal)", "Oui, par étapes"],
        "Vote électronique intégral (machines)": ["Élevé", "Indispensable", "Fragile (boîte noire)", "Très rapide", "Difficile sans trace papier",
                                                  "Risque informatique", "Non"],
    }), hide_index=True, use_container_width=True)
    analyse_box("Recommandation", [
        "Garder le **bulletin papier** (preuve physique, recomptage possible) et **numériser la transmission** : photo du PV au bureau, "
        "envoi chiffré dès qu'un réseau est disponible, publication bureau par bureau.",
        "La comparaison automatique entre l'image du PV et l'original papier rend visible toute modification en route.",
        "Le vote électronique intégral n'est pas adapté au contexte : coût, électricité, et surtout confiance.",
    ])

with t_amel:
    st.dataframe(E[["ordre", "etape", "faiblesses", "amelioration_proposee"]], hide_index=True, use_container_width=True)
    analyse_box("Cinq priorités", [
        "**Registre fiable** : audit indépendant et croisement avec l'état civil (décès).",
        "**Vérification en ligne** : chaque électeur trouve son centre de vote par SMS avec sa CIN.",
        "**PV publics** : image de chaque PV en ligne, bureau par bureau, le soir du scrutin.",
        "**Contentieux rapide et motivé** : décisions publiées en créole et en français.",
        "**Données ouvertes** : résultats en CSV par bureau ; comptage parallèle par des observateurs nationaux.",
    ])

with t_spec:
    c1, c2 = st.columns(2)
    with c1:
        analyse_box("Déplacés internes (≈1,5 million)", [
            "Permettre de **voter là où l'on vit** : transfert d'inscription simplifié vers un centre proche du site de déplacement.",
            "Bureaux ONI mobiles pour refaire la CIN perdue.",
            "Centres de vote dans les sites, sécurisés par la PNH.",
        ])
    with c2:
        analyse_box("Diaspora", [
            "Le décret référendaire de 2020 prévoyait déjà le vote des Haïtiens de l'étranger (art. 14), selon des conditions fixées par le CEP.",
            "Pistes : bureaux dans les consulats des grandes villes (Miami, New York, Boston, Montréal, Paris), inscription en ligne avec la CIN, "
            "vote anticipé.",
            "Prérequis : CIN délivrée à l'étranger et registre spécifique audité.",
        ])

with t_exp:
    def blocs():
        return [
            ("h1", "1. Les étapes du processus électoral"),
            ("table", E[["ordre", "etape", "acteurs", "description", "document_cle"]]),
            ("h1", "2. Faiblesses et améliorations"),
            ("table", E[["etape", "faiblesses", "amelioration_proposee"]]),
            ("h1", "3. Manuel, hybride ou électronique"),
            ("p", "Recommandation : bulletin papier conservé, transmission numérique de l'image du procès-verbal, vérification "
                  "biométrique de la CIN et publication des résultats bureau par bureau."),
            ("h1", "4. Diaspora et déplacés"),
            ("ul", ["Transfert d'inscription vers un centre proche du lieu de déplacement.", "Bureaux ONI mobiles.",
                    "Bureaux de vote consulaires et inscription en ligne pour la diaspora."]),
        ]

    panneau_exports("elec", "Le processus électoral en Haïti", "De l'inscription au dépouillement : fonctionnement et améliorations",
                    blocs, {"processus_electoral": E},
                    sources="CEP (notes de presse 2026) ; projet de décret électoral (avril 2026) ; décret référendaire (2020) ; "
                            "Haiti Policy House ; Political Database of the Americas.")

pied("<a href='https://cephaiti.ht'>CEP</a> ; <a href='https://lequotidien509.com/wp-content/uploads/2026/04/projet-de-decret-electoral-2026-avril-2026.pdf'>projet de décret électoral</a> ; "
     "<a href='https://www.haitipolicyhouse.org/haiti-election-tracker'>Haiti Policy House</a>.")
