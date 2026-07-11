# (code, nom, categorie, description, bonus_stats, prix, poids_loot)

FRUITS = [
    # Singulier (Mineur) - pouvoirs uniques et polyvalents
    ("fruit_roc", "Fruit du Roc", "Singulier", "Confère une robustesse semblable à la pierre.", {"force": 8, "defense": 0, "vitesse": 0, "agilite": 0}, 5000, 30),
    ("fruit_vent", "Fruit du Vent", "Singulier", "Permet de générer de puissantes rafales.", {"force": 0, "defense": 0, "vitesse": 8, "agilite": 0}, 5000, 30),
    ("fruit_fer", "Fruit du Fer", "Singulier", "Durcit la peau comme du métal.", {"force": 0, "defense": 8, "vitesse": 0, "agilite": 0}, 5000, 30),
    ("fruit_mirage", "Fruit du Mirage", "Singulier", "Brouille la perception des adversaires.", {"force": 0, "defense": 0, "vitesse": 0, "agilite": 8}, 5000, 30),
    ("fruit_poids", "Fruit du Poids", "Singulier", "Manipule la gravité autour de son porteur.", {"force": 5, "defense": 5, "vitesse": 0, "agilite": 0}, 5000, 30),
    ("fruit_echo", "Fruit de l'Écho", "Singulier", "Projette des ondes sonores dévastatrices.", {"force": 0, "defense": 0, "vitesse": 5, "agilite": 5}, 5000, 30),

    # Élémentaire (Majeur) - contrôle d'un élément
    ("fruit_flammes", "Fruit des Flammes", "Élémentaire", "Le corps se transforme en flammes vivantes.", {"force": 12, "defense": 0, "vitesse": 6, "agilite": 0}, 15000, 12),
    ("fruit_gel", "Fruit du Gel", "Élémentaire", "Permet de geler et de se transformer en glace.", {"force": 0, "defense": 12, "vitesse": 0, "agilite": 6}, 15000, 12),
    ("fruit_foudre", "Fruit de la Foudre", "Élémentaire", "Le corps devient électricité pure.", {"force": 6, "defense": 0, "vitesse": 12, "agilite": 0}, 15000, 12),
    ("fruit_sables", "Fruit des Sables", "Élémentaire", "Le corps se dissout en sable mouvant.", {"force": 6, "defense": 12, "vitesse": 0, "agilite": 0}, 15000, 12),
    ("fruit_tenebres", "Fruit des Ténèbres", "Élémentaire", "Absorbe et manipule les ténèbres.", {"force": 7, "defense": 7, "vitesse": 0, "agilite": 0}, 15000, 12),

    # Mutation (Suprême) - transformations les plus puissantes
    ("fruit_tigre", "Fruit du Tigre Ancestral", "Mutation", "Autorise la transformation en tigre légendaire.", {"force": 16, "defense": 0, "vitesse": 10, "agilite": 0}, 40000, 4),
    ("fruit_dragon", "Fruit du Dragon Oublié", "Mutation", "Le plus rare de tous, il éveille une force draconique.", {"force": 12, "defense": 12, "vitesse": 12, "agilite": 12}, 40000, 2),
    ("fruit_phenix", "Fruit du Phénix Renaissant", "Mutation", "Confère une résistance quasi surnaturelle.", {"force": 0, "defense": 18, "vitesse": 0, "agilite": 8}, 40000, 4),
    ("fruit_loup", "Fruit du Loup des Neiges", "Mutation", "Autorise la transformation en loup des glaces.", {"force": 8, "defense": 0, "vitesse": 18, "agilite": 0}, 40000, 4),
]
