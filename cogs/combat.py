import discord
from discord import app_commands
import random
import datetime
from database.db import get_pool
from utils.players import get_player, add_xp
from utils.combat_stats import get_effective_stats
from utils.channel_check import require_salon
from utils.announcements import announce_level_up
from data.ennemis import ENNEMIS

COUT_ENDURANCE = 20

def barre(valeur, max_valeur, taille=10, plein="🟩", vide="⬜"):
    valeur = max(0, min(max_valeur, valeur))
    rempli = round(valeur / max_valeur * taille) if max_valeur > 0 else 0
    return plein * rempli + vide * (taille - rempli)


class ItemSelect(discord.ui.Select):
    def __init__(self, combat_view, options_data):
        options = [
            discord.SelectOption(label=f"{o['nom']} (x{o['quantite']})", value=str(o["inv_id"]), description=o["effet"][:100])
            for o in options_data
        ]
        super().__init__(placeholder="Choisis un objet à utiliser...", options=options)
        self.combat_view = combat_view
        self.options_data = {str(o["inv_id"]): o for o in options_data}

    async def callback(self, interaction: discord.Interaction):
        chosen = self.options_data[self.values[0]]
        await self.combat_view.utiliser_objet(interaction, chosen)


class ItemSelectView(discord.ui.View):
    def __init__(self, combat_view, options_data):
        super().__init__(timeout=30)
        self.add_item(ItemSelect(combat_view, options_data))


class CombatView(discord.ui.View):
    def __init__(self, guild_id, user_id, enemy, player_pv_depart, true_pv_max, effective_stats):
        super().__init__(timeout=90)
        self.guild_id = guild_id
        self.user_id = user_id
        self.enemy = dict(enemy)
        self.player_pv = player_pv_depart
        self.player_pv_max = player_pv_depart
        self.true_pv_max = true_pv_max
        self.eff = effective_stats
        self.termine = False
        self.message = None
        self.log = []

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("⛔ Ce n'est pas ton combat !", ephemeral=True)
            return False
        return True

    def build_embed(self):
        titre = f"⚔️ Combat — {self.enemy['nom'].capitalize()}"
        if self.enemy.get("boss"):
            titre = f"👑 BOSS — {self.enemy['nom'].capitalize()}"
        embed = discord.Embed(title=titre, color=0xC0392B)
        embed.add_field(name="Tes PV", value=barre(self.player_pv, self.player_pv_max), inline=False)
        embed.add_field(name="PV ennemi", value=barre(self.enemy["pv"], self.enemy["pv_max"]), inline=False)
        if self.log:
            embed.description = "\n".join(self.log[-4:])
        embed.set_footer(text="🌊 One Piece Bot • Combat")
        return embed

    async def appliquer_victoire(self, interaction):
        self.termine = True
        for c in self.children:
            c.disabled = True

        pool = get_pool()
        berrys_gain = random.randint(self.enemy["berrys_min"], self.enemy["berrys_max"])
        pv_final = min(self.player_pv, self.true_pv_max)
        async with pool.acquire() as conn:
            await conn.execute(
                "UPDATE players SET berrys = berrys + $3, prime = prime + $4, pv = $5 WHERE guild_id=$1 AND user_id=$2",
                self.guild_id, self.user_id, berrys_gain, self.enemy["prime_gain"], pv_final
            )
        niveaux_gagnes, nouveau_niveau = await add_xp(self.guild_id, self.user_id, self.enemy["xp"], self.enemy["xpc"])

        self.log.append(f"🏆 Victoire ! Tu gagnes **{berrys_gain}฿**, **{self.enemy['prime_gain']}฿ de prime**, et de l'XP !")
        embed = self.build_embed()
        embed.color = 0x27AE60
        await self.message.edit(embed=embed, view=self)

        if niveaux_gagnes > 0:
            await announce_level_up(interaction, interaction.user, nouveau_niveau)

    async def appliquer_defaite(self):
        self.termine = True
        for c in self.children:
            c.disabled = True

        pool = get_pool()
        async with pool.acquire() as conn:
            player = await conn.fetchrow("SELECT berrys FROM players WHERE guild_id=$1 AND user_id=$2", self.guild_id, self.user_id)
            perte_pct = random.uniform(0.10, 0.20)
            perte_berrys = round(player["berrys"] * perte_pct)
            ko_jusqua = datetime.datetime.utcnow() + datetime.timedelta(minutes=self.enemy["ko_minutes"])

            equipped = await conn.fetch(
                "SELECT id FROM inventory WHERE guild_id=$1 AND user_id=$2 AND equipe = TRUE",
                self.guild_id, self.user_id
            )
            for e in equipped:
                perte_dur = random.randint(5, 15)
                await conn.execute("UPDATE inventory SET durabilite = GREATEST(0, durabilite - $2) WHERE id=$1", e["id"], perte_dur)

            await conn.execute(
                "UPDATE players SET berrys = berrys - $3, pv = 1, ko_jusqua = $4 WHERE guild_id=$1 AND user_id=$2",
                self.guild_id, self.user_id, perte_berrys, ko_jusqua
            )

        self.log.append(
            f"💀 Défaite... Tu perds **{perte_berrys}฿**, ton équipement s'abîme, "
            f"et tu es K.O. pendant **{self.enemy['ko_minutes']} minutes** (les actions pacifiques restent possibles)."
        )
        embed = self.build_embed()
        embed.color = 0x7F0000
        await self.message.edit(embed=embed, view=self)

    async def tour_ennemi(self, defense_active=False):
        if self.enemy["pv"] <= 0:
            return
        degats = max(1, round(self.enemy["force"] * random.uniform(0.85, 1.15) - self.eff["defense"] * 0.5))
        if defense_active:
            degats = max(1, round(degats * 0.5))
        self.player_pv -= degats
        self.log.append(f"L'ennemi riposte pour **{degats}** dégâts !")

    @discord.ui.button(label="Attaque", emoji="⚔️", style=discord.ButtonStyle.danger)
    async def attaque(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        if self.termine:
            return
        degats = max(1, round(self.eff["force"] * random.uniform(0.85, 1.15) - self.enemy["defense"] * 0.5))
        self.enemy["pv"] -= degats
        self.log.append(f"Tu infliges **{degats}** dégâts !")

        if self.enemy["pv"] <= 0:
            await self.appliquer_victoire(interaction)
            return

        await self.tour_ennemi()
        if self.player_pv <= 0:
            await self.appliquer_defaite()
            return

        await self.message.edit(embed=self.build_embed(), view=self)

    @discord.ui.button(label="Défense", emoji="🛡️", style=discord.ButtonStyle.primary)
    async def defense(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        if self.termine:
            return
        self.log.append("Tu te mets en garde, prêt à encaisser le prochain coup.")
        await self.tour_ennemi(defense_active=True)
        if self.player_pv <= 0:
            await self.appliquer_defaite()
            return
        await self.message.edit(embed=self.build_embed(), view=self)

    @discord.ui.button(label="Objet", emoji="🎒", style=discord.ButtonStyle.secondary)
    async def objet(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.termine:
            return
        pool = get_pool()
        async with pool.acquire() as conn:
            rows = await conn.fetch("""
                SELECT inventory.id AS inv_id, inventory.quantite, shop_items.nom, shop_items.soin_pv, shop_items.soin_endurance
                FROM inventory JOIN shop_items ON inventory.item_id = shop_items.id
                WHERE inventory.guild_id=$1 AND inventory.user_id=$2 AND inventory.quantite > 0
                  AND (shop_items.soin_pv > 0 OR shop_items.soin_endurance > 0)
            """, self.guild_id, self.user_id)
        if not rows:
            await interaction.response.send_message("Tu n'as aucun objet utilisable en combat.", ephemeral=True)
            return
        options_data = []
        for r in rows:
            effet_parts = []
            if r["soin_pv"]:
                effet_parts.append(f"+{r['soin_pv']} PV")
            if r["soin_endurance"]:
                effet_parts.append(f"+{r['soin_endurance']} Endurance")
            options_data.append({
                "inv_id": r["inv_id"], "nom": r["nom"], "quantite": r["quantite"],
                "effet": ", ".join(effet_parts), "soin_pv": r["soin_pv"], "soin_endurance": r["soin_endurance"]
            })
        await interaction.response.send_message("Choisis un objet :", view=ItemSelectView(self, options_data), ephemeral=True)

    async def utiliser_objet(self, interaction: discord.Interaction, item_data):
        pool = get_pool()
        async with pool.acquire() as conn:
            async with conn.transaction():
                inv_row = await conn.fetchrow("SELECT quantite FROM inventory WHERE id = $1", item_data["inv_id"])
                if not inv_row or inv_row["quantite"] <= 0:
                    await interaction.response.edit_message(content="Cet objet n'est plus disponible.", view=None)
                    return
                if inv_row["quantite"] > 1:
                    await conn.execute("UPDATE inventory SET quantite = quantite - 1 WHERE id=$1", item_data["inv_id"])
                else:
                    await conn.execute("DELETE FROM inventory WHERE id=$1", item_data["inv_id"])

        self.player_pv = min(self.player_pv_max, self.player_pv + item_data["soin_pv"])
        self.log.append(f"Tu utilises **{item_data['nom']}** ({item_data['effet']}) !")

        await interaction.response.edit_message(content=f"✅ {item_data['nom']} utilisé !", view=None)

        await self.tour_ennemi()
        if self.player_pv <= 0:
            await self.appliquer_defaite()
            return
        await self.message.edit(embed=self.build_embed(), view=self)

    @discord.ui.button(label="Fuite", emoji="🏃", style=discord.ButtonStyle.secondary)
    async def fuite(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        if self.termine:
            return
        chance = max(10, min(90, 50 + (self.eff["agilite"] - self.enemy["vitesse"]) * 2))
        if random.randint(1, 100) <= chance:
            self.termine = True
            for c in self.children:
                c.disabled = True
            self.log.append("🏃 Tu prends la fuite avec succès, sans récompense ni pénalité.")
            await self.message.edit(embed=self.build_embed(), view=self)
            return

        self.log.append("Ta tentative de fuite échoue, l'ennemi en profite !")
        await self.tour_ennemi()
        if self.player_pv <= 0:
            await self.appliquer_defaite()
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


@app_commands.command(name="combattre", description="Affronter un ennemi présent sur ta mer actuelle")
@require_salon("salon_combat")
async def combattre(interaction: discord.Interaction):
    await interaction.response.defer()
    player = await get_player(interaction.guild_id, interaction.user.id)
    if player is None:
        await interaction.followup.send("Tu n'as pas encore de personnage ! Lance `/commencer` pour débuter l'aventure 🏴‍☠️")
        return

    if player["ko_jusqua"]:
        now = datetime.datetime.utcnow()
        if player["ko_jusqua"] > now:
            restant = int((player["ko_jusqua"] - now).total_seconds() // 60) + 1
            await interaction.followup.send(f"😵 Tu es encore K.O. pendant **{restant} minute(s)**. Repose-toi avant de repartir au combat !")
            return

    if player["endurance"] < COUT_ENDURANCE:
        await interaction.followup.send(f"😮‍💨 Il te faut {COUT_ENDURANCE} endurance pour combattre (tu as {player['endurance']}).")
        return

    pool_ennemis = [e for e in ENNEMIS if e["mer"] == player["mer"]]
    if not pool_ennemis:
        await interaction.followup.send(f"Aucun ennemi connu sur **{player['mer']}** pour le moment.")
        return

    enemy_template = random.choices(pool_ennemis, weights=[e["poids"] for e in pool_ennemis], k=1)[0]
    enemy = dict(enemy_template)
    enemy["pv_max"] = enemy["pv"]

    pool = get_pool()
    async with pool.acquire() as conn:
        await conn.execute(
            "UPDATE players SET endurance = endurance - $3 WHERE guild_id=$1 AND user_id=$2",
            interaction.guild_id, interaction.user.id, COUT_ENDURANCE
        )

    eff = await get_effective_stats(interaction.guild_id, interaction.user.id, player)
    player_pv_combat = player["pv"] + eff["bonus_pv_combat"]

    view = CombatView(interaction.guild_id, interaction.user.id, enemy, player_pv_combat, player["pv_max"], eff)
    intro = f"👑 **{enemy['nom'].capitalize()}** légendaire se dresse devant toi !" if enemy.get("boss") else f"**{enemy['nom'].capitalize()}** te barre la route !"
    embed = view.build_embed()
    embed.description = intro
    msg = await interaction.followup.send(embed=embed, view=view)
    view.message = msg


def setup_combat_commands(bot):
    bot.tree.add_command(combattre)
