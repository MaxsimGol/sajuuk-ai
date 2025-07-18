# core/game_analysis.py

from typing import TYPE_CHECKING, List
import numpy as np
import inspect

from sc2.units import Units

from core.interfaces.analysis_task_abc import AnalysisTask
from core.event_bus import EventBus
from core.utilities.constants import LOW_FREQUENCY_TASK_RATE
from core.analysis.analysis_configuration import (
    HIGH_FREQUENCY_TASK_CLASSES,
    LOW_FREQUENCY_TASK_CLASSES,
    PRE_ANALYSIS_TASK_CLASSES,
)

if TYPE_CHECKING:
    from sc2.bot_ai import BotAI
    from sc2.position import Point2


class GameAnalyzer:
    """
    The central analysis engine. Owns analytical state and runs a staged,
    scheduled pipeline of tasks to ensure data dependencies and performance.
    """

    def __init__(self, event_bus: EventBus):
        # --- Analytical State Attributes ---
        self.friendly_army_value: int = 0
        self.enemy_army_value: int = 0
        self.friendly_units: Units | None = None
        self.friendly_structures: Units | None = None
        self.friendly_workers: Units | None = None
        self.friendly_army_units: Units | None = None
        self.idle_production_structures: Units | None = None
        self.threat_map: np.ndarray | None = None
        self.known_enemy_units: Units | None = None
        self.known_enemy_structures: Units | None = None
        self.known_enemy_townhalls: Units | None = None
        self.available_expansion_locations: set[Point2] = set()
        self.occupied_locations: set[Point2] = set()
        self.enemy_occupied_locations: set[Point2] = set()

        # --- Task Pipeline and Scheduler ---
        self._pre_analysis_tasks: List[AnalysisTask] = self._instantiate_tasks(
            PRE_ANALYSIS_TASK_CLASSES, event_bus
        )
        self._high_freq_tasks: List[AnalysisTask] = self._instantiate_tasks(
            HIGH_FREQUENCY_TASK_CLASSES, event_bus
        )
        self._low_freq_tasks: List[AnalysisTask] = self._instantiate_tasks(
            LOW_FREQUENCY_TASK_CLASSES, event_bus
        )
        self._high_freq_index: int = 0
        self._low_freq_index: int = 0

    def _instantiate_tasks(
        self, task_classes: List[type[AnalysisTask]], event_bus: EventBus
    ) -> List[AnalysisTask]:
        """
        Factory helper to instantiate tasks and wire up event subscriptions
        for those that require it.
        """
        tasks = []
        for TaskCls in task_classes:
            task = TaskCls()
            # If the task has a subscription method, call it.
            if hasattr(task, "subscribe_to_events"):
                subscribe_method = getattr(task, "subscribe_to_events")
                if callable(subscribe_method):
                    subscribe_method(event_bus)
            tasks.append(task)
        return tasks

    def run(self, bot: "BotAI"):
        """Executes the full analysis pipeline for the current game frame."""
        # STAGE 1: Pre-Analysis (every frame, guaranteed order)
        for task in self._pre_analysis_tasks:
            task.execute(self, bot)

        # STAGE 2: Scheduled High-Frequency Analysis (round-robin)
        if self._high_freq_tasks:
            task_to_run = self._high_freq_tasks[self._high_freq_index]
            task_to_run.execute(self, bot)
            self._high_freq_index = (self._high_freq_index + 1) % len(
                self._high_freq_tasks
            )

        # STAGE 3: Scheduled Low-Frequency Analysis (periodic)
        if self._low_freq_tasks and (
            bot.state.game_loop % LOW_FREQUENCY_TASK_RATE == 0
        ):
            task_to_run = self._low_freq_tasks[self._low_freq_index]
            task_to_run.execute(self, bot)
            self._low_freq_index = (self._low_freq_index + 1) % len(
                self._low_freq_tasks
            )
