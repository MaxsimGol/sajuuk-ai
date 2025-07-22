# terran/tactics/positioning_manager.py
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
    from sc2.units import Units
    from core.global_cache import GlobalCache
    from core.event_bus import EventBus
    from core.frame_plan import FramePlan

# --- Tunable Positioning Constants ---
RALLY_BEHIND_DISTANCE = 8
STAGING_DISTANCE_FROM_TARGET = 25  # Increased for safety
RAMP_SEARCH_RADIUS = 15


class PositioningManager(Manager):
    """
    Battlefield Topographer.
    Provides dynamic spatial analysis for defense, rallying, and staging.
    """

    def __init__(self, bot: "BotAI"):
        super().__init__(bot)

    async def execute(
        self, cache: "GlobalCache", plan: "FramePlan", bus: "EventBus"
    ) -> List[CommandFunctor]:
        # The order of calculation matters as some positions depend on others.
        defensive_pos = self._calculate_defensive_position(cache)
        setattr(plan, "defensive_position", defensive_pos)

        staging_point = self._calculate_staging_point(cache, plan, defensive_pos)
        setattr(plan, "staging_point", staging_point)

        rally_point = self._calculate_rally_point(
            cache, plan, defensive_pos, staging_point
        )
        setattr(plan, "rally_point", rally_point)

        return []

    def _calculate_defensive_position(self, cache: "GlobalCache") -> Point2:
        """Determines the most logical choke point to defend."""
        if not self.bot.townhalls.ready:
            return self.bot.start_location

        enemy_main_base = self.bot.enemy_start_locations[0]

        # --- MODIFICATION: Find our base closest to any known enemy base for a more dynamic frontline ---
        if cache.known_enemy_townhalls and cache.known_enemy_townhalls.exists:
            frontier_base = self.bot.townhalls.ready.closest_to(
                cache.known_enemy_townhalls.center
            )
        else:
            frontier_base = self.bot.townhalls.ready.closest_to(enemy_main_base)

        try:
            ramps_near_base = [
                r
                for r in self.bot.game_info.map_ramps
                if r.bottom_center.distance_to(frontier_base.position)
                < RAMP_SEARCH_RADIUS
            ]
            if ramps_near_base:
                defensive_pos = min(
                    ramps_near_base,
                    key=lambda r: r.bottom_center.distance_to(frontier_base.position),
                ).top_center
            else:  # Fallback for bases not near a ramp
                defensive_pos = frontier_base.position.towards(
                    self.bot.start_location, 5
                )
        except (ValueError, AttributeError):
            defensive_pos = (
                frontier_base.position.towards(self.bot.start_location, 5)
                if frontier_base
                else self.bot.start_location
            )

        cache.logger.debug(f"Defensive position updated to {defensive_pos.rounded}")
        return defensive_pos

    def _calculate_staging_point(
        self, cache: "GlobalCache", plan: "FramePlan", defensive_pos: Point2
    ) -> Point2 | None:
        """Determines a forward assembly area for an impending attack."""
        if plan.army_stance != ArmyStance.AGGRESSIVE or not getattr(
            plan, "target_location", None
        ):
            return None

        attack_target = plan.target_location
        # --- MODIFICATION: Calculate staging point by moving back from the enemy towards our army. ---
        army_center = (
            cache.friendly_army_units.center
            if cache.friendly_army_units.exists
            else defensive_pos
        )

        ideal_staging_point = attack_target.towards(
            army_center, STAGING_DISTANCE_FROM_TARGET
        )

        if cache.threat_map is not None:
            safe_staging_point = find_safe_point_from_threat_map(
                cache.threat_map, reference_point=ideal_staging_point, search_radius=15
            )
        else:
            safe_staging_point = ideal_staging_point

        cache.logger.debug(f"Staging point calculated at {safe_staging_point.rounded}")
        return safe_staging_point

    def _calculate_rally_point(
        self,
        cache: "GlobalCache",
        plan: "FramePlan",
        defensive_pos: Point2,
        staging_point: Point2 | None,
    ) -> Point2:
        """Determines a safe point for newly trained units to gather."""
        front_line = (
            staging_point
            if plan.army_stance == ArmyStance.AGGRESSIVE and staging_point
            else defensive_pos
        )

        production_buildings = cache.friendly_structures.of_type(
            TERRAN_PRODUCTION_TYPES
        )
        if not production_buildings.exists:
            rear_area = self.bot.main_base_ramp.top_center
        else:
            rear_area = production_buildings.center

        ideal_rally_point = front_line.towards(rear_area, RALLY_BEHIND_DISTANCE)

        if cache.threat_map is not None:
            safe_rally = find_safe_point_from_threat_map(
                cache.threat_map, reference_point=ideal_rally_point, search_radius=10
            )
        else:
            safe_rally = ideal_rally_point

        cache.logger.debug(f"Rally point updated to {safe_rally.rounded}")
        return safe_rally
