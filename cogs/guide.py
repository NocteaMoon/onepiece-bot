import discord
from discord import app_commands
from utils.channel_check import require_salon

def embed_accueil():
    embed = discord.Embed(
        title="📖 Carnet de bord de l'aventurier",
        description=(
            "Bienvenue à bord ! Ce carnet te guide à travers toutes les possibilités du monde.\n\n"
            "Utilise le menu déroulant ci-dessous pour explorer chaque section : ton personnage, "
            "l'économie, l'aventure, les quêtes, les récompenses, le combat, les métiers, les organisations, les mini-jeux...\n\n"
            "🌊 Bon vent, moussaillon !"
        ),
        color=0x1B3A5C
    )
    embed.set_footer(text="🌊 One Piece Bot • Guide du joueur")
    return embed

def embed_profil():
    embed = discord.Embed(
        title="📈 Ton personnage",
        description=(
            "**`/commencer`** — Crée ton personnage et choisis ta faction : Pirate, Marine, "
            "Révolutionnaire ou Civil. Chacune a sa propre voie de jeu, alors réfléchis bien !\n\n"
            "**`/profil`** — Ta fiche complète : niveau, Berrys, prime, stats de combat, position, équipage...\n\n"
            "Tu gagnes de l'XP en faisant à peu près tout (explorer, pêcher, combattre, cuisiner...). "
            "En montant de niveau, tes stats augmentent et tu es entièrement soigné !"
        ),
        color=0x95A5A6
    )
    embed.set_footer(text="🌊 One Piece Bot • Guide du joueur")
    return embed

def embed_economie():
    embed = discord.Embed(
        title="💰 Économie",
        description=(
            "**`/economie travailler`** — Un petit boulot pour gagner des Berrys (cooldown 30 min).\n\n"
            "**`/economie banque depot|retrait|solde`** — Mets tes Berrys à l'abri ! En cas de défaite, "
            "seul ton argent **liquide** est menacé, pas ta banque.\n\n"
            "**`/marche voir|infos|acheter`** — Le marché aux trésors, filtré selon ta faction.\n\n"
            "**`/inventaire voir|equiper|desequiper|utiliser|jeter`** — Gère tes objets et ton équipement.\n\n"
            "**`/economie donner`** — Envoie des Berrys à un autre joueur."
        ),
        color=0xF4C430
    )
    embed.set_footer(text="🌊 One Piece Bot • Guide du joueur")
    return embed

def embed_aventure():
    embed = discord.Embed(
        title="🗺️ Aventure",
        description=(
            "**`/explorer`** — Fouille les environs de ton île actuelle : Berrys, objets, trésors cachés, ou parfois rien du tout.\n\n"
            "**`/pecher` / `/chasser` / `/recolter`** — Récolte des ingrédients bruts (utiles pour la cuisine !), "
            "accessible à toutes les factions.\n\n"
            "**`/debarquer`** — Change d'île au sein de ta mer actuelle, pour un coût minime en endurance "
            "(contrairement à `/voyager` qui change carrément de mer et coûte bien plus cher).\n\n"
            "**`/carte`** — Affiche ton île actuelle avec sa description, et les autres îles accessibles.\n\n"
            "**`/voyager`** — Change de mer. Chaque mer demande un niveau minimum, et le trajet réserve "
            "son lot de surprises (calme, tempête, découverte...).\n\n"
            "Toutes ces actions coûtent de l'**endurance**, qui se régénère automatiquement avec le temps."
        ),
        color=0x1B3A5C
    )
    embed.set_footer(text="🌊 One Piece Bot • Guide du joueur")
    return embed

def embed_quetes():
    embed = discord.Embed(
        title="📜 Quêtes",
        description=(
            "Trois types de quêtes différents, tous regroupés sous `/quetes` :\n\n"
            "**`/quetes journalieres`** — 3 quêtes renouvelées chaque jour + 2 hebdomadaires renouvelées chaque semaine. "
            "Progression automatique en jouant, bouton 🎁 pour réclamer une fois terminées.\n\n"
            "**`/quetes principale`** — Une histoire à suivre, chapitre par chapitre. Une seule à la fois, "
            "la suivante se débloque automatiquement une fois la précédente réclamée. Certains chapitres "
            "débloquent même un titre exclusif !\n\n"
            "**`/quetes secondaires`** — Des missions optionnelles au choix (2 maximum en même temps). "
            "Utilise `/quetes secondaire_rejoindre` pour en accepter une, `/quetes secondaire_abandonner` "
            "pour en libérer une si tu changes d'avis.\n\n"
            "💡 Toutes progressent automatiquement dès que tu joues normalement (explorer, combattre, voyager...)."
        ),
        color=0xD4A017
    )
    embed.set_footer(text="🌊 One Piece Bot • Guide du joueur")
    return embed

def embed_recompenses():
    embed = discord.Embed(
        title="🎁 Récompenses régulières",
        description=(
            "Différentes des quêtes : ici, pas d'objectif à remplir, juste revenir régulièrement !\n\n"
            "**`/recompenses quotidienne`** — Toutes les 24h. Plus tu reviens de jours **consécutifs**, "
            "plus le bonus grandit (jusqu'à +35฿ au 7ème jour de série). Rate un jour et la série repart à zéro !\n\n"
            "**`/recompenses hebdomadaire`** — Tous les 7 jours, un bon paquet de Berrys fixe.\n\n"
            "**`/recompenses mensuelle`** — Tous les 30 jours, la plus généreuse (Berrys, XP, et une chance "
            "d'objet rare en bonus).\n\n"
            "💡 Ces trois récompenses sont indépendantes les unes des autres : tu peux les réclamer toutes "
            "le même jour si les cooldowns sont passés !"
        ),
        color=0xF4C430
    )
    embed.set_footer(text="🌊 One Piece Bot • Guide du joueur")
    return embed

def embed_combat():
    embed = discord.Embed(
        title="⚔️ Combat",
        description=(
            "**`/combattre`** — Affronte un ennemi de ta mer actuelle. Boutons Attaque/Défense/Objet/Fuite.\n\n"
            "**`/duel`** — Défie un autre joueur (mise optionnelle). Sans risque réel pour tes vraies stats, "
            "c'est un vrai duel sportif !\n\n"
            "⚠️ **En cas de défaite en PvE** : tu perds un peu de Berrys liquides, ton équipement s'abîme "
            "(pense à un Forgeron !), et tu es K.O. quelques minutes (les actions pacifiques restent possibles).\n\n"
            "Équipe de bonnes armes/armures via `/inventaire equiper` pour de meilleures stats en combat !"
        ),
        color=0xC0392B
    )
    embed.set_footer(text="🌊 One Piece Bot • Guide du joueur")
    return embed

def embed_metiers():
    embed = discord.Embed(
        title="🔧 Les Métiers — bien comprendre le système",
        description=(
            "Les métiers sont **réservés à la faction Civil**. Choisis-en un avec `/metier choisir`, "
            "puis suis ta progression avec `/metier voir`.\n\n"
            "**🍳 Cuisinier** → `/cuisiner` transforme tes ingrédients récoltés en plats qui soignent.\n"
            "**🔨 Forgeron** → `/reparer` restaure la durabilité de ton équipement abîmé.\n"
            "**💊 Médecin** → `/soigner` restaure les PV et lève le K.O. d'un joueur.\n"
            "**🧭 Navigateur** → `/route_sure` garantit un voyage sans risque à quelqu'un.\n\n"
            "⚠️ **Attention à ne pas confondre deux systèmes de rangs différents :**\n"
            "• Ton **rang de métier** (Apprenti → Confirmé → Maître) = ta compétence personnelle, "
            "progresse via `metier_xp` en pratiquant ton métier.\n"
            "• Ton **rang de Guilde** (Membre → Compagnon → Expert → Maître de Guilde) = ta place "
            "dans la hiérarchie **sociale** d'une guilde (`/guilde`), complètement indépendant de ton niveau de compétence !\n\n"
            "Tu peux très bien être Maître dans ton métier sans être Maître de Guilde, et inversement."
        ),
        color=0xD4A017
    )
    embed.set_footer(text="🌊 One Piece Bot • Guide du joueur")
    return embed

def embed_organisations():
    embed = discord.Embed(
        title="🏴‍☠️ Organisations",
        description=(
            "Chaque faction a son organisation collective, avec la même mécanique mais son propre thème :\n\n"
            "**🏴‍☠️ Pirate** → `/equipage` (Membre→Officier→Second→Capitaine)\n"
            "**⚓ Marine** → `/marine` (Matelot→Officier→Commandant→Amiral)\n"
            "**🔥 Révolutionnaire** → `/revolution` (Recrue→Agent→Commandant→Meneur)\n"
            "**🧵 Civil** → `/guilde` (Membre→Compagnon→Expert→Maître de Guilde)\n\n"
            "Sous-commandes communes : `creer`, `inviter`, `expulser`, `quitter`, `promouvoir`, "
            "`coffre depot|retrait|solde`, `info`, `liste`, et bien sûr un emblème personnalisable !"
        ),
        color=0x8E44AD
    )
    embed.set_footer(text="🌊 One Piece Bot • Guide du joueur")
    return embed

def embed_minijeux():
    embed = discord.Embed(
        title="🎲 Mini-jeux",
        description=(
            "**Solo :** `/peche_au_gros`, `/bras_de_fer`, `/concours_nourriture`, "
            "`/casino machine-a-sous|des|roulette|blackjack`\n\n"
            "**Multijoueurs :** `/regate` (course 2-4), `/chasse_tresor` (coopératif 2-4), "
            "`/raid_boss` (coopératif 2-4), `/tournoi` (bracket à 4), `/bras_de_fer_duel` (1v1)\n\n"
            "La plupart fonctionnent avec de vrais boutons interactifs — tente ta chance !"
        ),
        color=0xE67E22
    )
    embed.set_footer(text="🌊 One Piece Bot • Guide du joueur")
    return embed

def embed_prime():
    embed = discord.Embed(
        title="☠️ Ta réputation",
        description=(
            "**`/prime_tete`** — Ton avis de recherche officiel : prime, navire, équipage, faction. "
            "Regarde aussi celui d'un ami avec `/prime_tete membre:@quelqu'un` !\n\n"
            "Ta prime augmente en gagnant des combats et certains mini-jeux."
        ),
        color=0x1A1A1A
    )
    embed.set_footer(text="🌊 One Piece Bot • Guide du joueur")
    return embed


SECTIONS = {
    "accueil": embed_accueil,
    "profil": embed_profil,
    "economie": embed_economie,
    "aventure": embed_aventure,
    "quetes": embed_quetes,
    "recompenses": embed_recompenses,
    "combat": embed_combat,
    "metiers": embed_metiers,
    "organisations": embed_organisations,
    "minijeux": embed_minijeux,
    "prime": embed_prime,
}


class GuideSelect(discord.ui.Select):
    def __init__(self):
        options = [
            discord.SelectOption(label="Accueil", value="accueil", emoji="📖"),
            discord.SelectOption(label="Ton personnage", value="profil", emoji="📈"),
            discord.SelectOption(label="Économie", value="economie", emoji="💰"),
            discord.SelectOption(label="Aventure", value="aventure", emoji="🗺️"),
            discord.SelectOption(label="Quêtes", value="quetes", emoji="📜"),
            discord.SelectOption(label="Récompenses", value="recompenses", emoji="🎁"),
            discord.SelectOption(label="Combat", value="combat", emoji="⚔️"),
            discord.SelectOption(label="Métiers", value="metiers", emoji="🔧"),
            discord.SelectOption(label="Organisations", value="organisations", emoji="🏴‍☠️"),
            discord.SelectOption(label="Mini-jeux", value="minijeux", emoji="🎲"),
            discord.SelectOption(label="Ta réputation", value="prime", emoji="☠️"),
        ]
        super().__init__(placeholder="Choisis une section du guide...", options=options, custom_id="guide_select")

    async def callback(self, interaction: discord.Interaction):
        embed = SECTIONS[self.values[0]]()
        await interaction.response.edit_message(embed=embed, view=self.view)


class GuideView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(GuideSelect())


@app_commands.command(name="guide", description="Ouvrir le carnet de bord de l'aventurier (guide du joueur)")
@require_salon("salon_carnet")
async def guide(interaction: discord.Interaction):
    await interaction.response.send_message(embed=embed_accueil(), view=GuideView())


def setup_guide_commands(bot):
    bot.tree.add_command(guide)
