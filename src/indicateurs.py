"""Indicateurs clés de la Banque mondiale, traduits en français et classés par thème.

Le script de mise à jour (scripts/update_world_bank.py) interroge en priorité cette liste.
"""

INDICATEURS_CLES: dict[str, tuple[str, str, str]] = {
    # code: (libellé français, thème, unité courte)
    # --- Croissance & revenus
    "NY.GDP.MKTP.CD": ("PIB (USD courants)", "Croissance & revenus", "USD"),
    "NY.GDP.MKTP.KD.ZG": ("Croissance du PIB réel", "Croissance & revenus", "%"),
    "NY.GDP.PCAP.CD": ("PIB par habitant (USD courants)", "Croissance & revenus", "USD"),
    "NY.GDP.PCAP.KD": ("PIB par habitant (USD constants 2015)", "Croissance & revenus", "USD"),
    "NY.GDP.PCAP.KD.ZG": ("Croissance du PIB par habitant", "Croissance & revenus", "%"),
    "NY.GNP.PCAP.CD": ("RNB par habitant, méthode Atlas (USD)", "Croissance & revenus", "USD"),
    "NV.AGR.TOTL.ZS": ("Agriculture, valeur ajoutée (% du PIB)", "Croissance & revenus", "% PIB"),
    "NV.IND.TOTL.ZS": ("Industrie, valeur ajoutée (% du PIB)", "Croissance & revenus", "% PIB"),
    "NV.SRV.TOTL.ZS": ("Services, valeur ajoutée (% du PIB)", "Croissance & revenus", "% PIB"),
    "NE.CON.PRVT.ZS": ("Consommation des ménages (% du PIB)", "Croissance & revenus", "% PIB"),
    "NE.GDI.TOTL.ZS": ("Formation brute de capital (% du PIB)", "Croissance & revenus", "% PIB"),
    # --- Prix & monnaie
    "FP.CPI.TOTL.ZG": ("Inflation, prix à la consommation", "Prix & monnaie", "%"),
    "NY.GDP.DEFL.KD.ZG": ("Inflation, déflateur du PIB", "Prix & monnaie", "%"),
    "PA.NUS.FCRF": ("Taux de change officiel (HTG pour 1 USD)", "Prix & monnaie", "HTG"),
    "FM.LBL.BMNY.GD.ZS": ("Masse monétaire large (% du PIB)", "Prix & monnaie", "% PIB"),
    "FR.INR.LEND": ("Taux d'intérêt débiteur", "Prix & monnaie", "%"),
    "FR.INR.RINR": ("Taux d'intérêt réel", "Prix & monnaie", "%"),
    # --- Secteur financier
    "FS.AST.PRVT.GD.ZS": ("Crédit intérieur au secteur privé (% du PIB)", "Secteur financier", "% PIB"),
    "FB.BNK.CAPA.ZS": ("Ratio fonds propres / actifs des banques", "Secteur financier", "%"),
    "FB.AST.NPER.ZS": ("Prêts non performants (% des prêts bruts)", "Secteur financier", "%"),
    "FB.CBK.BRCH.P5": ("Agences bancaires pour 100 000 adultes", "Secteur financier", "/100k"),
    "FB.ATM.TOTL.P5": ("Distributeurs automatiques pour 100 000 adultes", "Secteur financier", "/100k"),
    "FI.RES.TOTL.CD": ("Réserves totales, or compris (USD)", "Secteur financier", "USD"),
    "FI.RES.TOTL.MO": ("Réserves totales en mois d'importations", "Secteur financier", "mois"),
    # --- Commerce & extérieur
    "NE.EXP.GNFS.ZS": ("Exportations de biens et services (% du PIB)", "Commerce & extérieur", "% PIB"),
    "NE.IMP.GNFS.ZS": ("Importations de biens et services (% du PIB)", "Commerce & extérieur", "% PIB"),
    "TX.VAL.MRCH.CD.WT": ("Exportations de marchandises (USD)", "Commerce & extérieur", "USD"),
    "TM.VAL.MRCH.CD.WT": ("Importations de marchandises (USD)", "Commerce & extérieur", "USD"),
    "TG.VAL.TOTL.GD.ZS": ("Commerce de marchandises (% du PIB)", "Commerce & extérieur", "% PIB"),
    "BX.TRF.PWKR.CD.DT": ("Transferts de fonds reçus (USD)", "Commerce & extérieur", "USD"),
    "BX.TRF.PWKR.DT.GD.ZS": ("Transferts de fonds reçus (% du PIB)", "Commerce & extérieur", "% PIB"),
    "BX.KLT.DINV.CD.WD": ("Investissements directs étrangers, entrées nettes (USD)", "Commerce & extérieur", "USD"),
    "BN.CAB.XOKA.GD.ZS": ("Solde du compte courant (% du PIB)", "Commerce & extérieur", "% PIB"),
    "DT.ODA.ODAT.CD": ("Aide publique au développement reçue (USD)", "Commerce & extérieur", "USD"),
    "DT.ODA.ODAT.GN.ZS": ("Aide publique au développement (% du RNB)", "Commerce & extérieur", "% RNB"),
    # --- Dette
    "DT.DOD.DECT.CD": ("Dette extérieure totale (USD)", "Dette", "USD"),
    "DT.DOD.DECT.GN.ZS": ("Dette extérieure (% du RNB)", "Dette", "% RNB"),
    "DT.TDS.DECT.EX.ZS": ("Service de la dette (% des exportations)", "Dette", "%"),
    # --- Secteur public
    "GC.REV.XGRT.GD.ZS": ("Recettes publiques hors dons (% du PIB)", "Secteur public", "% PIB"),
    "GC.TAX.TOTL.GD.ZS": ("Recettes fiscales (% du PIB)", "Secteur public", "% PIB"),
    "MS.MIL.XPND.GD.ZS": ("Dépenses militaires (% du PIB)", "Secteur public", "% PIB"),
    "IC.BUS.EASE.XQ": ("Facilité de faire des affaires (rang)", "Secteur public", "rang"),
    "IC.REG.DURS": ("Délai de création d'entreprise (jours)", "Secteur public", "jours"),
    # --- Population & société
    "SP.POP.TOTL": ("Population totale", "Population & société", "hab."),
    "SP.POP.GROW": ("Croissance démographique", "Population & société", "%"),
    "SP.URB.TOTL.IN.ZS": ("Population urbaine (% du total)", "Population & société", "%"),
    "SP.RUR.TOTL.ZS": ("Population rurale (% du total)", "Population & société", "%"),
    "SP.DYN.LE00.IN": ("Espérance de vie à la naissance", "Population & société", "ans"),
    "SP.DYN.TFRT.IN": ("Indice de fécondité", "Population & société", "enfants/femme"),
    "SP.DYN.IMRT.IN": ("Mortalité infantile (pour 1 000)", "Population & société", "‰"),
    "SE.PRM.ENRR": ("Scolarisation primaire (brut, %)", "Population & société", "%"),
    "SE.SEC.ENRR": ("Scolarisation secondaire (brut, %)", "Population & société", "%"),
    "SE.ADT.LITR.ZS": ("Taux d'alphabétisation des adultes", "Population & société", "%"),
    "SL.UEM.TOTL.ZS": ("Chômage (% de la population active, OIT)", "Population & société", "%"),
    "SI.POV.GINI": ("Indice de Gini", "Population & société", "indice"),
    "EG.ELC.ACCS.ZS": ("Accès à l'électricité (% de la population)", "Population & société", "%"),
    "IT.NET.USER.ZS": ("Utilisateurs d'Internet (% de la population)", "Population & société", "%"),
    "IT.CEL.SETS.P2": ("Abonnements mobiles pour 100 habitants", "Population & société", "/100"),
    "SH.H2O.BASW.ZS": ("Accès à l'eau potable de base (%)", "Population & société", "%"),
    # --- Agriculture & environnement
    "AG.LND.AGRI.ZS": ("Terres agricoles (% du territoire)", "Agriculture & environnement", "%"),
    "AG.LND.FRST.ZS": ("Surface forestière (% du territoire)", "Agriculture & environnement", "%"),
    "AG.PRD.CREL.MT": ("Production de céréales (tonnes)", "Agriculture & environnement", "t"),
    "AG.YLD.CREL.KG": ("Rendement céréalier (kg/ha)", "Agriculture & environnement", "kg/ha"),
    "SL.AGR.EMPL.ZS": ("Emploi agricole (% de l'emploi total)", "Agriculture & environnement", "%"),
    "EN.ATM.CO2E.PC": ("Émissions de CO2 par habitant (t)", "Agriculture & environnement", "t"),
}

THEMES_FICHIERS = {
    "economy-and-growth": "Économie et croissance",
    "financial-sector": "Secteur financier",
    "private-sector": "Secteur privé",
    "trade": "Commerce",
    "external-debt": "Dette extérieure",
    "public-sector": "Secteur public",
    "agriculture-and-rural-development": "Agriculture et développement rural",
    "millenium-development-goals": "Objectifs du millénaire",
}

# Événements majeurs à annoter sur les séries temporelles
EVENEMENTS = [
    (1986, "Fin du régime Duvalier"),
    (1991, "Coup d'État"),
    (1994, "Fin de l'embargo"),
    (2004, "Crise politique"),
    (2008, "Crise alimentaire & cyclones"),
    (2010, "Séisme du 12 janvier"),
    (2016, "Ouragan Matthew"),
    (2018, "Crise du carburant"),
    (2021, "Assassinat du président & séisme du Sud"),
]


def libelle(code: str, defaut: str = "") -> str:
    return INDICATEURS_CLES.get(code, (defaut or code,))[0]
