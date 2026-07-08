# Chaque recette : (nom_recette, [(nom_ingredient, quantite), ...], nom_plat_resultat, rang_requis)
# rang_requis : 0 = Apprenti, 1 = Confirmé, 2 = Maître

RECETTES = [
    ("Soupe de fortune", [("Poisson argenté", 2)], "Soupe de fortune", 0),
    ("Riz sauté du marin", [("Baies sucrées", 1), ("Racine noueuse", 1)], "Riz sauté du marin", 0),
    ("Ragoût de sanglier", [("Viande de sanglier des mers", 1), ("Champignon des embruns", 1)], "Ragoût de sanglier", 1),
    ("Poisson tigre grillé", [("Poisson tigre", 1), ("Baies sucrées", 1)], "Poisson tigre grillé", 1),
    ("Tarte de la moisson", [("Fleur de corail", 2)], "Tarte de la moisson", 1),
    ("Festin du capitaine", [("Peau de varan des dunes", 1), ("Fleur de corail", 1), ("Poisson tigre", 1)], "Festin du capitaine", 2),
]
