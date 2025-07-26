# terran/specialists/micro/cyclone_controller.py
from __future__ import annotations
from typing import TYPE_CHECKING, List, Set, Tuple

from sc2.ids.unit_typeid import UnitTypeId
from sc2.ids.ability_id import AbilityId
from sc2.unit import Unit

from core.interfaces.controller_abc import ControllerABC
from core.types import CommandFunctor

if TYPE_CHECKING:
    from sc2.units import Units
    from terran.tactics.micro_context import MicroContext

# --- Tunable Constants ---
# How far a Cyclone will look for a target to Lock On to.
LOCK_ON_ACQUISITION_RANGE = 12
# How far to kite back while Lock On is active.
KITE_DISTANCE = 3

# Priority targets for the Lock On ability.
LOCK_ON_TARGET_PRIORITIES: List[UnitTypeId] = [
    # High-value Air
    UnitTypeId.BATTLECRUISER,
    UnitTypeId.CARRIER,
    UnitTypeId.MOTHERSHIP,
    UnitTypeId.BROODLORD,
    UnitTypeId.LIBERATOR,
    UnitTypeId.TEMPEST,
    # High-value Ground
    UnitTypeId.SIEGETANK,
    UnitTypeId.SIEGETANKSIEGED,
    UnitTypeId.THOR,
    UnitTypeId.ULTRALISK,
    UnitTypeId.COLOSSUS,
    UnitTypeId.IMMORTAL,
    # Other threatening units
    UnitTypeId.BANSHEE,
    UnitTypeId.RAVEN,
    UnitTypeId.VIKINGFIGHTER,
    UnitTypeId.CORRUPTOR,
    UnitTypeId.VOIDRAY,
]


class CycloneController(ControllerABC):
    """
    Skirmisher Specialist. Manages Cyclones to maximize the use of their
    Lock On ability while kiting to survive.
    """

    def execute(self, context: "MicroContext") -> Tuple[List[CommandFunctor], Set[int]]:
        """
        Executes micro-management for a squad of Cyclones.
        """
        # --- Unpack Context ---
        cyclones = context.units_to_control
        strategic_target = context.target
        cache = context.cache

        actions: List[CommandFunctor] = []
        if not cyclones:
            return [], set()

        nearby_enemies = cache.enemy_units.closer_than(
            LOCK_ON_ACQUISITION_RANGE + 5, cyclones.center
        )

        for cyclone in cyclones:
            action = self._handle_single_cyclone(
                cyclone, nearby_enemies, strategic_target, cache
            )
            if action:
                actions.append(action)

        return actions, cyclones.tags

    def _handle_single_cyclone(
        self,
        cyclone: Unit,
        nearby_enemies: "Units",
        strategic_target: "Point2",
        context: "MicroContext",  # Add context here
    ) -> CommandFunctor | None:
        """The core decision tree for an individual Cyclone."""

        # (Kiting logic remains the same)
        # ...

        # (Ability Usage for Lock On remains the same)
        if self.bot.can_cast(cyclone, AbilityId.LOCKON_LOCKON):
            lock_on_target = self._find_lock_on_target(cyclone, nearby_enemies)
            if lock_on_target:
                # ...
                return lambda c=cyclone, t=lock_on_target: c(AbilityId.LOCKON_LOCKON, t)

        # 3. Standard Engagement: Use the new unified targeting logic
        best_target = self._find_best_standard_target(cyclone, nearby_enemies, context)
        if best_target:
            return lambda c=cyclone, t=best_target: c.attack(t)

        # (Positioning logic remains the same)
        # ...

    def _find_best_standard_target(
        self, cyclone: Unit, nearby_enemies: "Units", context: "MicroContext"
    ) -> Unit | None:
        """Finds the best target for the Cyclone's standard auto-attack."""
        attackable_enemies = nearby_enemies.in_attack_range_of(cyclone).filter(
            lambda u: u.can_be_attacked
        )
        if not attackable_enemies:
            return None

        # 1. Obey focus fire command
        focus_target = context.focus_fire_target
        if focus_target and focus_target in attackable_enemies:
            return focus_target

        # 2. Fallback: Prioritize armored targets
        armored_targets = attackable_enemies.filter(lambda u: u.is_armored)
        if armored_targets.exists:
            return armored_targets.closest_to(cyclone)

        # 3. Default: Closest enemy
        return attackable_enemies.closest_to(cyclone)
