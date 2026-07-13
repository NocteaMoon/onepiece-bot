from database.db import get_pool

MONTANT_PAR_BERRYS_DEPOSES = 50  # +1 respect tous les 50 Berrys déposés au coffre
BONUS_PAR_PALIER_DEFENSE = 1
POINTS_PAR_PALIER = 15


async def add_respect(guild_id: int, user_id: int, montant_depose: int):
    gain = montant_depose // MONTANT_PAR_BERRYS_DEPOSES
    if gain <= 0:
        return
    pool = get_pool()
    async with pool.acquire() as conn:
        await conn.execute(
            "UPDATE players SET respect_equipage = respect_equipage + $3 WHERE guild_id=$1 AND user_id=$2",
            guild_id, user_id, gain
        )


def get_respect_bonus(player) -> int:
    respect = player["respect_equipage"] or 0
    return (respect // POINTS_PAR_PALIER) * BONUS_PAR_PALIER_DEFENSE
