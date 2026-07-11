# Catalogue d'objets par défaut, dans l'esprit One Piece (noms originaux, non copiés de l'œuvre).
# (nom, description, categorie, faction, rarete, prix, slot,
#  b_force, b_defense, b_vitesse, b_agilite, b_pv, b_chance,
#  soin_pv, soin_endurance, durabilite_max, stock, niveau_requis, type_arme)
# type_arme : "epee", "poings", "lance", "pistolet", "fusil", "arc", ou None si pas une arme

CATALOGUE = [
    # ===== CONSOMMABLES (communs à tous) =====
    ("Ration de bord", "Restaure un peu d'endurance.", "Consommable", "Tous", "Commun", 30, None, 0,0,0,0,0,0, 0, 40, 1, -1, 1, None),
    ("Repas de taverne", "Un bon repas chaud qui redonne des forces.", "Consommable", "Tous", "Commun", 60, None, 0,0,0,0,0,0, 30, 60, 1, -1, 1, None),
    ("Potion de soin", "Restaure 50 PV instantanément.", "Consommable", "Tous", "Aiguisé", 120, None, 0,0,0,0,0,0, 50, 0, 1, -1, 1, None),
    ("Grand remède", "Restaure 120 PV instantanément.", "Consommable", "Tous", "Grade", 300, None, 0,0,0,0,0,0, 120, 0, 1, 20, 5, None),
    ("Élixir du médecin", "Restaure tous les PV et l'endurance.", "Consommable", "Tous", "Grand Grade", 800, None, 0,0,0,0,0,0, 9999, 9999, 1, 20, 10, None),

    # ===== ACCESSOIRES (communs) =====
    ("Bandana usé", "Un simple bandana. +2 agilité.", "Accessoire", "Tous", "Commun", 80, "accessoire", 0,0,0,2,0,0, 0,0, 100, -1, 1, None),
    ("Longue-vue", "Améliore la perception. +3 chance.", "Accessoire", "Tous", "Aiguisé", 200, "accessoire", 0,0,0,0,0,3, 0,0, 100, -1, 1, None),
    ("Amulette de jade", "Une amulette porte-bonheur. +5 chance.", "Accessoire", "Tous", "Grade", 500, "accessoire", 0,0,0,0,0,5, 0,0, 100, 5, 1, None),
    ("Ceinture lestée", "Entraînement au poids. +4 force.", "Accessoire", "Tous", "Grade", 450, "accessoire", 4,0,0,0,0,0, 0,0, 100, 5, 1, None),
    ("Boussole enchantée", "Ne perd jamais le nord. +6 chance, +2 vitesse.", "Accessoire", "Tous", "Grand Grade", 1200, "accessoire", 0,0,2,0,0,6, 0,0, 100, 10, 1, None),

    # ===== ARMURES / TÊTE (communs) =====
    ("Foulard de matelot", "Protection minime. +2 défense.", "Tête", "Tous", "Commun", 70, "tete", 0,2,0,0,0,0, 0,0, 100, -1, 1, None),
    ("Casque de cuir", "Un casque simple. +5 défense.", "Tête", "Tous", "Aiguisé", 180, "tete", 0,5,0,0,0,0, 0,0, 120, -1, 1, None),
    ("Manteau renforcé", "Un manteau épais. +8 défense, +10 PV.", "Corps", "Tous", "Grade", 550, "corps", 0,8,0,0,10,0, 0,0, 150, 5, 1, None),
    ("Armure d'écailles", "Solide et souple. +14 défense, +20 PV.", "Corps", "Tous", "Grand Grade", 1500, "corps", 0,14,0,0,20,0, 0,0, 200, 12, 1, None),

    # ===== NAVIRES (communs, achetables) =====
    ("Barque de pêcheur", "Un frêle esquif pour débuter.", "Navire", "Tous", "Commun", 250, "navire", 0,0,2,0,0,0, 0,0, 100, -1, 1, None),
    ("Sloop rapide", "Un petit voilier agile. +5 vitesse.", "Navire", "Tous", "Grade", 900, "navire", 0,0,5,0,0,0, 0,0, 150, 5, 1, None),
    ("Caravelle robuste", "Un navire fiable. +6 défense, +4 vitesse.", "Navire", "Tous", "Grand Grade", 2500, "navire", 0,6,4,0,0,0, 0,0, 250, 12, 1, None),
    ("Galion de guerre", "Un mastodonte des mers. +12 défense, +6 vitesse, +40 PV.", "Navire", "Tous", "Suprême", 8000, "navire", 0,12,6,0,40,0, 0,0, 400, 25, 1, None),

    # ===== ARMES POLYVALENTES (Tous, comblent Arc/Poings/Lance) =====
    ("Gants de combat renforcés", "Des gants épais renforcés de cuir bouilli. +5 force.", "Arme", "Tous", "Commun", 85, "arme_principale", 5,0,0,0,0,0, 0,0, 100, -1, 1, "poings"),
    ("Lance de fortune", "Une lance simple, taillée dans un bois solide. +5 force, +1 défense.", "Arme", "Tous", "Commun", 95, "arme_principale", 5,1,0,0,0,0, 0,0, 110, -1, 1, "lance"),
    ("Arc court de chasse", "Un arc léger, facile à manier. +5 force.", "Arme", "Tous", "Commun", 90, "arme_principale", 5,0,0,0,0,0, 0,0, 100, -1, 1, "arc"),
    ("Arc long renforcé", "Une portée redoutable entre des mains entraînées. +11 force, +2 vitesse.", "Arme", "Tous", "Aiguisé", 320, "arme_principale", 11,0,2,0,0,0, 0,0, 130, -1, 1, "arc"),

    # ===== ARMES PIRATES =====
    ("Sabre d'abordage rouillé", "L'arme du pirate débutant. +5 force.", "Arme", "Pirate", "Commun", 100, "arme_principale", 5,0,0,0,0,0, 0,0, 100, -1, 1, "epee"),
    ("Cimeterre corsaire", "Une lame courbe redoutable. +10 force.", "Arme", "Pirate", "Aiguisé", 350, "arme_principale", 10,0,0,0,0,0, 0,0, 120, -1, 1, "epee"),
    ("Lame écarlate", "Forgée dans le feu. +18 force, +3 vitesse.", "Arme", "Pirate", "Grade", 900, "arme_principale", 18,0,3,0,0,0, 0,0, 150, 8, 1, "epee"),
    ("Grand sabre des mers", "Une arme de capitaine. +28 force, +5 vitesse.", "Arme", "Pirate", "Grand Grade", 2800, "arme_principale", 28,0,5,0,0,0, 0,0, 220, 15, 1, "epee"),
    ("Lame noire du corsaire", "Une lame légendaire noircie au combat. +45 force, +8 vitesse.", "Arme", "Pirate", "Suprême", 9500, "arme_principale", 45,0,8,0,0,0, 0,0, 350, 28, 1, "epee"),
    ("Pistolet à silex", "Arme à feu de poing. +8 force.", "Arme", "Pirate", "Aiguisé", 400, "arme_secondaire", 8,0,0,2,0,0, 0,0, 100, -1, 1, "pistolet"),

    # ===== ARMES MARINE =====
    ("Sabre réglementaire", "L'arme standard du soldat. +5 force, +2 défense.", "Arme", "Marine", "Commun", 100, "arme_principale", 5,2,0,0,0,0, 0,0, 110, -1, 1, "epee"),
    ("Lame de justice", "Forgée pour l'ordre. +11 force, +4 défense.", "Arme", "Marine", "Aiguisé", 380, "arme_principale", 11,4,0,0,0,0, 0,0, 130, -1, 1, "epee"),
    ("Sabre d'officier", "Réservé aux gradés. +19 force, +6 défense.", "Arme", "Marine", "Grade", 950, "arme_principale", 19,6,0,0,0,0, 0,0, 160, 8, 1, "epee"),
    ("Lame du quartier-général", "Arme d'élite marine. +30 force, +10 défense.", "Arme", "Marine", "Grand Grade", 3000, "arme_principale", 30,10,0,0,0,0, 0,0, 240, 15, 1, "epee"),
    ("Lame noire de l'amiral", "Symbole de la justice absolue. +48 force, +14 défense.", "Arme", "Marine", "Suprême", 10000, "arme_principale", 48,14,0,0,0,0, 0,0, 380, 28, 1, "epee"),
    ("Fusil réglementaire", "Arme à distance de la Marine. +10 force.", "Arme", "Marine", "Aiguisé", 420, "arme_secondaire", 10,0,0,0,0,0, 0,0, 100, -1, 1, "fusil"),
    ("Armure lourde marine", "Plaque d'acier réglementaire. +18 défense, +25 PV.", "Corps", "Marine", "Grand Grade", 1800, "corps", 0,18,0,0,25,0, 0,0, 250, 12, 1, None),

    # ===== ARMES RÉVOLUTIONNAIRES =====
    ("Dague furtive", "Silencieuse et rapide. +6 force, +4 agilité.", "Arme", "Révolutionnaire", "Commun", 110, "arme_principale", 6,0,0,4,0,0, 0,0, 100, -1, 1, "epee"),
    ("Lames jumelles", "Deux lames légères. +12 force, +6 agilité.", "Arme", "Révolutionnaire", "Aiguisé", 390, "arme_principale", 12,0,0,6,0,0, 0,0, 120, -1, 1, "epee"),
    ("Griffes de l'ombre", "Pour frapper vite et disparaître. +20 force, +8 agilité.", "Arme", "Révolutionnaire", "Grade", 980, "arme_principale", 20,0,4,8,0,0, 0,0, 150, 8, 1, "poings"),
    ("Faux de la révolte", "Arme emblématique des insurgés. +31 force, +10 agilité.", "Arme", "Révolutionnaire", "Grand Grade", 3100, "arme_principale", 31,0,6,10,0,0, 0,0, 230, 15, 1, "lance"),
    ("Lame noire du libérateur", "Née dans les flammes de la révolte. +46 force, +14 agilité.", "Arme", "Révolutionnaire", "Suprême", 9800, "arme_principale", 46,0,8,14,0,0, 0,0, 370, 28, 1, "epee"),
    ("Cape d'infiltration", "Se fondre dans l'ombre. +6 agilité, +4 chance.", "Corps", "Révolutionnaire", "Grade", 600, "corps", 0,3,0,6,0,4, 0,0, 130, 5, 1, None),

    # ===== INGRÉDIENTS (communs, base des métiers) =====
    ("Poisson argenté", "Un petit poisson argenté, idéal pour une soupe simple.", "Ingrédient", "Tous", "Commun", 8, None, 0,0,0,0,0,0, 0,0, 1, -1, 1, None),
    ("Poisson tigre", "Un poisson rayé à la chair ferme, plus difficile à attraper.", "Ingrédient", "Tous", "Aiguisé", 25, None, 0,0,0,0,0,0, 0,0, 1, -1, 1, None),
    ("Anguille des courants", "Une anguille vive qui se faufile dans les courants marins.", "Ingrédient", "Tous", "Aiguisé", 20, None, 0,0,0,0,0,0, 0,0, 1, -1, 1, None),
    ("Étoile de mer scintillante", "Rare et précieuse, elle brille faiblement la nuit.", "Ingrédient", "Tous", "Grade", 60, None, 0,0,0,0,0,0, 0,0, 1, -1, 1, None),
    ("Viande de sanglier des mers", "Une viande goûteuse prisée des cuisiniers de bord.", "Ingrédient", "Tous", "Commun", 10, None, 0,0,0,0,0,0, 0,0, 1, -1, 1, None),
    ("Plume de faucon-tonnerre", "Une plume électrique arrachée à un rapace redouté.", "Ingrédient", "Tous", "Aiguisé", 22, None, 0,0,0,0,0,0, 0,0, 1, -1, 1, None),
    ("Peau de varan des dunes", "Résistante et rare, elle vient d'un lézard géant.", "Ingrédient", "Tous", "Grade", 55, None, 0,0,0,0,0,0, 0,0, 1, -1, 1, None),
    ("Baies sucrées", "De petites baies gorgées de sucre naturel.", "Ingrédient", "Tous", "Commun", 6, None, 0,0,0,0,0,0, 0,0, 1, -1, 1, None),
    ("Racine noueuse", "Une racine terreuse, base de nombreux plats simples.", "Ingrédient", "Tous", "Commun", 6, None, 0,0,0,0,0,0, 0,0, 1, -1, 1, None),
    ("Champignon des embruns", "Pousse uniquement près des côtes brumeuses.", "Ingrédient", "Tous", "Aiguisé", 18, None, 0,0,0,0,0,0, 0,0, 1, -1, 1, None),
    ("Fleur de corail", "Une fleur rarissime qui pousse sur le corail vivant.", "Ingrédient", "Tous", "Grade", 50, None, 0,0,0,0,0,0, 0,0, 1, -1, 1, None),

    # ===== MINERAIS (Forgeron) =====
    ("Minerai de fer", "Un minerai commun mais essentiel à toute forge.", "Ingrédient", "Tous", "Commun", 12, None, 0,0,0,0,0,0, 0,0, 1, -1, 1, None),
    ("Minerai d'étain", "Plus rare, utilisé pour les alliages robustes.", "Ingrédient", "Tous", "Aiguisé", 28, None, 0,0,0,0,0,0, 0,0, 1, -1, 1, None),
    ("Pépite d'acier bleu", "Un minerai précieux aux reflets bleutés, très recherché.", "Ingrédient", "Tous", "Grade", 65, None, 0,0,0,0,0,0, 0,0, 1, -1, 1, None),

    # ===== HERBES (Médecin) =====
    ("Herbe apaisante", "Une plante commune aux vertus calmantes.", "Ingrédient", "Tous", "Commun", 10, None, 0,0,0,0,0,0, 0,0, 1, -1, 1, None),
    ("Feuille de saule marin", "Pousse près des côtes, prisée des guérisseurs.", "Ingrédient", "Tous", "Aiguisé", 24, None, 0,0,0,0,0,0, 0,0, 1, -1, 1, None),
    ("Racine de vitalité", "Rare et puissante, elle redonne une énergie insoupçonnée.", "Ingrédient", "Tous", "Grade", 62, None, 0,0,0,0,0,0, 0,0, 1, -1, 1, None),

    # ===== MATÉRIAUX DE NAVIGATION (Navigateur) =====
    ("Parchemin usé", "Un vieux parchemin récupéré d'une épave.", "Ingrédient", "Tous", "Commun", 9, None, 0,0,0,0,0,0, 0,0, 1, -1, 1, None),
    ("Encre de seiche", "Une encre naturelle idéale pour tracer des cartes.", "Ingrédient", "Tous", "Aiguisé", 21, None, 0,0,0,0,0,0, 0,0, 1, -1, 1, None),
    ("Corail luminescent", "Rare corail qui brille dans l'obscurité, précieux pour les navigateurs.", "Ingrédient", "Tous", "Grade", 58, None, 0,0,0,0,0,0, 0,0, 1, -1, 1, None),

    # ===== BOIS ET CORDAGES (Charpentier) =====
    ("Planche de bois flotté", "Du bois solide échoué sur le rivage, parfait pour réparer un navire.", "Ingrédient", "Tous", "Commun", 11, None, 0,0,0,0,0,0, 0,0, 1, -1, 1, None),
    ("Corde tressée", "Une corde robuste tressée à la main.", "Ingrédient", "Tous", "Aiguisé", 26, None, 0,0,0,0,0,0, 0,0, 1, -1, 1, None),
    ("Voile renforcée", "Une toile épaisse et rare, résistante aux pires tempêtes.", "Ingrédient", "Tous", "Grade", 60, None, 0,0,0,0,0,0, 0,0, 1, -1, 1, None),

    # ===== INSTRUMENTS ET PARTITIONS (Musicien) =====
    ("Corde de luth", "Une corde de rechange pour instrument à cordes.", "Ingrédient", "Tous", "Commun", 10, None, 0,0,0,0,0,0, 0,0, 1, -1, 1, None),
    ("Roseau à vent", "Un roseau sec parfait pour tailler un instrument à vent.", "Ingrédient", "Tous", "Aiguisé", 23, None, 0,0,0,0,0,0, 0,0, 1, -1, 1, None),
    ("Parchemin de mélodie", "Un parchemin rare porteur d'une mélodie oubliée.", "Ingrédient", "Tous", "Grade", 57, None, 0,0,0,0,0,0, 0,0, 1, -1, 1, None),

    # ===== VESTIGES ANCIENS (Archéologue) =====
    ("Fragment de poterie ancienne", "Un morceau de poterie brisée, vestige d'une civilisation oubliée.", "Ingrédient", "Tous", "Commun", 12, None, 0,0,0,0,0,0, 0,0, 1, -1, 1, None),
    ("Éclat de pierre gravée", "Un éclat de pierre portant d'étranges gravures.", "Ingrédient", "Tous", "Aiguisé", 27, None, 0,0,0,0,0,0, 0,0, 1, -1, 1, None),
    ("Médaillon oublié", "Un médaillon ancien, rare et intact malgré les âges.", "Ingrédient", "Tous", "Grade", 63, None, 0,0,0,0,0,0, 0,0, 1, -1, 1, None),

    # ===== PLATS (uniquement via /cuisiner, jamais achetables — stock à 0) =====
    ("Soupe de fortune", "Une soupe chaude et réconfortante, préparée avec le peu qu'on a.", "Plat", "Tous", "Commun", 40, None, 0,0,0,0,0,0, 40,0, 1, 0, 1, None),
    ("Riz sauté du marin", "Un plat roboratif qui redonne de l'énergie avant une longue traversée.", "Plat", "Tous", "Commun", 45, None, 0,0,0,0,0,0, 0,50, 1, 0, 1, None),
    ("Ragoût de sanglier", "Un ragoût copieux qui tient au corps.", "Plat", "Tous", "Aiguisé", 90, None, 0,0,0,0,0,0, 80,30, 1, 0, 1, None),
    ("Poisson tigre grillé", "Grillé à la perfection, ce poisson redonne toute son énergie.", "Plat", "Tous", "Aiguisé", 100, None, 0,0,0,0,0,0, 100,0, 1, 0, 1, None),
    ("Tarte de la moisson", "Une tarte délicate aux fleurs de corail confites.", "Plat", "Tous", "Aiguisé", 70, None, 0,0,0,0,0,0, 60,0, 1, 0, 1, None),
    ("Festin du capitaine", "Un festin digne d'un capitaine de légende.", "Plat", "Tous", "Grand Grade", 250, None, 0,0,0,0,0,0, 200,100, 1, 0, 1, None),

    # ===== OBJETS FORGÉS (uniquement via /forgeron forger, jamais achetables) =====
    ("Dague artisanale", "Forgée à la main à partir de minerai de fer brut.", "Arme", "Tous", "Commun", 0, "arme_secondaire", 6,0,0,0,0,0, 0,0, 100, 0, 1, "epee"),
    ("Sabre forgé maison", "Un sabre solide né de la forge d'un Forgeron talentueux.", "Arme", "Tous", "Aiguisé", 0, "arme_principale", 14,0,0,0,0,0, 0,0, 140, 0, 1, "epee"),
    ("Armure d'acier bleu", "Une armure rare forgée dans l'acier bleu précieux.", "Corps", "Tous", "Grade", 0, "corps", 0,20,0,0,15,0, 0,0, 180, 0, 1, None),

    # ===== REMÈDES (uniquement via /medecin preparer, jamais achetables) =====
    ("Tisane apaisante", "Une tisane simple préparée à partir d'herbe apaisante.", "Plat", "Tous", "Commun", 0, None, 0,0,0,0,0,0, 40,0, 1, 0, 1, None),
    ("Baume de saule", "Un baume revigorant à base de feuille de saule marin.", "Plat", "Tous", "Aiguisé", 0, None, 0,0,0,0,0,0, 0,60, 1, 0, 1, None),
    ("Élixir de vitalité", "Un puissant élixir préparé par un Médecin expérimenté.", "Plat", "Tous", "Grade", 0, None, 0,0,0,0,0,0, 150,80, 1, 0, 1, None),

    # ===== CARTES (uniquement via /navigateur dresser_carte, jamais achetables) =====
    ("Carte des courants côtiers", "Une carte tracée à partir d'un vieux parchemin.", "Plat", "Tous", "Commun", 0, None, 0,0,0,0,0,0, 0,50, 1, 0, 1, None),
    ("Atlas des vents", "Un atlas détaillé, fruit d'un travail méticuleux.", "Plat", "Tous", "Aiguisé", 0, None, 0,0,0,0,0,0, 0,90, 1, 0, 1, None),
    ("Carte des abysses lumineuses", "Une carte rarissime dressée par un Navigateur chevronné.", "Plat", "Tous", "Grade", 0, None, 0,0,0,0,0,0, 40,140, 1, 0, 1, None),

    # ===== NAVIRES DU CHARPENTIER (uniquement via /charpentier construire, jamais achetables) =====
    ("Radeau renforcé", "Un radeau solidifié à la main, bien plus fiable qu'une simple planche.", "Navire", "Tous", "Commun", 0, "navire", 0,1,1,0,0,0, 0,0, 110, 0, 1, None),
    ("Voilier artisanal", "Un voilier façonné avec soin par un Charpentier talentueux.", "Navire", "Tous", "Aiguisé", 0, "navire", 0,3,3,0,10,0, 0,0, 160, 0, 1, None),
    ("Navire du charpentier légendaire", "Un chef-d'œuvre naval, fruit d'un savoir-faire rarissime.", "Navire", "Tous", "Grade", 0, "navire", 0,10,8,0,30,0, 0,0, 260, 0, 8, None),

    # ===== PARTITIONS (uniquement via /musicien composer, jamais achetables) =====
    ("Partition improvisée", "Une mélodie simple griffonnée sur le vif.", "Partition", "Tous", "Commun", 0, None, 0,0,0,0,0,0, 0,40, 1, 0, 1, None),
    ("Partition entraînante", "Un air entraînant qui redonne du cœur à l'ouvrage.", "Partition", "Tous", "Aiguisé", 0, None, 0,0,0,0,0,0, 30,50, 1, 0, 1, None),
    ("Symphonie de la mer", "Une œuvre rare composée par un Musicien chevronné.", "Partition", "Tous", "Grade", 0, None, 0,0,0,0,0,0, 90,110, 1, 0, 1, None),

    # ===== RELIQUES DÉCHIFFRÉES (uniquement via /archeologue dechiffrer, jamais achetables) =====
    ("Parchemin déchiffré", "Un vieux savoir enfin révélé après des heures d'étude.", "Relique", "Tous", "Commun", 0, None, 0,0,0,0,0,0, 0,45, 1, 0, 1, None),
    ("Amulette ancienne restaurée", "Une amulette d'un autre âge, restaurée avec soin.", "Relique", "Tous", "Aiguisé", 0, None, 0,0,0,0,0,0, 40,50, 1, 0, 1, None),
    ("Trésor des temps perdus", "Une relique rarissime, témoin d'une époque révolue.", "Relique", "Tous", "Grade", 0, None, 0,0,0,0,0,0, 100,120, 1, 0, 1, None),
]
