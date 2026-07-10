import discord
from discord import app_commands
import asyncio
import random
from database.db import get_pool
from utils.players import get_player, add_xp
from utils.combat_stats import get_effective_stats
from utils.channel_check import require_salon
from utils.announcements import announce_level_up

DUREE_INSCRIPTION = 45


def barre(valeur, max_valeur, taille=10, plein="🟩", vide="⬜"):
    valeur = max(0, min(max_valeur, valeur))
    rempli = round(valeur / max_valeur * taille) if max_valeur > 0 else 0
    return plein * rempli + vide * (taille - rempli)


class TournamentMatchView(discord.ui.View):
    def __init__(self, guild_id, p1, p2, round_label):
        super().__init__(timeout=90)
        self.guild_id = guild_id
        self.p1 = p1
        self.p2 = p2
        self.round_label = round_label
        self.current_turn_id = random.choice([p1["id"], p2["id"]])
        self.termine_event = asyncio.Event()
        self.winner = None
        self.message = None
        self.log = []

    def joueur(self, uid):
        return self.p1 if uid == self.p1["id"] else self.p2

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id not in (self.p1["id"], self.p2["id"]):
            await interaction.response.send_message("⛔ Ce match ne te concerne pas !", ephemeral=True)
            return False
        if interaction.user.id != self.current_turn_id:
            await interaction.response.send_message("⌛ Ce n'est pas ton tour !", ephemeral=True)
            return False
        return True

    def build_embed(self):
        embed = discord.Embed(title=f"🏆 Tournoi — {self.round_label}", color=0xE67E22)
        embed.description = f"{self.p1['name']} VS {self.p2['name']}"
        embed.add_field(name=f"{self.p1['name']} — {max(0, self.p1['pv'])}/{self.p1['pv_max']} PV", value=barre(self.p1["pv"], self.p1["pv_max"]), inline=False)
        embed.add_field(name=f"{self.p2['name']} — {max(0, self.p2['pv'])}/{self.p2['pv_max']} PV", value=barre(self.p2["pv"], self.p2["pv_max"]), inline=False)
        if self.log:
            embed.add_field(name="Journal", value="\n".join(self.log[-3:]), inline=False)
        tour = self.joueur(self.current_turn_id)
        embed.set_footer(text=f"🌊 One Piece Bot • Tournoi • Au tour de {tour['name']}")
        return embed

    async def terminer(self, gagnant_id, message):
        self.termine_event.set()
        for c in self.children:
            c.disabled = True
        self.winner = self.joueur(gagnant_id)
        self.log.append(message)
        embed = self.build_embed()
        embed.color = 0x27AE60
        await self.message.edit(embed=embed, view=self)

    @discord.ui.button(label="Attaque", emoji="⚔️", style=discord.ButtonStyle.danger)
    async def attaque(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        if self.termine_event.is_set():
            return
        attaquant_id = self.current_turn_id
        defenseur_id = self.p2["id"] if attaquant_id == self.p1["id"] else self.p1["id"]
        attaquant = self.joueur(attaquant_id)
        defenseur = self.joueur(defenseur_id)

        attaquant["defense_active"] = False
        degats = max(1, round(attaquant["eff"]["force"] * random.uniform(0.85, 1.15) - defenseur["eff"]["defense"] * 0.5))
        if defenseur.get("defense_active"):
            degats = max(1, round(degats * 0.5))
            defenseur["defense_active"] = False

        defenseur["pv"] -= degats
        self.log.append(f"**{attaquant['name']}** inflige **{degats}** dégâts à **{defenseur['name']}** !")

        if defenseur["pv"] <= 0:
            await self.terminer(attaquant_id, f"**{defenseur['name']}** est éliminé(e) du tournoi !")
            return

        self.current_turn_id = defenseur_id
        await self.message.edit(embed=self.build_embed(), view=self)

    @discord.ui.button(label="Défense", emoji="🛡️", style=discord.ButtonStyle.primary)
    async def defense(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        if self.termine_event.is_set():
            return
        joueur_id = self.current_turn_id
        joueur = self.joueur(joueur_id)
        joueur["defense_active"] = True
        self.log.append(f"**{joueur['name']}** se met en garde.")
        self.current_turn_id = self.p2["id"] if joueur_id == self.p1["id"] else self.p1["id"]
        await self.message.edit(embed=self.build_embed(), view=self)

    @discord.ui.button(label="Abandonner", emoji="🏳️", style=discord.ButtonStyle.secondary)
    async def abandon(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        if self.termine_event.is_set():
            return
        abandonneur_id = self.current_turn_id
        gagnant_id = self.p2["id"] if abandonneur_id == self.p1["id"] else self.p1["id"]
        abandonneur = self.joueur(abandonneur_id)
        await self.terminer(gagnant_id, f"**{abandonneur['name']}** abandonne le match !")

    async def on_timeout(self):
        if self.termine_event.is_set():
            return
        await self.terminer(self.p1["id"], f"⌛ Match non terminé à temps, **{self.p1['name']}** est qualifié(e) par défaut.")


class TournoiInscriptionView(discord.ui.View):
    def __init__(self, guild_id, hote: discord.Member):
        super().__init__(timeout=DUREE_INSCRIPTION)
        self.guild_id = guild_id
        self.participants = {hote.id: hote}
        self.message = None
        self.lancee = False

    def build_embed(self):
        names = [m.mention for m in self.participants.values()]
        embed = discord.Embed(
            title="🏆 Tournoi — Inscriptions ouvertes !",
            description="Rejoins le tournoi ! Il faut exactement **4 participants** pour démarrer.",
            color=0xE67E22
        )
        embed.add_field(name=f"Participants ({len(names)}/4)", value="\n".join(names) or "Aucun", inline=False)
        embed.set_footer(text=f"🌊 One Piece Bot • Tournoi • {DUREE_INSCRIPTION}s pour compléter l'effectif")
        return embed

    @discord.ui.button(label="Rejoindre le tournoi", emoji="🏆", style=discord.ButtonStyle.success)
    async def rejoindre(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.lancee:
            await interaction.response.send_message("Le tournoi a déjà commencé !", ephemeral=True)
            return
        if interaction.user.id in self.participants:
            await interaction.response.send_message("Tu es déjà inscrit !", ephemeral=True)
            return
        if len(self.participants) >= 4:
            await interaction.response.send_message("Le tournoi est déjà complet (4/4) !", ephemeral=True)
            return

        player = await get_player(self.guild_id, interaction.user.id)
        if player is None:
            await interaction.response.send_message("Tu n'as pas encore de personnage ! Lance `/commencer` d'abord.", ephemeral=True)
            return

        self.participants[interaction.user.id] = interaction.user

        if len(self.participants) >= 4:
            self.lancee = True
            for c in self.children:
                c.disabled = True
            await interaction.response.edit_message(embed=self.build_embed(), view=self)
            self.stop()
        else:
            await interaction.response.edit_message(embed=self.build_embed(), view=self)

    async def on_timeout(self):
        self.stop()


async def creer_participant(guild_id, member):
    p_data = await get_player(guild_id, member.id)
    eff = await get_effective_stats(guild_id, member.id, p_data)
    pv_max = p_data["pv_max"] + eff["bonus_pv_combat"]
    return {"id": member.id, "name": member.display_name, "member": member, "eff": eff, "pv": pv_max, "pv_max": pv_max, "defense_active": False}


async def jouer_match(channel, guild_id, p1, p2, round_label):
    p1 = dict(p1, pv=p1["pv_max"], defense_active=False)
    p2 = dict(p2, pv=p2["pv_max"], defense_active=False)
    view = TournamentMatchView(guild_id, p1, p2, round_label)
    msg = await channel.send(embed=view.build_embed(), view=view)
    view.message = msg
    await view.termine_event.wait()
    return view.winner


@app_commands.command(name="tournoi", description="Organiser un tournoi à élimination directe (4 joueurs)")
@require_salon("salon_duel")
async def tournoi(interaction: discord.Interaction):
    await interaction.response.defer()
    player = await get_player(interaction.guild_id, interaction.user.id)
    if player is None:
        await interaction.followup.send("Tu n'as pas encore de personnage ! Lance `/commencer` pour débuter l'aventure 🏴‍☠️")
        return

    view = TournoiInscriptionView(interaction.guild_id, interaction.user)
    msg = await interaction.followup.send(embed=view.build_embed(), view=view)
    view.message = msg

    await view.wait()

    if len(view.participants) < 4:
        await msg.edit(content="⌛ Pas assez de participants (4 requis), le tournoi est annulé.", embed=None, view=None)
        return

    membres = list(view.participants.values())
    random.shuffle(membres)
    p1, p2, p3, p4 = [await creer_participant(interaction.guild_id, m) for m in membres]

    channel = interaction.channel
    await channel.send(embed=discord.Embed(
        title="🏆 Le tournoi commence !",
        description=f"Demi-finale 1 : **{p1['name']}** VS **{p2['name']}**\nDemi-finale 2 : **{p3['name']}** VS **{p4['name']}**",
        color=0xE67E22
    ))

    gagnant1 = await jouer_match(channel, interaction.guild_id, p1, p2, "Demi-finale 1")
    gagnant2 = await jouer_match(channel, interaction.guild_id, p3, p4, "Demi-finale 2")

    await channel.send(embed=discord.Embed(
        title="🏆 Finale !",
        description=f"**{gagnant1['name']}** VS **{gagnant2['name']}**",
        color=0xE67E22
    ))

    champion = await jouer_match(channel, interaction.guild_id, gagnant1, gagnant2, "Finale")

    pool = get_pool()
    recompense = 250
    async with pool.acquire() as conn:
        await conn.execute(
            "UPDATE players SET berrys = berrys + $3, prime = prime + $4, succes_tournoi_gagne = TRUE WHERE guild_id=$1 AND user_id=$2",
            interaction.guild_id, champion["id"], recompense, 60
        )
    niveaux, niveau = await add_xp(interaction.guild_id, champion["id"], 100, 40)

    for p in [p1, p2, p3, p4]:
        if p["id"] != champion["id"]:
            await add_xp(interaction.guild_id, p["id"], 20, 8)

    await channel.send(embed=discord.Embed(
        title="👑 Champion du tournoi !",
        description=f"**{champion['name']}** remporte le tournoi et **{recompense:,}฿** !",
        color=0x27AE60
    ))

    if niveaux > 0:
        await announce_level_up(interaction, champion["member"], niveau)


def setup_tournoi_commands(bot):
    bot.tree.add_command(tournoi)
