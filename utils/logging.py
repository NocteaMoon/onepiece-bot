import discord
from database.db import get_pool

async def log_action(guild: discord.Guild, action: str, moderateur: discord.Member, cible, reason: str = None):
    pool = get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow("SELECT salon_logs FROM guild_config WHERE guild_id = $1", guild.id)
    if not row or not row["salon_logs"]:
        return
    channel = guild.get_channel(row["salon_logs"])
    if not channel:
        return
    embed = discord.Embed(title=f"🛡️ {action}", color=0x2C3E50)
    embed.add_field(name="Cible", value=str(cible), inline=True)
    embed.add_field(name="Modérateur", value=moderateur.mention, inline=True)
    if reason:
        embed.add_field(name="Raison", value=reason, inline=False)
    embed.set_footer(text="🌊 One Piece Bot • Logs")
    try:
        await channel.send(embed=embed)
    except discord.Forbidden:
        pass
