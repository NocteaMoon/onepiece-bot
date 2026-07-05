import os
import discord
from discord.ext import commands
from flask import Flask
from threading import Thread

# --- Petit serveur web pour satisfaire Render (garde le bot "vivant") ---
app = Flask('')

@app.route('/')
def home():
    return "Le bot est en ligne !"

def run_web():
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 8080)))

def keep_alive():
    t = Thread(target=run_web)
    t.start()

# --- Configuration du bot Discord ---
intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents)

@bot.event
async def on_ready():
    print(f"{bot.user} est connecté et en ligne !")
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
