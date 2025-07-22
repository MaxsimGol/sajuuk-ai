# sajuuk.py
import asyncio
from typing import TYPE_CHECKING, List

from sc2.bot_ai import BotAI
from sc2.data import Race
from sc2.unit import Unit
from sc2.unit_command import UnitCommand  # Import for type checking

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

        # --- FIX 1: Avoid the library's buggy distance calculation matrix ---
        self.distance_calculation_method = 0

        # --- FIX 2: Ensure unit methods return UnitCommand objects ---
        # This tells the library that we will handle action execution by appending
        # to self.actions, rather than using the old self.do() pattern.
        self.unit_command_uses_self_do = True

        self.global_cache = GlobalCache()
        self.logger = self.global_cache.logger
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
        game_time = self.time_formatted
        log = self.logger.bind(game_time=game_time)

        log.debug(f"--- Step {iteration} Start ---")

        await self.event_bus.process_events()

        self.game_analyzer.run(self)

        self.global_cache.update(self, self.game_analyzer, iteration)

        log.info(
            f"Cache Updated. Army Value: {self.global_cache.friendly_army_value} (F) vs "
            f"{self.global_cache.enemy_army_value} (E). Supply: {self.global_cache.supply_used}/{self.global_cache.supply_cap}"
        )

        frame_plan = FramePlan()

        command_functors: list[CommandFunctor] = await self.active_general.execute_step(
            self.global_cache, frame_plan, self.event_bus
        )

        log.info(
            f"Plan Generated. Budget: [I:{frame_plan.resource_budget.infrastructure}, C:{frame_plan.resource_budget.capabilities}]. "
            f"Stance: {frame_plan.army_stance.name}"
        )

        # --- FIX 3: Correctly process and queue actions ---
        if command_functors:
            for func in command_functors:
                # Execute the lambda to get the UnitCommand object
                action = func()
                # Ensure it's a valid command before appending
                if isinstance(action, UnitCommand):
                    self.actions.append(action)

        # The python-sc2 main loop will now execute everything in self.actions
        log.debug(f"Queued {len(self.actions)} actions for execution.")

        await self.event_bus.process_events()

        log.debug(f"--- Step {iteration} End ---")
