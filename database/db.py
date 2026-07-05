import asyncpg
import os

pool = None

async def init_db():
    global pool
    pool = await asyncpg.create_pool(os.environ["DATABASE_URL"])
    
    async with pool.acquire() as conn:
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS guild_config (
                guild_id BIGINT PRIMARY KEY,
                lang TEXT DEFAULT 'fr',
                salon_annonces BIGINT,
                salon_logs BIGINT,
                salon_moderation BIGINT,
                salon_economie BIGINT,
                salon_minijeux BIGINT,
                salon_equipages BIGINT,
                salon_rapports BIGINT
            )
        """)
    print("Base de données connectée et tables vérifiées.")

def get_pool():
    return pool
