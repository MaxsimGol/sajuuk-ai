# core/global_cache.py

from typing import TYPE_CHECKING
import numpy as np

if TYPE_CHECKING:
    from sc2.game_state import GameState
    from sc2.units import Units


class GlobalCache:
    """
    The bot's long-term, read-only memory and analytical engine.

    This class is instantiated once by the Sajuuk Conductor. Its `update`
    method is called exactly once per frame. All other components in the
    architecture treat this object as strictly read-only. It translates the
    raw game state into high-level, actionable insights.
    """

    def __init__(self):
        """
        Initializes the cache properties. These will be refreshed each frame.
        """
        # --- Fast Cache (Updated every frame) ---
        self.my_units: Units | None = None
        self.my_structures: Units | None = None
        self.enemy_units: Units | None = None
        self.enemy_structures: Units | None = None
        self.resources: dict | None = None  # Minerals, Vespene, Supply

        # --- Detailed Cache (Updated every N frames to save performance) ---
        self.threat_map: np.ndarray | None = None
        self.enemy_army_value: float = 0.0

    def update(self, game_state: GameState):
        """
        Updates the cache with the new game state. This is the ONLY place
        the cache is written to.

        :param game_state: The raw game_state object from the BotAI.
        """
        # --- Update Fast Cache every frame ---
        self._update_unit_lists(game_state)
        self._update_resources(game_state)

        # --- Update Detailed Cache periodically ---
        # Example: if game_state.game_loop % 8 == 0:
        #     self._calculate_threat_map()
        #     self._calculate_enemy_army_value()
        pass

    def _update_unit_lists(self, game_state: GameState):
        """Populates the core unit and structure lists."""
        self.my_units = game_state.units
        self.my_structures = game_state.structures
        self.enemy_units = game_state.enemy_units
        self.enemy_structures = game_state.enemy_structures

    def _update_resources(self, game_state: GameState):
        """Populates resource information."""
        self.resources = {
            "minerals": game_state.minerals,
            "vespene": game_state.vespene,
            "supply_left": game_state.supply_left,
            "supply_cap": game_state.supply_cap,
        }

    # --- Placeholder methods for future complex analysis ---
    def _calculate_threat_map(self):
        """Generates a heatmap of enemy DPS across the map."""
        pass

    def _calculate_enemy_army_value(self):
        """Calculates the total resource value of the visible enemy army."""
        pass
