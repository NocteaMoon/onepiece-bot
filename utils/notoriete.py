from database.db import get_pool

MONTANT_BOSS_MONDIAL = 3
MONTANT_TOURNOI = 8
MONTANT_SUCCES = 2
MONTANT_COLLECTION = 3
MONTANT_MINIJEU_COOP = 2


async def add_notoriete(guild_id: int, user_id: int, montant: int):
    pool = get_pool()
    async with pool.acquire() as conn:
        await conn.execute(
            "UPDATE players SET notoriete = notoriete + $3 WHERE guild_id=$1 AND user_id=$2",
            guild_id, user_id, montant
        )
