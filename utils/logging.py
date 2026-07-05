import discord
from database.db import get_pool

async def _get_log_channel(guild: discord.Guild):
    pool = get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow("SELECT salon_logs FROM guild_config WHERE guild_id = $1", guild.id)
    if not row or not row["salon_logs"]:
        return None
    return guild.get_channel(row["salon_logs"])

async def log_action(guild: discord.Guild, action: str, moderateur, cible, reason: str = None):
    channel = await _get_log_channel(guild)
    if not channel:
        return
    embed = discord.Embed(title=f"🛡️ {action}", color=0x2C3E50)
    embed.add_field(name="Cible", value=str(cible), inline=True)
    embed.add_field(name="Modérateur", value=getattr(moderateur, "mention", str(moderateur)), inline=True)
    if reason:
        embed.add_field(name="Raison", value=reason, inline=False)
    embed.set_footer(text="🌊 One Piece Bot • Logs")
    try:
        await channel.send(embed=embed)
    except discord.Forbidden:
        pass

async def log_event(guild: discord.Guild, title: str, fields: list, color: int = 0x2C3E50, thumbnail: str = None):
    channel = await _get_log_channel(guild)
    if not channel:
        return
    embed = discord.Embed(title=title, color=color)
    for name, value in fields:
        embed.add_field(name=name, value=value if value else "—", inline=False)
    if thumbnail:
        embed.set_thumbnail(url=thumbnail)
    embed.set_footer(text="🌊 One Piece Bot • Logs")
    try:
        await channel.send(embed=embed)
    except discord.Forbidden:
        pass
