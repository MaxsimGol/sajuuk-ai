from __future__ import annotations
from typing import TYPE_CHECKING, List

from sc2.ids.unit_typeid import UnitTypeId

from core.frame_plan import EconomicStance
from core.interfaces.manager_abc import Manager
from core.types import CommandFunctor
from core.utilities.events import Event, EventType, BuildRequestPayload
from core.utilities.constants import EVENT_PRIORITY_NORMAL

if TYPE_CHECKING:
    from sc2.bot_ai import BotAI
    from core.global_cache import GlobalCache
    from core.event_bus import EventBus
    from core.frame_plan import FramePlan


class ExpansionManager(Manager):
    """
    Manages the bot's strategic expansion timing and location.
    It determines WHEN to expand based on the Director's plan and publishes a
    request for the ConstructionManager to handle.
    """

    def __init__(self, bot: "BotAI"):
        super().__init__(bot)

    async def execute(
        self, cache: "GlobalCache", plan: "FramePlan", bus: "EventBus"
    ) -> List[CommandFunctor]:
        """
        If the director has ordered an expansion, find a location and request it.
        """
        # This manager's only trigger is the Director's economic stance.
        if plan.economic_stance != EconomicStance.SAVING_FOR_EXPANSION:
            return []

        # The director has already determined we are not currently expanding.
        # This manager's job is now simply to find the location and publish the request.
        # The ConstructionManager will handle affordability.

        next_expansion_location = await self.bot.get_next_expansion()

        if next_expansion_location:
            cache.logger.info(
                f"Economic goal is to expand. Requesting COMMANDCENTER at {next_expansion_location.rounded}"
            )
            # Publish a request to build a Command Center.
            # We use 'unique=True' to prevent spamming the build queue on subsequent frames
            # while we are saving up minerals. The ConstructionManager will handle this.
            payload = BuildRequestPayload(
                item_id=UnitTypeId.COMMANDCENTER,
                position=next_expansion_location,
                priority=EVENT_PRIORITY_NORMAL,
                unique=True,
            )
            bus.publish(Event(EventType.INFRA_BUILD_REQUEST, payload))

        # This manager only publishes events, it does not issue direct commands.
        return []
