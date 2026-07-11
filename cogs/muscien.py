import discord
from discord import app_commands
import random
import datetime
from database.db import get_pool
from utils.players import get_player, add_xp
from utils.metiers import get_rang, rang_label
from utils.shop import get_item_by_name
from utils.channel_check import require_salon
from utils.quetes import increment_quest_progress
from data.recettes_musicien import RECETTES_MUSICIEN

musicien_group = app_commands.Group(name="musicien", description="Actions du métier de Musicien")

COUT_ENDURANCE = 12
COOLDOWNS_PAR_RANG = {0: 15, 1: 10, 2: 6}
GAINS_PAR_RANG = {0: (15, 35), 1: (30, 60), 2: (50, 100)}

_last_jouer = {}

AIRS = [
    "un air entraînant sur le port",
    "une ballade mélancolique à la taverne",
    "une mélodie rythmée sur la place du marché",
    "un chant de marins repris par la foule",
    "une improvisation endiablée près des quais",
]

@musicien_group.command(name="jouer", description="Jouer un morceau pour gagner des Berrys (réservé aux Musiciens)")
@require_salon("salon_taverne")
async def musicien_jouer(interaction: discord.Interaction):
    await interaction.response.defer()
    player = await get_player(interaction.guild_id, interaction.user.id)
    if player is None:
        await interaction.followup.send("Tu n'as pas encore de personnage ! Lance `/commencer` pour débuter l'aventure 🏴‍☠️")
        return
    if player["metier"] != "Musicien":
        await interaction.followup.send("⛔ Tu dois être **Musicien** pour jouer un morceau ! Choisis ce métier avec `/metier choisir` (réservé aux Civils).")
        return
    if player["endurance"] < COUT_ENDURANCE:
        await interaction.followup.send(f"😮‍💨 Il te faut {COUT_ENDURANCE} endurance pour ça (tu as {player['endurance']}).")
        return

    rang = get_rang(player["metier_xp"])
    cooldown_minutes = COOLDOWNS_PAR_RANG.get(rang, 15)
    key = (interaction.guild_id, interaction.user.id)
    now = datetime.datetime.utcnow()
    last = _last_jouer.get(key)
    if last:
        elapsed = (now - last).total_seconds() / 60
        if elapsed < cooldown_minutes:
            restant = int(cooldown_minutes - elapsed)
            await interaction.followup.send(f"😮‍💨 Tu dois encore attendre **{restant} min** avant de rejouer.")
            return

    gain_min, gain_max = GAINS_PAR_RANG.get(rang, (15, 35))
    gain = random.randint(gain_min, gain_max)
    air = random.choice(AIRS)

    pool = get_pool()
    async with pool.acquire() as conn:
        await conn.execute(
            "UPDATE players SET berrys = berrys + $3, endurance = endurance - $4, metier_xp = metier_xp + 15 WHERE guild_id=$1 AND user_id=$2",
            interaction.guild_id, interaction.user.id, gain, COUT_ENDURANCE
        )

    _last_jouer[key] = now
    niveaux_gagnes, nouveau_niveau = await add_xp(interaction.guild_id, interaction.user.id, 8, 4)
    await increment_quest_progress(interaction.guild_id, interaction.user.id, "jouer_musique")

    embed = discord.Embed(
        title="🎵 Morceau joué !",
        description=f"Tu joues {air}, les passants applaudissent et te lancent **{gain}฿** !",
        color=0xE67E22
    )
    embed.set_footer(text="🌊 One Piece Bot • Guilde des métiers")
    await interaction.followup.send(embed=embed)

    if niveaux_gagnes > 0:
        await interaction.followup.send(embed=discord.Embed(
            title="🎉 Niveau supérieur !",
            description=f"{interaction.user.mention} passe **niveau {nouveau_niveau}** !",
            color=0x27AE60
        ))


async def recette_musicien_autocomplete(interaction: discord.Interaction, current: str):
    player = await get_player(interaction.guild_id, interaction.user.id)
    if not player or player["metier"] != "Musicien":
        return []
    rang = get_rang(player["metier_xp"])
    dispo = [r for r in RECETTES_MUSICIEN if r[3] <= rang and current.lower() in r[0].lower()]
    return [app_commands.Choice(name=r[0], value=r[0]) for r in dispo[:25]]

@musicien_group.command(name="composer", description="Composer une partition à partir de tes instruments (réservé aux Musiciens)")
@app_commands.describe(recette="La partition à composer")
@app_commands.autocomplete(recette=recette_musicien_autocomplete)
@require_salon("salon_taverne")
async def musicien_composer(interaction: discord.Interaction, recette: str):
    await interaction.response.defer()
    player = await get_player(interaction.guild_id, interaction.user.id)
    if player is None:
        await interaction.followup.send("Tu n'as pas encore de personnage ! Lance `/commencer` pour débuter l'aventure 🏴‍☠️")
        return
    if player["metier"] != "Musicien":
        await interaction.followup.send("⛔ Tu dois être **Musicien** pour composer ! Choisis ce métier avec `/metier choisir` (réservé aux Civils).")
        return

    recette_data = next((r for r in RECETTES_MUSICIEN if r[0] == recette), None)
    if not recette_data:
        await interaction.followup.send("Recette introuvable.")
        return
    nom_recette, ingredients, nom_partition, rang_requis = recette_data

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

        partition_item = await get_item_by_name(interaction.guild_id, nom_partition)
        if not partition_item:
            await interaction.followup.send("⚠️ Erreur interne : la partition n'existe pas dans le catalogue.")
            return

        async with conn.transaction():
            for nom_ingredient, (inv_id, quantite_actuelle, quantite_requise) in inventaire_ids.items():
                if quantite_actuelle > quantite_requise:
                    await conn.execute("UPDATE inventory SET quantite = quantite - $2 WHERE id=$1", inv_id, quantite_requise)
                else:
                    await conn.execute("DELETE FROM inventory WHERE id=$1", inv_id)

            existing = await conn.fetchrow(
                "SELECT id FROM inventory WHERE guild_id=$1 AND user_id=$2 AND item_id=$3",
                interaction.guild_id, interaction.user.id, partition_item["id"]
            )
            if existing:
                await conn.execute("UPDATE inventory SET quantite = quantite + 1 WHERE id=$1", existing["id"])
            else:
                await conn.execute(
                    "INSERT INTO inventory (guild_id, user_id, item_id, quantite, durabilite) VALUES ($1,$2,$3,1,$4)",
                    interaction.guild_id, interaction.user.id, partition_item["id"], partition_item["durabilite_max"]
                )

            metier_xp_gain = 15 + (rang_requis * 10)
            await conn.execute("UPDATE players SET metier_xp = metier_xp + $3 WHERE guild_id=$1 AND user_id=$2",
                                interaction.guild_id, interaction.user.id, metier_xp_gain)

    niveaux_gagnes, nouveau_niveau = await add_xp(interaction.guild_id, interaction.user.id, 8, 4)
    await increment_quest_progress(interaction.guild_id, interaction.user.id, "composer_partition")

    nouveau_metier_xp = player["metier_xp"] + metier_xp_gain
    nouveau_rang = get_rang(nouveau_metier_xp)
    rang_monte = nouveau_rang > rang_joueur

    embed = discord.Embed(
        title="🎵 Partition composée !",
        description=f"Tu as composé **{nom_partition}** ! Retrouve-la dans `/inventaire voir`.",
        color=0xF4C430
    )
    embed.set_footer(text=f"🌊 One Piece Bot • +{metier_xp_gain} XP Métier")
    await interaction.followup.send(embed=embed)

    if rang_monte:
        await interaction.followup.send(embed=discord.Embed(
            title="🎵 Rang de métier supérieur !",
            description=f"Tu passes rang **{rang_label(nouveau_rang)}** en tant que Musicien !",
            color=0x27AE60
        ))
    if niveaux_gagnes > 0:
        await interaction.followup.send(embed=discord.Embed(
            title="🎉 Niveau supérieur !",
            description=f"{interaction.user.mention} passe **niveau {nouveau_niveau}** !",
            color=0x27AE60
        ))


def setup_musicien_commands(bot):
    bot.tree.add_command(musicien_group)
