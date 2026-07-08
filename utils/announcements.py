import discord
from database.db import get_pool

async def announce_level_up(interaction: discord.Interaction, member, nouveau_niveau: int):
    pool = get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow("SELECT salon_succes FROM guild_config WHERE guild_id = $1", interaction.guild_id)

    embed = discord.Embed(
        title="🎉 Niveau supérieur !",
        description=f"{member.mention} passe **niveau {nouveau_niveau}** !",
        color=0x27AE60
    )
    embed.set_footer(text="🌊 One Piece Bot • Succès")

    channel = None
    if row and row["salon_succes"]:
        channel = interaction.guild.get_channel(row["salon_succes"])

    if channel:
        try:
            await channel.send(embed=embed)
            return
        except discord.Forbidden:
            pass

    await interaction.followup.send(embed=embed)
