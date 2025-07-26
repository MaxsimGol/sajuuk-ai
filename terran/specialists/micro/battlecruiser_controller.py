# terran/specialists/micro/battlecruiser_controller.py
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
ENGAGEMENT_RANGE = 20
YAMATO_ENERGY_COST = 125
TACTICAL_JUMP_ENERGY_COST = 75
SURVIVAL_HEALTH_THRESHOLD = 0.35  # Jump away if health drops below this

# Prioritized list of targets for Yamato Cannon.
YAMATO_TARGET_PRIORITIES: List[UnitTypeId] = [
    # Capital Ships & Super Units
    UnitTypeId.BATTLECRUISER,
    UnitTypeId.CARRIER,
    UnitTypeId.MOTHERSHIP,
    UnitTypeId.THOR,
    UnitTypeId.ULTRALISK,
    UnitTypeId.COLOSSUS,
    # High-Value Casters & Tech
    UnitTypeId.INFESTOR,
    UnitTypeId.HIGHTEMPLAR,
    UnitTypeId.SIEGETANKSIEGED,
    UnitTypeId.LURKERMPBURROWED,
]


class BattlecruiserController(ControllerABC):
    """
    Capital Ship Commander. Manages Battlecruisers to leverage their durability,
    high-impact abilities, and tactical mobility.
    """

    def execute(self, context: "MicroContext") -> Tuple[List[CommandFunctor], Set[int]]:
        """
        Executes micro-management for a squad of Battlecruisers.
        """
        # --- Unpack Context ---
        battlecruisers = context.units_to_control
        strategic_target = context.target
        cache = context.cache
        plan = context.plan

        actions: List[CommandFunctor] = []
        if not battlecruisers:
            return [], set()

        nearby_enemies = cache.enemy_units.closer_than(
            ENGAGEMENT_RANGE, battlecruisers.center
        )

        for bc in battlecruisers:
            action = self._handle_single_bc(
                bc, nearby_enemies, strategic_target, cache, plan
            )
            if action:
                actions.append(action)

        return actions, battlecruisers.tags

    def _handle_single_bc(
        self,
        bc: Unit,
        nearby_enemies: "Units",
        strategic_target: "Point2",
        cache: "GlobalCache",
        plan: "FramePlan",
    ) -> CommandFunctor | None:
        """The core decision tree for an individual Battlecruiser."""

        # 1. Survival: Tactical Jump to safety if health is critical.
        if (
            bc.health_percentage < SURVIVAL_HEALTH_THRESHOLD
            and bc.energy >= TACTICAL_JUMP_ENERGY_COST
        ):
            safe_position = plan.rally_point or self.bot.start_location
            cache.logger.warning(
                f"Battlecruiser {bc.tag} is retreating via Tactical Jump."
            )
            return lambda b=bc, p=safe_position: b(AbilityId.EFFECT_TACTICALJUMP, p)

        # 2. Ability Usage: Yamato Cannon on high-value targets.
        if bc.energy >= YAMATO_ENERGY_COST:
            yamato_target = self._find_yamato_target(bc, nearby_enemies)
            if yamato_target:
                cache.logger.info(
                    f"Battlecruiser {bc.tag} firing Yamato on {yamato_target.name}."
                )
                return lambda b=bc, t=yamato_target: b(AbilityId.YAMATO_YAMATOGUN, t)

        # 3. Target Selection: Standard attack on the best available target.
        best_target = self._find_standard_attack_target(bc, nearby_enemies)
        if best_target:
            return lambda b=bc, t=best_target: b.attack(t)

        # 4. Positioning: If no immediate threats, move towards the strategic target.
        if bc.distance_to(strategic_target) > 10:
            return lambda b=bc, t=strategic_target: b.attack(t)

        return None

    def _find_yamato_target(self, bc: Unit, nearby_enemies: "Units") -> Unit | None:
        """Finds the best target for Yamato Cannon based on the priority list."""
        # Range of Yamato Cannon is 10.
        targets_in_range = nearby_enemies.closer_than(10, bc).filter(
            lambda u: u.can_be_attacked
        )
        if not targets_in_range:
            return None

        for unit_type in YAMATO_TARGET_PRIORITIES:
            potential_targets = targets_in_range.of_type(unit_type)
            if potential_targets.exists:
                return potential_targets.closest_to(bc)

        return None

    def _find_standard_attack_target(
        self, bc: Unit, nearby_enemies: "Units", context: "MicroContext"
    ) -> Unit | None:
        """Finds the best target for regular attacks."""
        attackable_enemies = nearby_enemies.in_attack_range_of(bc).filter(
            lambda u: u.can_be_attacked
        )
        if not attackable_enemies:
            return None

        # 1. Obey focus fire command
        focus_target = context.focus_fire_target
        if focus_target and focus_target in attackable_enemies:
            return focus_target

        # 2. Fallback: Prioritize expensive units or units that can shoot back.
        high_value_targets = attackable_enemies.filter(
            lambda u: u.cost > 100 or u.can_attack_air
        )
        if high_value_targets.exists:
            return high_value_targets.closest_to(bc)

        # 3. Default: shoot the closest thing.
        return attackable_enemies.closest_to(bc)
