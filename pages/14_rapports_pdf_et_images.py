import io
import zipfile
from datetime import date

import streamlit as st

from src import data as D
from src import territoire as T
from src.rapports import fmt_fr, infographie
from src.rapports_sections import SECTIONS, generer
from src.ui import entete, note, pied, setup
from src.utils import ASSETS

setup("Rapports PDF & images", "📄")
entete("Rapports PDF & images", "Composez un rapport sur un ou plusieurs aspects d'Haïti et téléchargez-le en PDF, "
                                "avec tous ses graphiques en images PNG.")

a, b = st.columns([2, 1])
modele = b.radio("Modèle", ["Rapport complet", "Économie", "Territoire & population", "Tourisme & richesses",
                            "Fiche commune", "Personnalisé"])
PRESETS = {
    "Rapport complet": SECTIONS[:-1],
    "Économie": ["Synthèse nationale", "Développement (indice multifactoriel)", "Économie & finances", "Actualités récentes"],
    "Territoire & population": ["Synthèse nationale", "Population & territoire", "Éducation & institutions",
                                "Îles, routes & transports"],
    "Tourisme & richesses": ["Synthèse nationale", "Richesses & ressources", "Tourisme & cadre de vie", "Îles, routes & transports"],
    "Fiche commune": ["Fiche commune"],
    "Personnalisé": [],
}
sections = a.multiselect("Sections du rapport", SECTIONS, default=PRESETS[modele], placeholder="Choisir les sections")
pcode = None
if "Fiche commune" in sections:
    com = D.communes()
    c1, c2 = st.columns(2)
    dep = c1.selectbox("Département", sorted(com.departement.unique()), index=sorted(com.departement.unique()).index("Sud-Est"))
    nom = c2.selectbox("Commune", sorted(com[com.departement == dep].commune))
    pcode = com[(com.commune == nom) & (com.departement == dep)].adm2_pcode.iloc[0]
titre = st.text_input("Titre du rapport", "Haïti — " + (modele.lower() if modele != "Fiche commune" else "fiche commune"))
photos = {"Cap-Haïtien": "cap_haitien.jpg", "Marché en Fer": "marche_en_fer.jpg", "Delmas": "delmas.jpg",
          "Villa en pierre": "villa.jpg", "Ouanaminthe": "ouanaminthe.jpg", "Ferrier": "ferrier.jpg", "Aucune": None}
photo = st.selectbox("Photo de couverture", list(photos))

if st.button("📄 Générer le rapport", type="primary", disabled=not sections):
    with st.spinner("Création du PDF et des graphiques…"):
        p = photos[photo]
        pdf, imgs = generer(sections, titre, pcode, str(ASSETS / "img" / p) if p else None)
    st.session_state["rapport"] = (pdf, imgs, titre)

if "rapport" in st.session_state:
    pdf, imgs, t = st.session_state["rapport"]
    nomf = t.lower().replace(" ", "_").replace("—", "-")[:60]
    st.success(f"Rapport prêt : {len(pdf) // 1024} Ko, {len(imgs)} graphiques.")
    c1, c2 = st.columns(2)
    c1.download_button("⬇️ Télécharger le PDF", pdf, f"{nomf}_{date.today():%Y%m%d}.pdf", "application/pdf", type="primary")
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        for k, v in imgs.items():
            z.writestr(k, v)
    c2.download_button("🖼️ Tous les graphiques (ZIP de PNG)", buf.getvalue(), f"{nomf}_graphiques.zip", "application/zip")
    st.markdown("**Aperçu des graphiques** (cliquez sur le bouton sous chaque image pour la télécharger)")
    cols = st.columns(3)
    for i, (k, v) in enumerate(imgs.items()):
        with cols[i % 3]:
            st.image(v, use_container_width=True)
            st.download_button(f"PNG · {k}", v, k, "image/png", key=f"png_{k}")

st.divider()
st.subheader("🖼️ Infographie à partager")
st.caption("Une image de synthèse au format 16:9 (réseaux sociaux, présentations).")
theme = st.selectbox("Thème de l'infographie", ["Haïti en chiffres", "Ayiti, terre de richesses", "Économie", "Commune"])
dep = D.departements()
pop, an = D.derniere_valeur("SP.POP.TOTL")
act = D.indicateurs_actuels()


def a_(ind, per=None):
    d = act[act.indicateur == ind]
    if per:
        d = d[d.periode.astype(str) == per]
    return d.iloc[-1] if len(d) else None


if theme == "Haïti en chiffres":
    ch = [("Population", fmt_fr(pop) if pop else fmt_fr(dep.population.sum()), f"Banque mondiale {an or 2022}"),
          ("Communes", "140", "570 sections communales"),
          ("Moins de 18 ans", f"{100 * dep.enfants.sum() / dep.population.sum():.0f} %", "un pays jeune (2022)"),
          ("Littoral", "≈ 1 500 km", f"{len(T.communes_cotieres())} communes côtières"),
          ("Enseignement supérieur", "190", "IES reconnues en 2026"),
          ("Diaspora", "4,1 Md USD", "transferts reçus en 2024")]
    sous = "Ayiti · Hayti — portrait d'un pays jeune et riche de ressources"
elif theme == "Ayiti, terre de richesses":
    ch = [("Vétiver", "> 2/3", "de l'huile essentielle mondiale"), ("Potentiel minier", "≈ 20 Md USD", "or et cuivre (estim. 2012)"),
          ("Patrimoine UNESCO", "2", "Citadelle · soup joumou"), ("Cacao fin", "4,5 M USD", "exportations 2023"),
          ("Sites remarquables", str(len(T.sites_touristiques())), "plages, cascades, forts, parcs"),
          ("Îles", str(len(T.iles())), "Gonâve, Tortue, Île-à-Vache…")]
    sous = "Agriculture d'exception, sous-sol, mer, culture et patrimoine"
elif theme == "Économie":
    g, i, rm = a_("Croissance du PIB réel", "2025"), a_("Inflation (prix à la consommation)", "2025"), a_("Transferts de la diaspora")
    g27 = a_("Croissance du PIB réel", "2027")
    ch = [("Croissance 2025", f"{g.valeur:+.1f} %" if g is not None else "–", "FMI"),
          ("Prévision 2027", f"{g27.valeur:+.1f} %" if g27 is not None else "–", "retour à la croissance (FMI)"),
          ("Inflation 2025", f"{i.valeur:.1f} %" if i is not None else "–", "FMI"),
          ("Transferts", f"{rm.valeur:.0f} % du PIB" if rm is not None else "–", "1re source de devises"),
          ("Taux de change", "≈ 131 HTG", "pour 1 USD, stable depuis fin 2023"),
          ("Réserves brutes", "3,1 Md USD", "juin 2025 (BRH)")]
    sous = "Indicateurs récents (sources : FMI, BRH, DG Trésor)"
else:
    com = D.communes()
    nomc = st.selectbox("Commune ", sorted(com.commune))
    c = com[com.commune == nomc].iloc[0]
    ch = [("Population 2022", fmt_fr(c.population), c.departement), ("Densité", f"{fmt_fr(c.densite_hab_km2)}", "hab/km²"),
          ("Superficie", f"{fmt_fr(c.superficie_km2, 1)} km²", ""), ("Localités", str(int(c.nb_localites)), "recensées"),
          ("Moins de 18 ans", f"{c.part_enfants_pct:.0f} %", "de la population"),
          ("Littoral", "oui" if c.adm2_pcode in T.communes_cotieres() else "non", "commune côtière")]
    sous, theme = f"{c.departement} · {c.adm2_pcode}", c.commune
png = infographie(ch, theme, sous)
st.image(png, use_container_width=True)
st.download_button("⬇️ Télécharger l'infographie (PNG)", png, f"infographie_{theme.lower().replace(' ', '_')}.png", "image/png")
note("Les PDF reprennent les chiffres et sources de la plateforme au moment de la génération ; après une mise à jour des "
     "données, régénérez le rapport pour obtenir les valeurs les plus récentes.")
pied("Graphiques : matplotlib · PDF : fpdf2 · données : voir la section Sources de chaque rapport.")
