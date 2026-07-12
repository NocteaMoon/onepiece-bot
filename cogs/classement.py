import discord
from discord import app_commands
from database.db import get_pool
from utils.channel_check import require_salon

CREW_TYPE_EMOJIS = {"Pirate": "🏴‍☠️", "Marine": "⚓", "Revolution": "🔥", "Guilde": "🧵"}


async def embed_richesse(guild_id, guild):
    pool = get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            "SELECT user_id, berrys, banque FROM players WHERE guild_id=$1 ORDER BY (berrys+banque) DESC LIMIT 10",
            guild_id
        )
    embed = discord.Embed(title="💰 Classement — Richesse", color=0xF4C430)
    lignes = []
    for i, r in enumerate(rows):
        member = guild.get_member(r["user_id"])
        nom = member.display_name if member else f"Joueur {r['user_id']}"
        total = r["berrys"] + r["banque"]
        lignes.append(f"**{i+1}.** {nom} — {total:,}฿")
    embed.description = "\n".join(lignes) if lignes else "Aucune donnée pour l'instant."
    embed.set_footer(text="🌊 One Piece Bot • Classements")
    return embed


async def embed_prime(guild_id, guild):
    pool = get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            "SELECT user_id, prime FROM players WHERE guild_id=$1 ORDER BY prime DESC LIMIT 10",
            guild_id
        )
    embed = discord.Embed(title="☠️ Classement — Prime", color=0x1A1A1A)
    lignes = []
    for i, r in enumerate(rows):
        member = guild.get_member(r["user_id"])
        nom = member.display_name if member else f"Joueur {r['user_id']}"
        lignes.append(f"**{i+1}.** {nom} — ☠️ {r['prime']:,}฿")
    embed.description = "\n".join(lignes) if lignes else "Aucune donnée pour l'instant."
    embed.set_footer(text="🌊 One Piece Bot • Classements")
    return embed


async def embed_niveau(guild_id, guild):
    pool = get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            "SELECT user_id, niveau FROM players WHERE guild_id=$1 ORDER BY niveau DESC, xp DESC LIMIT 10",
            guild_id
        )
    embed = discord.Embed(title="📈 Classement — Niveau", color=0x27AE60)
    lignes = []
    for i, r in enumerate(rows):
        member = guild.get_member(r["user_id"])
        nom = member.display_name if member else f"Joueur {r['user_id']}"
        lignes.append(f"**{i+1}.** {nom} — Niveau {r['niveau']}")
    embed.description = "\n".join(lignes) if lignes else "Aucune donnée pour l'instant."
    embed.set_footer(text="🌊 One Piece Bot • Classements")
    return embed


async def embed_notoriete(guild_id, guild):
    pool = get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            "SELECT user_id, notoriete FROM players WHERE guild_id=$1 ORDER BY notoriete DESC LIMIT 10",
            guild_id
        )
    embed = discord.Embed(title="🌟 Classement — Notoriété", color=0xF39C12)
    lignes = []
    for i, r in enumerate(rows):
        member = guild.get_member(r["user_id"])
        nom = member.display_name if member else f"Joueur {r['user_id']}"
        lignes.append(f"**{i+1}.** {nom} — {r['notoriete']:,} pts")
    embed.description = "\n".join(lignes) if lignes else "Aucune donnée pour l'instant."
    embed.set_footer(text="🌊 One Piece Bot • Classements")
    return embed


async def embed_organisations(guild_id, guild):
    pool = get_pool()
    async with pool.acquire() as conn:
        crews = await conn.fetch("SELECT * FROM crews WHERE guild_id=$1", guild_id)
        result = []
        for c in crews:
            row = await conn.fetchrow(
                "SELECT COUNT(*) AS nb, COALESCE(SUM(prime),0) AS prime_totale FROM players WHERE guild_id=$1 AND equipage_id=$2",
                guild_id, c["id"]
            )
            result.append((c["nom"], c["type"], row["nb"], row["prime_totale"]))
    result.sort(key=lambda x: x[3], reverse=True)
    result = result[:10]

    embed = discord.Embed(title="🏴‍☠️ Classement — Organisations", color=0x8E44AD)
    lignes = []
    for i, (nom, type_, nb, prime_totale) in enumerate(result):
        emoji = CREW_TYPE_EMOJIS.get(type_, "🏴‍☠️")
        lignes.append(f"**{i+1}.** {emoji} {nom} — {nb} membre(s) — ☠️ {prime_totale:,}฿")
    embed.description = "\n".join(lignes) if lignes else "Aucune organisation fondée pour l'instant."
    embed.set_footer(text="🌊 One Piece Bot • Classements")
    return embed


CATEGORIES = {
    "richesse": embed_richesse,
    "prime": embed_prime,
    "niveau": embed_niveau,
    "notoriete": embed_notoriete,
    "organisations": embed_organisations,
}


class ClassementSelect(discord.ui.Select):
    def __init__(self):
        options = [
            discord.SelectOption(label="Richesse", value="richesse", emoji="💰"),
            discord.SelectOption(label="Prime", value="prime", emoji="☠️"),
            discord.SelectOption(label="Niveau", value="niveau", emoji="📈"),
            discord.SelectOption(label="Notoriété", value="notoriete", emoji="🌟"),
            discord.SelectOption(label="Organisations", value="organisations", emoji="🏴‍☠️"),
        ]
        super().__init__(placeholder="Choisis un classement...", options=options, custom_id="classement_select")

    async def callback(self, interaction: discord.Interaction):
        embed = await CATEGORIES[self.values[0]](interaction.guild_id, interaction.guild)
        await interaction.response.edit_message(embed=embed, view=self.view)


class ClassementView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=120)
        self.add_item(ClassementSelect())


@app_commands.command(name="classement", description="Voir les classements du serveur")
@require_salon("salon_classements")
async def classement(interaction: discord.Interaction):
    await interaction.response.defer()
    embed = await embed_richesse(interaction.guild_id, interaction.guild)
    await interaction.followup.send(embed=embed, view=ClassementView())


def setup_classement_commands(bot):
    bot.tree.add_command(classement)
