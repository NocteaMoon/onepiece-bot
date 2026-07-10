import random
import datetime
from database.db import get_pool
from data.quetes import OBJECTIFS
from data.quetes_principales import QUETES_PRINCIPALES
from data.quetes_secondaires import QUETES_SECONDAIRES
from utils.titres import unlock_titre

CODES = list(OBJECTIFS.keys())
MAX_SECONDAIRES_ACTIVES = 2


# ===== JOURNALIERES / HEBDOMADAIRES =====

async def ensure_quests(guild_id: int, user_id: int):
    pool = get_pool()
    now = datetime.datetime.utcnow()
    async with pool.acquire() as conn:
        for periode, nb_slots, duree_heures in [("daily", 3, 24), ("weekly", 2, 168)]:
            rows = await conn.fetch(
                "SELECT * FROM quest_progress WHERE guild_id=$1 AND user_id=$2 AND periode=$3",
                guild_id, user_id, periode
            )
            actives = [r for r in rows if r["expire_le"] and r["expire_le"] > now]
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
            "SELECT * FROM quest_progress WHERE guild_id=$1 AND user_id=$2 AND periode IN ('daily','weekly') ORDER BY periode, slot",
            guild_id, user_id
        )
    return rows


async def claim_daily_weekly(guild_id: int, user_id: int):
    pool = get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch("""
            SELECT * FROM quest_progress
            WHERE guild_id=$1 AND user_id=$2 AND periode IN ('daily','weekly') AND reclame = FALSE AND progres >= cible
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


# ===== PROGRESSION COMMUNE (appelée par tous les mini-jeux) =====

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


# ===== QUETE PRINCIPALE =====

async def get_main_quest(guild_id: int, user_id: int):
    pool = get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT * FROM quest_progress WHERE guild_id=$1 AND user_id=$2 AND periode='principale' AND reclame=FALSE",
            guild_id, user_id
        )
        if row:
            return row

        nb_terminees = await conn.fetchval(
            "SELECT COUNT(*) FROM quest_progress WHERE guild_id=$1 AND user_id=$2 AND periode='principale' AND reclame=TRUE",
            guild_id, user_id
        )
        if nb_terminees >= len(QUETES_PRINCIPALES):
            return None

        quete = QUETES_PRINCIPALES[nb_terminees]
        qid = quete[0]
        objectif_code = quete[3]
        cible = quete[4]
        row = await conn.fetchrow("""
            INSERT INTO quest_progress (guild_id, user_id, slot, periode, objectif_code, cible, progres, reclame, expire_le, ref_id)
            VALUES ($1,$2,0,'principale',$3,$4,0,FALSE,NULL,$5)
            RETURNING *
        """, guild_id, user_id, objectif_code, cible, str(qid))
        return row


async def claim_main_quest(guild_id: int, user_id: int):
    row = await get_main_quest(guild_id, user_id)
    if row is None or row["progres"] < row["cible"]:
        return None

    quete = next((q for q in QUETES_PRINCIPALES if str(q[0]) == row["ref_id"]), None)
    if quete is None:
        return None
    berrys, xp, titre_debloque = quete[5], quete[6], quete[8]

    pool = get_pool()
    async with pool.acquire() as conn:
        async with conn.transaction():
            await conn.execute("UPDATE quest_progress SET reclame = TRUE WHERE id = $1", row["id"])
            await conn.execute("UPDATE players SET berrys = berrys + $3 WHERE guild_id=$1 AND user_id=$2", guild_id, user_id, berrys)

    if titre_debloque:
        await unlock_titre(guild_id, user_id, titre_debloque)

    return quete[1], berrys, xp, titre_debloque


# ===== QUETES SECONDAIRES =====

async def get_active_secondaires(guild_id: int, user_id: int):
    pool = get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            "SELECT * FROM quest_progress WHERE guild_id=$1 AND user_id=$2 AND periode='secondaire' AND reclame=FALSE ORDER BY id",
            guild_id, user_id
        )
    return rows


async def get_available_secondaires(guild_id: int, user_id: int):
    pool = get_pool()
    async with pool.acquire() as conn:
        deja_vues = await conn.fetch(
            "SELECT ref_id FROM quest_progress WHERE guild_id=$1 AND user_id=$2 AND periode='secondaire'",
            guild_id, user_id
        )
    codes_exclus = {r["ref_id"] for r in deja_vues}
    return [q for q in QUETES_SECONDAIRES if q[0] not in codes_exclus]


async def accept_secondaire(guild_id: int, user_id: int, code: str):
    actives = await get_active_secondaires(guild_id, user_id)
    if len(actives) >= MAX_SECONDAIRES_ACTIVES:
        return False, "Tu as déjà 2 quêtes secondaires en cours. Abandonnes-en une avant d'en accepter une nouvelle."

    quete = next((q for q in QUETES_SECONDAIRES if q[0] == code), None)
    if quete is None:
        return False, "Quête introuvable."

    pool = get_pool()
    async with pool.acquire() as conn:
        existe = await conn.fetchrow(
            "SELECT 1 FROM quest_progress WHERE guild_id=$1 AND user_id=$2 AND periode='secondaire' AND ref_id=$3",
            guild_id, user_id, quete[0]
        )
        if existe:
            return False, "Tu as déjà accepté ou terminé cette quête."
        await conn.execute("""
            INSERT INTO quest_progress (guild_id, user_id, slot, periode, objectif_code, cible, progres, reclame, expire_le, ref_id)
            VALUES ($1,$2,0,'secondaire',$3,$4,0,FALSE,NULL,$5)
        """, guild_id, user_id, quete[3], quete[4], quete[0])
    return True, quete[1]


async def abandon_secondaire(guild_id: int, user_id: int, quest_progress_id: int):
    pool = get_pool()
    async with pool.acquire() as conn:
        await conn.execute(
            "DELETE FROM quest_progress WHERE id=$1 AND guild_id=$2 AND user_id=$3 AND periode='secondaire' AND reclame=FALSE",
            quest_progress_id, guild_id, user_id
        )


async def claim_secondaire(guild_id: int, user_id: int, quest_progress_id: int):
    pool = get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT * FROM quest_progress WHERE id=$1 AND guild_id=$2 AND user_id=$3 AND periode='secondaire' AND reclame=FALSE",
            quest_progress_id, guild_id, user_id
        )
        if row is None or row["progres"] < row["cible"]:
            return None
        quete = next((q for q in QUETES_SECONDAIRES if q[0] == row["ref_id"]), None)
        if quete is None:
            return None
        berrys, xp = quete[5], quete[6]
        await conn.execute("UPDATE quest_progress SET reclame = TRUE WHERE id = $1", row["id"])
        await conn.execute("UPDATE players SET berrys = berrys + $3 WHERE guild_id=$1 AND user_id=$2", guild_id, user_id, berrys)
    return quete[1], berrys, xp
