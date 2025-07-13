# tests/test_core/test_global_cache.py

import unittest
from unittest.mock import Mock, PropertyMock

import numpy as np
from sc2.ids.unit_typeid import UnitTypeId
from sc2.unit import Unit


# Use a test double for the Units class to provide necessary properties.
class UnitsTestDouble(list):
    def of_type(self, type_id_set):
        """A simple mock implementation of the of_type filter."""
        return UnitsTestDouble([u for u in self if u.type_id in type_id_set])

    @property
    def structure(self):
        return UnitsTestDouble([u for u in self if u.is_structure])

    @property
    def worker(self):
        return UnitsTestDouble([u for u in self if u.is_worker])

    @property
    def not_structure(self):
        return UnitsTestDouble([u for u in self if not u.is_structure])

    @property
    def not_worker(self):
        return UnitsTestDouble([u for u in self if not u.is_worker])

    @property
    def idle(self):
        return self


class TestGlobalCache(unittest.TestCase):
    """
    Tests the GlobalCache class to ensure it passively stores data
    and correctly populates its high-frequency attributes from game_state.
    """

    def setUp(self):
        """Create a fresh cache and mock dependencies for each test."""
        from core.global_cache import GlobalCache

        self.cache = GlobalCache()

        # Mock the main bot and game state objects
        self.mock_bot = Mock()
        self.mock_game_state = Mock()

        # Mock nested properties for common state
        self.mock_bot.game_info.map_ramps = ["ramp1"]
        self.mock_bot.expansion_locations_list = ["loc1"]

        # Mock the 'common' attribute on game_state
        self.mock_game_state.common = Mock()
        self.mock_game_state.common.minerals = 50
        self.mock_game_state.common.vespene = 25
        self.mock_game_state.common.food_used = 15
        self.mock_game_state.common.food_cap = 23
        self.mock_game_state.upgrades = {"upgrade1"}

    def test_update_populates_common_state(self):
        """Verify that basic resource and supply counts are updated."""
        # Arrange
        self.mock_game_state.game_loop = 100  # Not first frame

        # Act
        self.cache.update(self.mock_game_state, self.mock_bot)

        # Assert
        self.assertEqual(self.cache.minerals, 50)
        self.assertEqual(self.cache.vespene, 25)
        self.assertEqual(self.cache.supply_used, 15)
        self.assertEqual(self.cache.supply_cap, 23)
        self.assertEqual(self.cache.supply_left, 8)  # 23 - 15
        self.assertEqual(self.cache.friendly_upgrades, {"upgrade1"})

    def test_update_populates_static_map_info_on_first_frame_only(self):
        """Verify map_ramps and expansion_locations are set only on game_loop 0."""
        # --- Frame 0 ---
        # Arrange
        self.mock_game_state.game_loop = 0

        # Act
        self.cache.update(self.mock_game_state, self.mock_bot)

        # Assert
        self.assertEqual(self.cache.map_ramps, ["ramp1"])
        self.assertEqual(self.cache.expansion_locations, ["loc1"])

        # --- Frame 1 ---
        # Arrange: Change the source data on the mock bot
        self.mock_bot.game_info.map_ramps = ["new_ramp"]
        self.mock_game_state.game_loop = 1

        # Act
        self.cache.update(self.mock_game_state, self.mock_bot)

        # Assert: The cache data should NOT have changed
        self.assertEqual(self.cache.map_ramps, ["ramp1"])

    def test_update_populates_unit_collections(self):
        """Verify that unit lists are correctly filtered and populated."""
        # Arrange
        mock_scv = Mock(spec=Unit)
        mock_scv.is_structure = False
        mock_scv.is_worker = True

        mock_marine = Mock(spec=Unit)
        mock_marine.is_structure = False
        mock_marine.is_worker = False

        mock_barracks = Mock(spec=Unit, type_id=UnitTypeId.BARRACKS)
        mock_barracks.is_structure = True
        mock_barracks.is_worker = False

        self.mock_game_state.units = UnitsTestDouble(
            [mock_scv, mock_marine, mock_barracks]
        )

        # Act
        self.cache.update(self.mock_game_state, self.mock_bot)

        # Assert
        self.assertEqual(list(self.cache.friendly_workers), [mock_scv])
        self.assertEqual(list(self.cache.friendly_army_units), [mock_marine])
        self.assertEqual(list(self.cache.friendly_structures), [mock_barracks])
        self.assertEqual(list(self.cache.idle_production_structures), [mock_barracks])

    def test_update_does_not_change_analytical_data(self):
        """Verify that update() does not touch data populated by the GameAnalyzer."""
        # Arrange
        initial_threat_map = np.zeros((1, 1))
        self.cache.threat_map = initial_threat_map
        self.cache.enemy_army_value = 5000

        # Act
        self.cache.update(self.mock_game_state, self.mock_bot)

        # Assert
        self.assertIs(self.cache.threat_map, initial_threat_map)
        self.assertEqual(self.cache.enemy_army_value, 5000)
