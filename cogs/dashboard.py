import discord
from discord import app_commands
from database.db import get_pool
from cogs.admin import SALON_DEFINITIONS
from cogs.boss_mondial import get_active_boss

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


async def get_overview_stats(guild_id: int):
    pool = get_pool()
    async with pool.acquire() as conn:
        config_row = await conn.fetchrow("SELECT * FROM guild_config WHERE guild_id = $1", guild_id)
        automod_row = await conn.fetchrow("SELECT * FROM automod_config WHERE guild_id = $1", guild_id)
        nb_items = await conn.fetchval("SELECT COUNT(*) FROM shop_items WHERE guild_id = $1 AND actif = TRUE", guild_id)
        nb_permissions = await conn.fetchval("SELECT COUNT(*) FROM guild_command_roles WHERE guild_id = $1", guild_id)

    if config_row:
        nb_salons = sum(1 for _, value in SALON_DEFINITIONS if config_row[value])
        langue = config_row["lang"]
    else:
        nb_salons = 0
        langue = "fr"

    if automod_row:
        nb_automod_actifs = sum(1 for col in AUTOMOD_COLUMNS if automod_row[col])
    else:
        nb_automod_actifs = 0

    boss_actif = await get_active_boss(guild_id)

    return {
        "nb_salons": nb_salons,
        "total_salons": len(SALON_DEFINITIONS),
        "langue": langue,
        "nb_items": nb_items or 0,
        "nb_permissions": nb_permissions or 0,
        "nb_automod_actifs": nb_automod_actifs,
        "total_automod": len(AUTOMOD_COLUMNS),
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
    embed.add_field(name="🔑 Permissions", value=f"{stats['nb_permissions']} règle(s) personnalisée(s)", inline=True)
    embed.add_field(name="👑 Boss mondial", value="🟢 Actif" if stats["boss_actif"] else "⚪ Aucun en cours", inline=True)
    embed.set_footer(text="🌊 One Piece Bot • Dashboard")
    return embed


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
            channel_types=[discord.ChannelType.text],
            min_values=1, max_values=1
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


class DashboardBackHomeButton(discord.ui.Button):
    def __init__(self):
        super().__init__(label="Accueil", emoji="🏠", style=discord.ButtonStyle.secondary)

    async def callback(self, interaction: discord.Interaction):
        stats = await get_overview_stats(interaction.guild_id)
        embed = build_home_embed(stats, interaction.guild.name)
        await interaction.response.edit_message(embed=embed, view=DashboardHomeView())


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
        super().__init__(placeholder="Choisis le type de salon à configurer...", options=options, custom_id=f"dash_salon_type_{category_key}")

    async def callback(self, interaction: discord.Interaction):
        salon_column = self.values[0]
        salon_label = LABEL_BY_COLUMN.get(salon_column, salon_column)
        embed = discord.Embed(
            title=f"🗺️ Configurer : {salon_label}",
            description="Choisis le salon Discord ci-dessous.",
            color=0x2C3E50
        )
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
        super().__init__(placeholder="Choisis une catégorie de salons...", options=options, custom_id="dash_salon_cat")

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


# ===== ACCUEIL =====

CATEGORIES = {
    "salons": "🗺️ Salons",
    "moderation": "🛡️ Modération & Automod",
    "marche": "🛒 Marché",
    "joueurs": "👤 Joueurs",
    "boss": "👑 Boss mondial",
    "permissions": "🔑 Permissions",
    "langue": "🌐 Langue",
}


class DashboardCategorySelect(discord.ui.Select):
    def __init__(self):
        options = [discord.SelectOption(label=label, value=key) for key, label in CATEGORIES.items()]
        super().__init__(placeholder="Choisis une section à gérer...", options=options, custom_id="dashboard_select")

    async def callback(self, interaction: discord.Interaction):
        if self.values[0] == "salons":
            embed = await build_salons_overview_embed(interaction.guild_id)
            await interaction.response.edit_message(embed=embed, view=DashboardSalonsOverviewView())
            return

        label = CATEGORIES[self.values[0]]
        embed = discord.Embed(
            title=label,
            description=(
                "🚧 Cette section du Dashboard sera bâtie dans une prochaine passe.\n\n"
                "En attendant, la commande `/config` équivalente reste pleinement fonctionnelle."
            ),
            color=0x95A5A6
        )
        embed.set_footer(text="🌊 One Piece Bot • Dashboard")
        await interaction.response.edit_message(embed=embed, view=DashboardSectionView())


class DashboardSectionView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=180)
        self.add_item(DashboardCategorySelect())
        self.add_item(DashboardBackHomeButton())


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
