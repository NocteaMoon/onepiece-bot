import random
from database.db import get_pool

# (nom, emoji, poids_tirage, description)
METEOS = [
    ("Ciel dégagé", "☀️", 40, "Un temps calme et dégagé règne sur ces eaux."),
    ("Pluie fine", "🌧️", 20, "Une pluie légère tombe, mais les récoltes s'annoncent bonnes."),
    ("Vent favorable", "💨", 15, "Un vent porteur souffle dans la bonne direction, les voyages sont facilités."),
    ("Tempête", "⛈️", 15, "Le ciel s'assombrit dangereusement, la navigation devient risquée."),
    ("Brouillard épais", "🌫️", 10, "Une brume épaisse réduit la visibilité aux alentours."),
]

# Multiplicateurs appliqués selon la météo active
MODIFIERS = {
    "Ciel dégagé": {"endurance_voyage": 1.0, "bad_event": 1.0, "berrys_explorer": 1.0, "rien_explorer": 1.0},
    "Pluie fine": {"endurance_voyage": 1.0, "bad_event": 1.0, "berrys_explorer": 1.25, "rien_explorer": 1.0},
    "Vent favorable": {"endurance_voyage": 0.8, "bad_event": 1.0, "berrys_explorer": 1.0, "rien_explorer": 1.0},
    "Tempête": {"endurance_voyage": 1.0, "bad_event": 1.6, "berrys_explorer": 1.0, "rien_explorer": 1.0},
    "Brouillard épais": {"endurance_voyage": 1.0, "bad_event": 1.0, "berrys_explorer": 1.0, "rien_explorer": 1.4},
}


async def get_current_weather(guild_id: int) -> str:
    pool = get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow("SELECT meteo FROM guild_weather WHERE guild_id=$1", guild_id)
    if not row:
        return await rotate_weather(guild_id)
    return row["meteo"]


async def rotate_weather(guild_id: int) -> str:
    nom = random.choices([m[0] for m in METEOS], weights=[m[2] for m in METEOS], k=1)[0]
    pool = get_pool()
    async with pool.acquire() as conn:
        await conn.execute("""
            INSERT INTO guild_weather (guild_id, meteo, changee_le) VALUES ($1, $2, NOW())
            ON CONFLICT (guild_id) DO UPDATE SET meteo = $2, changee_le = NOW()
        """, guild_id, nom)
    return nom


def get_meteo_info(nom: str):
    for n, emoji, poids, desc in METEOS:
        if n == nom:
            return emoji, desc
    return "☀️", ""


def get_modifiers(nom: str) -> dict:
    return MODIFIERS.get(nom, MODIFIERS["Ciel dégagé"])
