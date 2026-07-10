import discord
from discord import app_commands
from utils.gathering import do_gather

LIEUX_PECHE = ["une crique poissonneuse", "le ponton du port", "un banc de sable immergé", "les hauts-fonds", "l'embouchure de la rivière", "une zone de courants calmes", "une épave à demi engloutie"]
POOL_PECHE = [("Poisson argenté", 40), ("Anguille des courants", 20), ("Poisson tigre", 12), ("Étoile de mer scintillante", 4), ("Parchemin usé", 22), ("Encre de seiche", 12), ("Corail luminescent", 4), ("RIEN", 20)]

LIEUX_CHASSE = ["l'orée de la forêt", "les hautes herbes", "le flanc de la colline", "un sentier de gibier", "les broussailles denses", "une clairière isolée"]
POOL_CHASSE = [("Viande de sanglier des mers", 55), ("Plume de faucon-tonnerre", 30), ("Peau de varan des dunes", 15), ("RIEN", 30)]

LIEUX_RECOLTE = ["un bosquet fruitier", "une prairie sauvage", "le sous-bois humide", "les rochers moussus", "un jardin abandonné", "une pente ensoleillée", "une veine de minerai affleurante", "un carré d'herbes médicinales", "un rivage jonché de bois flotté"]
POOL_RECOLTE = [
    ("Baies sucrées", 26), ("Racine noueuse", 24), ("Champignon des embruns", 13), ("Fleur de corail", 3),
    ("Minerai de fer", 24), ("Minerai d'étain", 12), ("Pépite d'acier bleu", 3),
    ("Herbe apaisante", 24), ("Feuille de saule marin", 12), ("Racine de vitalité", 3),
    ("Planche de bois flotté", 24), ("Corde tressée", 12), ("Voile renforcée", 3),
    ("RIEN", 22),
]

@app_commands.command(name="pecher", description="Pêcher pour obtenir des ingrédients marins")
async def pecher(interaction: discord.Interaction):
    await do_gather(interaction, "🎣 Pêche", "pêches", LIEUX_PECHE, POOL_PECHE, 0x1B3A5C)

@app_commands.command(name="chasser", description="Chasser pour obtenir des ingrédients de viande")
async def chasser(interaction: discord.Interaction):
    await do_gather(interaction, "🏹 Chasse", "chasses", LIEUX_CHASSE, POOL_CHASSE, 0xC0392B)

@app_commands.command(name="recolter", description="Récolter des plantes et ingrédients naturels")
async def recolter(interaction: discord.Interaction):
    await do_gather(interaction, "🌿 Récolte", "récoltes", LIEUX_RECOLTE, POOL_RECOLTE, 0x27AE60)

def setup_collecte_commands(bot):
    bot.tree.add_command(pecher)
    bot.tree.add_command(chasser)
    bot.tree.add_command(recolter)
