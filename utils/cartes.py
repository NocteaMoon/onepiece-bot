import random
import datetime
from database.db import get_pool
from utils.titres import unlock_titre
from data.cartes_monde import CARTES_MONDE

# Pour ajouter une nouvelle catégorie plus tard : créer data/cartes_xxx.py,
# l'importer ci-dessus, puis ajouter une ligne ici. Aucun autre code à toucher.
CATEGORIES = {
    "monde": ("🗺️ Monde", CARTES_MONDE),
}

# Récompense de complétion par catégorie : (berrys, titre_debloque)
COMPLETION_REWARDS = {
    "monde": (1000, "Cartographe du Monde"),
}

RARETE_ORDRE = ["Commun", "Rare", "Épique", "Légendaire"]
RARETE_EMOJIS = {"Commun": "⚪", "Rare": "🔵", "Épique": "🟣", "Légendaire": "🟡"}
RARETE_VENTE = {"Commun": 12, "Rare": 35, "Épique": 90, "Légendaire": 250}

# Aucune garantie de rareté : chaque carte d'un booster est tirée indépendamment
# selon ces poids. Plus de cartes par booster aux paliers hauts pour compenser
# l'absence de garantie, mais la malchance reste toujours possible.
BOOSTERS = {
    "commun": {"nom": "Booster Commun", "prix": 80, "cartes": 3,
               "poids": {"Commun": 70, "Rare": 25, "Épique": 5, "Légendaire": 0}},
    "rare": {"nom": "Booster Rare", "prix": 250, "cartes": 4,
             "poids": {"Commun": 35, "Rare": 45, "Épique": 18, "Légendaire": 2}},
    "epique": {"nom": "Booster Épique", "prix": 700, "cartes": 5,
               "poids": {"Commun": 15, "Rare": 35, "Épique": 42, "Légendaire": 8}},
    "legendaire": {"nom": "Booster Légendaire", "prix": 1000, "cartes": 6,
                   "poids": {"Commun": 5, "Rare": 20, "Épique": 45, "Légendaire": 30}},
}


def get_all_cards():
    result = []
    for cle, (nom_cat, cartes) in CATEGORIES.items():
        for code, nom, description, rarete in cartes:
            result.append({"code": code, "nom": nom, "description": description, "rarete": rarete, "categorie": cle})
    return result


def get_card(code):
    for c in get_all_cards():
        if c["code"] == code:
            return c
    return None


def tirer_booster(booster_key):
    """Tirage 100% indépendant, carte par carte, sans aucune garantie de rareté minimale."""
    config = BOOSTERS[booster_key]
    toutes = get_all_cards()
    par_rarete = {r: [c for c in toutes if c["rarete"] == r] for r in RARETE_ORDRE}

    resultats = []
    for _ in range(config["cartes"]):
        rarete_tiree = random.choices(RARETE_ORDRE, weights=[config["poids"][r] for r in RARETE_ORDRE], k=1)[0]
        pool = par_rarete.get(rarete_tiree) or toutes
        resultats.append(random.choice(pool))

    return resultats


async def add_card(guild_id: int, user_id: int, code: str, qty: int = 1) -> bool:
    """Ajoute une carte, retourne True si c'est une toute nouvelle carte pour ce joueur."""
    pool = get_pool()
    async with pool.acquire() as conn:
        existing = await conn.fetchrow(
            "SELECT quantite FROM cards_owned WHERE guild_id=$1 AND user_id=$2 AND code=$3",
            guild_id, user_id, code
        )
        if existing:
            await conn.execute(
                "UPDATE cards_owned SET quantite = quantite + $4 WHERE guild_id=$1 AND user_id=$2 AND code=$3",
                guild_id, user_id, code, qty
            )
            return False
        await conn.execute(
            "INSERT INTO cards_owned (guild_id, user_id, code, quantite) VALUES ($1,$2,$3,$4)",
            guild_id, user_id, code, qty
        )
        return True


async def remove_card(guild_id: int, user_id: int, code: str, qty: int = 1) -> bool:
    pool = get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT quantite FROM cards_owned WHERE guild_id=$1 AND user_id=$2 AND code=$3",
            guild_id, user_id, code
        )
        if not row or row["quantite"] < qty:
            return False
        nouvelle = row["quantite"] - qty
        if nouvelle <= 0:
            await conn.execute("DELETE FROM cards_owned WHERE guild_id=$1 AND user_id=$2 AND code=$3", guild_id, user_id, code)
        else:
            await conn.execute(
                "UPDATE cards_owned SET quantite=$4 WHERE guild_id=$1 AND user_id=$2 AND code=$3",
                guild_id, user_id, code, nouvelle
            )
    return True


async def get_owned(guild_id: int, user_id: int) -> dict:
    pool = get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch("SELECT code, quantite FROM cards_owned WHERE guild_id=$1 AND user_id=$2", guild_id, user_id)
    return {r["code"]: r["quantite"] for r in rows}


async def get_collection_status(guild_id: int, user_id: int, categorie_key: str):
    nom_cat, cartes = CATEGORIES[categorie_key]
    owned = await get_owned(guild_id, user_id)
    result = []
    for code, nom, description, rarete in cartes:
        result.append({"code": code, "nom": nom, "description": description, "rarete": rarete, "quantite": owned.get(code, 0)})
    return nom_cat, result


async def get_overview(guild_id: int, user_id: int):
    total = 0
    possede = 0
    for cle in CATEGORIES:
        _, statuts = await get_collection_status(guild_id, user_id, cle)
        total += len(statuts)
        possede += sum(1 for s in statuts if s["quantite"] > 0)
    return possede, total


async def check_completion_claimable(guild_id: int, user_id: int, categorie_key: str) -> bool:
    if categorie_key not in COMPLETION_REWARDS:
        return False
    _, cartes = CATEGORIES[categorie_key]
    owned = await get_owned(guild_id, user_id)
    complet = all(c[0] in owned for c in cartes)
    if not complet:
        return False
    pool = get_pool()
    async with pool.acquire() as conn:
        claimed = await conn.fetchrow(
            "SELECT 1 FROM card_collections_claimed WHERE guild_id=$1 AND user_id=$2 AND categorie=$3",
            guild_id, user_id, categorie_key
        )
    return claimed is None


async def claim_completion(guild_id: int, user_id: int, categorie_key: str):
    ok = await check_completion_claimable(guild_id, user_id, categorie_key)
    if not ok:
        return None
    berrys, titre = COMPLETION_REWARDS[categorie_key]
    pool = get_pool()
    async with pool.acquire() as conn:
        async with conn.transaction():
            await conn.execute(
                "INSERT INTO card_collections_claimed (guild_id, user_id, categorie) VALUES ($1,$2,$3)",
                guild_id, user_id, categorie_key
            )
            await conn.execute("UPDATE players SET berrys = berrys + $3 WHERE guild_id=$1 AND user_id=$2", guild_id, user_id, berrys)
    if titre:
        await unlock_titre(guild_id, user_id, titre)
    return berrys, titre


def is_echange_ouvert() -> bool:
    # Mardi = 1, Dimanche = 6 (lundi = 0 en Python)
    return datetime.datetime.utcnow().weekday() in (1, 6)
