import discord
from discord import app_commands
from utils.players import get_player
from utils.titres import get_titres_debloques, equip_titre

titre_group = app_commands.Group(name="titre", description="Gérer tes titres débloqués")

async def titre_autocomplete(interaction: discord.Interaction, current: str):
    titres = await get_titres_debloques(interaction.guild_id, interaction.user.id)
    filtered = [t for t in titres if current.lower() in t.lower()]
    return [app_commands.Choice(name=t, value=t) for t in filtered[:25]]

@titre_group.command(name="choisir", description="Équiper un titre parmi ceux débloqués")
@app_commands.describe(titre="Le titre à équiper")
@app_commands.autocomplete(titre=titre_autocomplete)
async def titre_choisir(interaction: discord.Interaction, titre: str):
    await interaction.response.defer()
    player = await get_player(interaction.guild_id, interaction.user.id)
    if player is None:
        await interaction.followup.send("Tu n'as pas encore de personnage ! Lance `/commencer` pour débuter l'aventure 🏴‍☠️")
        return
    ok = await equip_titre(interaction.guild_id, interaction.user.id, titre)
    if not ok:
        await interaction.followup.send("⛔ Tu n'as pas débloqué ce titre.")
        return
    await interaction.followup.send(f"✅ Titre équipé : **{titre}**")


@titre_group.command(name="voir", description="Voir tous tes titres débloqués")
async def titre_voir(interaction: discord.Interaction):
    await interaction.response.defer()
    player = await get_player(interaction.guild_id, interaction.user.id)
    if player is None:
        await interaction.followup.send("Tu n'as pas encore de personnage ! Lance `/commencer` pour débuter l'aventure 🏴‍☠️")
        return
    titres = await get_titres_debloques(interaction.guild_id, interaction.user.id)
    if not titres:
        await interaction.followup.send("Tu n'as encore débloqué aucun titre.")
        return
    lignes = [f"{'👉 ' if t == player['titre'] else ''}{t}" for t in titres]
    embed = discord.Embed(title="🎖️ Tes titres débloqués", description="\n".join(lignes), color=0xD4A017)
    embed.set_footer(text="🌊 One Piece Bot • Titres")
    await interaction.followup.send(embed=embed)


def setup_titre_commands(bot):
    bot.tree.add_command(titre_group)
