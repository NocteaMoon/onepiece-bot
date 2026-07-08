import discord
from discord import app_commands
import random
from database.db import get_pool
from utils.players import get_player, add_xp
from utils.channel_check import require_salon
from utils.announcements import announce_level_up

COUT_ENDURANCE = 15
RISQUE_BASE = 8
RISQUE_INCREMENT = 9
RISQUE_MAX = 85

PLATS_FLAVORS = [
    "un ragoût fumant", "une pile de brochettes grillées", "un plat de riz épicé",
    "une montagne de fruits de mer", "un pain de viande copieux", "une soupe corsée",
    "un assortiment de beignets", "un poisson entier grillé", "une tourte bien garnie",
    "une platée de nouilles sautées", "un rôti fumant", "une tarte salée généreuse",
]


def barre(risque, taille=10):
    rempli = round(risque / 100 * taille)
    return "🟥" * rempli + "⬜" * (taille - rempli)


class ConcoursView(discord.ui.View):
    def __init__(self, guild_id, user_id):
        super().__init__(timeout=45)
        self.guild_id = guild_id
        self.user_id = user_id
        self.plats_manges = 0
        self.cagnotte = 0
        self.termine = False
        self.message = None

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("⛔ Ce n'est pas ton concours !", ephemeral=True)
            return False
        return True

    def risque_actuel(self):
        return min(RISQUE_MAX, RISQUE_BASE + self.plats_manges * RISQUE_INCREMENT)

    def build_embed(self, message: str = None):
        embed = discord.Embed(title="🍖 Concours de nourriture", color=0xF4C430)
        embed.description = message or "Le défi commence, la table est chargée de victuailles !"
        embed.add_field(name="Plats engloutis", value=str(self.plats_manges), inline=True)
        embed.add_field(name="Cagnotte actuelle", value=f"{self.cagnotte:,}฿", inline=True)
        embed.add_field(name=f"Risque du prochain plat — {self.risque_actuel()}%", value=barre(self.risque_actuel()), inline=False)
        embed.set_footer(text="🌊 One Piece Bot • Défis de taverne")
        return embed

    async def finir(self, victoire: bool, message: str):
        self.termine = True
        for c in self.children:
            c.disabled = True

        niveaux_gagnes = 0
        nouveau_niveau = None
        if victoire and self.cagnotte > 0:
            pool = get_pool()
            async with pool.acquire() as conn:
                await conn.execute(
                    "UPDATE players SET berrys = berrys + $3 WHERE guild_id=$1 AND user_id=$2",
                    self.guild_id, self.user_id, self.cagnotte
                )
            xp = self.plats_manges * random.randint(5, 9)
            xpc = self.plats_manges * random.randint(2, 4)
            niveaux_gagnes, nouveau_niveau = await add_xp(self.guild_id, self.user_id, xp, xpc)
            message += f"\n\n🏆 Tu empoches **{self.cagnotte:,} Berrys** !"

        embed = self.build_embed(message)
        embed.color = 0x27AE60 if victoire else 0xC0392B
        await self.message.edit(embed=embed, view=self)
        return niveaux_gagnes, nouveau_niveau

    @discord.ui.button(label="Continuer à manger", emoji="🍖", style=discord.ButtonStyle.danger)
    async def continuer(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        if self.termine:
            return

        risque = self.risque_actuel()
        plat = random.choice(PLATS_FLAVORS)

        if random.randint(1, 100) <= risque:
            niveaux_gagnes, nouveau_niveau = await self.finir(
                False, f"💥 En attaquant {plat}, ton estomac ne suit plus... tu abandonnes le concours, cagnotte perdue !"
            )
            return

        gain_plat = random.randint(15 + self.plats_manges * 3, 30 + self.plats_manges * 3)
        self.cagnotte += gain_plat
        self.plats_manges += 1

        await interaction.edit_original_response(
            embed=self.build_embed(f"Tu engloutis {plat} sans broncher ! (+{gain_plat}฿ potentiels)"),
            view=self
        )

    @discord.ui.button(label="S'arrêter", emoji="✋", style=discord.ButtonStyle.secondary)
    async def arreter(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        if self.termine:
            return
        if self.plats_manges == 0:
            niveaux_gagnes, nouveau_niveau = await self.finir(False, "Tu te retires avant même d'avoir commencé... aucun gain, mais l'honneur est sauf.")
        else:
            niveaux_gagnes, nouveau_niveau = await self.finir(True, f"Tu reposes ta fourchette après **{self.plats_manges} plats**, sagement !")

        if niveaux_gagnes and niveaux_gagnes > 0:
            await announce_level_up(interaction, interaction.user, nouveau_niveau)

    async def on_timeout(self):
        for c in self.children:
            c.disabled = True
        if self.message:
            try:
                await self.message.edit(view=self)
            except discord.HTTPException:
                pass


@app_commands.command(name="concours_nourriture", description="Participer à un concours de nourriture (push your luck)")
@require_salon("salon_taverne")
async def concours_nourriture(interaction: discord.Interaction):
    await interaction.response.defer()
    player = await get_player(interaction.guild_id, interaction.user.id)
    if player is None:
        await interaction.followup.send("Tu n'as pas encore de personnage ! Lance `/commencer` pour débuter l'aventure 🏴‍☠️")
        return

    if player["endurance"] < COUT_ENDURANCE:
        await interaction.followup.send(f"😮‍💨 Il te faut {COUT_ENDURANCE} endurance pour participer (tu as {player['endurance']}).")
        return

    pool = get_pool()
    async with pool.acquire() as conn:
        await conn.execute(
            "UPDATE players SET endurance = endurance - $3 WHERE guild_id=$1 AND user_id=$2",
            interaction.guild_id, interaction.user.id, COUT_ENDURANCE
        )

    view = ConcoursView(interaction.guild_id, interaction.user.id)
    msg = await interaction.followup.send(embed=view.build_embed(), view=view)
    view.message = msg


def setup_concours_nourriture_commands(bot):
    bot.tree.add_command(concours_nourriture)
