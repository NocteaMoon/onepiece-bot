import discord
from discord import app_commands
import random
from database.db import get_pool
from utils.players import get_player
from utils.channel_check import require_salon

casino_group = app_commands.Group(name="casino", description="Tente ta chance au casino")


async def require_player_and_mise(interaction, mise):
    player = await get_player(interaction.guild_id, interaction.user.id)
    if player is None:
        await interaction.followup.send("Tu n'as pas encore de personnage ! Lance `/commencer` pour débuter l'aventure 🏴‍☠️")
        return None
    if mise <= 0:
        await interaction.followup.send("La mise doit être positive 🙃")
        return None
    if mise > player["berrys"]:
        await interaction.followup.send(f"Tu n'as que **{player['berrys']:,}฿** en liquide, impossible de miser **{mise:,}฿**.")
        return None
    return player


async def ajuster_berrys(guild_id, user_id, delta):
    pool = get_pool()
    async with pool.acquire() as conn:
        await conn.execute("UPDATE players SET berrys = berrys + $3 WHERE guild_id=$1 AND user_id=$2", guild_id, user_id, delta)


# ===== MACHINE À SOUS =====

SLOT_SYMBOLS = [("🍒", 35, 2), ("🍋", 30, 3), ("🍇", 20, 5), ("⭐", 10, 10), ("💰", 5, 25)]

async def jouer_machine_a_sous(guild_id, user_id, mise):
    noms = [s[0] for s in SLOT_SYMBOLS]
    poids = [s[1] for s in SLOT_SYMBOLS]
    tirage = random.choices(noms, weights=poids, k=3)

    if tirage[0] == tirage[1] == tirage[2]:
        mult = next(s[2] for s in SLOT_SYMBOLS if s[0] == tirage[0])
        gain = mise * mult
        resultat = f"🎉 **TRIPLE {tirage[0]}** ! Multiplicateur x{mult} !"
    elif tirage[0] == tirage[1] or tirage[1] == tirage[2] or tirage[0] == tirage[2]:
        gain = mise
        resultat = "Deux symboles identiques — mise remboursée."
    else:
        gain = 0
        resultat = "Aucune combinaison... la maison gagne cette fois."

    delta = gain - mise
    await ajuster_berrys(guild_id, user_id, delta)

    embed = discord.Embed(
        title="🎰 Machine à sous",
        color=0x27AE60 if delta > 0 else (0x95A5A6 if delta == 0 else 0xC0392B)
    )
    embed.description = f"[ {tirage[0]} | {tirage[1]} | {tirage[2]} ]\n\n{resultat}"
    embed.add_field(name="Résultat", value=(f"+{delta:,}฿" if delta > 0 else (f"{delta:,}฿" if delta < 0 else "0฿ (mise rendue)")), inline=False)
    embed.set_footer(text=f"🌊 One Piece Bot • Casino • Mise : {mise:,}฿")

    view = SlotView(guild_id, user_id, mise)
    return embed, view


class SlotView(discord.ui.View):
    def __init__(self, guild_id, user_id, mise):
        super().__init__(timeout=30)
        self.guild_id = guild_id
        self.user_id = user_id
        self.mise = mise

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("⛔ Ce n'est pas ta machine à sous !", ephemeral=True)
            return False
        return True

    @discord.ui.button(label="Retenter (même mise)", emoji="🎰", style=discord.ButtonStyle.primary)
    async def retenter(self, interaction: discord.Interaction, button: discord.ui.Button):
        player = await get_player(self.guild_id, self.user_id)
        if player["berrys"] < self.mise:
            await interaction.response.send_message("⛔ Tu n'as plus assez de Berrys pour retenter avec cette mise.", ephemeral=True)
            return
        embed, view = await jouer_machine_a_sous(self.guild_id, self.user_id, self.mise)
        await interaction.response.edit_message(embed=embed, view=view)


@casino_group.command(name="machine-a-sous", description="Tenter ta chance à la machine à sous")
@app_commands.describe(mise="Le montant à miser")
@require_salon("salon_casino")
async def machine_a_sous(interaction: discord.Interaction, mise: int):
    await interaction.response.defer()
    player = await require_player_and_mise(interaction, mise)
    if player is None:
        return
    embed, view = await jouer_machine_a_sous(interaction.guild_id, interaction.user.id, mise)
    await interaction.followup.send(embed=embed, view=view)


# ===== DÉS =====

@casino_group.command(name="des", description="Parier sur la somme d'un lancer de deux dés")
@app_commands.describe(mise="Le montant à miser", pari="Ton pari")
@app_commands.choices(pari=[
    app_commands.Choice(name="Petit (somme 2 à 6)", value="petit"),
    app_commands.Choice(name="Grand (somme 8 à 12)", value="grand"),
    app_commands.Choice(name="Sept pile (somme = 7)", value="sept"),
])
@require_salon("salon_casino")
async def des(interaction: discord.Interaction, mise: int, pari: app_commands.Choice[str]):
    await interaction.response.defer()
    player = await require_player_and_mise(interaction, mise)
    if player is None:
        return

    d1, d2 = random.randint(1, 6), random.randint(1, 6)
    somme = d1 + d2

    gagne = False
    multiplicateur = 0
    if pari.value == "petit" and 2 <= somme <= 6:
        gagne = True
        multiplicateur = 1.9
    elif pari.value == "grand" and 8 <= somme <= 12:
        gagne = True
        multiplicateur = 1.9
    elif pari.value == "sept" and somme == 7:
        gagne = True
        multiplicateur = 4.0

    gain = round(mise * multiplicateur) if gagne else 0
    delta = gain - mise
    await ajuster_berrys(interaction.guild_id, interaction.user.id, delta)

    embed = discord.Embed(title="🎲 Dés", color=0x27AE60 if gagne else 0xC0392B)
    embed.description = f"🎲 {d1} + 🎲 {d2} = **{somme}**\n\nTon pari : {pari.name}"
    embed.add_field(name="Résultat", value=(f"+{delta:,}฿" if delta > 0 else f"{delta:,}฿"), inline=False)
    embed.set_footer(text=f"🌊 One Piece Bot • Casino • Mise : {mise:,}฿")
    await interaction.followup.send(embed=embed)


# ===== ROULETTE =====

@casino_group.command(name="roulette", description="Miser sur la couleur ou un numéro à la roulette")
@app_commands.describe(mise="Le montant à miser", type_pari="Type de pari", numero="Numéro exact (0-36), si tu paries sur un numéro")
@app_commands.choices(type_pari=[
    app_commands.Choice(name="Rouge", value="rouge"),
    app_commands.Choice(name="Noir", value="noir"),
    app_commands.Choice(name="Numéro exact", value="numero"),
])
@require_salon("salon_casino")
async def roulette(interaction: discord.Interaction, mise: int, type_pari: app_commands.Choice[str], numero: int = None):
    await interaction.response.defer()
    player = await require_player_and_mise(interaction, mise)
    if player is None:
        return

    if type_pari.value == "numero" and (numero is None or not (0 <= numero <= 36)):
        await interaction.followup.send("⛔ Précise un numéro entre 0 et 36 pour ce type de pari.")
        return

    resultat_numero = random.randint(0, 36)
    if resultat_numero == 0:
        couleur = "vert"
    elif resultat_numero % 2 == 1:
        couleur = "rouge"
    else:
        couleur = "noir"

    gagne = False
    multiplicateur = 0
    if type_pari.value in ("rouge", "noir") and couleur == type_pari.value:
        gagne = True
        multiplicateur = 2.0
    elif type_pari.value == "numero" and numero == resultat_numero:
        gagne = True
        multiplicateur = 35.0

    gain = round(mise * multiplicateur) if gagne else 0
    delta = gain - mise
    await ajuster_berrys(interaction.guild_id, interaction.user.id, delta)

    emoji_couleur = {"rouge": "🔴", "noir": "⚫", "vert": "🟢"}[couleur]
    embed = discord.Embed(title="🎡 Roulette", color=0x27AE60 if gagne else 0xC0392B)
    embed.description = f"La bille s'arrête sur **{resultat_numero}** {emoji_couleur}"
    embed.add_field(name="Résultat", value=(f"+{delta:,}฿" if delta > 0 else f"{delta:,}฿"), inline=False)
    embed.set_footer(text=f"🌊 One Piece Bot • Casino • Mise : {mise:,}฿")
    await interaction.followup.send(embed=embed)


# ===== BLACKJACK =====

CARD_RANKS = ["A", "2", "3", "4", "5", "6", "7", "8", "9", "10", "J", "Q", "K"]

def tirer_carte():
    return random.choice(CARD_RANKS)

def valeur_carte(carte):
    if carte == "A":
        return 11
    if carte in ("J", "Q", "K"):
        return 10
    return int(carte)

def valeur_main(main):
    total = sum(valeur_carte(c) for c in main)
    as_count = main.count("A")
    while total > 21 and as_count > 0:
        total -= 10
        as_count -= 1
    return total

def main_texte(main):
    return " ".join(main)


class BlackjackView(discord.ui.View):
    def __init__(self, guild_id, user_id, mise, main_joueur, main_croupier):
        super().__init__(timeout=60)
        self.guild_id = guild_id
        self.user_id = user_id
        self.mise = mise
        self.main_joueur = main_joueur
        self.main_croupier = main_croupier
        self.termine = False
        self.message = None

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("⛔ Ce n'est pas ta partie !", ephemeral=True)
            return False
        return True

    def build_embed(self, cache_croupier=True, message=None):
        val_joueur = valeur_main(self.main_joueur)
        embed = discord.Embed(title="🃏 Blackjack", color=0x8E44AD)
        if message:
            embed.description = message
        embed.add_field(name=f"Ta main — {val_joueur}", value=main_texte(self.main_joueur), inline=False)
        if cache_croupier:
            embed.add_field(name="Main du croupier", value=f"{self.main_croupier[0]} 🂠", inline=False)
        else:
            val_croupier = valeur_main(self.main_croupier)
            embed.add_field(name=f"Main du croupier — {val_croupier}", value=main_texte(self.main_croupier), inline=False)
        embed.set_footer(text=f"🌊 One Piece Bot • Casino • Mise : {self.mise:,}฿")
        return embed

    async def resoudre(self):
        self.termine = True
        for c in self.children:
            c.disabled = True

        val_joueur = valeur_main(self.main_joueur)
        val_croupier = valeur_main(self.main_croupier)

        if val_joueur > 21:
            issue = "perdu"
        else:
            while val_croupier < 17:
                self.main_croupier.append(tirer_carte())
                val_croupier = valeur_main(self.main_croupier)
            if val_croupier > 21 or val_joueur > val_croupier:
                issue = "gagne"
            elif val_joueur == val_croupier:
                issue = "egalite"
            else:
                issue = "perdu"

        if issue == "gagne":
            blackjack_naturel = len(self.main_joueur) == 2 and val_joueur == 21
            mult = 2.5 if blackjack_naturel else 2.0
            gain = round(self.mise * mult)
            message = "🏆 Tu gagnes la partie !" + (" (Blackjack naturel !)" if blackjack_naturel else "")
        elif issue == "egalite":
            gain = self.mise
            message = "🤝 Égalité, ta mise t'est rendue."
        else:
            gain = 0
            message = "💀 Tu perds cette manche."

        delta = gain - self.mise
        await ajuster_berrys(self.guild_id, self.user_id, delta)

        embed = self.build_embed(cache_croupier=False, message=message)
        embed.add_field(name="Résultat", value=(f"+{delta:,}฿" if delta > 0 else (f"{delta:,}฿" if delta < 0 else "0฿ (mise rendue)")), inline=False)
        embed.color = 0x27AE60 if delta > 0 else (0x95A5A6 if delta == 0 else 0xC0392B)
        await self.message.edit(embed=embed, view=self)

    @discord.ui.button(label="Tirer une carte", emoji="🃏", style=discord.ButtonStyle.primary)
    async def tirer(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        if self.termine:
            return
        self.main_joueur.append(tirer_carte())
        if valeur_main(self.main_joueur) > 21:
            await self.resoudre()
            return
        await self.message.edit(embed=self.build_embed(), view=self)

    @discord.ui.button(label="Rester", emoji="✋", style=discord.ButtonStyle.secondary)
    async def rester(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        if self.termine:
            return
        await self.resoudre()

    async def on_timeout(self):
        for c in self.children:
            c.disabled = True
        if self.message:
            try:
                await self.message.edit(view=self)
            except discord.HTTPException:
                pass


@casino_group.command(name="blackjack", description="Jouer une partie de blackjack contre le croupier")
@app_commands.describe(mise="Le montant à miser")
@require_salon("salon_casino")
async def blackjack(interaction: discord.Interaction, mise: int):
    await interaction.response.defer()
    player = await require_player_and_mise(interaction, mise)
    if player is None:
        return

    main_joueur = [tirer_carte(), tirer_carte()]
    main_croupier = [tirer_carte(), tirer_carte()]

    view = BlackjackView(interaction.guild_id, interaction.user.id, mise, main_joueur, main_croupier)
    msg = await interaction.followup.send(embed=view.build_embed(), view=view)
    view.message = msg

    if valeur_main(main_joueur) == 21:
        await view.resoudre()


def setup_casino_commands(bot):
    bot.tree.add_command(casino_group)
