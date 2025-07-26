# terran/specialists/micro/marauder_controller.py
from __future__ import annotations
from typing import TYPE_CHECKING, List, Set, Tuple

from sc2.ids.unit_typeid import UnitTypeId
from sc2.ids.buff_id import BuffId
from sc2.ids.ability_id import AbilityId
from sc2.position import Point2
from sc2.unit import Unit

from core.interfaces.controller_abc import ControllerABC
from core.types import CommandFunctor

if TYPE_CHECKING:
    from sc2.units import Units
    from terran.tactics.micro_context import MicroContext

# --- Tunable Constants ---
ENGAGEMENT_RANGE = 15
SURVIVAL_HEALTH_THRESHOLD = 0.4
STIM_HEALTH_THRESHOLD = 35  # Marauders have more health than marines
KITE_DISTANCE = 1.0
STIM_OFFENSIVE_TRIGGER_COUNT = 3

# Priority targets for Marauders, focusing on armored units they counter.
MARAUDER_TARGET_PRIORITIES: List[UnitTypeId] = [
    UnitTypeId.STALKER,
    UnitTypeId.ROACH,
    UnitTypeId.IMMORTAL,
    UnitTypeId.SIEGETANK,
    UnitTypeId.SIEGETANKSIEGED,
    UnitTypeId.THOR,
    UnitTypeId.COLOSSUS,
    UnitTypeId.ULTRALISK,
]


class MarauderController(ControllerABC):
    """
    Armored Target Specialist. Manages Marauders to act as durable frontline
    units, prioritizing armored targets and using Concussive Shells to control engagements.
    """

    def execute(self, context: "MicroContext") -> Tuple[List[CommandFunctor], Set[int]]:
        """
        Executes micro-management for a squad of Marauders.
        """
        # --- Unpack Context ---
        marauders = context.units_to_control
        strategic_target = context.target
        cache = context.cache

        actions: List[CommandFunctor] = []
        if not marauders:
            return [], set()

        nearby_enemies = cache.enemy_units.closer_than(
            ENGAGEMENT_RANGE, marauders.center
        )

        # 1. Squad-level Stimpack logic
        stim_actions = self._handle_stim(marauders, nearby_enemies, cache)
        actions.extend(stim_actions)

        # 2. Individual Marauder Micro
        for marauder in marauders:
            action = self._handle_single_marauder(
                marauder, nearby_enemies, strategic_target
            )
            if action:
                actions.append(action)

        return actions, marauders.tags

    def _handle_stim(
        self, marauders: "Units", nearby_enemies: "Units", cache: "GlobalCache"
    ) -> List[CommandFunctor]:
        """Makes a squad-level decision to use Stimpack."""
        if not nearby_enemies or marauders.amount < 3:
            return []

        stimmed_marauders = marauders.filter(
            lambda m: m.has_buff(BuffId.STIMPACKMARAUDER)
        )
        if stimmed_marauders.amount / marauders.amount > 0.5:
            return []

        if nearby_enemies.amount >= STIM_OFFENSIVE_TRIGGER_COUNT:
            stim_candidates = marauders.filter(
                lambda m: not m.has_buff(BuffId.STIMPACKMARAUDER)
                and m.health > STIM_HEALTH_THRESHOLD
            )
            if stim_candidates:
                cache.logger.info(
                    f"Using offensive Stimpack for {stim_candidates.amount} marauders."
                )
                return [
                    lambda m=marauder: m(AbilityId.EFFECT_STIM_MARAUDER)
                    for marauder in stim_candidates
                ]
        return []

    def _handle_single_marauder(
        self,
        marauder: Unit,
        nearby_enemies: "Units",
        strategic_target: Point2,
    ) -> CommandFunctor | None:
        """The core decision tree for an individual Marauder."""
        # Rule 1: Survival
        if (
            marauder.health_percentage < SURVIVAL_HEALTH_THRESHOLD
            and nearby_enemies.exists
        ):
            closest_enemy = nearby_enemies.closest_to(marauder)
            retreat_position = marauder.position.towards(closest_enemy.position, -5)
            return lambda m=marauder, p=retreat_position: m.move(p)

        # Rule 2: Find and engage the best target
        best_target = self._find_best_target(marauder, nearby_enemies)
        if best_target:
            if marauder.weapon_cooldown == 0:
                return lambda m=marauder, t=best_target: m.attack(t)
            else:
                # Stutter-step: move towards target while reloading to maintain pressure.
                return lambda m=marauder, t=best_target: m.move(t.position)

        # Rule 3: No enemies in range, move to the strategic target.
        return lambda m=marauder, t=strategic_target: m.attack(t)

    def _find_best_target(
        self, marauder: Unit, nearby_enemies: "Units", context: "MicroContext"
    ) -> Unit | None:
        """Finds the most valuable enemy for a Marauder to attack."""
        attackable_enemies = nearby_enemies.in_attack_range_of(marauder).filter(
            lambda u: not u.is_flying and u.can_be_attacked
        )
        if not attackable_enemies:
            return None

        # 1. Obey focus fire command
        focus_target = context.focus_fire_target
        if focus_target and focus_target in attackable_enemies:
            return focus_target

        # 2. Fallback to specialist logic: high-priority armored targets
        for priority_id in MARAUDER_TARGET_PRIORITIES:
            priority_targets = attackable_enemies.of_type(priority_id)
            if priority_targets.exists:
                return priority_targets.closest_to(marauder)

        # 3. Fallback: any armored unit
        armored_units = attackable_enemies.filter(lambda u: u.is_armored)
        if armored_units.exists:
            return armored_units.closest_to(marauder)

        # 4. Default: closest enemy
        return attackable_enemies.closest_to(marauder)
