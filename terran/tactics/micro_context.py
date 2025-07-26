# terran/tactics/micro_context.py
from __future__ import annotations
from dataclasses import dataclass
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from sc2.position import Point2
    from sc2.units import Units
    from sc2.unit import Unit
    from core.global_cache import GlobalCache
    from core.frame_plan import FramePlan


@dataclass
class MicroContext:
    """
    A standardized container for all data required by a micro-controller.

    This object is created by the ArmyControlManager each frame and passed to
    the `execute` method of each specialist controller, ensuring a consistent
    interface while providing specialized information.
    """

    # --- Core Information for ALL Controllers ---
    # The specific group of units this controller instance should manage.
    units_to_control: "Units"
    # The high-level strategic target for the army.
    target: "Point2"
    # The complete, read-only state of the game for this frame.
    cache: "GlobalCache"
    # The high-level plan and strategic stances for this frame.
    plan: "FramePlan"

    # --- Coordinated Action Information ---
    # The single, highest-priority enemy unit for the entire army to focus fire.
    focus_fire_target: Optional["Unit"] = None

    # --- Optional Squad Information ---
    # Provides context about other friendly forces for coordination.
    bio_squad: Optional["Units"] = None
    mech_squad: Optional["Units"] = None
    air_squad: Optional["Units"] = None
    support_squad: Optional["Units"] = None
