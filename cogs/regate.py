import discord
from discord import app_commands
import random
import asyncio
from database.db import get_pool
from utils.players import get_player, add_xp
from utils.channel_check import require_salon
from utils.announcements import announce_level_up

COUT_ENDURANCE = 15
DISTANCE_COURSE = 100
DUREE_INSCRIPTION = 30
MISE_PARTICIPATION = 20

BATEAUX_EMOJIS = ["🛶", "⛵", "🚤", "🛥️"]


def piste(position, distance=DISTANCE_COURSE, taille=15, bateau="🛶"):
    position = max(0, min(distance, position))
    progression = round(position / distance * taille)
    return "🌊" * progression + bateau + "〰️" * (taille - progression) + "🏁"


class RegateCourseView(discord.ui.View):
    def __init__(self, guild_id, participants):
        super().__init__(timeout=90)
        self.guild_id = guild_id
        self.participants = participants  # liste de dicts: id, name, position, force
        self.termine = False
        self.message = None
        for i, p in enumerate(self.participants):
            p["bateau"] = BATEAUX_EMOJIS[i % len(BATEAUX_EMOJIS)]

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id not in [p["id"] for p in self.participants]:
            await interaction.response.send_message("⛔ Tu ne participes pas à cette régate !", ephemeral=True)
            return False
        return True

    def build_embed(self, message: str = None):
        embed = discord.Embed(title="🚣 Régate en cours !", color=0x1B3A5C)
        embed.description = message or "Ramez de toutes vos forces jusqu'à la ligne d'arrivée !"
        for p in self.participants:
            embed.add_field(
                name=f"{p['bateau']} {p['name']} — {p['position']}/{DISTANCE_COURSE}m",
                value=piste(p["position"], bateau=p["bateau"]),
                inline=False
            )
        embed.set_footer(text=f"🌊 One Piece Bot • Régate • {MISE_PARTICIPATION}฿ mis en jeu par participant")
        return embed

    async def finir(self, interaction, gagnant):
        self.termine = True
        for c in self.children:
            c.disabled = True

        cagnotte = MISE_PARTICIPATION * len(self.participants)
        pool = get_pool()
        async with pool.acquire() as conn:
            await conn.execute(
                "UPDATE players SET berrys = berrys + $3 WHERE guild_id=$1 AND user_id=$2",
                self.guild_id, gagnant["id"], cagnotte
            )

        for p in self.participants:
            if p["id"] == gagnant["id"]:
                niveaux, niveau = await add_xp(self.guild_id, p["id"], 40, 16)
            else:
                niveaux, niveau = await add_xp(self.guild_id, p["id"], 12, 5)
            if niveaux > 0:
                member = interaction.guild.get_member(p["id"])
                if member:
                    await announce_level_up(interaction, member, niveau)

        embed = self.build_embed(f"🏆 **{gagnant['name']}** franchit la ligne d'arrivée en tête et remporte **{cagnotte:,}฿** !")
        embed.color = 0x27AE60
        await self.message.edit(embed=embed, view=self)

    @discord.ui.button(label="Ramer !", emoji="🚣", style=discord.ButtonStyle.primary)
    async def ramer(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        if self.termine:
            return

        joueur = next(p for p in self.participants if p["id"] == interaction.user.id)
        avance = random.randint(4, 9) + (joueur["force"] // 15)
        joueur["position"] += avance

        if joueur["position"] >= DISTANCE_COURSE:
            joueur["position"] = DISTANCE_COURSE
            await self.finir(interaction, joueur)
            return

        await self.message.edit(embed=self.build_embed(), view=self)

    async def on_timeout(self):
        for c in self.children:
            c.disabled = True
        if self.message:
            try:
                await self.message.edit(view=self)
            except discord.HTTPException:
                pass


class RegateInscriptionView(discord.ui.View):
    def __init__(self, guild_id, hote_id):
        super().__init__(timeout=DUREE_INSCRIPTION)
        self.guild_id = guild_id
        self.participants_ids = [hote_id]
        self.message = None
        self.lancee = False

    def build_embed(self, participants_names):
        embed = discord.Embed(
            title="🚣 Régate — Inscriptions ouvertes !",
            description=f"Rejoins la course avant qu'elle ne démarre ! (2 à 4 participants, {MISE_PARTICIPATION}฿ de mise chacun)",
            color=0x1B3A5C
        )
        embed.add_field(name=f"Participants ({len(participants_names)}/4)", value="\n".join(participants_names) or "Aucun", inline=False)
        embed.set_footer(text=f"🌊 One Piece Bot • Départ dans {DUREE_INSCRIPTION}s ou dès 4 inscrits")
        return embed

    @discord.ui.button(label="Rejoindre la régate", emoji="🚣", style=discord.ButtonStyle.success)
    async def rejoindre(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.lancee:
            await interaction.response.send_message("La course a déjà commencé !", ephemeral=True)
            return
        if interaction.user.id in self.participants_ids:
            await interaction.response.send_message("Tu es déjà inscrit !", ephemeral=True)
            return
        if len(self.participants_ids) >= 4:
            await interaction.response.send_message("La régate est déjà complète (4/4) !", ephemeral=True)
            return

        player = await get_player(self.guild_id, interaction.user.id)
        if player is None:
            await interaction.response.send_message("Tu n'as pas encore de personnage ! Lance `/commencer` d'abord.", ephemeral=True)
            return
        if player["berrys"] < MISE_PARTICIPATION:
            await interaction.response.send_message(f"⛔ Il te faut {MISE_PARTICIPATION}฿ pour participer.", ephemeral=True)
            return

        self.participants_ids.append(interaction.user.id)
        names = [f"<@{uid}>" for uid in self.participants_ids]
        await interaction.response.edit_message(embed=self.build_embed(names), view=self)

        if len(self.participants_ids) >= 4:
            await self.lancer_course(interaction)

    async def lancer_course(self, interaction):
        self.lancee = True
        for c in self.children:
            c.disabled = True

        participants = []
        pool = get_pool()
        async with pool.acquire() as conn:
            for uid in self.participants_ids:
                p_data = await get_player(self.guild_id, uid)
                await conn.execute(
                    "UPDATE players SET endurance = endurance - $3, berrys = berrys - $4 WHERE guild_id=$1 AND user_id=$2",
                    self.guild_id, uid, COUT_ENDURANCE, MISE_PARTICIPATION
                )
                member = interaction.guild.get_member(uid)
                participants.append({
                    "id": uid, "name": member.display_name if member else "Joueur",
                    "position": 0, "force": p_data["force"]
                })

        course_view = RegateCourseView(self.guild_id, participants)
        embed = course_view.build_embed("🏁 Top départ ! Que la meilleure équipe l'emporte !")
        await interaction.edit_original_response(embed=embed, view=course_view)
        course_view.message = await interaction.original_response()

    async def on_timeout(self):
        if self.lancee:
            return
        if len(self.participants_ids) < 2:
            for c in self.children:
                c.disabled = True
            if self.message:
                try:
                    await self.message.edit(content="⌛ Pas assez de participants, la régate est annulée.", view=self)
                except discord.HTTPException:
                    pass
            return

        # Lance avec les participants actuels (2 ou 3)
        fake_interaction = None
        self.lancee = True
        for c in self.children:
            c.disabled = True

        participants = []
        pool = get_pool()
        async with pool.acquire() as conn:
            for uid in self.participants_ids:
                p_data = await get_player(self.guild_id, uid)
                await conn.execute(
                    "UPDATE players SET endurance = endurance - $3, berrys = berrys - $4 WHERE guild_id=$1 AND user_id=$2",
                    self.guild_id, uid, COUT_ENDURANCE, MISE_PARTICIPATION
                )
                guild = self.message.guild if self.message else None
                member = guild.get_member(uid) if guild else None
                participants.append({
                    "id": uid, "name": member.display_name if member else "Joueur",
                    "position": 0, "force": p_data["force"]
                })

        course_view = RegateCourseView(self.guild_id, participants)
        embed = course_view.build_embed("🏁 Le temps d'inscription est écoulé, top départ !")
        if self.message:
            try:
                await self.message.edit(embed=embed, view=course_view)
                course_view.message = self.message
            except discord.HTTPException:
                pass


@app_commands.command(name="regate", description="Organiser une régate à 2-4 joueurs")
@require_salon("salon_regates")
async def regate(interaction: discord.Interaction):
    await interaction.response.defer()
    player = await get_player(interaction.guild_id, interaction.user.id)
    if player is None:
        await interaction.followup.send("Tu n'as pas encore de personnage ! Lance `/commencer` pour débuter l'aventure 🏴‍☠️")
        return
    if player["endurance"] < COUT_ENDURANCE:
        await interaction.followup.send(f"😮‍💨 Il te faut {COUT_ENDURANCE} endurance pour participer (tu as {player['endurance']}).")
        return
    if player["berrys"] < MISE_PARTICIPATION:
        await interaction.followup.send(f"⛔ Il te faut au moins {MISE_PARTICIPATION}฿ pour organiser une régate.")
        return

    view = RegateInscriptionView(interaction.guild_id, interaction.user.id)
    embed = view.build_embed([interaction.user.mention])
    msg = await interaction.followup.send(embed=embed, view=view)
    view.message = msg


def setup_regate_commands(bot):
    bot.tree.add_command(regate)
