"""
Sample relic data for the Warframe Relic Companion.
This can be expanded with data from the Warframe API or manual entry.
"""

from models import Relic, Reward, RelicEra, RewardRarity


def get_sample_relics() -> list[Relic]:
    """
    Returns a list of sample relics.
    In a full implementation, this would be loaded from an API or database.
    """
    relics = [
        # Lith Relics
        Relic(
            era=RelicEra.LITH,
            name="A1",
            rewards=[
                Reward("Akstiletto Prime Barrel", RewardRarity.COMMON, 15),
                Reward("Braton Prime Stock", RewardRarity.COMMON, 15),
                Reward("Forma Blueprint", RewardRarity.COMMON, 0, is_forma=True),
                Reward("Paris Prime Lower Limb", RewardRarity.UNCOMMON, 45),
                Reward("Fang Prime Handle", RewardRarity.UNCOMMON, 45),
                Reward("Trinity Prime Systems Blueprint", RewardRarity.RARE, 100),
            ],
            vaulted=True
        ),
        Relic(
            era=RelicEra.LITH,
            name="B1",
            rewards=[
                Reward("Burston Prime Barrel", RewardRarity.COMMON, 15),
                Reward("Bronco Prime Blueprint", RewardRarity.COMMON, 15),
                Reward("Forma Blueprint", RewardRarity.COMMON, 0, is_forma=True),
                Reward("Lex Prime Barrel", RewardRarity.UNCOMMON, 45),
                Reward("Bo Prime Ornament", RewardRarity.UNCOMMON, 45),
                Reward("Rhino Prime Chassis Blueprint", RewardRarity.RARE, 100),
            ],
            vaulted=False
        ),
        
        # Meso Relics
        Relic(
            era=RelicEra.MESO,
            name="C1",
            rewards=[
                Reward("Cernos Prime Lower Limb", RewardRarity.COMMON, 15),
                Reward("Carrier Prime Blueprint", RewardRarity.COMMON, 15),
                Reward("Forma Blueprint", RewardRarity.COMMON, 0, is_forma=True),
                Reward("Helios Prime Blueprint", RewardRarity.UNCOMMON, 45),
                Reward("Aklex Prime Link", RewardRarity.UNCOMMON, 45),
                Reward("Nekros Prime Chassis Blueprint", RewardRarity.RARE, 100),
            ],
            vaulted=False
        ),
        Relic(
            era=RelicEra.MESO,
            name="D1",
            rewards=[
                Reward("Dual Kamas Prime Blade", RewardRarity.COMMON, 15),
                Reward("Destreza Prime Blade", RewardRarity.COMMON, 15),
                Reward("Forma Blueprint", RewardRarity.COMMON, 0, is_forma=True),
                Reward("Oberon Prime Neuroptics Blueprint", RewardRarity.UNCOMMON, 45),
                Reward("Tiberon Prime Barrel", RewardRarity.UNCOMMON, 45),
                Reward("Mesa Prime Chassis Blueprint", RewardRarity.RARE, 100),
            ],
            vaulted=False
        ),
        
        # Neo Relics
        Relic(
            era=RelicEra.NEO,
            name="A1",
            rewards=[
                Reward("Akbronco Prime Link", RewardRarity.COMMON, 15),
                Reward("Aksomati Prime Barrel", RewardRarity.COMMON, 15),
                Reward("Forma Blueprint", RewardRarity.COMMON, 0, is_forma=True),
                Reward("Nikana Prime Blueprint", RewardRarity.UNCOMMON, 45),
                Reward("Saryn Prime Neuroptics Blueprint", RewardRarity.UNCOMMON, 45),
                Reward("Volt Prime Neuroptics Blueprint", RewardRarity.RARE, 100),
            ],
            vaulted=True
        ),
        Relic(
            era=RelicEra.NEO,
            name="B1",
            rewards=[
                Reward("Ballistica Prime Lower Limb", RewardRarity.COMMON, 15),
                Reward("Baza Prime Barrel", RewardRarity.COMMON, 15),
                Reward("Forma Blueprint", RewardRarity.COMMON, 0, is_forma=True),
                Reward("Braton Prime Receiver", RewardRarity.UNCOMMON, 45),
                Reward("Banshee Prime Systems Blueprint", RewardRarity.UNCOMMON, 45),
                Reward("Hydroid Prime Systems Blueprint", RewardRarity.RARE, 100),
            ],
            vaulted=False
        ),
        
        # Axi Relics
        Relic(
            era=RelicEra.AXI,
            name="A1",
            rewards=[
                Reward("Akstiletto Prime Link", RewardRarity.COMMON, 15),
                Reward("Akjagara Prime Blueprint", RewardRarity.COMMON, 15),
                Reward("Forma Blueprint", RewardRarity.COMMON, 0, is_forma=True),
                Reward("Ash Prime Systems Blueprint", RewardRarity.UNCOMMON, 45),
                Reward("Atlas Prime Neuroptics Blueprint", RewardRarity.UNCOMMON, 45),
                Reward("Chroma Prime Blueprint", RewardRarity.RARE, 100),
            ],
            vaulted=True
        ),
        Relic(
            era=RelicEra.AXI,
            name="B1",
            rewards=[
                Reward("Baza Prime Stock", RewardRarity.COMMON, 15),
                Reward("Ballistica Prime Blueprint", RewardRarity.COMMON, 15),
                Reward("Forma Blueprint", RewardRarity.COMMON, 0, is_forma=True),
                Reward("Baruuk Prime Neuroptics Blueprint", RewardRarity.UNCOMMON, 45),
                Reward("Boltor Prime Stock", RewardRarity.UNCOMMON, 45),
                Reward("Ivara Prime Blueprint", RewardRarity.RARE, 100),
            ],
            vaulted=False
        ),
    ]
    
    return relics


# Farming locations for different relic eras
RELIC_FARMING_LOCATIONS = {
    RelicEra.LITH: [
        {"mission": "Hepit", "location": "Void", "type": "Capture", "rotation": "A"},
        {"mission": "Olympus", "location": "Mars", "type": "Disruption", "rotation": "A"},
        {"mission": "Ukko", "location": "Void", "type": "Capture", "rotation": "A"},
    ],
    RelicEra.MESO: [
        {"mission": "Ukko", "location": "Void", "type": "Capture", "rotation": "A"},
        {"mission": "Io", "location": "Jupiter", "type": "Defense", "rotation": "A"},
        {"mission": "Paimon", "location": "Europa", "type": "Defense", "rotation": "A"},
    ],
    RelicEra.NEO: [
        {"mission": "Ukko", "location": "Void", "type": "Capture", "rotation": "A/B"},
        {"mission": "Xini", "location": "Eris", "type": "Interception", "rotation": "A/B"},
        {"mission": "Hydron", "location": "Sedna", "type": "Defense", "rotation": "B"},
    ],
    RelicEra.AXI: [
        {"mission": "Xini", "location": "Eris", "type": "Interception", "rotation": "B/C"},
        {"mission": "Apollo", "location": "Lua", "type": "Disruption", "rotation": "B/C"},
        {"mission": "Hieracon", "location": "Pluto", "type": "Excavation", "rotation": "B/C"},
    ],
}
