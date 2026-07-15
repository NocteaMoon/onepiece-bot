import discord
from discord import app_commands
from database.db import get_pool
from cogs.admin import SALON_DEFINITIONS
from cogs.boss_mondial import get_active_boss

AUTOMOD_COLUMNS = ["anti_spam", "anti_liens", "anti_insultes", "anti_raid", "anti_mention", "anti_pub", "anti_alt", "anti_bot"]


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


class DashboardBackButton(discord.ui.Button):
    def __init__(self):
        super().__init__(label="Retour à l'accueil", emoji="🏠", style=discord.ButtonStyle.secondary)

    async def callback(self, interaction: discord.Interaction):
        stats = await get_overview_stats(interaction.guild_id)
        embed = build_home_embed(stats, interaction.guild.name)
        await interaction.response.edit_message(embed=embed, view=DashboardHomeView())


class DashboardHomeView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=180)
        self.add_item(DashboardCategorySelect())


class DashboardSectionView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=180)
        self.add_item(DashboardBackButton())


@app_commands.command(name="dashboard", description="Ouvrir le tableau de bord d'administration")
@app_commands.default_permissions(administrator=True)
async def dashboard(interaction: discord.Interaction):
    await interaction.response.defer(ephemeral=True)
    stats = await get_overview_stats(interaction.guild_id)
    embed = build_home_embed(stats, interaction.guild.name)
    await interaction.followup.send(embed=embed, view=DashboardHomeView(), ephemeral=True)


def setup_dashboard_commands(bot):
    bot.tree.add_command(dashboard)
