import discord
from discord import app_commands
from database.db import get_pool
from utils.players import get_player
from utils.shop import seed_shop_if_needed, get_visible_items, get_item_by_id
from utils.channel_check import require_salon
from utils.reputation import get_discount_pct, add_reputation_marchand

RARETE_COLORS = {
    "Commun": 0x95A5A6,
    "Aiguisé": 0x2ECC71,
    "Grade": 0x3498DB,
    "Grand Grade": 0x9B59B6,
    "Suprême": 0xE67E22,
    "Mythique": 0x2C3E50,
}

CATEGORIE_CHOICES = [
    app_commands.Choice(name="Consommables", value="Consommable"),
    app_commands.Choice(name="Accessoires", value="Accessoire"),
    app_commands.Choice(name="Têtes", value="Tête"),
    app_commands.Choice(name="Corps", value="Corps"),
    app_commands.Choice(name="Navires", value="Navire"),
    app_commands.Choice(name="Armes", value="Arme"),
    app_commands.Choice(name="Ingrédients", value="Ingrédient"),
]

marche_group = app_commands.Group(name="marche", description="Le marché aux trésors — achète ton équipement")

async def item_autocomplete(interaction: discord.Interaction, current: str):
    player = await get_player(interaction.guild_id, interaction.user.id)
    faction = player["faction"] if player else "Civil"
    await seed_shop_if_needed(interaction.guild_id)
    items = await get_visible_items(interaction.guild_id, faction)
    filtered = [i for i in items if current.lower() in i["nom"].lower()][:25]
    return [app_commands.Choice(name=f"{i['nom']} — {i['prix']:,}฿ ({i['rarete']})", value=i["id"]) for i in filtered]

@marche_group.command(name="voir", description="Parcourir le marché")
@app_commands.describe(categorie="Filtrer par catégorie")
@app_commands.choices(categorie=CATEGORIE_CHOICES)
@require_salon("salon_boutique")
async def marche_voir(interaction: discord.Interaction, categorie: app_commands.Choice[str] = None):
    await interaction.response.defer()
    player = await get_player(interaction.guild_id, interaction.user.id)
    if player is None:
        await interaction.followup.send("Tu n'as pas encore de personnage ! Lance `/commencer` 🏴‍☠️")
        return
    await seed_shop_if_needed(interaction.guild_id)
    cat_value = categorie.value if categorie else None
    items = await get_visible_items(interaction.guild_id, player["faction"], cat_value)
    if not items:
        await interaction.followup.send("Aucun objet disponible dans cette catégorie pour le moment.")
        return

    discount = get_discount_pct(player)
    reduction_texte = f" • 🎭 Réduction fidélité active : **-{discount}%**" if discount > 0 else ""
    embed = discord.Embed(
        title="🛒 Marché aux trésors",
        description=f"Faction : **{player['faction']}** — {len(items)} objet(s) disponible(s)\nUtilise `/marche infos` pour les détails, `/marche acheter` pour acheter.{reduction_texte}",
        color=0xF4C430
    )
    for it in items[:20]:
        stock_txt = "Stock illimité" if it["stock"] == -1 else f"Stock : {it['stock']}"
        prix_affiche = it["prix"] if discount == 0 else round(it["prix"] * (1 - discount / 100))
        prix_texte = f"{prix_affiche:,}฿" if discount == 0 else f"~~{it['prix']:,}฿~~ **{prix_affiche:,}฿**"
        embed.add_field(
            name=f"{it['nom']} — {prix_texte}",
            value=f"{it['rarete']} • Niv. {it['niveau_requis']}+ • {stock_txt}",
            inline=False
        )
    embed.set_footer(text="🌊 One Piece Bot • Marché")
    await interaction.followup.send(embed=embed)


@marche_group.command(name="infos", description="Voir le détail d'un objet du marché")
@app_commands.describe(objet="L'objet à consulter")
@app_commands.autocomplete(objet=item_autocomplete)
@require_salon("salon_boutique")
async def marche_infos(interaction: discord.Interaction, objet: int):
    await interaction.response.defer()
    await seed_shop_if_needed(interaction.guild_id)
    item = await get_item_by_id(interaction.guild_id, objet)
    if not item:
        await interaction.followup.send("Objet introuvable.")
        return
    embed = discord.Embed(title=f"📦 {item['nom']}", description=item["description"], color=RARETE_COLORS.get(item["rarete"], 0x95A5A6))
    embed.add_field(name="Prix", value=f"{item['prix']:,}฿", inline=True)
    embed.add_field(name="Rareté", value=item["rarete"], inline=True)
    embed.add_field(name="Faction", value=item["faction"], inline=True)
    embed.add_field(name="Niveau requis", value=str(item["niveau_requis"]), inline=True)
    stock_txt = "Illimité" if item["stock"] == -1 else str(item["stock"])
    embed.add_field(name="Stock", value=stock_txt, inline=True)

    bonus_lines = []
    for label, key in [("Force","bonus_force"),("Défense","bonus_defense"),("Vitesse","bonus_vitesse"),
                        ("Agilité","bonus_agilite"),("PV","bonus_pv"),("Chance","bonus_chance")]:
        if item[key]:
            bonus_lines.append(f"+{item[key]} {label}")
    if item["soin_pv"]:
        bonus_lines.append(f"Soigne {item['soin_pv']} PV")
    if item["soin_endurance"]:
        bonus_lines.append(f"Restaure {item['soin_endurance']} Endurance")
    if bonus_lines:
        embed.add_field(name="Effets", value="\n".join(bonus_lines), inline=False)

    embed.set_footer(text="🌊 One Piece Bot • Marché")
    await interaction.followup.send(embed=embed)


@marche_group.command(name="acheter", description="Acheter un objet du marché")
@app_commands.describe(objet="L'objet à acheter", quantite="Quantité (1 par défaut)")
@app_commands.autocomplete(objet=item_autocomplete)
@require_salon("salon_boutique")
async def marche_acheter(interaction: discord.Interaction, objet: int, quantite: int = 1):
    await interaction.response.defer()
    await seed_shop_if_needed(interaction.guild_id)
    player = await get_player(interaction.guild_id, interaction.user.id)
    if player is None:
        await interaction.followup.send("Tu n'as pas encore de personnage ! Lance `/commencer` 🏴‍☠️")
        return
    if quantite <= 0:
        await interaction.followup.send("La quantité doit être positive 🙃")
        return

    item = await get_item_by_id(interaction.guild_id, objet)
    if not item or not item["actif"]:
        await interaction.followup.send("Cet objet n'existe pas ou n'est plus disponible.")
        return
    if item["faction"] != "Tous" and item["faction"] != player["faction"]:
        await interaction.followup.send(f"⛔ Cet objet est réservé à la faction **{item['faction']}**.")
        return
    if player["niveau"] < item["niveau_requis"]:
        await interaction.followup.send(f"⛔ Niveau {item['niveau_requis']} requis (tu es niveau {player['niveau']}).")
        return

    discount = get_discount_pct(player)
    prix_unitaire = round(item["prix"] * (1 - discount / 100)) if discount > 0 else item["prix"]
    cout_total = prix_unitaire * quantite
    if cout_total > player["berrys"]:
        await interaction.followup.send(f"Tu n'as pas assez de Berrys ! Il te faut **{cout_total:,}฿**, tu as **{player['berrys']:,}฿**.")
        return

    pool = get_pool()
    async with pool.acquire() as conn:
        async with conn.transaction():
            if item["stock"] != -1:
                fresh = await conn.fetchrow("SELECT stock FROM shop_items WHERE id = $1 FOR UPDATE", item["id"])
                if fresh["stock"] < quantite:
                    await interaction.followup.send(f"⛔ Stock insuffisant ! Il ne reste que {fresh['stock']} en stock.")
                    return
                await conn.execute("UPDATE shop_items SET stock = stock - $2 WHERE id = $1", item["id"], quantite)

            await conn.execute("UPDATE players SET berrys = berrys - $3 WHERE guild_id = $1 AND user_id = $2",
                                interaction.guild_id, interaction.user.id, cout_total)

            if item["slot"] is None:
                existing = await conn.fetchrow(
                    "SELECT id FROM inventory WHERE guild_id = $1 AND user_id = $2 AND item_id = $3",
                    interaction.guild_id, interaction.user.id, item["id"]
                )
                if existing:
                    await conn.execute("UPDATE inventory SET quantite = quantite + $2 WHERE id = $1", existing["id"], quantite)
                else:
                    await conn.execute(
                        "INSERT INTO inventory (guild_id, user_id, item_id, quantite, durabilite) VALUES ($1,$2,$3,$4,$5)",
                        interaction.guild_id, interaction.user.id, item["id"], quantite, item["durabilite_max"]
                    )
            else:
                for _ in range(quantite):
                    await conn.execute(
                        "INSERT INTO inventory (guild_id, user_id, item_id, quantite, durabilite) VALUES ($1,$2,$3,1,$4)",
                        interaction.guild_id, interaction.user.id, item["id"], item["durabilite_max"]
                    )

    await add_reputation_marchand(interaction.guild_id, interaction.user.id)

    description = f"Tu as acheté **{quantite}x {item['nom']}** pour **{cout_total:,}฿**."
    if discount > 0:
        description += f" (réduction fidélité -{discount}% appliquée)"
    embed = discord.Embed(title="✅ Achat effectué !", description=description, color=0x27AE60)
    embed.set_footer(text="🌊 One Piece Bot • Marché")
    await interaction.followup.send(embed=embed)


def setup_marche_commands(bot):
    bot.tree.add_command(marche_group)
