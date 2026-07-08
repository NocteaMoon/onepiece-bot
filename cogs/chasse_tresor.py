import discord
from discord import app_commands
import random
from database.db import get_pool
from utils.players import get_player, add_xp
from utils.channel_check import require_salon
from utils.announcements import announce_level_up

COUT_ENDURANCE = 15
MISE_PARTICIPATION = 15
DUREE_INSCRIPTION = 30
NB_ETAPES = 4

ETAPES_NOMS = [
    "une jungle dense et humide",
    "une grotte scellée par une porte de pierre",
    "un pont suspendu instable au-dessus d'un ravin",
    "la chambre finale, où repose le trésor",
]


def barre_pot(pot, taille=10):
    plafond = 600
    rempli = min(taille, round(pot / plafond * taille))
    return "🟨" * rempli + "⬜" * (taille - rempli)


class ChasseTresorView(discord.ui.View):
    def __init__(self, guild_id, participants):
        super().__init__(timeout=90)
        self.guild_id = guild_id
        self.participants = participants
        self.etape = 0
        self.pot = 0
        self.termine = False
        self.message = None

    def ids(self):
        return [p["id"] for p in self.participants]

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id not in self.ids():
            await interaction.response.send_message("⛔ Tu ne participes pas à cette expédition !", ephemeral=True)
            return False
        return True

    def build_embed(self, message: str = None):
        embed = discord.Embed(title="🗺️ Chasse au trésor coopérative", color=0x8E44AD)
        if self.etape < NB_ETAPES:
            embed.description = message or f"Étape {self.etape + 1}/{NB_ETAPES} : vous atteignez **{ETAPES_NOMS[self.etape]}**. Quel chemin choisissez-vous ?"
        else:
            embed.description = message
        embed.add_field(name="Équipe", value=", ".join(p["name"] for p in self.participants), inline=False)
        embed.add_field(name=f"Butin accumulé — {self.pot:,}฿", value=barre_pot(self.pot), inline=False)
        embed.set_footer(text="🌊 One Piece Bot • Chasse au trésor • Le premier clic décide pour l'équipe")
        return embed

    async def resoudre_etape(self, interaction, risque: bool):
        nb = len(self.participants)
        if risque:
            if random.random() < 0.30:
                perte = round(self.pot * 0.5)
                self.pot -= perte
                await self.terminer(interaction, f"💥 Un piège se déclenche ! L'équipe perd **{perte:,}฿** et bat en retraite précipitamment...")
                return
            gain = random.randint(40, 70) * nb
            self.pot += gain
            message = f"🔥 Chemin risqué payant ! L'équipe récupère **{gain:,}฿** supplémentaires."
        else:
            gain = random.randint(15, 30) * nb
            self.pot += gain
            message = f"🟢 Chemin sûr emprunté, l'équipe récupère **{gain:,}฿**."

        self.etape += 1
        if self.etape >= NB_ETAPES:
            await self.terminer(interaction, message + "\n\n🏆 Le trésor est enfin à portée de main !")
            return

        await self.message.edit(embed=self.build_embed(message), view=self)

    async def terminer(self, interaction, message):
        self.termine = True
        for c in self.children:
            c.disabled = True

        pool = get_pool()
        part_chacun = self.pot // len(self.participants) if self.pot > 0 else 0
        async with pool.acquire() as conn:
            for p in self.participants:
                if part_chacun > 0:
                    await conn.execute(
                        "UPDATE players SET berrys = berrys + $3 WHERE guild_id=$1 AND user_id=$2",
                        self.guild_id, p["id"], part_chacun
                    )

        for p in self.participants:
            niveaux, niveau = await add_xp(self.guild_id, p["id"], 25, 10)
            if niveaux > 0:
                await announce_level_up(interaction, p["member"], niveau)

        if part_chacun > 0:
            message += f"\n\n💰 Chaque membre de l'équipe reçoit **{part_chacun:,}฿** !"
        else:
            message += "\n\nAucun butin à répartir cette fois..."

        embed = self.build_embed(message)
        embed.color = 0x27AE60 if part_chacun > 0 else 0xC0392B
        await self.message.edit(embed=embed, view=self)

    @discord.ui.button(label="Chemin sûr", emoji="🟢", style=discord.ButtonStyle.success)
    async def chemin_sur(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        if self.termine:
            return
        await self.resoudre_etape(interaction, risque=False)

    @discord.ui.button(label="Chemin risqué", emoji="🔴", style=discord.ButtonStyle.danger)
    async def chemin_risque(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        if self.termine:
            return
        await self.resoudre_etape(interaction, risque=True)

    async def on_timeout(self):
        for c in self.children:
            c.disabled = True
        if self.message:
            try:
                await self.message.edit(view=self)
            except discord.HTTPException:
                pass


class ChasseTresorInscriptionView(discord.ui.View):
    def __init__(self, guild_id, hote: discord.Member):
        super().__init__(timeout=DUREE_INSCRIPTION)
        self.guild_id = guild_id
        self.participants = {hote.id: hote}
        self.message = None
        self.lancee = False

    def build_embed(self):
        names = [m.mention for m in self.participants.values()]
        embed = discord.Embed(
            title="🗺️ Chasse au trésor — Formez votre équipe !",
            description=f"Rejoignez l'expédition avant le départ ! (2 à 4 aventuriers, {MISE_PARTICIPATION}฿ de mise chacun)",
            color=0x8E44AD
        )
        embed.add_field(name=f"Équipe ({len(names)}/4)", value="\n".join(names) or "Aucun", inline=False)
        embed.set_footer(text=f"🌊 One Piece Bot • Départ dans {DUREE_INSCRIPTION}s ou dès 4 inscrits")
        return embed

    @discord.ui.button(label="Rejoindre l'expédition", emoji="🗺️", style=discord.ButtonStyle.success)
    async def rejoindre(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.lancee:
            await interaction.response.send_message("L'expédition a déjà commencé !", ephemeral=True)
            return
        if interaction.user.id in self.participants:
            await interaction.response.send_message("Tu es déjà inscrit !", ephemeral=True)
            return
        if len(self.participants) >= 4:
            await interaction.response.send_message("L'équipe est déjà complète (4/4) !", ephemeral=True)
            return

        player = await get_player(self.guild_id, interaction.user.id)
        if player is None:
            await interaction.response.send_message("Tu n'as pas encore de personnage ! Lance `/commencer` d'abord.", ephemeral=True)
            return
        if player["berrys"] < MISE_PARTICIPATION:
            await interaction.response.send_message(f"⛔ Il te faut {MISE_PARTICIPATION}฿ pour participer.", ephemeral=True)
            return
        if player["endurance"] < COUT_ENDURANCE:
            await interaction.response.send_message(f"😮‍💨 Il te faut {COUT_ENDURANCE} endurance pour participer.", ephemeral=True)
            return

        self.participants[interaction.user.id] = interaction.user
        await interaction.response.edit_message(embed=self.build_embed(), view=self)

        if len(self.participants) >= 4:
            await self.lancer(interaction)

    async def _construire_participants(self):
        participants_data = []
        pool = get_pool()
        async with pool.acquire() as conn:
            for uid, member in self.participants.items():
                await conn.execute(
                    "UPDATE players SET endurance = endurance - $3, berrys = berrys - $4 WHERE guild_id=$1 AND user_id=$2",
                    self.guild_id, uid, COUT_ENDURANCE, MISE_PARTICIPATION
                )
                participants_data.append({"id": uid, "name": member.display_name, "member": member})
        return participants_data

    async def lancer(self, interaction):
        self.lancee = True
        for c in self.children:
            c.disabled = True
        participants_data = await self._construire_participants()
        view = ChasseTresorView(self.guild_id, participants_data)
        await interaction.response.edit_message(embed=view.build_embed(), view=view)
        view.message = await interaction.original_response()

    async def on_timeout(self):
        if self.lancee:
            return
        if len(self.participants) < 2:
            for c in self.children:
                c.disabled = True
            if self.message:
                try:
                    await self.message.edit(content="⌛ Pas assez d'aventuriers, l'expédition est annulée.", view=self)
                except discord.HTTPException:
                    pass
            return

        self.lancee = True
        for c in self.children:
            c.disabled = True
        participants_data = await self._construire_participants()
        view = ChasseTresorView(self.guild_id, participants_data)
        if self.message:
            try:
                await self.message.edit(embed=view.build_embed(), view=view)
                view.message = self.message
            except discord.HTTPException:
                pass


@app_commands.command(name="chasse_tresor", description="Organiser une chasse au trésor coopérative (2-4 joueurs)")
@require_salon("salon_tresor")
async def chasse_tresor(interaction: discord.Interaction):
    await interaction.response.defer()
    player = await get_player(interaction.guild_id, interaction.user.id)
    if player is None:
        await interaction.followup.send("Tu n'as pas encore de personnage ! Lance `/commencer` pour débuter l'aventure 🏴‍☠️")
        return
    if player["endurance"] < COUT_ENDURANCE:
        await interaction.followup.send(f"😮‍💨 Il te faut {COUT_ENDURANCE} endurance pour organiser une expédition.")
        return
    if player["berrys"] < MISE_PARTICIPATION:
        await interaction.followup.send(f"⛔ Il te faut au moins {MISE_PARTICIPATION}฿ pour organiser une expédition.")
        return

    view = ChasseTresorInscriptionView(interaction.guild_id, interaction.user)
    msg = await interaction.followup.send(embed=view.build_embed(), view=view)
    view.message = msg


def setup_chasse_tresor_commands(bot):
    bot.tree.add_command(chasse_tresor)
