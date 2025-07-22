# terran/capabilities/structures/addon_manager.py
from __future__ import annotations
from typing import TYPE_CHECKING, List, Dict

from sc2.ids.unit_typeid import UnitTypeId

from core.interfaces.manager_abc import Manager
from core.types import CommandFunctor
from core.utilities.unit_types import TERRAN_PRODUCTION_TYPES

if TYPE_CHECKING:
    from sc2.bot_ai import BotAI
    from core.global_cache import GlobalCache
    from core.event_bus import EventBus
    from core.frame_plan import FramePlan

# Maps addon types to the base structure they are built from.
ADDON_TO_STRUCTURE_MAP: Dict[UnitTypeId, UnitTypeId] = {
    UnitTypeId.BARRACKSTECHLAB: UnitTypeId.BARRACKS,
    UnitTypeId.BARRACKSREACTOR: UnitTypeId.BARRACKS,
    UnitTypeId.FACTORYTECHLAB: UnitTypeId.FACTORY,
    UnitTypeId.FACTORYREACTOR: UnitTypeId.FACTORY,
    UnitTypeId.STARPORTTECHLAB: UnitTypeId.STARPORT,
    UnitTypeId.STARPORTREACTOR: UnitTypeId.STARPORT,
}
# Maps addon types to the final building type id (for counting)
ADDON_BUILDING_MAP: Dict[UnitTypeId, UnitTypeId] = {
    UnitTypeId.TECHLAB: {
        UnitTypeId.BARRACKSTECHLAB,
        UnitTypeId.FACTORYTECHLAB,
        UnitTypeId.STARPORTTECHLAB,
    },
    UnitTypeId.REACTOR: {
        UnitTypeId.BARRACKSREACTOR,
        UnitTypeId.FACTORYREACTOR,
        UnitTypeId.STARPORTREACTOR,
    },
}


class AddonManager(Manager):
    """
    Add-on Specialist.

    This manager executes the add-on construction goals set by the
    CapabilityDirector in the FramePlan. It finds eligible buildings and issues
    direct build commands for the required add-ons.
    """

    def __init__(self, bot: "BotAI"):
        super().__init__(bot)

    async def execute(
        self, cache: "GlobalCache", plan: "FramePlan", bus: "EventBus"
    ) -> List[CommandFunctor]:
        """
        Reads the add-on goals from the FramePlan and attempts to build one if a deficit is found.
        """
        addon_goals = getattr(plan, "addon_goal", {})
        if not addon_goals:
            return []

        # Iterate through the desired add-ons (e.g., BARRACKSTECHLAB, BARRACKSREACTOR)
        for addon_id, target_count in addon_goals.items():

            # Count how many of this specific add-on we have or are building
            current_count = cache.friendly_structures.of_type(addon_id).amount
            if self.bot.already_pending(addon_id):
                current_count += 1

            # If we have met the target, move to the next goal
            if current_count >= target_count:
                continue

            # We have a deficit, try to build one
            base_structure_type = ADDON_TO_STRUCTURE_MAP.get(addon_id)
            if not base_structure_type:
                continue

            # Find a ready, idle, "naked" building of the correct type
            eligible_buildings = cache.friendly_structures.of_type(
                base_structure_type
            ).ready.idle.filter(lambda b: b.add_on_tag == 0)

            if not eligible_buildings.exists:
                continue  # No available building to create this add-on right now

            building_to_use = eligible_buildings.first
            addon_to_build = (
                UnitTypeId.TECHLAB if "TECHLAB" in addon_id.name else UnitTypeId.REACTOR
            )

            if self.bot.can_afford(addon_to_build):
                cache.logger.info(
                    f"Add-on deficit detected for {addon_id.name}. Building on {base_structure_type.name}."
                )
                # Issue the command and return immediately to build only one per frame.
                return [lambda b=building_to_use, a=addon_to_build: b.build(a)]

        return []
