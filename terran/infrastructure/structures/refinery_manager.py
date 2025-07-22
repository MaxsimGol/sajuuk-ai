from __future__ import annotations
from typing import TYPE_CHECKING, List

from sc2.ids.unit_typeid import UnitTypeId
from sc2.data import race_townhalls

from core.interfaces.manager_abc import Manager
from core.types import CommandFunctor
from core.utilities.events import Event, EventType, BuildRequestPayload
from core.utilities.constants import EVENT_PRIORITY_NORMAL

if TYPE_CHECKING:
    from sc2.bot_ai import BotAI
    from core.global_cache import GlobalCache
    from core.event_bus import EventBus
    from core.frame_plan import FramePlan
    from terran.infrastructure.infrastructure_director import InfrastructureDirector


class RefineryManager(Manager):
    """
    Manages the construction of Refineries to secure a vespene gas income.
    It decides WHEN to build a refinery and publishes a request.
    """

    # --- MODIFICATION 1: Update __init__ to accept the director ---
    def __init__(self, bot: "BotAI", director: "InfrastructureDirector"):
        super().__init__(bot)
        self.director = director  # Store the reference

    async def execute(
        self, cache: "GlobalCache", plan: "FramePlan", bus: "EventBus"
    ) -> List[CommandFunctor]:
        """
        Determines if a new refinery is needed and publishes a build request.
        """
        # --- Target Calculation ---
        # A simple heuristic: aim for two refineries for every completed base.
        terran_townhalls = race_townhalls[self.bot.race]
        ready_bases = cache.friendly_structures.of_type(terran_townhalls).ready
        target_refinery_count = ready_bases.amount * 2

        # --- Current State Assessment ---
        current_refinery_count = cache.friendly_structures.of_type(
            UnitTypeId.REFINERY
        ).amount + self.bot.already_pending(UnitTypeId.REFINERY)

        if current_refinery_count >= target_refinery_count:
            return []

        # --- Find a Suitable Geyser ---
        # We need to find a geyser near one of our bases that doesn't already have a refinery on it.
        for th in ready_bases:
            geysers = self.bot.vespene_geyser.closer_than(10.0, th)
            for geyser in geysers:
                # Check if there is already a refinery (or assimilated/extractor) on this geyser
                if not self.bot.gas_buildings.closer_than(1.0, geyser).exists:
                    # Found a valid, unoccupied geyser.

                    # --- MODIFICATION 2: Use the direct director reference ---
                    # Get the construction manager via the director reference
                    construction_manager = self.director.construction_manager

                    is_gas_in_queue = any(
                        req.item_id == UnitTypeId.REFINERY
                        for req in construction_manager.build_queue
                    )

                    if not is_gas_in_queue:
                        # Publish the build request. The ConstructionManager will handle
                        # affordability and worker assignment.
                        cache.logger.info(
                            f"Requesting REFINERY at {geyser.position.rounded}"
                        )
                        payload = BuildRequestPayload(
                            item_id=UnitTypeId.REFINERY,
                            position=geyser,  # Pass the geyser unit directly
                            priority=EVENT_PRIORITY_NORMAL,
                            unique=False,  # Allow multiple refineries
                        )
                        bus.publish(Event(EventType.INFRA_BUILD_REQUEST, payload))

                    # Request only one refinery per frame to avoid spending all minerals at once.
                    return []

        return []
