# Textes variés pour éviter toute répétition dans les mini-jeux Marine

LIEUX_PATROUILLE = [
    "les quais du port principal",
    "la ruelle marchande derrière la caserne",
    "le môle nord, souvent désert la nuit",
    "les entrepôts sous contrôle militaire",
    "la place du marché, sous surveillance",
    "le sentier côtier menant au phare",
    "les abords du poste de garde avancé",
]

# (label, berrys_min, berrys_max, xp_gain, chance)
EVENEMENTS_PATROUILLE = [
    ("rien_signaler", 5, 15, 5, 35),
    ("contrebandier", 25, 50, 15, 20),
    ("secours_civil", 15, 30, 12, 20),
    ("pirate_fuite", 30, 60, 20, 15),
    ("fausse_alerte", 0, 0, 3, 10),
]

TEXTES_EVENEMENTS_PATROUILLE = {
    "rien_signaler": ["La ronde se déroule sans le moindre incident.", "Tout est calme, comme souvent à cette heure.", "Une patrouille de routine, sans surprise."],
    "contrebandier": ["Tu surprends un contrebandier en pleine transaction et confisques sa marchandise !", "Un trafic suspect est intercepté juste à temps !"],
    "secours_civil": ["Tu portes secours à un civil en détresse, reconnaissant de ton aide.", "Une commerçante te remercie chaleureusement pour ton intervention."],
    "pirate_fuite": ["Tu repères un pirate recherché qui tente de filer, et récupères une partie de sa cargaison abandonnée !", "Un fuyard laisse tomber sa bourse en détalant !"],
    "fausse_alerte": ["Une fausse alerte te fait perdre du temps, mais l'exercice reste utile.", "Rien de grave, juste un chat effrayé par l'orage."],
}

# (description, pv_min, pv_max, berrys_min, berrys_max)
NAVIRES_PIRATES_TRAQUES = [
    ("un brigantin pirate signalé au large", 250, 380, 200, 320),
    ("une frégate corsaire connue pour ses raids", 300, 430, 240, 360),
    ("un navire affilié à une bande recherchée depuis des semaines", 320, 460, 260, 400),
    ("un vaisseau isolé battant un pavillon inconnu", 220, 340, 180, 300),
]

SUSPECTS_INTERROGATOIRE = [
    "un marin ivre aux réponses évasives",
    "un commerçant nerveux qui évite ton regard",
    "un passager qui change son histoire à chaque question",
    "un vieux loup de mer qui en sait plus qu'il ne le dit",
    "un jeune mousse visiblement terrifié",
]

EXERCICES_INSPECTION = [
    "un parcours d'obstacles chronométré",
    "une démonstration de maniement d'arme",
    "un exercice de coordination en binôme",
    "une épreuve d'endurance sur le pont",
    "un test de rapidité de réaction",
]
