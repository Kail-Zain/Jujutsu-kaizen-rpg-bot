from dataclasses import dataclass
from typing import Optional

@dataclass
class Enemy:
    id: int
    name: str
    rank: str
    base_hp: int
    base_atk: int
    base_def: int
    base_spd: int
    reward_yen: int
    reward_xp: int
    is_boss: bool
    image_url: Optional[str]
    # scaled fields (not in DB)
    hp: Optional[int] = None
    atk: Optional[int] = None
    def_: Optional[int] = None
    spd: Optional[int] = None
    max_hp: Optional[int] = None
