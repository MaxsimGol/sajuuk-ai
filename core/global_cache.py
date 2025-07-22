# core/global_cache.py

from __future__ import annotations
from typing import TYPE_CHECKING
import numpy as np
from sc2.ids.upgrade_id import UpgradeId
from sc2.ids.unit_typeid import UnitTypeId
from sc2.units import Units

if TYPE_CHECKING:
    from sc2.bot_ai import BotAI
    from sc2.game_info import Ramp
    from sc2.position import Point2
    from core.game_analysis import GameAnalyzer

from core.event_bus import EventBus
from core.logger import logger


class GlobalCache:
    """
    A passive data container for the bot's "world state" on a single frame.
    It is populated once per frame by the Sajuuk conductor.
    """

    def __init__(self):
        self.logger = logger
        self.event_bus: EventBus = EventBus(self.logger)

        # Raw Perceived State
        self.bot: "BotAI" | None = None
        self.game_loop: int = 0
        self.iteration: int = 0
        self.minerals: int = 0
        self.vespene: int = 0
        self.supply_left: int = 0
        self.supply_cap: int = 0
        self.supply_used: int = 0
        self.friendly_upgrades: set["UpgradeId"] = set()
        self.enemy_units: "Units" | None = None  # Can be None if no bot object yet
        self.enemy_structures: "Units" | None = None  # Can be None if no bot object yet
        self.map_ramps: list["Ramp"] | None = None

        # Analyzed State (Copied from GameAnalyzer)
        # MODIFICATION: Initialize with empty values, will be populated on first update
        self.friendly_units: "Units" | None = None
        self.friendly_structures: "Units" | None = None
        self.friendly_workers: "Units" | None = None
        self.friendly_army_units: "Units" | None = None
        self.idle_production_structures: "Units" | None = None
        self.threat_map: np.ndarray | None = None
        self.base_is_under_attack: bool = False
        self.threat_location: "Point2" | None = None
        self.friendly_army_value: int = 0
        self.enemy_army_value: int = 0
        self.known_enemy_units: "Units" | None = None
        self.known_enemy_structures: "Units" | None = None
        self.known_enemy_townhalls: "Units" | None = None
        self.available_expansion_locations: set[Point2] = set()
        self.occupied_locations: set[Point2] = set()
        self.enemy_occupied_locations: set[Point2] = set()

    def update(self, bot: "BotAI", analyzer: "GameAnalyzer", iteration: int):
        """Populates the cache from the raw bot state and the GameAnalyzer."""
        if self.bot is None:
            self.bot = bot
            self.map_ramps = self.bot.game_info.map_ramps
            # Initialize empty units objects here where 'bot' is available
            self.friendly_units = Units([], bot)
            self.friendly_structures = Units([], bot)
            self.friendly_workers = Units([], bot)
            self.friendly_army_units = Units([], bot)
            self.idle_production_structures = Units([], bot)
            self.known_enemy_units = Units([], bot)
            self.known_enemy_structures = Units([], bot)
            self.known_enemy_townhalls = Units([], bot)
            self.enemy_units = Units([], bot)
            self.enemy_structures = Units([], bot)

        # --- Copy Raw Perceived State ---
        self.game_loop = bot.state.game_loop
        self.iteration = iteration
        self.minerals = bot.minerals
        self.vespene = bot.vespene
        self.supply_used = bot.supply_used
        self.supply_cap = bot.supply_cap
        self.supply_left = bot.supply_left
        self.friendly_upgrades = bot.state.upgrades
        self.enemy_units = bot.enemy_units
        self.enemy_structures = bot.enemy_structures

        # --- Copy Final Analyzed State ---
        self.friendly_units = analyzer.friendly_units
        self.friendly_structures = analyzer.friendly_structures
        self.friendly_workers = analyzer.friendly_workers
        self.friendly_army_units = analyzer.friendly_army_units
        self.idle_production_structures = analyzer.idle_production_structures
        self.threat_map = analyzer.threat_map
        self.base_is_under_attack = getattr(analyzer, "base_is_under_attack", False)
        self.threat_location = getattr(analyzer, "threat_location", None)
        self.friendly_army_value = analyzer.friendly_army_value
        self.enemy_army_value = analyzer.enemy_army_value
        self.known_enemy_units = analyzer.known_enemy_units
        self.known_enemy_structures = analyzer.known_enemy_structures
        self.known_enemy_townhalls = analyzer.known_enemy_townhalls
        self.available_expansion_locations = analyzer.available_expansion_locations
        self.occupied_locations = analyzer.occupied_locations
        self.enemy_occupied_locations = analyzer.enemy_occupied_locations
