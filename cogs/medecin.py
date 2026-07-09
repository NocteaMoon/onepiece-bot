import discord
from discord import app_commands
import datetime
from database.db import get_pool
from utils.players import get_player, add_xp
from utils.metiers import get_rang
from utils.channel_check import require_salon

COUT_ENDURANCE = 15
COOLDOWNS_PAR_RANG = {0: 20, 1: 15, 2: 10}

_last_soin = {}

@app_commands.command(name="soigner", description="Soigner un joueur : PV restaurés et K.O. levé (réservé aux Médecins)")
@app_commands.describe(membre="Le joueur à soigner (toi par défaut)")
@require_salon("salon_taverne")
async def soigner(interaction: discord.Interaction, membre: discord.Member = None):
    await interaction.response.defer()
    soigneur = await get_player(interaction.guild_id, interaction.user.id)
    if soigneur is None:
        await interaction.followup.send("Tu n'as pas encore de personnage ! Lance `/commencer` pour débuter l'aventure 🏴‍☠️")
        return
    if soigneur["metier"] != "Médecin":
        await interaction.followup.send("⛔ Tu dois être **Médecin** pour soigner quelqu'un ! Choisis ce métier avec `/metier choisir` (réservé aux Civils).")
        return
    if soigneur["endurance"] < COUT_ENDURANCE:
        await interaction.followup.send(f"😮‍💨 Il te faut {COUT_ENDURANCE} endurance pour ça (tu as {soigneur['endurance']}).")
        return

    cible = membre or interaction.user
    cible_data = await get_player(interaction.guild_id, cible.id)
    if cible_data is None:
        await interaction.followup.send(f"{cible.display_name} n'a pas encore de personnage.")
        return

    rang = get_rang(soigneur["metier_xp"])
    cooldown_minutes = COOLDOWNS_PAR_RANG.get(rang, 20)
    key = (interaction.guild_id, interaction.user.id)
    now = datetime.datetime.utcnow()
    last = _last_soin.get(key)
    if last:
        elapsed = (now - last).total_seconds() / 60
        if elapsed < cooldown_minutes:
            restant = int(cooldown_minutes - elapsed)
            await interaction.followup.send(f"😮‍💨 Tu dois encore attendre **{restant} min** avant de pouvoir soigner à nouveau.")
            return

    pool = get_pool()
    async with pool.acquire() as conn:
        async with conn.transaction():
            await conn.execute(
                "UPDATE players SET endurance = endurance - $3, metier_xp = metier_xp + 20 WHERE guild_id=$1 AND user_id=$2",
                interaction.guild_id, interaction.user.id, COUT_ENDURANCE
            )
            await conn.execute(
                "UPDATE players SET pv = pv_max, ko_jusqua = NULL WHERE guild_id=$1 AND user_id=$2",
                interaction.guild_id, cible.id
            )

    _last_soin[key] = now
    await add_xp(interaction.guild_id, interaction.user.id, 8, 4)

    embed = discord.Embed(
        title="💊 Soins prodigués !",
        description=f"{cible.mention} est remis(e) sur pied : PV entièrement restaurés, K.O. levé.",
        color=0x27AE60
    )
    embed.set_footer(text="🌊 One Piece Bot • Guilde des métiers")
    await interaction.followup.send(embed=embed)


def setup_medecin_commands(bot):
    bot.tree.add_command(soigner)
