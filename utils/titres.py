from database.db import get_pool

async def unlock_titre(guild_id: int, user_id: int, titre: str):
    """Débloque un titre définitivement. L'équipe automatiquement si le joueur n'en a aucun."""
    pool = get_pool()
    async with pool.acquire() as conn:
        async with conn.transaction():
            inserted = await conn.fetchrow(
                "INSERT INTO titres_debloques (guild_id, user_id, titre) VALUES ($1,$2,$3) ON CONFLICT DO NOTHING RETURNING titre",
                guild_id, user_id, titre
            )
            if inserted:
                current = await conn.fetchrow("SELECT titre FROM players WHERE guild_id=$1 AND user_id=$2", guild_id, user_id)
                if current and not current["titre"]:
                    await conn.execute("UPDATE players SET titre = $3 WHERE guild_id=$1 AND user_id=$2", guild_id, user_id, titre)


async def get_titres_debloques(guild_id: int, user_id: int):
    pool = get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch("SELECT titre FROM titres_debloques WHERE guild_id=$1 AND user_id=$2 ORDER BY titre", guild_id, user_id)
    return [r["titre"] for r in rows]


async def equip_titre(guild_id: int, user_id: int, titre: str) -> bool:
    pool = get_pool()
    async with pool.acquire() as conn:
        owned = await conn.fetchrow("SELECT 1 FROM titres_debloques WHERE guild_id=$1 AND user_id=$2 AND titre=$3", guild_id, user_id, titre)
        if not owned:
            return False
        await conn.execute("UPDATE players SET titre = $3 WHERE guild_id=$1 AND user_id=$2", guild_id, user_id, titre)
    return True
