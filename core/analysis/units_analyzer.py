# core/analysis/unit_analyzer.py

from typing import TYPE_CHECKING, Dict

from sc2.unit import Unit
from sc2.units import Units

from core.interfaces.analysis_task_abc import AnalysisTask
from core.utilities.events import (
    Event,
    EventType,
    UnitDestroyedPayload,
    EnemyUnitSeenPayload,
)
from core.utilities.unit_types import TERRAN_PRODUCTION_TYPES

if TYPE_CHECKING:
    from sc2.bot_ai import BotAI
    from core.event_bus import EventBus
    from core.game_analysis import GameAnalyzer


class UnitsAnalyzer(AnalysisTask):
    """
    A central, stateful analyzer that maintains a persistent memory of all
    known enemy units, including snapshots in the fog of war.
    """

    def __init__(self, event_bus: "EventBus"):
        super().__init__(event_bus)
        self._known_enemy_units: Dict[int, Unit] = {}

    def subscribe_to_events(self, event_bus: "EventBus"):
        """Subscribes to the fundamental unit-tracking events."""
        event_bus.subscribe(
            EventType.TACTICS_ENEMY_UNIT_SEEN, self.handle_enemy_unit_seen
        )
        event_bus.subscribe(EventType.UNIT_DESTROYED, self.handle_unit_destroyed)

    def execute(self, analyzer: "GameAnalyzer", bot: "BotAI"):
        """
        On each frame, this method updates the GameAnalyzer with the current
        snapshot of all known units from its persistent memory.
        """
        all_friendly_units = bot.units

        analyzer.friendly_units = all_friendly_units
        analyzer.friendly_structures = all_friendly_units.structure
        analyzer.friendly_workers = all_friendly_units.worker

        analyzer.friendly_army_units = all_friendly_units.filter(
            lambda u: not u.is_structure and not u.is_worker
        )
        analyzer.idle_production_structures = analyzer.friendly_structures.of_type(
            TERRAN_PRODUCTION_TYPES
        ).idle
        analyzer.known_enemy_units = Units(self._known_enemy_units.values(), bot)
        analyzer.known_enemy_structures = analyzer.known_enemy_units.structure

    async def handle_enemy_unit_seen(self, event: Event):
        """Adds or updates a unit in our persistent memory when it enters vision."""
        payload: EnemyUnitSeenPayload = event.payload
        self._known_enemy_units[payload.unit.tag] = payload.unit

    async def handle_unit_destroyed(self, event: Event):
        """Removes a unit from our persistent memory when it is destroyed."""
        payload: UnitDestroyedPayload = event.payload
        self._known_enemy_units.pop(payload.unit_tag, None)
