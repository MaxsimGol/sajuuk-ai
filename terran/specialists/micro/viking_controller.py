# terran/specialists/micro/viking_controller.py
from __future__ import annotations
from typing import TYPE_CHECKING, List, Set, Tuple

from sc2.ids.unit_typeid import UnitTypeId
from sc2.ids.ability_id import AbilityId
from sc2.unit import Unit
from sc2.position import Point2

from core.interfaces.controller_abc import ControllerABC
from core.types import CommandFunctor
from terran.tactics.micro_context import MicroContext

if TYPE_CHECKING:
    from sc2.units import Units

# --- Tunable Constants ---
ENGAGEMENT_RANGE = 18
LEASH_DISTANCE = 6  # How far Vikings should stay behind the ground army.

# Priority targets in Fighter Mode (Air).
AIR_TARGET_PRIORITIES: List[UnitTypeId] = [
    UnitTypeId.COLOSSUS,  # Can be attacked by air
    UnitTypeId.BROODLORD,
    UnitTypeId.CARRIER,
    UnitTypeId.BATTLECRUISER,
    UnitTypeId.LIBERATOR,
    UnitTypeId.TEMPEST,
    UnitTypeId.VOIDRAY,
    UnitTypeId.CORRUPTOR,
    UnitTypeId.VIKINGFIGHTER,
    UnitTypeId.BANSHEE,
]
# Priority targets in Assault Mode (Ground).
GROUND_TARGET_PRIORITIES: List[UnitTypeId] = [
    UnitTypeId.SIEGETANK,
    UnitTypeId.SIEGETANKSIEGED,
    UnitTypeId.THOR,
    UnitTypeId.IMMORTAL,
]


class VikingController(ControllerABC):
    """
    Air Superiority and Anti-Mech Specialist. Manages Vikings, focusing on
    intelligent mode-switching to counter the most significant threats.
    """

    def execute(self, context: "MicroContext") -> Tuple[List[CommandFunctor], Set[int]]:
        """
        Executes micro-management for a squad of Vikings.
        """
        # --- Unpack Context ---
        vikings = context.units_to_control
        strategic_target = context.target
        cache = context.cache
        main_army = context.bio_squad or context.mech_squad or Units([], self.bot)

        actions: List[CommandFunctor] = []
        if not vikings:
            return [], set()

        nearby_enemies = cache.enemy_units.closer_than(ENGAGEMENT_RANGE, vikings.center)

        for viking in vikings:
            action = self._handle_single_viking(
                viking, nearby_enemies, strategic_target, main_army, cache
            )
            if action:
                actions.append(action)

        return actions, vikings.tags

    def _handle_single_viking(
        self,
        viking: Unit,
        nearby_enemies: "Units",
        strategic_target: "Point2",
        main_army: "Units",
        cache: "GlobalCache",
    ) -> CommandFunctor | None:
        """The core decision tree for an individual Viking."""

        # 1. Mode Switching: The most critical decision for a Viking.
        mode_switch_action = self._handle_mode_switching(viking, nearby_enemies)
        if mode_switch_action:
            return mode_switch_action

        # 2. Target Selection and Engagement.
        best_target = self._find_best_target(viking, nearby_enemies)
        if best_target:
            return lambda v=viking, t=best_target: v.attack(t)

        # 3. Positioning: Stay with the main army for support.
        if main_army.exists and viking.distance_to(main_army.center) > LEASH_DISTANCE:
            safe_position = main_army.center.towards(viking.position, -LEASH_DISTANCE)
            return lambda v=viking, p=safe_position: v.move(p)
        elif viking.distance_to(strategic_target) > 10:
            return lambda v=viking, t=strategic_target: v.attack(t)

        return None

    def _handle_mode_switching(
        self, viking: Unit, nearby_enemies: "Units"
    ) -> CommandFunctor | None:
        """Decides if the Viking should be in the air or on the ground."""

        has_air_threats = nearby_enemies.flying.exists
        has_priority_ground_threats = nearby_enemies.of_type(
            GROUND_TARGET_PRIORITIES
        ).exists

        # If in Fighter Mode (air)...
        if viking.is_flying:
            # Land if there are no air threats but there are priority ground targets.
            if not has_air_threats and has_priority_ground_threats:
                return lambda v=viking: v(AbilityId.MORPH_VIKINGASSAULTMODE)

        # If in Assault Mode (ground)...
        else:
            # Take off immediately if any air threats appear.
            if has_air_threats:
                return lambda v=viking: v(AbilityId.MORPH_VIKINGFIGHTERMODE)

        return None

    def _find_best_target(
        self, viking: Unit, nearby_enemies: "Units", context: "MicroContext"
    ) -> Unit | None:
        """Finds the highest-priority target for the Viking's current mode."""
        attackable_enemies = nearby_enemies.in_attack_range_of(viking).filter(
            lambda u: u.can_be_attacked
        )
        if not attackable_enemies:
            return None

        # 1. Obey focus fire command
        focus_target = context.focus_fire_target
        if focus_target and focus_target in attackable_enemies:
            return focus_target

        # 2. Fallback to specialist logic based on current mode
        priorities = (
            AIR_TARGET_PRIORITIES if viking.is_flying else GROUND_TARGET_PRIORITIES
        )
        for unit_type in priorities:
            potential_targets = attackable_enemies.of_type(unit_type)
            if potential_targets.exists:
                return potential_targets.closest_to(viking)

        # 3. Default: attack the closest valid enemy.
        return attackable_enemies.closest_to(viking)
