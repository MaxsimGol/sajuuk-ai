from __future__ import annotations
from typing import TYPE_CHECKING, List

from sc2.ids.unit_typeid import UnitTypeId

from core.interfaces.manager_abc import Manager
from core.types import CommandFunctor
from core.utilities.events import Event, EventType, BuildRequestPayload
from core.utilities.constants import (
    SUPPLY_BUFFER_BASE,
    SUPPLY_BUFFER_PER_PRODUCTION_STRUCTURE,
    EVENT_PRIORITY_HIGH,
)
from core.utilities.unit_types import TERRAN_PRODUCTION_TYPES

if TYPE_CHECKING:
    from sc2.bot_ai import BotAI
    from core.global_cache import GlobalCache
    from core.event_bus import EventBus
    from core.frame_plan import FramePlan


class SupplyManager(Manager):
    """
    Manages the bot's supply to prevent it from getting supply blocked.
    It does not issue direct build commands but instead publishes a high-priority
    build request to the EventBus.
    """

    def __init__(self, bot: "BotAI"):
        super().__init__(bot)

    async def execute(
        self, cache: "GlobalCache", plan: "FramePlan", bus: "EventBus"
    ) -> List[CommandFunctor]:
        """
        Checks supply and requests a new Supply Depot if needed.
        """
        # Don't request depots if we are at max supply
        if cache.supply_cap >= 200:
            return []

        # Check if a Supply Depot is already in production or queued by a worker
        if self.bot.already_pending(UnitTypeId.SUPPLYDEPOT) > 0:
            return []

        # Calculate the required supply buffer
        num_production_structures = cache.friendly_structures.of_type(
            TERRAN_PRODUCTION_TYPES
        ).amount
        required_buffer = (
            SUPPLY_BUFFER_BASE
            + num_production_structures * SUPPLY_BUFFER_PER_PRODUCTION_STRUCTURE
        )

        # If supply is low, publish a high-priority build request
        if cache.supply_left < required_buffer:
            payload = BuildRequestPayload(
                item_id=UnitTypeId.SUPPLYDEPOT, priority=EVENT_PRIORITY_HIGH
            )
            bus.publish(Event(EventType.INFRA_BUILD_REQUEST, payload))

        # This manager only publishes events, it does not issue commands
        return []
