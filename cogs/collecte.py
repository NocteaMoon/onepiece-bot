import discord
from discord import app_commands
from utils.gathering import do_gather
from utils.channel_check import require_salon

LIEUX_PECHE = ["dans une crique poissonneuse", "au ponton du port", "sur un banc de sable immergé", "aux hauts-fonds", "à l'embouchure de la rivière", "dans une zone de courants calmes"]
POOL_PECHE = [("Poisson argenté", 55), ("Anguille des courants", 25), ("Poisson tigre", 15), ("Étoile de mer scintillante", 5), ("RIEN", 25)]

LIEUX_CHASSE = ["à l'orée de la forêt", "dans les hautes herbes", "sur le flanc de la colline", "le long d'un sentier de gibier", "dans les broussailles denses", "au creux d'une clairière isolée"]
POOL_CHASSE = [("Viande de sanglier des mers", 55), ("Plume de faucon-tonnerre", 30), ("Peau de varan des dunes", 15), ("RIEN", 30)]

LIEUX_RECOLTE = ["dans un bosquet fruitier", "dans une prairie sauvage", "au fond du sous-bois humide", "sur les rochers moussus", "dans un jardin abandonné", "sur une pente ensoleillée"]
POOL_RECOLTE = [("Baies sucrées", 40), ("Racine noueuse", 35), ("Champignon des embruns", 20), ("Fleur de corail", 5), ("RIEN", 20)]

@app_commands.command(name="pecher", description="Pêcher pour obtenir des ingrédients marins")
@require_salon("salon_peche")
async def pecher(interaction: discord.Interaction):
    await do_gather(interaction, "🎣 Pêche", "pêches", LIEUX_PECHE, POOL_PECHE, 0x1B3A5C)

@app_commands.command(name="chasser", description="Chasser pour obtenir des ingrédients de viande")
@require_salon("salon_peche")
async def chasser(interaction: discord.Interaction):
    await do_gather(interaction, "🏹 Chasse", "chasses", LIEUX_CHASSE, POOL_CHASSE, 0xC0392B)

@app_commands.command(name="recolter", description="Récolter des plantes et ingrédients naturels")
@require_salon("salon_peche")
async def recolter(interaction: discord.Interaction):
    await do_gather(interaction, "🌿 Récolte", "récoltes", LIEUX_RECOLTE, POOL_RECOLTE, 0x27AE60)

def setup_collecte_commands(bot):
    bot.tree.add_command(pecher)
    bot.tree.add_command(chasser)
    bot.tree.add_command(recolter)
