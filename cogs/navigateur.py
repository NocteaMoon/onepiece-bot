import discord
from discord import app_commands
import datetime
from database.db import get_pool
from utils.players import get_player, add_xp
from utils.metiers import get_rang, rang_label
from utils.shop import get_item_by_name
from utils.channel_check import require_salon
from utils.quetes import increment_quest_progress
from data.recettes_navigateur import RECETTES_NAVIGATEUR

navigateur_group = app_commands.Group(name="navigateur", description="Actions du métier de Navigateur")

COUT_ENDURANCE = 15
COOLDOWNS_PAR_RANG = {0: 20, 1: 15, 2: 10}
VOYAGES_OFFERTS_PAR_RANG = {0: 1, 1: 2, 2: 3}

_last_route = {}

@navigateur_group.command(name="route_sure", description="Garantir un trajet sans risque au prochain voyage d'un joueur (réservé aux Navigateurs)")
@app_commands.describe(membre="Le joueur à aider (toi par défaut)")
@require_salon("salon_taverne")
async def navigateur_route_sure(interaction: discord.Interaction, membre: discord.Member = None):
    await interaction.response.defer()
    navigateur = await get_player(interaction.guild_id, interaction.user.id)
    if navigateur is None:
        await interaction.followup.send("Tu n'as pas encore de personnage ! Lance `/commencer` pour débuter l'aventure 🏴‍☠️")
        return
    if navigateur["metier"] != "Navigateur":
        await interaction.followup.send("⛔ Tu dois être **Navigateur** pour tracer une route sûre ! Choisis ce métier avec `/metier choisir` (réservé aux Civils).")
        return
    if navigateur["endurance"] < COUT_ENDURANCE:
        await interaction.followup.send(f"😮‍💨 Il te faut {COUT_ENDURANCE} endurance pour ça (tu as {navigateur['endurance']}).")
        return

    cible = membre or interaction.user
    cible_data = await get_player(interaction.guild_id, cible.id)
    if cible_data is None:
        await interaction.followup.send(f"{cible.display_name} n'a pas encore de personnage.")
        return

    rang = get_rang(navigateur["metier_xp"])
    cooldown_minutes = COOLDOWNS_PAR_RANG.get(rang, 20)
    nb_voyages = VOYAGES_OFFERTS_PAR_RANG.get(rang, 1)

    key = (interaction.guild_id, interaction.user.id)
    now = datetime.datetime.utcnow()
    last = _last_route.get(key)
    if last:
        elapsed = (now - last).total_seconds() / 60
        if elapsed < cooldown_minutes:
            restant = int(cooldown_minutes - elapsed)
            await interaction.followup.send(f"😮‍💨 Tu dois encore attendre **{restant} min** avant de retracer une route.")
            return

    pool = get_pool()
    async with pool.acquire() as conn:
        async with conn.transaction():
            await conn.execute(
                "UPDATE players SET endurance = endurance - $3, metier_xp = metier_xp + 20 WHERE guild_id=$1 AND user_id=$2",
                interaction.guild_id, interaction.user.id, COUT_ENDURANCE
            )
            await conn.execute(
                "UPDATE players SET voyage_protege = voyage_protege + $3 WHERE guild_id=$1 AND user_id=$2",
                interaction.guild_id, cible.id, nb_voyages
            )

    _last_route[key] = now
    await add_xp(interaction.guild_id, interaction.user.id, 8, 4)

    embed = discord.Embed(
        title="🧭 Route tracée !",
        description=f"{cible.mention} bénéficie de **{nb_voyages} voyage(s) sans risque** grâce à tes conseils avisés !",
        color=0x1B3A5C
    )
    embed.set_footer(text="🌊 One Piece Bot • Guilde des métiers")
    await interaction.followup.send(embed=embed)


async def recette_navigateur_autocomplete(interaction: discord.Interaction, current: str):
    player = await get_player(interaction.guild_id, interaction.user.id)
    if not player or player["metier"] != "Navigateur":
        return []
    rang = get_rang(player["metier_xp"])
    dispo = [r for r in RECETTES_NAVIGATEUR if r[3] <= rang and current.lower() in r[0].lower()]
    return [app_commands.Choice(name=r[0], value=r[0]) for r in dispo[:25]]

@navigateur_group.command(name="dresser_carte", description="Dresser une carte à partir de matériaux de navigation (réservé aux Navigateurs)")
@app_commands.describe(recette="La carte à dresser")
@app_commands.autocomplete(recette=recette_navigateur_autocomplete)
@require_salon("salon_taverne")
async def navigateur_dresser_carte(interaction: discord.Interaction, recette: str):
    await interaction.response.defer()
    player = await get_player(interaction.guild_id, interaction.user.id)
    if player is None:
        await interaction.followup.send("Tu n'as pas encore de personnage ! Lance `/commencer` pour débuter l'aventure 🏴‍☠️")
        return
    if player["metier"] != "Navigateur":
        await interaction.followup.send("⛔ Tu dois être **Navigateur** pour dresser une carte ! Choisis ce métier avec `/metier choisir` (réservé aux Civils).")
        return

    recette_data = next((r for r in RECETTES_NAVIGATEUR if r[0] == recette), None)
    if not recette_data:
        await interaction.followup.send("Recette introuvable.")
        return
    nom_recette, ingredients, nom_carte, rang_requis = recette_data

    rang_joueur = get_rang(player["metier_xp"])
    if rang_joueur < rang_requis:
        await interaction.followup.send(f"⛔ Cette recette nécessite le rang **{rang_label(rang_requis)}** (tu es {rang_label(rang_joueur)}).")
        return

    pool = get_pool()
    async with pool.acquire() as conn:
        manquants = []
        inventaire_ids = {}
        for nom_ingredient, quantite_requise in ingredients:
            item = await get_item_by_name(interaction.guild_id, nom_ingredient)
            if not item:
                manquants.append(nom_ingredient)
                continue
            inv_row = await conn.fetchrow(
                "SELECT id, quantite FROM inventory WHERE guild_id=$1 AND user_id=$2 AND item_id=$3",
                interaction.guild_id, interaction.user.id, item["id"]
            )
            if not inv_row or inv_row["quantite"] < quantite_requise:
                manquants.append(f"{nom_ingredient} (x{quantite_requise})")
            else:
                inventaire_ids[nom_ingredient] = (inv_row["id"], inv_row["quantite"], quantite_requise)

        if manquants:
            await interaction.followup.send(f"⛔ Ingrédients manquants : {', '.join(manquants)}")
            return

        carte_item = await get_item_by_name(interaction.guild_id, nom_carte)
        if not carte_item:
            await interaction.followup.send("⚠️ Erreur interne : la carte n'existe pas dans le catalogue.")
            return

        async with conn.transaction():
            for nom_ingredient, (inv_id, quantite_actuelle, quantite_requise) in inventaire_ids.items():
                if quantite_actuelle > quantite_requise:
                    await conn.execute("UPDATE inventory SET quantite = quantite - $2 WHERE id=$1", inv_id, quantite_requise)
                else:
                    await conn.execute("DELETE FROM inventory WHERE id=$1", inv_id)

            existing = await conn.fetchrow(
                "SELECT id FROM inventory WHERE guild_id=$1 AND user_id=$2 AND item_id=$3",
                interaction.guild_id, interaction.user.id, carte_item["id"]
            )
            if existing:
                await conn.execute("UPDATE inventory SET quantite = quantite + 1 WHERE id=$1", existing["id"])
            else:
                await conn.execute(
                    "INSERT INTO inventory (guild_id, user_id, item_id, quantite, durabilite) VALUES ($1,$2,$3,1,$4)",
                    interaction.guild_id, interaction.user.id, carte_item["id"], carte_item["durabilite_max"]
                )

            metier_xp_gain = 15 + (rang_requis * 10)
            await conn.execute("UPDATE players SET metier_xp = metier_xp + $3 WHERE guild_id=$1 AND user_id=$2",
                                interaction.guild_id, interaction.user.id, metier_xp_gain)

    niveaux_gagnes, nouveau_niveau = await add_xp(interaction.guild_id, interaction.user.id, 8, 4)
    await increment_quest_progress(interaction.guild_id, interaction.user.id, "dresser_carte")

    nouveau_metier_xp = player["metier_xp"] + metier_xp_gain
    nouveau_rang = get_rang(nouveau_metier_xp)
    rang_monte = nouveau_rang > rang_joueur

    embed = discord.Embed(
        title="🧭 Carte dressée !",
        description=f"Tu as dressé **{nom_carte}** ! Retrouve-la dans `/inventaire voir`.",
        color=0xF4C430
    )
    embed.set_footer(text=f"🌊 One Piece Bot • +{metier_xp_gain} XP Métier")
    await interaction.followup.send(embed=embed)

    if rang_monte:
        await interaction.followup.send(embed=discord.Embed(
            title="🧭 Rang de métier supérieur !",
            description=f"Tu passes rang **{rang_label(nouveau_rang)}** en tant que Navigateur !",
            color=0x27AE60
        ))
    if niveaux_gagnes > 0:
        await interaction.followup.send(embed=discord.Embed(
            title="🎉 Niveau supérieur !",
            description=f"{interaction.user.mention} passe **niveau {nouveau_niveau}** !",
            color=0x27AE60
        ))


def setup_navigateur_commands(bot):
    bot.tree.add_command(navigateur_group)
