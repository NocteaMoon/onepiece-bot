import discord
from discord import app_commands
import random
import asyncio
import datetime
from database.db import get_pool
from utils.players import get_player, add_xp
from utils.combat_stats import get_effective_stats
from utils.channel_check import require_salon
from data.marine_flavor import (
    LIEUX_PATROUILLE, EVENEMENTS_PATROUILLE, TEXTES_EVENEMENTS_PATROUILLE,
    NAVIRES_PIRATES_TRAQUES, SUSPECTS_INTERROGATOIRE, EXERCICES_INSPECTION
)

amiraute_group = app_commands.Group(name="amiraute", description="Mini-jeux exclusifs à la faction Marine")

COUT_PATROUILLE = 15
COOLDOWN_PATROUILLE = 20
COUT_TIR = 10
COOLDOWN_TIR = 15
COUT_INTERROGATOIRE = 15
COOLDOWN_INTERROGATOIRE = 25
DUREE_JOIN_BATAILLE = 60
DUREE_JOIN_INSPECTION = 45

_last_patrouille = {}
_last_tir = {}
_last_interrogatoire = {}


async def verifier_marine(interaction: discord.Interaction):
    player = await get_player(interaction.guild_id, interaction.user.id)
    if player is None:
        await interaction.followup.send("Tu n'as pas encore de personnage ! Lance `/commencer` pour débuter l'aventure 🏴‍☠️")
        return None
    if player["faction"] != "Marine":
        await interaction.followup.send("⛔ Ces exercices sont réservés à la faction **Marine**.")
        return None
    return player


# ===== PATROUILLE =====

@amiraute_group.command(name="patrouille", description="Effectuer une ronde de patrouille (Marine)")
@require_salon("salon_taverne")
async def amiraute_patrouille(interaction: discord.Interaction):
    await interaction.response.defer()
    player = await verifier_marine(interaction)
    if player is None:
        return

    key = (interaction.guild_id, interaction.user.id)
    now = datetime.datetime.utcnow()
    last = _last_patrouille.get(key)
    if last:
        elapsed = (now - last).total_seconds() / 60
        if elapsed < COOLDOWN_PATROUILLE:
            restant = int(COOLDOWN_PATROUILLE - elapsed)
            await interaction.followup.send(f"😮‍💨 Tu dois encore attendre **{restant} min** avant ta prochaine ronde.")
            return
    if player["endurance"] < COUT_PATROUILLE:
        await interaction.followup.send(f"😮‍💨 Il te faut {COUT_PATROUILLE} endurance pour patrouiller (tu as {player['endurance']}).")
        return

    _last_patrouille[key] = now
    lieu = random.choice(LIEUX_PATROUILLE)
    label, b_min, b_max, xp, poids = random.choices(EVENEMENTS_PATROUILLE, weights=[e[4] for e in EVENEMENTS_PATROUILLE], k=1)[0]
    gain = random.randint(b_min, b_max)
    texte = random.choice(TEXTES_EVENEMENTS_PATROUILLE[label])

    pool = get_pool()
    async with pool.acquire() as conn:
        await conn.execute("UPDATE players SET berrys = berrys + $3, endurance = endurance - $4 WHERE guild_id=$1 AND user_id=$2",
                            interaction.guild_id, interaction.user.id, gain, COUT_PATROUILLE)
    await add_xp(interaction.guild_id, interaction.user.id, xp, xp // 2)

    embed = discord.Embed(
        title="🔍 Patrouille",
        description=f"En ronde sur {lieu} : {texte}" + (f"\n\n**+{gain}฿**" if gain else ""),
        color=0x3498DB
    )
    embed.set_footer(text="🌊 One Piece Bot • Mini-jeux Marine")
    await interaction.followup.send(embed=embed)


# ===== EXERCICE DE TIR =====

class ExerciceTirView(discord.ui.View):
    def __init__(self, guild_id, user_id):
        super().__init__(timeout=15)
        self.guild_id = guild_id
        self.user_id = user_id
        self.signal_time = None
        self.termine = False
        self.message = None

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        return interaction.user.id == self.user_id

    @discord.ui.button(label="En position...", style=discord.ButtonStyle.secondary)
    async def tirer(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.termine:
            return
        self.termine = True
        for c in self.children:
            c.disabled = True

        now = datetime.datetime.utcnow()
        if self.signal_time is None:
            gain = random.randint(5, 15)
            texte = "⚠️ Tu tires avant le signal ! Coup manqué."
            couleur = 0x7F0000
        else:
            elapsed = (now - self.signal_time).total_seconds()
            if elapsed < 1.0:
                gain = random.randint(60, 90)
                texte = f"🎯 **Tir exceptionnel !** ({elapsed:.2f}s de réaction)"
                couleur = 0xF1C40F
            elif elapsed < 2.5:
                gain = random.randint(35, 55)
                texte = f"🎯 Beau tir ! ({elapsed:.2f}s de réaction)"
                couleur = 0x27AE60
            else:
                gain = random.randint(15, 30)
                texte = f"🎯 Tir correct, mais un peu lent ({elapsed:.2f}s de réaction)."
                couleur = 0x95A5A6

        pool = get_pool()
        async with pool.acquire() as conn:
            await conn.execute("UPDATE players SET berrys = berrys + $3 WHERE guild_id=$1 AND user_id=$2", self.guild_id, self.user_id, gain)
        await add_xp(self.guild_id, self.user_id, 12, 5)

        embed = discord.Embed(title="🎯 Exercice de tir", description=f"{texte}\n\n**+{gain}฿**", color=couleur)
        embed.set_footer(text="🌊 One Piece Bot • Mini-jeux Marine")
        await interaction.response.edit_message(embed=embed, view=self)

    async def lancer_signal(self):
        await asyncio.sleep(random.uniform(3, 7))
        if self.termine:
            return
        self.signal_time = datetime.datetime.utcnow()
        self.children[0].label = "🎯 TIREZ !"
        self.children[0].style = discord.ButtonStyle.danger
        if self.message:
            try:
                embed = discord.Embed(title="🎯 Exercice de tir", description="🎯 **LA CIBLE APPARAÎT !**", color=0xE67E22)
                embed.set_footer(text="🌊 One Piece Bot • Mini-jeux Marine")
                await self.message.edit(embed=embed, view=self)
            except discord.HTTPException:
                pass

    async def on_timeout(self):
        if self.termine:
            return
        self.termine = True
        for c in self.children:
            c.disabled = True
        if self.message:
            try:
                await self.message.edit(content="⌛ Trop lent, la cible a disparu.", embed=None, view=self)
            except discord.HTTPException:
                pass


@amiraute_group.command(name="exercice_tir", description="S'entraîner au tir de précision (Marine)")
@require_salon("salon_taverne")
async def amiraute_exercice_tir(interaction: discord.Interaction):
    await interaction.response.defer()
    player = await verifier_marine(interaction)
    if player is None:
        return

    key = (interaction.guild_id, interaction.user.id)
    now = datetime.datetime.utcnow()
    last = _last_tir.get(key)
    if last:
        elapsed = (now - last).total_seconds() / 60
        if elapsed < COOLDOWN_TIR:
            restant = int(COOLDOWN_TIR - elapsed)
            await interaction.followup.send(f"😮‍💨 Tu dois encore attendre **{restant} min** avant ton prochain exercice.")
            return
    if player["endurance"] < COUT_TIR:
        await interaction.followup.send(f"😮‍💨 Il te faut {COUT_TIR} endurance pour t'entraîner (tu as {player['endurance']}).")
        return

    pool = get_pool()
    async with pool.acquire() as conn:
        await conn.execute("UPDATE players SET endurance = endurance - $3 WHERE guild_id=$1 AND user_id=$2",
                            interaction.guild_id, interaction.user.id, COUT_TIR)
    _last_tir[key] = now

    view = ExerciceTirView(interaction.guild_id, interaction.user.id)
    embed = discord.Embed(title="🎯 Exercice de tir", description="Attends le signal, et tire au bon moment !", color=0x2C3E50)
    embed.set_footer(text="🌊 One Piece Bot • Mini-jeux Marine")
    msg = await interaction.followup.send(embed=embed, view=view)
    view.message = msg
    asyncio.create_task(view.lancer_signal())


# ===== INTERROGATOIRE =====

APPROCHES = {
    "intimidation": ("Intimidation", 0.55, (20, 45)),
    "persuasion": ("Persuasion", 0.65, (15, 35)),
    "ruse": ("Ruse", 0.60, (25, 50)),
}

class InterrogatoireView(discord.ui.View):
    def __init__(self, guild_id, user_id, suspect):
        super().__init__(timeout=30)
        self.guild_id = guild_id
        self.user_id = user_id
        self.suspect = suspect
        self.termine = False

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        return interaction.user.id == self.user_id

    async def resoudre(self, interaction, approche_key):
        if self.termine:
            return
        self.termine = True
        for c in self.children:
            c.disabled = True

        label, chance, (b_min, b_max) = APPROCHES[approche_key]
        reussi = random.random() < chance

        pool = get_pool()
        if reussi:
            gain = random.randint(b_min, b_max)
            async with pool.acquire() as conn:
                await conn.execute("UPDATE players SET berrys = berrys + $3 WHERE guild_id=$1 AND user_id=$2", self.guild_id, self.user_id, gain)
            await add_xp(self.guild_id, self.user_id, 15, 6)
            texte = f"🗣️ Ton approche par **{label}** fonctionne ! {self.suspect.capitalize()} finit par craquer et te livre une récompense de **{gain}฿**."
            couleur = 0x27AE60
        else:
            texte = f"🗣️ Ton approche par **{label}** échoue. {self.suspect.capitalize()} reste muet(te) comme une tombe."
            couleur = 0x7F0000

        embed = discord.Embed(title="🗣️ Interrogatoire", description=texte, color=couleur)
        embed.set_footer(text="🌊 One Piece Bot • Mini-jeux Marine")
        await interaction.response.edit_message(embed=embed, view=self)

    @discord.ui.button(label="Intimidation", emoji="😤", style=discord.ButtonStyle.danger)
    async def intimidation(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.resoudre(interaction, "intimidation")

    @discord.ui.button(label="Persuasion", emoji="🤝", style=discord.ButtonStyle.primary)
    async def persuasion(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.resoudre(interaction, "persuasion")

    @discord.ui.button(label="Ruse", emoji="🃏", style=discord.ButtonStyle.secondary)
    async def ruse(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.resoudre(interaction, "ruse")

    async def on_timeout(self):
        if self.termine:
            return
        for c in self.children:
            c.disabled = True


@amiraute_group.command(name="interrogatoire", description="Interroger un suspect pour en tirer des informations (Marine)")
@require_salon("salon_taverne")
async def amiraute_interrogatoire(interaction: discord.Interaction):
    await interaction.response.defer()
    player = await verifier_marine(interaction)
    if player is None:
        return

    key = (interaction.guild_id, interaction.user.id)
    now = datetime.datetime.utcnow()
    last = _last_interrogatoire.get(key)
    if last:
        elapsed = (now - last).total_seconds() / 60
        if elapsed < COOLDOWN_INTERROGATOIRE:
            restant = int(COOLDOWN_INTERROGATOIRE - elapsed)
            await interaction.followup.send(f"😮‍💨 Tu dois encore attendre **{restant} min** avant un nouvel interrogatoire.")
            return
    if player["endurance"] < COUT_INTERROGATOIRE:
        await interaction.followup.send(f"😮‍💨 Il te faut {COUT_INTERROGATOIRE} endurance pour interroger un suspect (tu as {player['endurance']}).")
        return

    pool = get_pool()
    async with pool.acquire() as conn:
        await conn.execute("UPDATE players SET endurance = endurance - $3 WHERE guild_id=$1 AND user_id=$2",
                            interaction.guild_id, interaction.user.id, COUT_INTERROGATOIRE)
    _last_interrogatoire[key] = now

    suspect = random.choice(SUSPECTS_INTERROGATOIRE)
    view = InterrogatoireView(interaction.guild_id, interaction.user.id, suspect)
    embed = discord.Embed(
        title="🗣️ Interrogatoire",
        description=f"Tu es face à **{suspect}**. Quelle approche choisis-tu ?",
        color=0x2C3E50
    )
    embed.set_footer(text="🌊 One Piece Bot • Mini-jeux Marine")
    await interaction.followup.send(embed=embed, view=view)


# ===== BATAILLE NAVALE (chasse au navire pirate, coopératif) =====

class BatailleJoinView(discord.ui.View):
    def __init__(self, guild_id, hote: discord.Member):
        super().__init__(timeout=DUREE_JOIN_BATAILLE)
        self.guild_id = guild_id
        self.participants = {hote.id: hote}
        self.message = None
        self.lancee = False

    def build_embed(self):
        names = [m.mention for m in self.participants.values()]
        embed = discord.Embed(
            title="🚢 Bataille navale — Inscriptions !",
            description="Rassemble ton unité pour traquer un navire pirate signalé !",
            color=0x3498DB
        )
        embed.add_field(name=f"Participants ({len(names)}/4)", value="\n".join(names) or "Aucun", inline=False)
        embed.set_footer(text=f"🌊 One Piece Bot • Mini-jeux Marine • {DUREE_JOIN_BATAILLE}s pour rejoindre (2 minimum)")
        return embed

    @discord.ui.button(label="Rejoindre l'unité", emoji="⚓", style=discord.ButtonStyle.primary)
    async def rejoindre(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.lancee:
            await interaction.response.send_message("La bataille a déjà commencé !", ephemeral=True)
            return
        if interaction.user.id in self.participants:
            await interaction.response.send_message("Tu es déjà de l'unité !", ephemeral=True)
            return
        if len(self.participants) >= 4:
            await interaction.response.send_message("L'unité est déjà complète (4/4) !", ephemeral=True)
            return
        player = await get_player(self.guild_id, interaction.user.id)
        if player is None or player["faction"] != "Marine":
            await interaction.response.send_message("⛔ Réservé aux Marines ayant un personnage.", ephemeral=True)
            return
        self.participants[interaction.user.id] = interaction.user
        await interaction.response.edit_message(embed=self.build_embed(), view=self)

    async def on_timeout(self):
        self.lancee = True
        for c in self.children:
            c.disabled = True
        self.stop()


class BatailleCombatView(discord.ui.View):
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
            await interaction.response.send_message("⛔ Tu ne fais pas partie de cette unité !", ephemeral=True)
            return False
        return True

    def build_embed(self, message=None):
        embed = discord.Embed(title=f"🚢 Bataille navale — {self.description}", color=0x3498DB)
        embed.description = message or "Cliquez sur Tirer autant de fois que possible !"
        rempli = round(max(0, self.pv) / self.pv_max * 14) if self.pv_max else 0
        embed.add_field(name=f"PV du navire — {max(0, self.pv):,}/{self.pv_max:,}", value="🟦" * rempli + "⬜" * (14 - rempli), inline=False)
        embed.set_footer(text="🌊 One Piece Bot • Mini-jeux Marine")
        return embed

    @discord.ui.button(label="Tirer !", emoji="⚓", style=discord.ButtonStyle.primary)
    async def tirer(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        if self.termine:
            return
        player = await get_player(self.guild_id, interaction.user.id)
        eff = await get_effective_stats(self.guild_id, interaction.user.id, player)
        degats = max(1, round(eff["force"] * random.uniform(0.8, 1.2)))
        self.pv -= degats
        self.degats[interaction.user.id] += degats

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
                member = interaction.guild.get_member(uid)
                lignes.append(f"{member.mention if member else uid} : +{part}฿")
            embed = self.build_embed(f"🏆 **{self.description}** est neutralisé et capturé !\n\n" + "\n".join(lignes))
            embed.color = 0x27AE60
            await self.message.edit(embed=embed, view=self)
            return

        await self.message.edit(embed=self.build_embed(f"**{interaction.user.display_name}** touche pour **{degats}** dégâts !"), view=self)

    async def on_timeout(self):
        if self.termine:
            return
        self.termine = True
        for c in self.children:
            c.disabled = True
        if self.message:
            try:
                embed = self.build_embed(f"⏱️ Le temps est écoulé, **{self.description}** parvient à fuir dans le brouillard.")
                embed.color = 0x7F0000
                await self.message.edit(embed=embed, view=self)
            except discord.HTTPException:
                pass


@amiraute_group.command(name="bataille_navale", description="Traquer un navire pirate en unité (Marine, coopératif 2-4)")
@require_salon("salon_taverne")
async def amiraute_bataille_navale(interaction: discord.Interaction):
    await interaction.response.defer()
    player = await verifier_marine(interaction)
    if player is None:
        return

    view = BatailleJoinView(interaction.guild_id, interaction.user)
    msg = await interaction.followup.send(embed=view.build_embed(), view=view)
    view.message = msg
    await view.wait()

    if len(view.participants) < 2:
        await msg.edit(content="😴 Pas assez d'unités mobilisées (2 minimum), mission annulée.", embed=None, view=None)
        return

    description, pv_min, pv_max, b_min, b_max = random.choice(NAVIRES_PIRATES_TRAQUES)
    pv_navire = random.randint(pv_min, pv_max)
    membres = list(view.participants.values())

    combat_view = BatailleCombatView(interaction.guild_id, description, pv_navire, [m.id for m in membres], b_min, b_max)
    embed = combat_view.build_embed(f"L'unité repère **{description}** ! Ouverture du feu !")
    combat_msg = await interaction.channel.send(embed=embed, view=combat_view)
    combat_view.message = combat_msg


# ===== INSPECTION DE GRADE =====

class InspectionJoinView(discord.ui.View):
    def __init__(self, guild_id, hote: discord.Member):
        super().__init__(timeout=DUREE_JOIN_INSPECTION)
        self.guild_id = guild_id
        self.participants = {hote.id: hote}
        self.message = None
        self.lancee = False

    def build_embed(self):
        names = [m.mention for m in self.participants.values()]
        embed = discord.Embed(
            title="🎖️ Inspection de grade — Inscriptions !",
            description="Une inspection collective va avoir lieu. Rejoins pour être noté(e) !",
            color=0x3498DB
        )
        embed.add_field(name=f"Participants ({len(names)}/4)", value="\n".join(names) or "Aucun", inline=False)
        embed.set_footer(text=f"🌊 One Piece Bot • Mini-jeux Marine • {DUREE_JOIN_INSPECTION}s pour rejoindre (2 minimum)")
        return embed

    @discord.ui.button(label="Se présenter", emoji="🎖️", style=discord.ButtonStyle.primary)
    async def rejoindre(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.lancee:
            await interaction.response.send_message("L'inspection a déjà commencé !", ephemeral=True)
            return
        if interaction.user.id in self.participants:
            await interaction.response.send_message("Tu es déjà inscrit(e) !", ephemeral=True)
            return
        if len(self.participants) >= 4:
            await interaction.response.send_message("L'inspection est déjà complète (4/4) !", ephemeral=True)
            return
        player = await get_player(self.guild_id, interaction.user.id)
        if player is None or player["faction"] != "Marine":
            await interaction.response.send_message("⛔ Réservé aux Marines ayant un personnage.", ephemeral=True)
            return
        self.participants[interaction.user.id] = interaction.user
        await interaction.response.edit_message(embed=self.build_embed(), view=self)

    async def on_timeout(self):
        self.lancee = True
        for c in self.children:
            c.disabled = True
        self.stop()


@amiraute_group.command(name="inspection", description="Organiser une inspection de grade collective (Marine, 2-4)")
@require_salon("salon_taverne")
async def amiraute_inspection(interaction: discord.Interaction):
    await interaction.response.defer()
    player = await verifier_marine(interaction)
    if player is None:
        return

    view = InspectionJoinView(interaction.guild_id, interaction.user)
    msg = await interaction.followup.send(embed=view.build_embed(), view=view)
    view.message = msg
    await view.wait()

    if len(view.participants) < 2:
        await msg.edit(content="😴 Pas assez de monde pour une vraie inspection (2 minimum), annulée.", embed=None, view=None)
        return

    exercice = random.choice(EXERCICES_INSPECTION)
    membres = list(view.participants.values())
    scores = {}
    pool = get_pool()
    for m in membres:
        player_data = await get_player(interaction.guild_id, m.id)
        eff = await get_effective_stats(interaction.guild_id, m.id, player_data)
        scores[m.id] = eff["force"] + eff["agilite"] + random.randint(0, 30)

    meilleur_id = max(scores, key=scores.get)
    lignes = []
    for m in membres:
        base = random.randint(15, 25)
        bonus = 40 if m.id == meilleur_id else 0
        gain = base + bonus
        async with pool.acquire() as conn:
            await conn.execute("UPDATE players SET berrys = berrys + $3 WHERE guild_id=$1 AND user_id=$2", interaction.guild_id, m.id, gain)
        await add_xp(interaction.guild_id, m.id, 20 + (15 if m.id == meilleur_id else 0), 8)
        tag = " 🏅 Meilleur élément !" if m.id == meilleur_id else ""
        lignes.append(f"{m.mention}{tag} : +{gain}฿")

    embed = discord.Embed(
        title="🎖️ Inspection de grade terminée !",
        description=f"L'unité s'est illustrée lors d'un(e) {exercice} :\n\n" + "\n".join(lignes),
        color=0x27AE60
    )
    embed.set_footer(text="🌊 One Piece Bot • Mini-jeux Marine")
    await interaction.channel.send(embed=embed)


def setup_marine_minijeux_commands(bot):
    bot.tree.add_command(amiraute_group)
