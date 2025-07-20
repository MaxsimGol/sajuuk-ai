# sajuuk.py

import asyncio
from typing import TYPE_CHECKING

from sc2.bot_ai import BotAI
from sc2.data import Race
from sc2.unit import Unit

from core.global_cache import GlobalCache
from core.game_analysis import GameAnalyzer
from core.frame_plan import FramePlan
from core.types import CommandFunctor
from core.interfaces.race_general_abc import RaceGeneral
from core.utilities.events import (
    Event,
    EventType,
    UnitDestroyedPayload,
    EnemyUnitSeenPayload,
)
from terran.general.terran_general import TerranGeneral

if TYPE_CHECKING:
    from core.event_bus import EventBus


class Sajuuk(BotAI):
    """The Conductor. Orchestrates the main Perceive-Analyze-Plan-Act loop."""

    def __init__(self):
        super().__init__()
        self.global_cache = GlobalCache()
        self.event_bus: "EventBus" = self.global_cache.event_bus
        self.game_analyzer = GameAnalyzer(self.event_bus)
        self.active_general: RaceGeneral | None = None

    async def on_start(self):
        if self.race == Race.Terran:
            self.active_general = TerranGeneral(self)
        else:
            raise NotImplementedError(f"Sajuuk does not support race: {self.race}")
        if self.active_general:
            await self.active_general.on_start()

    async def on_enemy_unit_entered_vision(self, unit: Unit):
        self.event_bus.publish(
            Event(EventType.TACTICS_ENEMY_UNIT_SEEN, EnemyUnitSeenPayload(unit))
        )

    async def on_unit_destroyed(self, unit_tag: int):
        unit = self._all_units_previous_map.get(unit_tag)
        if not unit:
            return
        self.event_bus.publish(
            Event(
                EventType.UNIT_DESTROYED,
                UnitDestroyedPayload(unit.tag, unit.type_id, unit.position),
            )
        )

    async def on_step(self, iteration: int):
        # 1. PROCESS SENSOR INPUT: Handle all perception events that have been
        # queued by the on_... hooks since the last frame. This updates the
        # internal state of analyzers BEFORE they run.
        await self.event_bus.process_events()

        # 2. ANALYZE: Run the full analysis pipeline. The analyzer now has
        # the most up-to-date information from the event handlers.
        self.game_analyzer.run(self)

        # 3. CACHE: Populate the GlobalCache with a consistent snapshot for this frame.
        self.global_cache.update(self, self.game_analyzer)

        # 4. PLAN: Create a fresh "scratchpad" for this frame's intentions.
        frame_plan = FramePlan()

        # 5. DECIDE: The race-specific General orchestrates its Directors.
        # This phase may PUBLISH new events (like BuildRequest).
        command_functors: list[CommandFunctor] = await self.active_general.execute_step(
            self.global_cache, frame_plan, self.event_bus
        )

        # 6. ACT: Execute all collected commands.
        if command_functors:
            async_tasks = [
                func() for func in command_functors if asyncio.iscoroutine(func())
            ]
            sync_actions = [
                func() for func in command_functors if not asyncio.iscoroutine(func())
            ]
            if async_tasks:
                await asyncio.gather(*async_tasks)

        # 7. PROCESS ACTION/REQUEST EVENTS: Now process the events that were
        # queued during the DECIDE phase (step 5). This allows service managers
        # like ConstructionManager and RepairManager to run.
        await self.event_bus.process_events()
