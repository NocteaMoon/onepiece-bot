from database.db import get_pool
from utils.fruits import get_fruit_bonus
from utils.haki import get_haki_bonus
from utils.maitrise import get_maitrise_bonus
from utils.respect import get_respect_bonus
from utils.buffs import get_buff_bonus

async def get_effective_stats(guild_id: int, user_id: int, base_player):
    """Calcule les stats effectives : base + équipement + Fruit + Haki + Maîtrise + Respect + Buff de cuisine."""
    pool = get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch("""
            SELECT shop_items.bonus_force, shop_items.bonus_defense, shop_items.bonus_vitesse,
                   shop_items.bonus_agilite, shop_items.bonus_pv, shop_items.bonus_chance
            FROM inventory
            JOIN shop_items ON inventory.item_id = shop_items.id
            WHERE inventory.guild_id = $1 AND inventory.user_id = $2 AND inventory.equipe = TRUE
        """, guild_id, user_id)

        type_arme_row = None
        if base_player["equip_arme_principale"]:
            type_arme_row = await conn.fetchrow(
                "SELECT type_arme FROM shop_items WHERE id = $1", base_player["equip_arme_principale"]
            )

    def total(cle):
        return sum(r[cle] for r in rows) if rows else 0

    fruit_bonus = get_fruit_bonus(base_player)
    haki_bonus = get_haki_bonus(base_player)
    type_arme_equipee = type_arme_row["type_arme"] if type_arme_row else None
    maitrise_bonus = get_maitrise_bonus(base_player, type_arme_equipee)
    respect_bonus = get_respect_bonus(base_player)
    buff_bonus = await get_buff_bonus(guild_id, user_id)

    return {
        "force": base_player["force"] + total("bonus_force") + fruit_bonus["force"] + haki_bonus["force"] + maitrise_bonus + buff_bonus["force"],
        "defense": base_player["defense"] + total("bonus_defense") + fruit_bonus["defense"] + haki_bonus["defense"] + respect_bonus + buff_bonus["defense"],
        "vitesse": base_player["vitesse"] + total("bonus_vitesse") + fruit_bonus["vitesse"] + haki_bonus["vitesse"] + buff_bonus["vitesse"],
        "agilite": base_player["agilite"] + total("bonus_agilite") + fruit_bonus["agilite"] + haki_bonus["agilite"] + buff_bonus["agilite"],
        "chance": base_player["chance"] + total("bonus_chance"),
        "bonus_pv_combat": total("bonus_pv"),
        "type_arme_equipee": type_arme_equipee,
    }
