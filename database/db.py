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
    "salon_taverne", "salon_regates", "salon_tresor", "salon_creation", "salon_guilde",
    "salon_carnet", "salon_recompenses", "salon_cartes", "salon_entrainement",
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

        await conn.execute("ALTER TABLE guild_config ADD COLUMN IF NOT EXISTS role_pirate BIGINT")
        await conn.execute("ALTER TABLE guild_config ADD COLUMN IF NOT EXISTS role_marine BIGINT")
        await conn.execute("ALTER TABLE guild_config ADD COLUMN IF NOT EXISTS role_revolutionnaire BIGINT")
        await conn.execute("ALTER TABLE guild_config ADD COLUMN IF NOT EXISTS role_civil BIGINT")

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

        await conn.execute("""
            CREATE TABLE IF NOT EXISTS logs_config (
                guild_id BIGINT PRIMARY KEY,
                log_msg_delete BOOLEAN DEFAULT TRUE,
                log_msg_edit BOOLEAN DEFAULT TRUE,
                log_join_leave BOOLEAN DEFAULT TRUE,
                log_salons BOOLEAN DEFAULT TRUE,
                log_roles BOOLEAN DEFAULT TRUE,
                log_pseudos BOOLEAN DEFAULT TRUE
            )
        """)

        await conn.execute("""
            CREATE TABLE IF NOT EXISTS tickets (
                channel_id BIGINT PRIMARY KEY,
                guild_id BIGINT,
                user_id BIGINT,
                type TEXT,
                status TEXT DEFAULT 'open',
                created_at TIMESTAMP DEFAULT NOW()
            )
        """)

        await conn.execute("""
            CREATE TABLE IF NOT EXISTS welcome_config (
                guild_id BIGINT PRIMARY KEY,
                message TEXT DEFAULT 'Bienvenue {mention} sur {serveur} ! Tu es notre {nombre}ème membre 🏴‍☠️',
                auto_role_id BIGINT,
                verification_enabled BOOLEAN DEFAULT FALSE,
                background_url TEXT
            )
        """)
        await conn.execute("ALTER TABLE welcome_config ADD COLUMN IF NOT EXISTS background_url TEXT")

        await conn.execute("""
            CREATE TABLE IF NOT EXISTS players (
                guild_id BIGINT,
                user_id BIGINT,
                niveau INT DEFAULT 1,
                xp BIGINT DEFAULT 0,
                xp_cache BIGINT DEFAULT 0,
                titre TEXT,
                metier TEXT,
                faction TEXT DEFAULT 'Civil',
                berrys BIGINT DEFAULT 100,
                banque BIGINT DEFAULT 0,
                prime BIGINT DEFAULT 0,
                rep_pirates INT DEFAULT 0,
                rep_marine INT DEFAULT 0,
                rep_revolutionnaires INT DEFAULT 0,
                rep_civils INT DEFAULT 0,
                rep_marchands INT DEFAULT 0,
                notoriete INT DEFAULT 0,
                pv_max INT DEFAULT 100,
                pv INT DEFAULT 100,
                force INT DEFAULT 10,
                defense INT DEFAULT 10,
                vitesse INT DEFAULT 10,
                agilite INT DEFAULT 10,
                endurance_max INT DEFAULT 100,
                endurance INT DEFAULT 100,
                maitrise_epee INT DEFAULT 0,
                maitrise_poings INT DEFAULT 0,
                maitrise_lance INT DEFAULT 0,
                maitrise_pistolet INT DEFAULT 0,
                maitrise_fusil INT DEFAULT 0,
                maitrise_arc INT DEFAULT 0,
                fruit TEXT,
                fruit_eveil BOOLEAN DEFAULT FALSE,
                haki_armement INT DEFAULT 0,
                haki_observation INT DEFAULT 0,
                haki_rois INT DEFAULT 0,
                equip_arme_principale BIGINT,
                equip_arme_secondaire BIGINT,
                equip_tete BIGINT,
                equip_corps BIGINT,
                equip_accessoire1 BIGINT,
                equip_accessoire2 BIGINT,
                equip_navire BIGINT,
                mer TEXT DEFAULT 'East Blue',
                ile TEXT DEFAULT 'Île de départ',
                equipage_id BIGINT,
                grade_equipage TEXT,
                chance INT DEFAULT 0,
                ko_jusqua TIMESTAMP,
                derniere_regen TIMESTAMP DEFAULT NOW(),
                cree_le TIMESTAMP DEFAULT NOW(),
                PRIMARY KEY (guild_id, user_id)
            )
        """)
        await conn.execute("ALTER TABLE players ADD COLUMN IF NOT EXISTS metier_xp INT DEFAULT 0")
        await conn.execute("ALTER TABLE players ADD COLUMN IF NOT EXISTS metier_rang INT DEFAULT 0")
        await conn.execute("ALTER TABLE players ADD COLUMN IF NOT EXISTS voyage_protege INT DEFAULT 0")
        await conn.execute("ALTER TABLE players ADD COLUMN IF NOT EXISTS last_daily TIMESTAMP")
        await conn.execute("ALTER TABLE players ADD COLUMN IF NOT EXISTS daily_streak INT DEFAULT 0")
        await conn.execute("ALTER TABLE players ADD COLUMN IF NOT EXISTS last_weekly TIMESTAMP")
        await conn.execute("ALTER TABLE players ADD COLUMN IF NOT EXISTS last_monthly TIMESTAMP")
        await conn.execute("ALTER TABLE players ADD COLUMN IF NOT EXISTS succes_tournoi_gagne BOOLEAN DEFAULT FALSE")
        await conn.execute("ALTER TABLE players ADD COLUMN IF NOT EXISTS nb_tournois_gagnes INT DEFAULT 0")
        await conn.execute("ALTER TABLE players ADD COLUMN IF NOT EXISTS nb_boss_vaincus INT DEFAULT 0")
        await conn.execute("ALTER TABLE players ADD COLUMN IF NOT EXISTS respect_equipage INT DEFAULT 0")
        await conn.execute("ALTER TABLE players ADD COLUMN IF NOT EXISTS nb_voyages_reussis INT DEFAULT 0")
        await conn.execute("ALTER TABLE players ADD COLUMN IF NOT EXISTS secret_trouve BOOLEAN DEFAULT FALSE")

        await conn.execute("""
            CREATE TABLE IF NOT EXISTS shop_items (
                id SERIAL PRIMARY KEY,
                guild_id BIGINT,
                nom TEXT,
                description TEXT,
                categorie TEXT,
                faction TEXT DEFAULT 'Tous',
                rarete TEXT DEFAULT 'Commun',
                prix BIGINT DEFAULT 0,
                slot TEXT,
                bonus_force INT DEFAULT 0,
                bonus_defense INT DEFAULT 0,
                bonus_vitesse INT DEFAULT 0,
                bonus_agilite INT DEFAULT 0,
                bonus_pv INT DEFAULT 0,
                bonus_chance INT DEFAULT 0,
                soin_pv INT DEFAULT 0,
                soin_endurance INT DEFAULT 0,
                durabilite_max INT DEFAULT 100,
                stock INT DEFAULT -1,
                niveau_requis INT DEFAULT 1,
                actif BOOLEAN DEFAULT TRUE,
                cree_le TIMESTAMP DEFAULT NOW()
            )
        """)
        await conn.execute("ALTER TABLE shop_items ADD COLUMN IF NOT EXISTS type_arme TEXT")

        await conn.execute("""
            CREATE TABLE IF NOT EXISTS inventory (
                id SERIAL PRIMARY KEY,
                guild_id BIGINT,
                user_id BIGINT,
                item_id BIGINT,
                quantite INT DEFAULT 1,
                durabilite INT DEFAULT 100,
                equipe BOOLEAN DEFAULT FALSE
            )
        """)

        await conn.execute("""
            CREATE TABLE IF NOT EXISTS shop_seeded (
                guild_id BIGINT PRIMARY KEY
            )
        """)

        await conn.execute("""
            CREATE TABLE IF NOT EXISTS crews (
                id SERIAL PRIMARY KEY,
                guild_id BIGINT,
                nom TEXT,
                drapeau_url TEXT,
                capitaine_id BIGINT,
                coffre_berrys BIGINT DEFAULT 0,
                cree_le TIMESTAMP DEFAULT NOW()
            )
        """)
        await conn.execute("ALTER TABLE crews ADD COLUMN IF NOT EXISTS type TEXT DEFAULT 'Pirate'")

        await conn.execute("""
            CREATE TABLE IF NOT EXISTS quest_progress (
                id SERIAL PRIMARY KEY,
                guild_id BIGINT,
                user_id BIGINT,
                slot INT,
                periode TEXT,
                objectif_code TEXT,
                cible INT,
                progres INT DEFAULT 0,
                reclame BOOLEAN DEFAULT FALSE,
                expire_le TIMESTAMP
            )
        """)
        await conn.execute("ALTER TABLE quest_progress ADD COLUMN IF NOT EXISTS ref_id TEXT")

        await conn.execute("""
            CREATE TABLE IF NOT EXISTS world_boss (
                id SERIAL PRIMARY KEY,
                guild_id BIGINT,
                mer TEXT,
                boss_nom TEXT,
                pv INT,
                pv_max INT,
                phase TEXT DEFAULT 'inscription',
                channel_id BIGINT,
                message_id BIGINT,
                cree_le TIMESTAMP DEFAULT NOW()
            )
        """)

        await conn.execute("""
            CREATE TABLE IF NOT EXISTS world_boss_participants (
                id SERIAL PRIMARY KEY,
                world_boss_id INT,
                guild_id BIGINT,
                user_id BIGINT,
                degats INT DEFAULT 0
            )
        """)

        await conn.execute("""
            CREATE TABLE IF NOT EXISTS achievements_claimed (
                guild_id BIGINT,
                user_id BIGINT,
                code TEXT,
                claimed_at TIMESTAMP DEFAULT NOW(),
                PRIMARY KEY (guild_id, user_id, code)
            )
        """)

        await conn.execute("""
            CREATE TABLE IF NOT EXISTS mers_visitees (
                guild_id BIGINT,
                user_id BIGINT,
                mer TEXT,
                PRIMARY KEY (guild_id, user_id, mer)
            )
        """)

        await conn.execute("""
            CREATE TABLE IF NOT EXISTS titres_debloques (
                guild_id BIGINT,
                user_id BIGINT,
                titre TEXT,
                PRIMARY KEY (guild_id, user_id, titre)
            )
        """)

        await conn.execute("""
            CREATE TABLE IF NOT EXISTS cards_owned (
                guild_id BIGINT,
                user_id BIGINT,
                code TEXT,
                quantite INT DEFAULT 0,
                PRIMARY KEY (guild_id, user_id, code)
            )
        """)

        await conn.execute("""
            CREATE TABLE IF NOT EXISTS card_collections_claimed (
                guild_id BIGINT,
                user_id BIGINT,
                categorie TEXT,
                claimed_at TIMESTAMP DEFAULT NOW(),
                PRIMARY KEY (guild_id, user_id, categorie)
            )
        """)

        await conn.execute("""
            CREATE TABLE IF NOT EXISTS xp_cache_paliers_atteints (
                guild_id BIGINT,
                user_id BIGINT,
                palier TEXT,
                PRIMARY KEY (guild_id, user_id, palier)
            )
        """)

        await conn.execute("""
            CREATE TABLE IF NOT EXISTS guild_weather (
                guild_id BIGINT PRIMARY KEY,
                meteo TEXT DEFAULT 'Ciel dégagé',
                changee_le TIMESTAMP DEFAULT NOW()
            )
        """)

        await conn.execute("""
            CREATE TABLE IF NOT EXISTS active_buffs (
                guild_id BIGINT,
                user_id BIGINT,
                stat TEXT,
                valeur INT,
                expire_le TIMESTAMP,
                PRIMARY KEY (guild_id, user_id)
            )
        """)

    print("Base de données connectée et tables vérifiées.")

def get_pool():
    return pool
