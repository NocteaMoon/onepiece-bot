import discord
import random
from database.db import get_pool
from utils.players import get_player, add_xp
from utils.shop import get_item_by_name
from utils.announcements import announce_level_up

COUT_ENDURANCE_COLLECTE = 10

async def do_gather(interaction: discord.Interaction, titre: str, verbe_action: str, lieux: list, pool_ingredients: list, couleur: int):
    await interaction.response.defer()
    player = await get_player(interaction.guild_id, interaction.user.id)
    if player is None:
        await interaction.followup.send("Tu n'as pas encore de personnage ! Lance `/commencer` pour débuter l'aventure 🏴‍☠️")
        return

    if player["endurance"] < COUT_ENDURANCE_COLLECTE:
        await interaction.followup.send(
            f"😮‍💨 Tu es trop fatigué (il te faut {COUT_ENDURANCE_COLLECTE} endurance, tu as {player['endurance']}). "
            f"Ton endurance se régénère avec le temps."
        )
        return

    lieu = random.choice(lieux)
    noms = [p[0] for p in pool_ingredients]
    poids = [p[1] for p in pool_ingredients]
    resultat = random.choices(noms, weights=poids, k=1)[0]

    xp_gain = random.randint(4, 10)
    xpc_gain = random.randint(2, 5)

    db_pool = get_pool()
    async with db_pool.acquire() as conn:
        async with conn.transaction():
            await conn.execute(
                "UPDATE players SET endurance = endurance - $3 WHERE guild_id=$1 AND user_id=$2",
                interaction.guild_id, interaction.user.id, COUT_ENDURANCE_COLLECTE
            )
            if resultat != "RIEN":
                item = await get_item_by_name(interaction.guild_id, resultat)
                if item:
                    existing = await conn.fetchrow(
                        "SELECT id FROM inventory WHERE guild_id=$1 AND user_id=$2 AND item_id=$3",
                        interaction.guild_id, interaction.user.id, item["id"]
                    )
                    if existing:
                        await conn.execute("UPDATE inventory SET quantite = quantite + 1 WHERE id=$1", existing["id"])
                    else:
                        await conn.execute(
                            "INSERT INTO inventory (guild_id, user_id, item_id, quantite, durabilite) VALUES ($1,$2,$3,1,$4)",
                            interaction.guild_id, interaction.user.id, item["id"], item["durabilite_max"]
                        )

    niveaux_gagnes, nouveau_niveau = await add_xp(interaction.guild_id, interaction.user.id, xp_gain, xpc_gain)

    if resultat == "RIEN":
        message = f"Tu {verbe_action} {lieu} mais ne trouves rien cette fois-ci."
    else:
        message = f"Tu {verbe_action} {lieu} et obtiens **{resultat}** !"

    embed = discord.Embed(title=titre, description=message, color=couleur)
    embed.set_footer(text=f"🌊 One Piece Bot • +{xp_gain} XP • -{COUT_ENDURANCE_COLLECTE} endurance")
    await interaction.followup.send(embed=embed)

    if niveaux_gagnes > 0:
        await announce_level_up(interaction, interaction.user, nouveau_niveau)
