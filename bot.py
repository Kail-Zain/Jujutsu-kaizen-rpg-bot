import asyncio
import os
import random
import json
import logging
import traceback
import html
import difflib
from datetime import datetime, timedelta
from io import StringIO
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, InputMediaPhoto, BufferedInputFile
import asyncpg
from dotenv import load_dotenv

logging.basicConfig(level=logging.INFO)

load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")
DATABASE_URL = os.getenv("DATABASE_URL")
if not BOT_TOKEN or not DATABASE_URL:
    raise ValueError("Missing BOT_TOKEN or DATABASE_URL")

OWNER_ID = 8609946980
OWNER_NAME = "𝕄𝕒𝕩𝕨𝕖𝕝𝕝-𝟜𝟟"
YEN_PURCHASE_INFO = f"💰 <b>Buy Yen</b> — Contact {html.escape(OWNER_NAME)} directly."
MAX_YEN = 999999999
CURRENT_SEASON = "Culling Games"  # Used for the Season Pass

# ---------- QUOTES ----------
CHARACTER_QUOTES = {
    "Yuji Itadori": [
        "I'll keep moving forward, until I destroy my enemies!",
        "I don't know about the future, but I can change the present.",
        "I want to live without regrets!",
        "I'm not alone. I have my friends!",
        "I will curse you. Even if I die, I'll curse you.",
        "Come on! Let's go!",
        "I'm a cog. But I'll keep fighting.",
    ],
    "Gojo Satoru": [
        "Throughout Heaven and Earth, I alone am the honored one.",
        "You're weak. Why are you weak? Because you lack... hatred.",
        "Don't worry. I'm the strongest.",
        "I don't want to be a clown. I want to be the strongest.",
        "Nah, I'd win.",
        "You can't kill me. I'm the strongest.",
        "My students are my pride.",
    ],
    "Sukuna": [
        "The only ones who should kill are those prepared to be killed.",
        "I'll show you true despair.",
        "You're nothing but a pawn.",
        "I am the King of Curses.",
        "I alone am the honored one.",
        "Your existence is meaningless.",
        "I'll tear you apart.",
    ],
    "Megumi Fushiguro": [
        "I'll save you. Even if it costs me my life.",
        "I'm not weak. I'll prove it.",
        "I'll do what I have to do.",
        "I don't need anyone's help.",
        "I'll become stronger.",
        "I'll protect everyone.",
    ],
    "Nobara Kugisaki": [
        "I don't need a reason to fight. I just want to win.",
        "I'm not a coward.",
        "I'll strike with all my might!",
        "I'm a sorcerer. I fight.",
        "I'll crush you!",
    ],
    "Nanami Kento": [
        "I'm tired. Let's finish this quickly.",
        "I'll do my job.",
        "I'm not a hero. I'm a sorcerer.",
        "I'll protect the civilians.",
        "I'll take over for you.",
    ],
    "Maki Zenin": [
        "I don't need cursed energy. I have my fists.",
        "I'll crush the Zenin clan.",
        "I'm not afraid of anyone.",
        "I'll become the strongest.",
        "I'll show them what I'm made of.",
    ],
    "Yuta Okkotsu": [
        "I'll fight to protect everyone.",
        "I won't let anyone die.",
        "I have Rika with me.",
        "I'll stop the curses.",
        "I'll make sure we all survive.",
    ],
    "Kenjaku": [
        "Everything is going according to plan.",
        "I'll create a new world.",
        "You're just a pawn in my game.",
        "I've been waiting for this moment.",
        "I'll break the cycle.",
    ],
    "Toji Fushiguro": [
        "I don't care about sorcerers.",
        "I'll kill anyone who gets in my way.",
        "I'm not bound by anything.",
        "I'll take the money and run.",
        "I'm just a hired killer.",
    ],
    "Panda": [
        "I'm a panda. What's your excuse?",
        "I'll fight with all my might!",
        "I'm not just a mascot!",
        "I'll protect my friends.",
        "I'll show you what a panda can do!",
    ],
    "default": [
        "The world is full of curses. But I'll still fight.",
        "Every moment you live, you're being watched by a curse.",
        "Don't you ever get tired of being so weak?",
        "I'll curse you. Even if I die, I'll curse you.",
        "I want to live without regrets. I want to be strong.",
        "Throughout Heaven and Earth, I alone am the honored one.",
        "The only ones who should kill are those prepared to be killed.",
    ],
}

SPECIAL_QUOTES = {
    "black_flash": [
        "⚡ BLACK FLASH! The distortion of space!",
        "💥 The air shatters with cursed energy!",
        "⚡ A critical hit beyond the limits!",
    ],
    "domain": [
        "🌐 My domain expands! This is my territory!",
        "🏯 You are now inside my domain. Sure‑hit effect!",
        "🕋 Welcome to my world!",
    ],
    "victory": [
        "🎉 Victory is mine!",
        "🏆 I won! Just as expected.",
        "💪 I'm the strongest!",
    ],
    "defeat": [
        "💀 I lost... but I'll come back stronger.",
        "😔 Defeat... I'll never forget this.",
        "🔥 I'll train harder and return!",
    ],
}

# ---------- NEW: BOSS CINEMATIC INTROS ----------
BOSS_CINEMATICS = {
    "Jogo": "💥 \"You think you can match a Disaster Curse? BURN!\" - Jogo grins wickedly.",
    "Hanami": "🌿 \"Nature will reclaim this world. You are nothing but pests.\" - Hanami declares.",
    "Dagon": "🌊 \"Welcome to my watery abyss. You will drown here!\" - Dagon bellows.",
    "Mahito": "👹 \"I am the true embodiment of humanity! Let me touch your soul...\" - Mahito smiles.",
    "Mahoraga": "🌀 \"The Divine General adjusts to all attacks! DESTROY!\" - The wheel spins.",
    "Sukuna": "🔥 \"You are merely a fly trying to swat a god. Bow down.\" - Sukuna sneers.",
    "Kenjaku": "🔮 \"All according to plan. You are just a pawn.\" - Kenjaku laughs.",
    "default": "⚔️ The Cursed Spirit roars, unleashing its full malice upon you!"
}

def get_jjk_quote(character_name=None, event_type=None):
    if event_type and event_type in SPECIAL_QUOTES:
        return random.choice(SPECIAL_QUOTES[event_type])
    quotes = CHARACTER_QUOTES.get(character_name)
    if not quotes:
        quotes = CHARACTER_QUOTES["default"]
    return random.choice(quotes)

def get_boss_intro(boss_name):
    return BOSS_CINEMATICS.get(boss_name, BOSS_CINEMATICS["default"])

# ---------- EFFECTS ----------
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
user_sessions = {}
npc_sessions = {}  # NEW: Dict to track NPC text fallbacks

# ---------- COMMAND LIST FOR CORRECTION ----------
ALL_COMMANDS = [
    "start", "guide", "stats", "addyenall", "removeyenall",
    "restriction", "vow", "vow_status",  # Added vow_status
    "shikigami", "profile", "characters",
    "select", "shop", "buy", "bag", "use", "equip", "learn",
    "techniques", "enemies", "story", "story_chapter", "boss", "bosses", # Added bosses
    "battle", "status", "resume", "prestige", "pvp_challenge",
    "pvp_accept", "missions", "daily", "clan",
    "awakening", "npc", "dungeon", "tower", "achievements",
    "buyyen", "commands", "addadmin", "removeadmin", "addyen",
    "removeyen", "addxp", "removexp", "setrank", "addlevel",
    "removelevel", "recalc", "diagnosis", "clearbattles",
    "event", "event_battle", "quests", "quest_accept", "quest_reward",
    "materials", "craft", "leaderboard", "broadcast",
    "raid", "raid_attack", "users", "bosses", "toggles", "inspect", "season" # Added toggles, inspect, season
]

def set_session(user_id, session_type, **kwargs):
    user_sessions[user_id] = {"type": session_type, **kwargs}

def clear_session(user_id):
    user_sessions.pop(user_id, None)

def get_session(user_id):
    return user_sessions.get(user_id)

def is_in_session(user_id, session_type=None, battle_id=None):
    sess = get_session(user_id)
    if not sess:
        return False
    if session_type and sess.get("type") != session_type:
        return False
    if battle_id and sess.get("battle_id") != battle_id:
        return False
    return True

# ---------- HELPERS ----------
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

# ---------- STATS UPDATE & REGEN ----------
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

async def apply_passive_regen(player):
    if not player.get('curse_regen'):
        return player
    now = datetime.now()
    last_regen = player.get('last_hp_regen')
    if not last_regen:
        last_regen = now - timedelta(seconds=10)
    delta = (now - last_regen).total_seconds()
    if delta >= 10:
        regen_amt = max(1, int(player['max_hp'] * 0.01))
        new_hp = min(player['max_hp'], player['hp'] + regen_amt)
        async with db_pool.acquire() as conn:
            await conn.execute("UPDATE players SET hp = $1, last_hp_regen = $2 WHERE user_id = $3",
                               new_hp, now, player['user_id'])
        player['hp'] = new_hp
        player['last_hp_regen'] = now
    return player

async def regen_ce(player):
    now = datetime.now()
    last = player.get('last_ce_regen') or now
    delta = (now - last).total_seconds()
    regen = int(delta // 10)
    if regen > 0:
        new_ce = min(player['max_ce'], player['ce'] + regen)
        async with db_pool.acquire() as conn:
            await conn.execute("UPDATE players SET ce = $1, last_ce_regen = $2 WHERE user_id = $3",
                               new_ce, now, player['user_id'])
        player['ce'] = new_ce
        player['last_ce_regen'] = now
    return player

# ---------- ACHIEVEMENTS ----------
async def check_achievements(user_id):
    async with db_pool.acquire() as conn:
        player = await conn.fetchrow("SELECT * FROM players WHERE user_id = $1", user_id)
        if not player:
            return
        achievements = await conn.fetch("SELECT * FROM achievements")
        unlocked = [a['achievement_id'] for a in await conn.fetch("SELECT achievement_id FROM player_achievements WHERE player_id = $1", user_id)]
        newly_unlocked = []
        for ach in achievements:
            if ach['id'] in unlocked:
                continue
            req = ach['requirement']
            if ':' in req:
                key, val = req.split(':')
                val = int(val)
                if key == 'wins' and player['wins'] >= val:
                    newly_unlocked.append(ach)
                elif key == 'boss_kills' and player['boss_kills'] >= val:
                    newly_unlocked.append(ach)
                elif key == 'level' and player['level'] >= val:
                    newly_unlocked.append(ach)
                elif key == 'prestige' and player.get('prestige_level', 0) >= val:
                    newly_unlocked.append(ach)
                elif key == 'black_flash' and player.get('black_flash_count', 0) >= val:
                    newly_unlocked.append(ach)
        for ach in newly_unlocked:
            await conn.execute("INSERT INTO player_achievements (player_id, achievement_id) VALUES ($1, $2)", user_id, ach['id'])
            await bot.send_message(user_id, f"🏆 <b>Achievement Unlocked!</b>\n{e(ach['name'])} – {e(ach['description'])}", parse_mode="HTML")
    return newly_unlocked

# ---------- MISSION PROGRESS ----------
async def update_missions(user_id, action_type, amount=1):
    async with db_pool.acquire() as conn:
        missions = await conn.fetch("SELECT * FROM missions WHERE type = 'daily' OR type = 'weekly'")
        for m in missions:
            pm = await conn.fetchrow("SELECT * FROM player_missions WHERE player_id = $1 AND mission_id = $2", user_id, m['id'])
            if pm and pm['completed']:
                continue
            req = m['requirement']
            if req.startswith(action_type):
                _, target = req.split(':')
                target = int(target)
                if not pm:
                    await conn.execute("INSERT INTO player_missions (player_id, mission_id, progress) VALUES ($1, $2, $3)",
                                       user_id, m['id'], min(amount, target))
                else:
                    new_progress = min(pm['progress'] + amount, target)
                    await conn.execute("UPDATE player_missions SET progress = $1 WHERE player_id = $2 AND mission_id = $3",
                                       new_progress, user_id, m['id'])
                    if new_progress >= target:
                        await conn.execute("UPDATE player_missions SET completed = TRUE WHERE player_id = $1 AND mission_id = $2",
                                           user_id, m['id'])
                        await bot.send_message(user_id, f"✅ Mission complete: {e(m['name'])}! Use /daily to claim rewards.", parse_mode="HTML")

# ---------- QUESTS ----------
async def update_quests(user_id, action_type, amount=1):
    async with db_pool.acquire() as conn:
        quests = await conn.fetch("SELECT * FROM quests")
        for q in quests:
            pq = await conn.fetchrow("SELECT * FROM player_quests WHERE player_id = $1 AND quest_id = $2", user_id, q['id'])
            if pq and pq['completed']:
                continue
            req = q['requirement']
            if req.startswith(action_type):
                _, target = req.split(':')
                target = int(target)
                if not pq:
                    await conn.execute("INSERT INTO player_quests (player_id, quest_id, progress) VALUES ($1, $2, $3)",
                                       user_id, q['id'], min(amount, target))
                else:
                    new_progress = min(pq['progress'] + amount, target)
                    await conn.execute("UPDATE player_quests SET progress = $1 WHERE player_id = $2 AND quest_id = $3",
                                       new_progress, user_id, q['id'])
                    if new_progress >= target:
                        await conn.execute("UPDATE player_quests SET completed = TRUE WHERE player_id = $1 AND quest_id = $2",
                                           user_id, q['id'])
                        await bot.send_message(user_id, f"📜 Quest complete: {e(q['title'])}! Use /quest_reward {q['id']} to claim.", parse_mode="HTML")

# ---------- BINDING VOWS ----------
async def apply_vows_to_player(user_id, player_stats):
    async with db_pool.acquire() as conn:
        active_vows = await conn.fetch("""
            SELECT v.*, pv.remaining_turns 
            FROM player_vows pv 
            JOIN binding_vows v ON pv.vow_id = v.id 
            WHERE pv.player_id = $1 AND pv.active = TRUE
        """, user_id)
        if not active_vows:
            return player_stats
        atk_mod = 1.0
        def_mod = 1.0
        spd_mod = 1.0
        for vow in active_vows:
            eff = vow['effect']
            if eff.startswith("atk+"):
                val = float(eff.split("+")[1].replace("%","")) / 100
                atk_mod += val
            elif eff.startswith("def+"):
                val = float(eff.split("+")[1].replace("%","")) / 100
                def_mod += val
            elif eff.startswith("spd+"):
                val = float(eff.split("+")[1].replace("%","")) / 100
                spd_mod += val
            remaining = vow['remaining_turns'] - 1
            if remaining <= 0:
                await conn.execute("UPDATE player_vows SET active = FALSE, remaining_turns = 0 WHERE player_id = $1 AND vow_id = $2",
                                   user_id, vow['vow_id'])
            else:
                await conn.execute("UPDATE player_vows SET remaining_turns = $1 WHERE player_id = $2 AND vow_id = $3",
                                   remaining, user_id, vow['vow_id'])
        player_stats['atk'] = int(player_stats['atk'] * atk_mod)
        player_stats['def'] = int(player_stats['def'] * def_mod)
        player_stats['spd'] = int(player_stats['spd'] * spd_mod)
        return player_stats

# ---------- PVP TIMEOUT CLEANER ----------
async def clean_expired_pvp():
    while True:
        await asyncio.sleep(30)
        now = datetime.now()
        async with db_pool.acquire() as conn:
            expired = await conn.fetch("SELECT id, player1_id, player2_id FROM battles WHERE is_pvp = TRUE AND status = 'pending' AND timeout < $1", now)
            for b in expired:
                await conn.execute("UPDATE battles SET status = 'abandoned' WHERE id = $1", b['id'])
                for pid in (b['player1_id'], b['player2_id']):
                    if pid in ongoing_battles:
                        del ongoing_battles[pid]
                    clear_session(pid)
                battle_queues.pop(b['id'], None)
                pvp_matches.pop(b['id'], None)

# ---------- MEDIA HELPERS ----------
def e(text):
    if text is None:
        return ""
    return html.escape(str(text))

async def safe_send_media(message, media_type, media_url, caption=None, reply_markup=None):
    if not media_url:
        await message.reply(caption or "ℹ️ No media available.", reply_markup=reply_markup)
        return
    placeholder = "https://via.placeholder.com/300x200?text=Jujutsu+Kaisen"
    try:
        if media_type == 'photo':
            await message.reply_photo(photo=media_url, caption=caption, reply_markup=reply_markup)
        elif media_type == 'animation':
            await message.reply_animation(animation=media_url, caption=caption, reply_markup=reply_markup)
        else:
            await message.reply(caption or "ℹ️ Media unavailable.", reply_markup=reply_markup)
    except Exception as exc:
        logging.warning(f"Media send failed: {exc}")
        try:
            await message.reply_photo(photo=placeholder, caption=caption or "⚠️ Media unavailable.", reply_markup=reply_markup)
        except:
            await message.reply(caption or "⚠️ Media unavailable.", reply_markup=reply_markup)

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
            await callback.message.edit_text(caption, reply_markup=reply_markup, parse_mode="HTML")
    except Exception as exc:
        if "message is not modified" in str(exc):
            pass
        else:
            logging.error(f"Edit battle message error: {exc}")

# ---------- NOTIFY PLAYER (DM + fallback) ----------
async def notify_player(next_player: int, battle_id: int, chat_id: int, bot_instance=None):
    if bot_instance is None:
        bot_instance = bot
    try:
        await bot_instance.send_message(next_player, f"⚔️ Your turn in battle {battle_id}! Check the group chat.")
        return
    except Exception:
        try:
            next_user = await bot_instance.get_chat(next_player)
            mention = f"<a href='tg://user?id={next_player}'>{next_user.first_name}</a>" if next_user else f"Player {next_player}"
            await bot_instance.send_message(chat_id, f"⏳ {mention}, it's your turn in battle {battle_id}!", parse_mode="HTML")
        except Exception as e:
            logging.warning(f"Failed to notify {next_player}: {e}")

# ---------- STARTUP / SHUTDOWN ----------
async def on_startup():
    global db_pool
    db_pool = await asyncpg.create_pool(DATABASE_URL)
    async with db_pool.acquire() as conn:
        await conn.execute("ALTER TABLE battles ADD COLUMN IF NOT EXISTS turn_player BIGINT")
        await conn.execute("ALTER TABLE players ADD COLUMN IF NOT EXISTS last_hp_regen TIMESTAMP")
        await conn.execute("ALTER TABLE player_vows ADD COLUMN IF NOT EXISTS remaining_turns INTEGER DEFAULT 0")
    asyncio.create_task(clean_expired_pvp())
    print("✅ Database connected!")

async def on_shutdown():
    await db_pool.close()
    print("✅ Database closed!")

# ---------- ERROR HANDLER & COMMAND CORRECTION ----------
def friendly_error(func):
    async def wrapper(message: types.Message, *args, **kwargs):
        try:
            if message.text and message.text.startswith('/'):
                cmd = message.text.split()[0].lower().lstrip('/')
                allow_list = ['start', 'help', 'guide', 'status', 'commands', 'buyyen', 'diagnosis']
                if cmd not in allow_list:
                    sess = get_session(message.from_user.id)
                    if sess:
                        if cmd in ['battle', 'boss', 'pvp_challenge', 'dungeon', 'tower', 'raid']:
                            await message.reply("⚠️ You're already in a session! Finish or use /status to resume.")
                            return
                if cmd not in ALL_COMMANDS:
                    matches = difflib.get_close_matches(cmd, ALL_COMMANDS, n=3, cutoff=0.7)
                    if matches:
                        suggestions = ", ".join([f"/{m}" for m in matches])
                        await message.reply(
                            f"❓ Unknown command `/{cmd}`.\n"
                            f"Did you mean: {suggestions}?\n"
                            f"Type /commands for the full list."
                        )
                    else:
                        await message.reply(
                            f"❓ Unknown command `/{cmd}`.\n"
                            f"Type /commands to see all available commands."
                        )
                    return
            return await func(message)
        except Exception as exc:
            logging.error(f"Error in {func.__name__}: {traceback.format_exc()}")
            error_text = (
                f"❌ Oops! Something went wrong.\n\n"
                f"Please try again later. If the problem persists, contact the owner.\n"
                f"Error details: {str(exc)[:150]}\n\n"
                f"{get_jjk_quote()}"
            )
            await message.reply(error_text)
    return wrapper

# ================================================================
# COMMANDS
# ================================================================

@dp.message(Command("start"))
@friendly_error
async def start_cmd(message: types.Message):
    user_id = message.from_user.id
    username = e(message.from_user.username or "Unknown")
    chat_id = message.chat.id

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

        await conn.execute("""
            UPDATE players SET character_name = COALESCE(character_name, 'Yuji Itadori')
            WHERE user_id = $1 AND character_name IS NULL
        """, user_id)

        await conn.execute("UPDATE players SET last_ce_regen = NOW() WHERE user_id = $1 AND last_ce_regen IS NULL", user_id)
        await conn.execute("UPDATE players SET in_battle = FALSE WHERE user_id = $1", user_id)
        await update_player_stats(user_id)

        player = await conn.fetchrow("SELECT * FROM players WHERE user_id = $1", user_id)
        player = await apply_passive_regen(dict(player))

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

    char_name = e(player.get('character_name') or "None")
    quote = get_jjk_quote(char_name)
    msg = (
        f"🧙 <b>Welcome back, {username}!</b>\n"
        f"━━━━━━━━━━━━━━━━━━━\n"
        f"🎭 Character: {char_name}\n"
        f"🏅 Rank: {calc_rank(player['level'])}\n"
        f"📊 Level: {player['level']}\n"
        f"💰 Yen: ¥{player['yen']:,}\n"
        f"❤️ HP: {player['hp']}/{player['max_hp']}\n"
        f"🔵 CE: {player['ce']}/{player['max_ce']}\n"
        f"━━━━━━━━━━━━━━━━━━━\n"
        f"<i>{quote}</i>"
    )
    await message.reply(msg, reply_markup=keyboard, parse_mode="HTML")

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

@dp.message(Command("guide"))
@friendly_error
async def guide_cmd(message: types.Message):
    guide_text = (
        "📖 <b>Cursed Chronicles – Complete Game Guide</b>\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        "⚔️ <b>BATTLE SYSTEM</b>\n"
        "• Combo Points (CP) = level/5+1 (max 5).\n"
        "• Chain moves, enemy counters once.\n"
        "• <b>Domain Sure-Hit</b>: Domains ignore DEF.\n"
        "• <b>Domain Clash</b>: If both use domain, stronger multiplier wins.\n"
        "• <b>Multiplayer</b>: Clan raids allow multiple players to attack the same boss!\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        "🛡️ <b>HEAVENLY RESTRICTION</b> (at level 10)\n"
        "• /restriction toji – CE=0, ATK/DEF/SPD ×2.\n"
        "• /restriction maki – weapon mastery (+50% ATK from weapons).\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        "👹 <b>CURSE EVOLUTION</b>\n"
        "• Defeat bosses to evolve: Grade 4 → ... → Disaster Curse.\n"
        "• Unlocks passive regeneration at Special Grade.\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        "🌀 <b>SHIKIGAMI</b> (Megumi only)\n"
        "• /shikigami summon [name] in battle.\n"
        "• Effects: Divine Dogs (+ATK), Nue (stun), Mahoraga (8x DMG).\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        "⚖️ <b>BINDING VOWS</b>\n"
        "• /vow list and /vow [name] to activate.\n"
        "• Risk/reward buffs last several turns.\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        "📊 <b>LEVELING & PRESTIGE</b>\n"
        "• HP/CE/ATK/DEF/SPD scale with level.\n"
        "• /prestige at level 100 for permanent bonuses.\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        "📜 <b>STORY MODE</b>\n"
        "• /story to see chapters.\n"
        "• /story_chapter [num] to start a chapter.\n"
        "• Each chapter has a boss and rewards.\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        "🏰 <b>DUNGEON & TOWER</b>\n"
        "• /dungeon – infinite procedural floors.\n"
        "• /tower – 100 floors, boss every 10.\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"📌 <b>Owner</b>: {e(OWNER_NAME)}\n"
        "Type /commands for full command list."
    )
    await message.reply(guide_text, parse_mode="HTML")

@dp.message(Command("stats"))
@friendly_error
async def stats_cmd(message: types.Message):
    user_id = message.from_user.id
    async with db_pool.acquire() as conn:
        player = await conn.fetchrow("SELECT * FROM players WHERE user_id = $1", user_id)
        if not player:
            await message.reply("❌ Start with /start first!")
            return
        char_name = e(player.get('character_name') or "None")
        caption = (
            f"📊 <b>Combat Stats</b>\n"
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
        await message.reply(caption, parse_mode="HTML")

@dp.message(Command("addyenall"))
@friendly_error
async def addyenall_cmd(message: types.Message):
    if not await is_owner(message.from_user.id):
        await message.reply("❌ Owner only!")
        return
    args = message.text.split()
    if len(args) < 2:
        await message.reply("📝 Usage: /addyenall amount")
        return
    try:
        amount = int(args[1])
    except:
        await message.reply("❌ Please enter a valid number.")
        return
    if amount <= 0 or amount > MAX_YEN:
        await message.reply(f"❌ Amount must be between 1 and {MAX_YEN}.")
        return
    async with db_pool.acquire() as conn:
        await conn.execute("UPDATE players SET yen = LEAST(yen + $1, $2)", amount, MAX_YEN)
        count = await conn.fetchval("SELECT COUNT(*) FROM players")
        await message.reply(f"✅ Added ¥{amount:,} to all <b>{count}</b> players.", parse_mode="HTML")

@dp.message(Command("removeyenall"))
@friendly_error
async def removeyenall_cmd(message: types.Message):
    if not await is_owner(message.from_user.id):
        await message.reply("❌ Owner only!")
        return
    args = message.text.split()
    if len(args) < 2:
        await message.reply("📝 Usage: /removeyenall amount")
        return
    try:
        amount = int(args[1])
    except:
        await message.reply("❌ Please enter a valid number.")
        return
    if amount <= 0 or amount > MAX_YEN:
        await message.reply(f"❌ Amount must be between 1 and {MAX_YEN}.")
        return
    async with db_pool.acquire() as conn:
        await conn.execute("UPDATE players SET yen = GREATEST(yen - $1, 0)", amount)
        count = await conn.fetchval("SELECT COUNT(*) FROM players")
        await message.reply(f"✅ Removed ¥{amount:,} from all <b>{count}</b> players.", parse_mode="HTML")

@dp.message(Command("restriction"))
@friendly_error
async def restriction_cmd(message: types.Message):
    args = message.text.split()
    if len(args) < 2:
        await message.reply("📝 Usage: /restriction toji | /restriction maki")
        return
    user_id = message.from_user.id
    async with db_pool.acquire() as conn:
        player = await conn.fetchrow("SELECT * FROM players WHERE user_id = $1", user_id)
        if not player:
            await message.reply("❌ Start with /start first!")
            return
        if player['level'] < 10:
            await message.reply("❌ You need at least level 10 to choose a restriction.")
            return
        if player.get('restriction'):
            await message.reply("❌ You already have a restriction. You cannot change it.")
            return
        choice = args[1].lower()
        if choice == 'toji':
            await conn.execute("UPDATE players SET restriction = 'toji' WHERE user_id = $1", user_id)
            await update_player_stats(user_id)
            await safe_send_media(message, 'animation', EFFECTS["heavenly_restriction"], caption="🔒 <b>Heavenly Restriction: Toji Type</b>\nCE → 0, ATK/DEF/SPD ×2.")
        elif choice == 'maki':
            await conn.execute("UPDATE players SET restriction = 'maki' WHERE user_id = $1", user_id)
            await update_player_stats(user_id)
            await safe_send_media(message, 'animation', EFFECTS["heavenly_restriction"], caption="🔒 <b>Heavenly Restriction: Maki Type</b>\nWeapon mastery: +50% ATK from equipped weapons.")
        else:
            await message.reply("❌ Invalid restriction. Choose 'toji' or 'maki'.")

@dp.message(Command("vow"))
@friendly_error
async def vow_cmd(message: types.Message):
    args = message.text.split()
    if len(args) < 2:
        await message.reply("📝 Usage: /vow list | /vow [name]")
        return
    user_id = message.from_user.id
    async with db_pool.acquire() as conn:
        if args[1].lower() == 'list':
            vows = await conn.fetch("SELECT * FROM binding_vows")
            if not vows:
                await message.reply("No vows available.")
                return
            resp = "⚖️ <b>Binding Vows</b>\n━━━━━━━━━━━━━━━━━━━\n"
            for v in vows:
                resp += f"• <b>{e(v['name'])}</b>: {e(v['description'])} (Duration: {v['duration']} turns, Cooldown: {v['cooldown']} min)\n"
            resp += "\nUse /vow [name] to activate."
            await message.reply(resp, parse_mode="HTML")
            return
        name = " ".join(args[1:])
        vow = await conn.fetchrow("SELECT * FROM binding_vows WHERE name ILIKE $1", name)
        if not vow:
            await message.reply(f"❌ Vow '{name}' not found.")
            return
        player_vow = await conn.fetchrow("SELECT * FROM player_vows WHERE player_id = $1 AND vow_id = $2", user_id, vow['id'])
        if player_vow and player_vow.get('active'):
            await message.reply("⚠️ This vow is already active.")
            return
        if player_vow:
            last = player_vow.get('last_used')
            if last and (datetime.now() - last).total_seconds() < vow['cooldown'] * 60:
                remaining = int(vow['cooldown'] * 60 - (datetime.now() - last).total_seconds())
                await message.reply(f"⏳ Vow is on cooldown. Wait {remaining} seconds.")
                return
        await conn.execute("""
            INSERT INTO player_vows (player_id, vow_id, active, last_used, remaining_turns)
            VALUES ($1, $2, TRUE, NOW(), $3)
            ON CONFLICT (player_id, vow_id) DO UPDATE SET active = TRUE, last_used = NOW(), remaining_turns = $3
        """, user_id, vow['id'], vow['duration'])
        await message.reply(f"⚖️ <b>Binding Vow activated: {e(vow['name'])}</b>\n{e(vow['description'])}\nDuration: {vow['duration']} turns.", parse_mode="HTML")

@dp.message(Command("shikigami"))
@friendly_error
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
            resp = "🌀 <b>Megumi's Shikigami</b>\n━━━━━━━━━━━━━━━━━━━\n"
            for s in shikigami:
                resp += f"• <b>{e(s['name'])}</b>: {e(s['description'])} (CE: {s['ce_cost']})\n"
            resp += "\nUse /shikigami summon [name] in battle."
            await message.reply(resp, parse_mode="HTML")
            return
        if args[1].lower() == 'summon':
            if len(args) < 3:
                await message.reply("📝 Usage: /shikigami summon [name]")
                return
            s_name = " ".join(args[2:])
            shikigami = await conn.fetchrow("SELECT * FROM shikigami WHERE name ILIKE $1", s_name)
            if not shikigami:
                await message.reply(f"❌ Shikigami '{s_name}' not found.")
                return
            owned = await conn.fetchrow("SELECT * FROM player_shikigami WHERE player_id = $1 AND shikigami_id = $2", user_id, shikigami['id'])
            if not owned:
                await message.reply(f"❌ You don't own {shikigami['name']}. Defeat bosses to unlock.")
                return
            await safe_send_media(message, 'animation', EFFECTS["shikigami_summon"], caption=f"🌀 <b>{e(shikigami['name'])} summoned!</b>\nEffect: {e(shikigami['effect'])}")
        else:
            await message.reply("❌ Unknown subcommand. Use /shikigami to list or /shikigami summon [name].")

@dp.message(Command("profile"))
@friendly_error
async def profile_cmd(message: types.Message):
    user_id = message.from_user.id
    async with db_pool.acquire() as conn:
        player = await conn.fetchrow("SELECT * FROM players WHERE user_id = $1", user_id)
        if not player:
            await message.reply("❌ Start with /start first!")
            return
        player = await apply_passive_regen(dict(player))
        char_name = e(player.get('character_name'))
        image_url = None
        if char_name:
            char = await conn.fetchrow("SELECT image_url FROM characters WHERE name = $1", char_name)
            if char: image_url = char['image_url']
        weapon = e(player.get('equipped_weapon') or "None")
        title = e(player.get('equipped_title') or "None")
        awakening = e(player.get('awakening') or "None")
        clan_name = "None"
        if player.get('clan_id'):
            clan = await conn.fetchrow("SELECT name FROM clans WHERE id = $1", player['clan_id'])
            if clan: clan_name = e(clan['name'])
        restriction = e(player.get('restriction') or "None")
        curse_rank = e(player.get('curse_rank') or "None")
        rep_str = safe_rep_str(player.get('reputation'))
        prestige_lv = player.get('prestige_level', 0)
        caption = (
            f"👤 <b>Cursed Chronicle</b>\n"
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
            await safe_send_media(message, 'animation', EFFECTS["awakening"], caption=caption)
        elif image_url:
            await safe_send_media(message, 'photo', image_url, caption=caption)
        else:
            await message.reply(caption, parse_mode="HTML")

@dp.message(Command("characters"))
@friendly_error
async def characters_cmd(message: types.Message):
    async with db_pool.acquire() as conn:
        count = await conn.fetchval("SELECT COUNT(*) FROM characters")
        if count == 0:
            await message.reply("❌ No characters available.")
            return
        await send_char_page(message, 0)

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
                f"🎭 <b>{e(char['name'])}</b> - {e(char['rank'])}\n"
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
                buttons.append([InlineKeyboardButton(text=f"✅ Select {e(char['name'])}", callback_data=f"char_select_{char['id']}")])
            else:
                if char['price'] == 0:
                    buttons.append([InlineKeyboardButton(text=f"✅ Get Free {e(char['name'])}", callback_data=f"char_buy_free_{char['id']}")])
                else:
                    buttons.append([InlineKeyboardButton(text=f"💰 Buy {e(char['name'])} (¥{char['price']:,})", callback_data=f"char_buy_{char['id']}")])
            buttons.append([
                InlineKeyboardButton(text="⬅️", callback_data=f"char_page_{page-1}"),
                InlineKeyboardButton(text=f"{page+1}", callback_data="char_page_noop"),
                InlineKeyboardButton(text="➡️", callback_data=f"char_page_{page+1}")
            ])
            keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)

            if isinstance(message_or_callback, types.Message):
                msg = message_or_callback
                if char.get('image_url'):
                    await safe_send_media(msg, 'photo', char['image_url'], caption=caption, reply_markup=keyboard)
                else:
                    await msg.reply(caption, reply_markup=keyboard, parse_mode="HTML")
            else:
                callback = message_or_callback
                if char.get('image_url'):
                    await callback.message.edit_media(
                        InputMediaPhoto(media=char['image_url'], caption=caption),
                        reply_markup=keyboard
                    )
                else:
                    await callback.message.edit_text(caption, reply_markup=keyboard, parse_mode="HTML")
    except Exception as exc:
        if isinstance(message_or_callback, types.Message):
            await message_or_callback.reply(f"❌ An error occurred: {str(exc)[:150]}")
        else:
            await message_or_callback.answer("❌ An error occurred.", show_alert=True)

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
                await callback.answer("❌ Character not found!", show_alert=True)
                return
            owned = await conn.fetchrow("SELECT * FROM player_characters WHERE player_id = $1 AND character_name = $2",
                                        user_id, char['name'])
            if owned:
                await callback.answer("❌ You already own this character!", show_alert=True)
                await send_char_page(callback, int(parts[2]) if len(parts) > 2 else 0)
                return
            if not free:
                player = await conn.fetchrow("SELECT yen FROM players WHERE user_id = $1", user_id)
                if player['yen'] < char['price']:
                    await callback.answer(f"❌ Not enough Yen! Need ¥{char['price']:,}", show_alert=True)
                    return
                await conn.execute("UPDATE players SET yen = yen - $1 WHERE user_id = $2", char['price'], user_id)
                await conn.execute("INSERT INTO player_characters (player_id, character_name) VALUES ($1, $2)",
                                   user_id, char['name'])
                await callback.answer(f"✅ Bought {char['name']}!")
            else:
                await conn.execute("INSERT INTO player_characters (player_id, character_name) VALUES ($1, $2)",
                                   user_id, char['name'])
                await callback.answer(f"✅ Got {char['name']} for free!")
            await send_char_page(callback, 0)
    except Exception as exc:
        await callback.answer(f"❌ Error: {str(exc)[:100]}", show_alert=True)

@dp.callback_query(lambda c: c.data.startswith("char_select_"))
async def char_select_cb(callback: types.CallbackQuery):
    char_id = int(callback.data.split("_")[2])
    user_id = callback.from_user.id
    try:
        async with db_pool.acquire() as conn:
            char = await conn.fetchrow("SELECT * FROM characters WHERE id = $1", char_id)
            if not char:
                await callback.answer("❌ Character not found!", show_alert=True)
                return
            owned = await conn.fetchrow("SELECT * FROM player_characters WHERE player_id = $1 AND character_name = $2",
                                        user_id, char['name'])
            if not owned and char['price'] != 0:
                await callback.answer("❌ You don't own this character! Buy it first.", show_alert=True)
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
                f"✅ You selected <b>{e(char['name'])}</b> as your fighter!\n"
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
                await callback.message.edit_text(caption, reply_markup=None, parse_mode="HTML")
    except Exception as exc:
        await callback.answer(f"❌ Error: {str(exc)[:100]}", show_alert=True)

@dp.callback_query(lambda c: c.data == "char_page_noop")
async def char_page_noop(callback: types.CallbackQuery):
    await callback.answer("Current page")

@dp.message(Command("select"))
@friendly_error
async def select_cmd(message: types.Message):
    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        await message.reply("📝 Usage: /select \"character name\"")
        return
    name = args[1].strip()
    user_id = message.from_user.id
    async with db_pool.acquire() as conn:
        char = await conn.fetchrow("SELECT * FROM characters WHERE name ILIKE $1", name)
        if not char:
            await message.reply(f"❌ Character '{name}' not found.")
            return
        owned = await conn.fetchrow("SELECT * FROM player_characters WHERE player_id = $1 AND character_name = $2",
                                    user_id, char['name'])
        if not owned and char['price'] != 0:
            await message.reply(f"❌ You don't own {char['name']}! Buy it via /characters.")
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
        await message.reply(f"✅ Selected <b>{e(char['name'])}</b>! Check /profile", parse_mode="HTML")

@dp.message(Command("shop"))
@friendly_error
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
                await message_or_callback.reply("❌ Shop is empty.")
                return
            max_page = (total + per_page - 1) // per_page
            if page < 1: page = 1
            if page > max_page: page = max_page
            offset = (page - 1) * per_page
            items = await conn.fetch("SELECT * FROM shop_items ORDER BY category, name LIMIT $1 OFFSET $2", per_page, offset)
            response = f"🏪 <b>Jujutsu Shop — Page {page}/{max_page}</b>\n━━━━━━━━━━━━━━━━━━━\n"
            current_cat = None
            for it in items:
                if it['category'] != current_cat:
                    current_cat = it['category']
                    response += f"\n📌 <b>{current_cat.upper()}</b>\n"
                response += f"  • <b>{e(it['name'])}</b>\n"
                response += f"    💰 ¥{it['price']:,}\n"
                if it['effect']:
                    response += f"    ✨ {e(it['effect'].replace('|', ' | '))}\n"
                if it['description']:
                    response += f"    📖 {e(it['description'])}\n"
            response += "\n━━━━━━━━━━━━━━━━━━━\n"
            response += f"Page {page}/{max_page} — Use /shop [page] to jump\n"
            response += "Buy: /buy \"item name\""
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="⬅️", callback_data=f"shop_page_{page-1}"),
                 InlineKeyboardButton(text=f"{page}/{max_page}", callback_data="shop_page_noop"),
                 InlineKeyboardButton(text="➡️", callback_data=f"shop_page_{page+1}")]
            ])
            if isinstance(message_or_callback, types.Message):
                await message_or_callback.reply(response, reply_markup=keyboard, parse_mode="HTML")
            else:
                callback = message_or_callback
                await callback.message.edit_text(response, reply_markup=keyboard, parse_mode="HTML")
    except Exception as exc:
        if isinstance(message_or_callback, types.Message):
            await message_or_callback.reply(f"❌ An error occurred: {str(exc)[:150]}")
        else:
            await message_or_callback.answer("❌ An error occurred.", show_alert=True)

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
@friendly_error
async def buy_cmd(message: types.Message):
    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        await message.reply("📝 Usage: /buy \"item name\"")
        return
    item_name = args[1].strip()
    user_id = message.from_user.id
    async with db_pool.acquire() as conn:
        player = await conn.fetchrow("SELECT * FROM players WHERE user_id = $1", user_id)
        if not player:
            await message.reply("❌ Start with /start first!")
            return
        item = await conn.fetchrow("SELECT * FROM shop_items WHERE name ILIKE $1", item_name)
        if not item:
            await message.reply(f"❌ Item '{item_name}' not found in shop.")
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
        await message.reply(f"✅ Bought <b>{e(item['name'])}</b>!\n💰 Remaining: ¥{player['yen'] - item['price']:,}\n📦 Check /bag", parse_mode="HTML")

@dp.message(Command("bag"))
@friendly_error
async def bag_cmd(message: types.Message):
    user_id = message.from_user.id
    async with db_pool.acquire() as conn:
        player = await conn.fetchrow("SELECT * FROM players WHERE user_id = $1", user_id)
        if not player:
            await message.reply("❌ Start with /start first!")
            return
        bag = player.get('bag') or []
        techniques = player.get('techniques') or []
        domains = player.get('domains') or []
        if not bag and not techniques and not domains:
            await message.reply("📦 Your inventory is empty. Buy from /shop.")
            return
        resp = "📦 <b>Your Inventory</b>\n━━━━━━━━━━━━━━━━━━━\n"
        if bag:
            resp += "\n📦 <b>Items:</b>\n"
            for it in bag[:20]: resp += f"  • {e(it)}\n"
            if len(bag) > 20: resp += f"  ... and {len(bag)-20} more\n"
        if techniques:
            resp += "\n🌀 <b>Techniques:</b>\n"
            for t in techniques[:20]: resp += f"  • {e(t)}\n"
            if len(techniques) > 20: resp += f"  ... and {len(techniques)-20} more\n"
        if domains:
            resp += "\n🌐 <b>Domains:</b>\n"
            for d in domains[:10]: resp += f"  • {e(d)}\n"
            if len(domains) > 10: resp += f"  ... and {len(domains)-10} more\n"
        resp += "\n━━━━━━━━━━━━━━━━━━━\n"
        resp += "Use: /use \"item name\"\n"
        resp += "Equip: /equip \"weapon name\"\n"
        resp += "Learn: /learn \"tech name\""
        await message.reply(resp, parse_mode="HTML")

@dp.message(Command("use"))
@friendly_error
async def use_cmd(message: types.Message):
    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        await message.reply("📝 Usage: /use \"item name\"")
        return
    item_name = args[1].strip()
    user_id = message.from_user.id
    async with db_pool.acquire() as conn:
        player = await conn.fetchrow("SELECT * FROM players WHERE user_id = $1", user_id)
        if not player:
            await message.reply("❌ Start with /start first!")
            return
        bag = player.get('bag') or []
        if item_name not in bag:
            await message.reply(f"❌ You don't have '{item_name}' in your bag.")
            return
        item = await conn.fetchrow("SELECT * FROM shop_items WHERE name ILIKE $1", item_name)
        if not item:
            await message.reply(f"❌ Item '{item_name}' not found.")
            return
        effects = parse_effect(item['effect'])
        response = f"✅ Used <b>{e(item['name'])}</b>!\n━━━━━━━━━━━━━━━━━━━\n"
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
            await safe_send_media(message, 'animation', EFFECTS["heal"], caption=response)
        else:
            await message.reply(response, parse_mode="HTML")

@dp.message(Command("equip"))
@friendly_error
async def equip_cmd(message: types.Message):
    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        await message.reply("📝 Usage: /equip \"weapon name\"")
        return
    weapon_name = args[1].strip()
    user_id = message.from_user.id
    async with db_pool.acquire() as conn:
        player = await conn.fetchrow("SELECT * FROM players WHERE user_id = $1", user_id)
        if not player:
            await message.reply("❌ Start with /start first!")
            return
        bag = player.get('bag') or []
        if weapon_name not in bag:
            await message.reply(f"❌ You don't have '{weapon_name}' in your bag.")
            return
        weapon = await conn.fetchrow("SELECT * FROM shop_items WHERE name ILIKE $1 AND category = 'weapon'", weapon_name)
        if not weapon:
            await message.reply(f"❌ '{weapon_name}' is not a weapon.")
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
        await message.reply(f"✅ Equipped <b>{e(weapon_name)}</b>! (ATK +{atk_bonus}) Check /profile.", parse_mode="HTML")

@dp.message(Command("learn"))
@friendly_error
async def learn_cmd(message: types.Message):
    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        await message.reply("📝 Usage: /learn \"technique name\"")
        return
    raw_name = args[1].strip()
    normalized = " ".join(raw_name.split())
    user_id = message.from_user.id
    async with db_pool.acquire() as conn:
        player = await conn.fetchrow("SELECT * FROM players WHERE user_id = $1", user_id)
        if not player:
            await message.reply("❌ Start with /start first!")
            return
        techniques = player.get('techniques') or []
        domains = player.get('domains') or []

        matched_tech = None
        for t in techniques:
            if t.lower().strip() == normalized.lower():
                matched_tech = t
                break
        if matched_tech:
            await safe_send_media(
                message,
                'animation',
                EFFECTS["cursed_energy"],
                caption=f"🌀 <b>{e(matched_tech)}</b> is ready to use in battle!\nUse the 'Technique' button."
            )
            return

        matched_domain = None
        for d in domains:
            if d.lower().strip() == normalized.lower():
                matched_domain = d
                break
        if matched_domain:
            await message.reply(
                f"🌐 <b>{e(matched_domain)}</b> is a Domain Expansion.\n"
                f"Use the <b>'Domain'</b> button in battle to activate it.",
                parse_mode="HTML"
            )
            return

        await message.reply(f"❌ You don't own '{normalized}'. Buy it from /shop first.")

@dp.message(Command("techniques"))
@friendly_error
async def techniques_cmd(message: types.Message):
    user_id = message.from_user.id
    async with db_pool.acquire() as conn:
        player = await conn.fetchrow("SELECT techniques, character_name FROM players WHERE user_id = $1", user_id)
        if not player:
            await message.reply("❌ Start with /start first!")
            return
        techs = player.get('techniques') or []
        if not techs:
            await message.reply("🌀 You haven't learned any techniques. Buy from /shop and /learn.")
            return
        resp = "🌀 <b>Your Techniques</b>\n━━━━━━━━━━━━━━━━━━━\n"
        for t in techs:
            detail = await conn.fetchrow("SELECT * FROM techniques WHERE name = $1", t)
            if detail:
                char_req = detail.get('character_name') or "Universal"
                resp += f"  • {e(t)} (DMG: {detail['damage_multiplier']}x, CE: {detail['ce_cost']}, Character: {e(char_req)})\n"
            else:
                resp += f"  • {e(t)}\n"
        await message.reply(resp, parse_mode="HTML")

@dp.message(Command("enemies"))
@friendly_error
async def enemies_cmd(message: types.Message):
    async with db_pool.acquire() as conn:
        enemies = await conn.fetch("SELECT * FROM enemies ORDER BY is_boss DESC, rank")
        if not enemies:
            await message.reply("❌ No enemies found.")
            return
        bosses = [e for e in enemies if e['is_boss']]
        response = (
            f"👹 <b>Cursed Spirits</b>\n"
            f"━━━━━━━━━━━━━━━━━━━\n"
            f"Total: {len(enemies)}\n"
            f"👑 Bosses: {len(bosses)}\n"
            f"━━━━━━━━━━━━━━━━━━━\n"
            f"⚔️ Fight: /battle\n"
            f"👑 Boss: /boss [name]"
        )
        await message.reply(response, parse_mode="HTML")

@dp.message(Command("bosses"))
@friendly_error
async def bosses_cmd(message: types.Message):
    async with db_pool.acquire() as conn:
        rows = await conn.fetch("SELECT name, grade, level FROM enemies WHERE is_boss = TRUE ORDER BY name")
        if not rows:
            await message.reply("👹 No bosses available right now.")
            return
        txt = "👹 **Available Bosses:**\n\n"
        for r in rows:
            txt += f"• **{r['name']}** - Grade {r['grade']} (Lv.{r['level']})\n"
        await message.reply(txt, parse_mode="HTML")

@dp.message(Command("story"))
@friendly_error
async def story_cmd(message: types.Message):
    user_id = message.from_user.id
    async with db_pool.acquire() as conn:
        chapters = await conn.fetch("SELECT * FROM story_chapters ORDER BY chapter_num")
        if not chapters:
            await message.reply("❌ No story chapters available.")
            return
        player_progress = await conn.fetch("SELECT chapter_id FROM player_story WHERE player_id = $1 AND completed = TRUE", user_id)
        completed = [p['chapter_id'] for p in player_progress]
        resp = "📜 <b>Story Mode</b>\n━━━━━━━━━━━━━━━━━━━\n"
        for ch in chapters:
            status = "✅" if ch['id'] in completed else "🔒" if ch['id'] > len(completed) + 1 else "⏳"
            resp += f"{status} <b>Chapter {ch['chapter_num']}: {e(ch['title'])}</b>\n"
            resp += f"   {e(ch['description'])}\n"
            resp += f"   Boss: {e(ch['boss_name'])} | Rewards: ¥{ch['reward_yen']} + {ch['reward_xp']} XP\n"
        resp += "\nUse /story_chapter [number] to start a chapter."
        await message.reply(resp, parse_mode="HTML")

@dp.message(Command("story_chapter"))
@friendly_error
async def story_chapter_cmd(message: types.Message):
    args = message.text.split()
    if len(args) < 2:
        await message.reply("📝 Usage: /story_chapter [chapter number]")
        return
    try:
        chapter_num = int(args[1])
    except:
        await message.reply("❌ Invalid chapter number.")
        return
    user_id = message.from_user.id
    async with db_pool.acquire() as conn:
        chapter = await conn.fetchrow("SELECT * FROM story_chapters WHERE chapter_num = $1", chapter_num)
        if not chapter:
            await message.reply(f"❌ Chapter {chapter_num} not found.")
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
        await safe_send_media(message, 'animation', EFFECTS["story_boss"], caption=f"⚔️ <b>Story Chapter {chapter_num}: {e(chapter['title'])}</b>\nBoss: {e(chapter['boss_name'])}\nDefeat it to claim your rewards!")
        await boss_cmd(message, chapter['boss_name'], is_story=True, chapter_id=chapter['id'])

# ================================================================
# BOSS & BATTLE
# ================================================================
async def boss_cmd(message: types.Message, boss_name: str = None, is_story: bool = False, chapter_id: int = None):
    if boss_name is None:
        args = message.text.split(maxsplit=1)
        if len(args) < 2:
            await message.reply("📝 Usage: /boss \"boss name\"")
            return
        boss_name = args[1].strip()
    user_id = message.from_user.id
    if user_id in ongoing_battles:
        await message.reply("⚠️ You already have an ongoing battle! Use /status or /resume.")
        return
    try:
        async with db_pool.acquire() as conn:
            player = await conn.fetchrow("SELECT * FROM players WHERE user_id = $1", user_id)
            if not player:
                await message.reply("❌ Start with /start first!")
                return
            player = await regen_ce(dict(player))
            player = await apply_passive_regen(player)

            if is_story:
                enemy_base = await conn.fetchrow("SELECT * FROM enemies WHERE name ILIKE $1", boss_name)
            else:
                enemy_base = await conn.fetchrow("SELECT * FROM enemies WHERE name ILIKE $1 AND is_boss = TRUE", boss_name)

            if not enemy_base:
                await message.reply(f"❌ Enemy '{boss_name}' not found.")
                return

            enemy = scale_enemy_to_player(player, enemy_base)
            await safe_send_media(message, 'animation', EFFECTS["versus"])
            
            # --- NEW: Boss Cinematic Intro ---
            await message.reply(f"💥 **{enemy['name']}** appears!\n<i>{get_boss_intro(enemy['name'])}</i>", parse_mode="HTML")

            battle_id = await conn.fetchval("""
                INSERT INTO battles (chat_id, player1_id, current_hp1, current_hp2, 
                                     enemy_name, enemy_rank, enemy_atk, enemy_def, enemy_spd,
                                     is_boss, enemy_reward_yen, enemy_reward_xp, enemy_max_hp,
                                     vow_effects, participants, is_story, chapter_id)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15, $16, $17)
                RETURNING id
            """, message.chat.id, user_id, player['hp'], enemy['hp'], 
               enemy['name'], enemy['rank'], enemy['atk'], enemy['def'], enemy['spd'],
               enemy.get('is_boss', False), enemy.get('reward_yen', 5000), enemy.get('reward_xp', 500), enemy['hp'],
               json.dumps([]), json.dumps([user_id]), is_story, chapter_id)
            ongoing_battles[user_id] = battle_id
            battle_queues[battle_id] = {
                "participants": {user_id: []},
                "current_hp": enemy['hp'],
                "log": []
            }
            active_vows = await conn.fetch("""
                SELECT v.*, pv.remaining_turns 
                FROM player_vows pv 
                JOIN binding_vows v ON pv.vow_id = v.id 
                WHERE pv.player_id = $1 AND pv.active = TRUE
            """, user_id)
            vow_effects = [v['effect'] for v in active_vows]
            await conn.execute("UPDATE battles SET vow_effects = $1 WHERE id = $2", json.dumps(vow_effects), battle_id)
            await show_battle_turn(message, battle_id, player, enemy, vow_effects)
    except Exception as exc:
        await message.reply(f"❌ Error starting boss: {str(exc)[:150]}")

@dp.message(Command("boss"))
async def boss_cmd_handler(message: types.Message):
    await boss_cmd(message)

@dp.message(Command("battle"))
@friendly_error
async def battle_cmd(message: types.Message):
    user_id = message.from_user.id
    if user_id in ongoing_battles:
        await message.reply("⚠️ You already have an ongoing battle! Use /status or /resume.")
        return
    try:
        async with db_pool.acquire() as conn:
            player = await conn.fetchrow("SELECT * FROM players WHERE user_id = $1", user_id)
            if not player:
                await message.reply("❌ Start with /start first!")
                return
            player = await regen_ce(dict(player))
            player = await apply_passive_regen(player)

            enemy_base = await conn.fetchrow("SELECT * FROM enemies WHERE is_boss = FALSE ORDER BY RANDOM() LIMIT 1")
            if not enemy_base:
                await message.reply("❌ No enemies available!")
                return
            enemy = scale_enemy_to_player(player, enemy_base)
            await safe_send_media(message, 'animation', EFFECTS["versus"])
            battle_id = await conn.fetchval("""
                INSERT INTO battles (chat_id, player1_id, current_hp1, current_hp2, 
                                     enemy_name, enemy_rank, enemy_atk, enemy_def, enemy_spd,
                                     is_boss, enemy_reward_yen, enemy_reward_xp, enemy_max_hp,
                                     vow_effects, participants)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15)
                RETURNING id
            """, message.chat.id, user_id, player['hp'], enemy['hp'], 
               enemy['name'], enemy['rank'], enemy['atk'], enemy['def'], enemy['spd'],
               False, enemy.get('reward_yen', 1000), enemy.get('reward_xp', 100), enemy['hp'],
               json.dumps([]), json.dumps([user_id]))
            ongoing_battles[user_id] = battle_id
            set_session(user_id, "battle", battle_id=battle_id, role="player1")
            battle_queues[battle_id] = {
                "participants": {user_id: []},
                "current_hp": enemy['hp'],
                "log": []
            }
            active_vows = await conn.fetch("""
                SELECT v.*, pv.remaining_turns 
                FROM player_vows pv 
                JOIN binding_vows v ON pv.vow_id = v.id 
                WHERE pv.player_id = $1 AND pv.active = TRUE
            """, user_id)
            vow_effects = [v['effect'] for v in active_vows]
            await conn.execute("UPDATE battles SET vow_effects = $1 WHERE id = $2", json.dumps(vow_effects), battle_id)
            await show_battle_turn(message, battle_id, player, enemy, vow_effects)
    except Exception as exc:
        await message.reply(f"❌ Error starting battle: {str(exc)[:150]}")

async def show_battle_turn(message_or_callback, battle_id, player, enemy, vow_effects=[], log_lines=None):
    cp = get_combo_points(player['level'])
    queue = battle_queues.get(battle_id, {}).get('participants', {}).get(player['user_id'], [])
    used_cp = sum(m.get('cp_cost', 0) for m in queue)

    log_text = ""
    if battle_queues.get(battle_id, {}).get('log'):
        log_lines = battle_queues[battle_id]['log'][-5:]
        log_text = "\n".join(f"• {line}" for line in log_lines)
        log_text = f"\n📜 <b>Battle Log:</b>\n{log_text}\n"
    elif log_lines:
        log_text = "\n".join(f"• {line}" for line in log_lines[-5:])
        log_text = f"\n📜 <b>Battle Log:</b>\n{log_text}\n"

    keyboard_buttons = [
        [InlineKeyboardButton(text=f"⚔️ Attack (1 CP, 0 CE)", callback_data=f"bt|add|{battle_id}|attack|1|0")],
        [InlineKeyboardButton(text=f"🛡️ Defend (1 CP, 0 CE)", callback_data=f"bt|add|{battle_id}|defend|1|0")],
        [InlineKeyboardButton(text=f"💥 Special (2 CP, 30 CE)", callback_data=f"bt|add|{battle_id}|special|2|30")],
        [InlineKeyboardButton(text="🌀 Technique", callback_data=f"bt|tech|{battle_id}")],
        [InlineKeyboardButton(text="🌐 Domain", callback_data=f"bt|domain|{battle_id}")],
    ]
    if player.get('character_name') == 'Megumi Fushiguro':
        keyboard_buttons.append([InlineKeyboardButton(text="🌀 Shikigami", callback_data=f"bt|shikigami|{battle_id}")])
    keyboard_buttons.append([
        InlineKeyboardButton(text=f"▶️ Execute Combo ({used_cp}/{cp} CP used)", callback_data=f"bt|execute|{battle_id}"),
        InlineKeyboardButton(text="🏃 Run", callback_data=f"bt|run|{battle_id}")
    ])
    keyboard = InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)

    hp_bar = build_hp_bar(player['hp'], player['max_hp'])
    ce_bar = build_ce_bar(player['ce'], player['max_ce'])
    enemy_hp_bar = build_hp_bar(enemy['hp'], enemy['max_hp'])

    quote = get_jjk_quote(player.get('character_name'))
    caption = (
        f"⚔️ <b>BATTLE</b>\n"
        f"━━━━━━━━━━━━━━━━━━━\n"
        f"🧙 {e(player.get('character_name') or 'You')}\n"
        f"❤️ HP: {player['hp']}/{player['max_hp']} {hp_bar}\n"
        f"🔵 CE: {player['ce']}/{player['max_ce']} {ce_bar}\n"
        f"━━━━━━━━━━━━━━━━━━━\n"
        f"💀 <b>{e(enemy['name'])}</b> - {e(enemy['rank'])}\n"
        f"❤️ HP: {enemy['hp']} {enemy_hp_bar}\n"
        f"━━━━━━━━━━━━━━━━━━━\n"
        f"🌀 Combo Points: {cp} (used: {used_cp})\n"
        f"Select moves, then press Execute Combo.\n"
        f"{log_text}\n"
        f"<i>{quote}</i>"
    )

    if isinstance(message_or_callback, types.Message):
        msg = message_or_callback
        if enemy.get('image_url'):
            await safe_send_media(msg, 'photo', enemy['image_url'], caption=caption, reply_markup=keyboard)
        else:
            await msg.reply(caption, reply_markup=keyboard, parse_mode="HTML")
    else:
        callback = message_or_callback
        media_url = enemy.get('image_url') or EFFECTS["default_domain"]
        await edit_battle_message(callback, caption, keyboard, media_url)

# ---------- BATTLE CALLBACK (bt|) – FULL ----------
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
    elif action == "shikigami":
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
    elif action == "addshikigami":
        battle_id = int(parts[2])
        shikigami_id = int(parts[3])
        cp_cost = int(parts[4])
        ce_cost = int(parts[5])
    else:
        await callback.answer("❌ Unknown action.", show_alert=True)
        return

    user_id = callback.from_user.id
    try:
        async with db_pool.acquire() as conn:
            battle = await conn.fetchrow("SELECT * FROM battles WHERE id = $1", battle_id)
            if not battle or battle['status'] != 'active':
                await callback.answer("❌ Battle expired!", show_alert=True)
                return

            if battle.get('is_pvp'):
                if user_id not in (battle['player1_id'], battle['player2_id']):
                    await callback.answer("❌ You are not in this battle.", show_alert=True)
                    return
            else:
                if user_id != battle['player1_id']:
                    await callback.answer("❌ You are not the player in this battle.", show_alert=True)
                    return

            player_record = await conn.fetchrow("SELECT * FROM players WHERE user_id = $1", user_id)
            if not player_record:
                await callback.answer("❌ Player not found!", show_alert=True)
                return
            player = dict(player_record)

            player = await apply_vows_to_player(user_id, player)

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
                    await callback.answer("❌ Enemy not found.", show_alert=True)
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

            # --- SHIKIGAMI selection ---
            if action == "shikigami":
                if player.get('character_name') != 'Megumi Fushiguro':
                    await callback.answer("❌ Only Megumi can summon shikigami.", show_alert=True)
                    return
                shikigami_list = await conn.fetch("""
                    SELECT s.* FROM shikigami s
                    JOIN player_shikigami ps ON s.id = ps.shikigami_id
                    WHERE ps.player_id = $1
                """, user_id)
                if not shikigami_list:
                    await callback.answer("❌ You have no shikigami. Defeat bosses to unlock.", show_alert=True)
                    return
                buttons = []
                for s in shikigami_list:
                    ce_cost = s['ce_cost']
                    cp_cost = 2
                    buttons.append([InlineKeyboardButton(
                        text=f"🌀 {s['name']} ({cp_cost} CP, {ce_cost} CE)",
                        callback_data=f"bt|addshikigami|{battle_id}|{s['id']}|{cp_cost}|{ce_cost}"
                    )])
                buttons.append([InlineKeyboardButton(text="🔙 Back", callback_data=f"bt|back|{battle_id}")])
                markup = InlineKeyboardMarkup(inline_keyboard=buttons)
                await callback.message.edit_text(
                    f"🌀 <b>Select a Shikigami</b>\nChoose a shikigami to add to your combo.",
                    reply_markup=markup, parse_mode="HTML"
                )
                await callback.answer()
                return

            # --- ADD SHIKIGAMI to queue ---
            if action == "addshikigami":
                shikigami_id = int(parts[3])
                cp_cost = int(parts[4])
                ce_cost = int(parts[5])
                cp = get_combo_points(player['level'])
                used_cp = sum(m.get('cp_cost', 0) for m in queue)
                if used_cp + cp_cost > cp:
                    await callback.answer(f"❌ Not enough Combo Points! (Used {used_cp}/{cp})", show_alert=True)
                    return
                total_ce = sum(m.get('ce_cost', 0) for m in queue) + ce_cost
                if player['ce'] < total_ce:
                    await callback.answer(f"❌ Not enough CE! Need {total_ce}, have {player['ce']}", show_alert=True)
                    return
                shikigami = await conn.fetchrow("SELECT * FROM shikigami WHERE id = $1", shikigami_id)
                if not shikigami:
                    await callback.answer("❌ Shikigami not found.", show_alert=True)
                    return
                move = {"type": "shikigami", "cp_cost": cp_cost, "ce_cost": ce_cost, "shikigami_id": shikigami_id, "shikigami_name": shikigami['name']}
                queue.append(move)
                await callback.answer(f"✅ Added {shikigami['name']}!")
                await show_battle_turn(callback, battle_id, player, enemy, vow_effects)
                return

            # --- ADD regular moves ---
            if action == "add":
                cp = get_combo_points(player['level'])
                used_cp = sum(m.get('cp_cost', 0) for m in queue)
                if used_cp + cp_cost > cp:
                    await callback.answer(f"❌ Not enough Combo Points! (Used {used_cp}/{cp})", show_alert=True)
                    return
                total_ce = sum(m.get('ce_cost', 0) for m in queue) + ce_cost
                if player['ce'] < total_ce:
                    await callback.answer(f"❌ Not enough CE! Need {total_ce}, have {player['ce']}", show_alert=True)
                    return
                move = {"type": move_type, "cp_cost": cp_cost, "ce_cost": ce_cost}
                queue.append(move)
                await callback.answer(f"✅ Added {move_type}!")
                await show_battle_turn(callback, battle_id, player, enemy, vow_effects)

            # --- TECHNIQUE selection ---
            elif action == "tech":
                techs = player.get('techniques') or []
                if not techs:
                    await callback.answer("❌ You have no techniques!", show_alert=True)
                    return
                player_char = player.get('character_name')
                compatible = []
                for t in techs:
                    tech = await conn.fetchrow("SELECT * FROM techniques WHERE name = $1", t)
                    if tech:
                        if tech.get('character_name') is None or tech['character_name'] == player_char:
                            compatible.append(t)
                if not compatible:
                    await callback.answer("❌ No techniques compatible with your current character!", show_alert=True)
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
                    f"🌀 <b>Select a Technique</b>\nChoose a technique to add to your combo.",
                    reply_markup=markup, parse_mode="HTML"
                )
                await callback.answer()

            # --- DOMAIN selection ---
            elif action == "domain":
                domains = player.get('domains') or []
                if not domains:
                    await callback.answer("❌ You have no domains!", show_alert=True)
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
                    await callback.answer("❌ No domains compatible with your current character!", show_alert=True)
                    return
                buttons = []
                for d in compatible[:5]:
                    domain = await conn.fetchrow("SELECT * FROM techniques WHERE name = $1 AND category = 'domain'", d)
                    if domain:
                        ce_cost = domain['ce_cost']
                        dmg_mult = float(domain['damage_multiplier']) if domain else 3.5
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
                    f"🌐 <b>Select a Domain</b>\nChoose a domain to add to your combo.",
                    reply_markup=markup, parse_mode="HTML"
                )
                await callback.answer()

            # --- BACK to battle ---
            elif action == "back":
                await show_battle_turn(callback, battle_id, player, enemy, vow_effects)
                await callback.answer()

            # --- ADD TECH to queue ---
            elif action == "addtech":
                tech = await conn.fetchrow("SELECT * FROM techniques WHERE name = $1", tech_name)
                if tech and tech.get('character_name') is not None and tech['character_name'] != player.get('character_name'):
                    await callback.answer("❌ This technique is not compatible with your character!", show_alert=True)
                    return
                cp = get_combo_points(player['level'])
                used_cp = sum(m.get('cp_cost', 0) for m in queue)
                if used_cp + cp_cost > cp:
                    await callback.answer(f"❌ Not enough Combo Points! (Used {used_cp}/{cp})", show_alert=True)
                    return
                total_ce = sum(m.get('ce_cost', 0) for m in queue) + ce_cost
                if player['ce'] < total_ce:
                    await callback.answer(f"❌ Not enough CE! Need {total_ce}, have {player['ce']}", show_alert=True)
                    return
                move = {"type": "technique", "cp_cost": cp_cost, "ce_cost": ce_cost, "tech_name": tech_name}
                queue.append(move)
                await callback.answer(f"✅ Added {tech_name}!")
                await show_battle_turn(callback, battle_id, player, enemy, vow_effects)

            # --- ADD DOMAIN to queue ---
            elif action == "adddomain":
                domain = await conn.fetchrow("SELECT * FROM techniques WHERE name = $1 AND category = 'domain'", domain_name)
                if domain and domain.get('character_name') is not None and domain['character_name'] != player.get('character_name'):
                    await callback.answer("❌ This domain is not compatible with your character!", show_alert=True)
                    return
                cp = get_combo_points(player['level'])
                used_cp = sum(m.get('cp_cost', 0) for m in queue)
                if used_cp + cp_cost > cp:
                    await callback.answer(f"❌ Not enough Combo Points! (Used {used_cp}/{cp})", show_alert=True)
                    return
                total_ce = sum(m.get('ce_cost', 0) for m in queue) + ce_cost
                if player['ce'] < total_ce:
                    await callback.answer(f"❌ Not enough CE! Need {total_ce}, have {player['ce']}", show_alert=True)
                    return
                move = {"type": "domain", "cp_cost": cp_cost, "ce_cost": ce_cost, "domain_name": domain_name, "dmg_mult": dmg_mult}
                queue.append(move)
                await callback.answer(f"✅ Added {domain_name}!")
                await show_battle_turn(callback, battle_id, player, enemy, vow_effects)

            # --- EXECUTE combo ---
            elif action == "execute":
                if not queue:
                    await callback.answer("❌ No moves in queue!", show_alert=True)
                    return
                total_ce = sum(m.get('ce_cost', 0) for m in queue)
                if player['ce'] < total_ce:
                    await callback.answer(f"❌ Not enough CE! Need {total_ce}, have {player['ce']}", show_alert=True)
                    return
                await conn.execute("UPDATE players SET ce = ce - $1 WHERE user_id = $2", total_ce, player['user_id'])
                player['ce'] -= total_ce

                exec_log = []
                total_damage = 0
                defend_flag = False
                black_flash_triggered = False

                for move in queue:
                    mtype = move['type']
                    if mtype == 'attack':
                        base_dmg = player['atk'] * random.uniform(0.8, 1.2)
                        reduction = enemy['def'] * 0.5
                        dmg = max(1, int(base_dmg - reduction))
                        if random.random() < 0.01:
                            dmg = int(dmg * 2.5)
                            black_flash_triggered = True
                            await safe_send_media(callback.message, 'animation', EFFECTS["black_flash"], caption="⚡ BLACK FLASH!")
                            await conn.execute("UPDATE players SET black_flash_count = black_flash_count + 1 WHERE user_id = $1", user_id)
                        total_damage += dmg
                        exec_log.append(f"⚔️ Attack: {dmg} damage" + (" (Black Flash!)" if black_flash_triggered else ""))
                    elif mtype == 'defend':
                        defend_flag = True
                        exec_log.append("🛡️ Defend (halves next enemy damage)")
                    elif mtype == 'special':
                        base_dmg = player['atk'] * random.uniform(1.5, 2.5)
                        reduction = enemy['def'] * 0.5
                        dmg = max(1, int(base_dmg - reduction))
                        total_damage += dmg
                        exec_log.append(f"💥 Special: {dmg} damage")
                    elif mtype == 'technique':
                        tech_name = move.get('tech_name')
                        tech = await conn.fetchrow("SELECT * FROM techniques WHERE name = $1", tech_name)
                        if tech:
                            base_dmg = player['atk'] * float(tech['damage_multiplier']) * random.uniform(0.9, 1.1)
                            reduction = enemy['def'] * 0.5
                            dmg = max(1, int(base_dmg - reduction))
                            total_damage += dmg
                            exec_log.append(f"🌀 {tech_name}: {dmg} damage")
                            if "Purple" in tech_name:
                                await safe_send_media(callback.message, 'animation', EFFECTS["gojo_purple"])
                            elif "Red" in tech_name:
                                await safe_send_media(callback.message, 'animation', EFFECTS["gojo_red"])
                            elif "Blue" in tech_name:
                                await safe_send_media(callback.message, 'animation', EFFECTS["gojo_blue"])
                            else:
                                await safe_send_media(callback.message, 'animation', EFFECTS["cursed_energy"])
                    elif mtype == 'domain':
                        domain_name = move.get('domain_name')
                        dmg_mult = move.get('dmg_mult', 3.5)
                        dmg = max(1, int(player['atk'] * float(dmg_mult) * random.uniform(0.9, 1.1)))
                        total_damage += dmg
                        exec_log.append(f"🌐 <b>Domain: {domain_name}</b> (Sure-Hit, {dmg} damage)")
                        if "Unlimited Void" in domain_name:
                            await safe_send_media(callback.message, 'animation', EFFECTS["gojo_unlimited_void"])
                        elif "Malevolent" in domain_name:
                            await safe_send_media(callback.message, 'animation', EFFECTS["sukuna_domain"])
                        elif "Mahito" in domain_name or "Self" in domain_name:
                            await safe_send_media(callback.message, 'animation', EFFECTS["mahito_domain"])
                        else:
                            await safe_send_media(callback.message, 'animation', EFFECTS["default_domain"])
                    elif mtype == 'shikigami':
                        shikigami_id = move.get('shikigami_id')
                        shikigami = await conn.fetchrow("SELECT * FROM shikigami WHERE id = $1", shikigami_id)
                        if shikigami:
                            if "Divine Dogs" in shikigami['name']:
                                atk_bonus = int(player['atk'] * 0.2)
                                base_dmg = (player['atk'] + atk_bonus) * random.uniform(0.8, 1.2)
                                reduction = enemy['def'] * 0.5
                                dmg = max(1, int(base_dmg - reduction))
                                exec_log.append(f"🌀 {shikigami['name']} (ATK+20%, {dmg} damage)")
                            elif "Nue" in shikigami['name']:
                                dmg = max(1, int(player['atk'] * random.uniform(0.6, 0.9)))
                                battle_queues[battle_id]['stun'] = True
                                exec_log.append(f"🌀 {shikigami['name']} (stuns enemy, {dmg} damage)")
                            elif "Mahoraga" in shikigami['name']:
                                dmg = max(1, int(player['atk'] * 8 * random.uniform(0.9, 1.1)))
                                exec_log.append(f"🌀 {shikigami['name']} (8x damage, {dmg} damage)")
                            else:
                                base_dmg = player['atk'] * random.uniform(0.8, 1.2)
                                reduction = enemy['def'] * 0.5
                                dmg = max(1, int(base_dmg - reduction))
                                exec_log.append(f"🌀 {shikigami['name']} ({dmg} damage)")
                            total_damage += dmg
                            await safe_send_media(callback.message, 'animation', EFFECTS["shikigami_summon"], caption=f"🌀 {shikigami['name']} summoned!")

                # Apply damage
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

                # Enemy counter-attack (PvE only)
                if not battle.get('is_pvp'):
                    enemy_dmg = 0
                    if battle_queues.get(battle_id, {}).get('stun'):
                        exec_log.append("🌀 Enemy is stunned! No counter-attack.")
                        battle_queues[battle_id]['stun'] = False
                    elif not defend_flag:
                        enemy_dmg = max(1, int(enemy['atk'] * random.uniform(0.5, 0.9)))
                        exec_log.append(f"💢 Enemy counter‑attack: {enemy_dmg} damage")
                    else:
                        enemy_dmg = max(1, int(enemy['atk'] * random.uniform(0.2, 0.4)))
                        exec_log.append(f"🛡️ Enemy damage reduced to {enemy_dmg} (Defend)")
                        await conn.execute("UPDATE battles SET defend_flag = FALSE WHERE id = $1", battle_id)
                    new_player_hp = max(0, battle['current_hp1'] - enemy_dmg)
                    await conn.execute("UPDATE battles SET current_hp1 = $1 WHERE id = $2", new_player_hp, battle_id)
                    player['hp'] = new_player_hp
                else:
                    new_player_hp = battle['current_hp1']

                battle_queues[battle_id]['log'].extend(exec_log)
                if len(battle_queues[battle_id]['log']) > 10:
                    battle_queues[battle_id]['log'] = battle_queues[battle_id]['log'][-10:]

                battle_queues[battle_id]['participants'][user_id] = []

                # --- Check victory/defeat ---
                if battle.get('is_pvp'):
                    other_hp = battle_queues[battle_id]['current_hp']
                    if other_hp <= 0:
                        await safe_send_media(callback.message, 'animation', EFFECTS["victory_normal"])
                        winner_id = user_id
                        loser_id = other_id
                        await conn.execute("UPDATE players SET wins = wins + 1, yen = LEAST(yen + 1000, $1), xp = xp + 500 WHERE user_id = $2", MAX_YEN, winner_id)
                        await conn.execute("UPDATE players SET losses = losses + 1 WHERE user_id = $1", loser_id)
                        await update_player_stats(winner_id)
                        await update_player_stats(loser_id)
                        await check_achievements(winner_id)
                        await update_missions(winner_id, "wins", 1)
                        await update_quests(winner_id, "wins", 1)
                        summary = f"🎉 <b>PVP VICTORY!</b>\nPlayer {winner_id} wins against {loser_id}!"
                        await callback.message.edit_text(summary, parse_mode="HTML")
                        if winner_id in ongoing_battles: del ongoing_battles[winner_id]
                        if loser_id in ongoing_battles: del ongoing_battles[loser_id]
                        if battle_id in battle_queues: del battle_queues[battle_id]
                        clear_session(winner_id)
                        clear_session(loser_id)
                        await callback.answer("🎉 Victory!")
                        return
                else:
                    if new_enemy_hp <= 0:
                        is_boss = battle['is_boss']
                        is_story = battle.get('is_story', False)
                        chapter_id = battle.get('chapter_id')
                        victory_effect = EFFECTS["victory_boss"] if is_boss else EFFECTS["victory_normal"]
                        await safe_send_media(callback.message, 'animation', victory_effect)
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
                        await check_achievements(user_id)
                        await update_missions(user_id, "wins", 1)

                        # --- NEW: 1. CURSE MARKS (RNG Fragment Drops) ---
                        if is_boss and random.random() < 0.05:
                            frag_name = f"{battle['enemy_name']} Fragment"
                            await conn.execute("UPDATE players SET cursed_marks = cursed_marks || $1 WHERE user_id = $2", json.dumps([frag_name]), user_id)
                            await callback.message.reply(f"🌀 **Curse Mark Absorbed!** You have absorbed the power of {e(battle['enemy_name'])}! (+{frag_name})")

                        # --- NEW: 2. SEASON PASS PROGRESSION ---
                        await conn.execute("UPDATE players SET season_progress = season_progress + 1 WHERE user_id = $1", user_id)
                        season_prog = await conn.fetchval("SELECT season_progress FROM players WHERE user_id = $1", user_id)
                        if season_prog % 10 == 0 and season_prog > 0:
                            await callback.message.reply(f"📅 **Season Pass Progress!** You reached Tier {season_prog//10} in {CURRENT_SEASON}!")

                        # --- NEW: 3. HALL OF FAME (Legendary Broadcasts) ---
                        if player.get('legendary_tag') == False:
                            milestone = False
                            if player['level'] >= 100: milestone = True
                            elif player['prestige_level'] >= 5: milestone = True
                            if milestone:
                                await conn.execute("UPDATE players SET legendary_tag = TRUE WHERE user_id = $1", user_id)
                                all_users = await conn.fetch("SELECT user_id FROM players")
                                for u in all_users:
                                    try:
                                        await bot.send_message(u['user_id'], f"🌍 **BREAKING NEWS!** {e(player['username'])} has achieved Legendary status! The age of sorcerers is upon us!")
                                    except: pass

                        if is_boss:
                            await update_missions(user_id, "boss_kills", 1)
                            await update_quests(user_id, "boss_kills", 1)
                            # Curse evolution
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
                                await safe_send_media(callback.message, 'animation', EFFECTS["curse_evolution"], caption=f"👹 <b>Curse Evolution!</b> You evolved to {e(new_rank)}!")
                                if new_rank in ["Special Grade", "Disaster Curse"]:
                                    await conn.execute("UPDATE players SET curse_regen = TRUE WHERE user_id = $1", user_id)
                                    await callback.message.reply("You now have passive regeneration out of battle.")
                            # Random domain drop
                            if random.random() < 0.10:
                                domains = player.get('domains') or []
                                available = ['Unlimited Void', 'Malevolent Shrine', 'Shadow Garden', 'Idle Death Gamble', 'Self-Embodiment', 'Womb Profusion', 'Coffin of the Iron Mountain']
                                new_domain = None
                                for d in available:
                                    if d not in domains:
                                        new_domain = d
                                        break
                                if new_domain:
                                    await conn.execute("UPDATE players SET domains = array_append(domains, $1) WHERE user_id = $2", new_domain, player['user_id'])
                                    await safe_send_media(callback.message, 'animation', EFFECTS["awakening"], caption=f"🌐 <b>Domain Unlocked!</b> You gained <b>{e(new_domain)}</b>!")

                        if is_story and chapter_id:
                            await conn.execute("""
                                INSERT INTO player_story (player_id, chapter_id, completed)
                                VALUES ($1, $2, TRUE)
                                ON CONFLICT (player_id, chapter_id) DO UPDATE SET completed = TRUE
                            """, player['user_id'], chapter_id)
                            chapter = await conn.fetchrow("SELECT * FROM story_chapters WHERE id = $1", chapter_id)
                            if chapter and chapter.get('reward_title'):
                                await callback.message.reply(f"📜 <b>Story Chapter Completed!</b>\nYou earned the title: {e(chapter['reward_title'])}", parse_mode="HTML")

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
                                    await callback.message.reply("🏆 <b>Tower Complete!</b> You have cleared all 100 floors! 🎉", parse_mode="HTML")
                                else:
                                    await callback.message.reply(f"🗼 You climb to floor {floor+1}!")

                        full_log = battle_queues[battle_id].get('log', [])
                        log_summary = "\n".join(f"• {line}" for line in full_log[-10:])
                        summary = (
                            f"🎉 <b>VICTORY!</b>\n"
                            f"━━━━━━━━━━━━━━━━━━━\n"
                            f"<b>Battle Log:</b>\n{log_summary}\n"
                            f"━━━━━━━━━━━━━━━━━━━\n"
                            f"❤️ Your HP: {new_player_hp}  |  💀 {e(enemy['name'])} HP: 0\n"
                            f"💰 +¥{yen_reward}\n"
                            f"⭐ +{xp_reward} XP"
                        )
                        await callback.message.edit_text(summary, parse_mode="HTML")
                        if user_id in ongoing_battles: del ongoing_battles[user_id]
                        if battle_id in battle_queues: del battle_queues[battle_id]
                        clear_session(user_id)
                        await callback.answer("🎉 Victory!")
                        return

                if new_player_hp <= 0:
                    await safe_send_media(callback.message, 'animation', EFFECTS["defeat"])
                    await conn.execute("UPDATE players SET losses = losses + 1 WHERE user_id = $1", player['user_id'])
                    full_log = battle_queues[battle_id].get('log', [])
                    log_summary = "\n".join(f"• {line}" for line in full_log[-10:])
                    summary = (
                        f"💀 <b>DEFEAT!</b>\n"
                        f"━━━━━━━━━━━━━━━━━━━\n"
                        f"<b>Battle Log:</b>\n{log_summary}\n"
                        f"━━━━━━━━━━━━━━━━━━━\n"
                        f"❤️ Your HP: 0  |  💀 {e(enemy['name'])} HP: {enemy['hp']}\n"
                        f"Better luck next time!"
                    )
                    await callback.message.edit_text(summary, parse_mode="HTML")
                    if user_id in ongoing_battles: del ongoing_battles[user_id]
                    if battle_id in battle_queues: del battle_queues[battle_id]
                    clear_session(user_id)
                    await callback.answer("💀 Defeated!")
                    return

                enemy['hp'] = battle_queues[battle_id]['current_hp']
                log_lines = battle_queues[battle_id].get('log', [])
                await show_battle_turn(callback, battle_id, player, enemy, vow_effects, log_lines)
                await callback.answer("✅ Combo executed!")

            # --- RUN ---
            elif action == "run":
                if random.random() < 0.6:
                    await callback.message.edit_text("🏃 You successfully escaped!", parse_mode="HTML")
                    if user_id in ongoing_battles: del ongoing_battles[user_id]
                    if battle_id in battle_queues: del battle_queues[battle_id]
                    clear_session(user_id)
                    await callback.answer("🏃 Escaped!")
                else:
                    enemy_dmg = max(1, int(enemy['atk'] * random.uniform(0.8, 1.2)))
                    new_hp = max(0, battle['current_hp1'] - enemy_dmg)
                    await conn.execute("UPDATE battles SET current_hp1 = $1 WHERE id = $2", new_hp, battle_id)
                    if new_hp <= 0:
                        await conn.execute("UPDATE players SET losses = losses + 1 WHERE user_id = $1", player['user_id'])
                        await safe_send_media(callback.message, 'animation', EFFECTS["defeat"])
                        await callback.message.edit_text("💀 <b>DEFEAT!</b>\nFailed to escape.", parse_mode="HTML")
                        if user_id in ongoing_battles: del ongoing_battles[user_id]
                        if battle_id in battle_queues: del battle_queues[battle_id]
                        clear_session(user_id)
                        await callback.answer("💀 Defeated!")
                        return
                    player['hp'] = new_hp
                    await show_battle_turn(callback, battle_id, player, enemy, vow_effects)
                    await callback.answer("❌ Failed to escape! Enemy attacked.")

    except Exception as exc:
        await callback.answer(f"❌ Error: {str(exc)[:100]}", show_alert=True)

# ================================================================
# PVP – FULL UPGRADED IMPLEMENTATION
# ================================================================

@dp.message(Command("pvp_challenge"))
@friendly_error
async def pvp_challenge(message: types.Message):
    args = message.text.split()
    if len(args) < 2:
        await message.reply("📝 Usage: /pvp_challenge @user")
        return
    target = args[1].replace("@", "")
    challenger = message.from_user.id

    if get_session(challenger):
        await message.reply("⚠️ You're already in a battle or session!")
        return

    async with db_pool.acquire() as conn:
        target_user = await conn.fetchrow("SELECT * FROM players WHERE username ILIKE $1", target)
        if not target_user:
            await message.reply("❌ User not found.")
            return
        if target_user['user_id'] == challenger:
            await message.reply("❌ You can't challenge yourself.")
            return
        if get_session(target_user['user_id']):
            await message.reply("❌ That user is currently in a session.")
            return
        if challenger in ongoing_battles or target_user['user_id'] in ongoing_battles:
            await message.reply("❌ One of you is already in a battle.")
            return

        player1 = await conn.fetchrow("SELECT * FROM players WHERE user_id = $1", challenger)
        player2 = target_user
        battle_id = await conn.fetchval("""
            INSERT INTO battles (chat_id, player1_id, player2_id, current_hp1, current_hp2, is_pvp, status, turn, timeout)
            VALUES ($1, $2, $3, $4, $5, TRUE, 'pending', 1, NOW() + INTERVAL '60 seconds')
            RETURNING id
        """, message.chat.id, challenger, target_user['user_id'], player1['hp'], player2['hp'])
        pvp_matches[battle_id] = {'challenger': challenger, 'target': target_user['user_id'], 'turn': 1}
        await message.reply(
            f"⚔️ <b>PVP Challenge sent to {e(target)}!</b>\n"
            f"They have 60 seconds to type /pvp_accept {battle_id}.\n"
            f"<i>{get_jjk_quote(player1.get('character_name'))}</i>",
            parse_mode="HTML"
        )

@dp.message(Command("pvp_accept"))
@friendly_error
async def pvp_accept(message: types.Message):
    args = message.text.split()
    if len(args) < 2:
        return
    battle_id = int(args[1])
    user_id = message.from_user.id

    async with db_pool.acquire() as conn:
        battle = await conn.fetchrow("SELECT * FROM battles WHERE id = $1 AND is_pvp = TRUE", battle_id)
        if not battle or battle['status'] != 'pending':
            await message.reply("❌ Invalid or expired battle.")
            return
        if battle['player2_id'] != user_id:
            await message.reply("❌ This battle is not for you.")
            return

        set_session(battle['player1_id'], "pvp", battle_id=battle_id)
        set_session(battle['player2_id'], "pvp", battle_id=battle_id)

        await conn.execute("UPDATE battles SET status = 'active', timeout = NOW() + INTERVAL '60 seconds' WHERE id = $1", battle_id)
        ongoing_battles[battle['player1_id']] = battle_id
        ongoing_battles[battle['player2_id']] = battle_id

        p1 = await conn.fetchrow("SELECT * FROM players WHERE user_id = $1", battle['player1_id'])
        p2 = await conn.fetchrow("SELECT * FROM players WHERE user_id = $1", battle['player2_id'])

        battle_queues[battle_id] = {
            "participants": {battle['player1_id']: [], battle['player2_id']: []},
            "current_hp1": battle['current_hp1'],
            "current_hp2": battle['current_hp2'],
            "log": [],
            "pvp": True,
            "turn": 1,
            "player1": dict(p1),
            "player2": dict(p2),
            "chat_id": message.chat.id,
            "message_id": None,
            "defend_flag": None
        }
        first = random.choice([battle['player1_id'], battle['player2_id']])
        battle_queues[battle_id]['turn_player'] = first

        await send_or_update_pvp_battle(battle_id, chat_id=message.chat.id)

        # Notify both players (DM first, fallback group mention) – but battle message is already in group
        for pid in [battle['player1_id'], battle['player2_id']]:
            msg = f"⚔️ Your turn! Check the battle in the group chat." if pid == first else f"⚔️ PVP BATTLE START! Wait for your turn in the group chat."
            try:
                await bot.send_message(pid, msg)
            except Exception:
                pass  # group mention not needed because the battle message is already there

def render_pvp_battle(battle_id, viewer_id=None):
    q = battle_queues.get(battle_id)
    if not q:
        return None, None

    p1 = q['player1']
    p2 = q['player2']
    turn = q['turn_player']
    hp1 = q['current_hp1']
    hp2 = q['current_hp2']
    ce1 = p1.get('ce', p1['max_ce'])
    ce2 = p2.get('ce', p2['max_ce'])

    name1 = e(p1.get('character_name') or p1.get('username') or str(p1['user_id']))
    name2 = e(p2.get('character_name') or p2.get('username') or str(p2['user_id']))

    hp_bar1 = build_hp_bar(hp1, p1['max_hp'])
    hp_bar2 = build_hp_bar(hp2, p2['max_hp'])
    ce_bar1 = build_ce_bar(ce1, p1['max_ce'])
    ce_bar2 = build_ce_bar(ce2, p2['max_ce'])

    if viewer_id == turn:
        turn_indicator = "🔵 <b>YOUR TURN</b>"
    elif turn in (p1['user_id'], p2['user_id']):
        turn_indicator = f"⏳ Waiting for {e(p1['username'] if turn == p1['user_id'] else p2['username'])}..."
    else:
        turn_indicator = "⏳ Waiting..."

    text = (
        f"⚔️ <b>PVP BATTLE</b>\n"
        f"━━━━━━━━━━━━━━━━━━━\n"
        f"<b>{name1}</b>\n"
        f"❤️ HP: {hp1}/{p1['max_hp']} {hp_bar1}\n"
        f"🔵 CE: {ce1}/{p1['max_ce']} {ce_bar1}\n"
        f"━━━━━━━━━━━━━━━━━━━\n"
        f"<b>{name2}</b>\n"
        f"❤️ HP: {hp2}/{p2['max_hp']} {hp_bar2}\n"
        f"🔵 CE: {ce2}/{p2['max_ce']} {ce_bar2}\n"
        f"━━━━━━━━━━━━━━━━━━━\n"
        f"⏳ Turn: {turn_indicator}"
    )

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="⚔️ Attack", callback_data=f"pvp_quick|{battle_id}|attack"),
            InlineKeyboardButton(text="🛡️ Defend", callback_data=f"pvp_quick|{battle_id}|defend")
        ],
        [
            InlineKeyboardButton(text="🌀 Technique", callback_data=f"pvp_tech|{battle_id}"),
            InlineKeyboardButton(text="🌐 Domain", callback_data=f"pvp_domain|{battle_id}")
        ],
        [
            InlineKeyboardButton(text="⏭️ Pass", callback_data=f"pvp_quick|{battle_id}|pass"),
            InlineKeyboardButton(text="🏳️ Surrender", callback_data=f"pvp_quick|{battle_id}|surrender")
        ]
    ])

    return text, keyboard

async def send_or_update_pvp_battle(battle_id, chat_id=None, callback=None):
    q = battle_queues.get(battle_id)
    if not q:
        return

    viewer_id = callback.from_user.id if callback else None
    text, keyboard = render_pvp_battle(battle_id, viewer_id)
    if not text:
        return

    if callback:
        try:
            await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")
            q['message_id'] = callback.message.message_id
            q['chat_id'] = callback.message.chat.id
            return
        except Exception as exc:
            logging.error(f"Failed to edit PvP message: {exc}")
            new_msg = await callback.message.reply(text, reply_markup=keyboard, parse_mode="HTML")
            q['message_id'] = new_msg.message_id
            q['chat_id'] = new_msg.chat.id
            return

    if chat_id:
        sent = await bot.send_message(chat_id, text, reply_markup=keyboard, parse_mode="HTML")
        q['message_id'] = sent.message_id
        q['chat_id'] = chat_id
        return

    if q.get('message_id') and q.get('chat_id'):
        try:
            await bot.edit_message_text(text, chat_id=q['chat_id'], message_id=q['message_id'], reply_markup=keyboard, parse_mode="HTML")
        except Exception as exc:
            logging.error(f"Failed to edit PvP message: {exc}")
            sent = await bot.send_message(q['chat_id'], text, reply_markup=keyboard, parse_mode="HTML")
            q['message_id'] = sent.message_id
            q['chat_id'] = sent.chat.id

@dp.callback_query(lambda c: c.data.startswith("pvp_quick"))
async def pvp_quick_cb(callback: types.CallbackQuery):
    data = callback.data.split("|")
    battle_id = int(data[1])
    action = data[2]
    user_id = callback.from_user.id

    q = battle_queues.get(battle_id)
    if not q:
        await callback.answer("❌ Battle expired.", show_alert=True)
        return

    if q.get('turn_player') != user_id:
        await callback.answer("❌ Not your turn!", show_alert=True)
        return

    async with db_pool.acquire() as conn:
        battle = await conn.fetchrow("SELECT * FROM battles WHERE id = $1 AND status = 'active'", battle_id)
        if not battle:
            await callback.answer("❌ Battle not active.", show_alert=True)
            return

        player = await conn.fetchrow("SELECT * FROM players WHERE user_id = $1", user_id)
        if user_id == battle['player1_id']:
            opponent_id = battle['player2_id']
            opponent_hp = q['current_hp2']
            opponent_def = q['player2']['def']
        else:
            opponent_id = battle['player1_id']
            opponent_hp = q['current_hp1']
            opponent_def = q['player1']['def']

        damage = 0
        effect_msg = ""
        black_flash = False

        if action == "attack":
            base_dmg = player['atk'] * random.uniform(0.8, 1.2)
            reduction = opponent_def * 0.5
            damage = max(1, int(base_dmg - reduction))
            if random.random() < 0.01:
                damage = int(damage * 2.5)
                black_flash = True
                effect_msg = f"⚡ <b>BLACK FLASH!</b> {e(player['character_name'])} lands a critical hit for <b>{damage}</b> damage!"
                await safe_send_media(callback.message, 'animation', EFFECTS["black_flash"], caption=effect_msg)
                await conn.execute("UPDATE players SET black_flash_count = black_flash_count + 1 WHERE user_id = $1", user_id)
            else:
                effect_msg = f"⚔️ {e(player['character_name'])} attacks for <b>{damage}</b> damage!"
        elif action == "defend":
            q['defend_flag'] = user_id
            await conn.execute("UPDATE battles SET defend_flag = TRUE WHERE id = $1", battle_id)
            effect_msg = f"🛡️ {e(player['character_name'])} braces for impact!"
            damage = 0
        elif action == "pass":
            effect_msg = f"⏭️ {e(player['character_name'])} passes the turn."
            damage = 0
        elif action == "surrender":
            await handle_pvp_victory(callback, battle_id, opponent_id, user_id)
            return

        if damage > 0:
            if q.get('defend_flag') == opponent_id:
                damage = damage // 2
                q['defend_flag'] = None
                effect_msg += " (halved by Defend!)"
            if user_id == battle['player1_id']:
                new_opp_hp = max(0, opponent_hp - damage)
                q['current_hp2'] = new_opp_hp
            else:
                new_opp_hp = max(0, opponent_hp - damage)
                q['current_hp1'] = new_opp_hp
            await conn.execute("UPDATE battles SET current_hp1 = $1, current_hp2 = $2 WHERE id = $3",
                               q['current_hp1'], q['current_hp2'], battle_id)
            logging.info(f"PvP attack: {user_id} dealt {damage} damage. New opponent HP: {new_opp_hp}")
        else:
            new_opp_hp = opponent_hp

        if new_opp_hp <= 0:
            await handle_pvp_victory(callback, battle_id, user_id, opponent_id)
            return

        next_player = battle['player1_id'] if user_id == battle['player2_id'] else battle['player2_id']
        q['turn_player'] = next_player
        await conn.execute("UPDATE battles SET turn = turn + 1, turn_player = $1 WHERE id = $2", next_player, battle_id)

        q['log'].append(effect_msg)
        if len(q['log']) > 10: q['log'] = q['log'][-10:]

        await send_or_update_pvp_battle(battle_id, callback=callback)

        # Notify next player: try DM, fallback to group mention
        chat_id = q.get('chat_id')
        if chat_id:
            await notify_player(next_player, battle_id, chat_id)

        await callback.answer("✅ Move executed!")

@dp.callback_query(lambda c: c.data.startswith("pvp_tech"))
async def pvp_tech_cb(callback: types.CallbackQuery):
    battle_id = int(callback.data.split("|")[1])
    user_id = callback.from_user.id
    q = battle_queues.get(battle_id)
    if not q or q.get('turn_player') != user_id:
        await callback.answer("❌ Not your turn!", show_alert=True)
        return

    async with db_pool.acquire() as conn:
        player = await conn.fetchrow("SELECT * FROM players WHERE user_id = $1", user_id)
        techs = player.get('techniques') or []
        if not techs:
            await callback.answer("❌ You have no techniques!", show_alert=True)
            return
        player_char = player.get('character_name')
        compatible = []
        for t in techs:
            tech = await conn.fetchrow("SELECT * FROM techniques WHERE name = $1", t)
            if tech and (tech.get('character_name') is None or tech['character_name'] == player_char):
                compatible.append(t)
        if not compatible:
            await callback.answer("❌ No compatible techniques!", show_alert=True)
            return
        buttons = []
        for t in compatible[:10]:
            tech = await conn.fetchrow("SELECT * FROM techniques WHERE name = $1", t)
            if tech:
                buttons.append([InlineKeyboardButton(
                    text=f"🌀 {t} (DMG {tech['damage_multiplier']}x, CE {tech['ce_cost']})",
                    callback_data=f"pvp_quick_tech|{battle_id}|{t}"
                )])
        buttons.append([InlineKeyboardButton(text="🔙 Back", callback_data=f"pvp_back|{battle_id}")])
        markup = InlineKeyboardMarkup(inline_keyboard=buttons)
        await callback.message.edit_text("🌀 <b>Select a Technique:</b>", reply_markup=markup, parse_mode="HTML")
        await callback.answer()

@dp.callback_query(lambda c: c.data.startswith("pvp_quick_tech"))
async def pvp_quick_tech_cb(callback: types.CallbackQuery):
    data = callback.data.split("|")
    battle_id = int(data[1])
    tech_name = data[2]
    user_id = callback.from_user.id
    q = battle_queues.get(battle_id)
    if not q or q.get('turn_player') != user_id:
        await callback.answer("❌ Not your turn!", show_alert=True)
        return

    async with db_pool.acquire() as conn:
        battle = await conn.fetchrow("SELECT * FROM battles WHERE id = $1 AND status = 'active'", battle_id)
        if not battle:
            await callback.answer("❌ Battle not active.", show_alert=True)
            return
        player = await conn.fetchrow("SELECT * FROM players WHERE user_id = $1", user_id)
        tech = await conn.fetchrow("SELECT * FROM techniques WHERE name = $1", tech_name)
        if not tech:
            await callback.answer("❌ Technique not found.", show_alert=True)
            return
        if player['ce'] < tech['ce_cost']:
            await callback.answer(f"❌ Need {tech['ce_cost']} CE, have {player['ce']}", show_alert=True)
            return
        await conn.execute("UPDATE players SET ce = ce - $1 WHERE user_id = $2", tech['ce_cost'], user_id)
        player['ce'] -= tech['ce_cost']
        if user_id == battle['player1_id']:
            q['player1']['ce'] = player['ce']
        else:
            q['player2']['ce'] = player['ce']

        dmg_mult = float(tech['damage_multiplier'])
        if user_id == battle['player1_id']:
            opponent_def = q['player2']['def']
        else:
            opponent_def = q['player1']['def']
        base_dmg = player['atk'] * dmg_mult * random.uniform(0.9, 1.1)
        reduction = opponent_def * 0.5
        damage = max(1, int(base_dmg - reduction))
        if q.get('defend_flag') == (battle['player1_id'] if user_id != battle['player1_id'] else battle['player2_id']):
            damage = damage // 2
            q['defend_flag'] = None
            effect_extra = " (halved by Defend!)"
        else:
            effect_extra = ""
        if user_id == battle['player1_id']:
            new_opp_hp = max(0, q['current_hp2'] - damage)
            q['current_hp2'] = new_opp_hp
        else:
            new_opp_hp = max(0, q['current_hp1'] - damage)
            q['current_hp1'] = new_opp_hp
        await conn.execute("UPDATE battles SET current_hp1 = $1, current_hp2 = $2 WHERE id = $3",
                           q['current_hp1'], q['current_hp2'], battle_id)
        logging.info(f"PvP Tech: {user_id} used {tech_name} for {damage} damage. New opponent HP: {new_opp_hp}")

        # Animation
        if "Purple" in tech_name:
            await safe_send_media(callback.message, 'animation', EFFECTS["gojo_purple"], caption=f"🌀 {e(player['character_name'])} unleashes {e(tech_name)}!")
        elif "Red" in tech_name:
            await safe_send_media(callback.message, 'animation', EFFECTS["gojo_red"], caption=f"🌀 {e(player['character_name'])} casts {e(tech_name)}!")
        elif "Blue" in tech_name:
            await safe_send_media(callback.message, 'animation', EFFECTS["gojo_blue"], caption=f"🌀 {e(player['character_name'])} uses {e(tech_name)}!")
        else:
            await safe_send_media(callback.message, 'animation', EFFECTS["cursed_energy"], caption=f"🌀 {e(player['character_name'])} uses {e(tech_name)}!")

        if new_opp_hp <= 0:
            await handle_pvp_victory(callback, battle_id, user_id, battle['player1_id'] if user_id != battle['player1_id'] else battle['player2_id'])
            return

        next_player = battle['player1_id'] if user_id == battle['player2_id'] else battle['player2_id']
        q['turn_player'] = next_player
        await conn.execute("UPDATE battles SET turn = turn + 1, turn_player = $1 WHERE id = $2", next_player, battle_id)

        effect_msg = f"🌀 {e(player['character_name'])} uses {e(tech_name)} for {damage} damage!{effect_extra}"
        q['log'].append(effect_msg)
        if len(q['log']) > 10: q['log'] = q['log'][-10:]

        await send_or_update_pvp_battle(battle_id, callback=callback)

        chat_id = q.get('chat_id')
        if chat_id:
            await notify_player(next_player, battle_id, chat_id)

        await callback.answer("✅ Technique executed!")

@dp.callback_query(lambda c: c.data.startswith("pvp_domain"))
async def pvp_domain_cb(callback: types.CallbackQuery):
    battle_id = int(callback.data.split("|")[1])
    user_id = callback.from_user.id
    q = battle_queues.get(battle_id)
    if not q or q.get('turn_player') != user_id:
        await callback.answer("❌ Not your turn!", show_alert=True)
        return

    async with db_pool.acquire() as conn:
        player = await conn.fetchrow("SELECT * FROM players WHERE user_id = $1", user_id)
        domains = player.get('domains') or []
        if not domains:
            await callback.answer("❌ No domains!", show_alert=True)
            return
        player_char = player.get('character_name')
        compatible = []
        for d in domains:
            domain = await conn.fetchrow("SELECT * FROM techniques WHERE name = $1 AND category = 'domain'", d)
            if domain and (domain.get('character_name') is None or domain['character_name'] == player_char):
                compatible.append(d)
        if not compatible:
            await callback.answer("❌ No compatible domains!", show_alert=True)
            return
        buttons = []
        for d in compatible[:5]:
            domain = await conn.fetchrow("SELECT * FROM techniques WHERE name = $1 AND category = 'domain'", d)
            if domain:
                ce_cost = domain['ce_cost']
                dmg_mult = float(domain['damage_multiplier'])
                buttons.append([InlineKeyboardButton(
                    text=f"🌐 {d} (DMG {dmg_mult}x, CE {ce_cost})",
                    callback_data=f"pvp_quick_domain|{battle_id}|{d}|{dmg_mult}|{ce_cost}"
                )])
        buttons.append([InlineKeyboardButton(text="🔙 Back", callback_data=f"pvp_back|{battle_id}")])
        markup = InlineKeyboardMarkup(inline_keyboard=buttons)
        await callback.message.edit_text("🌐 <b>Select a Domain:</b>", reply_markup=markup, parse_mode="HTML")
        await callback.answer()

@dp.callback_query(lambda c: c.data.startswith("pvp_quick_domain"))
async def pvp_quick_domain_cb(callback: types.CallbackQuery):
    data = callback.data.split("|")
    battle_id = int(data[1])
    domain_name = data[2]
    dmg_mult = float(data[3])
    ce_cost = int(data[4])
    user_id = callback.from_user.id
    q = battle_queues.get(battle_id)
    if not q or q.get('turn_player') != user_id:
        await callback.answer("❌ Not your turn!", show_alert=True)
        return

    async with db_pool.acquire() as conn:
        battle = await conn.fetchrow("SELECT * FROM battles WHERE id = $1 AND status = 'active'", battle_id)
        if not battle:
            await callback.answer("❌ Battle not active.", show_alert=True)
            return
        player = await conn.fetchrow("SELECT * FROM players WHERE user_id = $1", user_id)
        if player['ce'] < ce_cost:
            await callback.answer(f"❌ Need {ce_cost} CE, have {player['ce']}", show_alert=True)
            return
        await conn.execute("UPDATE players SET ce = ce - $1 WHERE user_id = $2", ce_cost, user_id)
        player['ce'] -= ce_cost
        if user_id == battle['player1_id']:
            q['player1']['ce'] = player['ce']
        else:
            q['player2']['ce'] = player['ce']

        # Domain ignores DEF
        damage = max(1, int(player['atk'] * dmg_mult * random.uniform(0.9, 1.1)))
        if q.get('defend_flag') == (battle['player1_id'] if user_id != battle['player1_id'] else battle['player2_id']):
            damage = damage // 2
            q['defend_flag'] = None
            effect_extra = " (halved by Defend!)"
        else:
            effect_extra = ""
        if user_id == battle['player1_id']:
            new_opp_hp = max(0, q['current_hp2'] - damage)
            q['current_hp2'] = new_opp_hp
        else:
            new_opp_hp = max(0, q['current_hp1'] - damage)
            q['current_hp1'] = new_opp_hp
        await conn.execute("UPDATE battles SET current_hp1 = $1, current_hp2 = $2 WHERE id = $3",
                           q['current_hp1'], q['current_hp2'], battle_id)
        logging.info(f"PvP Domain: {user_id} used {domain_name} for {damage} damage. New opponent HP: {new_opp_hp}")

        # Animation
        if "Unlimited Void" in domain_name:
            await safe_send_media(callback.message, 'animation', EFFECTS["gojo_unlimited_void"], caption=f"🌐 {e(player['character_name'])} expands {e(domain_name)}!")
        elif "Malevolent" in domain_name:
            await safe_send_media(callback.message, 'animation', EFFECTS["sukuna_domain"], caption=f"🌐 {e(player['character_name'])} expands {e(domain_name)}!")
        elif "Mahito" in domain_name or "Self" in domain_name:
            await safe_send_media(callback.message, 'animation', EFFECTS["mahito_domain"], caption=f"🌐 {e(player['character_name'])} expands {e(domain_name)}!")
        else:
            await safe_send_media(callback.message, 'animation', EFFECTS["default_domain"], caption=f"🌐 {e(player['character_name'])} expands {e(domain_name)}!")

        if new_opp_hp <= 0:
            await handle_pvp_victory(callback, battle_id, user_id, battle['player1_id'] if user_id != battle['player1_id'] else battle['player2_id'])
            return

        next_player = battle['player1_id'] if user_id == battle['player2_id'] else battle['player2_id']
        q['turn_player'] = next_player
        await conn.execute("UPDATE battles SET turn = turn + 1, turn_player = $1 WHERE id = $2", next_player, battle_id)

        effect_msg = f"🌐 {e(player['character_name'])} expands {e(domain_name)} for {damage} damage!{effect_extra}"
        q['log'].append(effect_msg)
        if len(q['log']) > 10: q['log'] = q['log'][-10:]

        await send_or_update_pvp_battle(battle_id, callback=callback)

        chat_id = q.get('chat_id')
        if chat_id:
            await notify_player(next_player, battle_id, chat_id)

        await callback.answer("✅ Domain expanded!")

@dp.callback_query(lambda c: c.data.startswith("pvp_back"))
async def pvp_back_cb(callback: types.CallbackQuery):
    battle_id = int(callback.data.split("|")[1])
    await send_or_update_pvp_battle(battle_id, callback=callback)
    await callback.answer()

async def handle_pvp_victory(callback, battle_id, winner_id, loser_id):
    async with db_pool.acquire() as conn:
        await conn.execute("UPDATE players SET wins = wins + 1, yen = LEAST(yen + 1000, $1), xp = xp + 500 WHERE user_id = $2", MAX_YEN, winner_id)
        await conn.execute("UPDATE players SET losses = losses + 1 WHERE user_id = $1", loser_id)
        await update_player_stats(winner_id)
        await update_player_stats(loser_id)
        await conn.execute("UPDATE battles SET status = 'completed' WHERE id = $1", battle_id)
        await check_achievements(winner_id)
        await update_missions(winner_id, "wins", 1)
        await update_quests(winner_id, "wins", 1)

        clear_session(winner_id)
        clear_session(loser_id)
        if winner_id in ongoing_battles: del ongoing_battles[winner_id]
        if loser_id in ongoing_battles: del ongoing_battles[loser_id]
        q = battle_queues.pop(battle_id, None)
        pvp_matches.pop(battle_id, None)

        winner = await conn.fetchrow("SELECT character_name, username FROM players WHERE user_id = $1", winner_id)
        loser = await conn.fetchrow("SELECT character_name, username FROM players WHERE user_id = $1", loser_id)
        winner_name = e(winner['character_name'] or winner['username'])
        loser_name = e(loser['character_name'] or loser['username'])

        victory_quote = get_jjk_quote(winner['character_name'] if winner else None, "victory")
        final_text = (
            f"🎉 <b>PVP VICTORY!</b>\n"
            f"━━━━━━━━━━━━━━━━━━━\n"
            f"<b>{winner_name}</b> defeats <b>{loser_name}</b>!\n"
            f"🏆 +1 Win, +1000 Yen, +500 XP\n"
            f"<i>{victory_quote}</i>"
        )
        try:
            await callback.message.edit_text(final_text, parse_mode="HTML")
        except:
            await callback.message.reply(final_text, parse_mode="HTML")
        await callback.answer("🎉 Victory!")

# ================================================================
# STATUS & RESUME
# ================================================================
@dp.message(Command("status"))
@friendly_error
async def status_cmd(message: types.Message):
    user_id = message.from_user.id
    if user_id in ongoing_battles:
        battle_id = ongoing_battles[user_id]
        async with db_pool.acquire() as conn:
            battle = await conn.fetchrow("SELECT * FROM battles WHERE id = $1 AND status = 'active'", battle_id)
            if battle:
                if battle['is_pvp']:
                    other_id = battle['player1_id'] if user_id == battle['player2_id'] else battle['player2_id']
                    other_player = await conn.fetchrow("SELECT username, character_name FROM players WHERE user_id = $1", other_id)
                    enemy_name = e(other_player['username'] or other_player['character_name'] or "Opponent")
                    your_hp = battle['current_hp1'] if user_id == battle['player1_id'] else battle['current_hp2']
                    enemy_hp = battle['current_hp2'] if user_id == battle['player1_id'] else battle['current_hp2']
                else:
                    enemy_name = e(battle['enemy_name'] or "Enemy")
                    your_hp = battle['current_hp1']
                    enemy_hp = battle['current_hp2']
                await message.reply(
                    f"⚔️ <b>You have an ongoing battle!</b>\n"
                    f"ID: {battle_id}\n"
                    f"Enemy: {enemy_name}\n"
                    f"Your HP: {your_hp}\n"
                    f"Enemy HP: {enemy_hp}\n"
                    f"Type /resume {battle_id} to continue.",
                    parse_mode="HTML"
                )
                return
    await message.reply("✅ No ongoing battle. Start one with /battle or /boss.")

@dp.message(Command("resume"))
@friendly_error
async def resume_cmd(message: types.Message):
    args = message.text.split()
    if len(args) < 2:
        await message.reply("📝 Usage: /resume battle_id")
        return
    battle_id = int(args[1])
    user_id = message.from_user.id
    async with db_pool.acquire() as conn:
        battle = await conn.fetchrow("SELECT * FROM battles WHERE id = $1 AND status = 'active'", battle_id)
        if not battle:
            await message.reply("❌ Battle not found or already finished.")
            return
        if user_id not in (battle['player1_id'], battle.get('player2_id')):
            await message.reply("❌ You are not a participant.")
            return
        if battle['is_pvp']:
            q = battle_queues.get(battle_id)
            if q:
                await send_or_update_pvp_battle(battle_id, chat_id=message.chat.id)
            else:
                await message.reply("⚠️ Battle data not found. Try /status.")
            return
        # PvE resume
        player = await conn.fetchrow("SELECT * FROM players WHERE user_id = $1", user_id)
        player = await apply_passive_regen(dict(player))
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
        if battle_id not in battle_queues:
            battle_queues[battle_id] = {"participants": {user_id: []}, "current_hp": enemy['hp'], "log": []}
        if user_id not in battle_queues[battle_id]['participants']:
            battle_queues[battle_id]['participants'][user_id] = []
        vows = json.loads(battle.get('vow_effects', '[]'))
        log_lines = battle_queues[battle_id].get('log', [])
        set_session(user_id, "battle", battle_id=battle_id, role="player1")
        await show_battle_turn(message, battle_id, player, enemy, vows, log_lines)

# ================================================================
# OTHER COMMANDS (Prestige, Missions, Daily, Clan, Raid, Dungeon, Tower, Achievements, Events, Quests, Materials, Craft, Leaderboard, NPC, Awakening)
# ================================================================

@dp.message(Command("prestige"))
@friendly_error
async def prestige_cmd(message: types.Message):
    user_id = message.from_user.id
    async with db_pool.acquire() as conn:
        player = await conn.fetchrow("SELECT * FROM players WHERE user_id = $1", user_id)
        if not player:
            await message.reply("❌ Start with /start first!")
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
        await safe_send_media(message, 'animation', EFFECTS["awakening"], caption=f"🌟 <b>Prestige Complete!</b>\n━━━━━━━━━━━━━━━━━━━\nPrestige Level: {new_prestige}/10\nPermanent ATK Bonus: +{bonus_atk}\nPermanent HP Bonus: +{bonus_hp}\nLevel reset to 1. Good luck!")

@dp.message(Command("missions"))
@friendly_error
async def missions_cmd(message: types.Message):
    user_id = message.from_user.id
    async with db_pool.acquire() as conn:
        player = await conn.fetchrow("SELECT * FROM players WHERE user_id = $1", user_id)
        if not player:
            await message.reply("❌ Start with /start first!")
            return
        missions = await conn.fetch("SELECT * FROM missions ORDER BY type, id")
        if not missions:
            await message.reply("❌ No missions available.")
            return
        player_missions = await conn.fetch("SELECT * FROM player_missions WHERE player_id = $1", user_id)
        resp = "📋 <b>Your Missions</b>\n━━━━━━━━━━━━━━━━━━━\n"
        current_type = None
        for m in missions:
            if m['type'] != current_type:
                current_type = m['type']
                resp += f"\n📌 <b>{current_type.upper()}</b>\n"
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
            resp += f"  • <b>{e(m['name'])}</b> - {e(m['description'])}\n"
            resp += f"    Reward: ¥{m['reward_yen']:,} | ⭐ +{m['reward_xp']} XP\n"
            resp += f"    Status: {status}\n"
        resp += "\n━━━━━━━━━━━━━━━━━━━\n"
        resp += "Use /daily to claim daily rewards."
        await message.reply(resp, parse_mode="HTML")

@dp.message(Command("daily"))
@friendly_error
async def daily_cmd(message: types.Message):
    user_id = message.from_user.id
    async with db_pool.acquire() as conn:
        player = await conn.fetchrow("SELECT * FROM players WHERE user_id = $1", user_id)
        if not player:
            await message.reply("❌ Start with /start first!")
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

@dp.message(Command("clan"))
@friendly_error
async def clan_cmd(message: types.Message):
    args = message.text.split()
    if len(args) < 2:
        await message.reply("📝 Usage:\n/clan create [name]\n/clan join [name]\n/clan info\n/clan leave\n/clan upgrade\n/clan war [clan]")
        return
    action = args[1].lower()
    user_id = message.from_user.id
    async with db_pool.acquire() as conn:
        if action == "create":
            if len(args) < 3:
                await message.reply("📝 Usage: /clan create [clan name]")
                return
            name = " ".join(args[2:])
            existing = await conn.fetchrow("SELECT * FROM clans WHERE name ILIKE $1", name)
            if existing:
                await message.reply(f"❌ Clan '{name}' already exists.")
                return
            await conn.execute("INSERT INTO clans (name, leader_id, member_count) VALUES ($1, $2, 1)", name, user_id)
            await conn.execute("UPDATE players SET clan_id = (SELECT id FROM clans WHERE name = $1), clan_rank = 'Leader' WHERE user_id = $2", name, user_id)
            await message.reply(f"✅ Clan '{name}' created! You are the leader.")
        elif action == "join":
            if len(args) < 3:
                await message.reply("📝 Usage: /clan join [clan name]")
                return
            name = " ".join(args[2:])
            clan = await conn.fetchrow("SELECT * FROM clans WHERE name ILIKE $1", name)
            if not clan:
                await message.reply(f"❌ Clan '{name}' not found.")
                return
            await conn.execute("UPDATE players SET clan_id = $1, clan_rank = 'Member' WHERE user_id = $2", clan['id'], user_id)
            await conn.execute("UPDATE clans SET member_count = member_count + 1 WHERE id = $1", clan['id'])
            await message.reply(f"✅ Joined clan '{name}'!")
        elif action == "info":
            player = await conn.fetchrow("SELECT clan_id FROM players WHERE user_id = $1", user_id)
            if not player or not player['clan_id']:
                await message.reply("❌ You are not in a clan.")
                return
            clan = await conn.fetchrow("SELECT * FROM clans WHERE id = $1", player['clan_id'])
            members = await conn.fetch("SELECT username, clan_rank FROM players WHERE clan_id = $1", clan['id'])
            member_list = "\n".join([f"• {e(m['username'])} ({e(m['clan_rank'])})" for m in members])
            await message.reply(
                f"🏛️ <b>Clan: {e(clan['name'])}</b>\n"
                f"Leader: {clan['leader_id']}\n"
                f"Members: {clan['member_count']}\n"
                f"Level: {clan['level']}\n"
                f"━━━━━━━━━━━━━━━━━━━\n"
                f"{member_list}",
                parse_mode="HTML"
            )
        elif action == "leave":
            player = await conn.fetchrow("SELECT clan_id, clan_rank FROM players WHERE user_id = $1", user_id)
            if not player or not player['clan_id']:
                await message.reply("❌ You are not in a clan.")
                return
            if player['clan_rank'] == 'Leader':
                await message.reply("❌ You cannot leave as leader. Transfer leadership first or disband.")
                return
            await conn.execute("UPDATE clans SET member_count = member_count - 1 WHERE id = $1", player['clan_id'])
            await conn.execute("UPDATE players SET clan_id = NULL, clan_rank = 'Member' WHERE user_id = $1", user_id)
            await message.reply("✅ You left the clan.")
        elif action == "upgrade":
            player = await conn.fetchrow("SELECT clan_id, clan_rank FROM players WHERE user_id = $1", user_id)
            if not player or not player['clan_id']:
                await message.reply("❌ You're not in a clan.")
                return
            if player['clan_rank'] != 'Leader':
                await message.reply("❌ Only the leader can upgrade.")
                return
            clan = await conn.fetchrow("SELECT * FROM clans WHERE id = $1", player['clan_id'])
            current_level = clan['level']
            cost = 1000 * (current_level + 1)
            if clan['xp'] < cost:
                await message.reply(f"❌ Not enough clan XP. Need {cost}, have {clan['xp']}.")
                return
            await conn.execute("UPDATE clans SET level = level + 1, xp = xp - $1 WHERE id = $2", cost, player['clan_id'])
            await message.reply(f"✅ Clan upgraded to level {current_level+1}!")
        elif action == "war":
            if len(args) < 3:
                await message.reply("📝 Usage: /clan war [clan name]")
                return
            target_clan_name = " ".join(args[2:])
            player = await conn.fetchrow("SELECT clan_id, clan_rank FROM players WHERE user_id = $1", user_id)
            if not player or player['clan_rank'] != 'Leader':
                await message.reply("❌ Only clan leaders can declare war.")
                return
            target_clan = await conn.fetchrow("SELECT id, name FROM clans WHERE name ILIKE $1", target_clan_name)
            if not target_clan:
                await message.reply("❌ Clan not found.")
                return
            if target_clan['id'] == player['clan_id']:
                await message.reply("❌ You can't war with your own clan.")
                return
            existing = await conn.fetchrow("SELECT * FROM clan_wars WHERE (clan1_id = $1 OR clan2_id = $1) AND status = 'active'", player['clan_id'])
            if existing:
                await message.reply("❌ Your clan is already in a war.")
                return
            await conn.execute("""
                INSERT INTO clan_wars (clan1_id, clan2_id, start_time, end_time)
                VALUES ($1, $2, NOW(), NOW() + INTERVAL '24 hours')
            """, player['clan_id'], target_clan['id'])
            await message.reply(f"⚔️ <b>CLAN WAR DECLARED!</b>\nYour clan vs {e(target_clan['name'])}\nWar ends in 24 hours.", parse_mode="HTML")
        else:
            await message.reply("❌ Unknown action. Use create, join, info, leave, upgrade, or war.")

# ================================================================
# RAID – FULL IMPLEMENTATION
# ================================================================
@dp.message(Command("raid"))
@friendly_error
async def raid_cmd(message: types.Message):
    user_id = message.from_user.id
    if user_id in ongoing_battles:
        await message.reply("⚠️ You already have an ongoing battle! Use /status or /resume.")
        return
    async with db_pool.acquire() as conn:
        player = await conn.fetchrow("SELECT * FROM players WHERE user_id = $1", user_id)
        if not player:
            await message.reply("❌ Start with /start first!")
            return
        clan_id = player.get('clan_id')
        if not clan_id:
            await message.reply("❌ You must be in a clan to start a raid.")
            return
        clan_members = await conn.fetch("SELECT user_id FROM players WHERE clan_id = $1", clan_id)
        if len(clan_members) < 2:
            await message.reply("❌ Your clan needs at least 2 members to start a raid.")
            return
        enemy_base = await conn.fetchrow("SELECT * FROM enemies WHERE is_boss = TRUE ORDER BY RANDOM() LIMIT 1")
        if not enemy_base:
            await message.reply("❌ No bosses available!")
            return
        member_ids = [m['user_id'] for m in clan_members]
        members = await conn.fetch("SELECT * FROM players WHERE user_id = ANY($1)", member_ids)
        avg_atk = sum(m['atk'] for m in members) / len(members)
        avg_def = sum(m['def'] for m in members) / len(members)
        avg_hp = sum(m['max_hp'] for m in members) / len(members)
        player_sample = {"atk": avg_atk, "def": avg_def, "max_hp": avg_hp, "level": player['level']}
        enemy = scale_enemy_to_player(player_sample, enemy_base)
        enemy['hp'] = int(enemy['hp'] * 1.5 * len(members))
        enemy['max_hp'] = enemy['hp']
        enemy['reward_yen'] = int(enemy['reward_yen'] * 1.5)
        enemy['reward_xp'] = int(enemy['reward_xp'] * 1.5)

        battle_id = await conn.fetchval("""
            INSERT INTO battles (chat_id, player1_id, current_hp1, current_hp2, 
                                 enemy_name, enemy_rank, enemy_atk, enemy_def, enemy_spd,
                                 is_boss, enemy_reward_yen, enemy_reward_xp, enemy_max_hp,
                                 vow_effects, participants, is_raid, raid_owner, max_participants)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15, $16, $17, $18)
            RETURNING id
        """, message.chat.id, user_id, 0, enemy['hp'], 
           enemy['name'], enemy['rank'], enemy['atk'], enemy['def'], enemy['spd'],
           True, enemy['reward_yen'], enemy['reward_xp'], enemy['hp'],
           json.dumps([]), json.dumps(member_ids), True, user_id, len(member_ids))
        for mid in member_ids:
            ongoing_battles[mid] = battle_id
            set_session(mid, "battle", battle_id=battle_id, role="raid")
        battle_queues[battle_id] = {"participants": {mid: [] for mid in member_ids}, 
                                    "current_hp": enemy['hp'], "raid": True, "log": []}
        await safe_send_media(message, 'animation', EFFECTS["clan_raid"])
        await message.reply(
            f"👑 <b>CLAN RAID STARTED!</b>\n"
            f"━━━━━━━━━━━━━━━━━━━\n"
            f"Boss: {e(enemy['name'])} (HP: {enemy['hp']})\n"
            f"All clan members can attack!\n"
            f"Use /raid_attack to deal damage.",
            parse_mode="HTML"
        )
        await show_raid_status(message, battle_id, enemy)

@dp.message(Command("raid_attack"))
@friendly_error
async def raid_attack_cmd(message: types.Message):
    user_id = message.from_user.id
    if user_id not in ongoing_battles:
        await message.reply("❌ You are not in a battle.")
        return
    battle_id = ongoing_battles[user_id]
    async with db_pool.acquire() as conn:
        battle = await conn.fetchrow("SELECT * FROM battles WHERE id = $1", battle_id)
        if not battle or battle['status'] != 'active':
            await message.reply("❌ Battle is no longer active.")
            return
        if not battle.get('is_raid'):
            await message.reply("❌ This is not a raid battle.")
            return
        player = await conn.fetchrow("SELECT * FROM players WHERE user_id = $1", user_id)
        if not player:
            return
        dmg = max(1, int(player['atk'] * random.uniform(0.6, 1.2)))
        new_hp = max(0, battle['current_hp2'] - dmg)
        await conn.execute("UPDATE battles SET current_hp2 = $1 WHERE id = $2", new_hp, battle_id)
        contrib = battle.get('contributions') or {}
        if isinstance(contrib, str):
            contrib = json.loads(contrib)
        contrib[str(user_id)] = contrib.get(str(user_id), 0) + dmg
        await conn.execute("UPDATE battles SET contributions = $1 WHERE id = $2", json.dumps(contrib), battle_id)
        if new_hp <= 0:
            participants = json.loads(battle['participants'])
            for pid in participants:
                reward_yen = int(battle['enemy_reward_yen'] / len(participants))
                reward_xp = int(battle['enemy_reward_xp'] / len(participants))
                await conn.execute("""
                    UPDATE players SET yen = LEAST(yen + $1, $2), xp = xp + $3
                    WHERE user_id = $4
                """, reward_yen, MAX_YEN, reward_xp, pid)
                await update_player_stats(pid)
                if pid in ongoing_battles:
                    del ongoing_battles[pid]
                clear_session(pid)
            await conn.execute("UPDATE battles SET status = 'completed' WHERE id = $1", battle_id)
            await message.reply(f"🎉 <b>Raid Boss Defeated!</b>\nAll participants earned rewards!", parse_mode="HTML")
            if battle_id in battle_queues:
                del battle_queues[battle_id]
            return
        battle_queues[battle_id]['current_hp'] = new_hp
        await show_raid_status(message, battle_id, {"name": battle['enemy_name'], "hp": new_hp, "max_hp": battle['enemy_max_hp']})

async def show_raid_status(message, battle_id, enemy):
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⚔️ Attack", callback_data=f"raid_attack_{battle_id}")],
        [InlineKeyboardButton(text="🔄 Refresh", callback_data=f"raid_refresh_{battle_id}")]
    ])
    hp_bar = build_hp_bar(enemy['hp'], enemy['max_hp'])
    caption = (
        f"👑 <b>Raid Boss</b>\n"
        f"━━━━━━━━━━━━━━━━━━━\n"
        f"💀 {e(enemy['name'])}\n"
        f"❤️ HP: {enemy['hp']}/{enemy['max_hp']} {hp_bar}\n"
        f"━━━━━━━━━━━━━━━━━━━\n"
        f"Click Attack to deal damage!"
    )
    await message.reply(caption, reply_markup=keyboard, parse_mode="HTML")

@dp.callback_query(lambda c: c.data.startswith("raid_attack_"))
async def raid_attack_cb(callback: types.CallbackQuery):
    battle_id = int(callback.data.split("_")[2])
    user_id = callback.from_user.id
    async with db_pool.acquire() as conn:
        battle = await conn.fetchrow("SELECT * FROM battles WHERE id = $1", battle_id)
        if not battle or battle['status'] != 'active':
            await callback.answer("❌ Battle ended.", show_alert=True)
            return
        player = await conn.fetchrow("SELECT * FROM players WHERE user_id = $1", user_id)
        if not player:
            return
        dmg = max(1, int(player['atk'] * random.uniform(0.6, 1.2)))
        new_hp = max(0, battle['current_hp2'] - dmg)
        await conn.execute("UPDATE battles SET current_hp2 = $1 WHERE id = $2", new_hp, battle_id)
        contrib = battle.get('contributions') or {}
        if isinstance(contrib, str):
            contrib = json.loads(contrib)
        contrib[str(user_id)] = contrib.get(str(user_id), 0) + dmg
        await conn.execute("UPDATE battles SET contributions = $1 WHERE id = $2", json.dumps(contrib), battle_id)
        if new_hp <= 0:
            participants = json.loads(battle['participants'])
            for pid in participants:
                reward_yen = int(battle['enemy_reward_yen'] / len(participants))
                reward_xp = int(battle['enemy_reward_xp'] / len(participants))
                await conn.execute("""
                    UPDATE players SET yen = LEAST(yen + $1, $2), xp = xp + $3
                    WHERE user_id = $4
                """, reward_yen, MAX_YEN, reward_xp, pid)
                await update_player_stats(pid)
                if pid in ongoing_battles:
                    del ongoing_battles[pid]
                clear_session(pid)
            await conn.execute("UPDATE battles SET status = 'completed' WHERE id = $1", battle_id)
            await callback.message.edit_text("🎉 <b>Raid Boss Defeated!</b> All participants earned rewards!", parse_mode="HTML")
            if battle_id in battle_queues:
                del battle_queues[battle_id]
            await callback.answer("Victory!")
            return
        battle_queues[battle_id]['current_hp'] = new_hp
        await callback.answer(f"✅ Dealt {dmg} damage!")
        await show_raid_status(callback.message, battle_id, {"name": battle['enemy_name'], "hp": new_hp, "max_hp": battle['enemy_max_hp']})

@dp.callback_query(lambda c: c.data.startswith("raid_refresh_"))
async def raid_refresh_cb(callback: types.CallbackQuery):
    battle_id = int(callback.data.split("_")[2])
    async with db_pool.acquire() as conn:
        battle = await conn.fetchrow("SELECT * FROM battles WHERE id = $1", battle_id)
        if not battle:
            await callback.answer("❌ Battle not found.", show_alert=True)
            return
        await show_raid_status(callback.message, battle_id, {"name": battle['enemy_name'], "hp": battle['current_hp2'], "max_hp": battle['enemy_max_hp']})
        await callback.answer("🔄 Refreshed!")

# ================================================================
# DUNGEON, TOWER, ACHIEVEMENTS, EVENTS, QUESTS, MATERIALS, CRAFT, LEADERBOARD, NPC, AWAKENING
# ================================================================

@dp.message(Command("dungeon"))
@friendly_error
async def dungeon_cmd(message: types.Message):
    user_id = message.from_user.id
    if user_id in ongoing_battles:
        await message.reply("⚠️ You already have an ongoing battle! Use /status or /resume.")
        return
    async with db_pool.acquire() as conn:
        player = await conn.fetchrow("SELECT * FROM players WHERE user_id = $1", user_id)
        if not player:
            await message.reply("❌ Start with /start first!")
            return
        player = await regen_ce(dict(player))
        player = await apply_passive_regen(player)
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
            await message.reply("❌ No enemies available.")
            return
        enemy = scale_enemy_to_player(player, enemy_base)
        enemy['hp'] = int(enemy['hp'] * (1 + floor * 0.2))
        enemy['atk'] = int(enemy['atk'] * (1 + floor * 0.15))
        enemy['def'] = int(enemy['def'] * (1 + floor * 0.1))
        enemy['reward_yen'] = int(enemy['reward_yen'] * (1 + floor * 0.1))
        enemy['reward_xp'] = int(enemy['reward_xp'] * (1 + floor * 0.1))
        enemy['rank'] = f"Dungeon Floor {floor}"
        await safe_send_media(message, 'animation', EFFECTS["dungeon_clear"], caption=f"🏰 <b>Dungeon – Floor {floor}</b>\nEnemy: {e(enemy['name'])}\nHP: {enemy['hp']} | ATK: {enemy['atk']} | DEF: {enemy['def']}\nReward: ¥{enemy['reward_yen']} + {enemy['reward_xp']} XP\nDefeat it to advance to the next floor!")
        battle_id = await conn.fetchval("""
            INSERT INTO battles (chat_id, player1_id, current_hp1, current_hp2, 
                                 enemy_name, enemy_rank, enemy_atk, enemy_def, enemy_spd,
                                 is_boss, enemy_reward_yen, enemy_reward_xp, enemy_max_hp,
                                 vow_effects, is_dungeon, dungeon_run_id)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15, $16)
            RETURNING id
        """, message.chat.id, user_id, player['hp'], enemy['hp'], 
           enemy['name'], enemy['rank'], enemy['atk'], enemy['def'], enemy['spd'],
           False, enemy['reward_yen'], enemy['reward_xp'], enemy['hp'],
           json.dumps([]), True, run_id)
        ongoing_battles[user_id] = battle_id
        set_session(user_id, "battle", battle_id=battle_id, role="player1")
        battle_queues[battle_id] = {"participants": {user_id: []}, "current_hp": enemy['hp'], "log": []}
        await show_battle_turn(message, battle_id, player, enemy, [])

@dp.message(Command("tower"))
@friendly_error
async def tower_cmd(message: types.Message):
    user_id = message.from_user.id
    if user_id in ongoing_battles:
        await message.reply("⚠️ You already have an ongoing battle! Use /status or /resume.")
        return
    async with db_pool.acquire() as conn:
        player = await conn.fetchrow("SELECT * FROM players WHERE user_id = $1", user_id)
        if not player:
            await message.reply("❌ Start with /start first!")
            return
        player = await regen_ce(dict(player))
        player = await apply_passive_regen(player)
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
            await message.reply("🏆 <b>Tower Complete!</b> You have cleared all 100 floors.", parse_mode="HTML")
            await conn.execute("UPDATE tower_runs SET status = 'completed' WHERE id = $1", run_id)
            return
        is_boss = (floor % 10 == 0)
        enemy_base = await conn.fetchrow("SELECT * FROM enemies WHERE is_boss = $1 ORDER BY RANDOM() LIMIT 1", is_boss)
        if not enemy_base:
            await message.reply("❌ No enemies available.")
            return
        enemy = scale_enemy_to_player(player, enemy_base)
        enemy['hp'] = int(enemy['hp'] * (1 + floor * 0.1))
        enemy['atk'] = int(enemy['atk'] * (1 + floor * 0.08))
        enemy['def'] = int(enemy['def'] * (1 + floor * 0.05))
        enemy['reward_yen'] = int(enemy['reward_yen'] * (1 + floor * 0.05))
        enemy['reward_xp'] = int(enemy['reward_xp'] * (1 + floor * 0.05))
        enemy['rank'] = f"Tower Floor {floor}"
        await safe_send_media(message, 'animation', EFFECTS["tower_clear"], caption=f"🗼 <b>Tower – Floor {floor}/100</b>\nEnemy: {e(enemy['name'])} {'(BOSS)' if is_boss else ''}\nHP: {enemy['hp']} | ATK: {enemy['atk']} | DEF: {enemy['def']}\nReward: ¥{enemy['reward_yen']} + {enemy['reward_xp']} XP\nDefeat it to climb higher!")
        battle_id = await conn.fetchval("""
            INSERT INTO battles (chat_id, player1_id, current_hp1, current_hp2, 
                                 enemy_name, enemy_rank, enemy_atk, enemy_def, enemy_spd,
                                 is_boss, enemy_reward_yen, enemy_reward_xp, enemy_max_hp,
                                 vow_effects, is_tower, tower_run_id, tower_floor)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15, $16, $17)
            RETURNING id
        """, message.chat.id, user_id, player['hp'], enemy['hp'], 
           enemy['name'], enemy['rank'], enemy['atk'], enemy['def'], enemy['spd'],
           is_boss, enemy['reward_yen'], enemy['reward_xp'], enemy['hp'],
           json.dumps([]), True, run_id, floor)
        ongoing_battles[user_id] = battle_id
        set_session(user_id, "battle", battle_id=battle_id, role="player1")
        battle_queues[battle_id] = {"participants": {user_id: []}, "current_hp": enemy['hp'], "log": []}
        await show_battle_turn(message, battle_id, player, enemy, [])

@dp.message(Command("achievements"))
@friendly_error
async def achievements_cmd(message: types.Message):
    user_id = message.from_user.id
    async with db_pool.acquire() as conn:
        achievements = await conn.fetch("SELECT * FROM achievements")
        if not achievements:
            await message.reply("❌ No achievements available.")
            return
        player_achievements = await conn.fetch("SELECT achievement_id FROM player_achievements WHERE player_id = $1", user_id)
        unlocked = [pa['achievement_id'] for pa in player_achievements]
        resp = "🏆 <b>Achievements</b>\n━━━━━━━━━━━━━━━━━━━\n"
        for a in achievements:
            status = "✅" if a['id'] in unlocked else "🔒"
            resp += f"{status} <b>{e(a['name'])}</b> – {e(a['description'])}\n"
        await message.reply(resp, parse_mode="HTML")

@dp.message(Command("event"))
@friendly_error
async def event_cmd(message: types.Message):
    async with db_pool.acquire() as conn:
        now = datetime.now()
        events = await conn.fetch("SELECT * FROM events WHERE active = TRUE AND start_time <= $1 AND end_time >= $1", now)
        if not events:
            await message.reply("🎯 No active events right now.")
            return
        resp = "🎯 <b>Active Events</b>\n━━━━━━━━━━━━━━━━━━━\n"
        for ev in events:
            resp += f"🔥 {ev['event_type'].title()}: <b>{e(ev['boss_name'])}</b>\n"
            resp += f"⏳ Ends: {ev['end_time'].strftime('%Y-%m-%d %H:%M')}\n"
            if ev.get('reward_pool'):
                rewards = json.loads(ev['reward_pool'])
                resp += f"🎁 Rewards: {', '.join([f'{k}: {v}' for k, v in rewards.items()])}\n"
            resp += f"Use /event_battle {ev['id']} to fight!\n\n"
        await message.reply(resp, parse_mode="HTML")

@dp.message(Command("event_battle"))
@friendly_error
async def event_battle_cmd(message: types.Message):
    args = message.text.split()
    if len(args) < 2:
        await message.reply("📝 Usage: /event_battle [event_id]")
        return
    event_id = int(args[1])
    user_id = message.from_user.id
    if user_id in ongoing_battles:
        await message.reply("⚠️ You already have an ongoing battle.")
        return
    async with db_pool.acquire() as conn:
        event = await conn.fetchrow("SELECT * FROM events WHERE id = $1 AND active = TRUE AND start_time <= NOW() AND end_time >= NOW()", event_id)
        if not event:
            await message.reply("❌ Event not found or expired.")
            return
        player = await conn.fetchrow("SELECT * FROM players WHERE user_id = $1", user_id)
        if not player:
            await message.reply("❌ Start with /start first!")
            return
        player = await regen_ce(dict(player))
        player = await apply_passive_regen(player)
        enemy_base = await conn.fetchrow("SELECT * FROM enemies WHERE name ILIKE $1", event['boss_name'])
        if not enemy_base:
            await message.reply("❌ Boss not found in database.")
            return
        enemy = scale_enemy_to_player(player, enemy_base)
        enemy['hp'] = int(enemy['hp'] * 1.5)
        enemy['reward_yen'] = int(enemy['reward_yen'] * 1.5)
        enemy['reward_xp'] = int(enemy['reward_xp'] * 1.5)
        await safe_send_media(message, 'animation', EFFECTS["clan_raid"])
        battle_id = await conn.fetchval("""
            INSERT INTO battles (chat_id, player1_id, current_hp1, current_hp2,
                                 enemy_name, enemy_rank, enemy_atk, enemy_def, enemy_spd,
                                 is_boss, enemy_reward_yen, enemy_reward_xp, enemy_max_hp,
                                 vow_effects, participants, is_event, event_id)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15, $16, $17)
            RETURNING id
        """, message.chat.id, user_id, player['hp'], enemy['hp'],
           enemy['name'], enemy['rank'], enemy['atk'], enemy['def'], enemy['spd'],
           True, enemy['reward_yen'], enemy['reward_xp'], enemy['hp'],
           json.dumps([]), json.dumps([user_id]), True, event_id)
        ongoing_battles[user_id] = battle_id
        set_session(user_id, "battle", battle_id=battle_id, role="player1")
        battle_queues[battle_id] = {
            "participants": {user_id: []},
            "current_hp": enemy['hp'],
            "log": []
        }
        active_vows = await conn.fetch("""
            SELECT v.*, pv.remaining_turns 
            FROM player_vows pv 
            JOIN binding_vows v ON pv.vow_id = v.id 
            WHERE pv.player_id = $1 AND pv.active = TRUE
        """, user_id)
        vow_effects = [v['effect'] for v in active_vows]
        await conn.execute("UPDATE battles SET vow_effects = $1 WHERE id = $2", json.dumps(vow_effects), battle_id)
        await show_battle_turn(message, battle_id, player, enemy, vow_effects)

@dp.message(Command("quests"))
@friendly_error
async def quests_cmd(message: types.Message):
    user_id = message.from_user.id
    async with db_pool.acquire() as conn:
        quests = await conn.fetch("SELECT * FROM quests WHERE type = 'side' OR (type = 'story' AND chapter_id IS NOT NULL)")
        if not quests:
            await message.reply("❌ No quests available.")
            return
        player_quests = await conn.fetch("SELECT quest_id, progress, completed FROM player_quests WHERE player_id = $1", user_id)
        resp = "📜 <b>Quests</b>\n━━━━━━━━━━━━━━━━━━━\n"
        for q in quests:
            pq = next((p for p in player_quests if p['quest_id'] == q['id']), None)
            status = "✅" if pq and pq['completed'] else "⏳" if pq else "🔒"
            progress = f" ({pq['progress']}/{q['requirement'].split(':')[1]})" if pq and not pq['completed'] else ""
            resp += f"{status} <b>{e(q['title'])}</b> – {e(q['description'])}{progress}\n"
            resp += f"   Reward: ¥{q['reward_yen']}, XP {q['reward_xp']}\n"
        resp += "\nAccept: /quest_accept [id]"
        await message.reply(resp, parse_mode="HTML")

@dp.message(Command("quest_accept"))
@friendly_error
async def quest_accept(message: types.Message):
    args = message.text.split()
    if len(args) < 2:
        await message.reply("📝 Usage: /quest_accept [quest_id]")
        return
    quest_id = int(args[1])
    user_id = message.from_user.id
    async with db_pool.acquire() as conn:
        quest = await conn.fetchrow("SELECT * FROM quests WHERE id = $1", quest_id)
        if not quest:
            await message.reply("❌ Quest not found.")
            return
        existing = await conn.fetchrow("SELECT * FROM player_quests WHERE player_id = $1 AND quest_id = $2", user_id, quest_id)
        if existing:
            await message.reply("❌ You already have this quest.")
            return
        await conn.execute("INSERT INTO player_quests (player_id, quest_id, progress) VALUES ($1, $2, 0)", user_id, quest_id)
        await message.reply(f"✅ Quest accepted: <b>{e(quest['title'])}</b>", parse_mode="HTML")

@dp.message(Command("quest_reward"))
@friendly_error
async def quest_reward(message: types.Message):
    args = message.text.split()
    if len(args) < 2:
        await message.reply("📝 Usage: /quest_reward [quest_id]")
        return
    quest_id = int(args[1])
    user_id = message.from_user.id
    async with db_pool.acquire() as conn:
        pq = await conn.fetchrow("SELECT * FROM player_quests WHERE player_id = $1 AND quest_id = $2 AND completed = TRUE", user_id, quest_id)
        if not pq:
            await message.reply("❌ Quest not completed or not found.")
            return
        quest = await conn.fetchrow("SELECT * FROM quests WHERE id = $1", quest_id)
        if not quest:
            await message.reply("❌ Quest not found.")
            return
        await conn.execute("UPDATE players SET yen = LEAST(yen + $1, $2), xp = xp + $3 WHERE user_id = $4",
                           quest['reward_yen'], MAX_YEN, quest['reward_xp'], user_id)
        if quest.get('reward_item'):
            await conn.execute("UPDATE players SET bag = array_append(bag, $1) WHERE user_id = $2",
                               quest['reward_item'], user_id)
        await conn.execute("DELETE FROM player_quests WHERE player_id = $1 AND quest_id = $2", user_id, quest_id)
        await update_player_stats(user_id)
        await message.reply(f"✅ Rewards claimed for <b>{e(quest['title'])}</b>! +¥{quest['reward_yen']}, +{quest['reward_xp']} XP.", parse_mode="HTML")

@dp.message(Command("materials"))
@friendly_error
async def materials_cmd(message: types.Message):
    user_id = message.from_user.id
    async with db_pool.acquire() as conn:
        materials = await conn.fetch("SELECT m.*, pm.quantity FROM materials m LEFT JOIN player_materials pm ON m.id = pm.material_id AND pm.player_id = $1", user_id)
        if not materials:
            await message.reply("❌ You have no materials. Defeat bosses to earn them.")
            return
        resp = "📦 <b>Your Materials</b>\n━━━━━━━━━━━━━━━━━━━\n"
        for m in materials:
            qty = m['quantity'] or 0
            resp += f"• {e(m['name'])} x{qty} ({e(m['rarity'])})\n"
        await message.reply(resp, parse_mode="HTML")

@dp.message(Command("craft"))
@friendly_error
async def craft_cmd(message: types.Message):
    args = message.text.split()
    if len(args) < 2:
        await message.reply("📝 Usage: /craft list | /craft [recipe name]")
        return
    user_id = message.from_user.id
    async with db_pool.acquire() as conn:
        if args[1].lower() == 'list':
            recipes = await conn.fetch("SELECT * FROM recipes")
            if not recipes:
                await message.reply("❌ No recipes available.")
                return
            resp = "🔨 <b>Crafting Recipes</b>\n━━━━━━━━━━━━━━━━━━━\n"
            for r in recipes:
                resp += f"• <b>{e(r['name'])}</b> – {e(r['description'])}\n"
                resp += f"  Result: {e(r['result_item'])}\n"
                resp += f"  Cost: ¥{r['cost_yen']}\n"
                ingredients = json.loads(r['ingredients'])
                for mid, qty in ingredients.items():
                    mat = await conn.fetchrow("SELECT name FROM materials WHERE id = $1", int(mid))
                    mat_name = mat['name'] if mat else f"Material {mid}"
                    resp += f"    - {e(mat_name)} x{qty}\n"
            await message.reply(resp, parse_mode="HTML")
            return
        name = " ".join(args[1:])
        recipe = await conn.fetchrow("SELECT * FROM recipes WHERE name ILIKE $1", name)
        if not recipe:
            await message.reply("❌ Recipe not found.")
            return
        ingredients = json.loads(recipe['ingredients'])
        player = await conn.fetchrow("SELECT yen FROM players WHERE user_id = $1", user_id)
        if player['yen'] < recipe['cost_yen']:
            await message.reply(f"❌ Not enough Yen! Need ¥{recipe['cost_yen']}, have ¥{player['yen']}.")
            return
        for mid, qty in ingredients.items():
            player_mat = await conn.fetchrow("SELECT quantity FROM player_materials WHERE player_id = $1 AND material_id = $2", user_id, int(mid))
            if not player_mat or player_mat['quantity'] < qty:
                mat = await conn.fetchrow("SELECT name FROM materials WHERE id = $1", int(mid))
                mat_name = mat['name'] if mat else f"Material {mid}"
                await message.reply(f"❌ Not enough {mat_name}. Need {qty}.")
                return
        await conn.execute("UPDATE players SET yen = yen - $1 WHERE user_id = $2", recipe['cost_yen'], user_id)
        for mid, qty in ingredients.items():
            await conn.execute("UPDATE player_materials SET quantity = quantity - $1 WHERE player_id = $2 AND material_id = $3",
                               qty, user_id, int(mid))
        await conn.execute("UPDATE players SET bag = array_append(bag, $1) WHERE user_id = $2", recipe['result_item'], user_id)
        await message.reply(f"✅ Crafted <b>{e(recipe['result_item'])}</b>! Check /bag.", parse_mode="HTML")

@dp.message(Command("leaderboard"))
@friendly_error
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
            await message.reply("❌ Invalid category. Options: level, wins, boss_kills, prestige, yen")
            return
        if not rows:
            await message.reply("❌ No players found.")
            return
        resp = f"🏆 <b>Leaderboard – {category.title()}</b>\n━━━━━━━━━━━━━━━━━━━\n"
        for i, row in enumerate(rows, 1):
            val = row[category]
            resp += f"{i}. {e(row['username'])} – {val} {label}\n"
        await message.reply(resp, parse_mode="HTML")

@dp.message(Command("npc"))
@friendly_error
async def npc_cmd(message: types.Message):
    args = message.text.split()
    if len(args) < 2:
        await message.reply("📝 Usage:\n/npc list\n/npc talk [name]")
        return
    action = args[1].lower()
    async with db_pool.acquire() as conn:
        if action == "list":
            npcs = await conn.fetch("SELECT * FROM npcs")
            if not npcs:
                await message.reply("❌ No NPCs available.")
                return
            resp = "🧙 <b>Available NPCs</b>\n━━━━━━━━━━━━━━━━━━━\n"
            for n in npcs:
                resp += f"• <b>{e(n['name'])}</b> – {e(n['role'])}\n"
            resp += "\nUse /npc talk [name] to interact."
            await message.reply(resp, parse_mode="HTML")
        elif action == "talk":
            if len(args) < 3:
                await message.reply("📝 Usage: /npc talk [name]")
                return
            name = " ".join(args[2:])
            npc = await conn.fetchrow("SELECT * FROM npcs WHERE name ILIKE $1", name)
            if not npc:
                await message.reply(f"❌ NPC '{name}' not found.")
                return
            
            # -- NEW: Set session for text fallback --
            npc_sessions[message.from_user.id] = npc['id']
            
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="✅ Yes", callback_data=f"npc_yes_{npc['id']}"),
                 InlineKeyboardButton(text="❌ No", callback_data=f"npc_no_{npc['id']}")]
            ])
            await message.reply(f"🧙 <b>{e(npc['name'])}</b> says:\n{npc['dialogue']}", reply_markup=keyboard, parse_mode="HTML")

# -- NEW: NPC Button Fallbacks --
@dp.callback_query(lambda c: c.data.startswith("npc_yes_"))
async def npc_yes_cb(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    async with db_pool.acquire() as conn:
        player = await conn.fetchrow("SELECT ce FROM players WHERE user_id=$1", user_id)
        if not player or player['ce'] < 50:
            await callback.answer("❌ Not enough CE!", show_alert=True); return
        await conn.execute("UPDATE players SET ce = ce - 50, xp = xp + 20 WHERE user_id = $1", user_id)
        await callback.message.edit_text("✅ You trained! -50 CE, +20 XP.")
    if user_id in npc_sessions: del npc_sessions[user_id]
    await callback.answer()

@dp.callback_query(lambda c: c.data.startswith("npc_no_"))
async def npc_no_cb(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    await callback.message.edit_text("❌ You walked away.")
    if user_id in npc_sessions: del npc_sessions[user_id]
    await callback.answer()

@dp.message(Command("awakening"))
@friendly_error
async def awakening_cmd(message: types.Message):
    user_id = message.from_user.id
    async with db_pool.acquire() as conn:
        player = await conn.fetchrow("SELECT awakening, awakening_level, awakening_aura FROM players WHERE user_id = $1", user_id)
        if not player:
            await message.reply("❌ Start with /start first!")
            return
        if player['awakening']:
            await message.reply(
                f"🌀 <b>Awakening: {e(player['awakening'])}</b>\n"
                f"Level: {player['awakening_level']}\n"
                f"Aura: {'✅ Active' if player['awakening_aura'] else '❌ Inactive'}\n"
                f"━━━━━━━━━━━━━━━━━━━\n"
                f"Keep fighting to evolve your awakening!",
                parse_mode="HTML"
            )
        else:
            await message.reply(
                "🌀 <b>No Awakening Yet</b>\n"
                "Awakenings can be triggered by:\n"
                "• Defeating a boss (10% chance)\n"
                "• Dropping below 10% HP in battle (5% chance)\n"
                "• Random luck (1% chance)",
                parse_mode="HTML"
            )

async def send_owner_info(message: types.Message):
    await message.reply(
        f"👑 <b>Owner & Developer</b>\n"
        f"━━━━━━━━━━━━━━━━━━━\n"
        f"Name: {e(OWNER_NAME)}\n"
        f"ID: {OWNER_ID}\n"
        f"━━━━━━━━━━━━━━━━━━━\n"
        f"{YEN_PURCHASE_INFO}",
        parse_mode="HTML"
    )

@dp.message(Command("buyyen"))
async def buyyen_cmd(message: types.Message):
    await send_owner_info(message)

@dp.message(Command("commands"))
@friendly_error
async def commands_cmd(message: types.Message):
    await message.reply(
        "📋 <b>Cursed Chronicles — Command List</b>\n"
        "━━━━━━━━━━━━━━━━━━━\n"
        "<b>General</b>\n"
        "/start, /profile, /guide, /status, /resume [id], /commands, /buyyen, /stats\n"
        "━━━━━━━━━━━━━━━━━━━\n"
        "<b>Characters</b>\n"
        "/characters, /select [name]\n"
        "━━━━━━━━━━━━━━━━━━━\n"
        "<b>Battle</b>\n"
        "/battle, /boss [name], /enemies, /pvp_challenge [user], /pvp_accept [id], /raid, /raid_attack\n"
        "━━━━━━━━━━━━━━━━━━━\n"
        "<b>Shop & Inventory</b>\n"
        "/shop, /buy [item], /bag, /use [item], /equip [weapon], /techniques, /learn [tech]\n"
        "━━━━━━━━━━━━━━━━━━━\n"
        "<b>Clans</b>\n"
        "/clan create [name], /clan join [name], /clan info, /clan leave, /clan upgrade, /clan war [clan]\n"
        "━━━━━━━━━━━━━━━━━━━\n"
        "<b>Advanced</b>\n"
        "/awakening, /npc list, /npc talk [name], /shikigami, /restriction, /vow\n"
        "/story, /story_chapter [num], /dungeon, /tower, /achievements\n"
        "━━━━━━━━━━━━━━━━━━━\n"
        "<b>Quests & Events</b>\n"
        "/quests, /quest_accept [id], /quest_reward [id], /event, /event_battle [id]\n"
        "━━━━━━━━━━━━━━━━━━━\n"
        "<b>Crafting</b>\n"
        "/materials, /craft list, /craft [recipe]\n"
        "━━━━━━━━━━━━━━━━━━━\n"
        "<b>Leaderboard</b>\n"
        "/leaderboard [category] – level, wins, boss_kills, prestige, yen\n"
        "━━━━━━━━━━━━━━━━━━━\n"
        "<b>Admin</b> (owner only)\n"
        "/addadmin [user], /removeadmin [user], /broadcast [message]\n"
        "━━━━━━━━━━━━━━━━━━━\n"
        "<b>Owner</b> (full access)\n"
        "/addyen, /removeyen, /addyenall, /removeyenall, /addxp, /removexp, /setrank, /addlevel, /removelevel, /recalc, /diagnosis, /clearbattles",
        parse_mode="HTML"
    ) # ================================================================
# ADMIN & OWNER COMMANDS
# ================================================================

@dp.message(Command("addadmin"))
@friendly_error
async def add_admin_cmd(message: types.Message):
    if not await is_owner(message.from_user.id):
        await message.reply("❌ Only the owner can add admins!")
        return
    args = message.text.split()
    if len(args) < 2:
        await message.reply("📝 Usage: /addadmin @user")
        return
    target = args[1].replace("@", "")
    async with db_pool.acquire() as conn:
        user = await conn.fetchrow("SELECT user_id FROM players WHERE username ILIKE $1", target)
        if not user:
            await message.reply(f"❌ User '{target}' not found.")
            return
        await conn.execute("INSERT INTO admins (user_id, role) VALUES ($1, 'admin') ON CONFLICT DO NOTHING", user['user_id'])
        await message.reply(f"✅ Added {target} as an admin.")

@dp.message(Command("removeadmin"))
@friendly_error
async def remove_admin_cmd(message: types.Message):
    if not await is_owner(message.from_user.id):
        await message.reply("❌ Only the owner can remove admins!")
        return
    args = message.text.split()
    if len(args) < 2:
        await message.reply("📝 Usage: /removeadmin @user")
        return
    target = args[1].replace("@", "")
    async with db_pool.acquire() as conn:
        user = await conn.fetchrow("SELECT user_id FROM players WHERE username ILIKE $1", target)
        if not user:
            await message.reply(f"❌ User '{target}' not found.")
            return
        await conn.execute("DELETE FROM admins WHERE user_id = $1", user['user_id'])
        await message.reply(f"✅ Removed {target} from admins.")

@dp.message(Command("addyen"))
@friendly_error
async def addyen_cmd(message: types.Message):
    if not await can_manage_yen(message.from_user.id):
        await message.reply("❌ Only the owner can manage Yen!")
        return
    args = message.text.split()
    if len(args) < 3:
        await message.reply("📝 Usage: /addyen @user amount")
        return
    target = args[1].replace("@", "")
    amount = int(args[2])
    if amount <= 0 or amount > MAX_YEN:
        await message.reply(f"❌ Amount must be between 1 and {MAX_YEN}.")
        return
    async with db_pool.acquire() as conn:
        res = await conn.execute("UPDATE players SET yen = LEAST(yen + $1, $2) WHERE username ILIKE $3",
                                 amount, MAX_YEN, target)
        if res == "UPDATE 0":
            await message.reply(f"❌ User '{target}' not found.")
        else:
            await message.reply(f"✅ Added ¥{amount:,} to {target}.")

@dp.message(Command("removeyen"))
@friendly_error
async def removeyen_cmd(message: types.Message):
    if not await can_manage_yen(message.from_user.id):
        await message.reply("❌ Only the owner can manage Yen!")
        return
    args = message.text.split()
    if len(args) < 3:
        await message.reply("📝 Usage: /removeyen @user amount")
        return
    target = args[1].replace("@", "")
    amount = int(args[2])
    if amount <= 0:
        await message.reply("❌ Amount must be positive.")
        return
    async with db_pool.acquire() as conn:
        res = await conn.execute("UPDATE players SET yen = yen - $1 WHERE username ILIKE $2 AND yen >= $1",
                                 amount, target)
        if res == "UPDATE 0":
            await message.reply(f"❌ User not found or insufficient yen.")
        else:
            await message.reply(f"✅ Removed ¥{amount:,} from {target}.")

@dp.message(Command("addxp"))
@friendly_error
async def addxp_cmd(message: types.Message):
    if not await is_owner(message.from_user.id) and not await is_admin(message.from_user.id):
        await message.reply("❌ Admin or Owner only!")
        return
    args = message.text.split()
    if len(args) < 3:
        await message.reply("📝 Usage: /addxp @user amount")
        return
    target = args[1].replace("@", "")
    amount = int(args[2])
    if amount <= 0:
        await message.reply("❌ Amount must be positive.")
        return
    async with db_pool.acquire() as conn:
        player = await conn.fetchrow("SELECT * FROM players WHERE username ILIKE $1", target)
        if not player:
            await message.reply(f"❌ User '{target}' not found.")
            return
        new_xp = player['xp'] + amount
        await conn.execute("UPDATE players SET xp = $1 WHERE username ILIKE $2", new_xp, target)
        await update_player_stats(player['user_id'])
        await message.reply(f"✅ Added {amount} XP to {target}.")

@dp.message(Command("removexp"))
@friendly_error
async def removexp_cmd(message: types.Message):
    if not await is_owner(message.from_user.id) and not await is_admin(message.from_user.id):
        await message.reply("❌ Admin or Owner only!")
        return
    args = message.text.split()
    if len(args) < 3:
        await message.reply("📝 Usage: /removexp @user amount")
        return
    target = args[1].replace("@", "")
    amount = int(args[2])
    if amount <= 0:
        await message.reply("❌ Amount must be positive.")
        return
    async with db_pool.acquire() as conn:
        player = await conn.fetchrow("SELECT * FROM players WHERE username ILIKE $1", target)
        if not player:
            await message.reply(f"❌ User '{target}' not found.")
            return
        new_xp = max(0, player['xp'] - amount)
        await conn.execute("UPDATE players SET xp = $1 WHERE username ILIKE $2", new_xp, target)
        await update_player_stats(player['user_id'])
        await message.reply(f"✅ Removed {amount} XP from {target}.")

@dp.message(Command("setrank"))
@friendly_error
async def setrank_cmd(message: types.Message):
    if not await is_owner(message.from_user.id) and not await is_admin(message.from_user.id):
        await message.reply("❌ Admin or Owner only!")
        return
    args = message.text.split(maxsplit=2)
    if len(args) < 3:
        await message.reply("📝 Usage: /setrank @user rank")
        return
    target = args[1].replace("@", "")
    rank = args[2]
    async with db_pool.acquire() as conn:
        res = await conn.execute("UPDATE players SET rank = $1 WHERE username ILIKE $2", rank, target)
        if res == "UPDATE 0":
            await message.reply(f"❌ User '{target}' not found.")
        else:
            await message.reply(f"✅ Set {target}'s rank to {rank}.")

@dp.message(Command("addlevel"))
@friendly_error
async def addlevel_cmd(message: types.Message):
    if not await is_owner(message.from_user.id) and not await is_admin(message.from_user.id):
        await message.reply("❌ Admin or Owner only!")
        return
    args = message.text.split()
    if len(args) < 3:
        await message.reply("📝 Usage: /addlevel @user amount")
        return
    target = args[1].replace("@", "")
    amount = int(args[2])
    if amount <= 0:
        await message.reply("❌ Amount must be positive.")
        return
    async with db_pool.acquire() as conn:
        player = await conn.fetchrow("SELECT * FROM players WHERE username ILIKE $1", target)
        if not player:
            await message.reply(f"❌ User '{target}' not found.")
            return
        new_level = player['level'] + amount
        await conn.execute("UPDATE players SET level = $1 WHERE username ILIKE $2", new_level, target)
        await update_player_stats(player['user_id'])
        await message.reply(f"✅ Added {amount} levels to {target}.")

@dp.message(Command("removelevel"))
@friendly_error
async def removelevel_cmd(message: types.Message):
    if not await is_owner(message.from_user.id) and not await is_admin(message.from_user.id):
        await message.reply("❌ Admin or Owner only!")
        return
    args = message.text.split()
    if len(args) < 3:
        await message.reply("📝 Usage: /removelevel @user amount")
        return
    target = args[1].replace("@", "")
    amount = int(args[2])
    if amount <= 0:
        await message.reply("❌ Amount must be positive.")
        return
    async with db_pool.acquire() as conn:
        player = await conn.fetchrow("SELECT * FROM players WHERE username ILIKE $1", target)
        if not player:
            await message.reply(f"❌ User '{target}' not found.")
            return
        new_level = max(1, player['level'] - amount)
        await conn.execute("UPDATE players SET level = $1 WHERE username ILIKE $2", new_level, target)
        await update_player_stats(player['user_id'])
        await message.reply(f"✅ Removed {amount} levels from {target}.")

@dp.message(Command("recalc"))
@friendly_error
async def recalc_cmd(message: types.Message):
    if not await is_owner(message.from_user.id) and not await is_admin(message.from_user.id):
        await message.reply("❌ Admin or Owner only!")
        return
    args = message.text.split()
    async with db_pool.acquire() as conn:
        if len(args) > 1:
            target = args[1].replace("@", "")
            player = await conn.fetchrow("SELECT * FROM players WHERE username ILIKE $1", target)
            if not player:
                await message.reply(f"❌ User '{target}' not found.")
                return
            await update_player_stats(player['user_id'])
            await message.reply(f"✅ Recalculated {target}.")
        else:
            players = await conn.fetch("SELECT user_id FROM players")
            for p in players:
                await update_player_stats(p['user_id'])
            await message.reply(f"✅ Recalculated all {len(players)} players.")

@dp.message(Command("diagnosis"))
@friendly_error
async def diagnosis_cmd(message: types.Message):
    if not await is_owner(message.from_user.id):
        await message.reply("❌ Owner only.")
        return

    report = []
    report.append("🔍 CURSED CHRONICLES – SYSTEM DIAGNOSIS")
    report.append(f"🕒 Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    report.append("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    report.append("📊 All data below is fetched in real‑time.")

    report.append("\n🌐 ENVIRONMENT")
    env_vars = ["BOT_TOKEN", "DATABASE_URL", "OWNER_ID"]
    for var in env_vars:
        if var == "OWNER_ID":
            value = f"{OWNER_ID}" if OWNER_ID else "❌ Not set"
        else:
            value = "✅ Set" if os.getenv(var) else "❌ Missing"
        report.append(f"• {var}: {value}")

    report.append("\n🗄️ DATABASE")
    try:
        async with db_pool.acquire() as conn:
            test = await conn.fetchval("SELECT 1")
            report.append("• Connection: ✅ OK" if test == 1 else "❌ Failed")

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
                    report.append(f"• Table '{table}': ✅ {count} rows")
                except Exception as exc:
                    report.append(f"• Table '{table}': ❌ {str(exc)[:30]}")

            total_players = await conn.fetchval("SELECT COUNT(*) FROM players")
            active_battles_db = await conn.fetchval("SELECT COUNT(*) FROM battles WHERE status = 'active'")
            report.append(f"• Total players: {total_players}")
            report.append(f"• Active battles (DB): {active_battles_db}")
    except Exception as exc:
        report.append(f"❌ Database error: {exc}")

    report.append("\n🧠 GLOBAL STATE (IN‑MEMORY)")
    report.append(f"• ongoing_battles: {len(ongoing_battles)} entries")
    report.append(f"• battle_queues: {len(battle_queues)} entries")
    report.append(f"• pvp_matches: {len(pvp_matches)} entries")

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

    report.append("\n📊 BATTLE QUEUES SNAPSHOT")
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

    report.append("\n⚔️ PVP MATCHES")
    if pvp_matches:
        for b_id, meta in pvp_matches.items():
            report.append(f"• Battle {b_id}: Challenger={meta['challenger']}, Target={meta['target']}, Turn={meta.get('turn', 1)}")
    else:
        report.append("• No PvP matches.")

    report.append("\n📋 COMMANDS REGISTERED")
    cmd_list = [
        "start", "guide", "stats", "addyenall", "removeyenall",
        "restriction", "vow", "shikigami", "profile", "characters",
        "select", "shop", "buy", "bag", "use", "equip", "learn",
        "techniques", "enemies", "story", "story_chapter", "boss",
        "battle", "status", "resume", "prestige", "pvp_challenge",
        "pvp_accept", "missions", "daily", "clan",
        "awakening", "npc", "dungeon", "tower", "achievements",
        "buyyen", "commands", "addadmin", "removeadmin", "addyen",
        "removeyen", "addxp", "removexp", "setrank", "addlevel",
        "removelevel", "recalc", "diagnosis", "clearbattles",
        "event", "event_battle", "quests", "quest_accept", "quest_reward",
        "materials", "craft", "leaderboard", "broadcast",
        "raid", "raid_attack", "users"
    ]
    report.append(f"• Total commands: {len(cmd_list)}")
    report.append(f"• List: {', '.join(cmd_list)}")

    report.append("\n🛠️ RECOMMENDATIONS")
    issues = []
    if orphaned or stale:
        issues.append("• Clear orphaned/stale battles using /clearbattles.")
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
        await message.reply(final_report)

@dp.message(Command("clearbattles"))
@friendly_error
async def clearbattles_cmd(message: types.Message):
    if not await is_owner(message.from_user.id):
        await message.reply("❌ Owner only.")
        return
    ongoing_battles.clear()
    battle_queues.clear()
    pvp_matches.clear()
    user_sessions.clear()
    async with db_pool.acquire() as conn:
        await conn.execute("UPDATE battles SET status = 'abandoned' WHERE status = 'active' OR status = 'pending'")
    await message.reply("✅ All battle data cleared.")

@dp.message(Command("broadcast"))
@friendly_error
async def broadcast_cmd(message: types.Message):
    if not await is_owner(message.from_user.id):
        await message.reply("❌ Owner only.")
        return
    text = message.text.replace('/broadcast', '', 1).strip()
    if not text:
        await message.reply("📝 Usage: /broadcast [message]")
        return
    async with db_pool.acquire() as conn:
        players = await conn.fetch("SELECT user_id FROM players")
        sent = 0
        for p in players:
            try:
                await bot.send_message(p['user_id'], f"📢 <b>Announcement:</b>\n{text}", parse_mode="HTML")
                sent += 1
                await asyncio.sleep(0.05)
            except:
                pass
        await message.reply(f"✅ Broadcast sent to {sent} players.")

# ================================================================
# NEW QOL COMMANDS (TOGGLES, VOW_STATUS, INSPECT, SEASON)
# ================================================================

@dp.message(Command("users"))
@friendly_error
async def users_cmd(message: types.Message):
    if not await is_owner(message.from_user.id) and not await is_admin(message.from_user.id):
        await message.reply("❌ Admin or Owner only!")
        return
    async with db_pool.acquire() as conn:
        rows = await conn.fetch("SELECT user_id, username, first_name, level FROM players ORDER BY user_id LIMIT 50")
        if not rows:
            await message.reply("📭 No players found.")
            return
        txt = "📋 **Registered Users (Recent 50):**\n\n"
        for idx, row in enumerate(rows, 1):
            username = f"@{row['username']}" if row['username'] else "No username"
            name = e(row['first_name'] or "Unknown")
            txt += f"{idx}. `{row['user_id']}` — {name} ({username}) [Lv.{row['level']}]\n"
        await message.reply(txt, parse_mode="HTML")

@dp.message(Command("toggles"))
@friendly_error
async def toggles_cmd(message: types.Message):
    args = message.text.split()
    if len(args) < 2: return await message.reply("📝 Usage: /toggles detailed | /toggles brief")
    mode = args[1].lower()
    if mode not in ['detailed', 'brief']: return await message.reply("❌ Invalid mode. Choose 'detailed' or 'brief'.")
    async with db_pool.acquire() as conn:
        await conn.execute("UPDATE players SET battle_mode = $1 WHERE user_id = $2", mode, message.from_user.id)
    await message.reply(f"✅ Battle mode set to <b>{mode.capitalize()}</b>.", parse_mode="HTML")

@dp.message(Command("vow_status"))
@friendly_error
async def vow_status_cmd(message: types.Message):
    user_id = message.from_user.id
    async with db_pool.acquire() as conn:
        vows = await conn.fetch("SELECT v.name, pv.last_used, v.cooldown, pv.active FROM player_vows pv JOIN binding_vows v ON pv.vow_id = v.id WHERE pv.player_id = $1", user_id)
        if not vows: return await message.reply("❌ You have no Binding Vows.")
        resp = "⚖️ <b>Vow Status</b>\n━━━━━━━━━━━━\n"
        now = datetime.now()
        for v in vows:
            if v['active']:
                remaining = max(0, (v['last_used'] + timedelta(minutes=v['cooldown']) - now).total_seconds())
                resp += f"• {e(v['name'])}: Active (Cooldown: {int(remaining)}s)\n"
            else:
                resp += f"• {e(v['name'])}: Inactive/Expired\n"
        await message.reply(resp, parse_mode="HTML")

@dp.message(Command("inspect"))
@friendly_error
async def inspect_cmd(message: types.Message):
    args = message.text.split(maxsplit=1)
    if len(args) < 2: return await message.reply("📝 Usage: /inspect @user")
    target = args[1].replace("@", "")
    async with db_pool.acquire() as conn:
        p = await conn.fetchrow("SELECT username, level, prestige_level, character_name, wins, losses, boss_kills, curse_rank FROM players WHERE username ILIKE $1", target)
        if not p: return await message.reply(f"❌ User '{target}' not found.")
        resp = f"👤 <b>{e(p['username'])}</b>\n━━━━━━━━━━━━\n🎭 {e(p['character_name'])}\n📊 Level: {p['level']}\n💎 Prestige: {p['prestige_level']}\n🏆 {p['wins']} W | {p['losses']} L\n👑 Boss Kills: {p['boss_kills']}\n👹 Curse Rank: {e(p['curse_rank'])}"
        await message.reply(resp, parse_mode="HTML")

@dp.message(Command("season"))
@friendly_error
async def season_cmd(message: types.Message):
    user_id = message.from_user.id
    async with db_pool.acquire() as conn:
        prog = await conn.fetchval("SELECT season_progress FROM players WHERE user_id = $1", user_id) or 0
        tier = prog // 10
        await message.reply(f"📅 <b>Season: {CURRENT_SEASON}</b>\n━━━━━━━━━━━━\nPoints: {prog}\nCurrent Tier: {tier}\nNext Reward at: {(tier+1)*10} points", parse_mode="HTML")

# ================================================================
# NPC TEXT FALLBACK & TYPO HANDLER
# ================================================================

@dp.message()
async def npc_text_fallback(message: types.Message):
    user_id = message.from_user.id
    if message.text.startswith('/') or user_id not in npc_sessions: return
    text = message.text.lower()
    async with db_pool.acquire() as conn:
        if text in ['yes', 'yeq', 'yep', 'yeah', 'y']:
            npc_id = npc_sessions[user_id]
            player = await conn.fetchrow("SELECT ce FROM players WHERE user_id = $1", user_id)
            if player and player['ce'] >= 50:
                await conn.execute("UPDATE players SET ce = ce - 50, xp = xp + 20 WHERE user_id = $1", user_id)
                await message.reply("✅ You trained! -50 CE, +20 XP.")
            else: await message.reply("❌ Not enough CE!")
            del npc_sessions[user_id]
            return
        elif text in ['no', 'n', 'nah']:
            del npc_sessions[user_id]; await message.reply("❌ You walked away.")

@dp.message()
async def typo_handler(message: types.Message):
    if not message.text.startswith('/'): return
    cmd = message.text.split()[0].lower().lstrip('/')
    if cmd in ALL_COMMANDS: return
    matches = difflib.get_close_matches(cmd, ALL_COMMANDS, n=3, cutoff=0.7)
    if matches: await message.reply(f"❓ Unknown command `/{cmd}`. Did you mean: {', '.join([f'/{m}' for m in matches])}?")
    else: await message.reply(f"❓ Unknown command `/{cmd}`. Type /commands for the full list.")
# ================================================================
# DUNGEON, TOWER, ACHIEVEMENTS, QUESTS, EVENTS, MATERIALS, CRAFT, LEADERBOARD, NPC, USERS, TOGGLES, INSPECT, SEASON, ADMIN
# ================================================================

@dp.message(Command("dungeon"))
@friendly_error
async def dungeon_cmd(message: types.Message):
    user_id = message.from_user.id
    if user_id in ongoing_battles:
        await message.reply("⚠️ Already in battle.")
        return
    async with db_pool.acquire() as conn:
        player = await conn.fetchrow("SELECT * FROM players WHERE user_id=$1", user_id)
        run = await conn.fetchrow("SELECT id, floor FROM dungeon_runs WHERE player_id=$1 AND status='active'", user_id)
        if not run:
            run_id = await conn.fetchval("INSERT INTO dungeon_runs (player_id, floor, status) VALUES ($1,1,'active') RETURNING id", user_id)
            floor = 1
        else:
            run_id, floor = run['id'], run['floor']
        enemy_base = await conn.fetchrow("SELECT * FROM enemies WHERE is_boss=FALSE ORDER BY RANDOM() LIMIT 1")
        enemy = scale_enemy_to_player(player, enemy_base)
        enemy['hp'] = int(enemy['hp'] * (1 + floor * 0.2))
        enemy['atk'] = int(enemy['atk'] * (1 + floor * 0.15))
        enemy['def'] = int(enemy['def'] * (1 + floor * 0.1))
        enemy['reward_yen'] = int(enemy['reward_yen'] * (1 + floor * 0.1))
        enemy['reward_xp'] = int(enemy['reward_xp'] * (1 + floor * 0.1))
        battle_id = await conn.fetchval("""
            INSERT INTO battles (chat_id, player1_id, current_hp1, current_hp2, 
                enemy_name, enemy_rank, enemy_atk, enemy_def, enemy_spd,
                is_boss, enemy_reward_yen, enemy_reward_xp, enemy_max_hp,
                is_dungeon, dungeon_run_id)
            VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,FALSE,$10,$11,$12,TRUE,$13)
            RETURNING id
        """, message.chat.id, user_id, player['hp'], enemy['hp'], enemy['name'], 
            f"Floor {floor}", enemy['atk'], enemy['def'], enemy['spd'],
            enemy['reward_yen'], enemy['reward_xp'], enemy['hp'], run_id)
        ongoing_battles[user_id] = battle_id
        battle_queues[battle_id] = {"participants": {user_id: []}, "current_hp": enemy['hp'], "log": []}
        await show_battle_turn(message, battle_id, player, enemy, [])

@dp.message(Command("tower"))
@friendly_error
async def tower_cmd(message: types.Message):
    user_id = message.from_user.id
    if user_id in ongoing_battles:
        await message.reply("⚠️ Already in battle.")
        return
    async with db_pool.acquire() as conn:
        player = await conn.fetchrow("SELECT * FROM players WHERE user_id=$1", user_id)
        run = await conn.fetchrow("SELECT id, floor FROM tower_runs WHERE player_id=$1 AND status='active'", user_id)
        if not run:
            run_id = await conn.fetchval("INSERT INTO tower_runs (player_id, floor, status) VALUES ($1,1,'active') RETURNING id", user_id)
            floor = 1
        else:
            run_id, floor = run['id'], run['floor']
        if floor > 100:
            await message.reply("🏆 Tower Complete!")
            await conn.execute("UPDATE tower_runs SET status='completed' WHERE id=$1", run_id)
            return
        is_boss = (floor % 10 == 0)
        enemy_base = await conn.fetchrow("SELECT * FROM enemies WHERE is_boss=$1 ORDER BY RANDOM() LIMIT 1", is_boss)
        enemy = scale_enemy_to_player(player, enemy_base)
        enemy['hp'] = int(enemy['hp'] * (1 + floor * 0.1))
        enemy['atk'] = int(enemy['atk'] * (1 + floor * 0.08))
        enemy['def'] = int(enemy['def'] * (1 + floor * 0.05))
        battle_id = await conn.fetchval("""
            INSERT INTO battles (chat_id, player1_id, current_hp1, current_hp2, 
                enemy_name, enemy_rank, enemy_atk, enemy_def, enemy_spd,
                is_boss, enemy_reward_yen, enemy_reward_xp, enemy_max_hp,
                is_tower, tower_run_id, tower_floor)
            VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12,$13,TRUE,$14,$15)
            RETURNING id
        """, message.chat.id, user_id, player['hp'], enemy['hp'], enemy['name'], 
            f"Floor {floor}", enemy['atk'], enemy['def'], enemy['spd'],
            is_boss, enemy['reward_yen'], enemy['reward_xp'], enemy['hp'], run_id, floor)
        ongoing_battles[user_id] = battle_id
        battle_queues[battle_id] = {"participants": {user_id: []}, "current_hp": enemy['hp'], "log": []}
        await show_battle_turn(message, battle_id, player, enemy, [])

@dp.message(Command("achievements"))
@friendly_error
async def achievements_cmd(message: types.Message):
    user_id = message.from_user.id
    async with db_pool.acquire() as conn:
        all_ach = await conn.fetch("SELECT * FROM achievements")
        unlocked = [a['achievement_id'] for a in await conn.fetch("SELECT achievement_id FROM player_achievements WHERE player_id=$1", user_id)]
        resp = "🏆 **Achievements**\n━━━━━━━\n" + "\n".join(
            [f"{'✅' if a['id'] in unlocked else '🔒'} {e(a['name'])} – {e(a['description'])}" for a in all_ach]
        )
        await message.reply(resp, parse_mode="HTML")

@dp.message(Command("quests"))
@friendly_error
async def quests_cmd(message: types.Message):
    user_id = message.from_user.id
    async with db_pool.acquire() as conn:
        quests = await conn.fetch("SELECT * FROM quests")
        player_q = {q['quest_id']: q for q in await conn.fetch("SELECT * FROM player_quests WHERE player_id=$1", user_id)}
        resp = "📜 **Quests**\n━━━━━━━\n"
        for q in quests:
            pq = player_q.get(q['id'])
            status = "✅ Completed" if pq and pq['completed'] else f"{pq['progress']}/{q['requirement'].split(':')[1]}" if pq else "Not Started"
            resp += f"• <b>{e(q['title'])}</b> [{status}]\n  {e(q['description'])} (Reward: ¥{q['reward_yen']}, XP {q['reward_xp']})\n"
        await message.reply(resp, parse_mode="HTML")

@dp.message(Command("quest_accept"))
@friendly_error
async def quest_accept(message: types.Message):
    args = message.text.split()
    if len(args) < 2:
        return await message.reply("Usage: /quest_accept [quest_id]")
    quest_id = int(args[1])
    user_id = message.from_user.id
    async with db_pool.acquire() as conn:
        if await conn.fetchrow("SELECT 1 FROM player_quests WHERE player_id=$1 AND quest_id=$2", user_id, quest_id):
            return await message.reply("❌ Already have this quest.")
        await conn.execute("INSERT INTO player_quests (player_id, quest_id, progress) VALUES ($1,$2,0)", user_id, quest_id)
        await message.reply("✅ Quest accepted!")

@dp.message(Command("quest_reward"))
@friendly_error
async def quest_reward(message: types.Message):
    args = message.text.split()
    if len(args) < 2:
        return await message.reply("Usage: /quest_reward [quest_id]")
    quest_id = int(args[1])
    user_id = message.from_user.id
    async with db_pool.acquire() as conn:
        pq = await conn.fetchrow("SELECT * FROM player_quests WHERE player_id=$1 AND quest_id=$2 AND completed=TRUE", user_id, quest_id)
        if not pq:
            return await message.reply("❌ Quest not completed.")
        quest = await conn.fetchrow("SELECT * FROM quests WHERE id=$1", quest_id)
        await conn.execute("UPDATE players SET yen=LEAST(yen+$1,$2), xp=xp+$3 WHERE user_id=$4",
                           quest['reward_yen'], MAX_YEN, quest['reward_xp'], user_id)
        if quest.get('reward_item'):
            await conn.execute("UPDATE players SET bag=array_append(bag,$1) WHERE user_id=$2", quest['reward_item'], user_id)
        await conn.execute("DELETE FROM player_quests WHERE player_id=$1 AND quest_id=$2", user_id, quest_id)
        await message.reply(f"✅ Rewards claimed for <b>{e(quest['title'])}</b>!", parse_mode="HTML")

@dp.message(Command("event"))
@friendly_error
async def event_cmd(message: types.Message):
    async with db_pool.acquire() as conn:
        now = datetime.now()
        events = await conn.fetch("SELECT * FROM events WHERE active=TRUE AND start_time<=$1 AND end_time>=$1", now)
        if not events:
            return await message.reply("🎯 No active events.")
        resp = "🎯 **Active Events**\n"
        for ev in events:
            resp += f"• {ev['event_type'].title()}: <b>{e(ev['boss_name'])}</b> (ends {ev['end_time']})\n"
        resp += "\nUse /event_battle [event_id] to fight."
        await message.reply(resp, parse_mode="HTML")

@dp.message(Command("event_battle"))
@friendly_error
async def event_battle_cmd(message: types.Message):
    args = message.text.split()
    if len(args) < 2:
        return await message.reply("Usage: /event_battle [event_id]")
    event_id = int(args[1])
    user_id = message.from_user.id
    if user_id in ongoing_battles:
        return await message.reply("⚠️ Already in battle.")
    async with db_pool.acquire() as conn:
        event = await conn.fetchrow("SELECT * FROM events WHERE id=$1 AND active=TRUE AND start_time<=NOW() AND end_time>=NOW()", event_id)
        if not event:
            return await message.reply("❌ Event not found or expired.")
        player = await conn.fetchrow("SELECT * FROM players WHERE user_id=$1", user_id)
        enemy_base = await conn.fetchrow("SELECT * FROM enemies WHERE name ILIKE $1", event['boss_name'])
        enemy = scale_enemy_to_player(player, enemy_base)
        enemy['hp'] = int(enemy['hp'] * 1.5)
        enemy['reward_yen'] = int(enemy['reward_yen'] * 1.5)
        enemy['reward_xp'] = int(enemy['reward_xp'] * 1.5)
        battle_id = await conn.fetchval("""
            INSERT INTO battles (chat_id, player1_id, current_hp1, current_hp2,
                enemy_name, enemy_rank, enemy_atk, enemy_def, enemy_spd,
                is_boss, enemy_reward_yen, enemy_reward_xp, enemy_max_hp,
                is_event, event_id)
            VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,TRUE,$10,$11,$12,TRUE,$13)
            RETURNING id
        """, message.chat.id, user_id, player['hp'], enemy['hp'], enemy['name'],
            enemy['rank'], enemy['atk'], enemy['def'], enemy['spd'],
            enemy['reward_yen'], enemy['reward_xp'], enemy['hp'], event_id)
        ongoing_battles[user_id] = battle_id
        battle_queues[battle_id] = {"participants": {user_id: []}, "current_hp": enemy['hp'], "log": []}
        await show_battle_turn(message, battle_id, player, enemy, [])

@dp.message(Command("materials"))
@friendly_error
async def materials_cmd(message: types.Message):
    user_id = message.from_user.id
    async with db_pool.acquire() as conn:
        mats = await conn.fetch("SELECT m.name, m.rarity, pm.quantity FROM materials m LEFT JOIN player_materials pm ON m.id=pm.material_id AND pm.player_id=$1", user_id)
        if not mats:
            return await message.reply("📦 You have no materials.")
        resp = "📦 **Your Materials**\n" + "\n".join([f"• {e(m['name'])} x{m['quantity'] or 0} ({e(m['rarity'])})" for m in mats])
        await message.reply(resp, parse_mode="HTML")

@dp.message(Command("craft"))
@friendly_error
async def craft_cmd(message: types.Message):
    args = message.text.split()
    if len(args) < 2:
        return await message.reply("Usage: /craft list | /craft [recipe]")
    async with db_pool.acquire() as conn:
        if args[1].lower() == 'list':
            recipes = await conn.fetch("SELECT * FROM recipes")
            if not recipes:
                return await message.reply("❌ No recipes.")
            resp = "🔨 **Recipes**\n"
            for r in recipes:
                mats = json.loads(r['ingredients'])
                mat_str = ", ".join([f"Mat {mid} x{qty}" for mid, qty in mats.items()])
                resp += f"• <b>{e(r['name'])}</b>: {e(r['result_item'])} (Cost: ¥{r['cost_yen']}, Needs: {mat_str})\n"
            await message.reply(resp, parse_mode="HTML")
        else:
            name = " ".join(args[1:])
            recipe = await conn.fetchrow("SELECT * FROM recipes WHERE name ILIKE $1", name)
            if not recipe:
                return await message.reply("❌ Recipe not found.")
            mats = json.loads(recipe['ingredients'])
            player = await conn.fetchrow("SELECT yen FROM players WHERE user_id=$1", message.from_user.id)
            if player['yen'] < recipe['cost_yen']:
                return await message.reply(f"❌ Not enough Yen! Need ¥{recipe['cost_yen']}.")
            for mid, qty in mats.items():
                pm = await conn.fetchrow("SELECT quantity FROM player_materials WHERE player_id=$1 AND material_id=$2", message.from_user.id, int(mid))
                if not pm or pm['quantity'] < qty:
                    mat = await conn.fetchrow("SELECT name FROM materials WHERE id=$1", int(mid))
                    return await message.reply(f"❌ Not enough {e(mat['name'])}. Need {qty}.")
            await conn.execute("UPDATE players SET yen=yen-$1 WHERE user_id=$2", recipe['cost_yen'], message.from_user.id)
            for mid, qty in mats.items():
                await conn.execute("UPDATE player_materials SET quantity=quantity-$1 WHERE player_id=$2 AND material_id=$3",
                                   qty, message.from_user.id, int(mid))
            await conn.execute("UPDATE players SET bag=array_append(bag,$1) WHERE user_id=$2", recipe['result_item'], message.from_user.id)
            await message.reply(f"✅ Crafted <b>{e(recipe['result_item'])}</b>!", parse_mode="HTML")

@dp.message(Command("leaderboard"))
@friendly_error
async def leaderboard_cmd(message: types.Message):
    args = message.text.split()
    category = args[1].lower() if len(args) > 1 else 'level'
    if category not in ['level','wins','boss_kills','prestige','yen']:
        return await message.reply("❌ Invalid category.")
    async with db_pool.acquire() as conn:
        rows = await conn.fetch(f"SELECT username, {category} FROM players ORDER BY {category} DESC LIMIT 10")
        resp = f"🏆 **Top 10 by {category.title()}**\n" + "\n".join(
            [f"{i+1}. {e(r['username'])} – {r[category]}" for i, r in enumerate(rows)]
        )
        await message.reply(resp, parse_mode="HTML")

# --- NPC SYSTEM ---
@dp.message(Command("npc"))
@friendly_error
async def npc_cmd(message: types.Message):
    args = message.text.split()
    if len(args) < 2:
        return await message.reply("Usage: /npc list | /npc talk [name]")
    action = args[1].lower()
    async with db_pool.acquire() as conn:
        if action == "list":
            npcs = await conn.fetch("SELECT * FROM npcs ORDER BY name")
            if not npcs:
                return await message.reply("❌ No NPCs.")
            resp = "🧙 **Available NPCs**\n" + "\n".join(
                [f"• <b>{e(n['name'])}</b> – {e(n['role'])}" for n in npcs]
            )
            await message.reply(resp, parse_mode="HTML")
        elif action == "talk":
            if len(args) < 3:
                return await message.reply("Usage: /npc talk [name]")
            name = " ".join(args[2:])
            npc = await conn.fetchrow("SELECT * FROM npcs WHERE name ILIKE $1", name)
            if not npc:
                return await message.reply(f"❌ NPC '{name}' not found.")
            dialogue = npc.get('dialogue') or npc.get('description') or "I have nothing to say."
            npc_sessions[message.from_user.id] = npc['id']
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="✅ Yes", callback_data=f"npc_yes_{npc['id']}"),
                 InlineKeyboardButton(text="❌ No", callback_data=f"npc_no_{npc['id']}")]
            ])
            await message.reply(f"🧙 **{e(npc['name'])}** says:\n{e(dialogue)}", reply_markup=keyboard, parse_mode="HTML")
        else:
            await message.reply("❌ Unknown action.")

@dp.callback_query(lambda c: c.data.startswith("npc_yes_"))
async def npc_yes_cb(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    async with db_pool.acquire() as conn:
        player = await conn.fetchrow("SELECT ce FROM players WHERE user_id=$1", user_id)
        if not player or player['ce'] < 50:
            await callback.answer("❌ Not enough CE!", show_alert=True)
            return
        await conn.execute("UPDATE players SET ce=ce-50, xp=xp+20 WHERE user_id=$1", user_id)
        await callback.message.edit_text("✅ You trained! -50 CE, +20 XP.")
    if user_id in npc_sessions: del npc_sessions[user_id]
    await callback.answer()

@dp.callback_query(lambda c: c.data.startswith("npc_no_"))
async def npc_no_cb(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    await callback.message.edit_text("❌ You walked away.")
    if user_id in npc_sessions: del npc_sessions[user_id]
    await callback.answer()

@dp.message()
async def npc_text_fallback(message: types.Message):
    user_id = message.from_user.id
    if message.text.startswith('/') or user_id not in npc_sessions:
        return
    text = message.text.lower()
    if text in ['yes', 'yeq', 'yep', 'yeah', 'y']:
        async with db_pool.acquire() as conn:
            player = await conn.fetchrow("SELECT ce FROM players WHERE user_id=$1", user_id)
            if not player or player['ce'] < 50:
                await message.reply("❌ Not enough CE!")
                del npc_sessions[user_id]
                return
            await conn.execute("UPDATE players SET ce=ce-50, xp=xp+20 WHERE user_id=$1", user_id)
        await message.reply("✅ You trained! -50 CE, +20 XP.")
        del npc_sessions[user_id]
        return
    if text in ['no', 'n', 'nah']:
        await message.reply("❌ You walked away.")
        del npc_sessions[user_id]

# --- ADMIN COMMANDS ---
@dp.message(Command("users"))
@friendly_error
async def users_cmd(message: types.Message):
    if not await is_owner(message.from_user.id) and not await is_admin(message.from_user.id):
        return await message.reply("❌ Admin only.")
    async with db_pool.acquire() as conn:
        rows = await conn.fetch("SELECT user_id, username, first_name, level FROM players ORDER BY user_id LIMIT 50")
        if not rows: return await message.reply("No players.")
        resp = "📋 **Players (Last 50)**\n" + "\n".join(
            [f"{i+1}. `{r['user_id']}` – {e(r['username'])} (Lv.{r['level']})" for i, r in enumerate(rows)]
        )
        await message.reply(resp[:4096], parse_mode="HTML")

@dp.message(Command("toggles"))
@friendly_error
async def toggles_cmd(message: types.Message):
    args = message.text.split()
    if len(args) < 2:
        return await message.reply("Usage: /toggles detailed | /toggles brief")
    mode = args[1].lower()
    if mode not in ['detailed', 'brief']:
        return await message.reply("❌ Invalid mode.")
    async with db_pool.acquire() as conn:
        await conn.execute("UPDATE players SET battle_mode=$1 WHERE user_id=$2", mode, message.from_user.id)
    await message.reply(f"✅ Battle mode set to {mode}.")

@dp.message(Command("inspect"))
@friendly_error
async def inspect_cmd(message: types.Message):
    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        return await message.reply("Usage: /inspect @user")
    target = args[1].replace("@", "")
    async with db_pool.acquire() as conn:
        p = await conn.fetchrow("SELECT username, level, prestige_level, character_name, wins, losses, boss_kills, curse_rank FROM players WHERE username ILIKE $1", target)
        if not p:
            return await message.reply("❌ User not found.")
        resp = f"👤 **{e(p['username'])}**\n🎭 {e(p['character_name'])}\nLevel: {p['level']}\nPrestige: {p['prestige_level']}\nWins: {p['wins']} | Losses: {p['losses']}\nBoss Kills: {p['boss_kills']}\nCurse Rank: {e(p['curse_rank'])}"
        await message.reply(resp, parse_mode="HTML")

@dp.message(Command("season"))
@friendly_error
async def season_cmd(message: types.Message):
    user_id = message.from_user.id
    async with db_pool.acquire() as conn:
        prog = await conn.fetchval("SELECT season_progress FROM players WHERE user_id=$1", user_id) or 0
        tier = prog // 10
        await message.reply(f"📅 **Season: {CURRENT_SEASON}**\nPoints: {prog}\nCurrent Tier: {tier}\nNext Reward at: {(tier+1)*10}")

        @dp.message(Command("season_claim"))
@friendly_error
async def season_claim_cmd(message: types.Message):
    user_id = message.from_user.id
    async with db_pool.acquire() as conn:
        row = await conn.fetchrow("SELECT season_progress, claimed_tier FROM players WHERE user_id=$1", user_id)
        if not row:
            return await message.reply("❌ You have no season progress.")
        prog = row['season_progress'] or 0
        claimed = row['claimed_tier'] or 0
        current_tier = prog // 10
        if current_tier <= claimed:
            return await message.reply("❌ No new rewards to claim.")
        reward_yen = (current_tier - claimed) * 500
        await conn.execute("UPDATE players SET yen=LEAST(yen+$1,$2), claimed_tier=$3 WHERE user_id=$4",
                           reward_yen, MAX_YEN, current_tier, user_id)
        await message.reply(f"✅ Claimed {reward_yen} Yen for reaching Tier {current_tier}!")

@dp.message()
async def typo_handler(message: types.Message):
    if not message.text or not message.text.startswith('/'):
        return
    cmd = message.text.split()[0].lower().lstrip('/')
    if cmd in ALL_COMMANDS:
        return
    matches = difflib.get_close_matches(cmd, ALL_COMMANDS, n=3, cutoff=0.7)
    if matches:
        await message.reply(
            f"❓ Unknown command `/{cmd}`.\n"
            f"Did you mean: {', '.join([f'/{m}' for m in matches])}?"
        )
    else:
        await message.reply(
            f"❓ Unknown command `/{cmd}`.\n"
            f"Type /commands to see all available commands."
        )  # <--- This must be a regular closing parenthesis ')', NOT a curly brace '}'

async def main():
    await on_startup()
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
            
