from __future__ import annotations
from typing import TYPE_CHECKING, List

from sc2.ids.unit_typeid import UnitTypeId

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
    It determines when to expand and publishes a request to the EventBus
    for the ConstructionManager to handle.
    """

    def __init__(self, bot: "BotAI"):
        super().__init__(bot)
        # A simple heuristic: trigger an expansion when we have this many
        # workers for each base we currently own.
        self.workers_per_base_to_expand = 18

    async def execute(
        self, cache: "GlobalCache", plan: "FramePlan", bus: "EventBus"
    ) -> List[CommandFunctor]:
        """
        Determines if and where to expand based on worker count, supply, and affordability.
        """
        # Condition 1: Are we already building a townhall? If so, wait.
        if self.bot.already_pending(UnitTypeId.COMMANDCENTER) > 0:
            return []

        # Condition 2: Are we about to be supply blocked? If so, wait for a depot.
        # This prevents spending 400 minerals on an expansion when a 100 mineral depot is critical.
        if cache.supply_left < 4 and cache.supply_cap < 200:
            return []

        # Condition 3: Is our economy ready for an expansion?
        # Trigger expansion based on the number of workers per base.
        num_bases = self.bot.townhalls.amount
        worker_trigger_count = num_bases * self.workers_per_base_to_expand
        if cache.friendly_workers.amount < worker_trigger_count:
            return []

        # Condition 4: Can we afford it right now?
        if not self.bot.can_afford(UnitTypeId.COMMANDCENTER):
            return []

        # All conditions met, let's expand.
        next_expansion_location = await self.bot.get_next_expansion()

        if next_expansion_location:
            # Publish a request to build a Command Center at the found location.
            payload = BuildRequestPayload(
                item_id=UnitTypeId.COMMANDCENTER,
                position=next_expansion_location,
                priority=EVENT_PRIORITY_NORMAL,
            )
            bus.publish(Event(EventType.INFRA_BUILD_REQUEST, payload))

        # This manager only publishes events, it does not issue commands.
        return []
