import discord
from discord import app_commands
from database.db import get_pool
from utils.players import get_player
from utils.channel_check import require_salon
from utils.haki import is_on_cooldown, entrainer_haki, COUT_ENDURANCE

haki_group = app_commands.Group(name="haki", description="Entraîner et consulter ton Haki")

TYPE_CHOICES = [
    app_commands.Choice(name="Armement (renforce tes attaques)", value="armement"),
    app_commands.Choice(name="Observation (renforce ton esquive)", value="observation"),
]

TYPE_LABELS = {"armement": "Armement", "observation": "Observation"}


@haki_group.command(name="voir", description="Voir ton niveau de Haki")
@app_commands.describe(membre="Le membre dont tu veux voir le Haki (toi par défaut)")
async def haki_voir(interaction: discord.Interaction, membre: discord.Member = None):
    await interaction.response.defer()
    cible = membre or interaction.user
    player = await get_player(interaction.guild_id, cible.id)
    if player is None:
        await interaction.followup.send("Tu n'as pas encore de personnage ! Lance `/commencer` pour débuter l'aventure 🏴‍☠️")
        return

    embed = discord.Embed(title=f"🌊 Haki de {cible.display_name}", color=0x2C3E50)
    embed.add_field(name="⚔️ Armement", value=f"{player['haki_armement']}/10", inline=True)
    embed.add_field(name="👁️ Observation", value=f"{player['haki_observation']}/10", inline=True)
    rois_texte = "✨ Éveillé !" if player["haki_rois"] and player["haki_rois"] > 0 else "Non éveillé (extrêmement rare, se déclenche au hasard en combat)"
    embed.add_field(name="👑 Rois", value=rois_texte, inline=False)
    embed.set_footer(text="🌊 One Piece Bot • Haki")
    await interaction.followup.send(embed=embed)


@haki_group.command(name="entrainer", description="S'entraîner pour progresser en Haki (Armement ou Observation)")
@app_commands.describe(type="Le type de Haki à entraîner")
@app_commands.choices(type=TYPE_CHOICES)
@require_salon("salon_entrainement")
async def haki_entrainer(interaction: discord.Interaction, type: app_commands.Choice[str]):
    await interaction.response.defer()
    player = await get_player(interaction.guild_id, interaction.user.id)
    if player is None:
        await interaction.followup.send("Tu n'as pas encore de personnage ! Lance `/commencer` pour débuter l'aventure 🏴‍☠️")
        return

    restant = is_on_cooldown(interaction.guild_id, interaction.user.id)
    if restant is not None:
        await interaction.followup.send(f"😮‍💨 Tu dois encore attendre **{restant} min** avant de t'entraîner à nouveau.")
        return
    if player["endurance"] < COUT_ENDURANCE:
        await interaction.followup.send(f"😮‍💨 Il te faut {COUT_ENDURANCE} endurance pour t'entraîner (tu as {player['endurance']}).")
        return

    pool = get_pool()
    async with pool.acquire() as conn:
        await conn.execute("UPDATE players SET endurance = endurance - $3 WHERE guild_id=$1 AND user_id=$2", interaction.guild_id, interaction.user.id, COUT_ENDURANCE)

    progres = await entrainer_haki(interaction.guild_id, interaction.user.id, type.value)

    if progres:
        embed = discord.Embed(
            title="🌊 Percée !",
            description=f"Ta concentration porte ses fruits : ton Haki **{TYPE_LABELS[type.value]}** progresse d'un cran !",
            color=0x27AE60
        )
    else:
        embed = discord.Embed(
            title="🌊 Entraînement difficile",
            description="Tu t'entraînes dur, mais cette fois ta concentration n'a pas suffi à progresser.",
            color=0x95A5A6
        )
    embed.set_footer(text="🌊 One Piece Bot • Haki")
    await interaction.followup.send(embed=embed)


def setup_haki_commands(bot):
    bot.tree.add_command(haki_group)
