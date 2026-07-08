import discord
from discord import app_commands
import random
from database.db import get_pool
from utils.players import get_player, add_xp
from utils.combat_stats import get_effective_stats
from utils.channel_check import require_salon
from utils.announcements import announce_level_up


def barre(valeur, max_valeur, taille=10, plein="🟩", vide="⬜"):
    valeur = max(0, min(max_valeur, valeur))
    rempli = round(valeur / max_valeur * taille) if max_valeur > 0 else 0
    return plein * rempli + vide * (taille - rempli)


class DuelCombatView(discord.ui.View):
    def __init__(self, guild_id, p1, p2, eff1, eff2, mise):
        super().__init__(timeout=120)
        self.guild_id = guild_id
        self.p1 = p1
        self.p2 = p2
        self.eff = {p1["id"]: eff1, p2["id"]: eff2}
        self.mise = mise
        self.current_turn_id = random.choice([p1["id"], p2["id"]])
        self.termine = False
        self.message = None
        self.log = []

    def joueur(self, uid):
        return self.p1 if uid == self.p1["id"] else self.p2

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id not in (self.p1["id"], self.p2["id"]):
            await interaction.response.send_message("⛔ Ce duel ne te concerne pas !", ephemeral=True)
            return False
        if interaction.user.id != self.current_turn_id:
            await interaction.response.send_message("⌛ Ce n'est pas ton tour !", ephemeral=True)
            return False
        return True

    def build_embed(self):
        embed = discord.Embed(title=f"⚔️ Duel — {self.p1['name']} VS {self.p2['name']}", color=0x8E44AD)
        if self.mise:
            embed.description = f"💰 Mise : **{self.mise:,}฿** pour le vainqueur"
        embed.add_field(
            name=f"{self.p1['name']} — {max(0, self.p1['pv'])}/{self.p1['pv_max']} PV",
            value=barre(self.p1["pv"], self.p1["pv_max"]), inline=False
        )
        embed.add_field(
            name=f"{self.p2['name']} — {max(0, self.p2['pv'])}/{self.p2['pv_max']} PV",
            value=barre(self.p2["pv"], self.p2["pv_max"]), inline=False
        )
        if self.log:
            embed.add_field(name="Journal", value="\n".join(self.log[-4:]), inline=False)
        tour_joueur = self.joueur(self.current_turn_id)
        embed.set_footer(text=f"🌊 One Piece Bot • Duel • Au tour de {tour_joueur['name']}")
        return embed

    async def terminer(self, interaction, gagnant_id, perdant_id, message):
        self.termine = True
        for c in self.children:
            c.disabled = True

        gagnant = self.joueur(gagnant_id)
        perdant = self.joueur(perdant_id)

        pool = get_pool()
        transfert = 0
        async with pool.acquire() as conn:
            if self.mise:
                perdant_row = await conn.fetchrow("SELECT berrys FROM players WHERE guild_id=$1 AND user_id=$2", self.guild_id, perdant_id)
                transfert = min(self.mise, perdant_row["berrys"])
                if transfert > 0:
                    await conn.execute("UPDATE players SET berrys = berrys - $3 WHERE guild_id=$1 AND user_id=$2", self.guild_id, perdant_id, transfert)
                    await conn.execute("UPDATE players SET berrys = berrys + $3 WHERE guild_id=$1 AND user_id=$2", self.guild_id, gagnant_id, transfert)

        niveaux_g, niveau_g = await add_xp(self.guild_id, gagnant_id, 35, 15)
        niveaux_p, niveau_p = await add_xp(self.guild_id, perdant_id, 10, 4)

        recap = f"🏆 **{gagnant['name']}** remporte le duel !"
        if transfert:
            recap += f" (+{transfert:,}฿)"
        self.log.append(message)
        self.log.append(recap)

        embed = self.build_embed()
        embed.color = 0x27AE60
        await self.message.edit(embed=embed, view=self)

        if niveaux_g > 0:
            gagnant_member = interaction.guild.get_member(gagnant_id)
            if gagnant_member:
                await announce_level_up(interaction, gagnant_member, niveau_g)
        if niveaux_p > 0:
            perdant_member = interaction.guild.get_member(perdant_id)
            if perdant_member:
                await announce_level_up(interaction, perdant_member, niveau_p)

    @discord.ui.button(label="Attaque", emoji="⚔️", style=discord.ButtonStyle.danger)
    async def attaque(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        if self.termine:
            return
        attaquant_id = self.current_turn_id
        defenseur_id = self.p2["id"] if attaquant_id == self.p1["id"] else self.p1["id"]
        attaquant = self.joueur(attaquant_id)
        defenseur = self.joueur(defenseur_id)
        eff_att = self.eff[attaquant_id]
        eff_def = self.eff[defenseur_id]

        attaquant["defense_active"] = False
        degats = max(1, round(eff_att["force"] * random.uniform(0.85, 1.15) - eff_def["defense"] * 0.5))
        if defenseur.get("defense_active"):
            degats = max(1, round(degats * 0.5))
            defenseur["defense_active"] = False

        defenseur["pv"] -= degats
        self.log.append(f"**{attaquant['name']}** attaque et inflige **{degats}** dégâts à **{defenseur['name']}** !")

        if defenseur["pv"] <= 0:
            await self.terminer(interaction, attaquant_id, defenseur_id, f"**{defenseur['name']}** s'effondre !")
            return

        self.current_turn_id = defenseur_id
        await self.message.edit(embed=self.build_embed(), view=self)

    @discord.ui.button(label="Défense", emoji="🛡️", style=discord.ButtonStyle.primary)
    async def defense(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        if self.termine:
            return
        joueur_id = self.current_turn_id
        joueur = self.joueur(joueur_id)
        joueur["defense_active"] = True
        self.log.append(f"**{joueur['name']}** se met en garde, prêt(e) à encaisser la prochaine attaque.")
        self.current_turn_id = self.p2["id"] if joueur_id == self.p1["id"] else self.p1["id"]
        await self.message.edit(embed=self.build_embed(), view=self)

    @discord.ui.button(label="Abandonner", emoji="🏳️", style=discord.ButtonStyle.secondary)
    async def abandon(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        if self.termine:
            return
        abandonneur_id = self.current_turn_id
        gagnant_id = self.p2["id"] if abandonneur_id == self.p1["id"] else self.p1["id"]
        abandonneur = self.joueur(abandonneur_id)
        await self.terminer(interaction, gagnant_id, abandonneur_id, f"**{abandonneur['name']}** abandonne le duel !")

    async def on_timeout(self):
        for c in self.children:
            c.disabled = True
        if self.message:
            try:
                await self.message.edit(view=self)
            except discord.HTTPException:
                pass


class DuelChallengeView(discord.ui.View):
    def __init__(self, guild_id, challenger_id, target_id, mise):
        super().__init__(timeout=60)
        self.guild_id = guild_id
        self.challenger_id = challenger_id
        self.target_id = target_id
        self.mise = mise
        self.repondu = False
        self.message = None

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.target_id:
            await interaction.response.send_message("⛔ Ce défi ne t'est pas adressé !", ephemeral=True)
            return False
        return True

    @discord.ui.button(label="Accepter", emoji="⚔️", style=discord.ButtonStyle.success)
    async def accepter(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.repondu:
            return
        self.repondu = True
        for c in self.children:
            c.disabled = True

        p1_data = await get_player(self.guild_id, self.challenger_id)
        p2_data = await get_player(self.guild_id, self.target_id)

        if self.mise:
            if p1_data["berrys"] < self.mise:
                await interaction.response.edit_message(content="⛔ Le défieur n'a plus assez de Berrys, le duel est annulé.", embed=None, view=None)
                return
            if p2_data["berrys"] < self.mise:
                await interaction.response.edit_message(content="⛔ Tu n'as pas assez de Berrys pour cette mise, le duel est annulé.", embed=None, view=None)
                return

        eff1 = await get_effective_stats(self.guild_id, self.challenger_id, p1_data)
        eff2 = await get_effective_stats(self.guild_id, self.target_id, p2_data)

        challenger_member = interaction.guild.get_member(self.challenger_id)
        target_member = interaction.guild.get_member(self.target_id)

        p1 = {"id": self.challenger_id, "name": challenger_member.display_name if challenger_member else "Joueur 1",
              "pv": p1_data["pv_max"] + eff1["bonus_pv_combat"], "pv_max": p1_data["pv_max"] + eff1["bonus_pv_combat"],
              "defense_active": False}
        p2 = {"id": self.target_id, "name": target_member.display_name if target_member else "Joueur 2",
              "pv": p2_data["pv_max"] + eff2["bonus_pv_combat"], "pv_max": p2_data["pv_max"] + eff2["bonus_pv_combat"],
              "defense_active": False}

        duel_view = DuelCombatView(self.guild_id, p1, p2, eff1, eff2, self.mise)
        embed = duel_view.build_embed()
        embed.description = (embed.description + "\n\n" if embed.description else "") + "⚔️ Le duel commence !"
        await interaction.response.edit_message(content=None, embed=embed, view=duel_view)
        duel_view.message = await interaction.original_response()

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


@app_commands.command(name="duel", description="Défier un autre joueur en duel")
@app_commands.describe(adversaire="Le joueur à défier", mise="Mise en Berrys (optionnelle)")
@require_salon("salon_duel")
async def duel(interaction: discord.Interaction, adversaire: discord.Member, mise: int = 0):
    await interaction.response.defer()
    if adversaire.id == interaction.user.id:
        await interaction.followup.send("Tu ne peux pas te défier toi-même 🙃")
        return
    if adversaire.bot:
        await interaction.followup.send("Tu ne peux pas défier un bot 🤖")
        return
    if mise < 0:
        await interaction.followup.send("La mise ne peut pas être négative 🙃")
        return

    challenger_data = await get_player(interaction.guild_id, interaction.user.id)
    if challenger_data is None:
        await interaction.followup.send("Tu n'as pas encore de personnage ! Lance `/commencer` pour débuter l'aventure 🏴‍☠️")
        return
    target_data = await get_player(interaction.guild_id, adversaire.id)
    if target_data is None:
        await interaction.followup.send(f"{adversaire.display_name} n'a pas encore de personnage.")
        return

    if mise > 0 and challenger_data["berrys"] < mise:
        await interaction.followup.send(f"Tu n'as que **{challenger_data['berrys']:,}฿**, tu ne peux pas miser **{mise:,}฿**.")
        return

    embed = discord.Embed(
        title="⚔️ Défi en duel !",
        description=f"{interaction.user.mention} défie {adversaire.mention} en duel !" + (f"\n💰 Mise proposée : **{mise:,}฿**" if mise else ""),
        color=0x8E44AD
    )
    embed.set_footer(text="🌊 One Piece Bot • Duel • 60 secondes pour répondre")
    view = DuelChallengeView(interaction.guild_id, interaction.user.id, adversaire.id, mise)
    msg = await interaction.followup.send(embed=embed, view=view)
    view.message = msg


def setup_duel_commands(bot):
    bot.tree.add_command(duel)
