from __future__ import annotations
from typing import TYPE_CHECKING, List, Set

from core.interfaces.manager_abc import Manager
from core.types import CommandFunctor
from core.utilities.events import Event, EventType, UnitTookDamagePayload

if TYPE_CHECKING:
    from sc2.bot_ai import BotAI
    from sc2.unit import Unit
    from core.global_cache import GlobalCache
    from core.event_bus import EventBus
    from core.frame_plan import FramePlan


class RepairManager(Manager):
    """
    Damage Control. This manager subscribes to damage events and dispatches
    idle SCVs to repair damaged mechanical units and structures.
    """

    def __init__(self, bot: "BotAI"):
        super().__init__(bot)
        self.repair_targets: Set[int] = set()
        bus = bot.event_bus
        bus.subscribe(EventType.TACTICS_UNIT_TOOK_DAMAGE, self.handle_unit_took_damage)

    async def handle_unit_took_damage(self, event: Event):
        """
        Event handler that adds a damaged unit's tag to a set for future processing.
        """
        payload: UnitTookDamagePayload = event.payload
        self.repair_targets.add(payload.unit_tag)

    async def execute(
        self, cache: "GlobalCache", plan: "FramePlan", bus: "EventBus"
    ) -> List[CommandFunctor]:
        """
        Assigns idle SCVs to repair targets from the queue.
        """
        actions: List[CommandFunctor] = []
        if not self.repair_targets or not cache.friendly_workers.exists:
            return []

        # Identify targets already being repaired to avoid redundant commands
        repairing_workers = cache.friendly_workers.filter(lambda w: w.is_repairing)
        active_repair_targets = {
            order.target for worker in repairing_workers for order in worker.orders
        }

        # Use a copy to allow modification during iteration
        targets_to_process = self.repair_targets.copy()

        available_workers = cache.friendly_workers.idle.copy()

        for unit_tag in targets_to_process:
            if not available_workers:
                break  # No more workers to assign

            if unit_tag in active_repair_targets:
                self.repair_targets.remove(unit_tag)
                continue

            target_unit: Unit | None = cache.friendly_units.find_by_tag(unit_tag)

            # Cleanup invalid or fully repaired targets
            if (
                not target_unit
                or target_unit.health_percentage >= 1
                or not (target_unit.is_mechanical or target_unit.is_structure)
            ):
                self.repair_targets.remove(unit_tag)
                continue

            # Assign the closest available worker
            worker_to_assign = available_workers.closest_to(target_unit)
            # Wrap the command in a lambda to defer execution
            actions.append(lambda t=target_unit, w=worker_to_assign: w.repair(t))

            # Remove worker and target from pools for this frame
            available_workers.remove(worker_to_assign)
            self.repair_targets.remove(unit_tag)

        return actions
