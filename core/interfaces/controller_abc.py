from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

from core.types import CommandFunctor

if TYPE_CHECKING:
    from sc2.position import Point2
    from sc2.units import Units
    from core.global_cache import GlobalCache
    from core.frame_plan import FramePlan


class ControllerABC(ABC):
    """
    Defines the abstract contract for a specialist unit micro-controller.
    """

    @abstractmethod
    def execute(
        self, units: "Units", target: "Point2", cache: "GlobalCache", plan: "FramePlan"
    ) -> tuple[list[CommandFunctor], set[int]]:
        """
        Executes micro-management for a group of units.

        :param units: The Units object containing the units to be controlled.
        :param target: The high-level strategic target.
        :param cache: The global cache for accessing game state.
        :param plan: The frame plan for accessing tactical positions.
        :return: A tuple containing (list of command functors, set of handled unit tags).
        """
        pass
