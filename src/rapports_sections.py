"""Contenu des sections de rapport : chaque fonction ajoute une section au PDF et renvoie ses images PNG."""
from __future__ import annotations

import pandas as pd

from src import data as D
from src import territoire as T
from src.analyse import analyser_commune, analyser_departements, analyser_serie
from src.developpement import lecture
from src.indicateurs import INDICATEURS_CLES
from src.ui import SERIES
from src.rapports import (RapportPDF, fig_barres, fig_carte, fig_developpement, fig_ligne, fmt_fr)

SECTIONS = ["Synthèse nationale", "Développement (indice multifactoriel)", "Économie & finances",
            "Population & territoire", "Éducation & institutions", "Humanitaire & sécurité alimentaire",
            "Richesses & ressources", "Tourisme & cadre de vie", "Îles, routes & transports", "Actualités récentes",
            "Fiche commune"]


def _act(ind: str, per: str | None = None):
    a = D.indicateurs_actuels()
    d = a[a.indicateur == ind]
    if per:
        d = d[d.periode.astype(str) == per]
    return d.iloc[-1] if len(d) else None


def synthese(pdf: RapportPDF) -> dict[str, bytes]:
    com, dep = D.communes(), D.departements()
    pdf.section("Synthèse nationale")
    pop, an = D.derniere_valeur("SP.POP.TOTL")
    cr, inf, ipc, idp = (_act("Croissance du PIB réel", "2025"), _act("Inflation (prix à la consommation)", "2025"),
                         _act("Personnes en phase IPC 3+ (crise ou pire)"), _act("Personnes déplacées internes"))
    pdf.chiffres([("Population", fmt_fr(pop) if pop else fmt_fr(dep.population.sum())),
                  ("Communes / sections", "140 / 570"),
                  ("Moins de 18 ans", f"{100 * dep.enfants.sum() / dep.population.sum():.0f} %"),
                  ("Croissance PIB 2025", f"{cr.valeur:+.1f} %" if cr is not None else "–"),
                  ("Inflation 2025", f"{inf.valeur:.1f} %" if inf is not None else "–"),
                  ("Phase IPC 3+ (2026)", fmt_fr(ipc.valeur) if ipc is not None else "–"),
                  ("Déplacés (sept. 2026)", "≈ " + fmt_fr(idp.valeur) if idp is not None else "–"),
                  ("Transferts diaspora 2024", "4,1 Md USD"),
                  ("Communes côtières", str(len(T.communes_cotieres())))])
    carte = fig_carte(D.geojson("communes"), dict(zip(com.adm2_pcode, com.densite_hab_km2.clip(upper=3000))),
                      "Densité de population par commune (hab/km², plafonnée à 3 000)", "Blues", label="hab/km²")
    pdf.figure(carte, "Sources : HDX/OCHA (population 2022), CNIGS, geoBoundaries.")
    for p in analyser_departements(dep):
        pdf.paragraphe(p, puce=True)
    pdf.paragraphe("Haïti traverse une période difficile (sécurité, croissance négative depuis 2019, insécurité alimentaire) "
                   "mais dispose d'atouts majeurs : une population jeune, une diaspora puissante, des filières agricoles de "
                   "niche reconnues mondialement, un patrimoine historique et culturel unique et ~1 500 km de côtes.")
    return {"carte_densite.png": carte}


def developpement(pdf: RapportPDF) -> dict[str, bytes]:
    ind, det = D.indice_developpement()
    pdf.section("Développement — indice multifactoriel")
    if ind.empty:
        pdf.paragraphe("Données insuffisantes.")
        return {}
    f = fig_developpement(ind)
    pdf.figure(f, "Six dimensions : économique, politique & institutions, social, culture & ouverture, population, "
                  "nature & environnement. Source : calculs Ayiti Data Hub sur données Banque mondiale.")
    for p in lecture(ind):
        pdf.paragraphe(p, puce=True)
    pdf.tableau(det[["dimension", "indicateur", "sens", "premiere_annee", "derniere_annee"]], [42, 70, 20, 23, 23])
    return {"indice_developpement.png": f}


def economie(pdf: RapportPDF) -> dict[str, bytes]:
    pdf.section("Économie & finances")
    imgs = {}
    a = D.indicateurs_actuels()
    for code, unite, lien_ in [("NY.GDP.MKTP.KD.ZG", "%", "Croissance du PIB réel"), ("FP.CPI.TOTL.ZG", "%", "Inflation (prix à la consommation)"),
                               ("NY.GDP.PCAP.KD", "USD", None), ("BX.TRF.PWKR.DT.GD.ZS", "% PIB", None)]:
        s = D.serie(code)
        if not len(s):
            continue
        rec = None
        if lien_:
            r = a[a.indicateur == lien_].copy()
            r["annee"] = pd.to_numeric(r.periode, errors="coerce")
            rec = r.dropna(subset=["annee"])[["annee", "valeur"]]
        lab = INDICATEURS_CLES[code][0]
        f = fig_ligne({lab: s[s.annee >= 1980]}, lab, unite, rec)
        imgs[f"{code}.png"] = f
        pdf.figure(f)
        for p in analyser_serie(s, lab, unite)[:3]:
            pdf.paragraphe(p, puce=True)
    pdf.paragraphe("Chiffres récents (sources datées) :")
    pdf.tableau(a[a.theme.isin(["Économie", "Finances publiques", "Secteur extérieur"])][["indicateur", "periode", "valeur", "unite", "source"]],
                [62, 22, 20, 28, 46])
    return imgs


def population(pdf: RapportPDF) -> dict[str, bytes]:
    dep, com = D.departements(), D.communes()
    pdf.section("Population & territoire")
    f1 = fig_barres(list(dep.departement), list(dep.population), "Population par département (2022)", "habitants")
    f2 = fig_carte(D.geojson("communes"), dict(zip(com.adm2_pcode, com.part_enfants_pct)),
                   "Part des moins de 18 ans par commune (%)", "Oranges", label="%")
    pdf.figure(f1)
    pdf.figure(f2)
    top = com.nlargest(15, "population")[["commune", "departement", "population", "densite_hab_km2", "part_enfants_pct"]]
    pdf.tableau(top, [45, 35, 32, 34, 32])
    return {"population_departements.png": f1, "carte_jeunesse.png": f2}


def education(pdf: RapportPDF) -> dict[str, bytes]:
    pdf.section("Éducation & institutions")
    ec, uni = D.ecoles(), D.universites()
    ies = pd.read_csv(T.CURATED / "ies_privees_par_departement_2026.csv")
    f1 = fig_barres(list(ies.departement), list(ies.institutions_privees), "IES privées reconnues par département (2026)", "institutions")
    e = ec.groupby("departement").size()
    f2 = fig_barres(list(e.index), list(e.values), "Écoles recensées (cartographie 2022, 4 départements)", "écoles", couleur=SERIES[1])
    pdf.paragraphe(f"{len(ec)} établissements scolaires recensés en 2022 (Grand'Anse, Nippes, Sud, 8 communes de l'Ouest), "
                   f"dont {100 * (ec.secteur == 'Public').mean():.0f} % publics. {len(uni)} institutions d'enseignement "
                   "supérieur reconnues dans la liste du MENFP ; 190 en 2026 contre 138 en 2018 (+38 %).")
    dep = D.departements()
    imgs_osm = {}
    if "nb_ecoles_osm" in dep:
        f3 = fig_barres(list(dep.departement), list(dep.ecoles_osm_pour_1000_enfants),
                        "Écoles OpenStreetMap pour 1 000 enfants, par département (tout le pays)", "écoles / 1 000 enfants",
                        couleur=SERIES[4])
        com = D.communes()
        f4 = fig_carte(D.geojson("communes"), dict(zip(com.adm2_pcode, com.ecoles_osm_pour_1000_enfants.clip(upper=4))),
                       "Écoles OpenStreetMap pour 1 000 enfants par commune", "Oranges", label="écoles / 1 000 enfants")
        pdf.paragraphe(f"OpenStreetMap recense {int(dep.nb_etab_education_osm.sum())} établissements d'enseignement "
                       f"géolocalisés sur tout le territoire ({int(dep.nb_superieur_osm.sum())} établissements supérieurs). "
                       "Cette carte collaborative couvre tout le pays mais reste incomplète en zone rurale.")
        pdf.figure(f4)
        pdf.figure(f3)
        imgs_osm = {"carte_ecoles_osm.png": f4, "ecoles_osm_departements.png": f3}
    pdf.figure(f1)
    pdf.figure(f2)
    pdf.tableau(uni[uni.statut == "Public"][["nom", "composante", "commune"]].head(35), [110, 30, 38], max_lignes=35)
    return {"ies_departements.png": f1, "ecoles_departements.png": f2, **imgs_osm}


def humanitaire(pdf: RapportPDF) -> dict[str, bytes]:
    pdf.section("Humanitaire & sécurité alimentaire")
    f = fig_barres(["mars-juin 2023", "sept. 2025 (proj.)", "mars-juin 2026 (proj.)"], [4_890_000, 5_910_000, 5_830_000],
                   "Personnes en phase IPC 3 ou plus", "personnes", couleur="#d03b3b")
    pdf.figure(f, "Source : IPC.")
    for t in ["5,83 millions de personnes (52 % de la population analysée) en phase IPC 3 ou plus en mars-juin 2026, "
              "dont près de 1,9 million en urgence (phase 4).",
              "Environ 1,5 million de personnes déplacées internes en septembre 2026 (OIM), dont ~80 % hors de Port-au-Prince.",
              "Les zones en phase 4 : Nord-Ouest, Bas-Artibonite, Bas-Plateau, Gonâve, Belle-Anse, quartiers pauvres de "
              "Port-au-Prince et Cité Soleil."]:
        pdf.paragraphe(t, puce=True)
    org = D.organisations()
    if len(org):
        k = org.groupby("categorie").size().sort_values()
        f2 = fig_barres(list(k.index), list(k.values), "Organisations recensées en 2020 par catégorie", "organisations", couleur=SERIES[2])
        pdf.figure(f2)
        return {"ipc.png": f, "organisations.png": f2}
    return {"ipc.png": f}


def richesses(pdf: RapportPDF) -> dict[str, bytes]:
    pdf.section("Richesses & ressources")
    for x in D.richesses().itertuples():
        pdf.set_font("DV", "B", 11)
        pdf.set_text_color(11, 11, 11)
        pdf.set_x(pdf.l_margin)
        pdf.multi_cell(0, 6, f"{x.ressource} — {x.chiffre_cle}")
        pdf.paragraphe(x.description)
        if isinstance(x.url, str):
            pdf.lien(f"Source : {x.source}", x.url)
        pdf.ln(1)
    return {}


def tourisme(pdf: RapportPDF) -> dict[str, bytes]:
    pdf.section("Tourisme & cadre de vie")
    s = T.sites_touristiques().assign(categorie="Sites")
    f1 = fig_carte(D.geojson("communes"), None, "Sites touristiques et patrimoniaux", points=s[["lon", "lat", "categorie"]])
    pdf.figure(f1)
    pdf.tableau(s[["nom", "type", "commune"]], [80, 55, 43], max_lignes=30)
    cv = T.indice_cadre_de_vie()
    top = cv.nsmallest(15, "rang")
    f2 = fig_barres(list(top.commune), list(top.indice_cadre_de_vie), "Indice « cadre de vie » : 15 communes en tête", "/100",
                    couleur=SERIES[2])
    pdf.figure(f2, "Indice composite : services, accessibilité, nature (mer, sites), densité équilibrée, vie urbaine. "
                   "La sécurité n'est pas mesurée : consulter les avis officiels.")
    return {"sites_touristiques.png": f1, "cadre_de_vie.png": f2}


def territoire(pdf: RapportPDF) -> dict[str, bytes]:
    pdf.section("Îles, routes & transports")
    il = T.iles()
    pdf.tableau(il[["ile", "departement", "population_2022", "superficie_km2"]].fillna("–"), [70, 45, 33, 30])
    tr = T.transports().dropna(subset=["lat"])
    pts = tr.assign(categorie=tr.type.map(lambda t: "Aéroports" if "Aéroport" in str(t) else "Ports"))
    f = fig_carte(D.geojson("communes"), None, "Aéroports et ports", points=pts[["lon", "lat", "categorie"]])
    pdf.figure(f)
    r = T.longueur_km(T.routes_osm() or T.routes_schematiques())
    if "villes" in r:
        pdf.tableau(r[["ref", "nom", "villes"]], [15, 55, 108])
    return {"transports.png": f}


def actualites(pdf: RapportPDF) -> dict[str, bytes]:
    pdf.section("Actualités récentes")
    n = D.actualites_enrichies()
    if n.empty:
        pdf.paragraphe("Aucune actualité téléchargée.")
        return {}
    n = n.assign(_p=(n.priorite > 0.2).astype(int)).sort_values(["_p", "date"], ascending=[False, False]).head(25)
    for x in n.itertuples():
        pdf.set_font("DV", "", 8)
        pdf.set_text_color(138, 137, 132)
        pdf.cell(0, 4, f"{str(x.date)[:10]} · {x.theme} · {x.tonalite} · {x.source}")
        pdf.ln(4)
        pdf.lien(str(x.titre), str(x.url))
        pdf.ln(1)
    return {}


def fiche_commune(pdf: RapportPDF, pcode: str) -> dict[str, bytes]:
    com = D.communes()
    c = com[com.adm2_pcode == pcode].iloc[0]
    pdf.section(f"Fiche commune — {c.commune} ({c.departement})")
    pdf.chiffres([("Population 2022", fmt_fr(c.population)), ("Densité", f"{fmt_fr(c.densite_hab_km2)} hab/km²"),
                  ("Superficie", f"{fmt_fr(c.superficie_km2, 1)} km²"), ("Localités", str(int(c.nb_localites))),
                  ("Moins de 18 ans", f"{c.part_enfants_pct:.1f} %"),
                  ("Écoles 2022", str(int(c.nb_ecoles)) if c.couverture_ecoles_2022 else "non couvert")])
    geo = D.geojson("communes")
    f = fig_carte(geo, {pcode: 1.0, **{x: 0.15 for x in com[com.departement == c.departement].adm2_pcode if x != pcode}},
                  f"Localisation de {c.commune}", "Blues")
    pdf.figure(f, largeur=140)
    for p in analyser_commune(c, com):
        pdf.paragraphe(p, puce=True)
    s = D.sections()
    pdf.tableau(s[s.adm2_pcode == pcode][["adm3_pcode", "section_communale", "superficie_km2", "nb_localites"]], [30, 80, 34, 34])
    return {f"commune_{pcode}.png": f}


def generer(sections: list[str], titre: str, pcode: str | None = None, photo: str | None = None) -> tuple[bytes, dict[str, bytes]]:
    pdf = RapportPDF(titre)
    com = D.communes()
    couv = fig_carte(D.geojson("communes"), dict(zip(com.adm2_pcode, com.population)), "", "Blues", label="habitants")
    pdf.couverture("Rapport généré automatiquement à partir des données ouvertes sur Haïti : " + ", ".join(sections) + ".",
                   None, photo)
    imgs = {}
    fonctions = {"Synthèse nationale": synthese, "Développement (indice multifactoriel)": developpement,
                 "Économie & finances": economie, "Population & territoire": population,
                 "Éducation & institutions": education, "Humanitaire & sécurité alimentaire": humanitaire,
                 "Richesses & ressources": richesses, "Tourisme & cadre de vie": tourisme,
                 "Îles, routes & transports": territoire, "Actualités récentes": actualites}
    for s in sections:
        if s == "Fiche commune" and pcode:
            imgs.update(fiche_commune(pdf, pcode))
        elif s in fonctions:
            imgs.update(fonctions[s](pdf))
    pdf.section("Sources")
    src = pd.read_csv(T.CURATED / "sources.csv")
    for x in src.itertuples():
        pdf.paragraphe(f"{x.donnees} — {x.producteur} ({x.periode}).", puce=True)
        if isinstance(x.url, str) and x.url:
            pdf.lien("   " + x.url, x.url)
    imgs["carte_population.png"] = couv
    return bytes(pdf.output()), imgs
