import subprocess
import sys

import pandas as pd
import streamlit as st

from src import admin
from src import data as D
from src.medias import EXT_IMG, UPLOADS, slug
from src.ui import entete, note, setup
from src.utils import CURATED, ROOT

setup("Administration", "🔐")
entete("Espace administrateur", "Mettre à jour les données, ajouter des images, des vidéos et des liens, lancer les mises à jour.")

if not admin.formulaire_connexion():
    st.stop()

c1, c2 = st.columns([3, 1])
c1.success("Connecté en tant qu'administrateur. " + ("Sauvegarde GitHub **activée** : chaque modification est permanente."
                                                    if admin.github_actif() else
                                                    "Sauvegarde GitHub **non configurée** : modifications temporaires sur Streamlit Cloud."))
if c2.button("Se déconnecter"):
    st.session_state["admin_ok"] = False
    st.rerun()

RUBRIQUES = ["Contributions", "Sport", "Konpa", "Gastronomie", "Histoire", "Diaspora", "Tourisme", "Richesses", "Accueil"]
t1, t2, t3, t4 = st.tabs(["✏️ Modifier les données", "🖼️ Images, vidéos & liens", "🔄 Mises à jour", "📤 Importer un fichier"])

# ------------------------------------------------------------------ 1. édition des CSV
with t1:
    fichiers = {p.stem: p for p in sorted(CURATED.glob("*.csv"))}
    nom = st.selectbox("Fichier de données", list(fichiers), index=list(fichiers).index("indicateurs_actuels")
                       if "indicateurs_actuels" in fichiers else 0,
                       help="Données vérifiées affichées dans la plateforme (chiffres récents, palmarès sportif, konpa, "
                            "gastronomie, histoire, diaspora, sources d'actualités, liens utiles…).")
    df = pd.read_csv(fichiers[nom])
    st.caption("Modifiez les cellules, ajoutez une ligne avec « + » en bas du tableau ou supprimez des lignes, puis enregistrez.")
    edite = st.data_editor(df, num_rows="dynamic", use_container_width=True, height=460, key=f"ed_{nom}")
    a, b = st.columns([1, 3])
    if a.button("💾 Enregistrer", type="primary"):
        msg = admin.enregistrer(fichiers[nom], edite.to_csv(index=False).encode("utf-8"),
                                f"Administration : mise à jour de {nom}.csv")
        D.vider_cache()
        st.success(f"{nom}.csv {msg}.")
    b.download_button("⬇️ Télécharger ce fichier", df.to_csv(index=False).encode("utf-8"), f"{nom}.csv")

# ------------------------------------------------------------------ 2. médias
with t2:
    st.markdown("#### Ajouter une image (fichier)")
    r1, r2 = st.columns(2)
    rub = r1.selectbox("Rubrique", RUBRIQUES)
    titre = r2.text_input("Titre / légende de l'image", placeholder="ex. Les Grenadiers à Atlanta, 2026")
    up = st.file_uploader("Image (JPG, PNG, WEBP)", type=[e.strip(".") for e in EXT_IMG])
    if up and st.button("Téléverser l'image"):
        ext = "." + up.name.rsplit(".", 1)[-1].lower()
        dest = UPLOADS / slug(rub) / f"{slug(titre or up.name.rsplit('.', 1)[0])}{ext}"
        msg = admin.enregistrer(dest, up.getvalue(), f"Administration : image {dest.name} ({rub})")
        st.success(f"Image {msg}.")
    st.caption("Rubrique « Contributions » : donnez à l'image exactement le nom de la personne (ex. « Dany Laferrière ») "
               "pour qu'elle remplace la photo Wikipédia sur son portrait.")
    note("Vérifiez que vous avez le droit de publier l'image (photo personnelle, licence libre, autorisation de l'auteur) "
         "et indiquez le crédit dans la légende.")
    st.divider()
    st.markdown("#### Ajouter une vidéo, une image en ligne ou un lien")
    m1, m2, m3 = st.columns([1, 1, 2])
    rub2 = m1.selectbox("Rubrique ", RUBRIQUES, key="rub2")
    typ = m2.selectbox("Type", ["video", "lien", "image"],
                       format_func={"video": "Vidéo (YouTube…)", "lien": "Lien / article", "image": "Image (adresse web)"}.get)
    t = m3.text_input("Titre")
    u = st.text_input("Adresse (URL)", placeholder="https://www.youtube.com/watch?v=…")
    cr = st.text_input("Crédit / source (facultatif)")
    if st.button("Ajouter", type="primary", disabled=not (t and u.startswith("http"))):
        p = CURATED / "medias.csv"
        m = pd.read_csv(p)
        m = pd.concat([m, pd.DataFrame([{"rubrique": rub2, "titre": t, "type": typ, "url": u, "credit": cr}])], ignore_index=True)
        msg = admin.enregistrer(p, m.to_csv(index=False).encode("utf-8"), f"Administration : média « {t} » ({rub2})")
        st.success(f"Média {msg}. Une vidéo YouTube avec un lien direct (watch?v=…) s'affiche intégrée dans la rubrique.")
    st.divider()
    st.markdown("#### Médias existants")
    m = pd.read_csv(CURATED / "medias.csv")
    st.dataframe(m, hide_index=True, use_container_width=True, column_config={"url": st.column_config.LinkColumn("url")})
    imgs = sorted(p for p in UPLOADS.rglob("*") if p.suffix.lower() in EXT_IMG)
    if imgs:
        choix = st.selectbox("Supprimer une image téléversée", ["—"] + [p.relative_to(UPLOADS).as_posix() for p in imgs])
        if choix != "—" and st.button("🗑️ Supprimer cette image"):
            st.info(admin.supprimer(UPLOADS / choix, f"Administration : suppression de {choix}"))

# ------------------------------------------------------------------ 3. mises à jour
with t3:
    st.markdown("**Sur ce serveur** (immédiat)")
    mode = st.radio("Étendue", ["Actualités seulement", "Tout sauf OpenStreetMap", "Complet"], horizontal=True)
    if st.button("🔄 Lancer la mise à jour ici"):
        opt = {"Actualités seulement": ["--rapide"], "Tout sauf OpenStreetMap": ["--sans-osm"]}.get(mode, [])
        with st.status("Mise à jour…", expanded=True) as s:
            p = subprocess.run([sys.executable, str(ROOT / "scripts" / "update_all.py")] + opt, cwd=ROOT,
                               capture_output=True, text=True, timeout=900)
            st.code((p.stdout or "")[-6000:] + (p.stderr or "")[-2000:], language="text")
            s.update(label="Terminé", state="complete" if p.returncode == 0 else "error")
        D.vider_cache()
    st.divider()
    st.markdown("**Sur GitHub Actions** (permanent : les nouveaux fichiers sont enregistrés dans le dépôt)")
    mg = st.radio("Mode GitHub", ["rapide", "complet"], horizontal=True)
    if st.button("🚀 Lancer la mise à jour sur GitHub"):
        st.info(admin.lancer_action_github(mg))
    if st.button("♻️ Vider le cache de l'application"):
        D.vider_cache()
        st.success("Cache vidé : toutes les pages relisent les fichiers.")

# ------------------------------------------------------------------ 4. import
with t4:
    st.markdown("Importez un **nouveau fichier CSV** (par exemple des données d'AyitiStats, d'un ministère ou d'Haïti Explorer). "
                "Il apparaîtra dans l'Explorateur de données ; s'il contient une colonne `adm2_pcode`, il pourra être affiché "
                "sur la carte.")
    f = st.file_uploader("Fichier CSV ou Excel", type=["csv", "xlsx", "xls"], key="imp")
    dest_dir = st.radio("Dossier", ["data/processed (données)", "data/curated (données vérifiées)"], horizontal=True)
    if f:
        try:
            d = pd.read_csv(f) if f.name.endswith(".csv") else pd.read_excel(f)
            st.dataframe(d.head(50), use_container_width=True)
            nomf = st.text_input("Nom du fichier", slug(f.name.rsplit(".", 1)[0]))
            if st.button("Importer", type="primary"):
                base = ROOT / ("data/processed" if dest_dir.startswith("data/processed") else "data/curated")
                msg = admin.enregistrer(base / f"{slug(nomf)}.csv", d.to_csv(index=False).encode("utf-8"),
                                        f"Administration : import de {nomf}.csv")
                D.vider_cache()
                st.success(f"{nomf}.csv {msg}.")
        except Exception as e:
            st.error(f"Lecture impossible : {e}")
