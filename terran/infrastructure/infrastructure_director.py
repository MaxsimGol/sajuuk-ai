from __future__ import annotations
from typing import TYPE_CHECKING, List

from core.interfaces.director_abc import Director
from core.interfaces.manager_abc import Manager
from core.types import CommandFunctor
from .units.scv_manager import SCVManager
from .units.mule_manager import MuleManager
from .structures.supply_manager import SupplyManager
from .structures.expansion_manager import ExpansionManager
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
        self.scv_manager = SCVManager(bot)
        self.mule_manager = MuleManager(bot)
        self.supply_manager = SupplyManager(bot)
        self.expansion_manager = ExpansionManager(bot)
        self.repair_manager = RepairManager(bot)
        self.construction_manager = ConstructionManager(bot)

        # The execution order of managers is strategically significant.
        self.managers: List[Manager] = [
            self.scv_manager,
            self.mule_manager,
            self.supply_manager,
            self.expansion_manager,
            self.repair_manager,
            self.construction_manager,  # Construction is last to fulfill requests made this frame.
        ]

    async def execute(
        self, cache: "GlobalCache", plan: "FramePlan", bus: "EventBus"
    ) -> list[CommandFunctor]:
        """
        Executes the director's logic and orchestrates its managers.
        """
        # 1. Director's Logic: Budgeting and Goal Setting
        # Sets the official resource budget for the frame in the FramePlan.
        # Simple placeholder logic: if fewer than 3 bases, focus on infrastructure.
        if len(self.bot.townhalls) < 3:
            plan.set_budget(infrastructure=70, capabilities=30)
        else:
            plan.set_budget(infrastructure=30, capabilities=70)

        # 2. Orchestrate Managers
        actions: list[CommandFunctor] = []
        for manager in self.managers:
            manager_actions = await manager.execute(cache, plan, bus)
            actions.extend(manager_actions)

        return actions
