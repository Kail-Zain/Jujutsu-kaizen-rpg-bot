import asyncio
import logging
from aiogram import Bot, Dispatcher
from aiogram.filters import Command
from config import BOT_TOKEN
from services.db import create_pool, close_pool, db_pool
from handlers import start, profile, characters, battle, shop, clan, pvp, story, dungeon_tower, quests, crafting, leaderboard, admin, misc
from utils.decorators import friendly_error
import asyncpg

logging.basicConfig(level=logging.INFO)

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# Include all handlers
dp.include_routers(
    start.router,
    profile.router,
    characters.router,
    battle.router,
    shop.router,
    clan.router,
    pvp.router,
    story.router,
    dungeon_tower.router,
    quests.router,
    crafting.router,
    leaderboard.router,
    admin.router,
    misc.router,
)

@dp.message(Command("start"))
@friendly_error
async def start_cmd(message):
    await start.start_cmd(message)

# Add other catch‑all if needed

async def on_startup():
    global db_pool
    db_pool = await create_pool()
    print("✅ Database connected!")

async def on_shutdown():
    await close_pool()
    print("✅ Database closed!")

async def main():
    await on_startup()
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
