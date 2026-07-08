import discord
from discord import app_commands
import random
from database.db import get_pool
from utils.players import get_player, add_xp
from utils.combat_stats import get_effective_stats
from utils.channel_check import require_salon
from utils.announcements import announce_level_up
from data.ennemis import ENNEMIS

COUT_ENDURANCE = 25
DUREE_INSCRIPTION = 30
TOURS_MAX = 20


def barre(valeur, max_valeur, taille=12, plein="🟥", vide="⬜"):
    valeur = max(0, min(max_valeur, valeur))
    rempli = round(valeur / max_valeur * taille) if max_valeur > 0 else 0
    return plein * rempli + vide * (taille - rempli)


class RaidBossView(discord.ui.View):
    def __init__(self, guild_id, participants, boss_nom, boss_pv):
        super().__init__(timeout=120)
        self.guild_id = guild_id
        self.participants = participants
        self.boss_nom = boss_nom
        self.boss_pv = boss_pv
        self.boss_pv_max = boss_pv
        self.tours_restants = TOURS_MAX
        self.contributions = {p["id"]: 0 for p in participants}
        self.termine = False
        self.message = None
        self.log = []

    def ids(self):
        return [p["id"] for p in self.participants]

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id not in self.ids():
            await interaction.response.send_message("⛔ Tu ne participes pas à ce raid !", ephemeral=True)
            return False
        return True

    def build_embed(self, message: str = None):
        embed = discord.Embed(title=f"👑 RAID — {self.boss_nom.capitalize()}", color=0xC0392B)
        embed.description = message or "L'équipe se rassemble face au colosse !"
        embed.add_field(
            name=f"PV du boss — {max(0, self.boss_pv)}/{self.boss_pv_max}",
            value=barre(self.boss_pv, self.boss_pv_max), inline=False
        )
        embed.add_field(name="Équipe", value=", ".join(p["name"] for p in self.participants), inline=False)
        if self.log:
            embed.add_field(name="Journal", value="\n".join(self.log[-4:]), inline=False)
        embed.set_footer(text=f"🌊 One Piece Bot • Raid • Tours restants : {self.tours_restants}")
        return embed

    async def victoire(self, interaction):
        self.termine = True
        for c in self.children:
            c.disabled = True

        cagnotte_totale = len(self.participants) * random.randint(120, 200)
        mvp_id = max(self.contributions, key=self.contributions.get)
        pool = get_pool()
        part = cagnotte_totale // len(self.participants)
        async with pool.acquire() as conn:
            for p in self.participants:
                await conn.execute(
                    "UPDATE players SET berrys = berrys + $3, prime = prime + $4 WHERE guild_id=$1 AND user_id=$2",
                    self.guild_id, p["id"], part, 40
                )

        for p in self.participants:
            xp = 60 if p["id"] == mvp_id else 45
            niveaux, niveau = await add_xp(self.guild_id, p["id"], xp, xp // 2)
            if niveaux > 0:
                await announce_level_up(interaction, p["member"], niveau)

        mvp_name = next(p["name"] for p in self.participants if p["id"] == mvp_id)
        embed = self.build_embed(
            f"🏆 **Le {self.boss_nom} est vaincu !** L'équipe se partage la récompense.\n👑 MVP du raid : **{mvp_name}**"
        )
        embed.color = 0x27AE60
        await self.message.edit(embed=embed, view=self)

    async def echec(self):
        self.termine = True
        for c in self.children:
            c.disabled = True
        embed = self.build_embed(f"⏱️ Le temps est écoulé... **{self.boss_nom.capitalize()}** prend la fuite, aucune récompense cette fois.")
        embed.color = 0x7F0000
        await self.message.edit(embed=embed, view=self)

    @discord.ui.button(label="Attaquer !", emoji="⚔️", style=discord.ButtonStyle.danger)
    async def attaquer(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        if self.termine:
            return

        joueur = next(p for p in self.participants if p["id"] == interaction.user.id)
        degats = max(1, round(joueur["eff"]["force"] * random.uniform(0.85, 1.2)))
        self.boss_pv -= degats
        self.contributions[joueur["id"]] += degats
        self.tours_restants -= 1
        self.log.append(f"**{joueur['name']}** frappe pour **{degats}** dégâts !")

        if self.boss_pv <= 0:
            await self.victoire(interaction)
            return
        if self.tours_restants <= 0:
            await self.echec()
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


class RaidInscriptionView(discord.ui.View):
    def __init__(self, guild_id, hote: discord.Member, mer_hote):
        super().__init__(timeout=DUREE_INSCRIPTION)
        self.guild_id = guild_id
        self.participants = {hote.id: hote}
        self.mer = mer_hote
        self.message = None
        self.lancee = False

    def build_embed(self):
        names = [m.mention for m in self.participants.values()]
        embed = discord.Embed(
            title="👑 Raid de boss — Rassemblez votre équipe !",
            description=f"Un boss redoutable rôde sur **{self.mer}**. Rejoignez le raid avant le départ ! (2 à 4 joueurs)",
            color=0xC0392B
        )
        embed.add_field(name=f"Équipe ({len(names)}/4)", value="\n".join(names) or "Aucun", inline=False)
        embed.set_footer(text=f"🌊 One Piece Bot • Départ dans {DUREE_INSCRIPTION}s ou dès 4 inscrits")
        return embed

    @discord.ui.button(label="Rejoindre le raid", emoji="👑", style=discord.ButtonStyle.danger)
    async def rejoindre(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.lancee:
            await interaction.response.send_message("Le raid a déjà commencé !", ephemeral=True)
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
        if player["mer"] != self.mer:
            await interaction.response.send_message(f"⛔ Tu dois être sur **{self.mer}** pour rejoindre ce raid.", ephemeral=True)
            return
        if player["endurance"] < COUT_ENDURANCE:
            await interaction.response.send_message(f"😮‍💨 Il te faut {COUT_ENDURANCE} endurance pour participer.", ephemeral=True)
            return

        self.participants[interaction.user.id] = interaction.user
        await interaction.response.edit_message(embed=self.build_embed(), view=self)

        if len(self.participants) >= 4:
            await self.lancer(interaction)

    async def _construire(self):
        pool_ennemis = [e for e in ENNEMIS if e["mer"] == self.mer]
        boss_template = max(pool_ennemis, key=lambda e: e["pv"])
        nb = len(self.participants)
        boss_pv = round(boss_template["pv"] * (1.3 + 0.5 * nb))

        participants_data = []
        pool = get_pool()
        async with pool.acquire() as conn:
            for uid, member in self.participants.items():
                p_data = await get_player(self.guild_id, uid)
                eff = await get_effective_stats(self.guild_id, uid, p_data)
                await conn.execute(
                    "UPDATE players SET endurance = endurance - $3 WHERE guild_id=$1 AND user_id=$2",
                    self.guild_id, uid, COUT_ENDURANCE
                )
                participants_data.append({"id": uid, "name": member.display_name, "member": member, "eff": eff})
        return participants_data, boss_template["nom"], boss_pv

    async def lancer(self, interaction):
        self.lancee = True
        for c in self.children:
            c.disabled = True
        participants_data, boss_nom, boss_pv = await self._construire()
        view = RaidBossView(self.guild_id, participants_data, boss_nom, boss_pv)
        embed = view.build_embed(f"👑 **{boss_nom.capitalize()}** légendaire se dresse devant l'équipe !")
        await interaction.response.edit_message(embed=embed, view=view)
        view.message = await interaction.original_response()

    async def on_timeout(self):
        if self.lancee:
            return
        if len(self.participants) < 2:
            for c in self.children:
                c.disabled = True
            if self.message:
                try:
                    await self.message.edit(content="⌛ Pas assez de joueurs, le raid est annulé.", view=self)
                except discord.HTTPException:
                    pass
            return

        self.lancee = True
        for c in self.children:
            c.disabled = True
        participants_data, boss_nom, boss_pv = await self._construire()
        view = RaidBossView(self.guild_id, participants_data, boss_nom, boss_pv)
        embed = view.build_embed(f"👑 **{boss_nom.capitalize()}** légendaire se dresse devant l'équipe !")
        if self.message:
            try:
                await self.message.edit(embed=embed, view=view)
                view.message = self.message
            except discord.HTTPException:
                pass


@app_commands.command(name="raid_boss", description="Organiser un raid coopératif contre un boss (2-4 joueurs)")
@require_salon("salon_combat")
async def raid_boss(interaction: discord.Interaction):
    await interaction.response.defer()
    player = await get_player(interaction.guild_id, interaction.user.id)
    if player is None:
        await interaction.followup.send("Tu n'as pas encore de personnage ! Lance `/commencer` pour débuter l'aventure 🏴‍☠️")
        return
    if player["endurance"] < COUT_ENDURANCE:
        await interaction.followup.send(f"😮‍💨 Il te faut {COUT_ENDURANCE} endurance pour organiser un raid.")
        return

    pool_ennemis = [e for e in ENNEMIS if e["mer"] == player["mer"]]
    if not pool_ennemis:
        await interaction.followup.send(f"Aucun boss connu sur **{player['mer']}** pour le moment.")
        return

    view = RaidInscriptionView(interaction.guild_id, interaction.user, player["mer"])
    msg = await interaction.followup.send(embed=view.build_embed(), view=view)
    view.message = msg


def setup_raid_boss_commands(bot):
    bot.tree.add_command(raid_boss)
