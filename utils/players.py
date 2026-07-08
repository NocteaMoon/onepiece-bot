import datetime
from database.db import get_pool

REGEN_PV_PAR_MINUTE = 5
REGEN_ENDURANCE_PAR_MINUTE = 10

async def get_player(guild_id: int, user_id: int):
    pool = get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT * FROM players WHERE guild_id = $1 AND user_id = $2",
            guild_id, user_id
        )
    if row:
        row = await apply_regen(row)
    return row

async def create_player(guild_id: int, user_id: int, faction: str):
    pool = get_pool()
    async with pool.acquire() as conn:
        await conn.execute(
            "INSERT INTO players (guild_id, user_id, faction) VALUES ($1, $2, $3) ON CONFLICT DO NOTHING",
            guild_id, user_id, faction
        )

async def apply_regen(row):
    now = datetime.datetime.utcnow()
    last = row["derniere_regen"]
    minutes = int((now - last).total_seconds() // 60)
    if minutes <= 0:
        return row
    if row["pv"] >= row["pv_max"] and row["endurance"] >= row["endurance_max"]:
        return row

    new_pv = min(row["pv_max"], row["pv"] + minutes * REGEN_PV_PAR_MINUTE)
    new_endurance = min(row["endurance_max"], row["endurance"] + minutes * REGEN_ENDURANCE_PAR_MINUTE)

    pool = get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow("""
            UPDATE players SET pv = $3, endurance = $4, derniere_regen = $5
            WHERE guild_id = $1 AND user_id = $2
            RETURNING *
        """, row["guild_id"], row["user_id"], new_pv, new_endurance, now)
    return row

def xp_requis(niveau: int) -> int:
    return int(100 * (niveau ** 1.5))

async def add_xp(guild_id: int, user_id: int, xp_gain: int, xp_cache_gain: int = 0):
    """Ajoute de l'XP (visible + cachée) et gère la montée de niveau automatiquement.
    Retourne (niveaux_gagnes, nouveau_niveau)."""
    pool = get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT niveau, xp, xp_cache FROM players WHERE guild_id=$1 AND user_id=$2",
            guild_id, user_id
        )
        niveau = row["niveau"]
        xp = row["xp"] + xp_gain
        xp_cache = row["xp_cache"] + xp_cache_gain
        niveaux_gagnes = 0
        bonus_pv_max = 0
        bonus_force = 0
        bonus_defense = 0
        bonus_vitesse = 0
        bonus_agilite = 0
        bonus_endurance_max = 0

        while xp >= xp_requis(niveau):
            xp -= xp_requis(niveau)
            niveau += 1
            niveaux_gagnes += 1
            bonus_pv_max += 8
            bonus_force += 2
            bonus_defense += 2
            bonus_vitesse += 1
            bonus_agilite += 1
            bonus_endurance_max += 5

        if niveaux_gagnes > 0:
            await conn.execute("""
                UPDATE players SET
                    niveau = $3,
                    xp = $4,
                    xp_cache = $5,
                    pv_max = pv_max + $6,
                    force = force + $7,
                    defense = defense + $8,
                    vitesse = vitesse + $9,
                    agilite = agilite + $10,
                    endurance_max = endurance_max + $11,
                    pv = pv_max + $6,
                    endurance = endurance_max + $11
                WHERE guild_id = $1 AND user_id = $2
            """, guild_id, user_id, niveau, xp, xp_cache,
                 bonus_pv_max, bonus_force, bonus_defense, bonus_vitesse, bonus_agilite, bonus_endurance_max)
        else:
            await conn.execute(
                "UPDATE players SET xp=$3, xp_cache=$4 WHERE guild_id=$1 AND user_id=$2",
                guild_id, user_id, xp, xp_cache
            )

    return niveaux_gagnes, niveau
