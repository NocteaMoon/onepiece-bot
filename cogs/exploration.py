import discord
from discord import app_commands
import random
from database.db import get_pool
from utils.players import get_player, add_xp
from utils.shop import get_random_loot
from utils.channel_check import require_salon
from utils.announcements import announce_level_up
from utils.quetes import increment_quest_progress
from utils.combat_stats import get_effective_stats
from utils.fruits import get_fruits_disponibles, manger_fruit
from utils.meteo import get_current_weather, get_modifiers

COUT_ENDURANCE = 15

FRUIT_CHANCE_BASE = 0.003
FRUIT_CHANCE_PAR_POINT = 0.0004
SECRET_CHANCE = 0.0015

LIEUX = [
    "la plage de galets", "la forêt tropicale", "les ruines abandonnées", "le vieux phare",
    "le marché flottant", "les grottes côtières", "la crique cachée", "le village de pêcheurs",
    "les collines herbeuses", "le cimetière de navires", "la jungle dense", "les marais brumeux",
    "le sentier côtier", "les rochers battus par les vents", "la clairière secrète",
]

OUTCOMES = [
    ("rien", 30, 5, 12, 2, 5),
    ("petits_berrys", 25, 8, 15, 3, 6),
    ("gros_berrys", 8, 15, 25, 5, 10),
    ("objet", 15, 10, 20, 4, 8),
    ("coffre", 6, 25, 40, 8, 15),
    ("pnj", 8, 8, 15, 3, 6),
    ("meteo", 4, 5, 10, 2, 4),
    ("tresor_cache", 1, 50, 80, 15, 25),
    ("empreintes", 3, 10, 15, 5, 10),
]

# Réaction du PNJ selon la Notoriété du joueur : (seuil, texte, multiplicateur de Berrys)
NOTORIETE_PNJ_TIERS = [
    (500, "une foule enthousiaste s'attroupe pour te saluer, ta réputation te précède partout", 1.5),
    (200, "un marin, visiblement impressionné par ta réputation, t'offre volontiers quelques Berrys", 1.3),
    (50, "un vieux marin qui semble te reconnaître te confie quelques Berrys", 1.15),
    (0, "un vieux marin te confie quelques Berrys en souvenir d'une autre époque", 1.0),
]

def get_pnj_reaction(notoriete: int):
    for seuil, texte, mult in NOTORIETE_PNJ_TIERS:
        if notoriete >= seuil:
            return texte, mult
    return NOTORIETE_PNJ_TIERS[-1][1], NOTORIETE_PNJ_TIERS[-1][2]


@app_commands.command(name="explorer", description="Explorer les environs pour trouver des ressources")
@require_salon("salon_exploration")
async def explorer(interaction: discord.Interaction):
    await interaction.response.defer()
    player = await get_player(interaction.guild_id, interaction.user.id)
    if player is None:
        await interaction.followup.send("Tu n'as pas encore de personnage ! Lance `/commencer` pour débuter l'aventure 🏴‍☠️")
        return

    if player["endurance"] < COUT_ENDURANCE:
        await interaction.followup.send(
            f"😮‍💨 Tu es trop fatigué pour explorer (il te faut {COUT_ENDURANCE} endurance, "
            f"tu as {player['endurance']}). Ton endurance se régénère avec le temps, patiente un peu !"
        )
        return

    meteo_nom = await get_current_weather(interaction.guild_id)
    mods = get_modifiers(meteo_nom)

    # Chance ultra-rare de tomber sur un Fruit du Démon, influencée par la stat Chance cachée
    if not player["fruit"]:
        fruits_dispo = await get_fruits_disponibles(interaction.guild_id)
        if fruits_dispo:
            eff = await get_effective_stats(interaction.guild_id, interaction.user.id, player)
            chance_fruit = FRUIT_CHANCE_BASE + eff["chance"] * FRUIT_CHANCE_PAR_POINT
            if random.random() < chance_fruit:
                fruit_tire = random.choice(fruits_dispo)
                code, nom, categorie, description, bonus, prix, poids = fruit_tire
                ok = await manger_fruit(interaction.guild_id, interaction.user.id, code)
                if ok:
                    pool = get_pool()
                    async with pool.acquire() as conn:
                        await conn.execute(
                            "UPDATE players SET endurance = endurance - $3 WHERE guild_id=$1 AND user_id=$2",
                            interaction.guild_id, interaction.user.id, COUT_ENDURANCE
                        )
                    niveaux_gagnes, nouveau_niveau = await add_xp(interaction.guild_id, interaction.user.id, 40, 20)
                    await increment_quest_progress(interaction.guild_id, interaction.user.id, "explorer")

                    embed = discord.Embed(
                        title="🍈 DÉCOUVERTE INCROYABLE !",
                        description=(
                            f"En explorant, tu trouves un fruit à l'apparence étrange... N'écoutant que ta curiosité, "
                            f"tu le manges sur-le-champ !\n\n**{nom}** ({categorie})\n{description}\n\n"
                            f"Tu ne pourras plus jamais nager, mais ses pouvoirs sont désormais tiens !"
                        ),
                        color=0x8E44AD
                    )
                    embed.set_footer(text="🌊 One Piece Bot • Fruit du Démon")
                    await interaction.followup.send(embed=embed)
                    if niveaux_gagnes > 0:
                        await announce_level_up(interaction, interaction.user, nouveau_niveau)
                    return

    # Découverte secrète ultra-rare, une seule fois par joueur
    if not player["secret_trouve"]:
        if random.random() < SECRET_CHANCE:
            gain_secret = random.randint(200, 400)
            pool = get_pool()
            async with pool.acquire() as conn:
                await conn.execute(
                    "UPDATE players SET endurance = endurance - $3, berrys = berrys + $4, chance = chance + 3, secret_trouve = TRUE WHERE guild_id=$1 AND user_id=$2",
                    interaction.guild_id, interaction.user.id, COUT_ENDURANCE, gain_secret
                )
            niveaux_gagnes, nouveau_niveau = await add_xp(interaction.guild_id, interaction.user.id, 50, 25)
            await increment_quest_progress(interaction.guild_id, interaction.user.id, "explorer")

            embed = discord.Embed(
                title="✨ Une trouvaille hors du commun...",
                description=(
                    f"Au détour d'un rocher, tu découvres une bouteille scellée depuis des lustres, "
                    f"un message à demi-effacé roulé à l'intérieur... Personne d'autre n'a jamais mis la main dessus.\n\n"
                    f"🎁 **{gain_secret}฿** et un éclat de chance qui semble te suivre désormais (+3 Chance, permanent) !"
                ),
                color=0xF1C40F
            )
            embed.set_footer(text="🌊 One Piece Bot • ???")
            await interaction.followup.send(embed=embed)
            if niveaux_gagnes > 0:
                await announce_level_up(interaction, interaction.user, nouveau_niveau)
            return

    lieu = random.choice(LIEUX)
    outcomes_ajustes = []
    for name, poids, xp_min, xp_max, xpc_min, xpc_max in OUTCOMES:
        if name == "rien":
            poids = poids * mods["rien_explorer"]
        outcomes_ajustes.append((name, poids, xp_min, xp_max, xpc_min, xpc_max))
    outcome = random.choices(outcomes_ajustes, weights=[o[1] for o in outcomes_ajustes], k=1)[0]
    type_, _, xp_min, xp_max, xpc_min, xpc_max = outcome

    xp_gain = random.randint(xp_min, xp_max)
    xpc_gain = random.randint(xpc_min, xpc_max)
    berrys_gain = 0
    item = None
    endurance_cost = COUT_ENDURANCE
    message = ""

    if type_ == "rien":
        message = f"Tu explores {lieu} mais ne trouves rien de particulier cette fois-ci."
    elif type_ == "petits_berrys":
        berrys_gain = round(random.randint(10, 30) * mods["berrys_explorer"])
        message = f"Tu explores {lieu} et trouves **{berrys_gain} Berrys** abandonnés au sol !"
    elif type_ == "gros_berrys":
        berrys_gain = round(random.randint(40, 90) * mods["berrys_explorer"])
        message = f"En fouillant {lieu}, tu déniches une bourse oubliée contenant **{berrys_gain} Berrys** !"
    elif type_ == "objet":
        item = await get_random_loot(interaction.guild_id, player["faction"])
        if item:
            message = f"En explorant {lieu}, tu mets la main sur **{item['nom']}** !"
        else:
            berrys_gain = round(random.randint(10, 25) * mods["berrys_explorer"])
            message = f"Tu explores {lieu} et trouves **{berrys_gain} Berrys** à la place."
    elif type_ == "coffre":
        berrys_gain = round(random.randint(50, 100) * mods["berrys_explorer"])
        message = f"En fouillant {lieu}, tu découvres un coffre entrouvert contenant **{berrys_gain} Berrys** !"
    elif type_ == "pnj":
        reaction_texte, reaction_mult = get_pnj_reaction(player["notoriete"])
        berrys_gain = round(random.randint(10, 25) * mods["berrys_explorer"] * reaction_mult)
        message = f"En explorant {lieu}, {reaction_texte} : **{berrys_gain} Berrys** !"
    elif type_ == "meteo":
        endurance_cost += 10
        message = f"Une pluie soudaine te surprend alors que tu explores {lieu}. Tu es plus fatigué que prévu (endurance supplémentaire dépensée)."
    elif type_ == "tresor_cache":
        berrys_gain = round(random.randint(150, 300) * mods["berrys_explorer"])
        message = f"🌟 **INCROYABLE !** En fouillant minutieusement {lieu}, tu déterres un véritable **trésor caché** : **{berrys_gain} Berrys** !"
    elif type_ == "empreintes":
        message = f"En explorant {lieu}, tu remarques d'étranges empreintes... quelque chose — ou quelqu'un — est passé par là récemment. 👣"

    pool = get_pool()
    async with pool.acquire() as conn:
        async with conn.transaction():
            await conn.execute(
                "UPDATE players SET endurance = endurance - $3, berrys = berrys + $4 WHERE guild_id=$1 AND user_id=$2",
                interaction.guild_id, interaction.user.id, endurance_cost, berrys_gain
            )
            if item:
                if item["slot"] is None:
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
                else:
                    await conn.execute(
                        "INSERT INTO inventory (guild_id, user_id, item_id, quantite, durabilite) VALUES ($1,$2,$3,1,$4)",
                        interaction.guild_id, interaction.user.id, item["id"], item["durabilite_max"]
                    )

    niveaux_gagnes, nouveau_niveau = await add_xp(interaction.guild_id, interaction.user.id, xp_gain, xpc_gain)
    await increment_quest_progress(interaction.guild_id, interaction.user.id, "explorer")

    embed = discord.Embed(title=f"🗺️ Exploration — {player['ile']}", description=message, color=0x1B3A5C)
    embed.set_footer(text=f"🌊 One Piece Bot • +{xp_gain} XP • -{endurance_cost} endurance")
    await interaction.followup.send(embed=embed)

    if niveaux_gagnes > 0:
        await announce_level_up(interaction, interaction.user, nouveau_niveau)


def setup_exploration_commands(bot):
    bot.tree.add_command(explorer)
