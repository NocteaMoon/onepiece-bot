import discord
from discord import app_commands
import datetime
from database.db import get_pool
from utils.players import get_player, add_xp
from utils.metiers import get_rang, rang_label
from utils.shop import get_item_by_name
from utils.channel_check import require_salon
from data.recettes_medecin import RECETTES_MEDECIN

medecin_group = app_commands.Group(name="medecin", description="Actions du métier de Médecin")

COUT_ENDURANCE = 15
COOLDOWNS_PAR_RANG = {0: 20, 1: 15, 2: 10}

_last_soin = {}

@medecin_group.command(name="soigner", description="Soigner un joueur : PV restaurés et K.O. levé (réservé aux Médecins)")
@app_commands.describe(membre="Le joueur à soigner (toi par défaut)")
@require_salon("salon_taverne")
async def medecin_soigner(interaction: discord.Interaction, membre: discord.Member = None):
    await interaction.response.defer()
    soigneur = await get_player(interaction.guild_id, interaction.user.id)
    if soigneur is None:
        await interaction.followup.send("Tu n'as pas encore de personnage ! Lance `/commencer` pour débuter l'aventure 🏴‍☠️")
        return
    if soigneur["metier"] != "Médecin":
        await interaction.followup.send("⛔ Tu dois être **Médecin** pour soigner quelqu'un ! Choisis ce métier avec `/metier choisir` (réservé aux Civils).")
        return
    if soigneur["endurance"] < COUT_ENDURANCE:
        await interaction.followup.send(f"😮‍💨 Il te faut {COUT_ENDURANCE} endurance pour ça (tu as {soigneur['endurance']}).")
        return

    cible = membre or interaction.user
    cible_data = await get_player(interaction.guild_id, cible.id)
    if cible_data is None:
        await interaction.followup.send(f"{cible.display_name} n'a pas encore de personnage.")
        return

    rang = get_rang(soigneur["metier_xp"])
    cooldown_minutes = COOLDOWNS_PAR_RANG.get(rang, 20)
    key = (interaction.guild_id, interaction.user.id)
    now = datetime.datetime.utcnow()
    last = _last_soin.get(key)
    if last:
        elapsed = (now - last).total_seconds() / 60
        if elapsed < cooldown_minutes:
            restant = int(cooldown_minutes - elapsed)
            await interaction.followup.send(f"😮‍💨 Tu dois encore attendre **{restant} min** avant de pouvoir soigner à nouveau.")
            return

    pool = get_pool()
    async with pool.acquire() as conn:
        async with conn.transaction():
            await conn.execute(
                "UPDATE players SET endurance = endurance - $3, metier_xp = metier_xp + 20 WHERE guild_id=$1 AND user_id=$2",
                interaction.guild_id, interaction.user.id, COUT_ENDURANCE
            )
            await conn.execute(
                "UPDATE players SET pv = pv_max, ko_jusqua = NULL WHERE guild_id=$1 AND user_id=$2",
                interaction.guild_id, cible.id
            )

    _last_soin[key] = now
    await add_xp(interaction.guild_id, interaction.user.id, 8, 4)

    embed = discord.Embed(
        title="💊 Soins prodigués !",
        description=f"{cible.mention} est remis(e) sur pied : PV entièrement restaurés, K.O. levé.",
        color=0x27AE60
    )
    embed.set_footer(text="🌊 One Piece Bot • Guilde des métiers")
    await interaction.followup.send(embed=embed)


async def recette_medecin_autocomplete(interaction: discord.Interaction, current: str):
    player = await get_player(interaction.guild_id, interaction.user.id)
    if not player or player["metier"] != "Médecin":
        return []
    rang = get_rang(player["metier_xp"])
    dispo = [r for r in RECETTES_MEDECIN if r[3] <= rang and current.lower() in r[0].lower()]
    return [app_commands.Choice(name=r[0], value=r[0]) for r in dispo[:25]]

@medecin_group.command(name="preparer", description="Préparer un remède à partir d'herbes (réservé aux Médecins)")
@app_commands.describe(recette="Le remède à préparer")
@app_commands.autocomplete(recette=recette_medecin_autocomplete)
@require_salon("salon_taverne")
async def medecin_preparer(interaction: discord.Interaction, recette: str):
    await interaction.response.defer()
    player = await get_player(interaction.guild_id, interaction.user.id)
    if player is None:
        await interaction.followup.send("Tu n'as pas encore de personnage ! Lance `/commencer` pour débuter l'aventure 🏴‍☠️")
        return
    if player["metier"] != "Médecin":
        await interaction.followup.send("⛔ Tu dois être **Médecin** pour préparer un remède ! Choisis ce métier avec `/metier choisir` (réservé aux Civils).")
        return

    recette_data = next((r for r in RECETTES_MEDECIN if r[0] == recette), None)
    if not recette_data:
        await interaction.followup.send("Recette introuvable.")
        return
    nom_recette, ingredients, nom_remede, rang_requis = recette_data

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

        remede_item = await get_item_by_name(interaction.guild_id, nom_remede)
        if not remede_item:
            await interaction.followup.send("⚠️ Erreur interne : le remède n'existe pas dans le catalogue.")
            return

        async with conn.transaction():
            for nom_ingredient, (inv_id, quantite_actuelle, quantite_requise) in inventaire_ids.items():
                if quantite_actuelle > quantite_requise:
                    await conn.execute("UPDATE inventory SET quantite = quantite - $2 WHERE id=$1", inv_id, quantite_requise)
                else:
                    await conn.execute("DELETE FROM inventory WHERE id=$1", inv_id)

            existing = await conn.fetchrow(
                "SELECT id FROM inventory WHERE guild_id=$1 AND user_id=$2 AND item_id=$3",
                interaction.guild_id, interaction.user.id, remede_item["id"]
            )
            if existing:
                await conn.execute("UPDATE inventory SET quantite = quantite + 1 WHERE id=$1", existing["id"])
            else:
                await conn.execute(
                    "INSERT INTO inventory (guild_id, user_id, item_id, quantite, durabilite) VALUES ($1,$2,$3,1,$4)",
                    interaction.guild_id, interaction.user.id, remede_item["id"], remede_item["durabilite_max"]
                )

            metier_xp_gain = 15 + (rang_requis * 10)
            await conn.execute("UPDATE players SET metier_xp = metier_xp + $3 WHERE guild_id=$1 AND user_id=$2",
                                interaction.guild_id, interaction.user.id, metier_xp_gain)

    niveaux_gagnes, nouveau_niveau = await add_xp(interaction.guild_id, interaction.user.id, 8, 4)

    nouveau_metier_xp = player["metier_xp"] + metier_xp_gain
    nouveau_rang = get_rang(nouveau_metier_xp)
    rang_monte = nouveau_rang > rang_joueur

    embed = discord.Embed(
        title="💊 Remède préparé !",
        description=f"Tu as préparé **{nom_remede}** ! Retrouve-le dans `/inventaire voir`.",
        color=0xF4C430
    )
    embed.set_footer(text=f"🌊 One Piece Bot • +{metier_xp_gain} XP Métier")
    await interaction.followup.send(embed=embed)

    if rang_monte:
        await interaction.followup.send(embed=discord.Embed(
            title="💊 Rang de métier supérieur !",
            description=f"Tu passes rang **{rang_label(nouveau_rang)}** en tant que Médecin !",
            color=0x27AE60
        ))
    if niveaux_gagnes > 0:
        await interaction.followup.send(embed=discord.Embed(
            title="🎉 Niveau supérieur !",
            description=f"{interaction.user.mention} passe **niveau {nouveau_niveau}** !",
            color=0x27AE60
        ))


def setup_medecin_commands(bot):
    bot.tree.add_command(medecin_group)
