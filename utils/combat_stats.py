from database.db import get_pool

async def get_effective_stats(guild_id: int, user_id: int, base_player):
    """Calcule les stats effectives (base + bonus d'équipement équipé)."""
    pool = get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch("""
            SELECT shop_items.bonus_force, shop_items.bonus_defense, shop_items.bonus_vitesse,
                   shop_items.bonus_agilite, shop_items.bonus_pv, shop_items.bonus_chance
            FROM inventory
            JOIN shop_items ON inventory.item_id = shop_items.id
            WHERE inventory.guild_id = $1 AND inventory.user_id = $2 AND inventory.equipe = TRUE
        """, guild_id, user_id)

    def total(cle):
        return sum(r[cle] for r in rows) if rows else 0

    return {
        "force": base_player["force"] + total("bonus_force"),
        "defense": base_player["defense"] + total("bonus_defense"),
        "vitesse": base_player["vitesse"] + total("bonus_vitesse"),
        "agilite": base_player["agilite"] + total("bonus_agilite"),
        "chance": base_player["chance"] + total("bonus_chance"),
        "bonus_pv_combat": total("bonus_pv"),
    }
