import asyncio
import os
import random
import re
from datetime import datetime, timedelta
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
import asyncpg
from dotenv import load_dotenv

# ========================================
# LOAD ENVIRONMENT VARIABLES
# ========================================
load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
DATABASE_URL = os.getenv("DATABASE_URL")

if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN is not set!")
if not DATABASE_URL:
    raise ValueError("DATABASE_URL is not set!")

# ========================================
# OWNER / ADMIN ID
# ========================================
ADMIN_IDS = [8609946980]  # Your Telegram ID

# ========================================
# INITIALIZE BOT
# ========================================
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()
db_pool = None

# ========================================
# DATABASE CONNECTION
# ========================================
async def on_startup():
    global db_pool
    db_pool = await asyncpg.create_pool(DATABASE_URL)
    print("✅ Database connected!")

async def on_shutdown():
    await db_pool.close()
    print("✅ Database closed!")

# ========================================
# HELPER FUNCTIONS
# ========================================

def calculate_rank(level, wins):
    if level >= 50 and wins >= 100:
        return "Special Grade"
    elif level >= 30 and wins >= 50:
        return "Semi-Special"
    elif level >= 20 and wins >= 30:
        return "Grade 1"
    elif level >= 15 and wins >= 20:
        return "Grade 2"
    elif level >= 10 and wins >= 10:
        return "Grade 3"
    else:
        return "Grade 4"

def calculate_level(xp):
    return (xp // 100) + 1

def parse_effect(effect_str):
    effects = {}
    for part in effect_str.split('|'):
        if ':' in part:
            key, value = part.split(':')
            effects[key] = value
        else:
            effects[part] = True
    return effects

# ========================================
# COMMAND: /start (Welcome Menu)
# ========================================
@dp.message(Command("start"))
async def start_command(message: types.Message):
    user_id = message.from_user.id
    username = message.from_user.username or "Unknown"
    chat_id = message.chat.id
    
    try:
        async with db_pool.acquire() as conn:
            await conn.execute('''
                INSERT INTO players (user_id, username, chat_id)
                VALUES ($1, $2, $3)
                ON CONFLICT (user_id) DO UPDATE SET username = $2
            ''', user_id, username, chat_id)
    except Exception as e:
        print(f"Database error: {e}")
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🧙 Profile", callback_data="welcome_profile"),
            InlineKeyboardButton(text="⚔️ Battle", callback_data="welcome_battle")
        ],
        [
            InlineKeyboardButton(text="🎭 Characters", callback_data="welcome_characters"),
            InlineKeyboardButton(text="🏪 Shop", callback_data="welcome_shop")
        ],
        [
            InlineKeyboardButton(text="👹 Enemies", callback_data="welcome_enemies"),
            InlineKeyboardButton(text="📦 Bag", callback_data="welcome_bag")
        ],
        [
            InlineKeyboardButton(text="📋 Commands", callback_data="welcome_commands")
        ]
    ])
    
    try:
        async with db_pool.acquire() as conn:
            player = await conn.fetchrow(
                'SELECT * FROM players WHERE user_id = $1', user_id
            )
    except:
        player = None
    
    if player:
        char_name = player.get('character_name', 'No character selected')
        welcome_msg = (
            f"🧙 **Welcome back, {username}!**\n"
            f"━━━━━━━━━━━━━━━━━━━\n"
            f"🎭 Character: {char_name}\n"
            f"🏅 Rank: {player['rank']}\n"
            f"📊 Level: {player['level']}\n"
            f"💰 Yen: ¥{player['yen']:,}\n"
            f"❤️ HP: {player['hp']}/{player['max_hp']}\n"
            f"🔵 CE: {player['ce']}/{player['max_ce']}\n"
            f"━━━━━━━━━━━━━━━━━━━\n"
            f"⚔️ ATK: {player['atk']} | 🛡️ DEF: {player['def']} | 💨 SPD: {player['spd']}\n"
            f"━━━━━━━━━━━━━━━━━━━\n"
            f"Select an option below:"
        )
    else:
        welcome_msg = (
            f"🧙 **Welcome to Jujutsu Kaisen RPG, {username}!**\n"
            f"━━━━━━━━━━━━━━━━━━━\n"
            f"⚔️ Fight cursed spirits\n"
            f"🎭 Collect all characters\n"
            f"🏪 Buy weapons and techniques\n"
            f"👥 Form clans with friends\n"
            f"━━━━━━━━━━━━━━━━━━━\n"
            f"Select an option below to start your journey!"
        )
    
    await message.reply(welcome_msg, reply_markup=keyboard)

# ========================================
# WELCOME CALLBACK HANDLER
# ========================================
@dp.callback_query(lambda c: c.data.startswith("welcome_"))
async def welcome_callback(callback: types.CallbackQuery):
    action = callback.data.replace("welcome_", "")
    
    if action == "profile":
        await callback.answer("📊 Opening profile...")
        await profile_command(callback.message)
    elif action == "battle":
        await callback.answer("⚔️ Starting battle...")
        await battle_command(callback.message)
    elif action == "characters":
        await callback.answer("🎭 Loading characters...")
        await characters_command(callback.message)
    elif action == "shop":
        await callback.answer("🏪 Loading shop...")
        await shop_command(callback.message)
    elif action == "enemies":
        await callback.answer("👹 Loading enemies...")
        await enemies_command(callback.message)
    elif action == "bag":
        await callback.answer("📦 Opening bag...")
        await bag_command(callback.message)
    elif action == "commands":
        await callback.answer("📋 Loading commands...")
        await commands_command(callback.message)

# ========================================
# COMMAND: /profile
# ========================================
@dp.message(Command("profile"))
async def profile_command(message: types.Message):
    user_id = message.from_user.id
    
    try:
        async with db_pool.acquire() as conn:
            player = await conn.fetchrow(
                'SELECT * FROM players WHERE user_id = $1', user_id
            )
    except Exception as e:
        await message.reply("Database error. Please try again.")
        return
    
    if not player:
        await message.reply("Start your journey with /start first!")
        return
    
    char_name = player.get('character_name', 'None')
    weapon = player.get('equipped_weapon', 'None')
    
    await message.reply(
        f"👤 **Profile**\n"
        f"━━━━━━━━━━━━━━━━━━━\n"
        f"🎭 Character: {char_name}\n"
        f"🏅 Rank: {player['rank']}\n"
        f"📊 Level: {player['level']}\n"
        f"⭐ XP: {player['xp']}\n"
        f"💰 Yen: ¥{player['yen']:,}\n"
        f"🏆 Wins: {player['wins']} | ❌ Losses: {player['losses']}\n"
        f"━━━━━━━━━━━━━━━━━━━\n"
        f"❤️ HP: {player['hp']}/{player['max_hp']}\n"
        f"🔵 CE: {player['ce']}/{player['max_ce']}\n"
        f"⚔️ ATK: {player['atk']}\n"
        f"🛡️ DEF: {player['def']}\n"
        f"💨 SPD: {player['spd']}\n"
        f"━━━━━━━━━━━━━━━━━━━\n"
        f"🗡️ Weapon: {weapon}\n"
        f"🏛️ Clan: {player.get('clan', 'None')}"
    )

# ========================================
# COMMAND: /characters
# ========================================
@dp.message(Command("characters"))
async def characters_command(message: types.Message):
    try:
        async with db_pool.acquire() as conn:
            characters = await conn.fetch('SELECT * FROM characters ORDER BY id')
    except Exception as e:
        await message.reply("Database error. Please try again.")
        return
    
    if not characters:
        await message.reply("No characters available!")
        return
    
    for char in characters:
        caption = (
            f"🎭 **{char['name']}** - {char['rank']}\n"
            f"━━━━━━━━━━━━━━━━━━━\n"
            f"⚔️ ATK: {char['atk']} | 🛡️ DEF: {char['def']} | 💨 SPD: {char['spd']}\n"
            f"❤️ HP: {char['hp']} | 🔵 CE: {char['ce']}\n"
            f"💰 Price: ¥{char['price']:,}\n"
            f"━━━━━━━━━━━━━━━━━━━\n"
            f"To select: /select {char['name']}"
        )
        
        if char.get('image_url') and char['image_url']:
            await message.reply_photo(photo=char['image_url'], caption=caption)
        else:
            await message.reply(caption)

# ========================================
# COMMAND: /select
# ========================================
@dp.message(Command("select"))
async def select_character(message: types.Message):
    args = message.text.split()
    if len(args) < 2:
        await message.reply("❌ Usage: /select [character name]\nExample: /select Gojo Satoru")
        return
    
    character_name = " ".join(args[1:])
    user_id = message.from_user.id
    
    try:
        async with db_pool.acquire() as conn:
            char = await conn.fetchrow(
                'SELECT * FROM characters WHERE name ILIKE $1', character_name
            )
            
            if not char:
                await message.reply(f"❌ Character '{character_name}' not found!")
                return
            
            await conn.execute('''
                UPDATE players 
                SET character_name = $1, 
                    atk = $2, def = $3, spd = $4, 
                    hp = $5, ce = $6, max_hp = $5, max_ce = $6
                WHERE user_id = $7
            ''', char['name'], char['atk'], char['def'], char['spd'], 
               char['hp'], char['ce'], user_id)
            
            caption = (
                f"✅ You selected **{char['name']}** as your fighter!\n"
                f"━━━━━━━━━━━━━━━━━━━\n"
                f"⚔️ ATK: {char['atk']} | 🛡️ DEF: {char['def']} | 💨 SPD: {char['spd']}\n"
                f"❤️ HP: {char['hp']} | 🔵 CE: {char['ce']}\n"
                f"━━━━━━━━━━━━━━━━━━━\n"
                f"Check /profile to see your updated stats!"
            )
            
            if char.get('image_url') and char['image_url']:
                await message.reply_photo(photo=char['image_url'], caption=caption)
            else:
                await message.reply(caption)
                
    except Exception as e:
        await message.reply(f"Database error: {e}")

# ========================================
# COMMAND: /shop
# ========================================
@dp.message(Command("shop"))
async def shop_command(message: types.Message):
    try:
        async with db_pool.acquire() as conn:
            items = await conn.fetch('SELECT * FROM shop_items ORDER BY category')
    except Exception as e:
        await message.reply("Database error. Please try again.")
        return
    
    if not items:
        await message.reply("Shop is empty!")
        return
    
    categories = {}
    for item in items:
        cat = item['category']
        if cat not in categories:
            categories[cat] = []
        categories[cat].append(item)
    
    response = "🏪 **Jujutsu Shop**\n━━━━━━━━━━━━━━━━━━━\n"
    
    for category, items_list in categories.items():
        response += f"\n📌 **{category.upper()}**\n"
        for item in items_list[:5]:
            response += f"  • {item['name']} - ¥{item['price']:,}\n"
        if len(items_list) > 5:
            response += f"  ... and {len(items_list) - 5} more\n"
    
    response += "\n━━━━━━━━━━━━━━━━━━━\n"
    response += "Use: /buy [item name]\n"
    response += "Example: /buy Health Potion"
    
    await message.reply(response)

# ========================================
# COMMAND: /buy
# ========================================
@dp.message(Command("buy"))
async def buy_command(message: types.Message):
    args = message.text.split()
    if len(args) < 2:
        await message.reply("❌ Usage: /buy [item name]\nExample: /buy Health Potion")
        return
    
    item_name = " ".join(args[1:])
    user_id = message.from_user.id
    
    try:
        async with db_pool.acquire() as conn:
            player = await conn.fetchrow(
                'SELECT * FROM players WHERE user_id = $1', user_id
            )
            
            if not player:
                await message.reply("Start your journey with /start first!")
                return
            
            item = await conn.fetchrow(
                'SELECT * FROM shop_items WHERE name ILIKE $1', item_name
            )
            
            if not item:
                await message.reply(f"❌ Item '{item_name}' not found in shop!")
                return
            
            if player['yen'] < item['price']:
                await message.reply(
                    f"❌ You don't have enough Yen!\n"
                    f"💰 You have: ¥{player['yen']:,}\n"
                    f"💰 Price: ¥{item['price']:,}"
                )
                return
            
            await conn.execute(
                'UPDATE players SET yen = yen - $1 WHERE user_id = $2',
                item['price'], user_id
            )
            
            if item['category'] in ['consumable', 'elixir', 'weapon', 'domain']:
                await conn.execute(
                    "UPDATE players SET bag = array_append(bag, $1) WHERE user_id = $2",
                    item['name'], user_id
                )
            elif item['category'] == 'technique':
                await conn.execute(
                    "UPDATE players SET techniques = array_append(techniques, $1) WHERE user_id = $2",
                    item['name'], user_id
                )
            
            await message.reply(
                f"✅ You bought **{item['name']}**!\n"
                f"💰 Remaining Yen: ¥{player['yen'] - item['price']:,}\n"
                f"📦 Check your bag: /bag"
            )
            
    except Exception as e:
        await message.reply(f"Database error: {e}")

# ========================================
# COMMAND: /bag
# ========================================
@dp.message(Command("bag"))
async def bag_command(message: types.Message):
    user_id = message.from_user.id
    
    try:
        async with db_pool.acquire() as conn:
            player = await conn.fetchrow(
                'SELECT * FROM players WHERE user_id = $1', user_id
            )
            
            if not player:
                await message.reply("Start your journey with /start first!")
                return
            
            bag = player.get('bag', [])
            techniques = player.get('techniques', [])
            
            if not bag and not techniques:
                await message.reply(
                    "📦 **Your Bag is Empty!**\n"
                    "━━━━━━━━━━━━━━━━━━━\n"
                    "Buy items from /shop to fill your bag!"
                )
                return
            
            response = "📦 **Your Inventory**\n━━━━━━━━━━━━━━━━━━━\n"
            
            if bag:
                response += "\n📦 **Items:**\n"
                for item in bag[:20]:
                    response += f"  • {item}\n"
                if len(bag) > 20:
                    response += f"  ... and {len(bag) - 20} more\n"
            
            if techniques:
                response += "\n🌀 **Techniques:**\n"
                for tech in techniques[:20]:
                    response += f"  • {tech}\n"
                if len(techniques) > 20:
                    response += f"  ... and {len(techniques) - 20} more\n"
            
            response += "\n━━━━━━━━━━━━━━━━━━━\n"
            response += "Use: /use [item name]\n"
            response += "Use: /equip [weapon]\n"
            response += "Use: /techniques to view all"
            
            await message.reply(response)
            
    except Exception as e:
        await message.reply(f"Database error: {e}")

# ========================================
# COMMAND: /use
# ========================================
@dp.message(Command("use"))
async def use_command(message: types.Message):
    args = message.text.split()
    if len(args) < 2:
        await message.reply("❌ Usage: /use [item name]\nExample: /use Health Potion")
        return
    
    item_name = " ".join(args[1:])
    user_id = message.from_user.id
    
    try:
        async with db_pool.acquire() as conn:
            player = await conn.fetchrow(
                'SELECT * FROM players WHERE user_id = $1', user_id
            )
            
            if not player:
                await message.reply("Start your journey with /start first!")
                return
            
            bag = player.get('bag', [])
            if item_name not in bag:
                await message.reply(f"❌ You don't have '{item_name}' in your bag!")
                return
            
            item = await conn.fetchrow(
                'SELECT * FROM shop_items WHERE name ILIKE $1', item_name
            )
            
            if not item:
                await message.reply(f"❌ Item '{item_name}' not found!")
                return
            
            effects = parse_effect(item['effect'])
            response = f"✅ Used **{item['name']}**!\n━━━━━━━━━━━━━━━━━━━\n"
            
            if item['category'] == 'consumable':
                if 'heal_hp' in effects:
                    hp_heal = int(effects['heal_hp'])
                    new_hp = min(player['hp'] + hp_heal, player['max_hp'])
                    await conn.execute(
                        'UPDATE players SET hp = $1 WHERE user_id = $2',
                        new_hp, user_id
                    )
                    response += f"❤️ Restored {hp_heal} HP!\n"
                    response += f"❤️ HP: {new_hp}/{player['max_hp']}"
                
                if 'heal_ce' in effects:
                    ce_heal = int(effects['heal_ce'])
                    new_ce = min(player['ce'] + ce_heal, player['max_ce'])
                    await conn.execute(
                        'UPDATE players SET ce = $1 WHERE user_id = $2',
                        new_ce, user_id
                    )
                    response += f"🔵 Restored {ce_heal} CE!\n"
                    response += f"🔵 CE: {new_ce}/{player['max_ce']}"
                
                if 'heal_full' in effects:
                    await conn.execute(
                        'UPDATE players SET hp = max_hp, ce = max_ce WHERE user_id = $1',
                        user_id
                    )
                    response += "❤️ HP fully restored!\n"
                    response += "🔵 CE fully restored!"
            
            elif item['category'] == 'elixir':
                if 'add_xp' in effects:
                    xp_gain = int(effects['add_xp'])
                    new_xp = player['xp'] + xp_gain
                    new_level = calculate_level(new_xp)
                    new_rank = calculate_rank(new_level, player['wins'])
                    
                    await conn.execute('''
                        UPDATE players 
                        SET xp = $1, level = $2, rank = $3
                        WHERE user_id = $4
                    ''', new_xp, new_level, new_rank, user_id)
                    
                    response += f"⭐ Gained {xp_gain} XP!\n"
                    response += f"📊 Level: {new_level} | Rank: {new_rank}"
                
                if 'heal_hp' in effects:
                    hp_heal = int(effects['heal_hp'])
                    new_hp = min(player['hp'] + hp_heal, player['max_hp'])
                    await conn.execute(
                        'UPDATE players SET hp = $1 WHERE user_id = $2',
                        new_hp, user_id
                    )
                    response += f"\n❤️ Restored {hp_heal} HP!"
                
                if 'heal_ce' in effects:
                    ce_heal = int(effects['heal_ce'])
                    new_ce = min(player['ce'] + ce_heal, player['max_ce'])
                    await conn.execute(
                        'UPDATE players SET ce = $1 WHERE user_id = $2',
                        new_ce, user_id
                    )
                    response += f"\n🔵 Restored {ce_heal} CE!"
            
            await conn.execute(
                "UPDATE players SET bag = array_remove(bag, $1) WHERE user_id = $2",
                item_name, user_id
            )
            
            await message.reply(response)
            
    except Exception as e:
        await message.reply(f"Database error: {e}")

# ========================================
# COMMAND: /equip
# ========================================
@dp.message(Command("equip"))
async def equip_command(message: types.Message):
    args = message.text.split()
    if len(args) < 2:
        await message.reply("❌ Usage: /equip [weapon name]")
        return
    
    weapon_name = " ".join(args[1:])
    user_id = message.from_user.id
    
    try:
        async with db_pool.acquire() as conn:
            player = await conn.fetchrow(
                'SELECT * FROM players WHERE user_id = $1', user_id
            )
            
            if not player:
                await message.reply("Start your journey with /start first!")
                return
            
            bag = player.get('bag', [])
            if weapon_name not in bag:
                await message.reply(f"❌ You don't have '{weapon_name}' in your bag!")
                return
            
            weapon = await conn.fetchrow(
                'SELECT * FROM shop_items WHERE name ILIKE $1 AND category = $2',
                weapon_name, 'weapon'
            )
            
            if not weapon:
                await message.reply(f"❌ '{weapon_name}' is not a weapon!")
                return
            
            effects = parse_effect(weapon['effect'])
            atk_bonus = int(effects.get('atk_bonus', 0))
            
            await conn.execute('''
                UPDATE players 
                SET equipped_weapon = $1, atk = atk + $2
                WHERE user_id = $3
            ''', weapon_name, atk_bonus, user_id)
            
            await message.reply(
                f"✅ Equipped **{weapon_name}**!\n"
                f"━━━━━━━━━━━━━━━━━━━\n"
                f"⚔️ ATK Bonus: +{atk_bonus}\n"
                f"Check /profile to see your updated stats!"
            )
            
    except Exception as e:
        await message.reply(f"Database error: {e}")

# ========================================
# COMMAND: /techniques
# ========================================
@dp.message(Command("techniques"))
async def techniques_command(message: types.Message):
    user_id = message.from_user.id
    
    try:
        async with db_pool.acquire() as conn:
            player = await conn.fetchrow(
                'SELECT * FROM players WHERE user_id = $1', user_id
            )
            
            if not player:
                await message.reply("Start your journey with /start first!")
                return
            
            techniques = player.get('techniques', [])
            
            if not techniques:
                await message.reply(
                    "🌀 **No Techniques Learned!**\n"
                    "━━━━━━━━━━━━━━━━━━━\n"
                    "Buy techniques from /shop to learn them!"
                )
                return
            
            response = "🌀 **Your Techniques**\n━━━━━━━━━━━━━━━━━━━\n"
            for tech in techniques:
                response += f"  • {tech}\n"
            
            response += "\n━━━━━━━━━━━━━━━━━━━\n"
            response += "Use in battle with buttons!"
            
            await message.reply(response)
            
    except Exception as e:
        await message.reply(f"Database error: {e}")

# ========================================
# COMMAND: /enemies
# ========================================
@dp.message(Command("enemies"))
async def enemies_command(message: types.Message):
    try:
        async with db_pool.acquire() as conn:
            enemies = await conn.fetch('SELECT * FROM enemies ORDER BY is_boss DESC, rank')
    except Exception as e:
        await message.reply("Database error. Please try again.")
        return
    
    if not enemies:
        await message.reply("No enemies found!")
        return
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⚔️ Fight Random Curse", callback_data="enemy_fight_random")],
        [InlineKeyboardButton(text="👑 Fight Boss", callback_data="enemy_fight_boss")]
    ])
    
    bosses = [e for e in enemies if e['is_boss']]
    response = (
        f"👹 **Cursed Spirits**\n"
        f"━━━━━━━━━━━━━━━━━━━\n"
        f"Total Enemies: {len(enemies)}\n"
        f"👑 Bosses: {len(bosses)}\n"
        f"━━━━━━━━━━━━━━━━━━━\n"
        f"⚔️ Use /battle to fight!\n"
        f"👑 Challenge a boss with /boss [name]"
    )
    
    await message.reply(response, reply_markup=keyboard)

# ========================================
# COMMAND: /battle
# ========================================
@dp.message(Command("battle"))
async def battle_command(message: types.Message):
    user_id = message.from_user.id
    
    try:
        async with db_pool.acquire() as conn:
            player = await conn.fetchrow(
                'SELECT * FROM players WHERE user_id = $1', user_id
            )
            
            if not player:
                await message.reply("Start your journey with /start first!")
                return
            
            enemy = await conn.fetchrow(
                'SELECT * FROM enemies WHERE is_boss = FALSE ORDER BY RANDOM() LIMIT 1'
            )
            
            if not enemy:
                await message.reply("No enemies available for battle!")
                return
            
            battle_id = await conn.fetchval('''
                INSERT INTO battles (chat_id, player1_id, current_hp1, current_hp2)
                VALUES ($1, $2, $3, $4)
                RETURNING id
            ''', message.chat.id, user_id, player['hp'], enemy['hp'])
            
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [
                    InlineKeyboardButton(text="⚔️ Attack", callback_data=f"battle_attack_{battle_id}"),
                    InlineKeyboardButton(text="🛡️ Defend", callback_data=f"battle_defend_{battle_id}")
                ],
                [
                    InlineKeyboardButton(text="💥 Special", callback_data=f"battle_special_{battle_id}"),
                    InlineKeyboardButton(text="🏃 Run", callback_data=f"battle_run_{battle_id}")
                ],
                [
                    InlineKeyboardButton(text="🌀 Technique", callback_data=f"battle_tech_{battle_id}")
                ]
            ])
            
            char_name = player.get('character_name', 'You')
            
            if enemy.get('image_url') and enemy['image_url']:
                await message.reply_photo(
                    photo=enemy['image_url'],
                    caption=(
                        f"⚔️ **Battle Started!**\n"
                        f"━━━━━━━━━━━━━━━━━━━\n"
                        f"🧙 {char_name}\n"
                        f"❤️ HP: {player['hp']}/{player['max_hp']}\n"
                        f"🔵 CE: {player['ce']}/{player['max_ce']}\n"
                        f"━━━━━━━━━━━━━━━━━━━\n"
                        f"💀 **{enemy['name']}** - {enemy['rank']}\n"
                        f"❤️ HP: {enemy['hp']}\n"
                        f"━━━━━━━━━━━━━━━━━━━\n"
                        f"Choose your action:"
                    ),
                    reply_markup=keyboard
                )
            else:
                await message.reply(
                    f"⚔️ **Battle Started!**\n"
                    f"━━━━━━━━━━━━━━━━━━━\n"
                    f"🧙 {char_name}\n"
                    f"❤️ HP: {player['hp']}/{player['max_hp']}\n"
                    f"🔵 CE: {player['ce']}/{player['max_ce']}\n"
                    f"━━━━━━━━━━━━━━━━━━━\n"
                    f"💀 **{enemy['name']}** - {enemy['rank']}\n"
                    f"❤️ HP: {enemy['hp']}\n"
                    f"━━━━━━━━━━━━━━━━━━━\n"
                    f"Choose your action:",
                    reply_markup=keyboard
                )
            
    except Exception as e:
        await message.reply(f"Database error: {e}")

# ========================================
# COMMAND: /boss
# ========================================
@dp.message(Command("boss"))
async def boss_command(message: types.Message):
    args = message.text.split()
    if len(args) < 2:
        await message.reply("❌ Usage: /boss [boss name]\nExample: /boss Jogo")
        return
    
    boss_name = " ".join(args[1:])
    user_id = message.from_user.id
    
    try:
        async with db_pool.acquire() as conn:
            player = await conn.fetchrow(
                'SELECT * FROM players WHERE user_id = $1', user_id
            )
            
            if not player:
                await message.reply("Start your journey with /start first!")
                return
            
            enemy = await conn.fetchrow(
                'SELECT * FROM enemies WHERE name ILIKE $1 AND is_boss = TRUE', boss_name
            )
            
            if not enemy:
                await message.reply(f"❌ Boss '{boss_name}' not found!\nUse /enemies to see available bosses.")
                return
            
            battle_id = await conn.fetchval('''
                INSERT INTO battles (chat_id, player1_id, current_hp1, current_hp2)
                VALUES ($1, $2, $3, $4)
                RETURNING id
            ''', message.chat.id, user_id, player['hp'], enemy['hp'])
            
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [
                    InlineKeyboardButton(text="⚔️ Attack", callback_data=f"battle_attack_{battle_id}"),
                    InlineKeyboardButton(text="🛡️ Defend", callback_data=f"battle_defend_{battle_id}")
                ],
                [
                    InlineKeyboardButton(text="💥 Special", callback_data=f"battle_special_{battle_id}"),
                    InlineKeyboardButton(text="🏃 Run", callback_data=f"battle_run_{battle_id}")
                ],
                [
                    InlineKeyboardButton(text="🌀 Technique", callback_data=f"battle_tech_{battle_id}")
                ]
            ])
            
            char_name = player.get('character_name', 'You')
            
            if enemy.get('image_url') and enemy['image_url']:
                await message.reply_photo(
                    photo=enemy['image_url'],
                    caption=(
                        f"👑 **Boss Battle!**\n"
                        f"━━━━━━━━━━━━━━━━━━━\n"
                        f"🧙 {char_name}\n"
                        f"❤️ HP: {player['hp']}/{player['max_hp']}\n"
                        f"🔵 CE: {player['ce']}/{player['max_ce']}\n"
                        f"━━━━━━━━━━━━━━━━━━━\n"
                        f"👑 **{enemy['name']}** - {enemy['rank']}\n"
                        f"❤️ HP: {enemy['hp']}\n"
                        f"━━━━━━━━━━━━━━━━━━━\n"
                        f"Choose your action:"
                    ),
                    reply_markup=keyboard
                )
            else:
                await message.reply(
                    f"👑 **Boss Battle!**\n"
                    f"━━━━━━━━━━━━━━━━━━━\n"
                    f"🧙 {char_name}\n"
                    f"❤️ HP: {player['hp']}/{player['max_hp']}\n"
                    f"🔵 CE: {player['ce']}/{player['max_ce']}\n"
                    f"━━━━━━━━━━━━━━━━━━━\n"
                    f"👑 **{enemy['name']}** - {enemy['rank']}\n"
                    f"❤️ HP: {enemy['hp']}\n"
                    f"━━━━━━━━━━━━━━━━━━━\n"
                    f"Choose your action:",
                    reply_markup=keyboard
                )
            
    except Exception as e:
        await message.reply(f"Database error: {e}")

# ========================================
# BATTLE CALLBACK HANDLER
# ========================================
@dp.callback_query(lambda c: c.data.startswith("battle_"))
async def battle_callback(callback: types.CallbackQuery):
    parts = callback.data.split("_")
    action = parts[1]
    battle_id = int(parts[2])
    
    await callback.answer(f"⚔️ {action.capitalize()}!")
    
    try:
        async with db_pool.acquire() as conn:
            battle = await conn.fetchrow(
                'SELECT * FROM battles WHERE id = $1', battle_id
            )
            
            if not battle:
                await callback.message.edit_text("❌ Battle not found!")
                return
            
            player = await conn.fetchrow(
                'SELECT * FROM players WHERE user_id = $1', battle['player1_id']
            )
            
            enemy = await conn.fetchrow(
                'SELECT * FROM enemies ORDER BY RANDOM() LIMIT 1'
            )
            
            if action == "attack":
                damage = random.randint(10, 30)
                new_hp = battle['current_hp2'] - damage
                
                await conn.execute(
                    'UPDATE battles SET current_hp2 = $1 WHERE id = $2',
                    max(0, new_hp), battle_id
                )
                
                if new_hp <= 0:
                    await callback.message.edit_text(
                        f"⚔️ **Victory!**\n"
                        f"━━━━━━━━━━━━━━━━━━━\n"
                        f"🎉 You defeated the enemy!\n"
                        f"💰 Rewards coming soon!"
                    )
                    return
                
                enemy_damage = random.randint(5, 15)
                new_player_hp = battle['current_hp1'] - enemy_damage
                
                await conn.execute(
                    'UPDATE battles SET current_hp1 = $1 WHERE id = $2',
                    max(0, new_player_hp), battle_id
                )
                
                if new_player_hp <= 0:
                    await callback.message.edit_text(
                        f"💀 **Defeat!**\n"
                        f"━━━━━━━━━━━━━━━━━━━\n"
                        f"You have been defeated!\n"
                        f"Train harder and try again!"
                    )
                    return
                
                keyboard = InlineKeyboardMarkup(inline_keyboard=[
                    [
                        InlineKeyboardButton(text="⚔️ Attack", callback_data=f"battle_attack_{battle_id}"),
                        InlineKeyboardButton(text="🛡️ Defend", callback_data=f"battle_defend_{battle_id}")
                    ],
                    [
                        InlineKeyboardButton(text="💥 Special", callback_data=f"battle_special_{battle_id}"),
                        InlineKeyboardButton(text="🏃 Run", callback_data=f"battle_run_{battle_id}")
                    ],
                    [
                        InlineKeyboardButton(text="🌀 Technique", callback_data=f"battle_tech_{battle_id}")
                    ]
                ])
                
                await callback.message.edit_text(
                    f"⚔️ **Battle Continues!**\n"
                    f"━━━━━━━━━━━━━━━━━━━\n"
                    f"🧙 You dealt {damage} damage!\n"
                    f"💀 Enemy dealt {enemy_damage} damage!\n"
                    f"━━━━━━━━━━━━━━━━━━━\n"
                    f"❤️ Your HP: {new_player_hp}\n"
                    f"❤️ Enemy HP: {new_hp}\n"
                    f"━━━━━━━━━━━━━━━━━━━\n"
                    f"Choose your next action:",
                    reply_markup=keyboard
                )
            
            elif action == "defend":
                await callback.message.edit_text(
                    f"🛡️ **Defending!**\n"
                    f"━━━━━━━━━━━━━━━━━━━\n"
                    f"You brace for the next attack!\n"
                    f"Next damage will be reduced by 50%!"
                )
            
            elif action == "special":
                if player['ce'] < 30:
                    await callback.message.edit_text(
                        f"❌ Not enough CE!\n"
                        f"━━━━━━━━━━━━━━━━━━━\n"
                        f"🔵 CE: {player['ce']}/30 needed"
                    )
                    return
                
                damage = random.randint(30, 60)
                new_hp = battle['current_hp2'] - damage
                
                await conn.execute(
                    'UPDATE battles SET current_hp2 = $1 WHERE id = $2',
                    max(0, new_hp), battle_id
                )
                
                if new_hp <= 0:
                    await callback.message.edit_text(
                        f"💥 **Special Attack Victory!**\n"
                        f"━━━━━━━━━━━━━━━━━━━\n"
                        f"🎉 You obliterated the enemy!\n"
                        f"💰 Rewards coming soon!"
                    )
                    return
                
                await callback.message.edit_text(
                    f"💥 **Special Attack!**\n"
                    f"━━━━━━━━━━━━━━━━━━━\n"
                    f"⚡ You dealt {damage} damage!\n"
                    f"❤️ Enemy HP: {new_hp}"
                )
            
            elif action == "run":
                if random.random() < 0.7:
                    await callback.message.edit_text(
                        f"🏃 **Escaped!**\n"
                        f"━━━━━━━━━━━━━━━━━━━\n"
                        f"You successfully ran away!\n"
                        f"Live to fight another day!"
                    )
                else:
                    await callback.message.edit_text(
                        f"🏃 **Failed to Escape!**\n"
                        f"━━━━━━━━━━━━━━━━━━━\n"
                        f"You couldn't escape!\n"
                        f"Fight or die trying!"
                    )
            
            elif action == "tech":
                await callback.message.edit_text(
                    f"🌀 **Techniques**\n"
                    f"━━━━━━━━━━━━━━━━━━━\n"
                    f"Feature coming soon!\n"
                    f"Learn techniques from the shop!"
                )
            
    except Exception as e:
        await callback.message.edit_text(f"❌ Battle error: {e}")

# ========================================
# COMMAND: /challenge
# ========================================
@dp.message(Command("challenge"))
async def challenge_command(message: types.Message):
    args = message.text.split()
    if len(args) < 2:
        await message.reply("❌ Usage: /challenge @username")
        return
    
    target = args[1]
    await message.reply(
        f"👊 **Challenge Sent!**\n"
        f"━━━━━━━━━━━━━━━━━━━\n"
        f"You challenged {target} to a duel!\n"
        f"PvP system coming soon!"
    )

# ========================================
# COMMAND: /commands
# ========================================
@dp.message(Command("commands"))
async def commands_command(message: types.Message):
    await message.reply(
        f"📋 **Full Command List**\n"
        f"━━━━━━━━━━━━━━━━━━━\n"
        f"**General**\n"
        f"/start - Welcome menu\n"
        f"/profile - View your stats\n"
        f"/commands - Show this list\n"
        f"━━━━━━━━━━━━━━━━━━━\n"
        f"**Characters**\n"
        f"/characters - View all characters\n"
        f"/select [name] - Select a character\n"
        f"━━━━━━━━━━━━━━━━━━━\n"
        f"**Battle**\n"
        f"/battle - Fight a cursed spirit\n"
        f"/boss [name] - Fight a boss\n"
        f"/enemies - View all enemies\n"
        f"━━━━━━━━━━━━━━━━━━━\n"
        f"**Shop & Inventory**\n"
        f"/shop - View shop items\n"
        f"/buy [item] - Buy an item\n"
        f"/bag - View your inventory\n"
        f"/use [item] - Use an item\n"
        f"/equip [weapon] - Equip a weapon\n"
        f"/techniques - View learned techniques\n"
        f"━━━━━━━━━━━━━━━━━━━\n"
        f"**PvP**\n"
        f"/challenge @user - Challenge a player\n"
        f"━━━━━━━━━━━━━━━━━━━\n"
        f"**Owner Commands**\n"
        f"/addyen @user amount\n"
        f"/removeyen @user amount\n"
        f"/addxp @user amount\n"
        f"/removexp @user amount\n"
        f"/setrank @user rank\n"
        f"/addlevel @user amount\n"
        f"/removelevel @user amount\n"
        f"/recalc @user (or all)"
    )

# ========================================
# ========================================
# OWNER COMMANDS (Protected by ADMIN_IDS)
# ========================================
# ========================================

# ========================================
# COMMAND: /enemy_list (Admin only)
# ========================================
@dp.message(Command("enemy_list"))
async def enemy_list_command(message: types.Message):
    if message.from_user.id not in ADMIN_IDS:
        await message.reply("❌ Owner only!")
        return
    
    try:
        async with db_pool.acquire() as conn:
            enemies = await conn.fetch('SELECT * FROM enemies ORDER BY is_boss DESC, rank')
    except Exception as e:
        await message.reply("Database error. Please try again.")
        return
    
    response = "👹 **Full Enemy List**\n━━━━━━━━━━━━━━━━━━━\n"
    for enemy in enemies:
        boss_icon = "👑 " if enemy['is_boss'] else "💀 "
        response += f"{boss_icon}{enemy['name']} - {enemy['rank']}\n"
        response += f"  HP: {enemy['hp']} | ATK: {enemy['atk']}\n"
    
    await message.reply(response)

# ========================================
# COMMAND: /addyen
# ========================================
@dp.message(Command("addyen"))
async def add_yen_command(message: types.Message):
    if message.from_user.id not in ADMIN_IDS:
        await message.reply("❌ Owner only!")
        return
    
    args = message.text.split()
    if len(args) < 3:
        await message.reply("❌ Usage: /addyen @user amount")
        return
    
    target = args[1].replace("@", "")
    amount = int(args[2])
    
    try:
        async with db_pool.acquire() as conn:
            result = await conn.execute(
                'UPDATE players SET yen = yen + $1 WHERE username ILIKE $2',
                amount, target
            )
            
            if result == "UPDATE 0":
                await message.reply(f"❌ User '{target}' not found!")
            else:
                await message.reply(
                    f"✅ Added ¥{amount:,} to {target}!\n"
                    f"💰 New balance: ¥{amount:,}+"
                )
    except Exception as e:
        await message.reply(f"Database error: {e}")

# ========================================
# COMMAND: /removeyen
# ========================================
@dp.message(Command("removeyen"))
async def remove_yen_command(message: types.Message):
    if message.from_user.id not in ADMIN_IDS:
        await message.reply("❌ Owner only!")
        return
    
    args = message.text.split()
    if len(args) < 3:
        await message.reply("❌ Usage: /removeyen @user amount")
        return
    
    target = args[1].replace("@", "")
    amount = int(args[2])
    
    try:
        async with db_pool.acquire() as conn:
            result = await conn.execute(
                'UPDATE players SET yen = yen - $1 WHERE username ILIKE $2 AND yen >= $1',
                amount, target
            )
            
            if result == "UPDATE 0":
                await message.reply(f"❌ User '{target}' not found or not enough yen!")
            else:
                await message.reply(f"✅ Removed ¥{amount:,} from {target}!")
    except Exception as e:
        await message.reply(f"Database error: {e}")

# ========================================
# COMMAND: /addxp
# ========================================
@dp.message(Command("addxp"))
async def add_xp_command(message: types.Message):
    if message.from_user.id not in ADMIN_IDS:
        await message.reply("❌ Owner only!")
        return
    
    args = message.text.split()
    if len(args) < 3:
        await message.reply("❌ Usage: /addxp @user amount")
        return
    
    target = args[1].replace("@", "")
    amount = int(args[2])
    
    try:
        async with db_pool.acquire() as conn:
            player = await conn.fetchrow(
                'SELECT * FROM players WHERE username ILIKE $1', target
            )
            
            if not player:
                await message.reply(f"❌ User '{target}' not found!")
                return
            
            new_xp = player['xp'] + amount
            new_level = calculate_level(new_xp)
            new_rank = calculate_rank(new_level, player['wins'])
            
            await conn.execute('''
                UPDATE players 
                SET xp = $1, level = $2, rank = $3
                WHERE username ILIKE $4
            ''', new_xp, new_level, new_rank, target)
            
            await message.reply(
                f"✅ Added {amount} XP to {target}!\n"
                f"📊 New Level: {new_level} | Rank: {new_rank}"
            )
    except Exception as e:
        await message.reply(f"Database error: {e}")

# ========================================
# COMMAND: /removexp
# ========================================
@dp.message(Command("removexp"))
async def remove_xp_command(message: types.Message):
    if message.from_user.id not in ADMIN_IDS:
        await message.reply("❌ Owner only!")
        return
    
    args = message.text.split()
    if len(args) < 3:
        await message.reply("❌ Usage: /removexp @user amount")
        return
    
    target = args[1].replace("@", "")
    amount = int(args[2])
    
    try:
        async with db_pool.acquire() as conn:
            player = await conn.fetchrow(
                'SELECT * FROM players WHERE username ILIKE $1', target
            )
            
            if not player:
                await message.reply(f"❌ User '{target}' not found!")
                return
            
            new_xp = max(0, player['xp'] - amount)
            new_level = calculate_level(new_xp)
            new_rank = calculate_rank(new_level, player['wins'])
            
            await conn.execute('''
                UPDATE players 
                SET xp = $1, level = $2, rank = $3
                WHERE username ILIKE $4
            ''', new_xp, new_level, new_rank, target)
            
            await message.reply(
                f"✅ Removed {amount} XP from {target}!\n"
                f"📊 New Level: {new_level} | Rank: {new_rank}"
            )
    except Exception as e:
        await message.reply(f"Database error: {e}")

# ========================================
# COMMAND: /setrank
# ========================================
@dp.message(Command("setrank"))
async def set_rank_command(message: types.Message):
    if message.from_user.id not in ADMIN_IDS:
        await message.reply("❌ Owner only!")
        return
    
    args = message.text.split()
    if len(args) < 3:
        await message.reply("❌ Usage: /setrank @user rank\nRanks: Grade 4, Grade 3, Grade 2, Grade 1, Semi-Special, Special Grade")
        return
    
    target = args[1].replace("@", "")
    rank = " ".join(args[2:])
    
    try:
        async with db_pool.acquire() as conn:
            result = await conn.execute(
                'UPDATE players SET rank = $1 WHERE username ILIKE $2',
                rank, target
            )
            
            if result == "UPDATE 0":
                await message.reply(f"❌ User '{target}' not found!")
            else:
                await message.reply(f"✅ Set {target}'s rank to: {rank}")
    except Exception as e:
        await message.reply(f"Database error: {e}")

# ========================================
# COMMAND: /addlevel
# ========================================
@dp.message(Command("addlevel"))
async def add_level_command(message: types.Message):
    if message.from_user.id not in ADMIN_IDS:
        await message.reply("❌ Owner only!")
        return
    
    args = message.text.split()
    if len(args) < 3:
        await message.reply("❌ Usage: /addlevel @user amount")
        return
    
    target = args[1].replace("@", "")
    amount = int(args[2])
    
    try:
        async with db_pool.acquire() as conn:
            player = await conn.fetchrow(
                'SELECT * FROM players WHERE username ILIKE $1', target
            )
            
            if not player:
                await message.reply(f"❌ User '{target}' not found!")
                return
            
            new_level = player['level'] + amount
            new_rank = calculate_rank(new_level, player['wins'])
            
            await conn.execute('''
                UPDATE players 
                SET level = $1, rank = $2
                WHERE username ILIKE $3
            ''', new_level, new_rank, target)
            
            await message.reply(
                f"✅ Added {amount} levels to {target}!\n"
                f"📊 New Level: {new_level} | Rank: {new_rank}"
            )
    except Exception as e:
        await message.reply(f"Database error: {e}")

# ========================================
# COMMAND: /removelevel
# ========================================
@dp.message(Command("removelevel"))
async def remove_level_command(message: types.Message):
    if message.from_user.id not in ADMIN_IDS:
        await message.reply("❌ Owner only!")
        return
    
    args = message.text.split()
    if len(args) < 3:
        await message.reply("❌ Usage: /removelevel @user amount")
        return
    
    target = args[1].replace("@", "")
    amount = int(args[2])
    
    try:
        async with db_pool.acquire() as conn:
            player = await conn.fetchrow(
                'SELECT * FROM players WHERE username ILIKE $1', target
            )
            
            if not player:
                await message.reply(f"❌ User '{target}' not found!")
                return
            
            new_level = max(1, player['level'] - amount)
            new_rank = calculate_rank(new_level, player['wins'])
            
            await conn.execute('''
                UPDATE players 
                SET level = $1, rank = $2
                WHERE username ILIKE $3
            ''', new_level, new_rank, target)
            
            await message.reply(
                f"✅ Removed {amount} levels from {target}!\n"
                f"📊 New Level: {new_level} | Rank: {new_rank}"
            )
    except Exception as e:
        await message.reply(f"Database error: {e}")

# ========================================
# COMMAND: /recalc
# ========================================
@dp.message(Command("recalc"))
async def recalc_command(message: types.Message):
    if message.from_user.id not in ADMIN_IDS:
        await message.reply("❌ Owner only!")
        return
    
    args = message.text.split()
    
    try:
        async with db_pool.acquire() as conn:
            if len(args) > 1:
                target = args[1].replace("@", "")
                player = await conn.fetchrow(
                    'SELECT * FROM players WHERE username ILIKE $1', target
                )
                
                if not player:
                    await message.reply(f"❌ User '{target}' not found!")
                    return
                
                new_level = calculate_level(player['xp'])
                new_rank = calculate_rank(new_level, player['wins'])
                
                await conn.execute('''
                    UPDATE players 
                    SET level = $1, rank = $2
                    WHERE username ILIKE $3
                ''', new_level, new_rank, target)
                
                await message.reply(
                    f"✅ Recalculated {target}:\n"
                    f"📊 Level: {new_level} | Rank: {new_rank}"
                )
            else:
                players = await conn.fetch('SELECT * FROM players')
                count = 0
                
                for player in players:
                    new_level = calculate_level(player['xp'])
                    new_rank = calculate_rank(new_level, player['wins'])
                    
                    await conn.execute('''
                        UPDATE players 
                        SET level = $1, rank = $2
                        WHERE user_id = $3
                    ''', new_level, new_rank, player['user_id'])
                    count += 1
                
                await message.reply(
                    f"✅ Recalculated all players!\n"
                    f"📊 {count} players updated."
                )
                
    except Exception as e:
        await message.reply(f"Database error: {e}")

# ========================================
# MAIN
# ========================================
async def main():
    await on_startup()
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
