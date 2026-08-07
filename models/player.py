from dataclasses import dataclass
from typing import Optional, List, Dict, Any

@dataclass
class Player:
    user_id: int
    username: str
    chat_id: int
    character_name: Optional[str]
    level: int
    xp: int
    yen: int
    hp: int
    max_hp: int
    ce: int
    max_ce: int
    atk: int
    def_: int
    spd: int
    wins: int
    losses: int
    boss_kills: int
    black_flash_count: int
    awakening: Optional[str]
    awakening_level: int
    awakening_aura: bool
    equipped_weapon: Optional[str]
    equipped_title: Optional[str]
    clan_id: Optional[int]
    clan_rank: str
    reputation: Dict[str, Any]
    prestige_level: int
    prestige_bonus_atk: int
    prestige_bonus_hp: int
    arena_rank: int
    restriction: Optional[str]
    curse_rank: str
    curse_evolution_count: int
    curse_regen: bool
    in_battle: bool
    last_ce_regen: Optional[str]
    techniques: List[str]
    domains: List[str]
    bag: List[str]
    created_at: Optional[str]

    @classmethod
    def from_row(cls, row):
        return cls(**dict(row))
