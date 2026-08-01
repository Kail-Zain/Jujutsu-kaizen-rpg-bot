import asyncio
import os
import random
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
# COMMAND: /start
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
    
    await message.reply(
        "🧙 **Welcome to Jujutsu Kaisen RPG!**\n\n"
        "🔥 Choose your character: /characters\n"
        "👤 Check your profile: /profile\n"
        "🏪 Visit the shop: /shop\n"
        "⚔️ Fight curses: /battle\n"
        "👹 View cursed spirits: /enemies\n"
        "👊 Challenge a friend: /challenge @username\n\n"
        "Become the strongest sorcerer! 💪"
    )

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
    
    # Get character name
    char_name = player.get('character_name', 'None')
    
    await message.reply(
        f"👤 **Profile**\n"
        f"━━━━━━━━━━━━━━━━━━━\n"
        f"🎭 Character: {char_name}\n"
        f"🏅 Rank: {player['rank']}\n"
        f"📊 Level: {player['level']}\n"
        f"⭐ XP: {player['xp']}\n"
        f"💰 Yen: ¥{player['yen']:,}\n"
        f"━━━━━━━━━━━━━━━━━━━\n"
        f"❤️ HP: {player['hp']}/{player['max_hp']}\n"
        f"🔵 CE: {player['ce']}/{player['max_ce']}\n"
        f"⚔️ ATK: {player['atk']}\n"
        f"🛡️ DEF: {player['def']}\n"
        f"💨 SPD: {player['spd']}\n"
        f"━━━━━━━━━━━━━━━━━━━\n"
        f"🏛️ Clan: {player.get('clan', 'None')}"
    )

# ========================================
# COMMAND: /characters (WITH IMAGES)
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
        await message.reply("No characters available yet! Add some in the database.")
        return
    
    # Send first character with image
    for char in characters:
        caption = (
            f"🎭 **{char['name']}** - {char['rank']}\n"
            f"⚔️ ATK: {char['atk']} | 🛡️ DEF: {char['def']} | 💨 SPD: {char['spd']}\n"
            f"❤️ HP: {char['hp']} | 🔵 CE: {char['ce']}\n"
            f"💰 Price: ¥{char['price']:,}\n"
            f"━━━━━━━━━━━━━━━━━━━\n"
            f"To select: /select {char['name']}"
        )
        
        # Send image if URL exists
        if char.get('image_url') and char['image_url']:
            await message.reply_photo(
                photo=char['image_url'],
                caption=caption
            )
        else:
            await message.reply(caption)

# ========================================
# COMMAND: /select [character name]
# ========================================
@dp.message(Command("select"))
async def select_character(message: types.Message):
    args = message.text.split()
    if len(args) < 2:
        await message.reply(
            "❌ Usage: /select [character name]\n"
            "Example: /select Gojo Satoru"
        )
        return
    
    character_name = " ".join(args[1:])
    user_id = message.from_user.id
    
    try:
        async with db_pool.acquire() as conn:
            # Check if character exists
            char = await conn.fetchrow(
                'SELECT * FROM characters WHERE name ILIKE $1', character_name
            )
            
            if not char:
                await message.reply(f"❌ Character '{character_name}' not found!\n"
                                   f"Use /characters to see all available.")
                return
            
            # Update player's character and stats
            await conn.execute('''
                UPDATE players 
                SET character_name = $1, 
                    atk = $2, def = $3, spd = $4, 
                    hp = $5, ce = $6, max_hp = $5, max_ce = $6
                WHERE user_id = $7
            ''', char['name'], char['atk'], char['def'], char['spd'], 
               char['hp'], char['ce'], user_id)
            
            await message.reply_photo(
                photo=char['image_url'],
                caption=(
                    f"✅ You selected **{char['name']}** as your fighter!\n"
                    f"━━━━━━━━━━━━━━━━━━━\n"
                    f"⚔️ ATK: {char['atk']} | 🛡️ DEF: {char['def']} | 💨 SPD: {char['spd']}\n"
                    f"❤️ HP: {char['hp']} | 🔵 CE: {char['ce']}\n"
                    f"━━━━━━━━━━━━━━━━━━━\n"
                    f"Your stats have been updated! Check /profile"
                )
            )
    except Exception as e:
        await message.reply(f"Database error: {e}")

# ========================================
# COMMAND: /shop
# ========================================
@dp.message(Command("shop"))
async def shop_command(message: types.Message):
    await message.reply(
        "🏪 **Jujutsu Shop**\n"
        "━━━━━━━━━━━━━━━━━━━\n"
        "🩸 Health Potion - ¥100,000\n"
        "   Restores 50 HP\n"
        "⚡ CE Potion - ¥100,000\n"
        "   Restores 50 CE\n"
        "💊 Cursed Energy Elixir - ¥50,000\n"
        "   +500 XP\n"
        "🔮 Sukuna's Blood - ¥300,000\n"
        "   +2,000 XP\n"
        "🌀 Reverse Cursed Elixir - ¥500,000\n"
        "   +3,000 XP, +50 HP\n"
        "🌌 Heaven's Nectar - ¥750,000\n"
        "   +5,000 XP\n"
        "♾️ Limitless Shard - ¥1,500,000\n"
        "   +8,000 XP, +100 CE\n"
        "━━━━━━━━━━━━━━━━━━━\n"
        "Use: /buy [item name]"
    )

# ========================================
# COMMAND: /enemies (WITH IMAGES FOR BOSSES)
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
    
    # Send bosses with images
    for enemy in enemies:
        # Only send image for bosses that have one
        if enemy['is_boss'] and enemy.get('image_url') and enemy['image_url']:
            caption = (
                f"👑 **{enemy['name']}** - {enemy['rank']}\n"
                f"━━━━━━━━━━━━━━━━━━━\n"
                f"⚔️ ATK: {enemy['atk']} | 🛡️ DEF: {enemy['def']} | 💨 SPD: {enemy['spd']}\n"
                f"❤️ HP: {enemy['hp']} | 🔵 CE: {enemy['ce']}\n"
                f"━━━━━━━━━━━━━━━━━━━\n"
                f"💰 Reward: ¥{enemy['reward_yen']:,} | 📈 XP: {enemy['reward_xp']}"
            )
            await message.reply_photo(
                photo=enemy['image_url'],
                caption=caption
            )
        else:
            # Send as text for non-bosses or bosses without images
            boss_icon = "👑 " if enemy['is_boss'] else "💀 "
            await message.reply(
                f"{boss_icon}**{enemy['name']}** - {enemy['rank']}\n"
                f"⚔️ ATK: {enemy['atk']} | 🛡️ DEF: {enemy['def']} | 💨 SPD: {enemy['spd']}\n"
                f"❤️ HP: {enemy['hp']} | 🔵 CE: {enemy['ce']}\n"
                f"💰 Reward: ¥{enemy['reward_yen']:,} | 📈 XP: {enemy['reward_xp']}"
            )

# ========================================
# COMMAND: /battle
# ========================================
@dp.message(Command("battle"))
async def battle_command(message: types.Message):
    user_id = message.from_user.id
    
    try:
        async with db_pool.acquire() as conn:
            # Get player stats
            player = await conn.fetchrow(
                'SELECT * FROM players WHERE user_id = $1', user_id
            )
            
            if not player:
                await message.reply("Start your journey with /start first!")
                return
            
            # Get a random enemy (non-boss for normal battles)
            enemy = await conn.fetchrow(
                'SELECT * FROM enemies WHERE is_boss = FALSE ORDER BY RANDOM() LIMIT 1'
            )
            
            if not enemy:
                await message.reply("No enemies available for battle!")
                return
            
            # Create battle entry
            battle_id = await conn.fetchval('''
                INSERT INTO battles (chat_id, player1_id, current_hp1, current_hp2)
                VALUES ($1, $2, $3, $4)
                RETURNING id
            ''', message.chat.id, user_id, player['hp'], enemy['hp'])
            
            # Build battle keyboard
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [
                    InlineKeyboardButton(text="⚔️ Attack", callback_data=f"battle_attack_{battle_id}"),
                    InlineKeyboardButton(text="🛡️ Defend", callback_data=f"battle_defend_{battle_id}")
                ],
                [
                    InlineKeyboardButton(text="💥 Special", callback_data=f"battle_special_{battle_id}"),
                    InlineKeyboardButton(text="🏃 Run", callback_data=f"battle_run_{battle_id}")
                ]
            ])
            
            await message.reply(
                f"⚔️ **Battle Started!**\n"
                f"━━━━━━━━━━━━━━━━━━━\n"
                f"🧙 {player['character_name'] or 'You'}\n"
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
        f"Wait for them to accept with:\n"
        f"/accept @yourusername"
    )

# ========================================
# COMMAND: /attack (Simple attack for testing)
# ========================================
@dp.message(Command("attack"))
async def attack_command(message: types.Message):
    # Random damage between 10-30
    damage = random.randint(10, 30)
    await message.reply(
        f"⚡ **Attack!**\n"
        f"━━━━━━━━━━━━━━━━━━━\n"
        f"You strike the cursed spirit with {damage} damage!\n"
        f"Spirit HP: {100 - damage}/100"
    )

# ========================================
# CALLBACK QUERY HANDLER (Battle Actions)
# ========================================
@dp.callback_query()
async def battle_callback(callback: types.CallbackQuery):
    data = callback.data
    
    if data.startswith("battle_"):
        parts = data.split("_")
        action = parts[1]
        battle_id = int(parts[2])
        
        await callback.answer(f"Action: {action.capitalize()}!")
        
        # Here you would implement the full battle logic
        # For now, just update the message
        await callback.message.edit_text(
            f"⚔️ **Battle Action: {action.capitalize()}**\n"
            f"━━━━━━━━━━━━━━━━━━━\n"
            f"Battle system coming soon!\n"
            f"Battle ID: {battle_id}"
        )

# ========================================
# MAIN
# ========================================
async def main():
    await on_startup()
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
