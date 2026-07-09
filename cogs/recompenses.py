import discord
from discord import app_commands
import random
import datetime
from database.db import get_pool
from utils.players import get_player, add_xp
from utils.shop import get_item_by_name
from utils.channel_check import require_salon
from utils.announcements import announce_level_up

recompenses_group = app_commands.Group(name="recompenses", description="Récompenses régulières : quotidienne, hebdomadaire, mensuelle")


@recompenses_group.command(name="quotidienne", description="Réclamer ta récompense quotidienne")
@require_salon("salon_recompenses")
async def quotidienne(interaction: discord.Interaction):
    await interaction.response.defer()
    player = await get_player(interaction.guild_id, interaction.user.id)
    if player is None:
        await interaction.followup.send("Tu n'as pas encore de personnage ! Lance `/commencer` pour débuter l'aventure 🏴‍☠️")
        return

    now = datetime.datetime.utcnow()
    last = player["last_daily"]
    streak = player["daily_streak"]

    if last:
        elapsed_hours = (now - last).total_seconds() / 3600
        if elapsed_hours < 24:
            restant = int(24 - elapsed_hours)
            await interaction.followup.send(f"😮‍💨 Tu as déjà réclamé ta récompense aujourd'hui. Reviens dans **{restant}h**.")
            return
        if elapsed_hours <= 48:
            streak = min(7, streak + 1)
        else:
            streak = 1
    else:
        streak = 1

    base = random.randint(20, 50)
    bonus_streak = (streak - 1) * 5
    gain = base + bonus_streak

    pool = get_pool()
    async with pool.acquire() as conn:
        await conn.execute(
            "UPDATE players SET berrys = berrys + $3, last_daily = $4, daily_streak = $5 WHERE guild_id=$1 AND user_id=$2",
            interaction.guild_id, interaction.user.id, gain, now, streak
        )
    niveaux_gagnes, nouveau_niveau = await add_xp(interaction.guild_id, interaction.user.id, 10, 4)

    embed = discord.Embed(
        title="🎁 Récompense quotidienne !",
        description=f"Tu reçois **{gain}฿** !\n🔥 Série actuelle : **{streak} jour(s)** consécutif(s)",
        color=0xF4C430
    )
    if streak < 7:
        embed.set_footer(text=f"🌊 One Piece Bot • Reviens demain pour augmenter ta série (max +35฿ au 7ème jour)")
    else:
        embed.set_footer(text="🌊 One Piece Bot • Série maximale atteinte !")
    await interaction.followup.send(embed=embed)

    if niveaux_gagnes > 0:
        await announce_level_up(interaction, interaction.user, nouveau_niveau)


@recompenses_group.command(name="hebdomadaire", description="Réclamer ta récompense hebdomadaire")
@require_salon("salon_recompenses")
async def hebdomadaire(interaction: discord.Interaction):
    await interaction.response.defer()
    player = await get_player(interaction.guild_id, interaction.user.id)
    if player is None:
        await interaction.followup.send("Tu n'as pas encore de personnage ! Lance `/commencer` pour débuter l'aventure 🏴‍☠️")
        return

    now = datetime.datetime.utcnow()
    last = player["last_weekly"]
    if last:
        elapsed_days = (now - last).total_seconds() / 86400
        if elapsed_days < 7:
            restant = int(7 - elapsed_days)
            await interaction.followup.send(f"😮‍💨 Tu as déjà réclamé ta récompense cette semaine. Reviens dans **{restant} jour(s)**.")
            return

    gain = random.randint(150, 250)
    pool = get_pool()
    async with pool.acquire() as conn:
        await conn.execute(
            "UPDATE players SET berrys = berrys + $3, last_weekly = $4 WHERE guild_id=$1 AND user_id=$2",
            interaction.guild_id, interaction.user.id, gain, now
        )
    niveaux_gagnes, nouveau_niveau = await add_xp(interaction.guild_id, interaction.user.id, 30, 12)

    embed = discord.Embed(
        title="🎁 Récompense hebdomadaire !",
        description=f"Tu reçois **{gain}฿** !",
        color=0xF4C430
    )
    embed.set_footer(text="🌊 One Piece Bot • Récompenses")
    await interaction.followup.send(embed=embed)

    if niveaux_gagnes > 0:
        await announce_level_up(interaction, interaction.user, nouveau_niveau)


@recompenses_group.command(name="mensuelle", description="Réclamer ta récompense mensuelle")
@require_salon("salon_recompenses")
async def mensuelle(interaction: discord.Interaction):
    await interaction.response.defer()
    player = await get_player(interaction.guild_id, interaction.user.id)
    if player is None:
        await interaction.followup.send("Tu n'as pas encore de personnage ! Lance `/commencer` pour débuter l'aventure 🏴‍☠️")
        return

    now = datetime.datetime.utcnow()
    last = player["last_monthly"]
    if last:
        elapsed_days = (now - last).total_seconds() / 86400
        if elapsed_days < 30:
            restant = int(30 - elapsed_days)
            await interaction.followup.send(f"😮‍💨 Tu as déjà réclamé ta récompense ce mois-ci. Reviens dans **{restant} jour(s)**.")
            return

    gain = random.randint(500, 800)
    item = None
    if random.random() < 0.25:
        item = await get_item_by_name(interaction.guild_id, "Poisson légendaire des abysses")

    pool = get_pool()
    async with pool.acquire() as conn:
        async with conn.transaction():
            await conn.execute(
                "UPDATE players SET berrys = berrys + $3, last_monthly = $4 WHERE guild_id=$1 AND user_id=$2",
                interaction.guild_id, interaction.user.id, gain, now
            )
            if item:
                existing = await conn.fetchrow(
                    "SELECT id FROM inventory WHERE guild_id=$1 AND user_id=$2 AND item_id=$3",
                    interaction.guild_id, interaction.user.id, item["id"]
                )
                if existing:
                    await conn.execute("UPDATE inventory SET quantite = quantite + 1 WHERE id=$1", existing["id"])
                else:
                    await conn.execute(
                        "INSERT INTO inventory (guild_id, user_id, item_id, quantite, durabilite) VALUES ($1,$2,$3,1,$4)",
                        interaction.guild_id, interaction.user.id, item["id"], item["durabilite_max"]
                    )

    niveaux_gagnes, nouveau_niveau = await add_xp(interaction.guild_id, interaction.user.id, 80, 30)

    description = f"Tu reçois **{gain}฿** !"
    if item:
        description += f"\n🎉 Bonus rare : **{item['nom']}** !"

    embed = discord.Embed(title="🎁 Récompense mensuelle !", description=description, color=0xF4C430)
    embed.set_footer(text="🌊 One Piece Bot • Récompenses")
    await interaction.followup.send(embed=embed)

    if niveaux_gagnes > 0:
        await announce_level_up(interaction, interaction.user, nouveau_niveau)


def setup_recompenses_commands(bot):
    bot.tree.add_command(recompenses_group)
