# core/interfaces/manager_abc.py

from abc import ABC, abstractmethod


class Manager(ABC):
    """
    Defines the abstract contract for any high-level domain Manager.
    e.g., EconomyManager, MilitaryManager.
    """

    @abstractmethod
    async def execute(self):
        """
        The main execution method for the manager, called by its General
        on every game step.
        """
        pass
