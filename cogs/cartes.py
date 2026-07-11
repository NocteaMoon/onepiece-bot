import discord
from discord import app_commands
from database.db import get_pool
from utils.players import get_player
from utils.channel_check import require_salon
from utils.cartes import (
    CATEGORIES, PAQUETS, RARETE_EMOJIS, RARETE_VENTE,
    get_all_cards, get_card, tirer_paquet, add_card, remove_card, get_owned,
    get_collection_status, get_overview, check_completion_claimable, claim_completion,
    is_echange_ouvert,
)

cartes_group = app_commands.Group(name="cartes", description="Le jeu de cartes à collectionner")

PAQUET_CHOICES = [app_commands.Choice(name=cfg["nom"], value=cle) for cle, cfg in PAQUETS.items()]


@cartes_group.command(name="ouvrir", description="Acheter et ouvrir un paquet de cartes")
@app_commands.describe(paquet="Le type de paquet à ouvrir")
@app_commands.choices(paquet=PAQUET_CHOICES)
@require_salon("salon_cartes")
async def cartes_ouvrir(interaction: discord.Interaction, paquet: app_commands.Choice[str]):
    await interaction.response.defer()
    player = await get_player(interaction.guild_id, interaction.user.id)
    if player is None:
        await interaction.followup.send("Tu n'as pas encore de personnage ! Lance `/commencer` pour débuter l'aventure 🏴‍☠️")
        return

    config = PAQUETS[paquet.value]
    if player["berrys"] < config["prix"]:
        await interaction.followup.send(f"⛔ **{config['nom']}** coûte **{config['prix']:,}฿**, tu n'as que {player['berrys']:,}฿.")
        return

    cartes_tirees = tirer_paquet(paquet.value)

    pool = get_pool()
    async with pool.acquire() as conn:
        await conn.execute(
            "UPDATE players SET berrys = berrys - $3 WHERE guild_id=$1 AND user_id=$2",
            interaction.guild_id, interaction.user.id, config["prix"]
        )

    lignes = []
    for carte in cartes_tirees:
        est_nouvelle = await add_card(interaction.guild_id, interaction.user.id, carte["code"])
        emoji = RARETE_EMOJIS[carte["rarete"]]
        statut = "✨ NOUVELLE" if est_nouvelle else "🔁 doublon"
        lignes.append(f"{emoji} **{carte['nom']}** ({carte['rarete']}) — {statut}")

    embed = discord.Embed(
        title=f"🃏 {config['nom']} ouvert !",
        description="\n".join(lignes),
        color=0xD4A017
    )
    embed.set_footer(text=f"🌊 One Piece Bot • -{config['prix']:,}฿ • Cartes")
    await interaction.followup.send(embed=embed)

    for cle in CATEGORIES:
        if await check_completion_claimable(interaction.guild_id, interaction.user.id, cle):
            nom_cat, _ = CATEGORIES[cle]
            await interaction.followup.send(
                f"🎉 Collection **{nom_cat}** complète ! Utilise `/cartes collection` pour réclamer ta récompense."
            )


def build_collection_embed(nom_cat, statuts):
    embed = discord.Embed(title=f"🃏 Collection — {nom_cat}", color=0xD4A017)
    lignes = []
    for s in statuts:
        emoji = RARETE_EMOJIS[s["rarete"]]
        if s["quantite"] > 0:
            lignes.append(f"{emoji} ✅ x{s['quantite']} — **{s['nom']}**")
        else:
            lignes.append(f"{emoji} 🔒 — {s['nom']}")
    embed.description = "\n".join(lignes)
    nb_possede = sum(1 for s in statuts if s["quantite"] > 0)
    embed.set_footer(text=f"🌊 One Piece Bot • {nb_possede}/{len(statuts)} cartes possédées")
    return embed


class ClaimCompletionButton(discord.ui.Button):
    def __init__(self, guild_id, user_id, categorie_key, nom_cat):
        super().__init__(label=f"Réclamer : {nom_cat}", emoji="🎁", style=discord.ButtonStyle.success)
        self.guild_id = guild_id
        self.user_id = user_id
        self.categorie_key = categorie_key

    async def callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("⛔ Ce n'est pas ta collection !", ephemeral=True)
            return
        await interaction.response.defer()
        resultat = await claim_completion(self.guild_id, self.user_id, self.categorie_key)
        if resultat is None:
            await interaction.followup.send("Cette récompense n'est plus réclamable.", ephemeral=True)
            return
        berrys, titre = resultat
        message = f"🎉 Collection complète ! +{berrys:,}฿"
        if titre:
            message += f" et le titre **{titre}** débloqué !"
        await interaction.followup.send(message, ephemeral=True)


class CollectionSelect(discord.ui.Select):
    def __init__(self, guild_id, user_id):
        self.guild_id = guild_id
        self.user_id = user_id
        options = [discord.SelectOption(label=nom, value=cle) for cle, (nom, _) in CATEGORIES.items()]
        super().__init__(placeholder="Choisis une catégorie...", options=options, custom_id="cartes_collection_select")

    async def callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("⛔ Ce n'est pas ta collection !", ephemeral=True)
            return
        nom_cat, statuts = await get_collection_status(self.guild_id, self.user_id, self.values[0])
        embed = build_collection_embed(nom_cat, statuts)
        claimable = await check_completion_claimable(self.guild_id, self.user_id, self.values[0])
        view = CollectionView(self.guild_id, self.user_id, self.values[0] if claimable else None, nom_cat)
        await interaction.response.edit_message(embed=embed, view=view)


class CollectionView(discord.ui.View):
    def __init__(self, guild_id, user_id, claimable_categorie=None, nom_cat=None):
        super().__init__(timeout=120)
        self.add_item(CollectionSelect(guild_id, user_id))
        if claimable_categorie:
            self.add_item(ClaimCompletionButton(guild_id, user_id, claimable_categorie, nom_cat))


@cartes_group.command(name="collection", description="Voir ta collection de cartes")
@require_salon("salon_cartes")
async def cartes_collection(interaction: discord.Interaction):
    await interaction.response.defer()
    player = await get_player(interaction.guild_id, interaction.user.id)
    if player is None:
        await interaction.followup.send("Tu n'as pas encore de personnage ! Lance `/commencer` pour débuter l'aventure 🏴‍☠️")
        return

    possede, total = await get_overview(interaction.guild_id, interaction.user.id)
    premiere_cle = next(iter(CATEGORIES))
    nom_cat, statuts = await get_collection_status(interaction.guild_id, interaction.user.id, premiere_cle)
    embed = build_collection_embed(nom_cat, statuts)
    embed.description = f"**{possede}/{total}** cartes possédées, toutes catégories confondues.\n\n" + embed.description

    claimable = await check_completion_claimable(interaction.guild_id, interaction.user.id, premiere_cle)
    view = CollectionView(interaction.guild_id, interaction.user.id, premiere_cle if claimable else None, nom_cat)
    await interaction.followup.send(embed=embed, view=view)


async def doublon_autocomplete(interaction: discord.Interaction, current: str):
    owned = await get_owned(interaction.guild_id, interaction.user.id)
    toutes = get_all_cards()
    dispo = [c for c in toutes if owned.get(c["code"], 0) > 1 and current.lower() in c["nom"].lower()]
    return [
        app_commands.Choice(name=f"{c['nom']} (x{owned[c['code']]}, {RARETE_VENTE[c['rarete']]}฿/carte)", value=c["code"])
        for c in dispo[:25]
    ]

@cartes_group.command(name="vendre", description="Vendre des cartes en double")
@app_commands.describe(carte="La carte à vendre (doublons uniquement)", quantite="Nombre d'exemplaires à vendre")
@app_commands.autocomplete(carte=doublon_autocomplete)
@require_salon("salon_cartes")
async def cartes_vendre(interaction: discord.Interaction, carte: str, quantite: int = 1):
    await interaction.response.defer()
    player = await get_player(interaction.guild_id, interaction.user.id)
    if player is None:
        await interaction.followup.send("Tu n'as pas encore de personnage ! Lance `/commencer` pour débuter l'aventure 🏴‍☠️")
        return
    if quantite <= 0:
        await interaction.followup.send("La quantité doit être positive 🙃")
        return

    carte_data = get_card(carte)
    if not carte_data:
        await interaction.followup.send("Carte introuvable.")
        return

    owned = await get_owned(interaction.guild_id, interaction.user.id)
    possede = owned.get(carte, 0)
    max_vendable = max(0, possede - 1)
    if quantite > max_vendable:
        await interaction.followup.send(f"⛔ Tu ne peux vendre que **{max_vendable}** exemplaire(s) de cette carte (tu dois en garder au moins 1).")
        return

    prix_unitaire = RARETE_VENTE[carte_data["rarete"]]
    gain = prix_unitaire * quantite

    await remove_card(interaction.guild_id, interaction.user.id, carte, quantite)
    pool = get_pool()
    async with pool.acquire() as conn:
        await conn.execute("UPDATE players SET berrys = berrys + $3 WHERE guild_id=$1 AND user_id=$2", interaction.guild_id, interaction.user.id, gain)

    await interaction.followup.send(f"💰 **{quantite}x {carte_data['nom']}** vendue(s) pour **{gain:,}฿** !")


async def ma_carte_autocomplete(interaction: discord.Interaction, current: str):
    owned = await get_owned(interaction.guild_id, interaction.user.id)
    toutes = get_all_cards()
    dispo = [c for c in toutes if owned.get(c["code"], 0) > 0 and current.lower() in c["nom"].lower()]
    return [app_commands.Choice(name=f"{c['nom']} (x{owned[c['code']]})", value=c["code"]) for c in dispo[:25]]


async def leur_carte_autocomplete(interaction: discord.Interaction, current: str):
    membre = interaction.namespace.membre
    if not membre:
        return []
    owned = await get_owned(interaction.guild_id, membre.id)
    toutes = get_all_cards()
    dispo = [c for c in toutes if owned.get(c["code"], 0) > 0 and current.lower() in c["nom"].lower()]
    return [app_commands.Choice(name=f"{c['nom']} (x{owned[c['code']]})", value=c["code"]) for c in dispo[:25]]


class EchangeConfirmView(discord.ui.View):
    def __init__(self, guild_id, proposeur: discord.Member, cible: discord.Member, carte_offerte, carte_demandee):
        super().__init__(timeout=120)
        self.guild_id = guild_id
        self.proposeur = proposeur
        self.cible = cible
        self.carte_offerte = carte_offerte
        self.carte_demandee = carte_demandee
        self.repondu = False

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.cible.id:
            await interaction.response.send_message("⛔ Cette proposition d'échange ne t'est pas adressée !", ephemeral=True)
            return False
        return True

    @discord.ui.button(label="Accepter", emoji="🤝", style=discord.ButtonStyle.success)
    async def accepter(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.repondu:
            return
        self.repondu = True
        for c in self.children:
            c.disabled = True

        owned_cible = await get_owned(self.guild_id, self.cible.id)
        owned_proposeur = await get_owned(self.guild_id, self.proposeur.id)
        if owned_cible.get(self.carte_demandee, 0) < 1 or owned_proposeur.get(self.carte_offerte, 0) < 1:
            await interaction.response.edit_message(content="⛔ L'un des deux joueurs ne possède plus la carte concernée, échange annulé.", embed=None, view=self)
            return

        await remove_card(self.guild_id, self.proposeur.id, self.carte_offerte, 1)
        await remove_card(self.guild_id, self.cible.id, self.carte_demandee, 1)
        await add_card(self.guild_id, self.cible.id, self.carte_offerte, 1)
        await add_card(self.guild_id, self.proposeur.id, self.carte_demandee, 1)

        carte_offerte_data = get_card(self.carte_offerte)
        carte_demandee_data = get_card(self.carte_demandee)
        await interaction.response.edit_message(
            content=f"🤝 Échange conclu ! {self.proposeur.mention} ↔️ {self.cible.mention} : **{carte_offerte_data['nom']}** contre **{carte_demandee_data['nom']}**",
            embed=None, view=self
        )

    @discord.ui.button(label="Refuser", emoji="🚫", style=discord.ButtonStyle.danger)
    async def refuser(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.repondu:
            return
        self.repondu = True
        for c in self.children:
            c.disabled = True
        await interaction.response.edit_message(content="L'échange a été refusé.", embed=None, view=self)


@cartes_group.command(name="echanger", description="Proposer un échange de cartes (mardi et dimanche uniquement)")
@app_commands.describe(membre="Le joueur avec qui échanger", ma_carte="La carte que tu offres", leur_carte="La carte que tu demandes")
@app_commands.autocomplete(ma_carte=ma_carte_autocomplete, leur_carte=leur_carte_autocomplete)
@require_salon("salon_cartes")
async def cartes_echanger(interaction: discord.Interaction, membre: discord.Member, ma_carte: str, leur_carte: str):
    await interaction.response.defer()
    if not is_echange_ouvert():
        await interaction.followup.send("⛔ Les échanges de cartes ne sont ouverts que le **mardi** et le **dimanche**. Reviens un de ces jours-là !")
        return
    if membre.id == interaction.user.id or membre.bot:
        await interaction.followup.send("Choix invalide 🙃")
        return

    owned = await get_owned(interaction.guild_id, interaction.user.id)
    if owned.get(ma_carte, 0) < 1:
        await interaction.followup.send("⛔ Tu ne possèdes pas cette carte.")
        return

    owned_cible = await get_owned(interaction.guild_id, membre.id)
    if owned_cible.get(leur_carte, 0) < 1:
        await interaction.followup.send(f"⛔ {membre.display_name} ne possède pas cette carte.")
        return

    carte_offerte_data = get_card(ma_carte)
    carte_demandee_data = get_card(leur_carte)

    embed = discord.Embed(
        title="🤝 Proposition d'échange !",
        description=(
            f"{interaction.user.mention} propose un échange à {membre.mention} :\n\n"
            f"Il/elle offre : **{carte_offerte_data['nom']}** ({carte_offerte_data['rarete']})\n"
            f"Contre : **{carte_demandee_data['nom']}** ({carte_demandee_data['rarete']})"
        ),
        color=0xD4A017
    )
    embed.set_footer(text="🌊 One Piece Bot • Cartes • 2 minutes pour répondre")
    view = EchangeConfirmView(interaction.guild_id, interaction.user, membre, ma_carte, leur_carte)
    await interaction.followup.send(content=membre.mention, embed=embed, view=view)


def setup_cartes_commands(bot):
    bot.tree.add_command(cartes_group)
