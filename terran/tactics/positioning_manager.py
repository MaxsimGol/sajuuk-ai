from __future__ import annotations
from typing import TYPE_CHECKING, List

from sc2.position import Point2

from core.frame_plan import ArmyStance
from core.interfaces.manager_abc import Manager
from core.types import CommandFunctor
from core.utilities.geometry import find_safe_point_from_threat_map
from core.utilities.unit_types import TERRAN_PRODUCTION_TYPES

if TYPE_CHECKING:
    from sc2.bot_ai import BotAI
    from sc2.game_info import Ramp
    from core.global_cache import GlobalCache
    from core.event_bus import EventBus
    from core.frame_plan import FramePlan


class PositioningManager(Manager):
    """
    Battlefield Topographer.

    This is a "service" manager that performs dynamic spatial analysis. It uses the
    threat map and knowledge of base locations to identify the most strategically
    sound locations for defense, rallying, and staging on a frame-by-frame basis.
    """

    def __init__(self, bot: "BotAI"):
        super().__init__(bot)

    async def execute(
        self, cache: "GlobalCache", plan: "FramePlan", bus: "EventBus"
    ) -> List[CommandFunctor]:
        """
        Analyzes the map and writes key tactical positions to the FramePlan.
        """
        self._calculate_defensive_position(cache, plan)
        self._calculate_rally_point(cache, plan)
        self._calculate_staging_point(cache, plan)

        # This is a service manager; its job is analysis, not action.
        return []

    def _calculate_defensive_position(self, cache: "GlobalCache", plan: "FramePlan"):
        """
        Determines the most logical choke point to defend. This is typically the
        ramp of our forward-most expansion.
        """
        if not self.bot.townhalls.ready:
            setattr(plan, "defensive_position", self.bot.start_location)
            return

        # Find the forward-most base (closest to the enemy).
        enemy_start = self.bot.enemy_start_locations[0]
        forward_base = self.bot.townhalls.ready.closest_to(enemy_start)

        # Find the ramp associated with this base.
        # A ramp's "bottom_center" is on the low ground.
        try:
            associated_ramp = min(
                self.bot.game_info.map_ramps,
                key=lambda ramp: ramp.bottom_center.distance_to(forward_base.position),
            )
            defensive_pos = associated_ramp.top_center
        except ValueError:
            # Fallback for maps with no ramps (e.g., flat maps).
            defensive_pos = forward_base.position.towards(enemy_start, -5)

        setattr(plan, "defensive_position", defensive_pos)
        cache.logger.debug(f"Defensive position updated to {defensive_pos.rounded}")

    def _calculate_rally_point(self, cache: "GlobalCache", plan: "FramePlan"):
        """
        Determines a safe point for newly trained units to gather. This point should
        be near our production but away from known threats.
        """
        production_buildings = cache.friendly_structures.of_type(
            TERRAN_PRODUCTION_TYPES
        )
        if not production_buildings:
            # If no production, rally at the defensive position.
            setattr(plan, "rally_point", getattr(plan, "defensive_position"))
            return

        # Calculate the center of our production infrastructure.
        production_center = production_buildings.center

        # Use the threat map to find the safest spot near our production center.
        safe_rally = find_safe_point_from_threat_map(
            cache.threat_map, reference_point=production_center, search_radius=15
        )
        setattr(plan, "rally_point", safe_rally)
        cache.logger.debug(f"Rally point updated to {safe_rally.rounded}")

    def _calculate_staging_point(self, cache: "GlobalCache", plan: "FramePlan"):
        """
        Determines a forward assembly area for an impending attack. This should
        be close to the enemy, but in a low-threat area.
        """
        if plan.army_stance != ArmyStance.AGGRESSIVE:
            setattr(plan, "staging_point", None)
            return

        # Determine the enemy's likely forward position.
        if cache.known_enemy_townhalls.exists:
            enemy_front = cache.known_enemy_townhalls.closest_to(
                self.bot.start_location
            )
        else:
            enemy_front = self.bot.enemy_start_locations[0]

        # Define a point roughly halfway between our main ramp and the enemy front.
        # This gives us a reference area to search for a safe spot.
        midpoint = self.bot.main_base_ramp.top_center.towards(
            enemy_front,
            self.bot.main_base_ramp.top_center.distance_to(enemy_front) * 0.75,
        )

        # Use the threat map to find the safest spot within that forward area.
        safe_staging_point = find_safe_point_from_threat_map(
            cache.threat_map, reference_point=midpoint, search_radius=25
        )
        setattr(plan, "staging_point", safe_staging_point)
        cache.logger.debug(f"Staging point calculated at {safe_staging_point.rounded}")
