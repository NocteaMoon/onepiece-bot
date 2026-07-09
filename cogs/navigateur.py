import discord
from discord import app_commands
import datetime
from database.db import get_pool
from utils.players import get_player, add_xp
from utils.metiers import get_rang
from utils.channel_check import require_salon

COUT_ENDURANCE = 15
COOLDOWNS_PAR_RANG = {0: 20, 1: 15, 2: 10}
VOYAGES_OFFERTS_PAR_RANG = {0: 1, 1: 2, 2: 3}

_last_route = {}

@app_commands.command(name="route_sure", description="Garantir un trajet sans risque au prochain voyage d'un joueur (réservé aux Navigateurs)")
@app_commands.describe(membre="Le joueur à aider (toi par défaut)")
@require_salon("salon_taverne")
async def route_sure(interaction: discord.Interaction, membre: discord.Member = None):
    await interaction.response.defer()
    navigateur = await get_player(interaction.guild_id, interaction.user.id)
    if navigateur is None:
        await interaction.followup.send("Tu n'as pas encore de personnage ! Lance `/commencer` pour débuter l'aventure 🏴‍☠️")
        return
    if navigateur["metier"] != "Navigateur":
        await interaction.followup.send("⛔ Tu dois être **Navigateur** pour tracer une route sûre ! Choisis ce métier avec `/metier choisir` (réservé aux Civils).")
        return
    if navigateur["endurance"] < COUT_ENDURANCE:
        await interaction.followup.send(f"😮‍💨 Il te faut {COUT_ENDURANCE} endurance pour ça (tu as {navigateur['endurance']}).")
        return

    cible = membre or interaction.user
    cible_data = await get_player(interaction.guild_id, cible.id)
    if cible_data is None:
        await interaction.followup.send(f"{cible.display_name} n'a pas encore de personnage.")
        return

    rang = get_rang(navigateur["metier_xp"])
    cooldown_minutes = COOLDOWNS_PAR_RANG.get(rang, 20)
    nb_voyages = VOYAGES_OFFERTS_PAR_RANG.get(rang, 1)

    key = (interaction.guild_id, interaction.user.id)
    now = datetime.datetime.utcnow()
    last = _last_route.get(key)
    if last:
        elapsed = (now - last).total_seconds() / 60
        if elapsed < cooldown_minutes:
            restant = int(cooldown_minutes - elapsed)
            await interaction.followup.send(f"😮‍💨 Tu dois encore attendre **{restant} min** avant de retracer une route.")
            return

    pool = get_pool()
    async with pool.acquire() as conn:
        async with conn.transaction():
            await conn.execute(
                "UPDATE players SET endurance = endurance - $3, metier_xp = metier_xp + 20 WHERE guild_id=$1 AND user_id=$2",
                interaction.guild_id, interaction.user.id, COUT_ENDURANCE
            )
            await conn.execute(
                "UPDATE players SET voyage_protege = voyage_protege + $3 WHERE guild_id=$1 AND user_id=$2",
                interaction.guild_id, cible.id, nb_voyages
            )

    _last_route[key] = now
    await add_xp(interaction.guild_id, interaction.user.id, 8, 4)

    embed = discord.Embed(
        title="🧭 Route tracée !",
        description=f"{cible.mention} bénéficie de **{nb_voyages} voyage(s) sans risque** grâce à tes conseils avisés !",
        color=0x1B3A5C
    )
    embed.set_footer(text="🌊 One Piece Bot • Guilde des métiers")
    await interaction.followup.send(embed=embed)


def setup_navigateur_commands(bot):
    bot.tree.add_command(route_sure)
