import discord
from discord import app_commands
import random
from database.db import get_pool
from utils.players import get_player, add_xp
from utils.channel_check import require_salon
from utils.announcements import announce_level_up

COUT_ENDURANCE = 12

ADVERSAIRES_PVE = [
    {"nom": "un marin bedonnant bien éméché", "difficulte": 15, "berrys_min": 20, "berrys_max": 40, "xp": 15, "xpc": 6},
    {"nom": "un docker aux bras noueux", "difficulte": 35, "berrys_min": 35, "berrys_max": 65, "xp": 25, "xpc": 10},
    {"nom": "un ancien second de navire", "difficulte": 55, "berrys_min": 55, "berrys_max": 100, "xp": 40, "xpc": 16},
    {"nom": "le colosse de la taverne", "difficulte": 75, "berrys_min": 90, "berrys_max": 160, "xp": 60, "xpc": 24},
]

REACTIONS_BON_TIMING = [
    "pousse au moment parfait !",
    "place un effort bien senti, du terrain est gagné !",
    "a une prise solide, il/elle avance !",
    "sent l'adversaire vaciller !",
]

REACTIONS_MAUVAIS_TIMING = [
    "pousse trop tôt, le geste est mal engagé...",
    "perd l'équilibre un instant...",
    "se fait surprendre par un geste précipité...",
    "voit sa prise déraper légèrement...",
]

def barre(valeur, taille=10):
    valeur = max(0, min(100, valeur))
    rempli = round(valeur / 100 * taille)
    return "🟦" * rempli + "⬜" * (taille - rempli)


# ===== VERSION SOLO (PvE) =====

class BrasDeFerPvEView(discord.ui.View):
    def __init__(self, guild_id, user_id, adversaire, force_joueur):
        super().__init__(timeout=45)
        self.guild_id = guild_id
        self.user_id = user_id
        self.adversaire = adversaire
        self.force_joueur = force_joueur
        self.position = 50
        self.termine = False
        self.message = None

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("⛔ Ce bras de fer ne te concerne pas !", ephemeral=True)
            return False
        return True

    def build_embed(self, message: str = None):
        embed = discord.Embed(title=f"💪 Bras de fer contre {self.adversaire['nom']}", color=0xC0392B)
        embed.description = message or "Vos mains se serrent sur la table, la tension monte..."
        embed.add_field(name="Toi ⬅️ ———— ➡️ Adversaire", value=barre(self.position), inline=False)
        embed.set_footer(text="🌊 One Piece Bot • Défis de taverne")
        return embed

    async def finir(self, victoire: bool, message: str):
        self.termine = True
        for c in self.children:
            c.disabled = True

        niveaux_gagnes = 0
        nouveau_niveau = None
        if victoire:
            berrys_gain = random.randint(self.adversaire["berrys_min"], self.adversaire["berrys_max"])
            pool = get_pool()
            async with pool.acquire() as conn:
                await conn.execute(
                    "UPDATE players SET berrys = berrys + $3 WHERE guild_id=$1 AND user_id=$2",
                    self.guild_id, self.user_id, berrys_gain
                )
            niveaux_gagnes, nouveau_niveau = await add_xp(self.guild_id, self.user_id, self.adversaire["xp"], self.adversaire["xpc"])
            message += f"\n\n🏆 Tu remportes **{berrys_gain} Berrys** !"

        embed = self.build_embed(message)
        embed.color = 0x27AE60 if victoire else 0xC0392B
        await self.message.edit(embed=embed, view=self)
        return niveaux_gagnes, nouveau_niveau

    @discord.ui.button(label="Pousser !", emoji="💪", style=discord.ButtonStyle.danger)
    async def pousser(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        if self.termine:
            return

        reussite = random.randint(1, 100) > self.adversaire["difficulte"] - (self.force_joueur // 3)
        if reussite:
            gain = random.randint(8, 15)
            self.position += gain
            message = f"Tu {random.choice(REACTIONS_BON_TIMING)}"
        else:
            perte = random.randint(5, 12)
            self.position -= perte
            message = f"Tu {random.choice(REACTIONS_MAUVAIS_TIMING)}"

        if self.position >= 100:
            niveaux_gagnes, nouveau_niveau = await self.finir(True, "🎉 Tu plaques le bras de ton adversaire sur la table !")
            if niveaux_gagnes > 0:
                await announce_level_up(interaction, interaction.user, nouveau_niveau)
            return
        if self.position <= 0:
            await self.finir(False, "💥 Ton bras cède, l'adversaire triomphe dans les rires de la taverne...")
            return

        await self.message.edit(embed=self.build_embed(message), view=self)

    async def on_timeout(self):
        for c in self.children:
            c.disabled = True
        if self.message:
            try:
                await self.message.edit(view=self)
            except discord.HTTPException:
                pass


# ===== VERSION PVP (2 joueurs) =====

class BrasDeFerPvPView(discord.ui.View):
    def __init__(self, guild_id, p1_id, p1_name, p1_force, p2_id, p2_name, p2_force):
        super().__init__(timeout=60)
        self.guild_id = guild_id
        self.p1 = {"id": p1_id, "name": p1_name, "force": p1_force}
        self.p2 = {"id": p2_id, "name": p2_name, "force": p2_force}
        self.position = 50  # >50 = avantage p1, <50 = avantage p2
        self.termine = False
        self.message = None

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id not in (self.p1["id"], self.p2["id"]):
            await interaction.response.send_message("⛔ Ce bras de fer ne te concerne pas !", ephemeral=True)
            return False
        return True

    def build_embed(self, message: str = None):
        embed = discord.Embed(title=f"💪 Bras de fer — {self.p1['name']} VS {self.p2['name']}", color=0x8E44AD)
        embed.description = message or "Les deux adversaires serrent les dents, la table tremble déjà..."
        embed.add_field(name=f"{self.p1['name']} ⬅️ ———— ➡️ {self.p2['name']}", value=barre(self.position), inline=False)
        embed.set_footer(text="🌊 One Piece Bot • Défis de taverne • Cliquez tous les deux sur Pousser !")
        return embed

    async def finir(self, interaction, gagnant, perdant, message):
        self.termine = True
        for c in self.children:
            c.disabled = True

        berrys_gain = random.randint(40, 90)
        pool = get_pool()
        async with pool.acquire() as conn:
            await conn.execute(
                "UPDATE players SET berrys = berrys + $3 WHERE guild_id=$1 AND user_id=$2",
                self.guild_id, gagnant["id"], berrys_gain
            )
        niveaux_g, niveau_g = await add_xp(self.guild_id, gagnant["id"], 30, 12)
        niveaux_p, niveau_p = await add_xp(self.guild_id, perdant["id"], 8, 3)

        message += f"\n\n🏆 **{gagnant['name']}** remporte le duel et empoche **{berrys_gain}฿** !"
        embed = self.build_embed(message)
        embed.color = 0x27AE60
        await self.message.edit(embed=embed, view=self)

        if niveaux_g > 0:
            gm = interaction.guild.get_member(gagnant["id"])
            if gm:
                await announce_level_up(interaction, gm, niveau_g)
        if niveaux_p > 0:
            pm = interaction.guild.get_member(perdant["id"])
            if pm:
                await announce_level_up(interaction, pm, niveau_p)

    @discord.ui.button(label="Pousser !", emoji="💪", style=discord.ButtonStyle.danger)
    async def pousser(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        if self.termine:
            return

        joueur = self.p1 if interaction.user.id == self.p1["id"] else self.p2
        adversaire = self.p2 if joueur is self.p1 else self.p1
        sens = 1 if joueur is self.p1 else -1

        avantage = (joueur["force"] - adversaire["force"]) // 4
        effort = random.randint(5, 15) + max(-8, min(8, avantage))
        self.position += sens * effort

        if self.position >= 100:
            self.position = 100
            await self.finir(interaction, self.p1, self.p2, f"**{self.p1['name']}** plaque le bras de **{self.p2['name']}** sur la table !")
            return
        if self.position <= 0:
            self.position = 0
            await self.finir(interaction, self.p2, self.p1, f"**{self.p2['name']}** plaque le bras de **{self.p1['name']}** sur la table !")
            return

        await self.message.edit(embed=self.build_embed(f"**{joueur['name']}** pousse de toutes ses forces !"), view=self)

    async def on_timeout(self):
        for c in self.children:
            c.disabled = True
        if self.message:
            try:
                await self.message.edit(view=self)
            except discord.HTTPException:
                pass


class BrasDeFerChallengeView(discord.ui.View):
    def __init__(self, guild_id, challenger_id, target_id):
        super().__init__(timeout=60)
        self.guild_id = guild_id
        self.challenger_id = challenger_id
        self.target_id = target_id
        self.repondu = False
        self.message = None

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.target_id:
            await interaction.response.send_message("⛔ Ce défi ne t'est pas adressé !", ephemeral=True)
            return False
        return True

    @discord.ui.button(label="Accepter", emoji="💪", style=discord.ButtonStyle.success)
    async def accepter(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.repondu:
            return
        self.repondu = True
        for c in self.children:
            c.disabled = True

        p1_data = await get_player(self.guild_id, self.challenger_id)
        p2_data = await get_player(self.guild_id, self.target_id)
        challenger_member = interaction.guild.get_member(self.challenger_id)
        target_member = interaction.guild.get_member(self.target_id)

        view = BrasDeFerPvPView(
            self.guild_id,
            self.challenger_id, challenger_member.display_name if challenger_member else "Joueur 1", p1_data["force"],
            self.target_id, target_member.display_name if target_member else "Joueur 2", p2_data["force"],
        )
        await interaction.response.edit_message(content=None, embed=view.build_embed(), view=view)
        view.message = await interaction.original_response()

    @discord.ui.button(label="Refuser", emoji="🚫", style=discord.ButtonStyle.danger)
    async def refuser(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.repondu:
            return
        self.repondu = True
        for c in self.children:
            c.disabled = True
        await interaction.response.edit_message(content="Le défi a été décliné.", embed=None, view=None)

    async def on_timeout(self):
        if self.repondu:
            return
        for c in self.children:
            c.disabled = True
        if self.message:
            try:
                await self.message.edit(content="⌛ Le défi a expiré.", view=self)
            except discord.HTTPException:
                pass


# ===== COMMANDES =====

@app_commands.command(name="bras_de_fer", description="Défier un PNJ de taverne en bras de fer")
@require_salon("salon_taverne")
async def bras_de_fer(interaction: discord.Interaction):
    await interaction.response.defer()
    player = await get_player(interaction.guild_id, interaction.user.id)
    if player is None:
        await interaction.followup.send("Tu n'as pas encore de personnage ! Lance `/commencer` pour débuter l'aventure 🏴‍☠️")
        return

    if player["endurance"] < COUT_ENDURANCE:
        await interaction.followup.send(f"😮‍💨 Il te faut {COUT_ENDURANCE} endurance pour ça (tu as {player['endurance']}).")
        return

    pool = get_pool()
    async with pool.acquire() as conn:
        await conn.execute(
            "UPDATE players SET endurance = endurance - $3 WHERE guild_id=$1 AND user_id=$2",
            interaction.guild_id, interaction.user.id, COUT_ENDURANCE
        )

    adversaire = random.choice(ADVERSAIRES_PVE)
    view = BrasDeFerPvEView(interaction.guild_id, interaction.user.id, adversaire, player["force"])
    embed = view.build_embed(f"**{adversaire['nom'].capitalize()}** te défie du regard et pose son coude sur la table !")
    msg = await interaction.followup.send(embed=embed, view=view)
    view.message = msg


@app_commands.command(name="bras_de_fer_duel", description="Défier un autre joueur en bras de fer")
@app_commands.describe(adversaire="Le joueur à défier")
@require_salon("salon_taverne")
async def bras_de_fer_duel(interaction: discord.Interaction, adversaire: discord.Member):
    await interaction.response.defer()
    if adversaire.id == interaction.user.id:
        await interaction.followup.send("Tu ne peux pas te défier toi-même 🙃")
        return
    if adversaire.bot:
        await interaction.followup.send("Tu ne peux pas défier un bot 🤖")
        return

    challenger_data = await get_player(interaction.guild_id, interaction.user.id)
    if challenger_data is None:
        await interaction.followup.send("Tu n'as pas encore de personnage ! Lance `/commencer` pour débuter l'aventure 🏴‍☠️")
        return
    target_data = await get_player(interaction.guild_id, adversaire.id)
    if target_data is None:
        await interaction.followup.send(f"{adversaire.display_name} n'a pas encore de personnage.")
        return

    embed = discord.Embed(
        title="💪 Défi de bras de fer !",
        description=f"{interaction.user.mention} défie {adversaire.mention} en bras de fer !",
        color=0x8E44AD
    )
    embed.set_footer(text="🌊 One Piece Bot • Défis de taverne • 60 secondes pour répondre")
    view = BrasDeFerChallengeView(interaction.guild_id, interaction.user.id, adversaire.id)
    msg = await interaction.followup.send(embed=embed, view=view)
    view.message = msg


def setup_bras_de_fer_commands(bot):
    bot.tree.add_command(bras_de_fer)
    bot.tree.add_command(bras_de_fer_duel)
