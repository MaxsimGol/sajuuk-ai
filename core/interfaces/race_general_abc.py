from abc import ABC, abstractmethod


class RaceGeneral(ABC):
    """
    Defines the abstract contract for a race-specific General.
    This is the interface the main Sajuuk Conductor interacts with.
    """

    @abstractmethod
    async def on_start(self):
        """
        Called once at the start of the game.
        Responsible for initializing all race-specific managers.
        """
        pass

    @abstractmethod
    async def execute_step(self):
        """
        The main logic loop for the General, called every game step by the Conductor.
        Responsible for orchestrating its managers.
        """
        pass
