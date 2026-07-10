import discord
from discord import app_commands
from utils.players import get_player
from utils.channel_check import require_salon
from utils.succes import get_succes_status, claim_succes

STATUT_EMOJIS = {"reclame": "✅", "atteignable": "🎉", "non_atteint": "🔒"}


class SuccesClaimButton(discord.ui.Button):
    def __init__(self, guild_id, user_id, code, titre):
        super().__init__(label=f"Réclamer : {titre[:60]}", emoji="🎁", style=discord.ButtonStyle.success)
        self.guild_id = guild_id
        self.user_id = user_id
        self.code = code

    async def callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("⛔ Ce ne sont pas tes succès !", ephemeral=True)
            return
        await interaction.response.defer()
        player = await get_player(self.guild_id, self.user_id)
        resultat = await claim_succes(self.guild_id, self.user_id, player, self.code)
        if resultat is None:
            await interaction.followup.send("Ce succès n'est plus réclamable.", ephemeral=True)
            return
        titre, berrys = resultat
        await interaction.followup.send(f"🏆 Succès **{titre}** débloqué ! +{berrys:,}฿", ephemeral=True)


class SuccesView(discord.ui.View):
    def __init__(self, guild_id, user_id, statuts):
        super().__init__(timeout=60)
        for s in statuts:
            if s["statut"] == "atteignable":
                self.add_item(SuccesClaimButton(guild_id, user_id, s["code"], s["titre"]))


@app_commands.command(name="succes", description="Voir tes succès et hauts faits")
@require_salon("salon_succes")
async def succes(interaction: discord.Interaction):
    await interaction.response.defer()
    player = await get_player(interaction.guild_id, interaction.user.id)
    if player is None:
        await interaction.followup.send("Tu n'as pas encore de personnage ! Lance `/commencer` pour débuter l'aventure 🏴‍☠️")
        return

    statuts = await get_succes_status(interaction.guild_id, interaction.user.id, player)
    nb_reclames = sum(1 for s in statuts if s["statut"] == "reclame")

    embed = discord.Embed(title="🏆 Tes succès", description=f"{nb_reclames}/{len(statuts)} débloqués", color=0xD4A017)
    for s in statuts:
        emoji = STATUT_EMOJIS[s["statut"]]
        valeur = s["description"]
        if s["statut"] == "atteignable":
            valeur += f"\n🎁 Réclamable : +{s['berrys']:,}฿"
        embed.add_field(name=f"{emoji} {s['titre']}", value=valeur, inline=False)
    embed.set_footer(text="🌊 One Piece Bot • Succès")

    has_claimable = any(s["statut"] == "atteignable" for s in statuts)
    if has_claimable:
        await interaction.followup.send(embed=embed, view=SuccesView(interaction.guild_id, interaction.user.id, statuts))
    else:
        await interaction.followup.send(embed=embed)


def setup_succes_commands(bot):
    bot.tree.add_command(succes)
