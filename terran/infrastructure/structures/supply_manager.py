from __future__ import annotations
from typing import TYPE_CHECKING, List

from sc2.ids.unit_typeid import UnitTypeId

from core.interfaces.manager_abc import Manager
from core.frame_plan import EconomicStance
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
        if cache.supply_cap >= 200:
            return []

        # Check for pending depots + depots in construction to avoid over-building.
        if (
            self.bot.already_pending(UnitTypeId.SUPPLYDEPOT)
            + self.bot.structures(UnitTypeId.SUPPLYDEPOT).not_ready.amount
            > 0
        ):
            return []

        required_buffer = 0
        if plan.economic_stance == EconomicStance.SAVING_FOR_EXPANSION:
            required_buffer = 2
        else:
            num_production_structures = cache.friendly_structures.of_type(
                TERRAN_PRODUCTION_TYPES
            ).amount
            required_buffer = (
                SUPPLY_BUFFER_BASE
                + num_production_structures * SUPPLY_BUFFER_PER_PRODUCTION_STRUCTURE
            )

        if cache.supply_left < required_buffer:
            # --- CORRECTED: Smarter and Safer Placement Logic ---
            placement_pos = self.bot.start_location  # Default fallback

            # CRITICAL CHECK: Ensure a ready townhall exists before trying to access it.
            ready_townhalls = self.bot.townhalls.ready
            if ready_townhalls.exists:
                main_th = ready_townhalls.first
                mineral_fields = self.bot.mineral_field.closer_than(10, main_th)
                if mineral_fields.exists:
                    # Calculate a point "behind" the townhall, away from the minerals.
                    placement_pos = main_th.position.towards(mineral_fields.center, -8)
            # --- END CORRECTION ---

            payload = BuildRequestPayload(
                item_id=UnitTypeId.SUPPLYDEPOT,
                position=placement_pos,
                priority=EVENT_PRIORITY_HIGH,
                unique=True,
            )
            bus.publish(Event(EventType.INFRA_BUILD_REQUEST, payload))
            cache.logger.info(
                f"Supply low. Requesting SUPPLYDEPOT near {placement_pos.rounded}"
            )

        return []
