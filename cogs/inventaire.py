import discord
from discord import app_commands
from database.db import get_pool
from utils.players import get_player
from utils.shop import get_inventory
from utils.buffs import apply_buff
from data.buffs_cuisine import BUFFS_CUISINE

SLOT_LABELS = {
    "arme_principale": "Arme principale",
    "arme_secondaire": "Arme secondaire",
    "tete": "Tête",
    "corps": "Corps",
    "accessoire1": "Accessoire 1",
    "accessoire2": "Accessoire 2",
    "navire": "Navire",
}

DESEQUIPER_CHOICES = [app_commands.Choice(name=v, value=k) for k, v in SLOT_LABELS.items()]

inventaire_group = app_commands.Group(name="inventaire", description="Gérer ton inventaire et ton équipement")

async def inventory_item_autocomplete(interaction: discord.Interaction, current: str):
    rows = await get_inventory(interaction.guild_id, interaction.user.id)
    filtered = [r for r in rows if current.lower() in r["nom"].lower()][:25]
    return [app_commands.Choice(name=f"{r['nom']} x{r['quantite']}" + (" (équipé)" if r["equipe"] else ""), value=r["id"]) for r in filtered]

@inventaire_group.command(name="voir", description="Voir ton inventaire")
@app_commands.describe(membre="Le membre dont tu veux voir l'inventaire (toi par défaut)")
async def inventaire_voir(interaction: discord.Interaction, membre: discord.Member = None):
    await interaction.response.defer()
    cible = membre or interaction.user
    player = await get_player(interaction.guild_id, cible.id)
    if player is None:
        await interaction.followup.send(f"{cible.display_name} n'a pas encore de personnage.")
        return
    rows = await get_inventory(interaction.guild_id, cible.id)
    if not rows:
        await interaction.followup.send(f"L'inventaire de {cible.display_name} est vide.")
        return

    embed = discord.Embed(title=f"🎒 Inventaire de {cible.display_name}", color=0x8E44AD)
    grouped = {}
    for r in rows:
        grouped.setdefault(r["categorie"], []).append(r)
    for cat, items in grouped.items():
        lines = []
        for it in items:
            etat = " ✅ équipé" if it["equipe"] else ""
            dur = f" ({it['durabilite']}/{it['durabilite_max']} durabilité)" if it["slot"] else ""
            buff_tag = " 🍳" if it["nom"] in BUFFS_CUISINE else ""
            lines.append(f"**{it['nom']}**{buff_tag} x{it['quantite']}{etat}{dur}")
        embed.add_field(name=cat, value="\n".join(lines), inline=False)
    embed.set_footer(text="🌊 One Piece Bot • Inventaire • 🍳 = donne un bonus temporaire à l'usage")
    await interaction.followup.send(embed=embed)


@inventaire_group.command(name="equiper", description="Équiper un objet de ton inventaire")
@app_commands.autocomplete(objet=inventory_item_autocomplete)
async def inventaire_equiper(interaction: discord.Interaction, objet: int):
    await interaction.response.defer()
    pool = get_pool()
    async with pool.acquire() as conn:
        inv_row = await conn.fetchrow("SELECT * FROM inventory WHERE id = $1 AND guild_id = $2 AND user_id = $3",
                                       objet, interaction.guild_id, interaction.user.id)
        if not inv_row:
            await interaction.followup.send("Cet objet n'est pas dans ton inventaire.")
            return
        item = await conn.fetchrow("SELECT * FROM shop_items WHERE id = $1", inv_row["item_id"])
        if not item or not item["slot"]:
            await interaction.followup.send("Cet objet ne peut pas être équipé.")
            return

        slot = item["slot"]
        if slot == "accessoire":
            player = await conn.fetchrow("SELECT equip_accessoire1, equip_accessoire2 FROM players WHERE guild_id=$1 AND user_id=$2",
                                          interaction.guild_id, interaction.user.id)
            if not player["equip_accessoire1"]:
                column = "equip_accessoire1"
            elif not player["equip_accessoire2"]:
                column = "equip_accessoire2"
            else:
                await interaction.followup.send("⛔ Tes deux emplacements accessoires sont déjà occupés. Déséquipe d'abord.")
                return
        else:
            column = f"equip_{slot}"

        async with conn.transaction():
            old_item_id = await conn.fetchval(f"SELECT {column} FROM players WHERE guild_id=$1 AND user_id=$2",
                                                interaction.guild_id, interaction.user.id)
            if old_item_id:
                await conn.execute("UPDATE inventory SET equipe = FALSE WHERE guild_id=$1 AND user_id=$2 AND item_id=$3 AND equipe = TRUE",
                                    interaction.guild_id, interaction.user.id, old_item_id)
            await conn.execute(f"UPDATE players SET {column} = $3 WHERE guild_id=$1 AND user_id=$2",
                                interaction.guild_id, interaction.user.id, item["id"])
            await conn.execute("UPDATE inventory SET equipe = TRUE WHERE id = $1", inv_row["id"])

    await interaction.followup.send(f"✅ **{item['nom']}** équipé !")


@inventaire_group.command(name="desequiper", description="Retirer un objet équipé")
@app_commands.choices(emplacement=DESEQUIPER_CHOICES)
async def inventaire_desequiper(interaction: discord.Interaction, emplacement: app_commands.Choice[str]):
    await interaction.response.defer()
    column = f"equip_{emplacement.value}"
    pool = get_pool()
    async with pool.acquire() as conn:
        old_item_id = await conn.fetchval(f"SELECT {column} FROM players WHERE guild_id=$1 AND user_id=$2",
                                           interaction.guild_id, interaction.user.id)
        if not old_item_id:
            await interaction.followup.send(f"Rien n'est équipé sur **{emplacement.name}**.")
            return
        async with conn.transaction():
            await conn.execute(f"UPDATE players SET {column} = NULL WHERE guild_id=$1 AND user_id=$2",
                                interaction.guild_id, interaction.user.id)
            await conn.execute("UPDATE inventory SET equipe = FALSE WHERE guild_id=$1 AND user_id=$2 AND item_id=$3 AND equipe = TRUE",
                                interaction.guild_id, interaction.user.id, old_item_id)
    await interaction.followup.send(f"✅ Objet retiré de **{emplacement.name}**.")


@inventaire_group.command(name="utiliser", description="Utiliser un consommable de ton inventaire")
@app_commands.autocomplete(objet=inventory_item_autocomplete)
async def inventaire_utiliser(interaction: discord.Interaction, objet: int):
    await interaction.response.defer()
    pool = get_pool()
    async with pool.acquire() as conn:
        inv_row = await conn.fetchrow("SELECT * FROM inventory WHERE id = $1 AND guild_id = $2 AND user_id = $3",
                                       objet, interaction.guild_id, interaction.user.id)
        if not inv_row:
            await interaction.followup.send("Cet objet n'est pas dans ton inventaire.")
            return
        item = await conn.fetchrow("SELECT * FROM shop_items WHERE id = $1", inv_row["item_id"])
        if not item or item["slot"] is not None:
            await interaction.followup.send("Cet objet ne peut pas être utilisé ainsi (ce n'est pas un consommable).")
            return
        if item["soin_pv"] == 0 and item["soin_endurance"] == 0:
            await interaction.followup.send("Cet objet n'a aucun effet à l'usage.")
            return

        async with conn.transaction():
            player = await conn.fetchrow("SELECT pv, pv_max, endurance, endurance_max FROM players WHERE guild_id=$1 AND user_id=$2",
                                          interaction.guild_id, interaction.user.id)
            new_pv = min(player["pv_max"], player["pv"] + item["soin_pv"])
            new_end = min(player["endurance_max"], player["endurance"] + item["soin_endurance"])
            await conn.execute("UPDATE players SET pv = $3, endurance = $4 WHERE guild_id=$1 AND user_id=$2",
                                interaction.guild_id, interaction.user.id, new_pv, new_end)

            if inv_row["quantite"] > 1:
                await conn.execute("UPDATE inventory SET quantite = quantite - 1 WHERE id = $1", inv_row["id"])
            else:
                await conn.execute("DELETE FROM inventory WHERE id = $1", inv_row["id"])

    description = f"PV : {player['pv']} → {new_pv}\nEndurance : {player['endurance']} → {new_end}"

    buff = BUFFS_CUISINE.get(item["nom"])
    if buff:
        stat, valeur, duree = buff
        await apply_buff(interaction.guild_id, interaction.user.id, stat, valeur, duree)
        stat_labels = {"force": "Force", "defense": "Défense", "vitesse": "Vitesse", "agilite": "Agilité"}
        description += f"\n\n🍳 **Bonus temporaire** : +{valeur} {stat_labels.get(stat, stat)} pendant {duree} minutes !"

    embed = discord.Embed(title=f"✨ {item['nom']} utilisé !", description=description, color=0x27AE60)
    embed.set_footer(text="🌊 One Piece Bot • Inventaire")
    await interaction.followup.send(embed=embed)


@inventaire_group.command(name="jeter", description="Jeter un objet de ton inventaire")
@app_commands.autocomplete(objet=inventory_item_autocomplete)
@app_commands.describe(quantite="Quantité à jeter (tout par défaut)")
async def inventaire_jeter(interaction: discord.Interaction, objet: int, quantite: int = None):
    await interaction.response.defer()
    pool = get_pool()
    async with pool.acquire() as conn:
        inv_row = await conn.fetchrow("SELECT * FROM inventory WHERE id = $1 AND guild_id = $2 AND user_id = $3",
                                       objet, interaction.guild_id, interaction.user.id)
        if not inv_row:
            await interaction.followup.send("Cet objet n'est pas dans ton inventaire.")
            return
        if inv_row["equipe"]:
            await interaction.followup.send("⛔ Déséquipe d'abord cet objet avant de le jeter.")
            return
        item = await conn.fetchrow("SELECT nom FROM shop_items WHERE id = $1", inv_row["item_id"])

        a_jeter = quantite if quantite else inv_row["quantite"]
        a_jeter = min(a_jeter, inv_row["quantite"])

        if a_jeter >= inv_row["quantite"]:
            await conn.execute("DELETE FROM inventory WHERE id = $1", inv_row["id"])
        else:
            await conn.execute("UPDATE inventory SET quantite = quantite - $2 WHERE id = $1", inv_row["id"], a_jeter)

    await interaction.followup.send(f"🗑️ Tu as jeté **{a_jeter}x {item['nom']}**.")


def setup_inventaire_commands(bot):
    bot.tree.add_command(inventaire_group)
