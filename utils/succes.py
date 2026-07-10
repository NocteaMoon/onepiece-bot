from database.db import get_pool
from utils.metiers import get_rang
from data.succes import SUCCES

GRADES_CHEFS = ("Capitaine", "Amiral", "Meneur", "Maitre")


async def _condition_remplie(guild_id, user_id, player, check_type, param):
    if check_type == "niveau_min":
        return player["niveau"] >= param
    if check_type == "banque_min":
        return player["banque"] >= param
    if check_type == "total_min":
        return (player["berrys"] + player["banque"]) >= param
    if check_type == "prime_min":
        return player["prime"] >= param
    if check_type == "metier_maitre":
        if not player["metier"]:
            return False
        return get_rang(player["metier_xp"]) >= 2
    if check_type == "chef_organisation":
        if not player["grade_equipage"]:
            return False
        return player["grade_equipage"] in GRADES_CHEFS
    if check_type == "mer_atteinte":
        return player["mer"] == param
    if check_type == "boss_mondial_vaincu":
        pool = get_pool()
        async with pool.acquire() as conn:
            row = await conn.fetchrow("""
                SELECT 1 FROM world_boss_participants wp
                JOIN world_boss wb ON wp.world_boss_id = wb.id
                WHERE wp.guild_id=$1 AND wp.user_id=$2 AND wb.pv <= 0
                LIMIT 1
            """, guild_id, user_id)
        return row is not None
    if check_type == "tournoi_gagne":
        return bool(player["succes_tournoi_gagne"])
    return False


async def get_claimed_codes(guild_id, user_id):
    pool = get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch("SELECT code FROM achievements_claimed WHERE guild_id=$1 AND user_id=$2", guild_id, user_id)
    return {r["code"] for r in rows}


async def get_succes_status(guild_id, user_id, player):
    claimed = await get_claimed_codes(guild_id, user_id)
    result = []
    for code, titre, description, berrys, check_type, param in SUCCES:
        if code in claimed:
            statut = "reclame"
        else:
            ok = await _condition_remplie(guild_id, user_id, player, check_type, param)
            statut = "atteignable" if ok else "non_atteint"
        result.append({"code": code, "titre": titre, "description": description, "berrys": berrys, "statut": statut})
    return result


async def claim_succes(guild_id, user_id, player, code):
    entry = next((s for s in SUCCES if s[0] == code), None)
    if entry is None:
        return None
    _, titre, description, berrys, check_type, param = entry

    claimed = await get_claimed_codes(guild_id, user_id)
    if code in claimed:
        return None
    ok = await _condition_remplie(guild_id, user_id, player, check_type, param)
    if not ok:
        return None

    pool = get_pool()
    async with pool.acquire() as conn:
        async with conn.transaction():
            await conn.execute(
                "INSERT INTO achievements_claimed (guild_id, user_id, code) VALUES ($1,$2,$3)",
                guild_id, user_id, code
            )
            await conn.execute(
                "UPDATE players SET berrys = berrys + $3 WHERE guild_id=$1 AND user_id=$2",
                guild_id, user_id, berrys
            )
    return titre, berrys
