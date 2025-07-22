from __future__ import annotations
from typing import TYPE_CHECKING, List, Set, Tuple

from sc2.ids.unit_typeid import UnitTypeId
from sc2.position import Point2

from core.frame_plan import ArmyStance
from core.types import CommandFunctor
from core.utilities.geometry import find_safe_point_from_threat_map

if TYPE_CHECKING:
    from sc2.unit import Unit
    from sc2.units import Units
    from core.global_cache import GlobalCache

# --- Tunable Constants for Tank Behavior ---
SIEGE_RANGE = 13
MINIMUM_RANGE = 2
SIEGE_THREAT_THRESHOLD = 3  # Min enemy supply in range to consider sieging.
LEAPFROG_DISTANCE = 6  # How far behind the bio ball tanks should stay.
SPLASH_RADIUS = 1.5  # Estimated splash radius for friendly fire check.
FRIENDLY_FIRE_THRESHOLD = 3  # Don't siege if it would splash this many friendlies.

BIO_UNIT_TYPES = {
    UnitTypeId.MARINE,
    UnitTypeId.MARAUDER,
    UnitTypeId.REAPER,
    UnitTypeId.GHOST,
}


class TankController:
    """
    Siege Artillery Specialist.

    This advanced controller manages Siege Tanks with a focus on intelligent
    positioning, threat assessment, and friendly fire avoidance.
    """

    def execute(
        self, tanks: "Units", target: Point2, cache: "GlobalCache"
    ) -> Tuple[List[CommandFunctor], Set[int]]:
        """
        Executes micro-management for a squad of Siege Tanks.

        :param tanks: The Units object of tanks to be controlled.
        :param target: The high-level target position from the ArmyControlManager.
        :param cache: The global cache for accessing game state.
        :return: A tuple containing (list of command functors, set of handled unit tags).
        """
        actions: List[CommandFunctor] = []
        if not tanks:
            return [], set()

        nearby_enemies = cache.enemy_units.closer_than(SIEGE_RANGE + 5, tanks.center)
        friendly_bio = cache.friendly_army_units.of_type(BIO_UNIT_TYPES)

        for tank in tanks:
            if tank.type_id == UnitTypeId.SIEGETANKSIEGED:
                actions.extend(self._handle_sieged_tank(tank, nearby_enemies, cache))
            else:  # UnitTypeId.SIEGETANK
                actions.extend(
                    self._handle_mobile_tank(tank, nearby_enemies, friendly_bio, cache)
                )

        # This controller provides a command (or a decision not to act) for every tank.
        return actions, tanks.tags

    def _handle_sieged_tank(
        self, tank: "Unit", nearby_enemies: "Units", cache: "GlobalCache"
    ) -> List[CommandFunctor]:
        """Logic for a tank that is already in siege mode."""
        if self._should_unsiege(tank, nearby_enemies, cache):
            return [lambda t=tank: t.unsiege()]
        # If it shouldn't unsiege, do nothing. The game's auto-targeting is efficient.
        return []

    def _handle_mobile_tank(
        self,
        tank: "Unit",
        nearby_enemies: "Units",
        friendly_bio: "Units",
        cache: "GlobalCache",
    ) -> List[CommandFunctor]:
        """Logic for a tank that is in mobile tank mode."""
        # 1. Check if we should siege at our current location.
        if self._should_siege(tank, nearby_enemies, friendly_bio):
            return [lambda t=tank: t.siege()]

        # 2. If not sieging, calculate the best position to move to.
        best_position = self._calculate_best_position(tank, friendly_bio, cache)

        # 3. Only issue a move command if we are not already close to the target position.
        if tank.distance_to(best_position) > 3:
            return [lambda t=tank, p=best_position: t.move(p)]

        return []

    def _should_siege(
        self, tank: "Unit", nearby_enemies: "Units", friendly_bio: "Units"
    ) -> bool:
        """Determines if a mobile tank should transition into siege mode."""
        ground_enemies = nearby_enemies.filter(lambda u: not u.is_flying)
        if not ground_enemies:
            return False

        # Do not siege if dangerous units are already inside the minimum range.
        if ground_enemies.closer_than(MINIMUM_RANGE + 1, tank).exists:
            return False

        # Only consider sieging if there is a significant threat in range.
        enemies_in_range = ground_enemies.closer_than(SIEGE_RANGE, tank)
        threat_value = sum(e.supply_cost for e in enemies_in_range)
        if threat_value < SIEGE_THREAT_THRESHOLD:
            return False

        # CRITICAL: Check for friendly fire before committing.
        if not self._is_safe_to_siege(tank, enemies_in_range, friendly_bio):
            return False

        return True

    def _should_unsiege(
        self, sieged_tank: "Unit", nearby_enemies: "Units", cache: "GlobalCache"
    ) -> bool:
        """Determines if a sieged tank should transition back to mobile mode."""
        army_target = getattr(cache.frame_plan, "target_location", sieged_tank.position)
        if sieged_tank.distance_to(army_target) > SIEGE_RANGE + 5:
            return True

        ground_enemies = nearby_enemies.filter(lambda u: not u.is_flying)

        if ground_enemies.closer_than(MINIMUM_RANGE, sieged_tank).amount >= 2:
            return True

        if not ground_enemies.closer_than(SIEGE_RANGE, sieged_tank).exists:
            return True

        return False

    def _is_safe_to_siege(
        self, tank: "Unit", enemies_in_range: "Units", friendly_bio: "Units"
    ) -> bool:
        """
        Performs a friendly fire check. Returns False if sieging is likely to
        cause significant damage to our own units.
        """
        if not friendly_bio.exists:
            return True

        for enemy in enemies_in_range:
            friendlies_in_splash_zone = friendly_bio.closer_than(
                SPLASH_RADIUS, enemy.position
            ).amount
            if friendlies_in_splash_zone >= FRIENDLY_FIRE_THRESHOLD:
                return False

        return True

    def _calculate_best_position(
        self, tank: "Unit", friendly_bio: "Units", cache: "GlobalCache"
    ) -> Point2:
        """
        Calculates the optimal position for a mobile tank based on army stance and threat.
        """
        stance = cache.frame_plan.army_stance
        army_target = getattr(cache.frame_plan, "target_location", tank.position)

        if stance == ArmyStance.DEFENSIVE:
            ideal_pos = getattr(
                cache.frame_plan, "defensive_position", self.bot.start_location
            )
        else:  # AGGRESSIVE or HARASS
            if not friendly_bio.exists:
                return army_target

            bio_center = friendly_bio.center
            ideal_pos = bio_center.towards(army_target, -LEAPFROG_DISTANCE)

        # Refine the ideal position by finding the safest nearby point using the threat map.
        safe_position = find_safe_point_from_threat_map(
            cache.threat_map, reference_point=ideal_pos, search_radius=5
        )
        return safe_position
