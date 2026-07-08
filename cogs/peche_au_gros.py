import discord
from discord import app_commands
import random
from database.db import get_pool
from utils.players import get_player, add_xp
from utils.shop import get_item_by_name
from utils.channel_check import require_salon

COUT_ENDURANCE = 20

FISH_TIERS = [
    {"nom": "un petit poisson vif", "poids": 40, "stamina": 60, "tension_depart": 15, "tours": 5,
     "berrys_min": 20, "berrys_max": 40, "loot_chance": 0.10, "loot_options": ["Poisson argenté"],
     "xp": 15, "xpc": 6, "intro": "Une petite secousse... quelque chose mord à l'hameçon !"},
    {"nom": "un poisson robuste", "poids": 30, "stamina": 90, "tension_depart": 20, "tours": 6,
     "berrys_min": 40, "berrys_max": 80, "loot_chance": 0.25, "loot_options": ["Poisson tigre", "Anguille des courants"],
     "xp": 25, "xpc": 10, "intro": "Ça tire fort au bout de la ligne, ça pourrait bien valoir le coup !"},
    {"nom": "un poisson géant des courants", "poids": 20, "stamina": 130, "tension_depart": 25, "tours": 7,
     "berrys_min": 80, "berrys_max": 150, "loot_chance": 0.5, "loot_options": ["Étoile de mer scintillante", "Poisson tigre"],
     "xp": 40, "xpc": 16, "intro": "La canne plie dangereusement... c'est du gros !"},
    {"nom": "le légendaire poisson des abysses", "poids": 8, "stamina": 180, "tension_depart": 30, "tours": 8,
     "berrys_min": 150, "berrys_max": 300, "loot_chance": 1.0, "loot_options": ["Poisson légendaire des abysses"],
     "xp": 70, "xpc": 28, "intro": "Tu sens que c'est du très, très gros... une prise légendaire, peut-être !"},
    {"nom": "un monstre des profondeurs", "poids": 2, "stamina": 250, "tension_depart": 35, "tours": 9,
     "berrys_min": 300, "berrys_max": 500, "loot_chance": 1.0, "loot_options": ["Poisson légendaire des abysses"],
     "xp": 120, "xpc": 45, "intro": "⚠️ Une force monstrueuse tire au bout de la ligne... tiens bon !"},
]

TIRER_FLAVORS = [
    "Tu tires fermement sur la ligne !",
    "Tu donnes un grand coup sec sur la canne !",
    "Tu serres les dents et tires de toutes tes forces !",
    "Tu profites d'un instant de faiblesse du poisson pour tirer !",
    "Tu ramènes du fil d'un geste sûr !",
]

RELACHER_FLAVORS = [
    "Tu relâches un peu de fil pour soulager la ligne.",
    "Tu laisses filer quelques mètres pour ne rien casser.",
    "Tu desserres ta prise, laissant le poisson souffler.",
    "Tu joues la patience en relâchant du mou.",
    "Tu laisses la ligne se détendre légèrement.",
]

def barre(valeur, max_valeur=100, taille=10, plein="🟦", vide="⬜"):
    valeur = max(0, min(max_valeur, valeur))
    rempli = round(valeur / max_valeur * taille)
    return plein * rempli + vide * (taille - rempli)


class PecheAuGrosView(discord.ui.View):
    def __init__(self, guild_id, user_id, tier):
        super().__init__(timeout=60)
        self.guild_id = guild_id
        self.user_id = user_id
        self.tier = tier
        self.tension = tier["tension_depart"]
        self.stamina = tier["stamina"]
        self.stamina_max = tier["stamina"]
        self.tours_restants = tier["tours"]
        self.termine = False
        self.message = None

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("⛔ Ce n'est pas ta partie de pêche !", ephemeral=True)
            return False
        return True

    def loot_text(self):
        if self.tier["loot_chance"] >= 1.0:
            return f"\n🎁 Butin garanti : {', '.join(self.tier['loot_options'])}"
        elif self.tier["loot_chance"] > 0:
            pct = int(self.tier["loot_chance"] * 100)
            return f"\n🎁 {pct}% de chance d'obtenir : {', '.join(self.tier['loot_options'])}"
        return ""

    def build_embed(self, message: str = None):
        embed = discord.Embed(title=f"🎣 Pêche au gros — {self.tier['nom'].capitalize()}", color=0x1B3A5C)
        desc = message or self.tier["intro"]
        desc += f"\n\n💰 Butin potentiel : {self.tier['berrys_min']}-{self.tier['berrys_max']} Berrys{self.loot_text()}"
        embed.description = desc
        embed.add_field(name="Tension de la ligne", value=barre(self.tension, plein="🟥"), inline=False)
        embed.add_field(name="Résistance du poisson", value=barre(self.stamina, self.stamina_max), inline=False)
        embed.set_footer(text=f"🌊 One Piece Bot • Tours restants : {self.tours_restants}")
        return embed

    async def finir(self, interaction: discord.Interaction, victoire: bool, message: str):
        self.termine = True
        for child in self.children:
            child.disabled = True

        niveaux_gagnes = 0
        nouveau_niveau = None

        if victoire:
            pool = get_pool()
            berrys_bonus = random.randint(self.tier["berrys_min"], self.tier["berrys_max"])
            loot_item = None
            if random.random() < self.tier["loot_chance"]:
                nom_loot = random.choice(self.tier["loot_options"])
                loot_item = await get_item_by_name(self.guild_id, nom_loot)

            async with pool.acquire() as conn:
                async with conn.transaction():
                    await conn.execute(
                        "UPDATE players SET berrys = berrys + $3 WHERE guild_id=$1 AND user_id=$2",
                        self.guild_id, self.user_id, berrys_bonus
                    )
                    if loot_item:
                        existing = await conn.fetchrow(
                            "SELECT id FROM inventory WHERE guild_id=$1 AND user_id=$2 AND item_id=$3",
                            self.guild_id, self.user_id, loot_item["id"]
                        )
                        if existing:
                            await conn.execute("UPDATE inventory SET quantite = quantite + 1 WHERE id=$1", existing["id"])
                        else:
                            await conn.execute(
                                "INSERT INTO inventory (guild_id, user_id, item_id, quantite, durabilite) VALUES ($1,$2,$3,1,$4)",
                                self.guild_id, self.user_id, loot_item["id"], loot_item["durabilite_max"]
                            )

            niveaux_gagnes, nouveau_niveau = await add_xp(self.guild_id, self.user_id, self.tier["xp"], self.tier["xpc"])
            message += f"\n\n🏆 Tu remportes **{berrys_bonus} Berrys**"
            if loot_item:
                message += f" et **{loot_item['nom']}** !"
            else:
                message += " !"

        embed = self.build_embed(message)
        embed.color = 0x27AE60 if victoire else 0xC0392B
        await interaction.edit_original_response(embed=embed, view=self)

        if niveaux_gagnes > 0:
            await interaction.followup.send(embed=discord.Embed(
                title="🎉 Niveau supérieur !",
                description=f"{interaction.user.mention} passe **niveau {nouveau_niveau}** !",
                color=0x27AE60
            ))

    @discord.ui.button(label="Tirer sur la ligne", emoji="🎣", style=discord.ButtonStyle.primary)
    async def tirer(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        if self.termine:
            return
        degats = random.randint(15, 25)
        risque = random.randint(10, 22)
        self.stamina -= degats
        self.tension += risque
        self.tours_restants -= 1

        if self.stamina <= 0:
            await self.finir(interaction, True, "D'un dernier effort, tu remontes le poisson à bord !")
            return
        if self.tension >= 100:
            await self.finir(interaction, False, "💥 La ligne cède sous la tension ! Le poisson s'échappe...")
            return
        if self.tours_restants <= 0:
            await self.finir(interaction, False, "Le poisson finit par se libérer et replonge dans les profondeurs...")
            return

        embed = self.build_embed(random.choice(TIRER_FLAVORS))
        await interaction.edit_original_response(embed=embed, view=self)

    @discord.ui.button(label="Relâcher du fil", emoji="🪢", style=discord.ButtonStyle.secondary)
    async def relacher(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        if self.termine:
            return
        recup = random.randint(15, 25)
        regen_poisson = random.randint(5, 12)
        self.tension = max(0, self.tension - recup)
        self.stamina = min(self.stamina_max, self.stamina + regen_poisson)
        self.tours_restants -= 1

        if self.tours_restants <= 0:
            await self.finir(interaction, False, "Le poisson finit par se libérer et replonge dans les profondeurs...")
            return

        embed = self.build_embed(random.choice(RELACHER_FLAVORS))
        await interaction.edit_original_response(embed=embed, view=self)

    @discord.ui.button(label="Lâcher prise", emoji="✋", style=discord.ButtonStyle.danger)
    async def abandonner(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        if self.termine:
            return
        await self.finir(interaction, False, "Tu préfères lâcher prise plutôt que de risquer de perdre ta canne...")

    async def on_timeout(self):
        for child in self.children:
            child.disabled = True
        if self.message:
            try:
                await self.message.edit(view=self)
            except discord.HTTPException:
                pass


@app_commands.command(name="peche_au_gros", description="Tenter d'attraper un poisson géant (mini-jeu interactif à boutons)")
@require_salon("salon_peche")
async def peche_au_gros(interaction: discord.Interaction):
    await interaction.response.defer()
    player = await get_player(interaction.guild_id, interaction.user.id)
    if player is None:
        await interaction.followup.send("Tu n'as pas encore de personnage ! Lance `/commencer` pour débuter l'aventure 🏴‍☠️")
        return

    if player["endurance"] < COUT_ENDURANCE:
        await interaction.followup.send(
            f"😮‍💨 Il te faut {COUT_ENDURANCE} endurance pour tenter ça (tu as {player['endurance']}). Repose-toi un peu !"
        )
        return

    pool = get_pool()
    async with pool.acquire() as conn:
        await conn.execute(
            "UPDATE players SET endurance = endurance - $3 WHERE guild_id=$1 AND user_id=$2",
            interaction.guild_id, interaction.user.id, COUT_ENDURANCE
        )

    tier = random.choices(FISH_TIERS, weights=[t["poids"] for t in FISH_TIERS], k=1)[0]
    view = PecheAuGrosView(interaction.guild_id, interaction.user.id, tier)
    embed = view.build_embed()
    msg = await interaction.followup.send(embed=embed, view=view)
    view.message = msg


def setup_peche_au_gros_commands(bot):
    bot.tree.add_command(peche_au_gros)
