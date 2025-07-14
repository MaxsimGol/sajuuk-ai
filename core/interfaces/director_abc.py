from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from sc2.bot_ai import BotAI
    from core.global_cache import GlobalCache
    from core.event_bus import EventBus
    from core.frame_plan import FramePlan

from core.types import CommandFunctor


class Director(ABC):
    """
    Defines the abstract contract for a high-level functional Director.

    A Director is responsible for a major functional area of the bot
    (e.g., Infrastructure, Capabilities). It orchestrates several related
    Managers to achieve a strategic goal.
    """

    def __init__(self, bot: "BotAI"):
        self.bot = bot

    @abstractmethod
    async def execute(
        self, cache: "GlobalCache", plan: "FramePlan", bus: "EventBus"
    ) -> list[CommandFunctor]:
        """
        The main execution method for the Director, called by its General.

        :param cache: The read-only GlobalCache with the current world state.
        :param plan: The ephemeral "scratchpad" for the current frame's intentions.
        :param bus: The EventBus for reactive messaging.
        :return: A list of all commands requested by its subordinate managers.
        """
        pass
