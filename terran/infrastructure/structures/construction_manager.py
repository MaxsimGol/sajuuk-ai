from __future__ import annotations
from typing import TYPE_CHECKING, List

from sc2.ids.unit_typeid import UnitTypeId

from core.interfaces.manager_abc import Manager
from core.types import CommandFunctor
from core.utilities.events import Event, EventType, BuildRequestPayload
from core.utilities.unit_types import WORKER_TYPES

if TYPE_CHECKING:
    from sc2.bot_ai import BotAI
    from core.global_cache import GlobalCache
    from core.event_bus import EventBus
    from core.frame_plan import FramePlan


class ConstructionManager(Manager):
    """
    The Civil Engineering Service. This manager is a service that fulfills
    build requests published to the EventBus. It maintains a prioritized queue
    and handles the low-level logic of finding a placement and assigning a worker.
    """

    def __init__(self, bot: "BotAI"):
        super().__init__(bot)
        self.build_queue: List[BuildRequestPayload] = []
        # Subscribe to build requests from the event bus
        bot.event_bus.subscribe(
            EventType.INFRA_BUILD_REQUEST, self.handle_build_request
        )

    async def handle_build_request(self, event: Event):
        """Event handler that adds a new build request to the queue."""
        payload: BuildRequestPayload = event.payload
        if payload.unique:
            is_duplicate = any(
                req.item_id == payload.item_id for req in self.build_queue
            )
            if is_duplicate:
                self.bot.global_cache.logger.debug(
                    f"Ignoring duplicate build request for unique item: {payload.item_id.name}"
                )
                return
        self.build_queue.append(payload)

    async def execute(
        self, cache: "GlobalCache", plan: "FramePlan", bus: "EventBus"
    ) -> List[CommandFunctor]:
        """
        Processes the build queue, attempting to construct the highest-priority
        affordable building each frame.
        """
        if not self.build_queue:
            return []

        # Sort queue by priority (lower number is higher priority)
        self.build_queue.sort(key=lambda req: req.priority)

        # Attempt to process the highest priority request
        request = self.build_queue[0]

        if not self.bot.can_afford(request.item_id):
            return []  # Can't afford the top priority, wait for more resources

        gas_buildings = {
            UnitTypeId.REFINERY,
            UnitTypeId.EXTRACTOR,
            UnitTypeId.ASSIMILATOR,
        }

        # --- Special logic for Gas Buildings ---
        if request.item_id in gas_buildings:
            # Find an unoccupied geyser near the requested position or any townhall.
            search_point = request.position or self.bot.start_location
            geysers = self.bot.vespene_geyser.filter(
                lambda g: not self.bot.structures.closer_than(1.0, g).exists()
            )
            if geysers.exists:
                geyser = geysers.closest_to(search_point)
                worker = self.bot.select_build_worker(geyser.position)
                if worker:
                    self.build_queue.pop(0)  # Remove fulfilled request
                    # Wrap the command in a lambda to defer execution
                    return [lambda: worker.build_gas(geyser)]
            return []  # No available geyser or worker, retry next frame

        # --- Standard logic for all other buildings ---
        search_origin = request.position or self.bot.start_location
        placement_position = await self.bot.find_placement(
            request.item_id, near=search_origin
        )

        if not placement_position:
            # Can't find placement, maybe the area is blocked. Retry next frame.
            return []

        worker = self.bot.select_build_worker(placement_position)
        if not worker:
            # No worker available, retry next frame.
            return []

        # We have a valid placement, a worker, and can afford it.
        self.build_queue.pop(0)  # Remove fulfilled request
        # Wrap the command in a lambda to defer execution
        return [lambda: worker.build(request.item_id, placement_position)]
