import discord
from discord import app_commands
from database.db import get_pool
from utils.channel_check import require_salon


async def get_config_row(guild_id):
    pool = get_pool()
    async with pool.acquire() as conn:
        return await conn.fetchrow("SELECT * FROM guild_config WHERE guild_id=$1", guild_id)


def salon(config_row, column, nom_repli):
    """Renvoie un vrai lien cliquable si le salon est configuré, sinon le nom en texte simple."""
    if config_row and config_row[column]:
        return f"<#{config_row[column]}>"
    return f"#{nom_repli}"


def embed_accueil(config_row):
    embed = discord.Embed(
        title="📖 Carnet de bord de l'aventurier",
        description=(
            "Bienvenue à bord ! Ce carnet te guide à travers toutes les possibilités du monde.\n\n"
            "Utilise le menu déroulant ci-dessous pour explorer chaque section : ton personnage, "
            "l'économie, l'aventure, les quêtes, les récompenses, les succès, les pouvoirs, le combat, "
            "les métiers, les organisations, les mini-jeux...\n\n"
            "🌊 Bon vent, moussaillon !"
        ),
        color=0x1B3A5C
    )
    embed.set_footer(text="🌊 One Piece Bot • Guide du joueur")
    return embed


def embed_profil(config_row):
    creation = salon(config_row, "salon_creation", "création-personnage")
    embed = discord.Embed(
        title="📈 Ton personnage",
        description=(
            f"**`/commencer`** (dans {creation}) — Crée ton personnage et choisis ta faction : Pirate, "
            "Marine, Révolutionnaire ou Civil. Chacune a sa propre voie de jeu, alors réfléchis bien !\n\n"
            "**`/profil`** — Ta fiche complète : niveau, Berrys, prime, stats de combat, position, équipage, "
            "et ta **Notoriété** (renommée gagnée via les gros exploits).\n\n"
            "**`/reputation`** — Ta réputation détaillée par faction, ton respect d'équipage, ta notoriété.\n\n"
            "**`/titre choisir`** — Équipe le titre de ton choix parmi ceux débloqués. **`/titre voir`** liste tous tes titres.\n\n"
            "💭 On raconte qu'une force cachée grandirait en secret chez les aventuriers les plus déterminés...\n\n"
            "Tu gagnes de l'XP en faisant à peu près tout. En montant de niveau, tes stats augmentent et tu es entièrement soigné !"
        ),
        color=0x95A5A6
    )
    embed.set_footer(text="🌊 One Piece Bot • Guide du joueur")
    return embed


def embed_economie(config_row):
    economie = salon(config_row, "salon_economie", "économie")
    boutique = salon(config_row, "salon_boutique", "boutique")
    embed = discord.Embed(
        title="💰 Économie",
        description=(
            f"**`/economie travailler`** (dans {economie}) — Un petit boulot pour gagner des Berrys (cooldown 30 min).\n\n"
            "**`/economie banque depot|retrait|solde`** — Mets tes Berrys à l'abri ! En cas de défaite, "
            "seul ton argent **liquide** est menacé, pas ta banque.\n\n"
            f"**`/marche voir|infos|acheter`** (dans {boutique}) — Le marché aux trésors, filtré selon ta faction. "
            "Ta réputation peut te faire économiser jusqu'à 20% !\n\n"
            "**`/inventaire voir|equiper|desequiper|utiliser|jeter`** — Gère tes objets et ton équipement. "
            "Certains plats (🍳) donnent un bonus temporaire en plus du soin !\n\n"
            "**`/economie donner`** — Envoie des Berrys à un autre joueur."
        ),
        color=0xF4C430
    )
    embed.set_footer(text="🌊 One Piece Bot • Guide du joueur")
    return embed


def embed_aventure(config_row):
    exploration = salon(config_row, "salon_exploration", "exploration")
    embed = discord.Embed(
        title="🗺️ Aventure",
        description=(
            f"**`/explorer`** (dans {exploration}) — Fouille ton île actuelle : Berrys, objets, trésors cachés, "
            "voire (très rarement) un Fruit du Démon !\n\n"
            "**`/pecher` / `/chasser` / `/recolter`** — Récolte des ingrédients bruts, utiles pour les métiers. "
            "Utilisables dans n'importe quel salon.\n\n"
            f"**`/debarquer`** (dans {exploration}) — Change d'île au sein de ta mer, coût minime en endurance.\n\n"
            "**`/carte`** — Affiche ton île actuelle et les îles accessibles.\n\n"
            f"**`/voyager`** (dans {exploration}) — Change de mer. Chaque mer demande un niveau minimum et réserve "
            "son lot de surprises. Plus tu voyages, moins les risques sont élevés !\n\n"
            "**`/meteo`** — La météo du serveur, elle influence légèrement l'exploration et les voyages.\n\n"
            "Toutes ces actions coûtent de l'**endurance**, qui se régénère automatiquement."
        ),
        color=0x1B3A5C
    )
    embed.set_footer(text="🌊 One Piece Bot • Guide du joueur")
    return embed


def embed_quetes(config_row):
    quetes = salon(config_row, "salon_quetes", "quêtes-événements")
    embed = discord.Embed(
        title="📜 Quêtes",
        description=(
            f"Trois types de quêtes, tous regroupés sous `/quetes` (dans {quetes}) :\n\n"
            "**`/quetes journalieres`** — 3 quêtes par jour + 2 par semaine, renouvelées automatiquement. "
            "Progression en jouant normalement, bouton 🎁 pour réclamer.\n\n"
            "**`/quetes principale`** — Une histoire à suivre chapitre par chapitre, certains débloquent un titre exclusif.\n\n"
            "**`/quetes secondaires`** — Missions optionnelles au choix (2 max en même temps). "
            "`secondaire_rejoindre` pour accepter, `secondaire_abandonner` pour libérer une place.\n\n"
            "💡 Les quêtes liées à un métier ou une faction ne sont proposées qu'aux joueurs concernés !"
        ),
        color=0xD4A017
    )
    embed.set_footer(text="🌊 One Piece Bot • Guide du joueur")
    return embed


def embed_recompenses(config_row):
    recompenses = salon(config_row, "salon_recompenses", "récompenses")
    embed = discord.Embed(
        title="🎁 Récompenses régulières",
        description=(
            f"Pas d'objectif à remplir ici, juste revenir régulièrement dans {recompenses} !\n\n"
            "**`/recompenses quotidienne`** — Toutes les 24h. Bonus croissant sur 7 jours **consécutifs**, "
            "la série repart à zéro si tu rates un jour.\n\n"
            "**`/recompenses hebdomadaire`** — Tous les 7 jours.\n\n"
            "**`/recompenses mensuelle`** — Tous les 30 jours, la plus généreuse (+ chance d'objet rare).\n\n"
            "💡 Les trois sont indépendantes : réclame-les toutes le même jour si les cooldowns sont passés !"
        ),
        color=0xF4C430
    )
    embed.set_footer(text="🌊 One Piece Bot • Guide du joueur")
    return embed


def embed_succes(config_row):
    succes = salon(config_row, "salon_succes", "succès")
    embed = discord.Embed(
        title="🏆 Succès",
        description=(
            f"**`/succes`** (dans {succes}) — Tes hauts faits classés par catégorie : Niveau, Richesse, Prime, "
            "Mers explorées, Métier, Commandement, Organisation, Tournois, Boss mondiaux, Notoriété, "
            "Réputation, Collection de cartes, Mini-jeux de faction.\n\n"
            "Chaque catégorie a plusieurs paliers, du plus facile au plus dur. Un succès accompli affiche 🎉 "
            "avec un bouton pour le réclamer — la récompense n'est jamais automatique !"
        ),
        color=0xD4A017
    )
    embed.set_footer(text="🌊 One Piece Bot • Guide du joueur")
    return embed


def embed_pouvoirs(config_row):
    boutique = salon(config_row, "salon_boutique", "boutique")
    entrainement = salon(config_row, "salon_entrainement", "entraînement")
    embed = discord.Embed(
        title="🍈 Fruits du Démon & Haki",
        description=(
            "**🍈 Fruits du Démon** — Un seul par joueur, et chaque fruit est **unique** sur le serveur.\n"
            "• `/fruit voir` — ton fruit actuel et s'il est éveillé.\n"
            f"• `/fruit marche_noir` / `/fruit acheter` (dans {boutique}) — 5 000฿ à 75 000฿ selon la rareté.\n"
            "• Chance infime d'en trouver un gratuitement en explorant.\n"
            "• **L'Éveil** est 100% aléatoire, après n'importe quelle victoire — impossible à provoquer.\n\n"
            "**⚔️ Haki** — Trois types, cachés dans ton profil :\n"
            "• `/haki voir` — consulter tes niveaux, n'importe où.\n"
            f"• `/haki entrainer` (dans {entrainement}) — Armement ou Observation, chance de progression à chaque session.\n"
            "• **Haki des Rois** : aussi rare que l'Éveil, jamais entraînable.\n\n"
            "**⚔️ Maîtrise d'armes** — `/maitrise` pour tes 6 maîtrises. Progresse automatiquement en combattant "
            "avec l'arme équipée.\n\n"
            f"**🏋️ `/entrainement`** (dans {entrainement}) — Une session dédiée selon ta faction (et ton grade "
            "pour Marine/Révolutionnaire, ton métier pour Civil). En plus de tes autres progressions, pas à leur place !"
        ),
        color=0x8E44AD
    )
    embed.set_footer(text="🌊 One Piece Bot • Guide du joueur")
    return embed


def embed_combat(config_row):
    combat = salon(config_row, "salon_combat", "combat")
    duel = salon(config_row, "salon_duel", "duel-pvp")
    embed = discord.Embed(
        title="⚔️ Combat",
        description=(
            f"**`/combattre`** (dans {combat}) — Affronte un ennemi de ta mer actuelle. "
            "Boutons Attaque/Défense/Objet/Fuite.\n\n"
            f"**`/duel`** (dans {duel}) — Défie un autre joueur (mise optionnelle). ⚓ Un Marine qui gagne "
            "réduit la prime de son adversaire d'une autre faction de 20% !\n\n"
            "⚠️ **En cas de défaite en PvE** : perte de Berrys liquides, équipement abîmé (pense à un Forgeron !), "
            "et K.O. temporaire (les actions pacifiques restent possibles).\n\n"
            "Équipement, Fruit du Démon, Haki, maîtrise d'arme, Respect d'équipage et un bon repas boostent tous tes stats effectives !"
        ),
        color=0xC0392B
    )
    embed.set_footer(text="🌊 One Piece Bot • Guide du joueur")
    return embed


def embed_metiers(config_row):
    entrainement = salon(config_row, "salon_entrainement", "entraînement")
    embed = discord.Embed(
        title="🔧 Les Métiers",
        description=(
            "Réservés à la faction **Civil**. Choisis-en un avec `/metier choisir`, suis ta progression avec `/metier voir`.\n\n"
            "**🍳 Cuisinier** → `/cuisiner` (plats, certains donnent un bonus temporaire)\n"
            "**🔨 Forgeron** → `/forgeron reparer|forger`\n"
            "**💊 Médecin** → `/medecin soigner|preparer`\n"
            "**🧭 Navigateur** → `/navigateur route_sure|dresser_carte`\n"
            "**🚢 Charpentier** → `/charpentier reparer_navire|construire`\n"
            "**🎵 Musicien** → `/musicien jouer|composer`\n"
            "**🏺 Archéologue** → `/archeologue etudier|dechiffrer`\n\n"
            f"💡 `/entrainement` (dans {entrainement}) offre aussi un perfectionnement dédié à ton métier.\n\n"
            "⚠️ Ne confonds pas ton **rang de métier** (Apprenti→Confirmé→Maître, ta compétence personnelle) "
            "et ton **rang de Guilde** (Membre→Compagnon→Expert→Maître de Guilde, ta place sociale dans `/guilde`) "
            "— les deux sont totalement indépendants !"
        ),
        color=0xD4A017
    )
    embed.set_footer(text="🌊 One Piece Bot • Guide du joueur")
    return embed


def embed_organisations(config_row):
    equipages = salon(config_row, "salon_equipages", "équipages")
    marine = salon(config_row, "salon_marine", "marine")
    revolution = salon(config_row, "salon_revolutionnaires", "révolutionnaires")
    guilde = salon(config_row, "salon_guilde", "guilde-des-métiers")
    embed = discord.Embed(
        title="🏴‍☠️ Organisations",
        description=(
            "Chaque faction a son organisation collective, même mécanique, thème différent :\n\n"
            f"**🏴‍☠️ Pirate** → `/equipage` (dans {equipages}) — Membre→Officier→Second→Capitaine\n"
            f"**⚓ Marine** → `/marine` (dans {marine}) — Matelot→Officier→Commandant→Amiral\n"
            f"**🔥 Révolutionnaire** → `/revolution` (dans {revolution}) — Recrue→Agent→Commandant→Meneur\n"
            f"**🧵 Civil** → `/guilde` (dans {guilde}) — Membre→Compagnon→Expert→Maître de Guilde\n\n"
            "Sous-commandes communes : `creer`, `inviter`, `expulser`, `quitter`, `promouvoir`, "
            "`coffre depot|retrait|solde`, `info`, `liste`, emblème personnalisable.\n\n"
            "💰 Déposer dans le coffre augmente ton **Respect d'équipage** → bonus de défense en combat."
        ),
        color=0x8E44AD
    )
    embed.set_footer(text="🌊 One Piece Bot • Guide du joueur")
    return embed


def embed_minijeux(config_row):
    taverne = salon(config_row, "salon_taverne", "défis-de-taverne")
    duel = salon(config_row, "salon_duel", "duel-pvp")
    combat = salon(config_row, "salon_combat", "combat")
    embed = discord.Embed(
        title="🎲 Mini-jeux",
        description=(
            f"**Universels** (dans {taverne} sauf mention contraire) :\n"
            "Solo : `/peche_au_gros`, `/bras_de_fer`, `/concours_nourriture`, `/casino`, `/cartes`\n"
            f"Multi : `/regate`, `/chasse_tresor`, `/raid_boss` (dans {combat}), "
            f"`/tournoi` (dans {duel}), `/bras_de_fer_duel`, `/duel` (dans {duel})\n\n"
            "**🏴‍☠️ Pirate — `/pirate`** : `chasse_prime`, `abordage`, `beuverie`, `pillage_convoi` (coop), `duel_eclair`\n\n"
            "**⚓ Marine — `/amiraute`** : `patrouille`, `exercice_tir`, `interrogatoire`, `bataille_navale` (coop), `inspection`\n\n"
            "**🔥 Révolutionnaire — `/insurrection`** : `briefing`, `infiltration`, `sabotage` (coop), `code_secret`, `recrutement`\n\n"
            "**🏘️ Civil — `/atelier`** : `rapidite`, `artisanat`, `negociation`, `encheres`, `foire` (coop)\n\n"
            "**Boss mondial :** apparition aléatoire, ouvert à tous les joueurs présents sur la mer. "
            "`/boss_mondial statut` pour vérifier."
        ),
        color=0xE67E22
    )
    embed.set_footer(text="🌊 One Piece Bot • Guide du joueur")
    return embed


def embed_prime(config_row):
    embed = discord.Embed(
        title="☠️ Ta réputation",
        description=(
            "**`/prime_tete`** — Ton avis de recherche officiel, ou celui d'un ami avec `membre:@quelqu'un`.\n\n"
            "**`/reputation`** — Ta réputation par faction, ta notoriété et ton respect d'équipage. "
            "La Notoriété débloque aussi des titres exclusifs à certains paliers cachés !\n\n"
            "Ta prime augmente en combat et en mini-jeux — mais un Marine qui te bat en duel la réduit de 20% !"
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
    "succes": embed_succes,
    "pouvoirs": embed_pouvoirs,
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
            discord.SelectOption(label="Succès", value="succes", emoji="🏆"),
            discord.SelectOption(label="Fruits & Haki", value="pouvoirs", emoji="🍈"),
            discord.SelectOption(label="Combat", value="combat", emoji="⚔️"),
            discord.SelectOption(label="Métiers", value="metiers", emoji="🔧"),
            discord.SelectOption(label="Organisations", value="organisations", emoji="🏴‍☠️"),
            discord.SelectOption(label="Mini-jeux", value="minijeux", emoji="🎲"),
            discord.SelectOption(label="Ta réputation", value="prime", emoji="☠️"),
        ]
        super().__init__(placeholder="Choisis une section du guide...", options=options, custom_id="guide_select")

    async def callback(self, interaction: discord.Interaction):
        config_row = await get_config_row(interaction.guild_id)
        embed = SECTIONS[self.values[0]](config_row)
        await interaction.response.edit_message(embed=embed, view=self.view)


class GuideView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(GuideSelect())


@app_commands.command(name="guide", description="Ouvrir le carnet de bord de l'aventurier (guide du joueur)")
@require_salon("salon_carnet")
async def guide(interaction: discord.Interaction):
    config_row = await get_config_row(interaction.guild_id)
    await interaction.response.send_message(embed=embed_accueil(config_row), view=GuideView())


def setup_guide_commands(bot):
    bot.tree.add_command(guide)
