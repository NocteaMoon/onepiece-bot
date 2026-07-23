import discord
from discord import app_commands
import random
import asyncio
import datetime
from database.db import get_pool
from utils.players import get_player, add_xp
from utils.channel_check import require_salon
from utils.reputation import add_reputation_faction, MONTANT_COMBAT_VICTOIRE
from utils.notoriete import add_notoriete, MONTANT_MINIJEU_COOP
from utils.quetes import increment_quest_progress
from data.civil_flavor import OBJETS_ENCHERES, NPCS_NEGOCIATION, RARETE_RECOMPENSE_ARTISANAT

atelier_group = app_commands.Group(name="atelier", description="Mini-jeux exclusifs à la faction Civil")

COUT_RAPIDITE = 10
COOLDOWN_RAPIDITE = 15
COOLDOWN_ARTISANAT = 20
COUT_NEGOCIATION = 10
COOLDOWN_NEGOCIATION = 20
DUREE_JOIN_ENCHERES = 45
DUREE_BID_ENCHERES = 45
DUREE_JOIN_FOIRE = 60

_last_rapidite = {}
_last_artisanat = {}
_last_negociation = {}


async def verifier_civil(interaction: discord.Interaction):
    player = await get_player(interaction.guild_id, interaction.user.id)
    if player is None:
        await interaction.followup.send("Tu n'as pas encore de personnage ! Lance `/commencer` pour débuter l'aventure 🏴‍☠️")
        return None
    if player["faction"] != "Civil":
        await interaction.followup.send("⛔ Ces activités sont réservées à la faction **Civil**.")
        return None
    return player


# ===== DÉFI DE RAPIDITÉ =====

class RapiditeView(discord.ui.View):
    def __init__(self, guild_id, user_id):
        super().__init__(timeout=15)
        self.guild_id = guild_id
        self.user_id = user_id
        self.signal_time = None
        self.termine = False
        self.message = None

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        return interaction.user.id == self.user_id

    @discord.ui.button(label="Préparez l'outil...", style=discord.ButtonStyle.secondary)
    async def cliquer(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.termine:
            return
        self.termine = True
        for c in self.children:
            c.disabled = True

        now = datetime.datetime.utcnow()
        if self.signal_time is None:
            gain = random.randint(5, 15)
            texte = "⚠️ Tu actionnes l'outil trop tôt, le geste est raté."
            couleur = 0x7F0000
        else:
            elapsed = (now - self.signal_time).total_seconds()
            if elapsed < 1.0:
                gain = random.randint(55, 85)
                texte = f"⏱️ **Geste parfait !** ({elapsed:.2f}s de réaction)"
                couleur = 0xF1C40F
            elif elapsed < 2.5:
                gain = random.randint(30, 50)
                texte = f"⏱️ Bon geste ! ({elapsed:.2f}s de réaction)"
                couleur = 0x27AE60
            else:
                gain = random.randint(12, 28)
                texte = f"⏱️ Geste correct, mais un peu lent ({elapsed:.2f}s)."
                couleur = 0x95A5A6

        pool = get_pool()
        async with pool.acquire() as conn:
            await conn.execute("UPDATE players SET berrys = berrys + $3 WHERE guild_id=$1 AND user_id=$2", self.guild_id, self.user_id, gain)
        await add_xp(self.guild_id, self.user_id, 12, 5)
        await add_reputation_faction(self.guild_id, self.user_id, "Civil", MONTANT_COMBAT_VICTOIRE)
        await increment_quest_progress(self.guild_id, self.user_id, "civil_minijeu")

        embed = discord.Embed(title="⏱️ Défi de rapidité", description=f"{texte}\n\n**+{gain}฿**", color=couleur)
        embed.set_footer(text="🌊 One Piece Bot • Mini-jeux Civils")
        await interaction.response.edit_message(embed=embed, view=self)

    async def lancer_signal(self):
        await asyncio.sleep(random.uniform(3, 7))
        if self.termine:
            return
        self.signal_time = datetime.datetime.utcnow()
        self.children[0].label = "⏱️ MAINTENANT !"
        self.children[0].style = discord.ButtonStyle.success
        if self.message:
            try:
                embed = discord.Embed(title="⏱️ Défi de rapidité", description="⏱️ **VAS-Y !**", color=0xE67E22)
                embed.set_footer(text="🌊 One Piece Bot • Mini-jeux Civils")
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
                await self.message.edit(content="⌛ Trop lent, l'occasion est passée.", embed=None, view=self)
            except discord.HTTPException:
                pass


@atelier_group.command(name="rapidite", description="Défi de rapidité et de précision en atelier (Civil)")
@require_salon("salon_taverne")
async def atelier_rapidite(interaction: discord.Interaction):
    await interaction.response.defer()
    player = await verifier_civil(interaction)
    if player is None:
        return

    key = (interaction.guild_id, interaction.user.id)
    now = datetime.datetime.utcnow()
    last = _last_rapidite.get(key)
    if last:
        elapsed = (now - last).total_seconds() / 60
        if elapsed < COOLDOWN_RAPIDITE:
            restant = int(COOLDOWN_RAPIDITE - elapsed)
            await interaction.followup.send(f"😮‍💨 Tu dois encore attendre **{restant} min** avant un nouveau défi.")
            return
    if player["endurance"] < COUT_RAPIDITE:
        await interaction.followup.send(f"😮‍💨 Il te faut {COUT_RAPIDITE} endurance pour ce défi (tu as {player['endurance']}).")
        return

    pool = get_pool()
    async with pool.acquire() as conn:
        await conn.execute("UPDATE players SET endurance = endurance - $3 WHERE guild_id=$1 AND user_id=$2",
                            interaction.guild_id, interaction.user.id, COUT_RAPIDITE)
    _last_rapidite[key] = now

    view = RapiditeView(interaction.guild_id, interaction.user.id)
    embed = discord.Embed(title="⏱️ Défi de rapidité", description="Attends le bon moment, puis agis vite !", color=0x2C3E50)
    embed.set_footer(text="🌊 One Piece Bot • Mini-jeux Civils")
    msg = await interaction.followup.send(embed=embed, view=view)
    view.message = msg
    asyncio.create_task(view.lancer_signal())


# ===== CONCOURS D'ARTISANAT =====

async def ingredient_autocomplete(interaction: discord.Interaction, current: str):
    pool = get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch("""
            SELECT inventory.id AS inv_id, shop_items.nom, shop_items.rarete, inventory.quantite
            FROM inventory JOIN shop_items ON inventory.item_id = shop_items.id
            WHERE inventory.guild_id=$1 AND inventory.user_id=$2 AND shop_items.categorie = 'Ingrédient' AND inventory.quantite > 0
        """, interaction.guild_id, interaction.user.id)
    filtered = [r for r in rows if current.lower() in r["nom"].lower()][:25]
    return [app_commands.Choice(name=f"{r['nom']} x{r['quantite']} ({r['rarete']})", value=r["inv_id"]) for r in filtered]


@atelier_group.command(name="artisanat", description="Présenter un ingrédient à un concours d'artisanat (Civil)")
@app_commands.describe(ingredient="L'ingrédient à présenter (sera consommé)")
@app_commands.autocomplete(ingredient=ingredient_autocomplete)
@require_salon("salon_taverne")
async def atelier_artisanat(interaction: discord.Interaction, ingredient: int):
    await interaction.response.defer()
    player = await verifier_civil(interaction)
    if player is None:
        return

    key = (interaction.guild_id, interaction.user.id)
    now = datetime.datetime.utcnow()
    last = _last_artisanat.get(key)
    if last:
        elapsed = (now - last).total_seconds() / 60
        if elapsed < COOLDOWN_ARTISANAT:
            restant = int(COOLDOWN_ARTISANAT - elapsed)
            await interaction.followup.send(f"😮‍💨 Tu dois encore attendre **{restant} min** avant un nouveau concours.")
            return

    pool = get_pool()
    async with pool.acquire() as conn:
        inv_row = await conn.fetchrow(
            "SELECT * FROM inventory WHERE id=$1 AND guild_id=$2 AND user_id=$3",
            ingredient, interaction.guild_id, interaction.user.id
        )
        if not inv_row or inv_row["quantite"] <= 0:
            await interaction.followup.send("Cet ingrédient n'est plus dans ton inventaire.")
            return
        item = await conn.fetchrow("SELECT nom, rarete, categorie FROM shop_items WHERE id=$1", inv_row["item_id"])
        if not item or item["categorie"] != "Ingrédient":
            await interaction.followup.send("Cet objet n'est pas un ingrédient valide pour ce concours.")
            return

        async with conn.transaction():
            if inv_row["quantite"] > 1:
                await conn.execute("UPDATE inventory SET quantite = quantite - 1 WHERE id=$1", inv_row["id"])
            else:
                await conn.execute("DELETE FROM inventory WHERE id=$1", inv_row["id"])

    _last_artisanat[key] = now
    b_min, b_max, chance_chef_oeuvre = RARETE_RECOMPENSE_ARTISANAT.get(item["rarete"], (15, 30, 0.05))
    gain = random.randint(b_min, b_max)
    chef_oeuvre = random.random() < chance_chef_oeuvre
    if chef_oeuvre:
        gain = round(gain * 3)

    async with pool.acquire() as conn:
        await conn.execute("UPDATE players SET berrys = berrys + $3 WHERE guild_id=$1 AND user_id=$2", interaction.guild_id, interaction.user.id, gain)
    await add_xp(interaction.guild_id, interaction.user.id, 15 + (15 if chef_oeuvre else 0), 6)
    await add_reputation_faction(interaction.guild_id, interaction.user.id, "Civil", MONTANT_COMBAT_VICTOIRE)
    await increment_quest_progress(interaction.guild_id, interaction.user.id, "civil_minijeu")

    if chef_oeuvre:
        embed = discord.Embed(
            title="🏆 CHEF-D'ŒUVRE !",
            description=f"Ta pièce faite à partir de **{item['nom']}** émerveille le jury ! Récompense exceptionnelle : **{gain:,}฿** !",
            color=0xF1C40F
        )
    else:
        embed = discord.Embed(
            title="🔨 Concours d'artisanat",
            description=f"Ta pièce à base de **{item['nom']}** est bien reçue par le jury. Récompense : **{gain:,}฿**.",
            color=0x27AE60
        )
    embed.set_footer(text="🌊 One Piece Bot • Mini-jeux Civils")
    await interaction.followup.send(embed=embed)


# ===== NÉGOCIATION =====

APPROCHES_NEGOCIATION = {
    "ferme": ("Position ferme", 0.55, (20, 45)),
    "souple": ("Approche souple", 0.65, (15, 35)),
    "charme": ("Charme", 0.60, (18, 40)),
}

class NegociationView(discord.ui.View):
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

        label, chance, (b_min, b_max) = APPROCHES_NEGOCIATION[approche_key]
        reussi = random.random() < chance

        pool = get_pool()
        await increment_quest_progress(self.guild_id, self.user_id, "civil_minijeu")
        if reussi:
            gain = random.randint(b_min, b_max)
            async with pool.acquire() as conn:
                await conn.execute("UPDATE players SET berrys = berrys + $3 WHERE guild_id=$1 AND user_id=$2", self.guild_id, self.user_id, gain)
            await add_xp(self.guild_id, self.user_id, 15, 6)
            await add_reputation_faction(self.guild_id, self.user_id, "Civil", MONTANT_COMBAT_VICTOIRE)
            texte = f"💬 Ta **{label}** convainc {self.npc} ! Tu repars avec **{gain}฿** de bénéfice."
            couleur = 0x27AE60
        else:
            texte = f"💬 {self.npc.capitalize()} ne cède pas face à ta **{label}**."
            couleur = 0x7F0000

        embed = discord.Embed(title="💬 Négociation", description=texte, color=couleur)
        embed.set_footer(text="🌊 One Piece Bot • Mini-jeux Civils")
        await interaction.response.edit_message(embed=embed, view=self)

    @discord.ui.button(label="Position ferme", emoji="✊", style=discord.ButtonStyle.danger)
    async def ferme(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.resoudre(interaction, "ferme")

    @discord.ui.button(label="Approche souple", emoji="🤝", style=discord.ButtonStyle.primary)
    async def souple(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.resoudre(interaction, "souple")

    @discord.ui.button(label="Charme", emoji="😊", style=discord.ButtonStyle.secondary)
    async def charme(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.resoudre(interaction, "charme")

    async def on_timeout(self):
        if self.termine:
            return
        for c in self.children:
            c.disabled = True


@atelier_group.command(name="negociation", description="Négocier avec un marchand (Civil)")
@require_salon("salon_taverne")
async def atelier_negociation(interaction: discord.Interaction):
    await interaction.response.defer()
    player = await verifier_civil(interaction)
    if player is None:
        return

    key = (interaction.guild_id, interaction.user.id)
    now = datetime.datetime.utcnow()
    last = _last_negociation.get(key)
    if last:
        elapsed = (now - last).total_seconds() / 60
        if elapsed < COOLDOWN_NEGOCIATION:
            restant = int(COOLDOWN_NEGOCIATION - elapsed)
            await interaction.followup.send(f"😮‍💨 Tu dois encore attendre **{restant} min** avant une nouvelle négociation.")
            return
    if player["endurance"] < COUT_NEGOCIATION:
        await interaction.followup.send(f"😮‍💨 Il te faut {COUT_NEGOCIATION} endurance pour négocier (tu as {player['endurance']}).")
        return

    pool = get_pool()
    async with pool.acquire() as conn:
        await conn.execute("UPDATE players SET endurance = endurance - $3 WHERE guild_id=$1 AND user_id=$2",
                            interaction.guild_id, interaction.user.id, COUT_NEGOCIATION)
    _last_negociation[key] = now

    npc = random.choice(NPCS_NEGOCIATION)
    view = NegociationView(interaction.guild_id, interaction.user.id, npc)
    embed = discord.Embed(title="💬 Négociation", description=f"Tu fais face à **{npc}**. Quelle approche choisis-tu ?", color=0x2C3E50)
    embed.set_footer(text="🌊 One Piece Bot • Mini-jeux Civils")
    await interaction.followup.send(embed=embed, view=view)


# ===== ENCHÈRES (secrètes) =====

class EncheresJoinView(discord.ui.View):
    def __init__(self, guild_id, hote: discord.Member):
        super().__init__(timeout=DUREE_JOIN_ENCHERES)
        self.guild_id = guild_id
        self.participants = {hote.id: hote}
        self.message = None
        self.lancee = False

    def build_embed(self):
        names = [m.mention for m in self.participants.values()]
        embed = discord.Embed(
            title="🏺 Vente aux enchères — Inscriptions !",
            description="Un objet mystérieux sera bientôt mis aux enchères. Rejoins pour tenter ta chance !",
            color=0xD4A017
        )
        embed.add_field(name=f"Participants ({len(names)}/6)", value="\n".join(names) or "Aucun", inline=False)
        embed.set_footer(text=f"🌊 One Piece Bot • Mini-jeux Civils • {DUREE_JOIN_ENCHERES}s pour rejoindre (2 minimum)")
        return embed

    @discord.ui.button(label="Rejoindre l'enchère", emoji="🏺", style=discord.ButtonStyle.primary)
    async def rejoindre(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.lancee:
            await interaction.response.send_message("L'enchère a déjà commencé !", ephemeral=True)
            return
        if interaction.user.id in self.participants:
            await interaction.response.send_message("Tu es déjà inscrit(e) !", ephemeral=True)
            return
        if len(self.participants) >= 6:
            await interaction.response.send_message("L'enchère est déjà complète (6/6) !", ephemeral=True)
            return
        player = await get_player(self.guild_id, interaction.user.id)
        if player is None or player["faction"] != "Civil":
            await interaction.response.send_message("⛔ Réservé aux Civils ayant un personnage.", ephemeral=True)
            return
        self.participants[interaction.user.id] = interaction.user
        await interaction.response.edit_message(embed=self.build_embed(), view=self)

    async def on_timeout(self):
        self.lancee = True
        for c in self.children:
            c.disabled = True
        self.stop()


class EncheresBidModal(discord.ui.Modal, title="Enchère secrète"):
    def __init__(self, bid_view, user_id):
        super().__init__()
        self.bid_view = bid_view
        self.user_id = user_id
        self.montant = discord.ui.TextInput(label="Montant de ton enchère (Berrys)", max_length=7)
        self.add_item(self.montant)

    async def on_submit(self, interaction: discord.Interaction):
        try:
            montant = int(self.montant.value)
        except ValueError:
            await interaction.response.send_message("⛔ Doit être un nombre entier.", ephemeral=True)
            return
        if montant <= 0:
            await interaction.response.send_message("⛔ L'enchère doit être positive.", ephemeral=True)
            return
        player = await get_player(self.bid_view.guild_id, self.user_id)
        if montant > player["berrys"]:
            await interaction.response.send_message(f"⛔ Tu n'as que {player['berrys']:,}฿ en poche.", ephemeral=True)
            return
        self.bid_view.bids[self.user_id] = montant
        await interaction.response.send_message(f"✅ Ton enchère secrète de **{montant:,}฿** est enregistrée.", ephemeral=True)


class EncheresBidView(discord.ui.View):
    def __init__(self, guild_id, description, valeur, participant_ids):
        super().__init__(timeout=DUREE_BID_ENCHERES)
        self.guild_id = guild_id
        self.description = description
        self.valeur = valeur
        self.participant_ids = set(participant_ids)
        self.bids = {}
        self.message = None

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id not in self.participant_ids:
            await interaction.response.send_message("⛔ Tu ne participes pas à cette enchère !", ephemeral=True)
            return False
        return True

    @discord.ui.button(label="Placer une enchère secrète", emoji="🏺", style=discord.ButtonStyle.primary)
    async def enchere(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(EncheresBidModal(self, interaction.user.id))

    async def on_timeout(self):
        for c in self.children:
            c.disabled = True

        if not self.bids:
            embed = discord.Embed(
                title="🏺 Enchère terminée",
                description=f"Personne n'a osé enchérir sur {self.description}... il retourne dans un coffre poussiéreux.",
                color=0x95A5A6
            )
            embed.set_footer(text="🌊 One Piece Bot • Mini-jeux Civils")
            if self.message:
                try:
                    await self.message.edit(embed=embed, view=self)
                except discord.HTTPException:
                    pass
            return

        gagnant_id = max(self.bids, key=self.bids.get)
        bid_gagnant = self.bids[gagnant_id]

        pool = get_pool()
        async with pool.acquire() as conn:
            player = await conn.fetchrow("SELECT berrys FROM players WHERE guild_id=$1 AND user_id=$2", self.guild_id, gagnant_id)
            bid_final = min(bid_gagnant, player["berrys"])
            await conn.execute(
                "UPDATE players SET berrys = berrys - $3 + $4 WHERE guild_id=$1 AND user_id=$2",
                self.guild_id, gagnant_id, bid_final, self.valeur
            )
        await add_xp(self.guild_id, gagnant_id, 20, 8)
        await add_reputation_faction(self.guild_id, gagnant_id, "Civil", MONTANT_COMBAT_VICTOIRE)
        await increment_quest_progress(self.guild_id, gagnant_id, "civil_minijeu")

        profit = self.valeur - bid_final
        resultat_txt = f"un joli bénéfice de **+{profit:,}฿**" if profit >= 0 else f"une perte sèche de **{profit:,}฿**"
        embed = discord.Embed(
            title="🏺 Enchère conclue !",
            description=(
                f"{self.description.capitalize()} valait en réalité **{self.valeur:,}฿**.\n\n"
                f"🏆 <@{gagnant_id}> remporte l'objet avec une enchère secrète de **{bid_final:,}฿**, "
                f"pour {resultat_txt} !"
            ),
            color=0x27AE60 if profit >= 0 else 0x7F0000
        )
        embed.set_footer(text="🌊 One Piece Bot • Mini-jeux Civils")
        if self.message:
            try:
                await self.message.edit(embed=embed, view=self)
            except discord.HTTPException:
                pass


@atelier_group.command(name="encheres", description="Organiser une vente aux enchères secrète (Civil, 2-6 joueurs)")
@require_salon("salon_taverne")
async def atelier_encheres(interaction: discord.Interaction):
    await interaction.response.defer()
    player = await verifier_civil(interaction)
    if player is None:
        return

    view = EncheresJoinView(interaction.guild_id, interaction.user)
    msg = await interaction.followup.send(embed=view.build_embed(), view=view)
    view.message = msg
    await view.wait()

    if len(view.participants) < 2:
        await msg.edit(content="😴 Pas assez d'acheteurs intéressés (2 minimum), enchère annulée.", embed=None, view=None)
        return

    description = random.choice(OBJETS_ENCHERES)
    valeur = random.randint(150, 450)
    membres = list(view.participants.values())

    bid_view = EncheresBidView(interaction.guild_id, description, valeur, [m.id for m in membres])
    embed = discord.Embed(
        title="🏺 Vente aux enchères secrète !",
        description=f"L'objet du jour : **{description}**. Sa vraie valeur reste secrète jusqu'à la fin. Placez votre enchère à l'aveugle !",
        color=0xD4A017
    )
    embed.set_footer(text=f"🌊 One Piece Bot • Mini-jeux Civils • {DUREE_BID_ENCHERES}s pour enchérir")
    bid_msg = await interaction.channel.send(embed=embed, view=bid_view)
    bid_view.message = bid_msg


# ===== FOIRE DU VILLAGE (coopératif) =====

class FoireJoinView(discord.ui.View):
    def __init__(self, guild_id, hote: discord.Member):
        super().__init__(timeout=DUREE_JOIN_FOIRE)
        self.guild_id = guild_id
        self.participants = {hote.id: hote}
        self.message = None
        self.lancee = False

    def build_embed(self):
        names = [m.mention for m in self.participants.values()]
        embed = discord.Embed(
            title="🎪 Foire du village — Préparatifs !",
            description="Rassemble du monde pour organiser une grande foire communautaire !",
            color=0xE67E22
        )
        embed.add_field(name=f"Participants ({len(names)}/6)", value="\n".join(names) or "Aucun", inline=False)
        embed.set_footer(text=f"🌊 One Piece Bot • Mini-jeux Civils • {DUREE_JOIN_FOIRE}s pour rejoindre (2 minimum)")
        return embed

    @discord.ui.button(label="Aider aux préparatifs", emoji="🎪", style=discord.ButtonStyle.success)
    async def rejoindre(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.lancee:
            await interaction.response.send_message("Les préparatifs ont déjà commencé !", ephemeral=True)
            return
        if interaction.user.id in self.participants:
            await interaction.response.send_message("Tu aides déjà !", ephemeral=True)
            return
        if len(self.participants) >= 6:
            await interaction.response.send_message("Assez de monde pour l'instant (6/6) !", ephemeral=True)
            return
        player = await get_player(self.guild_id, interaction.user.id)
        if player is None or player["faction"] != "Civil":
            await interaction.response.send_message("⛔ Réservé aux Civils ayant un personnage.", ephemeral=True)
            return
        self.participants[interaction.user.id] = interaction.user
        await interaction.response.edit_message(embed=self.build_embed(), view=self)

    async def on_timeout(self):
        self.lancee = True
        for c in self.children:
            c.disabled = True
        self.stop()


class FoireContributionView(discord.ui.View):
    def __init__(self, guild_id, objectif, participant_ids):
        super().__init__(timeout=300)
        self.guild_id = guild_id
        self.objectif = objectif
        self.progres = 0
        self.participant_ids = set(participant_ids)
        self.contributions = {uid: 0 for uid in participant_ids}
        self.termine = False
        self.message = None

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id not in self.participant_ids:
            await interaction.response.send_message("⛔ Tu ne participes pas à cette foire !", ephemeral=True)
            return False
        return True

    def build_embed(self, message=None):
        embed = discord.Embed(title="🎪 Foire du village", color=0xE67E22)
        embed.description = message or "Cliquez sur Participer autant de fois que possible !"
        rempli = round(max(0, self.progres) / self.objectif * 14) if self.objectif else 0
        rempli = min(rempli, 14)
        embed.add_field(name=f"Préparatifs — {max(0, self.progres):,}/{self.objectif:,}", value="🟨" * rempli + "⬜" * (14 - rempli), inline=False)
        embed.set_footer(text="🌊 One Piece Bot • Mini-jeux Civils")
        return embed

    @discord.ui.button(label="Participer aux préparatifs", emoji="🎪", style=discord.ButtonStyle.success)
    async def participer(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        if self.termine:
            return
        player = await get_player(self.guild_id, interaction.user.id)
        bonus_metier = (player["metier_xp"] or 0) // 50
        contribution = random.randint(10, 20) + bonus_metier
        self.progres += contribution
        self.contributions[interaction.user.id] += contribution

        if self.progres >= self.objectif:
            self.termine = True
            for c in self.children:
                c.disabled = True
            total = sum(self.contributions.values()) or 1
            gain_total = random.randint(200, 350)
            pool = get_pool()
            lignes = []
            for uid, contrib in self.contributions.items():
                part = max(15, round(gain_total * contrib / total))
                async with pool.acquire() as conn:
                    await conn.execute("UPDATE players SET berrys = berrys + $3 WHERE guild_id=$1 AND user_id=$2", self.guild_id, uid, part)
                await add_xp(self.guild_id, uid, 25, 10)
                await add_reputation_faction(self.guild_id, uid, "Civil", MONTANT_COMBAT_VICTOIRE)
                await add_notoriete(self.guild_id, uid, MONTANT_MINIJEU_COOP)
                await increment_quest_progress(self.guild_id, uid, "civil_minijeu")
                member = interaction.guild.get_member(uid)
                lignes.append(f"{member.mention if member else uid} : +{part}฿")
            embed = self.build_embed("🎉 La foire est un franc succès grâce à la contribution de tous !\n\n" + "\n".join(lignes))
            embed.color = 0x27AE60
            await self.message.edit(embed=embed, view=self)
            return

        await self.message.edit(embed=self.build_embed(f"**{interaction.user.display_name}** contribue avec **{contribution}** points de préparation !"), view=self)

    async def on_timeout(self):
        if self.termine:
            return
        self.termine = True
        for c in self.children:
            c.disabled = True
        if self.message:
            try:
                embed = self.build_embed("⏱️ Le temps est écoulé, la foire n'a pas pu se tenir à temps cette fois.")
                embed.color = 0x7F0000
                await self.message.edit(embed=embed, view=self)
            except discord.HTTPException:
                pass


@atelier_group.command(name="foire", description="Organiser une foire du village en communauté (Civil, coopératif 2-6)")
@require_salon("salon_taverne")
async def atelier_foire(interaction: discord.Interaction):
    await interaction.response.defer()
    player = await verifier_civil(interaction)
    if player is None:
        return

    view = FoireJoinView(interaction.guild_id, interaction.user)
    msg = await interaction.followup.send(embed=view.build_embed(), view=view)
    view.message = msg
    await view.wait()

    if len(view.participants) < 2:
        await msg.edit(content="😴 Pas assez de bras pour organiser une vraie foire (2 minimum), reportée.", embed=None, view=None)
        return

    objectif = random.randint(150, 220)
    membres = list(view.participants.values())

    contrib_view = FoireContributionView(interaction.guild_id, objectif, [m.id for m in membres])
    embed = contrib_view.build_embed("Les préparatifs commencent, chacun met la main à la pâte !")
    contrib_msg = await interaction.channel.send(embed=embed, view=contrib_view)
    contrib_view.message = contrib_msg


def setup_civil_minijeux_commands(bot):
    bot.tree.add_command(atelier_group)
