# Catalogue d'objets par défaut, dans l'esprit One Piece (noms originaux, non copiés de l'œuvre).
# (nom, description, categorie, faction, rarete, prix, slot,
#  b_force, b_defense, b_vitesse, b_agilite, b_pv, b_chance,
#  soin_pv, soin_endurance, durabilite_max, stock, niveau_requis)

CATALOGUE = [
    # ===== CONSOMMABLES (communs à tous) =====
    ("Ration de bord", "Restaure un peu d'endurance.", "Consommable", "Tous", "Commun", 30, None, 0,0,0,0,0,0, 0, 40, 1, -1, 1),
    ("Repas de taverne", "Un bon repas chaud qui redonne des forces.", "Consommable", "Tous", "Commun", 60, None, 0,0,0,0,0,0, 30, 60, 1, -1, 1),
    ("Potion de soin", "Restaure 50 PV instantanément.", "Consommable", "Tous", "Aiguisé", 120, None, 0,0,0,0,0,0, 50, 0, 1, -1, 1),
    ("Grand remède", "Restaure 120 PV instantanément.", "Consommable", "Tous", "Grade", 300, None, 0,0,0,0,0,0, 120, 0, 1, 20, 5),
    ("Élixir du médecin", "Restaure tous les PV et l'endurance.", "Consommable", "Tous", "Grand Grade", 800, None, 0,0,0,0,0,0, 9999, 9999, 1, 20, 10),

    # ===== ACCESSOIRES (communs) =====
    ("Bandana usé", "Un simple bandana. +2 agilité.", "Accessoire", "Tous", "Commun", 80, "accessoire", 0,0,0,2,0,0, 0,0, 100, -1, 1),
    ("Longue-vue", "Améliore la perception. +3 chance.", "Accessoire", "Tous", "Aiguisé", 200, "accessoire", 0,0,0,0,0,3, 0,0, 100, -1, 1),
    ("Amulette de jade", "Une amulette porte-bonheur. +5 chance.", "Accessoire", "Tous", "Grade", 500, "accessoire", 0,0,0,0,0,5, 0,0, 100, 5, 1),
    ("Ceinture lestée", "Entraînement au poids. +4 force.", "Accessoire", "Tous", "Grade", 450, "accessoire", 4,0,0,0,0,0, 0,0, 100, 5, 1),
    ("Boussole enchantée", "Ne perd jamais le nord. +6 chance, +2 vitesse.", "Accessoire", "Tous", "Grand Grade", 1200, "accessoire", 0,0,2,0,0,6, 0,0, 100, 10, 1),

    # ===== ARMURES / TÊTE (communs) =====
    ("Foulard de matelot", "Protection minime. +2 défense.", "Tête", "Tous", "Commun", 70, "tete", 0,2,0,0,0,0, 0,0, 100, -1, 1),
    ("Casque de cuir", "Un casque simple. +5 défense.", "Tête", "Tous", "Aiguisé", 180, "tete", 0,5,0,0,0,0, 0,0, 120, -1, 1),
    ("Manteau renforcé", "Un manteau épais. +8 défense, +10 PV.", "Corps", "Tous", "Grade", 550, "corps", 0,8,0,0,10,0, 0,0, 150, 5, 1),
    ("Armure d'écailles", "Solide et souple. +14 défense, +20 PV.", "Corps", "Tous", "Grand Grade", 1500, "corps", 0,14,0,0,20,0, 0,0, 200, 12, 1),

    # ===== NAVIRES (communs) =====
    ("Barque de pêcheur", "Un frêle esquif pour débuter.", "Navire", "Tous", "Commun", 250, "navire", 0,0,2,0,0,0, 0,0, 100, -1, 1),
    ("Sloop rapide", "Un petit voilier agile. +5 vitesse.", "Navire", "Tous", "Grade", 900, "navire", 0,0,5,0,0,0, 0,0, 150, 5, 1),
    ("Caravelle robuste", "Un navire fiable. +6 défense, +4 vitesse.", "Navire", "Tous", "Grand Grade", 2500, "navire", 0,6,4,0,0,0, 0,0, 250, 12, 1),
    ("Galion de guerre", "Un mastodonte des mers. +12 défense, +6 vitesse, +40 PV.", "Navire", "Tous", "Suprême", 8000, "navire", 0,12,6,0,40,0, 0,0, 400, 25, 1),

    # ===== ARMES PIRATES =====
    ("Sabre d'abordage rouillé", "L'arme du pirate débutant. +5 force.", "Arme", "Pirate", "Commun", 100, "arme_principale", 5,0,0,0,0,0, 0,0, 100, -1, 1),
    ("Cimeterre corsaire", "Une lame courbe redoutable. +10 force.", "Arme", "Pirate", "Aiguisé", 350, "arme_principale", 10,0,0,0,0,0, 0,0, 120, -1, 1),
    ("Lame écarlate", "Forgée dans le feu. +18 force, +3 vitesse.", "Arme", "Pirate", "Grade", 900, "arme_principale", 18,0,3,0,0,0, 0,0, 150, 8, 1),
    ("Grand sabre des mers", "Une arme de capitaine. +28 force, +5 vitesse.", "Arme", "Pirate", "Grand Grade", 2800, "arme_principale", 28,0,5,0,0,0, 0,0, 220, 15, 1),
    ("Lame noire du corsaire", "Une lame légendaire noircie au combat. +45 force, +8 vitesse.", "Arme", "Pirate", "Suprême", 9500, "arme_principale", 45,0,8,0,0,0, 0,0, 350, 28, 1),
    ("Pistolet à silex", "Arme à feu de poing. +8 force.", "Arme", "Pirate", "Aiguisé", 400, "arme_secondaire", 8,0,0,2,0,0, 0,0, 100, -1, 1),

    # ===== ARMES MARINE =====
    ("Sabre réglementaire", "L'arme standard du soldat. +5 force, +2 défense.", "Arme", "Marine", "Commun", 100, "arme_principale", 5,2,0,0,0,0, 0,0, 110, -1, 1),
    ("Lame de justice", "Forgée pour l'ordre. +11 force, +4 défense.", "Arme", "Marine", "Aiguisé", 380, "arme_principale", 11,4,0,0,0,0, 0,0, 130, -1, 1),
    ("Sabre d'officier", "Réservé aux gradés. +19 force, +6 défense.", "Arme", "Marine", "Grade", 950, "arme_principale", 19,6,0,0,0,0, 0,0, 160, 8, 1),
    ("Lame du quartier-général", "Arme d'élite marine. +30 force, +10 défense.", "Arme", "Marine", "Grand Grade", 3000, "arme_principale", 30,10,0,0,0,0, 0,0, 240, 15, 1),
    ("Lame noire de l'amiral", "Symbole de la justice absolue. +48 force, +14 défense.", "Arme", "Marine", "Suprême", 10000, "arme_principale", 48,14,0,0,0,0, 0,0, 380, 28, 1),
    ("Fusil réglementaire", "Arme à distance de la Marine. +10 force.", "Arme", "Marine", "Aiguisé", 420, "arme_secondaire", 10,0,0,0,0,0, 0,0, 100, -1, 1),
    ("Armure lourde marine", "Plaque d'acier réglementaire. +18 défense, +25 PV.", "Corps", "Marine", "Grand Grade", 1800, "corps", 0,18,0,0,25,0, 0,0, 250, 12, 1),

    # ===== ARMES RÉVOLUTIONNAIRES =====
    ("Dague furtive", "Silencieuse et rapide. +6 force, +4 agilité.", "Arme", "Révolutionnaire", "Commun", 110, "arme_principale", 6,0,0,4,0,0, 0,0, 100, -1, 1),
    ("Lames jumelles", "Deux lames légères. +12 force, +6 agilité.", "Arme", "Révolutionnaire", "Aiguisé", 390, "arme_principale", 12,0,0,6,0,0, 0,0, 120, -1, 1),
    ("Griffes de l'ombre", "Pour frapper vite et disparaître. +20 force, +8 agilité.", "Arme", "Révolutionnaire", "Grade", 980, "arme_principale", 20,0,4,8,0,0, 0,0, 150, 8, 1),
    ("Faux de la révolte", "Arme emblématique des insurgés. +31 force, +10 agilité.", "Arme", "Révolutionnaire", "Grand Grade", 3100, "arme_principale", 31,0,6,10,0,0, 0,0, 230, 15, 1),
    ("Lame noire du libérateur", "Née dans les flammes de la révolte. +46 force, +14 agilité.", "Arme", "Révolutionnaire", "Suprême", 9800, "arme_principale", 46,0,8,14,0,0, 0,0, 370, 28, 1),
    ("Cape d'infiltration", "Se fondre dans l'ombre. +6 agilité, +4 chance.", "Corps", "Révolutionnaire", "Grade", 600, "corps", 0,3,0,6,0,4, 0,0, 130, 5, 1),

    # ===== INGRÉDIENTS (communs, base des métiers) =====
    ("Poisson argenté", "Un petit poisson argenté, idéal pour une soupe simple.", "Ingrédient", "Tous", "Commun", 8, None, 0,0,0,0,0,0, 0,0, 1, -1, 1),
    ("Poisson tigre", "Un poisson rayé à la chair ferme, plus difficile à attraper.", "Ingrédient", "Tous", "Aiguisé", 25, None, 0,0,0,0,0,0, 0,0, 1, -1, 1),
    ("Anguille des courants", "Une anguille vive qui se faufile dans les courants marins.", "Ingrédient", "Tous", "Aiguisé", 20, None, 0,0,0,0,0,0, 0,0, 1, -1, 1),
    ("Étoile de mer scintillante", "Rare et précieuse, elle brille faiblement la nuit.", "Ingrédient", "Tous", "Grade", 60, None, 0,0,0,0,0,0, 0,0, 1, -1, 1),
    ("Viande de sanglier des mers", "Une viande goûteuse prisée des cuisiniers de bord.", "Ingrédient", "Tous", "Commun", 10, None, 0,0,0,0,0,0, 0,0, 1, -1, 1),
    ("Plume de faucon-tonnerre", "Une plume électrique arrachée à un rapace redouté.", "Ingrédient", "Tous", "Aiguisé", 22, None, 0,0,0,0,0,0, 0,0, 1, -1, 1),
    ("Peau de varan des dunes", "Résistante et rare, elle vient d'un lézard géant.", "Ingrédient", "Tous", "Grade", 55, None, 0,0,0,0,0,0, 0,0, 1, -1, 1),
    ("Baies sucrées", "De petites baies gorgées de sucre naturel.", "Ingrédient", "Tous", "Commun", 6, None, 0,0,0,0,0,0, 0,0, 1, -1, 1),
    ("Racine noueuse", "Une racine terreuse, base de nombreux plats simples.", "Ingrédient", "Tous", "Commun", 6, None, 0,0,0,0,0,0, 0,0, 1, -1, 1),
    ("Champignon des embruns", "Pousse uniquement près des côtes brumeuses.", "Ingrédient", "Tous", "Aiguisé", 18, None, 0,0,0,0,0,0, 0,0, 1, -1, 1),
    ("Fleur de corail", "Une fleur rarissime qui pousse sur le corail vivant.", "Ingrédient", "Tous", "Grade", 50, None, 0,0,0,0,0,0, 0,0, 1, -1, 1),
    ("Poisson légendaire des abysses", "Une prise rarissime venue des profondeurs, prisée des plus grands chefs.", "Ingrédient", "Tous", "Grand Grade", 150, None, 0,0,0,0,0,0, 0,0, 1, -1, 1),

    # ===== PLATS (uniquement via /cuisiner, jamais achetables — stock à 0) =====
    ("Soupe de fortune", "Une soupe chaude et réconfortante, préparée avec le peu qu'on a.", "Plat", "Tous", "Commun", 40, None, 0,0,0,0,0,0, 40,0, 1, 0, 1),
    ("Riz sauté du marin", "Un plat roboratif qui redonne de l'énergie avant une longue traversée.", "Plat", "Tous", "Commun", 45, None, 0,0,0,0,0,0, 0,50, 1, 0, 1),
    ("Ragoût de sanglier", "Un ragoût copieux qui tient au corps.", "Plat", "Tous", "Aiguisé", 90, None, 0,0,0,0,0,0, 80,30, 1, 0, 1),
    ("Poisson tigre grillé", "Grillé à la perfection, ce poisson redonne toute son énergie.", "Plat", "Tous", "Aiguisé", 100, None, 0,0,0,0,0,0, 100,0, 1, 0, 1),
    ("Tarte de la moisson", "Une tarte délicate aux fleurs de corail confites.", "Plat", "Tous", "Aiguisé", 70, None, 0,0,0,0,0,0, 60,0, 1, 0, 1),
    ("Festin du capitaine", "Un festin digne d'un capitaine de légende.", "Plat", "Tous", "Grand Grade", 250, None, 0,0,0,0,0,0, 200,100, 1, 0, 1),
]
