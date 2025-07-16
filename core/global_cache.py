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

from core.event_bus import EventBus
from core.game_analysis import GameAnalyzer
from core.utilities.unit_types import WORKER_TYPES, ALL_STRUCTURE_TYPES


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
        self.bot: "BotAI" | None = None

        self._analyzer = GameAnalyzer()
        self.event_bus: EventBus = EventBus()

        # --- Game State ---
        self.game_loop: int = 0

        # --- Core Resources ---
        self.minerals: int = 0
        self.vespene: int = 0
        self.supply_left: int = 0
        self.supply_cap: int = 0
        self.supply_used: int = 0

        # --- Friendly State ---
        self.friendly_units: "Units" | None = None
        self.friendly_structures: "Units" | None = None
        self.friendly_workers: "Units" | None = None
        self.friendly_army_units: "Units" | None = None
        self.idle_production_structures: "Units" | None = None
        self.friendly_upgrades: set["UpgradeId"] | None = None

        # --- Enemy State ---
        self.enemy_units: "Units" | None = None
        self.enemy_structures: "Units" | None = None
        self.known_enemy_structures: "Units" | None = None
        self.known_enemy_townhalls: "Units" | None = None

        # --- Map Information ---
        self.map_ramps: list["Ramp"] | None = None
        self.occupied_locations: set[Point2] = set()
        self.enemy_occupied_locations: set[Point2] = set()
        self.available_expansion_locations: set[Point2] = set()

        # --- Analytical Data (Populated by GameAnalyzer) ---
        self.threat_map: np.ndarray | None = None
        self.friendly_army_value: int = 0
        self.enemy_army_value: int = 0

    def update(self, game_state: "GameState", bot_object: "BotAI"):
        """
        Populates the cache with high-frequency, low-cost data from the
        current game state.
        """
        if self.bot is None:
            self._initialize_first_time(bot_object)
        self.game_loop = game_state.game_loop

        self._update_common_state(game_state)
        self._update_unit_collections(bot_object)

    def _update_common_state(self, game_state: "GameState"):
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

    def _update_unit_collections(self, bot_object: "BotAI"):
        """Updates and filters all friendly and enemy unit collections."""
        all_friendly_units = bot_object.units
        self.friendly_units = all_friendly_units
        self.friendly_structures = all_friendly_units.filter(
            lambda unit: unit.type_id in ALL_STRUCTURE_TYPES
        )
        self.friendly_workers = all_friendly_units.filter(
            lambda unit: unit.type_id in WORKER_TYPES
        )
        self.friendly_army_units = all_friendly_units.filter(
            lambda unit: unit.type_id not in ALL_STRUCTURE_TYPES
            and unit.type_id not in WORKER_TYPES
        )

        self.enemy_units = bot_object.enemy_units
        self.enemy_structures = bot_object.enemy_structures

        # Filter for idle production structures.
        production_types = {
            UnitTypeId.BARRACKS,
            UnitTypeId.FACTORY,
            UnitTypeId.STARPORT,
        }
        self.idle_production_structures = self.friendly_structures.of_type(
            production_types
        ).idle

    def _initialize_first_time(self, bot_object: "BotAI"):
        """
        Performs all one-time setup tasks for the cache and its subsystems.
        """
        # Set the persistent bot reference.
        self.bot = bot_object

        # Initialize the internal analyzer.
        self._analyzer = GameAnalyzer()

        # This data is a bot-level memory, not available on the transient game_state.
        self.map_ramps = self.bot.game_info.map_ramps
