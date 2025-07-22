from __future__ import annotations
from typing import TYPE_CHECKING, List, Dict, Set

from sc2.ids.unit_typeid import UnitTypeId

from core.interfaces.manager_abc import Manager
from core.types import CommandFunctor
from core.utilities.unit_types import TERRAN_PRODUCTION_TYPES

if TYPE_CHECKING:
    from sc2.bot_ai import BotAI
    from core.global_cache import GlobalCache
    from core.event_bus import EventBus
    from core.frame_plan import FramePlan

# Maps units that require a TechLab to the structure that builds them.
TECHLAB_REQUIREMENTS: Dict[UnitTypeId, Set[UnitTypeId]] = {
    UnitTypeId.BARRACKS: {UnitTypeId.MARAUDER, UnitTypeId.GHOST},
    UnitTypeId.FACTORY: {UnitTypeId.SIEGETANK, UnitTypeId.THOR},
    UnitTypeId.STARPORT: {
        UnitTypeId.RAVEN,
        UnitTypeId.BANSHEE,
        UnitTypeId.BATTLECRUISER,
    },
}


class AddonManager(Manager):
    """
    Add-on Specialist.

    This manager is responsible for building TechLabs and Reactors on production
    structures. It reads the production goals from the FramePlan to make an
    intelligent decision about which add-on is needed.

    NOTE: This manager is an exception to the event-based building system.
    Building an add-on is an ability of an existing structure, not a new
    construction handled by an SCV, so it issues commands directly.
    """

    def __init__(self, bot: "BotAI"):
        super().__init__(bot)

    async def execute(
        self, cache: "GlobalCache", plan: "FramePlan", bus: "EventBus"
    ) -> List[CommandFunctor]:
        """
        Identifies idle, add-on-less production buildings and builds the
        appropriate add-on based on the current production goals.
        """
        # Read production goals from the plan. If none, no decisions can be made.
        unit_goal = getattr(plan, "unit_composition_goal", {})
        if not unit_goal:
            return []

        # Find eligible buildings: ready, idle, and without an existing add-on.
        eligible_buildings = cache.friendly_structures.of_type(
            TERRAN_PRODUCTION_TYPES
        ).ready.idle.filter(lambda b: b.add_on_tag == 0)

        if not eligible_buildings:
            return []

        # Process one add-on request per frame to manage resource spending.
        building = eligible_buildings.first
        building_type = building.type_id
        needed_addon = None

        # --- Decision Logic: TechLab or Reactor? ---
        # 1. Check if a TechLab is required for any unit in our goal.
        tech_units_needed = TECHLAB_REQUIREMENTS.get(building_type, set())
        if any(unit_id in unit_goal for unit_id in tech_units_needed):
            needed_addon = UnitTypeId.TECHLAB
        # 2. If no tech is needed, default to a Reactor (if applicable).
        # Barracks and Starports can have Reactors. Factories can too.
        elif building_type in {
            UnitTypeId.BARRACKS,
            UnitTypeId.FACTORY,
            UnitTypeId.STARPORT,
        }:
            needed_addon = UnitTypeId.REACTOR

        if not needed_addon:
            return []

        # 3. Check affordability.
        if not self.bot.can_afford(needed_addon):
            return []

        # 4. Issue the direct build command.
        # The build action for add-ons is an ability of the structure itself.
        # The python-sc2 library handles placement validation internally.
        cache.logger.info(
            f"Building {needed_addon.name} on {building_type.name} at {building.position.rounded}"
        )
        return [lambda b=building, a=needed_addon: b.build(a)]

        # No action was taken this frame.
        return []
