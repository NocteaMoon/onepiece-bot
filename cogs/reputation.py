import discord
from discord import app_commands
from utils.players import get_player

@app_commands.command(name="reputation", description="Voir ta réputation, ta notoriété et ton respect d'équipage")
@app_commands.describe(membre="Le membre à consulter (toi par défaut)")
async def reputation(interaction: discord.Interaction, membre: discord.Member = None):
    await interaction.response.defer()
    cible = membre or interaction.user
    player = await get_player(interaction.guild_id, cible.id)
    if player is None:
        if cible == interaction.user:
            await interaction.followup.send("Tu n'as pas encore de personnage ! Lance `/commencer` pour débuter l'aventure 🏴‍☠️")
        else:
            await interaction.followup.send(f"{cible.display_name} n'a pas encore de personnage.")
        return

    embed = discord.Embed(title=f"🎭 Réputation de {cible.display_name}", color=0x2C3E50)
    embed.add_field(name="🏴‍☠️ Pirates", value=str(player["rep_pirates"]), inline=True)
    embed.add_field(name="⚓ Marine", value=str(player["rep_marine"]), inline=True)
    embed.add_field(name="🔥 Révolutionnaires", value=str(player["rep_revolutionnaires"]), inline=True)
    embed.add_field(name="🏘️ Civils", value=str(player["rep_civils"]), inline=True)
    embed.add_field(name="🛒 Marchands", value=str(player["rep_marchands"]), inline=True)
    embed.add_field(name="\u200b", value="\u200b", inline=True)
    embed.add_field(name="🌟 Notoriété", value=f"{player['notoriete']:,} pts", inline=True)
    embed.add_field(name="🏴‍☠️ Respect d'équipage", value=f"{player['respect_equipage']:,} pts", inline=True)
    embed.set_footer(text="🌊 One Piece Bot • Réputation")
    await interaction.followup.send(embed=embed)


def setup_reputation_commands(bot):
    bot.tree.add_command(reputation)
