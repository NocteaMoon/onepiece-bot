import discord
from discord import app_commands
from database.db import get_pool

async def has_group_permission(interaction: discord.Interaction, group: str) -> bool:
    if interaction.user.guild_permissions.administrator:
        return True
    pool = get_pool()
    role_ids = [r.id for r in interaction.user.roles]
    if not role_ids:
        return False
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT 1 FROM guild_command_roles WHERE guild_id = $1 AND command_group = $2 AND role_id = ANY($3::bigint[])",
            interaction.guild_id, group, role_ids
        )
    return row is not None

def require_group(group: str):
    async def predicate(interaction: discord.Interaction) -> bool:
        allowed = await has_group_permission(interaction, group)
        if not allowed:
            await interaction.response.send_message("⛔ Tu n'as pas la permission d'utiliser cette commande.", ephemeral=True)
        return allowed
    return app_commands.check(predicate)
