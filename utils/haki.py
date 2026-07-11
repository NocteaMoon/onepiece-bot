import random
import datetime
from database.db import get_pool

COUT_ENDURANCE = 15
COOLDOWN_MINUTES = 30
CHANCE_PROGRES = 0.35
PLAFOND_HAKI = 10

EVEIL_ROIS_CHANCE_PAR_VICTOIRE = 0.015

BONUS_PAR_POINT_ARMEMENT = 2
BONUS_PAR_POINT_OBSERVATION = 2
BONUS_ROIS = 5

_last_entrainement = {}


def is_on_cooldown(guild_id: int, user_id: int):
    key = (guild_id, user_id)
    now = datetime.datetime.utcnow()
    last = _last_entrainement.get(key)
    if last:
        elapsed = (now - last).total_seconds() / 60
        if elapsed < COOLDOWN_MINUTES:
            return int(COOLDOWN_MINUTES - elapsed)
    return None


async def entrainer_haki(guild_id: int, user_id: int, type_haki: str) -> bool:
    """type_haki: 'armement' ou 'observation'. Retourne True si progrès, False sinon."""
    key = (guild_id, user_id)
    _last_entrainement[key] = datetime.datetime.utcnow()
    colonne = f"haki_{type_haki}"

    pool = get_pool()
    async with pool.acquire() as conn:
        current = await conn.fetchval(f"SELECT {colonne} FROM players WHERE guild_id=$1 AND user_id=$2", guild_id, user_id)
        progres = False
        if current < PLAFOND_HAKI and random.random() < CHANCE_PROGRES:
            await conn.execute(f"UPDATE players SET {colonne} = {colonne} + 1 WHERE guild_id=$1 AND user_id=$2", guild_id, user_id)
            progres = True
    return progres


async def check_eveil_rois(guild_id: int, user_id: int) -> bool:
    pool = get_pool()
    async with pool.acquire() as conn:
        current = await conn.fetchval("SELECT haki_rois FROM players WHERE guild_id=$1 AND user_id=$2", guild_id, user_id)
        if current and current > 0:
            return False
        if random.random() < EVEIL_ROIS_CHANCE_PAR_VICTOIRE:
            await conn.execute("UPDATE players SET haki_rois = 1 WHERE guild_id=$1 AND user_id=$2", guild_id, user_id)
            return True
    return False


def get_haki_bonus(player):
    bonus = {"force": 0, "defense": 0, "vitesse": 0, "agilite": 0}
    bonus["force"] += player["haki_armement"] * BONUS_PAR_POINT_ARMEMENT
    bonus["agilite"] += player["haki_observation"] * BONUS_PAR_POINT_OBSERVATION
    if player["haki_rois"] and player["haki_rois"] > 0:
        bonus["force"] += BONUS_ROIS
        bonus["defense"] += BONUS_ROIS
        bonus["vitesse"] += BONUS_ROIS
        bonus["agilite"] += BONUS_ROIS
    return bonus
