import random
from database.db import get_pool

PLAFOND_MAITRISE = 20
CHANCE_PROGRES_PAR_ATTAQUE = 0.08
BONUS_PAR_POINT = 1

COLONNES = {
    "epee": "maitrise_epee",
    "poings": "maitrise_poings",
    "lance": "maitrise_lance",
    "pistolet": "maitrise_pistolet",
    "fusil": "maitrise_fusil",
    "arc": "maitrise_arc",
}

LABELS = {
    "epee": "Épée", "poings": "Poings", "lance": "Lance",
    "pistolet": "Pistolet", "fusil": "Fusil", "arc": "Arc",
}


async def progresser_maitrise(guild_id: int, user_id: int, type_arme: str):
    """Appelé à chaque attaque en combat. Retourne le nouveau palier si progrès, sinon None."""
    if not type_arme or type_arme not in COLONNES:
        return None
    colonne = COLONNES[type_arme]
    pool = get_pool()
    async with pool.acquire() as conn:
        current = await conn.fetchval(f"SELECT {colonne} FROM players WHERE guild_id=$1 AND user_id=$2", guild_id, user_id)
        if current is None or current >= PLAFOND_MAITRISE:
            return None
        if random.random() < CHANCE_PROGRES_PAR_ATTAQUE:
            await conn.execute(f"UPDATE players SET {colonne} = {colonne} + 1 WHERE guild_id=$1 AND user_id=$2", guild_id, user_id)
            return current + 1
    return None


def get_maitrise_bonus(player, type_arme_equipee):
    """Bonus de force si l'arme équipée correspond au type maîtrisé."""
    if not type_arme_equipee or type_arme_equipee not in COLONNES:
        return 0
    colonne = COLONNES[type_arme_equipee]
    valeur = player[colonne] or 0
    return valeur * BONUS_PAR_POINT
