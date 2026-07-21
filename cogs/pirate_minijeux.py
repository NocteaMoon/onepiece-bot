import discord
from discord import app_commands
import random
import asyncio
import datetime
from database.db import get_pool
from utils.players import get_player, add_xp
from utils.combat_stats import get_effective_stats
from utils.channel_check import require_salon
from data.pirate_flavor import LIEUX_CHASSE_PRIME, CONVOIS_ABORDAGE, ROUNDS_BEUVERIE, GROS_CONVOIS_PILLAGE

pirate_group = app_commands.Group(name="pirate", description="Mini-jeux exclusifs à la faction Pirate")

COUT_CHASSE_PRIME = 25
COOLDOWN_CHASSE_PRIME = 45
COUT_ABORDAGE = 20
COOLDOWN_ABORDAGE = 25
MISE_BEUVERIE = 30
DUREE_JOIN_BEUVERIE = 45
DUREE_JOIN_PILLAGE = 60

_last_chasse = {}
_last_abordage = {}


async def verifier_pirate(interaction: discord.Interaction):
    player = await get_player(interaction.guild_id, interaction.user.id)
    if player is None:
        await interaction.followup.send("Tu n'as pas encore de personnage ! Lance `/commencer` pour débuter l'aventure 🏴‍☠️")
        return None
    if player["faction"] != "Pirate":
        await interaction.followup.send("⛔ Ces défis sont réservés à la faction **Pirate**.")
        return None
    return player


# ===== CHASSE À LA PRIME =====

@pirate_group.command(name="chasse_prime", description="Traquer un autre joueur pour lui voler une partie de sa prime (Pirate)")
@app_commands.describe(cible="Le joueur à traquer")
@require_salon("salon_taverne")
async def pirate_chasse_prime(interaction: discord.Interaction, cible: discord.Member):
    await interaction.response.defer()
    player = await verifier_pirate(interaction)
    if player is None:
        return
    if cible.id == interaction.user.id or cible.bot:
        await interaction.followup.send("Choix invalide 🙃")
        return

    cible_data = await get_player(interaction.guild_id, cible.id)
    if cible_data is None:
        await interaction.followup.send(f"{cible.display_name} n'a pas encore de personnage.")
        return
    if cible_data["prime"] < 50:
        await interaction.followup.send(f"⛔ La prime de {cible.display_name} est trop faible pour valoir le coup.")
        return

    key = (interaction.guild_id, interaction.user.id)
    now = datetime.datetime.utcnow()
    last = _last_chasse.get(key)
    if last:
        elapsed = (now - last).total_seconds() / 60
        if elapsed < COOLDOWN_CHASSE_PRIME:
            restant = int(COOLDOWN_CHASSE_PRIME - elapsed)
            await interaction.followup.send(f"😮‍💨 Tu dois encore attendre **{restant} min** avant une nouvelle traque.")
            return
    if player["endurance"] < COUT_CHASSE_PRIME:
        await interaction.followup.send(f"😮‍💨 Il te faut {COUT_CHASSE_PRIME} endurance pour partir en chasse (tu as {player['endurance']}).")
        return

    _last_chasse[key] = now
    lieu = random.choice(LIEUX_CHASSE_PRIME)

    eff_a = await get_effective_stats(interaction.guild_id, interaction.user.id, player)
    eff_c = await get_effective_stats(interaction.guild_id, cible.id, cible_data)
    score_a = eff_a["force"] + eff_a["vitesse"] + random.randint(0, 25)
    score_c = eff_c["defense"] + eff_c["agilite"] + random.randint(0, 25)

    pool = get_pool()
    async with pool.acquire() as conn:
        await conn.execute("UPDATE players SET endurance = endurance - $3 WHERE guild_id=$1 AND user_id=$2",
                            interaction.guild_id, interaction.user.id, COUT_CHASSE_PRIME)

    if score_a > score_c:
        vol = max(20, round(cible_data["prime"] * random.uniform(0.05, 0.12)))
        async with pool.acquire() as conn:
            await conn.execute("UPDATE players SET berrys = berrys + $3, prime = prime + $4 WHERE guild_id=$1 AND user_id=$2",
                                interaction.guild_id, interaction.user.id, vol, vol // 2)
            await conn.execute("UPDATE players SET prime = GREATEST(0, prime - $3) WHERE guild_id=$1 AND user_id=$2",
                                interaction.guild_id, cible.id, vol)
        await add_xp(interaction.guild_id, interaction.user.id, 20, 8)
        embed = discord.Embed(
            title="💰 Traque réussie !",
            description=f"Tu repères **{cible.display_name}** dans {lieu} et lui subtilises une partie de sa mise à prix : **+{vol:,}฿** !",
            color=0x27AE60
        )
    else:
        perte = min(player["berrys"], random.randint(15, 35))
        async with pool.acquire() as conn:
            await conn.execute("UPDATE players SET berrys = berrys - $3 WHERE guild_id=$1 AND user_id=$2",
                                interaction.guild_id, interaction.user.id, perte)
        embed = discord.Embed(
            title="💨 Traque manquée...",
            description=f"Tu repères **{cible.display_name}** dans {lieu}, mais il/elle t'échappe ! Tu perds **{perte}฿** dans la manœuvre.",
            color=0x7F0000
        )
    embed.set_footer(text="🌊 One Piece Bot • Mini-jeux Pirates")
    await interaction.followup.send(embed=embed)


# ===== ABORDAGE =====

@pirate_group.command(name="abordage", description="Aborder un convoi marchand pour du butin (Pirate)")
@require_salon("salon_taverne")
async def pirate_abordage(interaction: discord.Interaction):
    await interaction.response.defer()
    player = await verifier_pirate(interaction)
    if player is None:
        return

    key = (interaction.guild_id, interaction.user.id)
    now = datetime.datetime.utcnow()
    last = _last_abordage.get(key)
    if last:
        elapsed = (now - last).total_seconds() / 60
        if elapsed < COOLDOWN_ABORDAGE:
            restant = int(COOLDOWN_ABORDAGE - elapsed)
            await interaction.followup.send(f"😮‍💨 Tu dois encore attendre **{restant} min** avant un nouvel abordage.")
            return
    if player["endurance"] < COUT_ABORDAGE:
        await interaction.followup.send(f"😮‍💨 Il te faut {COUT_ABORDAGE} endurance pour aborder un navire (tu as {player['endurance']}).")
        return

    _last_abordage[key] = now
    description, b_min, b_max, chance = random.choice(CONVOIS_ABORDAGE)
    reussi = random.random() < chance

    pool = get_pool()
    if reussi:
        gain = random.randint(b_min, b_max)
        async with pool.acquire() as conn:
            await conn.execute("UPDATE players SET berrys = berrys + $3, endurance = endurance - $4 WHERE guild_id=$1 AND user_id=$2",
                                interaction.guild_id, interaction.user.id, gain, COUT_ABORDAGE)
        await add_xp(interaction.guild_id, interaction.user.id, 15, 6)
        embed = discord.Embed(
            title="⚔️ Abordage réussi !",
            description=f"Tu prends d'assaut **{description}** ! Butin récupéré : **{gain:,}฿**.",
            color=0x27AE60
        )
    else:
        perte_pv = random.randint(5, 15)
        async with pool.acquire() as conn:
            await conn.execute("UPDATE players SET pv = GREATEST(1, pv - $3), endurance = endurance - $4 WHERE guild_id=$1 AND user_id=$2",
                                interaction.guild_id, interaction.user.id, perte_pv, COUT_ABORDAGE)
        embed = discord.Embed(
            title="⚔️ Abordage repoussé...",
            description=f"L'équipage de **{description}** se défend mieux que prévu ! Tu bats en retraite, un peu amoché (-{perte_pv} PV).",
            color=0x7F0000
        )
    embed.set_footer(text="🌊 One Piece Bot • Mini-jeux Pirates")
    await interaction.followup.send(embed=embed)


# ===== BEUVERIE DE TAVERNE =====

class BeuverieJoinView(discord.ui.View):
    def __init__(self, guild_id, hote: discord.Member):
        super().__init__(timeout=DUREE_JOIN_BEUVERIE)
        self.guild_id = guild_id
        self.participants = {hote.id: hote}
        self.message = None
        self.lancee = False

    def build_embed(self):
        names = [m.mention for m in self.participants.values()]
        embed = discord.Embed(
            title="🍺 Beuverie de taverne — Inscriptions !",
            description=f"Mise d'entrée : **{MISE_BEUVERIE}฿**. Rejoins pour tenter de tout remporter !",
            color=0xE67E22
        )
        embed.add_field(name=f"Participants ({len(names)}/4)", value="\n".join(names) or "Aucun", inline=False)
        embed.set_footer(text=f"🌊 One Piece Bot • Mini-jeux Pirates • {DUREE_JOIN_BEUVERIE}s pour rejoindre (2 minimum)")
        return embed

    @discord.ui.button(label="Rejoindre (30฿)", emoji="🍺", style=discord.ButtonStyle.success)
    async def rejoindre(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.lancee:
            await interaction.response.send_message("La beuverie a déjà commencé !", ephemeral=True)
            return
        if interaction.user.id in self.participants:
            await interaction.response.send_message("Tu es déjà de la partie !", ephemeral=True)
            return
        if len(self.participants) >= 4:
            await interaction.response.send_message("La table est déjà complète (4/4) !", ephemeral=True)
            return

        player = await get_player(self.guild_id, interaction.user.id)
        if player is None or player["faction"] != "Pirate":
            await interaction.response.send_message("⛔ Réservé aux Pirates ayant un personnage.", ephemeral=True)
            return
        if player["berrys"] < MISE_BEUVERIE:
            await interaction.response.send_message(f"Il te faut {MISE_BEUVERIE}฿ pour participer.", ephemeral=True)
            return

        self.participants[interaction.user.id] = interaction.user
        await interaction.response.edit_message(embed=self.build_embed(), view=self)

    async def on_timeout(self):
        self.lancee = True
        for c in self.children:
            c.disabled = True
        self.stop()


@pirate_group.command(name="beuverie", description="Organiser une beuverie de taverne (Pirate, 2-4 joueurs)")
@require_salon("salon_taverne")
async def pirate_beuverie(interaction: discord.Interaction):
    await interaction.response.defer()
    player = await verifier_pirate(interaction)
    if player is None:
        return
    if player["berrys"] < MISE_BEUVERIE:
        await interaction.followup.send(f"Il te faut {MISE_BEUVERIE}฿ pour lancer une beuverie.")
        return

    view = BeuverieJoinView(interaction.guild_id, interaction.user)
    msg = await interaction.followup.send(embed=view.build_embed(), view=view)
    view.message = msg
    await view.wait()

    if len(view.participants) < 2:
        await msg.edit(content="😴 Pas assez de monde pour une vraie beuverie (2 minimum), annulée.", embed=None, view=None)
        return

    membres = list(view.participants.values())
    pool = get_pool()
    async with pool.acquire() as conn:
        for m in membres:
            await conn.execute("UPDATE players SET berrys = berrys - $3 WHERE guild_id=$1 AND user_id=$2", interaction.guild_id, m.id, MISE_BEUVERIE)

    channel = interaction.channel
    restants = {m.id: m for m in membres}
    log = []
    while len(restants) > 1:
        await asyncio.sleep(1.5)
        scores = {uid: random.randint(1, 100) for uid in restants}
        elimine_id = min(scores, key=scores.get)
        elimine = restants.pop(elimine_id)
        log.append(f"{random.choice(ROUNDS_BEUVERIE)} **{elimine.display_name}** craque et quitte la table !")

    gagnant = list(restants.values())[0]
    pot = MISE_BEUVERIE * len(membres)
    async with pool.acquire() as conn:
        await conn.execute("UPDATE players SET berrys = berrys + $3 WHERE guild_id=$1 AND user_id=$2", interaction.guild_id, gagnant.id, pot)
    await add_xp(interaction.guild_id, gagnant.id, 25, 10)

    embed = discord.Embed(
        title="🍺 Beuverie terminée !",
        description="\n".join(log[-5:]) + f"\n\n🏆 **{gagnant.display_name}** tient encore debout et remporte le pot : **{pot:,}฿** !",
        color=0x27AE60
    )
    embed.set_footer(text="🌊 One Piece Bot • Mini-jeux Pirates")
    await channel.send(embed=embed)


# ===== PILLAGE DE CONVOI =====

class PillageJoinView(discord.ui.View):
    def __init__(self, guild_id, hote: discord.Member):
        super().__init__(timeout=DUREE_JOIN_PILLAGE)
        self.guild_id = guild_id
        self.participants = {hote.id: hote}
        self.message = None
        self.lancee = False

    def build_embed(self):
        names = [m.mention for m in self.participants.values()]
        embed = discord.Embed(
            title="🏴‍☠️ Pillage de convoi — Inscriptions !",
            description="Rassemble ton équipage pour un raid coopératif !",
            color=0xE67E22
        )
        embed.add_field(name=f"Participants ({len(names)}/4)", value="\n".join(names) or "Aucun", inline=False)
        embed.set_footer(text=f"🌊 One Piece Bot • Mini-jeux Pirates • {DUREE_JOIN_PILLAGE}s pour rejoindre (2 minimum)")
        return embed

    @discord.ui.button(label="Rejoindre le raid", emoji="🏴‍☠️", style=discord.ButtonStyle.danger)
    async def rejoindre(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.lancee:
            await interaction.response.send_message("Le raid a déjà commencé !", ephemeral=True)
            return
        if interaction.user.id in self.participants:
            await interaction.response.send_message("Tu es déjà de l'équipage !", ephemeral=True)
            return
        if len(self.participants) >= 4:
            await interaction.response.send_message("L'équipage est déjà complet (4/4) !", ephemeral=True)
            return
        player = await get_player(self.guild_id, interaction.user.id)
        if player is None or player["faction"] != "Pirate":
            await interaction.response.send_message("⛔ Réservé aux Pirates ayant un personnage.", ephemeral=True)
            return
        self.participants[interaction.user.id] = interaction.user
        await interaction.response.edit_message(embed=self.build_embed(), view=self)

    async def on_timeout(self):
        self.lancee = True
        for c in self.children:
            c.disabled = True
        self.stop()


class PillageCombatView(discord.ui.View):
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
            await interaction.response.send_message("⛔ Tu ne fais pas partie de ce raid !", ephemeral=True)
            return False
        return True

    def build_embed(self, message=None):
        embed = discord.Embed(title=f"🏴‍☠️ Pillage — {self.description}", color=0xE67E22)
        embed.description = message or "Cliquez sur Piller autant de fois que possible !"
        rempli = round(max(0, self.pv) / self.pv_max * 14) if self.pv_max else 0
        embed.add_field(name=f"PV du convoi — {max(0, self.pv):,}/{self.pv_max:,}", value="🟥" * rempli + "⬜" * (14 - rempli), inline=False)
        embed.set_footer(text="🌊 One Piece Bot • Mini-jeux Pirates")
        return embed

    @discord.ui.button(label="Piller !", emoji="⚔️", style=discord.ButtonStyle.danger)
    async def piller(self, interaction: discord.Interaction, button: discord.ui.Button):
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
            embed = self.build_embed(f"🏆 **{self.description}** est pillé avec succès !\n\n" + "\n".join(lignes))
            embed.color = 0x27AE60
            await self.message.edit(embed=embed, view=self)
            return

        await self.message.edit(embed=self.build_embed(f"**{interaction.user.display_name}** frappe pour **{degats}** dégâts !"), view=self)

    async def on_timeout(self):
        if self.termine:
            return
        self.termine = True
        for c in self.children:
            c.disabled = True
        if self.message:
            try:
                embed = self.build_embed(f"⏱️ Le temps est écoulé, **{self.description}** parvient à s'échapper.")
                embed.color = 0x7F0000
                await self.message.edit(embed=embed, view=self)
            except discord.HTTPException:
                pass


@pirate_group.command(name="pillage_convoi", description="Piller un gros convoi en équipage (Pirate, coopératif 2-4)")
@require_salon("salon_taverne")
async def pirate_pillage_convoi(interaction: discord.Interaction):
    await interaction.response.defer()
    player = await verifier_pirate(interaction)
    if player is None:
        return

    view = PillageJoinView(interaction.guild_id, interaction.user)
    msg = await interaction.followup.send(embed=view.build_embed(), view=view)
    view.message = msg
    await view.wait()

    if len(view.participants) < 2:
        await msg.edit(content="😴 Pas assez de monde pour un raid digne de ce nom (2 minimum), annulé.", embed=None, view=None)
        return

    description, pv_min, pv_max, b_min, b_max = random.choice(GROS_CONVOIS_PILLAGE)
    pv_convoi = random.randint(pv_min, pv_max)
    membres = list(view.participants.values())

    combat_view = PillageCombatView(interaction.guild_id, description, pv_convoi, [m.id for m in membres], b_min, b_max)
    embed = combat_view.build_embed(f"L'équipage repère **{description}** ! À l'abordage !")
    combat_msg = await interaction.channel.send(embed=embed, view=combat_view)
    combat_view.message = combat_msg


# ===== DUEL AU SABRE ÉCLAIR =====

class DuelEclairView(discord.ui.View):
    def __init__(self, guild_id, p1: discord.Member, p2: discord.Member):
        super().__init__(timeout=30)
        self.guild_id = guild_id
        self.p1 = p1
        self.p2 = p2
        self.pret = False
        self.termine = False
        self.message = None

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        return interaction.user.id in (self.p1.id, self.p2.id)

    @discord.ui.button(label="⏳ Attendez...", style=discord.ButtonStyle.secondary, disabled=False)
    async def degainer(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.termine:
            return
        self.termine = True
        for c in self.children:
            c.disabled = True

        if not self.pret:
            perdant = interaction.user
            gagnant = self.p2 if perdant.id == self.p1.id else self.p1
            texte = f"⚠️ **{perdant.display_name}** dégaine trop tôt ! **{gagnant.display_name}** remporte le duel par défaut."
        else:
            gagnant = interaction.user
            perdant = self.p2 if gagnant.id == self.p1.id else self.p1
            texte = f"⚡ **{gagnant.display_name}** dégaine en un éclair et remporte le duel contre **{perdant.display_name}** !"

        gain = random.randint(30, 70)
        pool = get_pool()
        async with pool.acquire() as conn:
            await conn.execute("UPDATE players SET berrys = berrys + $3 WHERE guild_id=$1 AND user_id=$2", self.guild_id, gagnant.id, gain)
        await add_xp(self.guild_id, gagnant.id, 15, 6)

        embed = discord.Embed(title="🗡️ Duel au sabre éclair", description=f"{texte}\n\n+{gain}฿ pour le vainqueur !", color=0x27AE60 if self.pret else 0x7F0000)
        embed.set_footer(text="🌊 One Piece Bot • Mini-jeux Pirates")
        await interaction.response.edit_message(embed=embed, view=self)

    async def lancer_signal(self):
        await asyncio.sleep(random.uniform(3, 7))
        if self.termine:
            return
        self.pret = True
        self.children[0].label = "⚡ DÉGAINEZ !"
        self.children[0].style = discord.ButtonStyle.danger
        if self.message:
            try:
                embed = discord.Embed(title="🗡️ Duel au sabre éclair", description="⚡ **MAINTENANT !**", color=0xE67E22)
                embed.set_footer(text="🌊 One Piece Bot • Mini-jeux Pirates")
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
                await self.message.edit(content="⌛ Personne n'a dégainé à temps.", embed=None, view=self)
            except discord.HTTPException:
                pass


@pirate_group.command(name="duel_eclair", description="Défier un autre Pirate en duel de réflexes (Pirate)")
@app_commands.describe(adversaire="Le Pirate à défier")
@require_salon("salon_taverne")
async def pirate_duel_eclair(interaction: discord.Interaction, adversaire: discord.Member):
    await interaction.response.defer()
    player = await verifier_pirate(interaction)
    if player is None:
        return
    if adversaire.id == interaction.user.id or adversaire.bot:
        await interaction.followup.send("Choix invalide 🙃")
        return
    adversaire_data = await get_player(interaction.guild_id, adversaire.id)
    if adversaire_data is None or adversaire_data["faction"] != "Pirate":
        await interaction.followup.send(f"⛔ {adversaire.display_name} doit être Pirate et avoir un personnage.")
        return

    view = DuelEclairView(interaction.guild_id, interaction.user, adversaire)
    embed = discord.Embed(
        title="🗡️ Duel au sabre éclair",
        description=f"{interaction.user.mention} défie {adversaire.mention} ! Attendez le signal, et surtout... ne dégainez pas trop tôt.",
        color=0x2C3E50
    )
    embed.set_footer(text="🌊 One Piece Bot • Mini-jeux Pirates")
    msg = await interaction.followup.send(content=adversaire.mention, embed=embed, view=view)
    view.message = msg
    asyncio.create_task(view.lancer_signal())


def setup_pirate_minijeux_commands(bot):
    bot.tree.add_command(pirate_group)
