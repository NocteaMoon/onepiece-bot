import discord
from discord import app_commands
from discord.ext import commands
import aiohttp
from database.db import get_pool
from utils.welcome_card import generate_welcome_card

welcome_group = app_commands.Group(
    name="bienvenue",
    description="Configurer le système de bienvenue",
    parent=None
)

async def get_welcome_config(guild_id: int):
    pool = get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow("SELECT * FROM welcome_config WHERE guild_id = $1", guild_id)
        if row is None:
            await conn.execute("INSERT INTO welcome_config (guild_id) VALUES ($1)", guild_id)
            row = await conn.fetchrow("SELECT * FROM welcome_config WHERE guild_id = $1", guild_id)
    return row

@welcome_group.command(name="message", description="Définir le message de bienvenue")
@app_commands.describe(texte="Utilise {mention}, {pseudo}, {serveur}, {nombre} comme variables")
async def bienvenue_message(interaction: discord.Interaction, texte: str):
    await get_welcome_config(interaction.guild_id)
    pool = get_pool()
    async with pool.acquire() as conn:
        await conn.execute("UPDATE welcome_config SET message = $2 WHERE guild_id = $1", interaction.guild_id, texte)
    await interaction.response.send_message("✅ Message de bienvenue mis à jour.", ephemeral=True)

@welcome_group.command(name="role", description="Définir le rôle attribué automatiquement à l'arrivée ou via la vérification")
async def bienvenue_role(interaction: discord.Interaction, role: discord.Role):
    await get_welcome_config(interaction.guild_id)
    pool = get_pool()
    async with pool.acquire() as conn:
        await conn.execute("UPDATE welcome_config SET auto_role_id = $2 WHERE guild_id = $1", interaction.guild_id, role.id)
    await interaction.response.send_message(f"✅ Rôle automatique défini sur {role.mention}", ephemeral=True)

@welcome_group.command(name="verification", description="Activer/désactiver la vérification (rôle via bouton au lieu d'automatique)")
@app_commands.choices(etat=[
    app_commands.Choice(name="Activé (le membre doit cliquer sur le bouton du panneau règlement)", value="on"),
    app_commands.Choice(name="Désactivé (rôle donné automatiquement à l'arrivée)", value="off"),
])
async def bienvenue_verification(interaction: discord.Interaction, etat: app_commands.Choice[str]):
    await get_welcome_config(interaction.guild_id)
    pool = get_pool()
    async with pool.acquire() as conn:
        await conn.execute("UPDATE welcome_config SET verification_enabled = $2 WHERE guild_id = $1", interaction.guild_id, etat.value == "on")
    await interaction.response.send_message(f"✅ Vérification **{etat.name}**", ephemeral=True)

@welcome_group.command(name="fond", description="Définir une image de fond personnalisée pour la carte de bienvenue")
@app_commands.describe(image="Upload une image (laisse vide pour revenir au fond sombre par défaut)")
async def bienvenue_fond(interaction: discord.Interaction, image: discord.Attachment = None):
    await get_welcome_config(interaction.guild_id)
    pool = get_pool()
    url = image.url if image else None
    async with pool.acquire() as conn:
        await conn.execute("UPDATE welcome_config SET background_url = $2 WHERE guild_id = $1", interaction.guild_id, url)
    if url:
        await interaction.response.send_message("✅ Image de fond personnalisée définie.", ephemeral=True)
    else:
        await interaction.response.send_message("✅ Retour au fond sombre par défaut.", ephemeral=True)

@welcome_group.command(name="panneau-verification", description="Poster le bouton de vérification dans ce salon (sous ton règlement)")
async def bienvenue_panneau(interaction: discord.Interaction):
    row = await get_welcome_config(interaction.guild_id)
    if not row["auto_role_id"]:
        await interaction.response.send_message("⚠️ Configure d'abord un rôle avec `/config bienvenue role`.", ephemeral=True)
        return
    await interaction.channel.send(view=WelcomeVerifyView())
    await interaction.response.send_message("✅ Panneau de vérification posté dans ce salon.", ephemeral=True)

@welcome_group.command(name="voir", description="Voir la configuration de bienvenue actuelle")
async def bienvenue_voir(interaction: discord.Interaction):
    row = await get_welcome_config(interaction.guild_id)
    embed = discord.Embed(title="👋 Configuration Bienvenue", color=0x27AE60)
    embed.add_field(name="Message", value=row["message"], inline=False)
    role = interaction.guild.get_role(row["auto_role_id"]) if row["auto_role_id"] else None
    embed.add_field(name="Rôle automatique", value=role.mention if role else "Non défini", inline=True)
    embed.add_field(name="Vérification", value="🟢 Activée" if row["verification_enabled"] else "🔴 Désactivée", inline=True)
    embed.add_field(name="Fond personnalisé", value="🟢 Oui" if row["background_url"] else "🔴 Non (fond sombre par défaut)", inline=True)
    embed.set_footer(text="🌊 One Piece Bot • Bienvenue")
    await interaction.response.send_message(embed=embed, ephemeral=True)

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

async def setup_welcome_commands(bot, parent_group):
    welcome_group.parent = None
    parent_group.add_command(welcome_group)
    await bot.add_cog(WelcomeListener(bot))
