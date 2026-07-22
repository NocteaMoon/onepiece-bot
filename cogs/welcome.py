import discord
from discord.ext import commands
import aiohttp
from database.db import get_pool
from utils.welcome_card import generate_welcome_card

async def get_welcome_config(guild_id: int):
    pool = get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow("SELECT * FROM welcome_config WHERE guild_id = $1", guild_id)
        if row is None:
            await conn.execute("INSERT INTO welcome_config (guild_id) VALUES ($1)", guild_id)
            row = await conn.fetchrow("SELECT * FROM welcome_config WHERE guild_id = $1", guild_id)
    return row


def _format_message(template: str, member: discord.Member) -> str:
    return (
        template
        .replace("{mention}", member.mention)
        .replace("{pseudo}", member.display_name)
        .replace("{serveur}", member.guild.name)
        .replace("{nombre}", str(member.guild.member_count))
    )


class WelcomeVerifyView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="J'ai lu le règlement, je valide !", emoji="✅", style=discord.ButtonStyle.success, custom_id="welcome_verify")
    async def verify(self, interaction: discord.Interaction, button: discord.ui.Button):
        row = await get_welcome_config(interaction.guild_id)
        if not row["auto_role_id"]:
            await interaction.response.send_message("⚠️ Aucun rôle n'est configuré, contacte un administrateur.", ephemeral=True)
            return
        role = interaction.guild.get_role(row["auto_role_id"])
        if role is None:
            await interaction.response.send_message("⚠️ Le rôle configuré est introuvable.", ephemeral=True)
            return
        if role in interaction.user.roles:
            await interaction.response.send_message("Tu es déjà vérifié ✅", ephemeral=True)
            return
        try:
            await interaction.user.add_roles(role, reason="Vérification règlement")
        except discord.Forbidden:
            await interaction.response.send_message("❌ Je n'ai pas la permission de te donner ce rôle.", ephemeral=True)
            return
        await interaction.response.send_message("✅ Bienvenue à bord, tu es maintenant vérifié !", ephemeral=True)


class WelcomeListener(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        pool = get_pool()
        async with pool.acquire() as conn:
            guild_row = await conn.fetchrow("SELECT salon_bienvenue FROM guild_config WHERE guild_id = $1", member.guild.id)
        if not guild_row or not guild_row["salon_bienvenue"]:
            return
        channel = member.guild.get_channel(guild_row["salon_bienvenue"])
        if not channel:
            return

        row = await get_welcome_config(member.guild.id)

        background_bytes = None
        if row["background_url"]:
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.get(row["background_url"]) as resp:
                        if resp.status == 200:
                            background_bytes = await resp.read()
            except Exception:
                background_bytes = None

        try:
            avatar_bytes = await member.display_avatar.replace(size=256, format="png").read()
            image_buffer = generate_welcome_card(avatar_bytes, member.display_name, member.guild.member_count, background_bytes)
            file = discord.File(image_buffer, filename="bienvenue.png")
        except Exception:
            file = None

        content = _format_message(row["message"], member)

        try:
            if file:
                await channel.send(content=content, file=file)
            else:
                await channel.send(content=content)
        except discord.Forbidden:
            pass

        if not row["verification_enabled"] and row["auto_role_id"]:
            role = member.guild.get_role(row["auto_role_id"])
            if role:
                try:
                    await member.add_roles(role, reason="Rôle automatique de bienvenue")
                except discord.Forbidden:
                    pass


async def setup_welcome_commands(bot):
    await bot.add_cog(WelcomeListener(bot))
