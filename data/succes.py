# Chaque famille : (nom_affiche, check_type, [(seuil, recompense_berrys, titre), ...])
# Pour ajouter un palier plus tard : ajoute simplement un tuple à la liste concernee.

FAMILLES = {
    "niveau": ("📈 Niveau", "niveau_min", [
        (5, 50, "Premiers pas"),
        (10, 80, "Aventurier confirmé"),
        (20, 130, "Vétéran des mers"),
        (35, 200, "Héros légendaire"),
        (50, 320, "Icône du Nouveau Monde"),
        (70, 500, "Empereur en devenir"),
    ]),
    "richesse": ("💰 Richesse", "total_min", [
        (200, 40, "Petit épargnant"),
        (600, 90, "Marchand prometteur"),
        (1500, 180, "Négociant aguerri"),
        (4000, 350, "Grand richard"),
        (10000, 700, "Magnat des mers"),
        (25000, 1400, "Fortune légendaire"),
    ]),
    "prime": ("☠️ Prime", "prime_min", [
        (100, 60, "Chasseur de primes"),
        (300, 120, "Voyou recherché"),
        (800, 220, "Terreur locale"),
        (2000, 400, "Terreur des mers"),
        (5000, 750, "Menace mondiale"),
        (12000, 1400, "Légende à prime"),
    ]),
    "mers": ("🗺️ Mers explorées", "mers_visitees_min", [
        (1, 30, "Premier voyage"),
        (2, 60, "Explorateur régional"),
        (3, 100, "Globe-trotter"),
        (4, 150, "Sillonneur des Blues"),
        (5, 220, "Aux portes de la Grand Line"),
        (6, 320, "Maître du Nouveau Monde"),
    ]),
    "metier": ("🔧 Métier", "metier_xp_min", [
        (50, 40, "Apprenti prometteur"),
        (150, 90, "Artisan confirmé"),
        (400, 180, "Artisan accompli"),
        (800, 320, "Vétéran du métier"),
        (1500, 600, "Légende de la Guilde"),
    ]),
    "leadership": ("🧭 Commandement", "chef_organisation", [
        (None, 100, "Meneur né"),
    ]),
    "organisation": ("🏴‍☠️ Organisation", "org_prime_min", [
        (500, 150, "Petite bande qui monte"),
        (2000, 350, "Équipage redouté"),
        (6000, 700, "Puissance montante"),
        (15000, 1400, "Légende collective"),
    ]),
    "tournoi": ("🏆 Tournois", "tournois_gagnes_min", [
        (1, 200, "Champion du tournoi"),
        (3, 500, "Champion aguerri"),
        (7, 1000, "Légende du tournoi"),
    ]),
    "boss_mondial": ("👑 Boss mondiaux", "boss_vaincus_min", [
        (1, 250, "Terrasseur de titans"),
        (5, 700, "Chasseur de colosses"),
        (15, 1500, "Fléau des boss mondiaux"),
    ]),
    "notoriete": ("🌟 Notoriété", "notoriete_min", [
        (10, 50, "Un nom qui circule"),
        (30, 100, "Réputation grandissante"),
        (75, 200, "Connu sur les quatre mers"),
        (150, 400, "Figure respectée"),
        (300, 800, "Légende vivante"),
    ]),
    "reputation": ("🤝 Réputation", "reputation_max", [
        (20, 40, "Bien vu des siens"),
        (50, 90, "Pilier de sa faction"),
        (100, 180, "Voix qui compte"),
        (200, 350, "Figure de proue"),
    ]),
    "cartes": ("🃏 Collection de cartes", "cartes_uniques_min", [
        (10, 60, "Petit collectionneur"),
        (30, 150, "Collectionneur assidu"),
        (60, 300, "Collectionneur chevronné"),
        (100, 600, "Collection impressionnante"),
        (143, 1200, "Collection complète"),
    ]),
}
