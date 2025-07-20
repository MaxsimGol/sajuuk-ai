import unittest
from unittest.mock import MagicMock, patch


import numpy as np
from sc2.game_data import Cost
from sc2.ids.unit_typeid import UnitTypeId
from sc2.position import Point2
from sc2.units import Units
from sc2.data import Race

from core.analysis.analysis_configuration import (
    HIGH_FREQUENCY_TASK_CLASSES,
    LOW_FREQUENCY_TASK_CLASSES,
    PRE_ANALYSIS_TASK_CLASSES,
)
from core.analysis.army_value_analyzer import (
    EnemyArmyValueAnalyzer,
    FriendlyArmyValueAnalyzer,
)
from core.analysis.expansion_analyzer import ExpansionAnalyzer
from core.analysis.known_enemy_townhall_analyzer import KnownEnemyTownhallAnalyzer
from core.analysis.threat_map_analyzer import ThreatMapAnalyzer
from core.analysis.units_analyzer import UnitsAnalyzer
from core.game_analysis import GameAnalyzer
from core.utilities.constants import LOW_FREQUENCY_TASK_RATE
from core.utilities.events import (
    Event,
    EventType,
    EnemyUnitSeenPayload,
    UnitDestroyedPayload,
)


def create_mock_unit(type_id, position=(0, 0), tag=0, is_structure=False):
    """Helper function to create a mock Unit object."""
    unit = MagicMock()
    unit.type_id = type_id
    unit.position = Point2(position)
    unit.tag = tag
    unit.is_structure = is_structure
    return unit


class TestGameAnalyzerScheduler(unittest.TestCase):
    """Tests the scheduling logic of the GameAnalyzer.run() method."""

    def setUp(self):
        self.mock_bot = MagicMock()
        self.mock_event_bus = MagicMock()
        self.analyzer = GameAnalyzer(self.mock_event_bus)

    def test_run_executes_pre_analysis_tasks_every_time(self):
        # Arrange
        mock_tasks = [MagicMock() for _ in PRE_ANALYSIS_TASK_CLASSES]
        with patch.object(self.analyzer, "_pre_analysis_tasks", mock_tasks):
            # Act
            self.analyzer.run(self.mock_bot)
            self.analyzer.run(self.mock_bot)

            # Assert
            for task in mock_tasks:
                self.assertEqual(task.execute.call_count, 2)
                task.execute.assert_called_with(self.analyzer, self.mock_bot)

    def test_run_executes_high_frequency_tasks_round_robin(self):
        # Arrange
        mock_tasks = [MagicMock(), MagicMock()]  # Two mock tasks
        with patch.object(self.analyzer, "_high_freq_tasks", mock_tasks):
            # Act & Assert - First run
            self.analyzer.run(self.mock_bot)
            mock_tasks[0].execute.assert_called_once_with(self.analyzer, self.mock_bot)
            mock_tasks[1].execute.assert_not_called()

            # Act & Assert - Second run
            self.analyzer.run(self.mock_bot)
            mock_tasks[0].execute.assert_called_once()  # Still 1
            mock_tasks[1].execute.assert_called_once_with(self.analyzer, self.mock_bot)

            # Act & Assert - Third run (wraps around)
            self.analyzer.run(self.mock_bot)
            self.assertEqual(mock_tasks[0].execute.call_count, 2)
            self.assertEqual(mock_tasks[1].execute.call_count, 1)

    def test_run_executes_low_frequency_tasks_periodically(self):
        # Arrange
        mock_task = MagicMock()
        with patch.object(self.analyzer, "_low_freq_tasks", [mock_task]):
            # Act & Assert - Off-cycle
            self.mock_bot.state.game_loop = LOW_FREQUENCY_TASK_RATE - 1
            self.analyzer.run(self.mock_bot)
            mock_task.execute.assert_not_called()

            # Act & Assert - On-cycle
            self.mock_bot.state.game_loop = LOW_FREQUENCY_TASK_RATE
            self.analyzer.run(self.mock_bot)
            mock_task.execute.assert_called_once_with(self.analyzer, self.mock_bot)

            # Act & Assert - Another off-cycle
            self.mock_bot.state.game_loop = LOW_FREQUENCY_TASK_RATE + 1
            self.analyzer.run(self.mock_bot)
            mock_task.execute.assert_called_once()  # Still 1 call


class TestAnalysisTasks(unittest.TestCase):
    """Tests the logic of individual AnalysisTask classes."""

    def setUp(self):
        self.mock_bot = MagicMock()
        # Mock the Units class to accept an iterable
        self.mock_bot.units = Units([], self.mock_bot)
        self.mock_bot.enemy_units = Units([], self.mock_bot)
        self.mock_event_bus = MagicMock()
        self.analyzer = GameAnalyzer(self.mock_event_bus)

    def test_units_analyzer_categorizes_friendly_units(self):
        # Arrange
        scv = create_mock_unit(UnitTypeId.SCV)
        marine = create_mock_unit(UnitTypeId.MARINE)
        barracks = create_mock_unit(UnitTypeId.BARRACKS, is_structure=True)
        self.mock_bot.units = Units([scv, marine, barracks], self.mock_bot)
        task = UnitsAnalyzer()

        # Act
        task.execute(self.analyzer, self.mock_bot)

        # Assert
        self.assertEqual(len(self.analyzer.friendly_units), 3)
        self.assertEqual(self.analyzer.friendly_structures.first, barracks)
        self.assertEqual(self.analyzer.friendly_workers.first, scv)
        self.assertEqual(self.analyzer.friendly_army_units.first, marine)

    def test_friendly_army_value_analyzer(self):
        # Arrange
        marines = [create_mock_unit(UnitTypeId.MARINE) for _ in range(2)]
        marauder = create_mock_unit(UnitTypeId.MARAUDER)
        self.analyzer.friendly_army_units = Units(marines + [marauder], self.mock_bot)

        # Mock game_data for cost calculation
        self.mock_bot.game_data.units = {
            UnitTypeId.MARINE.value: MagicMock(cost=Cost(50, 0)),
            UnitTypeId.MARAUDER.value: MagicMock(cost=Cost(100, 25)),
        }
        task = FriendlyArmyValueAnalyzer()

        # Act
        task.execute(self.analyzer, self.mock_bot)

        # Assert
        expected_value = (50 * 2) + (100 + 25)
        self.assertEqual(self.analyzer.friendly_army_value, expected_value)

    def test_enemy_army_value_analyzer(self):
        # Arrange
        zerglings = [create_mock_unit(UnitTypeId.ZERGLING) for _ in range(4)]
        self.mock_bot.enemy_units = Units(zerglings, self.mock_bot)

        self.mock_bot.game_data.units = {
            UnitTypeId.ZERGLING.value: MagicMock(cost=Cost(25, 0)),
        }
        task = EnemyArmyValueAnalyzer()

        # Act
        task.execute(self.analyzer, self.mock_bot)

        # Assert
        expected_value = 25 * 4
        self.assertEqual(self.analyzer.enemy_army_value, expected_value)

    def test_expansion_analyzer(self):
        # Arrange
        exp_locs = [Point2((10, 10)), Point2((20, 20)), Point2((30, 30))]
        self.mock_bot.expansion_locations_list = exp_locs

        # Friendly base at (10,10)
        self.mock_bot.owned_expansions = {
            exp_locs[0]: create_mock_unit(UnitTypeId.COMMANDCENTER)
        }

        # Enemy base near (30,30)
        hatch = create_mock_unit(UnitTypeId.HATCHERY, position=(30.5, 29.5))
        self.analyzer.known_enemy_townhalls = Units([hatch], self.mock_bot)

        task = ExpansionAnalyzer()

        # Act
        task.execute(self.analyzer, self.mock_bot)

        # Assert
        self.assertEqual(self.analyzer.occupied_locations, {exp_locs[0]})
        self.assertEqual(self.analyzer.enemy_occupied_locations, {exp_locs[2]})
        self.assertEqual(self.analyzer.available_expansion_locations, {exp_locs[1]})

    def test_known_enemy_townhall_analyzer(self):
        # Arrange
        hatch = create_mock_unit(UnitTypeId.HATCHERY, is_structure=True)
        spire = create_mock_unit(UnitTypeId.SPIRE, is_structure=True)
        self.analyzer.known_enemy_structures = Units([hatch, spire], self.mock_bot)
        self.mock_bot.enemy_race = Race.Zerg
        task = KnownEnemyTownhallAnalyzer()

        # Act
        task.execute(self.analyzer, self.mock_bot)

        # Assert
        self.assertEqual(len(self.analyzer.known_enemy_townhalls), 1)
        self.assertEqual(self.analyzer.known_enemy_townhalls.first, hatch)

    def test_threat_map_analyzer(self):
        # Arrange
        self.mock_bot.game_info.map_size = (100, 100)
        enemy_marine = create_mock_unit(UnitTypeId.MARINE, position=(50, 50))
        enemy_marine.radius = 0.5
        self.mock_bot.enemy_units = Units([enemy_marine], self.mock_bot)
        task = ThreatMapAnalyzer()

        # Act
        task.execute(self.analyzer, self.mock_bot)

        # Assert
        self.assertIsNotNone(self.analyzer.threat_map)
        self.assertEqual(self.analyzer.threat_map.shape, (100, 100))
        # Threat should be highest at the marine's position
        self.assertGreater(self.analyzer.threat_map[50, 50], 0)
        # Threat should be zero far away from the marine
        self.assertEqual(self.analyzer.threat_map[10, 10], 0)


class TestUnitsAnalyzerEvents(unittest.IsolatedAsyncioTestCase):
    """
    Tests the stateful event-driven logic of the UnitsAnalyzer.
    Uses IsolatedAsyncioTestCase to handle async event handlers.
    """

    async def test_units_analyzer_event_handling(self):
        # Arrange
        mock_bot = MagicMock()
        analyzer = GameAnalyzer(MagicMock())
        task = UnitsAnalyzer()

        # --- Test EnemyUnitSeen Event ---
        enemy_unit = create_mock_unit(UnitTypeId.ZERGLING, tag=123)
        seen_event = Event(
            EventType.TACTICS_ENEMY_UNIT_SEEN, EnemyUnitSeenPayload(enemy_unit)
        )

        # Act
        await task.handle_enemy_unit_seen(seen_event)
        task.execute(analyzer, mock_bot)

        # Assert
        self.assertIn(123, task._known_enemy_units)
        self.assertEqual(len(analyzer.known_enemy_units), 1)
        self.assertEqual(analyzer.known_enemy_units.first, enemy_unit)

        # --- Test UnitDestroyed Event ---
        destroyed_event = Event(
            EventType.UNIT_DESTROYED,
            UnitDestroyedPayload(123, UnitTypeId.ZERGLING, Point2((0, 0))),
        )

        # Act
        await task.handle_unit_destroyed(destroyed_event)
        task.execute(analyzer, mock_bot)

        # Assert
        self.assertNotIn(123, task._known_enemy_units)
        self.assertTrue(analyzer.known_enemy_units.empty)


if __name__ == "__main__":
    unittest.main()
