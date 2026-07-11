import discord
from discord import app_commands
from database.db import get_pool
from utils.players import get_player, add_xp
from utils.metiers import get_rang, rang_label
from utils.shop import get_item_by_name
from utils.channel_check import require_salon
from utils.quetes import increment_quest_progress
from data.recettes_forgeron import RECETTES_FORGERON

forgeron_group = app_commands.Group(name="forgeron", description="Actions du métier de Forgeron")

COUT_PAR_RARETE = {
    "Commun": 2, "Aiguisé": 4, "Grade": 8, "Grand Grade": 15, "Suprême": 30, "Mythique": 60,
}

async def objet_endommage_autocomplete(interaction: discord.Interaction, current: str):
    player = await get_player(interaction.guild_id, interaction.user.id)
    if not player or player["metier"] != "Forgeron":
        return []
    pool = get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch("""
            SELECT inventory.id AS inv_id, shop_items.nom, inventory.durabilite, shop_items.durabilite_max
            FROM inventory JOIN shop_items ON inventory.item_id = shop_items.id
            WHERE inventory.guild_id=$1 AND inventory.user_id=$2 AND inventory.equipe = TRUE AND inventory.durabilite < shop_items.durabilite_max
        """, interaction.guild_id, interaction.user.id)
    filtered = [r for r in rows if current.lower() in r["nom"].lower()]
    return [app_commands.Choice(name=f"{r['nom']} ({r['durabilite']}/{r['durabilite_max']})", value=r["inv_id"]) for r in filtered[:25]]

@forgeron_group.command(name="reparer", description="Réparer un de tes objets équipés endommagés (réservé aux Forgerons)")
@app_commands.describe(objet="L'objet équipé à réparer")
@app_commands.autocomplete(objet=objet_endommage_autocomplete)
@require_salon("salon_taverne")
async def forgeron_reparer(interaction: discord.Interaction, objet: int):
    await interaction.response.defer()
    player = await get_player(interaction.guild_id, interaction.user.id)
    if player is None:
        await interaction.followup.send("Tu n'as pas encore de personnage ! Lance `/commencer` pour débuter l'aventure 🏴‍☠️")
        return
    if player["metier"] != "Forgeron":
        await interaction.followup.send("⛔ Tu dois être **Forgeron** pour réparer de l'équipement ! Choisis ce métier avec `/metier choisir` (réservé aux Civils).")
        return

    pool = get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow("""
            SELECT inventory.id AS inv_id, inventory.durabilite, shop_items.nom, shop_items.rarete, shop_items.durabilite_max
            FROM inventory JOIN shop_items ON inventory.item_id = shop_items.id
            WHERE inventory.id = $1 AND inventory.guild_id=$2 AND inventory.user_id=$3 AND inventory.equipe = TRUE
        """, objet, interaction.guild_id, interaction.user.id)

    if not row:
        await interaction.followup.send("Objet introuvable ou non équipé.")
        return
    if row["durabilite"] >= row["durabilite_max"]:
        await interaction.followup.send(f"**{row['nom']}** est déjà en parfait état.")
        return

    points_manquants = row["durabilite_max"] - row["durabilite"]
    cout_point = COUT_PAR_RARETE.get(row["rarete"], 5)
    cout_total = points_manquants * cout_point

    if player["berrys"] < cout_total:
        await interaction.followup.send(f"⛔ La réparation de **{row['nom']}** coûte **{cout_total:,}฿**, tu n'as que {player['berrys']:,}฿.")
        return

    async with pool.acquire() as conn:
        async with conn.transaction():
            await conn.execute("UPDATE inventory SET durabilite = $2 WHERE id = $1", row["inv_id"], row["durabilite_max"])
            await conn.execute(
                "UPDATE players SET berrys = berrys - $3, metier_xp = metier_xp + 20 WHERE guild_id=$1 AND user_id=$2",
                interaction.guild_id, interaction.user.id, cout_total
            )

    await add_xp(interaction.guild_id, interaction.user.id, 8, 4)

    embed = discord.Embed(
        title="🔨 Réparation terminée !",
        description=f"**{row['nom']}** est comme neuf ! ({points_manquants} points de durabilité restaurés)",
        color=0xF4C430
    )
    embed.set_footer(text=f"🌊 One Piece Bot • -{cout_total:,}฿ • +20 XP Métier")
    await interaction.followup.send(embed=embed)


async def recette_forgeron_autocomplete(interaction: discord.Interaction, current: str):
    player = await get_player(interaction.guild_id, interaction.user.id)
    if not player or player["metier"] != "Forgeron":
        return []
    rang = get_rang(player["metier_xp"])
    dispo = [r for r in RECETTES_FORGERON if r[3] <= rang and current.lower() in r[0].lower()]
    return [app_commands.Choice(name=r[0], value=r[0]) for r in dispo[:25]]

@forgeron_group.command(name="forger", description="Forger une arme ou armure à partir de minerais (réservé aux Forgerons)")
@app_commands.describe(recette="L'objet à forger")
@app_commands.autocomplete(recette=recette_forgeron_autocomplete)
@require_salon("salon_taverne")
async def forgeron_forger(interaction: discord.Interaction, recette: str):
    await interaction.response.defer()
    player = await get_player(interaction.guild_id, interaction.user.id)
    if player is None:
        await interaction.followup.send("Tu n'as pas encore de personnage ! Lance `/commencer` pour débuter l'aventure 🏴‍☠️")
        return
    if player["metier"] != "Forgeron":
        await interaction.followup.send("⛔ Tu dois être **Forgeron** pour forger ! Choisis ce métier avec `/metier choisir` (réservé aux Civils).")
        return

    recette_data = next((r for r in RECETTES_FORGERON if r[0] == recette), None)
    if not recette_data:
        await interaction.followup.send("Recette introuvable.")
        return
    nom_recette, ingredients, nom_objet, rang_requis = recette_data

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

        objet_item = await get_item_by_name(interaction.guild_id, nom_objet)
        if not objet_item:
            await interaction.followup.send("⚠️ Erreur interne : l'objet n'existe pas dans le catalogue.")
            return

        async with conn.transaction():
            for nom_ingredient, (inv_id, quantite_actuelle, quantite_requise) in inventaire_ids.items():
                if quantite_actuelle > quantite_requise:
                    await conn.execute("UPDATE inventory SET quantite = quantite - $2 WHERE id=$1", inv_id, quantite_requise)
                else:
                    await conn.execute("DELETE FROM inventory WHERE id=$1", inv_id)

            await conn.execute(
                "INSERT INTO inventory (guild_id, user_id, item_id, quantite, durabilite) VALUES ($1,$2,$3,1,$4)",
                interaction.guild_id, interaction.user.id, objet_item["id"], objet_item["durabilite_max"]
            )

            metier_xp_gain = 15 + (rang_requis * 10)
            await conn.execute("UPDATE players SET metier_xp = metier_xp + $3 WHERE guild_id=$1 AND user_id=$2",
                                interaction.guild_id, interaction.user.id, metier_xp_gain)

    niveaux_gagnes, nouveau_niveau = await add_xp(interaction.guild_id, interaction.user.id, 8, 4)
    await increment_quest_progress(interaction.guild_id, interaction.user.id, "forger")

    nouveau_metier_xp = player["metier_xp"] + metier_xp_gain
    nouveau_rang = get_rang(nouveau_metier_xp)
    rang_monte = nouveau_rang > rang_joueur

    embed = discord.Embed(
        title="🔨 Objet forgé !",
        description=f"Tu as forgé **{nom_objet}** ! Retrouve-le dans `/inventaire voir`.",
        color=0xF4C430
    )
    embed.set_footer(text=f"🌊 One Piece Bot • +{metier_xp_gain} XP Métier")
    await interaction.followup.send(embed=embed)

    if rang_monte:
        await interaction.followup.send(embed=discord.Embed(
            title="🔨 Rang de métier supérieur !",
            description=f"Tu passes rang **{rang_label(nouveau_rang)}** en tant que Forgeron !",
            color=0x27AE60
        ))
    if niveaux_gagnes > 0:
        await interaction.followup.send(embed=discord.Embed(
            title="🎉 Niveau supérieur !",
            description=f"{interaction.user.mention} passe **niveau {nouveau_niveau}** !",
            color=0x27AE60
        ))


def setup_forgeron_commands(bot):
    bot.tree.add_command(forgeron_group)
