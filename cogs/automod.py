import discord
from discord.ext import commands
import re
import time
from database.db import get_pool
from utils.permissions import member_has_group
from utils.logging import log_action

async def get_config(guild_id: int):
    pool = get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow("SELECT * FROM automod_config WHERE guild_id = $1", guild_id)
        if row is None:
            await conn.execute("INSERT INTO automod_config (guild_id) VALUES ($1)", guild_id)
            row = await conn.fetchrow("SELECT * FROM automod_config WHERE guild_id = $1", guild_id)
    return row


BAD_WORDS = ["connard", "encule", "pute", "batard", "salope", "pd", "negre", "abruti"]
URL_PATTERN = re.compile(r"(https?://|www\.)\S+", re.IGNORECASE)
INVITE_PATTERN = re.compile(r"(discord\.gg/|discord\.com/invite/)\S+", re.IGNORECASE)

_spam_tracker = {}
_raid_tracker = {}

class AutomodListener(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot or not message.guild:
            return
        if await member_has_group(message.author, "mod"):
            return

        row = await get_config(message.guild.id)

        if row["anti_pub"] and INVITE_PATTERN.search(message.content):
            await self._delete_and_warn(message, "Anti-pub", "Lien d'invitation Discord détecté")
            return

        if row["anti_liens"] and URL_PATTERN.search(message.content):
            await self._delete_and_warn(message, "Anti-liens", "Lien détecté")
            return

        if row["anti_insultes"]:
            lowered = message.content.lower()
            if any(word in lowered for word in BAD_WORDS):
                await self._delete_and_warn(message, "Anti-insultes", "Langage inapproprié détecté")
                return

        if row["anti_mention"]:
            contient_everyone_here = (
                "@everyone" in message.content
                or "@here" in message.content
                or message.mention_everyone
            )
            if contient_everyone_here:
                await self._delete_and_warn(message, "Anti-mention", "Mention @everyone/@here interdite pour les membres")
                return

            nb_mentions = len(message.mentions) + len(message.role_mentions)
            if nb_mentions > row["mention_limit"]:
                await self._delete_and_warn(message, "Anti-mention", f"Trop de mentions ({nb_mentions})")
                return

        if row["anti_spam"]:
            key = (message.guild.id, message.author.id)
            now = time.time()
            history = _spam_tracker.setdefault(key, [])
            history.append(now)
            window = row["spam_seconds"]
            _spam_tracker[key] = [t for t in history if now - t <= window]
            if len(_spam_tracker[key]) > row["spam_msg_limit"]:
                _spam_tracker[key] = []
                try:
                    await message.delete()
                except discord.HTTPException:
                    pass
                try:
                    import datetime
                    await message.author.timeout(datetime.timedelta(seconds=60), reason="Anti-spam automatique")
                except discord.Forbidden:
                    pass
                await log_action(message.guild, "Anti-spam", self.bot.user, message.author, "Spam détecté, timeout 60s appliqué")

    async def _delete_and_warn(self, message: discord.Message, protection: str, raison: str):
        try:
            await message.delete()
        except discord.HTTPException:
            pass
        await log_action(message.guild, protection, self.bot.user, message.author, raison)

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        if member.guild is None:
            return
        row = await get_config(member.guild.id)

        if row["anti_bot"] and member.bot:
            try:
                await member.kick(reason="Anti-bot automatique")
            except discord.Forbidden:
                pass
            await log_action(member.guild, "Anti-bot", self.bot.user, member, "Bot non autorisé expulsé")
            return

        if row["anti_alt"] and not member.bot:
            import datetime
            age_days = (datetime.datetime.now(datetime.timezone.utc) - member.created_at).days
            if age_days < row["alt_min_days"]:
                try:
                    await member.kick(reason="Anti-alt automatique (compte trop récent)")
                except discord.Forbidden:
                    pass
                await log_action(member.guild, "Anti-alt", self.bot.user, member, f"Compte créé il y a {age_days} jour(s), minimum {row['alt_min_days']}")
                return

        if row["anti_raid"]:
            key = member.guild.id
            now = time.time()
            history = _raid_tracker.setdefault(key, [])
            history.append(now)
            window = row["raid_seconds"]
            _raid_tracker[key] = [t for t in history if now - t <= window]
            if len(_raid_tracker[key]) > row["raid_join_limit"]:
                try:
                    await member.kick(reason="Anti-raid automatique")
                except discord.Forbidden:
                    pass
                await log_action(member.guild, "Anti-raid", self.bot.user, member, "Vague d'arrivées suspecte détectée")

async def setup_automod_commands(bot):
    await bot.add_cog(AutomodListener(bot))
