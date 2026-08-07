import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
DATABASE_URL = os.getenv("DATABASE_URL")

# Static data (we'll move to DB eventually, but keep here for speed)
CHARACTERS = {
    "Yuji": {"rank": "Grade 1", "hp": 100, "ce": 80, "atk": 25, "def": 20, "spd": 22, "price": 0},
    "Gojo": {"rank": "Special Grade", "hp": 120, "ce": 150, "atk": 35, "def": 30, "spd": 28, "price": 5000},
    # ... (all others from your schema)
}

# XP thresholds per level (example)
LEVEL_XP = {i: i * 100 for i in range(1, 101)}  # adjust later

# Cooldowns (seconds)
BATTLE_COOLDOWN = 60
BOSS_COOLDOWN = 300
PVP_COOLDOWN = 120
