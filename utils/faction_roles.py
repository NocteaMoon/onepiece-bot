import discord
from database.db import get_pool

FACTION_ROLE_COLUMNS = {
    "Pirate": "role_pirate",
    "Marine": "role_marine",
    "Révolutionnaire": "role_revolutionnaire",
    "Civil": "role_civil",
}

FACTION_COLORS = {
    "Pirate": discord.Color(0x8E44AD),
    "Marine": discord.Color(0x3498DB),
    "Révolutionnaire": discord.Color(0xC0392B),
    "Civil": discord.Color(0x95A5A6),
}

FACTION_ROLE_NAMES = {
    "Pirate": "🏴‍☠️ Pirate",
    "Marine": "⚓ Marine",
    "Révolutionnaire": "🔥 Révolutionnaire",
    "Civil": "🏘️ Civil",
}


async def get_faction_role_ids(guild_id: int) -> dict:
    pool = get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT role_pirate, role_marine, role_revolutionnaire, role_civil FROM guild_config WHERE guild_id=$1",
            guild_id
        )
    if not row:
        return {f: None for f in FACTION_ROLE_COLUMNS}
    return {
        "Pirate": row["role_pirate"],
        "Marine": row["role_marine"],
        "Révolutionnaire": row["role_revolutionnaire"],
        "Civil": row["role_civil"],
    }


async def set_faction_role_id(guild_id: int, faction: str, role_id: int):
    column = FACTION_ROLE_COLUMNS[faction]
    pool = get_pool()
    async with pool.acquire() as conn:
        await conn.execute(f"""
            INSERT INTO guild_config (guild_id, {column}) VALUES ($1, $2)
            ON CONFLICT (guild_id) DO UPDATE SET {column} = $2
        """, guild_id, role_id)


async def create_all_faction_roles(guild: discord.Guild) -> dict:
    """Crée les 4 rôles de faction avec des couleurs distinctes et les lie."""
    created = {}
    for faction, name in FACTION_ROLE_NAMES.items():
        role = await guild.create_role(
            name=name, color=FACTION_COLORS[faction],
            reason="Création automatique des rôles de faction"
        )
        await set_faction_role_id(guild.id, faction, role.id)
        created[faction] = role
    return created


async def assign_faction_role(guild: discord.Guild, member: discord.Member, faction: str):
    """Retire les autres rôles de faction du membre et lui donne le bon (si les rôles sont configurés)."""
    role_ids = await get_faction_role_ids(guild.id)
    a_retirer = []
    role_a_donner = None
    for f, rid in role_ids.items():
        if not rid:
            continue
        role = guild.get_role(rid)
        if not role:
            continue
        if f == faction:
            role_a_donner = role
        elif role in member.roles:
            a_retirer.append(role)
    try:
        if a_retirer:
            await member.remove_roles(*a_retirer, reason="Changement de faction")
        if role_a_donner and role_a_donner not in member.roles:
            await member.add_roles(role_a_donner, reason="Attribution du rôle de faction")
    except discord.Forbidden:
        pass


async def remove_all_faction_roles(guild: discord.Guild, member: discord.Member):
    """Retire tous les rôles de faction du membre (utilisé lors d'une réinitialisation de fiche)."""
    role_ids = await get_faction_role_ids(guild.id)
    a_retirer = []
    for rid in role_ids.values():
        if not rid:
            continue
        role = guild.get_role(rid)
        if role and role in member.roles:
            a_retirer.append(role)
    if a_retirer:
        try:
            await member.remove_roles(*a_retirer, reason="Réinitialisation de la fiche joueur")
        except discord.Forbidden:
            pass


async def sync_all_members_faction_roles(guild: discord.Guild) -> tuple:
    """Réassigne le rôle de faction à tous les joueurs existants en base. Retourne (succès, échecs)."""
    pool = get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch("SELECT user_id, faction FROM players WHERE guild_id=$1", guild.id)
    succes = 0
    echecs = 0
    for r in rows:
        member = guild.get_member(r["user_id"])
        if not member:
            echecs += 1
            continue
        try:
            await assign_faction_role(guild, member, r["faction"])
            succes += 1
        except Exception:
            echecs += 1
    return succes, echecs
