import random
import datetime
from database.db import get_pool
from data.quetes import OBJECTIFS

CODES = list(OBJECTIFS.keys())

async def ensure_quests(guild_id: int, user_id: int):
    pool = get_pool()
    now = datetime.datetime.utcnow()
    async with pool.acquire() as conn:
        for periode, nb_slots, duree_heures in [("daily", 3, 24), ("weekly", 2, 168)]:
            rows = await conn.fetch(
                "SELECT * FROM quest_progress WHERE guild_id=$1 AND user_id=$2 AND periode=$3",
                guild_id, user_id, periode
            )
            actives = [r for r in rows if r["expire_le"] > now]
            if actives:
                continue

            await conn.execute(
                "DELETE FROM quest_progress WHERE guild_id=$1 AND user_id=$2 AND periode=$3",
                guild_id, user_id, periode
            )
            codes = random.sample(CODES, min(nb_slots, len(CODES)))
            expire_le = now + datetime.timedelta(hours=duree_heures)
            for slot, code in enumerate(codes):
                data = OBJECTIFS[code]
                if periode == "daily":
                    cible = random.randint(data["daily_min"], data["daily_max"])
                else:
                    cible = random.randint(data["weekly_min"], data["weekly_max"])
                await conn.execute("""
                    INSERT INTO quest_progress (guild_id, user_id, slot, periode, objectif_code, cible, progres, reclame, expire_le)
                    VALUES ($1,$2,$3,$4,$5,$6,0,FALSE,$7)
                """, guild_id, user_id, slot, periode, code, cible, expire_le)


async def get_quests(guild_id: int, user_id: int):
    await ensure_quests(guild_id, user_id)
    pool = get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            "SELECT * FROM quest_progress WHERE guild_id=$1 AND user_id=$2 ORDER BY periode, slot",
            guild_id, user_id
        )
    return rows


async def increment_quest_progress(guild_id: int, user_id: int, objectif_code: str, montant: int = 1):
    await ensure_quests(guild_id, user_id)
    pool = get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch("""
            SELECT id, progres, cible FROM quest_progress
            WHERE guild_id=$1 AND user_id=$2 AND objectif_code=$3 AND reclame = FALSE
        """, guild_id, user_id, objectif_code)
        for r in rows:
            nouveau = min(r["cible"], r["progres"] + montant)
            await conn.execute("UPDATE quest_progress SET progres = $2 WHERE id = $1", r["id"], nouveau)


async def claim_completed(guild_id: int, user_id: int):
    pool = get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch("""
            SELECT * FROM quest_progress
            WHERE guild_id=$1 AND user_id=$2 AND reclame = FALSE AND progres >= cible
        """, guild_id, user_id)
        if not rows:
            return 0, 0, 0
        total_berrys = 0
        total_xp = 0
        for r in rows:
            data = OBJECTIFS[r["objectif_code"]]
            total_berrys += r["cible"] * data["berrys_per"]
            total_xp += r["cible"] * data["xp_per"]
            await conn.execute("UPDATE quest_progress SET reclame = TRUE WHERE id = $1", r["id"])
        await conn.execute(
            "UPDATE players SET berrys = berrys + $3 WHERE guild_id=$1 AND user_id=$2",
            guild_id, user_id, total_berrys
        )
    return len(rows), total_berrys, total_xp
