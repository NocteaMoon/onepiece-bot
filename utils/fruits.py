import random
from database.db import get_pool
from data.fruits import FRUITS

EVEIL_CHANCE_PAR_VICTOIRE = 0.03  # 3% de chance à chaque victoire, si fruit non éveillé
BONUS_EVEIL_MULTIPLICATEUR = 1.5


def get_fruit(code):
    for f in FRUITS:
        if f[0] == code:
            return f
    return None


def get_fruit_by_nom(nom):
    for f in FRUITS:
        if f[1] == nom:
            return f
    return None


async def get_fruits_possedes(guild_id: int):
    pool = get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch("SELECT fruit FROM players WHERE guild_id=$1 AND fruit IS NOT NULL", guild_id)
    return {r["fruit"] for r in rows}


async def get_fruits_disponibles(guild_id: int):
    possedes = await get_fruits_possedes(guild_id)
    return [f for f in FRUITS if f[1] not in possedes]


async def manger_fruit(guild_id: int, user_id: int, code: str) -> bool:
    fruit = get_fruit(code)
    if not fruit:
        return False
    possedes = await get_fruits_possedes(guild_id)
    if fruit[1] in possedes:
        return False
    pool = get_pool()
    async with pool.acquire() as conn:
        await conn.execute(
            "UPDATE players SET fruit = $3, fruit_eveil = FALSE WHERE guild_id=$1 AND user_id=$2",
            guild_id, user_id, fruit[1]
        )
    return True


async def check_eveil(guild_id: int, user_id: int) -> bool:
    """Appelé après une victoire. Retourne True si l'éveil vient de se déclencher."""
    pool = get_pool()
    async with pool.acquire() as conn:
        player = await conn.fetchrow("SELECT fruit, fruit_eveil FROM players WHERE guild_id=$1 AND user_id=$2", guild_id, user_id)
        if not player or not player["fruit"] or player["fruit_eveil"]:
            return False
        if random.random() < EVEIL_CHANCE_PAR_VICTOIRE:
            await conn.execute("UPDATE players SET fruit_eveil = TRUE WHERE guild_id=$1 AND user_id=$2", guild_id, user_id)
            return True
    return False


def get_fruit_bonus(player):
    """Retourne les bonus de stats issus du fruit mangé (doublés partiellement si éveillé)."""
    if not player["fruit"]:
        return {"force": 0, "defense": 0, "vitesse": 0, "agilite": 0}
    fruit = get_fruit_by_nom(player["fruit"])
    if not fruit:
        return {"force": 0, "defense": 0, "vitesse": 0, "agilite": 0}
    bonus = dict(fruit[4])
    if player["fruit_eveil"]:
        bonus = {k: round(v * BONUS_EVEIL_MULTIPLICATEUR) for k, v in bonus.items()}
    return bonus
