import discord
from discord import app_commands
import random
import datetime
from database.db import get_pool
from utils.players import get_player
from utils.channel_check import require_salon
from utils.quetes import increment_quest_progress

economie_group = app_commands.Group(name="economie", description="Commandes d'économie")

TRAVAUX = [
    ("Tu as aidé un pêcheur à remonter ses filets", 30, 60),
    ("Tu as servi des clients dans une taverne bondée", 25, 55),
    ("Tu as réparé la coque d'un navire marchand", 40, 80),
    ("Tu as livré des caisses de fruits au marché", 20, 50),
    ("Tu as nettoyé le pont d'un galion", 15, 45),
    ("Tu as aidé un cartographe à recopier des cartes", 35, 70),
    ("Tu as fait le guet pour des dockers pressés", 25, 60),
    ("Tu as cuisiné pour l'équipage d'un navire de passage", 30, 65),
    ("Tu as vendu des journaux à la criée", 15, 40),
    ("Tu as aidé un forgeron à la forge toute la matinée", 45, 85),
    ("Tu as porté les bagages de riches voyageurs", 20, 55),
    ("Tu as participé à la récolte dans une ferme voisine", 25, 60),
    ("Tu as chanté dans une taverne pour divertir les clients", 20, 70),
    ("Tu as aidé le médecin du village à trier ses remèdes", 35, 65),
    ("Tu as gardé l'étal d'un marchand pendant sa pause", 20, 50),
]

COOLDOWN_TRAVAIL_MINUTES = 30
_last_work = {}

async def require_player(interaction: discord.Interaction):
    player = await get_player(interaction.guild_id, interaction.user.id)
    if player is None:
        await interaction.followup.send("Tu n'as pas encore de personnage ! Lance `/commencer` pour débuter l'aventure 🏴‍☠️")
        return None
    return player

@economie_group.command(name="travailler", description="Faire un petit boulot pour gagner des Berrys")
@require_salon("salon_economie")
async def travailler(interaction: discord.Interaction):
    await interaction.response.defer()
    player = await require_player(interaction)
    if player is None:
        return

    key = (interaction.guild_id, interaction.user.id)
    now = datetime.datetime.utcnow()
    last = _last_work.get(key)
    if last:
        elapsed = (now - last).total_seconds() / 60
        if elapsed < COOLDOWN_TRAVAIL_MINUTES:
            restant = int(COOLDOWN_TRAVAIL_MINUTES - elapsed)
            await interaction.followup.send(f"😮‍💨 Tu es fatigué ! Repose-toi encore **{restant} min** avant de retravailler.")
            return

    travail, gain_min, gain_max = random.choice(TRAVAUX)
    gain = random.randint(gain_min, gain_max)
    _last_work[key] = now

    pool = get_pool()
    async with pool.acquire() as conn:
        await conn.execute(
            "UPDATE players SET berrys = berrys + $3 WHERE guild_id = $1 AND user_id = $2",
            interaction.guild_id, interaction.user.id, gain
        )

    await increment_quest_progress(interaction.guild_id, interaction.user.id, "travailler")

    embed = discord.Embed(
        title="💼 Travail terminé !",
        description=f"{travail}.\n\n💰 Tu gagnes **{gain} Berrys** !",
        color=0xF4C430
    )
    embed.set_footer(text="🌊 One Piece Bot • Économie")
    await interaction.followup.send(embed=embed)


banque_group = app_commands.Group(name="banque", description="Gérer ton compte en banque", parent=economie_group)

@banque_group.command(name="depot", description="Déposer des Berrys en banque (protégés en cas de défaite)")
@app_commands.describe(montant="Le montant à déposer")
async def banque_depot(interaction: discord.Interaction, montant: int):
    await interaction.response.defer()
    player = await require_player(interaction)
    if player is None:
        return
    if montant <= 0:
        await interaction.followup.send("Le montant doit être positif 🙃")
        return
    if montant > player["berrys"]:
        await interaction.followup.send(f"Tu n'as que **{player['berrys']:,} ฿** en liquide !")
        return

    pool = get_pool()
    async with pool.acquire() as conn:
        await conn.execute(
            "UPDATE players SET berrys = berrys - $3, banque = banque + $3 WHERE guild_id = $1 AND user_id = $2",
            interaction.guild_id, interaction.user.id, montant
        )
    await interaction.followup.send(f"🏦 **{montant:,} ฿** déposés en banque. Tes économies sont à l'abri !")

@banque_group.command(name="retrait", description="Retirer des Berrys de la banque")
@app_commands.describe(montant="Le montant à retirer")
async def banque_retrait(interaction: discord.Interaction, montant: int):
    await interaction.response.defer()
    player = await require_player(interaction)
    if player is None:
        return
    if montant <= 0:
        await interaction.followup.send("Le montant doit être positif 🙃")
        return
    if montant > player["banque"]:
        await interaction.followup.send(f"Tu n'as que **{player['banque']:,} ฿** en banque !")
        return

    pool = get_pool()
    async with pool.acquire() as conn:
        await conn.execute(
            "UPDATE players SET berrys = berrys + $3, banque = banque - $3 WHERE guild_id = $1 AND user_id = $2",
            interaction.guild_id, interaction.user.id, montant
        )
    await interaction.followup.send(f"🏦 **{montant:,} ฿** retirés de la banque.")

@banque_group.command(name="solde", description="Voir ton solde (liquide + banque)")
async def banque_solde(interaction: discord.Interaction):
    await interaction.response.defer()
    player = await require_player(interaction)
    if player is None:
        return
    embed = discord.Embed(title="🏦 Ton compte", color=0xF4C430)
    embed.add_field(name="💰 Liquide", value=f"{player['berrys']:,} ฿", inline=True)
    embed.add_field(name="🏦 Banque", value=f"{player['banque']:,} ฿", inline=True)
    embed.add_field(name="💎 Total", value=f"{player['berrys'] + player['banque']:,} ฿", inline=True)
    embed.set_footer(text="🌊 One Piece Bot • Économie")
    await interaction.followup.send(embed=embed)


@economie_group.command(name="donner", description="Donner des Berrys à un autre joueur")
@app_commands.describe(membre="Le joueur qui reçoit", montant="Le montant à donner")
async def donner(interaction: discord.Interaction, membre: discord.Member, montant: int):
    await interaction.response.defer()
    player = await require_player(interaction)
    if player is None:
        return
    if membre.id == interaction.user.id:
        await interaction.followup.send("Tu ne peux pas te donner des Berrys à toi-même 🙃")
        return
    if membre.bot:
        await interaction.followup.send("Les bots n'ont pas besoin de Berrys 🤖")
        return
    if montant <= 0:
        await interaction.followup.send("Le montant doit être positif 🙃")
        return
    if montant > player["berrys"]:
        await interaction.followup.send(f"Tu n'as que **{player['berrys']:,} ฿** en liquide !")
        return

    cible = await get_player(interaction.guild_id, membre.id)
    if cible is None:
        await interaction.followup.send(f"{membre.display_name} n'a pas encore de personnage !")
        return

    pool = get_pool()
    async with pool.acquire() as conn:
        async with conn.transaction():
            await conn.execute(
                "UPDATE players SET berrys = berrys - $3 WHERE guild_id = $1 AND user_id = $2",
                interaction.guild_id, interaction.user.id, montant
            )
            await conn.execute(
                "UPDATE players SET berrys = berrys + $3 WHERE guild_id = $1 AND user_id = $2",
                interaction.guild_id, membre.id, montant
            )

    embed = discord.Embed(
        title="🤝 Transfert effectué",
        description=f"{interaction.user.mention} a donné **{montant:,} ฿** à {membre.mention} !",
        color=0xF4C430
    )
    embed.set_footer(text="🌊 One Piece Bot • Économie")
    await interaction.followup.send(embed=embed)


def setup_economie_commands(bot):
    bot.tree.add_command(economie_group)
