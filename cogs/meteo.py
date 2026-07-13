import discord
from discord import app_commands
from discord.ext import tasks
from utils.meteo import get_current_weather, rotate_weather, get_meteo_info

@app_commands.command(name="meteo", description="Voir la météo actuelle sur le serveur")
async def meteo(interaction: discord.Interaction):
    await interaction.response.defer()
    nom = await get_current_weather(interaction.guild_id)
    emoji, description = get_meteo_info(nom)
    embed = discord.Embed(title=f"{emoji} Météo actuelle — {nom}", description=description, color=0x3498DB)
    embed.set_footer(text="🌊 One Piece Bot • La météo influence légèrement l'exploration et les voyages")
    await interaction.followup.send(embed=embed)


_bot_ref = None

@tasks.loop(hours=3)
async def meteo_rotation_loop():
    if _bot_ref is None:
        return
    for guild in _bot_ref.guilds:
        try:
            await rotate_weather(guild.id)
        except Exception as e:
            print(f"Erreur rotation météo ({guild.id}): {e}")


def start_meteo_loop(bot):
    global _bot_ref
    _bot_ref = bot
    if not meteo_rotation_loop.is_running():
        meteo_rotation_loop.start()


def setup_meteo_commands(bot):
    bot.tree.add_command(meteo)
