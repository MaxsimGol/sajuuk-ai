# terran/specialists/micro/marine_controller.py
from __future__ import annotations
from typing import TYPE_CHECKING, List, Set, Tuple

from sc2.ids.unit_typeid import UnitTypeId
from sc2.ids.buff_id import BuffId
from sc2.ids.ability_id import AbilityId
from sc2.position import Point2
from sc2.unit import Unit

from core.types import CommandFunctor

if TYPE_CHECKING:
    from sc2.units import Units
    from core.global_cache import GlobalCache

# --- Tunable Micro Constants ---
# How far marines will look for enemies to engage.
ENGAGEMENT_RANGE = 15
# Health percentage below which a marine will prioritize survival.
SURVIVAL_HEALTH_THRESHOLD = 0.4
# Don't stim if health is below this absolute value.
STIM_HEALTH_THRESHOLD = 20
# How far to back away from a melee target while stutter-stepping.
KITE_DISTANCE = 1.5
# Minimum number of enemy units to justify an offensive stim.
STIM_OFFENSIVE_TRIGGER_COUNT = 4

# A prioritized list of targets. Marines will always try to kill the first unit type in this list first.
MARINE_TARGET_PRIORITIES: List[UnitTypeId] = [
    # Highest priority splash threats that can wipe out a bio ball instantly.
    UnitTypeId.BANELING,
    UnitTypeId.HIGHTEMPLAR,
    UnitTypeId.DISRUPTOR,
    UnitTypeId.SIEGETANKSIEGED,
    UnitTypeId.WIDOWMINEBURROWED,
    # Key casters and high-value units that need to be removed quickly.
    UnitTypeId.INFESTOR,
    UnitTypeId.COLOSSUS,
    UnitTypeId.LURKERMPBURROWED,
]


class MarineController:
    """
    Infantry Micro Expert.

    This controller manages the detailed, real-time actions of a squad of Marines
    based on best-practice rule-based AI principles. Each marine acts as an
    individual agent, leading to emergent, intelligent squad behavior.
    """

    def execute(
        self, marines: "Units", target: Point2, cache: "GlobalCache"
    ) -> Tuple[List[CommandFunctor], Set[int]]:
        """
        Executes micro-management for a squad of marines.

        :param marines: The Units object containing the marines to be controlled.
        :param target: The high-level strategic target from the ArmyControlManager.
        :param cache: The global cache for accessing game state.
        :return: A tuple containing (list of command functors, set of handled unit tags).
        """
        actions: List[CommandFunctor] = []
        if not marines:
            return [], set()

        # Find all enemies within a generous engagement range of the marine squad's center.
        nearby_enemies = cache.enemy_units.closer_than(ENGAGEMENT_RANGE, marines.center)

        # 1. Squad-level Decision: Should we use Stimpack?
        stim_actions = self._handle_stim(marines, nearby_enemies, cache)
        actions.extend(stim_actions)

        # 2. Individual Marine Micro: Each marine makes its own decision.
        for marine in marines:
            action = self._handle_single_marine(marine, nearby_enemies, target)
            if action:
                actions.append(action)

        # This controller handles all marines passed to it.
        return actions, marines.tags

    def _handle_stim(
        self, marines: "Units", nearby_enemies: "Units", cache: "GlobalCache"
    ) -> List[CommandFunctor]:
        """Makes a squad-level decision to use Stimpack."""
        # Don't stim if there are no enemies or the squad is too small.
        if not nearby_enemies or marines.amount < 5:
            return []

        # Check if a significant portion of the squad is already stimmed.
        stimmed_count = marines.filter(lambda m: m.has_buff(BuffId.STIMPACK)).amount
        if stimmed_count / marines.amount > 0.5:
            return []

        # Offensive Stim: Use if facing a critical mass of enemies.
        if nearby_enemies.amount >= STIM_OFFENSIVE_TRIGGER_COUNT:
            # Filter for marines that are healthy enough to stim.
            stim_candidates = marines.filter(
                lambda m: not m.has_buff(BuffId.STIMPACK)
                and m.health > STIM_HEALTH_THRESHOLD
            )
            if stim_candidates:
                cache.logger.info(
                    f"Using offensive Stimpack for {stim_candidates.amount} marines."
                )
                return [
                    lambda m=marine: m(AbilityId.EFFECT_STIM)
                    for marine in stim_candidates
                ]

        return []

    def _handle_single_marine(
        self, marine: Unit, nearby_enemies: "Units", strategic_target: Point2
    ) -> CommandFunctor | None:
        """The core decision tree for an individual marine."""

        # Rule 1: Survival. If health is critical, retreat from the nearest threat.
        if (
            marine.health_percentage < SURVIVAL_HEALTH_THRESHOLD
            and nearby_enemies.exists
        ):
            closest_enemy = nearby_enemies.closest_to(marine)
            retreat_position = marine.position.towards(closest_enemy.position, -5)
            return lambda m=marine, p=retreat_position: m.move(p)

        # Rule 2: Find the best individual target.
        best_target = self._find_best_target_for_marine(marine, nearby_enemies)

        # Rule 3: Engage or move.
        if best_target:
            # Weapon is ready to fire, so shoot.
            if marine.weapon_cooldown == 0:
                return lambda m=marine, t=best_target: m.attack(t)

            # Weapon is on cooldown, so reposition (stutter-step).
            else:
                # Kite melee units by moving away.
                if best_target.ground_range <= 2:
                    kite_position = marine.position.towards(
                        best_target.position, -KITE_DISTANCE
                    )
                    return lambda m=marine, p=kite_position: m.move(p)
                # For ranged units, just hold position or move slightly to avoid being an easy target.
                # A simple move command towards the strategic target keeps the squad advancing.
                else:
                    return lambda m=marine, t=strategic_target: m.move(t)

        # Rule 4: No enemies in range, so move towards the strategic target.
        return lambda m=marine, t=strategic_target: m.attack(t)

    def _find_best_target_for_marine(
        self, marine: Unit, nearby_enemies: "Units"
    ) -> Unit | None:
        """Finds the most dangerous enemy unit for a single marine to focus fire."""

        # Consider only enemies that this marine can actually attack.
        attackable_enemies = nearby_enemies.in_attack_range_of(
            marine, bonus_distance=1
        ).filter(lambda e: not e.is_flying and e.can_be_attacked)
        if not attackable_enemies:
            return None

        # 1. Check for top-priority threats (Banelings, Storms, etc.).
        for priority_id in MARINE_TARGET_PRIORITIES:
            priority_targets = attackable_enemies.of_type(priority_id)
            if priority_targets.exists:
                return priority_targets.closest_to(marine)

        # 2. If no high-priority threats, target the closest enemy unit.
        return attackable_enemies.closest_to(marine)
