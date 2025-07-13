# sajuuk.py

import asyncio
from typing import Callable, Coroutine, List

from sc2.bot_ai import BotAI
from sc2.data import Race

# Core Services (No changes here)
from core.global_cache import GlobalCache
from core.event_bus import EventBus
from core.game_analysis import GameAnalyzer
from core.frame_plan import FramePlan
from core.types import CommandFunctor

# Interfaces and Generals (No changes here)
from core.interfaces.race_general_abc import RaceGeneral
from terran.general.terran_general import TerranGeneral

# ... other generals


class Sajuuk(BotAI):
    """
    The Conductor. (Documentation remains the same)
    """

    def __init__(self):
        """(Initialization is the same)"""
        super().__init__()
        self.global_cache: GlobalCache = GlobalCache()
        self.event_bus: EventBus = EventBus()
        self.game_analyzer: GameAnalyzer = GameAnalyzer()
        self.active_general: RaceGeneral | None = None

    async def on_start(self):
        """(on_start is the same)"""
        if self.race == Race.Terran:
            self.active_general = TerranGeneral(self)
        else:
            raise NotImplementedError(f"Sajuuk does not support race: {self.race}")

        if self.active_general:
            await self.active_general.on_start()

    async def on_step(self, iteration: int):
        """
        The main cognitive loop, now adapted for the modern python-sc2 API.
        """
        if not self.active_general:
            return

        # 1. PERCEIVE
        self.global_cache.update(self.state, self)

        # 2. ANALYZE
        self.game_analyzer.run_scheduled_tasks(self.global_cache, self)

        # 3. PLAN
        frame_plan = FramePlan()

        # 4. DECIDE
        # The General now returns a list of Command Functors (callables).
        command_functors: List[CommandFunctor] = await self.active_general.execute_step(
            self.global_cache, frame_plan, self.event_bus
        )

        # 5. ACT: Execute all collected command functors.
        # This is the new, correct way to handle actions. We iterate through the
        # list of deferred actions and execute them now, in one controlled burst.
        if command_functors:
            # We can use asyncio.gather to run them concurrently for maximum efficiency.
            await asyncio.gather(*[func() for func in command_functors])

        # 6. PROCESS REFLEXES
        await self.event_bus.process_events()
