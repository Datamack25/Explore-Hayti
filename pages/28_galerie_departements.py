import streamlit as st
from urllib.parse import quote_plus

from src import admin
from src import images_dep as I
from src import photos_web as W
from src.exports_doc import panneau_exports
from src.ui import entete, kpis, note, pied, setup

setup("Galerie des départements", "📸")
entete("Les 10 départements en images",
       "Villes, monuments, paysages : des photos libres de droits (Wikimedia Commons), avec leur auteur et leur licence. "
       "Cliquez sur une photo pour ouvrir sa source.")

CAT, CRED = I.catalogue(), I.credits()
CHOIX = W.photos_choisies()
AJOUTS = W.photos_ajoutees()

# Lieux ajoutés par l'administrateur qui ne sont pas encore dans le catalogue
if len(AJOUTS):
    connus = set(zip(CAT.departement, CAT.legende))
    nouveaux = AJOUTS[[(d, l) not in connus for d, l in zip(AJOUTS.departement, AJOUTS.legende)]]
    if len(nouveaux):
        import pandas as pd
        CAT = pd.concat([CAT, pd.DataFrame({"departement": nouveaux.departement, "legende": nouveaux.legende,
                                            "fichier": "", "titre_wikipedia": ""})], ignore_index=True)

locales = sum(1 for f in CAT.fichier if f and I.chemin_local(f))
kpis([
    {"lab": "Images au catalogue", "val": str(len(CAT)), "sub": "≥3 par département", "style": "accent"},
    {"lab": "Téléchargées", "val": f"{locales} / {len(CAT)}", "sub": "dans assets/img/departements"},
    {"lab": "Photos ajoutées depuis le web", "val": str(len(AJOUTS))},
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


@st.cache_data(show_spinner=False, ttl=3600)
def recherche(q: str):
    return W.rechercher_commons(q, n=12)


cred = CRED.set_index("fichier") if len(CRED) else None


def recherche_commons_lien(legende: str) -> str:
    return "https://commons.wikimedia.org/w/index.php?title=Special:MediaSearch&type=image&search=" + quote_plus(f"{legende} Haïti")


def resoudre(dep: str, legende: str, fichier: str, titre: str) -> dict:
    """Ordre : photo ajoutée par l'admin > photo choisie > fichier du projet > recherche automatique > lien."""
    a = AJOUTS[(AJOUTS.departement == dep) & (AJOUTS.legende == legende)] if len(AJOUTS) else AJOUTS
    if len(a):
        a = a.iloc[-1]
        return dict(type="photo", url=a.image_url, lien=a.page or a.image_url, chemin=W.chemin_ajout(a.fichier_local),
                    credit=" — ".join(x for x in (a.auteur, a.licence) if x) or "Source en lien",
                    auteur=a.auteur, licence=a.licence)
    nom_lieu = legende.split(" :")[0].strip()
    c = CHOIX.get(legende.strip()) or CHOIX.get(nom_lieu)
    if c:
        if c.get("image_url"):
            return dict(type="photo", url=c["image_url"], lien=c["lien"], chemin=None,
                        credit="Wikimedia Commons, licence libre", auteur="Wikimedia Commons", licence="libre (voir source)")
        return dict(type="lien", lien=c.get("lien") or recherche_commons_lien(nom_lieu))
    p = I.chemin_local(fichier) if fichier else None
    if p:
        cr = cred.loc[fichier] if cred is not None and fichier in cred.index else None
        return dict(type="local", chemin=p, lien=recherche_commons_lien(nom_lieu),
                    credit=f"{cr.auteur}, {cr.licence}" if cr is not None else "Wikimedia Commons",
                    auteur=cr.auteur if cr is not None else "", licence=cr.licence if cr is not None else "")
    if titre:
        url, page = distante(titre)
        if url:
            return dict(type="photo", url=url, lien=page or url, chemin=None, credit="Wikimedia Commons",
                        auteur="Wikimedia Commons", licence="voir source")
    return dict(type="lien", lien=recherche_commons_lien(nom_lieu))


# ------------------------------------------------------------------ galerie
onglets = st.tabs(list(dict.fromkeys(CAT.departement)))
for tab, (dep, sous) in zip(onglets, CAT.groupby("departement", sort=False)):
    with tab:
        cols = st.columns(3)
        album = []
        for i, r in enumerate(sous.itertuples()):
            x = resoudre(dep, r.legende, r.fichier, r.titre_wikipedia)
            with cols[i % 3]:
                if x["type"] == "photo":
                    st.markdown(W.carte_html(x["url"], x["lien"], r.legende, x["credit"]), unsafe_allow_html=True)
                    if x["chemin"]:
                        st.download_button("⬇️ Télécharger", x["chemin"].read_bytes(), file_name=x["chemin"].name,
                                           key=f"dl-{dep}-{i}", use_container_width=True)
                    else:
                        st.markdown(f"[⬇️ Télécharger l'original]({x['url'].split('?width=')[0]})")
                    album.append(dict(nom=f"{i + 1:02d}_{W._nom_fichier(dep, r.legende, x['url'])}", chemin=x["chemin"],
                                      url=x["url"], departement=dep, legende=r.legende, auteur=x["auteur"],
                                      licence=x["licence"], page=x["lien"]))
                elif x["type"] == "local":
                    st.image(str(x["chemin"]), caption=f"{r.legende} — {x['credit']}", use_container_width=True)
                    c1, c2 = st.columns(2)
                    c1.download_button("⬇️ Télécharger", x["chemin"].read_bytes(), file_name=x["chemin"].name,
                                       key=f"dl-{dep}-{i}", use_container_width=True)
                    c2.link_button("🔎 Plus de photos", x["lien"], use_container_width=True)
                    album.append(dict(nom=f"{i + 1:02d}_{x['chemin'].name}", chemin=x["chemin"], departement=dep,
                                      legende=r.legende, auteur=x["auteur"], licence=x["licence"], page=""))
                else:
                    st.markdown(W.carte_sans_photo(r.legende, x["lien"]), unsafe_allow_html=True)

        if album:
            cle = f"zip-{dep}"
            if st.button(f"📦 Préparer l'album photo « {dep} » (ZIP)", key=f"btn-{cle}"):
                with st.spinner("Téléchargement des photos…"):
                    st.session_state[cle] = W.album_zip(album)
            if cle in st.session_state:
                data, n = st.session_state[cle]
                st.download_button(f"⬇️ Télécharger l'album ({n} photos + crédits)", data,
                                   file_name=f"album_{W._nom_fichier(dep, 'photos', 'x.zip')[:-4]}.zip",
                                   mime="application/zip", key=f"dl-{cle}")

# ------------------------------------------------------------------ ajout depuis Internet
with st.expander("🌐 Ajouter ou remplacer une photo depuis Internet", expanded=False):
    if not admin.connecte():
        st.info("Réservé à l'administrateur : connectez-vous dans la page **Administration** pour ajouter des photos.")
    else:
        deps = list(dict.fromkeys(CAT.departement))
        c1, c2 = st.columns(2)
        dep_choisi = c1.selectbox("Département", deps, key="aj-dep")
        lieux = list(dict.fromkeys(CAT[CAT.departement == dep_choisi].legende)) + ["➕ Nouveau lieu…"]
        lieu = c2.selectbox("Lieu (la photo actuelle sera remplacée)", lieux, key="aj-lieu")
        if lieu == "➕ Nouveau lieu…":
            lieu = st.text_input("Nom du nouveau lieu", key="aj-nouveau").strip()

        mode = st.radio("Source", ["🔎 Chercher sur Wikimedia Commons (libre de droits)", "🔗 Coller un lien"],
                        horizontal=True, key="aj-mode")

        if mode.startswith("🔎"):
            q = st.text_input("Recherche", value=f"{lieu.split(' :')[0]} Haïti" if lieu else "", key=f"aj-q-{lieu}")
            if q and st.button("Chercher", key="aj-go"):
                st.session_state["aj-res"] = q
            if st.session_state.get("aj-res"):
                try:
                    res = recherche(st.session_state["aj-res"])
                except Exception as e:
                    res = []
                    st.error(f"Recherche impossible pour le moment ({e}).")
                if not res:
                    st.warning("Aucune photo trouvée. Essayez un autre mot (monument, plage, cathédrale…) ou un nom en anglais.")
                g = st.columns(3)
                for k, it in enumerate(res):
                    with g[k % 3]:
                        st.markdown(W.carte_html(it["miniature"], it["page"], it["titre"], f"{it['auteur']} — {it['licence']}"),
                                    unsafe_allow_html=True)
                        if st.button("✅ Utiliser cette photo", key=f"aj-use-{k}", disabled=not lieu, use_container_width=True):
                            try:
                                W.ajouter_photo(dep_choisi, lieu, it["image_url"], it["page"], it["auteur"], it["licence"])
                                st.session_state.pop("aj-res", None)
                                st.success("Photo enregistrée.")
                                st.rerun()
                            except Exception as e:
                                st.error(f"Échec du téléchargement : {e}")
        else:
            lien = st.text_input("Lien de la photo (page Wikimedia Commons ou lien direct vers une image .jpg/.png)", key="aj-lien")
            info = W.infos_depuis_lien(lien) if lien else None
            if info:
                st.markdown(W.carte_html(info["image_url"], info["page"], lieu or info["titre"], ""), unsafe_allow_html=True)
                auteur = st.text_input("Auteur / photographe", value=info["auteur"], key="aj-aut")
                licence = st.text_input("Licence (ex. CC BY-SA 4.0)", value=info["licence"], key="aj-lic")
                ok_droits = st.checkbox("Je confirme que cette photo est libre de droits ou que j'ai l'autorisation de l'auteur.",
                                        key="aj-ok")
                if st.button("✅ Enregistrer la photo", disabled=not (lieu and auteur and licence and ok_droits), key="aj-save"):
                    try:
                        W.ajouter_photo(dep_choisi, lieu, info["image_url"], info["page"], auteur, licence)
                        st.success("Photo enregistrée.")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Échec : {e}")

        if len(AJOUTS):
            st.markdown("**Photos ajoutées**")
            for k, a in enumerate(AJOUTS.itertuples()):
                c1, c2 = st.columns([5, 1])
                c1.markdown(f"{a.departement} · **{a.legende}** — {a.auteur}, {a.licence} ([source]({a.page}))")
                if c2.button("Retirer", key=f"aj-del-{k}"):
                    W.retirer_photo(a.departement, a.legende)
                    st.rerun()
            st.download_button("💾 Télécharger photos_ajoutees.csv", W.CSV_AJOUTS.read_bytes(), "photos_ajoutees.csv",
                               mime="text/csv", key="aj-csv")
            note("Sur Streamlit Cloud, les ajouts sont effacés au redémarrage de l'application. Pour les garder, déposez "
                 "<code>photos_ajoutees.csv</code> dans le dossier <code>data/</code> de votre dépôt GitHub.", "warn")

# ------------------------------------------------------------------ exports
with st.expander("📥 Exporter l'album (HTML, CSV, PDF, Word)"):
    def blocs():
        b = []
        for dep, sous in CAT.groupby("departement", sort=False):
            b.append(("h1", dep))
            for r in sous.itertuples():
                x = resoudre(dep, r.legende, r.fichier, r.titre_wikipedia)
                donnees = None
                if x.get("chemin"):
                    donnees = x["chemin"].read_bytes()
                elif x["type"] == "photo":
                    try:
                        donnees = W.telecharger(x["url"])
                    except Exception:
                        donnees = None
                if donnees:
                    b.append(("img", donnees, f"{r.legende} — {x['credit']}"))
                else:
                    b.append(("p", f"{r.legende} — photos : {x['lien']}"))
        return b

    panneau_exports("album", "Haïti : les 10 départements en images", "Album photo — Wikimedia Commons, licences libres", blocs,
                    {"catalogue_images": CAT, "credits_images": CRED, "photos_ajoutees": AJOUTS},
                    sources="Wikipédia ; Wikimedia Commons (auteurs et licences dans credits_images.csv et photos_ajoutees.csv).")

pied("Wikipédia et Wikimedia Commons — chaque image garde l'auteur et la licence indiqués sur sa page Commons.")
