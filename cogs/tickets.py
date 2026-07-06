import discord
from discord import app_commands
from discord.ext import commands
from database.db import get_pool
from utils.permissions import member_has_group

TICKET_TYPES = {
    "ticket_support": ("🎫 Support / Questions", "Support"),
    "ticket_recrutement": ("📋 Recrutement", "Recrutement"),
    "ticket_signalement": ("🚨 Signalement", "Signalement"),
    "ticket_pub": ("📢 Pub / Partenariat", "Pub-Partenariat"),
}

async def get_mod_roles(guild: discord.Guild):
    pool = get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            "SELECT role_id FROM guild_command_roles WHERE guild_id = $1 AND command_group = 'mod'",
            guild.id
        )
    roles = []
    for r in rows:
        role = guild.get_role(r["role_id"])
        if role:
            roles.append(role)
    return roles

async def create_ticket_channel(interaction: discord.Interaction, type_key: str):
    label, type_name = TICKET_TYPES[type_key]
    guild = interaction.guild
    user = interaction.user

    pool = get_pool()
    async with pool.acquire() as conn:
        existing = await conn.fetchrow(
            "SELECT channel_id FROM tickets WHERE guild_id = $1 AND user_id = $2 AND type = $3 AND status = 'open'",
            guild.id, user.id, type_name
        )
    if existing:
        channel = guild.get_channel(existing["channel_id"])
        if channel:
            await interaction.response.send_message(f"Tu as déjà un ticket ouvert ici : {channel.mention}", ephemeral=True)
            return

    await interaction.response.defer(ephemeral=True)

    category = discord.utils.get(guild.categories, name="🎫 TICKETS")
    if category is None:
        category = await guild.create_category("🎫 TICKETS")

    mod_roles = await get_mod_roles(guild)
    overwrites = {
        guild.default_role: discord.PermissionOverwrite(view_channel=False),
        user: discord.PermissionOverwrite(view_channel=True, send_messages=True, read_message_history=True),
        guild.me: discord.PermissionOverwrite(view_channel=True, send_messages=True),
    }
    for role in mod_roles:
        overwrites[role] = discord.PermissionOverwrite(view_channel=True, send_messages=True)

    safe_name = f"{type_name.lower().replace(' ', '-')}-{user.name}"[:90]
    channel = await guild.create_text_channel(safe_name, category=category, overwrites=overwrites)

    async with pool.acquire() as conn:
        await conn.execute(
            "INSERT INTO tickets (channel_id, guild_id, user_id, type) VALUES ($1, $2, $3, $4)",
            channel.id, guild.id, user.id, type_name
        )

    embed = discord.Embed(
        title=f"{label}",
        description=f"Bonjour {user.mention} ! Un membre du staff va s'occuper de ta demande sous peu.\nDécris ta demande ici.",
        color=0x8E44AD
    )
    embed.set_footer(text="🌊 One Piece Bot • Tickets")
    await channel.send(embed=embed, view=TicketCloseView())

    await interaction.followup.send(f"✅ Ton ticket a été créé : {channel.mention}", ephemeral=True)


class TicketPanelView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Support / Questions", emoji="🎫", style=discord.ButtonStyle.primary, custom_id="ticket_support")
    async def support(self, interaction: discord.Interaction, button: discord.ui.Button):
        await create_ticket_channel(interaction, "ticket_support")

    @discord.ui.button(label="Recrutement", emoji="📋", style=discord.ButtonStyle.primary, custom_id="ticket_recrutement")
    async def recrutement(self, interaction: discord.Interaction, button: discord.ui.Button):
        await create_ticket_channel(interaction, "ticket_recrutement")

    @discord.ui.button(label="Signalement", emoji="🚨", style=discord.ButtonStyle.danger, custom_id="ticket_signalement")
    async def signalement(self, interaction: discord.Interaction, button: discord.ui.Button):
        await create_ticket_channel(interaction, "ticket_signalement")

    @discord.ui.button(label="Pub / Partenariat", emoji="📢", style=discord.ButtonStyle.secondary, custom_id="ticket_pub")
    async def pub(self, interaction: discord.Interaction, button: discord.ui.Button):
        await create_ticket_channel(interaction, "ticket_pub")


class TicketCloseView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Fermer le ticket", emoji="🔒", style=discord.ButtonStyle.danger, custom_id="ticket_close")
    async def close(self, interaction: discord.Interaction, button: discord.ui.Button):
        guild = interaction.guild
        channel = interaction.channel

        pool = get_pool()
        async with pool.acquire() as conn:
            ticket = await conn.fetchrow("SELECT * FROM tickets WHERE channel_id = $1", channel.id)

        if ticket is None:
            await interaction.response.send_message("Ce salon n'est pas reconnu comme un ticket.", ephemeral=True)
            return

        is_owner = interaction.user.id == ticket["user_id"]
        is_mod = await member_has_group(interaction.user, "mod")
        if not (is_owner or is_mod):
            await interaction.response.send_message("⛔ Tu n'as pas la permission de fermer ce ticket.", ephemeral=True)
            return

        await interaction.response.send_message("🔒 Ticket fermé, ce salon va être supprimé dans 5 secondes...")

        async with pool.acquire() as conn:
            await conn.execute("UPDATE tickets SET status = 'closed' WHERE channel_id = $1", channel.id)

        config_pool = get_pool()
        async with config_pool.acquire() as conn:
            row = await conn.fetchrow("SELECT salon_rapports FROM guild_config WHERE guild_id = $1", guild.id)
        if row and row["salon_rapports"]:
            rapport_channel = guild.get_channel(row["salon_rapports"])
            if rapport_channel:
                await rapport_channel.send(
                    f"🔒 Ticket **{ticket['type']}** de <@{ticket['user_id']}> fermé par {interaction.user.mention} (salon : {channel.name})"
                )

        import asyncio
        await asyncio.sleep(5)
        await channel.delete()


tickets_group = app_commands.Group(
    name="ticket",
    description="Gérer le système de tickets",
    default_permissions=discord.Permissions(administrator=True)
)

@tickets_group.command(name="panel", description="Poster le panneau de tickets dans ce salon")
async def ticket_panel(interaction: discord.Interaction):
    embed = discord.Embed(
        title="🎫 Centre d'assistance",
        description="Clique sur un bouton ci-dessous pour ouvrir un ticket avec l'équipe.",
        color=0x8E44AD
    )
    embed.set_footer(text="🌊 One Piece Bot • Tickets")
    await interaction.channel.send(embed=embed, view=TicketPanelView())
    await interaction.response.send_message("✅ Panneau de tickets posté.", ephemeral=True)

def setup_tickets_commands(bot):
    bot.tree.add_command(tickets_group)
