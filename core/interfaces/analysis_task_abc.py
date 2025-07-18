from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from sc2.bot_ai import BotAI
    from core.game_analysis import GameAnalyzer


class AnalysisTask(ABC):
    """
    Abstract base class for a single, focused analysis task.
    """

    def __init__(self):
        """
        Initializes the task. Subclasses that need to subscribe to events
        should implement a 'subscribe_to_events' method.
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
