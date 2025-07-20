import unittest
from unittest.mock import MagicMock

import numpy as np
from sc2.units import Units

from core.global_cache import GlobalCache
from core.event_bus import EventBus


class TestGlobalCache(unittest.TestCase):
    """
    Tests the GlobalCache class to ensure it functions as a reliable,
    passive data container that is correctly updated each frame.
    """

    def setUp(self):
        """
        Create a fresh GlobalCache instance before each test.
        """
        self.cache = GlobalCache()

    def test_init_initializes_correctly(self):
        """
        Tests that a new GlobalCache instance starts with the expected default values.
        """
        # Assert core components are instantiated
        self.assertIsInstance(self.cache.event_bus, EventBus)
        self.assertIsNotNone(self.cache.logger)

        # Assert data attributes have correct default values
        self.assertIsNone(self.cache.bot)
        self.assertEqual(self.cache.game_loop, 0)
        self.assertEqual(self.cache.minerals, 0)
        self.assertEqual(self.cache.vespene, 0)
        self.assertIsNone(self.cache.friendly_units)
        self.assertEqual(self.cache.friendly_army_value, 0)
        self.assertEqual(self.cache.enemy_army_value, 0)
        self.assertEqual(self.cache.available_expansion_locations, set())

    def test_update_copies_all_attributes_from_bot_and_analyzer(self):
        """
        The primary test for GlobalCache. It verifies that the update method
        correctly copies every relevant attribute from the BotAI and GameAnalyzer
        source objects into its own state.
        """
        # Arrange: Create mock BotAI and GameAnalyzer objects with unique, testable values.
        mock_bot = MagicMock()
        mock_bot.state.game_loop = 1337
        mock_bot.minerals = 500
        mock_bot.vespene = 250
        mock_bot.supply_used = 50
        mock_bot.supply_cap = 100
        mock_bot.supply_left = 50
        mock_bot.state.upgrades = {"upgrade1", "upgrade2"}
        mock_bot.enemy_units = "mock_enemy_units"
        mock_bot.enemy_structures = "mock_enemy_structures"
        mock_bot.game_info.map_ramps = ["ramp_A", "ramp_B"]

        mock_analyzer = MagicMock()
        mock_analyzer.friendly_units = "mock_friendly_units"
        mock_analyzer.friendly_structures = "mock_friendly_structures"
        mock_analyzer.friendly_workers = "mock_friendly_workers"
        mock_analyzer.friendly_army_units = "mock_friendly_army_units"
        mock_analyzer.idle_production_structures = "mock_idle_prod_structures"
        mock_analyzer.threat_map = np.array([[1, 2], [3, 4]])
        mock_analyzer.friendly_army_value = 12345
        mock_analyzer.enemy_army_value = 54321
        mock_analyzer.known_enemy_units = "mock_known_enemies"
        mock_analyzer.known_enemy_structures = "mock_known_enemy_structs"
        mock_analyzer.known_enemy_townhalls = "mock_known_enemy_ths"
        mock_analyzer.available_expansion_locations = {"loc1", "loc2"}
        mock_analyzer.occupied_locations = {"loc3"}
        mock_analyzer.enemy_occupied_locations = {"loc4"}

        # Act: Run the update method
        self.cache.update(mock_bot, mock_analyzer)

        # Assert: Verify every single attribute was copied correctly
        # Raw Perceived State from BotAI
        self.assertEqual(self.cache.game_loop, 1337)
        self.assertEqual(self.cache.minerals, 500)
        self.assertEqual(self.cache.vespene, 250)
        self.assertEqual(self.cache.supply_used, 50)
        self.assertEqual(self.cache.supply_cap, 100)
        self.assertEqual(self.cache.supply_left, 50)
        self.assertEqual(self.cache.friendly_upgrades, {"upgrade1", "upgrade2"})
        self.assertEqual(self.cache.enemy_units, "mock_enemy_units")
        self.assertEqual(self.cache.enemy_structures, "mock_enemy_structures")
        self.assertEqual(self.cache.map_ramps, ["ramp_A", "ramp_B"])

        # Analyzed State from GameAnalyzer
        self.assertEqual(self.cache.friendly_units, "mock_friendly_units")
        self.assertEqual(self.cache.friendly_structures, "mock_friendly_structures")
        self.assertEqual(self.cache.friendly_workers, "mock_friendly_workers")
        self.assertEqual(self.cache.friendly_army_units, "mock_friendly_army_units")
        self.assertEqual(
            self.cache.idle_production_structures, "mock_idle_prod_structures"
        )
        np.testing.assert_array_equal(self.cache.threat_map, np.array([[1, 2], [3, 4]]))
        self.assertEqual(self.cache.friendly_army_value, 12345)
        self.assertEqual(self.cache.enemy_army_value, 54321)
        self.assertEqual(self.cache.known_enemy_units, "mock_known_enemies")
        self.assertEqual(self.cache.known_enemy_structures, "mock_known_enemy_structs")
        self.assertEqual(self.cache.known_enemy_townhalls, "mock_known_enemy_ths")
        self.assertEqual(self.cache.available_expansion_locations, {"loc1", "loc2"})
        self.assertEqual(self.cache.occupied_locations, {"loc3"})
        self.assertEqual(self.cache.enemy_occupied_locations, {"loc4"})

    def test_update_sets_bot_and_map_ramps_only_on_first_call(self):
        """
        Tests the special logic that the main 'bot' object and 'map_ramps' are
        only set the very first time update() is called.
        """
        # Arrange
        mock_bot_1 = MagicMock()
        mock_bot_1.game_info.map_ramps = ["initial_ramps"]
        mock_analyzer = MagicMock()

        mock_bot_2 = MagicMock()
        mock_bot_2.game_info.map_ramps = ["different_ramps"]

        # Act (First call)
        self.cache.update(mock_bot_1, mock_analyzer)

        # Assert (First call)
        self.assertIs(self.cache.bot, mock_bot_1)
        self.assertEqual(self.cache.map_ramps, ["initial_ramps"])

        # Act (Second call with a different bot object)
        self.cache.update(mock_bot_2, mock_analyzer)

        # Assert (Second call)
        # The bot object and map_ramps should NOT have been updated.
        self.assertIs(self.cache.bot, mock_bot_1)
        self.assertEqual(self.cache.map_ramps, ["initial_ramps"])


if __name__ == "__main__":
    unittest.main()
