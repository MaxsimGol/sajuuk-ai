# core/interfaces/controller_abc.py
from __future__ import annotations
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, List, Set, Tuple

from core.types import CommandFunctor

if TYPE_CHECKING:
    # Import the new context object for type hinting.
    from terran.tactics.micro_context import MicroContext


class ControllerABC(ABC):
    """
    Defines the abstract contract for a specialist unit micro-controller.
    """

    @abstractmethod
    def execute(self, context: "MicroContext") -> tuple[list[CommandFunctor], set[int]]:
        """
        Executes micro-management for the units specified in the context.

        This method is the single entry point for all micro-controllers. It
        receives a unified context object, ensuring a consistent interface while
        allowing access to both general and specialized game state information.

        :param context: The MicroContext object containing all necessary data for
                        this frame's decision-making, including the specific
                        `units_to_control` and references to other friendly squads.
        :return: A tuple containing a list of command functors to be executed and
                a set of the unit tags that this controller has handled.
        """
        pass
