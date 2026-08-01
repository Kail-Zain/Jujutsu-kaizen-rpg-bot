import asyncio
import os
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
import asyncpg
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Get credentials from environment
BOT_TOKEN = os.getenv("BOT_TOKEN")
DATABASE_URL = os.getenv("DATABASE_URL")

if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN is not set!")

if not DATABASE_URL:
    raise ValueError("DATABASE_URL is not set!")

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()
db_pool = None

async def on_startup():
    global db_pool
    db_pool = await asyncpg.create_pool(DATABASE_URL)
    print("✅ Database connected!")

async def on_shutdown():
    await db_pool.close()
    print("✅ Database closed!")

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
        "Check your profile: /profile\n"
        "View characters: /characters\n"
        "Visit the shop: /shop\n"
        "Fight: /battle\n"
        "Challenge: /challenge @username\n\n"
        "🔥 Become the strongest sorcerer!"
    )

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
    
    await message.reply(
        f"👤 **Profile**\n"
        f"Rank: {player['rank']}\n"
        f"Level: {player['level']}\n"
        f"XP: {player['xp']}\n"
        f"💰 Yen: {player['yen']:,}\n"
        f"❤️ HP: {player['hp']}/{player['max_hp']}\n"
        f"🔵 CE: {player['ce']}/{player['max_ce']}\n"
        f"⚔️ ATK: {player['atk']} | 🛡️ DEF: {player['def']} | 💨 SPD: {player['spd']}"
    )

@dp.message(Command("characters"))
async def characters_command(message: types.Message):
    try:
        async with db_pool.acquire() as conn:
            characters = await conn.fetch('SELECT * FROM characters')
    except Exception as e:
        await message.reply("Database error. Please try again.")
        return
    
    if not characters:
        await message.reply("No characters available yet! Add some in the database.")
        return
    
    response = "🎭 **Available Characters**\n\n"
    for char in characters:
        response += f"**{char['name']}** - {char['rank']}\n"
        response += f"⚔️ ATK: {char['atk']} | 🛡️ DEF: {char['def']} | 💨 SPD: {char['spd']}\n"
        response += f"❤️ HP: {char['hp']} | 🔵 CE: {char['ce']}\n"
        response += f"💰 Price: ¥{char['price']:,}\n\n"
    
    await message.reply(response)

@dp.message(Command("shop"))
async def shop_command(message: types.Message):
    await message.reply(
        "🏪 **Jujutsu Shop**\n\n"
        "🩸 Health Potion - ¥100,000 (Restores 50 HP)\n"
        "⚡ CE Potion - ¥100,000 (Restores 50 CE)\n"
        "💊 Cursed Energy Elixir - ¥50,000 (+500 XP)\n"
        "🔮 Sukuna's Blood - ¥300,000 (+2000 XP)\n"
        "🌀 Reverse Cursed Elixir - ¥500,000 (+3000 XP, +50 HP)\n"
        "🌌 Heaven's Nectar - ¥750,000 (+5000 XP)\n"
        "♾️ Limitless Shard - ¥1,500,000 (+8000 XP, +100 CE)\n\n"
        "Use: /buy [item name]"
    )

@dp.message(Command("battle"))
async def battle_command(message: types.Message):
    await message.reply(
        "⚔️ **Battle Mode**\n\n"
        "A cursed spirit appears!\n\n"
        "Use /attack to strike!\n"
        "Use /defend to block!\n"
        "Use /special for your technique!"
    )

@dp.message(Command("challenge"))
async def challenge_command(message: types.Message):
    args = message.text.split()
    if len(args) < 2:
        await message.reply("Usage: /challenge @username")
        return
    
    target = args[1]
    await message.reply(
        f"👊 You challenged {target} to a duel!\n\n"
        f"Wait for them to accept with /accept @yourusername"
    )

@dp.message(Command("attack"))
async def attack_command(message: types.Message):
    await message.reply(
        "⚡ **Attack!**\n\n"
        "You strike the cursed spirit with 25 damage!\n"
        "Spirit HP: 75/100"
    )

async def main():
    await on_startup()
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
