from __future__ import annotations
from enum import Enum, auto
from dataclasses import dataclass
from typing import TYPE_CHECKING
from abc import ABC

# This block was missing. It provides the definitions for type hints.
if TYPE_CHECKING:
    from sc2.ids.unit_typeid import UnitTypeId
    from sc2.position import Point2
    from sc2.unit import Unit

from core.utilities.constants import EVENT_PRIORITY_NORMAL


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

    # Published by the main bot's on_enemy_unit_entered_vision hook.
    # Handled by GameAnalyzer.
    TACTICS_ENEMY_UNIT_SEEN = auto()

    # Published by the main bot loop's on_unit_destroyed hook.
    # Handled by GameAnalyzer.
    UNIT_DESTROYED = auto()


class Payload(ABC):
    """An abstract base class for all event payloads."""

    pass


# --- Payload Data Structures ---


@dataclass
class BuildRequestPayload(Payload):
    """Payload for an INFRA_BUILD_REQUEST event."""

    item_id: "UnitTypeId"
    position: "Point2" | None = None
    priority: int = EVENT_PRIORITY_NORMAL
    unique: bool = False


@dataclass
class BuildRequestFailedPayload(Payload):
    """Payload for an INFRA_BUILD_REQUEST_FAILED event."""

    item_id: "UnitTypeId"
    reason: str


@dataclass
class EnemyTechScoutedPayload(Payload):
    """Payload for a TACTICS_ENEMY_TECH_SCOUTED event."""

    tech_id: "UnitTypeId"


@dataclass
class UnitTookDamagePayload(Payload):
    """Payload for a TACTICS_UNIT_TOOK_DAMAGE event."""

    unit_tag: int
    damage_amount: float


@dataclass
class UnitDestroyedPayload(Payload):
    """Payload for a UNIT_DESTROYED event."""

    unit_tag: int
    unit_type: "UnitTypeId"
    last_known_position: "Point2"


@dataclass
class EnemyUnitSeenPayload(Payload):
    """Payload for a TACTICS_ENEMY_UNIT_SEEN event."""

    unit: "Unit"


# --- The Generic Event Wrapper ---


@dataclass
class Event:
    """
    A generic wrapper for an event published to the EventBus.

    Attributes:
    -----------
    event_type: EventType
        The specific type of the event, which determines which subscribers
        will be notified. This is the primary identifier for the event.

    payload: PayloadT | None
        The data associated with the event, providing context for what
        happened. This is typically one of the specific payload dataclasses
        (e.g., BuildRequestPayload, UnitDestroyedPayload). Its type is
        linked to the event_type through the generic `PayloadT`.
    """

    event_type: EventType
    payload: Payload | None = None
