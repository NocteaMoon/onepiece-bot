import discord
from discord import app_commands
import random
from database.db import get_pool
from utils.players import get_player, add_xp
from utils.shop import get_item_by_name
from utils.channel_check import require_salon

COUT_ENDURANCE = 20
MAX_TOURS = 6

def barre(valeur, taille=10, plein="🟦", vide="⬜"):
    valeur = max(0, min(100, valeur))
    rempli = round(valeur / 100 * taille)
    return plein * rempli + vide * (taille - rempli)


class PecheAuGrosView(discord.ui.View):
    def __init__(self, guild_id, user_id):
        super().__init__(timeout=60)
        self.guild_id = guild_id
        self.user_id = user_id
        self.tension = 30
        self.stamina = 100
        self.tours_restants = MAX_TOURS
        self.termine = False
        self.message = None

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("⛔ Ce n'est pas ta partie de pêche !", ephemeral=True)
            return False
        return True

    def build_embed(self, message: str = None):
        embed = discord.Embed(title="🎣 Pêche au gros !", color=0x1B3A5C)
        if message:
            embed.description = message
        embed.add_field(name="Tension de la ligne", value=barre(self.tension, plein="🟥"), inline=False)
        embed.add_field(name="Résistance du poisson", value=barre(self.stamina), inline=False)
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
            item = await get_item_by_name(self.guild_id, "Poisson légendaire des abysses")
            berrys_bonus = random.randint(80, 150)
            async with pool.acquire() as conn:
                async with conn.transaction():
                    await conn.execute(
                        "UPDATE players SET berrys = berrys + $3 WHERE guild_id=$1 AND user_id=$2",
                        self.guild_id, self.user_id, berrys_bonus
                    )
                    if item:
                        existing = await conn.fetchrow(
                            "SELECT id FROM inventory WHERE guild_id=$1 AND user_id=$2 AND item_id=$3",
                            self.guild_id, self.user_id, item["id"]
                        )
                        if existing:
                            await conn.execute("UPDATE inventory SET quantite = quantite + 1 WHERE id=$1", existing["id"])
                        else:
                            await conn.execute(
                                "INSERT INTO inventory (guild_id, user_id, item_id, quantite, durabilite) VALUES ($1,$2,$3,1,$4)",
                                self.guild_id, self.user_id, item["id"], item["durabilite_max"]
                            )
            niveaux_gagnes, nouveau_niveau = await add_xp(self.guild_id, self.user_id, 40, 15)
            message += f"\n\n🏆 Tu remportes **{berrys_bonus} Berrys**"
            if item:
                message += " et un **Poisson légendaire des abysses** !"

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
        risque = random.randint(10, 20)
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

        embed = self.build_embed("Tu tires fermement sur la ligne !")
        await interaction.edit_original_response(embed=embed, view=self)

    @discord.ui.button(label="Relâcher du fil", emoji="🪢", style=discord.ButtonStyle.secondary)
    async def relacher(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        if self.termine:
            return
        recup = random.randint(15, 25)
        regen_poisson = random.randint(5, 10)
        self.tension = max(0, self.tension - recup)
        self.stamina = min(100, self.stamina + regen_poisson)
        self.tours_restants -= 1

        if self.tours_restants <= 0:
            await self.finir(interaction, False, "Le poisson finit par se libérer et replonge dans les profondeurs...")
            return

        embed = self.build_embed("Tu relâches un peu de fil pour soulager la ligne.")
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

    view = PecheAuGrosView(interaction.guild_id, interaction.user.id)
    embed = view.build_embed("Une secousse violente ! Quelque chose de gros a mordu à l'hameçon !")
    msg = await interaction.followup.send(embed=embed, view=view)
    view.message = msg


def setup_peche_au_gros_commands(bot):
    bot.tree.add_command(peche_au_gros)
