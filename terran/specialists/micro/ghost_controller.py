# terran/specialists/micro/ghost_controller.py
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
ENGAGEMENT_RANGE = 15
SNIPE_ENERGY_COST = 50
EMP_ENERGY_COST = 75
CLOAK_MIN_ENERGY = 80  # Cloak only if energy is high, to save for spells.
SURVIVAL_HEALTH_THRESHOLD = 0.5

# Priority targets for Steady Targeting (Snipe).
SNIPE_TARGET_PRIORITIES: List[UnitTypeId] = [
    UnitTypeId.ULTRALISK,
    UnitTypeId.BROODLORD,
    UnitTypeId.INFESTOR,
    UnitTypeId.LURKERMP,
    UnitTypeId.LURKERMPBURROWED,
    UnitTypeId.RAVAGER,
    UnitTypeId.HYDRALISK,
    UnitTypeId.BANELING,
    UnitTypeId.GHOST,
]

# Units that are high-priority targets for EMP.
EMP_TARGET_PRIORITIES: Set[UnitTypeId] = {
    UnitTypeId.HIGHTEMPLAR,
    UnitTypeId.SENTRY,
    UnitTypeId.ARCHON,
    UnitTypeId.ORACLE,
    UnitTypeId.SHIELDBATTERY,
    UnitTypeId.INFESTOR,
    UnitTypeId.QUEEN,
    UnitTypeId.MEDIVAC,
    UnitTypeId.BATTLECRUISER,
    UnitTypeId.RAVEN,
}


class GhostController(ControllerABC):
    """
    Special Operations Agent. Manages Ghosts to neutralize high-value targets
    and cripple enemy armies with EMP and Snipe.
    """

    def execute(self, context: "MicroContext") -> Tuple[List[CommandFunctor], Set[int]]:
        """
        Executes micro-management for a squad of Ghosts.
        """
        # --- Unpack Context ---
        ghosts = context.units_to_control
        strategic_target = context.target
        cache = context.cache

        actions: List[CommandFunctor] = []
        if not ghosts:
            return [], set()

        nearby_enemies = cache.enemy_units.closer_than(ENGAGEMENT_RANGE, ghosts.center)

        for ghost in ghosts:
            action = self._handle_single_ghost(
                ghost, nearby_enemies, strategic_target, cache
            )
            if action:
                actions.append(action)

        return actions, ghosts.tags

    def _handle_single_ghost(
        self,
        ghost: Unit,
        nearby_enemies: "Units",
        strategic_target: "Point2",
        context: "MicroContext",  # Add context
    ) -> CommandFunctor | None:
        """The core decision tree for an individual Ghost."""

        # (Survival logic is unchanged)
        # ...

        # 2. Ability Usage: Prioritize spells over standard attacks.
        spell_action = self._use_spells(ghost, nearby_enemies, context.cache)
        if spell_action:
            return spell_action

        # (Cloak Management is unchanged)
        # ...

        # 4. Standard Attack: If no spell was cast, use regular attack with focus fire.
        attackable_enemies = nearby_enemies.in_attack_range_of(ghost)
        if attackable_enemies:
            target = context.focus_fire_target or attackable_enemies.closest_to(ghost)
            if target in attackable_enemies:
                return lambda g=ghost, t=target: g.attack(t)
            # If focus target is not in range, attack closest available
            return lambda g=ghost, t=attackable_enemies.closest_to(g): g.attack(t)

        # (Positioning logic is unchanged)
        # ...

        return None

    def _use_spells(
        self, ghost: Unit, nearby_enemies: "Units", cache: "GlobalCache"
    ) -> CommandFunctor | None:
        """Selects and executes the best spell for the current situation."""

        # Priority 1: EMP against high-value clumps
        if ghost.energy >= EMP_ENERGY_COST:
            emp_target_point = self._find_best_emp_target(ghost, nearby_enemies)
            if emp_target_point:
                cache.logger.info(
                    f"Ghost {ghost.tag} firing EMP at {emp_target_point.rounded}."
                )
                return lambda g=ghost, p=emp_target_point: g(AbilityId.EMP_EMP, p)

        # Priority 2: Snipe high-priority biological targets
        if ghost.energy >= SNIPE_ENERGY_COST and self.bot.can_cast(
            ghost, AbilityId.EFFECT_GHOSTSNIPE
        ):
            snipe_target = self._find_best_snipe_target(ghost, nearby_enemies)
            if snipe_target:
                cache.logger.info(f"Ghost {ghost.tag} sniping {snipe_target.name}.")
                return lambda g=ghost, t=snipe_target: g(AbilityId.EFFECT_GHOSTSNIPE, t)

        return None

    def _find_best_emp_target(
        self, ghost: Unit, nearby_enemies: "Units"
    ) -> "Point2" | None:
        """Finds the optimal location to cast EMP."""
        # EMP has a radius of 1.5. Find the spot that hits the most valuable targets.
        emp_candidates = nearby_enemies.filter(
            lambda u: u.is_protoss or u.type_id in EMP_TARGET_PRIORITIES
        ).closer_than(10, ghost)

        if emp_candidates.amount < 2:
            return None

        # Find the point that covers the most units.
        best_point = max(
            emp_candidates.positions,
            key=lambda p: emp_candidates.closer_than(1.5, p).amount,
            default=None,
        )
        return best_point

    def _find_best_snipe_target(
        self, ghost: Unit, nearby_enemies: "Units"
    ) -> Unit | None:
        """Finds the best target for Steady Targeting."""
        targets_in_range = nearby_enemies.closer_than(10, ghost).filter(
            lambda u: u.is_biological and u.can_be_attacked
        )
        if not targets_in_range:
            return None

        for unit_type in SNIPE_TARGET_PRIORITIES:
            potential_targets = targets_in_range.of_type(unit_type)
            if potential_targets.exists:
                return potential_targets.sorted_by_distance_to(ghost).first

        return None

    def _handle_cloak(
        self, ghost: Unit, nearby_enemies: "Units"
    ) -> CommandFunctor | None:
        """Manages cloak to conserve energy for spells."""
        has_cloak_upgrade = (
            self.bot.already_pending_upgrade(UpgradeId.PERSONALCLOAKING) == 1
        )
        if not has_cloak_upgrade:
            return None

        if (
            not ghost.is_cloaked
            and ghost.energy >= CLOAK_MIN_ENERGY
            and nearby_enemies.closer_than(8, ghost).exists
        ):
            return lambda g=ghost: g(AbilityId.BEHAVIOR_CLOAKON_GHOST)

        if ghost.is_cloaked and not nearby_enemies.closer_than(10, ghost).exists:
            return lambda g=ghost: g(AbilityId.BEHAVIOR_CLOAKOFF_GHOST)

        return None
