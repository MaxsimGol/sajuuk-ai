# core/frame_plan.py
from __future__ import annotations
from enum import Enum, auto
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Dict, List, Set, Optional

if TYPE_CHECKING:
    from sc2.ids.unit_typeid import UnitTypeId
    from sc2.ids.upgrade_id import UpgradeId
    from sc2.position import Point2

# --- Strategic Stances ---


class ArmyStance(Enum):
    """Defines the high-level tactical stance of the army for the current frame."""

    DEFENSIVE = auto()
    AGGRESSIVE = auto()
    HARASS = auto()


class EconomicStance(Enum):
    """Defines the high-level economic goal for the frame."""

    NORMAL = auto()
    SAVING_FOR_EXPANSION = auto()
    SAVING_FOR_TECH = auto()


@dataclass
class ResourceBudget:
    """Defines the resource allocation for a frame. Values should sum to 100."""

    infrastructure: int = 50
    capabilities: int = 50
    tactics: int = 0


class FramePlan:
    """
    An ephemeral "scratchpad" for the current frame's strategic intentions.
    It is created fresh each step and populated by Directors to guide Managers.
    """

    def __init__(self):
        # --- High-Level Intentions (Set by Directors) ---
        self.resource_budget: ResourceBudget = ResourceBudget()
        self.army_stance: ArmyStance = ArmyStance.DEFENSIVE
        self.economic_stance: EconomicStance = EconomicStance.NORMAL

        # --- Capability Goals (Set by CapabilityDirector) ---
        self.unit_composition_goal: Dict[UnitTypeId, int] = field(default_factory=dict)
        self.tech_goals: Set[UnitTypeId] = field(default_factory=set)
        self.upgrade_goal: List[UpgradeId] = field(default_factory=list)
        # --- ADDED BACK: The missing piece ---
        # Defines the target count for each type of addon building.
        # e.g., {UnitTypeId.BARRACKSTECHLAB: 1, UnitTypeId.BARRACKSREACTOR: 2}
        self.addon_goal: Dict[UnitTypeId, int] = field(default_factory=dict)

        # --- Tactical Positions (Set by PositioningManager) ---
        self.defensive_position: Optional["Point2"] = None
        self.staging_point: Optional["Point2"] = None
        self.rally_point: Optional["Point2"] = None
        self.target_location: Optional["Point2"] = None

    def set_budget(self, infrastructure: int, capabilities: int, tactics: int = 0):
        """Sets the resource budget for the frame. Called by InfrastructureDirector."""
        if (infrastructure + capabilities + tactics) == 100:
            self.resource_budget = ResourceBudget(infrastructure, capabilities, tactics)

    def set_army_stance(self, stance: ArmyStance):
        """Sets the army's tactical stance. Called by TacticalDirector."""
        self.army_stance = stance

    def set_economic_stance(self, stance: EconomicStance):
        """Sets the economic focus. Called by InfrastructureDirector."""
        self.economic_stance = stance
