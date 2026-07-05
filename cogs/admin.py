import discord
from discord import app_commands
from database.db import get_pool

config_group = app_commands.Group(name="config", description="Configuration du bot pour ce serveur")

SALON_CHOICES = [
    app_commands.Choice(name="Annonces", value="salon_annonces"),
    app_commands.Choice(name="Règlement", value="salon_reglement"),
    app_commands.Choice(name="Bienvenue", value="salon_bienvenue"),
    app_commands.Choice(name="Logs", value="salon_logs"),
    app_commands.Choice(name="Modération", value="salon_moderation"),
    app_commands.Choice(name="Rapports", value="salon_rapports"),
    app_commands.Choice(name="Général", value="salon_general"),
    app_commands.Choice(name="Économie", value="salon_economie"),
    app_commands.Choice(name="Boutique", value="salon_boutique"),
    app_commands.Choice(name="Exploration", value="salon_exploration"),
    app_commands.Choice(name="Combat", value="salon_combat"),
    app_commands.Choice(name="Duel / PvP", value="salon_duel"),
    app_commands.Choice(name="Pêche-Chasse-Récolte", value="salon_peche"),
    app_commands.Choice(name="Casino", value="salon_casino"),
    app_commands.Choice(name="Équipages", value="salon_equipages"),
    app_commands.Choice(name="Marine", value="salon_marine"),
    app_commands.Choice(name="Révolutionnaires", value="salon_revolutionnaires"),
    app_commands.Choice(name="Classements", value="salon_classements"),
    app_commands.Choice(name="Quêtes / Événements", value="salon_quetes"),
    app_commands.Choice(name="Succès", value="salon_succes"),
]

@config_group.command(name="salon", description="Définir un salon pour une fonctionnalité")
@app_commands.describe(type="Le type de salon à configurer", salon="Le salon à utiliser")
@app_commands.choices(type=SALON_CHOICES)
@app_commands.checks.has_permissions(administrator=True)
async def config_salon(interaction: discord.Interaction, type: app_commands.Choice[str], salon: discord.TextChannel):
    pool = get_pool()
    async with pool.acquire() as conn:
        await conn.execute(f"""
            INSERT INTO guild_config (guild_id, {type.value})
            VALUES ($1, $2)
            ON CONFLICT (guild_id) DO UPDATE SET {type.value} = $2
        """, interaction.guild_id, salon.id)
    await interaction.response.send_message(f"✅ Salon **{type.name}** défini sur {salon.mention}", ephemeral=True)

@config_group.command(name="lang", description="Définir la langue du bot pour ce serveur")
@app_commands.choices(langue=[
    app_commands.Choice(name="Français", value="fr"),
    app_commands.Choice(name="English", value="en"),
])
@app_commands.checks.has_permissions(administrator=True)
async def config_lang(interaction: discord.Interaction, langue: app_commands.Choice[str]):
    pool = get_pool()
    async with pool.acquire() as conn:
        await conn.execute("""
            INSERT INTO guild_config (guild_id, lang)
            VALUES ($1, $2)
            ON CONFLICT (guild_id) DO UPDATE SET lang = $2
        """, interaction.guild_id, langue.value)
    await interaction.response.send_message(f"✅ Langue définie sur **{langue.name}**", ephemeral=True)

@config_group.command(name="voir", description="Afficher la configuration actuelle du serveur")
@app_commands.checks.has_permissions(administrator=True)
async def config_voir(interaction: discord.Interaction):
    pool = get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow("SELECT * FROM guild_config WHERE guild_id = $1", interaction.guild_id)
    if row is None:
        await interaction.response.send_message("Aucune configuration trouvée pour ce serveur.", ephemeral=True)
        return

    embed = discord.Embed(title="⚙️ Configuration du serveur", color=0x2C3E50)
    embed.add_field(name="Langue", value=row["lang"], inline=False)
    for choice in SALON_CHOICES:
        val = row[choice.value]
        embed.add_field(name=choice.name, value=f"<#{val}>" if val else "Non défini", inline=True)
    embed.set_footer(text="🌊 One Piece Bot • Configuration")
    await interaction.response.send_message(embed=embed, ephemeral=True)

@config_group.command(name="reset", description="Réinitialiser toute la configuration du serveur")
@app_commands.checks.has_permissions(administrator=True)
async def config_reset(interaction: discord.Interaction):
    pool = get_pool()
    async with pool.acquire() as conn:
        await conn.execute("DELETE FROM guild_config WHERE guild_id = $1", interaction.guild_id)
    await interaction.response.send_message("🔄 Configuration réinitialisée.", ephemeral=True)

def setup_admin_commands(bot):
    bot.tree.add_command(config_group)
