import discord
from discord import app_commands
import random
import datetime
from database.db import get_pool
from utils.players import get_player
from data.secrets_legende import LEGENDES

COOLDOWN_HEURES = 20
GAIN_MIN, GAIN_MAX = 30, 70

_last_legende = {}

@app_commands.command(name="legende", description="???")
async def legende(interaction: discord.Interaction):
    await interaction.response.defer()
    player = await get_player(interaction.guild_id, interaction.user.id)
    if player is None:
        await interaction.followup.send("Tu n'as pas encore de personnage ! Lance `/commencer` pour débuter l'aventure 🏴‍☠️")
        return

    key = (interaction.guild_id, interaction.user.id)
    now = datetime.datetime.utcnow()
    last = _last_legende.get(key)
    if last:
        elapsed = (now - last).total_seconds() / 3600
        if elapsed < COOLDOWN_HEURES:
            restant = round(COOLDOWN_HEURES - elapsed, 1)
            await interaction.followup.send(f"🤫 Cette légende s'est déjà racontée récemment... reviens dans environ **{restant}h**.")
            return

    _last_legende[key] = now
    texte = random.choice(LEGENDES)
    gain = random.randint(GAIN_MIN, GAIN_MAX)

    pool = get_pool()
    async with pool.acquire() as conn:
        await conn.execute("UPDATE players SET berrys = berrys + $3 WHERE guild_id=$1 AND user_id=$2", interaction.guild_id, interaction.user.id, gain)

    embed = discord.Embed(
        title="🕯️ Une légende oubliée...",
        description=f"{texte}\n\nEn remerciement de ton écoute, on te glisse discrètement **{gain}฿**.",
        color=0x2C3E50
    )
    await interaction.followup.send(embed=embed)


def setup_secrets_commands(bot):
    bot.tree.add_command(legende)
