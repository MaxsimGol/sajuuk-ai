# terran/builds/two_rax_reaper.py

from sc2.ids.unit_typeid import UnitTypeId
from sc2.ids.upgrade_id import UpgradeId


class TwoRaxReaper:
    """
    Stores the step-by-step build order for a standard 2-Rax Reaper expand,
    including the critical Reaper speed upgrade.
    """

    # The build order is a list of tuples: (supply, item_to_build)
    # The ProductionManager will iterate through this list.
    BUILD_ORDER = [
        # Standard opening
        (14, UnitTypeId.SUPPLYDEPOT),
        (16, UnitTypeId.BARRACKS),
        (16, UnitTypeId.REFINERY),
        (19, UnitTypeId.REAPER),  # First Reaper
        (20, UnitTypeId.ORBITALCOMMAND),
        (20, UnitTypeId.SUPPLYDEPOT),
        # Add Tech Lab to first Barracks and research Reaper speed
        # This assumes the manager can handle building addons.
        (20, UnitTypeId.BARRACKSTECHLAB),
        (20, UpgradeId.REAPERSPEED),
        # Second Barracks
        (21, UnitTypeId.BARRACKS),
        # Start Reaper production from both Barracks
        (23, UnitTypeId.REAPER),
        (25, UnitTypeId.REAPER),
        (27, UnitTypeId.REAPER),
        (29, UnitTypeId.REAPER),
        # Expand and transition
        (30, UnitTypeId.COMMANDCENTER),
        (30, UnitTypeId.SUPPLYDEPOT),
        (32, UnitTypeId.FACTORY),
        (34, UnitTypeId.REFINERY),
    ]
