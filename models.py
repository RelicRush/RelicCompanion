"""
Data models for Warframe Relic Companion
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class RelicEra(Enum):
    """The four eras of Void Relics."""
    LITH = "Lith"
    MESO = "Meso"
    NEO = "Neo"
    AXI = "Axi"


class RelicRefinement(Enum):
    """Refinement levels for relics."""
    INTACT = "Intact"
    EXCEPTIONAL = "Exceptional"
    FLAWLESS = "Flawless"
    RADIANT = "Radiant"


class RewardRarity(Enum):
    """Rarity tiers for relic rewards."""
    COMMON = "Common"
    UNCOMMON = "Uncommon"
    RARE = "Rare"


# Drop chances based on refinement level
DROP_CHANCES = {
    RelicRefinement.INTACT: {
        RewardRarity.COMMON: 25.33,
        RewardRarity.UNCOMMON: 11.00,
        RewardRarity.RARE: 2.00
    },
    RelicRefinement.EXCEPTIONAL: {
        RewardRarity.COMMON: 23.33,
        RewardRarity.UNCOMMON: 13.00,
        RewardRarity.RARE: 4.00
    },
    RelicRefinement.FLAWLESS: {
        RewardRarity.COMMON: 20.00,
        RewardRarity.UNCOMMON: 17.00,
        RewardRarity.RARE: 6.00
    },
    RelicRefinement.RADIANT: {
        RewardRarity.COMMON: 16.67,
        RewardRarity.UNCOMMON: 20.00,
        RewardRarity.RARE: 10.00
    }
}


@dataclass
class Reward:
    """Represents a single reward from a relic."""
    name: str
    rarity: RewardRarity
    ducats: int = 0
    is_forma: bool = False
    
    def __str__(self):
        return f"{self.name} ({self.rarity.value}) - {self.ducats} Ducats"


@dataclass
class Relic:
    """Represents a Void Relic."""
    era: RelicEra
    name: str
    rewards: list[Reward] = field(default_factory=list)
    vaulted: bool = False
    
    @property
    def full_name(self) -> str:
        """Returns the full relic name (e.g., 'Lith A1')."""
        return f"{self.era.value} {self.name}"
    
    def get_common_rewards(self) -> list[Reward]:
        """Returns all common rewards."""
        return [r for r in self.rewards if r.rarity == RewardRarity.COMMON]
    
    def get_uncommon_rewards(self) -> list[Reward]:
        """Returns all uncommon rewards."""
        return [r for r in self.rewards if r.rarity == RewardRarity.UNCOMMON]
    
    def get_rare_reward(self) -> Optional[Reward]:
        """Returns the rare reward if it exists."""
        rare_rewards = [r for r in self.rewards if r.rarity == RewardRarity.RARE]
        return rare_rewards[0] if rare_rewards else None
    
    def get_drop_chance(self, reward: Reward, refinement: RelicRefinement) -> float:
        """Calculate drop chance for a specific reward at a refinement level."""
        return DROP_CHANCES[refinement][reward.rarity]
    
    def __str__(self):
        status = " [VAULTED]" if self.vaulted else ""
        return f"{self.full_name}{status}"


@dataclass
class InventoryItem:
    """Represents a relic in the user's inventory."""
    relic: Relic
    refinement: RelicRefinement
    quantity: int = 1
    
    def __str__(self):
        return f"{self.relic.full_name} ({self.refinement.value}) x{self.quantity}"
