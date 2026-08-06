# ================================================================
#                 CURSED CHRONICLES – COMPLETE BOT
#                 ALL FEATURES – NO PLACEHOLDERS
# ================================================================

import asyncio
import os
import random
import json
from datetime import datetime, timedelta
from io import StringIO
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, InputMediaPhoto, BufferedInputFile
import asyncpg
from dotenv import load_dotenv

load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")
DATABASE_URL = os.getenv("DATABASE_URL")
if not BOT_TOKEN or not DATABASE_URL:
    raise ValueError("Missing BOT_TOKEN or DATABASE_URL")

OWNER_ID = 8609946980
OWNER_NAME = "𝕄𝕒𝕩𝕨𝕖𝕝𝕝-𝟜𝟟"
MAX_YEN = 999999999

EFFECTS = {
    "yuji_attack": "https://files.catbox.moe/zw09u9.mp4",
    "yuji_domain": "https://files.catbox.moe/ufmbdo.mp4",
    "heal": "https://files.catbox.moe/fi5ror.mp4",
    "domain_clash": "https://files.catbox.moe/t21htk.mp4",
    "shikigami_summon": "https://files.catbox.moe/bh9ng9.mp4",
    "defeat": "https://files.catbox.moe/myq7p2.mp4",
    "versus": "https://files.catbox.moe/9jpq2h.mp4",
    "yuta_final": "https://files.catbox.moe/a7bnl2.mp4",
    "powerful_domain_clash": "https://files.catbox.moe/iyc41x.jpg",
    "sukuna_domain": "https://files.catbox.moe/77an7b.jpg",
    "mahito_domain": "https://files.catbox.moe/xkfqwn.jpg",
    "black_flash": "https://files.catbox.moe/410g09.jpg",
    "cursed_energy": "https://files.catbox.moe/wq4cu7.jpg",
    "gojo_purple": "https://files.catbox.moe/9qo4pf.jpg",
    "gojo_red": "https://files.catbox.moe/e1rjlx.jpg",
    "gojo_blue": "https://files.catbox.moe/0910n9.jpg",
    "gojo_unlimited_void": "https://files.catbox.moe/yixtqh.jpg",
    "curse_evolution": "https://files.catbox.moe/b4u7eh.jpg",
    "default_domain": "https://files.catbox.moe/anryee.jpg",
    "victory_normal": "https://files.catbox.moe/wdzn1a.jpg",
    "victory_boss": "https://files.catbox.moe/byndj2.jpg",
    "awakening": "https://files.catbox.moe/ath91a.jpg",
    "clan_raid": "https://files.catbox.moe/0fr9g2.jpg",
    "story_boss": "https://files.catbox.moe/13bc2a.jpg",
    "heavenly_restriction": "https://files.catbox.moe/sgtc5w.jpg",
    "achievement": "https://files.catbox.moe/bfrhbv.jpg",
    "dungeon_clear": "https://files.catbox.moe/wq4cu7.jpg",
    "tower_clear": "https://files.catbox.moe/wq4cu7.jpg",
}

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()
db_pool = None

ongoing_battles = {}
battle_queues = {}
pvp_matches = {}

# ------------------------------------------------------------
# HELPERS
# ------------------------------------------------------------
def calc_rank(level):
    if level >= 50: return "Special Grade"
    if level >= 30: return "Semi-Special"
    if level >= 20: return "Grade 1"
    if level >= 15: return "Grade 2"
    if level >= 10: return "Grade 3"
    return "Grade 4"

def calc_level(xp):
    lvl = 1
    while True:
        needed = 100 + (lvl - 1) * 25
        if xp < needed:
            return lvl
        xp -= needed
        lvl += 1

def parse_effect(eff_str):
    out = {}
    if not eff_str: return out
    for part in eff_str.split('|'):
        if ':' in part:
            k, v = part.split(':')
            out[k] = v
        else:
            out[part] = True
    return out

def build_hp_bar(current, max_hp, length=15):
    if max_hp <= 0: max_hp = 1
    ratio = current / max_hp
    ratio = max(0, min(1, ratio))
    filled = int(ratio * length)
    empty = length - filled
    bar = "█" * filled + "░" * empty
    if ratio >= 0.75: prefix = "🟢"
    elif ratio >= 0.4: prefix = "🟡"
    else: prefix = "🔴"
    return f"{prefix} {bar}"

def build_ce_bar(current, max_ce, length=12):
    if max_ce <= 0: max_ce = 1
    ratio = current / max_ce
    ratio = max(0, min(1, ratio))
    filled = int(ratio * length)
    empty = length - filled
    bar = "█" * filled + "░" * empty
    if ratio >= 0.7: prefix = "🔵"
    elif ratio >= 0.3: prefix = "🟣"
    else: prefix = "⚪"
    return f"{prefix} {bar}"

def safe_rep_str(rep_data):
    if isinstance(rep_data, dict):
        return ", ".join([f"{k}: {v}" for k, v in rep_data.items()]) if rep_data else "None"
    elif isinstance(rep_data, str):
        try:
            rep_dict = json.loads(rep_data)
            return ", ".join([f"{k}: {v}" for k, v in rep_dict.items()]) if rep_dict else "None"
        except:
            return rep_data or "None"
    return "None"

def get_combo_points(level):
    return max(1, min(5, (level // 5) + 1))

def scale_stats_from_base(base_atk, base_def, base_spd, base_hp, base_ce, level, bonus_atk=0, bonus_hp=0, restriction_bonus_atk=0, restriction_bonus_def=0, restriction_bonus_spd=0):
    new_hp = base_hp + (level * 8) + bonus_hp
    new_ce = base_ce + (level * 5)
    new_atk = base_atk + (level * 2) + bonus_atk + restriction_bonus_atk
    new_def = base_def + int(level * 1.5) + restriction_bonus_def
    new_spd = base_spd + level + restriction_bonus_spd
    return new_hp, new_ce, new_atk, new_def, new_spd

def scale_enemy_to_player(player, enemy_base):
    if not player or not enemy_base:
        return enemy_base
    level = player.get('level', 1)
    player_atk = player.get('atk', 10)
    player_def = player.get('def', 10)
    player_hp = player.get('max_hp', 100)

    if level <= 5:
        hp_mult, atk_mult, reward_mult = 1.0, 0.8, 1.0
    elif level <= 10:
        hp_mult, atk_mult, reward_mult = 1.5, 1.0, 1.5
    elif level <= 20:
        hp_mult, atk_mult, reward_mult = 2.0, 1.2, 2.0
    elif level <= 35:
        hp_mult, atk_mult, reward_mult = 3.0, 1.5, 3.0
    elif level <= 50:
        hp_mult, atk_mult, reward_mult = 4.5, 2.0, 4.5
    elif level <= 70:
        hp_mult, atk_mult, reward_mult = 6.0, 2.5, 6.0
    else:
        hp_mult, atk_mult, reward_mult = 8.0, 3.0, 8.0

    enemy = dict(enemy_base)
    enemy['hp'] = int(max(player_hp * 1.5, enemy.get('base_hp', 100) * hp_mult))
    enemy['atk'] = int(max(player_atk * 0.8, enemy.get('base_atk', 10) * atk_mult))
    enemy['def'] = int(max(player_def * 0.6, enemy.get('base_def', 10) * atk_mult * 0.8))
    enemy['spd'] = int(enemy.get('base_spd', 10) * atk_mult * 0.9)
    enemy['reward_yen'] = int((enemy.get('reward_yen', 500) or 500) * reward_mult)
    enemy['reward_xp'] = int((enemy.get('reward_xp', 50) or 50) * reward_mult)
    enemy['max_hp'] = enemy['hp']
    enemy['rank'] = enemy_base.get('rank', 'Special Grade')
    return enemy

async def is_owner(user_id):
    return user_id == OWNER_ID

async def is_admin(user_id):
    async with db_pool.acquire() as conn:
        row = await conn.fetchrow("SELECT role FROM admins WHERE user_id = $1", user_id)
        return row is not None and row['role'] in ('owner', 'admin')

async def can_manage_yen(user_id):
    return user_id == OWNER_ID

def dedupe_domains(domains):
    if not domains:
        return []
    seen = set()
    result = []
    for d in domains:
        if d.lower() not in seen:
            seen.add(d.lower())
            result.append(d)
    return result

async def update_player_stats(user_id):
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

# ------------------------------------------------------------
# MESSAGE EDITING HELPER
# ------------------------------------------------------------
async def edit_battle_message(callback: types.CallbackQuery, caption: str, reply_markup=None, media_url=None):
    try:
        msg = callback.message
        if msg.photo or msg.animation:
            if not media_url:
                await callback.message.edit_caption(caption=caption, reply_markup=reply_markup)
            else:
                media = InputMediaPhoto(media=media_url, caption=caption)
                await callback.message.edit_media(media=media, reply_markup=reply_markup)
        else:
            await callback.message.edit_text(caption, reply_markup=reply_markup, parse_mode="Markdown")
    except Exception as e:
        if "message is not modified" in str(e):
            pass
        else:
            raise

# ------------------------------------------------------------
# DATABASE INIT
# ------------------------------------------------------------
async def on_startup():
    global db_pool
    db_pool = await asyncpg.create_pool(DATABASE_URL)
    print("✅ Database connected!")

async def on_shutdown():
    await db_pool.close()
    print("✅ Database closed!")

# ================================================================
# COMMANDS – ALL HANDLERS
# ================================================================

@dp.message(Command("start"))
async def start_cmd(message: types.Message):
    user_id = message.from_user.id
    username = message.from_user.username or "Unknown"
    chat_id = message.chat.id
    try:
        async with db_pool.acquire() as conn:
            await conn.execute("""
                INSERT INTO players (user_id, username, chat_id)
                VALUES ($1, $2, $3)
                ON CONFLICT (user_id) DO UPDATE SET username = $2
            """, user_id, username, chat_id)
            await conn.execute("""
                INSERT INTO player_characters (player_id, character_name)
                VALUES ($1, 'Yuji Itadori')
                ON CONFLICT DO NOTHING
            """, user_id)
            player = await conn.fetchrow("SELECT domains FROM players WHERE user_id = $1", user_id)
            if player and player['domains']:
                unique = dedupe_domains(player['domains'])
                await conn.execute("UPDATE players SET domains = $1 WHERE user_id = $2", unique, user_id)
            await conn.execute("UPDATE players SET last_ce_regen = NOW() WHERE user_id = $1 AND last_ce_regen IS NULL", user_id)
            await conn.execute("UPDATE players SET in_battle = FALSE WHERE user_id = $1", user_id)
            await update_player_stats(user_id)
    except Exception as e:
        print("start db error:", e)

    player = None
    try:
        async with db_pool.acquire() as conn:
            player = await conn.fetchrow("SELECT * FROM players WHERE user_id = $1", user_id)
    except:
        pass

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🧙 Profile", callback_data="welcome_profile"),
         InlineKeyboardButton(text="⚔️ Battle", callback_data="welcome_battle")],
        [InlineKeyboardButton(text="🎭 Characters", callback_data="welcome_characters"),
         InlineKeyboardButton(text="🏪 Shop", callback_data="welcome_shop")],
        [InlineKeyboardButton(text="👹 Enemies", callback_data="welcome_enemies"),
         InlineKeyboardButton(text="📦 Bag", callback_data="welcome_bag")],
        [InlineKeyboardButton(text="📋 Commands", callback_data="welcome_commands"),
         InlineKeyboardButton(text="💰 Buy Yen", callback_data="welcome_buy_yen")]
    ])

    if player:
        char_name = player.get('character_name') or "None"
        msg = (
            f"🧙 **Welcome back, {username}!**\n"
            f"━━━━━━━━━━━━━━━━━━━\n"
            f"🎭 Character: {char_name}\n"
            f"🏅 Rank: {calc_rank(player['level'])}\n"
            f"📊 Level: {player['level']}\n"
            f"💰 Yen: ¥{player['yen']:,}\n"
            f"❤️ HP: {player['hp']}/{player['max_hp']}\n"
            f"🔵 CE: {player['ce']}/{player['max_ce']}\n"
            f"━━━━━━━━━━━━━━━━━━━\n"
            f"Select an option below:"
        )
    else:
        msg = (
            f"🧙 **Welcome to Cursed Chronicles, {username}!**\n"
            f"━━━━━━━━━━━━━━━━━━━\n"
            f"⚔️ Fight cursed spirits\n"
            f"🎭 Collect all characters\n"
            f"🏪 Buy weapons and techniques\n"
            f"👥 Form clans with friends\n"
            f"━━━━━━━━━━━━━━━━━━━\n"
            f"Select an option below to start your journey!"
        )
    await message.reply(msg, reply_markup=keyboard)

@dp.callback_query(lambda c: c.data.startswith("welcome_"))
async def welcome_cb(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    action = callback.data.replace("welcome_", "")
    await callback.answer()
    if action == "profile": await profile_cmd(callback.message)
    elif action == "battle": await battle_cmd(callback.message)
    elif action == "characters": await characters_cmd(callback.message)
    elif action == "shop": await shop_cmd(callback.message)
    elif action == "enemies": await enemies_cmd(callback.message)
    elif action == "bag": await bag_cmd(callback.message)
    elif action == "commands": await commands_cmd(callback.message)
    elif action == "buy_yen": await send_owner_info(callback.message)

@dp.message(Command("guide"))
async def guide_cmd(message: types.Message):
    guide_text = (
        "📖 **Cursed Chronicles – Complete Game Guide**\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        "⚔️ **BATTLE SYSTEM**\n"
        "• Combo Points (CP) = level/5+1 (max 5).\n"
        "• Chain moves, enemy counters once.\n"
        "• **Domain Sure-Hit**: Domains ignore DEF.\n"
        "• **Domain Clash**: If both use domain, stronger multiplier wins.\n"
        "• **Multiplayer**: Clan raids allow multiple players to attack the same boss!\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        "🛡️ **HEAVENLY RESTRICTION** (at level 10)\n"
        "• `/restriction toji` – CE=0, ATK/DEF/SPD ×2.\n"
        "• `/restriction maki` – weapon mastery (+50% ATK from weapons).\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        "👹 **CURSE EVOLUTION**\n"
        "• Defeat bosses to evolve: Grade 4 → ... → Disaster Curse.\n"
        "• Unlocks passive regeneration at Special Grade.\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        "🌀 **SHIKIGAMI** (Megumi only)\n"
        "• `/shikigami summon [name]` in battle.\n"
        "• Effects: Divine Dogs (+ATK), Nue (stun), Mahoraga (8x DMG).\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        "⚖️ **BINDING VOWS**\n"
        "• `/vow list` and `/vow [name]` to activate.\n"
        "• Risk/reward buffs last several turns.\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        "📊 **LEVELING & PRESTIGE**\n"
        "• HP/CE/ATK/DEF/SPD scale with level.\n"
        "• `/prestige` at level 100 for permanent bonuses.\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        "📜 **STORY MODE**\n"
        "• `/story` to see chapters.\n"
        "• `/story_chapter [num]` to start a chapter.\n"
        "• Each chapter has a boss and rewards.\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        "🏰 **DUNGEON & TOWER**\n"
        "• `/dungeon` – infinite procedural floors.\n"
        "• `/tower` – 100 floors, boss every 10.\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"📌 **Owner**: {OWNER_NAME}\n"
        "Type `/commands` for full command list."
    )
    await message.reply(guide_text)

@dp.message(Command("stats"))
async def stats_cmd(message: types.Message):
    user_id = message.from_user.id
    async with db_pool.acquire() as conn:
        player = await conn.fetchrow("SELECT * FROM players WHERE user_id = $1", user_id)
        if not player:
            await message.reply("Start with /start first!")
            return
        char_name = player.get('character_name') or "None"
        caption = (
            f"📊 **Combat Stats**\n"
            f"━━━━━━━━━━━━━━━━━━━\n"
            f"🎭 Character: {char_name}\n"
            f"🏅 Rank: {calc_rank(player['level'])}\n"
            f"📊 Level: {player['level']}\n"
            f"⭐ XP: {player['xp']} (Next: {100 + (player['level']-1)*25 - player['xp']})\n"
            f"❤️ HP: {player['hp']}/{player['max_hp']}\n"
            f"🔵 CE: {player['ce']}/{player['max_ce']}\n"
            f"⚔️ ATK: {player['atk']}\n"
            f"🛡️ DEF: {player['def']}\n"
            f"💨 SPD: {player['spd']}\n"
            f"🏆 Wins: {player['wins']} | ❌ Losses: {player['losses']}\n"
            f"👑 Boss Kills: {player['boss_kills']}\n"
            f"⚡ Black Flash: {player['black_flash_count']}\n"
        )
        await message.reply(caption)

@dp.message(Command("addyenall"))
async def addyenall_cmd(message: types.Message):
    if not await is_owner(message.from_user.id):
        await message.reply("❌ Owner only!")
        return
    args = message.text.split()
    if len(args) < 2:
        await message.reply("Usage: /addyenall amount")
        return
    try:
        amount = int(args[1])
    except:
        await message.reply("❌ Invalid amount.")
        return
    if amount <= 0 or amount > MAX_YEN:
        await message.reply(f"❌ Amount must be between 1 and {MAX_YEN}.")
        return
    try:
        async with db_pool.acquire() as conn:
            await conn.execute("UPDATE players SET yen = LEAST(yen + $1, $2)", amount, MAX_YEN)
            count = await conn.fetchval("SELECT COUNT(*) FROM players")
            await message.reply(f"✅ Added ¥{amount:,} to all **{count}** players.")
    except Exception as e:
        await message.reply(f"Error: {e}")

@dp.message(Command("removeyenall"))
async def removeyenall_cmd(message: types.Message):
    if not await is_owner(message.from_user.id):
        await message.reply("❌ Owner only!")
        return
    args = message.text.split()
    if len(args) < 2:
        await message.reply("Usage: /removeyenall amount")
        return
    try:
        amount = int(args[1])
    except:
        await message.reply("❌ Invalid amount.")
        return
    if amount <= 0 or amount > MAX_YEN:
        await message.reply(f"❌ Amount must be between 1 and {MAX_YEN}.")
        return
    try:
        async with db_pool.acquire() as conn:
            await conn.execute("UPDATE players SET yen = GREATEST(yen - $1, 0)", amount)
            count = await conn.fetchval("SELECT COUNT(*) FROM players")
            await message.reply(f"✅ Removed ¥{amount:,} from all **{count}** players.")
    except Exception as e:
        await message.reply(f"Error: {e}")

@dp.message(Command("restriction"))
async def restriction_cmd(message: types.Message):
    args = message.text.split()
    if len(args) < 2:
        await message.reply("Usage: /restriction toji | /restriction maki")
        return
    user_id = message.from_user.id
    async with db_pool.acquire() as conn:
        player = await conn.fetchrow("SELECT * FROM players WHERE user_id = $1", user_id)
        if not player:
            await message.reply("Start with /start first!")
            return
        if player['level'] < 10:
            await message.reply("❌ You need at least level 10 to choose a restriction.")
            return
        if player.get('restriction'):
            await message.reply("You already have a restriction. You cannot change it.")
            return
        choice = args[1].lower()
        if choice == 'toji':
            await conn.execute("UPDATE players SET restriction = 'toji' WHERE user_id = $1", user_id)
            await update_player_stats(user_id)
            await message.reply_animation(animation=EFFECTS["heavenly_restriction"])
            await message.reply("🔒 **Heavenly Restriction: Toji Type**\nCE → 0, ATK/DEF/SPD ×2.")
        elif choice == 'maki':
            await conn.execute("UPDATE players SET restriction = 'maki' WHERE user_id = $1", user_id)
            await update_player_stats(user_id)
            await message.reply_animation(animation=EFFECTS["heavenly_restriction"])
            await message.reply("🔒 **Heavenly Restriction: Maki Type**\nWeapon mastery: +50% ATK from equipped weapons.")
        else:
            await message.reply("❌ Invalid restriction. Choose 'toji' or 'maki'.")

@dp.message(Command("vow"))
async def vow_cmd(message: types.Message):
    args = message.text.split()
    if len(args) < 2:
        await message.reply("Usage: /vow list | /vow [name]")
        return
    user_id = message.from_user.id
    async with db_pool.acquire() as conn:
        if args[1].lower() == 'list':
            vows = await conn.fetch("SELECT * FROM binding_vows")
            if not vows:
                await message.reply("No vows available.")
                return
            resp = "⚖️ **Binding Vows**\n━━━━━━━━━━━━━━━━━━━\n"
            for v in vows:
                resp += f"• **{v['name']}**: {v['description']} (Duration: {v['duration']} turns, Cooldown: {v['cooldown']} min)\n"
            resp += "\nUse `/vow [name]` to activate."
            await message.reply(resp)
            return
        name = " ".join(args[1:])
        vow = await conn.fetchrow("SELECT * FROM binding_vows WHERE name ILIKE $1", name)
        if not vow:
            await message.reply(f"Vow '{name}' not found.")
            return
        player_vow = await conn.fetchrow("SELECT * FROM player_vows WHERE player_id = $1 AND vow_id = $2", user_id, vow['id'])
        if player_vow:
            last = player_vow.get('last_used')
            if last and (datetime.now() - last).total_seconds() < vow['cooldown'] * 60:
                remaining = int(vow['cooldown'] * 60 - (datetime.now() - last).total_seconds())
                await message.reply(f"⏳ Vow is on cooldown. Wait {remaining} seconds.")
                return
        await conn.execute("""
            INSERT INTO player_vows (player_id, vow_id, active, last_used)
            VALUES ($1, $2, TRUE, NOW())
            ON CONFLICT (player_id, vow_id) DO UPDATE SET active = TRUE, last_used = NOW()
        """, user_id, vow['id'])
        await message.reply(f"⚖️ **Binding Vow activated: {vow['name']}**\n{vow['description']}\nDuration: {vow['duration']} turns.")

@dp.message(Command("shikigami"))
async def shikigami_cmd(message: types.Message):
    args = message.text.split()
    user_id = message.from_user.id
    async with db_pool.acquire() as conn:
        player = await conn.fetchrow("SELECT character_name FROM players WHERE user_id = $1", user_id)
        if not player or player['character_name'] != 'Megumi Fushiguro':
            await message.reply("❌ Only Megumi Fushiguro can summon Shikigami.")
            return
        if len(args) < 2:
            shikigami = await conn.fetch("SELECT * FROM shikigami ORDER BY id")
            if not shikigami:
                await message.reply("No shikigami available.")
                return
            resp = "🌀 **Megumi's Shikigami**\n━━━━━━━━━━━━━━━━━━━\n"
            for s in shikigami:
                resp += f"• **{s['name']}**: {s['description']} (CE: {s['ce_cost']})\n"
            resp += "\nUse `/shikigami summon [name]` in battle."
            await message.reply(resp)
            return
        if args[1].lower() == 'summon':
            if len(args) < 3:
                await message.reply("Usage: /shikigami summon [name]")
                return
            s_name = " ".join(args[2:])
            shikigami = await conn.fetchrow("SELECT * FROM shikigami WHERE name ILIKE $1", s_name)
            if not shikigami:
                await message.reply(f"Shikigami '{s_name}' not found.")
                return
            owned = await conn.fetchrow("SELECT * FROM player_shikigami WHERE player_id = $1 AND shikigami_id = $2", user_id, shikigami['id'])
            if not owned:
                await message.reply(f"You don't own {shikigami['name']}. Defeat bosses to unlock.")
                return
            await message.reply_animation(animation=EFFECTS["shikigami_summon"])
            await message.reply(f"🌀 **{shikigami['name']} summoned!**\nEffect: {shikigami['effect']}")
        else:
            await message.reply("Unknown subcommand. Use `/shikigami` to list or `/shikigami summon [name]`.")

@dp.message(Command("profile"))
async def profile_cmd(message: types.Message):
    user_id = message.from_user.id
    try:
        async with db_pool.acquire() as conn:
            player = await conn.fetchrow("SELECT * FROM players WHERE user_id = $1", user_id)
            if not player:
                await message.reply("Start with /start first!")
                return
            char_name = player.get('character_name')
            image_url = None
            if char_name:
                char = await conn.fetchrow("SELECT image_url FROM characters WHERE name = $1", char_name)
                if char: image_url = char['image_url']
            weapon = player.get('equipped_weapon') or "None"
            title = player.get('equipped_title') or "None"
            awakening = player.get('awakening') or "None"
            clan_name = "None"
            if player.get('clan_id'):
                clan = await conn.fetchrow("SELECT name FROM clans WHERE id = $1", player['clan_id'])
                if clan: clan_name = clan['name']
            restriction = player.get('restriction') or "None"
            curse_rank = player.get('curse_rank') or "None"
            rep_str = safe_rep_str(player.get('reputation'))
            prestige_lv = player.get('prestige_level', 0)
            caption = (
                f"👤 **Cursed Chronicle**\n"
                f"━━━━━━━━━━━━━━━━━━━\n"
                f"🎭 Character: {char_name or 'None'}\n"
                f"🏅 Rank: {calc_rank(player['level'])}\n"
                f"📊 Level: {player['level']}\n"
                f"⭐ XP: {player['xp']}\n"
                f"💰 Yen: ¥{player['yen']:,}\n"
                f"🏆 Wins: {player['wins']} | ❌ Losses: {player['losses']}\n"
                f"👑 Boss Kills: {player['boss_kills']}\n"
                f"⚡ Black Flash: {player['black_flash_count']}\n"
                f"━━━━━━━━━━━━━━━━━━━\n"
                f"❤️ HP: {player['hp']}/{player['max_hp']}\n"
                f"🔵 CE: {player['ce']}/{player['max_ce']}\n"
                f"⚔️ ATK: {player['atk']} | 🛡️ DEF: {player['def']} | 💨 SPD: {player['spd']}\n"
                f"━━━━━━━━━━━━━━━━━━━\n"
                f"🌀 Awakening: {awakening}\n"
                f"📜 Title: {title}\n"
                f"🗡️ Weapon: {weapon}\n"
                f"🏛️ Clan: {clan_name}\n"
                f"⭐ Reputation: {rep_str}\n"
                f"━━━━━━━━━━━━━━━━━━━\n"
                f"💎 Prestige: {prestige_lv}/10\n"
                f"🏟️ Arena Rank: {player['arena_rank']}\n"
                f"🔒 Restriction: {restriction}\n"
                f"👹 Curse Rank: {curse_rank}\n"
                f"━━━━━━━━━━━━━━━━━━━\n"
                f"{YEN_PURCHASE_INFO}"
            )
            if awakening != "None":
                await message.reply_animation(animation=EFFECTS["awakening"], caption=caption)
            elif image_url:
                await message.reply_photo(photo=image_url, caption=caption)
            else:
                await message.reply(caption)
    except Exception as e:
        await message.reply(f"Error: {e}")

@dp.message(Command("characters"))
async def characters_cmd(message: types.Message):
    try:
        async with db_pool.acquire() as conn:
            count = await conn.fetchval("SELECT COUNT(*) FROM characters")
            if count == 0:
                await message.reply("No characters available.")
                return
            await send_char_page(message, 0)
    except Exception as e:
        await message.reply(f"Error: {e}")

async def send_char_page(message_or_callback, page):
    per_page = 1
    try:
        async with db_pool.acquire() as conn:
            offset = page * per_page
            total = await conn.fetchval("SELECT COUNT(*) FROM characters")
            if offset >= total: offset = 0
            char = await conn.fetchrow("SELECT * FROM characters ORDER BY id LIMIT 1 OFFSET $1", offset)
            if not char: return

            user_id = None
            if isinstance(message_or_callback, types.Message):
                user_id = message_or_callback.from_user.id
            else:
                user_id = message_or_callback.from_user.id

            owned = False
            if user_id:
                own = await conn.fetchrow("SELECT * FROM player_characters WHERE player_id = $1 AND character_name = $2",
                                          user_id, char['name'])
                if own: owned = True

            caption = (
                f"🎭 **{char['name']}** - {char['rank']}\n"
                f"━━━━━━━━━━━━━━━━━━━\n"
                f"⚔️ ATK: {char['atk']} | 🛡️ DEF: {char['def']} | 💨 SPD: {char['spd']}\n"
                f"❤️ HP: {char['hp']} | 🔵 CE: {char['ce']}\n"
                f"💰 Price: ¥{char['price']:,}\n"
                f"━━━━━━━━━━━━━━━━━━━\n"
                f"Page {page+1}/{ (total + per_page -1)//per_page }\n"
                f"{'✅ Owned' if owned else '❌ Not Owned'}"
            )

            buttons = []
            if owned:
                buttons.append([InlineKeyboardButton(text=f"✅ Select {char['name']}", callback_data=f"char_select_{char['id']}")])
            else:
                if char['price'] == 0:
                    buttons.append([InlineKeyboardButton(text=f"✅ Get Free {char['name']}", callback_data=f"char_buy_free_{char['id']}")])
                else:
                    buttons.append([InlineKeyboardButton(text=f"💰 Buy {char['name']} (¥{char['price']:,})", callback_data=f"char_buy_{char['id']}")])
            buttons.append([
                InlineKeyboardButton(text="⬅️", callback_data=f"char_page_{page-1}"),
                InlineKeyboardButton(text=f"{page+1}", callback_data="char_page_noop"),
                InlineKeyboardButton(text="➡️", callback_data=f"char_page_{page+1}")
            ])
            keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)

            if isinstance(message_or_callback, types.Message):
                msg = message_or_callback
                if char.get('image_url'):
                    await msg.reply_photo(photo=char['image_url'], caption=caption, reply_markup=keyboard)
                else:
                    await msg.reply(caption, reply_markup=keyboard)
            else:
                callback = message_or_callback
                if char.get('image_url'):
                    await callback.message.edit_media(
                        InputMediaPhoto(media=char['image_url'], caption=caption),
                        reply_markup=keyboard
                    )
                else:
                    await callback.message.edit_text(caption, reply_markup=keyboard)
    except Exception as e:
        if isinstance(message_or_callback, types.Message):
            await message_or_callback.reply(f"Error: {e}")
        else:
            await message_or_callback.answer(f"Error: {e}", show_alert=True)

@dp.callback_query(lambda c: c.data.startswith("char_page_"))
async def char_page_cb(callback: types.CallbackQuery):
    page = int(callback.data.split("_")[2])
    if page < 0: page = 0
    await callback.answer()
    await send_char_page(callback, page)

@dp.callback_query(lambda c: c.data.startswith("char_buy_") or c.data.startswith("char_buy_free_"))
async def char_buy_cb(callback: types.CallbackQuery):
    data = callback.data
    parts = data.split("_")
    if parts[1] == "buy" and parts[2] != "free":
        char_id = int(parts[2])
        free = False
    else:
        char_id = int(parts[3])
        free = True

    user_id = callback.from_user.id
    try:
        async with db_pool.acquire() as conn:
            char = await conn.fetchrow("SELECT * FROM characters WHERE id = $1", char_id)
            if not char:
                await callback.answer("Character not found!", show_alert=True)
                return
            owned = await conn.fetchrow("SELECT * FROM player_characters WHERE player_id = $1 AND character_name = $2",
                                        user_id, char['name'])
            if owned:
                await callback.answer("You already own this character!", show_alert=True)
                return
            if not free:
                player = await conn.fetchrow("SELECT yen FROM players WHERE user_id = $1", user_id)
                if player['yen'] < char['price']:
                    await callback.answer(f"Not enough Yen! Need ¥{char['price']:,}", show_alert=True)
                    return
                await conn.execute("UPDATE players SET yen = yen - $1 WHERE user_id = $2", char['price'], user_id)
                await conn.execute("INSERT INTO player_characters (player_id, character_name) VALUES ($1, $2)",
                                   user_id, char['name'])
                await callback.answer(f"Bought {char['name']}!")
            else:
                await conn.execute("INSERT INTO player_characters (player_id, character_name) VALUES ($1, $2)",
                                   user_id, char['name'])
                await callback.answer(f"Got {char['name']} for free!")
            await send_char_page(callback, 0)
    except Exception as e:
        await callback.answer(f"Error: {e}", show_alert=True)

@dp.callback_query(lambda c: c.data.startswith("char_select_"))
async def char_select_cb(callback: types.CallbackQuery):
    char_id = int(callback.data.split("_")[2])
    user_id = callback.from_user.id
    try:
        async with db_pool.acquire() as conn:
            char = await conn.fetchrow("SELECT * FROM characters WHERE id = $1", char_id)
            if not char:
                await callback.answer("Character not found!", show_alert=True)
                return
            owned = await conn.fetchrow("SELECT * FROM player_characters WHERE player_id = $1 AND character_name = $2",
                                        user_id, char['name'])
            if not owned and char['price'] != 0:
                await callback.answer("You don't own this character! Buy it first.", show_alert=True)
                return
            await conn.execute("""
                UPDATE players 
                SET character_name = $1, 
                    atk = $2, def = $3, spd = $4, 
                    hp = $5, ce = $6, max_hp = $5, max_ce = $6
                WHERE user_id = $7
            """, char['name'], char['atk'], char['def'], char['spd'], 
               char['hp'], char['ce'], user_id)
            await update_player_stats(user_id)
            caption = (
                f"✅ You selected **{char['name']}** as your fighter!\n"
                f"━━━━━━━━━━━━━━━━━━━\n"
                f"⚔️ ATK: {char['atk']} | 🛡️ DEF: {char['def']} | 💨 SPD: {char['spd']}\n"
                f"❤️ HP: {char['hp']} | 🔵 CE: {char['ce']}\n"
                f"━━━━━━━━━━━━━━━━━━━\n"
                f"Check /profile to see your updated stats!"
            )
            if char.get('image_url'):
                await callback.message.edit_media(
                    InputMediaPhoto(media=char['image_url'], caption=caption),
                    reply_markup=None
                )
            else:
                await callback.message.edit_text(caption, reply_markup=None)
    except Exception as e:
        await callback.answer(f"Error: {e}", show_alert=True)

@dp.callback_query(lambda c: c.data == "char_page_noop")
async def char_page_noop(callback: types.CallbackQuery):
    await callback.answer("Current page")

@dp.message(Command("select"))
async def select_cmd(message: types.Message):
    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        await message.reply("Usage: /select \"character name\"")
        return
    name = args[1].strip()
    user_id = message.from_user.id
    try:
        async with db_pool.acquire() as conn:
            char = await conn.fetchrow("SELECT * FROM characters WHERE name ILIKE $1", name)
            if not char:
                await message.reply(f"Character '{name}' not found.")
                return
            owned = await conn.fetchrow("SELECT * FROM player_characters WHERE player_id = $1 AND character_name = $2",
                                        user_id, char['name'])
            if not owned and char['price'] != 0:
                await message.reply(f"You don't own {char['name']}! Buy it via /characters.")
                return
            await conn.execute("""
                UPDATE players 
                SET character_name = $1, 
                    atk = $2, def = $3, spd = $4, 
                    hp = $5, ce = $6, max_hp = $5, max_ce = $6
                WHERE user_id = $7
            """, char['name'], char['atk'], char['def'], char['spd'], 
               char['hp'], char['ce'], user_id)
            await update_player_stats(user_id)
            await message.reply(f"✅ Selected **{char['name']}**! Check /profile")
    except Exception as e:
        await message.reply(f"Error: {e}")

@dp.message(Command("shop"))
async def shop_cmd(message: types.Message):
    args = message.text.split()
    page = 1
    if len(args) > 1:
        try: page = int(args[1])
        except: page = 1
    await send_shop_page(message, page)

async def send_shop_page(message_or_callback, page):
    per_page = 5
    try:
        async with db_pool.acquire() as conn:
            total = await conn.fetchval("SELECT COUNT(*) FROM shop_items")
            if total == 0:
                await message_or_callback.reply("Shop is empty.")
                return
            max_page = (total + per_page - 1) // per_page
            if page < 1: page = 1
            if page > max_page: page = max_page
            offset = (page - 1) * per_page
            items = await conn.fetch("SELECT * FROM shop_items ORDER BY category, name LIMIT $1 OFFSET $2", per_page, offset)
            response = f"🏪 **Jujutsu Shop — Page {page}/{max_page}**\n━━━━━━━━━━━━━━━━━━━\n"
            current_cat = None
            for it in items:
                if it['category'] != current_cat:
                    current_cat = it['category']
                    response += f"\n📌 **{current_cat.upper()}**\n"
                response += f"  • **{it['name']}**\n"
                response += f"    💰 ¥{it['price']:,}\n"
                if it['effect']:
                    response += f"    ✨ {it['effect'].replace('|', ' | ')}\n"
                if it['description']:
                    response += f"    📖 {it['description']}\n"
            response += "\n━━━━━━━━━━━━━━━━━━━\n"
            response += f"Page {page}/{max_page} — Use /shop [page] to jump\n"
            response += "Buy: /buy \"item name\""
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="⬅️", callback_data=f"shop_page_{page-1}"),
                 InlineKeyboardButton(text=f"{page}/{max_page}", callback_data="shop_page_noop"),
                 InlineKeyboardButton(text="➡️", callback_data=f"shop_page_{page+1}")]
            ])
            if isinstance(message_or_callback, types.Message):
                await message_or_callback.reply(response, reply_markup=keyboard)
            else:
                callback = message_or_callback
                await callback.message.edit_text(response, reply_markup=keyboard)
    except Exception as e:
        if isinstance(message_or_callback, types.Message):
            await message_or_callback.reply(f"Error: {e}")
        else:
            await message_or_callback.answer(f"Error: {e}", show_alert=True)

@dp.callback_query(lambda c: c.data.startswith("shop_page_"))
async def shop_page_cb(callback: types.CallbackQuery):
    page = int(callback.data.split("_")[2])
    if page < 1: page = 1
    await callback.answer()
    await send_shop_page(callback, page)

@dp.callback_query(lambda c: c.data == "shop_page_noop")
async def shop_page_noop(callback: types.CallbackQuery):
    await callback.answer("Current page")

@dp.message(Command("buy"))
async def buy_cmd(message: types.Message):
    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        await message.reply("Usage: /buy \"item name\"")
        return
    item_name = args[1].strip()
    user_id = message.from_user.id
    try:
        async with db_pool.acquire() as conn:
            player = await conn.fetchrow("SELECT * FROM players WHERE user_id = $1", user_id)
            if not player:
                await message.reply("Start with /start first!")
                return
            item = await conn.fetchrow("SELECT * FROM shop_items WHERE name ILIKE $1", item_name)
            if not item:
                await message.reply(f"Item '{item_name}' not found in shop.")
                return
            if player['yen'] < item['price']:
                await message.reply(f"❌ Not enough Yen! You have ¥{player['yen']:,}, need ¥{item['price']:,}.")
                return
            if item['category'] == 'technique':
                techniques = player.get('techniques') or []
                if item['name'] in techniques:
                    await message.reply(f"⚠️ You already own technique '{item['name']}'.")
                    return
            await conn.execute("UPDATE players SET yen = yen - $1 WHERE user_id = $2", item['price'], user_id)
            if item['category'] == 'technique':
                await conn.execute("UPDATE players SET techniques = array_append(techniques, $1) WHERE user_id = $2",
                                   item['name'], user_id)
            else:
                await conn.execute("UPDATE players SET bag = array_append(bag, $1) WHERE user_id = $2",
                                   item['name'], user_id)
            await message.reply(f"✅ Bought **{item['name']}**!\n💰 Remaining: ¥{player['yen'] - item['price']:,}\n📦 Check /bag")
    except Exception as e:
        await message.reply(f"Error: {e}")

@dp.message(Command("bag"))
async def bag_cmd(message: types.Message):
    user_id = message.from_user.id
    try:
        async with db_pool.acquire() as conn:
            player = await conn.fetchrow("SELECT * FROM players WHERE user_id = $1", user_id)
            if not player:
                await message.reply("Start with /start first!")
                return
            bag = player.get('bag') or []
            techniques = player.get('techniques') or []
            domains = player.get('domains') or []
            if not bag and not techniques and not domains:
                await message.reply("📦 Your inventory is empty. Buy from /shop.")
                return
            resp = "📦 **Your Inventory**\n━━━━━━━━━━━━━━━━━━━\n"
            if bag:
                resp += "\n📦 **Items:**\n"
                for it in bag[:20]: resp += f"  • {it}\n"
                if len(bag) > 20: resp += f"  ... and {len(bag)-20} more\n"
            if techniques:
                resp += "\n🌀 **Techniques:**\n"
                for t in techniques[:20]: resp += f"  • {t}\n"
                if len(techniques) > 20: resp += f"  ... and {len(techniques)-20} more\n"
            if domains:
                resp += "\n🌐 **Domains:**\n"
                for d in domains[:10]: resp += f"  • {d}\n"
                if len(domains) > 10: resp += f"  ... and {len(domains)-10} more\n"
            resp += "\n━━━━━━━━━━━━━━━━━━━\n"
            resp += "Use: /use \"item name\"\n"
            resp += "Equip: /equip \"weapon name\"\n"
            resp += "Learn: /learn \"tech name\""
            await message.reply(resp)
    except Exception as e:
        await message.reply(f"Error: {e}")

@dp.message(Command("use"))
async def use_cmd(message: types.Message):
    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        await message.reply("Usage: /use \"item name\"")
        return
    item_name = args[1].strip()
    user_id = message.from_user.id
    try:
        async with db_pool.acquire() as conn:
            player = await conn.fetchrow("SELECT * FROM players WHERE user_id = $1", user_id)
            if not player:
                await message.reply("Start with /start first!")
                return
            bag = player.get('bag') or []
            if item_name not in bag:
                await message.reply(f"❌ You don't have '{item_name}' in your bag.")
                return
            item = await conn.fetchrow("SELECT * FROM shop_items WHERE name ILIKE $1", item_name)
            if not item:
                await message.reply(f"Item '{item_name}' not found.")
                return
            effects = parse_effect(item['effect'])
            response = f"✅ Used **{item['name']}**!\n━━━━━━━━━━━━━━━━━━━\n"
            if 'heal_hp' in effects:
                hp_heal = int(effects['heal_hp'])
                new_hp = min(player['hp'] + hp_heal, player['max_hp'])
                await conn.execute("UPDATE players SET hp = $1 WHERE user_id = $2", new_hp, user_id)
                response += f"❤️ Restored {hp_heal} HP! ({new_hp}/{player['max_hp']})\n"
            if 'heal_ce' in effects:
                ce_heal = int(effects['heal_ce'])
                new_ce = min(player['ce'] + ce_heal, player['max_ce'])
                await conn.execute("UPDATE players SET ce = $1 WHERE user_id = $2", new_ce, user_id)
                response += f"🔵 Restored {ce_heal} CE! ({new_ce}/{player['max_ce']})\n"
            if 'heal_full' in effects:
                await conn.execute("UPDATE players SET hp = max_hp, ce = max_ce WHERE user_id = $1", user_id)
                response += "❤️ HP and 🔵 CE fully restored!\n"
            if 'add_xp' in effects:
                xp_gain = int(effects['add_xp'])
                new_xp = player['xp'] + xp_gain
                await conn.execute("UPDATE players SET xp = $1 WHERE user_id = $2", new_xp, user_id)
                await update_player_stats(user_id)
                player = await conn.fetchrow("SELECT * FROM players WHERE user_id = $1", user_id)
                response += f"⭐ Gained {xp_gain} XP! (Level {player['level']}, Rank {calc_rank(player['level'])})\n"
            await conn.execute("UPDATE players SET bag = array_remove(bag, $1) WHERE user_id = $2",
                               item_name, user_id)
            if 'heal_hp' in effects or 'heal_ce' in effects or 'heal_full' in effects:
                await message.reply_animation(animation=EFFECTS["heal"], caption=response)
            else:
                await message.reply(response)
    except Exception as e:
        await message.reply(f"Error: {e}")

@dp.message(Command("equip"))
async def equip_cmd(message: types.Message):
    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        await message.reply("Usage: /equip \"weapon name\"")
        return
    weapon_name = args[1].strip()
    user_id = message.from_user.id
    try:
        async with db_pool.acquire() as conn:
            player = await conn.fetchrow("SELECT * FROM players WHERE user_id = $1", user_id)
            if not player:
                await message.reply("Start with /start first!")
                return
            bag = player.get('bag') or []
            if weapon_name not in bag:
                await message.reply(f"❌ You don't have '{weapon_name}' in your bag.")
                return
            weapon = await conn.fetchrow("SELECT * FROM shop_items WHERE name ILIKE $1 AND category = 'weapon'", weapon_name)
            if not weapon:
                await message.reply(f"'{weapon_name}' is not a weapon.")
                return
            effects = parse_effect(weapon['effect'])
            atk_bonus = int(effects.get('atk_bonus', 0))
            if player.get('restriction') == 'maki':
                atk_bonus = int(atk_bonus * 1.5)
            old_weapon = player.get('equipped_weapon')
            if old_weapon:
                old = await conn.fetchrow("SELECT * FROM shop_items WHERE name = $1 AND category = 'weapon'", old_weapon)
                if old:
                    old_effects = parse_effect(old['effect'])
                    old_bonus = int(old_effects.get('atk_bonus', 0))
                    if player.get('restriction') == 'maki':
                        old_bonus = int(old_bonus * 1.5)
                    await conn.execute("UPDATE players SET atk = atk - $1 WHERE user_id = $2", old_bonus, user_id)
            await conn.execute("UPDATE players SET equipped_weapon = $1, atk = atk + $2 WHERE user_id = $3",
                               weapon_name, atk_bonus, user_id)
            await message.reply(f"✅ Equipped **{weapon_name}**! (ATK +{atk_bonus}) Check /profile.")
    except Exception as e:
        await message.reply(f"Error: {e}")

@dp.message(Command("learn"))
async def learn_cmd(message: types.Message):
    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        await message.reply("Usage: /learn \"technique name\"")
        return
    raw_name = args[1].strip()
    normalized = " ".join(raw_name.split())
    user_id = message.from_user.id
    try:
        async with db_pool.acquire() as conn:
            player = await conn.fetchrow("SELECT * FROM players WHERE user_id = $1", user_id)
            if not player:
                await message.reply("Start with /start first!")
                return
            techniques = player.get('techniques') or []
            domains = player.get('domains') or []

            matched_tech = None
            for t in techniques:
                if t.lower().strip() == normalized.lower():
                    matched_tech = t
                    break
            if matched_tech:
                await message.reply_animation(
                    animation=EFFECTS["cursed_energy"],
                    caption=f"🌀 **{matched_tech}** is ready to use in battle!\nUse the 'Technique' button."
                )
                return

            matched_domain = None
            for d in domains:
                if d.lower().strip() == normalized.lower():
                    matched_domain = d
                    break
            if matched_domain:
                await message.reply(
                    f"🌐 **{matched_domain}** is a Domain Expansion.\n"
                    f"Use the **'Domain'** button in battle to activate it."
                )
                return

            await message.reply(f"❌ You don't own '{normalized}'. Buy it from /shop first.")
    except Exception as e:
        await message.reply(f"Error: {e}")

@dp.message(Command("techniques"))
async def techniques_cmd(message: types.Message):
    user_id = message.from_user.id
    try:
        async with db_pool.acquire() as conn:
            player = await conn.fetchrow("SELECT techniques, character_name FROM players WHERE user_id = $1", user_id)
            if not player:
                await message.reply("Start with /start first!")
                return
            techs = player.get('techniques') or []
            if not techs:
                await message.reply("🌀 You haven't learned any techniques. Buy from /shop and /learn.")
                return
            resp = "🌀 **Your Techniques**\n━━━━━━━━━━━━━━━━━━━\n"
            for t in techs:
                detail = await conn.fetchrow("SELECT * FROM techniques WHERE name = $1", t)
                if detail:
                    char_req = detail.get('character_name') or "Universal"
                    resp += f"  • {t} (DMG: {detail['damage_multiplier']}x, CE: {detail['ce_cost']}, Character: {char_req})\n"
                else:
                    resp += f"  • {t}\n"
            await message.reply(resp)
    except Exception as e:
        await message.reply(f"Error: {e}")

@dp.message(Command("enemies"))
async def enemies_cmd(message: types.Message):
    try:
        async with db_pool.acquire() as conn:
            enemies = await conn.fetch("SELECT * FROM enemies ORDER BY is_boss DESC, rank")
            if not enemies:
                await message.reply("No enemies found.")
                return
            bosses = [e for e in enemies if e['is_boss']]
            response = (
                f"👹 **Cursed Spirits**\n"
                f"━━━━━━━━━━━━━━━━━━━\n"
                f"Total: {len(enemies)}\n"
                f"👑 Bosses: {len(bosses)}\n"
                f"━━━━━━━━━━━━━━━━━━━\n"
                f"⚔️ Fight: /battle\n"
                f"👑 Boss: /boss [name]"
            )
            await message.reply(response)
    except Exception as e:
        await message.reply(f"Error: {e}")

# ------------------------------------------------------------
# STORY MODE
# ------------------------------------------------------------
@dp.message(Command("story"))
async def story_cmd(message: types.Message):
    user_id = message.from_user.id
    async with db_pool.acquire() as conn:
        chapters = await conn.fetch("SELECT * FROM story_chapters ORDER BY chapter_num")
        if not chapters:
            await message.reply("No story chapters available.")
            return
        player_progress = await conn.fetch("SELECT chapter_id FROM player_story WHERE player_id = $1 AND completed = TRUE", user_id)
        completed = [p['chapter_id'] for p in player_progress]
        resp = "📜 **Story Mode**\n━━━━━━━━━━━━━━━━━━━\n"
        for ch in chapters:
            status = "✅" if ch['id'] in completed else "🔒" if ch['id'] > len(completed) + 1 else "⏳"
            resp += f"{status} **Chapter {ch['chapter_num']}: {ch['title']}**\n"
            resp += f"   {ch['description']}\n"
            resp += f"   Boss: {ch['boss_name']} | Rewards: ¥{ch['reward_yen']} + {ch['reward_xp']} XP\n"
        resp += "\nUse `/story_chapter [number]` to start a chapter."
        await message.reply(resp)

@dp.message(Command("story_chapter"))
async def story_chapter_cmd(message: types.Message):
    args = message.text.split()
    if len(args) < 2:
        await message.reply("Usage: /story_chapter [chapter number]")
        return
    try:
        chapter_num = int(args[1])
    except:
        await message.reply("Invalid chapter number.")
        return
    user_id = message.from_user.id
    async with db_pool.acquire() as conn:
        chapter = await conn.fetchrow("SELECT * FROM story_chapters WHERE chapter_num = $1", chapter_num)
        if not chapter:
            await message.reply(f"Chapter {chapter_num} not found.")
            return
        completed = await conn.fetchrow("SELECT * FROM player_story WHERE player_id = $1 AND chapter_id = $2 AND completed = TRUE", user_id, chapter['id'])
        if completed:
            await message.reply(f"✅ You have already completed Chapter {chapter_num}.")
            return
        if chapter_num > 1:
            prev = await conn.fetchrow("SELECT * FROM story_chapters WHERE chapter_num = $1", chapter_num - 1)
            if prev:
                prev_done = await conn.fetchrow("SELECT * FROM player_story WHERE player_id = $1 AND chapter_id = $2 AND completed = TRUE", user_id, prev['id'])
                if not prev_done:
                    await message.reply(f"❌ You must complete Chapter {chapter_num - 1} first.")
                    return
        await message.reply_animation(animation=EFFECTS["story_boss"])
        await message.reply(f"⚔️ **Story Chapter {chapter_num}: {chapter['title']}**\nBoss: {chapter['boss_name']}\nDefeat it to claim your rewards!")
        await boss_cmd(message, chapter['boss_name'], is_story=True, chapter_id=chapter['id'])

# ------------------------------------------------------------
# BATTLE / BOSS (PvE)
# ------------------------------------------------------------
async def boss_cmd(message: types.Message, boss_name: str = None, is_story: bool = False, chapter_id: int = None):
    if boss_name is None:
        args = message.text.split(maxsplit=1)
        if len(args) < 2:
            await message.reply("Usage: /boss \"boss name\"")
            return
        boss_name = args[1].strip()
    user_id = message.from_user.id
    if user_id in ongoing_battles:
        await message.reply("⚠️ You already have an ongoing battle! Use `/status` or `/resume`.")
        return
    try:
        async with db_pool.acquire() as conn:
            player = await conn.fetchrow("SELECT * FROM players WHERE user_id = $1", user_id)
            if not player:
                await message.reply("Start with /start first!")
                return
            now = datetime.now()
            last = player.get('last_ce_regen') or now
            delta = (now - last).total_seconds()
            regen = int(delta // 10)
            if regen > 0:
                new_ce = min(player['max_ce'], player['ce'] + regen)
                await conn.execute("UPDATE players SET ce = $1, last_ce_regen = $2 WHERE user_id = $3",
                                   new_ce, now, user_id)
                player = await conn.fetchrow("SELECT * FROM players WHERE user_id = $1", user_id)
            enemy_base = await conn.fetchrow("SELECT * FROM enemies WHERE name ILIKE $1 AND is_boss = TRUE", boss_name)
            if not enemy_base:
                await message.reply(f"Boss '{boss_name}' not found.")
                return
            enemy = scale_enemy_to_player(player, enemy_base)
            await message.reply_animation(animation=EFFECTS["versus"])
            battle_id = await conn.fetchval("""
                INSERT INTO battles (chat_id, player1_id, current_hp1, current_hp2, 
                                     enemy_name, enemy_rank, enemy_atk, enemy_def, enemy_spd,
                                     is_boss, enemy_reward_yen, enemy_reward_xp, enemy_max_hp,
                                     vow_effects, participants, is_story, chapter_id)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, TRUE, $10, $11, $12, $13, $14, $15, $16)
                RETURNING id
            """, message.chat.id, user_id, player['hp'], enemy['hp'], 
               enemy['name'], enemy['rank'], enemy['atk'], enemy['def'], enemy['spd'],
               enemy.get('reward_yen', 5000), enemy.get('reward_xp', 500), enemy['hp'],
               json.dumps([]), json.dumps([user_id]), is_story, chapter_id)
            ongoing_battles[user_id] = battle_id
            battle_queues[battle_id] = {
                "participants": {user_id: []},
                "current_hp": enemy['hp'],
                "log": []
            }
            vows = await conn.fetch("SELECT v.effect FROM player_vows pv JOIN binding_vows v ON pv.vow_id = v.id WHERE pv.player_id = $1 AND pv.active = TRUE", user_id)
            vow_effects = [v['effect'] for v in vows]
            await conn.execute("UPDATE battles SET vow_effects = $1 WHERE id = $2", json.dumps(vow_effects), battle_id)
            await show_battle_turn(message, battle_id, player, enemy, vow_effects)
    except Exception as e:
        await message.reply(f"Error starting boss: {e}")

@dp.message(Command("boss"))
async def boss_cmd_handler(message: types.Message):
    await boss_cmd(message)

@dp.message(Command("battle"))
async def battle_cmd(message: types.Message):
    user_id = message.from_user.id
    if user_id in ongoing_battles:
        await message.reply("⚠️ You already have an ongoing battle! Use `/status` or `/resume`.")
        return
    try:
        async with db_pool.acquire() as conn:
            player = await conn.fetchrow("SELECT * FROM players WHERE user_id = $1", user_id)
            if not player:
                await message.reply("Start with /start first!")
                return
            now = datetime.now()
            last = player.get('last_ce_regen') or now
            delta = (now - last).total_seconds()
            regen = int(delta // 10)
            if regen > 0:
                new_ce = min(player['max_ce'], player['ce'] + regen)
                await conn.execute("UPDATE players SET ce = $1, last_ce_regen = $2 WHERE user_id = $3",
                                   new_ce, now, user_id)
                player = await conn.fetchrow("SELECT * FROM players WHERE user_id = $1", user_id)
            enemy_base = await conn.fetchrow("SELECT * FROM enemies WHERE is_boss = FALSE ORDER BY RANDOM() LIMIT 1")
            if not enemy_base:
                await message.reply("No enemies available!")
                return
            enemy = scale_enemy_to_player(player, enemy_base)
            await message.reply_animation(animation=EFFECTS["versus"])
            battle_id = await conn.fetchval("""
                INSERT INTO battles (chat_id, player1_id, current_hp1, current_hp2, 
                                     enemy_name, enemy_rank, enemy_atk, enemy_def, enemy_spd,
                                     is_boss, enemy_reward_yen, enemy_reward_xp, enemy_max_hp,
                                     vow_effects, participants)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, FALSE, $10, $11, $12, $13, $14)
                RETURNING id
            """, message.chat.id, user_id, player['hp'], enemy['hp'], 
               enemy['name'], enemy['rank'], enemy['atk'], enemy['def'], enemy['spd'],
               enemy.get('reward_yen', 1000), enemy.get('reward_xp', 100), enemy['hp'],
               json.dumps([]), json.dumps([user_id]))
            ongoing_battles[user_id] = battle_id
            battle_queues[battle_id] = {
                "participants": {user_id: []},
                "current_hp": enemy['hp'],
                "log": []
            }
            vows = await conn.fetch("SELECT v.effect FROM player_vows pv JOIN binding_vows v ON pv.vow_id = v.id WHERE pv.player_id = $1 AND pv.active = TRUE", user_id)
            vow_effects = [v['effect'] for v in vows]
            await conn.execute("UPDATE battles SET vow_effects = $1 WHERE id = $2", json.dumps(vow_effects), battle_id)
            await show_battle_turn(message, battle_id, player, enemy, vow_effects)
    except Exception as e:
        await message.reply(f"Error starting battle: {e}")

# show_battle_turn (called from PvE, PvP, and resuming)
async def show_battle_turn(message_or_callback, battle_id, player, enemy, vow_effects=[], log_lines=None):
    cp = get_combo_points(player['level'])
    queue = battle_queues.get(battle_id, {}).get('participants', {}).get(player['user_id'], [])
    used_cp = sum(m.get('cp_cost', 0) for m in queue)

    log_text = ""
    if battle_queues.get(battle_id, {}).get('log'):
        log_lines = battle_queues[battle_id]['log'][-5:]
        log_text = "\n".join(f"• {line}" for line in log_lines)
        log_text = f"\n📜 **Battle Log:**\n{log_text}\n"
    elif log_lines:
        log_text = "\n".join(f"• {line}" for line in log_lines[-5:])
        log_text = f"\n📜 **Battle Log:**\n{log_text}\n"

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=f"⚔️ Attack (1 CP, 0 CE)", callback_data=f"bt|add|{battle_id}|attack|1|0")],
        [InlineKeyboardButton(text=f"🛡️ Defend (1 CP, 0 CE)", callback_data=f"bt|add|{battle_id}|defend|1|0")],
        [InlineKeyboardButton(text=f"💥 Special (2 CP, 30 CE)", callback_data=f"bt|add|{battle_id}|special|2|30")],
        [InlineKeyboardButton(text="🌀 Technique", callback_data=f"bt|tech|{battle_id}")],
        [InlineKeyboardButton(text="🌐 Domain", callback_data=f"bt|domain|{battle_id}")],
        [InlineKeyboardButton(text=f"▶️ Execute Combo ({used_cp}/{cp} CP used)", callback_data=f"bt|execute|{battle_id}")],
        [InlineKeyboardButton(text="🏃 Run", callback_data=f"bt|run|{battle_id}")]
    ])

    hp_bar = build_hp_bar(player['hp'], player['max_hp'])
    ce_bar = build_ce_bar(player['ce'], player['max_ce'])
    enemy_hp_bar = build_hp_bar(enemy['hp'], enemy['max_hp'])

    caption = (
        f"⚔️ **BATTLE**\n"
        f"━━━━━━━━━━━━━━━━━━━\n"
        f"🧙 {player.get('character_name') or 'You'}\n"
        f"❤️ HP: {player['hp']}/{player['max_hp']} {hp_bar}\n"
        f"🔵 CE: {player['ce']}/{player['max_ce']} {ce_bar}\n"
        f"━━━━━━━━━━━━━━━━━━━\n"
        f"💀 **{enemy['name']}** - {enemy['rank']}\n"
        f"❤️ HP: {enemy['hp']} {enemy_hp_bar}\n"
        f"━━━━━━━━━━━━━━━━━━━\n"
        f"🌀 Combo Points: {cp} (used: {used_cp})\n"
        f"Select moves, then press Execute Combo.\n"
        f"{log_text}"
    )

    if isinstance(message_or_callback, types.Message):
        msg = message_or_callback
        if enemy.get('image_url'):
            await msg.reply_photo(photo=enemy['image_url'], caption=caption, reply_markup=keyboard)
        else:
            await msg.reply(caption, reply_markup=keyboard)
    else:
        callback = message_or_callback
        media_url = enemy.get('image_url') or EFFECTS["default_domain"]
        await edit_battle_message(callback, caption, keyboard, media_url)

# ------------------------------------------------------------
# BATTLE CALLBACK (bt|) – includes character filtering
# ------------------------------------------------------------
@dp.callback_query(lambda c: c.data.startswith("bt|"))
async def battle_turn_cb(callback: types.CallbackQuery):
    data = callback.data
    parts = data.split("|")
    action = parts[1]

    if action == "add":
        battle_id = int(parts[2])
        move_type = parts[3]
        cp_cost = int(parts[4])
        ce_cost = int(parts[5])
    elif action == "tech":
        battle_id = int(parts[2])
    elif action == "domain":
        battle_id = int(parts[2])
    elif action == "execute":
        battle_id = int(parts[2])
    elif action == "run":
        battle_id = int(parts[2])
    elif action == "back":
        battle_id = int(parts[2])
    elif action == "addtech":
        battle_id = int(parts[2])
        cp_cost = int(parts[3])
        ce_cost = int(parts[4])
        tech_name = parts[5]
    elif action == "adddomain":
        battle_id = int(parts[2])
        cp_cost = int(parts[3])
        ce_cost = int(parts[4])
        dmg_mult = float(parts[5])
        domain_name = parts[6]
    else:
        await callback.answer("Unknown action.", show_alert=True)
        return

    user_id = callback.from_user.id
    async with db_pool.acquire() as conn:
        battle = await conn.fetchrow("SELECT * FROM battles WHERE id = $1", battle_id)
        if not battle or battle['status'] != 'active':
            await callback.answer("Battle expired!", show_alert=True)
            return

        if battle.get('is_pvp'):
            if user_id not in (battle['player1_id'], battle['player2_id']):
                await callback.answer("You are not in this battle.", show_alert=True)
                return
        else:
            if user_id != battle['player1_id']:
                await callback.answer("You are not the player in this battle.", show_alert=True)
                return

        player_record = await conn.fetchrow("SELECT * FROM players WHERE user_id = $1", user_id)
        if not player_record:
            await callback.answer("Player not found!", show_alert=True)
            return
        player = dict(player_record)

        if battle.get('is_pvp'):
            other_id = battle['player1_id'] if user_id == battle['player2_id'] else battle['player2_id']
            other_player = await conn.fetchrow("SELECT * FROM players WHERE user_id = $1", other_id)
            if other_player:
                enemy = {
                    "name": other_player['character_name'] or "Player",
                    "rank": calc_rank(other_player['level']),
                    "hp": battle['current_hp2'] if user_id == battle['player1_id'] else battle['current_hp1'],
                    "atk": other_player['atk'],
                    "def": other_player['def'],
                    "spd": other_player['spd'],
                    "max_hp": other_player['max_hp'],
                    "image_url": None
                }
            else:
                await callback.answer("Enemy not found.", show_alert=True)
                return
        else:
            enemy = {
                "name": battle['enemy_name'],
                "rank": battle['enemy_rank'],
                "hp": battle['current_hp2'],
                "atk": battle['enemy_atk'],
                "def": battle['enemy_def'],
                "spd": battle['enemy_spd'],
                "max_hp": battle['enemy_max_hp'],
                "image_url": None
            }

        vow_effects = json.loads(battle.get('vow_effects', '[]'))

        if battle_id not in battle_queues:
            battle_queues[battle_id] = {"participants": {}, "current_hp": enemy['hp'], "log": []}
        if user_id not in battle_queues[battle_id]['participants']:
            battle_queues[battle_id]['participants'][user_id] = []
        queue = battle_queues[battle_id]['participants'][user_id]

        # ACTIONS
        if action == "add":
            cp = get_combo_points(player['level'])
            used_cp = sum(m.get('cp_cost', 0) for m in queue)
            if used_cp + cp_cost > cp:
                await callback.answer(f"Not enough Combo Points! (Used {used_cp}/{cp})", show_alert=True)
                return
            total_ce = sum(m.get('ce_cost', 0) for m in queue) + ce_cost
            if player['ce'] < total_ce:
                await callback.answer(f"Not enough CE! Need {total_ce}, have {player['ce']}", show_alert=True)
                return
            move = {"type": move_type, "cp_cost": cp_cost, "ce_cost": ce_cost}
            queue.append(move)
            await callback.answer(f"Added {move_type}!")
            await show_battle_turn(callback, battle_id, player, enemy, vow_effects)

        elif action == "tech":
            techs = player.get('techniques') or []
            if not techs:
                await callback.answer("You have no techniques!", show_alert=True)
                return
            player_char = player.get('character_name')
            compatible = []
            for t in techs:
                tech = await conn.fetchrow("SELECT * FROM techniques WHERE name = $1", t)
                if tech:
                    if tech.get('character_name') is None or tech['character_name'] == player_char:
                        compatible.append(t)
            if not compatible:
                await callback.answer("No techniques compatible with your current character!", show_alert=True)
                return
            buttons = []
            for t in compatible[:10]:
                tech = await conn.fetchrow("SELECT * FROM techniques WHERE name = $1", t)
                if tech:
                    ce_cost = tech['ce_cost']
                    cp_cost = 2
                    buttons.append([InlineKeyboardButton(
                        text=f"🌀 {t} ({cp_cost} CP, {ce_cost} CE)",
                        callback_data=f"bt|addtech|{battle_id}|{cp_cost}|{ce_cost}|{t}"
                    )])
            buttons.append([InlineKeyboardButton(text="🔙 Back", callback_data=f"bt|back|{battle_id}")])
            markup = InlineKeyboardMarkup(inline_keyboard=buttons)
            await callback.message.edit_text(
                f"🌀 **Select a Technique**\n"
                f"Choose a technique to add to your combo.",
                reply_markup=markup
            )
            await callback.answer()

        elif action == "domain":
            domains = player.get('domains') or []
            if not domains:
                await callback.answer("You have no domains!", show_alert=True)
                return
            player_char = player.get('character_name')
            compatible = []
            for d in domains:
                domain = await conn.fetchrow("SELECT * FROM techniques WHERE name = $1 AND category = 'domain'", d)
                if domain:
                    if domain.get('character_name') is None or domain['character_name'] == player_char:
                        compatible.append(d)
                else:
                    domain_item = await conn.fetchrow("SELECT * FROM shop_items WHERE name = $1 AND category = 'domain'", d)
                    if domain_item:
                        compatible.append(d)
            if not compatible:
                await callback.answer("No domains compatible with your current character!", show_alert=True)
                return
            buttons = []
            for d in compatible[:5]:
                domain = await conn.fetchrow("SELECT * FROM techniques WHERE name = $1 AND category = 'domain'", d)
                if domain:
                    ce_cost = domain['ce_cost']
                    dmg_mult = domain['damage_multiplier']
                else:
                    domain_item = await conn.fetchrow("SELECT * FROM shop_items WHERE name = $1 AND category = 'domain'", d)
                    if domain_item:
                        ce_cost = int(parse_effect(domain_item['effect']).get('ce_cost', 100))
                        dmg_mult = float(parse_effect(domain_item['effect']).get('damage', 3.5))
                    else:
                        continue
                cp_cost = 3
                buttons.append([InlineKeyboardButton(
                    text=f"🌐 {d} ({cp_cost} CP, {ce_cost} CE, {dmg_mult}x)",
                    callback_data=f"bt|adddomain|{battle_id}|{cp_cost}|{ce_cost}|{dmg_mult}|{d}"
                )])
            buttons.append([InlineKeyboardButton(text="🔙 Back", callback_data=f"bt|back|{battle_id}")])
            markup = InlineKeyboardMarkup(inline_keyboard=buttons)
            await callback.message.edit_text(
                f"🌐 **Select a Domain**\n"
                f"Choose a domain to add to your combo.",
                reply_markup=markup
            )
            await callback.answer()

        elif action == "back":
            await show_battle_turn(callback, battle_id, player, enemy, vow_effects)
            await callback.answer()

        elif action == "addtech":
            tech = await conn.fetchrow("SELECT * FROM techniques WHERE name = $1", tech_name)
            if tech and tech.get('character_name') is not None and tech['character_name'] != player.get('character_name'):
                await callback.answer("This technique is not compatible with your character!", show_alert=True)
                return
            cp = get_combo_points(player['level'])
            used_cp = sum(m.get('cp_cost', 0) for m in queue)
            if used_cp + cp_cost > cp:
                await callback.answer(f"Not enough Combo Points! (Used {used_cp}/{cp})", show_alert=True)
                return
            total_ce = sum(m.get('ce_cost', 0) for m in queue) + ce_cost
            if player['ce'] < total_ce:
                await callback.answer(f"Not enough CE! Need {total_ce}, have {player['ce']}", show_alert=True)
                return
            move = {"type": "technique", "cp_cost": cp_cost, "ce_cost": ce_cost, "tech_name": tech_name}
            queue.append(move)
            await callback.answer(f"Added {tech_name}!")
            await show_battle_turn(callback, battle_id, player, enemy, vow_effects)

        elif action == "adddomain":
            domain = await conn.fetchrow("SELECT * FROM techniques WHERE name = $1 AND category = 'domain'", domain_name)
            if domain and domain.get('character_name') is not None and domain['character_name'] != player.get('character_name'):
                await callback.answer("This domain is not compatible with your character!", show_alert=True)
                return
            cp = get_combo_points(player['level'])
            used_cp = sum(m.get('cp_cost', 0) for m in queue)
            if used_cp + cp_cost > cp:
                await callback.answer(f"Not enough Combo Points! (Used {used_cp}/{cp})", show_alert=True)
                return
            total_ce = sum(m.get('ce_cost', 0) for m in queue) + ce_cost
            if player['ce'] < total_ce:
                await callback.answer(f"Not enough CE! Need {total_ce}, have {player['ce']}", show_alert=True)
                return
            move = {"type": "domain", "cp_cost": cp_cost, "ce_cost": ce_cost, "domain_name": domain_name, "dmg_mult": dmg_mult}
            queue.append(move)
            await callback.answer(f"Added {domain_name}!")
            await show_battle_turn(callback, battle_id, player, enemy, vow_effects)

        elif action == "execute":
            if not queue:
                await callback.answer("No moves in queue!", show_alert=True)
                return
            total_ce = sum(m.get('ce_cost', 0) for m in queue)
            if player['ce'] < total_ce:
                await callback.answer(f"Not enough CE! Need {total_ce}, have {player['ce']}", show_alert=True)
                return
            await conn.execute("UPDATE players SET ce = ce - $1 WHERE user_id = $2", total_ce, player['user_id'])
            player['ce'] -= total_ce

            exec_log = []
            total_damage = 0
            defend_flag = False

            for move in queue:
                mtype = move['type']
                if mtype == 'attack':
                    dmg = max(1, int(player['atk'] * random.uniform(0.8, 1.2)))
                    total_damage += dmg
                    exec_log.append(f"⚔️ Attack: {dmg} damage")
                elif mtype == 'defend':
                    defend_flag = True
                    exec_log.append("🛡️ Defend (halves next enemy damage)")
                elif mtype == 'special':
                    dmg = max(1, int(player['atk'] * random.uniform(1.5, 2.5)))
                    total_damage += dmg
                    exec_log.append(f"💥 Special: {dmg} damage")
                elif mtype == 'technique':
                    tech_name = move.get('tech_name')
                    tech = await conn.fetchrow("SELECT * FROM techniques WHERE name = $1", tech_name)
                    if tech:
                        dmg = max(1, int(player['atk'] * tech['damage_multiplier'] * random.uniform(0.9, 1.1)))
                        total_damage += dmg
                        exec_log.append(f"🌀 {tech_name}: {dmg} damage")
                        if "Purple" in tech_name:
                            await callback.message.reply_animation(animation=EFFECTS["gojo_purple"])
                        elif "Red" in tech_name:
                            await callback.message.reply_animation(animation=EFFECTS["gojo_red"])
                        elif "Blue" in tech_name:
                            await callback.message.reply_animation(animation=EFFECTS["gojo_blue"])
                        else:
                            await callback.message.reply_animation(animation=EFFECTS["cursed_energy"])
                elif mtype == 'domain':
                    domain_name = move.get('domain_name')
                    dmg_mult = move.get('dmg_mult', 3.5)
                    dmg = max(1, int(player['atk'] * dmg_mult * random.uniform(0.9, 1.1)))
                    total_damage += dmg
                    exec_log.append(f"🌐 **Domain: {domain_name}** (Sure-Hit, {dmg} damage)")
                    if "Unlimited Void" in domain_name:
                        await callback.message.reply_animation(animation=EFFECTS["gojo_unlimited_void"])
                    elif "Malevolent" in domain_name:
                        await callback.message.reply_animation(animation=EFFECTS["sukuna_domain"])
                    elif "Mahito" in domain_name or "Self" in domain_name:
                        await callback.message.reply_animation(animation=EFFECTS["mahito_domain"])
                    else:
                        await callback.message.reply_animation(animation=EFFECTS["default_domain"])

            if battle.get('is_pvp'):
                other_id = battle['player1_id'] if user_id == battle['player2_id'] else battle['player2_id']
                if user_id == battle['player1_id']:
                    new_other_hp = max(0, battle['current_hp2'] - total_damage)
                    await conn.execute("UPDATE battles SET current_hp2 = $1 WHERE id = $2", new_other_hp, battle_id)
                else:
                    new_other_hp = max(0, battle['current_hp1'] - total_damage)
                    await conn.execute("UPDATE battles SET current_hp1 = $1 WHERE id = $2", new_other_hp, battle_id)
                battle_queues[battle_id]['current_hp'] = new_other_hp
            else:
                new_enemy_hp = max(0, battle['current_hp2'] - total_damage)
                await conn.execute("UPDATE battles SET current_hp2 = $1 WHERE id = $2", new_enemy_hp, battle_id)
                battle_queues[battle_id]['current_hp'] = new_enemy_hp

            enemy_dmg = 0
            if not defend_flag:
                enemy_dmg = max(1, int(enemy['atk'] * random.uniform(0.5, 0.9)))
                exec_log.append(f"💢 Enemy counter‑attack: {enemy_dmg} damage")
            else:
                enemy_dmg = max(1, int(enemy['atk'] * random.uniform(0.2, 0.4)))
                exec_log.append(f"🛡️ Enemy damage reduced to {enemy_dmg} (Defend)")
                await conn.execute("UPDATE battles SET defend_flag = FALSE WHERE id = $1", battle_id)
            new_player_hp = max(0, battle['current_hp1'] - enemy_dmg)
            await conn.execute("UPDATE battles SET current_hp1 = $1 WHERE id = $2", new_player_hp, battle_id)
            player['hp'] = new_player_hp

            battle_queues[battle_id]['log'].extend(exec_log)
            if len(battle_queues[battle_id]['log']) > 10:
                battle_queues[battle_id]['log'] = battle_queues[battle_id]['log'][-10:]
            print(f"[LOG] Battle {battle_id} log: {battle_queues[battle_id]['log']}")

            battle_queues[battle_id]['participants'][user_id] = []

            # Victory/defeat checks
            if battle.get('is_pvp'):
                other_hp = battle_queues[battle_id]['current_hp']
                if other_hp <= 0:
                    await callback.message.reply_animation(animation=EFFECTS["victory_normal"])
                    winner_id = user_id
                    loser_id = other_id
                    await conn.execute("UPDATE players SET wins = wins + 1, yen = yen + 1000, xp = xp + 500 WHERE user_id = $1", winner_id)
                    await conn.execute("UPDATE players SET losses = losses + 1 WHERE user_id = $1", loser_id)
                    await update_player_stats(winner_id)
                    await update_player_stats(loser_id)
                    summary = f"🎉 **PVP VICTORY!**\nPlayer {winner_id} wins against {loser_id}!"
                    await callback.message.edit_text(summary)
                    if winner_id in ongoing_battles: del ongoing_battles[winner_id]
                    if loser_id in ongoing_battles: del ongoing_battles[loser_id]
                    if battle_id in battle_queues: del battle_queues[battle_id]
                    await callback.answer("Victory!")
                    return
            else:
                if new_enemy_hp <= 0:
                    # PvE Victory
                    is_boss = battle['is_boss']
                    is_story = battle.get('is_story', False)
                    chapter_id = battle.get('chapter_id')
                    victory_effect = EFFECTS["victory_boss"] if is_boss else EFFECTS["victory_normal"]
                    await callback.message.reply_animation(animation=victory_effect)
                    yen_reward = battle['enemy_reward_yen'] or 1000
                    xp_reward = battle['enemy_reward_xp'] or 100
                    boss_kill_inc = 1 if is_boss else 0
                    await conn.execute("""
                        UPDATE players SET yen = LEAST(yen + $1, $2), 
                                           wins = wins + 1, 
                                           xp = xp + $3,
                                           boss_kills = boss_kills + $4
                        WHERE user_id = $5
                    """, yen_reward, MAX_YEN, xp_reward, boss_kill_inc, player['user_id'])
                    await update_player_stats(player['user_id'])

                    if is_story and chapter_id:
                        await conn.execute("""
                            INSERT INTO player_story (player_id, chapter_id, completed)
                            VALUES ($1, $2, TRUE)
                            ON CONFLICT (player_id, chapter_id) DO UPDATE SET completed = TRUE
                        """, player['user_id'], chapter_id)
                        chapter = await conn.fetchrow("SELECT * FROM story_chapters WHERE id = $1", chapter_id)
                        if chapter and chapter.get('reward_title'):
                            await callback.message.reply(f"📜 **Story Chapter Completed!**\nYou earned the title: {chapter['reward_title']}")

                    if is_boss and random.random() < 0.10:
                        domains = player.get('domains') or []
                        available = ['Unlimited Void', 'Malevolent Shrine', 'Shadow Garden', 'Idle Death Gamble', 'Self-Embodiment', 'Womb Profusion', 'Coffin of the Iron Mountain']
                        new_domain = None
                        for d in available:
                            if d not in domains:
                                new_domain = d
                                break
                        if new_domain:
                            await conn.execute("UPDATE players SET domains = array_append(domains, $1) WHERE user_id = $2", new_domain, player['user_id'])
                            await callback.message.reply_animation(animation=EFFECTS["awakening"])
                            await callback.message.reply(f"🌐 **Domain Unlocked!** You gained **{new_domain}**!")

                    if is_boss:
                        boss_kills = player['boss_kills'] + 1
                        if boss_kills >= 200:
                            new_rank = "Disaster Curse"
                        elif boss_kills >= 100:
                            new_rank = "Special Grade"
                        elif boss_kills >= 50:
                            new_rank = "Grade 1"
                        elif boss_kills >= 25:
                            new_rank = "Grade 2"
                        elif boss_kills >= 10:
                            new_rank = "Grade 3"
                        else:
                            new_rank = "Grade 4"
                        if new_rank != player.get('curse_rank'):
                            await conn.execute("UPDATE players SET curse_rank = $1, curse_evolution_count = curse_evolution_count + 1 WHERE user_id = $2", new_rank, user_id)
                            await callback.message.reply_animation(animation=EFFECTS["curse_evolution"])
                            await callback.message.reply(f"👹 **Curse Evolution!** You evolved to {new_rank}!")
                            if new_rank in ["Special Grade", "Disaster Curse"]:
                                await conn.execute("UPDATE players SET curse_regen = TRUE WHERE user_id = $1", user_id)
                                await callback.message.reply("You now have passive regeneration out of battle.")

                    if battle.get('is_dungeon'):
                        run_id = battle.get('dungeon_run_id')
                        if run_id:
                            await conn.execute("UPDATE dungeon_runs SET floor = floor + 1, enemies_defeated = enemies_defeated + 1 WHERE id = $1", run_id)
                            await callback.message.reply("🏰 You advance to the next floor!")
                    elif battle.get('is_tower'):
                        run_id = battle.get('tower_run_id')
                        floor = battle.get('tower_floor', 0)
                        if run_id:
                            await conn.execute("UPDATE tower_runs SET floor = floor + 1, boss_kills = boss_kills + $1 WHERE id = $2", 1 if battle.get('is_boss') else 0, run_id)
                            if floor >= 100:
                                await conn.execute("UPDATE tower_runs SET status = 'completed' WHERE id = $1", run_id)
                                await callback.message.reply("🏆 **Tower Complete!** You have cleared all 100 floors! 🎉")
                            else:
                                await callback.message.reply(f"🗼 You climb to floor {floor+1}!")

                    full_log = battle_queues[battle_id].get('log', [])
                    log_summary = "\n".join(f"• {line}" for line in full_log[-10:])
                    summary = (
                        f"🎉 **VICTORY!**\n"
                        f"━━━━━━━━━━━━━━━━━━━\n"
                        f"**Battle Log:**\n{log_summary}\n"
                        f"━━━━━━━━━━━━━━━━━━━\n"
                        f"❤️ Your HP: {new_player_hp}  |  💀 {enemy['name']} HP: 0\n"
                        f"💰 +¥{yen_reward}\n"
                        f"⭐ +{xp_reward} XP"
                    )
                    await callback.message.edit_text(summary)
                    if user_id in ongoing_battles: del ongoing_battles[user_id]
                    if battle_id in battle_queues: del battle_queues[battle_id]
                    await callback.answer("Victory! 🎉")
                    return

            if new_player_hp <= 0:
                await callback.message.reply_animation(animation=EFFECTS["defeat"])
                await conn.execute("UPDATE players SET losses = losses + 1 WHERE user_id = $1", player['user_id'])
                full_log = battle_queues[battle_id].get('log', [])
                log_summary = "\n".join(f"• {line}" for line in full_log[-10:])
                summary = (
                    f"💀 **DEFEAT!**\n"
                    f"━━━━━━━━━━━━━━━━━━━\n"
                    f"**Battle Log:**\n{log_summary}\n"
                    f"━━━━━━━━━━━━━━━━━━━\n"
                    f"❤️ Your HP: 0  |  💀 {enemy['name']} HP: {enemy['hp']}\n"
                    f"Better luck next time!"
                )
                await callback.message.edit_text(summary)
                if user_id in ongoing_battles: del ongoing_battles[user_id]
                if battle_id in battle_queues: del battle_queues[battle_id]
                await callback.answer("Defeated! 💀")
                return

            # Continue
            enemy['hp'] = battle_queues[battle_id]['current_hp']
            log_lines = battle_queues[battle_id].get('log', [])
            await show_battle_turn(callback, battle_id, player, enemy, vow_effects, log_lines)
            await callback.answer("Combo executed!")

        elif action == "run":
            if random.random() < 0.6:
                await callback.message.edit_text("🏃 You successfully escaped!")
                if user_id in ongoing_battles: del ongoing_battles[user_id]
                if battle_id in battle_queues: del battle_queues[battle_id]
                await callback.answer("Escaped!")
            else:
                enemy_dmg = max(1, int(enemy['atk'] * random.uniform(0.8, 1.2)))
                new_hp = max(0, battle['current_hp1'] - enemy_dmg)
                await conn.execute("UPDATE battles SET current_hp1 = $1 WHERE id = $2", new_hp, battle_id)
                if new_hp <= 0:
                    await conn.execute("UPDATE players SET losses = losses + 1 WHERE user_id = $1", player['user_id'])
                    await callback.message.reply_animation(animation=EFFECTS["defeat"])
                    await callback.message.edit_text("💀 **DEFEAT!**\nFailed to escape.")
                    if user_id in ongoing_battles: del ongoing_battles[user_id]
                    if battle_id in battle_queues: del battle_queues[battle_id]
                    await callback.answer("Defeated!")
                    return
                player['hp'] = new_hp
                await show_battle_turn(callback, battle_id, player, enemy, vow_effects)
                await callback.answer("Failed to escape! Enemy attacked.")

# ------------------------------------------------------------
# STATUS & RESUME
# ------------------------------------------------------------
@dp.message(Command("status"))
async def status_cmd(message: types.Message):
    user_id = message.from_user.id
    if user_id in ongoing_battles:
        battle_id = ongoing_battles[user_id]
        async with db_pool.acquire() as conn:
            battle = await conn.fetchrow("SELECT * FROM battles WHERE id = $1 AND status = 'active'", battle_id)
            if battle:
                await message.reply(
                    f"⚔️ **You have an ongoing battle!**\n"
                    f"ID: {battle_id}\n"
                    f"Enemy: {battle['enemy_name']}\n"
                    f"Your HP: {battle['current_hp1']}\n"
                    f"Enemy HP: {battle['current_hp2']}\n"
                    f"Type `/resume {battle_id}` to continue."
                )
                return
    await message.reply("✅ No ongoing battle. Start one with `/battle` or `/boss`.")

@dp.message(Command("resume"))
async def resume_cmd(message: types.Message):
    args = message.text.split()
    if len(args) < 2:
        await message.reply("Usage: /resume battle_id")
        return
    battle_id = int(args[1])
    user_id = message.from_user.id
    async with db_pool.acquire() as conn:
        battle = await conn.fetchrow("SELECT * FROM battles WHERE id = $1 AND player1_id = $2 AND status = 'active'",
                                     battle_id, user_id)
        if not battle:
            await message.reply("❌ Battle not found or already finished.")
            return
        player = await conn.fetchrow("SELECT * FROM players WHERE user_id = $1", user_id)
        enemy = {
            "name": battle['enemy_name'],
            "rank": battle['enemy_rank'],
            "hp": battle['current_hp2'],
            "atk": battle['enemy_atk'],
            "def": battle['enemy_def'],
            "spd": battle['enemy_spd'],
            "max_hp": battle['enemy_max_hp']
        }
        if battle_id not in battle_queues:
            battle_queues[battle_id] = {"participants": {user_id: []}, "current_hp": enemy['hp'], "log": []}
        vows = json.loads(battle.get('vow_effects', '[]'))
        log_lines = battle_queues[battle_id].get('log', [])
        await show_battle_turn(message, battle_id, player, enemy, vows, log_lines)

# ------------------------------------------------------------
# PRESTIGE
# ------------------------------------------------------------
@dp.message(Command("prestige"))
async def prestige_cmd(message: types.Message):
    user_id = message.from_user.id
    async with db_pool.acquire() as conn:
        player = await conn.fetchrow("SELECT * FROM players WHERE user_id = $1", user_id)
        if not player:
            await message.reply("Start with /start first!")
            return
        if player['level'] < 100:
            await message.reply("❌ You need at least level 100 to prestige.")
            return
        if player.get('prestige_level', 0) >= 10:
            await message.reply("❌ You have reached max prestige (10).")
            return
        new_prestige = player.get('prestige_level', 0) + 1
        bonus_atk = player.get('prestige_bonus_atk', 0) + int(player['atk'] * 0.05)
        bonus_hp = player.get('prestige_bonus_hp', 0) + int(player['max_hp'] * 0.05)
        await conn.execute("""
            UPDATE players 
            SET level = 1, xp = 0, prestige_level = $1, 
                prestige_bonus_atk = $2, prestige_bonus_hp = $3,
                max_hp = $4, max_ce = $5, atk = $6, def = $7, spd = $8,
                hp = $4, ce = $5
            WHERE user_id = $9
        """, new_prestige, bonus_atk, bonus_hp, 100, 100, 10, 10, 10, user_id)
        await message.reply_animation(animation=EFFECTS["awakening"])
        await message.reply(
            f"🌟 **Prestige Complete!**\n"
            f"━━━━━━━━━━━━━━━━━━━\n"
            f"Prestige Level: {new_prestige}/10\n"
            f"Permanent ATK Bonus: +{bonus_atk}\n"
            f"Permanent HP Bonus: +{bonus_hp}\n"
            f"Level reset to 1. Good luck!"
        )

# ------------------------------------------------------------
# PVP (full turn‑based)
# ------------------------------------------------------------
@dp.message(Command("pvp_challenge"))
async def pvp_challenge(message: types.Message):
    args = message.text.split()
    if len(args) < 2:
        await message.reply("Usage: /pvp_challenge @user")
        return
    target = args[1].replace("@", "")
    challenger = message.from_user.id
    async with db_pool.acquire() as conn:
        target_user = await conn.fetchrow("SELECT * FROM players WHERE username ILIKE $1", target)
        if not target_user:
            await message.reply("User not found.")
            return
        if target_user['user_id'] == challenger:
            await message.reply("You can't challenge yourself.")
            return
        if challenger in ongoing_battles or target_user['user_id'] in ongoing_battles:
            await message.reply("One of you is already in a battle.")
            return
        player1 = await conn.fetchrow("SELECT * FROM players WHERE user_id = $1", challenger)
        player2 = target_user
        battle_id = await conn.fetchval("""
            INSERT INTO battles (chat_id, player1_id, player2_id, current_hp1, current_hp2, is_pvp, status, turn, timeout)
            VALUES ($1, $2, $3, $4, $5, TRUE, 'pending', 1, NOW() + INTERVAL '60 seconds')
            RETURNING id
        """, message.chat.id, challenger, target_user['user_id'], player1['hp'], player2['hp'])
        pvp_matches[battle_id] = {'challenger': challenger, 'target': target_user['user_id'], 'turn': 1}
        await message.reply(f"⚔️ **PVP Challenge sent to {target}!**\nThey have 60 seconds to type `/pvp_accept {battle_id}`.")

@dp.message(Command("pvp_accept"))
async def pvp_accept(message: types.Message):
    args = message.text.split()
    if len(args) < 2:
        return
    battle_id = int(args[1])
    user_id = message.from_user.id
    async with db_pool.acquire() as conn:
        battle = await conn.fetchrow("SELECT * FROM battles WHERE id = $1 AND is_pvp = TRUE", battle_id)
        if not battle or battle['status'] != 'pending':
            await message.reply("Invalid or expired battle.")
            return
        if battle['player2_id'] != user_id:
            await message.reply("This battle is not for you.")
            return
        await conn.execute("UPDATE battles SET status = 'active', timeout = NOW() + INTERVAL '60 seconds' WHERE id = $1", battle_id)
        ongoing_battles[battle['player1_id']] = battle_id
        ongoing_battles[battle['player2_id']] = battle_id
        battle_queues[battle_id] = {
            "participants": {battle['player1_id']: [], battle['player2_id']: []},
            "current_hp1": battle['current_hp1'],
            "current_hp2": battle['current_hp2'],
            "log": [],
            "pvp": True,
            "turn": 1
        }
        first = random.choice([battle['player1_id'], battle['player2_id']])
        battle_queues[battle_id]['turn_player'] = first
        await message.reply(f"⚔️ **PVP BATTLE START!**\n<code>{first}</code> goes first.\nUse `/pvp_move` to select moves.")
        await bot.send_message(first, f"⚔️ **Your turn!** Use `/pvp_move {battle_id}` to select moves.")

@dp.message(Command("pvp_move"))
async def pvp_move(message: types.Message):
    args = message.text.split()
    if len(args) < 2:
        await message.reply("Usage: /pvp_move battle_id")
        return
    battle_id = int(args[1])
    user_id = message.from_user.id
    async with db_pool.acquire() as conn:
        battle = await conn.fetchrow("SELECT * FROM battles WHERE id = $1 AND is_pvp = TRUE AND status = 'active'", battle_id)
        if not battle:
            await message.reply("Battle not found or not active.")
            return
        if battle_id not in battle_queues:
            await message.reply("Battle queue not found.")
            return
        if battle_queues[battle_id].get('turn_player') != user_id:
            await message.reply("It's not your turn.")
            return
        player = await conn.fetchrow("SELECT * FROM players WHERE user_id = $1", user_id)
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="⚔️ Attack (1 CP)", callback_data=f"pvp_add|{battle_id}|attack|1|0")],
            [InlineKeyboardButton(text="🛡️ Defend (1 CP)", callback_data=f"pvp_add|{battle_id}|defend|1|0")],
            [InlineKeyboardButton(text="💥 Special (2 CP)", callback_data=f"pvp_add|{battle_id}|special|2|30")],
            [InlineKeyboardButton(text="🌀 Technique", callback_data=f"pvp_tech|{battle_id}")],
            [InlineKeyboardButton(text="🌐 Domain", callback_data=f"pvp_domain|{battle_id}")],
            [InlineKeyboardButton(text="⏭️ Pass (0 CP)", callback_data=f"pvp_pass|{battle_id}")]
        ])
        await message.reply("Select your moves for this turn:", reply_markup=keyboard)

@dp.callback_query(lambda c: c.data.startswith("pvp_"))
async def pvp_callback(callback: types.CallbackQuery):
    data = callback.data
    parts = data.split("|")
    action = parts[0].replace("pvp_", "")
    battle_id = int(parts[1])
    user_id = callback.from_user.id
    async with db_pool.acquire() as conn:
        battle = await conn.fetchrow("SELECT * FROM battles WHERE id = $1 AND is_pvp = TRUE AND status = 'active'", battle_id)
        if not battle:
            await callback.answer("Battle not found.", show_alert=True)
            return
        if battle_queues[battle_id].get('turn_player') != user_id:
            await callback.answer("It's not your turn.", show_alert=True)
            return
        player = await conn.fetchrow("SELECT * FROM players WHERE user_id = $1", user_id)
        queue = battle_queues[battle_id]['participants'][user_id]
        if action == "add":
            move_type = parts[2]
            cp_cost = int(parts[3])
            ce_cost = int(parts[4])
            cp = get_combo_points(player['level'])
            used_cp = sum(m.get('cp_cost', 0) for m in queue)
            if used_cp + cp_cost > cp:
                await callback.answer(f"Not enough Combo Points! (Used {used_cp}/{cp})", show_alert=True)
                return
            total_ce = sum(m.get('ce_cost', 0) for m in queue) + ce_cost
            if player['ce'] < total_ce:
                await callback.answer(f"Not enough CE! Need {total_ce}, have {player['ce']}", show_alert=True)
                return
            move = {"type": move_type, "cp_cost": cp_cost, "ce_cost": ce_cost}
            queue.append(move)
            await callback.answer(f"Added {move_type}!")
            await pvp_move_menu(callback.message, battle_id, user_id)
        elif action == "tech":
            techs = player.get('techniques') or []
            if not techs:
                await callback.answer("You have no techniques!", show_alert=True)
                return
            player_char = player.get('character_name')
            compatible = []
            for t in techs:
                tech = await conn.fetchrow("SELECT * FROM techniques WHERE name = $1", t)
                if tech:
                    if tech.get('character_name') is None or tech['character_name'] == player_char:
                        compatible.append(t)
            if not compatible:
                await callback.answer("No techniques compatible with your current character!", show_alert=True)
                return
            buttons = []
            for t in compatible[:10]:
                tech = await conn.fetchrow("SELECT * FROM techniques WHERE name = $1", t)
                if tech:
                    ce_cost = tech['ce_cost']
                    cp_cost = 2
                    buttons.append([InlineKeyboardButton(
                        text=f"🌀 {t} ({cp_cost} CP, {ce_cost} CE)",
                        callback_data=f"pvp_addtech|{battle_id}|{cp_cost}|{ce_cost}|{t}"
                    )])
            buttons.append([InlineKeyboardButton(text="🔙 Back", callback_data=f"pvp_back|{battle_id}")])
            markup = InlineKeyboardMarkup(inline_keyboard=buttons)
            await callback.message.edit_text("Select a technique:", reply_markup=markup)
            await callback.answer()
        elif action == "domain":
            domains = player.get('domains') or []
            if not domains:
                await callback.answer("You have no domains!", show_alert=True)
                return
            player_char = player.get('character_name')
            compatible = []
            for d in domains:
                domain = await conn.fetchrow("SELECT * FROM techniques WHERE name = $1 AND category = 'domain'", d)
                if domain:
                    if domain.get('character_name') is None or domain['character_name'] == player_char:
                        compatible.append(d)
                else:
                    domain_item = await conn.fetchrow("SELECT * FROM shop_items WHERE name = $1 AND category = 'domain'", d)
                    if domain_item:
                        compatible.append(d)
            if not compatible:
                await callback.answer("No domains compatible with your current character!", show_alert=True)
                return
            buttons = []
            for d in compatible[:5]:
                domain = await conn.fetchrow("SELECT * FROM techniques WHERE name = $1 AND category = 'domain'", d)
                if domain:
                    ce_cost = domain['ce_cost']
                    dmg_mult = domain['damage_multiplier']
                else:
                    domain_item = await conn.fetchrow("SELECT * FROM shop_items WHERE name = $1 AND category = 'domain'", d)
                    if domain_item:
                        ce_cost = int(parse_effect(domain_item['effect']).get('ce_cost', 100))
                        dmg_mult = float(parse_effect(domain_item['effect']).get('damage', 3.5))
                    else:
                        continue
                cp_cost = 3
                buttons.append([InlineKeyboardButton(
                    text=f"🌐 {d} ({cp_cost} CP, {ce_cost} CE, {dmg_mult}x)",
                    callback_data=f"pvp_adddomain|{battle_id}|{cp_cost}|{ce_cost}|{dmg_mult}|{d}"
                )])
            buttons.append([InlineKeyboardButton(text="🔙 Back", callback_data=f"pvp_back|{battle_id}")])
            markup = InlineKeyboardMarkup(inline_keyboard=buttons)
            await callback.message.edit_text("Select a domain:", reply_markup=markup)
            await callback.answer()
        elif action == "addtech":
            cp_cost = int(parts[2])
            ce_cost = int(parts[3])
            tech_name = parts[4]
            tech = await conn.fetchrow("SELECT * FROM techniques WHERE name = $1", tech_name)
            if tech and tech.get('character_name') is not None and tech['character_name'] != player.get('character_name'):
                await callback.answer("This technique is not compatible with your character!", show_alert=True)
                return
            cp = get_combo_points(player['level'])
            used_cp = sum(m.get('cp_cost', 0) for m in queue)
            if used_cp + cp_cost > cp:
                await callback.answer(f"Not enough Combo Points! (Used {used_cp}/{cp})", show_alert=True)
                return
            total_ce = sum(m.get('ce_cost', 0) for m in queue) + ce_cost
            if player['ce'] < total_ce:
                await callback.answer(f"Not enough CE! Need {total_ce}, have {player['ce']}", show_alert=True)
                return
            move = {"type": "technique", "cp_cost": cp_cost, "ce_cost": ce_cost, "tech_name": tech_name}
            queue.append(move)
            await callback.answer(f"Added {tech_name}!")
            await pvp_move_menu(callback.message, battle_id, user_id)
        elif action == "adddomain":
            cp_cost = int(parts[2])
            ce_cost = int(parts[3])
            dmg_mult = float(parts[4])
            domain_name = parts[5]
            domain = await conn.fetchrow("SELECT * FROM techniques WHERE name = $1 AND category = 'domain'", domain_name)
            if domain and domain.get('character_name') is not None and domain['character_name'] != player.get('character_name'):
                await callback.answer("This domain is not compatible with your character!", show_alert=True)
                return
            cp = get_combo_points(player['level'])
            used_cp = sum(m.get('cp_cost', 0) for m in queue)
            if used_cp + cp_cost > cp:
                await callback.answer(f"Not enough Combo Points! (Used {used_cp}/{cp})", show_alert=True)
                return
            total_ce = sum(m.get('ce_cost', 0) for m in queue) + ce_cost
            if player['ce'] < total_ce:
                await callback.answer(f"Not enough CE! Need {total_ce}, have {player['ce']}", show_alert=True)
                return
            move = {"type": "domain", "cp_cost": cp_cost, "ce_cost": ce_cost, "domain_name": domain_name, "dmg_mult": dmg_mult}
            queue.append(move)
            await callback.answer(f"Added {domain_name}!")
            await pvp_move_menu(callback.message, battle_id, user_id)
        elif action == "pass":
            queue.clear()
            await callback.answer("You passed.")
            await pvp_end_turn(callback.message, battle_id, user_id)
        elif action == "back":
            await pvp_move_menu(callback.message, battle_id, user_id)

async def pvp_move_menu(message, battle_id, user_id):
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⚔️ Attack (1 CP)", callback_data=f"pvp_add|{battle_id}|attack|1|0")],
        [InlineKeyboardButton(text="🛡️ Defend (1 CP)", callback_data=f"pvp_add|{battle_id}|defend|1|0")],
        [InlineKeyboardButton(text="💥 Special (2 CP)", callback_data=f"pvp_add|{battle_id}|special|2|30")],
        [InlineKeyboardButton(text="🌀 Technique", callback_data=f"pvp_tech|{battle_id}")],
        [InlineKeyboardButton(text="🌐 Domain", callback_data=f"pvp_domain|{battle_id}")],
        [InlineKeyboardButton(text="⏭️ Pass (0 CP)", callback_data=f"pvp_pass|{battle_id}")]
    ])
    await message.edit_text("Select your moves for this turn:", reply_markup=keyboard)

async def pvp_end_turn(message, battle_id, user_id):
    async with db_pool.acquire() as conn:
        queue = battle_queues[battle_id]['participants'][user_id]
        player = await conn.fetchrow("SELECT * FROM players WHERE user_id = $1", user_id)
        battle = await conn.fetchrow("SELECT * FROM battles WHERE id = $1", battle_id)
        other_id = battle['player1_id'] if user_id == battle['player2_id'] else battle['player2_id']
        other_player = await conn.fetchrow("SELECT * FROM players WHERE user_id = $1", other_id)
        total_damage = 0
        for move in queue:
            if move['type'] == 'attack':
                total_damage += max(1, int(player['atk'] * random.uniform(0.8, 1.2)))
            elif move['type'] == 'special':
                total_damage += max(1, int(player['atk'] * random.uniform(1.5, 2.5)))
            elif move['type'] == 'defend':
                pass  # handled separately
            elif move['type'] == 'technique':
                tech = await conn.fetchrow("SELECT * FROM techniques WHERE name = $1", move.get('tech_name'))
                if tech:
                    total_damage += max(1, int(player['atk'] * tech['damage_multiplier'] * random.uniform(0.9, 1.1)))
            elif move['type'] == 'domain':
                total_damage += max(1, int(player['atk'] * move.get('dmg_mult', 3.5) * random.uniform(0.9, 1.1)))
        if user_id == battle['player1_id']:
            new_hp = max(0, battle['current_hp2'] - total_damage)
            await conn.execute("UPDATE battles SET current_hp2 = $1 WHERE id = $2", new_hp, battle_id)
        else:
            new_hp = max(0, battle['current_hp1'] - total_damage)
            await conn.execute("UPDATE battles SET current_hp1 = $1 WHERE id = $2", new_hp, battle_id)
        battle_queues[battle_id]['current_hp'] = new_hp
        # Switch turn
        battle_queues[battle_id]['turn_player'] = other_id
        await bot.send_message(other_id, f"⚔️ **Your turn!** Use `/pvp_move {battle_id}` to select moves.")
        await message.edit_text("Turn ended. Waiting for opponent.")

# ------------------------------------------------------------
# MISSIONS & DAILY
# ------------------------------------------------------------
@dp.message(Command("missions"))
async def missions_cmd(message: types.Message):
    user_id = message.from_user.id
    try:
        async with db_pool.acquire() as conn:
            player = await conn.fetchrow("SELECT * FROM players WHERE user_id = $1", user_id)
            if not player:
                await message.reply("Start with /start first!")
                return
            missions = await conn.fetch("SELECT * FROM missions ORDER BY type, id")
            if not missions:
                await message.reply("No missions available.")
                return
            player_missions = await conn.fetch("SELECT * FROM player_missions WHERE player_id = $1", user_id)
            resp = "📋 **Your Missions**\n━━━━━━━━━━━━━━━━━━━\n"
            current_type = None
            for m in missions:
                if m['type'] != current_type:
                    current_type = m['type']
                    resp += f"\n📌 **{current_type.upper()}**\n"
                pm = next((p for p in player_missions if p['mission_id'] == m['id']), None)
                if pm and pm['completed']:
                    status = "✅ Completed"
                elif pm:
                    progress = pm['progress']
                    req = m['requirement']
                    req_parts = req.split(':')
                    if len(req_parts) == 2:
                        target = int(req_parts[1])
                        status = f"Progress: {progress}/{target}"
                    else:
                        status = "In Progress"
                else:
                    req_parts = m['requirement'].split(':')
                    if len(req_parts) == 2:
                        status = f"0/{req_parts[1]}"
                    else:
                        status = "Not started"
                resp += f"  • **{m['name']}** - {m['description']}\n"
                resp += f"    Reward: ¥{m['reward_yen']:,} | ⭐ +{m['reward_xp']} XP\n"
                resp += f"    Status: {status}\n"
            resp += "\n━━━━━━━━━━━━━━━━━━━\n"
            resp += "Use /daily to claim daily rewards."
            await message.reply(resp)
    except Exception as e:
        await message.reply(f"Error: {e}")

@dp.message(Command("daily"))
async def daily_cmd(message: types.Message):
    user_id = message.from_user.id
    try:
        async with db_pool.acquire() as conn:
            player = await conn.fetchrow("SELECT * FROM players WHERE user_id = $1", user_id)
            if not player:
                await message.reply("Start with /start first!")
                return
            daily_missions = await conn.fetch("SELECT * FROM missions WHERE type = 'daily'")
            for m in daily_missions:
                pm = await conn.fetchrow("SELECT * FROM player_missions WHERE player_id = $1 AND mission_id = $2", user_id, m['id'])
                if pm and pm['completed']:
                    continue
                if not pm:
                    await conn.execute("""
                        INSERT INTO player_missions (player_id, mission_id, progress, completed, last_claimed)
                        VALUES ($1, $2, $3, TRUE, NOW())
                    """, user_id, m['id'], 0)
                else:
                    await conn.execute("UPDATE player_missions SET completed = TRUE, progress = 0 WHERE player_id = $1 AND mission_id = $2",
                                       user_id, m['id'])
                await conn.execute("UPDATE players SET yen = LEAST(yen + $1, $2), xp = xp + $3 WHERE user_id = $4",
                                   m['reward_yen'], MAX_YEN, m['reward_xp'], user_id)
            await update_player_stats(user_id)
            await message.reply("✅ Daily missions claimed! Check your Yen and XP.")
    except Exception as e:
        await message.reply(f"Error: {e}")

# ------------------------------------------------------------
# ADMIN COMMANDS
# ------------------------------------------------------------
@dp.message(Command("addadmin"))
async def add_admin_cmd(message: types.Message):
    if not await is_owner(message.from_user.id):
        await message.reply("❌ Only the owner can add admins!")
        return
    args = message.text.split()
    if len(args) < 2:
        await message.reply("Usage: /addadmin @user")
        return
    target = args[1].replace("@", "")
    try:
        async with db_pool.acquire() as conn:
            user = await conn.fetchrow("SELECT user_id FROM players WHERE username ILIKE $1", target)
            if not user:
                await message.reply(f"User '{target}' not found.")
                return
            await conn.execute("INSERT INTO admins (user_id, role) VALUES ($1, 'admin') ON CONFLICT DO NOTHING", user['user_id'])
            await message.reply(f"✅ Added {target} as an admin.")
    except Exception as e:
        await message.reply(f"Error: {e}")

@dp.message(Command("removeadmin"))
async def remove_admin_cmd(message: types.Message):
    if not await is_owner(message.from_user.id):
        await message.reply("❌ Only the owner can remove admins!")
        return
    args = message.text.split()
    if len(args) < 2:
        await message.reply("Usage: /removeadmin @user")
        return
    target = args[1].replace("@", "")
    try:
        async with db_pool.acquire() as conn:
            user = await conn.fetchrow("SELECT user_id FROM players WHERE username ILIKE $1", target)
            if not user:
                await message.reply(f"User '{target}' not found.")
                return
            await conn.execute("DELETE FROM admins WHERE user_id = $1", user['user_id'])
            await message.reply(f"✅ Removed {target} from admins.")
    except Exception as e:
        await message.reply(f"Error: {e}")

# ------------------------------------------------------------
# CLAN COMMANDS
# ------------------------------------------------------------
@dp.message(Command("clan"))
async def clan_cmd(message: types.Message):
    args = message.text.split()
    if len(args) < 2:
        await message.reply("Usage:\n/clan create [name]\n/clan join [name]\n/clan info\n/clan leave\n/clan upgrade\n/clan war [clan]")
        return
    action = args[1].lower()
    user_id = message.from_user.id
    async with db_pool.acquire() as conn:
        if action == "create":
            if len(args) < 3:
                await message.reply("Usage: /clan create [clan name]")
                return
            name = " ".join(args[2:])
            existing = await conn.fetchrow("SELECT * FROM clans WHERE name ILIKE $1", name)
            if existing:
                await message.reply(f"Clan '{name}' already exists.")
                return
            await conn.execute("INSERT INTO clans (name, leader_id, member_count) VALUES ($1, $2, 1)", name, user_id)
            await conn.execute("UPDATE players SET clan_id = (SELECT id FROM clans WHERE name = $1), clan_rank = 'Leader' WHERE user_id = $2", name, user_id)
            await message.reply(f"✅ Clan '{name}' created! You are the leader.")
        elif action == "join":
            if len(args) < 3:
                await message.reply("Usage: /clan join [clan name]")
                return
            name = " ".join(args[2:])
            clan = await conn.fetchrow("SELECT * FROM clans WHERE name ILIKE $1", name)
            if not clan:
                await message.reply(f"Clan '{name}' not found.")
                return
            await conn.execute("UPDATE players SET clan_id = $1, clan_rank = 'Member' WHERE user_id = $2", clan['id'], user_id)
            await conn.execute("UPDATE clans SET member_count = member_count + 1 WHERE id = $1", clan['id'])
            await message.reply(f"✅ Joined clan '{name}'!")
        elif action == "info":
            player = await conn.fetchrow("SELECT clan_id FROM players WHERE user_id = $1", user_id)
            if not player or not player['clan_id']:
                await message.reply("You are not in a clan.")
                return
            clan = await conn.fetchrow("SELECT * FROM clans WHERE id = $1", player['clan_id'])
            members = await conn.fetch("SELECT username, clan_rank FROM players WHERE clan_id = $1", clan['id'])
            member_list = "\n".join([f"• {m['username']} ({m['clan_rank']})" for m in members])
            await message.reply(
                f"🏛️ **Clan: {clan['name']}**\n"
                f"Leader: {clan['leader_id']}\n"
                f"Members: {clan['member_count']}\n"
                f"Level: {clan['level']}\n"
                f"━━━━━━━━━━━━━━━━━━━\n"
                f"{member_list}"
            )
        elif action == "leave":
            player = await conn.fetchrow("SELECT clan_id, clan_rank FROM players WHERE user_id = $1", user_id)
            if not player or not player['clan_id']:
                await message.reply("You are not in a clan.")
                return
            if player['clan_rank'] == 'Leader':
                await message.reply("You cannot leave as leader. Transfer leadership first or disband.")
                return
            await conn.execute("UPDATE clans SET member_count = member_count - 1 WHERE id = $1", player['clan_id'])
            await conn.execute("UPDATE players SET clan_id = NULL, clan_rank = 'Member' WHERE user_id = $1", user_id)
            await message.reply("✅ You left the clan.")
        elif action == "upgrade":
            player = await conn.fetchrow("SELECT clan_id, clan_rank FROM players WHERE user_id = $1", user_id)
            if not player or not player['clan_id']:
                await message.reply("You're not in a clan.")
                return
            if player['clan_rank'] != 'Leader':
                await message.reply("Only the leader can upgrade.")
                return
            clan = await conn.fetchrow("SELECT * FROM clans WHERE id = $1", player['clan_id'])
            current_level = clan['level']
            cost = 1000 * (current_level + 1)
            if clan['xp'] < cost:
                await message.reply(f"Not enough clan XP. Need {cost}, have {clan['xp']}.")
                return
            await conn.execute("UPDATE clans SET level = level + 1, xp = xp - $1 WHERE id = $2", cost, player['clan_id'])
            await message.reply(f"✅ Clan upgraded to level {current_level+1}!")
        elif action == "war":
            if len(args) < 3:
                await message.reply("Usage: /clan war [clan name]")
                return
            target_clan_name = " ".join(args[2:])
            player = await conn.fetchrow("SELECT clan_id, clan_rank FROM players WHERE user_id = $1", user_id)
            if not player or player['clan_rank'] != 'Leader':
                await message.reply("Only clan leaders can declare war.")
                return
            target_clan = await conn.fetchrow("SELECT id, name FROM clans WHERE name ILIKE $1", target_clan_name)
            if not target_clan:
                await message.reply("Clan not found.")
                return
            if target_clan['id'] == player['clan_id']:
                await message.reply("You can't war with your own clan.")
                return
            existing = await conn.fetchrow("SELECT * FROM clan_wars WHERE (clan1_id = $1 OR clan2_id = $1) AND status = 'active'", player['clan_id'])
            if existing:
                await message.reply("Your clan is already in a war.")
                return
            war_id = await conn.fetchval("""
                INSERT INTO clan_wars (clan1_id, clan2_id, start_time, end_time)
                VALUES ($1, $2, NOW(), NOW() + INTERVAL '24 hours')
                RETURNING id
            """, player['clan_id'], target_clan['id'])
            await message.reply(f"⚔️ **CLAN WAR DECLARED!**\nYour clan vs {target_clan['name']}\nWar ends in 24 hours.")
        else:
            await message.reply("Unknown action. Use create, join, info, leave, upgrade, or war.")

# ------------------------------------------------------------
# AWAKENING
# ------------------------------------------------------------
@dp.message(Command("awakening"))
async def awakening_cmd(message: types.Message):
    user_id = message.from_user.id
    async with db_pool.acquire() as conn:
        player = await conn.fetchrow("SELECT awakening, awakening_level, awakening_aura FROM players WHERE user_id = $1", user_id)
        if not player:
            await message.reply("Start with /start first!")
            return
        if player['awakening']:
            await message.reply(
                f"🌀 **Awakening: {player['awakening']}**\n"
                f"Level: {player['awakening_level']}\n"
                f"Aura: {'✅ Active' if player['awakening_aura'] else '❌ Inactive'}\n"
                f"━━━━━━━━━━━━━━━━━━━\n"
                f"Keep fighting to evolve your awakening!"
            )
        else:
            await message.reply(
                "🌀 **No Awakening Yet**\n"
                "Awakenings can be triggered by:\n"
                "• Defeating a boss (10% chance)\n"
                "• Dropping below 10% HP in battle (5% chance)\n"
                "• Random luck (1% chance)"
            )

# ------------------------------------------------------------
# NPC
# ------------------------------------------------------------
@dp.message(Command("npc"))
async def npc_cmd(message: types.Message):
    args = message.text.split()
    if len(args) < 2:
        await message.reply("Usage:\n/npc list\n/npc talk [name]")
        return
    action = args[1].lower()
    async with db_pool.acquire() as conn:
        if action == "list":
            npcs = await conn.fetch("SELECT * FROM npcs")
            if not npcs:
                await message.reply("No NPCs available.")
                return
            resp = "🧙 **Available NPCs**\n━━━━━━━━━━━━━━━━━━━\n"
            for n in npcs:
                resp += f"• **{n['name']}** – {n['role']}\n"
            resp += "\nUse `/npc talk [name]` to interact."
            await message.reply(resp)
        elif action == "talk":
            if len(args) < 3:
                await message.reply("Usage: /npc talk [name]")
                return
            name = " ".join(args[2:])
            npc = await conn.fetchrow("SELECT * FROM npcs WHERE name ILIKE $1", name)
            if not npc:
                await message.reply(f"NPC '{name}' not found.")
                return
            responses = {
                "Gojo Satoru": "Hey there, weakling. Want to train? It'll cost you 50 CE.",
                "Nanami Kento": "I have some overtime quests if you're interested.",
                "Mei Mei": "Everything has a price, darling. Even my advice.",
                "Utahime Iori": "I can perform a ritual to heal you. Focus.",
                "Shoko Ieiri": "Medic here. I can patch you up. At a price.",
                "Tengen": "The barriers of this world are thin. Seek the truth.",
            }
            reply = responses.get(npc['name'], f"{npc['name']}: {npc['description']}")
            await message.reply(f"🧙 **{npc['name']}** says:\n{reply}")

# ------------------------------------------------------------
# DUNGEON
# ------------------------------------------------------------
@dp.message(Command("dungeon"))
async def dungeon_cmd(message: types.Message):
    user_id = message.from_user.id
    if user_id in ongoing_battles:
        await message.reply("⚠️ You already have an ongoing battle! Use `/status` or `/resume`.")
        return
    async with db_pool.acquire() as conn:
        player = await conn.fetchrow("SELECT * FROM players WHERE user_id = $1", user_id)
        if not player:
            await message.reply("Start with /start first!")
            return
        run = await conn.fetchrow("SELECT * FROM dungeon_runs WHERE player_id = $1 AND status = 'active'", user_id)
        if not run:
            run_id = await conn.fetchval("""
                INSERT INTO dungeon_runs (player_id, floor, status) 
                VALUES ($1, 1, 'active') RETURNING id
            """, user_id)
            floor = 1
        else:
            run_id = run['id']
            floor = run['floor']
        enemy_base = await conn.fetchrow("SELECT * FROM enemies WHERE is_boss = FALSE ORDER BY RANDOM() LIMIT 1")
        if not enemy_base:
            await message.reply("No enemies available.")
            return
        enemy = scale_enemy_to_player(player, enemy_base)
        enemy['hp'] = int(enemy['hp'] * (1 + floor * 0.2))
        enemy['atk'] = int(enemy['atk'] * (1 + floor * 0.15))
        enemy['def'] = int(enemy['def'] * (1 + floor * 0.1))
        enemy['reward_yen'] = int(enemy['reward_yen'] * (1 + floor * 0.1))
        enemy['reward_xp'] = int(enemy['reward_xp'] * (1 + floor * 0.1))
        enemy['rank'] = f"Dungeon Floor {floor}"
        await message.reply_animation(animation=EFFECTS["dungeon_clear"])
        await message.reply(
            f"🏰 **Dungeon – Floor {floor}**\n"
            f"Enemy: {enemy['name']}\n"
            f"HP: {enemy['hp']} | ATK: {enemy['atk']} | DEF: {enemy['def']}\n"
            f"Reward: ¥{enemy['reward_yen']} + {enemy['reward_xp']} XP\n"
            f"Defeat it to advance to the next floor!"
        )
        battle_id = await conn.fetchval("""
            INSERT INTO battles (chat_id, player1_id, current_hp1, current_hp2, 
                                 enemy_name, enemy_rank, enemy_atk, enemy_def, enemy_spd,
                                 is_boss, enemy_reward_yen, enemy_reward_xp, enemy_max_hp,
                                 vow_effects, is_dungeon, dungeon_run_id)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, FALSE, $10, $11, $12, $13, TRUE, $14)
            RETURNING id
        """, message.chat.id, user_id, player['hp'], enemy['hp'], 
           enemy['name'], enemy['rank'], enemy['atk'], enemy['def'], enemy['spd'],
           enemy['reward_yen'], enemy['reward_xp'], enemy['hp'],
           json.dumps([]), run_id)
        ongoing_battles[user_id] = battle_id
        battle_queues[battle_id] = {"participants": {user_id: []}, "current_hp": enemy['hp'], "log": []}
        await show_battle_turn(message, battle_id, player, enemy, [])

# ------------------------------------------------------------
# TOWER
# ------------------------------------------------------------
@dp.message(Command("tower"))
async def tower_cmd(message: types.Message):
    user_id = message.from_user.id
    if user_id in ongoing_battles:
        await message.reply("⚠️ You already have an ongoing battle! Use `/status` or `/resume`.")
        return
    async with db_pool.acquire() as conn:
        player = await conn.fetchrow("SELECT * FROM players WHERE user_id = $1", user_id)
        if not player:
            await message.reply("Start with /start first!")
            return
        run = await conn.fetchrow("SELECT * FROM tower_runs WHERE player_id = $1 AND status = 'active'", user_id)
        if not run:
            run_id = await conn.fetchval("""
                INSERT INTO tower_runs (player_id, floor, status) 
                VALUES ($1, 1, 'active') RETURNING id
            """, user_id)
            floor = 1
        else:
            run_id = run['id']
            floor = run['floor']
        if floor > 100:
            await message.reply("🏆 **Tower Complete!** You have cleared all 100 floors.")
            await conn.execute("UPDATE tower_runs SET status = 'completed' WHERE id = $1", run_id)
            return
        is_boss = (floor % 10 == 0)
        enemy_base = await conn.fetchrow("SELECT * FROM enemies WHERE is_boss = $1 ORDER BY RANDOM() LIMIT 1", is_boss)
        if not enemy_base:
            await message.reply("No enemies available.")
            return
        enemy = scale_enemy_to_player(player, enemy_base)
        enemy['hp'] = int(enemy['hp'] * (1 + floor * 0.1))
        enemy['atk'] = int(enemy['atk'] * (1 + floor * 0.08))
        enemy['def'] = int(enemy['def'] * (1 + floor * 0.05))
        enemy['reward_yen'] = int(enemy['reward_yen'] * (1 + floor * 0.05))
        enemy['reward_xp'] = int(enemy['reward_xp'] * (1 + floor * 0.05))
        enemy['rank'] = f"Tower Floor {floor}"
        await message.reply_animation(animation=EFFECTS["tower_clear"])
        await message.reply(
            f"🗼 **Tower – Floor {floor}/100**\n"
            f"Enemy: {enemy['name']} {'(BOSS)' if is_boss else ''}\n"
            f"HP: {enemy['hp']} | ATK: {enemy['atk']} | DEF: {enemy['def']}\n"
            f"Reward: ¥{enemy['reward_yen']} + {enemy['reward_xp']} XP\n"
            f"Defeat it to climb higher!"
        )
        battle_id = await conn.fetchval("""
            INSERT INTO battles (chat_id, player1_id, current_hp1, current_hp2, 
                                 enemy_name, enemy_rank, enemy_atk, enemy_def, enemy_spd,
                                 is_boss, enemy_reward_yen, enemy_reward_xp, enemy_max_hp,
                                 vow_effects, is_tower, tower_run_id, tower_floor)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, TRUE, $14, $15)
            RETURNING id
        """, message.chat.id, user_id, player['hp'], enemy['hp'], 
           enemy['name'], enemy['rank'], enemy['atk'], enemy['def'], enemy['spd'],
           is_boss, enemy['reward_yen'], enemy['reward_xp'], enemy['hp'],
           json.dumps([]), run_id, floor)
        ongoing_battles[user_id] = battle_id
        battle_queues[battle_id] = {"participants": {user_id: []}, "current_hp": enemy['hp'], "log": []}
        await show_battle_turn(message, battle_id, player, enemy, [])

# ------------------------------------------------------------
# ACHIEVEMENTS
# ------------------------------------------------------------
@dp.message(Command("achievements"))
async def achievements_cmd(message: types.Message):
    user_id = message.from_user.id
    async with db_pool.acquire() as conn:
        achievements = await conn.fetch("SELECT * FROM achievements")
        if not achievements:
            await message.reply("No achievements available.")
            return
        player_achievements = await conn.fetch("SELECT achievement_id FROM player_achievements WHERE player_id = $1", user_id)
        unlocked = [pa['achievement_id'] for pa in player_achievements]
        resp = "🏆 **Achievements**\n━━━━━━━━━━━━━━━━━━━\n"
        for a in achievements:
            status = "✅" if a['id'] in unlocked else "🔒"
            resp += f"{status} **{a['name']}** – {a['description']}\n"
        await message.reply(resp)

# ------------------------------------------------------------
# BUY YEN
# ------------------------------------------------------------
async def send_owner_info(message: types.Message):
    await message.reply(
        f"👑 **Owner & Developer**\n"
        f"━━━━━━━━━━━━━━━━━━━\n"
        f"Name: {OWNER_NAME}\n"
        f"ID: {OWNER_ID}\n"
        f"━━━━━━━━━━━━━━━━━━━\n"
        f"{YEN_PURCHASE_INFO}"
    )

@dp.message(Command("buyyen"))
async def buyyen_cmd(message: types.Message):
    await send_owner_info(message)

# ------------------------------------------------------------
# COMMANDS LIST
# ------------------------------------------------------------
@dp.message(Command("commands"))
async def commands_cmd(message: types.Message):
    await message.reply(
        f"📋 **Cursed Chronicles — Command List**\n"
        f"━━━━━━━━━━━━━━━━━━━\n"
        f"**General**\n"
        f"/start, /profile, /guide, /status, /resume [id], /commands, /buyyen, /stats\n"
        f"━━━━━━━━━━━━━━━━━━━\n"
        f"**Characters**\n"
        f"/characters, /select [name]\n"
        f"━━━━━━━━━━━━━━━━━━━\n"
        f"**Battle**\n"
        f"/battle, /boss [name], /enemies, /pvp_challenge [user], /pvp_accept [id], /pvp_move [id], /raid\n"
        f"━━━━━━━━━━━━━━━━━━━\n"
        f"**Shop & Inventory**\n"
        f"/shop, /buy [item], /bag, /use [item], /equip [weapon], /techniques, /learn [tech]\n"
        f"━━━━━━━━━━━━━━━━━━━\n"
        f"**Clans**\n"
        f"/clan create [name], /clan join [name], /clan info, /clan leave, /clan upgrade, /clan war [clan]\n"
        f"━━━━━━━━━━━━━━━━━━━\n"
        f"**Advanced**\n"
        f"/awakening, /npc list, /npc talk [name], /shikigami, /restriction, /vow\n"
        f"/story, /story_chapter [num], /dungeon, /tower, /achievements\n"
        f"━━━━━━━━━━━━━━━━━━━\n"
        f"**Quests & Events**\n"
        f"/quests, /quest_accept [id], /quest_reward [id], /event, /event_battle [id]\n"
        f"━━━━━━━━━━━━━━━━━━━\n"
        f"**Crafting**\n"
        f"/materials, /craft list, /craft [recipe]\n"
        f"━━━━━━━━━━━━━━━━━━━\n"
        f"**Leaderboard**\n"
        f"/leaderboard [category] – level, wins, boss_kills, prestige, yen\n"
        f"━━━━━━━━━━━━━━━━━━━\n"
        f"**Admin** (owner only)\n"
        f"/addadmin [user], /removeadmin [user], /broadcast [message]\n"
        f"━━━━━━━━━━━━━━━━━━━\n"
        f"**Owner** (full access)\n"
        f"/addyen, /removeyen, /addyenall, /removeyenall, /addxp, /removexp, /setrank, /addlevel, /removelevel, /recalc, /diagnosis, /clearbattles"
    )

# ------------------------------------------------------------
# OWNER / ADMIN COMMANDS (yen, xp, level, rank)
# ------------------------------------------------------------
@dp.message(Command("addyen"))
async def addyen_cmd(message: types.Message):
    if not await can_manage_yen(message.from_user.id):
        await message.reply("❌ Only the owner can manage Yen!")
        return
    args = message.text.split()
    if len(args) < 3:
        await message.reply("Usage: /addyen @user amount")
        return
    target = args[1].replace("@", "")
    amount = int(args[2])
    if amount <= 0 or amount > MAX_YEN:
        await message.reply(f"❌ Amount must be between 1 and {MAX_YEN}.")
        return
    try:
        async with db_pool.acquire() as conn:
            res = await conn.execute("UPDATE players SET yen = LEAST(yen + $1, $2) WHERE username ILIKE $3",
                                     amount, MAX_YEN, target)
            if res == "UPDATE 0":
                await message.reply(f"User '{target}' not found.")
            else:
                await message.reply(f"✅ Added ¥{amount:,} to {target}.")
    except Exception as e:
        await message.reply(f"Error: {e}")

@dp.message(Command("removeyen"))
async def removeyen_cmd(message: types.Message):
    if not await can_manage_yen(message.from_user.id):
        await message.reply("❌ Only the owner can manage Yen!")
        return
    args = message.text.split()
    if len(args) < 3:
        await message.reply("Usage: /removeyen @user amount")
        return
    target = args[1].replace("@", "")
    amount = int(args[2])
    if amount <= 0:
        await message.reply("❌ Amount must be positive.")
        return
    try:
        async with db_pool.acquire() as conn:
            res = await conn.execute("UPDATE players SET yen = yen - $1 WHERE username ILIKE $2 AND yen >= $1",
                                     amount, target)
            if res == "UPDATE 0":
                await message.reply(f"User not found or insufficient yen.")
            else:
                await message.reply(f"✅ Removed ¥{amount:,} from {target}.")
    except Exception as e:
        await message.reply(f"Error: {e}")

@dp.message(Command("addxp"))
async def addxp_cmd(message: types.Message):
    if not await is_owner(message.from_user.id) and not await is_admin(message.from_user.id):
        await message.reply("❌ Admin or Owner only!")
        return
    args = message.text.split()
    if len(args) < 3:
        await message.reply("Usage: /addxp @user amount")
        return
    target = args[1].replace("@", "")
    amount = int(args[2])
    if amount <= 0:
        await message.reply("❌ Amount must be positive.")
        return
    try:
        async with db_pool.acquire() as conn:
            player = await conn.fetchrow("SELECT * FROM players WHERE username ILIKE $1", target)
            if not player:
                await message.reply(f"User '{target}' not found.")
                return
            new_xp = player['xp'] + amount
            await conn.execute("UPDATE players SET xp = $1 WHERE username ILIKE $2", new_xp, target)
            await update_player_stats(player['user_id'])
            await message.reply(f"✅ Added {amount} XP to {target}.")
    except Exception as e:
        await message.reply(f"Error: {e}")

@dp.message(Command("removexp"))
async def removexp_cmd(message: types.Message):
    if not await is_owner(message.from_user.id) and not await is_admin(message.from_user.id):
        await message.reply("❌ Admin or Owner only!")
        return
    args = message.text.split()
    if len(args) < 3:
        await message.reply("Usage: /removexp @user amount")
        return
    target = args[1].replace("@", "")
    amount = int(args[2])
    if amount <= 0:
        await message.reply("❌ Amount must be positive.")
        return
    try:
        async with db_pool.acquire() as conn:
            player = await conn.fetchrow("SELECT * FROM players WHERE username ILIKE $1", target)
            if not player:
                await message.reply(f"User '{target}' not found.")
                return
            new_xp = max(0, player['xp'] - amount)
            await conn.execute("UPDATE players SET xp = $1 WHERE username ILIKE $2", new_xp, target)
            await update_player_stats(player['user_id'])
            await message.reply(f"✅ Removed {amount} XP from {target}.")
    except Exception as e:
        await message.reply(f"Error: {e}")

@dp.message(Command("setrank"))
async def setrank_cmd(message: types.Message):
    if not await is_owner(message.from_user.id) and not await is_admin(message.from_user.id):
        await message.reply("❌ Admin or Owner only!")
        return
    args = message.text.split(maxsplit=2)
    if len(args) < 3:
        await message.reply("Usage: /setrank @user rank")
        return
    target = args[1].replace("@", "")
    rank = args[2]
    try:
        async with db_pool.acquire() as conn:
            res = await conn.execute("UPDATE players SET rank = $1 WHERE username ILIKE $2", rank, target)
            if res == "UPDATE 0":
                await message.reply(f"User '{target}' not found.")
            else:
                await message.reply(f"✅ Set {target}'s rank to {rank}.")
    except Exception as e:
        await message.reply(f"Error: {e}")

@dp.message(Command("addlevel"))
async def addlevel_cmd(message: types.Message):
    if not await is_owner(message.from_user.id) and not await is_admin(message.from_user.id):
        await message.reply("❌ Admin or Owner only!")
        return
    args = message.text.split()
    if len(args) < 3:
        await message.reply("Usage: /addlevel @user amount")
        return
    target = args[1].replace("@", "")
    amount = int(args[2])
    if amount <= 0:
        await message.reply("❌ Amount must be positive.")
        return
    try:
        async with db_pool.acquire() as conn:
            player = await conn.fetchrow("SELECT * FROM players WHERE username ILIKE $1", target)
            if not player:
                await message.reply(f"User '{target}' not found.")
                return
            new_level = player['level'] + amount
            await conn.execute("UPDATE players SET level = $1 WHERE username ILIKE $2", new_level, target)
            await update_player_stats(player['user_id'])
            await message.reply(f"✅ Added {amount} levels to {target}.")
    except Exception as e:
        await message.reply(f"Error: {e}")

@dp.message(Command("removelevel"))
async def removelevel_cmd(message: types.Message):
    if not await is_owner(message.from_user.id) and not await is_admin(message.from_user.id):
        await message.reply("❌ Admin or Owner only!")
        return
    args = message.text.split()
    if len(args) < 3:
        await message.reply("Usage: /removelevel @user amount")
        return
    target = args[1].replace("@", "")
    amount = int(args[2])
    if amount <= 0:
        await message.reply("❌ Amount must be positive.")
        return
    try:
        async with db_pool.acquire() as conn:
            player = await conn.fetchrow("SELECT * FROM players WHERE username ILIKE $1", target)
            if not player:
                await message.reply(f"User '{target}' not found.")
                return
            new_level = max(1, player['level'] - amount)
            await conn.execute("UPDATE players SET level = $1 WHERE username ILIKE $2", new_level, target)
            await update_player_stats(player['user_id'])
            await message.reply(f"✅ Removed {amount} levels from {target}.")
    except Exception as e:
        await message.reply(f"Error: {e}")

@dp.message(Command("recalc"))
async def recalc_cmd(message: types.Message):
    if not await is_owner(message.from_user.id) and not await is_admin(message.from_user.id):
        await message.reply("❌ Admin or Owner only!")
        return
    args = message.text.split()
    try:
        async with db_pool.acquire() as conn:
            if len(args) > 1:
                target = args[1].replace("@", "")
                player = await conn.fetchrow("SELECT * FROM players WHERE username ILIKE $1", target)
                if not player:
                    await message.reply(f"User '{target}' not found.")
                    return
                await update_player_stats(player['user_id'])
                await message.reply(f"✅ Recalculated {target}.")
            else:
                players = await conn.fetch("SELECT user_id FROM players")
                for p in players:
                    await update_player_stats(p['user_id'])
                await message.reply(f"✅ Recalculated all {len(players)} players.")
    except Exception as e:
        await message.reply(f"Error: {e}")

# ------------------------------------------------------------
# COMMAND: /diagnosis – Full system check (owner only)
# ------------------------------------------------------------
@dp.message(Command("diagnosis"))
async def diagnosis_cmd(message: types.Message):
    if not await is_owner(message.from_user.id):
        await message.reply("❌ Owner only.")
        return

    report = []
    report.append("🔍 **CURSED CHRONICLES – SYSTEM DIAGNOSIS**")
    report.append(f"🕒 Timestamp: `{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}`")
    report.append("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")

    # 1. Environment
    report.append("\n🌐 **ENVIRONMENT**")
    env_vars = ["BOT_TOKEN", "DATABASE_URL"]
    for var in env_vars:
        value = "✅ Set" if os.getenv(var) else "❌ Missing"
        report.append(f"• {var}: {value}")

    # 2. Database
    report.append("\n🗄️ **DATABASE**")
    try:
        async with db_pool.acquire() as conn:
            await conn.fetchval("SELECT 1")
            report.append("• Connection: ✅ OK")
            tables = [
                "players", "characters", "shop_items", "techniques", "enemies",
                "battles", "clans", "player_characters", "player_missions",
                "player_story", "dungeon_runs", "tower_runs", "player_achievements",
                "player_vows", "player_shikigami", "admins", "binding_vows",
                "npcs", "missions", "achievements", "story_chapters",
                "events", "clan_wars", "quests", "player_quests",
                "materials", "player_materials", "recipes"
            ]
            for table in tables:
                try:
                    count = await conn.fetchval(f"SELECT COUNT(*) FROM {table}")
                    report.append(f"• Table `{table}`: ✅ {count} rows")
                except Exception as e:
                    report.append(f"• Table `{table}`: ❌ Error – {str(e)[:50]}")
            total_players = await conn.fetchval("SELECT COUNT(*) FROM players")
            report.append(f"• Total players: {total_players}")
            active_battles_db = await conn.fetchval("SELECT COUNT(*) FROM battles WHERE status = 'active'")
            report.append(f"• Active battles (DB): {active_battles_db}")
    except Exception as e:
        report.append(f"❌ Database error: {e}")

    # 3. Global state
    report.append("\n🧠 **GLOBAL STATE (IN‑MEMORY)**")
    report.append(f"• `ongoing_battles`: {len(ongoing_battles)} entries")
    report.append(f"• `battle_queues`: {len(battle_queues)} entries")
    report.append(f"• `pvp_matches`: {len(pvp_matches)} entries")

    orphaned = []
    for user_id, b_id in ongoing_battles.items():
        if b_id not in battle_queues:
            orphaned.append(str(user_id))
    if orphaned:
        report.append(f"⚠️ Orphaned battles: {', '.join(orphaned)}")
    else:
        report.append("✅ No orphaned battles.")

    stale = []
    for b_id in battle_queues:
        if b_id not in ongoing_battles.values():
            stale.append(str(b_id))
    if stale:
        report.append(f"⚠️ Stale queues: {', '.join(stale)}")
    else:
        report.append("✅ No stale queues.")

    # 4. Battle queues snapshot
    report.append("\n📊 **BATTLE QUEUES SNAPSHOT**")
    if battle_queues:
        for idx, (b_id, data) in enumerate(list(battle_queues.items())[:5]):
            participants = list(data.get('participants', {}).keys())
            hp = data.get('current_hp', 'N/A')
            log_len = len(data.get('log', []))
            report.append(f"• Battle {b_id}: HP={hp}, Participants={len(participants)}, Log={log_len} lines")
        if len(battle_queues) > 5:
            report.append(f"  ... and {len(battle_queues)-5} more.")
    else:
        report.append("• No active battles.")

    # 5. PvP
    report.append("\n⚔️ **PVP MATCHES**")
    if pvp_matches:
        for b_id, meta in pvp_matches.items():
            report.append(f"• Battle {b_id}: Challenger={meta['challenger']}, Target={meta['target']}, Turn={meta.get('turn', 1)}")
    else:
        report.append("• No PvP matches.")

    # 6. Commands
    report.append("\n📋 **COMMANDS REGISTERED**")
    cmd_list = [
        "start", "guide", "stats", "addyenall", "removeyenall",
        "restriction", "vow", "shikigami", "profile", "characters",
        "select", "shop", "buy", "bag", "use", "equip", "learn",
        "techniques", "enemies", "story", "story_chapter", "boss",
        "battle", "status", "resume", "prestige", "pvp_challenge",
        "pvp_accept", "pvp_move", "missions", "daily", "clan",
        "awakening", "npc", "dungeon", "tower", "achievements",
        "buyyen", "commands", "addadmin", "removeadmin", "addyen",
        "removeyen", "addxp", "removexp", "setrank", "addlevel",
        "removelevel", "recalc", "diagnosis", "clearbattles",
        "event", "event_battle", "quests", "quest_accept", "quest_reward",
        "materials", "craft", "leaderboard", "broadcast"
    ]
    report.append(f"• Total commands: {len(cmd_list)}")
    report.append(f"• List: `{', '.join(cmd_list)}`")

    # 7. Recommendations
    report.append("\n🛠️ **RECOMMENDATIONS**")
    issues = []
    if orphaned or stale:
        issues.append("• Clear orphaned/stale battles using `/clearbattles`.")
    if not battle_queues and active_battles_db > 0:
        issues.append("• Database shows active battles but none in memory – restart may fix.")
    if not issues:
        issues.append("✅ All systems nominal.")
    report.extend(issues)

    final_report = "\n".join(report)
    if len(final_report) > 4000:
        f = StringIO(final_report)
        await message.reply_document(
            BufferedInputFile(f.getvalue().encode(), filename="diagnosis.txt"),
            caption="📄 Full diagnosis report (too long for inline)."
        )
    else:
        await message.reply(final_report, parse_mode="Markdown")

# ------------------------------------------------------------
# COMMAND: /clearbattles – clean orphaned/stale (owner only)
# ------------------------------------------------------------
@dp.message(Command("clearbattles"))
async def clearbattles_cmd(message: types.Message):
    if not await is_owner(message.from_user.id):
        await message.reply("❌ Owner only.")
        return
    ongoing_battles.clear()
    battle_queues.clear()
    pvp_matches.clear()
    async with db_pool.acquire() as conn:
        await conn.execute("UPDATE battles SET status = 'abandoned' WHERE status = 'active' OR status = 'pending'")
    await message.reply("✅ All battle data cleared (in‑memory and database pending/active battles set to 'abandoned').")

# ------------------------------------------------------------
# NEW: EVENTS
# ------------------------------------------------------------
@dp.message(Command("event"))
async def event_cmd(message: types.Message):
    async with db_pool.acquire() as conn:
        now = datetime.now()
        events = await conn.fetch("SELECT * FROM events WHERE active = TRUE AND start_time <= $1 AND end_time >= $1", now)
        if not events:
            await message.reply("🎯 No active events right now.")
            return
        resp = "🎯 **Active Events**\n━━━━━━━━━━━━━━━━━━━\n"
        for e in events:
            resp += f"🔥 {e['event_type'].title()}: **{e['boss_name']}**\n"
            resp += f"⏳ Ends: {e['end_time'].strftime('%Y-%m-%d %H:%M')}\n"
            if e.get('reward_pool'):
                rewards = json.loads(e['reward_pool'])
                resp += f"🎁 Rewards: {', '.join([f'{k}: {v}' for k, v in rewards.items()])}\n"
            resp += f"Use `/event_battle {e['id']}` to fight!\n\n"
        await message.reply(resp)

@dp.message(Command("event_battle"))
async def event_battle_cmd(message: types.Message):
    args = message.text.split()
    if len(args) < 2:
        await message.reply("Usage: /event_battle [event_id]")
        return
    event_id = int(args[1])
    user_id = message.from_user.id
    if user_id in ongoing_battles:
        await message.reply("⚠️ You already have an ongoing battle.")
        return
    async with db_pool.acquire() as conn:
        event = await conn.fetchrow("SELECT * FROM events WHERE id = $1 AND active = TRUE AND start_time <= NOW() AND end_time >= NOW()", event_id)
        if not event:
            await message.reply("Event not found or expired.")
            return
        player = await conn.fetchrow("SELECT * FROM players WHERE user_id = $1", user_id)
        if not player:
            await message.reply("Start with /start first!")
            return
        enemy_base = await conn.fetchrow("SELECT * FROM enemies WHERE name ILIKE $1", event['boss_name'])
        if not enemy_base:
            await message.reply("Boss not found in database.")
            return
        enemy = scale_enemy_to_player(player, enemy_base)
        enemy['hp'] = int(enemy['hp'] * 1.5)
        enemy['reward_yen'] = int(enemy['reward_yen'] * 1.5)
        enemy['reward_xp'] = int(enemy['reward_xp'] * 1.5)
        await message.reply_animation(animation=EFFECTS["clan_raid"])
        battle_id = await conn.fetchval("""
            INSERT INTO battles (chat_id, player1_id, current_hp1, current_hp2,
                                 enemy_name, enemy_rank, enemy_atk, enemy_def, enemy_spd,
                                 is_boss, enemy_reward_yen, enemy_reward_xp, enemy_max_hp,
                                 vow_effects, participants, is_event, event_id)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, TRUE, $10, $11, $12, $13, $14, TRUE, $15)
            RETURNING id
        """, message.chat.id, user_id, player['hp'], enemy['hp'],
           enemy['name'], enemy['rank'], enemy['atk'], enemy['def'], enemy['spd'],
           enemy['reward_yen'], enemy['reward_xp'], enemy['hp'],
           json.dumps([]), json.dumps([user_id]), event_id)
        ongoing_battles[user_id] = battle_id
        battle_queues[battle_id] = {
            "participants": {user_id: []},
            "current_hp": enemy['hp'],
            "log": []
        }
        vows = await conn.fetch("SELECT v.effect FROM player_vows pv JOIN binding_vows v ON pv.vow_id = v.id WHERE pv.player_id = $1 AND pv.active = TRUE", user_id)
        vow_effects = [v['effect'] for v in vows]
        await conn.execute("UPDATE battles SET vow_effects = $1 WHERE id = $2", json.dumps(vow_effects), battle_id)
        await show_battle_turn(message, battle_id, player, enemy, vow_effects)

# ------------------------------------------------------------
# NEW: QUESTS
# ------------------------------------------------------------
@dp.message(Command("quests"))
async def quests_cmd(message: types.Message):
    user_id = message.from_user.id
    async with db_pool.acquire() as conn:
        quests = await conn.fetch("SELECT * FROM quests WHERE type = 'side' OR (type = 'story' AND chapter_id IS NOT NULL)")
        if not quests:
            await message.reply("No quests available.")
            return
        player_quests = await conn.fetch("SELECT quest_id, progress, completed FROM player_quests WHERE player_id = $1", user_id)
        resp = "📜 **Quests**\n━━━━━━━━━━━━━━━━━━━\n"
        for q in quests:
            pq = next((p for p in player_quests if p['quest_id'] == q['id']), None)
            status = "✅" if pq and pq['completed'] else "⏳" if pq else "🔒"
            progress = f" ({pq['progress']}/{q['requirement'].split(':')[1]})" if pq and not pq['completed'] else ""
            resp += f"{status} **{q['title']}** – {q['description']}{progress}\n"
            resp += f"   Reward: ¥{q['reward_yen']}, XP {q['reward_xp']}\n"
        resp += "\nAccept: `/quest_accept [id]`"
        await message.reply(resp)

@dp.message(Command("quest_accept"))
async def quest_accept(message: types.Message):
    args = message.text.split()
    if len(args) < 2:
        await message.reply("Usage: /quest_accept [quest_id]")
        return
    quest_id = int(args[1])
    user_id = message.from_user.id
    async with db_pool.acquire() as conn:
        quest = await conn.fetchrow("SELECT * FROM quests WHERE id = $1", quest_id)
        if not quest:
            await message.reply("Quest not found.")
            return
        existing = await conn.fetchrow("SELECT * FROM player_quests WHERE player_id = $1 AND quest_id = $2", user_id, quest_id)
        if existing:
            await message.reply("You already have this quest.")
            return
        await conn.execute("INSERT INTO player_quests (player_id, quest_id, progress) VALUES ($1, $2, 0)", user_id, quest_id)
        await message.reply(f"✅ Quest accepted: **{quest['title']}**")

@dp.message(Command("quest_reward"))
async def quest_reward(message: types.Message):
    args = message.text.split()
    if len(args) < 2:
        await message.reply("Usage: /quest_reward [quest_id]")
        return
    quest_id = int(args[1])
    user_id = message.from_user.id
    async with db_pool.acquire() as conn:
        pq = await conn.fetchrow("SELECT * FROM player_quests WHERE player_id = $1 AND quest_id = $2 AND completed = TRUE", user_id, quest_id)
        if not pq:
            await message.reply("Quest not completed or not found.")
            return
        quest = await conn.fetchrow("SELECT * FROM quests WHERE id = $1", quest_id)
        if not quest:
            await message.reply("Quest not found.")
            return
        await conn.execute("UPDATE players SET yen = LEAST(yen + $1, $2), xp = xp + $3 WHERE user_id = $4",
                           quest['reward_yen'], MAX_YEN, quest['reward_xp'], user_id)
        if quest.get('reward_item'):
            await conn.execute("UPDATE players SET bag = array_append(bag, $1) WHERE user_id = $2",
                               quest['reward_item'], user_id)
        await conn.execute("DELETE FROM player_quests WHERE player_id = $1 AND quest_id = $2", user_id, quest_id)
        await update_player_stats(user_id)
        await message.reply(f"✅ Rewards claimed for **{quest['title']}**! +¥{quest['reward_yen']}, +{quest['reward_xp']} XP.")

# ------------------------------------------------------------
# NEW: MATERIALS & CRAFTING
# ------------------------------------------------------------
@dp.message(Command("materials"))
async def materials_cmd(message: types.Message):
    user_id = message.from_user.id
    async with db_pool.acquire() as conn:
        materials = await conn.fetch("SELECT m.*, pm.quantity FROM materials m LEFT JOIN player_materials pm ON m.id = pm.material_id AND pm.player_id = $1", user_id)
        if not materials:
            await message.reply("You have no materials. Defeat bosses to earn them.")
            return
        resp = "📦 **Your Materials**\n━━━━━━━━━━━━━━━━━━━\n"
        for m in materials:
            qty = m['quantity'] or 0
            resp += f"• {m['name']} x{qty} ({m['rarity']})\n"
        await message.reply(resp)

@dp.message(Command("craft"))
async def craft_cmd(message: types.Message):
    args = message.text.split()
    if len(args) < 2:
        await message.reply("Usage: /craft list | /craft [recipe name]")
        return
    user_id = message.from_user.id
    async with db_pool.acquire() as conn:
        if args[1].lower() == 'list':
            recipes = await conn.fetch("SELECT * FROM recipes")
            if not recipes:
                await message.reply("No recipes available.")
                return
            resp = "🔨 **Crafting Recipes**\n━━━━━━━━━━━━━━━━━━━\n"
            for r in recipes:
                resp += f"• **{r['name']}** – {r['description']}\n"
                resp += f"  Result: {r['result_item']}\n"
                resp += f"  Cost: ¥{r['cost_yen']}\n"
                ingredients = json.loads(r['ingredients'])
                for mid, qty in ingredients.items():
                    mat = await conn.fetchrow("SELECT name FROM materials WHERE id = $1", int(mid))
                    mat_name = mat['name'] if mat else f"Material {mid}"
                    resp += f"    - {mat_name} x{qty}\n"
            await message.reply(resp)
            return
        name = " ".join(args[1:])
        recipe = await conn.fetchrow("SELECT * FROM recipes WHERE name ILIKE $1", name)
        if not recipe:
            await message.reply("Recipe not found.")
            return
        ingredients = json.loads(recipe['ingredients'])
        player = await conn.fetchrow("SELECT yen FROM players WHERE user_id = $1", user_id)
        if player['yen'] < recipe['cost_yen']:
            await message.reply(f"Not enough Yen! Need ¥{recipe['cost_yen']}, have ¥{player['yen']}.")
            return
        for mid, qty in ingredients.items():
            player_mat = await conn.fetchrow("SELECT quantity FROM player_materials WHERE player_id = $1 AND material_id = $2", user_id, int(mid))
            if not player_mat or player_mat['quantity'] < qty:
                mat = await conn.fetchrow("SELECT name FROM materials WHERE id = $1", int(mid))
                mat_name = mat['name'] if mat else f"Material {mid}"
                await message.reply(f"Not enough {mat_name}. Need {qty}.")
                return
        await conn.execute("UPDATE players SET yen = yen - $1 WHERE user_id = $2", recipe['cost_yen'], user_id)
        for mid, qty in ingredients.items():
            await conn.execute("UPDATE player_materials SET quantity = quantity - $1 WHERE player_id = $2 AND material_id = $3",
                               qty, user_id, int(mid))
        await conn.execute("UPDATE players SET bag = array_append(bag, $1) WHERE user_id = $2", recipe['result_item'], user_id)
        await message.reply(f"✅ Crafted **{recipe['result_item']}**! Check /bag.")

# ------------------------------------------------------------
# NEW: LEADERBOARDS
# ------------------------------------------------------------
@dp.message(Command("leaderboard"))
async def leaderboard_cmd(message: types.Message):
    args = message.text.split()
    category = args[1].lower() if len(args) > 1 else 'level'
    async with db_pool.acquire() as conn:
        if category == 'level':
            rows = await conn.fetch("SELECT username, level FROM players ORDER BY level DESC LIMIT 10")
            label = "Level"
        elif category == 'wins':
            rows = await conn.fetch("SELECT username, wins FROM players ORDER BY wins DESC LIMIT 10")
            label = "Wins"
        elif category == 'boss_kills':
            rows = await conn.fetch("SELECT username, boss_kills FROM players ORDER BY boss_kills DESC LIMIT 10")
            label = "Boss Kills"
        elif category == 'prestige':
            rows = await conn.fetch("SELECT username, prestige_level FROM players ORDER BY prestige_level DESC LIMIT 10")
            label = "Prestige"
        elif category == 'yen':
            rows = await conn.fetch("SELECT username, yen FROM players ORDER BY yen DESC LIMIT 10")
            label = "Yen"
        else:
            await message.reply("Invalid category. Options: level, wins, boss_kills, prestige, yen")
            return
        if not rows:
            await message.reply("No players found.")
            return
        resp = f"🏆 **Leaderboard – {category.title()}**\n━━━━━━━━━━━━━━━━━━━\n"
        for i, row in enumerate(rows, 1):
            val = row[category]
            resp += f"{i}. {row['username']} – {val} {label}\n"
        await message.reply(resp)

# ------------------------------------------------------------
# NEW: ADMIN BROADCAST (owner only)
# ------------------------------------------------------------
@dp.message(Command("broadcast"))
async def broadcast_cmd(message: types.Message):
    if not await is_owner(message.from_user.id):
        await message.reply("❌ Owner only.")
        return
    text = message.text.replace('/broadcast', '', 1).strip()
    if not text:
        await message.reply("Usage: /broadcast [message]")
        return
    async with db_pool.acquire() as conn:
        players = await conn.fetch("SELECT user_id FROM players")
        sent = 0
        for p in players:
            try:
                await bot.send_message(p['user_id'], f"📢 **Announcement:**\n{text}")
                sent += 1
                await asyncio.sleep(0.05)
            except:
                pass
        await message.reply(f"✅ Broadcast sent to {sent} players.")

# ------------------------------------------------------------
# MAIN
# ------------------------------------------------------------
async def main():
    await on_startup()
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
