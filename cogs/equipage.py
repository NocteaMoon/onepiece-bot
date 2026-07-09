import discord
from discord import app_commands
from database.db import get_pool
from utils.players import get_player
from utils.channel_check import require_salon
from utils.equipages import (
    RANGS_ORDRE, RANG_EMOJIS, MAX_MEMBRES, COUT_CREATION,
    rang_valeur, get_crew_by_id, get_crew_by_nom, get_membres, count_membres, prime_cumulee
)

equipage_group = app_commands.Group(name="equipage", description="Gérer ton équipage")


async def get_joueur_et_equipage(guild_id, user_id):
    player = await get_player(guild_id, user_id)
    if player is None or not player["equipage_id"]:
        return player, None
    crew = await get_crew_by_id(guild_id, player["equipage_id"])
    return player, crew


@equipage_group.command(name="creer", description="Créer ton propre équipage (réservé aux Pirates)")
@app_commands.describe(nom="Le nom de ton équipage")
@require_salon("salon_equipages")
async def equipage_creer(interaction: discord.Interaction, nom: str):
    await interaction.response.defer()
    player = await get_player(interaction.guild_id, interaction.user.id)
    if player is None:
        await interaction.followup.send("Tu n'as pas encore de personnage ! Lance `/commencer` pour débuter l'aventure 🏴‍☠️")
        return
    if player["faction"] != "Pirate":
        await interaction.followup.send("⛔ Seuls les Pirates peuvent fonder un équipage.")
        return
    if player["equipage_id"]:
        await interaction.followup.send("⛔ Tu fais déjà partie d'un équipage. Quitte-le d'abord avec `/equipage quitter`.")
        return
    if player["berrys"] < COUT_CREATION:
        await interaction.followup.send(f"⛔ Fonder un équipage coûte **{COUT_CREATION}฿** (tu as {player['berrys']:,}฿).")
        return
    if len(nom) < 3 or len(nom) > 32:
        await interaction.followup.send("⛔ Le nom doit faire entre 3 et 32 caractères.")
        return
    existant = await get_crew_by_nom(interaction.guild_id, nom)
    if existant:
        await interaction.followup.send("⛔ Ce nom est déjà pris sur ce serveur.")
        return

    pool = get_pool()
    async with pool.acquire() as conn:
        async with conn.transaction():
            row = await conn.fetchrow(
                "INSERT INTO crews (guild_id, nom, capitaine_id, type) VALUES ($1, $2, $3, 'Pirate') RETURNING id",
                interaction.guild_id, nom, interaction.user.id
            )
            await conn.execute(
                "UPDATE players SET berrys = berrys - $3, equipage_id = $4, grade_equipage = 'Capitaine' WHERE guild_id=$1 AND user_id=$2",
                interaction.guild_id, interaction.user.id, COUT_CREATION, row["id"]
            )

    embed = discord.Embed(
        title="🏴‍☠️ Équipage fondé !",
        description=f"**{nom}** voit le jour, sous le commandement du Capitaine {interaction.user.mention} !",
        color=0x8E44AD
    )
    embed.set_footer(text="🌊 One Piece Bot • Équipages")
    await interaction.followup.send(embed=embed)


@equipage_group.command(name="inviter", description="Inviter un joueur à rejoindre ton équipage")
@app_commands.describe(membre="Le joueur à inviter")
@require_salon("salon_equipages")
async def equipage_inviter(interaction: discord.Interaction, membre: discord.Member):
    await interaction.response.defer()
    player, crew = await get_joueur_et_equipage(interaction.guild_id, interaction.user.id)
    if crew is None:
        await interaction.followup.send("⛔ Tu ne fais partie d'aucun équipage.")
        return
    if rang_valeur(player["grade_equipage"], RANGS_ORDRE) < rang_valeur("Officier", RANGS_ORDRE):
        await interaction.followup.send("⛔ Il faut être au moins Officier pour inviter quelqu'un.")
        return
    if membre.id == interaction.user.id or membre.bot:
        await interaction.followup.send("Choix invalide 🙃")
        return

    nb_membres = await count_membres(interaction.guild_id, crew["id"])
    if nb_membres >= MAX_MEMBRES:
        await interaction.followup.send(f"⛔ L'équipage est déjà complet ({MAX_MEMBRES}/{MAX_MEMBRES}).")
        return

    cible_data = await get_player(interaction.guild_id, membre.id)
    if cible_data is None:
        await interaction.followup.send(f"{membre.display_name} n'a pas encore de personnage.")
        return
    if cible_data["faction"] != "Pirate":
        await interaction.followup.send(f"⛔ {membre.display_name} n'est pas Pirate.")
        return
    if cible_data["equipage_id"]:
        await interaction.followup.send(f"⛔ {membre.display_name} fait déjà partie d'un équipage.")
        return

    embed = discord.Embed(
        title="🏴‍☠️ Invitation d'équipage !",
        description=f"{interaction.user.mention} t'invite à rejoindre l'équipage **{crew['nom']}** !",
        color=0x8E44AD
    )
    embed.set_footer(text="🌊 One Piece Bot • Équipages • 60 secondes pour répondre")
    view = InvitationView(interaction.guild_id, crew["id"], crew["nom"], membre)
    msg = await interaction.followup.send(content=membre.mention, embed=embed, view=view)
    view.message = msg


class InvitationView(discord.ui.View):
    def __init__(self, guild_id, crew_id, crew_nom, target: discord.Member):
        super().__init__(timeout=60)
        self.guild_id = guild_id
        self.crew_id = crew_id
        self.crew_nom = crew_nom
        self.target = target
        self.repondu = False
        self.message = None

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.target.id:
            await interaction.response.send_message("⛔ Cette invitation ne t'est pas adressée !", ephemeral=True)
            return False
        return True

    @discord.ui.button(label="Rejoindre", emoji="🏴‍☠️", style=discord.ButtonStyle.success)
    async def accepter(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.repondu:
            return
        self.repondu = True
        for c in self.children:
            c.disabled = True

        cible_data = await get_player(self.guild_id, self.target.id)
        crew = await get_crew_by_id(self.guild_id, self.crew_id)
        if not crew:
            await interaction.response.edit_message(content="⛔ Cet équipage n'existe plus.", embed=None, view=None)
            return
        if cible_data["equipage_id"]:
            await interaction.response.edit_message(content="⛔ Tu fais déjà partie d'un équipage.", embed=None, view=None)
            return
        nb_membres = await count_membres(self.guild_id, self.crew_id)
        if nb_membres >= MAX_MEMBRES:
            await interaction.response.edit_message(content="⛔ L'équipage est complet entre-temps.", embed=None, view=None)
            return

        pool = get_pool()
        async with pool.acquire() as conn:
            await conn.execute(
                "UPDATE players SET equipage_id = $3, grade_equipage = 'Membre' WHERE guild_id=$1 AND user_id=$2",
                self.guild_id, self.target.id, self.crew_id
            )
        await interaction.response.edit_message(
            content=None,
            embed=discord.Embed(title="🎉 Bienvenue à bord !", description=f"{self.target.mention} rejoint l'équipage **{self.crew_nom}** !", color=0x27AE60),
            view=None
        )

    @discord.ui.button(label="Refuser", emoji="🚫", style=discord.ButtonStyle.danger)
    async def refuser(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.repondu:
            return
        self.repondu = True
        for c in self.children:
            c.disabled = True
        await interaction.response.edit_message(content="L'invitation a été déclinée.", embed=None, view=None)

    async def on_timeout(self):
        if self.repondu:
            return
        for c in self.children:
            c.disabled = True
        if self.message:
            try:
                await self.message.edit(content="⌛ L'invitation a expiré.", view=self)
            except discord.HTTPException:
                pass


@equipage_group.command(name="expulser", description="Expulser un membre de l'équipage")
@app_commands.describe(membre="Le membre à expulser")
@require_salon("salon_equipages")
async def equipage_expulser(interaction: discord.Interaction, membre: discord.Member):
    await interaction.response.defer()
    player, crew = await get_joueur_et_equipage(interaction.guild_id, interaction.user.id)
    if crew is None:
        await interaction.followup.send("⛔ Tu ne fais partie d'aucun équipage.")
        return
    if rang_valeur(player["grade_equipage"], RANGS_ORDRE) < rang_valeur("Officier", RANGS_ORDRE):
        await interaction.followup.send("⛔ Il faut être au moins Officier pour expulser quelqu'un.")
        return
    if membre.id == interaction.user.id:
        await interaction.followup.send("Utilise `/equipage quitter` pour partir toi-même.")
        return

    cible_data = await get_player(interaction.guild_id, membre.id)
    if not cible_data or cible_data["equipage_id"] != crew["id"]:
        await interaction.followup.send(f"{membre.display_name} ne fait pas partie de ton équipage.")
        return
    if rang_valeur(cible_data["grade_equipage"], RANGS_ORDRE) >= rang_valeur(player["grade_equipage"], RANGS_ORDRE):
        await interaction.followup.send("⛔ Tu ne peux pas expulser un membre de rang égal ou supérieur au tien.")
        return

    pool = get_pool()
    async with pool.acquire() as conn:
        await conn.execute(
            "UPDATE players SET equipage_id = NULL, grade_equipage = NULL WHERE guild_id=$1 AND user_id=$2",
            interaction.guild_id, membre.id
        )
    await interaction.followup.send(f"✅ {membre.mention} a été expulsé de **{crew['nom']}**.")


@equipage_group.command(name="quitter", description="Quitter ton équipage")
@require_salon("salon_equipages")
async def equipage_quitter(interaction: discord.Interaction):
    await interaction.response.defer()
    player, crew = await get_joueur_et_equipage(interaction.guild_id, interaction.user.id)
    if crew is None:
        await interaction.followup.send("⛔ Tu ne fais partie d'aucun équipage.")
        return
    if player["grade_equipage"] == "Capitaine":
        await interaction.followup.send("⛔ Le Capitaine ne peut pas quitter directement. Transfère le capitanat ou dissous l'équipage.")
        return

    pool = get_pool()
    async with pool.acquire() as conn:
        await conn.execute(
            "UPDATE players SET equipage_id = NULL, grade_equipage = NULL WHERE guild_id=$1 AND user_id=$2",
            interaction.guild_id, interaction.user.id
        )
    await interaction.followup.send(f"👋 Tu as quitté **{crew['nom']}**.")


PROMOTION_CHOICES = [
    app_commands.Choice(name="Membre", value="Membre"),
    app_commands.Choice(name="Officier", value="Officier"),
    app_commands.Choice(name="Second", value="Second"),
]

@equipage_group.command(name="promouvoir", description="Changer le rang d'un membre (réservé au Capitaine)")
@app_commands.describe(membre="Le membre concerné", rang="Le nouveau rang")
@app_commands.choices(rang=PROMOTION_CHOICES)
@require_salon("salon_equipages")
async def equipage_promouvoir(interaction: discord.Interaction, membre: discord.Member, rang: app_commands.Choice[str]):
    await interaction.response.defer()
    player, crew = await get_joueur_et_equipage(interaction.guild_id, interaction.user.id)
    if crew is None or player["grade_equipage"] != "Capitaine":
        await interaction.followup.send("⛔ Seul le Capitaine peut changer les rangs.")
        return

    cible_data = await get_player(interaction.guild_id, membre.id)
    if not cible_data or cible_data["equipage_id"] != crew["id"]:
        await interaction.followup.send(f"{membre.display_name} ne fait pas partie de ton équipage.")
        return

    pool = get_pool()
    async with pool.acquire() as conn:
        await conn.execute(
            "UPDATE players SET grade_equipage = $3 WHERE guild_id=$1 AND user_id=$2",
            interaction.guild_id, membre.id, rang.value
        )
    await interaction.followup.send(f"✅ {membre.mention} est maintenant **{rang.value}** {RANG_EMOJIS[rang.value]}")


@equipage_group.command(name="transferer_capitainat", description="Transférer le capitanat à un autre membre")
@app_commands.describe(nouveau_capitaine="Le membre qui deviendra Capitaine")
@require_salon("salon_equipages")
async def equipage_transferer(interaction: discord.Interaction, nouveau_capitaine: discord.Member):
    await interaction.response.defer()
    player, crew = await get_joueur_et_equipage(interaction.guild_id, interaction.user.id)
    if crew is None or player["grade_equipage"] != "Capitaine":
        await interaction.followup.send("⛔ Seul le Capitaine peut transférer le commandement.")
        return
    if nouveau_capitaine.id == interaction.user.id:
        await interaction.followup.send("Tu es déjà Capitaine 🙃")
        return

    cible_data = await get_player(interaction.guild_id, nouveau_capitaine.id)
    if not cible_data or cible_data["equipage_id"] != crew["id"]:
        await interaction.followup.send(f"{nouveau_capitaine.display_name} ne fait pas partie de ton équipage.")
        return

    pool = get_pool()
    async with pool.acquire() as conn:
        async with conn.transaction():
            await conn.execute("UPDATE crews SET capitaine_id = $2 WHERE id = $1", crew["id"], nouveau_capitaine.id)
            await conn.execute("UPDATE players SET grade_equipage = 'Second' WHERE guild_id=$1 AND user_id=$2", interaction.guild_id, interaction.user.id)
            await conn.execute("UPDATE players SET grade_equipage = 'Capitaine' WHERE guild_id=$1 AND user_id=$2", interaction.guild_id, nouveau_capitaine.id)
    await interaction.followup.send(f"🏴‍☠️ {nouveau_capitaine.mention} est le nouveau Capitaine de **{crew['nom']}** !")


@equipage_group.command(name="dissoudre", description="Dissoudre définitivement ton équipage (réservé au Capitaine)")
@require_salon("salon_equipages")
async def equipage_dissoudre(interaction: discord.Interaction):
    await interaction.response.defer()
    player, crew = await get_joueur_et_equipage(interaction.guild_id, interaction.user.id)
    if crew is None or player["grade_equipage"] != "Capitaine":
        await interaction.followup.send("⛔ Seul le Capitaine peut dissoudre l'équipage.")
        return

    view = DissolutionConfirmView(interaction.guild_id, crew["id"], crew["nom"], interaction.user.id)
    await interaction.followup.send(
        embed=discord.Embed(title="⚠️ Confirmation requise", description=f"Es-tu sûr de vouloir dissoudre **{crew['nom']}** ?", color=0xC0392B),
        view=view
    )


class DissolutionConfirmView(discord.ui.View):
    def __init__(self, guild_id, crew_id, crew_nom, capitaine_id):
        super().__init__(timeout=30)
        self.guild_id = guild_id
        self.crew_id = crew_id
        self.crew_nom = crew_nom
        self.capitaine_id = capitaine_id

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.capitaine_id:
            await interaction.response.send_message("⛔ Seul le Capitaine peut confirmer.", ephemeral=True)
            return False
        return True

    @discord.ui.button(label="Confirmer la dissolution", emoji="💥", style=discord.ButtonStyle.danger)
    async def confirmer(self, interaction: discord.Interaction, button: discord.ui.Button):
        pool = get_pool()
        async with pool.acquire() as conn:
            async with conn.transaction():
                await conn.execute("UPDATE players SET equipage_id = NULL, grade_equipage = NULL WHERE guild_id=$1 AND equipage_id=$2", self.guild_id, self.crew_id)
                await conn.execute("DELETE FROM crews WHERE id = $1", self.crew_id)
        for c in self.children:
            c.disabled = True
        await interaction.response.edit_message(content=f"💥 **{self.crew_nom}** a été dissous.", embed=None, view=self)

    @discord.ui.button(label="Annuler", style=discord.ButtonStyle.secondary)
    async def annuler(self, interaction: discord.Interaction, button: discord.ui.Button):
        for c in self.children:
            c.disabled = True
        await interaction.response.edit_message(content="Dissolution annulée.", embed=None, view=self)


@equipage_group.command(name="renommer", description="Renommer ton équipage (réservé au Capitaine)")
@app_commands.describe(nouveau_nom="Le nouveau nom")
@require_salon("salon_equipages")
async def equipage_renommer(interaction: discord.Interaction, nouveau_nom: str):
    await interaction.response.defer()
    player, crew = await get_joueur_et_equipage(interaction.guild_id, interaction.user.id)
    if crew is None or player["grade_equipage"] != "Capitaine":
        await interaction.followup.send("⛔ Seul le Capitaine peut renommer l'équipage.")
        return
    if len(nouveau_nom) < 3 or len(nouveau_nom) > 32:
        await interaction.followup.send("⛔ Le nom doit faire entre 3 et 32 caractères.")
        return
    existant = await get_crew_by_nom(interaction.guild_id, nouveau_nom)
    if existant:
        await interaction.followup.send("⛔ Ce nom est déjà pris.")
        return

    pool = get_pool()
    async with pool.acquire() as conn:
        await conn.execute("UPDATE crews SET nom = $2 WHERE id = $1", crew["id"], nouveau_nom)
    await interaction.followup.send(f"✅ L'équipage s'appelle maintenant **{nouveau_nom}** !")


@equipage_group.command(name="drapeau", description="Définir le drapeau de ton équipage (réservé au Capitaine)")
@app_commands.describe(image="L'image du drapeau")
@require_salon("salon_equipages")
async def equipage_drapeau(interaction: discord.Interaction, image: discord.Attachment):
    await interaction.response.defer()
    player, crew = await get_joueur_et_equipage(interaction.guild_id, interaction.user.id)
    if crew is None or player["grade_equipage"] != "Capitaine":
        await interaction.followup.send("⛔ Seul le Capitaine peut définir le drapeau.")
        return

    pool = get_pool()
    async with pool.acquire() as conn:
        await conn.execute("UPDATE crews SET drapeau_url = $2 WHERE id = $1", crew["id"], image.url)
    embed = discord.Embed(title="🏴‍☠️ Nouveau drapeau !", description=f"Le drapeau de **{crew['nom']}** a été mis à jour.", color=0x8E44AD)
    embed.set_image(url=image.url)
    await interaction.followup.send(embed=embed)


coffre_group = app_commands.Group(name="coffre", description="Gérer le coffre commun de l'équipage", parent=equipage_group)

@coffre_group.command(name="depot", description="Déposer des Berrys dans le coffre commun")
@app_commands.describe(montant="Le montant à déposer")
@require_salon("salon_equipages")
async def coffre_depot(interaction: discord.Interaction, montant: int):
    await interaction.response.defer()
    player, crew = await get_joueur_et_equipage(interaction.guild_id, interaction.user.id)
    if crew is None:
        await interaction.followup.send("⛔ Tu ne fais partie d'aucun équipage.")
        return
    if montant <= 0:
        await interaction.followup.send("Le montant doit être positif 🙃")
        return
    if montant > player["berrys"]:
        await interaction.followup.send(f"Tu n'as que **{player['berrys']:,}฿** en liquide.")
        return

    pool = get_pool()
    async with pool.acquire() as conn:
        async with conn.transaction():
            await conn.execute("UPDATE players SET berrys = berrys - $3 WHERE guild_id=$1 AND user_id=$2", interaction.guild_id, interaction.user.id, montant)
            await conn.execute("UPDATE crews SET coffre_berrys = coffre_berrys + $2 WHERE id = $1", crew["id"], montant)
    await interaction.followup.send(f"🏦 **{montant:,}฿** déposés dans le coffre de **{crew['nom']}**.")


@coffre_group.command(name="retrait", description="Retirer des Berrys du coffre commun (Second et Capitaine uniquement)")
@app_commands.describe(montant="Le montant à retirer")
@require_salon("salon_equipages")
async def coffre_retrait(interaction: discord.Interaction, montant: int):
    await interaction.response.defer()
    player, crew = await get_joueur_et_equipage(interaction.guild_id, interaction.user.id)
    if crew is None:
        await interaction.followup.send("⛔ Tu ne fais partie d'aucun équipage.")
        return
    if rang_valeur(player["grade_equipage"], RANGS_ORDRE) < rang_valeur("Second", RANGS_ORDRE):
        await interaction.followup.send("⛔ Il faut être Second ou Capitaine pour retirer du coffre.")
        return
    if montant <= 0:
        await interaction.followup.send("Le montant doit être positif 🙃")
        return
    if montant > crew["coffre_berrys"]:
        await interaction.followup.send(f"Le coffre ne contient que **{crew['coffre_berrys']:,}฿**.")
        return

    pool = get_pool()
    async with pool.acquire() as conn:
        async with conn.transaction():
            await conn.execute("UPDATE crews SET coffre_berrys = coffre_berrys - $2 WHERE id = $1", crew["id"], montant)
            await conn.execute("UPDATE players SET berrys = berrys + $3 WHERE guild_id=$1 AND user_id=$2", interaction.guild_id, interaction.user.id, montant)
    await interaction.followup.send(f"🏦 **{montant:,}฿** retirés du coffre commun.")


@coffre_group.command(name="solde", description="Voir le solde du coffre commun")
@require_salon("salon_equipages")
async def coffre_solde(interaction: discord.Interaction):
    await interaction.response.defer()
    player, crew = await get_joueur_et_equipage(interaction.guild_id, interaction.user.id)
    if crew is None:
        await interaction.followup.send("⛔ Tu ne fais partie d'aucun équipage.")
        return
    await interaction.followup.send(f"🏦 Le coffre de **{crew['nom']}** contient **{crew['coffre_berrys']:,}฿**.")


@equipage_group.command(name="info", description="Voir les informations d'un équipage")
@app_commands.describe(membre="Un membre de l'équipage à consulter (le tien par défaut)")
@require_salon("salon_equipages")
async def equipage_info(interaction: discord.Interaction, membre: discord.Member = None):
    await interaction.response.defer()
    cible = membre or interaction.user
    _, crew = await get_joueur_et_equipage(interaction.guild_id, cible.id)
    if crew is None:
        msg = "Tu ne fais partie d'aucun équipage." if cible == interaction.user else f"{cible.display_name} ne fait partie d'aucun équipage."
        await interaction.followup.send(msg)
        return

    membres = await get_membres(interaction.guild_id, crew["id"])
    prime_totale = await prime_cumulee(interaction.guild_id, crew["id"])

    embed = discord.Embed(title=f"🏴‍☠️ {crew['nom']}", color=0x8E44AD)
    if crew["drapeau_url"]:
        embed.set_thumbnail(url=crew["drapeau_url"])
    embed.add_field(name="Capitaine", value=f"<@{crew['capitaine_id']}>", inline=True)
    embed.add_field(name="Effectif", value=f"{len(membres)}/{MAX_MEMBRES}", inline=True)
    embed.add_field(name="Prime cumulée", value=f"☠️ {prime_totale:,}฿", inline=True)
    embed.add_field(name="Coffre commun", value=f"🏦 {crew['coffre_berrys']:,}฿", inline=True)

    grouped = {}
    for m in membres:
        grouped.setdefault(m["grade_equipage"], []).append(f"<@{m['user_id']}>")
    for rang in reversed(RANGS_ORDRE):
        if rang in grouped:
            embed.add_field(name=f"{RANG_EMOJIS[rang]} {rang}", value="\n".join(grouped[rang]), inline=False)

    embed.set_footer(text="🌊 One Piece Bot • Équipages")
    await interaction.followup.send(embed=embed)


@equipage_group.command(name="liste", description="Voir la liste des équipages du serveur")
@require_salon("salon_equipages")
async def equipage_liste(interaction: discord.Interaction):
    await interaction.response.defer()
    pool = get_pool()
    async with pool.acquire() as conn:
        crews = await conn.fetch("SELECT * FROM crews WHERE guild_id = $1 AND type = 'Pirate'", interaction.guild_id)

    if not crews:
        await interaction.followup.send("Aucun équipage n'a encore été fondé sur ce serveur.")
        return

    lignes = []
    for c in crews:
        nb = await count_membres(interaction.guild_id, c["id"])
        prime = await prime_cumulee(interaction.guild_id, c["id"])
        lignes.append((c["nom"], nb, prime))
    lignes.sort(key=lambda x: x[2], reverse=True)

    embed = discord.Embed(title="🏴‍☠️ Équipages du serveur", color=0x8E44AD)
    texte = "\n".join(f"**{i+1}. {nom}** — {nb}/{MAX_MEMBRES} membres — ☠️ {prime:,}฿" for i, (nom, nb, prime) in enumerate(lignes))
    embed.description = texte
    embed.set_footer(text="🌊 One Piece Bot • Équipages")
    await interaction.followup.send(embed=embed)


def setup_equipage_commands(bot):
    bot.tree.add_command(equipage_group)
