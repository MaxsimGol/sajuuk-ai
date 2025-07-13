from enum import Enum, auto
from typing import TYPE_CHECKING

import numpy as np

from core.utilities.geometry import create_threat_map
from core.utilities.unit_value import calculate_army_value

# Import the new constant for scheduling frequency
from core.utilities.constants import LOW_FREQUENCY_TASK_RATE

if TYPE_CHECKING:
    from sc2.bot_ai import BotAI
    from core.global_cache import GlobalCache


class HighFrequencyTask(Enum):
    """Defines lightweight tasks that can run in a fast round-robin cycle."""

    UPDATE_FRIENDLY_ARMY_VALUE = auto()
    UPDATE_ENEMY_ARMY_VALUE = auto()


class LowFrequencyTask(Enum):
    """Defines heavyweight tasks that run on a slower, periodic cycle."""

    UPDATE_THREAT_MAP = auto()


class GameAnalyzer:
    """
    An active component that performs scheduled analysis using a tiered approach.

    High-frequency tasks (like army value) are cycled through on every frame.
    Low-frequency tasks (like threat maps) are executed only once every N frames
    to ensure smooth performance.
    """

    def __init__(self):
        """Initializes the task lists for each tier."""
        self._high_freq_tasks: list[HighFrequencyTask] = list(HighFrequencyTask)
        self._low_freq_tasks: list[LowFrequencyTask] = list(LowFrequencyTask)

        self._high_freq_index: int = 0
        self._low_freq_index: int = 0

    def run_scheduled_tasks(self, cache: "GlobalCache", bot: "BotAI"):
        """
        Executes the next scheduled tasks based on the tiered schedule.

        This method is called once per frame by the RaceGeneral.
        """
        # --- Always run one high-frequency task ---
        if self._high_freq_tasks:
            task_to_run = self._high_freq_tasks[self._high_freq_index]
            self._execute_high_frequency_task(task_to_run, cache, bot)
            self._high_freq_index = (self._high_freq_index + 1) % len(
                self._high_freq_tasks
            )

        # --- Only run one low-frequency task periodically ---
        if self._low_freq_tasks and (
            bot.state.game_loop % LOW_FREQUENCY_TASK_RATE == 0
        ):
            task_to_run = self._low_freq_tasks[self._low_freq_index]
            self._execute_low_frequency_task(task_to_run, cache, bot)
            self._low_freq_index = (self._low_freq_index + 1) % len(
                self._low_freq_tasks
            )

    def _execute_high_frequency_task(
        self, task: HighFrequencyTask, cache: "GlobalCache", bot: "BotAI"
    ):
        """Executes a specific high-frequency analysis task."""
        if task == HighFrequencyTask.UPDATE_FRIENDLY_ARMY_VALUE:
            army_units = bot.units.not_structure.not_worker
            cache.friendly_army_value = calculate_army_value(army_units, bot.game_data)
        elif task == HighFrequencyTask.UPDATE_ENEMY_ARMY_VALUE:
            cache.enemy_army_value = calculate_army_value(
                bot.enemy_units, bot.game_data
            )

    def _execute_low_frequency_task(
        self, task: LowFrequencyTask, cache: "GlobalCache", bot: "BotAI"
    ):
        """Executes a specific low-frequency analysis task."""
        if task == LowFrequencyTask.UPDATE_THREAT_MAP:
            map_size = bot.game_info.map_size
            if bot.enemy_units.exists:
                cache.threat_map = create_threat_map(bot.enemy_units, map_size)
            elif cache.threat_map is None:
                cache.threat_map = np.zeros(map_size, dtype=np.float32)
