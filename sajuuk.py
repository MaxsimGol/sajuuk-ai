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
        # 1. PERCEIVE
        self.global_cache.update(self.state, self)

        # 2. ANALYZE
        self.game_analyzer.run_scheduled_tasks(self.global_cache, self)

        # 3. PLAN
        frame_plan = FramePlan()

        # 4. DECIDE
        command_functors: List[CommandFunctor] = await self.active_general.execute_step(
            self.global_cache, frame_plan, self.event_bus
        )

        # 5. ACT: Execute all collected command functors with intelligent handling.
        if command_functors:
            # This is the new, more robust execution logic.
            # We separate the synchronous from the asynchronous functors.
            async_tasks = []
            for func in command_functors:
                result = func()
                # If the result is a coroutine, it's an async action.
                # We add it to our list of tasks to be gathered.
                if asyncio.iscoroutine(result):
                    async_tasks.append(result)
                # If the result is not a coroutine, it was a synchronous action
                # that has already completed. We do nothing further.

            # We then await all the async tasks concurrently.
            if async_tasks:
                await asyncio.gather(*async_tasks)

        # 6. PROCESS REFLEXES (remains the same)
        await self.event_bus.process_events()
