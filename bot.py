import os
import discord
from discord.ext import commands
from flask import Flask
from threading import Thread
from database.db import init_db
from cogs.admin import setup_admin_commands
from cogs.moderation import setup_moderation_commands
from cogs.automod import setup_automod_commands
from cogs.serverlogs import setup_serverlogs_commands

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

setup_admin_commands(bot)
setup_moderation_commands(bot)

@bot.event
async def on_ready():
    print(f"{bot.user} est connecté et en ligne !")
    await init_db()
    await setup_automod_commands(bot)
    await setup_serverlogs_commands(bot)
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
