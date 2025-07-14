from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from sc2.bot_ai import BotAI
    from core.global_cache import GlobalCache
    from core.event_bus import EventBus
    from core.frame_plan import FramePlan

from core.types import CommandFunctor


class RaceGeneral(ABC):
    """
    Defines the abstract contract for a race-specific General.

    This is the primary interface the main Sajuuk Conductor interacts with.
    It orchestrates all Directors for a given race.
    """

    def __init__(self, bot: "BotAI"):
        self.bot = bot

    @abstractmethod
    async def on_start(self):
        """
        Called once at the start of the game.
        Responsible for initializing all race-specific Directors.
        """
        pass

    @abstractmethod
    async def execute_step(
        self, cache: "GlobalCache", plan: "FramePlan", bus: "EventBus"
    ) -> list[CommandFunctor]:
        """
        The main logic loop for the General, called every game step.

        It orchestrates its Directors, aggregates their requested actions,
        and returns the final list of commands for the frame.

        :param cache: The read-only GlobalCache with the current frame's state.
        :param bus: The EventBus for reactive messaging.
        :return: A list of UnitCommand objects to be executed by the Conductor.
        """
        pass
