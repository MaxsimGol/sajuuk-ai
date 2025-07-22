from __future__ import annotations
from typing import TYPE_CHECKING, List

from sc2.ids.unit_typeid import UnitTypeId

from core.interfaces.director_abc import Director
from core.interfaces.manager_abc import Manager
from core.types import CommandFunctor
from core.frame_plan import EconomicStance

# Unit Managers
from .units.scv_manager import SCVManager
from .units.mule_manager import MuleManager

# Structure Managers
from .structures.supply_manager import SupplyManager
from .structures.expansion_manager import ExpansionManager
from .structures.refinery_manager import RefineryManager
from .structures.repair_manager import RepairManager
from .structures.construction_manager import ConstructionManager

if TYPE_CHECKING:
    from sc2.bot_ai import BotAI
    from core.global_cache import GlobalCache
    from core.event_bus import EventBus
    from core.frame_plan import FramePlan


class InfrastructureDirector(Director):
    """
    The Chancellor. Manages economic strategy and resource allocation.
    Its primary role is to set the budget for the frame and orchestrate its
    subordinate managers to execute the economic plan.
    """

    def __init__(self, bot: "BotAI"):
        super().__init__(bot)
        self.workers_per_base_to_expand = 18

        self.scv_manager = SCVManager(bot)
        self.mule_manager = MuleManager(bot)
        self.supply_manager = SupplyManager(bot)
        self.expansion_manager = ExpansionManager(bot)
        # --- MODIFICATION: Pass 'self' (the director instance) to the manager ---
        self.refinery_manager = RefineryManager(bot, self)
        self.repair_manager = RepairManager(bot)
        self.construction_manager = ConstructionManager(bot)

        # The execution order of managers is strategically significant.
        self.managers: List[Manager] = [
            self.scv_manager,
            self.mule_manager,
            self.supply_manager,
            self.expansion_manager,
            self.refinery_manager,
            self.repair_manager,
            self.construction_manager,  # Construction is last to fulfill requests made this frame.
        ]

    def _set_economic_goals(self, cache: "GlobalCache", plan: "FramePlan"):
        """
        Analyzes the game state to decide the economic priority for the frame
        and sets it in the FramePlan. This is the Director's primary decision.
        """
        num_bases = self.bot.townhalls.amount
        worker_trigger_count = num_bases * self.workers_per_base_to_expand

        # Check if a Command Center is already being built or is in the construction queue.
        # We need to ask the ConstructionManager about its queue.
        is_expansion_in_queue = any(
            req.item_id == UnitTypeId.COMMANDCENTER
            for req in self.construction_manager.build_queue
        )
        is_already_expanding = (
            self.bot.already_pending(UnitTypeId.COMMANDCENTER) > 0
            or is_expansion_in_queue
        )

        # Decision: If we have enough workers and are not already expanding, our goal is to save for one.
        if (
            cache.friendly_workers.amount >= worker_trigger_count
            and not is_already_expanding
        ):
            plan.set_economic_stance(EconomicStance.SAVING_FOR_EXPANSION)
            cache.logger.info("Economic stance set to SAVING_FOR_EXPANSION.")
        else:
            plan.set_economic_stance(EconomicStance.NORMAL)

    async def execute(
        self, cache: "GlobalCache", plan: "FramePlan", bus: "EventBus"
    ) -> list[CommandFunctor]:
        """
        Executes the director's logic and orchestrates its managers.
        """
        # 1. Director's High-Level Logic
        # Sets the official resource budget for the frame.
        if len(self.bot.townhalls) < 3:
            plan.set_budget(infrastructure=70, capabilities=30)
        else:
            plan.set_budget(infrastructure=30, capabilities=70)

        # Sets the economic goal (e.g., should we be saving for an expansion?).
        self._set_economic_goals(cache, plan)

        # 2. Orchestrate Subordinate Managers
        actions: list[CommandFunctor] = []
        for manager in self.managers:
            manager_actions = await manager.execute(cache, plan, bus)
            actions.extend(manager_actions)

        return actions
