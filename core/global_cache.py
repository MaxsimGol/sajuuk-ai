# core/global_cache.py

from __future__ import annotations
from typing import TYPE_CHECKING

import numpy as np
from sc2.ids.upgrade_id import UpgradeId
from sc2.ids.unit_typeid import UnitTypeId

if TYPE_CHECKING:
    from sc2.bot_ai import BotAI
    from sc2.game_state import GameState
    from sc2.units import Units
    from sc2.game_info import Ramp
    from sc2.position import Point2


class GlobalCache:
    """
    A passive data container for the bot's "world state" on a single frame.

    This class is the definitive, read-only source of truth for all other
    components during a game step. It is intentionally "dumb" and contains
    no complex logic. Its attributes are populated by two external sources:
    1.  High-frequency data is populated by this class's own `update` method.
    2.  Low-frequency, expensive analysis (like threat maps) is calculated by
        the `GameAnalyzer` and written into this cache's attributes.
    """

    def __init__(self):
        # --- Bot Object Reference ---
        self.bot: BotAI | None = None

        # --- Game State ---
        self.game_loop: int = 0

        # --- Core Resources ---
        self.minerals: int = 0
        self.vespene: int = 0
        self.supply_left: int = 0
        self.supply_cap: int = 0
        self.supply_used: int = 0

        # --- Friendly State ---
        self.friendly_units: Units | None = None
        self.friendly_structures: Units | None = None
        self.friendly_workers: Units | None = None
        self.friendly_army_units: Units | None = None
        self.idle_production_structures: Units | None = None
        self.friendly_upgrades: set[UpgradeId] | None = None

        # --- Enemy State ---
        self.enemy_units: Units | None = None
        self.enemy_structures: Units | None = None
        self.known_enemy_structures: Units | None = None

        # --- Map Information ---
        self.map_ramps: list[Ramp] | None = None
        self.expansion_locations: list[Point2] | None = None

        # --- Analytical Data (Populated by GameAnalyzer) ---
        self.threat_map: np.ndarray | None = None
        self.friendly_army_value: int = 0
        self.enemy_army_value: int = 0

    def update(self, game_state: GameState, bot_object: BotAI):
        """
        Populates the cache with high-frequency, low-cost data from the
        current game state.
        """
        self.bot = bot_object
        self.game_loop = game_state.game_loop

        self._update_common_state(game_state)
        self._update_unit_collections(game_state)

    def _update_common_state(self, game_state: GameState):
        """Updates simple, high-frequency state attributes from the game_state."""
        self.minerals = game_state.common.minerals
        self.vespene = game_state.common.vespene
        self.supply_used = game_state.common.food_used
        self.supply_cap = game_state.common.food_cap
        self.supply_left = self.supply_cap - self.supply_used
        self.friendly_upgrades = game_state.upgrades

        # Static map info is populated only once at the start of the game.
        if self.game_loop == 0:
            self.map_ramps = self.bot.game_info.map_ramps
            self.expansion_locations = self.bot.expansion_locations_list

    def _update_unit_collections(self, game_state: GameState):
        """Updates and filters all friendly and enemy unit collections."""
        all_friendly_units = game_state.units

        self.friendly_units = all_friendly_units
        self.friendly_structures = all_friendly_units.structure
        self.friendly_workers = all_friendly_units.worker
        self.friendly_army_units = all_friendly_units.not_structure.not_worker

        self.enemy_units = game_state.enemy_units
        self.enemy_structures = game_state.enemy_structures

        # This data is a bot-level memory, not available on the transient game_state.
        self.known_enemy_structures = self.bot.known_enemy_structures

        # Filter for idle production structures.
        production_types = {
            UnitTypeId.BARRACKS,
            UnitTypeId.FACTORY,
            UnitTypeId.STARPORT,
        }
        self.idle_production_structures = self.friendly_structures.of_type(
            production_types
        ).idle
