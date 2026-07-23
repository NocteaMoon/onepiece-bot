import discord
from discord import app_commands
import asyncio
from database.db import get_pool

CHANNELS_STRUCTURE = [
    ("📢 INFOS", [
        ("salon_annonces", "annonces", False),
        ("salon_reglement", "règlement", False),
        ("salon_bienvenue", "bienvenue", False),
    ]),
    ("🛡️ STAFF", [
        ("salon_logs", "logs", True),
        ("salon_moderation", "modération", True),
        ("salon_rapports", "rapports", True),
    ]),
    ("💬 COMMUNAUTÉ", [
        ("salon_general", "général", False),
        ("salon_creation", "création-personnage", False),
        ("salon_carnet", "carnet-de-bord", False),
    ]),
    ("💰 ÉCONOMIE", [
        ("salon_economie", "économie", False),
        ("salon_boutique", "boutique", False),
    ]),
    ("🗺️ AVENTURE", [
        ("salon_exploration", "exploration", False),
        ("salon_combat", "combat", False),
        ("salon_duel", "duel-pvp", False),
        ("salon_peche", "pêche-chasse-récolte", False),
        ("salon_entrainement", "entraînement", False),
    ]),
    ("🎲 DIVERTISSEMENT", [
        ("salon_casino", "casino", False),
        ("salon_taverne", "défis-de-taverne", False),
        ("salon_regates", "régates", False),
        ("salon_tresor", "chasse-au-trésor", False),
        ("salon_cartes", "cartes-à-collectionner", False),
    ]),
    ("🏴‍☠️ ORGANISATIONS", [
        ("salon_equipages", "équipages", False),
        ("salon_marine", "marine", False),
        ("salon_revolutionnaires", "révolutionnaires", False),
        ("salon_guilde", "guilde-des-métiers", False),
    ]),
    ("📊 INFOS JEU", [
        ("salon_classements", "classements", False),
        ("salon_quetes", "quêtes-événements", False),
        ("salon_succes", "succès", False),
        ("salon_recompenses", "récompenses", False),
    ]),
]

setup_command_group = app_commands.Group(
    name="setup",
    description="Assistant de configuration initiale du serveur",
    default_permissions=discord.Permissions(administrator=True)
)

@setup_command_group.command(name="salons", description="Créer automatiquement toutes les catégories et salons du bot")
async def setup_salons(interaction: discord.Interaction):
    await interaction.response.defer(ephemeral=True)
    guild = interaction.guild
    pool = get_pool()

    created = []
    skipped = []
    erreurs = []

    try:
        async with pool.acquire() as conn:
            row = await conn.fetchrow("SELECT * FROM guild_config WHERE guild_id = $1", guild.id)
            if row is None:
                await conn.execute("INSERT INTO guild_config (guild_id) VALUES ($1)", guild.id)
                row = await conn.fetchrow("SELECT * FROM guild_config WHERE guild_id = $1", guild.id)

            mod_roles = await conn.fetch(
                "SELECT role_id FROM guild_command_roles WHERE guild_id = $1 AND command_group = 'mod'",
                guild.id
            )

        mod_role_objects = []
        for r in mod_roles:
            role = guild.get_role(r["role_id"])
            if role:
                mod_role_objects.append(role)

        for category_name, channels in CHANNELS_STRUCTURE:
            try:
                category = discord.utils.get(guild.categories, name=category_name)
                if category is None:
                    category = await guild.create_category(category_name)
                    await asyncio.sleep(1)
            except discord.HTTPException as e:
                erreurs.append(f"Catégorie {category_name} : {e}")
                continue

            for column, channel_name, is_staff in channels:
                existing_id = row[column]
                existing_channel = guild.get_channel(existing_id) if existing_id else None
                if existing_channel:
                    skipped.append(channel_name)
                    continue

                try:
                    overwrites = {}
                    if is_staff:
                        overwrites[guild.default_role] = discord.PermissionOverwrite(view_channel=False)
                        for role in mod_role_objects:
                            overwrites[role] = discord.PermissionOverwrite(view_channel=True)

                    new_channel = await guild.create_text_channel(
                        channel_name,
                        category=category,
                        overwrites=overwrites
                    )
                    await asyncio.sleep(1)

                    async with pool.acquire() as conn:
                        await conn.execute(f"UPDATE guild_config SET {column} = $2 WHERE guild_id = $1", guild.id, new_channel.id)

                    created.append(new_channel.mention)
                except discord.HTTPException as e:
                    erreurs.append(f"Salon {channel_name} : {e}")

        embed = discord.Embed(title="🏗️ Configuration automatique terminée", color=0x27AE60)
        embed.add_field(name=f"✅ Salons créés ({len(created)})", value="\n".join(created) if created else "Aucun", inline=False)
        if skipped:
            embed.add_field(name=f"⏭️ Déjà existants, ignorés ({len(skipped)})", value=", ".join(skipped), inline=False)
        if erreurs:
            embed.add_field(name=f"❌ Erreurs ({len(erreurs)})", value="\n".join(erreurs)[:1000], inline=False)
        embed.set_footer(text="🌊 One Piece Bot • Setup")
        await interaction.followup.send(embed=embed, ephemeral=True)

    except Exception as e:
        await interaction.followup.send(f"❌ Une erreur inattendue est survenue : {e}", ephemeral=True)

def setup_setup_commands(bot):
    bot.tree.add_command(setup_command_group)
