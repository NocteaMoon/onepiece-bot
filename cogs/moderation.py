import discord
from discord import app_commands
import datetime
from database.db import get_pool
from utils.permissions import has_group_permission
from utils.logging import log_action

mod_group = app_commands.Group(name="mod", description="Commandes de modération")

async def check_mod(interaction: discord.Interaction) -> bool:
    allowed = await has_group_permission(interaction, "mod")
    if not allowed:
        await interaction.followup.send("⛔ Tu n'as pas la permission d'utiliser cette commande.", ephemeral=True)
    return allowed

@mod_group.command(name="ban", description="Bannir un membre")
async def mod_ban(interaction: discord.Interaction, membre: discord.Member, raison: str = "Aucune raison fournie"):
    await interaction.response.defer(ephemeral=True)
    if not await check_mod(interaction):
        return
    try:
        await membre.ban(reason=raison)
    except discord.Forbidden:
        await interaction.followup.send("❌ Je n'ai pas la permission de bannir ce membre (vérifie la hiérarchie des rôles).", ephemeral=True)
        return
    await log_action(interaction.guild, "Bannissement", interaction.user, membre, raison)
    await interaction.followup.send(f"🔨 {membre.mention} a été banni. Raison : {raison}", ephemeral=True)

@mod_group.command(name="kick", description="Expulser un membre")
async def mod_kick(interaction: discord.Interaction, membre: discord.Member, raison: str = "Aucune raison fournie"):
    await interaction.response.defer(ephemeral=True)
    if not await check_mod(interaction):
        return
    try:
        await membre.kick(reason=raison)
    except discord.Forbidden:
        await interaction.followup.send("❌ Je n'ai pas la permission d'expulser ce membre (vérifie la hiérarchie des rôles).", ephemeral=True)
        return
    await log_action(interaction.guild, "Expulsion", interaction.user, membre, raison)
    await interaction.followup.send(f"👢 {membre.mention} a été expulsé. Raison : {raison}", ephemeral=True)

@mod_group.command(name="timeout", description="Réduire un membre au silence temporairement")
@app_commands.describe(minutes="Durée en minutes")
async def mod_timeout(interaction: discord.Interaction, membre: discord.Member, minutes: int, raison: str = "Aucune raison fournie"):
    await interaction.response.defer(ephemeral=True)
    if not await check_mod(interaction):
        return
    duree = datetime.timedelta(minutes=minutes)
    try:
        await membre.timeout(duree, reason=raison)
    except discord.Forbidden:
        await interaction.followup.send("❌ Je n'ai pas la permission de mettre ce membre en timeout.", ephemeral=True)
        return
    await log_action(interaction.guild, f"Timeout ({minutes} min)", interaction.user, membre, raison)
    await interaction.followup.send(f"🔇 {membre.mention} est en timeout pour {minutes} minutes. Raison : {raison}", ephemeral=True)

@mod_group.command(name="unmute", description="Retirer le timeout d'un membre")
async def mod_unmute(interaction: discord.Interaction, membre: discord.Member):
    await interaction.response.defer(ephemeral=True)
    if not await check_mod(interaction):
        return
    await membre.timeout(None)
    await log_action(interaction.guild, "Fin de timeout", interaction.user, membre)
    await interaction.followup.send(f"🔊 Le timeout de {membre.mention} a été retiré.", ephemeral=True)

@mod_group.command(name="warn", description="Avertir un membre")
async def mod_warn(interaction: discord.Interaction, membre: discord.Member, raison: str):
    await interaction.response.defer(ephemeral=True)
    if not await check_mod(interaction):
        return
    pool = get_pool()
    async with pool.acquire() as conn:
        await conn.execute(
            "INSERT INTO warnings (guild_id, user_id, moderator_id, reason) VALUES ($1, $2, $3, $4)",
            interaction.guild_id, membre.id, interaction.user.id, raison
        )
    await log_action(interaction.guild, "Avertissement", interaction.user, membre, raison)
    await interaction.followup.send(f"⚠️ {membre.mention} a été averti. Raison : {raison}", ephemeral=True)

@mod_group.command(name="unwarn", description="Retirer un avertissement d'un membre")
@app_commands.describe(membre="Le membre concerné", id="ID précis de l'avertissement (optionnel, sinon retire le plus récent)")
async def mod_unwarn(interaction: discord.Interaction, membre: discord.Member, id: int = None):
    await interaction.response.defer(ephemeral=True)
    if not await check_mod(interaction):
        return
    pool = get_pool()
    async with pool.acquire() as conn:
        if id is not None:
            result = await conn.execute("DELETE FROM warnings WHERE id = $1 AND guild_id = $2 AND user_id = $3", id, interaction.guild_id, membre.id)
            if result.endswith(" 0"):
                await interaction.followup.send(f"❌ Aucun avertissement #{id} trouvé pour {membre.mention}.", ephemeral=True)
                return
            await interaction.followup.send(f"✅ Avertissement #{id} supprimé pour {membre.mention}.", ephemeral=True)
        else:
            row = await conn.fetchrow("SELECT id FROM warnings WHERE guild_id = $1 AND user_id = $2 ORDER BY created_at DESC LIMIT 1", interaction.guild_id, membre.id)
            if not row:
                await interaction.followup.send(f"{membre.mention} n'a aucun avertissement.", ephemeral=True)
                return
            await conn.execute("DELETE FROM warnings WHERE id = $1", row["id"])
            await interaction.followup.send(f"✅ Dernier avertissement (#{row['id']}) supprimé pour {membre.mention}.", ephemeral=True)

@mod_group.command(name="historique", description="Voir les avertissements d'un membre")
async def mod_historique(interaction: discord.Interaction, membre: discord.Member):
    await interaction.response.defer(ephemeral=True)
    if not await check_mod(interaction):
        return
    pool = get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch("SELECT id, reason, created_at FROM warnings WHERE guild_id = $1 AND user_id = $2 ORDER BY created_at DESC", interaction.guild_id, membre.id)
    if not rows:
        await interaction.followup.send(f"{membre.mention} n'a aucun avertissement.", ephemeral=True)
        return
    embed = discord.Embed(title=f"⚠️ Avertissements de {membre.display_name}", color=0x2C3E50)
    for r in rows:
        embed.add_field(name=f"#{r['id']} — {r['created_at'].strftime('%d/%m/%Y')}", value=r["reason"], inline=False)
    embed.set_footer(text="🌊 One Piece Bot • Modération")
    await interaction.followup.send(embed=embed, ephemeral=True)

@mod_group.command(name="clear", description="Supprimer un nombre de messages")
async def mod_clear(interaction: discord.Interaction, nombre: int):
    await interaction.response.defer(ephemeral=True)
    if not await check_mod(interaction):
        return
    try:
        deleted = await interaction.channel.purge(limit=nombre)
    except discord.Forbidden:
        await interaction.followup.send("❌ Je n'ai pas la permission de gérer les messages dans ce salon.", ephemeral=True)
        return
    except discord.HTTPException as e:
        await interaction.followup.send(f"❌ Erreur lors de la suppression : {e}", ephemeral=True)
        return
    await log_action(interaction.guild, f"Clear ({len(deleted)} messages)", interaction.user, interaction.channel)
    await interaction.followup.send(f"🧹 {len(deleted)} messages supprimés.", ephemeral=True)

@mod_group.command(name="lock", description="Verrouiller le salon actuel")
async def mod_lock(interaction: discord.Interaction):
    await interaction.response.defer(ephemeral=True)
    if not await check_mod(interaction):
        return
    try:
        await interaction.channel.set_permissions(interaction.guild.default_role, send_messages=False)
    except discord.Forbidden:
        await interaction.followup.send("❌ Je n'ai pas la permission de modifier ce salon.", ephemeral=True)
        return
    await log_action(interaction.guild, "Salon verrouillé", interaction.user, interaction.channel)
    await interaction.followup.send(
        "🔒 Salon verrouillé pour @everyone.\n"
        "⚠️ Si un membre peut toujours écrire, vérifie qu'aucun **autre rôle** n'a une permission explicite "
        "\"Envoyer des messages : Autorisé\" sur ce salon — cette autorisation passe devant le verrouillage général.",
        ephemeral=True
    )

@mod_group.command(name="unlock", description="Déverrouiller le salon actuel")
async def mod_unlock(interaction: discord.Interaction):
    await interaction.response.defer(ephemeral=True)
    if not await check_mod(interaction):
        return
    try:
        await interaction.channel.set_permissions(interaction.guild.default_role, send_messages=None)
    except discord.Forbidden:
        await interaction.followup.send("❌ Je n'ai pas la permission de modifier ce salon.", ephemeral=True)
        return
    await log_action(interaction.guild, "Salon déverrouillé", interaction.user, interaction.channel)
    await interaction.followup.send("🔓 Salon déverrouillé.", ephemeral=True)

@mod_group.command(name="slowmode", description="Définir le mode lent du salon (en secondes)")
async def mod_slowmode(interaction: discord.Interaction, secondes: int):
    await interaction.response.defer(ephemeral=True)
    if not await check_mod(interaction):
        return
    try:
        await interaction.channel.edit(slowmode_delay=secondes)
    except discord.Forbidden:
        await interaction.followup.send("❌ Je n'ai pas la permission de modifier ce salon.", ephemeral=True)
        return
    except discord.HTTPException as e:
        await interaction.followup.send(f"❌ Erreur : {e}", ephemeral=True)
        return
    await log_action(interaction.guild, f"Slowmode ({secondes}s)", interaction.user, interaction.channel)
    await interaction.followup.send(f"🐌 Mode lent défini à {secondes} secondes.", ephemeral=True)

def setup_moderation_commands(bot):
    bot.tree.add_command(mod_group)
