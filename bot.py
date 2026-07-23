from dotenv import load_dotenv
load_dotenv()
import os
import discord
from discord.ext import commands
from flask import Flask
from threading import Thread
from database.db import init_db
from cogs.moderation import setup_moderation_commands
from cogs.automod import setup_automod_commands
from cogs.serverlogs import setup_serverlogs_commands
from cogs.setup import setup_setup_commands
from cogs.tickets import setup_tickets_commands, TicketPanelView, TicketCloseView
from cogs.welcome import setup_welcome_commands, WelcomeVerifyView
from cogs.profil import setup_profil_commands
from cogs.economie import setup_economie_commands
from cogs.marche import setup_marche_commands
from cogs.inventaire import setup_inventaire_commands
from cogs.exploration import setup_exploration_commands
from cogs.collecte import setup_collecte_commands
from cogs.metiers import setup_metiers_commands
from cogs.cuisine import setup_cuisine_commands
from cogs.navigation import setup_navigation_commands
from cogs.peche_au_gros import setup_peche_au_gros_commands
from cogs.combat import setup_combat_commands
from cogs.duel import setup_duel_commands
from cogs.casino import setup_casino_commands
from cogs.bras_de_fer import setup_bras_de_fer_commands
from cogs.concours_nourriture import setup_concours_nourriture_commands
from cogs.regate import setup_regate_commands
from cogs.prime_tete import setup_prime_tete_commands
from cogs.chasse_tresor import setup_chasse_tresor_commands
from cogs.raid_boss import setup_raid_boss_commands
from cogs.tournoi import setup_tournoi_commands
from cogs.equipage import setup_equipage_commands
from cogs.marine import setup_marine_commands
from cogs.revolution import setup_revolution_commands
from cogs.guilde import setup_guilde_commands
from cogs.forgeron import setup_forgeron_commands
from cogs.medecin import setup_medecin_commands
from cogs.navigateur import setup_navigateur_commands
from cogs.charpentier import setup_charpentier_commands
from cogs.musicien import setup_musicien_commands
from cogs.archeologue import setup_archeologue_commands
from cogs.guide import setup_guide_commands, GuideView
from cogs.quetes import setup_quetes_commands
from cogs.recompenses import setup_recompenses_commands
from cogs.monde import setup_monde_commands
from cogs.boss_mondial import setup_boss_mondial_commands, start_boss_loop
from cogs.succes import setup_succes_commands
from cogs.classement import setup_classement_commands
from cogs.titre import setup_titre_commands
from cogs.cartes import setup_cartes_commands
from cogs.fruit import setup_fruit_commands
from cogs.haki import setup_haki_commands
from cogs.maitrise import setup_maitrise_commands
from cogs.reputation import setup_reputation_commands
from cogs.meteo import setup_meteo_commands, start_meteo_loop
from cogs.secrets import setup_secrets_commands
from cogs.dashboard import setup_dashboard_commands
from cogs.pirate_minijeux import setup_pirate_minijeux_commands
from cogs.marine_minijeux import setup_marine_minijeux_commands
from cogs.revolution_minijeux import setup_revolution_minijeux_commands
from cogs.civil_minijeux import setup_civil_minijeux_commands

app = Flask('')

@app.route('/')
def home():
    return "Le bot est en ligne !"

def run_web():
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 8080)))

def keep_alive():
    t = Thread(target=run_web)
    t.start()

intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents)

setup_moderation_commands(bot)
setup_setup_commands(bot)
setup_tickets_commands(bot)
setup_profil_commands(bot)
setup_economie_commands(bot)
setup_marche_commands(bot)
setup_inventaire_commands(bot)
setup_exploration_commands(bot)
setup_collecte_commands(bot)
setup_metiers_commands(bot)
setup_cuisine_commands(bot)
setup_navigation_commands(bot)
setup_peche_au_gros_commands(bot)
setup_combat_commands(bot)
setup_duel_commands(bot)
setup_casino_commands(bot)
setup_bras_de_fer_commands(bot)
setup_concours_nourriture_commands(bot)
setup_regate_commands(bot)
setup_prime_tete_commands(bot)
setup_chasse_tresor_commands(bot)
setup_raid_boss_commands(bot)
setup_tournoi_commands(bot)
setup_equipage_commands(bot)
setup_marine_commands(bot)
setup_revolution_commands(bot)
setup_guilde_commands(bot)
setup_forgeron_commands(bot)
setup_medecin_commands(bot)
setup_navigateur_commands(bot)
setup_charpentier_commands(bot)
setup_musicien_commands(bot)
setup_archeologue_commands(bot)
setup_guide_commands(bot)
setup_quetes_commands(bot)
setup_recompenses_commands(bot)
setup_monde_commands(bot)
setup_boss_mondial_commands(bot)
setup_succes_commands(bot)
setup_classement_commands(bot)
setup_titre_commands(bot)
setup_cartes_commands(bot)
setup_fruit_commands(bot)
setup_haki_commands(bot)
setup_maitrise_commands(bot)
setup_reputation_commands(bot)
setup_meteo_commands(bot)
setup_secrets_commands(bot)
setup_dashboard_commands(bot)
setup_pirate_minijeux_commands(bot)
setup_marine_minijeux_commands(bot)
setup_revolution_minijeux_commands(bot)
setup_civil_minijeux_commands(bot)

@bot.event
async def on_ready():
    print(f"{bot.user} est connecté et en ligne !")
    await init_db()
    await setup_automod_commands(bot)
    await setup_serverlogs_commands(bot)
    await setup_welcome_commands(bot)
    bot.add_view(TicketPanelView())
    bot.add_view(TicketCloseView())
    bot.add_view(WelcomeVerifyView())
    bot.add_view(GuideView())
    start_boss_loop(bot)
    start_meteo_loop(bot)
    try:
        synced = await bot.tree.sync()
        print(f"{len(synced)} commande(s) slash synchronisée(s).")
    except Exception as e:
        print(f"Erreur de synchronisation : {e}")

@bot.tree.command(name="ping", description="Vérifie que le bot répond")
async def ping(interaction: discord.Interaction):
    await interaction.response.send_message("🏴‍☠️ Pong ! Le bot fonctionne parfaitement.")

keep_alive()
bot.run(os.environ["DISCORD_TOKEN"])
