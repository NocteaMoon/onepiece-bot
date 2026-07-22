import discord
from discord.ext import commands
from database.db import get_pool
from utils.logging import log_event

TYPES_LOGS = [
    ("Messages supprimés", "log_msg_delete"),
    ("Messages édités", "log_msg_edit"),
    ("Entrées / sorties de membres", "log_join_leave"),
    ("Création / suppression de salons", "log_salons"),
    ("Création / suppression de rôles", "log_roles"),
    ("Changements de pseudo", "log_pseudos"),
]

async def get_logs_config(guild_id: int):
    pool = get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow("SELECT * FROM logs_config WHERE guild_id = $1", guild_id)
        if row is None:
            await conn.execute("INSERT INTO logs_config (guild_id) VALUES ($1)", guild_id)
            row = await conn.fetchrow("SELECT * FROM logs_config WHERE guild_id = $1", guild_id)
    return row


class ServerLogsListener(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_message_delete(self, message: discord.Message):
        if not message.guild or message.author.bot:
            return
        config = await get_logs_config(message.guild.id)
        if not config["log_msg_delete"]:
            return
        await log_event(message.guild, "🗑️ Message supprimé", [
            ("Auteur", str(message.author)),
            ("Salon", message.channel.mention),
            ("Contenu", message.content[:1000] if message.content else "*(pas de texte, ou image/fichier)*"),
        ], color=0xC0392B)

    @commands.Cog.listener()
    async def on_message_edit(self, before: discord.Message, after: discord.Message):
        if not before.guild or before.author.bot or before.content == after.content:
            return
        config = await get_logs_config(before.guild.id)
        if not config["log_msg_edit"]:
            return
        await log_event(before.guild, "✏️ Message édité", [
            ("Auteur", str(before.author)),
            ("Salon", before.channel.mention),
            ("Avant", before.content[:500] if before.content else "—"),
            ("Après", after.content[:500] if after.content else "—"),
        ], color=0xF39C12)

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        config = await get_logs_config(member.guild.id)
        if not config["log_join_leave"]:
            return
        await log_event(member.guild, "📥 Arrivée d'un membre", [
            ("Membre", str(member)),
            ("Compte créé le", member.created_at.strftime("%d/%m/%Y")),
        ], color=0x27AE60, thumbnail=member.display_avatar.url)

    @commands.Cog.listener()
    async def on_member_remove(self, member: discord.Member):
        config = await get_logs_config(member.guild.id)
        if not config["log_join_leave"]:
            return
        await log_event(member.guild, "📤 Départ d'un membre", [
            ("Membre", str(member)),
        ], color=0xC0392B, thumbnail=member.display_avatar.url)

    @commands.Cog.listener()
    async def on_guild_channel_create(self, channel: discord.abc.GuildChannel):
        config = await get_logs_config(channel.guild.id)
        if not config["log_salons"]:
            return
        await log_event(channel.guild, "➕ Salon créé", [
            ("Nom", channel.name),
            ("Type", str(channel.type)),
        ], color=0x27AE60)

    @commands.Cog.listener()
    async def on_guild_channel_delete(self, channel: discord.abc.GuildChannel):
        config = await get_logs_config(channel.guild.id)
        if not config["log_salons"]:
            return
        await log_event(channel.guild, "➖ Salon supprimé", [
            ("Nom", channel.name),
            ("Type", str(channel.type)),
        ], color=0xC0392B)

    @commands.Cog.listener()
    async def on_guild_role_create(self, role: discord.Role):
        config = await get_logs_config(role.guild.id)
        if not config["log_roles"]:
            return
        await log_event(role.guild, "➕ Rôle créé", [
            ("Nom", role.name),
        ], color=0x27AE60)

    @commands.Cog.listener()
    async def on_guild_role_delete(self, role: discord.Role):
        config = await get_logs_config(role.guild.id)
        if not config["log_roles"]:
            return
        await log_event(role.guild, "➖ Rôle supprimé", [
            ("Nom", role.name),
        ], color=0xC0392B)

    @commands.Cog.listener()
    async def on_member_update(self, before: discord.Member, after: discord.Member):
        if before.nick == after.nick:
            return
        config = await get_logs_config(before.guild.id)
        if not config["log_pseudos"]:
            return
        await log_event(before.guild, "✏️ Changement de pseudo", [
            ("Membre", str(before)),
            ("Avant", before.nick or before.name),
            ("Après", after.nick or after.name),
        ], color=0xF39C12)

async def setup_serverlogs_commands(bot):
    await bot.add_cog(ServerLogsListener(bot))
