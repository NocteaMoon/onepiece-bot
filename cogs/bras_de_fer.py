import discord
from discord import app_commands
import random
from database.db import get_pool
from utils.players import get_player, add_xp
from utils.channel_check import require_salon
from utils.announcements import announce_level_up

COUT_ENDURANCE = 12

ADVERSAIRES = [
    {"nom": "un marin bedonnant bien éméché", "difficulte": 15, "berrys_min": 20, "berrys_max": 40, "xp": 15, "xpc": 6},
    {"nom": "un docker aux bras noueux", "difficulte": 35, "berrys_min": 35, "berrys_max": 65, "xp": 25, "xpc": 10},
    {"nom": "un ancien second de navire", "difficulte": 55, "berrys_min": 55, "berrys_max": 100, "xp": 40, "xpc": 16},
    {"nom": "le colosse de la taverne", "difficulte": 75, "berrys_min": 90, "berrys_max": 160, "xp": 60, "xpc": 24},
]

REACTIONS_BON_TIMING = [
    "Tu pousses au moment parfait !",
    "Un effort bien placé, tu gagnes du terrain !",
    "Ta prise est solide, tu avances !",
    "Tu sens l'adversaire vaciller !",
]

REACTIONS_MAUVAIS_TIMING = [
    "Tu pousses trop tôt, ton geste est mal engagé...",
    "Tu perds l'équilibre un instant...",
    "L'adversaire profite de ton geste précipité...",
    "Ta prise dérape légèrement...",
]

def barre(valeur, taille=10):
    valeur = max(0, min(100, valeur))
    rempli = round(valeur / 100 * taille)
    return "🟦" * rempli + "⬜" * (taille - rempli)


class BrasDeFerView(discord.ui.View):
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
            message = random.choice(REACTIONS_BON_TIMING)
        else:
            perte = random.randint(5, 12)
            self.position -= perte
            message = random.choice(REACTIONS_MAUVAIS_TIMING)

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

    adversaire = random.choice(ADVERSAIRES)
    view = BrasDeFerView(interaction.guild_id, interaction.user.id, adversaire, player["force"])
    embed = view.build_embed(f"**{adversaire['nom'].capitalize()}** te défie du regard et pose son coude sur la table !")
    msg = await interaction.followup.send(embed=embed, view=view)
    view.message = msg


def setup_bras_de_fer_commands(bot):
    bot.tree.add_command(bras_de_fer)
