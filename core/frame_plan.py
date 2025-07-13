from __future__ import annotations
from enum import Enum, auto
from dataclasses import dataclass, field

# --- Data Structures for Intentions ---


class ArmyStance(Enum):
    """Defines the high-level tactical stance of the army for the current frame."""

    DEFENSIVE = auto()
    AGGRESSIVE = auto()
    HARASS = auto()


@dataclass
class ResourceBudget:
    """
    Defines the percentage-based resource allocation for a frame.
    Values should sum to 100.
    """

    infrastructure: int = 20  # Builds your economy (bases, workers, supply).
    capabilities: int = 80  # Army + Tech + Upgrades
    tactics: int = 0  # e.g., for paid scouting like changelings


# --- The FramePlan Class ---


class FramePlan:
    """
    An ephemeral "scratchpad" for the current frame's strategic intentions.

    This object is created fresh by the General on every game step.
    Directors write their high-level plans to it (e.g., budget, stance),
    and other Directors or Managers can then read those plans to coordinate
    their actions within the same frame.

    This solves the intra-frame state conflict problem by providing a
    clear, one-way flow of intent.
    """

    def __init__(self):
        # The resource allocation plan set by the InfrastructureDirector.
        self.resource_budget: ResourceBudget = ResourceBudget()

        # The tactical plan set by the TacticalDirector.
        self.army_stance: ArmyStance = ArmyStance.DEFENSIVE

        # A set of high-priority production requests for the frame.
        self.production_requests: set[object] = set()

    def set_budget(self, infrastructure: int, capabilities: int, tactics: int = 0):
        """
        Sets the resource budget for the frame.
        Called by the InfrastructureDirector.
        Values should sum to 100
        """
        # Basic validation to ensure budget makes sense.
        if (infrastructure + capabilities + tactics) != 100:
            # In a real scenario, this would log a warning.
            # For now, we silently fail or adjust.
            pass
        self.resource_budget = ResourceBudget(infrastructure, capabilities, tactics)

    def set_army_stance(self, stance: ArmyStance):
        """
        Sets the army's tactical stance for the frame.
        Called by the TacticalDirector.
        """
        self.army_stance = stance

    def add_production_request(self, request: object):
        """
        Adds a high-priority production item to the plan.
        Useful for reactive builds (e.g., "Build a turret NOW").
        """
        self.production_requests.add(request)
