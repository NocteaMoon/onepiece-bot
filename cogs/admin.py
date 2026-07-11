import discord
from discord import app_commands
from database.db import get_pool
from cogs.boss_mondial import force_spawn_boss

config_group = app_commands.Group(
    name="config",
    description="Configuration du bot pour ce serveur",
    default_permissions=discord.Permissions(administrator=True)
)

SALON_DEFINITIONS = [
    ("Annonces", "salon_annonces"),
    ("Reglement", "salon_reglement"),
    ("Bienvenue", "salon_bienvenue"),
    ("Logs", "salon_logs"),
    ("Moderation", "salon_moderation"),
    ("Rapports", "salon_rapports"),
    ("General", "salon_general"),
    ("Economie", "salon_economie"),
    ("Boutique", "salon_boutique"),
    ("Exploration", "salon_exploration"),
    ("Combat", "salon_combat"),
    ("Duel / PvP", "salon_duel"),
    ("Peche-Chasse-Recolte", "salon_peche"),
    ("Casino", "salon_casino"),
    ("Equipages", "salon_equipages"),
    ("Marine", "salon_marine"),
    ("Revolutionnaires", "salon_revolutionnaires"),
    ("Classements", "salon_classements"),
    ("Quetes / Evenements", "salon_quetes"),
    ("Succes", "salon_succes"),
    ("Taverne (defis annexes)", "salon_taverne"),
    ("Regates", "salon_regates"),
    ("Chasse au tresor", "salon_tresor"),
    ("Creation de personnage", "salon_creation"),
    ("Guilde des metiers", "salon_guilde"),
    ("Carnet de bord (guide)", "salon_carnet"),
    ("Recompenses (daily/weekly/monthly)", "salon_recompenses"),
    ("Cartes a collectionner", "salon_cartes"),
]

async def salon_type_autocomplete(interaction: discord.Interaction, current: str):
    current_lower = current.lower()
    filtered = [(label, value) for label, value in SALON_DEFINITIONS if current_lower in label.lower()]
    return [app_commands.Choice(name=label, value=value) for label, value in filtered[:25]]

@config_group.command(name="salon", description="Definir un salon pour une fonctionnalite")
@app_commands.describe(type="Tape pour rechercher le type de salon", salon="Le salon a utiliser")
@app_commands.autocomplete(type=salon_type_autocomplete)
async def config_salon(interaction: discord.Interaction, type: str, salon: discord.TextChannel):
    valid_values = {value for _, value in SALON_DEFINITIONS}
    if type not in valid_values:
        await interaction.response.send_message("Type de salon invalide, choisis-en un dans la liste proposee par l autocompletion.", ephemeral=True)
        return

    pool = get_pool()
    async with pool.acquire() as conn:
        await conn.execute(f"""
            INSERT INTO guild_config (guild_id, {type})
            VALUES ($1, $2)
            ON CONFLICT (guild_id) DO UPDATE SET {type} = $2
        """, interaction.guild_id, salon.id)

    label = next((l for l, v in SALON_DEFINITIONS if v == type), type)
    await interaction.response.send_message(f"Salon {label} defini sur {salon.mention}", ephemeral=True)

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

    lignes = [f"**Langue** : {row['lang']}", ""]
    for label, value in SALON_DEFINITIONS:
        val = row[value]
        statut = f"<#{val}>" if val else "Non defini"
        lignes.append(f"**{label}** : {statut}")

    embed = discord.Embed(title="Configuration du serveur", description="\n".join(lignes), color=0x2C3E50)
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
            if row["equipage_id"] and faction.value != "Pirate":
                await conn.execute(
                    "UPDATE players SET equipage_id = NULL, grade_equipage = NULL WHERE guild_id=$1 AND user_id=$2",
                    interaction.guild_id, membre.id
                )
            if row["metier"] and faction.value != "Civil":
                await conn.execute(
                    "UPDATE players SET metier = NULL, metier_xp = 0, metier_rang = 0 WHERE guild_id=$1 AND user_id=$2",
                    interaction.guild_id, membre.id
                )
            await conn.execute("UPDATE players SET faction = $3 WHERE guild_id=$1 AND user_id=$2", interaction.guild_id, membre.id, faction.value)
    await interaction.response.send_message(f"Faction de {membre.mention} definie sur {faction.value}.", ephemeral=True)


@joueur_admin_group.command(name="reset", description="Reinitialiser completement la fiche d un joueur (outil admin/test)")
@app_commands.describe(membre="Le joueur a reinitialiser")
async def joueur_reset(interaction: discord.Interaction, membre: discord.Member):
    pool = get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow("SELECT * FROM players WHERE guild_id=$1 AND user_id=$2", interaction.guild_id, membre.id)
        if row is None:
            await interaction.response.send_message(f"{membre.display_name} n a pas de personnage a reinitialiser.", ephemeral=True)
            return

        async with conn.transaction():
            led_crews = await conn.fetch(
                "SELECT id, nom FROM crews WHERE guild_id=$1 AND capitaine_id=$2",
                interaction.guild_id, membre.id
            )
            for crew in led_crews:
                await conn.execute(
                    "UPDATE players SET equipage_id = NULL, grade_equipage = NULL WHERE guild_id=$1 AND equipage_id=$2",
                    interaction.guild_id, crew["id"]
                )
                await conn.execute("DELETE FROM crews WHERE id = $1", crew["id"])

            await conn.execute("DELETE FROM inventory WHERE guild_id=$1 AND user_id=$2", interaction.guild_id, membre.id)
            await conn.execute("DELETE FROM players WHERE guild_id=$1 AND user_id=$2", interaction.guild_id, membre.id)

    dissous = f" ({len(led_crews)} organisation(s) dissoute(s) au passage)" if led_crews else ""
    await interaction.response.send_message(
        f"Fiche de {membre.mention} entierement reinitialisee{dissous}. Il/elle peut refaire /commencer.",
        ephemeral=True
    )


boss_admin_group = app_commands.Group(name="boss", description="Outils admin pour le boss mondial", parent=config_group)

@boss_admin_group.command(name="forcer", description="Forcer l apparition immediate d un boss mondial (outil admin/test)")
async def boss_forcer(interaction: discord.Interaction):
    await interaction.response.defer(ephemeral=True)
    ok, message = await force_spawn_boss(interaction.guild)
    await interaction.followup.send(message, ephemeral=True)


def setup_admin_commands(bot):
    bot.tree.add_command(config_group)
