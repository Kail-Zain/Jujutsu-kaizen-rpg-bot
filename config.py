import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
DATABASE_URL = os.getenv("DATABASE_URL")
if not BOT_TOKEN or not DATABASE_URL:
    raise ValueError("Missing BOT_TOKEN or DATABASE_URL")

OWNER_ID = int(os.getenv("OWNER_ID", 8609946980))
OWNER_NAME = os.getenv("OWNER_NAME", "𝕄𝕒𝕩𝕨𝕖𝕝𝕝-𝟜𝟟")
MAX_YEN = 999999999
YEN_PURCHASE_INFO = f"💰 **Buy Yen** — Contact {OWNER_NAME} directly."

# Static media URLs (same as original)
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
