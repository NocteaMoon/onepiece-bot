from database.db import get_pool

REP_COLONNES = {
    "Pirate": "rep_pirates",
    "Marine": "rep_marine",
    "Révolutionnaire": "rep_revolutionnaires",
    "Civil": "rep_civils",
}

MONTANT_COMBAT_VICTOIRE = 2
MONTANT_ACHAT = 1
DISCOUNT_PAR_POINTS = 25
DISCOUNT_MAX_PCT = 20


async def add_reputation_faction(guild_id: int, user_id: int, faction: str, montant: int):
    colonne = REP_COLONNES.get(faction)
    if not colonne:
        return
    pool = get_pool()
    async with pool.acquire() as conn:
        await conn.execute(
            f"UPDATE players SET {colonne} = {colonne} + $3 WHERE guild_id=$1 AND user_id=$2",
            guild_id, user_id, montant
        )


async def add_reputation_marchand(guild_id: int, user_id: int, montant: int = MONTANT_ACHAT):
    pool = get_pool()
    async with pool.acquire() as conn:
        await conn.execute(
            "UPDATE players SET rep_marchands = rep_marchands + $3 WHERE guild_id=$1 AND user_id=$2",
            guild_id, user_id, montant
        )


def get_discount_pct(player) -> int:
    colonne = REP_COLONNES.get(player["faction"])
    rep_faction = player[colonne] if colonne else 0
    total = rep_faction + player["rep_marchands"]
    return min(DISCOUNT_MAX_PCT, total // DISCOUNT_PAR_POINTS)
