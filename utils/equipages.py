from database.db import get_pool

RANGS_ORDRE = ["Membre", "Officier", "Second", "Capitaine"]
RANG_EMOJIS = {"Capitaine": "🏴‍☠️", "Second": "⚔️", "Officier": "🎖️", "Membre": "🧭"}
MAX_MEMBRES = 10
COUT_CREATION = 200

def rang_valeur(rang: str) -> int:
    try:
        return RANGS_ORDRE.index(rang)
    except ValueError:
        return 0

async def get_crew_by_id(guild_id: int, crew_id: int):
    pool = get_pool()
    async with pool.acquire() as conn:
        return await conn.fetchrow("SELECT * FROM crews WHERE guild_id = $1 AND id = $2", guild_id, crew_id)

async def get_crew_by_nom(guild_id: int, nom: str):
    pool = get_pool()
    async with pool.acquire() as conn:
        return await conn.fetchrow("SELECT * FROM crews WHERE guild_id = $1 AND LOWER(nom) = LOWER($2)", guild_id, nom)

async def get_membres(guild_id: int, crew_id: int):
    pool = get_pool()
    async with pool.acquire() as conn:
        return await conn.fetch(
            "SELECT user_id, grade_equipage, prime FROM players WHERE guild_id = $1 AND equipage_id = $2 ORDER BY prime DESC",
            guild_id, crew_id
        )

async def count_membres(guild_id: int, crew_id: int) -> int:
    pool = get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow("SELECT COUNT(*) AS c FROM players WHERE guild_id = $1 AND equipage_id = $2", guild_id, crew_id)
    return row["c"]

async def prime_cumulee(guild_id: int, crew_id: int) -> int:
    pool = get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow("SELECT COALESCE(SUM(prime), 0) AS total FROM players WHERE guild_id = $1 AND equipage_id = $2", guild_id, crew_id)
    return row["total"]
