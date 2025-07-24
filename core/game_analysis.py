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
        # MODIFICATION: Initialize with empty Units objects instead of None
        # This requires a bot_object reference, which we don't have here.
        # We will initialize them as None and ensure the UnitsAnalyzer populates
        # them with valid, empty Units objects on the first run.
        # Let's add a placeholder for the bot object to create empty units.
        self._bot_object_for_init = None  # Will be set on first run.

        self.friendly_army_value: int = 0
        self.enemy_army_value: int = 0
        self.friendly_army_units: Units | None = None
        self.idle_production_structures: Units | None = None
        self.threat_map: np.ndarray | None = None
        # known_enemy attributes must be handled carefully, as they are stateful.
        # UnitsAnalyzer is responsible for their initialization and maintenance.
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

    def _initialize_empty_units(self, bot: "BotAI"):
        """Initializes all unit collections with empty Units objects on the first run."""
        if self._bot_object_for_init is None:
            self._bot_object_for_init = bot
            self.friendly_units = Units([], bot)
            self.friendly_structures = Units([], bot)
            self.friendly_workers = Units([], bot)
            self.friendly_army_units = Units([], bot)
            self.idle_production_structures = Units([], bot)
            self.known_enemy_units = Units([], bot)
            self.known_enemy_structures = Units([], bot)
            self.known_enemy_townhalls = Units([], bot)

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
            if hasattr(task, "subscribe_to_events"):
                subscribe_method = getattr(task, "subscribe_to_events")
                if callable(subscribe_method):
                    subscribe_method(event_bus)
            tasks.append(task)
        return tasks

    def run(self, bot: "BotAI"):
        """Executes the full analysis pipeline for the current game frame."""
        # Lazily initialize empty Units objects on the first run.
        self._initialize_empty_units(bot)

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
            or bot.state.game_loop
            < 10  # Run all low-freq tasks in the first few frames
        ):
            task_to_run = self._low_freq_tasks[self._low_freq_index]
            task_to_run.execute(self, bot)
            self._low_freq_index = (self._low_freq_index + 1) % len(
                self._low_freq_tasks
            )
