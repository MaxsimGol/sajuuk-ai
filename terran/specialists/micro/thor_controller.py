# terran/specialists/micro/thor_controller.py
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
# Minimum number of light air units to justify switching to AA splash mode.
AA_MODE_SWITCH_THRESHOLD = 4

# Units vulnerable to the Thor's anti-air splash attack.
LIGHT_AIR_UNITS: Set[UnitTypeId] = {UnitTypeId.MUTALISK, UnitTypeId.PHOENIX}
# Priority targets for the Thor's high-damage single-target attacks.
THOR_TARGET_PRIORITIES: List[UnitTypeId] = [
    # Massive Air
    UnitTypeId.BATTLECRUISER,
    UnitTypeId.CARRIER,
    UnitTypeId.BROODLORD,
    UnitTypeId.TEMPEST,
    # Massive Ground
    UnitTypeId.ULTRALISK,
    UnitTypeId.COLOSSUS,
    UnitTypeId.THOR,
    # High-Value Air
    UnitTypeId.LIBERATOR,
    UnitTypeId.CORRUPTOR,
    UnitTypeId.VOIDRAY,
]


class ThorController(ControllerABC):
    """
    Heavy Assault Specialist. Manages Thors to act as a durable anchor for the
    army, prioritizing massive targets and switching attack modes intelligently.
    """

    def execute(self, context: "MicroContext") -> Tuple[List[CommandFunctor], Set[int]]:
        """
        Executes micro-management for a squad of Thors.
        """
        # --- Unpack Context ---
        thors = context.units_to_control
        strategic_target = context.target
        cache = context.cache
        main_army = context.bio_squad or context.mech_squad or Units([], self.bot)

        actions: List[CommandFunctor] = []
        if not thors:
            return [], set()

        nearby_enemies = cache.enemy_units.closer_than(ENGAGEMENT_RANGE, thors.center)

        for thor in thors:
            action = self._handle_single_thor(
                thor, nearby_enemies, strategic_target, main_army
            )
            if action:
                actions.append(action)

        return actions, thors.tags

    def _handle_single_thor(
        self,
        thor: Unit,
        nearby_enemies: "Units",
        strategic_target: "Point2",
        main_army: "Units",
    ) -> CommandFunctor | None:
        """The core decision tree for an individual Thor."""

        # 1. Mode Switching: Choose the correct weapon system.
        mode_switch_action = self._handle_mode_switching(thor, nearby_enemies)
        if mode_switch_action:
            return mode_switch_action

        # 2. Target Selection and Engagement.
        best_target = self._find_best_target(thor, nearby_enemies)
        if best_target:
            return lambda t=thor, tgt=best_target: t.attack(tgt)

        # 3. Positioning: Stay with the main army.
        if main_army.exists and thor.distance_to(main_army.center) > 5:
            return lambda t=thor, p=main_army.center: t.move(p)
        elif thor.distance_to(strategic_target) > 8:
            return lambda t=thor, tgt=strategic_target: t.attack(tgt)

        return None

    def _handle_mode_switching(
        self, thor: Unit, nearby_enemies: "Units"
    ) -> CommandFunctor | None:
        """Decides if the Thor should switch between its attack modes."""

        # Check if we should switch to anti-air splash mode.
        if thor.type_id == UnitTypeId.THOR:
            if self._should_switch_to_aa_mode(thor, nearby_enemies):
                return lambda t=thor: t(AbilityId.MORPH_THORHIGHIMPACTMODE)

        # Check if we should switch back to standard high-impact mode.
        elif thor.type_id == UnitTypeId.THORAP:
            if not self._should_switch_to_aa_mode(thor, nearby_enemies):
                return lambda t=thor: t(AbilityId.MORPH_THOREXPLOSIVEMODE)

        return None

    def _should_switch_to_aa_mode(self, thor: Unit, nearby_enemies: "Units") -> bool:
        """
        Returns True if there is a significant clump of light air units that
        would be vulnerable to the Thor's splash damage.
        """
        light_air_threats = nearby_enemies.of_type(LIGHT_AIR_UNITS).closer_than(
            10, thor
        )

        if light_air_threats.amount >= AA_MODE_SWITCH_THRESHOLD:
            # Check if they are clumped up
            if light_air_threats.center.distance_to_closest(light_air_threats) < 3:
                return True
        return False


def _find_best_target(
    self, thor: Unit, nearby_enemies: "Units", context: "MicroContext"
) -> Unit | None:
    """Finds the highest-priority target for the Thor."""
    attackable_enemies = nearby_enemies.in_attack_range_of(thor).filter(
        lambda u: u.can_be_attacked
    )
    if not attackable_enemies:
        return None

    # 1. Obey focus fire command
    focus_target = context.focus_fire_target
    if focus_target and focus_target in attackable_enemies:
        return focus_target

    # 2. Fallback to specialist logic: high-value massive units
    for unit_type in THOR_TARGET_PRIORITIES:
        potential_targets = attackable_enemies.of_type(unit_type)
        if potential_targets.exists:
            return potential_targets.closest_to(thor)

    # 3. Default: attack the most expensive unit in range.
    return max(attackable_enemies, key=lambda u: u.cost, default=None)
