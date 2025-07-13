# core/utilities/unit_value.py

from typing import TYPE_CHECKING
from sc2.ids.unit_typeid import UnitTypeId

# This block was missing. It provides the definitions for type hints.
if TYPE_CHECKING:
    from sc2.game_data import GameData
    from sc2.units import Units

# --- Heuristic Threat Assessment ---
# This dictionary provides a non-resource-based "threat" score for units.
# These are opinionated values based on a unit's potential to do damage,
# its area-of-effect capabilities, and its strategic importance.
# These values are designed to be tuned over time.
# A higher score indicates a higher priority target.
THREAT_SCORE_MAP = {
    # --- Terran ---
    UnitTypeId.SIEGETANKSIEGED: 100,
    UnitTypeId.BATTLECRUISER: 95,
    UnitTypeId.LIBERATORAG: 90,
    UnitTypeId.BANSHEE: 80,
    UnitTypeId.SIEGETANK: 70,
    UnitTypeId.THOR: 65,
    UnitTypeId.MARAUDER: 30,
    UnitTypeId.MARINE: 20,
    UnitTypeId.REAPER: 15,
    UnitTypeId.SCV: 1,
    # --- Zerg ---
    UnitTypeId.LURKERMPBURROWED: 100,
    UnitTypeId.BANELING: 90,  # High threat against bio
    UnitTypeId.INFESTOR: 90,
    UnitTypeId.ULTRALISK: 85,
    UnitTypeId.BROODLORD: 80,
    UnitTypeId.HYDRALISK: 40,
    UnitTypeId.ROACH: 30,
    UnitTypeId.ZERGLING: 10,
    UnitTypeId.DRONE: 1,
    # --- Protoss ---
    UnitTypeId.DISRUPTOR: 100,
    UnitTypeId.HIGHTEMPLAR: 95,
    UnitTypeId.COLOSSUS: 85,
    UnitTypeId.ARCHON: 80,
    UnitTypeId.IMMORTAL: 70,
    UnitTypeId.STALKER: 30,
    UnitTypeId.ADEPT: 25,
    UnitTypeId.ZEALOT: 20,
    UnitTypeId.PROBE: 1,
}
# Default threat for units not in the map (e.g., workers, support units)
DEFAULT_THREAT_SCORE = 5


def calculate_threat_value(unit_type_id: UnitTypeId) -> float:
    """
    Calculates the tactical threat of a single unit based on a heuristic map.

    This value is used to prioritize targets in combat. It is not based
    on resource cost, but on the unit's potential impact on a battle.

    :param unit_type_id: The UnitTypeId of the unit to assess.
    :return: A float representing the unit's threat score.
    """
    return THREAT_SCORE_MAP.get(unit_type_id, DEFAULT_THREAT_SCORE)


def calculate_resource_value(unit_type_id: UnitTypeId, game_data: "GameData") -> int:
    """
    Calculates the combined mineral and vespene cost of a unit.

    :param unit_type_id: The UnitTypeId of the unit.
    :param game_data: The GameData object from the BotAI.
    :return: The total resource cost (minerals + vespene).
    """
    unit_data = game_data.units[unit_type_id.value]
    cost = unit_data.cost
    return cost.minerals + cost.vespene


def calculate_army_value(units: "Units", game_data: "GameData") -> int:
    """
    Calculates the total resource value of a collection of units.

    This is a simple way to estimate the size of an army.

    :param units: A `Units` object (a list-like collection of units).
    :param game_data: The GameData object from the BotAI.
    :return: The sum of the resource values of all units in the collection.
    """
    total_value = 0
    if not units:
        return total_value

    for unit in units:
        total_value += calculate_resource_value(unit.type_id, game_data)
    return total_value
