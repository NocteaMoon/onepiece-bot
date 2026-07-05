import discord
from discord import app_commands
from database.db import get_pool

config_group = app_commands.Group(name="config", description="Configuration du bot pour ce serveur")

SALON_CHOICES = [
    app_commands.Choice(name="Annonces", value="salon_annonces"),
    app_commands.Choice(name="Logs", value="salon_logs"),
    app_commands.Choice(name="Modération", value="salon_moderation"),
    app_commands.Choice(name="Économie", value="salon_economie"),
    app_commands.Choice(name="Mini-jeux", value="salon_minijeux"),
    app_commands.Choice(name="Équipages", value="salon_equipages"),
    app_commands.Choice(name="Rapports", value="salon_rapports"),
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
    embed = discord.Embed(title="⚙️ Configuration du serveur", color=discord.Color.blue())
    embed.add_field(name="Langue", value=row["lang"], inline=False)
    for key, label in [
        ("salon_annonces", "Annonces"), ("salon_logs", "Logs"),
        ("salon_moderation", "Modération"), ("salon_economie", "Économie"),
        ("salon_minijeux", "Mini-jeux"), ("salon_equipages", "Équipages"),
        ("salon_rapports", "Rapports"),
    ]:
        val = row[key]
        embed.add_field(name=label, value=f"<#{val}>" if val else "Non défini", inline=True)
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
