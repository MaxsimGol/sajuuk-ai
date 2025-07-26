# terran/specialists/micro/marine_controller.py
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
    from core.global_cache import GlobalCache
    from core.frame_plan import FramePlan
    from terran.tactics.micro_context import MicroContext

# --- Tunable Micro Constants ---
ENGAGEMENT_RANGE = 15
SURVIVAL_HEALTH_THRESHOLD = 0.4
STIM_HEALTH_THRESHOLD = 20
KITE_DISTANCE = 1.5
STIM_OFFENSIVE_TRIGGER_COUNT = 4

MARINE_TARGET_PRIORITIES: List[UnitTypeId] = [
    UnitTypeId.BANELING,
    UnitTypeId.HIGHTEMPLAR,
    UnitTypeId.DISRUPTOR,
    UnitTypeId.SIEGETANKSIEGED,
    UnitTypeId.WIDOWMINEBURROWED,
    UnitTypeId.INFESTOR,
    UnitTypeId.COLOSSUS,
    UnitTypeId.LURKERMPBURROWED,
]


class MarineController(ControllerABC):
    """
    Infantry Micro Expert. Manages the detailed, real-time actions of
    a squad of Marines based on rule-based AI principles.
    """

    def execute(self, context: "MicroContext") -> Tuple[List[CommandFunctor], Set[int]]:
        """
        Executes micro-management for a squad of marines using the provided context.
        """
        # --- Unpack Context ---
        marines = context.units_to_control
        strategic_target = context.target
        cache = context.cache

        actions: List[CommandFunctor] = []
        if not marines:
            return [], set()

        nearby_enemies = cache.enemy_units.closer_than(ENGAGEMENT_RANGE, marines.center)

        # 1. Squad-level Decision: Stimpack
        stim_actions = self._handle_stim(marines, nearby_enemies, cache)
        actions.extend(stim_actions)

        # 2. Individual Marine Micro
        for marine in marines:
            action = self._handle_single_marine(
                marine, nearby_enemies, strategic_target
            )
            if action:
                actions.append(action)

        return actions, marines.tags

    def _handle_stim(
        self, marines: "Units", nearby_enemies: "Units", cache: "GlobalCache"
    ) -> List[CommandFunctor]:
        """Makes a squad-level decision to use Stimpack."""
        if not nearby_enemies or marines.amount < 5:
            return []

        stimmed_marines = marines.filter(lambda m: m.has_buff(BuffId.STIMPACK))
        if stimmed_marines.amount / marines.amount > 0.5:
            return []

        if nearby_enemies.amount >= STIM_OFFENSIVE_TRIGGER_COUNT:
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
        if (
            marine.health_percentage < SURVIVAL_HEALTH_THRESHOLD
            and nearby_enemies.exists
        ):
            closest_enemy = nearby_enemies.closest_to(marine)
            retreat_position = marine.position.towards(closest_enemy.position, -5)
            return lambda m=marine, p=retreat_position: m.move(p)

        best_target = self._find_best_target_for_marine(marine, nearby_enemies)

        if best_target:
            if marine.weapon_cooldown == 0:
                return lambda m=marine, t=best_target: m.attack(t)
            else:
                if best_target.ground_range <= 2:
                    kite_position = marine.position.towards(
                        best_target.position, -KITE_DISTANCE
                    )
                    return lambda m=marine, p=kite_position: m.move(p)
                else:
                    return lambda m=marine, t=strategic_target: m.move(t)

        return lambda m=marine, t=strategic_target: m.attack(t)

    def _find_best_target_for_marine(
        self, marine: Unit, nearby_enemies: "Units", context: "MicroContext"
    ) -> Unit | None:
        """Finds the most dangerous enemy unit for a single marine to focus fire."""
        attackable_enemies = nearby_enemies.in_attack_range_of(
            marine, bonus_distance=1
        ).filter(lambda e: not e.is_flying and e.can_be_attacked)

        if not attackable_enemies:
            return None

        # 1. Obey focus fire command from the ArmyControlManager
        focus_target = context.focus_fire_target
        if focus_target and focus_target in attackable_enemies:
            return focus_target

        # 2. Fallback to specialist logic: Check for top-priority threats
        for priority_id in MARINE_TARGET_PRIORITIES:
            priority_targets = attackable_enemies.of_type(priority_id)
            if priority_targets.exists:
                return priority_targets.closest_to(marine)

        # 3. Default: Target the closest enemy unit.
        return attackable_enemies.closest_to(marine)
