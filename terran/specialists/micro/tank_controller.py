# terran/specialists/micro/tank_controller.py
from __future__ import annotations
from typing import TYPE_CHECKING, List, Set, Tuple

from sc2.ids.unit_typeid import UnitTypeId
from sc2.position import Point2
from sc2.unit import Unit

from core.frame_plan import ArmyStance
from core.interfaces.controller_abc import ControllerABC
from core.types import CommandFunctor
from core.utilities.geometry import find_safe_point_from_threat_map

if TYPE_CHECKING:
    from sc2.units import Units
    from terran.tactics.micro_context import MicroContext

# --- Tunable Constants ---
SIEGE_RANGE = 13
MINIMUM_RANGE = 2
SIEGE_THREAT_THRESHOLD = 3
LEAPFROG_DISTANCE = 6
SPLASH_RADIUS = 1.5
FRIENDLY_FIRE_THRESHOLD = 3


class TankController(ControllerABC):
    """
    Siege Artillery Specialist. Manages Siege Tanks with a focus on intelligent
    positioning, threat assessment, and friendly fire avoidance.
    """

    def execute(self, context: "MicroContext") -> Tuple[List[CommandFunctor], Set[int]]:
        """
        Executes micro-management for a squad of Siege Tanks.
        """
        # --- Unpack Context ---
        tanks = context.units_to_control
        cache = context.cache
        plan = context.plan
        friendly_bio = context.bio_squad or Units([], self.bot)

        actions: List[CommandFunctor] = []
        if not tanks:
            return [], set()

        nearby_enemies = cache.enemy_units.closer_than(SIEGE_RANGE + 5, tanks.center)

        for tank in tanks:
            if tank.type_id == UnitTypeId.SIEGETANKSIEGED:
                action = self._handle_sieged_tank(tank, nearby_enemies, plan)
                if action:
                    actions.append(action)
            else:  # UnitTypeId.SIEGETANK
                action = self._handle_mobile_tank(
                    tank, nearby_enemies, friendly_bio, cache, plan
                )
                if action:
                    actions.append(action)

        return actions, tanks.tags

    def _handle_sieged_tank(
        self, tank: "Unit", nearby_enemies: "Units", plan: "FramePlan"
    ) -> CommandFunctor | None:
        """Logic for a tank that is already in siege mode."""
        if self._should_unsiege(tank, nearby_enemies, plan):
            return lambda t=tank: t.unsiege()
        return None

    def _handle_mobile_tank(
        self,
        tank: "Unit",
        nearby_enemies: "Units",
        friendly_bio: "Units",
        cache: "GlobalCache",
        plan: "FramePlan",
    ) -> CommandFunctor | None:
        """Logic for a tank that is in mobile tank mode."""
        if self._should_siege(tank, nearby_enemies, friendly_bio):
            return lambda t=tank: t.siege()

        best_position = self._calculate_best_position(tank, friendly_bio, cache, plan)
        if tank.distance_to(best_position) > 3:
            return lambda t=tank, p=best_position: t.move(p)

        return None

    def _should_siege(
        self, tank: "Unit", nearby_enemies: "Units", friendly_bio: "Units"
    ) -> bool:
        """Determines if a mobile tank should transition into siege mode."""
        ground_enemies = nearby_enemies.filter(lambda u: not u.is_flying)
        if not ground_enemies:
            return False

        if ground_enemies.closer_than(MINIMUM_RANGE + 1, tank).exists:
            return False

        enemies_in_range = ground_enemies.closer_than(SIEGE_RANGE, tank)
        threat_value = sum(e.supply_cost for e in enemies_in_range)
        if threat_value < SIEGE_THREAT_THRESHOLD:
            return False

        if not self._is_safe_to_siege(tank, enemies_in_range, friendly_bio):
            return False

        return True

    def _should_unsiege(
        self, sieged_tank: "Unit", nearby_enemies: "Units", plan: "FramePlan"
    ) -> bool:
        """Determines if a sieged tank should transition back to mobile mode."""
        army_target = plan.target_location or sieged_tank.position
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
        """Performs a friendly fire check."""
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
        self,
        tank: "Unit",
        friendly_bio: "Units",
        cache: "GlobalCache",
        plan: "FramePlan",
    ) -> Point2:
        """Calculates the optimal position for a mobile tank."""
        if plan.army_stance == ArmyStance.DEFENSIVE:
            ideal_pos = plan.defensive_position or self.bot.start_location
        else:
            army_target = plan.target_location or tank.position
            if not friendly_bio.exists:
                return army_target
            bio_center = friendly_bio.center
            ideal_pos = bio_center.towards(army_target, -LEAPFROG_DISTANCE)

        if cache.threat_map is not None:
            return find_safe_point_from_threat_map(
                cache.threat_map, reference_point=ideal_pos, search_radius=5
            )
        return ideal_pos
