import discord
from discord import app_commands
from database.db import get_pool
from utils.players import get_player
from utils.channel_check import require_salon
from data.iles import ILES

COUT_ENDURANCE_DEBARQUER = 5

async def ile_autocomplete(interaction: discord.Interaction, current: str):
    player = await get_player(interaction.guild_id, interaction.user.id)
    if player is None:
        return []
    iles_mer = ILES.get(player["mer"], [])
    dispo = [nom for nom, _ in iles_mer if nom != player["ile"]]
    filtered = [n for n in dispo if current.lower() in n.lower()]
    return [app_commands.Choice(name=n, value=n) for n in filtered[:25]]


@app_commands.command(name="debarquer", description="Changer d'île au sein de ta mer actuelle")
@app_commands.describe(ile="L'île où débarquer")
@app_commands.autocomplete(ile=ile_autocomplete)
@require_salon("salon_exploration")
async def debarquer(interaction: discord.Interaction, ile: str):
    await interaction.response.defer()
    player = await get_player(interaction.guild_id, interaction.user.id)
    if player is None:
        await interaction.followup.send("Tu n'as pas encore de personnage ! Lance `/commencer` pour débuter l'aventure 🏴‍☠️")
        return

    iles_mer = ILES.get(player["mer"], [])
    noms_valides = {nom for nom, _ in iles_mer}
    if ile not in noms_valides:
        await interaction.followup.send(f"⛔ Cette île ne fait pas partie de **{player['mer']}**.")
        return
    if ile == player["ile"]:
        await interaction.followup.send(f"Tu es déjà sur **{ile}** !")
        return
    if player["endurance"] < COUT_ENDURANCE_DEBARQUER:
        await interaction.followup.send(f"😮‍💨 Il te faut {COUT_ENDURANCE_DEBARQUER} endurance pour débarquer ailleurs (tu as {player['endurance']}).")
        return

    description = next((desc for nom, desc in iles_mer if nom == ile), "")

    pool = get_pool()
    async with pool.acquire() as conn:
        await conn.execute(
            "UPDATE players SET ile = $3, endurance = endurance - $4 WHERE guild_id=$1 AND user_id=$2",
            interaction.guild_id, interaction.user.id, ile, COUT_ENDURANCE_DEBARQUER
        )

    embed = discord.Embed(title=f"⛵ Débarquement — {ile}", description=description, color=0x1B3A5C)
    embed.set_footer(text=f"🌊 One Piece Bot • {player['mer']}")
    await interaction.followup.send(embed=embed)


@app_commands.command(name="carte", description="Voir où tu te trouves et les îles accessibles")
@require_salon("salon_exploration")
async def carte(interaction: discord.Interaction):
    await interaction.response.defer()
    player = await get_player(interaction.guild_id, interaction.user.id)
    if player is None:
        await interaction.followup.send("Tu n'as pas encore de personnage ! Lance `/commencer` pour débuter l'aventure 🏴‍☠️")
        return

    iles_mer = ILES.get(player["mer"], [])
    description_actuelle = next((desc for nom, desc in iles_mer if nom == player["ile"]), "")

    embed = discord.Embed(
        title=f"🗺️ {player['mer']} — {player['ile']}",
        description=description_actuelle or "Une île mystérieuse, encore mal cartographiée...",
        color=0x1B3A5C
    )

    autres = [nom for nom, _ in iles_mer if nom != player["ile"]]
    if autres:
        embed.add_field(name="Autres îles accessibles (via /debarquer)", value="\n".join(f"• {n}" for n in autres), inline=False)
    embed.set_footer(text="🌊 One Piece Bot • Carte du monde")
    await interaction.followup.send(embed=embed)


def setup_monde_commands(bot):
    bot.tree.add_command(debarquer)
    bot.tree.add_command(carte)
