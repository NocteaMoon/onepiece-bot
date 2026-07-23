from database.db import get_pool
from data.succes import FAMILLES

GRADES_CHEFS = ("Capitaine", "Amiral", "Meneur", "Maitre")

DESCRIPTIONS = {
    "niveau_min": lambda s: f"Atteindre le niveau {s}",
    "total_min": lambda s: f"Posséder au moins {s:,}฿ au total (liquide + banque)",
    "prime_min": lambda s: f"Atteindre {s:,}฿ de prime",
    "mers_visitees_min": lambda s: f"Avoir exploré {s} mer(s) différente(s)",
    "metier_xp_min": lambda s: f"Atteindre {s} XP dans ton métier",
    "chef_organisation": lambda s: "Diriger une organisation (Capitaine, Amiral, Meneur ou Maître de Guilde)",
    "org_prime_min": lambda s: f"Ton organisation cumule au moins {s:,}฿ de prime parmi ses membres",
    "tournois_gagnes_min": lambda s: f"Remporter {s} tournoi(s)",
    "boss_vaincus_min": lambda s: f"Participer à la victoire contre {s} boss mondial/mondiaux",
    "notoriete_min": lambda s: f"Atteindre {s:,} points de Notoriété",
    "reputation_max": lambda s: f"Atteindre {s:,} points de réputation dans une faction (Pirates/Marine/Révolutionnaires/Civils)",
    "cartes_uniques_min": lambda s: f"Posséder {s} carte(s) unique(s) différente(s)",
}


async def record_mer_visitee(guild_id: int, user_id: int, mer: str):
    pool = get_pool()
    async with pool.acquire() as conn:
        await conn.execute(
            "INSERT INTO mers_visitees (guild_id, user_id, mer) VALUES ($1,$2,$3) ON CONFLICT DO NOTHING",
            guild_id, user_id, mer
        )


async def _condition_remplie(guild_id, user_id, player, check_type, seuil):
    if check_type == "niveau_min":
        return player["niveau"] >= seuil
    if check_type == "total_min":
        return (player["berrys"] + player["banque"]) >= seuil
    if check_type == "prime_min":
        return player["prime"] >= seuil
    if check_type == "mers_visitees_min":
        pool = get_pool()
        async with pool.acquire() as conn:
            count = await conn.fetchval(
                "SELECT COUNT(DISTINCT mer) FROM mers_visitees WHERE guild_id=$1 AND user_id=$2",
                guild_id, user_id
            )
        return (count or 0) >= seuil
    if check_type == "metier_xp_min":
        return bool(player["metier"]) and player["metier_xp"] >= seuil
    if check_type == "chef_organisation":
        return bool(player["grade_equipage"]) and player["grade_equipage"] in GRADES_CHEFS
    if check_type == "org_prime_min":
        if not player["equipage_id"] or not player["grade_equipage"] or player["grade_equipage"] not in GRADES_CHEFS:
            return False
        from utils.equipages import prime_cumulee
        total = await prime_cumulee(guild_id, player["equipage_id"])
        return total >= seuil
    if check_type == "tournois_gagnes_min":
        return player["nb_tournois_gagnes"] >= seuil
    if check_type == "boss_vaincus_min":
        return player["nb_boss_vaincus"] >= seuil
    if check_type == "notoriete_min":
        return player["notoriete"] >= seuil
    if check_type == "reputation_max":
        meilleure_rep = max(player["rep_pirates"], player["rep_marine"], player["rep_revolutionnaires"], player["rep_civils"])
        return meilleure_rep >= seuil
    if check_type == "cartes_uniques_min":
        pool = get_pool()
        async with pool.acquire() as conn:
            count = await conn.fetchval(
                "SELECT COUNT(DISTINCT code) FROM cards_owned WHERE guild_id=$1 AND user_id=$2",
                guild_id, user_id
            )
        return (count or 0) >= seuil
    return False


async def get_claimed_codes(guild_id, user_id):
    pool = get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch("SELECT code FROM achievements_claimed WHERE guild_id=$1 AND user_id=$2", guild_id, user_id)
    return {r["code"] for r in rows}


async def get_family_status(guild_id, user_id, player, famille_key):
    nom, check_type, tiers = FAMILLES[famille_key]
    claimed = await get_claimed_codes(guild_id, user_id)
    result = []
    for i, (seuil, berrys, titre) in enumerate(tiers):
        code = f"{famille_key}_{i+1}"
        if code in claimed:
            statut = "reclame"
        else:
            ok = await _condition_remplie(guild_id, user_id, player, check_type, seuil)
            statut = "atteignable" if ok else "non_atteint"
        description = DESCRIPTIONS[check_type](seuil)
        result.append({"code": code, "titre": titre, "description": description, "berrys": berrys, "statut": statut})
    return nom, result


async def get_overview(guild_id, user_id, player):
    total = 0
    reclames = 0
    for famille_key in FAMILLES:
        _, statuts = await get_family_status(guild_id, user_id, player, famille_key)
        total += len(statuts)
        reclames += sum(1 for s in statuts if s["statut"] == "reclame")
    return reclames, total


async def claim_succes(guild_id, user_id, player, code):
    famille_key, index_str = code.rsplit("_", 1)
    if famille_key not in FAMILLES:
        return None
    _, check_type, tiers = FAMILLES[famille_key]
    try:
        index = int(index_str) - 1
    except ValueError:
        return None
    if index < 0 or index >= len(tiers):
        return None
    seuil, berrys, titre = tiers[index]

    claimed = await get_claimed_codes(guild_id, user_id)
    if code in claimed:
        return None
    ok = await _condition_remplie(guild_id, user_id, player, check_type, seuil)
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
