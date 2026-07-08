import discord
from discord import app_commands
from database.db import get_pool

async def _get_salon_id(guild_id: int, salon_column: str):
    pool = get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(f"SELECT {salon_column} FROM guild_config WHERE guild_id = $1", guild_id)
    return row[salon_column] if row else None

def require_salon(salon_column: str):
    """Restreint une commande à un salon précis (configuré via /config salon).
    Si le salon n'est pas encore configuré, la commande reste utilisable partout."""
    async def predicate(interaction: discord.Interaction) -> bool:
        salon_id = await _get_salon_id(interaction.guild_id, salon_column)
        if salon_id is None:
            return True
        if interaction.channel_id != salon_id:
            channel = interaction.guild.get_channel(salon_id)
            lien = channel.mention if channel else "le salon configuré"
            await interaction.response.send_message(
                f"⛔ Cette commande ne peut être utilisée que dans {lien}.", ephemeral=True
            )
            return False
        return True
    return app_commands.check(predicate)
