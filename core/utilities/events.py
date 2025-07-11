# core/utilities/events.py

from enum import Enum, auto
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from sc2.ids.unit_typeid import UnitTypeId
    from sc2.position import Point2


class EventType(Enum):
    """
    Defines all possible event types in the system.

    This strict registry prevents the use of "magic strings" and makes the
    system's communication patterns discoverable and maintainable.
    Namespacing (e.g., DOMAIN_ACTION) clarifies event ownership.
    """

    # --- Infrastructure Events ---
    # Published by any module needing a structure built.
    # Handled by ConstructionManager.
    INFRA_BUILD_REQUEST = auto()

    # Published by ConstructionManager on failure.
    # Handled by the original requester.
    INFRA_BUILD_REQUEST_FAILED = auto()

    # --- Tactics Events ---
    # Published by ScoutingManager.
    # Handled by various Directors to adapt strategy.
    TACTICS_ENEMY_TECH_SCOUTED = auto()

    # A high-priority version of the above.
    TACTICS_PROXY_DETECTED = auto()

    # Published by the main bot loop's on_unit_took_damage hook.
    # Handled by RepairManager.
    TACTICS_UNIT_TOOK_DAMAGE = auto()


# --- Payload Data Structures ---


@dataclass
class BuildRequestPayload:
    """Payload for an INFRA_BUILD_REQUEST event."""

    item_id: UnitTypeId
    position: Point2 | None = None
    priority: int = 10  # Lower number is higher priority


@dataclass
class BuildRequestFailedPayload:
    """Payload for an INFRA_BUILD_REQUEST_FAILED event."""

    item_id: UnitTypeId
    reason: str


@dataclass
class EnemyTechScoutedPayload:
    """Payload for a TACTICS_ENEMY_TECH_SCOUTED event."""

    tech_id: UnitTypeId


@dataclass
class UnitTookDamagePayload:
    """Payload for a TACTICS_UNIT_TOOK_DAMAGE event."""

    unit_tag: int
    damage_amount: float


# --- The Generic Event Wrapper ---


@dataclass
class Event:
    """
    A generic wrapper for all events published to the EventBus.
    """

    type: EventType
    payload: object | None = None
