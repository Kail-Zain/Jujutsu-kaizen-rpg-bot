import asyncio
import os
import random
import json
from datetime import datetime, timedelta
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
ADMIN_IDS = [8609946980]  # Owner ID
OWNER_NAME = "𝕄𝕒𝕩𝕨𝕖𝕝𝕝-𝟜𝟟"
YEN_PURCHASE_INFO = f"💰 **Buy Yen** — Contact {OWNER_NAME} directly to purchase Yen."

# ============================================================
# EFFECT ASSETS (All URLs – NO PLACEHOLDERS)
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

# ============================================================
# DATABASE CONNECTION
# ============================================================
async def on_startup():
    global db_pool
    db_pool = await asyncpg.create_pool(DATABASE_URL)
    print("✅ Database connected!")

async def on_shutdown():
    await db_pool.close()
    print("✅ Database closed!")

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
    if not eff_str:
        return out
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
    if ratio >= 0.75:
        prefix = "🟢"
    elif ratio >= 0.4:
        prefix = "🟡"
    else:
        prefix = "🔴"
    return f"{prefix} {bar}"

def build_ce_bar(current, max_ce, length=12):
    if max_ce <= 0: max_ce = 1
    ratio = current / max_ce
    ratio = max(0, min(1, ratio))
    filled = int(ratio * length)
    empty = length - filled
    bar = "█" * filled + "░" * empty
    if ratio >= 0.7:
        prefix = "🔵"
    elif ratio >= 0.3:
        prefix = "🟣"
    else:
        prefix = "⚪"
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

# ============================================================
# COMMANDS
# ============================================================

# ----- START -----
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

# ----- WELCOME CALLBACK -----
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

# ----- PROFILE -----
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
                if char:
                    image_url = char['image_url']

            weapon = player.get('equipped_weapon') or "None"
            title = player.get('equipped_title') or "None"
            awakening = player.get('awakening') or "None"
            clan_name = "None"
            if player.get('clan_id'):
                clan = await conn.fetchrow("SELECT name FROM clans WHERE id = $1", player['clan_id'])
                if clan:
                    clan_name = clan['name']

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

# ----- CHARACTERS (Pagination) -----
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
            if offset >= total:
                offset = 0
            char = await conn.fetchrow("SELECT * FROM characters ORDER BY id LIMIT 1 OFFSET $1", offset)
            if not char:
                return

            caption = (
                f"🎭 **{char['name']}** - {char['rank']}\n"
                f"━━━━━━━━━━━━━━━━━━━\n"
                f"⚔️ ATK: {char['atk']} | 🛡️ DEF: {char['def']} | 💨 SPD: {char['spd']}\n"
                f"❤️ HP: {char['hp']} | 🔵 CE: {char['ce']}\n"
                f"💰 Price: ¥{char['price']:,}\n"
                f"━━━━━━━━━━━━━━━━━━━\n"
                f"Page {page+1}/{ (total + per_page -1)//per_page }\n"
                f"Select with /select \"{char['name']}\""
            )

            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="⬅️", callback_data=f"char_page_{page-1}"),
                 InlineKeyboardButton(text=f"{page+1}", callback_data="char_page_noop"),
                 InlineKeyboardButton(text="➡️", callback_data=f"char_page_{page+1}")],
                [InlineKeyboardButton(text=f"✅ Select {char['name']}", callback_data=f"char_select_{char['id']}")]
            ])

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

# ----- SELECT -----
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

# ----- SHOP (PAGINATED) -----
@dp.message(Command("shop"))
async def shop_cmd(message: types.Message):
    args = message.text.split()
    page = 1
    if len(args) > 1:
        try:
            page = int(args[1])
        except:
            page = 1
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
                    eff_desc = it['effect'].replace('|', ' | ')
                    response += f"    ✨ {eff_desc}\n"
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

# ----- BUY -----
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

            # Store in appropriate array
            if item['category'] == 'technique':
                await conn.execute("UPDATE players SET techniques = array_append(techniques, $1) WHERE user_id = $2",
                                   item['name'], user_id)
            elif item['category'] == 'domain':
                await conn.execute("UPDATE players SET domains = array_append(domains, $1) WHERE user_id = $2",
                                   item['name'], user_id)
            else:
                await conn.execute("UPDATE players SET bag = array_append(bag, $1) WHERE user_id = $2",
                                   item['name'], user_id)

            await message.reply(
                f"✅ Bought **{item['name']}**!\n"
                f"💰 Remaining: ¥{player['yen'] - item['price']:,}\n"
                f"📦 Check /bag or /techniques"
            )
    except Exception as e:
        await message.reply(f"Error: {e}")

# ----- BAG -----
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
                for it in bag[:20]:
                    resp += f"  • {it}\n"
                if len(bag) > 20:
                    resp += f"  ... and {len(bag)-20} more\n"
            if techniques:
                resp += "\n🌀 **Techniques:**\n"
                for t in techniques[:20]:
                    resp += f"  • {t}\n"
                if len(techniques) > 20:
                    resp += f"  ... and {len(techniques)-20} more\n"
            if domains:
                resp += "\n🌐 **Domains:**\n"
                for d in domains[:10]:
                    resp += f"  • {d}\n"
                if len(domains) > 10:
                    resp += f"  ... and {len(domains)-10} more\n"
            resp += "\n━━━━━━━━━━━━━━━━━━━\n"
            resp += "Use: /use \"item name\"\n"
            resp += "Equip weapon: /equip \"weapon name\"\n"
            resp += "Learn technique: /learn \"tech name\""
            await message.reply(resp)
    except Exception as e:
        await message.reply(f"Error: {e}")

# ----- USE -----
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

# ----- EQUIP -----
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

# ----- LEARN -----
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
            # Check if tech exists in techniques table or shop_items
            tech = await conn.fetchrow("SELECT * FROM techniques WHERE name ILIKE $1", tech_name)
            if not tech:
                # maybe it's a shop item of category technique
                shop_tech = await conn.fetchrow("SELECT * FROM shop_items WHERE name ILIKE $1 AND category = 'technique'", tech_name)
                if not shop_tech:
                    await message.reply(f"Technique '{tech_name}' not found.")
                    return
                # If it's in shop, we allow learning if bought? Actually we track via techniques array.
                # So we assume they already bought it and it's in their techniques array.
                # We'll check if they have it in techniques array.
            techniques = player.get('techniques') or []
            if tech_name in techniques:
                await message.reply(f"🌀 You already know **{tech_name}**!")
                return
            # Add to techniques array
            await conn.execute("UPDATE players SET techniques = array_append(techniques, $1) WHERE user_id = $2",
                               tech_name, user_id)
            # Fetch description from techniques table if exists
            desc = tech['description'] if tech else "Powerful cursed technique."
            dmg_mult = tech['damage_multiplier'] if tech else 2.0
            ce_cost = tech['ce_cost'] if tech else 30
            await message.reply_animation(
                animation=EFFECTS["cursed_energy"],
                caption=(
                    f"🌀 Learned **{tech_name}**!\n"
                    f"📖 {desc}\n"
                    f"⚡ DMG: {dmg_mult}x | CE Cost: {ce_cost}\n"
                    f"Use it in battle via the 'Technique' button."
                )
            )
    except Exception as e:
        await message.reply(f"Error: {e}")

# ----- TECHNIQUES LIST -----
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
                await message.reply("🌀 You haven't learned any techniques yet. Buy from /shop and /learn.")
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

# ----- ENEMIES -----
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
# BATTLE SYSTEM (with technique menu)
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

            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="⚔️ Attack", callback_data=f"battle_act_{battle_id}_attack"),
                 InlineKeyboardButton(text="🛡️ Defend", callback_data=f"battle_act_{battle_id}_defend")],
                [InlineKeyboardButton(text="💥 Special", callback_data=f"battle_act_{battle_id}_special"),
                 InlineKeyboardButton(text="🌀 Technique", callback_data=f"battle_act_{battle_id}_technique")],
                [InlineKeyboardButton(text="🌐 Domain", callback_data=f"battle_act_{battle_id}_domain"),
                 InlineKeyboardButton(text="🏃 Run", callback_data=f"battle_act_{battle_id}_run")]
            ])

            char_name = player.get('character_name') or "You"
            hp_bar = build_hp_bar(player['hp'], player['max_hp'])
            ce_bar = build_ce_bar(player['ce'], player['max_ce'])
            enemy_hp_bar = build_hp_bar(enemy['hp'], enemy['hp'])

            caption = (
                f"⚔️ **BATTLE START!**\n"
                f"━━━━━━━━━━━━━━━━━━━\n"
                f"🧙 {char_name}\n"
                f"❤️ HP: {player['hp']}/{player['max_hp']} {hp_bar}\n"
                f"🔵 CE: {player['ce']}/{player['max_ce']} {ce_bar}\n"
                f"━━━━━━━━━━━━━━━━━━━\n"
                f"💀 **{enemy['name']}** - {enemy['rank']}\n"
                f"❤️ HP: {enemy['hp']} {enemy_hp_bar}\n"
                f"━━━━━━━━━━━━━━━━━━━\n"
                f"Choose your action:"
            )

            if enemy.get('image_url'):
                await message.reply_photo(photo=enemy['image_url'], caption=caption, reply_markup=keyboard)
            else:
                await message.reply(caption, reply_markup=keyboard)

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

            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="⚔️ Attack", callback_data=f"battle_act_{battle_id}_attack"),
                 InlineKeyboardButton(text="🛡️ Defend", callback_data=f"battle_act_{battle_id}_defend")],
                [InlineKeyboardButton(text="💥 Special", callback_data=f"battle_act_{battle_id}_special"),
                 InlineKeyboardButton(text="🌀 Technique", callback_data=f"battle_act_{battle_id}_technique")],
                [InlineKeyboardButton(text="🌐 Domain", callback_data=f"battle_act_{battle_id}_domain"),
                 InlineKeyboardButton(text="🏃 Run", callback_data=f"battle_act_{battle_id}_run")]
            ])

            char_name = player.get('character_name') or "You"
            hp_bar = build_hp_bar(player['hp'], player['max_hp'])
            ce_bar = build_ce_bar(player['ce'], player['max_ce'])
            enemy_hp_bar = build_hp_bar(enemy['hp'], enemy['hp'])

            caption = (
                f"👑 **BOSS BATTLE!**\n"
                f"━━━━━━━━━━━━━━━━━━━\n"
                f"🧙 {char_name}\n"
                f"❤️ HP: {player['hp']}/{player['max_hp']} {hp_bar}\n"
                f"🔵 CE: {player['ce']}/{player['max_ce']} {ce_bar}\n"
                f"━━━━━━━━━━━━━━━━━━━\n"
                f"👑 **{enemy['name']}** - {enemy['rank']}\n"
                f"❤️ HP: {enemy['hp']} {enemy_hp_bar}\n"
                f"━━━━━━━━━━━━━━━━━━━\n"
                f"Choose your action:"
            )
            if enemy.get('image_url'):
                await message.reply_photo(photo=enemy['image_url'], caption=caption, reply_markup=keyboard)
            else:
                await message.reply(caption, reply_markup=keyboard)
    except Exception as e:
        await message.reply(f"Error: {e}")

# BATTLE ACTIONS CALLBACK (full with technique selection)
@dp.callback_query(lambda c: c.data.startswith("battle_act_"))
async def battle_action_cb(callback: types.CallbackQuery):
    await callback.answer("⚡ Calculating...", cache_time=0)
    parts = callback.data.split("_")
    battle_id = int(parts[2])
    action = parts[3]

    try:
        async with db_pool.acquire() as conn:
            battle = await conn.fetchrow("SELECT * FROM battles WHERE id = $1", battle_id)
            if not battle:
                await callback.answer("Battle expired!", show_alert=True)
                return

            player = await conn.fetchrow("SELECT * FROM players WHERE user_id = $1", battle['player1_id'])
            if not player:
                await callback.answer("Player not found!", show_alert=True)
                return

            enemy_hp = battle['current_hp2']
            enemy_name = battle['enemy_name']
            enemy_rank = battle['enemy_rank']
            enemy_atk = battle['enemy_atk']
            enemy_def = battle['enemy_def']
            enemy_max_hp = battle.get('enemy_max_hp', 100)

            player_hp = battle['current_hp1']
            player_max_hp = player['max_hp']
            player_ce = player['ce']
            player_max_ce = player['max_ce']
            player_atk = player['atk']
            player_def = player['def']

            resp = ""
            keyboard = None

            # ACTION HANDLING
            if action == "attack":
                dmg = max(1, int(player_atk * random.uniform(0.8, 1.2)))
                enemy_hp_new = max(0, enemy_hp - dmg)
                await conn.execute("UPDATE battles SET current_hp2 = $1 WHERE id = $2", enemy_hp_new, battle_id)

                enemy_dmg = max(1, int(enemy_atk * random.uniform(0.5, 0.9)))
                player_hp_new = max(0, player_hp - enemy_dmg)
                await conn.execute("UPDATE battles SET current_hp1 = $1 WHERE id = $2", player_hp_new, battle_id)

                # Black Flash check
                if random.random() < 0.01:
                    dmg = int(dmg * 2.5)
                    enemy_hp_new = max(0, enemy_hp - dmg)
                    await conn.execute("UPDATE battles SET current_hp2 = $1 WHERE id = $2", enemy_hp_new, battle_id)
                    await conn.execute("UPDATE players SET black_flash_count = black_flash_count + 1 WHERE user_id = $1", player['user_id'])
                    await callback.message.reply_animation(animation=EFFECTS["black_flash"])
                    resp = f"⚡ **BLACK FLASH!**\n━━━━━━━━━━━━━━━━━━━\n💥 Dealt {dmg} damage! (Critical)\n💀 {enemy_name} HP: {enemy_hp_new}\n━━━━━━━━━━━━━━━━━━━\n"
                else:
                    resp = f"⚔️ **You Attack!**\n━━━━━━━━━━━━━━━━━━━\n💥 Dealt {dmg} damage!\n💀 {enemy_name} HP: {enemy_hp_new}\n━━━━━━━━━━━━━━━━━━━\n💢 Enemy counter-attacked!\n❤️ Your HP: {player_hp_new}\n━━━━━━━━━━━━━━━━━━━\n"

                if enemy_hp_new <= 0:
                    await conn.execute("""
                        UPDATE players SET yen = yen + $1, wins = wins + 1, xp = xp + $2, boss_kills = boss_kills + $3
                        WHERE user_id = $4
                    """, battle['enemy_reward_yen'] or 1000, battle['enemy_reward_xp'] or 100,
                      1 if battle['is_boss'] else 0, player['user_id'])
                    await callback.message.reply_animation(animation=EFFECTS["defeat"])
                    await callback.message.edit_text(
                        f"🎉 **VICTORY!**\n"
                        f"━━━━━━━━━━━━━━━━━━━\n"
                        f"You defeated **{enemy_name}**!\n"
                        f"💰 +¥{battle['enemy_reward_yen'] or 1000}\n"
                        f"⭐ +{battle['enemy_reward_xp'] or 100} XP"
                    )
                    await callback.answer("Victory! 🎉")
                    return
                if player_hp_new <= 0:
                    await conn.execute("UPDATE players SET losses = losses + 1 WHERE user_id = $1", player['user_id'])
                    await callback.message.reply_animation(animation=EFFECTS["defeat"])
                    await callback.message.edit_text(
                        f"💀 **DEFEAT!**\n"
                        f"━━━━━━━━━━━━━━━━━━━\n"
                        f"You were defeated by **{enemy_name}**!\n"
                        f"Train harder and try again."
                    )
                    await callback.answer("Defeated! 💀")
                    return

            elif action == "defend":
                enemy_dmg = max(1, int(enemy_atk * random.uniform(0.2, 0.4)))
                player_hp_new = max(0, player_hp - enemy_dmg)
                await conn.execute("UPDATE battles SET current_hp1 = $1 WHERE id = $2", player_hp_new, battle_id)
                resp = f"🛡️ **You Defend!**\n━━━━━━━━━━━━━━━━━━━\n💢 Enemy dealt reduced damage: {enemy_dmg}\n❤️ Your HP: {player_hp_new}\n━━━━━━━━━━━━━━━━━━━\n"
                if player_hp_new <= 0:
                    await conn.execute("UPDATE players SET losses = losses + 1 WHERE user_id = $1", player['user_id'])
                    await callback.message.reply_animation(animation=EFFECTS["defeat"])
                    await callback.message.edit_text(
                        f"💀 **DEFEAT!**\n"
                        f"━━━━━━━━━━━━━━━━━━━\n"
                        f"You were defeated by **{enemy_name}**!"
                    )
                    await callback.answer("Defeated! 💀")
                    return

            elif action == "special":
                if player_ce < 30:
                    await callback.answer("Not enough CE! (Need 30)", show_alert=True)
                    return
                await conn.execute("UPDATE players SET ce = ce - 30 WHERE user_id = $1", player['user_id'])
                dmg = max(1, int(player_atk * random.uniform(1.5, 2.5)))
                enemy_hp_new = max(0, enemy_hp - dmg)
                await conn.execute("UPDATE battles SET current_hp2 = $1 WHERE id = $2", enemy_hp_new, battle_id)
                enemy_dmg = max(1, int(enemy_atk * random.uniform(0.6, 1.0)))
                player_hp_new = max(0, player_hp - enemy_dmg)
                await conn.execute("UPDATE battles SET current_hp1 = $1 WHERE id = $2", player_hp_new, battle_id)
                await callback.message.reply_animation(animation=EFFECTS["cursed_energy"])
                resp = f"💥 **Special Attack!**\n━━━━━━━━━━━━━━━━━━━\n🔥 Dealt {dmg} damage!\n💀 {enemy_name} HP: {enemy_hp_new}\n━━━━━━━━━━━━━━━━━━━\n💢 Enemy attacked!\n❤️ Your HP: {player_hp_new}\n"
                if enemy_hp_new <= 0:
                    await conn.execute("""
                        UPDATE players SET yen = yen + $1, wins = wins + 1, xp = xp + $2, boss_kills = boss_kills + $3
                        WHERE user_id = $4
                    """, battle['enemy_reward_yen'] or 1000, battle['enemy_reward_xp'] or 100,
                      1 if battle['is_boss'] else 0, player['user_id'])
                    await callback.message.reply_animation(animation=EFFECTS["defeat"])
                    await callback.message.edit_text(f"🎉 **VICTORY!** You defeated {enemy_name}!")
                    await callback.answer("Victory! 🎉")
                    return
                if player_hp_new <= 0:
                    await conn.execute("UPDATE players SET losses = losses + 1 WHERE user_id = $1", player['user_id'])
                    await callback.message.reply_animation(animation=EFFECTS["defeat"])
                    await callback.message.edit_text(f"💀 **DEFEAT!**")
                    await callback.answer("Defeated! 💀")
                    return

            elif action == "technique":
                # Show technique selection menu
                techniques = player.get('techniques') or []
                if not techniques:
                    await callback.answer("You haven't learned any techniques! Buy and /learn first.", show_alert=True)
                    return
                # Build inline keyboard with techniques
                tech_buttons = []
                for tech in techniques[:8]:  # limit to 8
                    tech_buttons.append([InlineKeyboardButton(text=tech, callback_data=f"battle_tech_{battle_id}_{tech}")])
                tech_buttons.append([InlineKeyboardButton(text="🔙 Back", callback_data=f"battle_back_{battle_id}")])
                tech_kb = InlineKeyboardMarkup(inline_keyboard=tech_buttons)
                await callback.message.edit_text(
                    f"🌀 **Choose a Technique:**\n"
                    f"━━━━━━━━━━━━━━━━━━━\n"
                    f"Select one to use against {enemy_name}.\n"
                    f"Each technique costs CE.",
                    reply_markup=tech_kb
                )
                await callback.answer()
                return

            elif action == "domain":
                domains = player.get('domains') or []
                if not domains:
                    await callback.answer("You don't own any Domain! Buy one from /shop.", show_alert=True)
                    return
                domain_name = domains[0]  # For simplicity, use first domain
                domain = await conn.fetchrow("SELECT * FROM techniques WHERE name = $1 AND category = 'domain'", domain_name)
                if not domain:
                    # fallback: maybe it's a shop item
                    domain_item = await conn.fetchrow("SELECT * FROM shop_items WHERE name = $1 AND category = 'domain'", domain_name)
                    if not domain_item:
                        await callback.answer("Domain data error.", show_alert=True)
                        return
                    ce_cost = int(parse_effect(domain_item['effect']).get('ce_cost', 100))
                    dmg_mult = float(parse_effect(domain_item['effect']).get('damage', 3.5))
                else:
                    ce_cost = domain['ce_cost']
                    dmg_mult = domain['damage_multiplier']

                if player_ce < ce_cost:
                    await callback.answer(f"Not enough CE! Need {ce_cost}", show_alert=True)
                    return
                await conn.execute("UPDATE players SET ce = ce - $1 WHERE user_id = $2", ce_cost, player['user_id'])
                dmg = max(1, int(player_atk * dmg_mult * random.uniform(0.9, 1.1)))
                enemy_hp_new = max(0, enemy_hp - dmg)
                await conn.execute("UPDATE battles SET current_hp2 = $1 WHERE id = $2", enemy_hp_new, battle_id)
                # Domain animation
                if "Unlimited Void" in domain_name:
                    await callback.message.reply_animation(animation=EFFECTS["gojo_unlimited_void"])
                elif "Malevolent" in domain_name:
                    await callback.message.reply_animation(animation=EFFECTS["sukuna_domain"])
                elif "Mahito" in domain_name or "Self" in domain_name:
                    await callback.message.reply_animation(animation=EFFECTS["mahito_domain"])
                else:
                    await callback.message.reply_animation(animation=EFFECTS["default_domain"])

                enemy_dmg = max(1, int(enemy_atk * random.uniform(0.5, 0.9)))
                player_hp_new = max(0, player_hp - enemy_dmg)
                await conn.execute("UPDATE battles SET current_hp1 = $1 WHERE id = $2", player_hp_new, battle_id)

                resp = f"🌐 **Domain Expansion: {domain_name}**!\n━━━━━━━━━━━━━━━━━━━\n🔥 Dealt {dmg} damage!\n💀 {enemy_name} HP: {enemy_hp_new}\n━━━━━━━━━━━━━━━━━━━\n💢 Enemy attacked!\n❤️ Your HP: {player_hp_new}\n"
                if enemy_hp_new <= 0:
                    await conn.execute("""
                        UPDATE players SET yen = yen + $1, wins = wins + 1, xp = xp + $2, boss_kills = boss_kills + $3
                        WHERE user_id = $4
                    """, battle['enemy_reward_yen'] or 1000, battle['enemy_reward_xp'] or 100,
                      1 if battle['is_boss'] else 0, player['user_id'])
                    await callback.message.reply_animation(animation=EFFECTS["defeat"])
                    await callback.message.edit_text(f"🎉 **VICTORY!** You obliterated {enemy_name} with your domain!")
                    await callback.answer("Victory! 🎉")
                    return
                if player_hp_new <= 0:
                    await conn.execute("UPDATE players SET losses = losses + 1 WHERE user_id = $1", player['user_id'])
                    await callback.message.reply_animation(animation=EFFECTS["defeat"])
                    await callback.message.edit_text(f"💀 **DEFEAT!**")
                    await callback.answer("Defeated! 💀")
                    return

            elif action == "run":
                if random.random() < 0.6:
                    await callback.message.edit_text("🏃 You successfully escaped!")
                    await callback.answer("Escaped! 🏃")
                    return
                else:
                    enemy_dmg = max(1, int(enemy_atk * random.uniform(0.8, 1.2)))
                    player_hp_new = max(0, player_hp - enemy_dmg)
                    await conn.execute("UPDATE battles SET current_hp1 = $1 WHERE id = $2", player_hp_new, battle_id)
                    resp = f"🏃 Failed to escape!\n💢 Enemy dealt {enemy_dmg} damage!\n❤️ Your HP: {player_hp_new}\n"
                    if player_hp_new <= 0:
                        await conn.execute("UPDATE players SET losses = losses + 1 WHERE user_id = $1", player['user_id'])
                        await callback.message.reply_animation(animation=EFFECTS["defeat"])
                        await callback.message.edit_text(f"💀 **DEFEAT!**")
                        await callback.answer("Defeated! 💀")
                        return

            # If we reach here, battle continues
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="⚔️ Attack", callback_data=f"battle_act_{battle_id}_attack"),
                 InlineKeyboardButton(text="🛡️ Defend", callback_data=f"battle_act_{battle_id}_defend")],
                [InlineKeyboardButton(text="💥 Special", callback_data=f"battle_act_{battle_id}_special"),
                 InlineKeyboardButton(text="🌀 Technique", callback_data=f"battle_act_{battle_id}_technique")],
                [InlineKeyboardButton(text="🌐 Domain", callback_data=f"battle_act_{battle_id}_domain"),
                 InlineKeyboardButton(text="🏃 Run", callback_data=f"battle_act_{battle_id}_run")]
            ])

            hp_bar_player = build_hp_bar(player_hp_new, player_max_hp)
            ce_bar_player = build_ce_bar(player_ce, player_max_ce)
            hp_bar_enemy = build_hp_bar(enemy_hp_new, enemy_max_hp)

            final_text = (
                f"⚔️ **BATTLE**\n"
                f"━━━━━━━━━━━━━━━━━━━\n"
                f"🧙 {player.get('character_name') or 'You'}\n"
                f"❤️ HP: {player_hp_new}/{player_max_hp} {hp_bar_player}\n"
                f"🔵 CE: {player_ce}/{player_max_ce} {ce_bar_player}\n"
                f"━━━━━━━━━━━━━━━━━━━\n"
                f"💀 **{enemy_name}** - {enemy_rank}\n"
                f"❤️ HP: {enemy_hp_new} {hp_bar_enemy}\n"
                f"━━━━━━━━━━━━━━━━━━━\n"
                f"{resp}\n"
                f"Choose your action:"
            )

            await callback.message.edit_text(final_text, reply_markup=keyboard)
            await callback.answer("⚡ Action complete!")

    except Exception as e:
        await callback.answer(f"Battle error: {e}", show_alert=True)
        print("Battle error:", e)

# HANDLE TECHNIQUE SELECTION IN BATTLE
@dp.callback_query(lambda c: c.data.startswith("battle_tech_"))
async def battle_tech_select(callback: types.CallbackQuery):
    parts = callback.data.split("_")
    battle_id = int(parts[2])
    tech_name = "_".join(parts[3:])  # handle spaces

    try:
        async with db_pool.acquire() as conn:
            battle = await conn.fetchrow("SELECT * FROM battles WHERE id = $1", battle_id)
            if not battle:
                await callback.answer("Battle expired!", show_alert=True)
                return
            player = await conn.fetchrow("SELECT * FROM players WHERE user_id = $1", battle['player1_id'])
            if not player:
                await callback.answer("Player not found!", show_alert=True)
                return

            # Get technique details
            tech = await conn.fetchrow("SELECT * FROM techniques WHERE name = $1", tech_name)
            if not tech:
                await callback.answer("Technique not found.", show_alert=True)
                return

            if player['ce'] < tech['ce_cost']:
                await callback.answer(f"Not enough CE! Need {tech['ce_cost']}", show_alert=True)
                return

            await conn.execute("UPDATE players SET ce = ce - $1 WHERE user_id = $2", tech['ce_cost'], player['user_id'])
            dmg = max(1, int(player['atk'] * tech['damage_multiplier'] * random.uniform(0.9, 1.1)))
            enemy_hp_new = max(0, battle['current_hp2'] - dmg)
            await conn.execute("UPDATE battles SET current_hp2 = $1 WHERE id = $2", enemy_hp_new, battle_id)

            # Enemy counter
            enemy_dmg = max(1, int(battle['enemy_atk'] * random.uniform(0.5, 0.9)))
            player_hp_new = max(0, battle['current_hp1'] - enemy_dmg)
            await conn.execute("UPDATE battles SET current_hp1 = $1 WHERE id = $2", player_hp_new, battle_id)

            # Effect animation based on tech name
            if "Purple" in tech_name:
                await callback.message.reply_animation(animation=EFFECTS["gojo_purple"])
            elif "Red" in tech_name:
                await callback.message.reply_animation(animation=EFFECTS["gojo_red"])
            elif "Blue" in tech_name:
                await callback.message.reply_animation(animation=EFFECTS["gojo_blue"])
            elif "Unlimited Void" in tech_name:
                await callback.message.reply_animation(animation=EFFECTS["gojo_unlimited_void"])
            elif "Malevolent" in tech_name:
                await callback.message.reply_animation(animation=EFFECTS["sukuna_domain"])
            else:
                await callback.message.reply_animation(animation=EFFECTS["cursed_energy"])

            # Check win/lose
            if enemy_hp_new <= 0:
                await conn.execute("""
                    UPDATE players SET yen = yen + $1, wins = wins + 1, xp = xp + $2, boss_kills = boss_kills + $3
                    WHERE user_id = $4
                """, battle['enemy_reward_yen'] or 1000, battle['enemy_reward_xp'] or 100,
                  1 if battle['is_boss'] else 0, player['user_id'])
                await callback.message.reply_animation(animation=EFFECTS["defeat"])
                await callback.message.edit_text(f"🎉 **VICTORY!** You defeated {battle['enemy_name']} with {tech_name}!")
                await callback.answer("Victory! 🎉")
                return
            if player_hp_new <= 0:
                await conn.execute("UPDATE players SET losses = losses + 1 WHERE user_id = $1", player['user_id'])
                await callback.message.reply_animation(animation=EFFECTS["defeat"])
                await callback.message.edit_text(f"💀 **DEFEAT!**")
                await callback.answer("Defeated! 💀")
                return

            # Continue battle
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="⚔️ Attack", callback_data=f"battle_act_{battle_id}_attack"),
                 InlineKeyboardButton(text="🛡️ Defend", callback_data=f"battle_act_{battle_id}_defend")],
                [InlineKeyboardButton(text="💥 Special", callback_data=f"battle_act_{battle_id}_special"),
                 InlineKeyboardButton(text="🌀 Technique", callback_data=f"battle_act_{battle_id}_technique")],
                [InlineKeyboardButton(text="🌐 Domain", callback_data=f"battle_act_{battle_id}_domain"),
                 InlineKeyboardButton(text="🏃 Run", callback_data=f"battle_act_{battle_id}_run")]
            ])

            hp_bar_player = build_hp_bar(player_hp_new, player['max_hp'])
            ce_bar_player = build_ce_bar(player['ce'], player['max_ce'])
            hp_bar_enemy = build_hp_bar(enemy_hp_new, battle['enemy_max_hp'])

            final_text = (
                f"⚔️ **BATTLE**\n"
                f"━━━━━━━━━━━━━━━━━━━\n"
                f"🧙 {player.get('character_name') or 'You'}\n"
                f"❤️ HP: {player_hp_new}/{player['max_hp']} {hp_bar_player}\n"
                f"🔵 CE: {player['ce']}/{player['max_ce']} {ce_bar_player}\n"
                f"━━━━━━━━━━━━━━━━━━━\n"
                f"💀 **{battle['enemy_name']}** - {battle['enemy_rank']}\n"
                f"❤️ HP: {enemy_hp_new} {hp_bar_enemy}\n"
                f"━━━━━━━━━━━━━━━━━━━\n"
                f"🌀 Used **{tech_name}**!\n"
                f"━━━━━━━━━━━━━━━━━━━\n"
                f"Choose your next action:"
            )
            await callback.message.edit_text(final_text, reply_markup=keyboard)
            await callback.answer("Technique used!")

    except Exception as e:
        await callback.answer(f"Error: {e}", show_alert=True)
        print("Tech error:", e)

# BACK from technique menu
@dp.callback_query(lambda c: c.data.startswith("battle_back_"))
async def battle_back_cb(callback: types.CallbackQuery):
    battle_id = int(callback.data.split("_")[2])
    await callback.answer("Returning to battle...")
    # Rebuild main battle keyboard
    try:
        async with db_pool.acquire() as conn:
            battle = await conn.fetchrow("SELECT * FROM battles WHERE id = $1", battle_id)
            if not battle:
                await callback.answer("Battle expired!", show_alert=True)
                return
            player = await conn.fetchrow("SELECT * FROM players WHERE user_id = $1", battle['player1_id'])
            if not player:
                await callback.answer("Player not found!", show_alert=True)
                return

            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="⚔️ Attack", callback_data=f"battle_act_{battle_id}_attack"),
                 InlineKeyboardButton(text="🛡️ Defend", callback_data=f"battle_act_{battle_id}_defend")],
                [InlineKeyboardButton(text="💥 Special", callback_data=f"battle_act_{battle_id}_special"),
                 InlineKeyboardButton(text="🌀 Technique", callback_data=f"battle_act_{battle_id}_technique")],
                [InlineKeyboardButton(text="🌐 Domain", callback_data=f"battle_act_{battle_id}_domain"),
                 InlineKeyboardButton(text="🏃 Run", callback_data=f"battle_act_{battle_id}_run")]
            ])

            hp_bar_player = build_hp_bar(battle['current_hp1'], player['max_hp'])
            ce_bar_player = build_ce_bar(player['ce'], player['max_ce'])
            hp_bar_enemy = build_hp_bar(battle['current_hp2'], battle['enemy_max_hp'])

            final_text = (
                f"⚔️ **BATTLE**\n"
                f"━━━━━━━━━━━━━━━━━━━\n"
                f"🧙 {player.get('character_name') or 'You'}\n"
                f"❤️ HP: {battle['current_hp1']}/{player['max_hp']} {hp_bar_player}\n"
                f"🔵 CE: {player['ce']}/{player['max_ce']} {ce_bar_player}\n"
                f"━━━━━━━━━━━━━━━━━━━\n"
                f"💀 **{battle['enemy_name']}** - {battle['enemy_rank']}\n"
                f"❤️ HP: {battle['current_hp2']} {hp_bar_enemy}\n"
                f"━━━━━━━━━━━━━━━━━━━\n"
                f"Choose your action:"
            )
            await callback.message.edit_text(final_text, reply_markup=keyboard)
    except Exception as e:
        await callback.answer(f"Error: {e}", show_alert=True)

# ============================================================
# PVP SYSTEM
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

            # Simple attack for now (expand later)
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
                next_player = defender
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
# MISSIONS SYSTEM
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

            # Get all missions
            missions = await conn.fetch("SELECT * FROM missions ORDER BY type, id")
            if not missions:
                await message.reply("No missions available.")
                return

            # Get player progress
            player_missions = await conn.fetch("SELECT * FROM player_missions WHERE player_id = $1", user_id)

            resp = "📋 **Your Missions**\n━━━━━━━━━━━━━━━━━━━\n"
            current_type = None
            for m in missions:
                if m['type'] != current_type:
                    current_type = m['type']
                    resp += f"\n📌 **{current_type.upper()}**\n"
                # Check if mission is completed
                pm = next((p for p in player_missions if p['mission_id'] == m['id']), None)
                if pm and pm['completed']:
                    status = "✅ Completed"
                elif pm:
                    progress = pm['progress']
                    req = m['requirement']
                    # parse requirement e.g., "win_battles:3"
                    req_parts = req.split(':')
                    if len(req_parts) == 2:
                        target = int(req_parts[1])
                        status = f"Progress: {progress}/{target}"
                    else:
                        status = "In Progress"
                else:
                    # Not started
                    req = m['requirement']
                    req_parts = req.split(':')
                    if len(req_parts) == 2:
                        status = f"0/{req_parts[1]}"
                    else:
                        status = "Not started"
                resp += f"  • **{m['name']}** - {m['description']}\n"
                resp += f"    Reward: ¥{m['reward_yen']:,} | ⭐ +{m['reward_xp']} XP\n"
                resp += f"    Status: {status}\n"
            resp += "\n━━━━━━━━━━━━━━━━━━━\n"
            resp += "Use /daily to claim daily rewards (auto-completes some missions)."
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

            # Check cooldown (daily reset)
            # For simplicity, we assume daily missions can be claimed once per day
            # We'll update player_missions to mark daily missions as completed.
            # We'll also give rewards based on missions that are completed.

            # Get all daily missions
            daily_missions = await conn.fetch("SELECT * FROM missions WHERE type = 'daily'")
            for m in daily_missions:
                # Check if player already completed this today (we'll allow daily claim once)
                pm = await conn.fetchrow("SELECT * FROM player_missions WHERE player_id = $1 AND mission_id = $2", user_id, m['id'])
                if pm and pm['completed']:
                    continue
                # Check if requirement met (for now, we auto-complete all dailies for testing)
                # In a real scenario, we would check progress against requirements.
                # We'll auto-complete for demonstration.
                if not pm:
                    # Insert with completed true
                    await conn.execute("""
                        INSERT INTO player_missions (player_id, mission_id, progress, completed, last_claimed)
                        VALUES ($1, $2, $3, TRUE, NOW())
                    """, user_id, m['id'], 0)
                else:
                    await conn.execute("UPDATE player_missions SET completed = TRUE, progress = 0 WHERE player_id = $1 AND mission_id = $2",
                                       user_id, m['id'])
                # Reward player
                await conn.execute("UPDATE players SET yen = yen + $1, xp = xp + $2 WHERE user_id = $3",
                                   m['reward_yen'], m['reward_xp'], user_id)

            await message.reply("✅ Daily missions claimed! Check your Yen and XP.")
    except Exception as e:
        await message.reply(f"Error: {e}")

# ============================================================
# OWNER INFO
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

# ============================================================
# COMMAND: /commands
# ============================================================
@dp.message(Command("commands"))
async def commands_cmd(message: types.Message):
    await message.reply(
        f"📋 **Cursed Chronicles — Command List**\n"
        f"━━━━━━━━━━━━━━━━━━━\n"
        f"**General**\n"
        f"/start - Main menu\n"
        f"/profile - View your Cursed Chronicle\n"
        f"/commands - This list\n"
        f"/buyyen - Contact owner to purchase Yen\n"
        f"━━━━━━━━━━━━━━━━━━━\n"
        f"**Characters**\n"
        f"/characters - Browse & select\n"
        f"/select \"name\" - Quick select\n"
        f"━━━━━━━━━━━━━━━━━━━\n"
        f"**Battle**\n"
        f"/battle - Fight a curse\n"
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
        f"/learn \"tech\" - Learn technique\n"
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
