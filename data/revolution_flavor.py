# Contenu varié pour les mini-jeux Révolutionnaires

# (question, [4 choix], index_bonne_reponse)
QUIZ_QUESTIONS = [
    ("Combien de mers composent le monde connu ?", ["4", "5", "6", "7"], 2),
    ("Quel est le rang le plus élevé chez les Révolutionnaires ?", ["Commandant", "Agent", "Meneur", "Recrue"], 2),
    ("Quel est le rang le plus élevé dans une Guilde des métiers ?", ["Expert", "Compagnon", "Membre", "Maître de Guilde"], 3),
    ("Quelle catégorie de Fruit du Démon est la plus rare ?", ["Singulier", "Élémentaire", "Mutation", "Aucune, toutes égales"], 2),
    ("Combien existe-t-il de métiers pour les Civils ?", ["5", "6", "7", "8"], 2),
    ("Quels jours les échanges de cartes sont-ils autorisés ?", ["Lundi et vendredi", "Mardi et dimanche", "Tous les jours", "Samedi uniquement"], 1),
    ("Quelle organisation utilise le grade « Amiral » ?", ["Pirates", "Marine", "Révolutionnaires", "Civils"], 1),
    ("Combien de catégories de cartes à collectionner existe-t-il ?", ["4", "5", "6", "8"], 2),
    ("Quel est le nom du Haki le plus rare de tous ?", ["Armement", "Observation", "des Rois", "des Anciens"], 2),
    ("À partir de quel niveau peut-on explorer le Nouveau Monde ?", ["35", "50", "70", "100"], 2),
    ("Où achète-t-on un Fruit du Démon contre de l'argent ?", ["Au marché noir", "Chez le Forgeron", "À la Guilde", "Nulle part, jamais"], 0),
    ("Quel métier permet de forger de nouvelles armes ?", ["Cuisinier", "Forgeron", "Médecin", "Musicien"], 1),
]

LIEUX_INFILTRATION = [
    "un entrepôt sous surveillance légère",
    "les archives poussiéreuses d'un bâtiment officiel",
    "une réserve gardée par un unique factionnaire somnolent",
    "le sous-sol d'une bâtisse abandonnée",
    "un poste de garde temporairement déserté",
    "une aile isolée d'une résidence bourgeoise",
]

# (description, pv_min, pv_max, berrys_min, berrys_max)
CIBLES_SABOTAGE = [
    ("un dépôt de ravitaillement d'une garnison locale", 220, 340, 180, 300),
    ("une ligne de communication reliée à un poste de commandement", 250, 380, 200, 340),
    ("un entrepôt appartenant à la Compagnie des Cent Voiles", 280, 420, 240, 380),
    ("un système de surveillance récemment installé", 200, 320, 160, 280),
]

MOTS_CODE_SECRET = [
    "LIBERTE", "TEMPETE", "OMBRE", "SECRET", "PHARE", "TRESOR",
    "PACTE", "REVOLTE", "SILENCE", "COMPLOT", "RESEAU", "EVASION",
]

NPCS_RECRUTEMENT = [
    "un docker désabusé par son quotidien",
    "une commerçante fatiguée des taxes excessives",
    "un ancien soldat en rupture avec sa hiérarchie",
    "un artisan à qui on a confisqué son atelier",
    "un jeune marin en quête de sens",
    "une informatrice discrète mais méfiante",
]
