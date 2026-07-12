import discord
from discord import app_commands
from utils.players import get_player, create_player, xp_requis
from utils.channel_check import require_salon
from utils.succes import record_mer_visitee

FACTION_COLORS = {
    "Pirate": 0x8E44AD,
    "Marine": 0x3498DB,
    "Révolutionnaire": 0xC0392B,
    "Civil": 0x95A5A6,
}

FACTION_EMOJIS = {
    "Pirate": "🏴‍☠️",
    "Marine": "⚓",
    "Révolutionnaire": "🔥",
    "Civil": "🏘️",
}

ESPACE = "\u200b"

@app_commands.command(name="commencer", description="Creer ton personnage et debuter l aventure")
@app_commands.choices(faction=[
    app_commands.Choice(name="Pirate - liberte, primes et tresors", value="Pirate"),
    app_commands.Choice(name="Marine - justice, grades et patrouilles", value="Marine"),
    app_commands.Choice(name="Revolutionnaire - l ombre et la revolte", value="Révolutionnaire"),
    app_commands.Choice(name="Civil - artisanat, metiers et commerce", value="Civil"),
])
@require_salon("salon_creation")
async def commencer(interaction: discord.Interaction, faction: app_commands.Choice[str]):
    await interaction.response.defer()
    existing = await get_player(interaction.guild_id, interaction.user.id)
    if existing:
        await interaction.followup.send("Tu as deja un personnage ! Consulte-le avec /profil")
        return

    await create_player(interaction.guild_id, interaction.user.id, faction.value)
    await record_mer_visitee(interaction.guild_id, interaction.user.id, "East Blue")

    embed = discord.Embed(
        title="🌊 Bienvenue dans la Grande Aventure !",
        description=(
            f"{interaction.user.mention}, ton periple commence a **East Blue** en tant que **{faction.name}**.\n\n"
            "Tu demarres avec **100 Berrys**\n"
            "Consulte ton profil avec /profil\n"
            "L aventure ne fait que commencer..."
        ),
        color=FACTION_COLORS[faction.value]
    )
    embed.set_thumbnail(url=interaction.user.display_avatar.url)
    embed.set_footer(text="🌊 One Piece Bot • Nouvelle aventure")
    await interaction.followup.send(embed=embed)


@app_commands.command(name="profil", description="Afficher le profil d un joueur")
@app_commands.describe(membre="Le membre dont tu veux voir le profil (toi par defaut)")
async def profil(interaction: discord.Interaction, membre: discord.Member = None):
    await interaction.response.defer()
    cible = membre or interaction.user
    player = await get_player(interaction.guild_id, cible.id)
    if player is None:
        if cible == interaction.user:
            await interaction.followup.send("Tu n as pas encore de personnage ! Lance /commencer pour debuter l aventure")
        else:
            await interaction.followup.send(f"{cible.display_name} n a pas encore de personnage.")
        return

    faction = player["faction"]
    color = FACTION_COLORS.get(faction, 0x95A5A6)
    emoji = FACTION_EMOJIS.get(faction, "🏘️")

    embed = discord.Embed(
        title=f"{emoji} Profil de {cible.display_name}",
        color=color
    )
    embed.set_thumbnail(url=cible.display_avatar.url)

    xp_prochain = xp_requis(player["niveau"])
    embed.add_field(
        name="📈 Progression",
        value=(
            f"Niveau **{player['niveau']}**\n"
            f"XP : {player['xp']}/{xp_prochain}\n"
            f"Titre : {player['titre'] or 'Aucun'}\n"
            f"Metier : {player['metier'] or 'Aucun'}\n{ESPACE}"
        ),
        inline=True
    )

    embed.add_field(
        name="💰 Richesse",
        value=(
            f"Berrys : **{player['berrys']:,}** ฿\n"
            f"Banque : {player['banque']:,} ฿\n"
            f"Prime : ☠️ {player['prime']:,} ฿\n{ESPACE}"
        ),
        inline=True
    )

    embed.add_field(
        name="⚔️ Combat",
        value=(
            f"PV : {player['pv']}/{player['pv_max']}\n"
            f"Endurance : {player['endurance']}/{player['endurance_max']}\n"
            f"Force {player['force']} - Def {player['defense']}\n"
            f"Vit {player['vitesse']} - Agi {player['agilite']}\n{ESPACE}"
        ),
        inline=True
    )

    fruit = player["fruit"] or "Aucun"
    eveil = " (eveille)" if player["fruit_eveil"] else ""
    haki_parts = []
    if player["haki_armement"] > 0:
        haki_parts.append(f"Armement {player['haki_armement']}")
    if player["haki_observation"] > 0:
        haki_parts.append(f"Observation {player['haki_observation']}")
    if player["haki_rois"] > 0:
        haki_parts.append(f"Rois {player['haki_rois']}")
    haki = " - ".join(haki_parts) if haki_parts else "Non eveille"

    embed.add_field(
        name="✨ Pouvoirs",
        value=f"Fruit : {fruit}{eveil}\nHaki : {haki}\n{ESPACE}",
        inline=True
    )

    embed.add_field(
        name="🗺️ Position",
        value=f"Mer : {player['mer']}\nIle : {player['ile']}\n{ESPACE}",
        inline=True
    )

    equipage = "Aucun"
    if player["equipage_id"]:
        grade = f" ({player['grade_equipage']})" if player["grade_equipage"] else ""
        equipage = f"ID {player['equipage_id']}{grade}"
    embed.add_field(
        name="🏴‍☠️ Equipage",
        value=f"{equipage}\nFaction : {faction}\n{ESPACE}",
        inline=True
    )

    embed.add_field(
        name="🌟 Renommée",
        value=f"Notoriété : {player['notoriete']:,} pts\n{ESPACE}",
        inline=True
    )

    embed.set_footer(text=f"🌊 One Piece Bot • Aventurier depuis le {player['cree_le'].strftime('%d/%m/%Y')}")
    await interaction.followup.send(embed=embed)


def setup_profil_commands(bot):
    bot.tree.add_command(commencer)
    bot.tree.add_command(profil)
