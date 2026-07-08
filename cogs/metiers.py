import discord
from discord import app_commands
from database.db import get_pool
from utils.players import get_player
from utils.metiers import METIERS_DISPONIBLES, get_rang, rang_label

metier_group = app_commands.Group(name="metier", description="Choisir et suivre ton métier (réservé aux Civils)")

METIER_CHOICES = [app_commands.Choice(name=m, value=m) for m in METIERS_DISPONIBLES]

@metier_group.command(name="choisir", description="Choisir un métier (réservé à la faction Civil)")
@app_commands.choices(metier=METIER_CHOICES)
async def metier_choisir(interaction: discord.Interaction, metier: app_commands.Choice[str]):
    await interaction.response.defer()
    player = await get_player(interaction.guild_id, interaction.user.id)
    if player is None:
        await interaction.followup.send("Tu n'as pas encore de personnage ! Lance `/commencer` pour débuter l'aventure 🏴‍☠️")
        return
    if player["faction"] != "Civil":
        await interaction.followup.send("⛔ Les métiers sont réservés à la faction **Civil**. Les autres factions doivent acheter les objets élaborés aux Civils sur le marché !")
        return
    if player["metier"] == metier.value:
        await interaction.followup.send(f"Tu es déjà **{metier.value}** !")
        return

    pool = get_pool()
    async with pool.acquire() as conn:
        await conn.execute(
            "UPDATE players SET metier = $3, metier_xp = 0, metier_rang = 0 WHERE guild_id=$1 AND user_id=$2",
            interaction.guild_id, interaction.user.id, metier.value
        )
    embed = discord.Embed(
        title="🔧 Nouveau métier !",
        description=f"{interaction.user.mention} devient **{metier.value}** ! (Rang : Apprenti)",
        color=0x8E44AD
    )
    embed.set_footer(text="🌊 One Piece Bot • Métiers")
    await interaction.followup.send(embed=embed)


@metier_group.command(name="voir", description="Voir ta progression de métier")
@app_commands.describe(membre="Le membre dont tu veux voir le métier (toi par défaut)")
async def metier_voir(interaction: discord.Interaction, membre: discord.Member = None):
    await interaction.response.defer()
    cible = membre or interaction.user
    player = await get_player(interaction.guild_id, cible.id)
    if player is None:
        await interaction.followup.send(f"{cible.display_name} n'a pas encore de personnage.")
        return
    if not player["metier"]:
        await interaction.followup.send(f"{cible.display_name} n'a pas encore de métier.")
        return

    rang = get_rang(player["metier_xp"])
    embed = discord.Embed(title=f"🔧 Métier de {cible.display_name}", color=0x8E44AD)
    embed.add_field(name="Métier", value=player["metier"], inline=True)
    embed.add_field(name="Rang", value=rang_label(rang), inline=True)
    embed.add_field(name="XP Métier", value=str(player["metier_xp"]), inline=True)
    embed.set_footer(text="🌊 One Piece Bot • Métiers")
    await interaction.followup.send(embed=embed)


def setup_metiers_commands(bot):
    bot.tree.add_command(metier_group)
