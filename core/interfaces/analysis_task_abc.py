from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from sc2.bot_ai import BotAI
    from core.event_bus import EventBus
    from core.game_analysis import GameAnalyzer


class AnalysisTask(ABC):
    """
    Abstract base class for a single, focused analysis task.

    Each task encapsulates a specific piece of game state analysis,
    like calculating army value or generating a threat map.
    """

    def __init__(self, event_bus: "EventBus" | None = None):
        """
        Initializes the task.
        An optional EventBus can be passed for tasks that need to react to events.
        """
        if event_bus:
            self.subscribe_to_events(event_bus)

    def subscribe_to_events(self, event_bus: "EventBus"):
        """
        A hook for subclasses to subscribe to events.
        By default, it does nothing.
        """
        pass

    @abstractmethod
    def execute(self, analyzer: "GameAnalyzer", bot: "BotAI"):
        """
        Executes the analysis task.

        :param analyzer: The GameAnalyzer instance to read from and write to.
        :param bot: The main bot instance, for accessing raw game state.
        """
        pass
