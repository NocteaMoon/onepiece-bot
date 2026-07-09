import discord
from discord import app_commands
from utils.players import get_player, add_xp
from utils.channel_check import require_salon
from utils.announcements import announce_level_up
from utils.quetes import get_quests, claim_completed
from data.quetes import OBJECTIFS

PERIODE_LABELS = {"daily": "Quêtes journalières", "weekly": "Quêtes hebdomadaires"}

def barre(progres, cible, taille=10):
    rempli = round(progres / cible * taille) if cible > 0 else 0
    rempli = min(taille, rempli)
    return "🟩" * rempli + "⬜" * (taille - rempli)


class QuetesView(discord.ui.View):
    def __init__(self, guild_id, user_id):
        super().__init__(timeout=60)
        self.guild_id = guild_id
        self.user_id = user_id

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("⛔ Ce ne sont pas tes quêtes !", ephemeral=True)
            return False
        return True

    @discord.ui.button(label="Réclamer les récompenses", emoji="🎁", style=discord.ButtonStyle.success)
    async def reclamer(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        nb, berrys, xp = await claim_completed(self.guild_id, self.user_id)
        if nb == 0:
            await interaction.followup.send("Aucune quête terminée à réclamer pour l'instant.", ephemeral=True)
            return

        niveaux_gagnes, nouveau_niveau = 0, None
        if xp > 0:
            niveaux_gagnes, nouveau_niveau = await add_xp(self.guild_id, self.user_id, xp, xp // 2)

        await interaction.followup.send(
            f"🎁 {nb} quête(s) réclamée(s) : **+{berrys:,}฿** et **+{xp} XP** !", ephemeral=True
        )
        if niveaux_gagnes > 0:
            await announce_level_up(interaction, interaction.user, nouveau_niveau)


@app_commands.command(name="quetes", description="Voir tes quêtes journalières et hebdomadaires")
@require_salon("salon_quetes")
async def quetes(interaction: discord.Interaction):
    await interaction.response.defer()
    player = await get_player(interaction.guild_id, interaction.user.id)
    if player is None:
        await interaction.followup.send("Tu n'as pas encore de personnage ! Lance `/commencer` pour débuter l'aventure 🏴‍☠️")
        return

    rows = await get_quests(interaction.guild_id, interaction.user.id)

    embed = discord.Embed(title="📜 Tes quêtes", color=0xD4A017)
    for periode in ["daily", "weekly"]:
        lignes = []
        for r in rows:
            if r["periode"] != periode:
                continue
            data = OBJECTIFS[r["objectif_code"]]
            label = data["label"].format(cible=r["cible"])
            statut = "✅" if r["reclame"] else ("🎉" if r["progres"] >= r["cible"] else "")
            lignes.append(f"{statut} {label}\n{barre(r['progres'], r['cible'])} {r['progres']}/{r['cible']}")
        if lignes:
            embed.add_field(name=PERIODE_LABELS[periode], value="\n\n".join(lignes), inline=False)

    embed.set_footer(text="🌊 One Piece Bot • Quêtes")
    await interaction.followup.send(embed=embed, view=QuetesView(interaction.guild_id, interaction.user.id))


def setup_quetes_commands(bot):
    bot.tree.add_command(quetes)
