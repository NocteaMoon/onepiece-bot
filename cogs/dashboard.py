import discord
from discord import app_commands
from database.db import get_pool
from cogs.admin import SALON_DEFINITIONS
from cogs.boss_mondial import get_active_boss, force_spawn_boss
from cogs.welcome import get_welcome_config, WelcomeVerifyView
from utils.faction_roles import (
    get_faction_role_ids, set_faction_role_id, create_all_faction_roles,
    assign_faction_role, sync_all_members_faction_roles, FACTION_ROLE_NAMES
)
from utils.players import add_xp
from data.mers import MERS

AUTOMOD_COLUMNS = ["anti_spam", "anti_liens", "anti_insultes", "anti_raid", "anti_mention", "anti_pub", "anti_alt", "anti_bot"]
LABEL_BY_COLUMN = {col: label for label, col in SALON_DEFINITIONS}

SALON_CATEGORIES = {
    "serveur": ("🛠️ Serveur & Modération", ["salon_annonces", "salon_reglement", "salon_bienvenue", "salon_logs", "salon_moderation", "salon_rapports", "salon_general"]),
    "economie": ("💰 Économie", ["salon_economie", "salon_boutique"]),
    "aventure": ("⚔️ Aventure & Combat", ["salon_exploration", "salon_combat", "salon_duel", "salon_peche", "salon_casino", "salon_entrainement"]),
    "organisations": ("🏴‍☠️ Organisations", ["salon_equipages", "salon_marine", "salon_revolutionnaires", "salon_guilde"]),
    "progression": ("📈 Progression", ["salon_classements", "salon_quetes", "salon_succes", "salon_recompenses", "salon_carnet", "salon_cartes"]),
    "social": ("🎉 Social & Création", ["salon_taverne", "salon_regates", "salon_tresor", "salon_creation"]),
}

AUTOMOD_TOGGLE_LABELS = {
    "anti_spam": "Anti-spam", "anti_liens": "Anti-liens", "anti_insultes": "Anti-insultes",
    "anti_raid": "Anti-raid", "anti_mention": "Anti-mention de masse", "anti_pub": "Anti-pub",
    "anti_alt": "Anti-comptes récents", "anti_bot": "Anti-bot",
}

LOGS_TOGGLE_LABELS = {
    "log_msg_delete": "Suppression de messages",
    "log_msg_edit": "Modification de messages",
    "log_join_leave": "Arrivées / départs",
    "log_salons": "Changements de salons",
    "log_roles": "Changements de rôles",
    "log_pseudos": "Changements de pseudo",
}

MARCHE_CATEGORIES = ["Consommable", "Accessoire", "Tête", "Corps", "Navire", "Arme", "Ingrédient", "Plat", "Relique", "Partition"]
MARCHE_FACTIONS = ["Tous", "Pirate", "Marine", "Révolutionnaire"]
MARCHE_RARETES = ["Commun", "Aiguisé", "Grade", "Grand Grade", "Suprême", "Mythique"]
MARCHE_SLOTS = [("Aucun (consommable)", "aucun"), ("Arme principale", "arme_principale"), ("Arme secondaire", "arme_secondaire"),
                ("Tête", "tete"), ("Corps", "corps"), ("Accessoire", "accessoire"), ("Navire", "navire")]

CHAMP_CHOICES_DASH = [
    ("Nom", "nom"), ("Description", "description"), ("Prix", "prix"), ("Stock (-1 = illimité)", "stock"),
    ("Niveau requis", "niveau_requis"), ("Bonus Force", "bonus_force"), ("Bonus Défense", "bonus_defense"),
    ("Bonus Vitesse", "bonus_vitesse"), ("Bonus Agilité", "bonus_agilite"), ("Bonus PV", "bonus_pv"),
    ("Bonus Chance", "bonus_chance"), ("Soin PV", "soin_pv"), ("Soin Endurance", "soin_endurance"),
    ("Durabilité max", "durabilite_max"), ("Actif (oui/non)", "actif"),
]


# ===== ACCUEIL =====

async def get_overview_stats(guild_id: int):
    pool = get_pool()
    async with pool.acquire() as conn:
        config_row = await conn.fetchrow("SELECT * FROM guild_config WHERE guild_id = $1", guild_id)
        automod_row = await conn.fetchrow("SELECT * FROM automod_config WHERE guild_id = $1", guild_id)
        logs_row = await conn.fetchrow("SELECT * FROM logs_config WHERE guild_id = $1", guild_id)
        welcome_row = await conn.fetchrow("SELECT * FROM welcome_config WHERE guild_id = $1", guild_id)
        nb_items = await conn.fetchval("SELECT COUNT(*) FROM shop_items WHERE guild_id = $1 AND actif = TRUE", guild_id)
        nb_permissions = await conn.fetchval("SELECT COUNT(*) FROM guild_command_roles WHERE guild_id = $1", guild_id)

    if config_row:
        nb_salons = sum(1 for _, value in SALON_DEFINITIONS if config_row[value])
        langue = config_row["lang"]
    else:
        nb_salons = 0
        langue = "fr"

    nb_automod_actifs = sum(1 for col in AUTOMOD_COLUMNS if automod_row[col]) if automod_row else 0
    nb_logs_actifs = sum(1 for col in LOGS_TOGGLE_LABELS if logs_row[col]) if logs_row else len(LOGS_TOGGLE_LABELS)
    bienvenue_configuree = bool(welcome_row) and bool(welcome_row["message"])
    boss_actif = await get_active_boss(guild_id)

    return {
        "nb_salons": nb_salons, "total_salons": len(SALON_DEFINITIONS), "langue": langue,
        "nb_items": nb_items or 0, "nb_permissions": nb_permissions or 0,
        "nb_automod_actifs": nb_automod_actifs, "total_automod": len(AUTOMOD_COLUMNS),
        "nb_logs_actifs": nb_logs_actifs, "total_logs": len(LOGS_TOGGLE_LABELS),
        "bienvenue_configuree": bienvenue_configuree,
        "boss_actif": boss_actif is not None,
    }


def build_home_embed(stats: dict, guild_name: str):
    embed = discord.Embed(
        title="🎛️ Dashboard d'administration",
        description=f"Vue d'ensemble de la configuration de **{guild_name}**. Choisis une section ci-dessous pour la gérer.",
        color=0x2C3E50
    )
    embed.add_field(name="🗺️ Salons", value=f"{stats['nb_salons']}/{stats['total_salons']} configurés", inline=True)
    embed.add_field(name="🌐 Langue", value=stats["langue"].upper(), inline=True)
    embed.add_field(name="🛒 Marché", value=f"{stats['nb_items']} objet(s) actif(s)", inline=True)
    embed.add_field(name="🛡️ Automod", value=f"{stats['nb_automod_actifs']}/{stats['total_automod']} règles actives", inline=True)
    embed.add_field(name="📋 Logs", value=f"{stats['nb_logs_actifs']}/{stats['total_logs']} actifs", inline=True)
    embed.add_field(name="👋 Bienvenue", value="✅ Configurée" if stats["bienvenue_configuree"] else "⚪ Par défaut", inline=True)
    embed.add_field(name="🔑 Permissions", value=f"{stats['nb_permissions']} règle(s) personnalisée(s)", inline=True)
    embed.add_field(name="👑 Boss mondial", value="🟢 Actif" if stats["boss_actif"] else "⚪ Aucun en cours", inline=True)
    embed.set_footer(text="🌊 One Piece Bot • Dashboard")
    return embed


class DashboardBackHomeButton(discord.ui.Button):
    def __init__(self):
        super().__init__(label="Accueil", emoji="🏠", style=discord.ButtonStyle.secondary)

    async def callback(self, interaction: discord.Interaction):
        stats = await get_overview_stats(interaction.guild_id)
        embed = build_home_embed(stats, interaction.guild.name)
        await interaction.response.edit_message(embed=embed, view=DashboardHomeView())


# ===== SALONS =====

async def get_salon_status_text(guild_id: int, columns: list) -> str:
    pool = get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow("SELECT * FROM guild_config WHERE guild_id=$1", guild_id)
    lignes = []
    for col in columns:
        label = LABEL_BY_COLUMN.get(col, col)
        val = row[col] if row else None
        statut = f"<#{val}>" if val else "❌ Non défini"
        lignes.append(f"**{label}** : {statut}")
    return "\n".join(lignes)


async def build_salons_overview_embed(guild_id: int):
    all_columns = [col for _, (label, cols) in SALON_CATEGORIES.items() for col in cols]
    texte = await get_salon_status_text(guild_id, all_columns)
    nb_configures = texte.count("<#")
    embed = discord.Embed(
        title="🗺️ Salons",
        description=f"**{nb_configures}/{len(all_columns)}** salons configurés au total. Choisis une catégorie ci-dessous.",
        color=0x2C3E50
    )
    embed.set_footer(text="🌊 One Piece Bot • Dashboard")
    return embed


class SalonChannelSelect(discord.ui.ChannelSelect):
    def __init__(self, salon_column: str, salon_label: str, category_key: str):
        super().__init__(
            placeholder=f"Choisis le salon pour « {salon_label} »...",
            channel_types=[discord.ChannelType.text], min_values=1, max_values=1
        )
        self.salon_column = salon_column
        self.salon_label = salon_label
        self.category_key = category_key

    async def callback(self, interaction: discord.Interaction):
        channel = self.values[0]
        pool = get_pool()
        async with pool.acquire() as conn:
            await conn.execute(f"""
                INSERT INTO guild_config (guild_id, {self.salon_column}) VALUES ($1, $2)
                ON CONFLICT (guild_id) DO UPDATE SET {self.salon_column} = $2
            """, interaction.guild_id, channel.id)

        label, columns = SALON_CATEGORIES[self.category_key]
        texte = await get_salon_status_text(interaction.guild_id, columns)
        embed = discord.Embed(
            title=f"✅ {self.salon_label} mis à jour !",
            description=f"Défini sur {channel.mention}.\n\n**{label}**\n{texte}",
            color=0x27AE60
        )
        embed.set_footer(text="🌊 One Piece Bot • Dashboard")
        await interaction.response.edit_message(embed=embed, view=DashboardSalonCategoryView(self.category_key))


class DashboardBackToSalonsButton(discord.ui.Button):
    def __init__(self):
        super().__init__(label="Toutes les catégories", emoji="🗺️", style=discord.ButtonStyle.secondary)

    async def callback(self, interaction: discord.Interaction):
        embed = await build_salons_overview_embed(interaction.guild_id)
        await interaction.response.edit_message(embed=embed, view=DashboardSalonsOverviewView())


class DashboardBackToCategoryButton(discord.ui.Button):
    def __init__(self, category_key: str):
        super().__init__(label="Retour", emoji="↩️", style=discord.ButtonStyle.secondary)
        self.category_key = category_key

    async def callback(self, interaction: discord.Interaction):
        label, columns = SALON_CATEGORIES[self.category_key]
        texte = await get_salon_status_text(interaction.guild_id, columns)
        embed = discord.Embed(title=label, description=texte, color=0x2C3E50)
        embed.set_footer(text="🌊 One Piece Bot • Dashboard")
        await interaction.response.edit_message(embed=embed, view=DashboardSalonCategoryView(self.category_key))


class DashboardSalonChannelPickView(discord.ui.View):
    def __init__(self, salon_column: str, salon_label: str, category_key: str):
        super().__init__(timeout=180)
        self.add_item(SalonChannelSelect(salon_column, salon_label, category_key))
        self.add_item(DashboardBackToCategoryButton(category_key))


class DashboardSalonTypeSelect(discord.ui.Select):
    def __init__(self, category_key: str):
        self.category_key = category_key
        label, columns = SALON_CATEGORIES[category_key]
        options = [discord.SelectOption(label=LABEL_BY_COLUMN.get(col, col), value=col) for col in columns]
        super().__init__(placeholder="Choisis le type de salon à configurer...", options=options)

    async def callback(self, interaction: discord.Interaction):
        salon_column = self.values[0]
        salon_label = LABEL_BY_COLUMN.get(salon_column, salon_column)
        embed = discord.Embed(title=f"🗺️ Configurer : {salon_label}", description="Choisis le salon Discord ci-dessous.", color=0x2C3E50)
        embed.set_footer(text="🌊 One Piece Bot • Dashboard")
        await interaction.response.edit_message(embed=embed, view=DashboardSalonChannelPickView(salon_column, salon_label, self.category_key))


class DashboardSalonCategoryView(discord.ui.View):
    def __init__(self, category_key: str):
        super().__init__(timeout=180)
        self.add_item(DashboardSalonTypeSelect(category_key))
        self.add_item(DashboardBackToSalonsButton())
        self.add_item(DashboardBackHomeButton())


class DashboardSalonsCategorySelect(discord.ui.Select):
    def __init__(self):
        options = [discord.SelectOption(label=label, value=key) for key, (label, cols) in SALON_CATEGORIES.items()]
        super().__init__(placeholder="Choisis une catégorie de salons...", options=options)

    async def callback(self, interaction: discord.Interaction):
        category_key = self.values[0]
        label, columns = SALON_CATEGORIES[category_key]
        texte = await get_salon_status_text(interaction.guild_id, columns)
        embed = discord.Embed(title=label, description=texte, color=0x2C3E50)
        embed.set_footer(text="🌊 One Piece Bot • Dashboard")
        await interaction.response.edit_message(embed=embed, view=DashboardSalonCategoryView(category_key))


class DashboardSalonsOverviewView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=180)
        self.add_item(DashboardSalonsCategorySelect())
        self.add_item(DashboardBackHomeButton())


# ===== LANGUE =====

class LangueSelect(discord.ui.Select):
    def __init__(self):
        options = [
            discord.SelectOption(label="Français", value="fr", emoji="🇫🇷"),
            discord.SelectOption(label="English", value="en", emoji="🇬🇧"),
        ]
        super().__init__(placeholder="Choisis la langue du bot...", options=options)

    async def callback(self, interaction: discord.Interaction):
        langue = self.values[0]
        pool = get_pool()
        async with pool.acquire() as conn:
            await conn.execute("""
                INSERT INTO guild_config (guild_id, lang) VALUES ($1, $2)
                ON CONFLICT (guild_id) DO UPDATE SET lang = $2
            """, interaction.guild_id, langue)
        label = "Français 🇫🇷" if langue == "fr" else "English 🇬🇧"
        embed = discord.Embed(title="🌐 Langue mise à jour !", description=f"Langue définie sur **{label}**.", color=0x27AE60)
        embed.set_footer(text="🌊 One Piece Bot • Dashboard")
        await interaction.response.edit_message(embed=embed, view=DashboardLangueView())


class DashboardLangueView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=180)
        self.add_item(LangueSelect())
        self.add_item(DashboardBackHomeButton())


async def build_langue_embed(guild_id: int):
    pool = get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow("SELECT lang FROM guild_config WHERE guild_id=$1", guild_id)
    langue_actuelle = row["lang"] if row else "fr"
    label = "Français 🇫🇷" if langue_actuelle == "fr" else "English 🇬🇧"
    embed = discord.Embed(title="🌐 Langue", description=f"Langue actuelle : **{label}**", color=0x2C3E50)
    embed.set_footer(text="🌊 One Piece Bot • Dashboard")
    return embed


# ===== BOSS MONDIAL =====

async def build_boss_embed(guild_id: int):
    actif = await get_active_boss(guild_id)
    if not actif:
        embed = discord.Embed(
            title="👑 Boss mondial",
            description="Aucun boss mondial actif pour l'instant. Ils apparaissent spontanément, ou tu peux forcer l'apparition ci-dessous (nécessite un salon Combat configuré).",
            color=0x2C3E50
        )
    else:
        phase_txt = "Inscriptions en cours" if actif["phase"] == "inscription" else "Combat en cours"
        embed = discord.Embed(
            title="👑 Boss mondial",
            description=f"**{actif['boss_nom'].capitalize()}** — {phase_txt}\nMer : {actif['mer']}\nPV : {max(0, actif['pv']):,}/{actif['pv_max']:,}",
            color=0x7F0000
        )
    embed.set_footer(text="🌊 One Piece Bot • Dashboard")
    return embed


class BossForcerButton(discord.ui.Button):
    def __init__(self):
        super().__init__(label="Forcer l'apparition", emoji="⚔️", style=discord.ButtonStyle.danger)

    async def callback(self, interaction: discord.Interaction):
        ok, message = await force_spawn_boss(interaction.guild)
        embed = await build_boss_embed(interaction.guild_id)
        await interaction.response.edit_message(embed=embed, view=DashboardBossView())
        await interaction.followup.send(message, ephemeral=True)


class DashboardBossView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=180)
        self.add_item(BossForcerButton())
        self.add_item(DashboardBackHomeButton())


# ===== MODÉRATION & AUTOMOD =====

async def ensure_automod_row(guild_id: int):
    pool = get_pool()
    async with pool.acquire() as conn:
        await conn.execute("INSERT INTO automod_config (guild_id) VALUES ($1) ON CONFLICT (guild_id) DO NOTHING", guild_id)


async def get_automod_row(guild_id: int):
    await ensure_automod_row(guild_id)
    pool = get_pool()
    async with pool.acquire() as conn:
        return await conn.fetchrow("SELECT * FROM automod_config WHERE guild_id=$1", guild_id)


async def build_moderation_embed(guild_id: int):
    row = await get_automod_row(guild_id)
    lignes = [f"{'✅' if row[col] else '❌'} {label}" for col, label in AUTOMOD_TOGGLE_LABELS.items()]
    lignes.append("")
    lignes.append("**Limites actuelles :**")
    lignes.append(f"Spam : {row['spam_msg_limit']} messages / {row['spam_seconds']}s")
    lignes.append(f"Raid : {row['raid_join_limit']} arrivées / {row['raid_seconds']}s")
    lignes.append(f"Mentions max : {row['mention_limit']}")
    lignes.append(f"Compte min : {row['alt_min_days']} jours")
    embed = discord.Embed(title="🛡️ Modération & Automod", description="\n".join(lignes), color=0x2C3E50)
    embed.set_footer(text="🌊 One Piece Bot • Dashboard")
    return embed


class AutomodToggleSelect(discord.ui.Select):
    def __init__(self, current_row):
        options = [
            discord.SelectOption(label=label, value=col, default=bool(current_row[col]))
            for col, label in AUTOMOD_TOGGLE_LABELS.items()
        ]
        super().__init__(placeholder="Coche les règles à activer...", options=options, min_values=0, max_values=len(options))

    async def callback(self, interaction: discord.Interaction):
        selected = set(self.values)
        pool = get_pool()
        async with pool.acquire() as conn:
            for col in AUTOMOD_TOGGLE_LABELS:
                await conn.execute(f"UPDATE automod_config SET {col} = $2 WHERE guild_id=$1", interaction.guild_id, col in selected)
        embed = await build_moderation_embed(interaction.guild_id)
        await interaction.response.edit_message(embed=embed, view=await DashboardModerationView.create(interaction.guild_id))


class AutomodSpamModal(discord.ui.Modal, title="Limites : Spam & Mentions"):
    def __init__(self, current_row):
        super().__init__()
        self.spam_msg = discord.ui.TextInput(label="Messages avant anti-spam", default=str(current_row["spam_msg_limit"]), max_length=3)
        self.spam_sec = discord.ui.TextInput(label="Fenêtre anti-spam (secondes)", default=str(current_row["spam_seconds"]), max_length=3)
        self.mention_lim = discord.ui.TextInput(label="Mentions max par message", default=str(current_row["mention_limit"]), max_length=3)
        self.add_item(self.spam_msg)
        self.add_item(self.spam_sec)
        self.add_item(self.mention_lim)

    async def on_submit(self, interaction: discord.Interaction):
        try:
            spam_msg, spam_sec, mention_lim = int(self.spam_msg.value), int(self.spam_sec.value), int(self.mention_lim.value)
        except ValueError:
            await interaction.response.send_message("⛔ Toutes les valeurs doivent être des nombres entiers.", ephemeral=True)
            return
        pool = get_pool()
        async with pool.acquire() as conn:
            await conn.execute(
                "UPDATE automod_config SET spam_msg_limit=$2, spam_seconds=$3, mention_limit=$4 WHERE guild_id=$1",
                interaction.guild_id, spam_msg, spam_sec, mention_lim
            )
        embed = await build_moderation_embed(interaction.guild_id)
        await interaction.response.edit_message(embed=embed, view=await DashboardModerationView.create(interaction.guild_id))


class AutomodRaidModal(discord.ui.Modal, title="Limites : Raid & Comptes récents"):
    def __init__(self, current_row):
        super().__init__()
        self.raid_join = discord.ui.TextInput(label="Arrivées avant anti-raid", default=str(current_row["raid_join_limit"]), max_length=3)
        self.raid_sec = discord.ui.TextInput(label="Fenêtre anti-raid (secondes)", default=str(current_row["raid_seconds"]), max_length=4)
        self.alt_days = discord.ui.TextInput(label="Âge de compte minimum (jours)", default=str(current_row["alt_min_days"]), max_length=3)
        self.add_item(self.raid_join)
        self.add_item(self.raid_sec)
        self.add_item(self.alt_days)

    async def on_submit(self, interaction: discord.Interaction):
        try:
            raid_join, raid_sec, alt_days = int(self.raid_join.value), int(self.raid_sec.value), int(self.alt_days.value)
        except ValueError:
            await interaction.response.send_message("⛔ Toutes les valeurs doivent être des nombres entiers.", ephemeral=True)
            return
        pool = get_pool()
        async with pool.acquire() as conn:
            await conn.execute(
                "UPDATE automod_config SET raid_join_limit=$2, raid_seconds=$3, alt_min_days=$4 WHERE guild_id=$1",
                interaction.guild_id, raid_join, raid_sec, alt_days
            )
        embed = await build_moderation_embed(interaction.guild_id)
        await interaction.response.edit_message(embed=embed, view=await DashboardModerationView.create(interaction.guild_id))


class AutomodSpamButton(discord.ui.Button):
    def __init__(self):
        super().__init__(label="Réglages Spam & Mentions", emoji="💬", style=discord.ButtonStyle.secondary)

    async def callback(self, interaction: discord.Interaction):
        row = await get_automod_row(interaction.guild_id)
        await interaction.response.send_modal(AutomodSpamModal(row))


class AutomodRaidButton(discord.ui.Button):
    def __init__(self):
        super().__init__(label="Réglages Raid & Comptes", emoji="🚪", style=discord.ButtonStyle.secondary)

    async def callback(self, interaction: discord.Interaction):
        row = await get_automod_row(interaction.guild_id)
        await interaction.response.send_modal(AutomodRaidModal(row))


class DashboardModerationView(discord.ui.View):
    def __init__(self, automod_row):
        super().__init__(timeout=180)
        self.add_item(AutomodToggleSelect(automod_row))
        self.add_item(AutomodSpamButton())
        self.add_item(AutomodRaidButton())
        self.add_item(DashboardBackHomeButton())

    @classmethod
    async def create(cls, guild_id):
        row = await get_automod_row(guild_id)
        return cls(row)


# ===== LOGS =====

async def ensure_logs_row(guild_id: int):
    pool = get_pool()
    async with pool.acquire() as conn:
        await conn.execute("INSERT INTO logs_config (guild_id) VALUES ($1) ON CONFLICT (guild_id) DO NOTHING", guild_id)


async def get_logs_row(guild_id: int):
    await ensure_logs_row(guild_id)
    pool = get_pool()
    async with pool.acquire() as conn:
        return await conn.fetchrow("SELECT * FROM logs_config WHERE guild_id=$1", guild_id)


async def build_logs_embed(guild_id: int):
    row = await get_logs_row(guild_id)
    lignes = [f"{'✅' if row[col] else '❌'} {label}" for col, label in LOGS_TOGGLE_LABELS.items()]
    embed = discord.Embed(title="📋 Logs", description="\n".join(lignes), color=0x2C3E50)
    embed.set_footer(text="🌊 One Piece Bot • Dashboard • Nécessite un salon Logs configuré (section Salons)")
    return embed


class LogsToggleSelect(discord.ui.Select):
    def __init__(self, current_row):
        options = [
            discord.SelectOption(label=label, value=col, default=bool(current_row[col]))
            for col, label in LOGS_TOGGLE_LABELS.items()
        ]
        super().__init__(placeholder="Coche les événements à journaliser...", options=options, min_values=0, max_values=len(options))

    async def callback(self, interaction: discord.Interaction):
        selected = set(self.values)
        pool = get_pool()
        async with pool.acquire() as conn:
            for col in LOGS_TOGGLE_LABELS:
                await conn.execute(f"UPDATE logs_config SET {col} = $2 WHERE guild_id=$1", interaction.guild_id, col in selected)
        embed = await build_logs_embed(interaction.guild_id)
        await interaction.response.edit_message(embed=embed, view=await DashboardLogsView.create(interaction.guild_id))


class DashboardLogsView(discord.ui.View):
    def __init__(self, logs_row):
        super().__init__(timeout=180)
        self.add_item(LogsToggleSelect(logs_row))
        self.add_item(DashboardBackHomeButton())

    @classmethod
    async def create(cls, guild_id):
        row = await get_logs_row(guild_id)
        return cls(row)


# ===== BIENVENUE =====

async def build_bienvenue_embed(guild_id: int):
    row = await get_welcome_config(guild_id)
    role_txt = f"<@&{row['auto_role_id']}>" if row["auto_role_id"] else "Aucun"
    verif_txt = "✅ Activée" if row["verification_enabled"] else "❌ Désactivée"
    bg_txt = "✅ Définie" if row["background_url"] else "❌ Aucune"
    description = (
        f"**Message actuel :**\n{row['message']}\n\n"
        f"**Rôle automatique :** {role_txt}\n"
        f"**Vérification :** {verif_txt}\n"
        f"**Image de fond :** {bg_txt}"
    )
    embed = discord.Embed(title="👋 Bienvenue", description=description, color=0x2C3E50)
    embed.set_footer(text="🌊 One Piece Bot • Dashboard")
    return embed


class WelcomeMessageModal(discord.ui.Modal, title="Modifier le message de bienvenue"):
    def __init__(self, current_message):
        super().__init__()
        self.message = discord.ui.TextInput(
            label="Message ({mention} {serveur} {nombre})",
            style=discord.TextStyle.paragraph,
            default=current_message,
            max_length=500
        )
        self.add_item(self.message)

    async def on_submit(self, interaction: discord.Interaction):
        pool = get_pool()
        async with pool.acquire() as conn:
            await conn.execute("UPDATE welcome_config SET message = $2 WHERE guild_id=$1", interaction.guild_id, self.message.value)
        embed = await build_bienvenue_embed(interaction.guild_id)
        await interaction.response.edit_message(embed=embed, view=await DashboardBienvenueView.create(interaction.guild_id))


class WelcomeMessageButton(discord.ui.Button):
    def __init__(self, current_message):
        self.current_message = current_message
        super().__init__(label="Modifier le message", emoji="✏️", style=discord.ButtonStyle.primary)

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.send_modal(WelcomeMessageModal(self.current_message))


class WelcomeRoleSelect(discord.ui.RoleSelect):
    def __init__(self):
        super().__init__(placeholder="Choisis le rôle automatique...", min_values=1, max_values=1)

    async def callback(self, interaction: discord.Interaction):
        role = self.values[0]
        pool = get_pool()
        async with pool.acquire() as conn:
            await conn.execute("UPDATE welcome_config SET auto_role_id = $2 WHERE guild_id=$1", interaction.guild_id, role.id)
        embed = await build_bienvenue_embed(interaction.guild_id)
        await interaction.response.edit_message(embed=embed, view=await DashboardBienvenueView.create(interaction.guild_id))


class WelcomeRoleButton(discord.ui.Button):
    def __init__(self):
        super().__init__(label="Définir le rôle auto", emoji="🎭", style=discord.ButtonStyle.secondary)

    async def callback(self, interaction: discord.Interaction):
        embed = discord.Embed(title="👋 Rôle automatique", description="Choisis le rôle à attribuer aux nouveaux membres.", color=0x2C3E50)
        embed.set_footer(text="🌊 One Piece Bot • Dashboard")
        view = discord.ui.View(timeout=180)
        view.add_item(WelcomeRoleSelect())
        await interaction.response.edit_message(embed=embed, view=view)


class WelcomeVerificationToggleButton(discord.ui.Button):
    def __init__(self, current_state):
        self.current_state = current_state
        label = "Désactiver la vérification" if current_state else "Activer la vérification"
        super().__init__(label=label, emoji="🔐", style=discord.ButtonStyle.secondary)

    async def callback(self, interaction: discord.Interaction):
        pool = get_pool()
        async with pool.acquire() as conn:
            await conn.execute("UPDATE welcome_config SET verification_enabled = $2 WHERE guild_id=$1", interaction.guild_id, not self.current_state)
        embed = await build_bienvenue_embed(interaction.guild_id)
        await interaction.response.edit_message(embed=embed, view=await DashboardBienvenueView.create(interaction.guild_id))


class WelcomeBackgroundModal(discord.ui.Modal, title="Image de fond de la carte de bienvenue"):
    def __init__(self, current_url):
        super().__init__()
        self.url = discord.ui.TextInput(label="Lien de l'image (URL directe)", default=current_url or "", required=False, max_length=300)
        self.add_item(self.url)

    async def on_submit(self, interaction: discord.Interaction):
        pool = get_pool()
        async with pool.acquire() as conn:
            await conn.execute("UPDATE welcome_config SET background_url = $2 WHERE guild_id=$1", interaction.guild_id, self.url.value or None)
        embed = await build_bienvenue_embed(interaction.guild_id)
        await interaction.response.edit_message(embed=embed, view=await DashboardBienvenueView.create(interaction.guild_id))


class WelcomeBackgroundButton(discord.ui.Button):
    def __init__(self, current_url):
        self.current_url = current_url
        super().__init__(label="Image de fond", emoji="🖼️", style=discord.ButtonStyle.secondary)

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.send_modal(WelcomeBackgroundModal(self.current_url))


class WelcomePosterPanneauButton(discord.ui.Button):
    def __init__(self, auto_role_id):
        self.auto_role_id = auto_role_id
        super().__init__(label="Poster le panneau de vérification ici", emoji="📌", style=discord.ButtonStyle.success)

    async def callback(self, interaction: discord.Interaction):
        if not self.auto_role_id:
            await interaction.response.send_message("⚠️ Configure d'abord un rôle automatique avant de poster le panneau.", ephemeral=True)
            return
        await interaction.channel.send(view=WelcomeVerifyView())
        await interaction.response.send_message("✅ Panneau de vérification posté dans ce salon (poste-le idéalement sous ton règlement).", ephemeral=True)


class DashboardBienvenueView(discord.ui.View):
    def __init__(self, welcome_row):
        super().__init__(timeout=180)
        self.add_item(WelcomeMessageButton(welcome_row["message"]))
        self.add_item(WelcomeRoleButton())
        self.add_item(WelcomeVerificationToggleButton(welcome_row["verification_enabled"]))
        self.add_item(WelcomeBackgroundButton(welcome_row["background_url"]))
        self.add_item(WelcomePosterPanneauButton(welcome_row["auto_role_id"]))
        self.add_item(DashboardBackHomeButton())

    @classmethod
    async def create(cls, guild_id):
        row = await get_welcome_config(guild_id)
        return cls(row)


# ===== MARCHÉ =====

async def build_marche_home_embed(guild_id: int):
    pool = get_pool()
    async with pool.acquire() as conn:
        nb_actifs = await conn.fetchval("SELECT COUNT(*) FROM shop_items WHERE guild_id=$1 AND actif=TRUE", guild_id)
        nb_total = await conn.fetchval("SELECT COUNT(*) FROM shop_items WHERE guild_id=$1", guild_id)
    embed = discord.Embed(title="🛒 Marché", description=f"**{nb_actifs or 0}/{nb_total or 0}** objets actifs. Choisis une action.", color=0x2C3E50)
    embed.set_footer(text="🌊 One Piece Bot • Dashboard")
    return embed


async def build_marche_liste_embed(guild_id: int):
    pool = get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch("SELECT id, nom, categorie, faction, prix, actif FROM shop_items WHERE guild_id=$1 ORDER BY categorie, nom", guild_id)
    if not rows:
        return discord.Embed(title="📋 Liste des objets", description="Aucun objet dans le marché.", color=0x2C3E50)
    lignes = [f"{'🟢' if r['actif'] else '🔴'} #{r['id']} — {r['nom']} ({r['categorie']}, {r['faction']}) — {r['prix']:,}฿" for r in rows]
    texte = "\n".join(lignes)
    if len(texte) > 3900:
        texte = texte[:3900] + "\n... (liste tronquée)"
    embed = discord.Embed(title="📋 Liste des objets", description=texte, color=0x2C3E50)
    embed.set_footer(text="🌊 One Piece Bot • Dashboard")
    return embed


class MarcheActionSelect(discord.ui.Select):
    def __init__(self):
        options = [
            discord.SelectOption(label="Voir la liste des objets", value="liste", emoji="📋"),
            discord.SelectOption(label="Ajouter un objet", value="ajouter", emoji="➕"),
            discord.SelectOption(label="Modifier un objet", value="modifier", emoji="✏️"),
            discord.SelectOption(label="Retirer un objet", value="supprimer", emoji="🗑️"),
        ]
        super().__init__(placeholder="Choisis une action...", options=options)

    async def callback(self, interaction: discord.Interaction):
        action = self.values[0]
        if action == "liste":
            embed = await build_marche_liste_embed(interaction.guild_id)
            await interaction.response.edit_message(embed=embed, view=DashboardMarcheView())
        elif action == "ajouter":
            await interaction.response.send_modal(MarcheAjouterModal())
        elif action in ("modifier", "supprimer"):
            embed = discord.Embed(
                title=("✏️ Modifier" if action == "modifier" else "🗑️ Retirer") + " un objet",
                description="Choisis d'abord la catégorie de l'objet.", color=0x2C3E50
            )
            embed.set_footer(text="🌊 One Piece Bot • Dashboard")
            await interaction.response.edit_message(embed=embed, view=MarcheCategoryPickView(action))


class DashboardMarcheView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=180)
        self.add_item(MarcheActionSelect())
        self.add_item(DashboardBackHomeButton())


class MarcheAjouterModal(discord.ui.Modal, title="Ajouter un objet — Étape 1/2"):
    def __init__(self):
        super().__init__()
        self.nom = discord.ui.TextInput(label="Nom de l'objet", max_length=100)
        self.description = discord.ui.TextInput(label="Description", style=discord.TextStyle.paragraph, max_length=300)
        self.prix = discord.ui.TextInput(label="Prix (en Berrys)", max_length=6)
        self.add_item(self.nom)
        self.add_item(self.description)
        self.add_item(self.prix)

    async def on_submit(self, interaction: discord.Interaction):
        try:
            prix_val = int(self.prix.value)
        except ValueError:
            await interaction.response.send_message("⛔ Le prix doit être un nombre entier.", ephemeral=True)
            return
        embed = discord.Embed(
            title="➕ Ajouter un objet — Étape 2/2",
            description=f"**{self.nom.value}**\n{self.description.value}\nPrix : {prix_val:,}฿\n\nChoisis la catégorie.",
            color=0x2C3E50
        )
        embed.set_footer(text="🌊 One Piece Bot • Dashboard")
        await interaction.response.edit_message(embed=embed, view=MarcheAjouterStep2View(self.nom.value, self.description.value, prix_val))


class MarcheCategorieSelect(discord.ui.Select):
    def __init__(self, nom, description, prix):
        self.nom, self.description, self.prix = nom, description, prix
        options = [discord.SelectOption(label=c, value=c) for c in MARCHE_CATEGORIES]
        super().__init__(placeholder="Catégorie...", options=options)

    async def callback(self, interaction: discord.Interaction):
        embed = discord.Embed(title="➕ Ajouter un objet — Étape 2/2", description=f"Catégorie : **{self.values[0]}**\n\nChoisis la faction.", color=0x2C3E50)
        embed.set_footer(text="🌊 One Piece Bot • Dashboard")
        await interaction.response.edit_message(embed=embed, view=MarcheAjouterFactionView(self.nom, self.description, self.prix, self.values[0]))


class MarcheAjouterStep2View(discord.ui.View):
    def __init__(self, nom, description, prix):
        super().__init__(timeout=300)
        self.add_item(MarcheCategorieSelect(nom, description, prix))


class MarcheFactionSelect(discord.ui.Select):
    def __init__(self, nom, description, prix, categorie):
        self.nom, self.description, self.prix, self.categorie = nom, description, prix, categorie
        options = [discord.SelectOption(label=f, value=f) for f in MARCHE_FACTIONS]
        super().__init__(placeholder="Faction...", options=options)

    async def callback(self, interaction: discord.Interaction):
        embed = discord.Embed(
            title="➕ Ajouter un objet — Étape 2/2",
            description=f"Catégorie : **{self.categorie}** • Faction : **{self.values[0]}**\n\nChoisis la rareté.", color=0x2C3E50
        )
        embed.set_footer(text="🌊 One Piece Bot • Dashboard")
        await interaction.response.edit_message(embed=embed, view=MarcheAjouterRareteView(self.nom, self.description, self.prix, self.categorie, self.values[0]))


class MarcheAjouterFactionView(discord.ui.View):
    def __init__(self, nom, description, prix, categorie):
        super().__init__(timeout=300)
        self.add_item(MarcheFactionSelect(nom, description, prix, categorie))


class MarcheRareteSelect(discord.ui.Select):
    def __init__(self, nom, description, prix, categorie, faction):
        self.nom, self.description, self.prix, self.categorie, self.faction = nom, description, prix, categorie, faction
        options = [discord.SelectOption(label=r, value=r) for r in MARCHE_RARETES]
        super().__init__(placeholder="Rareté...", options=options)

    async def callback(self, interaction: discord.Interaction):
        embed = discord.Embed(
            title="➕ Ajouter un objet — Étape 2/2",
            description=f"Catégorie : **{self.categorie}** • Faction : **{self.faction}** • Rareté : **{self.values[0]}**\n\nChoisis l'emplacement.",
            color=0x2C3E50
        )
        embed.set_footer(text="🌊 One Piece Bot • Dashboard")
        await interaction.response.edit_message(embed=embed, view=MarcheAjouterSlotView(self.nom, self.description, self.prix, self.categorie, self.faction, self.values[0]))


class MarcheAjouterRareteView(discord.ui.View):
    def __init__(self, nom, description, prix, categorie, faction):
        super().__init__(timeout=300)
        self.add_item(MarcheRareteSelect(nom, description, prix, categorie, faction))


class MarcheSlotSelect(discord.ui.Select):
    def __init__(self, nom, description, prix, categorie, faction, rarete):
        self.nom, self.description, self.prix = nom, description, prix
        self.categorie, self.faction, self.rarete = categorie, faction, rarete
        options = [discord.SelectOption(label=label, value=value) for label, value in MARCHE_SLOTS]
        super().__init__(placeholder="Emplacement...", options=options)

    async def callback(self, interaction: discord.Interaction):
        slot_value = None if self.values[0] == "aucun" else self.values[0]
        pool = get_pool()
        async with pool.acquire() as conn:
            row = await conn.fetchrow("""
                INSERT INTO shop_items (guild_id, nom, description, categorie, faction, rarete, prix, slot)
                VALUES ($1,$2,$3,$4,$5,$6,$7,$8) RETURNING id
            """, interaction.guild_id, self.nom, self.description, self.categorie, self.faction, self.rarete, self.prix, slot_value)
        embed = discord.Embed(
            title="✅ Objet créé !",
            description=f"**{self.nom}** (#{row['id']}) ajouté avec les valeurs par défaut pour les bonus/soin/stock.\nUtilise **Modifier** pour les ajuster si besoin.",
            color=0x27AE60
        )
        embed.set_footer(text="🌊 One Piece Bot • Dashboard")
        await interaction.response.edit_message(embed=embed, view=None)


class MarcheAjouterSlotView(discord.ui.View):
    def __init__(self, nom, description, prix, categorie, faction, rarete):
        super().__init__(timeout=300)
        self.add_item(MarcheSlotSelect(nom, description, prix, categorie, faction, rarete))


class MarcheCategoryPickSelect(discord.ui.Select):
    def __init__(self, mode):
        self.mode = mode
        options = [discord.SelectOption(label=c, value=c) for c in MARCHE_CATEGORIES]
        super().__init__(placeholder="Catégorie de l'objet...", options=options)

    async def callback(self, interaction: discord.Interaction):
        pool = get_pool()
        async with pool.acquire() as conn:
            rows = await conn.fetch(
                "SELECT id, nom FROM shop_items WHERE guild_id=$1 AND categorie=$2 ORDER BY nom LIMIT 25",
                interaction.guild_id, self.values[0]
            )
        if not rows:
            embed = discord.Embed(title="Aucun objet", description="Aucun objet dans cette catégorie.", color=0x2C3E50)
            await interaction.response.edit_message(embed=embed, view=DashboardMarcheView())
            return
        embed = discord.Embed(
            title=("✏️ Modifier" if self.mode == "modifier" else "🗑️ Retirer") + " un objet",
            description=f"Catégorie : **{self.values[0]}**\n\nChoisis l'objet.", color=0x2C3E50
        )
        embed.set_footer(text="🌊 One Piece Bot • Dashboard")
        await interaction.response.edit_message(embed=embed, view=MarcheItemPickView(self.mode, rows))


class MarcheCategoryPickView(discord.ui.View):
    def __init__(self, mode):
        super().__init__(timeout=300)
        self.add_item(MarcheCategoryPickSelect(mode))
        self.add_item(DashboardBackHomeButton())


class MarcheItemPickSelect(discord.ui.Select):
    def __init__(self, mode, rows):
        self.mode = mode
        options = [discord.SelectOption(label=r["nom"][:100], value=str(r["id"])) for r in rows]
        super().__init__(placeholder="Objet...", options=options)

    async def callback(self, interaction: discord.Interaction):
        item_id = int(self.values[0])
        if self.mode == "modifier":
            embed = discord.Embed(title="✏️ Modifier un objet", description="Choisis le champ à modifier.", color=0x2C3E50)
            embed.set_footer(text="🌊 One Piece Bot • Dashboard")
            await interaction.response.edit_message(embed=embed, view=MarcheChampPickView(item_id))
        else:
            pool = get_pool()
            async with pool.acquire() as conn:
                item = await conn.fetchrow("SELECT nom FROM shop_items WHERE id=$1", item_id)
                await conn.execute("UPDATE shop_items SET actif = FALSE WHERE id = $1", item_id)
            embed = discord.Embed(title="✅ Objet retiré", description=f"**{item['nom']}** a été retiré du marché.", color=0x27AE60)
            embed.set_footer(text="🌊 One Piece Bot • Dashboard")
            await interaction.response.edit_message(embed=embed, view=None)


class MarcheItemPickView(discord.ui.View):
    def __init__(self, mode, rows):
        super().__init__(timeout=300)
        self.add_item(MarcheItemPickSelect(mode, rows))
        self.add_item(DashboardBackHomeButton())


class MarcheChampSelect(discord.ui.Select):
    def __init__(self, item_id):
        self.item_id = item_id
        options = [discord.SelectOption(label=label, value=value) for label, value in CHAMP_CHOICES_DASH]
        super().__init__(placeholder="Champ à modifier...", options=options)

    async def callback(self, interaction: discord.Interaction):
        champ_key = self.values[0]
        champ_label = next(label for label, value in CHAMP_CHOICES_DASH if value == champ_key)
        await interaction.response.send_modal(MarcheValeurModal(self.item_id, champ_key, champ_label))


class MarcheChampPickView(discord.ui.View):
    def __init__(self, item_id):
        super().__init__(timeout=300)
        self.add_item(MarcheChampSelect(item_id))
        self.add_item(DashboardBackHomeButton())


class MarcheValeurModal(discord.ui.Modal):
    def __init__(self, item_id, champ_key, champ_label):
        super().__init__(title=f"Modifier : {champ_label}"[:45])
        self.item_id = item_id
        self.champ_key = champ_key
        self.valeur = discord.ui.TextInput(label=f"Nouvelle valeur ({champ_label})"[:45], max_length=200)
        self.add_item(self.valeur)

    async def on_submit(self, interaction: discord.Interaction):
        if self.champ_key in ("nom", "description"):
            parsed = self.valeur.value
        elif self.champ_key == "actif":
            parsed = self.valeur.value.lower() in ("true", "vrai", "oui", "1")
        else:
            try:
                parsed = int(self.valeur.value)
            except ValueError:
                await interaction.response.send_message("⛔ Cette valeur doit être un nombre entier.", ephemeral=True)
                return
        pool = get_pool()
        async with pool.acquire() as conn:
            await conn.execute(f"UPDATE shop_items SET {self.champ_key} = $2 WHERE id = $1", self.item_id, parsed)
            item = await conn.fetchrow("SELECT nom FROM shop_items WHERE id=$1", self.item_id)
        embed = discord.Embed(title="✅ Objet mis à jour", description=f"**{item['nom']}** modifié avec succès.", color=0x27AE60)
        embed.set_footer(text="🌊 One Piece Bot • Dashboard")
        await interaction.response.edit_message(embed=embed, view=None)


# ===== JOUEURS =====

class JoueurUserSelect(discord.ui.UserSelect):
    def __init__(self):
        super().__init__(placeholder="Choisis un joueur...", min_values=1, max_values=1)

    async def callback(self, interaction: discord.Interaction):
        membre = self.values[0]
        pool = get_pool()
        async with pool.acquire() as conn:
            player = await conn.fetchrow("SELECT * FROM players WHERE guild_id=$1 AND user_id=$2", interaction.guild_id, membre.id)
        if not player:
            embed = discord.Embed(title="👤 Joueurs", description=f"{membre.mention} n'a pas encore de personnage.", color=0x2C3E50)
            embed.set_footer(text="🌊 One Piece Bot • Dashboard")
            await interaction.response.edit_message(embed=embed, view=DashboardJoueursView())
            return
        embed = discord.Embed(
            title=f"👤 {membre.display_name}",
            description=f"Faction : **{player['faction']}**\nNiveau : **{player['niveau']}**\nBerrys : **{player['berrys']:,}฿**\nMer : **{player['mer']}**\n\nChoisis une action.",
            color=0x2C3E50
        )
        embed.set_footer(text="🌊 One Piece Bot • Dashboard")
        await interaction.response.edit_message(embed=embed, view=DashboardJoueurActionsView(membre))


class DashboardJoueursView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=180)
        self.add_item(JoueurUserSelect())
        self.add_item(DashboardBackHomeButton())


class JoueurFactionSelect(discord.ui.Select):
    def __init__(self, membre):
        self.membre = membre
        options = [discord.SelectOption(label=f, value=f) for f in ["Pirate", "Marine", "Révolutionnaire", "Civil"]]
        super().__init__(placeholder="Nouvelle faction...", options=options)

    async def callback(self, interaction: discord.Interaction):
        faction = self.values[0]
        pool = get_pool()
        async with pool.acquire() as conn:
            row = await conn.fetchrow("SELECT equipage_id, metier FROM players WHERE guild_id=$1 AND user_id=$2", interaction.guild_id, self.membre.id)
            async with conn.transaction():
                if row["equipage_id"] and faction != "Pirate":
                    await conn.execute("UPDATE players SET equipage_id = NULL, grade_equipage = NULL WHERE guild_id=$1 AND user_id=$2", interaction.guild_id, self.membre.id)
                if row["metier"] and faction != "Civil":
                    await conn.execute("UPDATE players SET metier = NULL, metier_xp = 0, metier_rang = 0 WHERE guild_id=$1 AND user_id=$2", interaction.guild_id, self.membre.id)
                await conn.execute("UPDATE players SET faction = $3 WHERE guild_id=$1 AND user_id=$2", interaction.guild_id, self.membre.id, faction)
        embed = discord.Embed(title="✅ Faction modifiée", description=f"Faction de {self.membre.mention} définie sur **{faction}**.", color=0x27AE60)
        embed.set_footer(text="🌊 One Piece Bot • Dashboard")
        await interaction.response.edit_message(embed=embed, view=None)


class JoueurFactionButton(discord.ui.Button):
    def __init__(self, membre):
        self.membre = membre
        super().__init__(label="Changer la faction", emoji="🔄", style=discord.ButtonStyle.primary)

    async def callback(self, interaction: discord.Interaction):
        embed = discord.Embed(title=f"🔄 Changer la faction de {self.membre.display_name}", description="Choisis la nouvelle faction.", color=0x2C3E50)
        embed.set_footer(text="🌊 One Piece Bot • Dashboard")
        view = discord.ui.View(timeout=180)
        view.add_item(JoueurFactionSelect(self.membre))
        await interaction.response.edit_message(embed=embed, view=view)


class JoueurResetConfirmButton(discord.ui.Button):
    def __init__(self, membre):
        self.membre = membre
        super().__init__(label="Confirmer la réinitialisation", emoji="💥", style=discord.ButtonStyle.danger)

    async def callback(self, interaction: discord.Interaction):
        pool = get_pool()
        async with pool.acquire() as conn:
            row = await conn.fetchrow("SELECT * FROM players WHERE guild_id=$1 AND user_id=$2", interaction.guild_id, self.membre.id)
            if row is None:
                await interaction.response.edit_message(content="Ce joueur n'a plus de fiche.", embed=None, view=None)
                return
            async with conn.transaction():
                led_crews = await conn.fetch("SELECT id FROM crews WHERE guild_id=$1 AND capitaine_id=$2", interaction.guild_id, self.membre.id)
                for crew in led_crews:
                    await conn.execute("UPDATE players SET equipage_id = NULL, grade_equipage = NULL WHERE guild_id=$1 AND equipage_id=$2", interaction.guild_id, crew["id"])
                    await conn.execute("DELETE FROM crews WHERE id = $1", crew["id"])
                await conn.execute("DELETE FROM inventory WHERE guild_id=$1 AND user_id=$2", interaction.guild_id, self.membre.id)
                await conn.execute("DELETE FROM players WHERE guild_id=$1 AND user_id=$2", interaction.guild_id, self.membre.id)
        embed = discord.Embed(title="💥 Fiche réinitialisée", description=f"La fiche de {self.membre.mention} a été entièrement réinitialisée.", color=0x27AE60)
        embed.set_footer(text="🌊 One Piece Bot • Dashboard")
        await interaction.response.edit_message(embed=embed, view=None)


class JoueurResetCancelButton(discord.ui.Button):
    def __init__(self):
        super().__init__(label="Annuler", style=discord.ButtonStyle.secondary)

    async def callback(self, interaction: discord.Interaction):
        embed = discord.Embed(title="👤 Joueurs", description="Réinitialisation annulée.", color=0x2C3E50)
        embed.set_footer(text="🌊 One Piece Bot • Dashboard")
        await interaction.response.edit_message(embed=embed, view=DashboardJoueursView())


class JoueurResetConfirmView(discord.ui.View):
    def __init__(self, membre):
        super().__init__(timeout=60)
        self.add_item(JoueurResetConfirmButton(membre))
        self.add_item(JoueurResetCancelButton())


class JoueurResetButton(discord.ui.Button):
    def __init__(self, membre):
        self.membre = membre
        super().__init__(label="Réinitialiser la fiche", emoji="💥", style=discord.ButtonStyle.danger)

    async def callback(self, interaction: discord.Interaction):
        embed = discord.Embed(
            title="⚠️ Confirmation requise",
            description=f"Es-tu sûr de vouloir **réinitialiser complètement** la fiche de {self.membre.mention} ? Cette action est irréversible.",
            color=0xC0392B
        )
        embed.set_footer(text="🌊 One Piece Bot • Dashboard")
        await interaction.response.edit_message(embed=embed, view=JoueurResetConfirmView(self.membre))


class JoueurXPModal(discord.ui.Modal, title="🧪 Ajouter de l'XP (test)"):
    def __init__(self, membre):
        super().__init__()
        self.membre = membre
        self.xp = discord.ui.TextInput(label="Montant d'XP à ajouter", placeholder="Ex : 50000 pour atteindre un haut niveau", max_length=8)
        self.add_item(self.xp)

    async def on_submit(self, interaction: discord.Interaction):
        try:
            montant = int(self.xp.value)
        except ValueError:
            await interaction.response.send_message("⛔ Doit être un nombre entier.", ephemeral=True)
            return
        niveaux_gagnes, nouveau_niveau = await add_xp(interaction.guild_id, self.membre.id, montant, montant // 2)
        description = f"{self.membre.mention} a reçu **{montant:,} XP**"
        description += f" et est passé au niveau **{nouveau_niveau}** !" if niveaux_gagnes > 0 else " (pas assez pour monter de niveau)."
        embed = discord.Embed(title="✅ XP ajoutée (test)", description=description, color=0x27AE60)
        embed.set_footer(text="🌊 One Piece Bot • Dashboard • Outil de test — utilise la vraie fonction de leveling")
        await interaction.response.edit_message(embed=embed, view=None)


class JoueurXPButton(discord.ui.Button):
    def __init__(self, membre):
        self.membre = membre
        super().__init__(label="Ajouter de l'XP", emoji="⭐", style=discord.ButtonStyle.success)

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.send_modal(JoueurXPModal(self.membre))


class JoueurNiveauModal(discord.ui.Modal, title="🧪 Définir le niveau (test)"):
    def __init__(self, membre):
        super().__init__()
        self.membre = membre
        self.niveau = discord.ui.TextInput(label="Niveau exact à définir", placeholder="Ex : 15", max_length=4)
        self.add_item(self.niveau)

    async def on_submit(self, interaction: discord.Interaction):
        try:
            niveau_val = int(self.niveau.value)
        except ValueError:
            await interaction.response.send_message("⛔ Doit être un nombre entier.", ephemeral=True)
            return
        if niveau_val < 1:
            await interaction.response.send_message("⛔ Le niveau doit être au moins 1.", ephemeral=True)
            return
        pool = get_pool()
        async with pool.acquire() as conn:
            await conn.execute("UPDATE players SET niveau = $3, xp = 0 WHERE guild_id=$1 AND user_id=$2", interaction.guild_id, self.membre.id, niveau_val)
        embed = discord.Embed(
            title="✅ Niveau défini (test)",
            description=(
                f"{self.membre.mention} est maintenant **niveau {niveau_val}** (XP remise à 0).\n\n"
                f"⚠️ Les stats de combat (Force/Défense/...) ne sont **pas recalculées automatiquement**, "
                f"seul le niveau change — pratique pour tester les accès liés au niveau (mers, quêtes...), "
                f"moins pour tester l'équilibrage du combat à ce niveau précis."
            ),
            color=0x27AE60
        )
        embed.set_footer(text="🌊 One Piece Bot • Dashboard • Outil de test")
        await interaction.response.edit_message(embed=embed, view=None)


class JoueurNiveauButton(discord.ui.Button):
    def __init__(self, membre):
        self.membre = membre
        super().__init__(label="Définir le niveau", emoji="📊", style=discord.ButtonStyle.danger)

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.send_modal(JoueurNiveauModal(self.membre))


class JoueurBerrysModal(discord.ui.Modal, title="🧪 Ajouter des Berrys (test)"):
    def __init__(self, membre):
        super().__init__()
        self.membre = membre
        self.montant = discord.ui.TextInput(label="Montant de Berrys à ajouter", max_length=8)
        self.add_item(self.montant)

    async def on_submit(self, interaction: discord.Interaction):
        try:
            montant = int(self.montant.value)
        except ValueError:
            await interaction.response.send_message("⛔ Doit être un nombre entier.", ephemeral=True)
            return
        pool = get_pool()
        async with pool.acquire() as conn:
            await conn.execute("UPDATE players SET berrys = berrys + $3 WHERE guild_id=$1 AND user_id=$2", interaction.guild_id, self.membre.id, montant)
        embed = discord.Embed(title="✅ Berrys ajoutés (test)", description=f"{self.membre.mention} a reçu **{montant:,}฿**.", color=0x27AE60)
        embed.set_footer(text="🌊 One Piece Bot • Dashboard • Outil de test")
        await interaction.response.edit_message(embed=embed, view=None)


class JoueurBerrysButton(discord.ui.Button):
    def __init__(self, membre):
        self.membre = membre
        super().__init__(label="Ajouter des Berrys", emoji="💰", style=discord.ButtonStyle.success)

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.send_modal(JoueurBerrysModal(self.membre))


class JoueurRetirerBerrysModal(discord.ui.Modal, title="🧪 Retirer des Berrys (test)"):
    def __init__(self, membre):
        super().__init__()
        self.membre = membre
        self.montant = discord.ui.TextInput(label="Montant de Berrys à retirer", max_length=8)
        self.add_item(self.montant)

    async def on_submit(self, interaction: discord.Interaction):
        try:
            montant = int(self.montant.value)
        except ValueError:
            await interaction.response.send_message("⛔ Doit être un nombre entier.", ephemeral=True)
            return
        pool = get_pool()
        async with pool.acquire() as conn:
            await conn.execute("UPDATE players SET berrys = GREATEST(0, berrys - $3) WHERE guild_id=$1 AND user_id=$2", interaction.guild_id, self.membre.id, montant)
            row = await conn.fetchrow("SELECT berrys FROM players WHERE guild_id=$1 AND user_id=$2", interaction.guild_id, self.membre.id)
        embed = discord.Embed(title="✅ Berrys retirés (test)", description=f"{self.membre.mention} a maintenant **{row['berrys']:,}฿**.", color=0x27AE60)
        embed.set_footer(text="🌊 One Piece Bot • Dashboard • Outil de test")
        await interaction.response.edit_message(embed=embed, view=None)


class JoueurRetirerBerrysButton(discord.ui.Button):
    def __init__(self, membre):
        self.membre = membre
        super().__init__(label="Retirer des Berrys", emoji="💸", style=discord.ButtonStyle.danger)

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.send_modal(JoueurRetirerBerrysModal(self.membre))


class JoueurTeleportSelect(discord.ui.Select):
    def __init__(self, membre):
        self.membre = membre
        options = [discord.SelectOption(label=f"{nom} (niv. {niv}+ normalement)", value=nom) for nom, niv, cout, end, ile in MERS]
        super().__init__(placeholder="Téléporter vers...", options=options)

    async def callback(self, interaction: discord.Interaction):
        nom_mer = self.values[0]
        mer_data = next((m for m in MERS if m[0] == nom_mer), None)
        ile_arrivee = mer_data[4] if mer_data else "Île de départ"
        pool = get_pool()
        async with pool.acquire() as conn:
            await conn.execute("UPDATE players SET mer = $3, ile = $4 WHERE guild_id=$1 AND user_id=$2", interaction.guild_id, self.membre.id, nom_mer, ile_arrivee)
        embed = discord.Embed(
            title="✅ Téléportation effectuée (test)",
            description=f"{self.membre.mention} est maintenant sur **{nom_mer}** ({ile_arrivee}) — sans condition de niveau ni coût, c'est un outil de test.",
            color=0x27AE60
        )
        embed.set_footer(text="🌊 One Piece Bot • Dashboard • Outil de test")
        await interaction.response.edit_message(embed=embed, view=None)


class JoueurTeleportButton(discord.ui.Button):
    def __init__(self, membre):
        self.membre = membre
        super().__init__(label="Téléporter (test)", emoji="🗺️", style=discord.ButtonStyle.success)

    async def callback(self, interaction: discord.Interaction):
        embed = discord.Embed(
            title=f"🗺️ Téléporter {self.membre.display_name}",
            description="Choisis la mer de destination — sans condition de niveau, sans coût, outil de test.",
            color=0x2C3E50
        )
        embed.set_footer(text="🌊 One Piece Bot • Dashboard • Outil de test")
        view = discord.ui.View(timeout=180)
        view.add_item(JoueurTeleportSelect(self.membre))
        await interaction.response.edit_message(embed=embed, view=view)


class DashboardJoueurActionsView(discord.ui.View):
    def __init__(self, membre):
        super().__init__(timeout=180)
        self.add_item(JoueurXPButton(membre))
        self.add_item(JoueurNiveauButton(membre))
        self.add_item(JoueurBerrysButton(membre))
        self.add_item(JoueurRetirerBerrysButton(membre))
        self.add_item(JoueurTeleportButton(membre))
        self.add_item(JoueurFactionButton(membre))
        self.add_item(JoueurResetButton(membre))
        self.add_item(DashboardBackHomeButton())


# ===== PERMISSIONS =====

async def build_permissions_embed(guild_id: int):
    pool = get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch("SELECT command_group, role_id FROM guild_command_roles WHERE guild_id=$1", guild_id)
    if not rows:
        description = "Aucune permission personnalisée définie. Par défaut, seuls les administrateurs peuvent utiliser les commandes de modération."
    else:
        description = "\n".join(f"<@&{r['role_id']}> → **{r['command_group']}**" for r in rows)
    embed = discord.Embed(title="🔑 Permissions", description=description, color=0x2C3E50)
    embed.set_footer(text="🌊 One Piece Bot • Dashboard")
    return embed


class PermissionRoleSelect(discord.ui.RoleSelect):
    def __init__(self):
        super().__init__(placeholder="Choisis un rôle à autoriser (Modération)...", min_values=1, max_values=1)

    async def callback(self, interaction: discord.Interaction):
        role = self.values[0]
        pool = get_pool()
        async with pool.acquire() as conn:
            await conn.execute(
                "INSERT INTO guild_command_roles (guild_id, command_group, role_id) VALUES ($1,'mod',$2) ON CONFLICT DO NOTHING",
                interaction.guild_id, role.id
            )
        embed = discord.Embed(title="✅ Permission ajoutée", description=f"{role.mention} peut désormais utiliser les commandes de **Modération**.", color=0x27AE60)
        embed.set_footer(text="🌊 One Piece Bot • Dashboard")
        await interaction.response.edit_message(embed=embed, view=DashboardPermissionsView())


class PermissionAutoriserButton(discord.ui.Button):
    def __init__(self):
        super().__init__(label="Autoriser un rôle", emoji="➕", style=discord.ButtonStyle.success)

    async def callback(self, interaction: discord.Interaction):
        embed = discord.Embed(title="🔑 Autoriser un rôle", description="Choisis le rôle à autoriser pour les commandes de Modération.", color=0x2C3E50)
        embed.set_footer(text="🌊 One Piece Bot • Dashboard")
        view = discord.ui.View(timeout=180)
        view.add_item(PermissionRoleSelect())
        await interaction.response.edit_message(embed=embed, view=view)


class PermissionRetirerSelect(discord.ui.Select):
    def __init__(self, rows):
        options = [discord.SelectOption(label=f"Rôle #{r['role_id']}", value=str(r["role_id"])) for r in rows[:25]]
        super().__init__(placeholder="Choisis le rôle à retirer...", options=options)

    async def callback(self, interaction: discord.Interaction):
        role_id = int(self.values[0])
        pool = get_pool()
        async with pool.acquire() as conn:
            await conn.execute("DELETE FROM guild_command_roles WHERE guild_id=$1 AND role_id=$2", interaction.guild_id, role_id)
        embed = discord.Embed(title="✅ Permission retirée", description=f"<@&{role_id}> n'a plus accès aux commandes de Modération.", color=0x27AE60)
        embed.set_footer(text="🌊 One Piece Bot • Dashboard")
        await interaction.response.edit_message(embed=embed, view=DashboardPermissionsView())


class PermissionRetirerButton(discord.ui.Button):
    def __init__(self):
        super().__init__(label="Retirer un rôle", emoji="➖", style=discord.ButtonStyle.danger)

    async def callback(self, interaction: discord.Interaction):
        pool = get_pool()
        async with pool.acquire() as conn:
            rows = await conn.fetch("SELECT role_id FROM guild_command_roles WHERE guild_id=$1", interaction.guild_id)
        if not rows:
            await interaction.response.send_message("Aucune permission à retirer.", ephemeral=True)
            return
        embed = discord.Embed(title="🔑 Retirer un rôle", description="Choisis le rôle à retirer.", color=0x2C3E50)
        embed.set_footer(text="🌊 One Piece Bot • Dashboard")
        view = discord.ui.View(timeout=180)
        view.add_item(PermissionRetirerSelect(rows))
        await interaction.response.edit_message(embed=embed, view=view)


class DashboardPermissionsView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=180)
        self.add_item(PermissionAutoriserButton())
        self.add_item(PermissionRetirerButton())
        self.add_item(DashboardBackHomeButton())


# ===== PARAMÈTRES AVANCÉS (Reset global) =====

class ResetGlobalConfirmButton(discord.ui.Button):
    def __init__(self):
        super().__init__(label="Confirmer la réinitialisation totale", emoji="💥", style=discord.ButtonStyle.danger)

    async def callback(self, interaction: discord.Interaction):
        pool = get_pool()
        async with pool.acquire() as conn:
            await conn.execute("DELETE FROM guild_config WHERE guild_id = $1", interaction.guild_id)
        embed = discord.Embed(
            title="💥 Configuration réinitialisée",
            description="Tous les salons et la langue ont été remis à zéro. Les autres réglages (automod, logs, bienvenue, marché) ne sont pas affectés.",
            color=0x27AE60
        )
        embed.set_footer(text="🌊 One Piece Bot • Dashboard")
        await interaction.response.edit_message(embed=embed, view=None)


class ResetGlobalCancelButton(discord.ui.Button):
    def __init__(self):
        super().__init__(label="Annuler", style=discord.ButtonStyle.secondary)

    async def callback(self, interaction: discord.Interaction):
        embed = discord.Embed(title="⚙️ Paramètres avancés", description="Réinitialisation annulée.", color=0x2C3E50)
        embed.set_footer(text="🌊 One Piece Bot • Dashboard")
        await interaction.response.edit_message(embed=embed, view=DashboardAvanceView())


class ResetGlobalButton(discord.ui.Button):
    def __init__(self):
        super().__init__(label="Réinitialiser toute la config des salons", emoji="💥", style=discord.ButtonStyle.danger)

    async def callback(self, interaction: discord.Interaction):
        embed = discord.Embed(
            title="⚠️ Confirmation requise",
            description="Es-tu sûr de vouloir **réinitialiser tous les salons configurés** et la langue ? Cette action est irréversible (les autres réglages restent intacts).",
            color=0xC0392B
        )
        embed.set_footer(text="🌊 One Piece Bot • Dashboard")
        view = discord.ui.View(timeout=60)
        view.add_item(ResetGlobalConfirmButton())
        view.add_item(ResetGlobalCancelButton())
        await interaction.response.edit_message(embed=embed, view=view)


class DashboardAvanceView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=180)
        self.add_item(ResetGlobalButton())
        self.add_item(DashboardBackHomeButton())


# ===== ACCUEIL (menu principal) =====

CATEGORIES = {
    "salons": "🗺️ Salons",
    "moderation": "🛡️ Modération & Automod",
    "logs": "📋 Logs",
    "bienvenue": "👋 Bienvenue",
    "marche": "🛒 Marché",
    "joueurs": "👤 Joueurs",
    "boss": "👑 Boss mondial",
    "permissions": "🔑 Permissions",
    "langue": "🌐 Langue",
    "avance": "⚙️ Paramètres avancés",
}


class DashboardCategorySelect(discord.ui.Select):
    def __init__(self):
        options = [discord.SelectOption(label=label, value=key) for key, label in CATEGORIES.items()]
        super().__init__(placeholder="Choisis une section à gérer...", options=options, custom_id="dashboard_select")

    async def callback(self, interaction: discord.Interaction):
        if self.values[0] == "salons":
            embed = await build_salons_overview_embed(interaction.guild_id)
            await interaction.response.edit_message(embed=embed, view=DashboardSalonsOverviewView())
        elif self.values[0] == "langue":
            embed = await build_langue_embed(interaction.guild_id)
            await interaction.response.edit_message(embed=embed, view=DashboardLangueView())
        elif self.values[0] == "boss":
            embed = await build_boss_embed(interaction.guild_id)
            await interaction.response.edit_message(embed=embed, view=DashboardBossView())
        elif self.values[0] == "moderation":
            embed = await build_moderation_embed(interaction.guild_id)
            await interaction.response.edit_message(embed=embed, view=await DashboardModerationView.create(interaction.guild_id))
        elif self.values[0] == "logs":
            embed = await build_logs_embed(interaction.guild_id)
            await interaction.response.edit_message(embed=embed, view=await DashboardLogsView.create(interaction.guild_id))
        elif self.values[0] == "bienvenue":
            embed = await build_bienvenue_embed(interaction.guild_id)
            await interaction.response.edit_message(embed=embed, view=await DashboardBienvenueView.create(interaction.guild_id))
        elif self.values[0] == "marche":
            embed = await build_marche_home_embed(interaction.guild_id)
            await interaction.response.edit_message(embed=embed, view=DashboardMarcheView())
        elif self.values[0] == "joueurs":
            embed = discord.Embed(title="👤 Joueurs", description="Choisis un joueur à gérer.", color=0x2C3E50)
            embed.set_footer(text="🌊 One Piece Bot • Dashboard")
            await interaction.response.edit_message(embed=embed, view=DashboardJoueursView())
        elif self.values[0] == "permissions":
            embed = await build_permissions_embed(interaction.guild_id)
            await interaction.response.edit_message(embed=embed, view=DashboardPermissionsView())
        elif self.values[0] == "avance":
            embed = discord.Embed(title="⚙️ Paramètres avancés", description="Actions de maintenance globales.", color=0x2C3E50)
            embed.set_footer(text="🌊 One Piece Bot • Dashboard")
            await interaction.response.edit_message(embed=embed, view=DashboardAvanceView())


class DashboardHomeView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=180)
        self.add_item(DashboardCategorySelect())


@app_commands.command(name="dashboard", description="Ouvrir le tableau de bord d'administration")
@app_commands.default_permissions(administrator=True)
async def dashboard(interaction: discord.Interaction):
    await interaction.response.defer(ephemeral=True)
    stats = await get_overview_stats(interaction.guild_id)
    embed = build_home_embed(stats, interaction.guild.name)
    await interaction.followup.send(embed=embed, view=DashboardHomeView(), ephemeral=True)


def setup_dashboard_commands(bot):
    bot.tree.add_command(dashboard)
