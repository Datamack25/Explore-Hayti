"""Classement thématique et tonalité des actualités (règles transparentes, FR / EN / créole).

- theme : Économie, Politique, Tourisme, Culture, Sport, Éducation & science, Santé, Environnement,
          Diaspora, Agriculture, Sécurité, Humanitaire, Société
- tonalite : score de -1 à +1 (mots positifs vs négatifs) -> « Positif », « Neutre », « Négatif »
La plateforme met en avant les nouvelles positives sans masquer les autres (filtre au choix).
"""
from __future__ import annotations

import re
import unicodedata

THEMES: dict[str, list[str]] = {
    "Tourisme": ["touris", "plage", "beach", "hotel", "hôtel", "croisi", "cruise", "visiteur", "labadee", "jacmel",
                 "ile-a-vache", "île-à-vache", "citadelle", "destination", "voyage", "travel", "resort"],
    "Culture": ["cultur", "artiste", "artist", "musique", "music", "kompa", "konpa", "rara", "carnaval", "carnival",
                "festival", "film", "cinéma", "cinema", "livre", "book", "écrivain", "writer", "peintre", "painting",
                "exposition", "exhibit", "patrimoine", "heritage", "unesco", "soup joumou", "gastronom", "cuisine",
                "littérature", "poète", "danse", "vodou", "musée", "museum", "mode", "fashion", "créole", "kreyòl"],
    "Sport": ["sport ", "sports", "sportif", "sportive", "football", "foot", "grenadier", "match", "coupe", "cup", "champion", "olymp", "athlète",
              "athlete", "basket", "boxe", "fifa", "concacaf", "médaille", "medal"],
    "Économie": ["économ", "econom", "transport", "infrastructur", "port ", "aéroport", "airport", "route", "investiss", "invest", "entreprise", "business", "export", "import", "brh",
                 "gourde", "dollar", "inflation", "pib", "gdp", "banque", "bank", "commerce", "trade", "emploi",
                 "job", "startup", "fintech", "transfert", "remittance", "budget", "fmi", "imf", "marché", "prix"],
    "Agriculture": ["agricult", "récolte", "harvest", "café", "coffee", "cacao", "cocoa", "mangue", "mango",
                    "vétiver", "vetiver", "pêche", "fishing", "élevage", "riz", "rice", "planteur", "farmer"],
    "Éducation & science": ["école", "school", "universit", "étudiant", "student", "éducation", "education",
                            "bourse", "scholarship", "recherche", "research", "science", "innovation", "technolog",
                            "diplôme", "graduate", "bac ", "examen", "menfp", "robot", "numérique", "digital"],
    "Santé": ["santé", "health", "hôpital", "hospital", "médecin", "doctor", "vaccin", "vaccine", "choléra",
              "cholera", "mspp", "clinique", "maladie", "disease", "malnutrition"],
    "Environnement": ["environnement", "environment", "climat", "climate", "reboisement", "reforest", "forêt",
                      "forest", "énergie", "energy", "solaire", "solar", "ouragan", "hurricane", "séisme",
                      "earthquake", "biodiversit", "mangrove", "corail", "coral", "parc national", "eau potable"],
    "Diaspora": ["diaspora", "haïtiano-", "haitian-american", "haitian american", "miami", "montréal", "montreal",
                 "boston", "new york", "brooklyn", "tps", "immigra", "migrant", "dominicain", "dominican"],
    "Politique": ["politi", "gouvernement", "government", "premier ministre", "prime minister", "président",
                  "president", "élection", "election", "csp", "conseil présidentiel", "parlement", "sénat",
                  "ministre", "minister", "transition", "constitution", "onu", "un security", "diplomat", "ambassad"],
    "Sécurité": ["gang", "violence", "kidnap", "enlèvement", "police", "pnh", "armée", "army", "sécurité",
                 "security", "mission multinationale", "kenya", "attaque", "attack", "tué", "killed", "fusillade",
                 "shooting", "viv ansanm", "gsf"],
    "Humanitaire": ["humanitaire", "humanitarian", "déplacé", "displaced", "faim", "hunger", "ipc", "pam", "wfp",
                    "unicef", "oim", "iom", "aide", "aid", "réfugié", "refugee", "ocha", "crise alimentaire"],
}

POSITIFS = ["succès", "success", "réussi", "réussite", "victoire", "victory", "gagne", "wins", "won", "prix ",
            "award", "lauréat", "laureate", "inaugur", "lance", "launch", "ouvre", "opens", "nouveau", "new ",
            "croissance", "growth", "hausse des export", "record", "fier", "proud", "célèbr", "celebrat", "festival",
            "innovation", "innov", "talent", "excellence", "espoir", "hope", "améliora", "improve", "progrès",
            "progress", "reprise", "recovery", "relance", "partenariat", "partnership", "accord", "agreement",
            "investiss", "financement", "funding", "bourse", "scholarship", "diplômé", "graduat", "médaille", "medal",
            "qualifi", "champion", "beauté", "beauty", "magnifique", "patrimoine", "heritage", "reboisement",
            "solidarit", "reconstru", "rebuild", "soutien", "support", "honneur", "honor", "première", "first",
            "bravo", "félicit", "potentiel", "potential", "opportunit", "investment", "advocat", "feed", "congrat", "kontan", "bèl", "viktwa", "siksè", "pwogrè", "espwa"]

NEGATIFS = ["gang", "violence", "tué", "killed", "mort", "dead", "death", "massacre", "kidnap", "enlèvement",
            "attaque", "attack", "crise", "crisis", "faim", "hunger", "famine", "choléra", "cholera", "déplacé",
            "displaced", "insécurité", "insecurity", "fusillade", "shooting", "incendie", "fire", "chaos",
            "effondr", "collapse", "pénurie", "shortage", "catastroph", "disaster", "victime", "victim", "viol",
            "rape", "corruption", "sanction", "expuls", "deport", "pillage", "looting", "blessé", "injured",
            "panique", "fuite", "flee", "drame", "tragédie", "tragedy", "inondation", "flood", "séisme",
            "earthquake", "ouragan", "hurricane", "suspend", "fermé", "closed", "recul", "decline", "chute",
            "contracted", "contraction", "contracte", "lanmò", "kidnapin", "ensekirite", "grangou"]


def _norm(t: str) -> str:
    t = unicodedata.normalize("NFKC", str(t or "")).lower()
    return re.sub(r"\s+", " ", t)


_LETTRE = "a-z0-9àâäçéèêëîïôöûùüÿœ"


def _compte(t: str, mots: list[str]) -> int:
    """Nombre de mots-clés trouvés en DÉBUT de mot (« cultur » ne compte pas dans « agricultural »)."""
    return sum(len(re.findall(rf"(?<![{_LETTRE}]){re.escape(m.strip())}", t)) for m in mots)


def theme(titre: str, resume: str = "") -> str:
    t = _norm(f"{titre} {resume}")
    scores = {k: _compte(t, mots) for k, mots in THEMES.items()}
    best = max(scores, key=scores.get)
    return best if scores[best] > 0 else "Société"


def tonalite(titre: str, resume: str = "") -> float:
    t = _norm(f"{titre} {resume}")
    p = _compte(t, POSITIFS)
    n = _compte(t, NEGATIFS)
    if p == n == 0:
        return 0.0
    return round((p - n) / (p + n), 2)


def etiquette(score: float) -> str:
    return "Positif" if score > 0.15 else "Négatif" if score < -0.15 else "Neutre"


THEMES_POSITIFS = {"Tourisme", "Culture", "Sport", "Éducation & science", "Agriculture", "Environnement", "Diaspora"}


def priorite(score: float, th: str) -> float:
    """Score d'affichage : met en avant les nouvelles positives et les thèmes valorisants."""
    return score + (0.35 if th in THEMES_POSITIFS else 0.0)
