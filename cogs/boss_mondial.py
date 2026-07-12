import discord
from discord import app_commands
from discord.ext import tasks
import random
from database.db import get_pool
from utils.players import get_player, add_xp
from utils.combat_stats import get_effective_stats
from utils.channel_check import require_salon
from utils.announcements import announce_level_up
from utils.notoriete import add_notoriete, MONTANT_BOSS_MONDIAL
from data.ennemis import ENNEMIS
from data.mers import MERS

CHANCE_SPAWN = 0.20
DUREE_INSCRIPTION = 180
DUREE_COMBAT = 600
COUT_ENDURANCE = 20
MULT_PV_MIN, MULT_PV_MAX = 15, 25

boss_mondial_group = app_commands.Group(name="boss_mondial", description="Boss mondial spontané, ouvert à toute une mer")


def barre(valeur, max_valeur, taille=14, plein="🟥", vide="⬜"):
    valeur = max(0, min(max_valeur, valeur))
    rempli = round(valeur / max_valeur * taille) if max_valeur > 0 else 0
    return plein * rempli + vide * (taille - rempli)


async def get_active_boss(guild_id: int):
    pool = get_pool()
    async with pool.acquire() as conn:
        return await conn.fetchrow(
            "SELECT * FROM world_boss WHERE guild_id=$1 AND phase IN ('inscription','combat') ORDER BY id DESC LIMIT 1",
            guild_id
        )


class WorldBossCombatView(discord.ui.View):
    def __init__(self, guild_id, world_boss_id, mer, boss_nom, pv, pv_max, participant_ids):
        super().__init__(timeout=DUREE_COMBAT)
        self.guild_id = guild_id
        self.world_boss_id = world_boss_id
        self.mer = mer
        self.boss_nom = boss_nom
        self.pv = pv
        self.pv_max = pv_max
        self.participant_ids = set(participant_ids)
        self.termine = False
        self.message = None

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id not in self.participant_ids:
            await interaction.response.send_message("⛔ Tu n'as pas rejoint ce combat à temps !", ephemeral=True)
            return False
        return True

    def build_embed(self, message: str = None):
        embed = discord.Embed(title=f"👑 BOSS MONDIAL — {self.boss_nom.capitalize()}", color=0x7F0000)
        embed.description = message or f"Toute **{self.mer}** se bat contre ce colosse ! Clique sur Attaquer autant de fois que possible."
        embed.add_field(name=f"PV du boss — {max(0, self.pv):,}/{self.pv_max:,}", value=barre(self.pv, self.pv_max), inline=False)
        embed.add_field(name="Combattants", value=str(len(self.participant_ids)), inline=True)
        embed.set_footer(text="🌊 One Piece Bot • Boss mondial")
        return embed

    async def victoire(self, interaction):
        self.termine = True
        for c in self.children:
            c.disabled = True

        pool = get_pool()
        async with pool.acquire() as conn:
            rows = await conn.fetch(
                "SELECT user_id, degats FROM world_boss_participants WHERE world_boss_id=$1",
                self.world_boss_id
            )
            await conn.execute("UPDATE world_boss SET phase='termine' WHERE id=$1", self.world_boss_id)

        total_degats = sum(r["degats"] for r in rows) or 1
        mvp = max(rows, key=lambda r: r["degats"]) if rows else None
        base_reward = random.randint(300, 500)
        prime_flat = random.randint(60, 120)

        lignes_recap = []
        for r in rows:
            ratio = r["degats"] / total_degats
            berrys = max(20, round(base_reward * ratio))
            xp = max(10, round(150 * ratio))
            if mvp and r["user_id"] == mvp["user_id"]:
                berrys = round(berrys * 1.5)
                xp = round(xp * 1.5)

            async with pool.acquire() as conn:
                await conn.execute(
                    "UPDATE players SET berrys = berrys + $3, prime = prime + $4, nb_boss_vaincus = nb_boss_vaincus + 1 WHERE guild_id=$1 AND user_id=$2",
                    self.guild_id, r["user_id"], berrys, prime_flat
                )
            await add_notoriete(self.guild_id, r["user_id"], MONTANT_BOSS_MONDIAL)
            niveaux, niveau = await add_xp(self.guild_id, r["user_id"], xp, xp // 2)
            member = interaction.guild.get_member(r["user_id"])
            tag_mvp = " 👑" if mvp and r["user_id"] == mvp["user_id"] else ""
            lignes_recap.append(f"{member.mention if member else r['user_id']}{tag_mvp} : +{berrys}฿, +{xp} XP")
            if niveaux > 0 and member:
                await announce_level_up(interaction, member, niveau)

        recap_texte = "\n".join(lignes_recap[:15])
        embed = self.build_embed(f"🏆 **{self.boss_nom.capitalize()}** est vaincu par les forces unies de **{self.mer}** !\n\n{recap_texte}")
        embed.color = 0x27AE60
        await self.message.edit(embed=embed, view=self)

    @discord.ui.button(label="Attaquer !", emoji="⚔️", style=discord.ButtonStyle.danger)
    async def attaquer(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        if self.termine:
            return

        player = await get_player(self.guild_id, interaction.user.id)
        eff = await get_effective_stats(self.guild_id, interaction.user.id, player)
        degats = max(1, round(eff["force"] * random.uniform(0.85, 1.2)))

        pool = get_pool()
        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                "UPDATE world_boss SET pv = pv - $2 WHERE id=$1 RETURNING pv",
                self.world_boss_id, degats
            )
            existing = await conn.fetchrow(
                "SELECT id FROM world_boss_participants WHERE world_boss_id=$1 AND user_id=$2",
                self.world_boss_id, interaction.user.id
            )
            if existing:
                await conn.execute("UPDATE world_boss_participants SET degats = degats + $2 WHERE id=$1", existing["id"], degats)
            else:
                await conn.execute(
                    "INSERT INTO world_boss_participants (world_boss_id, guild_id, user_id, degats) VALUES ($1,$2,$3,$4)",
                    self.world_boss_id, self.guild_id, interaction.user.id, degats
                )

        self.pv = row["pv"]
        if self.pv <= 0:
            await self.victoire(interaction)
            return

        await self.message.edit(embed=self.build_embed(f"**{interaction.user.display_name}** frappe pour **{degats}** dégâts !"), view=self)

    async def on_timeout(self):
        if self.termine:
            return
        self.termine = True
        for c in self.children:
            c.disabled = True
        pool = get_pool()
        async with pool.acquire() as conn:
            await conn.execute("UPDATE world_boss SET phase='termine' WHERE id=$1", self.world_boss_id)
        if self.message:
            try:
                embed = self.build_embed(f"⏱️ Le temps est écoulé... **{self.boss_nom.capitalize()}** s'échappe, plus fort que jamais.")
                embed.color = 0x7F0000
                await self.message.edit(embed=embed, view=self)
            except discord.HTTPException:
                pass


class WorldBossInscriptionView(discord.ui.View):
    def __init__(self, guild_id, world_boss_id, mer, boss_nom, pv_max):
        super().__init__(timeout=DUREE_INSCRIPTION)
        self.guild_id = guild_id
        self.world_boss_id = world_boss_id
        self.mer = mer
        self.boss_nom = boss_nom
        self.pv_max = pv_max
        self.participant_ids = []
        self.lancee = False
        self.message = None

    def build_embed(self):
        embed = discord.Embed(
            title=f"⚠️ UN BOSS MONDIAL APPARAÎT — {self.boss_nom.capitalize()} !",
            description=f"Un ennemi titanesque surgit sur **{self.mer}** ! Tous les aventuriers présents sur cette mer peuvent rejoindre le combat.",
            color=0x7F0000
        )
        embed.add_field(name="Combattants inscrits", value=str(len(self.participant_ids)), inline=True)
        embed.add_field(name="PV du boss", value=f"{self.pv_max:,}", inline=True)
        embed.set_footer(text=f"🌊 One Piece Bot • Boss mondial • {DUREE_INSCRIPTION // 60} min pour rejoindre")
        return embed

    @discord.ui.button(label="Rejoindre le combat !", emoji="⚔️", style=discord.ButtonStyle.danger)
    async def rejoindre(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.lancee:
            await interaction.response.send_message("Le combat a déjà commencé !", ephemeral=True)
            return
        if interaction.user.id in self.participant_ids:
            await interaction.response.send_message("Tu as déjà rejoint le combat !", ephemeral=True)
            return

        player = await get_player(self.guild_id, interaction.user.id)
        if player is None:
            await interaction.response.send_message("Tu n'as pas encore de personnage ! Lance `/commencer` d'abord.", ephemeral=True)
            return
        if player["mer"] != self.mer:
            await interaction.response.send_message(f"⛔ Tu dois être sur **{self.mer}** pour rejoindre ce combat (utilise `/voyager`).", ephemeral=True)
            return
        if player["endurance"] < COUT_ENDURANCE:
            await interaction.response.send_message(f"😮‍💨 Il te faut {COUT_ENDURANCE} endurance pour rejoindre.", ephemeral=True)
            return

        pool = get_pool()
        async with pool.acquire() as conn:
            await conn.execute(
                "UPDATE players SET endurance = endurance - $3 WHERE guild_id=$1 AND user_id=$2",
                self.guild_id, interaction.user.id, COUT_ENDURANCE
            )
        self.participant_ids.append(interaction.user.id)
        await interaction.response.edit_message(embed=self.build_embed(), view=self)

    async def on_timeout(self):
        if self.lancee:
            return
        self.lancee = True
        for c in self.children:
            c.disabled = True

        pool = get_pool()
        if not self.participant_ids:
            async with pool.acquire() as conn:
                await conn.execute("UPDATE world_boss SET phase='termine' WHERE id=$1", self.world_boss_id)
            if self.message:
                try:
                    await self.message.edit(content="😴 Personne n'a rejoint à temps, le boss retourne dans les profondeurs.", embed=None, view=self)
                except discord.HTTPException:
                    pass
            return

        async with pool.acquire() as conn:
            await conn.execute("UPDATE world_boss SET phase='combat' WHERE id=$1", self.world_boss_id)

        combat_view = WorldBossCombatView(self.guild_id, self.world_boss_id, self.mer, self.boss_nom, self.pv_max, self.pv_max, self.participant_ids)
        embed = combat_view.build_embed("🏁 Le combat commence ! Cliquez tous sur Attaquer autant de fois que possible.")
        if self.message:
            try:
                await self.message.edit(embed=embed, view=combat_view)
                combat_view.message = self.message
            except discord.HTTPException:
                pass


async def force_spawn_boss(guild: discord.Guild):
    pool = get_pool()
    async with pool.acquire() as conn:
        config = await conn.fetchrow("SELECT salon_combat FROM guild_config WHERE guild_id=$1", guild.id)
    if not config or not config["salon_combat"]:
        return False, "Aucun salon Combat configuré pour ce serveur."

    actif = await get_active_boss(guild.id)
    if actif:
        return False, "Un boss mondial est déjà actif sur ce serveur."

    mer_choisie = random.choice([m[0] for m in MERS])
    pool_ennemis = [e for e in ENNEMIS if e["mer"] == mer_choisie]
    if not pool_ennemis:
        return False, f"Aucun ennemi connu sur {mer_choisie}."

    boss_template = max(pool_ennemis, key=lambda e: e["pv"])
    multiplicateur = random.randint(MULT_PV_MIN, MULT_PV_MAX)
    pv_max = boss_template["pv"] * multiplicateur

    channel = guild.get_channel(config["salon_combat"])
    if channel is None:
        return False, "Le salon Combat configuré est introuvable."

    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "INSERT INTO world_boss (guild_id, mer, boss_nom, pv, pv_max, phase, channel_id) VALUES ($1,$2,$3,$4,$5,'inscription',$6) RETURNING id",
            guild.id, mer_choisie, boss_template["nom"], pv_max, pv_max, channel.id
        )
    world_boss_id = row["id"]

    view = WorldBossInscriptionView(guild.id, world_boss_id, mer_choisie, boss_template["nom"], pv_max)
    msg = await channel.send(embed=view.build_embed(), view=view)
    view.message = msg

    async with pool.acquire() as conn:
        await conn.execute("UPDATE world_boss SET message_id=$2 WHERE id=$1", world_boss_id, msg.id)

    return True, f"Boss mondial invoqué sur {mer_choisie} : {boss_template['nom']} ({pv_max:,} PV)."


_bot_ref = None

@tasks.loop(minutes=45)
async def spawn_check_loop():
    if _bot_ref is None:
        return
    for guild in _bot_ref.guilds:
        try:
            actif = await get_active_boss(guild.id)
            if actif:
                continue
            if random.random() > CHANCE_SPAWN:
                continue
            await force_spawn_boss(guild)
        except Exception as e:
            print(f"Erreur spawn boss mondial ({guild.id}): {e}")


@boss_mondial_group.command(name="statut", description="Voir si un boss mondial est actif sur le serveur")
@require_salon("salon_combat")
async def boss_mondial_statut(interaction: discord.Interaction):
    await interaction.response.defer()
    actif = await get_active_boss(interaction.guild_id)
    if not actif:
        await interaction.followup.send("Aucun boss mondial n'est actif pour l'instant. Ils apparaissent de façon imprévisible, reste à l'affût ! 👀")
        return

    if actif["phase"] == "inscription":
        await interaction.followup.send(f"⚠️ **{actif['boss_nom'].capitalize()}** vient d'apparaître sur **{actif['mer']}** ! Rejoins vite le message d'annonce dans ce salon.")
    else:
        await interaction.followup.send(f"👑 Combat en cours contre **{actif['boss_nom'].capitalize()}** sur **{actif['mer']}** — {max(0, actif['pv']):,}/{actif['pv_max']:,} PV restants.")


def start_boss_loop(bot):
    global _bot_ref
    _bot_ref = bot
    if not spawn_check_loop.is_running():
        spawn_check_loop.start()


def setup_boss_mondial_commands(bot):
    bot.tree.add_command(boss_mondial_group)
