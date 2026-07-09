import discord
from discord import app_commands
from database.db import get_pool

config_group = app_commands.Group(
    name="config",
    description="Configuration du bot pour ce serveur",
    default_permissions=discord.Permissions(administrator=True)
)

SALON_CHOICES = [
    app_commands.Choice(name="Annonces", value="salon_annonces"),
    app_commands.Choice(name="Reglement", value="salon_reglement"),
    app_commands.Choice(name="Bienvenue", value="salon_bienvenue"),
    app_commands.Choice(name="Logs", value="salon_logs"),
    app_commands.Choice(name="Moderation", value="salon_moderation"),
    app_commands.Choice(name="Rapports", value="salon_rapports"),
    app_commands.Choice(name="General", value="salon_general"),
    app_commands.Choice(name="Economie", value="salon_economie"),
    app_commands.Choice(name="Boutique", value="salon_boutique"),
    app_commands.Choice(name="Exploration", value="salon_exploration"),
    app_commands.Choice(name="Combat", value="salon_combat"),
    app_commands.Choice(name="Duel / PvP", value="salon_duel"),
    app_commands.Choice(name="Peche-Chasse-Recolte", value="salon_peche"),
    app_commands.Choice(name="Casino", value="salon_casino"),
    app_commands.Choice(name="Equipages", value="salon_equipages"),
    app_commands.Choice(name="Marine", value="salon_marine"),
    app_commands.Choice(name="Revolutionnaires", value="salon_revolutionnaires"),
    app_commands.Choice(name="Classements", value="salon_classements"),
    app_commands.Choice(name="Quetes / Evenements", value="salon_quetes"),
    app_commands.Choice(name="Succes", value="salon_succes"),
    app_commands.Choice(name="Taverne (defis annexes)", value="salon_taverne"),
    app_commands.Choice(name="Regates", value="salon_regates"),
    app_commands.Choice(name="Chasse au tresor", value="salon_tresor"),
    app_commands.Choice(name="Creation de personnage", value="salon_creation"),
]

@config_group.command(name="salon", description="Definir un salon pour une fonctionnalite")
@app_commands.describe(type="Le type de salon a configurer", salon="Le salon a utiliser")
@app_commands.choices(type=SALON_CHOICES)
async def config_salon(interaction: discord.Interaction, type: app_commands.Choice[str], salon: discord.TextChannel):
    pool = get_pool()
    async with pool.acquire() as conn:
        await conn.execute(f"""
            INSERT INTO guild_config (guild_id, {type.value})
            VALUES ($1, $2)
            ON CONFLICT (guild_id) DO UPDATE SET {type.value} = $2
        """, interaction.guild_id, salon.id)
    await interaction.response.send_message(f"Salon {type.name} defini sur {salon.mention}", ephemeral=True)

@config_group.command(name="lang", description="Definir la langue du bot pour ce serveur")
@app_commands.choices(langue=[
    app_commands.Choice(name="Francais", value="fr"),
    app_commands.Choice(name="English", value="en"),
])
async def config_lang(interaction: discord.Interaction, langue: app_commands.Choice[str]):
    pool = get_pool()
    async with pool.acquire() as conn:
        await conn.execute("""
            INSERT INTO guild_config (guild_id, lang)
            VALUES ($1, $2)
            ON CONFLICT (guild_id) DO UPDATE SET lang = $2
        """, interaction.guild_id, langue.value)
    await interaction.response.send_message(f"Langue definie sur {langue.name}", ephemeral=True)

@config_group.command(name="voir", description="Afficher la configuration actuelle du serveur")
async def config_voir(interaction: discord.Interaction):
    pool = get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow("SELECT * FROM guild_config WHERE guild_id = $1", interaction.guild_id)
    if row is None:
        await interaction.response.send_message("Aucune configuration trouvee pour ce serveur.", ephemeral=True)
        return

    embed = discord.Embed(title="Configuration du serveur", color=0x2C3E50)
    embed.add_field(name="Langue", value=row["lang"], inline=False)
    for choice in SALON_CHOICES:
        val = row[choice.value]
        embed.add_field(name=choice.name, value=f"<#{val}>" if val else "Non defini", inline=True)
    embed.set_footer(text="One Piece Bot - Configuration")
    await interaction.response.send_message(embed=embed, ephemeral=True)

@config_group.command(name="reset", description="Reinitialiser toute la configuration du serveur")
async def config_reset(interaction: discord.Interaction):
    pool = get_pool()
    async with pool.acquire() as conn:
        await conn.execute("DELETE FROM guild_config WHERE guild_id = $1", interaction.guild_id)
    await interaction.response.send_message("Configuration reinitialisee.", ephemeral=True)


permission_group = app_commands.Group(name="permission", description="Gerer les permissions par role", parent=config_group)

COMMAND_GROUP_CHOICES = [
    app_commands.Choice(name="Moderation", value="mod"),
]

@permission_group.command(name="autoriser", description="Autoriser un role a utiliser une categorie de commandes")
@app_commands.choices(commande=COMMAND_GROUP_CHOICES)
async def permission_autoriser(interaction: discord.Interaction, commande: app_commands.Choice[str], role: discord.Role):
    pool = get_pool()
    async with pool.acquire() as conn:
        await conn.execute("""
            INSERT INTO guild_command_roles (guild_id, command_group, role_id)
            VALUES ($1, $2, $3)
            ON CONFLICT DO NOTHING
        """, interaction.guild_id, commande.value, role.id)
    await interaction.response.send_message(f"Le role {role.mention} peut maintenant utiliser les commandes {commande.name}", ephemeral=True)

@permission_group.command(name="retirer", description="Retirer l acces d un role a une categorie de commandes")
@app_commands.choices(commande=COMMAND_GROUP_CHOICES)
async def permission_retirer(interaction: discord.Interaction, commande: app_commands.Choice[str], role: discord.Role):
    pool = get_pool()
    async with pool.acquire() as conn:
        await conn.execute("""
            DELETE FROM guild_command_roles WHERE guild_id = $1 AND command_group = $2 AND role_id = $3
        """, interaction.guild_id, commande.value, role.id)
    await interaction.response.send_message(f"Acces retire pour {role.mention} sur {commande.name}", ephemeral=True)

@permission_group.command(name="liste", description="Voir les roles autorises par categorie")
async def permission_liste(interaction: discord.Interaction):
    pool = get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch("SELECT command_group, role_id FROM guild_command_roles WHERE guild_id = $1", interaction.guild_id)
    if not rows:
        await interaction.response.send_message("Aucune permission personnalisee definie.", ephemeral=True)
        return
    embed = discord.Embed(title="Permissions par role", color=0x2C3E50)
    embed.set_footer(text="One Piece Bot - Configuration")
    grouped = {}
    for r in rows:
        grouped.setdefault(r["command_group"], []).append(f"<@&{r['role_id']}>")
    for group, roles in grouped.items():
        embed.add_field(name=group, value=", ".join(roles), inline=False)
    await interaction.response.send_message(embed=embed, ephemeral=True)


joueur_admin_group = app_commands.Group(name="joueur", description="Outils admin sur les fiches joueurs", parent=config_group)

FACTION_ADMIN_CHOICES = [
    app_commands.Choice(name="Pirate", value="Pirate"),
    app_commands.Choice(name="Marine", value="Marine"),
    app_commands.Choice(name="Revolutionnaire", value="Révolutionnaire"),
    app_commands.Choice(name="Civil", value="Civil"),
]

@joueur_admin_group.command(name="faction", description="Forcer la faction d un joueur (outil admin/test)")
@app_commands.describe(membre="Le joueur concerne", faction="La nouvelle faction")
@app_commands.choices(faction=FACTION_ADMIN_CHOICES)
async def joueur_faction(interaction: discord.Interaction, membre: discord.Member, faction: app_commands.Choice[str]):
    pool = get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow("SELECT equipage_id, metier FROM players WHERE guild_id=$1 AND user_id=$2", interaction.guild_id, membre.id)
        if row is None:
            await interaction.response.send_message(f"{membre.display_name} n a pas encore de personnage.", ephemeral=True)
            return
        async with conn.transaction():
            # Leaving Pirate removes crew membership
            if row["equipage_id"] and faction.value != "Pirate":
                await conn.execute(
                    "UPDATE players SET equipage_id = NULL, grade_equipage = NULL WHERE guild_id=$1 AND user_id=$2",
                    interaction.guild_id, membre.id
                )
            # Leaving Civil removes profession progress
            if row["metier"] and faction.value != "Civil":
                await conn.execute(
                    "UPDATE players SET metier = NULL, metier_xp = 0, metier_rang = 0 WHERE guild_id=$1 AND user_id=$2",
                    interaction.guild_id, membre.id
                )
            await conn.execute("UPDATE players SET faction = $3 WHERE guild_id=$1 AND user_id=$2", interaction.guild_id, membre.id, faction.value)
    await interaction.response.send_message(f"Faction de {membre.mention} definie sur {faction.value}.", ephemeral=True)


def setup_admin_commands(bot):
    bot.tree.add_command(config_group)
