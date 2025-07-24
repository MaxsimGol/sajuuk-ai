# terran/capabilities/structures/production_structure_manager.py
from __future__ import annotations
from typing import TYPE_CHECKING, List

from core.interfaces.manager_abc import Manager
from core.types import CommandFunctor
from core.utilities.events import Event, EventType, BuildRequestPayload
from core.utilities.constants import EVENT_PRIORITY_NORMAL

if TYPE_CHECKING:
    from sc2.bot_ai import BotAI
    from core.global_cache import GlobalCache
    from core.event_bus import EventBus
    from core.frame_plan import FramePlan


class ProductionStructureManager(Manager):
    """
    Constructs the key production and tech buildings required by the bot's strategy.
    This manager reads the set of desired tech buildings from the FramePlan and
    publishes a build request for the highest-priority (or first available) one.
    """

    def __init__(self, bot: "BotAI"):
        super().__init__(bot)

    async def execute(
        self, cache: "GlobalCache", plan: "FramePlan", bus: "EventBus"
    ) -> List[CommandFunctor]:
        """
        Reads tech goals from the FramePlan and requests the construction of one
        building per frame to advance the tech tree.
        """
        goal_buildings = getattr(plan, "tech_goals", set())
        if not goal_buildings:
            return []

        # Simple logic: attempt to build the first item in the set.
        # This can be expanded with a priority system if needed.
        goal_building = goal_buildings.pop()

        # The director already confirmed we need this building and have the tech for it.
        # The ConstructionManager will handle affordability and placement.
        cache.logger.info(
            f"Production goal: {goal_building.name}. Publishing build request."
        )

        payload = BuildRequestPayload(
            item_id=goal_building,
            position=self.bot.start_location,  # ConstructionManager will find specific placement
            priority=EVENT_PRIORITY_NORMAL,
            unique=True,  # Prevent spamming requests for the same building type
        )
        bus.publish(Event(EventType.INFRA_BUILD_REQUEST, payload))

        # We only request one structure per frame to manage resource spending.
        return []
