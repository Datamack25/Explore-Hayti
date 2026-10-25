# 🇭🇹 Ayiti Data Hub

**Toutes les données sur Haïti, réunies, croisées et analysées en un seul endroit — et mises à jour automatiquement.**

Plateforme interactive (Python · Streamlit · Plotly · Leaflet/Folium · scikit-learn) qui rassemble le territoire,
la population, les écoles, les universités, les institutions, l'économie et la situation humanitaire d'Haïti.
Toutes les tables sont reliées par les **P-codes officiels du CNIGS** (HT01 → HT0111 → HT0111-01).

## Ce que contient la plateforme

| Page | Contenu |
|---|---|
| 🏠 Accueil (tableau de bord) | **Diaporama de photos** (fondu toutes les 6 s, photos de la rubrique « Accueil » ajoutables par l'administrateur) avec **date et heure en direct** (heure d'Haïti et du visiteur) ; **Carte d'Haïti** + **fil d'actualités** à droite (mis à jour toutes les 6 h, « regard positif d'abord »), **indice de développement multifactoriel** sous la carte, richesses, liens utiles |
| 🗺️ Carte interactive | Choroplèthes par commune/département (9 indicateurs), carte Leaflet des localités et institutions |
| 🏘️ Fiche commune | Profil des 140 communes : population, pyramide, sections, localités, écoles, institutions, analyse automatique, communes similaires (ML), export CSV/Markdown |
| 🏫 Écoles, universités & institutions | Recherche globale filtrable sur tout le territoire, 4 122 écoles, 180 IES, santé, mairies, OpenStreetMap |
| 📈 Économie & finances | 612 indicateurs Banque mondiale (1960 →), comparaison indexée, corrélations, chiffres FMI récents |
| 👥 Population & territoire | Treemap, densité, jeunesse, équilibre femmes-hommes |
| 🆘 Humanitaire | IPC 2023 → 2026, déplacés, COVID-19 (archive 2020), organisations présentes |
| 🤖 Analyses & ML | Typologie K-means + ACP, indice de vulnérabilité réglable, prévisions (Holt + bootstrap), années de rupture (Isolation Forest), rapports générés, assistant IA optionnel |
| 🔄 Actualités & mises à jour | Bouton de mise à jour, journal, chiffres sourcés, dernières publications |
| 🗂️ Explorateur | Tous les CSV : filtrer, représenter, télécharger ; sources et licences |
| 💎 Richesses & ressources | Vétiver, mangue, cacao, café, or/cuivre, mer, patrimoine, diaspora, jeunesse — chiffrés et sourcés, carte |
| 🌴 Bien vivre & tourisme | Indice « cadre de vie » par commune (pondérable) + 26 sites à découvrir |
| 🏝️ Les îles | Gonâve, Tortue, Île-à-Vache, Cayemites, Arcadins, Navase : population, superficie, carte |
| 🛣️ Routes & transports | Routes nationales, aéroports, ports, distances (tracé réel OpenStreetMap après mise à jour) |
| 📄 Rapports PDF & images | Rapport PDF sur 1 à 11 sections au choix, graphiques PNG (ZIP), infographie 16:9 |
| ⚽ Sport | Palmarès (JO 1924 et 1928, CONCACAF 1973, Coupes caribéennes, Coupes du monde 1974 et 2026, Grenadières 2023), grandes figures |
| 🎶 Konpa & musique | Chronologie de 1948 à 2026 (Nemours Jean-Baptiste, mini-jazz, Tabou Combo, UNESCO 2025) |
| 🍲 Gastronomie | 17 spécialités (soup joumou UNESCO, griot, djon djon, pikliz, kremas, Barbancourt…) avec liens recettes |
| 📜 Histoire & solidarité | Grandes dates et carte des peuples qu'Haïti a aidés (Bolívar, Miranda, Grèce, Savannah…) |
| 🌍 Diaspora | Carte mondiale par pays et par ville, métiers aux États-Unis, transferts |
| 🔐 Administration | Espace protégé : modifier toutes les données, ajouter images/vidéos/liens, importer des CSV, lancer les mises à jour |

## Installation locale

```bash
git clone https://github.com/<votre-compte>/ayiti-data-hub.git
cd ayiti-data-hub
python -m venv .venv && source .venv/bin/activate      # Windows : .venv\Scripts\activate
pip install -r requirements.txt
streamlit run Accueil.py
```

## Déploiement gratuit (Streamlit Community Cloud)

1. Poussez le dossier sur un dépôt GitHub (public ou privé).
2. Sur https://share.streamlit.io → *New app* → choisissez le dépôt, branche `main`, fichier **`Accueil.py`**.
3. (Optionnel) *Settings → Secrets* pour l'assistant IA (voir plus bas).

## Mise à jour automatique des données

```bash
python scripts/update_all.py            # tout (≈ 2-6 min)
python scripts/update_all.py --sans-osm # sans OpenStreetMap
python scripts/update_world_bank.py --tous   # les ~600 indicateurs Banque mondiale
```

| Script | Source (gratuite, sans clé) | Fichier produit |
|---|---|---|
| `update_world_bank.py` | API Banque mondiale (repli : miroirs GitHub) | `data/live/wb_live.csv` |
| `update_osm.py` | OpenStreetMap / Overpass : écoles, universités, hôpitaux, cliniques, pharmacies, police, tribunaux, mairies, banques, bibliothèques, marchés… rattachés à leur commune | `data/live/osm_institutions.csv` |
| `update_hdx.py` | HDX/OCHA : dernière analyse IPC + catalogue des jeux de données Haïti | `data/live/ipc_live.csv`, `hdx_catalogue_haiti.csv` |
| `update_news.py` | 22 sources : médias haïtiens (Le Nouvelliste, Haïti Libre, Juno7, AyiboPost, AlterPresse, Rezo Nòdwès…), diaspora (Haitian Times…), Google Actualités (« Haïti », « Ayiti », « Hayti » + tourisme, culture, économie, sport), ReliefWeb. Chaque article reçoit un **thème** et une **tonalité** | `data/live/actualites.csv` |
| `update_routes.py` | OpenStreetMap : autoroutes, nationales, départementales, aéroports, ports, gares routières | `data/live/routes_osm.geojson`, `transports_osm.csv` |

- **Dans l'application** : page 🔄 → « Mettre à jour maintenant ».
- **Sur GitHub** : `.github/workflows/mise-a-jour-donnees.yml` relance les **actualités et l'IPC toutes les 6 heures**
  (`--rapide`) et **tout le reste chaque lundi**, puis enregistre les nouveaux CSV
  dans le dépôt (Streamlit Cloud redéploie alors automatiquement). Lancement manuel : onglet *Actions* → *Run workflow*.
- ReliefWeb peut exiger un nom d'application approuvé : ajoutez-le dans *Settings → Secrets → Actions* sous `RELIEFWEB_APPNAME`.

## Regard positif et tonalité des actualités

`src/veille.py` classe chaque article (économie, politique, tourisme, culture, sport, éducation & science, santé,
environnement, diaspora, agriculture, sécurité, humanitaire, société) et calcule une tonalité (positif / neutre / négatif)
à partir de listes de mots en français, anglais et créole. Par défaut, la plateforme **affiche d'abord les nouvelles
positives et les thèmes valorisants**, sans cacher le reste (interrupteur « Regard positif d'abord »). Les listes de mots
sont modifiables dans ce fichier ; une source s'ajoute par une ligne dans `data/curated/sources_actualites.csv`.

## Ajouter vos propres données (ex. celles de Haïti Explorer)

- **Un chiffre récent** : une ligne dans `data/curated/indicateurs_actuels.csv` (avec source et lien).
- **Une université / un hôpital** : une ligne dans `data/curated/universites.csv` ou `sante_reference.csv`, puis `python scripts/build_data.py`.
- **Un nouveau CSV** : déposez-le dans `data/processed/` ; il apparaît dans l'Explorateur. S'il contient une colonne
  `adm2_pcode`, il peut être joint à `communes.csv` dans `scripts/build_data.py` pour l'afficher sur la carte.

Reconstruire toutes les tables depuis les fichiers bruts : `python scripts/build_data.py`.

## Espace administrateur

1. Copiez `.streamlit/secrets.toml.example` vers `.streamlit/secrets.toml` (en local) ou collez son contenu dans
   **Streamlit Cloud → Settings → Secrets**, et choisissez `ADMIN_PASSWORD`.
2. Page 🔐 **Administration** : modifier n'importe quel fichier de `data/curated/` dans un tableau éditable, téléverser des
   images par rubrique (`assets/uploads/<rubrique>/`), ajouter des vidéos YouTube (intégrées si lien direct `watch?v=`),
   des liens ou des images en ligne (`data/curated/medias.csv`), importer un CSV/Excel, lancer les mises à jour.
3. **Pour rendre les modifications permanentes** sur Streamlit Cloud, ajoutez `GITHUB_TOKEN` (jeton « fine-grained »
   limité au dépôt : *Contents* et *Actions* en lecture/écriture) et `GITHUB_REPO` : chaque enregistrement devient un commit.

## Assistant IA (optionnel)

Dans `.streamlit/secrets.toml` (à ne jamais publier) ou les secrets Streamlit Cloud :

```toml
ANTHROPIC_API_KEY = "sk-ant-..."
# ou un modèle local gratuit avec Ollama :
# OLLAMA_URL = "http://localhost:11434"
# OLLAMA_MODEL = "mistral"
```

## Architecture

```
Accueil.py                 point d'entrée : menu de navigation (titres et icônes des pages)
pages/                     21 pages (noms de fichiers en ASCII pour éviter les caractères illisibles sous Windows)
src/  data.py              chargement + fusion base / données à jour (cache)
      ui.py                thème, CSS, cartes KPI HTML, palette validée
      charts.py            choroplèthes Plotly, cartes Leaflet, séries
      analyse.py           analyses automatiques en français
      ml.py                K-means, ACP, vulnérabilité, plus proches voisins, Holt, Isolation Forest
      indicateurs.py       65 indicateurs clés traduits + événements historiques
      assistant.py         assistant LLM optionnel
      veille.py            thème et tonalité des actualités
      developpement.py     indice composite de développement (6 dimensions)
      territoire.py        villes, îles, routes, transports, littoral, indice cadre de vie
      composants.py        fil d'actualités, cartes richesses, liens
      rapports.py          moteur PDF (fpdf2) et images (matplotlib)
      rapports_sections.py contenu des 11 sections de rapport
scripts/                   build_data.py, anonymiser_ong.py, update_*.py
data/raw/                  fichiers sources d'origine
data/processed/            tables propres reliées par P-code
data/curated/              listes vérifiées à la main (universités, santé, chiffres récents, sources)
data/live/                 données téléchargées par les mises à jour
data/geo/                  contours des communes et départements (GeoJSON)
```

## Limites connues (à lire)

- La **cartographie scolaire 2022** ne couvre que la Grand'Anse, les Nippes, le Sud et 8 communes de l'Ouest. Elle est
  complétée sur tout le pays par l'**export OpenStreetMap/HOT** (7 364 établissements géolocalisés, 5 octobre 2026,
  `scripts/integrer_education_osm.py`), collaboratif donc incomplet en zone rurale.
- Les écoles et universités sans coordonnées GPS sont placées au **centre de leur commune**.
- Les fichiers Banque mondiale fournis ne contiennent pas les thèmes santé/éducation/population : la première mise à jour
  les ajoute (espérance de vie, scolarisation, électricité, Internet…).
- La base de contacts ONG fournie contenait des **données personnelles** (noms, e-mails) : seule la liste agrégée des
  organisations est conservée ; le fichier brut est exclu par `.gitignore`.
- Les prévisions prolongent les tendances passées et ne peuvent pas anticiper les chocs.
- L'**indice de développement** mesure la trajectoire propre d'Haïti (0 = pire année, 100 = meilleure depuis 1990), pas un
  classement mondial ; les dimensions Social et Population reposent sur peu d'indicateurs tant que la mise à jour Banque
  mondiale n'a pas tourné.
- L'**indice cadre de vie** n'intègre pas la sécurité (pas de données communales fiables) : consulter les avis officiels.
- Les **routes** sont schématiques (villes reliées) jusqu'au premier téléchargement OpenStreetMap.
- Le classement automatique des actualités (thème, tonalité) repose sur des mots-clés : il peut se tromper sur un titre.

Sources et licences détaillées : `data/curated/sources.csv` (page 🗂️).
