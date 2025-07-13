# tests/test_core/test_game_analysis.py

from unittest import IsolatedAsyncioTestCase
from unittest.mock import Mock, patch, call

from core.game_analysis import GameAnalyzer, HighFrequencyTask, LowFrequencyTask
from core.utilities.constants import LOW_FREQUENCY_TASK_RATE


# --- NEW: Test Double for the sc2.units.Units class ---
class UnitsTestDouble(list):
    """
    A Test Double that mimics the essential properties of the sc2.units.Units class
    for testing purposes. It is iterable like a list and has an `exists` property.
    """

    @property
    def exists(self) -> bool:
        return len(self) > 0


class TestGameAnalyzer(IsolatedAsyncioTestCase):
    """
    Tests the GameAnalyzer to ensure its tiered scheduling correctly distributes
    computational load across game frames.
    """

    def setUp(self):
        """
        Set up a new analyzer and mock dependencies for each test.
        """
        self.analyzer = GameAnalyzer()

        self.mock_bot = Mock()
        self.mock_cache = Mock()

        # --- KEY FIX: Use the new Test Double ---
        # Instead of a bare list, we use our custom Test Double which has the
        # required '.exists' property.
        self.mock_bot.units.not_structure.not_worker = UnitsTestDouble()
        self.mock_bot.enemy_units = UnitsTestDouble()

        self.mock_bot.state = Mock()

    @patch.object(GameAnalyzer, "_execute_low_frequency_task")
    @patch.object(GameAnalyzer, "_execute_high_frequency_task")
    def test_high_frequency_tasks_cycle_every_frame(
        self, mock_high_freq_exec, mock_low_freq_exec
    ):
        # ... (This test's code does not need to change) ...
        self.mock_bot.state.game_loop = 0
        self.analyzer.run_scheduled_tasks(self.mock_cache, self.mock_bot)
        self.mock_bot.state.game_loop = 1
        self.analyzer.run_scheduled_tasks(self.mock_cache, self.mock_bot)
        self.mock_bot.state.game_loop = 2
        self.analyzer.run_scheduled_tasks(self.mock_cache, self.mock_bot)
        self.assertEqual(mock_high_freq_exec.call_count, 3)
        expected_calls = [
            call(
                HighFrequencyTask.UPDATE_FRIENDLY_ARMY_VALUE,
                self.mock_cache,
                self.mock_bot,
            ),
            call(
                HighFrequencyTask.UPDATE_ENEMY_ARMY_VALUE,
                self.mock_cache,
                self.mock_bot,
            ),
            call(
                HighFrequencyTask.UPDATE_FRIENDLY_ARMY_VALUE,
                self.mock_cache,
                self.mock_bot,
            ),
        ]
        self.assertEqual(mock_high_freq_exec.call_args_list, expected_calls)
        self.assertEqual(mock_low_freq_exec.call_count, 1)

    @patch.object(GameAnalyzer, "_execute_low_frequency_task")
    def test_low_frequency_tasks_run_periodically(self, mock_low_freq_exec):
        # ... (This test's code does not need to change) ...
        for i in range(LOW_FREQUENCY_TASK_RATE * 2 + 1):
            self.mock_bot.state.game_loop = i
            self.analyzer.run_scheduled_tasks(self.mock_cache, self.mock_bot)
        self.assertEqual(mock_low_freq_exec.call_count, 3)
        self.assertEqual(
            mock_low_freq_exec.call_args_list[0].args[0],
            LowFrequencyTask.UPDATE_THREAT_MAP,
        )
        self.assertEqual(
            mock_low_freq_exec.call_args_list[1].args[0],
            LowFrequencyTask.UPDATE_THREAT_MAP,
        )
        self.assertEqual(
            mock_low_freq_exec.call_args_list[2].args[0],
            LowFrequencyTask.UPDATE_THREAT_MAP,
        )

    @patch("core.game_analysis.create_threat_map")
    def test_threat_map_task_calls_utility_and_updates_cache(
        self, mock_create_threat_map
    ):
        """
        An integration test to verify that executing a specific task correctly
        calls its underlying utility function and writes the result to the cache.
        """
        # --- Arrange ---
        mock_map_data = "THREAT_MAP_DATA"
        mock_create_threat_map.return_value = mock_map_data

        # --- KEY FIX: Populate the Test Double ---
        # We can now add mock units to our test double just like a list.
        # This will make its `exists` property return True.
        mock_enemy_unit = Mock()
        self.mock_bot.enemy_units.append(mock_enemy_unit)

        self.mock_bot.game_info.map_size = (128, 128)

        # Force the low-frequency task to run
        self.mock_bot.state.game_loop = 0
        self.analyzer._low_freq_index = self.analyzer._low_freq_tasks.index(
            LowFrequencyTask.UPDATE_THREAT_MAP
        )

        # --- Act ---
        self.analyzer.run_scheduled_tasks(self.mock_cache, self.mock_bot)

        # --- Assert ---
        mock_create_threat_map.assert_called_once_with(
            self.mock_bot.enemy_units, (128, 128)
        )
        self.assertEqual(self.mock_cache.threat_map, mock_map_data)
