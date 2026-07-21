# Textes variés pour éviter toute répétition dans les mini-jeux Pirates

LIEUX_CHASSE_PRIME = [
    "les quais animés du port",
    "une ruelle sombre à l'écart des regards",
    "le marché noir en bord de mer",
    "les docks désertés à la nuit tombée",
    "une taverne mal famée en périphérie",
    "les entrepôts abandonnés du vieux port",
    "une venelle qui sent encore la marée basse",
]

# (description, berrys_min, berrys_max, chance_de_succes)
CONVOIS_ABORDAGE = [
    ("un caboteur marchand chargé de vivres", 20, 45, 0.85),
    ("une caravelle de commerçants nerveux", 30, 60, 0.80),
    ("un baleinier isolé loin des routes commerciales", 25, 50, 0.85),
    ("un petit galion mal gardé", 40, 80, 0.75),
    ("une jonque chargée d'épices rares", 35, 70, 0.78),
    ("un navire postal en retard sur sa route", 15, 35, 0.90),
]

ROUNDS_BEUVERIE = [
    "Un tour de rhum offert par la maison fait le tour de la table...",
    "Un chant à tue-tête envahit soudain la salle...",
    "Quelqu'un lance un pari risqué sur qui tiendra le plus longtemps...",
    "Le patron ressort une bouteille poussiéreuse, réservée aux grandes occasions...",
    "Une nouvelle tournée arrive, personne n'ose refuser...",
    "Les tables tremblent sous les rires et les chopes renversées...",
]

# (description, pv_min, pv_max, berrys_min, berrys_max) — ancrés dans le lore déjà établi
GROS_CONVOIS_PILLAGE = [
    ("un galion marchand affilié à la Compagnie des Cent Voiles", 300, 450, 250, 400),
    ("une flotte de trois caboteurs solidement escortés", 280, 420, 220, 380),
    ("le vaisseau du trésor d'un noble en exil", 350, 500, 300, 450),
    ("un convoi mystérieux qu'on murmure lié à la Guilde des Ombres", 380, 550, 320, 500),
]
