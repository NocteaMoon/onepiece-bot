import asyncpg
import os

pool = None

SALON_COLUMNS = [
    "salon_annonces", "salon_reglement", "salon_bienvenue",
    "salon_logs", "salon_moderation", "salon_rapports",
    "salon_general",
    "salon_economie", "salon_boutique",
    "salon_exploration", "salon_combat", "salon_duel", "salon_peche", "salon_casino",
    "salon_equipages", "salon_marine", "salon_revolutionnaires",
    "salon_classements", "salon_quetes", "salon_succes",
]

async def init_db():
    global pool
    pool = await asyncpg.create_pool(os.environ["DATABASE_URL"])

    async with pool.acquire() as conn:
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS guild_config (
                guild_id BIGINT PRIMARY KEY,
                lang TEXT DEFAULT 'fr'
            )
        """)

        for col in SALON_COLUMNS:
            await conn.execute(f"ALTER TABLE guild_config ADD COLUMN IF NOT EXISTS {col} BIGINT")

        await conn.execute("""
            CREATE TABLE IF NOT EXISTS guild_command_roles (
                guild_id BIGINT,
                command_group TEXT,
                role_id BIGINT,
                PRIMARY KEY (guild_id, command_group, role_id)
            )
        """)

        await conn.execute("""
            CREATE TABLE IF NOT EXISTS warnings (
                id SERIAL PRIMARY KEY,
                guild_id BIGINT,
                user_id BIGINT,
                moderator_id BIGINT,
                reason TEXT,
                created_at TIMESTAMP DEFAULT NOW()
            )
        """)

        await conn.execute("""
            CREATE TABLE IF NOT EXISTS automod_config (
                guild_id BIGINT PRIMARY KEY,
                anti_spam BOOLEAN DEFAULT FALSE,
                spam_msg_limit INT DEFAULT 5,
                spam_seconds INT DEFAULT 5,
                anti_liens BOOLEAN DEFAULT FALSE,
                anti_insultes BOOLEAN DEFAULT FALSE,
                anti_raid BOOLEAN DEFAULT FALSE,
                raid_join_limit INT DEFAULT 5,
                raid_seconds INT DEFAULT 10,
                anti_mention BOOLEAN DEFAULT FALSE,
                mention_limit INT DEFAULT 5,
                anti_pub BOOLEAN DEFAULT FALSE,
                anti_alt BOOLEAN DEFAULT FALSE,
                alt_min_days INT DEFAULT 7,
                anti_bot BOOLEAN DEFAULT FALSE
            )
        """)

    print("Base de données connectée et tables vérifiées.")

def get_pool():
    return pool
