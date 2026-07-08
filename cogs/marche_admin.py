import discord
from discord import app_commands
from database.db import get_pool
from cogs.admin import config_group
from utils.shop import get_item_by_id

marche_admin_group = app_commands.Group(name="marche", description="Gérer les objets du marché", parent=config_group)

FACTION_CHOICES = [
    app_commands.Choice(name="Tous", value="Tous"),
    app_commands.Choice(name="Pirate", value="Pirate"),
    app_commands.Choice(name="Marine", value="Marine"),
    app_commands.Choice(name="Révolutionnaire", value="Révolutionnaire"),
]

RARETE_CHOICES = [
    app_commands.Choice(name="Commun", value="Commun"),
    app_commands.Choice(name="Aiguisé", value="Aiguisé"),
    app_commands.Choice(name="Grade", value="Grade"),
    app_commands.Choice(name="Grand Grade", value="Grand Grade"),
    app_commands.Choice(name="Suprême", value="Suprême"),
    app_commands.Choice(name="Mythique", value="Mythique"),
]

CATEGORIE_CHOICES = [
    app_commands.Choice(name="Consommable", value="Consommable"),
    app_commands.Choice(name="Accessoire", value="Accessoire"),
    app_commands.Choice(name="Tête", value="Tête"),
    app_commands.Choice(name="Corps", value="Corps"),
    app_commands.Choice(name="Navire", value="Navire"),
    app_commands.Choice(name="Arme", value="Arme"),
]

SLOT_CHOICES = [
    app_commands.Choice(name="Aucun (consommable)", value="aucun"),
    app_commands.Choice(name="Arme principale", value="arme_principale"),
    app_commands.Choice(name="Arme secondaire", value="arme_secondaire"),
    app_commands.Choice(name="Tête", value="tete"),
    app_commands.Choice(name="Corps", value="corps"),
    app_commands.Choice(name="Accessoire", value="accessoire"),
    app_commands.Choice(name="Navire", value="navire"),
]

@marche_admin_group.command(name="ajouter", description="Ajouter un objet au marché")
@app_commands.choices(categorie=CATEGORIE_CHOICES, faction=FACTION_CHOICES, rarete=RARETE_CHOICES, slot=SLOT_CHOICES)
async def marche_ajouter(
    interaction: discord.Interaction,
    nom: str,
    description: str,
    categorie: app_commands.Choice[str],
    faction: app_commands.Choice[str],
    rarete: app_commands.Choice[str],
    prix: int,
    slot: app_commands.Choice[str],
    bonus_force: int = 0,
    bonus_defense: int = 0,
    bonus_vitesse: int = 0,
    bonus_agilite: int = 0,
    bonus_pv: int = 0,
    bonus_chance: int = 0,
    soin_pv: int = 0,
    soin_endurance: int = 0,
    durabilite_max: int = 100,
    stock: int = -1,
    niveau_requis: int = 1,
):
    slot_value = None if slot.value == "aucun" else slot.value
    pool = get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow("""
            INSERT INTO shop_items (
                guild_id, nom, description, categorie, faction, rarete, prix, slot,
                bonus_force, bonus_defense, bonus_vitesse, bonus_agilite, bonus_pv, bonus_chance,
                soin_pv, soin_endurance, durabilite_max, stock, niveau_requis
            ) VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12,$13,$14,$15,$16,$17,$18,$19)
            RETURNING id
        """, interaction.guild_id, nom, description, categorie.value, faction.value, rarete.value, prix, slot_value,
             bonus_force, bonus_defense, bonus_vitesse, bonus_agilite, bonus_pv, bonus_chance,
             soin_pv, soin_endurance, durabilite_max, stock, niveau_requis)
    await interaction.response.send_message(f"✅ Objet **{nom}** ajouté au marché (ID #{row['id']}).", ephemeral=True)


CHAMP_CHOICES = [
    app_commands.Choice(name="Nom", value="nom"),
    app_commands.Choice(name="Description", value="description"),
    app_commands.Choice(name="Prix", value="prix"),
    app_commands.Choice(name="Stock (-1 = illimité)", value="stock"),
    app_commands.Choice(name="Niveau requis", value="niveau_requis"),
    app_commands.Choice(name="Bonus Force", value="bonus_force"),
    app_commands.Choice(name="Bonus Défense", value="bonus_defense"),
    app_commands.Choice(name="Bonus Vitesse", value="bonus_vitesse"),
    app_commands.Choice(name="Bonus Agilité", value="bonus_agilite"),
    app_commands.Choice(name="Bonus PV", value="bonus_pv"),
    app_commands.Choice(name="Bonus Chance", value="bonus_chance"),
    app_commands.Choice(name="Soin PV", value="soin_pv"),
    app_commands.Choice(name="Soin Endurance", value="soin_endurance"),
    app_commands.Choice(name="Durabilité max", value="durabilite_max"),
    app_commands.Choice(name="Actif (true/false)", value="actif"),
]

async def marche_item_autocomplete(interaction: discord.Interaction, current: str):
    pool = get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            "SELECT id, nom FROM shop_items WHERE guild_id = $1 AND nom ILIKE $2 ORDER BY nom LIMIT 25",
            interaction.guild_id, f"%{current}%"
        )
    return [app_commands.Choice(name=f"#{r['id']} — {r['nom']}", value=r["id"]) for r in rows]

@marche_admin_group.command(name="modifier", description="Modifier un champ d'un objet du marché")
@app_commands.autocomplete(objet=marche_item_autocomplete)
@app_commands.choices(champ=CHAMP_CHOICES)
async def marche_modifier(interaction: discord.Interaction, objet: int, champ: app_commands.Choice[str], valeur: str):
    item = await get_item_by_id(interaction.guild_id, objet)
    if not item:
        await interaction.response.send_message("Objet introuvable.", ephemeral=True)
        return

    champ_key = champ.value
    if champ_key in ("nom", "description"):
        parsed_value = valeur
    elif champ_key == "actif":
        parsed_value = valeur.lower() in ("true", "vrai", "oui", "1")
    else:
        try:
            parsed_value = int(valeur)
        except ValueError:
            await interaction.response.send_message("⛔ Cette valeur doit être un nombre entier.", ephemeral=True)
            return

    pool = get_pool()
    async with pool.acquire() as conn:
        await conn.execute(f"UPDATE shop_items SET {champ_key} = $2 WHERE id = $1", objet, parsed_value)
    await interaction.response.send_message(f"✅ **{item['nom']}** mis à jour : {champ.name} = {valeur}", ephemeral=True)

@marche_admin_group.command(name="supprimer", description="Retirer un objet du marché")
@app_commands.autocomplete(objet=marche_item_autocomplete)
async def marche_supprimer(interaction: discord.Interaction, objet: int):
    item = await get_item_by_id(interaction.guild_id, objet)
    if not item:
        await interaction.response.send_message("Objet introuvable.", ephemeral=True)
        return
    pool = get_pool()
    async with pool.acquire() as conn:
        await conn.execute("UPDATE shop_items SET actif = FALSE WHERE id = $1", objet)
    await interaction.response.send_message(f"✅ **{item['nom']}** retiré du marché.", ephemeral=True)

@marche_admin_group.command(name="liste", description="Voir tous les objets du marché (admin)")
async def marche_liste(interaction: discord.Interaction):
    pool = get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch("SELECT id, nom, categorie, faction, prix, actif FROM shop_items WHERE guild_id = $1 ORDER BY categorie, nom", interaction.guild_id)
    if not rows:
        await interaction.response.send_message("Aucun objet dans le marché.", ephemeral=True)
        return
    lines = []
    for r in rows:
        etat = "🟢" if r["actif"] else "🔴"
        lines.append(f"{etat} #{r['id']} — {r['nom']} ({r['categorie']}, {r['faction']}) — {r['prix']:,}฿")
    text = "\n".join(lines)
    if len(text) > 1900:
        text = text[:1900] + "\n... (liste tronquée)"
    embed = discord.Embed(title="📋 Marché — Liste complète (admin)", description=text, color=0x2C3E50)
    embed.set_footer(text="🌊 One Piece Bot • Marché admin")
    await interaction.response.send_message(embed=embed, ephemeral=True)
