import discord
from discord import app_commands
from utils.players import get_player
from utils.channel_check import require_salon
from utils.succes import get_family_status, get_overview, claim_succes
from data.succes import FAMILLES

STATUT_EMOJIS = {"reclame": "✅", "atteignable": "🎉", "non_atteint": "🔒"}


def build_embed(nom_famille, statuts):
    embed = discord.Embed(title=f"🏆 Succès — {nom_famille}", color=0xD4A017)
    for s in statuts:
        emoji = STATUT_EMOJIS[s["statut"]]
        valeur = s["description"]
        if s["statut"] == "atteignable":
            valeur += f"\n🎁 Réclamable : +{s['berrys']:,}฿"
        embed.add_field(name=f"{emoji} {s['titre']}", value=valeur, inline=False)
    embed.set_footer(text="🌊 One Piece Bot • Succès")
    return embed


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


class FamilleSelect(discord.ui.Select):
    def __init__(self, guild_id, user_id):
        self.guild_id = guild_id
        self.user_id = user_id
        options = [discord.SelectOption(label=nom, value=key) for key, (nom, _, _) in FAMILLES.items()]
        super().__init__(placeholder="Choisis une catégorie de succès...", options=options, custom_id="succes_select")

    async def callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("⛔ Ce ne sont pas tes succès !", ephemeral=True)
            return
        player = await get_player(self.guild_id, self.user_id)
        nom, statuts = await get_family_status(self.guild_id, self.user_id, player, self.values[0])
        embed = build_embed(nom, statuts)
        new_view = SuccesView(self.guild_id, self.user_id, statuts)
        await interaction.response.edit_message(embed=embed, view=new_view)


class SuccesView(discord.ui.View):
    def __init__(self, guild_id, user_id, statuts):
        super().__init__(timeout=120)
        self.add_item(FamilleSelect(guild_id, user_id))
        for s in statuts:
            if s["statut"] == "atteignable":
                self.add_item(SuccesClaimButton(guild_id, user_id, s["code"], s["titre"]))


@app_commands.command(name="succes", description="Voir tes succès et hauts faits, classés par catégorie")
@require_salon("salon_succes")
async def succes(interaction: discord.Interaction):
    await interaction.response.defer()
    player = await get_player(interaction.guild_id, interaction.user.id)
    if player is None:
        await interaction.followup.send("Tu n'as pas encore de personnage ! Lance `/commencer` pour débuter l'aventure 🏴‍☠️")
        return

    reclames, total = await get_overview(interaction.guild_id, interaction.user.id, player)
    premiere_famille = next(iter(FAMILLES))
    nom, statuts = await get_family_status(interaction.guild_id, interaction.user.id, player, premiere_famille)

    embed = build_embed(nom, statuts)
    embed.description = f"**{reclames}/{total}** succès débloqués au total, toutes catégories confondues."

    view = SuccesView(interaction.guild_id, interaction.user.id, statuts)
    await interaction.followup.send(embed=embed, view=view)


def setup_succes_commands(bot):
    bot.tree.add_command(succes)
