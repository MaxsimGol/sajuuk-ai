"""
A central repository for static collections of UnitTypeIds.

This provides a single, authoritative source for filtering units by their
role or other shared characteristics, ensuring consistency and making the
code easier to read and maintain.
"""

from sc2.ids.unit_typeid import UnitTypeId

TERRAN_PRODUCTION_TYPES = {
    UnitTypeId.BARRACKS,
    UnitTypeId.FACTORY,
    UnitTypeId.STARPORT,
}
# A set of all worker types across all races.
WORKER_TYPES = {UnitTypeId.SCV, UnitTypeId.PROBE, UnitTypeId.DRONE}

# A set of all supply provider types across all races.
SUPPLY_PROVIDER_TYPES = {UnitTypeId.SUPPLYDEPOT, UnitTypeId.OVERLORD, UnitTypeId.PYLON}

# --- Terran Specific Types ---
STRUCTURE_TYPES_TERRAN = {
    UnitTypeId.BARRACKS,
    UnitTypeId.BARRACKSFLYING,
    UnitTypeId.BARRACKSREACTOR,
    UnitTypeId.BARRACKSTECHLAB,
    UnitTypeId.COMMANDCENTER,
    UnitTypeId.COMMANDCENTERFLYING,
    UnitTypeId.ORBITALCOMMAND,
    UnitTypeId.ORBITALCOMMANDFLYING,
    UnitTypeId.PLANETARYFORTRESS,
    UnitTypeId.ENGINEERINGBAY,
    UnitTypeId.FACTORY,
    UnitTypeId.FACTORYFLYING,
    UnitTypeId.FACTORYREACTOR,
    UnitTypeId.FACTORYTECHLAB,
    UnitTypeId.STARPORT,
    UnitTypeId.STARPORTFLYING,
    UnitTypeId.STARPORTREACTOR,
    UnitTypeId.STARPORTTECHLAB,
    UnitTypeId.FUSIONCORE,
    UnitTypeId.GHOSTACADEMY,
    UnitTypeId.ARMORY,
    UnitTypeId.SUPPLYDEPOT,
    UnitTypeId.SUPPLYDEPOTLOWERED,
    UnitTypeId.BUNKER,
    UnitTypeId.MISSILETURRET,
    UnitTypeId.SENSORTOWER,
    UnitTypeId.AUTOTURRET,
    UnitTypeId.REFINERY,
}

# --- Zerg Specific Types (Placeholder) ---
STRUCTURE_TYPES_ZERG = set()

# --- Protoss Specific Types (Placeholder) ---
STRUCTURE_TYPES_PROTOSS = set()

# A combined set of all structure types for easy filtering.
ALL_STRUCTURE_TYPES = (
    STRUCTURE_TYPES_TERRAN | STRUCTURE_TYPES_ZERG | STRUCTURE_TYPES_PROTOSS
)
