import discord
from discord import app_commands
import random
import datetime
from database.db import get_pool
from utils.players import get_player, add_xp
from utils.combat_stats import get_effective_stats
from utils.channel_check import require_salon
from utils.reputation import add_reputation_faction, MONTANT_COMBAT_VICTOIRE
from utils.maitrise import progresser_maitrise, LABELS as MAITRISE_LABELS
from utils.fruits import check_eveil
from utils.haki import check_eveil_rois
from utils.xp_cache import check_xp_cache_paliers, STAT_LABELS
from utils.notoriete import add_notoriete, MONTANT_MINIJEU_COOP
from data.revolution_flavor import (
    QUIZ_QUESTIONS, LIEUX_INFILTRATION, CIBLES_SABOTAGE, MOTS_CODE_SECRET, NPCS_RECRUTEMENT
)

insurrection_group = app_commands.Group(name="insurrection", description="Mini-jeux exclusifs à la faction Révolutionnaire")

COOLDOWN_BRIEFING = 20
COUT_INFILTRATION = 15
COOLDOWN_INFILTRATION = 25
DUREE_JOIN_SABOTAGE = 60
COOLDOWN_CODE_SECRET = 30
COUT_RECRUTEMENT = 15
COOLDOWN_RECRUTEMENT = 25
DECALAGE_CESAR = 3

_last_briefing = {}
_last_infiltration = {}
_last_code_secret = {}
_last_recrutement = {}


async def verifier_revolutionnaire(interaction: discord.Interaction):
    player = await get_player(interaction.guild_id, interaction.user.id)
    if player is None:
        await interaction.followup.send("Tu n'as pas encore de personnage ! Lance `/commencer` pour débuter l'aventure 🏴‍☠️")
        return None
    if player["faction"] != "Révolutionnaire":
        await interaction.followup.send("⛔ Ces activités sont réservées à la faction **Révolutionnaire**.")
        return None
    return player


async def notifier_progression_hors_combat(interaction, uid, member):
    if not member:
        return
    eveil_fruit = await check_eveil(interaction.guild_id, uid)
    if eveil_fruit:
        await interaction.followup.send(embed=discord.Embed(
            title="✨ ÉVEIL !",
            description=f"{member.mention} ressent un pouvoir immense monter en lui/elle... **Son Fruit du Démon vient de s'éveiller !**",
            color=0x8E44AD
        ))
    eveil_rois = await check_eveil_rois(interaction.guild_id, uid)
    if eveil_rois:
        await interaction.followup.send(embed=discord.Embed(
            title="👑 HAKI DES ROIS !",
            description=f"Une aura écrasante émane soudain de {member.mention}... **Le Haki des Rois vient de s'éveiller !**",
            color=0xD4A017
        ))
    nouveaux_paliers = await check_xp_cache_paliers(interaction.guild_id, uid)
    for seuil, berrys_palier, stat, valeur in nouveaux_paliers:
        label = STAT_LABELS.get(stat, stat)
        await interaction.followup.send(embed=discord.Embed(
            title="🌟 Une force insoupçonnée grandit en toi...",
            description=f"{member.mention} ressent une expérience cachée refaire surface : **+{berrys_palier:,}฿** et **+{valeur} {label}** de façon permanente !",
            color=0xF4C430
        ))


def encoder_cesar(mot: str, decalage: int) -> str:
    resultat = ""
    for c in mot:
        if c.isalpha():
            base = ord('A')
            resultat += chr((ord(c.upper()) - base + decalage) % 26 + base)
        else:
            resultat += c
    return resultat


# ===== BRIEFING (QUIZ) =====

class BriefingView(discord.ui.View):
    def __init__(self, guild_id, user_id, choix, index_correct):
        super().__init__(timeout=20)
        self.guild_id = guild_id
        self.user_id = user_id
        self.index_correct = index_correct
        self.termine = False
        for i, choix_texte in enumerate(choix):
            self.add_item(BriefingButton(choix_texte, i))

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        return interaction.user.id == self.user_id


class BriefingButton(discord.ui.Button):
    def __init__(self, texte, index):
        super().__init__(label=texte[:80], style=discord.ButtonStyle.secondary)
        self.index = index

    async def callback(self, interaction: discord.Interaction):
        view: BriefingView = self.view
        if view.termine:
            return
        view.termine = True
        for c in view.children:
            c.disabled = True
            if c.index == view.index_correct:
                c.style = discord.ButtonStyle.success
            elif c is self:
                c.style = discord.ButtonStyle.danger

        pool = get_pool()
        if self.index == view.index_correct:
            gain = random.randint(25, 50)
            async with pool.acquire() as conn:
                await conn.execute("UPDATE players SET berrys = berrys + $3 WHERE guild_id=$1 AND user_id=$2", view.guild_id, view.user_id, gain)
            await add_xp(view.guild_id, view.user_id, 15, 6)
            await add_reputation_faction(view.guild_id, view.user_id, "Révolutionnaire", MONTANT_COMBAT_VICTOIRE)
            texte = f"✅ Bonne réponse ! Ce renseignement vaut **{gain}฿**."
        else:
            texte = "❌ Mauvaise réponse... ce renseignement ne mène nulle part cette fois."

        embed = discord.Embed(title="🕵️ Briefing", description=texte, color=0x27AE60 if self.index == view.index_correct else 0x7F0000)
        embed.set_footer(text="🌊 One Piece Bot • Mini-jeux Révolutionnaires")
        await interaction.response.edit_message(embed=embed, view=view)


@insurrection_group.command(name="briefing", description="Répondre à une question de renseignement (Révolutionnaire)")
@require_salon("salon_taverne")
async def insurrection_briefing(interaction: discord.Interaction):
    await interaction.response.defer()
    player = await verifier_revolutionnaire(interaction)
    if player is None:
        return

    key = (interaction.guild_id, interaction.user.id)
    now = datetime.datetime.utcnow()
    last = _last_briefing.get(key)
    if last:
        elapsed = (now - last).total_seconds() / 60
        if elapsed < COOLDOWN_BRIEFING:
            restant = int(COOLDOWN_BRIEFING - elapsed)
            await interaction.followup.send(f"😮‍💨 Tu dois encore attendre **{restant} min** avant un nouveau briefing.")
            return

    _last_briefing[key] = now
    question, choix, index_correct = random.choice(QUIZ_QUESTIONS)
    view = BriefingView(interaction.guild_id, interaction.user.id, choix, index_correct)
    embed = discord.Embed(title="🕵️ Briefing", description=question, color=0x2C3E50)
    embed.set_footer(text="🌊 One Piece Bot • Mini-jeux Révolutionnaires")
    await interaction.followup.send(embed=embed, view=view)


# ===== INFILTRATION =====

@insurrection_group.command(name="infiltration", description="Infiltrer discrètement un lieu surveillé (Révolutionnaire)")
@require_salon("salon_taverne")
async def insurrection_infiltration(interaction: discord.Interaction):
    await interaction.response.defer()
    player = await verifier_revolutionnaire(interaction)
    if player is None:
        return

    key = (interaction.guild_id, interaction.user.id)
    now = datetime.datetime.utcnow()
    last = _last_infiltration.get(key)
    if last:
        elapsed = (now - last).total_seconds() / 60
        if elapsed < COOLDOWN_INFILTRATION:
            restant = int(COOLDOWN_INFILTRATION - elapsed)
            await interaction.followup.send(f"😮‍💨 Tu dois encore attendre **{restant} min** avant une nouvelle infiltration.")
            return
    if player["endurance"] < COUT_INFILTRATION:
        await interaction.followup.send(f"😮‍💨 Il te faut {COUT_INFILTRATION} endurance pour t'infiltrer (tu as {player['endurance']}).")
        return

    _last_infiltration[key] = now
    lieu = random.choice(LIEUX_INFILTRATION)
    eff = await get_effective_stats(interaction.guild_id, interaction.user.id, player)
    chance = max(0.35, min(0.90, 0.55 + (eff["agilite"] + eff["chance"]) * 0.01))

    pool = get_pool()
    async with pool.acquire() as conn:
        await conn.execute("UPDATE players SET endurance = endurance - $3 WHERE guild_id=$1 AND user_id=$2",
                            interaction.guild_id, interaction.user.id, COUT_INFILTRATION)

    if random.random() < chance:
        gain = random.randint(30, 70)
        async with pool.acquire() as conn:
            await conn.execute("UPDATE players SET berrys = berrys + $3 WHERE guild_id=$1 AND user_id=$2", interaction.guild_id, interaction.user.id, gain)
        await add_xp(interaction.guild_id, interaction.user.id, 18, 7)
        await add_reputation_faction(interaction.guild_id, interaction.user.id, "Révolutionnaire", MONTANT_COMBAT_VICTOIRE)
        embed = discord.Embed(
            title="🥷 Infiltration réussie !",
            description=f"Tu te faufiles sans un bruit dans {lieu} et repars avec **{gain}฿** de documents et objets de valeur.",
            color=0x27AE60
        )
    else:
        perte_pv = random.randint(5, 15)
        async with pool.acquire() as conn:
            await conn.execute("UPDATE players SET pv = GREATEST(1, pv - $3) WHERE guild_id=$1 AND user_id=$2", interaction.guild_id, interaction.user.id, perte_pv)
        embed = discord.Embed(
            title="🥷 Infiltration compromise...",
            description=f"Une patrouille te repère dans {lieu} ! Tu bats en retraite de justesse (-{perte_pv} PV).",
            color=0x7F0000
        )
    embed.set_footer(text="🌊 One Piece Bot • Mini-jeux Révolutionnaires")
    await interaction.followup.send(embed=embed)


# ===== SABOTAGE (coopératif) =====

class SabotageJoinView(discord.ui.View):
    def __init__(self, guild_id, hote: discord.Member):
        super().__init__(timeout=DUREE_JOIN_SABOTAGE)
        self.guild_id = guild_id
        self.participants = {hote.id: hote}
        self.message = None
        self.lancee = False

    def build_embed(self):
        names = [m.mention for m in self.participants.values()]
        embed = discord.Embed(
            title="💣 Sabotage — Inscriptions !",
            description="Rassemble ta cellule pour une opération de sabotage coordonnée.",
            color=0xC0392B
        )
        embed.add_field(name=f"Participants ({len(names)}/4)", value="\n".join(names) or "Aucun", inline=False)
        embed.set_footer(text=f"🌊 One Piece Bot • Mini-jeux Révolutionnaires • {DUREE_JOIN_SABOTAGE}s pour rejoindre (2 minimum)")
        return embed

    @discord.ui.button(label="Rejoindre la cellule", emoji="💣", style=discord.ButtonStyle.danger)
    async def rejoindre(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.lancee:
            await interaction.response.send_message("L'opération a déjà commencé !", ephemeral=True)
            return
        if interaction.user.id in self.participants:
            await interaction.response.send_message("Tu es déjà de la cellule !", ephemeral=True)
            return
        if len(self.participants) >= 4:
            await interaction.response.send_message("La cellule est déjà complète (4/4) !", ephemeral=True)
            return
        player = await get_player(self.guild_id, interaction.user.id)
        if player is None or player["faction"] != "Révolutionnaire":
            await interaction.response.send_message("⛔ Réservé aux Révolutionnaires ayant un personnage.", ephemeral=True)
            return
        self.participants[interaction.user.id] = interaction.user
        await interaction.response.edit_message(embed=self.build_embed(), view=self)

    async def on_timeout(self):
        self.lancee = True
        for c in self.children:
            c.disabled = True
        self.stop()


class SabotageCombatView(discord.ui.View):
    def __init__(self, guild_id, description, pv_max, participant_ids, berrys_min, berrys_max):
        super().__init__(timeout=300)
        self.guild_id = guild_id
        self.description = description
        self.pv = pv_max
        self.pv_max = pv_max
        self.participant_ids = set(participant_ids)
        self.degats = {uid: 0 for uid in participant_ids}
        self.berrys_min = berrys_min
        self.berrys_max = berrys_max
        self.termine = False
        self.message = None

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id not in self.participant_ids:
            await interaction.response.send_message("⛔ Tu ne fais pas partie de cette cellule !", ephemeral=True)
            return False
        return True

    def build_embed(self, message=None):
        embed = discord.Embed(title=f"💣 Sabotage — {self.description}", color=0xC0392B)
        embed.description = message or "Cliquez sur Saboter autant de fois que possible !"
        rempli = round(max(0, self.pv) / self.pv_max * 14) if self.pv_max else 0
        embed.add_field(name=f"Progression — {max(0, self.pv):,}/{self.pv_max:,}", value="🟧" * rempli + "⬜" * (14 - rempli), inline=False)
        embed.set_footer(text="🌊 One Piece Bot • Mini-jeux Révolutionnaires")
        return embed

    @discord.ui.button(label="Saboter !", emoji="💣", style=discord.ButtonStyle.danger)
    async def saboter(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        if self.termine:
            return
        player = await get_player(self.guild_id, interaction.user.id)
        eff = await get_effective_stats(self.guild_id, interaction.user.id, player)
        degats = max(1, round((eff["agilite"] + eff["force"]) / 2 * random.uniform(0.8, 1.2)))
        self.pv -= degats
        self.degats[interaction.user.id] += degats

        message_frappe = f"**{interaction.user.display_name}** progresse de **{degats}** points !"
        nouveau_palier = await progresser_maitrise(self.guild_id, interaction.user.id, eff.get("type_arme_equipee"))
        if nouveau_palier is not None:
            label = MAITRISE_LABELS.get(eff.get("type_arme_equipee"), "?")
            message_frappe += f"\n💪 Maîtrise en **{label}** progresse !"

        if self.pv <= 0:
            self.termine = True
            for c in self.children:
                c.disabled = True
            total = sum(self.degats.values()) or 1
            pool = get_pool()
            gain_total = random.randint(self.berrys_min, self.berrys_max)
            lignes = []
            for uid, dmg in self.degats.items():
                part = max(10, round(gain_total * dmg / total))
                async with pool.acquire() as conn:
                    await conn.execute("UPDATE players SET berrys = berrys + $3 WHERE guild_id=$1 AND user_id=$2", self.guild_id, uid, part)
                await add_xp(self.guild_id, uid, 30, 12)
                await add_reputation_faction(self.guild_id, uid, "Révolutionnaire", MONTANT_COMBAT_VICTOIRE)
                await add_notoriete(self.guild_id, uid, MONTANT_MINIJEU_COOP)
                member = interaction.guild.get_member(uid)
                lignes.append(f"{member.mention if member else uid} : +{part}฿")
            embed = self.build_embed(f"🏆 **{self.description}** est neutralisé avec succès !\n\n" + "\n".join(lignes))
            embed.color = 0x27AE60
            await self.message.edit(embed=embed, view=self)

            for uid in self.degats:
                member = interaction.guild.get_member(uid)
                await notifier_progression_hors_combat(interaction, uid, member)
            return

        await self.message.edit(embed=self.build_embed(message_frappe), view=self)

    async def on_timeout(self):
        if self.termine:
            return
        self.termine = True
        for c in self.children:
            c.disabled = True
        if self.message:
            try:
                embed = self.build_embed(f"⏱️ Le temps est écoulé, l'opération contre **{self.description}** échoue.")
                embed.color = 0x7F0000
                await self.message.edit(embed=embed, view=self)
            except discord.HTTPException:
                pass


@insurrection_group.command(name="sabotage", description="Organiser une opération de sabotage en cellule (Révolutionnaire, coopératif 2-4)")
@require_salon("salon_taverne")
async def insurrection_sabotage(interaction: discord.Interaction):
    await interaction.response.defer()
    player = await verifier_revolutionnaire(interaction)
    if player is None:
        return

    view = SabotageJoinView(interaction.guild_id, interaction.user)
    msg = await interaction.followup.send(embed=view.build_embed(), view=view)
    view.message = msg
    await view.wait()

    if len(view.participants) < 2:
        await msg.edit(content="😴 Pas assez de monde pour une opération sérieuse (2 minimum), annulée.", embed=None, view=None)
        return

    description, pv_min, pv_max, b_min, b_max = random.choice(CIBLES_SABOTAGE)
    pv_cible = random.randint(pv_min, pv_max)
    membres = list(view.participants.values())

    combat_view = SabotageCombatView(interaction.guild_id, description, pv_cible, [m.id for m in membres], b_min, b_max)
    embed = combat_view.build_embed(f"La cellule repère **{description}** ! L'opération commence.")
    combat_msg = await interaction.channel.send(embed=embed, view=combat_view)
    combat_view.message = combat_msg


# ===== CODE SECRET =====

class CodeSecretModal(discord.ui.Modal, title="Déchiffrer le code"):
    def __init__(self, guild_id, user_id, mot_original):
        super().__init__()
        self.guild_id = guild_id
        self.user_id = user_id
        self.mot_original = mot_original
        self.reponse = discord.ui.TextInput(label="Ta réponse déchiffrée", max_length=30)
        self.add_item(self.reponse)

    async def on_submit(self, interaction: discord.Interaction):
        pool = get_pool()
        if self.reponse.value.strip().upper() == self.mot_original:
            gain = random.randint(35, 65)
            async with pool.acquire() as conn:
                await conn.execute("UPDATE players SET berrys = berrys + $3 WHERE guild_id=$1 AND user_id=$2", self.guild_id, self.user_id, gain)
            await add_xp(self.guild_id, self.user_id, 20, 8)
            await add_reputation_faction(self.guild_id, self.user_id, "Révolutionnaire", MONTANT_COMBAT_VICTOIRE)
            embed = discord.Embed(title="🔐 Code déchiffré !", description=f"Bravo, le message disait bien **{self.mot_original}** ! +{gain}฿", color=0x27AE60)
        else:
            embed = discord.Embed(title="🔐 Mauvais déchiffrage...", description=f"Ce n'était pas ça. Le message disait **{self.mot_original}**.", color=0x7F0000)
        embed.set_footer(text="🌊 One Piece Bot • Mini-jeux Révolutionnaires")
        await interaction.response.edit_message(embed=embed, view=None)


class CodeSecretView(discord.ui.View):
    def __init__(self, guild_id, user_id, mot_original):
        super().__init__(timeout=120)
        self.guild_id = guild_id
        self.user_id = user_id
        self.mot_original = mot_original

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        return interaction.user.id == self.user_id

    @discord.ui.button(label="Déchiffrer", emoji="🔐", style=discord.ButtonStyle.primary)
    async def dechiffrer(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(CodeSecretModal(self.guild_id, self.user_id, self.mot_original))


@insurrection_group.command(name="code_secret", description="Déchiffrer un message codé (Révolutionnaire)")
@require_salon("salon_taverne")
async def insurrection_code_secret(interaction: discord.Interaction):
    await interaction.response.defer()
    player = await verifier_revolutionnaire(interaction)
    if player is None:
        return

    key = (interaction.guild_id, interaction.user.id)
    now = datetime.datetime.utcnow()
    last = _last_code_secret.get(key)
    if last:
        elapsed = (now - last).total_seconds() / 60
        if elapsed < COOLDOWN_CODE_SECRET:
            restant = int(COOLDOWN_CODE_SECRET - elapsed)
            await interaction.followup.send(f"😮‍💨 Tu dois encore attendre **{restant} min** avant un nouveau message à déchiffrer.")
            return

    _last_code_secret[key] = now
    mot = random.choice(MOTS_CODE_SECRET)
    encode = encoder_cesar(mot, DECALAGE_CESAR)

    view = CodeSecretView(interaction.guild_id, interaction.user.id, mot)
    embed = discord.Embed(
        title="🔐 Code secret intercepté",
        description=f"Un message codé te parvient : **{encode}**\n\nChaque lettre a été décalée de **{DECALAGE_CESAR}** rangs dans l'alphabet. À toi de le déchiffrer !",
        color=0x2C3E50
    )
    embed.set_footer(text="🌊 One Piece Bot • Mini-jeux Révolutionnaires")
    await interaction.followup.send(embed=embed, view=view)


# ===== RECRUTEMENT CLANDESTIN =====

APPROCHES_RECRUTEMENT = {
    "ideaux": ("Idéaux", 0.60, (20, 45)),
    "menace": ("Menace voilée", 0.55, (25, 50)),
    "pot_de_vin": ("Pot-de-vin", 0.75, (10, 25)),
}

class RecrutementView(discord.ui.View):
    def __init__(self, guild_id, user_id, npc):
        super().__init__(timeout=30)
        self.guild_id = guild_id
        self.user_id = user_id
        self.npc = npc
        self.termine = False

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        return interaction.user.id == self.user_id

    async def resoudre(self, interaction, approche_key):
        if self.termine:
            return
        self.termine = True
        for c in self.children:
            c.disabled = True

        label, chance, (b_min, b_max) = APPROCHES_RECRUTEMENT[approche_key]
        reussi = random.random() < chance

        pool = get_pool()
        if reussi:
            gain = random.randint(b_min, b_max)
            async with pool.acquire() as conn:
                await conn.execute("UPDATE players SET berrys = berrys + $3 WHERE guild_id=$1 AND user_id=$2", self.guild_id, self.user_id, gain)
            await add_xp(self.guild_id, self.user_id, 15, 6)
            await add_reputation_faction(self.guild_id, self.user_id, "Révolutionnaire", MONTANT_COMBAT_VICTOIRE)
            texte = f"📢 Ton approche par **{label}** convainc {self.npc} de coopérer ! Récompense : **{gain}฿**."
            couleur = 0x27AE60
        else:
            texte = f"📢 {self.npc.capitalize()} refuse net face à ton approche par **{label}**."
            couleur = 0x7F0000

        embed = discord.Embed(title="📢 Recrutement clandestin", description=texte, color=couleur)
        embed.set_footer(text="🌊 One Piece Bot • Mini-jeux Révolutionnaires")
        await interaction.response.edit_message(embed=embed, view=self)

    @discord.ui.button(label="Idéaux", emoji="✊", style=discord.ButtonStyle.primary)
    async def ideaux(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.resoudre(interaction, "ideaux")

    @discord.ui.button(label="Menace voilée", emoji="😠", style=discord.ButtonStyle.danger)
    async def menace(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.resoudre(interaction, "menace")

    @discord.ui.button(label="Pot-de-vin", emoji="💰", style=discord.ButtonStyle.secondary)
    async def pot_de_vin(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.resoudre(interaction, "pot_de_vin")

    async def on_timeout(self):
        if self.termine:
            return
        for c in self.children:
            c.disabled = True


@insurrection_group.command(name="recrutement", description="Tenter de recruter un allié clandestin (Révolutionnaire)")
@require_salon("salon_taverne")
async def insurrection_recrutement(interaction: discord.Interaction):
    await interaction.response.defer()
    player = await verifier_revolutionnaire(interaction)
    if player is None:
        return

    key = (interaction.guild_id, interaction.user.id)
    now = datetime.datetime.utcnow()
    last = _last_recrutement.get(key)
    if last:
        elapsed = (now - last).total_seconds() / 60
        if elapsed < COOLDOWN_RECRUTEMENT:
            restant = int(COOLDOWN_RECRUTEMENT - elapsed)
            await interaction.followup.send(f"😮‍💨 Tu dois encore attendre **{restant} min** avant une nouvelle tentative.")
            return
    if player["endurance"] < COUT_RECRUTEMENT:
        await interaction.followup.send(f"😮‍💨 Il te faut {COUT_RECRUTEMENT} endurance pour cette approche (tu as {player['endurance']}).")
        return

    pool = get_pool()
    async with pool.acquire() as conn:
        await conn.execute("UPDATE players SET endurance = endurance - $3 WHERE guild_id=$1 AND user_id=$2",
                            interaction.guild_id, interaction.user.id, COUT_RECRUTEMENT)
    _last_recrutement[key] = now

    npc = random.choice(NPCS_RECRUTEMENT)
    view = RecrutementView(interaction.guild_id, interaction.user.id, npc)
    embed = discord.Embed(
        title="📢 Recrutement clandestin",
        description=f"Tu approches **{npc}**. Quelle approche choisis-tu ?",
        color=0x2C3E50
    )
    embed.set_footer(text="🌊 One Piece Bot • Mini-jeux Révolutionnaires")
    await interaction.followup.send(embed=embed, view=view)


def setup_revolution_minijeux_commands(bot):
    bot.tree.add_command(insurrection_group)
