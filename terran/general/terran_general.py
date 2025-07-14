from __future__ import annotations
from typing import TYPE_CHECKING

# Core architectural components
from core.interfaces.race_general_abc import RaceGeneral
from core.types import CommandFunctor

# The Directors this General will orchestrate
from terran.infrastructure.infrastructure_director import InfrastructureDirector
from terran.capabilities.capability_director import CapabilityDirector
from terran.tactics.tactical_director import TacticalDirector

if TYPE_CHECKING:
    from sc2.bot_ai import BotAI
    from core.global_cache import GlobalCache
    from core.event_bus import EventBus
    from core.frame_plan import FramePlan


class TerranGeneral(RaceGeneral):
    """
    The Field Marshal for the Terran race.

    This class is the top-level orchestrator for all Terran-specific logic.
    It does not contain any tactical or economic logic itself. Instead, it
    owns instances of the three core functional Directors and is responsible
    for executing them in a strict, strategic order on each game step.
    """

    def __init__(self, bot: "BotAI"):
        """
        Initializes the General and all its subordinate Directors.

        The `bot` object is passed down to the Directors, as they need it
        to instantiate their own managers. The managers, in turn, use it
        as a "command factory" to create the command functors.
        """
        super().__init__(bot)
        self.infrastructure_director = InfrastructureDirector(bot)
        self.capability_director = CapabilityDirector(bot)
        self.tactical_director = TacticalDirector(bot)

    async def on_start(self):
        """
        Called once at the start of the game. Can be used for one-time
        setup tasks that require async operations.
        """
        # This is a hook for future use, e.g., pre-calculating optimal
        # defensive positions or wall-off locations.
        pass

    async def execute_step(
        self, cache: "GlobalCache", plan: "FramePlan", bus: "EventBus"
    ) -> list[CommandFunctor]:
        """
        Orchestrates the Directors and aggregates their requested actions.

        The order of execution is a critical strategic decision:
        1.  **Infrastructure:** First, assess our economy and set the resource
            budget for the frame. This informs all other decisions.
        2.  **Capabilities:** Second, based on the budget and our goals,
            decide what units, structures, or upgrades to build.
        3.  **Tactics:** Finally, with full knowledge of our economic state and
            production plans, decide how to control the army.

        :param cache: The read-only GlobalCache with the current world state.
        :param plan: The ephemeral "scratchpad" for the current frame's intentions.
        :param bus: The EventBus for reactive messaging.
        :return: An aggregated list of all command functors from all Directors.
        """
        actions: list[CommandFunctor] = []

        # The core orchestration sequence.
        actions.extend(await self.infrastructure_director.execute(cache, plan, bus))
        actions.extend(await self.capability_director.execute(cache, plan, bus))
        actions.extend(await self.tactical_director.execute(cache, plan, bus))

        return actions
