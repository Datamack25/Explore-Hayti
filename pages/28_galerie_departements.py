import streamlit as st

from src import admin
from src import images_dep as I
from src.exports_doc import panneau_exports
from src.ui import entete, kpis, note, pied, setup

setup("Galerie des départements", "📸")
entete("Les 10 départements en images",
       "Villes, monuments, paysages : des photos libres de droits (Wikimedia Commons), avec leur auteur et leur licence.")

CAT, CRED = I.catalogue(), I.credits()
locales = sum(1 for f in CAT.fichier if I.chemin_local(f))
kpis([
    {"lab": "Images au catalogue", "val": str(len(CAT)), "sub": "≥3 par département", "style": "accent"},
    {"lab": "Téléchargées", "val": f"{locales} / {len(CAT)}", "sub": "dans assets/img/departements"},
    {"lab": "Départements", "val": str(CAT.departement.nunique())},
])
if locales < len(CAT):
    note("Certaines images ne sont pas encore enregistrées dans le projet : elles s'affichent directement depuis Wikimedia. "
         "Pour les enregistrer (et les utiliser dans les PDF), lancez <code>python scripts/telecharger_images_departements.py</code> "
         "ou le bouton ci-dessous (espace administrateur).", "warn")
    if admin.connecte() and st.button("⬇️ Télécharger les images manquantes"):
        lignes = []
        with st.spinner("Téléchargement depuis Wikimedia Commons…"):
            ok, ko = I.telecharger_tout(journal=lignes.append)
        st.success(f"{ok} images disponibles, {ko} échec(s).")
        st.code("\n".join(lignes) or "rien à faire")


@st.cache_data(show_spinner=False, ttl=7 * 24 * 3600)
def distante(titre: str):
    try:
        im = I.trouver_image(titre)
        return (im["source"], im["page"]) if im else (None, None)
    except Exception:
        return None, None


cred = CRED.set_index("fichier") if len(CRED) else None
onglets = st.tabs(list(dict.fromkeys(CAT.departement)))
for tab, (dep, sous) in zip(onglets, CAT.groupby("departement", sort=False)):
    with tab:
        cols = st.columns(3)
        for i, r in enumerate(sous.itertuples()):
            with cols[i % 3]:
                p = I.chemin_local(r.fichier)
                if p:
                    c = cred.loc[r.fichier] if cred is not None and r.fichier in cred.index else None
                    legende = r.legende + (f" — {c.auteur}, {c.licence}" if c is not None else "")
                    st.image(str(p), caption=legende, use_container_width=True)
                else:
                    url, page = distante(r.titre_wikipedia)
                    if url:
                        st.image(url, caption=f"{r.legende} — Wikimedia Commons", use_container_width=True)
                        if page:
                            st.caption(f"[Source et licence]({page})")
                    else:
                        st.info(f"{r.legende} : image indisponible pour l'instant.")

with st.expander("📥 Exporter l'album (HTML, CSV, PDF, Word)"):
    def blocs():
        b = []
        for dep, sous in CAT.groupby("departement", sort=False):
            b.append(("h1", dep))
            for r in sous.itertuples():
                p = I.chemin_local(r.fichier)
                if p:
                    c = cred.loc[r.fichier] if cred is not None and r.fichier in cred.index else None
                    b.append(("img", p.read_bytes(), r.legende + (f" — {c.auteur}, {c.licence}" if c is not None else "")))
                else:
                    b.append(("p", f"{r.legende} (image à télécharger avec le script)"))
        return b

    panneau_exports("album", "Haïti : les 10 départements en images", "Album photo — Wikimedia Commons, licences libres", blocs,
                    {"catalogue_images": CAT, "credits_images": CRED}, sources="Wikipédia ; Wikimedia Commons (auteurs et licences dans credits_images.csv).")

pied("Wikipédia et Wikimedia Commons — chaque image garde l'auteur et la licence indiqués sur sa page Commons.")
