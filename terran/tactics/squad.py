# terran/tactics/squad.py
from __future__ import annotations
from dataclasses import dataclass
from enum import Enum, auto
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from sc2.position import Point2
    from sc2.units import Units


class SquadObjective(Enum):
    """
    Defines the high-level strategic goal for a squad.
    This determines the squad's behavior in the ArmyControlManager.
    """

    ATTACK = auto()  # Move to and engage the primary enemy target.
    DEFEND = auto()  # Hold a specific defensive position.
    HARASS = auto()  # Attack a secondary, vulnerable enemy location.
    SCOUT = auto()  # Gather information at a specific point.
    IDLE = auto()  # No current objective; gather at a rally point.


@dataclass
class Squad:
    """
    Represents a logical grouping of units with a shared, dynamic objective.

    This is a stateful object that allows the TacticalDirector and
    ArmyControlManager to issue high-level commands to a specific group of
    units without needing to manage them individually.
    """

    id: str
    units: "Units"
    objective: SquadObjective = SquadObjective.IDLE
    target: Optional["Point2"] = None

    @property
    def tags(self) -> set[int]:
        """Returns a set of all unit tags within this squad."""
        return self.units.tags

    @property
    def center(self) -> "Point2" | None:
        """Returns the geometric center of the squad's units."""
        return self.units.center if self.units.exists else None

    @property
    def is_empty(self) -> bool:
        """Returns True if the squad has no units."""
        return self.units.empty
