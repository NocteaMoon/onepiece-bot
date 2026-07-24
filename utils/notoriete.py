from database.db import get_pool

MONTANT_BOSS_MONDIAL = 3
MONTANT_TOURNOI = 8
MONTANT_SUCCES = 2
MONTANT_COLLECTION = 3
MONTANT_MINIJEU_COOP = 2

# (seuil, recompense_berrys, titre) — titres distincts de ceux des succès, persistés dans titres_debloques
PALIERS_NOTORIETE = [
    (25, 80, "Visage familier"),
    (75, 200, "Personnage en vue"),
    (200, 500, "Figure incontournable"),
    (500, 1200, "Légende des quatre mers"),
    (1000, 3000, "Mythe vivant"),
]


async def add_notoriete(guild_id: int, user_id: int, montant: int):
    pool = get_pool()
    async with pool.acquire() as conn:
        await conn.execute(
            "UPDATE players SET notoriete = notoriete + $3 WHERE guild_id=$1 AND user_id=$2",
            guild_id, user_id, montant
        )


async def check_notoriete_paliers(guild_id: int, user_id: int):
    """À appeler après consultation de la notoriété. Retourne les nouveaux paliers franchis : [(seuil, berrys, titre), ...]"""
    pool = get_pool()
    async with pool.acquire() as conn:
        notoriete = await conn.fetchval("SELECT notoriete FROM players WHERE guild_id=$1 AND user_id=$2", guild_id, user_id)
        if notoriete is None:
            return []
        deja_rows = await conn.fetch("SELECT titre FROM titres_debloques WHERE guild_id=$1 AND user_id=$2", guild_id, user_id)
        titres_deja = {r["titre"] for r in deja_rows}

        nouveaux = []
        for seuil, berrys, titre in PALIERS_NOTORIETE:
            if notoriete >= seuil and titre not in titres_deja:
                async with conn.transaction():
                    await conn.execute(
                        "INSERT INTO titres_debloques (guild_id, user_id, titre) VALUES ($1,$2,$3) ON CONFLICT DO NOTHING",
                        guild_id, user_id, titre
                    )
                    await conn.execute(
                        "UPDATE players SET berrys = berrys + $3 WHERE guild_id=$1 AND user_id=$2",
                        guild_id, user_id, berrys
                    )
                nouveaux.append((seuil, berrys, titre))
    return nouveaux
