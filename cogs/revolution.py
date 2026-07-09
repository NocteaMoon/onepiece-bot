import discord
from discord import app_commands
from database.db import get_pool
from utils.players import get_player
from utils.channel_check import require_salon
from utils.equipages import rang_valeur, get_crew_by_id, get_crew_by_nom, get_membres, count_membres, prime_cumulee

RANGS_ORDRE = ["Recrue", "Agent", "Commandant", "Meneur"]
RANG_EMOJIS = {"Meneur": "🔥", "Commandant": "🗡️", "Agent": "🕶️", "Recrue": "🧭"}
MAX_MEMBRES = 10
COUT_CREATION = 200

revolution_group = app_commands.Group(name="revolution", description="Gérer ta cellule révolutionnaire")


async def get_joueur_et_cellule(guild_id, user_id):
    player = await get_player(guild_id, user_id)
    if player is None or not player["equipage_id"]:
        return player, None
    crew = await get_crew_by_id(guild_id, player["equipage_id"])
    return player, crew


@revolution_group.command(name="creer", description="Fonder une cellule révolutionnaire (réservé aux Révolutionnaires)")
@app_commands.describe(nom="Le nom de ta cellule")
@require_salon("salon_revolutionnaires")
async def revolution_creer(interaction: discord.Interaction, nom: str):
    await interaction.response.defer()
    player = await get_player(interaction.guild_id, interaction.user.id)
    if player is None:
        await interaction.followup.send("Tu n'as pas encore de personnage ! Lance `/commencer` pour débuter l'aventure 🏴‍☠️")
        return
    if player["faction"] != "Révolutionnaire":
        await interaction.followup.send("⛔ Seuls les Révolutionnaires peuvent fonder une cellule.")
        return
    if player["equipage_id"]:
        await interaction.followup.send("⛔ Tu fais déjà partie d'une cellule. Quitte-la d'abord avec `/revolution quitter`.")
        return
    if player["berrys"] < COUT_CREATION:
        await interaction.followup.send(f"⛔ Fonder une cellule coûte **{COUT_CREATION}฿** (tu as {player['berrys']:,}฿).")
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
                "INSERT INTO crews (guild_id, nom, capitaine_id, type) VALUES ($1, $2, $3, 'Revolution') RETURNING id",
                interaction.guild_id, nom, interaction.user.id
            )
            await conn.execute(
                "UPDATE players SET berrys = berrys - $3, equipage_id = $4, grade_equipage = 'Meneur' WHERE guild_id=$1 AND user_id=$2",
                interaction.guild_id, interaction.user.id, COUT_CREATION, row["id"]
            )

    embed = discord.Embed(
        title="🔥 Cellule fondée !",
        description=f"La cellule **{nom}** entre dans l'ombre, menée par {interaction.user.mention} !",
        color=0xC0392B
    )
    embed.set_footer(text="🌊 One Piece Bot • Révolution")
    await interaction.followup.send(embed=embed)


@revolution_group.command(name="inviter", description="Inviter un joueur à rejoindre ta cellule")
@app_commands.describe(membre="Le joueur à inviter")
@require_salon("salon_revolutionnaires")
async def revolution_inviter(interaction: discord.Interaction, membre: discord.Member):
    await interaction.response.defer()
    player, crew = await get_joueur_et_cellule(interaction.guild_id, interaction.user.id)
    if crew is None:
        await interaction.followup.send("⛔ Tu ne fais partie d'aucune cellule.")
        return
    if rang_valeur(player["grade_equipage"], RANGS_ORDRE) < rang_valeur("Agent", RANGS_ORDRE):
        await interaction.followup.send("⛔ Il faut être au moins Agent pour inviter quelqu'un.")
        return
    if membre.id == interaction.user.id or membre.bot:
        await interaction.followup.send("Choix invalide 🙃")
        return

    nb_membres = await count_membres(interaction.guild_id, crew["id"])
    if nb_membres >= MAX_MEMBRES:
        await interaction.followup.send(f"⛔ La cellule est déjà complète ({MAX_MEMBRES}/{MAX_MEMBRES}).")
        return

    cible_data = await get_player(interaction.guild_id, membre.id)
    if cible_data is None:
        await interaction.followup.send(f"{membre.display_name} n'a pas encore de personnage.")
        return
    if cible_data["faction"] != "Révolutionnaire":
        await interaction.followup.send(f"⛔ {membre.display_name} n'est pas Révolutionnaire.")
        return
    if cible_data["equipage_id"]:
        await interaction.followup.send(f"⛔ {membre.display_name} fait déjà partie d'une cellule.")
        return

    embed = discord.Embed(
        title="🔥 Invitation de cellule !",
        description=f"{interaction.user.mention} t'invite à rejoindre la cellule **{crew['nom']}** !",
        color=0xC0392B
    )
    embed.set_footer(text="🌊 One Piece Bot • Révolution • 60 secondes pour répondre")
    view = InvitationRevolutionView(interaction.guild_id, crew["id"], crew["nom"], membre)
    msg = await interaction.followup.send(content=membre.mention, embed=embed, view=view)
    view.message = msg


class InvitationRevolutionView(discord.ui.View):
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

    @discord.ui.button(label="Rejoindre", emoji="🔥", style=discord.ButtonStyle.success)
    async def accepter(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.repondu:
            return
        self.repondu = True
        for c in self.children:
            c.disabled = True

        cible_data = await get_player(self.guild_id, self.target.id)
        crew = await get_crew_by_id(self.guild_id, self.crew_id)
        if not crew:
            await interaction.response.edit_message(content="⛔ Cette cellule n'existe plus.", embed=None, view=None)
            return
        if cible_data["equipage_id"]:
            await interaction.response.edit_message(content="⛔ Tu fais déjà partie d'une cellule.", embed=None, view=None)
            return
        nb_membres = await count_membres(self.guild_id, self.crew_id)
        if nb_membres >= MAX_MEMBRES:
            await interaction.response.edit_message(content="⛔ La cellule est complète entre-temps.", embed=None, view=None)
            return

        pool = get_pool()
        async with pool.acquire() as conn:
            await conn.execute(
                "UPDATE players SET equipage_id = $3, grade_equipage = 'Recrue' WHERE guild_id=$1 AND user_id=$2",
                self.guild_id, self.target.id, self.crew_id
            )
        await interaction.response.edit_message(
            content=None,
            embed=discord.Embed(title="🎉 Bienvenue dans l'ombre !", description=f"{self.target.mention} rejoint la cellule **{self.crew_nom}** !", color=0x27AE60),
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


@revolution_group.command(name="expulser", description="Expulser un membre de la cellule")
@app_commands.describe(membre="Le membre à expulser")
@require_salon("salon_revolutionnaires")
async def revolution_expulser(interaction: discord.Interaction, membre: discord.Member):
    await interaction.response.defer()
    player, crew = await get_joueur_et_cellule(interaction.guild_id, interaction.user.id)
    if crew is None:
        await interaction.followup.send("⛔ Tu ne fais partie d'aucune cellule.")
        return
    if rang_valeur(player["grade_equipage"], RANGS_ORDRE) < rang_valeur("Agent", RANGS_ORDRE):
        await interaction.followup.send("⛔ Il faut être au moins Agent pour expulser quelqu'un.")
        return
    if membre.id == interaction.user.id:
        await interaction.followup.send("Utilise `/revolution quitter` pour partir toi-même.")
        return

    cible_data = await get_player(interaction.guild_id, membre.id)
    if not cible_data or cible_data["equipage_id"] != crew["id"]:
        await interaction.followup.send(f"{membre.display_name} ne fait pas partie de ta cellule.")
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


@revolution_group.command(name="quitter", description="Quitter ta cellule")
@require_salon("salon_revolutionnaires")
async def revolution_quitter(interaction: discord.Interaction):
    await interaction.response.defer()
    player, crew = await get_joueur_et_cellule(interaction.guild_id, interaction.user.id)
    if crew is None:
        await interaction.followup.send("⛔ Tu ne fais partie d'aucune cellule.")
        return
    if player["grade_equipage"] == "Meneur":
        await interaction.followup.send("⛔ Le Meneur ne peut pas quitter directement. Transfère la direction ou dissous la cellule.")
        return

    pool = get_pool()
    async with pool.acquire() as conn:
        await conn.execute(
            "UPDATE players SET equipage_id = NULL, grade_equipage = NULL WHERE guild_id=$1 AND user_id=$2",
            interaction.guild_id, interaction.user.id
        )
    await interaction.followup.send(f"👋 Tu as quitté **{crew['nom']}**.")


PROMOTION_CHOICES = [
    app_commands.Choice(name="Recrue", value="Recrue"),
    app_commands.Choice(name="Agent", value="Agent"),
    app_commands.Choice(name="Commandant", value="Commandant"),
]

@revolution_group.command(name="promouvoir", description="Changer le rang d'un membre (réservé au Meneur)")
@app_commands.describe(membre="Le membre concerné", rang="Le nouveau rang")
@app_commands.choices(rang=PROMOTION_CHOICES)
@require_salon("salon_revolutionnaires")
async def revolution_promouvoir(interaction: discord.Interaction, membre: discord.Member, rang: app_commands.Choice[str]):
    await interaction.response.defer()
    player, crew = await get_joueur_et_cellule(interaction.guild_id, interaction.user.id)
    if crew is None or player["grade_equipage"] != "Meneur":
        await interaction.followup.send("⛔ Seul le Meneur peut changer les rangs.")
        return

    cible_data = await get_player(interaction.guild_id, membre.id)
    if not cible_data or cible_data["equipage_id"] != crew["id"]:
        await interaction.followup.send(f"{membre.display_name} ne fait pas partie de ta cellule.")
        return

    pool = get_pool()
    async with pool.acquire() as conn:
        await conn.execute(
            "UPDATE players SET grade_equipage = $3 WHERE guild_id=$1 AND user_id=$2",
            interaction.guild_id, membre.id, rang.value
        )
    await interaction.followup.send(f"✅ {membre.mention} est maintenant **{rang.value}** {RANG_EMOJIS[rang.value]}")


@revolution_group.command(name="transferer_direction", description="Transférer la direction à un autre membre")
@app_commands.describe(nouveau_meneur="Le membre qui deviendra Meneur")
@require_salon("salon_revolutionnaires")
async def revolution_transferer(interaction: discord.Interaction, nouveau_meneur: discord.Member):
    await interaction.response.defer()
    player, crew = await get_joueur_et_cellule(interaction.guild_id, interaction.user.id)
    if crew is None or player["grade_equipage"] != "Meneur":
        await interaction.followup.send("⛔ Seul le Meneur peut transférer la direction.")
        return
    if nouveau_meneur.id == interaction.user.id:
        await interaction.followup.send("Tu es déjà Meneur 🙃")
        return

    cible_data = await get_player(interaction.guild_id, nouveau_meneur.id)
    if not cible_data or cible_data["equipage_id"] != crew["id"]:
        await interaction.followup.send(f"{nouveau_meneur.display_name} ne fait pas partie de ta cellule.")
        return

    pool = get_pool()
    async with pool.acquire() as conn:
        async with conn.transaction():
            await conn.execute("UPDATE crews SET capitaine_id = $2 WHERE id = $1", crew["id"], nouveau_meneur.id)
            await conn.execute("UPDATE players SET grade_equipage = 'Commandant' WHERE guild_id=$1 AND user_id=$2", interaction.guild_id, interaction.user.id)
            await conn.execute("UPDATE players SET grade_equipage = 'Meneur' WHERE guild_id=$1 AND user_id=$2", interaction.guild_id, nouveau_meneur.id)
    await interaction.followup.send(f"🔥 {nouveau_meneur.mention} est le nouveau Meneur de **{crew['nom']}** !")


@revolution_group.command(name="dissoudre", description="Dissoudre définitivement ta cellule (réservé au Meneur)")
@require_salon("salon_revolutionnaires")
async def revolution_dissoudre(interaction: discord.Interaction):
    await interaction.response.defer()
    player, crew = await get_joueur_et_cellule(interaction.guild_id, interaction.user.id)
    if crew is None or player["grade_equipage"] != "Meneur":
        await interaction.followup.send("⛔ Seul le Meneur peut dissoudre la cellule.")
        return

    view = DissolutionRevolutionView(interaction.guild_id, crew["id"], crew["nom"], interaction.user.id)
    await interaction.followup.send(
        embed=discord.Embed(title="⚠️ Confirmation requise", description=f"Es-tu sûr de vouloir dissoudre **{crew['nom']}** ?", color=0xC0392B),
        view=view
    )


class DissolutionRevolutionView(discord.ui.View):
    def __init__(self, guild_id, crew_id, crew_nom, meneur_id):
        super().__init__(timeout=30)
        self.guild_id = guild_id
        self.crew_id = crew_id
        self.crew_nom = crew_nom
        self.meneur_id = meneur_id

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.meneur_id:
            await interaction.response.send_message("⛔ Seul le Meneur peut confirmer.", ephemeral=True)
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
        await interaction.response.edit_message(content=f"💥 **{self.crew_nom}** a été dissoute.", embed=None, view=self)

    @discord.ui.button(label="Annuler", style=discord.ButtonStyle.secondary)
    async def annuler(self, interaction: discord.Interaction, button: discord.ui.Button):
        for c in self.children:
            c.disabled = True
        await interaction.response.edit_message(content="Dissolution annulée.", embed=None, view=self)


@revolution_group.command(name="renommer", description="Renommer ta cellule (réservé au Meneur)")
@app_commands.describe(nouveau_nom="Le nouveau nom")
@require_salon("salon_revolutionnaires")
async def revolution_renommer(interaction: discord.Interaction, nouveau_nom: str):
    await interaction.response.defer()
    player, crew = await get_joueur_et_cellule(interaction.guild_id, interaction.user.id)
    if crew is None or player["grade_equipage"] != "Meneur":
        await interaction.followup.send("⛔ Seul le Meneur peut renommer la cellule.")
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
    await interaction.followup.send(f"✅ La cellule s'appelle maintenant **{nouveau_nom}** !")


@revolution_group.command(name="symbole", description="Définir le symbole de ta cellule (réservé au Meneur)")
@app_commands.describe(image="L'image du symbole")
@require_salon("salon_revolutionnaires")
async def revolution_symbole(interaction: discord.Interaction, image: discord.Attachment):
    await interaction.response.defer()
    player, crew = await get_joueur_et_cellule(interaction.guild_id, interaction.user.id)
    if crew is None or player["grade_equipage"] != "Meneur":
        await interaction.followup.send("⛔ Seul le Meneur peut définir le symbole.")
        return

    pool = get_pool()
    async with pool.acquire() as conn:
        await conn.execute("UPDATE crews SET drapeau_url = $2 WHERE id = $1", crew["id"], image.url)
    embed = discord.Embed(title="🔥 Nouveau symbole !", description=f"Le symbole de **{crew['nom']}** a été mis à jour.", color=0xC0392B)
    embed.set_image(url=image.url)
    await interaction.followup.send(embed=embed)


coffre_revolution_group = app_commands.Group(name="coffre", description="Gérer le coffre commun de la cellule", parent=revolution_group)

@coffre_revolution_group.command(name="depot", description="Déposer des Berrys dans le coffre commun")
@app_commands.describe(montant="Le montant à déposer")
@require_salon("salon_revolutionnaires")
async def coffre_revolution_depot(interaction: discord.Interaction, montant: int):
    await interaction.response.defer()
    player, crew = await get_joueur_et_cellule(interaction.guild_id, interaction.user.id)
    if crew is None:
        await interaction.followup.send("⛔ Tu ne fais partie d'aucune cellule.")
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


@coffre_revolution_group.command(name="retrait", description="Retirer des Berrys du coffre commun (Commandant et Meneur uniquement)")
@app_commands.describe(montant="Le montant à retirer")
@require_salon("salon_revolutionnaires")
async def coffre_revolution_retrait(interaction: discord.Interaction, montant: int):
    await interaction.response.defer()
    player, crew = await get_joueur_et_cellule(interaction.guild_id, interaction.user.id)
    if crew is None:
        await interaction.followup.send("⛔ Tu ne fais partie d'aucune cellule.")
        return
    if rang_valeur(player["grade_equipage"], RANGS_ORDRE) < rang_valeur("Commandant", RANGS_ORDRE):
        await interaction.followup.send("⛔ Il faut être Commandant ou Meneur pour retirer du coffre.")
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


@coffre_revolution_group.command(name="solde", description="Voir le solde du coffre commun")
@require_salon("salon_revolutionnaires")
async def coffre_revolution_solde(interaction: discord.Interaction):
    await interaction.response.defer()
    player, crew = await get_joueur_et_cellule(interaction.guild_id, interaction.user.id)
    if crew is None:
        await interaction.followup.send("⛔ Tu ne fais partie d'aucune cellule.")
        return
    await interaction.followup.send(f"🏦 Le coffre de **{crew['nom']}** contient **{crew['coffre_berrys']:,}฿**.")


@revolution_group.command(name="info", description="Voir les informations d'une cellule")
@app_commands.describe(membre="Un membre de la cellule à consulter (le tien par défaut)")
@require_salon("salon_revolutionnaires")
async def revolution_info(interaction: discord.Interaction, membre: discord.Member = None):
    await interaction.response.defer()
    cible = membre or interaction.user
    _, crew = await get_joueur_et_cellule(interaction.guild_id, cible.id)
    if crew is None:
        msg = "Tu ne fais partie d'aucune cellule." if cible == interaction.user else f"{cible.display_name} ne fait partie d'aucune cellule."
        await interaction.followup.send(msg)
        return

    membres = await get_membres(interaction.guild_id, crew["id"])
    prime_totale = await prime_cumulee(interaction.guild_id, crew["id"])

    embed = discord.Embed(title=f"🔥 {crew['nom']}", color=0xC0392B)
    if crew["drapeau_url"]:
        embed.set_thumbnail(url=crew["drapeau_url"])
    embed.add_field(name="Meneur", value=f"<@{crew['capitaine_id']}>", inline=True)
    embed.add_field(name="Effectif", value=f"{len(membres)}/{MAX_MEMBRES}", inline=True)
    embed.add_field(name="Prime cumulée", value=f"☠️ {prime_totale:,}฿", inline=True)
    embed.add_field(name="Coffre commun", value=f"🏦 {crew['coffre_berrys']:,}฿", inline=True)

    grouped = {}
    for m in membres:
        grouped.setdefault(m["grade_equipage"], []).append(f"<@{m['user_id']}>")
    for rang in reversed(RANGS_ORDRE):
        if rang in grouped:
            embed.add_field(name=f"{RANG_EMOJIS[rang]} {rang}", value="\n".join(grouped[rang]), inline=False)

    embed.set_footer(text="🌊 One Piece Bot • Révolution")
    await interaction.followup.send(embed=embed)


@revolution_group.command(name="liste", description="Voir la liste des cellules révolutionnaires")
@require_salon("salon_revolutionnaires")
async def revolution_liste(interaction: discord.Interaction):
    await interaction.response.defer()
    pool = get_pool()
    async with pool.acquire() as conn:
        crews = await conn.fetch("SELECT * FROM crews WHERE guild_id = $1 AND type = 'Revolution'", interaction.guild_id)

    if not crews:
        await interaction.followup.send("Aucune cellule n'a encore été fondée sur ce serveur.")
        return

    lignes = []
    for c in crews:
        nb = await count_membres(interaction.guild_id, c["id"])
        prime = await prime_cumulee(interaction.guild_id, c["id"])
        lignes.append((c["nom"], nb, prime))
    lignes.sort(key=lambda x: x[2], reverse=True)

    embed = discord.Embed(title="🔥 Cellules révolutionnaires", color=0xC0392B)
    texte = "\n".join(f"**{i+1}. {nom}** — {nb}/{MAX_MEMBRES} membres — ☠️ {prime:,}฿" for i, (nom, nb, prime) in enumerate(lignes))
    embed.description = texte
    embed.set_footer(text="🌊 One Piece Bot • Révolution")
    await interaction.followup.send(embed=embed)


def setup_revolution_commands(bot):
    bot.tree.add_command(revolution_group)
