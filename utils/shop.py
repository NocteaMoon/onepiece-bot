import random
from database.db import get_pool
from data.catalogue import CATALOGUE

async def seed_shop_if_needed(guild_id: int):
    """Insère les objets du catalogue manquants (idempotent : ne duplique jamais, ajoute juste les nouveautés)."""
    pool = get_pool()
    async with pool.acquire() as conn:
        existing = await conn.fetch("SELECT nom FROM shop_items WHERE guild_id = $1", guild_id)
        existing_names = {r["nom"] for r in existing}
        for item in CATALOGUE:
            (nom, description, categorie, faction, rarete, prix, slot,
             b_force, b_defense, b_vitesse, b_agilite, b_pv, b_chance,
             soin_pv, soin_endurance, durabilite_max, stock, niveau_requis, type_arme) = item
            if nom in existing_names:
                continue
            await conn.execute("""
                INSERT INTO shop_items (
                    guild_id, nom, description, categorie, faction, rarete, prix, slot,
                    bonus_force, bonus_defense, bonus_vitesse, bonus_agilite, bonus_pv, bonus_chance,
                    soin_pv, soin_endurance, durabilite_max, stock, niveau_requis, type_arme
                ) VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12,$13,$14,$15,$16,$17,$18,$19,$20)
            """, guild_id, nom, description, categorie, faction, rarete, prix, slot,
                 b_force, b_defense, b_vitesse, b_agilite, b_pv, b_chance,
                 soin_pv, soin_endurance, durabilite_max, stock, niveau_requis, type_arme)


async def get_visible_items(guild_id: int, faction: str, categorie: str = None):
    pool = get_pool()
    query = "SELECT * FROM shop_items WHERE guild_id = $1 AND actif = TRUE AND (faction = 'Tous' OR faction = $2)"
    params = [guild_id, faction]
    if categorie:
        query += " AND categorie = $3"
        params.append(categorie)
    query += " ORDER BY categorie, prix"
    async with pool.acquire() as conn:
        rows = await conn.fetch(query, *params)
    # Les objets obtenables uniquement par artisanat (plats, remèdes, objets forgés, cartes)
    # ont tous un stock à 0 et ne sont jamais vendus en boutique.
    return [r for r in rows if r["stock"] != 0]


async def get_item_by_id(guild_id: int, item_id: int):
    pool = get_pool()
    async with pool.acquire() as conn:
        return await conn.fetchrow("SELECT * FROM shop_items WHERE guild_id = $1 AND id = $2", guild_id, item_id)


async def get_item_by_name(guild_id: int, nom: str):
    pool = get_pool()
    async with pool.acquire() as conn:
        return await conn.fetchrow("SELECT * FROM shop_items WHERE guild_id = $1 AND nom = $2", guild_id, nom)


async def get_inventory(guild_id: int, user_id: int):
    pool = get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch("""
            SELECT inventory.*, shop_items.nom, shop_items.categorie, shop_items.slot, shop_items.durabilite_max
            FROM inventory
            JOIN shop_items ON inventory.item_id = shop_items.id
            WHERE inventory.guild_id = $1 AND inventory.user_id = $2
            ORDER BY shop_items.categorie, shop_items.nom
        """, guild_id, user_id)
    return rows


RARETE_WEIGHTS_LOOT = {
    "Commun": 100,
    "Aiguisé": 35,
    "Grade": 10,
    "Grand Grade": 3,
    "Suprême": 0,
    "Mythique": 0,
}

async def get_random_loot(guild_id: int, faction: str):
    """Tire un objet aléatoire (consommable/accessoire) pour le loot d'exploration, pondéré par rareté."""
    pool = get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch("""
            SELECT * FROM shop_items
            WHERE guild_id = $1 AND actif = TRUE
              AND categorie IN ('Consommable', 'Accessoire')
              AND (faction = 'Tous' OR faction = $2)
        """, guild_id, faction)
    if not rows:
        return None
    weights = [RARETE_WEIGHTS_LOOT.get(r["rarete"], 0) for r in rows]
    if sum(weights) == 0:
        return None
    return random.choices(rows, weights=weights, k=1)[0]
