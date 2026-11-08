import math

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from src.charts import barres_h
from src.medias import galerie
from src.photos import fichier_en_data_uri, initiales, photo_locale, photo_wikipedia, vignette
from src.ui import SERIES, analyse_box, entete, kpis, note, pied, setup
from src.utils import CURATED

setup("Contributions au monde", "🌟")
entete("Ce qu'Haïti apporte au monde",
       "Histoire, pensée, sciences, médecine, technologie, littérature, arts, diplomatie, sport, médias : des Haïtiens et des "
       "descendants d'Haïtiens qui ont marqué leur époque — ce qu'ils ont fait, où, quand et comment.")

c = pd.read_csv(CURATED / "contributions.csv")
s = pd.read_csv(CURATED / "contributions_stats.csv")
nes = c.lien_haiti.str.startswith(("Né", "Née")).sum()
DOM_COUL = {d: (SERIES + ["#52514e", "#0d366b"])[i] for i, d in enumerate(sorted(c.domaine.unique()))}

kpis([
    {"lab": "Personnalités présentées", "val": str(len(c)), "sub": f"{c.domaine.nunique()} domaines", "style": "accent"},
    {"lab": "Nés en Haïti / Saint-Domingue", "val": str(nes), "sub": f"{len(c) - nes} descendants ou groupes"},
    {"lab": "Pays où ils se sont illustrés", "val": str(c.pays_contribution.nunique())},
    {"lab": "Diplômés vivant dans l'OCDE", "val": "> 80 %", "sub": "Banque mondiale (2005)", "style": "accent"},
    {"lab": "Haïtiens des É.-U. dans la santé", "val": "22 %", "sub": "des actifs (2024)"},
    {"lab": "Patrimoine UNESCO", "val": "3", "sub": "Citadelle · soup joumou · konpa"},
])

t_portraits, t_stats = st.tabs(["🌟 Portraits", "📊 Statistiques & carte"])

# ------------------------------------------------------------------ portraits
with t_portraits:
    f1, f2, f3 = st.columns([3, 2, 2])
    dom = f1.multiselect("Domaine", sorted(c.domaine.unique()), placeholder="Tous les domaines")
    lien = f2.radio("Lien avec Haïti", ["Tous", "Nés en Haïti", "Descendants"], horizontal=True)
    q = f3.text_input("Rechercher (nom, mot-clé, ville…)")
    cc = c.copy()
    if dom:
        cc = cc[cc.domaine.isin(dom)]
    if lien == "Nés en Haïti":
        cc = cc[cc.lien_haiti.str.startswith(("Né", "Née"))]
    elif lien == "Descendants":
        cc = cc[cc.lien_haiti.str.startswith("Descend")]
    if q:
        cc = cc[cc.apply(lambda r: q.lower() in " ".join(map(str, r.values)).lower(), axis=1)]
    ordre = st.radio("Trier par", ["Chronologie", "Domaine", "Nom"], horizontal=True)
    cc = cc.sort_values({"Chronologie": "annee_cle", "Domaine": ["domaine", "annee_cle"], "Nom": "nom"}[ordre])

    PAR_PAGE = 12
    nb_pages = max(1, math.ceil(len(cc) / PAR_PAGE))
    page = st.number_input(f"Page (sur {nb_pages}) — {len(cc)} personnalités", 1, nb_pages, 1) if nb_pages > 1 else 1
    sel = cc.iloc[(page - 1) * PAR_PAGE: page * PAR_PAGE]

    cols = st.columns(3)
    for i, r in enumerate(sel.itertuples()):
        with cols[i % 3]:
            with st.container(border=True):
                loc = photo_locale(r.nom)
                img, wpage = photo_wikipedia(r.wikipedia if isinstance(r.wikipedia, str) else "", r.nom)
                if loc:
                    st.markdown(vignette(fichier_en_data_uri(loc)), unsafe_allow_html=True)
                elif img:
                    st.markdown(vignette(img, "Photo : Wikimedia Commons (licence libre)"), unsafe_allow_html=True)
                else:
                    st.markdown(initiales(r.nom, DOM_COUL[r.domaine]), unsafe_allow_html=True)
                st.markdown(f"#### {r.nom}")
                st.markdown(f"<span class='ay-badge'>{r.domaine}</span> "
                            f"<span style='color:#8a8984;font-size:.82rem'>{r.lien_haiti}</span>", unsafe_allow_html=True)
                st.markdown(f"**{r.contribution}**")
                st.markdown(f"📅 **Quand :** {r.periode} &nbsp;·&nbsp; 📍 **Où :** {r.ou}")
                with st.expander("Comment, naissance, distinctions, sources"):
                    st.markdown(f"🛠️ **Comment :** {r.comment}")
                    st.markdown(f"👶 **Naissance :** {r.naissance}")
                    st.markdown(f"🏅 **Distinction :** {r.distinction}")
                    st.markdown(f"🌍 **Pays de rayonnement :** {r.pays_contribution}")
                    liens = []
                    if isinstance(r.source, str) and r.source:
                        liens.append(f"[Source]({r.source})")
                    if wpage:
                        liens.append(f"[Wikipédia]({wpage})")
                    liens.append(f"[Vidéos](https://www.youtube.com/results?search_query={r.nom.replace(' ', '+')}+Haïti)")
                    st.markdown(" · ".join(liens))
    note("Photos : Wikimedia Commons (licences libres, via Wikipédia) ou fournies par l'administrateur. Pour remplacer une photo, "
         "téléversez une image dans la rubrique « Contributions » en lui donnant exactement le nom de la personne.")

# ------------------------------------------------------------------ statistiques
with t_stats:
    a, b = st.columns(2)
    with a:
        k = c.domaine.value_counts().reset_index()
        k.columns = ["domaine", "n"]
        st.plotly_chart(barres_h(k, "n", "domaine", "Personnalités par domaine", "personnes"), use_container_width=True)
    with b:
        ln = c.lien_haiti.map(lambda x: "Nés en Haïti / Saint-Domingue" if str(x).startswith(("Né", "Née"))
                              else "Descendants" if str(x).startswith("Descend") else "Groupes / autres").value_counts().reset_index()
        ln.columns = ["lien", "n"]
        st.plotly_chart(barres_h(ln, "n", "lien", "Lien avec Haïti", "personnes", color=SERIES[1]), use_container_width=True)
    fig = go.Figure(go.Scatter(x=c.annee_cle, y=c.domaine, mode="markers", text=c.nom,
                               marker=dict(size=13, color=SERIES[0], opacity=0.8, line=dict(color="white", width=1.5)),
                               hovertemplate="<b>%{text}</b> · %{x}<extra></extra>"))
    fig.update_layout(title="Deux siècles et demi de contributions (année de l'apport principal)", height=420,
                      hovermode="closest", xaxis=dict(dtick=25))
    st.plotly_chart(fig, use_container_width=True)

    st.markdown("#### 🗺️ Où ils ont marqué le monde")
    pays = c.groupby("pays_contribution").agg(n=("nom", "size"), noms=("nom", lambda x: ", ".join(x)),
                                              lat=("lat", "mean"), lon=("lon", "mean")).reset_index()
    fig = go.Figure(go.Scattergeo(lon=pays.lon, lat=pays.lat, mode="markers+text",
                                  text="<b>" + pays.pays_contribution + "</b> (" + pays.n.astype(str) + ")",
                                  textposition="bottom center", textfont=dict(size=11, color="#0b0b0b"),
                                  customdata=pays[["noms"]],
                                  marker=dict(size=8 + 3.5 * pays.n ** 0.8, color=SERIES[0], opacity=0.75,
                                              line=dict(color="white", width=1.5)),
                                  hovertemplate="%{text}<br>%{customdata[0]}<extra></extra>"))
    fig.update_geos(projection_type="natural earth", showcountries=True, countrycolor="#d6d5d0", showland=True,
                    landcolor="#f3f2ee", showocean=True, oceancolor="#eef4fd", lataxis_range=[-30, 62], lonaxis_range=[-125, 150])
    fig.update_layout(height=470, margin=dict(l=0, r=0, t=0, b=0))
    st.plotly_chart(fig, use_container_width=True)
    st.dataframe(s[["indicateur", "valeur", "unite", "annee", "source", "url"]], hide_index=True, use_container_width=True,
                 column_config={"url": st.column_config.LinkColumn("lien")})
    st.download_button("⬇️ Toutes les personnalités (CSV)", c.to_csv(index=False).encode("utf-8"), "contributions_haiti.csv")

analyse_box("À retenir", [
    "De **Toussaint Louverture** et **Dessalines** à **Michaëlle Jean**, Haïti a donné au monde des libérateurs, des bâtisseurs "
    "d'États et des diplomates (Saint-Lot, cosignataire de la Déclaration universelle des droits de l'homme).",
    "En **sciences et technologie** : Gérard Alphonse (diode superluminescente, 50+ brevets), Samuel Pierre (réseaux mobiles), "
    "Herriot Tabuteau (biotech, 200+ brevets) ; en **médecine** : Yvonne Sylvain, Jean William Pape, Henri Ford.",
    "En **pensée** : Firmin, Price-Mars et Trouillot ont transformé l'anthropologie et l'histoire mondiales.",
    "La **diaspora** concentre une part considérable des talents : plus de 80 % des diplômés du supérieur nés en Haïti vivaient "
    "dans un pays de l'OCDE (Banque mondiale, 2005).",
])
galerie("Contributions")
pied("Wikipedia, Engineers Canada, Université de Miami, Le Flambeau Foundation, Startup Grind, Essence, Migration Policy Institute, "
     "Banque mondiale, UNESCO. Photos : Wikimedia Commons ou administrateur.")
