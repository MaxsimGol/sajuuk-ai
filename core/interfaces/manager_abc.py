from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from sc2.bot_ai import BotAI
    from sc2.unit_command import UnitCommand
    from core.global_cache import GlobalCache
    from core.event_bus import EventBus


class Manager(ABC):
    """
    Defines the abstract contract for any specialized, stateful Manager.

    A Manager is responsible for a single, narrow domain of logic
    (e.g., producing SCVs, managing supply). It is orchestrated by a
    higher-level Director.
    """

    def __init__(self, bot: BotAI):
        self.bot = bot

    @abstractmethod
    async def execute(self, cache: GlobalCache, bus: EventBus) -> list[UnitCommand]:
        """
        The main execution method for the manager, called by its Director.

        :param cache: The read-only GlobalCache with the current frame's state.
        :param bus: The EventBus for reactive messaging.
        :return: A list of UnitCommand objects to be executed.
        """
        pass
