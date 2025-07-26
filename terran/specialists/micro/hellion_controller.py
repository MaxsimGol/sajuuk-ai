# terran/specialists/micro/hellion_controller.py
from __future__ import annotations
from typing import TYPE_CHECKING, List, Set, Tuple

from sc2.ids.unit_typeid import UnitTypeId
from sc2.ids.ability_id import AbilityId
from sc2.unit import Unit

from core.interfaces.controller_abc import ControllerABC
from core.types import CommandFunctor
from core.utilities.unit_types import WORKER_TYPES

if TYPE_CHECKING:
    from sc2.units import Units
    from terran.tactics.micro_context import MicroContext

# --- Tunable Constants ---
ENGAGEMENT_RANGE = 15
KITE_DISTANCE = 2.5
# Melee units that might justify morphing to Hellbat
MELEE_THREATS: Set[UnitTypeId] = {UnitTypeId.ZERGLING, UnitTypeId.ZEALOT}
# Minimum number of melee threats to consider morphing
HELLBAT_MORPH_THRESHOLD = 4


class HellionController(ControllerABC):
    """
    Harassment and Anti-Light Specialist. Manages Hellions and Hellbats,
    focusing on intelligent mode-switching and kiting.
    """

    def execute(self, context: "MicroContext") -> Tuple[List[CommandFunctor], Set[int]]:
        """
        Executes micro-management for Hellions and Hellbats.
        """
        # --- Unpack Context ---
        units = context.units_to_control
        strategic_target = context.target
        cache = context.cache

        actions: List[CommandFunctor] = []
        if not units:
            return [], set()

        hellions = units.of_type(UnitTypeId.HELLION)
        hellbats = units.of_type(UnitTypeId.HELLIONTANK)
        nearby_enemies = cache.enemy_units.closer_than(ENGAGEMENT_RANGE, units.center)

        for hellion in hellions:
            action = self._handle_single_hellion(
                hellion, nearby_enemies, strategic_target, cache
            )
            if action:
                actions.append(action)

        for hellbat in hellbats:
            action = self._handle_single_hellbat(
                hellbat, nearby_enemies, strategic_target
            )
            if action:
                actions.append(action)

        return actions, units.tags

    def _handle_single_hellion(
        self,
        hellion: Unit,
        nearby_enemies: "Units",
        strategic_target: "Point2",
        cache: "GlobalCache",
    ) -> CommandFunctor | None:
        """The core decision tree for a Hellion."""

        # 1. Mode Switching: Should we morph to Hellbat?
        if self._should_morph_to_hellbat(hellion, nearby_enemies, cache):
            return lambda h=hellion: h(AbilityId.MORPH_HELLBAT)

        # 2. Target Selection and Kiting
        best_target = self._find_best_target(hellion, nearby_enemies)

        if best_target:
            if hellion.weapon_cooldown == 0:
                return lambda h=hellion, t=best_target: h.attack(t)
            else:
                # Kite away from the closest threat while weapon is on cooldown
                closest_enemy = nearby_enemies.closest_to(hellion)
                kite_position = hellion.position.towards(
                    closest_enemy.position, -KITE_DISTANCE
                )
                return lambda h=hellion, p=kite_position: h.move(p)

        # 3. Positioning: No valid targets, move to the strategic target.
        if hellion.distance_to(strategic_target) > 10:
            return lambda h=hellion, t=strategic_target: h.attack(t)

        return None

    def _handle_single_hellbat(
        self,
        hellbat: Unit,
        nearby_enemies: "Units",
        strategic_target: "Point2",
    ) -> CommandFunctor | None:
        """The core decision tree for a Hellbat."""

        # 1. Mode Switching: Should we morph back to Hellion?
        if self._should_morph_to_hellion(nearby_enemies):
            return lambda h=hellbat: h(AbilityId.MORPH_HELLION)

        # 2. Engagement: Act as a frontline unit.
        attackable_enemies = nearby_enemies.filter(lambda u: not u.is_flying)
        if attackable_enemies:
            closest_enemy = attackable_enemies.closest_to(hellbat)
            return lambda h=hellbat, t=closest_enemy: h.attack(t)

        # 3. Positioning: Move to the strategic target.
        if hellbat.distance_to(strategic_target) > 3:
            return lambda h=hellbat, t=strategic_target: h.attack(t)

        return None

    def _find_best_target(
        self, hellion: Unit, nearby_enemies: "Units", context: "MicroContext"
    ) -> Unit | None:
        """Finds the best harassment target for a Hellion."""
        attackable_enemies = nearby_enemies.in_attack_range_of(hellion).filter(
            lambda u: not u.is_flying and u.can_be_attacked
        )
        if not attackable_enemies:
            return None

        # 1. Obey focus fire command IF the target is a light unit.
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
            return workers.closest_to(hellion)

        # 3. Fallback: Other light units
        light_units = attackable_enemies.filter(lambda u: u.is_light)
        if light_units.exists:
            return light_units.closest_to(hellion)

        # 4. Default: Closest enemy if no light units are available.
        return attackable_enemies.closest_to(hellion)

    def _should_morph_to_hellbat(
        self, hellion: Unit, nearby_enemies: "Units", cache: "GlobalCache"
    ) -> bool:
        """Decide if morphing to Hellbat is a good tactical choice."""
        # Must have an Armory to enable the morph.
        if not cache.friendly_structures.of_type(UnitTypeId.ARMORY).ready.exists:
            return False

        melee_threats = nearby_enemies.of_type(MELEE_THREATS).closer_than(5, hellion)

        # Morph if a significant number of melee units are swarming.
        return melee_threats.amount >= HELLBAT_MORPH_THRESHOLD

    def _should_morph_to_hellion(self, nearby_enemies: "Units") -> bool:
        """Decide if morphing back to Hellion is safe."""
        # If the immediate melee threat is gone, revert to the more mobile form.
        return not nearby_enemies.of_type(MELEE_THREATS).closer_than(6).exists
