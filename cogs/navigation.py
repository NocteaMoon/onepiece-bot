import discord
from discord import app_commands
import random
from database.db import get_pool
from utils.players import get_player, add_xp
from utils.channel_check import require_salon
from utils.announcements import announce_level_up
from utils.quetes import increment_quest_progress
from data.mers import MERS

MER_CHOICES = [app_commands.Choice(name=f"{nom} (niv. {niv}+)", value=nom) for nom, niv, _, _, _ in MERS]

EVENEMENTS = [
    ("calme", 40),
    ("courant_favorable", 20),
    ("tempete_legere", 15),
    ("decouverte", 10),
    ("rencontre_suspecte", 8),
    ("tempete_violente", 5),
    ("naufrage", 2),
]

@app_commands.command(name="voyager", description="Voyager vers une autre mer")
@app_commands.describe(destination="La mer vers laquelle naviguer")
@app_commands.choices(destination=MER_CHOICES)
@require_salon("salon_exploration")
async def voyager(interaction: discord.Interaction, destination: app_commands.Choice[str]):
    await interaction.response.defer()
    player = await get_player(interaction.guild_id, interaction.user.id)
    if player is None:
        await interaction.followup.send("Tu n'as pas encore de personnage ! Lance `/commencer` pour débuter l'aventure 🏴‍☠️")
        return

    mer_data = next((m for m in MERS if m[0] == destination.value), None)
    if not mer_data:
        await interaction.followup.send("Destination introuvable.")
        return
    nom_mer, niveau_requis, cout_berrys, cout_endurance, ile_arrivee = mer_data

    if player["mer"] == nom_mer:
        await interaction.followup.send(f"Tu navigues déjà sur **{nom_mer}** !")
        return
    if player["niveau"] < niveau_requis:
        await interaction.followup.send(f"⛔ **{nom_mer}** nécessite d'être niveau **{niveau_requis}** (tu es niveau {player['niveau']}). Continue à progresser !")
        return
    if player["berrys"] < cout_berrys:
        await interaction.followup.send(f"⛔ Le voyage vers **{nom_mer}** coûte **{cout_berrys:,}฿** de provisions, tu n'as que {player['berrys']:,}฿.")
        return
    if player["endurance"] < cout_endurance:
        await interaction.followup.send(f"😮‍💨 Il te faut **{cout_endurance}** endurance pour ce voyage (tu as {player['endurance']}). Repose-toi un peu !")
        return

    protege = player["voyage_protege"] > 0
    if protege:
        evenement = "calme"
    else:
        evenement = random.choices([e[0] for e in EVENEMENTS], weights=[e[1] for e in EVENEMENTS], k=1)[0]

    pv_perte = 0
    endurance_extra = 0
    berrys_bonus = 0
    berrys_perte = 0
    durabilite_perte = 0
    xp_bonus = 0

    if evenement == "calme":
        if protege:
            message = f"🧭 Grâce aux conseils avisés d'un Navigateur, la traversée vers **{nom_mer}** se déroule sans le moindre accroc !"
        else:
            message = f"La traversée vers **{nom_mer}** se déroule sans encombre, sous un ciel dégagé."
    elif evenement == "courant_favorable":
        endurance_extra = -5
        xp_bonus = 10
        message = f"Un courant favorable te porte vers **{nom_mer}** plus vite que prévu !"
    elif evenement == "tempete_legere":
        endurance_extra = 10
        message = f"Une tempête légère secoue le navire durant la traversée vers **{nom_mer}**, mais rien de grave."
    elif evenement == "decouverte":
        berrys_bonus = random.randint(20, 50)
        message = f"En chemin vers **{nom_mer}**, tu récupères une épave à la dérive contenant **{berrys_bonus} Berrys** !"
    elif evenement == "rencontre_suspecte":
        berrys_perte = max(min(player["berrys"] - cout_berrys, random.randint(10, 30)), 0)
        message = f"Un navire suspect te suit un moment durant la traversée vers **{nom_mer}**... tu parviens à le semer, mais pas sans perdre **{berrys_perte} Berrys** tombés à l'eau dans la manœuvre."
    elif evenement == "tempete_violente":
        pv_perte = random.randint(15, 30)
        endurance_extra = 15
        durabilite_perte = random.randint(5, 15)
        message = f"Une violente tempête frappe le navire en route vers **{nom_mer}** ! Tu es secoué (-{pv_perte} PV) et ton équipement en pâtit."
    elif evenement == "naufrage":
        pv_perte = random.randint(30, 50)
        endurance_extra = 25
        durabilite_perte = random.randint(15, 30)
        message = f"⚠️ **Naufrage !** Le navire chavire en approchant de **{nom_mer}**. Tu t'en sors de justesse, bien amoché."

    pool = get_pool()
    async with pool.acquire() as conn:
        async with conn.transaction():
            current = await conn.fetchrow(
                "SELECT pv, endurance, equip_arme_principale, equip_corps FROM players WHERE guild_id=$1 AND user_id=$2",
                interaction.guild_id, interaction.user.id
            )
            nouveau_pv = max(1, current["pv"] - pv_perte)
            nouvelle_endurance = max(0, current["endurance"] - cout_endurance - endurance_extra)

            await conn.execute("""
                UPDATE players SET
                    mer = $3, ile = $4,
                    berrys = berrys - $5 + $6,
                    pv = $7, endurance = $8
                WHERE guild_id=$1 AND user_id=$2
            """, interaction.guild_id, interaction.user.id, nom_mer, ile_arrivee,
                 cout_berrys + berrys_perte, berrys_bonus, nouveau_pv, nouvelle_endurance)

            if protege:
                await conn.execute(
                    "UPDATE players SET voyage_protege = GREATEST(0, voyage_protege - 1) WHERE guild_id=$1 AND user_id=$2",
                    interaction.guild_id, interaction.user.id
                )

            if durabilite_perte > 0:
                for item_id in [current["equip_arme_principale"], current["equip_corps"]]:
                    if item_id:
                        await conn.execute("""
                            UPDATE inventory SET durabilite = GREATEST(0, durabilite - $3)
                            WHERE guild_id=$1 AND user_id=$2 AND item_id=$4 AND equipe = TRUE
                        """, interaction.guild_id, interaction.user.id, durabilite_perte, item_id)

    await increment_quest_progress(interaction.guild_id, interaction.user.id, "voyager")

    xp_gain = 15 + xp_bonus
    niveaux_gagnes, nouveau_niveau = await add_xp(interaction.guild_id, interaction.user.id, xp_gain, 8)

    embed = discord.Embed(title="⛵ Voyage en mer", description=message, color=0x1B3A5C)
    footer_bits = [f"Arrivée : {nom_mer}", f"+{xp_gain} XP"]
    if cout_berrys + berrys_perte:
        footer_bits.insert(1, f"-{cout_berrys + berrys_perte}฿")
    embed.set_footer(text="🌊 One Piece Bot • " + " • ".join(footer_bits))
    await interaction.followup.send(embed=embed)

    if niveaux_gagnes > 0:
        await announce_level_up(interaction, interaction.user, nouveau_niveau)


def setup_navigation_commands(bot):
    bot.tree.add_command(voyager)
