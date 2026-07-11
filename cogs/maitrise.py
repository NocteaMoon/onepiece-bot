import discord
from discord import app_commands
from utils.players import get_player
from utils.maitrise import LABELS, COLONNES, PLAFOND_MAITRISE

@app_commands.command(name="maitrise", description="Voir tes maîtrises d'armes")
@app_commands.describe(membre="Le membre dont tu veux voir les maîtrises (toi par défaut)")
async def maitrise_voir(interaction: discord.Interaction, membre: discord.Member = None):
    await interaction.response.defer()
    cible = membre or interaction.user
    player = await get_player(interaction.guild_id, cible.id)
    if player is None:
        await interaction.followup.send("Tu n'as pas encore de personnage ! Lance `/commencer` pour débuter l'aventure 🏴‍☠️")
        return

    embed = discord.Embed(title=f"⚔️ Maîtrises d'armes de {cible.display_name}", color=0x2C3E50)
    for type_arme, colonne in COLONNES.items():
        valeur = player[colonne] or 0
        embed.add_field(name=LABELS[type_arme], value=f"{valeur}/{PLAFOND_MAITRISE}", inline=True)
    embed.set_footer(text="🌊 One Piece Bot • Progresse automatiquement en combattant avec l'arme équipée")
    await interaction.followup.send(embed=embed)


def setup_maitrise_commands(bot):
    bot.tree.add_command(maitrise_voir)
