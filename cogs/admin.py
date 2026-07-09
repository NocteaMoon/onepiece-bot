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
    app_commands.Choice(name="Taverne (défis annexes)", value="salon_taverne"),
    app_commands.Choice(name="Régates", value="salon_regates"),
    app_commands.Choice(name="Chasse au trésor", value="salon_tresor"),
]

@config_group.command(name="salon", description="Définir un salon pour une fonctionnalité")
@app_commands.describe(type="Le type de salon à configurer", salon="Le salon à utiliser")
@app_commands.choices(type=SALON_CHOICES)
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
async def config_reset(interaction: discord.Interaction):
    pool = get_pool()
    async with pool.acquire() as conn:
        await conn.execute("DELETE FROM guild_config WHERE guild_id = $1", interaction.guild_id)
    await interaction.response.send_message("🔄 Configuration réinitialisée.", ephemeral=True)


permission_group = app_commands.Group(name="permission", description="Gérer les permissions par rôle", parent=config_group)

COMMAND_GROUP_CHOICES = [
    app_commands.Choice(name="Modération", value="mod"),
]

@permission_group.command(name="autoriser", description="Autoriser un rôle à utiliser une catégorie de commandes")
@app_commands.choices(commande=COMMAND_GROUP_CHOICES)
async def permission_autoriser(interaction: discord.Interaction, commande: app_commands.Choice[str], role: discord.Role):
    pool = get_pool()
    async with pool.acquire() as conn:
        await conn.execute("""
            INSERT INTO guild_command_roles (guild_id, command_group, role_id)
            VALUES ($1, $2, $3)
            ON CONFLICT DO NOTHING
        """, interaction.guild_id, commande.value, role.id)
    await interaction.response.send_message(f"✅ Le rôle {role.mention} peut maintenant utiliser les commandes **{commande.name}**", ephemeral=True)

@permission_group.command(name="retirer", description="Retirer l'accès d'un rôle à une catégorie de commandes")
@app_commands.choices(commande=COMMAND_GROUP_CHOICES)
async def permission_retirer(interaction: discord.Interaction, commande: app_commands.Choice[str], role: discord.Role):
    pool = get_pool()
    async with pool.acquire() as conn:
        await conn.execute("""
            DELETE FROM guild_command_roles WHERE guild_id = $1 AND command_group = $2 AND role_id = $3
        """, interaction.guild_id, commande.value, role.id)
    await interaction.response.send_message(f"✅ Accès retiré pour {role.mention} sur **{commande.name}**", ephemeral=True)

@permission_group.command(name="liste", description="Voir les rôles autorisés par catégorie")
async def permission_liste(interaction: discord.Interaction):
    pool = get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch("SELECT command_group, role_id FROM guild_command_roles WHERE guild_id = $1", interaction.guild_id)
    if not rows:
        await interaction.response.send_message("Aucune permission personnalisée définie.", ephemeral=True)
        return
    embed = discord.Embed(title="🔑 Permissions par rôle", color=0x2C3E50)
    embed.set_footer(text="🌊 One Piece Bot • Configuration")
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
    app_commands.Choice(name="Révolutionnaire", value="Révolutionnaire"),
    app_commands.Choice(name="Civil", value="Civil"),
]

@joueur_admin_group.command(name="faction", description="Forcer la faction d'un joueur (outil admin/test)")
@app_commands.describe(membre="Le joueur concerné", faction="La nouvelle faction")
@app_commands.choices(faction=FACTION_ADMIN_CHOICES)
async def joueur_faction(interaction: discord.Interaction, membre: discord.Member, faction: app_commands.Choice[str]):
    pool = get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow("SELECT equipage_id, metier FROM players WHERE guild_id=$1 AND user_id=$2", interaction.guild_id, membre.id)
        if row is None:
            await interaction.response.send_message(f"{membre.display_name} n'a pas encore de personnage.", ephemeral=True)
            return
        async with conn.transaction():
            # Quitter Pirate = quitter l'équipage (incohérent sinon)
            if row["equipage_id"] and faction.value != "Pirate":
                await conn.execute(
                    "UPDATE players SET equipage_id = NULL, grade_equipage = NULL WHERE guild_id=$1 AND user_id=$2",
                    interaction.guild_id, membre.id
                )
            # Quitter Civil = perdre le métier (réservé aux Civils)
            if row["
