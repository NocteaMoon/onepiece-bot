import discord
from discord import app_commands
import random
import datetime
from database.db import get_pool
from utils.players import get_player, add_xp
from utils.channel_check import require_salon
from utils.reputation import add_reputation_faction, MONTANT_COMBAT_VICTOIRE
from utils.maitrise import LABELS as MAITRISE_LABELS, PLAFOND_MAITRISE, COLONNES as MAITRISE_COLONNES

COUT_ENDURANCE = 15
COOLDOWN_MINUTES = 20
CHANCE_BASE = 0.22
CHANCE_BONUS_GRADE = 0.06
CHANCE_METIER = 0.30
GAIN_METIER_XP = 25
HAKI_ELITE_CAP = 15

GRADES_ELITE_PIRATE = ("Officier", "Second", "Capitaine")
GRADES_ELITE_MARINE = ("Commandant", "Amiral")
GRADES_ELITE_REVOLUTION = ("Commandant", "Meneur")

METIER_EMOJIS = {
    "Cuisinier": "🍳", "Forgeron": "🔨", "Médecin": "💊", "Navigateur": "🧭",
    "Charpentier": "🚢", "Musicien": "🎵", "Archéologue": "🏺",
}

FACTION_INTROS = {
    "Pirate": [
        "🏴‍☠️ En tant que Pirate, tu peux t'exercer à n'importe quelle arme sur le pont du navire.",
        "🏴‍☠️ Les vieux loups de mer t'invitent à croiser le fer pour parfaire ta technique.",
        "🏴‍☠️ Un coin tranquille de la cale sert de terrain d'entraînement improvisé.",
        "🏴‍☠️ Le vent souffle fort sur le pont, mais rien n'arrête une bonne session d'entraînement.",
    ],
    "Marine": [
        "⚓ La discipline martiale de la Marine se concentre sur l'Épée, le Pistolet et le Fusil.",
        "⚓ Un instructeur t'attend sur le terrain d'exercice réglementaire.",
        "⚓ La caserne résonne du bruit des entraînements — à toi de t'y joindre.",
        "⚓ Rigueur et discipline : le quotidien de tout Marine qui se respecte.",
    ],
    "Révolutionnaire": [
        "🔥 L'entraînement clandestin privilégie les armes silencieuses : Poings, Lance et Arc.",
        "🔥 Dans un repaire discret, tu peaufines tes techniques loin des regards.",
        "🔥 Un vétéran de la cause t'apprend à frapper vite et sans bruit.",
        "🔥 Chaque session renforce un peu plus la cause que tu défends.",
    ],
    "Civil": [
        "🏘️ Un entraînement de base est toujours accessible, et ton métier t'offre un perfectionnement dédié.",
        "🏘️ Le petit terrain vague derrière l'atelier fait office de zone d'entraînement.",
        "🏘️ Entre deux clients, tu prends un moment pour t'exercer.",
        "🏘️ La vie civile n'empêche pas de progresser, à son rythme.",
    ],
}

MAITRISE_SUCCES_TEXTES = [
    "Un geste plus net que d'habitude, la maîtrise s'installe.",
    "Ta prise se raffine légèrement à chaque répétition.",
    "Quelque chose clique enfin dans ton geste.",
    "L'effort finit par payer, ta technique progresse.",
    "Un vrai déclic — tu sens que tu progresses.",
]

MAITRISE_ECHEC_TEXTES = [
    "Le geste reste hésitant, sans réel progrès aujourd'hui.",
    "Tu t'entraînes sérieusement, mais rien de neuf ne s'installe encore.",
    "Séance honnête, sans avancée notable cette fois.",
    "Tu répètes le mouvement, sans franchir de cap.",
]

HAKI_ELITE_SUCCES_TEXTES = [
    "Une discipline réservée aux gradés porte enfin ses fruits.",
    "Ton statut te donne accès à un savoir que peu maîtrisent — et ça se voit.",
    "L'entraînement d'élite paie, une vraie percée aujourd'hui.",
]

HAKI_ELITE_ECHEC_TEXTES = [
    "Même avec ce privilège de gradé, aucune percée aujourd'hui.",
    "La discipline reste difficile à cerner, malgré ton rang.",
    "Séance sérieuse, mais rien de neuf ne s'installe encore.",
]

METIER_SUCCES_TEXTES = [
    "Un vrai coup de main aujourd'hui, ton savoir-faire progresse.",
    "Tu affines une technique que tu maîtrisais mal jusque-là.",
    "L'entraînement porte ses fruits, ton métier progresse.",
]

METIER_ECHEC_TEXTES = [
    "Séance honnête, mais rien de neuf ne s'installe aujourd'hui.",
    "Tu t'exerces sérieusement, sans réel déclic cette fois.",
    "Le geste reste perfectible, à retravailler une prochaine fois.",
]

_last_entrainement = {}


async def add_haki_direct(guild_id, user_id, colonne, cap):
    pool = get_pool()
    async with pool.acquire() as conn:
        current = await conn.fetchval(f"SELECT {colonne} FROM players WHERE guild_id=$1 AND user_id=$2", guild_id, user_id)
        if current is not None and current >= cap:
            return False
        await conn.execute(f"UPDATE players SET {colonne} = {colonne} + 1 WHERE guild_id=$1 AND user_id=$2", guild_id, user_id)
        return True


async def progresser_maitrise_force(guild_id, user_id, type_arme):
    """Incrémente directement de +1 : la chance de réussite est déjà gérée en amont par l'entraînement dédié."""
    colonne = MAITRISE_COLONNES[type_arme]
    pool = get_pool()
    async with pool.acquire() as conn:
        await conn.execute(f"UPDATE players SET {colonne} = {colonne} + 1 WHERE guild_id=$1 AND user_id=$2", guild_id, user_id)


class EntrainementSelect(discord.ui.Select):
    def __init__(self, guild_id, user_id, player):
        self.guild_id = guild_id
        self.user_id = user_id
        self.player = player
        options = self._build_options(player)
        super().__init__(placeholder="Choisis un entraînement...", options=options)

    def _build_options(self, player):
        faction = player["faction"]
        options = []
        if faction == "Pirate":
            for type_arme, label in MAITRISE_LABELS.items():
                options.append(discord.SelectOption(label=f"Maîtrise : {label}", value=f"maitrise_{type_arme}", emoji="⚔️"))
        elif faction == "Marine":
            for type_arme in ("epee", "pistolet", "fusil"):
                options.append(discord.SelectOption(label=f"Maîtrise : {MAITRISE_LABELS[type_arme]}", value=f"maitrise_{type_arme}", emoji="⚔️"))
            if player["grade_equipage"] in GRADES_ELITE_MARINE:
                options.append(discord.SelectOption(label="Tactiques de commandement (Haki Armement)", value="haki_haki_armement", emoji="👊"))
        elif faction == "Révolutionnaire":
            for type_arme in ("poings", "lance", "arc"):
                options.append(discord.SelectOption(label=f"Maîtrise : {MAITRISE_LABELS[type_arme]}", value=f"maitrise_{type_arme}", emoji="⚔️"))
            if player["grade_equipage"] in GRADES_ELITE_REVOLUTION:
                options.append(discord.SelectOption(label="Discipline de l'ombre (Haki Observation)", value="haki_haki_observation", emoji="👁️"))
        else:  # Civil
            options.append(discord.SelectOption(label="Entraînement physique de base", value="maitrise_poings", emoji="🥊"))
            if player["metier"]:
                emoji = METIER_EMOJIS.get(player["metier"], "🔧")
                options.append(discord.SelectOption(label=f"Perfectionner : {player['metier']}", value="metier", emoji=emoji))
        return options

    async def callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("⛔ Ce n'est pas ton entraînement !", ephemeral=True)
            return
        await resoudre_entrainement(interaction, self.guild_id, self.user_id, self.player, self.values[0])


class EntrainementView(discord.ui.View):
    def __init__(self, guild_id, user_id, player):
        super().__init__(timeout=30)
        self.add_item(EntrainementSelect(guild_id, user_id, player))


async def resoudre_entrainement(interaction, guild_id, user_id, player, choix):
    pool = get_pool()
    async with pool.acquire() as conn:
        await conn.execute("UPDATE players SET endurance = endurance - $3 WHERE guild_id=$1 AND user_id=$2",
                            guild_id, user_id, COUT_ENDURANCE)
    await add_xp(guild_id, user_id, 10, 4)
    await add_reputation_faction(guild_id, user_id, player["faction"], MONTANT_COMBAT_VICTOIRE)

    if choix.startswith("maitrise_"):
        type_arme = choix.split("_", 1)[1]
        chance = CHANCE_BASE
        if player["faction"] == "Pirate" and player["grade_equipage"] in GRADES_ELITE_PIRATE:
            chance += CHANCE_BONUS_GRADE
        label = MAITRISE_LABELS.get(type_arme, type_arme)
        colonne = MAITRISE_COLONNES[type_arme]
        current = player[colonne] or 0
        if current >= PLAFOND_MAITRISE:
            embed = discord.Embed(title="⚔️ Entraînement", description=f"Ta maîtrise en **{label}** est déjà au maximum ({PLAFOND_MAITRISE}) !", color=0x95A5A6)
        elif random.random() < chance:
            await progresser_maitrise_force(guild_id, user_id, type_arme)
            texte = random.choice(MAITRISE_SUCCES_TEXTES)
            embed = discord.Embed(title="⚔️ Entraînement réussi !", description=f"{texte}\nTa maîtrise en **{label}** progresse d'un cran !", color=0x27AE60)
        else:
            texte = random.choice(MAITRISE_ECHEC_TEXTES)
            embed = discord.Embed(title="⚔️ Entraînement", description=f"{texte} (**{label}**)", color=0x95A5A6)

    elif choix.startswith("haki_"):
        colonne = choix.split("_", 1)[1]
        label = "Armement" if colonne == "haki_armement" else "Observation"
        if random.random() < CHANCE_BASE:
            ok = await add_haki_direct(guild_id, user_id, colonne, HAKI_ELITE_CAP)
            if ok:
                texte = random.choice(HAKI_ELITE_SUCCES_TEXTES)
                embed = discord.Embed(title="👑 Entraînement d'élite réussi !", description=f"{texte}\nTon Haki d'**{label}** progresse !", color=0x27AE60)
            else:
                embed = discord.Embed(title="👑 Entraînement d'élite", description=f"Ton Haki d'**{label}** a déjà atteint le maximum accessible par cette voie ({HAKI_ELITE_CAP}).", color=0x95A5A6)
        else:
            texte = random.choice(HAKI_ELITE_ECHEC_TEXTES)
            embed = discord.Embed(title="👑 Entraînement d'élite", description=f"{texte} (**{label}**)", color=0x95A5A6)

    else:  # metier
        if random.random() < CHANCE_METIER:
            async with pool.acquire() as conn:
                await conn.execute("UPDATE players SET metier_xp = metier_xp + $3 WHERE guild_id=$1 AND user_id=$2",
                                    guild_id, user_id, GAIN_METIER_XP)
            texte = random.choice(METIER_SUCCES_TEXTES)
            embed = discord.Embed(title="🔧 Perfectionnement réussi !", description=f"{texte}\n**{player['metier']}** : +{GAIN_METIER_XP} XP Métier !", color=0x27AE60)
        else:
            texte = random.choice(METIER_ECHEC_TEXTES)
            embed = discord.Embed(title="🔧 Perfectionnement", description=f"{texte} (**{player['metier']}**)", color=0x95A5A6)

    embed.set_footer(text="🌊 One Piece Bot • Entraînement")
    await interaction.response.edit_message(embed=embed, view=None)


@app_commands.command(name="entrainement", description="S'entraîner selon ta faction, ton métier et ton grade")
@require_salon("salon_entrainement")
async def entrainement(interaction: discord.Interaction):
    await interaction.response.defer()
    player = await get_player(interaction.guild_id, interaction.user.id)
    if player is None:
        await interaction.followup.send("Tu n'as pas encore de personnage ! Lance `/commencer` pour débuter l'aventure 🏴‍☠️")
        return

    key = (interaction.guild_id, interaction.user.id)
    now = datetime.datetime.utcnow()
    last = _last_entrainement.get(key)
    if last:
        elapsed = (now - last).total_seconds() / 60
        if elapsed < COOLDOWN_MINUTES:
            restant = int(COOLDOWN_MINUTES - elapsed)
            await interaction.followup.send(f"😮‍💨 Tu dois encore attendre **{restant} min** avant ta prochaine session.")
            return
    if player["endurance"] < COUT_ENDURANCE:
        await interaction.followup.send(f"😮‍💨 Il te faut {COUT_ENDURANCE} endurance pour t'entraîner (tu as {player['endurance']}).")
        return

    _last_entrainement[key] = now

    faction_intro = random.choice(FACTION_INTROS.get(player["faction"], [""]))

    view = EntrainementView(interaction.guild_id, interaction.user.id, player)
    embed = discord.Embed(
        title="🏋️ Entraînement",
        description=f"{faction_intro}\n\nChoisis ta session du jour :",
        color=0x2C3E50
    )
    embed.set_footer(text="🌊 One Piece Bot • Entraînement")
    await interaction.followup.send(embed=embed, view=view)


def setup_entrainement_faction_commands(bot):
    bot.tree.add_command(entrainement)
