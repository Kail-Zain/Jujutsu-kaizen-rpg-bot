import asyncio
import os
import random
import json
from datetime import datetime
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
import asyncpg
from dotenv import load_dotenv

# ============================================================
# ENVIRONMENT
# ============================================================
load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")
DATABASE_URL = os.getenv("DATABASE_URL")
if not BOT_TOKEN or not DATABASE_URL:
    raise ValueError("Missing BOT_TOKEN or DATABASE_URL")

# ============================================================
# OWNER & BRANDING
# ============================================================
ADMIN_IDS = [8609946980]
OWNER_NAME = "𝕄𝕒𝕩𝕨𝕖𝕝𝕝-𝟜𝟟"
YEN_PURCHASE_INFO = f"💰 **Buy Yen** — Contact {OWNER_NAME} directly."

# ============================================================
# EFFECT ASSETS (ALL – NO PLACEHOLDERS)
# ============================================================
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
}

# ============================================================
# BOT & DB
# ============================================================
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()
db_pool = None
battle_queues = {}  # {battle_id: {"player_id": int, "slots": [move_dict or None]}}

# ============================================================
# HELPERS
# ============================================================
def calc_rank(level, wins):
    if level >= 50 and wins >= 100: return "Special Grade"
    if level >= 30 and wins >= 50: return "Semi-Special"
    if level >= 20 and wins >= 30: return "Grade 1"
    if level >= 15 and wins >= 20: return "Grade 2"
    if level >= 10 and wins >= 10: return "Grade 3"
    return "Grade 4"

def calc_level(xp):
    return (xp // 100) + 1

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

def get_max_slots(level):
    if level >= 71: return 10
    if level >= 51: return 9
    if level >= 41: return 8
    if level >= 31: return 7
    if level >= 21: return 6
    if level >= 16: return 5
    if level >= 11: return 4
    if level >= 6: return 3
    return 2

def format_slot(slot, index):
    if slot is None:
        return f"Slot {index+1}: [ ]"
    move_type = slot.get('type', 'unknown')
    ce_cost = slot.get('ce_cost', 0)
    if move_type == 'attack':
        return f"Slot {index+1}: ⚔️ Attack ({ce_cost} CE)"
    elif move_type == 'defend':
        return f"Slot {index+1}: 🛡️ Defend ({ce_cost} CE)"
    elif move_type == 'special':
        return f"Slot {index+1}: 💥 Special ({ce_cost} CE)"
    elif move_type == 'technique':
        return f"Slot {index+1}: 🌀 {slot.get('tech_name')} ({ce_cost} CE)"
    elif move_type == 'domain':
        return f"Slot {index+1}: 🌐 {slot.get('domain_name')} ({ce_cost} CE)"
    return f"Slot {index+1}: ?"

# ============================================================
# GUIDE COMMAND
# ============================================================
@dp.message(Command("guide"))
async def guide_cmd(message: types.Message):
    guide_text = (
        "📖 **Cursed Chronicles – Game Guide**\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        "⚔️ **BATTLE SYSTEM**\n"
        "• You have a **move queue** of up to 10 slots.\n"
        "• The number of slots depends on your **Level**.\n"
        "• Each turn, fill slots with moves (Attack, Defend, Special, Technique, Domain).\n"
        "• Each move costs **Cursed Energy (CE)** – displayed on the button.\n"
        "• Click **Execute** to perform all queued moves in order.\n"
        "• The enemy counter‑attacks after your whole combo.\n"
        "• **CE** regenerates slowly outside battle (coming soon).\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        "🎭 **CHARACTERS**\n"
        "• Start with **Yuji Itadori** for free.\n"
        "• Buy other characters (Gojo, Sukuna, etc.) via `/characters`.\n"
        "• Each character has unique stats and techniques.\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        "🏪 **SHOP & INVENTORY**\n"
        "• Buy weapons, elixirs, techniques, and domains.\n"
        "• Equip weapons to boost ATK.\n"
        "• Use elixirs to gain XP and restore HP/CE.\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        "📋 **MISSIONS**\n"
        "• Daily, Weekly, Monthly and Clan missions.\n"
        "• Claim rewards with `/daily`.\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        "💰 **YEN**\n"
        "• Earn Yen by winning battles and completing missions.\n"
        "• Buy Yen directly from the owner: {OWNER_NAME}.\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        "👑 **PVP**\n"
        "• Challenge other players with `/pvp @username`.\n"
        "• Accept with `/pvp_accept battle_id`.\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        "🌟 **AWAKENING & PRESTIGE** (coming soon)\n"
        "• Unlock special abilities and reset for higher potential.\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"📌 **Owner**: {OWNER_NAME}\n"
        "Type /commands for the full command list."
    )
    await message.reply(guide_text)

# ============================================================
# COMMAND /start
# ============================================================
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
            # Give Yuji for free
            await conn.execute("""
                INSERT INTO player_characters (player_id, character_name)
                VALUES ($1, 'Yuji Itadori')
                ON CONFLICT DO NOTHING
            """, user_id)
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
            f"🏅 Rank: {player['rank']}\n"
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

# ============================================================
# WELCOME CALLBACK
# ============================================================
@dp.callback_query(lambda c: c.data.startswith("welcome_"))
async def welcome_cb(callback: types.CallbackQuery):
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

# ============================================================
# PROFILE (unchanged but with all stats)
# ============================================================
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
            rep_str = safe_rep_str(player.get('reputation'))
            caption = (
                f"👤 **Cursed Chronicle**\n"
                f"━━━━━━━━━━━━━━━━━━━\n"
                f"🎭 Character: {char_name or 'None'}\n"
                f"🏅 Rank: {player['rank']}\n"
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
                f"💎 Prestige: {player['prestige']} (Lv.{player['prestige_level']})\n"
                f"🏟️ Arena Rank: {player['arena_rank']}\n"
                f"━━━━━━━━━━━━━━━━━━━\n"
                f"{YEN_PURCHASE_INFO}"
            )
            if awakening != "None":
                await message.reply_animation(animation=EFFECTS["cursed_energy"], caption=caption)
            elif image_url:
                await message.reply_photo(photo=image_url, caption=caption)
            else:
                await message.reply(caption)
    except Exception as e:
        await message.reply(f"Error: {e}")

# ============================================================
# CHARACTERS (with purchase and ownership)
# ============================================================
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
                        types.InputMediaPhoto(media=char['image_url'], caption=caption),
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
    parts = callback.data.split("_")
    if parts[1] == "buy":
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
            await callback.answer(f"Selected {char['name']}!")
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
                    types.InputMediaPhoto(media=char['image_url'], caption=caption),
                    reply_markup=None
                )
            else:
                await callback.message.edit_text(caption, reply_markup=None)
    except Exception as e:
        await callback.answer(f"Error: {e}", show_alert=True)

@dp.callback_query(lambda c: c.data == "char_page_noop")
async def char_page_noop(callback: types.CallbackQuery):
    await callback.answer("Current page")

# ============================================================
# SELECT (with ownership check)
# ============================================================
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
            await message.reply(f"✅ Selected **{char['name']}**! Check /profile")
    except Exception as e:
        await message.reply(f"Error: {e}")

# ============================================================
# SHOP (unchanged)
# ============================================================
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

# ============================================================
# BUY (unchanged)
# ============================================================
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
            await conn.execute("UPDATE players SET yen = yen - $1 WHERE user_id = $2", item['price'], user_id)
            if item['category'] == 'technique':
                await conn.execute("UPDATE players SET techniques = array_append(techniques, $1) WHERE user_id = $2",
                                   item['name'], user_id)
            elif item['category'] == 'domain':
                await conn.execute("UPDATE players SET domains = array_append(domains, $1) WHERE user_id = $2",
                                   item['name'], user_id)
            else:
                await conn.execute("UPDATE players SET bag = array_append(bag, $1) WHERE user_id = $2",
                                   item['name'], user_id)
            await message.reply(f"✅ Bought **{item['name']}**!\n💰 Remaining: ¥{player['yen'] - item['price']:,}\n📦 Check /bag")
    except Exception as e:
        await message.reply(f"Error: {e}")

# ============================================================
# BAG, USE, EQUIP, LEARN, TECHNIQUES (unchanged)
# ============================================================
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
                new_level = calc_level(new_xp)
                new_rank = calc_rank(new_level, player['wins'])
                await conn.execute("UPDATE players SET xp = $1, level = $2, rank = $3 WHERE user_id = $4",
                                   new_xp, new_level, new_rank, user_id)
                response += f"⭐ Gained {xp_gain} XP! (Level {new_level}, Rank {new_rank})\n"
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
            old_weapon = player.get('equipped_weapon')
            if old_weapon:
                old = await conn.fetchrow("SELECT * FROM shop_items WHERE name = $1 AND category = 'weapon'", old_weapon)
                if old:
                    old_effects = parse_effect(old['effect'])
                    old_bonus = int(old_effects.get('atk_bonus', 0))
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
    tech_name = args[1].strip()
    user_id = message.from_user.id
    try:
        async with db_pool.acquire() as conn:
            player = await conn.fetchrow("SELECT * FROM players WHERE user_id = $1", user_id)
            if not player:
                await message.reply("Start with /start first!")
                return
            techniques = player.get('techniques') or []
            if tech_name not in techniques:
                await message.reply(f"❌ You don't own '{tech_name}'. Buy it from /shop first.")
                return
            await message.reply_animation(
                animation=EFFECTS["cursed_energy"],
                caption=f"🌀 **{tech_name}** is ready to use in battle!\nUse the 'Technique' button."
            )
    except Exception as e:
        await message.reply(f"Error: {e}")

@dp.message(Command("techniques"))
async def techniques_cmd(message: types.Message):
    user_id = message.from_user.id
    try:
        async with db_pool.acquire() as conn:
            player = await conn.fetchrow("SELECT techniques FROM players WHERE user_id = $1", user_id)
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
                    resp += f"  • {t} (DMG: {detail['damage_multiplier']}x, CE: {detail['ce_cost']})\n"
                else:
                    resp += f"  • {t}\n"
            await message.reply(resp)
    except Exception as e:
        await message.reply(f"Error: {e}")

# ============================================================
# ENEMIES (unchanged)
# ============================================================
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

# ============================================================
# BATTLE SYSTEM (SLOT-BASED QUEUE)
# ============================================================
@dp.message(Command("battle"))
async def battle_cmd(message: types.Message):
    user_id = message.from_user.id
    try:
        async with db_pool.acquire() as conn:
            player = await conn.fetchrow("SELECT * FROM players WHERE user_id = $1", user_id)
            if not player:
                await message.reply("Start with /start first!")
                return
            enemy = await conn.fetchrow("SELECT * FROM enemies WHERE is_boss = FALSE ORDER BY RANDOM() LIMIT 1")
            if not enemy:
                await message.reply("No enemies available!")
                return
            await message.reply_animation(animation=EFFECTS["versus"])
            battle_id = await conn.fetchval("""
                INSERT INTO battles (chat_id, player1_id, current_hp1, current_hp2, 
                                     enemy_name, enemy_rank, enemy_atk, enemy_def, enemy_spd,
                                     is_boss, enemy_reward_yen, enemy_reward_xp, enemy_max_hp)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, FALSE, $10, $11, $12)
                RETURNING id
            """, message.chat.id, user_id, player['hp'], enemy['hp'], 
               enemy['name'], enemy['rank'], enemy['atk'], enemy['def'], enemy['spd'],
               enemy.get('reward_yen', 1000), enemy.get('reward_xp', 100), enemy['hp'])
            # Initialize queue with empty slots
            max_slots = get_max_slots(player['level'])
            battle_queues[battle_id] = {"player_id": user_id, "slots": [None] * max_slots}
            await show_battle_slots(message, battle_id, player, enemy)
    except Exception as e:
        await message.reply(f"Error starting battle: {e}")

@dp.message(Command("boss"))
async def boss_cmd(message: types.Message):
    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        await message.reply("Usage: /boss \"boss name\"")
        return
    boss_name = args[1].strip()
    user_id = message.from_user.id
    try:
        async with db_pool.acquire() as conn:
            player = await conn.fetchrow("SELECT * FROM players WHERE user_id = $1", user_id)
            if not player:
                await message.reply("Start with /start first!")
                return
            enemy = await conn.fetchrow("SELECT * FROM enemies WHERE name ILIKE $1 AND is_boss = TRUE", boss_name)
            if not enemy:
                await message.reply(f"Boss '{boss_name}' not found.")
                return
            await message.reply_animation(animation=EFFECTS["versus"])
            battle_id = await conn.fetchval("""
                INSERT INTO battles (chat_id, player1_id, current_hp1, current_hp2, 
                                     enemy_name, enemy_rank, enemy_atk, enemy_def, enemy_spd,
                                     is_boss, enemy_reward_yen, enemy_reward_xp, enemy_max_hp)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, TRUE, $10, $11, $12)
                RETURNING id
            """, message.chat.id, user_id, player['hp'], enemy['hp'], 
               enemy['name'], enemy['rank'], enemy['atk'], enemy['def'], enemy['spd'],
               enemy.get('reward_yen', 5000), enemy.get('reward_xp', 500), enemy['hp'])
            max_slots = get_max_slots(player['level'])
            battle_queues[battle_id] = {"player_id": user_id, "slots": [None] * max_slots}
            await show_battle_slots(message, battle_id, player, enemy)
    except Exception as e:
        await message.reply(f"Error: {e}")

async def show_battle_slots(message_or_callback, battle_id, player, enemy):
    queue = battle_queues.get(battle_id, {"slots": [None] * get_max_slots(player['level'])})
    slots = queue.get("slots", [])
    max_slots = len(slots)
    # Build queue display
    queue_lines = []
    total_ce_cost = 0
    for i, slot in enumerate(slots):
        if slot is None:
            queue_lines.append(f"Slot {i+1}: [ ]")
        else:
            ce_cost = slot.get('ce_cost', 0)
            total_ce_cost += ce_cost
            queue_lines.append(format_slot(slot, i))
    used_slots = sum(1 for s in slots if s is not None)
    queue_text = "\n".join(queue_lines)
    ce_remaining = player['ce'] - total_ce_cost

    # Build keyboard with move buttons
    keyboard = []
    # Row 1: Attack, Defend, Special, Technique, Domain
    row1 = []
    row1.append(InlineKeyboardButton(text="⚔️ Attack (0)", callback_data=f"bs_add_{battle_id}_attack"))
    row1.append(InlineKeyboardButton(text="🛡️ Defend (0)", callback_data=f"bs_add_{battle_id}_defend"))
    row1.append(InlineKeyboardButton(text="💥 Special (30)", callback_data=f"bs_add_{battle_id}_special"))
    row1.append(InlineKeyboardButton(text="🌀 Tech", callback_data=f"bs_tech_{battle_id}"))
    row1.append(InlineKeyboardButton(text="🌐 Domain", callback_data=f"bs_domain_{battle_id}"))
    keyboard.append(row1)
    # Row 2: Remove last slot, Clear all, Execute, Run
    row2 = []
    row2.append(InlineKeyboardButton(text="🗑️ Clear", callback_data=f"bs_clear_{battle_id}"))
    row2.append(InlineKeyboardButton(text="▶️ Execute", callback_data=f"bs_execute_{battle_id}"))
    row2.append(InlineKeyboardButton(text="🏃 Run", callback_data=f"bs_run_{battle_id}"))
    keyboard.append(row2)
    # Add remove buttons for filled slots (if any)
    remove_buttons = []
    for i, slot in enumerate(slots):
        if slot is not None:
            remove_buttons.append(InlineKeyboardButton(text=f"❌ Slot {i+1}", callback_data=f"bs_remove_{battle_id}_{i}"))
    if remove_buttons:
        # split into rows of 3
        for i in range(0, len(remove_buttons), 3):
            keyboard.append(remove_buttons[i:i+3])

    markup = InlineKeyboardMarkup(inline_keyboard=keyboard)

    hp_bar = build_hp_bar(player['hp'], player['max_hp'])
    ce_bar = build_ce_bar(player['ce'], player['max_ce'])
    enemy_hp_bar = build_hp_bar(enemy['hp'], enemy['hp'])

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
        f"📦 **QUEUE** ({used_slots}/{max_slots} slots used)\n"
        f"{queue_text}\n"
        f"Total CE cost: {total_ce_cost} | Remaining CE: {ce_remaining}\n"
        f"━━━━━━━━━━━━━━━━━━━\n"
        f"Select a move to add, then press Execute."
    )

    if isinstance(message_or_callback, types.Message):
        msg = message_or_callback
        if enemy.get('image_url'):
            await msg.reply_photo(photo=enemy['image_url'], caption=caption, reply_markup=markup)
        else:
            await msg.reply(caption, reply_markup=markup)
    else:
        callback = message_or_callback
        if enemy.get('image_url'):
            await callback.message.edit_media(
                types.InputMediaPhoto(media=enemy['image_url'], caption=caption),
                reply_markup=markup
            )
        else:
            await callback.message.edit_text(caption, reply_markup=markup)

# ----- BATTLE SLOT CALLBACKS -----
@dp.callback_query(lambda c: c.data.startswith("bs_"))
async def battle_slot_cb(callback: types.CallbackQuery):
    parts = callback.data.split("_")
    action = parts[1]
    battle_id = int(parts[2])
    user_id = callback.from_user.id

    async with db_pool.acquire() as conn:
        battle = await conn.fetchrow("SELECT * FROM battles WHERE id = $1", battle_id)
        if not battle:
            await callback.answer("Battle expired!", show_alert=True)
            return
        if battle['status'] != 'active':
            await callback.answer("Battle ended.", show_alert=True)
            return
        player = await conn.fetchrow("SELECT * FROM players WHERE user_id = $1", battle['player1_id'])
        if not player:
            await callback.answer("Player not found!", show_alert=True)
            return
        enemy = {"name": battle['enemy_name'], "rank": battle['enemy_rank'], "hp": battle['current_hp2'],
                 "atk": battle['enemy_atk'], "def": battle['enemy_def'], "spd": battle['enemy_spd'],
                 "max_hp": battle['enemy_max_hp']}

        queue = battle_queues.get(battle_id, {"slots": [None] * get_max_slots(player['level'])})
        slots = queue.get("slots", [])
        max_slots = len(slots)

        if action == "add":
            move_type = parts[3]
            # Find first empty slot
            empty_index = -1
            for i, s in enumerate(slots):
                if s is None:
                    empty_index = i
                    break
            if empty_index == -1:
                await callback.answer("Queue full! Use Clear or Execute.", show_alert=True)
                return
            # Create move dict
            ce_cost = 0
            if move_type == "attack":
                move = {"type": "attack", "ce_cost": 0}
            elif move_type == "defend":
                move = {"type": "defend", "ce_cost": 0}
            elif move_type == "special":
                move = {"type": "special", "ce_cost": 30}
            else:
                await callback.answer("Unknown move.", show_alert=True)
                return
            slots[empty_index] = move
            queue["slots"] = slots
            battle_queues[battle_id] = queue
            await callback.answer(f"Added {move_type} to slot {empty_index+1}!")
            # Refresh battle view
            await show_battle_slots(callback, battle_id, player, enemy)

        elif action == "remove":
            slot_idx = int(parts[3])
            if slot_idx < 0 or slot_idx >= len(slots):
                await callback.answer("Invalid slot.", show_alert=True)
                return
            if slots[slot_idx] is None:
                await callback.answer("Slot is empty.", show_alert=True)
                return
            slots[slot_idx] = None
            queue["slots"] = slots
            battle_queues[battle_id] = queue
            await callback.answer(f"Cleared slot {slot_idx+1}.")
            await show_battle_slots(callback, battle_id, player, enemy)

        elif action == "clear":
            for i in range(len(slots)):
                slots[i] = None
            queue["slots"] = slots
            battle_queues[battle_id] = queue
            await callback.answer("Queue cleared.")
            await show_battle_slots(callback, battle_id, player, enemy)

        elif action == "execute":
            # Validate CE
            total_ce = sum(s.get('ce_cost', 0) for s in slots if s is not None)
            if player['ce'] < total_ce:
                await callback.answer(f"Not enough CE! Need {total_ce}, have {player['ce']}", show_alert=True)
                return
            # Execute all moves in order
            exec_log = []
            total_damage = 0
            defend_flag = False
            # Deduct CE first
            await conn.execute("UPDATE players SET ce = ce - $1 WHERE user_id = $2", total_ce, player['user_id'])
            new_player_ce = player['ce'] - total_ce
            # Process each slot
            for slot in slots:
                if slot is None:
                    continue
                move_type = slot.get('type')
                if move_type == 'attack':
                    dmg = max(1, int(player['atk'] * random.uniform(0.8, 1.2)))
                    total_damage += dmg
                    exec_log.append(f"⚔️ Attack: {dmg} damage")
                elif move_type == 'defend':
                    defend_flag = True
                    exec_log.append("🛡️ Defend (halves next enemy damage)")
                elif move_type == 'special':
                    dmg = max(1, int(player['atk'] * random.uniform(1.5, 2.5)))
                    total_damage += dmg
                    exec_log.append(f"💥 Special: {dmg} damage")
                elif move_type == 'technique':
                    tech_name = slot.get('tech_name')
                    tech = await conn.fetchrow("SELECT * FROM techniques WHERE name = $1", tech_name)
                    if tech:
                        dmg = max(1, int(player['atk'] * tech['damage_multiplier'] * random.uniform(0.9, 1.1)))
                        total_damage += dmg
                        exec_log.append(f"🌀 {tech_name}: {dmg} damage")
                elif move_type == 'domain':
                    domain_name = slot.get('domain_name')
                    domain = await conn.fetchrow("SELECT * FROM techniques WHERE name = $1 AND category = 'domain'", domain_name)
                    if domain:
                        dmg = max(1, int(player['atk'] * domain['damage_multiplier'] * random.uniform(0.9, 1.1)))
                        total_damage += dmg
                        exec_log.append(f"🌐 {domain_name}: {dmg} damage")
                    else:
                        # check shop_items fallback
                        domain_item = await conn.fetchrow("SELECT * FROM shop_items WHERE name = $1 AND category = 'domain'", domain_name)
                        if domain_item:
                            dmg_mult = float(parse_effect(domain_item['effect']).get('damage', 3.5))
                            dmg = max(1, int(player['atk'] * dmg_mult * random.uniform(0.9, 1.1)))
                            total_damage += dmg
                            exec_log.append(f"🌐 {domain_name}: {dmg} damage")
            # Apply total damage to enemy
            new_enemy_hp = max(0, battle['current_hp2'] - total_damage)
            await conn.execute("UPDATE battles SET current_hp2 = $1 WHERE id = $2", new_enemy_hp, battle_id)
            # Enemy counter (only if not defended)
            enemy_dmg = 0
            if not defend_flag:
                enemy_dmg = max(1, int(enemy['atk'] * random.uniform(0.5, 0.9)))
            else:
                enemy_dmg = max(1, int(enemy['atk'] * random.uniform(0.2, 0.4)))  # reduced
                # clear defend flag
                await conn.execute("UPDATE battles SET defend_flag = FALSE WHERE id = $1", battle_id)
            new_player_hp = max(0, battle['current_hp1'] - enemy_dmg)
            await conn.execute("UPDATE battles SET current_hp1 = $1 WHERE id = $2", new_player_hp, battle_id)

            # Check win/lose
            if new_enemy_hp <= 0:
                await conn.execute("""
                    UPDATE players SET yen = yen + $1, wins = wins + 1, xp = xp + $2, boss_kills = boss_kills + $3
                    WHERE user_id = $4
                """, battle['enemy_reward_yen'] or 1000, battle['enemy_reward_xp'] or 100,
                  1 if battle['is_boss'] else 0, player['user_id'])
                await callback.message.reply_animation(animation=EFFECTS["defeat"])
                await callback.message.edit_text(
                    f"🎉 **VICTORY!**\n"
                    f"━━━━━━━━━━━━━━━━━━━\n"
                    f"Executed moves:\n" + "\n".join(exec_log) +
                    f"\n━━━━━━━━━━━━━━━━━━━\n"
                    f"You defeated **{battle['enemy_name']}**!\n"
                    f"💰 +¥{battle['enemy_reward_yen'] or 1000}\n"
                    f"⭐ +{battle['enemy_reward_xp'] or 100} XP"
                )
                del battle_queues[battle_id]
                await callback.answer("Victory! 🎉")
                return
            if new_player_hp <= 0:
                await conn.execute("UPDATE players SET losses = losses + 1 WHERE user_id = $1", player['user_id'])
                await callback.message.reply_animation(animation=EFFECTS["defeat"])
                await callback.message.edit_text(
                    f"💀 **DEFEAT!**\n"
                    f"━━━━━━━━━━━━━━━━━━━\n"
                    f"Executed moves:\n" + "\n".join(exec_log) +
                    f"\n━━━━━━━━━━━━━━━━━━━\n"
                    f"You were defeated by **{battle['enemy_name']}**!"
                )
                del battle_queues[battle_id]
                await callback.answer("Defeated! 💀")
                return

            # Clear slots after execution
            for i in range(len(slots)):
                slots[i] = None
            queue["slots"] = slots
            battle_queues[battle_id] = queue
            # Update player stats for display
            player['hp'] = new_player_hp
            player['ce'] = new_player_ce
            enemy['hp'] = new_enemy_hp
            await show_battle_slots(callback, battle_id, player, enemy)
            await callback.answer(f"Executed {len([s for s in slots if s is None])} moves!")

        elif action == "run":
            if random.random() < 0.6:
                await callback.message.edit_text("🏃 You successfully escaped!")
                del battle_queues[battle_id]
                await callback.answer("Escaped! 🏃")
            else:
                enemy_dmg = max(1, int(enemy['atk'] * random.uniform(0.8, 1.2)))
                new_hp = max(0, battle['current_hp1'] - enemy_dmg)
                await conn.execute("UPDATE battles SET current_hp1 = $1 WHERE id = $2", new_hp, battle_id)
                if new_hp <= 0:
                    await conn.execute("UPDATE players SET losses = losses + 1 WHERE user_id = $1", player['user_id'])
                    await callback.message.reply_animation(animation=EFFECTS["defeat"])
                    await callback.message.edit_text("💀 **DEFEAT!**")
                    del battle_queues[battle_id]
                    await callback.answer("Defeated! 💀")
                    return
                # Continue battle
                player['hp'] = new_hp
                await show_battle_slots(callback, battle_id, player, enemy)
                await callback.answer("Failed to escape! Enemy attacked.")

        elif action == "tech":
            # Show technique selection
            techs = player.get('techniques') or []
            if not techs:
                await callback.answer("You have no techniques!", show_alert=True)
                return
            buttons = []
            for t in techs[:10]:
                tech = await conn.fetchrow("SELECT * FROM techniques WHERE name = $1", t)
                if tech:
                    ce_cost = tech['ce_cost']
                    buttons.append([InlineKeyboardButton(text=f"🌀 {t} ({ce_cost} CE)", callback_data=f"bs_addtech_{battle_id}_{t}")])
            buttons.append([InlineKeyboardButton(text="🔙 Back", callback_data=f"bs_back_{battle_id}")])
            markup = InlineKeyboardMarkup(inline_keyboard=buttons)
            await callback.message.edit_text(
                f"🌀 **Select a Technique**\n"
                f"Choose a technique to add to your queue.",
                reply_markup=markup
            )
            await callback.answer()

        elif action == "domain":
            # Show domain selection
            domains = player.get('domains') or []
            if not domains:
                await callback.answer("You have no domains!", show_alert=True)
                return
            buttons = []
            for d in domains[:5]:
                # find ce cost
                domain = await conn.fetchrow("SELECT * FROM techniques WHERE name = $1 AND category = 'domain'", d)
                if domain:
                    ce_cost = domain['ce_cost']
                else:
                    domain_item = await conn.fetchrow("SELECT * FROM shop_items WHERE name = $1 AND category = 'domain'", d)
                    if domain_item:
                        ce_cost = int(parse_effect(domain_item['effect']).get('ce_cost', 100))
                    else:
                        continue
                buttons.append([InlineKeyboardButton(text=f"🌐 {d} ({ce_cost} CE)", callback_data=f"bs_adddomain_{battle_id}_{d}")])
            buttons.append([InlineKeyboardButton(text="🔙 Back", callback_data=f"bs_back_{battle_id}")])
            markup = InlineKeyboardMarkup(inline_keyboard=buttons)
            await callback.message.edit_text(
                f"🌐 **Select a Domain**\n"
                f"Choose a domain to add to your queue.",
                reply_markup=markup
            )
            await callback.answer()

        elif action == "addtech":
            tech_name = parts[3]
            # find empty slot
            empty_index = -1
            for i, s in enumerate(slots):
                if s is None:
                    empty_index = i
                    break
            if empty_index == -1:
                await callback.answer("Queue full!", show_alert=True)
                return
            # Get ce cost
            tech = await conn.fetchrow("SELECT * FROM techniques WHERE name = $1", tech_name)
            if tech:
                ce_cost = tech['ce_cost']
                move = {"type": "technique", "tech_name": tech_name, "ce_cost": ce_cost}
            else:
                await callback.answer("Technique not found.", show_alert=True)
                return
            slots[empty_index] = move
            queue["slots"] = slots
            battle_queues[battle_id] = queue
            await callback.answer(f"Added {tech_name} to slot {empty_index+1}!")
            # Return to battle view
            await show_battle_slots(callback, battle_id, player, enemy)

        elif action == "adddomain":
            domain_name = parts[3]
            empty_index = -1
            for i, s in enumerate(slots):
                if s is None:
                    empty_index = i
                    break
            if empty_index == -1:
                await callback.answer("Queue full!", show_alert=True)
                return
            # Get ce cost
            domain = await conn.fetchrow("SELECT * FROM techniques WHERE name = $1 AND category = 'domain'", domain_name)
            if domain:
                ce_cost = domain['ce_cost']
            else:
                domain_item = await conn.fetchrow("SELECT * FROM shop_items WHERE name = $1 AND category = 'domain'", domain_name)
                if domain_item:
                    ce_cost = int(parse_effect(domain_item['effect']).get('ce_cost', 100))
                else:
                    await callback.answer("Domain not found.", show_alert=True)
                    return
            move = {"type": "domain", "domain_name": domain_name, "ce_cost": ce_cost}
            slots[empty_index] = move
            queue["slots"] = slots
            battle_queues[battle_id] = queue
            await callback.answer(f"Added {domain_name} to slot {empty_index+1}!")
            await show_battle_slots(callback, battle_id, player, enemy)

        elif action == "back":
            # Return to battle view
            await show_battle_slots(callback, battle_id, player, enemy)
            await callback.answer()

# ============================================================
# PVP (unchanged)
# ============================================================
@dp.message(Command("pvp"))
async def pvp_cmd(message: types.Message):
    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        await message.reply("Usage: /pvp @username")
        return
    target = args[1].strip().replace("@", "")
    user_id = message.from_user.id
    try:
        async with db_pool.acquire() as conn:
            player1 = await conn.fetchrow("SELECT * FROM players WHERE user_id = $1", user_id)
            if not player1:
                await message.reply("Start with /start first!")
                return
            target_user = await conn.fetchrow("SELECT * FROM players WHERE username ILIKE $1", target)
            if not target_user:
                await message.reply(f"User '{target}' not found.")
                return
            if target_user['user_id'] == user_id:
                await message.reply("You can't challenge yourself!")
                return
            battle_id = await conn.fetchval("""
                INSERT INTO battles (chat_id, player1_id, player2_id, current_hp1, current_hp2, is_pvp, enemy_max_hp)
                VALUES ($1, $2, $3, $4, $5, TRUE, $6)
                RETURNING id
            """, message.chat.id, user_id, target_user['user_id'], player1['hp'], target_user['hp'], target_user['max_hp'])
            await message.reply(
                f"⚔️ **PVP CHALLENGE!**\n"
                f"━━━━━━━━━━━━━━━━━━━\n"
                f"🧙 {player1['character_name'] or 'You'} vs {target_user['character_name'] or target}\n"
                f"❤️ Both at full HP!\n"
                f"━━━━━━━━━━━━━━━━━━━\n"
                f"Waiting for {target} to accept...\n"
                f"{target} type: /pvp_accept {battle_id}"
            )
    except Exception as e:
        await message.reply(f"Error: {e}")

@dp.message(Command("pvp_accept"))
async def pvp_accept_cmd(message: types.Message):
    args = message.text.split()
    if len(args) < 2:
        await message.reply("Usage: /pvp_accept battle_id")
        return
    battle_id = int(args[1])
    user_id = message.from_user.id
    try:
        async with db_pool.acquire() as conn:
            battle = await conn.fetchrow("SELECT * FROM battles WHERE id = $1 AND is_pvp = TRUE", battle_id)
            if not battle:
                await message.reply("Battle not found or already finished.")
                return
            if battle['player2_id'] != user_id:
                await message.reply("This battle is not for you.")
                return
            if battle['status'] != 'active':
                await message.reply("Battle already ended.")
                return
            player1 = await conn.fetchrow("SELECT * FROM players WHERE user_id = $1", battle['player1_id'])
            player2 = await conn.fetchrow("SELECT * FROM players WHERE user_id = $1", battle['player2_id'])
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="⚔️ Attack", callback_data=f"pvp_act_{battle_id}_attack"),
                 InlineKeyboardButton(text="🛡️ Defend", callback_data=f"pvp_act_{battle_id}_defend")],
                [InlineKeyboardButton(text="💥 Special", callback_data=f"pvp_act_{battle_id}_special"),
                 InlineKeyboardButton(text="🌀 Technique", callback_data=f"pvp_act_{battle_id}_technique")],
                [InlineKeyboardButton(text="🌐 Domain", callback_data=f"pvp_act_{battle_id}_domain"),
                 InlineKeyboardButton(text="🏃 Run", callback_data=f"pvp_act_{battle_id}_run")]
            ])
            caption = (
                f"⚔️ **PVP BATTLE START!**\n"
                f"━━━━━━━━━━━━━━━━━━━\n"
                f"🧙 {player1['character_name'] or 'Player1'}\n"
                f"❤️ HP: {battle['current_hp1']}/{player1['max_hp']}\n"
                f"━━━━━━━━━━━━━━━━━━━\n"
                f"🧙 {player2['character_name'] or 'Player2'}\n"
                f"❤️ HP: {battle['current_hp2']}/{player2['max_hp']}\n"
                f"━━━━━━━━━━━━━━━━━━━\n"
                f"It's your turn, {player2['character_name'] or 'Player2'}!"
            )
            await message.reply(caption, reply_markup=keyboard)
    except Exception as e:
        await message.reply(f"Error: {e}")

@dp.callback_query(lambda c: c.data.startswith("pvp_act_"))
async def pvp_action_cb(callback: types.CallbackQuery):
    await callback.answer("⚡ PVP Action!", cache_time=0)
    parts = callback.data.split("_")
    battle_id = int(parts[2])
    action = parts[3]
    try:
        async with db_pool.acquire() as conn:
            battle = await conn.fetchrow("SELECT * FROM battles WHERE id = $1 AND is_pvp = TRUE", battle_id)
            if not battle:
                await callback.answer("Battle expired!", show_alert=True)
                return
            user_id = callback.from_user.id
            if user_id == battle['player1_id']:
                attacker = await conn.fetchrow("SELECT * FROM players WHERE user_id = $1", battle['player1_id'])
                defender = await conn.fetchrow("SELECT * FROM players WHERE user_id = $1", battle['player2_id'])
                attack_hp = battle['current_hp1']
                defend_hp = battle['current_hp2']
                is_player1 = True
            elif user_id == battle['player2_id']:
                attacker = await conn.fetchrow("SELECT * FROM players WHERE user_id = $1", battle['player2_id'])
                defender = await conn.fetchrow("SELECT * FROM players WHERE user_id = $1", battle['player1_id'])
                attack_hp = battle['current_hp2']
                defend_hp = battle['current_hp1']
                is_player1 = False
            else:
                await callback.answer("You are not in this battle.", show_alert=True)
                return
            if not attacker or not defender:
                await callback.answer("Player data missing.", show_alert=True)
                return
            if action == "attack":
                dmg = max(1, int(attacker['atk'] * random.uniform(0.8, 1.2)))
                defend_hp_new = max(0, defend_hp - dmg)
                if is_player1:
                    await conn.execute("UPDATE battles SET current_hp2 = $1 WHERE id = $2", defend_hp_new, battle_id)
                else:
                    await conn.execute("UPDATE battles SET current_hp1 = $1 WHERE id = $2", defend_hp_new, battle_id)
                resp = f"⚔️ {attacker['character_name']} dealt {dmg} damage to {defender['character_name']}!"
                if defend_hp_new <= 0:
                    await conn.execute("UPDATE battles SET status = 'completed' WHERE id = $1", battle_id)
                    if is_player1:
                        await conn.execute("UPDATE players SET wins = wins + 1 WHERE user_id = $1", attacker['user_id'])
                        await conn.execute("UPDATE players SET losses = losses + 1 WHERE user_id = $1", defender['user_id'])
                    else:
                        await conn.execute("UPDATE players SET wins = wins + 1 WHERE user_id = $1", attacker['user_id'])
                        await conn.execute("UPDATE players SET losses = losses + 1 WHERE user_id = $1", defender['user_id'])
                    await callback.message.edit_text(
                        f"🏆 **PVP VICTORY!**\n"
                        f"━━━━━━━━━━━━━━━━━━━\n"
                        f"{attacker['character_name']} defeated {defender['character_name']}!"
                    )
                    await callback.answer("Battle over!")
                    return
                # Switch turn
                keyboard = InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="⚔️ Attack", callback_data=f"pvp_act_{battle_id}_attack"),
                     InlineKeyboardButton(text="🛡️ Defend", callback_data=f"pvp_act_{battle_id}_defend")],
                    [InlineKeyboardButton(text="💥 Special", callback_data=f"pvp_act_{battle_id}_special"),
                     InlineKeyboardButton(text="🌀 Technique", callback_data=f"pvp_act_{battle_id}_technique")],
                    [InlineKeyboardButton(text="🌐 Domain", callback_data=f"pvp_act_{battle_id}_domain"),
                     InlineKeyboardButton(text="🏃 Run", callback_data=f"pvp_act_{battle_id}_run")]
                ])
                caption = (
                    f"⚔️ **PVP BATTLE**\n"
                    f"━━━━━━━━━━━━━━━━━━━\n"
                    f"🧙 {attacker['character_name']}\n"
                    f"❤️ HP: {attack_hp}/{attacker['max_hp']}\n"
                    f"━━━━━━━━━━━━━━━━━━━\n"
                    f"🧙 {defender['character_name']}\n"
                    f"❤️ HP: {defend_hp_new}/{defender['max_hp']}\n"
                    f"━━━━━━━━━━━━━━━━━━━\n"
                    f"{resp}\n"
                    f"It's now {defender['character_name']}'s turn!"
                )
                await callback.message.edit_text(caption, reply_markup=keyboard)
                await callback.answer("Turn swapped!")
            else:
                await callback.answer("Other actions coming soon!", show_alert=True)
    except Exception as e:
        await callback.answer(f"PVP error: {e}", show_alert=True)

# ============================================================
# MISSIONS (unchanged)
# ============================================================
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
                await conn.execute("UPDATE players SET yen = yen + $1, xp = xp + $2 WHERE user_id = $3",
                                   m['reward_yen'], m['reward_xp'], user_id)
            await message.reply("✅ Daily missions claimed! Check your Yen and XP.")
    except Exception as e:
        await message.reply(f"Error: {e}")

# ============================================================
# OWNER INFO & BUY YEN
# ============================================================
async def send_owner_info(message: types.Message):
    await message.reply(
        f"👑 **Owner & Developer**\n"
        f"━━━━━━━━━━━━━━━━━━━\n"
        f"Name: {OWNER_NAME}\n"
        f"ID: {ADMIN_IDS[0]}\n"
        f"━━━━━━━━━━━━━━━━━━━\n"
        f"💰 **Purchase Yen**\n"
        f"Contact {OWNER_NAME} directly to buy Yen.\n"
        f"Current rates and promotions upon request."
    )

@dp.message(Command("buyyen"))
async def buyyen_cmd(message: types.Message):
    await send_owner_info(message)

# ============================================================
# COMMANDS
# ============================================================
@dp.message(Command("commands"))
async def commands_cmd(message: types.Message):
    await message.reply(
        f"📋 **Cursed Chronicles — Command List**\n"
        f"━━━━━━━━━━━━━━━━━━━\n"
        f"**General**\n"
        f"/start - Main menu\n"
        f"/profile - View your Cursed Chronicle\n"
        f"/guide - Game guide\n"
        f"/commands - This list\n"
        f"/buyyen - Contact owner to purchase Yen\n"
        f"━━━━━━━━━━━━━━━━━━━\n"
        f"**Characters**\n"
        f"/characters - Browse, buy, and select\n"
        f"/select \"name\" - Quick select (must own)\n"
        f"━━━━━━━━━━━━━━━━━━━\n"
        f"**Battle**\n"
        f"/battle - Fight a curse (slot‑based queue)\n"
        f"/boss \"name\" - Fight a boss\n"
        f"/enemies - Enemy list\n"
        f"/pvp @user - Challenge a player\n"
        f"━━━━━━━━━━━━━━━━━━━\n"
        f"**Shop & Inventory**\n"
        f"/shop - View items\n"
        f"/buy \"item\" - Purchase\n"
        f"/bag - Your items\n"
        f"/use \"item\" - Use consumable\n"
        f"/equip \"weapon\" - Equip\n"
        f"/techniques - Your techniques\n"
        f"/learn \"tech\" - Use technique (already owned)\n"
        f"━━━━━━━━━━━━━━━━━━━\n"
        f"**Missions**\n"
        f"/missions - View all missions\n"
        f"/daily - Claim daily rewards\n"
        f"━━━━━━━━━━━━━━━━━━━\n"
        f"**Owner Commands** (admin only)\n"
        f"/addyen, /removeyen, /addxp, /removexp, /setrank, /addlevel, /removelevel, /recalc"
    )

# ============================================================
# OWNER COMMANDS (Protected)
# ============================================================
@dp.message(Command("addyen"))
async def addyen_cmd(message: types.Message):
    if message.from_user.id not in ADMIN_IDS:
        await message.reply("❌ Owner only!")
        return
    args = message.text.split()
    if len(args) < 3:
        await message.reply("Usage: /addyen @user amount")
        return
    target = args[1].replace("@", "")
    amount = int(args[2])
    try:
        async with db_pool.acquire() as conn:
            res = await conn.execute("UPDATE players SET yen = yen + $1 WHERE username ILIKE $2", amount, target)
            if res == "UPDATE 0":
                await message.reply(f"User '{target}' not found.")
            else:
                await message.reply(f"✅ Added ¥{amount:,} to {target}.")
    except Exception as e:
        await message.reply(f"Error: {e}")

@dp.message(Command("removeyen"))
async def removeyen_cmd(message: types.Message):
    if message.from_user.id not in ADMIN_IDS:
        await message.reply("❌ Owner only!")
        return
    args = message.text.split()
    if len(args) < 3:
        await message.reply("Usage: /removeyen @user amount")
        return
    target = args[1].replace("@", "")
    amount = int(args[2])
    try:
        async with db_pool.acquire() as conn:
            res = await conn.execute("UPDATE players SET yen = yen - $1 WHERE username ILIKE $2 AND yen >= $1", amount, target)
            if res == "UPDATE 0":
                await message.reply(f"User not found or insufficient yen.")
            else:
                await message.reply(f"✅ Removed ¥{amount:,} from {target}.")
    except Exception as e:
        await message.reply(f"Error: {e}")

@dp.message(Command("addxp"))
async def addxp_cmd(message: types.Message):
    if message.from_user.id not in ADMIN_IDS:
        await message.reply("❌ Owner only!")
        return
    args = message.text.split()
    if len(args) < 3:
        await message.reply("Usage: /addxp @user amount")
        return
    target = args[1].replace("@", "")
    amount = int(args[2])
    try:
        async with db_pool.acquire() as conn:
            player = await conn.fetchrow("SELECT * FROM players WHERE username ILIKE $1", target)
            if not player:
                await message.reply(f"User '{target}' not found.")
                return
            new_xp = player['xp'] + amount
            new_level = calc_level(new_xp)
            new_rank = calc_rank(new_level, player['wins'])
            await conn.execute("UPDATE players SET xp = $1, level = $2, rank = $3 WHERE username ILIKE $4",
                               new_xp, new_level, new_rank, target)
            await message.reply(f"✅ Added {amount} XP to {target}. Level {new_level}, Rank {new_rank}.")
    except Exception as e:
        await message.reply(f"Error: {e}")

@dp.message(Command("removexp"))
async def removexp_cmd(message: types.Message):
    if message.from_user.id not in ADMIN_IDS:
        await message.reply("❌ Owner only!")
        return
    args = message.text.split()
    if len(args) < 3:
        await message.reply("Usage: /removexp @user amount")
        return
    target = args[1].replace("@", "")
    amount = int(args[2])
    try:
        async with db_pool.acquire() as conn:
            player = await conn.fetchrow("SELECT * FROM players WHERE username ILIKE $1", target)
            if not player:
                await message.reply(f"User '{target}' not found.")
                return
            new_xp = max(0, player['xp'] - amount)
            new_level = calc_level(new_xp)
            new_rank = calc_rank(new_level, player['wins'])
            await conn.execute("UPDATE players SET xp = $1, level = $2, rank = $3 WHERE username ILIKE $4",
                               new_xp, new_level, new_rank, target)
            await message.reply(f"✅ Removed {amount} XP from {target}. Level {new_level}, Rank {new_rank}.")
    except Exception as e:
        await message.reply(f"Error: {e}")

@dp.message(Command("setrank"))
async def setrank_cmd(message: types.Message):
    if message.from_user.id not in ADMIN_IDS:
        await message.reply("❌ Owner only!")
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
    if message.from_user.id not in ADMIN_IDS:
        await message.reply("❌ Owner only!")
        return
    args = message.text.split()
    if len(args) < 3:
        await message.reply("Usage: /addlevel @user amount")
        return
    target = args[1].replace("@", "")
    amount = int(args[2])
    try:
        async with db_pool.acquire() as conn:
            player = await conn.fetchrow("SELECT * FROM players WHERE username ILIKE $1", target)
            if not player:
                await message.reply(f"User '{target}' not found.")
                return
            new_level = player['level'] + amount
            new_rank = calc_rank(new_level, player['wins'])
            await conn.execute("UPDATE players SET level = $1, rank = $2 WHERE username ILIKE $3",
                               new_level, new_rank, target)
            await message.reply(f"✅ Added {amount} levels to {target}. New Level {new_level}, Rank {new_rank}.")
    except Exception as e:
        await message.reply(f"Error: {e}")

@dp.message(Command("removelevel"))
async def removelevel_cmd(message: types.Message):
    if message.from_user.id not in ADMIN_IDS:
        await message.reply("❌ Owner only!")
        return
    args = message.text.split()
    if len(args) < 3:
        await message.reply("Usage: /removelevel @user amount")
        return
    target = args[1].replace("@", "")
    amount = int(args[2])
    try:
        async with db_pool.acquire() as conn:
            player = await conn.fetchrow("SELECT * FROM players WHERE username ILIKE $1", target)
            if not player:
                await message.reply(f"User '{target}' not found.")
                return
            new_level = max(1, player['level'] - amount)
            new_rank = calc_rank(new_level, player['wins'])
            await conn.execute("UPDATE players SET level = $1, rank = $2 WHERE username ILIKE $3",
                               new_level, new_rank, target)
            await message.reply(f"✅ Removed {amount} levels from {target}. New Level {new_level}, Rank {new_rank}.")
    except Exception as e:
        await message.reply(f"Error: {e}")

@dp.message(Command("recalc"))
async def recalc_cmd(message: types.Message):
    if message.from_user.id not in ADMIN_IDS:
        await message.reply("❌ Owner only!")
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
                new_level = calc_level(player['xp'])
                new_rank = calc_rank(new_level, player['wins'])
                await conn.execute("UPDATE players SET level = $1, rank = $2 WHERE username ILIKE $3",
                                   new_level, new_rank, target)
                await message.reply(f"✅ Recalculated {target}: Level {new_level}, Rank {new_rank}.")
            else:
                players = await conn.fetch("SELECT * FROM players")
                count = 0
                for p in players:
                    nl = calc_level(p['xp'])
                    nr = calc_rank(nl, p['wins'])
                    await conn.execute("UPDATE players SET level = $1, rank = $2 WHERE user_id = $3",
                                       nl, nr, p['user_id'])
                    count += 1
                await message.reply(f"✅ Recalculated all {count} players.")
    except Exception as e:
        await message.reply(f"Error: {e}")

# ============================================================
# MAIN
# ============================================================
async def main():
    await on_startup()
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
