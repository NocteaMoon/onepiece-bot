import discord
from discord import app_commands
from database.db import get_pool
from utils.players import get_player, add_xp
from utils.channel_check import require_salon

COUT_PAR_RARETE = {
    "Commun": 2,
    "Aiguisé": 4,
    "Grade": 8,
    "Grand Grade": 15,
    "Suprême": 30,
    "Mythique": 60,
}

async def objet_endommage_autocomplete(interaction: discord.Interaction, current: str):
    player = await get_player(interaction.guild_id, interaction.user.id)
    if not player or player["metier"] != "Forgeron":
        return []
    pool = get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch("""
            SELECT inventory.id AS inv_id, shop_items.nom, inventory.durabilite, shop_items.durabilite_max
            FROM inventory JOIN shop_items ON inventory.item_id = shop_items.id
            WHERE inventory.guild_id=$1 AND inventory.user_id=$2 AND inventory.equipe = TRUE AND inventory.durabilite < shop_items.durabilite_max
        """, interaction.guild_id, interaction.user.id)
    filtered = [r for r in rows if current.lower() in r["nom"].lower()]
    return [
        app_commands.Choice(name=f"{r['nom']} ({r['durabilite']}/{r['durabilite_max']})", value=r["inv_id"])
        for r in filtered[:25]
    ]

@app_commands.command(name="reparer", description="Réparer un de tes objets équipés endommagés (réservé aux Forgerons)")
@app_commands.describe(objet="L'objet équipé à réparer")
@app_commands.autocomplete(objet=objet_endommage_autocomplete)
@require_salon("salon_taverne")
async def reparer(interaction: discord.Interaction, objet: int):
    await interaction.response.defer()
    player = await get_player(interaction.guild_id, interaction.user.id)
    if player is None:
        await interaction.followup.send("Tu n'as pas encore de personnage ! Lance `/commencer` pour débuter l'aventure 🏴‍☠️")
        return
    if player["metier"] != "Forgeron":
        await interaction.followup.send("⛔ Tu dois être **Forgeron** pour réparer de l'équipement ! Choisis ce métier avec `/metier choisir` (réservé aux Civils).")
        return

    pool = get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow("""
            SELECT inventory.id AS inv_id, inventory.durabilite, shop_items.nom, shop_items.rarete, shop_items.durabilite_max
            FROM inventory JOIN shop_items ON inventory.item_id = shop_items.id
            WHERE inventory.id = $1 AND inventory.guild_id=$2 AND inventory.user_id=$3 AND inventory.equipe = TRUE
        """, objet, interaction.guild_id, interaction.user.id)

    if not row:
        await interaction.followup.send("Objet introuvable ou non équipé.")
        return
    if row["durabilite"] >= row["durabilite_max"]:
        await interaction.followup.send(f"**{row['nom']}** est déjà en parfait état.")
        return

    points_manquants = row["durabilite_max"] - row["durabilite"]
    cout_point = COUT_PAR_RARETE.get(row["rarete"], 5)
    cout_total = points_manquants * cout_point

    if player["berrys"] < cout_total:
        await interaction.followup.send(f"⛔ La réparation de **{row['nom']}** coûte **{cout_total:,}฿**, tu n'as que {player['berrys']:,}฿.")
        return

    async with pool.acquire() as conn:
        async with conn.transaction():
            await conn.execute("UPDATE inventory SET durabilite = $2 WHERE id = $1", row["inv_id"], row["durabilite_max"])
            await conn.execute(
                "UPDATE players SET berrys = berrys - $3, metier_xp = metier_xp + 20 WHERE guild_id=$1 AND user_id=$2",
                interaction.guild_id, interaction.user.id, cout_total
            )

    await add_xp(interaction.guild_id, interaction.user.id, 8, 4)

    embed = discord.Embed(
        title="🔨 Réparation terminée !",
        description=f"**{row['nom']}** est comme neuf ! ({points_manquants} points de durabilité restaurés)",
        color=0xF4C430
    )
    embed.set_footer(text=f"🌊 One Piece Bot • -{cout_total:,}฿ • +20 XP Métier")
    await interaction.followup.send(embed=embed)


def setup_forgeron_commands(bot):
    bot.tree.add_command(reparer)
