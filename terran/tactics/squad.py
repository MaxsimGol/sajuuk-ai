# terran/tactics/squad.py
from __future__ import annotations
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from sc2.units import Units


@dataclass
class Squad:
    """
    Represents a logical grouping of units with a shared purpose.
    This is a stateful object that can be expanded to track squad health,
    orders, or status in the future.
    """

    id: str
    units: "Units" = field(default_factory=list)

    @property
    def tags(self) -> set[int]:
        return self.units.tags

    @property
    def center(self):
        return self.units.center if self.units.exists else None
