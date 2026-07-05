import discord
from discord import app_commands
from database.db import get_pool
from utils.permissions import require_group
from utils.logging import log_action

mod_group = app_commands.Group(name="mod", description="Commandes de modération")

@mod_group.command(name="ban", description="Bannir un membre")
@require_group("mod")
async def mod_ban(interaction: discord.Interaction, membre: discord.Member, raison: str = "Aucune raison fournie"):
    await membre.ban(reason=raison)
    await log_action(interaction.guild, "Bannissement", interaction.user, membre, raison)
    await interaction.response.send_message(f"🔨 {membre.mention} a été banni. Raison : {raison}", ephemeral=True)

@mod_group.command(name="kick", description="Expulser un membre")
@require_group("mod")
async def mod_kick(interaction: discord.Interaction, membre: discord.Member, raison: str = "Aucune raison fournie"):
    await membre.kick(reason=raison)
    await log_action(interaction.guild, "Expulsion", interaction.user, membre, raison)
    await interaction.response.send_message(f"👢 {membre.mention} a été expulsé. Raison : {raison}", ephemeral=True)

@mod_group.command(name="timeout", description="Réduire un membre au silence temporairement")
@app_commands.describe(minutes="Durée en minutes")
@require_group("mod")
async def mod_timeout(interaction: discord.Interaction, membre: discord.Member, minutes: int, raison: str = "Aucune raison fournie"):
    import datetime
    duree = datetime.timedelta(minutes=minutes)
    await membre.timeout(duree, reason=raison)
    await log_action(interaction.guild, f"Timeout ({minutes} min)", interaction.user, membre, raison)
    await interaction.response.send_message(f"🔇 {membre.mention} est en timeout pour {minutes} minutes. Raison : {raison}", ephemeral=True)

@mod_group.command(name="unmute", description="Retirer le timeout d'un membre")
@require_group("mod")
async def mod_unmute(interaction: discord.Interaction, membre: discord.Member):
    await membre.timeout(None)
    await log_action(interaction.guild, "Fin de timeout", interaction.user, membre)
    await interaction.response.send_message(f"🔊 Le timeout de {membre.mention} a été retiré.", ephemeral=True)

@mod_group.command(name="warn", description="Avertir un membre")
@require_group("mod")
async def mod_warn(interaction: discord.Interaction, membre: discord.Member, raison: str):
    pool = get_pool()
    async with pool.acquire() as conn:
        await conn.execute(
            "INSERT INTO warnings (guild_id, user_id, moderator_id, reason) VALUES ($1, $2, $3, $4)",
            interaction.guild_id, membre.id, interaction.user.id, raison
        )
    await log_action(interaction.guild, "Avertissement", interaction.user, membre, raison)
    await interaction.response.send_message(f"⚠️ {membre.mention} a été averti. Raison : {raison}", ephemeral=True)

@mod_group.command(name="unwarn", description="Retirer un avertissement par son ID")
@require_group("mod")
async def mod_unwarn(interaction: discord.Interaction, warning_id: int):
    pool = get_pool()
    async with pool.acquire() as conn:
        result = await conn.execute("DELETE FROM warnings WHERE id = $1 AND guild_id = $2", warning_id, interaction.guild_id)
    await interaction.response.send_message(f"✅ Avertissement #{warning_id} supprimé.", ephemeral=True)

@mod_group.command(name="historique", description="Voir les avertissements d'un membre")
@require_group("mod")
async def mod_historique(interaction: discord.Interaction, membre: discord.Member):
    pool = get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch("SELECT id, reason, created_at FROM warnings WHERE guild_id = $1 AND user_id = $2 ORDER BY created_at DESC", interaction.guild_id, membre.id)
    if not rows:
        await interaction.response.send_message(f"{membre.mention} n'a aucun avertissement.", ephemeral=True)
        return
    embed = discord.Embed(title=f"⚠️ Avertissements de {membre.display_name}", color=0x2C3E50)
    for r in rows:
        embed.add_field(name=f"#{r['id']} — {r['created_at'].strftime('%d/%m/%Y')}", value=r["reason"], inline=False)
    embed.set_footer(text="🌊 One Piece Bot • Modération")
    await interaction.response.send_message(embed=embed, ephemeral=True)

@mod_group.command(name="clear", description="Supprimer un nombre de messages")
@require_group("mod")
async def mod_clear(interaction: discord.Interaction, nombre: int):
    await interaction.response.defer(ephemeral=True)
    deleted = await interaction.channel.purge(limit=nombre)
    await log_action(interaction.guild, f"Clear ({len(deleted)} messages)", interaction.user, interaction.channel)
    await interaction.followup.send(f"🧹 {len(deleted)} messages supprimés.", ephemeral=True)

@mod_group.command(name="lock", description="Verrouiller le salon actuel")
@require_group("mod")
async def mod_lock(interaction: discord.Interaction):
    await interaction.channel.set_permissions(interaction.guild.default_role, send_messages=False)
    await log_action(interaction.guild, "Salon verrouillé", interaction.user, interaction.channel)
    await interaction.response.send_message("🔒 Salon verrouillé.", ephemeral=True)

@mod_group.command(name="unlock", description="Déverrouiller le salon actuel")
@require_group("mod")
async def mod_unlock(interaction: discord.Interaction):
    await interaction.channel.set_permissions(interaction.guild.default_role, send_messages=True)
    await log_action(interaction.guild, "Salon déverrouillé", interaction.user, interaction.channel)
    await interaction.response.send_message("🔓 Salon déverrouillé.", ephemeral=True)

@mod_group.command(name="slowmode", description="Définir le mode lent du salon (en secondes)")
@require_group("mod")
async def mod_slowmode(interaction: discord.Interaction, secondes: int):
    await interaction.channel.edit(slowmode_delay=secondes)
    await log_action(interaction.guild, f"Slowmode ({secondes}s)", interaction.user, interaction.channel)
    await interaction.response.send_message(f"🐌 Mode lent défini à {secondes} secondes.", ephemeral=True)

def setup_moderation_commands(bot):
    bot.tree.add_command(mod_group)
