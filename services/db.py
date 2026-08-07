import asyncpg
from config import DATABASE_URL
from typing import Optional, List, Dict, Any

db_pool = None

async def create_pool():
    global db_pool
    db_pool = await asyncpg.create_pool(DATABASE_URL)
    return db_pool

async def close_pool():
    if db_pool:
        await db_pool.close()

async def get_player(user_id: int):
    async with db_pool.acquire() as conn:
        return await conn.fetchrow("SELECT * FROM players WHERE user_id = $1", user_id)

async def get_player_by_username(username: str):
    async with db_pool.acquire() as conn:
        return await conn.fetchrow("SELECT * FROM players WHERE username ILIKE $1", username)

async def update_player_stats(user_id: int):
    # copy the original logic from bot.py: calc_level, scale_stats, etc.
    from utils.helpers import calc_level, scale_stats_from_base, calc_rank
    async with db_pool.acquire() as conn:
        player = await conn.fetchrow("SELECT * FROM players WHERE user_id = $1", user_id)
        if not player:
            return
        new_level = calc_level(player['xp'])
        char_name = player.get('character_name')
        if char_name:
            char = await conn.fetchrow("SELECT * FROM characters WHERE name = $1", char_name)
            if char:
                base_hp, base_ce, base_atk, base_def, base_spd = char['hp'], char['ce'], char['atk'], char['def'], char['spd']
            else:
                base_hp, base_ce, base_atk, base_def, base_spd = 100, 100, 10, 10, 10
        else:
            base_hp, base_ce, base_atk, base_def, base_spd = 100, 100, 10, 10, 10
        bonus_atk = player.get('prestige_bonus_atk', 0)
        bonus_hp = player.get('prestige_bonus_hp', 0)
        restriction = player.get('restriction')
        r_atk, r_def, r_spd = 0, 0, 0
        if restriction == 'toji':
            r_atk = base_atk * 2
            r_def = base_def * 2
            r_spd = base_spd * 2
        elif restriction == 'maki':
            r_atk = int(base_atk * 0.5)
        new_max_hp, new_max_ce, new_atk, new_def, new_spd = scale_stats_from_base(
            base_atk, base_def, base_spd, base_hp, base_ce, new_level, bonus_atk, bonus_hp, r_atk, r_def, r_spd
        )
        hp_ratio = player['hp'] / player['max_hp'] if player['max_hp'] > 0 else 1
        ce_ratio = player['ce'] / player['max_ce'] if player['max_ce'] > 0 else 1
        new_hp = int(new_max_hp * hp_ratio)
        new_ce = int(new_max_ce * ce_ratio)
        if restriction == 'toji':
            new_ce = 0
            new_max_ce = 0
        await conn.execute("""
            UPDATE players 
            SET level = $1, max_hp = $2, max_ce = $3, atk = $4, def = $5, spd = $6,
                hp = $7, ce = $8
            WHERE user_id = $9
        """, new_level, new_max_hp, new_max_ce, new_atk, new_def, new_spd, new_hp, new_ce, user_id)

async def get_character(name: str):
    async with db_pool.acquire() as conn:
        return await conn.fetchrow("SELECT * FROM characters WHERE name ILIKE $1", name)

async def get_shop_items(page, per_page=5):
    async with db_pool.acquire() as conn:
        offset = (page - 1) * per_page
        return await conn.fetch("SELECT * FROM shop_items ORDER BY category, name LIMIT $1 OFFSET $2", per_page, offset)

# ... add all other DB functions from original bot.py (get_enemy, get_clan, etc.)
