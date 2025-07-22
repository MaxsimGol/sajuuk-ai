# terran/infrastructure/units/scv_manager.py
from __future__ import annotations
from typing import TYPE_CHECKING, List

from sc2.ids.unit_typeid import UnitTypeId
from sc2.data import race_townhalls

from core.interfaces.manager_abc import Manager
from core.types import CommandFunctor
from core.utilities.constants import MAX_WORKER_COUNT, SCVS_PER_GEYSER

if TYPE_CHECKING:
    from sc2.bot_ai import BotAI
    from sc2.units import Units
    from core.global_cache import GlobalCache
    from core.event_bus import EventBus
    from core.frame_plan import FramePlan


class SCVManager(Manager):
    """
    Manages SCV production and worker assignment to both mineral lines and gas geysers.
    """

    def __init__(self, bot: "BotAI"):
        super().__init__(bot)

    async def execute(
        self, cache: "GlobalCache", plan: "FramePlan", bus: "EventBus"
    ) -> List[CommandFunctor]:
        """
        Handles SCV training and assigns idle workers to gas and mineral lines.
        """
        actions: List[CommandFunctor] = []
        terran_townhalls = race_townhalls[self.bot.race]

        # --- 1. SCV Production ---
        worker_target = MAX_WORKER_COUNT
        current_worker_count = cache.friendly_workers.amount
        pending_worker_count = self.bot.already_pending(UnitTypeId.SCV)

        if (
            current_worker_count + pending_worker_count < worker_target
            and self.bot.can_afford(UnitTypeId.SCV)
        ):
            # Check for townhalls that are ready and have queue space
            producible_townhalls: Units = cache.friendly_structures.of_type(
                terran_townhalls
            ).ready.filter(lambda th: len(th.orders) < 1)

            if producible_townhalls.exists:
                th = producible_townhalls.first
                cache.logger.debug(
                    f"Training SCV from {th.type_id} at {th.position.rounded}"
                )
                actions.append(lambda: th.train(UnitTypeId.SCV))

        # --- 2. Worker Assignment ---
        idle_workers = cache.friendly_workers.idle
        if not idle_workers:
            return actions

        # --- 2a. Gas Saturation (Priority) ---
        ready_refineries = cache.friendly_structures.of_type(UnitTypeId.REFINERY).ready
        unsaturated_refineries = ready_refineries.filter(
            lambda r: r.assigned_harvesters < SCVS_PER_GEYSER
        )

        for refinery in unsaturated_refineries:
            # Re-check for idle workers inside the loop
            if not idle_workers:
                break
            # Assign workers until this refinery is saturated
            while refinery.assigned_harvesters < SCVS_PER_GEYSER:
                if not idle_workers:
                    break
                worker = idle_workers.closest_to(refinery)
                actions.append(lambda w=worker, r=refinery: w.gather(r))
                # Remove the worker from the pool to prevent re-assignment
                idle_workers.remove(worker)
                # This is a temporary client-side update to avoid re-assigning
                # multiple workers to the same slot in the same frame.
                refinery.assigned_harvesters += 1

        # --- 2b. Mineral Saturation (Remaining Workers) ---
        if not idle_workers:
            return actions

        all_townhalls = cache.friendly_structures.of_type(terran_townhalls).ready
        if not all_townhalls.exists:
            return actions

        unsaturated_townhalls = all_townhalls.filter(
            lambda th: th.surplus_harvesters < 0
        )

        for worker in idle_workers:
            # If some bases are undersaturated, send there first.
            if unsaturated_townhalls.exists:
                target_th = unsaturated_townhalls.closest_to(worker)
            # Otherwise, just send to the nearest base.
            else:
                target_th = all_townhalls.closest_to(worker)

            local_minerals = self.bot.mineral_field.closer_than(10, target_th)
            if local_minerals.exists:
                # Find the mineral patch with the fewest workers assigned.
                target_mineral = local_minerals.sorted(
                    key=lambda mf: mf.assigned_harvesters
                ).first
                actions.append(lambda w=worker, m=target_mineral: w.gather(m))

        return actions
