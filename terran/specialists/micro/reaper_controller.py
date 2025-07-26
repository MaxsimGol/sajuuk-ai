# terran/specialists/micro/reaper_controller.py
from __future__ import annotations
from typing import TYPE_CHECKING, List, Set, Tuple

from sc2.ids.unit_typeid import UnitTypeId
from sc2.ids.ability_id import AbilityId
from sc2.unit import Unit
from sc2.position import Point2

from core.interfaces.controller_abc import ControllerABC
from core.types import CommandFunctor
from core.utilities.unit_types import WORKER_TYPES

if TYPE_CHECKING:
    from sc2.units import Units
    from terran.tactics.micro_context import MicroContext

# --- Tunable Constants ---
ENGAGEMENT_RANGE = 15
KITE_DISTANCE = 3.0  # Reapers are fast and should kite far
GRENADE_RANGE = 5
GRENADE_TARGET_COUNT = 2  # Use grenade on 2 or more workers/light units
RETREAT_HEALTH_THRESHOLD = 0.6  # Reapers should retreat early to heal


class ReaperController(ControllerABC):
    """
    Harassment and Scouting Specialist. Manages Reapers to exploit their high
    mobility for scouting, worker harassment, and kiting early-game units.
    """

    def execute(self, context: "MicroContext") -> Tuple[List[CommandFunctor], Set[int]]:
        """
        Executes micro-management for a squad of Reapers.
        """
        # --- Unpack Context ---
        reapers = context.units_to_control
        strategic_target = context.target
        cache = context.cache
        plan = context.plan

        actions: List[CommandFunctor] = []
        if not reapers:
            return [], set()

        nearby_enemies = cache.enemy_units.closer_than(ENGAGEMENT_RANGE, reapers.center)

        for reaper in reapers:
            action = self._handle_single_reaper(
                reaper, nearby_enemies, strategic_target, cache, plan
            )
            if action:
                actions.append(action)

        return actions, reapers.tags

    def _handle_single_reaper(
        self,
        reaper: Unit,
        nearby_enemies: "Units",
        strategic_target: "Point2",
        cache: "GlobalCache",
        plan: "FramePlan",
    ) -> CommandFunctor | None:
        """The core decision tree for an individual Reaper."""

        # 1. Survival: If health is low, retreat to a safe rally point to heal.
        if (
            reaper.health_percentage < RETREAT_HEALTH_THRESHOLD
            and nearby_enemies.exists
        ):
            retreat_position = plan.rally_point or self.bot.start_location
            return lambda r=reaper, p=retreat_position: r.move(p)

        # 2. Ability Usage: Use KD-8 Charge on valuable targets.
        if self.bot.can_cast(reaper, AbilityId.KD8CHARGE_KD8CHARGE):
            grenade_target = self._find_grenade_target(reaper, nearby_enemies)
            if grenade_target:
                cache.logger.info(f"Reaper {reaper.tag} using KD-8 Charge.")
                return lambda r=reaper, t=grenade_target: r(
                    AbilityId.KD8CHARGE_KD8CHARGE, t.position
                )

        # 3. Kiting and Engagement
        best_target = self._find_best_target(reaper, nearby_enemies)
        if best_target:
            if reaper.weapon_cooldown == 0:
                return lambda r=reaper, t=best_target: r.attack(t)
            else:
                # Always kite away from the closest enemy while reloading.
                closest_enemy = nearby_enemies.closest_to(reaper)
                kite_position = reaper.position.towards(
                    closest_enemy.position, -KITE_DISTANCE
                )
                return lambda r=reaper, p=kite_position: r.move(p)

        # 4. Positioning: No enemies, move to the strategic target.
        if reaper.distance_to(strategic_target) > 10:
            return lambda r=reaper, t=strategic_target: r.attack(t)

        return None

    def _find_best_target(self, reaper: Unit, nearby_enemies: "Units") -> Unit | None:
        """Finds the best harassment target for a Reaper."""
        # Reapers can only attack ground units.
        attackable_enemies = nearby_enemies.in_attack_range_of(reaper).filter(
            lambda u: not u.is_flying and u.can_be_attacked
        )
        if not attackable_enemies:
            return None

        # Priority 1: Workers
        workers = attackable_enemies.of_type(WORKER_TYPES)
        if workers.exists:
            return workers.closest_to(reaper)

        # Priority 2: Other light units that can't easily fight back (e.g., Queens)
        light_units = attackable_enemies.filter(lambda u: u.is_light)
        if light_units.exists:
            return light_units.closest_to(reaper)

        return None  # Avoid fighting non-light units unless necessary

    def _find_best_target(
        self, reaper: Unit, nearby_enemies: "Units", context: "MicroContext"
    ) -> Unit | None:
        """Finds the best harassment target for a Reaper."""
        attackable_enemies = nearby_enemies.in_attack_range_of(reaper).filter(
            lambda u: not u.is_flying and u.can_be_attacked
        )
        if not attackable_enemies:
            return None

        # 1. Obey focus fire command (but only if it's a valid light unit)
        focus_target = context.focus_fire_target
        if (
            focus_target
            and focus_target in attackable_enemies
            and focus_target.is_light
        ):
            return focus_target

        # 2. Fallback to specialist logic: Workers
        workers = attackable_enemies.of_type(WORKER_TYPES)
        if workers.exists:
            return workers.closest_to(reaper)

        # 3. Fallback: Other light units
        light_units = attackable_enemies.filter(lambda u: u.is_light)
        if light_units.exists:
            return light_units.closest_to(reaper)

        return None  # Avoid fighting non-light units
