# Chaque ennemi : dict avec nom, mer, poids (fréquence relative), stats de combat, récompenses, durée de K.O.

ENNEMIS = [
    # East Blue (niveau 1+)
    {"nom": "un bandit de grand chemin", "mer": "East Blue", "poids": 45, "pv": 40, "force": 6, "defense": 3, "vitesse": 8,
     "berrys_min": 15, "berrys_max": 30, "xp": 20, "xpc": 8, "prime_gain": 5, "ko_minutes": 2, "boss": False},
    {"nom": "un pirate débutant", "mer": "East Blue", "poids": 35, "pv": 55, "force": 8, "defense": 4, "vitesse": 10,
     "berrys_min": 20, "berrys_max": 40, "xp": 25, "xpc": 10, "prime_gain": 8, "ko_minutes": 3, "boss": False},
    {"nom": "un marin ivre cherchant la bagarre", "mer": "East Blue", "poids": 20, "pv": 35, "force": 5, "defense": 2, "vitesse": 6,
     "berrys_min": 10, "berrys_max": 25, "xp": 15, "xpc": 6, "prime_gain": 3, "ko_minutes": 2, "boss": False},

    # South Blue (niveau 15+)
    {"nom": "un pirate aguerri", "mer": "South Blue", "poids": 40, "pv": 120, "force": 16, "defense": 9, "vitesse": 16,
     "berrys_min": 50, "berrys_max": 90, "xp": 45, "xpc": 18, "prime_gain": 20, "ko_minutes": 5, "boss": False},
    {"nom": "un déserteur de la Marine", "mer": "South Blue", "poids": 35, "pv": 100, "force": 14, "defense": 10, "vitesse": 14,
     "berrys_min": 45, "berrys_max": 85, "xp": 40, "xpc": 16, "prime_gain": 18, "ko_minutes": 5, "boss": False},
    {"nom": "un chasseur de primes solitaire", "mer": "South Blue", "poids": 25, "pv": 140, "force": 18, "defense": 8, "vitesse": 20,
     "berrys_min": 60, "berrys_max": 100, "xp": 50, "xpc": 20, "prime_gain": 25, "ko_minutes": 6, "boss": False},

    # West Blue (niveau 15+)
    {"nom": "un pirate aguerri", "mer": "West Blue", "poids": 40, "pv": 120, "force": 16, "defense": 9, "vitesse": 16,
     "berrys_min": 50, "berrys_max": 90, "xp": 45, "xpc": 18, "prime_gain": 20, "ko_minutes": 5, "boss": False},
    {"nom": "un déserteur de la Marine", "mer": "West Blue", "poids": 35, "pv": 100, "force": 14, "defense": 10, "vitesse": 14,
     "berrys_min": 45, "berrys_max": 85, "xp": 40, "xpc": 16, "prime_gain": 18, "ko_minutes": 5, "boss": False},
    {"nom": "un chasseur de primes solitaire", "mer": "West Blue", "poids": 25, "pv": 140, "force": 18, "defense": 8, "vitesse": 20,
     "berrys_min": 60, "berrys_max": 100, "xp": 50, "xpc": 20, "prime_gain": 25, "ko_minutes": 6, "boss": False},

    # North Blue (niveau 15+)
    {"nom": "un pirate aguerri", "mer": "North Blue", "poids": 40, "pv": 120, "force": 16, "defense": 9, "vitesse": 16,
     "berrys_min": 50, "berrys_max": 90, "xp": 45, "xpc": 18, "prime_gain": 20, "ko_minutes": 5, "boss": False},
    {"nom": "un déserteur de la Marine", "mer": "North Blue", "poids": 35, "pv": 100, "force": 14, "defense": 10, "vitesse": 14,
     "berrys_min": 45, "berrys_max": 85, "xp": 40, "xpc": 16, "prime_gain": 18, "ko_minutes": 5, "boss": False},
    {"nom": "un chasseur de primes solitaire", "mer": "North Blue", "poids": 25, "pv": 140, "force": 18, "defense": 8, "vitesse": 20,
     "berrys_min": 60, "berrys_max": 100, "xp": 50, "xpc": 20, "prime_gain": 25, "ko_minutes": 6, "boss": False},

    # Grand Line (niveau 35+)
    {"nom": "un capitaine pirate redouté", "mer": "Grand Line", "poids": 40, "pv": 260, "force": 30, "defense": 18, "vitesse": 26,
     "berrys_min": 150, "berrys_max": 250, "xp": 90, "xpc": 35, "prime_gain": 60, "ko_minutes": 10, "boss": False},
    {"nom": "un officier de Marine gradé", "mer": "Grand Line", "poids": 35, "pv": 240, "force": 28, "defense": 20, "vitesse": 24,
     "berrys_min": 140, "berrys_max": 230, "xp": 85, "xpc": 33, "prime_gain": 55, "ko_minutes": 10, "boss": False},
    {"nom": "un roi des mers juvénile", "mer": "Grand Line", "poids": 25, "pv": 320, "force": 34, "defense": 16, "vitesse": 30,
     "berrys_min": 180, "berrys_max": 280, "xp": 110, "xpc": 42, "prime_gain": 70, "ko_minutes": 12, "boss": False},

    # Nouveau Monde (niveau 70+)
    {"nom": "un seigneur pirate légendaire", "mer": "Nouveau Monde", "poids": 45, "pv": 500, "force": 50, "defense": 30, "vitesse": 38,
     "berrys_min": 400, "berrys_max": 700, "xp": 200, "xpc": 80, "prime_gain": 150, "ko_minutes": 20, "boss": False},
    {"nom": "un amiral en second", "mer": "Nouveau Monde", "poids": 40, "pv": 480, "force": 48, "defense": 34, "vitesse": 36,
     "berrys_min": 380, "berrys_max": 680, "xp": 190, "xpc": 76, "prime_gain": 140, "ko_minutes": 20, "boss": False},
    {"nom": "un roi des mers ancestral", "mer": "Nouveau Monde", "poids": 15, "pv": 700, "force": 60, "defense": 38, "vitesse": 45,
     "berrys_min": 600, "berrys_max": 1000, "xp": 300, "xpc": 120, "prime_gain": 250, "ko_minutes": 30, "boss": True},
]
