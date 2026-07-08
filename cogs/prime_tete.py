import discord
from discord import app_commands
from database.db import get_pool
from utils.players import get_player

@app_commands.command(name="prime_tete", description="Afficher l'avis de recherche (prime) d'un pirate")
@app_commands.describe(membre="Le membre dont tu veux voir l'avis de recherche (toi par défaut)")
async def prime_tete(interaction: discord.Interaction, membre: discord.Member = None):
    await interaction.response.defer()
    cible = membre or interaction.user
    player = await get_player(interaction.guild_id, cible.id)
    if player is None:
        if cible == interaction.user:
            await interaction.followup.send("Tu n'as pas encore de personnage ! Lance `/commencer` pour débuter l'aventure 🏴‍☠️")
        else:
            await interaction.followup.send(f"{cible.display_name} n'a pas encore de personnage.")
        return

    pool = get_pool()
    navire_nom = "Aucun navire (voyage à la nage 🏊)"
    if player["equip_navire"]:
        async with pool.acquire() as conn:
            navire = await conn.fetchrow("SELECT nom FROM shop_items WHERE id = $1", player["equip_navire"])
        if navire:
            navire_nom = navire["nom"]

    equipage_texte = "Aventurier(ère) solitaire, sans équipage"
    if player["equipage_id"]:
        equipage_texte = f"Membre d'un équipage (ID {player['equipage_id']})"

    embed = discord.Embed(
        title="☠️ AVIS DE RECHERCHE ☠️",
        description=f"# {cible.display_name}",
        color=0x1A1A1A
    )
    embed.set_thumbnail(url=cible.display_avatar.url)
    embed.add_field(name="💰 Prime", value=f"**{player['prime']:,} ฿**", inline=False)
    embed.add_field(name="⛵ Navire", value=navire_nom, inline=True)
    embed.add_field(name="🏴‍☠️ Équipage", value=equipage_texte, inline=True)
    embed.add_field(name="🌊 Faction", value=player["faction"], inline=True)
    embed.set_footer(text="🌊 One Piece Bot • Avis de recherche officiel")
    await interaction.followup.send(embed=embed)


def setup_prime_tete_commands(bot):
    bot.tree.add_command(prime_tete)
