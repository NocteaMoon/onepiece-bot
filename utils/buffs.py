import datetime
from database.db import get_pool

async def apply_buff(guild_id: int, user_id: int, stat: str, valeur: int, duree_min: int):
    expire_le = datetime.datetime.utcnow() + datetime.timedelta(minutes=duree_min)
    pool = get_pool()
    async with pool.acquire() as conn:
        await conn.execute("""
            INSERT INTO active_buffs (guild_id, user_id, stat, valeur, expire_le)
            VALUES ($1,$2,$3,$4,$5)
            ON CONFLICT (guild_id, user_id) DO UPDATE SET stat=$3, valeur=$4, expire_le=$5
        """, guild_id, user_id, stat, valeur, expire_le)


async def get_active_buff(guild_id: int, user_id: int):
    pool = get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT stat, valeur, expire_le FROM active_buffs WHERE guild_id=$1 AND user_id=$2",
            guild_id, user_id
        )
    if not row:
        return None
    if row["expire_le"] < datetime.datetime.utcnow():
        return None
    return row["stat"], row["valeur"], row["expire_le"]


async def get_buff_bonus(guild_id: int, user_id: int) -> dict:
    bonus = {"force": 0, "defense": 0, "vitesse": 0, "agilite": 0}
    buff = await get_active_buff(guild_id, user_id)
    if buff:
        stat, valeur, _ = buff
        if stat in bonus:
            bonus[stat] += valeur
    return bonus
