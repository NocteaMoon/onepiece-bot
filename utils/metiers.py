METIERS_DISPONIBLES = ["Cuisinier", "Forgeron", "Médecin", "Navigateur"]

RANG_LABELS = {0: "Apprenti", 1: "Confirmé", 2: "Maître"}
SEUILS_RANG = {0: 0, 1: 150, 2: 400}

def get_rang(metier_xp: int) -> int:
    rang = 0
    for r, seuil in sorted(SEUILS_RANG.items()):
        if metier_xp >= seuil:
            rang = r
    return rang

def rang_label(rang: int) -> str:
    return RANG_LABELS.get(rang, "Apprenti")
