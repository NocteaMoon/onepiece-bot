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
