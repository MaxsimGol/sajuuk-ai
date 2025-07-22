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


class TechStructureManager(Manager):
    """
    Tech Path Planner.

    This manager now reads a set of desired tech buildings from the FramePlan
    and attempts to request one per frame, allowing for parallel tech progression.
    """

    def __init__(self, bot: "BotAI"):
        super().__init__(bot)

    async def execute(
        self, cache: "GlobalCache", plan: "FramePlan", bus: "EventBus"
    ) -> List[CommandFunctor]:
        """
        Reads the tech goals from the FramePlan and, if valid, publishes a BuildRequest.
        Only one request is sent per frame to avoid exhausting resources.
        """
        goal_buildings = getattr(plan, "tech_goals", set())
        if not goal_buildings:
            return []

        # Iterate through the set of desired buildings
        for goal_building in goal_buildings:
            # We already checked for prerequisites and current counts in the director.
            # Here we just need to publish the request.
            # The ConstructionManager will handle affordability.

            cache.logger.info(
                f"Tech goal {goal_building.name} is valid. Publishing build request."
            )

            payload = BuildRequestPayload(
                item_id=goal_building,
                position=self.bot.start_location,
                priority=EVENT_PRIORITY_NORMAL,
                unique=True,
            )
            bus.publish(Event(EventType.INFRA_BUILD_REQUEST, payload))

            # --- IMPORTANT ---
            # Only request ONE building per frame to allow the system to react
            # and manage resources. We break after the first valid request.
            return []

        # No valid requests could be published this frame
        return []
