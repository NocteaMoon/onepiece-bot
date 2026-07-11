RANGS_CODES = ["Membre", "Compagnon", "Expert", "Maitre"]
MAX_MEMBRES = 10
COUT_CREATION = 200

TITRES_PAR_METIER = {
    "Cuisinier": {"Membre": "Marmiton", "Compagnon": "Second de Cuisine", "Expert": "Chef Cuisinier"},
    "Forgeron": {"Membre": "Apprenti Forgeron", "Compagnon": "Compagnon Forgeron", "Expert": "Forgeron Confirmé"},
    "Médecin": {"Membre": "Aide-Soignant(e)", "Compagnon": "Infirmier(ère)", "Expert": "Médecin"},
    "Navigateur": {"Membre": "Mousse", "Compagnon": "Timonier(ère)", "Expert": "Navigateur Confirmé"},
    "Charpentier": {"Membre": "Apprenti Charpentier", "Compagnon": "Compagnon Charpentier", "Expert": "Charpentier Confirmé"},
    "Musicien": {"Membre": "Apprenti Ménestrel", "Compagnon": "Ménestrel", "Expert": "Musicien de Renom"},
    "Archéologue": {"Membre": "Apprenti Archéologue", "Compagnon": "Archéologue", "Expert": "Archéologue Renommé"},
}

METIER_EMOJIS = {
    "Cuisinier": "🍳",
    "Forgeron": "🔨",
    "Médecin": "💊",
    "Navigateur": "🧭",
    "Charpentier": "🚢",
    "Musicien": "🎵",
    "Archéologue": "🏺",
}

def rang_valeur(rang: str) -> int:
    try:
        return RANGS_CODES.index(rang)
    except ValueError:
        return 0

def titre_pour(code: str, metier: str) -> str:
    if code == "Maitre":
        return "Maître(sse) de Guilde"
    metier_titres = TITRES_PAR_METIER.get(metier)
    if not metier_titres:
        return "Novice"
    return metier_titres.get(code, "Novice")

def emoji_pour(metier: str) -> str:
    return METIER_EMOJIS.get(metier, "🧵")
