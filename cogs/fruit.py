import discord
from discord import app_commands
from database.db import get_pool
from utils.players import get_player
from utils.channel_check import require_salon
from utils.fruits import get_fruit, get_fruit_by_nom, get_fruits_disponibles, manger_fruit

fruit_group = app_commands.Group(name="fruit", description="Fruits du Démon")

CATEGORIE_EMOJIS = {"Singulier": "🔮", "Élémentaire": "🔥", "Mutation": "🐉"}


@fruit_group.command(name="voir", description="Voir ton Fruit du Démon actuel")
@app_commands.describe(membre="Le membre dont tu veux voir le fruit (toi par défaut)")
async def fruit_voir(interaction: discord.Interaction, membre: discord.Member = None):
    await interaction.response.defer()
    cible = membre or interaction.user
    player = await get_player(interaction.guild_id, cible.id)
    if player is None:
        await interaction.followup.send("Tu n'as pas encore de personnage ! Lance `/commencer` pour débuter l'aventure 🏴‍☠️")
        return
    if not player["fruit"]:
        possessif = "Tu n'" if cible == interaction.user else f"{cible.display_name} n'"
        await interaction.followup.send(f"{possessif}as encore mangé aucun Fruit du Démon.")
        return

    fruit = get_fruit_by_nom(player["fruit"])
    emoji = CATEGORIE_EMOJIS.get(fruit[2], "🍈") if fruit else "🍈"
    eveil_texte = "✨ **Éveillé !**" if player["fruit_eveil"] else "Non éveillé (l'éveil se déclenche au hasard, en combat)"

    embed = discord.Embed(title=f"{emoji} {player['fruit']}", color=0x8E44AD)
    if fruit:
        embed.description = fruit[3]
        embed.add_field(name="Catégorie", value=fruit[2], inline=True)
    embed.add_field(name="État", value=eveil_texte, inline=True)
    embed.set_footer(text="🌊 One Piece Bot • Fruits du Démon")
    await interaction.followup.send(embed=embed)


@fruit_group.command(name="marche_noir", description="Voir les Fruits du Démon disponibles à l'achat (très coûteux)")
@require_salon("salon_boutique")
async def fruit_marche_noir(interaction: discord.Interaction):
    await interaction.response.defer()
    player = await get_player(interaction.guild_id, interaction.user.id)
    if player is None:
        await interaction.followup.send("Tu n'as pas encore de personnage ! Lance `/commencer` pour débuter l'aventure 🏴‍☠️")
        return

    dispo = await get_fruits_disponibles(interaction.guild_id)
    if not dispo:
        await interaction.followup.send("Aucun Fruit du Démon disponible pour l'instant — ils sont tous déjà en possession de quelqu'un sur ce serveur.")
        return

    embed = discord.Embed(
        title="☠️ Marché noir des Fruits du Démon",
        description="Des marchands douteux proposent ces fruits, à prix d'or. Utilise `/fruit acheter` pour en acquérir un.",
        color=0x1A1A1A
    )
    for code, nom, categorie, description, bonus, prix, poids in dispo:
        emoji = CATEGORIE_EMOJIS.get(categorie, "🍈")
        embed.add_field(name=f"{emoji} {nom} — {prix:,}฿", value=f"{description} ({categorie})", inline=False)
    embed.set_footer(text="🌊 One Piece Bot • Fruits du Démon")
    await interaction.followup.send(embed=embed)


async def fruit_achat_autocomplete(interaction: discord.Interaction, current: str):
    dispo = await get_fruits_disponibles(interaction.guild_id)
    filtered = [f for f in dispo if current.lower() in f[1].lower()]
    return [app_commands.Choice(name=f"{f[1]} ({f[5]:,}฿)", value=f[0]) for f in filtered[:25]]

@fruit_group.command(name="acheter", description="Acheter et manger un Fruit du Démon au marché noir (très cher)")
@app_commands.describe(fruit="Le fruit à acheter")
@app_commands.autocomplete(fruit=fruit_achat_autocomplete)
@require_salon("salon_boutique")
async def fruit_acheter(interaction: discord.Interaction, fruit: str):
    await interaction.response.defer()
    player = await get_player(interaction.guild_id, interaction.user.id)
    if player is None:
        await interaction.followup.send("Tu n'as pas encore de personnage ! Lance `/commencer` pour débuter l'aventure 🏴‍☠️")
        return
    if player["fruit"]:
        await interaction.followup.send(f"⛔ Tu as déjà mangé **{player['fruit']}** ! Manger un second fruit est bien trop risqué...")
        return

    fruit_data = get_fruit(fruit)
    if not fruit_data:
        await interaction.followup.send("Fruit introuvable.")
        return
    code, nom, categorie, description, bonus, prix, poids = fruit_data

    if player["berrys"] < prix:
        await interaction.followup.send(f"⛔ **{nom}** coûte **{prix:,}฿**, tu n'as que {player['berrys']:,}฿.")
        return

    ok = await manger_fruit(interaction.guild_id, interaction.user.id, code)
    if not ok:
        await interaction.followup.send("⛔ Ce fruit vient d'être pris par quelqu'un d'autre, ou n'est plus disponible.")
        return

    pool = get_pool()
    async with pool.acquire() as conn:
        await conn.execute("UPDATE players SET berrys = berrys - $3 WHERE guild_id=$1 AND user_id=$2", interaction.guild_id, interaction.user.id, prix)

    emoji = CATEGORIE_EMOJIS.get(categorie, "🍈")
    embed = discord.Embed(
        title=f"{emoji} Fruit dévoré !",
        description=f"Tu manges **{nom}** sans hésiter... {description}\n\nSes pouvoirs sont désormais tiens, mais tu ne pourras plus jamais nager !",
        color=0x8E44AD
    )
    embed.set_footer(text=f"🌊 One Piece Bot • -{prix:,}฿ • Fruits du Démon")
    await interaction.followup.send(embed=embed)


def setup_fruit_commands(bot):
    bot.tree.add_command(fruit_group)
