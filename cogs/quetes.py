import discord
from discord import app_commands
from utils.players import get_player, add_xp
from utils.channel_check import require_salon
from utils.announcements import announce_level_up
from utils.quetes import (
    get_quests, claim_daily_weekly,
    get_main_quest, claim_main_quest,
    get_active_secondaires, get_available_secondaires, accept_secondaire, abandon_secondaire, claim_secondaire,
)
from data.quetes import OBJECTIFS
from data.quetes_principales import QUETES_PRINCIPALES
from data.quetes_secondaires import QUETES_SECONDAIRES

PERIODE_LABELS = {"daily": "Quêtes journalières", "weekly": "Quêtes hebdomadaires"}

quetes_group = app_commands.Group(name="quetes", description="Toutes tes quêtes : journalières, principales et secondaires")


def barre(progres, cible, taille=10):
    rempli = round(progres / cible * taille) if cible > 0 else 0
    rempli = min(taille, rempli)
    return "🟩" * rempli + "⬜" * (taille - rempli)


class JournalieresView(discord.ui.View):
    def __init__(self, guild_id, user_id):
        super().__init__(timeout=60)
        self.guild_id = guild_id
        self.user_id = user_id

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("⛔ Ce ne sont pas tes quêtes !", ephemeral=True)
            return False
        return True

    @discord.ui.button(label="Réclamer les récompenses", emoji="🎁", style=discord.ButtonStyle.success)
    async def reclamer(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        nb, berrys, xp = await claim_daily_weekly(self.guild_id, self.user_id)
        if nb == 0:
            await interaction.followup.send("Aucune quête terminée à réclamer pour l'instant.", ephemeral=True)
            return
        niveaux_gagnes, nouveau_niveau = (0, None)
        if xp > 0:
            niveaux_gagnes, nouveau_niveau = await add_xp(self.guild_id, self.user_id, xp, xp // 2)
        await interaction.followup.send(f"🎁 {nb} quête(s) réclamée(s) : **+{berrys:,}฿** et **+{xp} XP** !", ephemeral=True)
        if niveaux_gagnes > 0:
            await announce_level_up(interaction, interaction.user, nouveau_niveau)


@quetes_group.command(name="journalieres", description="Voir tes quêtes journalières et hebdomadaires")
@require_salon("salon_quetes")
async def quetes_journalieres(interaction: discord.Interaction):
    await interaction.response.defer()
    player = await get_player(interaction.guild_id, interaction.user.id)
    if player is None:
        await interaction.followup.send("Tu n'as pas encore de personnage ! Lance `/commencer` pour débuter l'aventure 🏴‍☠️")
        return

    rows = await get_quests(interaction.guild_id, interaction.user.id)
    embed = discord.Embed(title="📜 Quêtes journalières & hebdomadaires", color=0xD4A017)
    for periode in ["daily", "weekly"]:
        lignes = []
        for r in rows:
            if r["periode"] != periode:
                continue
            data = OBJECTIFS[r["objectif_code"]]
            label = data["label"].format(cible=r["cible"])
            statut = "✅" if r["reclame"] else ("🎉" if r["progres"] >= r["cible"] else "")
            lignes.append(f"{statut} {label}\n{barre(r['progres'], r['cible'])} {r['progres']}/{r['cible']}")
        if lignes:
            embed.add_field(name=PERIODE_LABELS[periode], value="\n\n".join(lignes), inline=False)
    embed.set_footer(text="🌊 One Piece Bot • Quêtes")
    await interaction.followup.send(embed=embed, view=JournalieresView(interaction.guild_id, interaction.user.id))


class PrincipaleView(discord.ui.View):
    def __init__(self, guild_id, user_id):
        super().__init__(timeout=60)
        self.guild_id = guild_id
        self.user_id = user_id

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("⛔ Ce n'est pas ta quête !", ephemeral=True)
            return False
        return True

    @discord.ui.button(label="Réclamer et continuer l'aventure", emoji="🏆", style=discord.ButtonStyle.success)
    async def reclamer(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        resultat = await claim_main_quest(self.guild_id, self.user_id)
        if resultat is None:
            await interaction.followup.send("Cette quête n'est pas encore terminée.", ephemeral=True)
            return
        titre_quete, berrys, xp, titre_debloque = resultat
        niveaux_gagnes, nouveau_niveau = await add_xp(self.guild_id, self.user_id, xp, xp // 2)

        message = f"🏆 **{titre_quete}** terminée ! +{berrys:,}฿, +{xp} XP"
        if titre_debloque:
            message += f"\n👑 Nouveau titre débloqué : **{titre_debloque}** !"
        await interaction.followup.send(message, ephemeral=True)

        if niveaux_gagnes > 0:
            await announce_level_up(interaction, interaction.user, nouveau_niveau)


@quetes_group.command(name="principale", description="Voir ta quête principale actuelle")
@require_salon("salon_quetes")
async def quetes_principale(interaction: discord.Interaction):
    await interaction.response.defer()
    player = await get_player(interaction.guild_id, interaction.user.id)
    if player is None:
        await interaction.followup.send("Tu n'as pas encore de personnage ! Lance `/commencer` pour débuter l'aventure 🏴‍☠️")
        return

    row = await get_main_quest(interaction.guild_id, interaction.user.id)
    if row is None:
        await interaction.followup.send("🎉 Tu as terminé toutes les quêtes principales disponibles pour l'instant ! De nouveaux chapitres arriveront bientôt.")
        return

    quete = next((q for q in QUETES_PRINCIPALES if str(q[0]) == row["ref_id"]), None)
    titre, description, berrys, xp, titre_debloque = quete[1], quete[2], quete[5], quete[6], quete[8]
    numero = QUETES_PRINCIPALES.index(quete) + 1

    embed = discord.Embed(title=f"📖 Chapitre {numero}/{len(QUETES_PRINCIPALES)} — {titre}", description=description, color=0xE67E22)
    embed.add_field(name="Objectif", value=f"{barre(row['progres'], row['cible'])} {row['progres']}/{row['cible']}", inline=False)
    embed.add_field(name="Récompense", value=f"{berrys:,}฿ • {xp} XP" + (f" • Titre : {titre_debloque}" if titre_debloque else ""), inline=False)
    embed.set_footer(text="🌊 One Piece Bot • Quête principale")

    if row["progres"] >= row["cible"]:
        await interaction.followup.send(embed=embed, view=PrincipaleView(interaction.guild_id, interaction.user.id))
    else:
        await interaction.followup.send(embed=embed)


class SecondaireClaimButton(discord.ui.Button):
    def __init__(self, guild_id, user_id, quest_id, titre):
        super().__init__(label=f"Réclamer : {titre[:60]}", emoji="🎁", style=discord.ButtonStyle.success)
        self.guild_id = guild_id
        self.user_id = user_id
        self.quest_id = quest_id

    async def callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("⛔ Ce ne sont pas tes quêtes !", ephemeral=True)
            return
        await interaction.response.defer()
        resultat = await claim_secondaire(self.guild_id, self.user_id, self.quest_id)
        if resultat is None:
            await interaction.followup.send("Cette quête n'est pas terminée.", ephemeral=True)
            return
        titre_quete, berrys, xp = resultat
        niveaux_gagnes, nouveau_niveau = await add_xp(self.guild_id, self.user_id, xp, xp // 2)
        await interaction.followup.send(f"🎁 **{titre_quete}** terminée ! +{berrys:,}฿, +{xp} XP", ephemeral=True)
        if niveaux_gagnes > 0:
            await announce_level_up(interaction, interaction.user, nouveau_niveau)


class SecondairesView(discord.ui.View):
    def __init__(self, guild_id, user_id, rows):
        super().__init__(timeout=60)
        for r in rows:
            if r["progres"] >= r["cible"]:
                quete = next((q for q in QUETES_SECONDAIRES if q[0] == r["ref_id"]), None)
                if quete:
                    self.add_item(SecondaireClaimButton(guild_id, user_id, r["id"], quete[1]))


@quetes_group.command(name="secondaires", description="Voir tes quêtes secondaires en cours (max 2)")
@require_salon("salon_quetes")
async def quetes_secondaires(interaction: discord.Interaction):
    await interaction.response.defer()
    player = await get_player(interaction.guild_id, interaction.user.id)
    if player is None:
        await interaction.followup.send("Tu n'as pas encore de personnage ! Lance `/commencer` pour débuter l'aventure 🏴‍☠️")
        return

    rows = await get_active_secondaires(interaction.guild_id, interaction.user.id)
    if not rows:
        await interaction.followup.send("Tu n'as aucune quête secondaire en cours. Utilise `/quetes secondaire_rejoindre` pour en accepter une !")
        return

    embed = discord.Embed(title="📋 Tes quêtes secondaires", color=0x3498DB)
    has_completed = False
    for r in rows:
        quete = next((q for q in QUETES_SECONDAIRES if q[0] == r["ref_id"]), None)
        if not quete:
            continue
        titre, description, berrys, xp = quete[1], quete[2], quete[5], quete[6]
        statut = "🎉" if r["progres"] >= r["cible"] else ""
        if r["progres"] >= r["cible"]:
            has_completed = True
        embed.add_field(
            name=f"{statut} {titre}",
            value=f"{description}\n{barre(r['progres'], r['cible'])} {r['progres']}/{r['cible']} • {berrys}฿, {xp} XP",
            inline=False
        )
    embed.set_footer(text="🌊 One Piece Bot • Quêtes secondaires")

    if has_completed:
        await interaction.followup.send(embed=embed, view=SecondairesView(interaction.guild_id, interaction.user.id, rows))
    else:
        await interaction.followup.send(embed=embed)


async def secondaire_disponible_autocomplete(interaction: discord.Interaction, current: str):
    dispo = await get_available_secondaires(interaction.guild_id, interaction.user.id)
    filtered = [q for q in dispo if current.lower() in q[1].lower()]
    return [app_commands.Choice(name=q[1], value=q[0]) for q in filtered[:25]]

@quetes_group.command(name="secondaire_rejoindre", description="Accepter une nouvelle quête secondaire (2 max en cours)")
@app_commands.describe(quete="La quête à accepter")
@app_commands.autocomplete(quete=secondaire_disponible_autocomplete)
@require_salon("salon_quetes")
async def quetes_secondaire_rejoindre(interaction: discord.Interaction, quete: str):
    await interaction.response.defer()
    player = await get_player(interaction.guild_id, interaction.user.id)
    if player is None:
        await interaction.followup.send("Tu n'as pas encore de personnage ! Lance `/commencer` pour débuter l'aventure 🏴‍☠️")
        return
    ok, message = await accept_secondaire(interaction.guild_id, interaction.user.id, quete)
    if ok:
        await interaction.followup.send(f"✅ Quête acceptée : **{message}** !")
    else:
        await interaction.followup.send(f"⛔ {message}")


async def secondaire_active_autocomplete(interaction: discord.Interaction, current: str):
    rows = await get_active_secondaires(interaction.guild_id, interaction.user.id)
    result = []
    for r in rows:
        quete = next((q for q in QUETES_SECONDAIRES if q[0] == r["ref_id"]), None)
        if quete and current.lower() in quete[1].lower():
            result.append(app_commands.Choice(name=quete[1], value=r["id"]))
    return result[:25]

@quetes_group.command(name="secondaire_abandonner", description="Abandonner une quête secondaire en cours")
@app_commands.describe(quete="La quête à abandonner")
@app_commands.autocomplete(quete=secondaire_active_autocomplete)
@require_salon("salon_quetes")
async def quetes_secondaire_abandonner(interaction: discord.Interaction, quete: int):
    await interaction.response.defer()
    await abandon_secondaire(interaction.guild_id, interaction.user.id, quete)
    await interaction.followup.send("✅ Quête abandonnée, tu peux en accepter une nouvelle.")


def setup_quetes_commands(bot):
    bot.tree.add_command(quetes_group)
