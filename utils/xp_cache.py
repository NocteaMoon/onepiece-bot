from database.db import get_pool

# (seuil, recompense_berrys, stat_bonus, valeur_bonus)
# Volontairement non communiqué aux joueurs : c'est une mécanique CACHÉE.
PALIERS = [
    (300, 100, "force", 1),
    (800, 200, "defense", 1),
    (2000, 400, "vitesse", 1),
    (4500, 800, "agilite", 1),
    (9000, 1500, "pv_max", 10),
    (18000, 3000, "endurance_max", 10),
    (35000, 6000, "force", 2),
    (65000, 12000, "vitesse", 2),
]

STAT_LABELS = {
    "force": "Force", "defense": "Défense", "vitesse": "Vitesse",
    "agilite": "Agilité", "pv_max": "PV maximum", "endurance_max": "Endurance maximum",
}


async def check_xp_cache_paliers(guild_id: int, user_id: int):
    """À appeler après un gain d'XP significatif (victoires de combat notamment).
    Retourne la liste des nouveaux paliers atteints : [(seuil, berrys, stat, valeur), ...]"""
    pool = get_pool()
    async with pool.acquire() as conn:
        xp_cache = await conn.fetchval("SELECT xp_cache FROM players WHERE guild_id=$1 AND user_id=$2", guild_id, user_id)
        if xp_cache is None:
            return []
        deja_reclames_rows = await conn.fetch(
            "SELECT palier FROM xp_cache_paliers_atteints WHERE guild_id=$1 AND user_id=$2", guild_id, user_id
        )
        codes_reclames = {r["palier"] for r in deja_reclames_rows}

        nouveaux = []
        for seuil, berrys, stat, valeur in PALIERS:
            code = f"palier_{seuil}"
            if xp_cache >= seuil and code not in codes_reclames:
                async with conn.transaction():
                    await conn.execute(
                        "INSERT INTO xp_cache_paliers_atteints (guild_id, user_id, palier) VALUES ($1,$2,$3)",
                        guild_id, user_id, code
                    )
                    await conn.execute(
                        f"UPDATE players SET berrys = berrys + $3, {stat} = {stat} + $4 WHERE guild_id=$1 AND user_id=$2",
                        guild_id, user_id, berrys, valeur
                    )
                nouveaux.append((seuil, berrys, stat, valeur))
    return nouveaux
