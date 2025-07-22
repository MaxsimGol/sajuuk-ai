from __future__ import annotations
from typing import TYPE_CHECKING, List, Set, Tuple

from sc2.ids.unit_typeid import UnitTypeId
from sc2.ids.buff_id import BuffId
from sc2.ids.ability_id import AbilityId
from sc2.position import Point2

from core.types import CommandFunctor
from core.utilities.unit_value import calculate_threat_value

if TYPE_CHECKING:
    from sc2.unit import Unit
    from sc2.units import Units
    from core.global_cache import GlobalCache

# A prioritized list of targets for marines. They will always try to kill the first unit type in this list first.
MARINE_TARGET_PRIORITIES: List[UnitTypeId] = [
    # Highest priority splash threats that can wipe out a bio ball instantly.
    UnitTypeId.BANELING,
    UnitTypeId.HIGHTEMPLAR,
    UnitTypeId.DISRUPTOR,
    UnitTypeId.SIEGETANKSIEGED,
    UnitTypeId.WIDOWMINEBURROWED,
    # Key casters and high-value units that need to be removed quickly.
    UnitTypeId.INFESTOR,
    UnitTypeId.QUEEN,
]


class MarineController:
    """
    Infantry Micro Expert.

    This controller manages the detailed, real-time actions of a squad of Marines.
    It is responsible for stutter-stepping, intelligent Stimpack usage, and
    prioritizing high-threat targets.
    """

    def execute(
        self, marines: "Units", target: Point2, cache: "GlobalCache"
    ) -> Tuple[List[CommandFunctor], Set[int]]:
        """
        Executes micro-management for a squad of marines.

        :param marines: The Units object containing the marines to be controlled.
        :param target: The high-level target position from the ArmyControlManager.
        :param cache: The global cache for accessing game state.
        :return: A tuple containing (list of command functors, set of handled unit tags).
        """
        actions: List[CommandFunctor] = []
        if not marines:
            return [], set()

        # Find all enemies within a generous engagement range of the marine squad's center.
        nearby_enemies = cache.enemy_units.closer_than(15, marines.center)
        if not nearby_enemies:
            # If no enemies are nearby, issue a single attack-move command for each marine.
            return [
                lambda m=marine, t=target: m.attack(t) for marine in marines
            ], marines.tags

        # --- 1. Target Prioritization ---
        # Get the TAG of the best target, then find the fresh Unit object for this frame.
        squad_target_tag = self._get_best_target_tag(marines, nearby_enemies)
        squad_target = (
            nearby_enemies.find_by_tag(squad_target_tag) if squad_target_tag else None
        )

        # --- 2. Stimpack Management ---
        if self._should_stim(marines, nearby_enemies, cache):
            stim_marines = marines.filter(
                lambda m: not m.has_buff(BuffId.STIMPACK) and m.health > 20
            )
            if stim_marines:
                # Create an individual stim command for EACH marine.
                actions.extend(
                    [
                        lambda m=marine: m(AbilityId.EFFECT_STIM)
                        for marine in stim_marines
                    ]
                )
                cache.logger.info("Marines are using Stimpack.")

        # --- 3. Individual Stutter-Step Micro ---
        for marine in marines:
            # A. Survival Instinct: Low health marines should retreat.
            if marine.health_percentage < 0.35 and nearby_enemies.exists:
                retreat_pos = marine.position.towards(nearby_enemies.center, -3)
                actions.append(lambda m=marine, p=retreat_pos: m.move(p))
                continue

            # B. Combat Micro: If a target exists, perform stutter-step logic.
            if squad_target:
                if marine.weapon_cooldown == 0:
                    actions.append(lambda m=marine, t=squad_target: m.attack(t))
                else:
                    if marine.distance_to(squad_target) < marine.ground_range:
                        move_pos = marine.position.towards(squad_target.position, -1)
                    else:
                        move_pos = marine.position.towards(squad_target.position, 1)
                    actions.append(lambda m=marine, p=move_pos: m.move(p))
            # C. Fallback: If no specific target, attack-move towards the strategic objective.
            else:
                actions.append(lambda m=marine, t=target: m.attack(t))

        # This controller handles all marines passed to it.
        return actions, marines.tags

    def _get_best_target_tag(self, marines: "Units", enemies: "Units") -> int | None:
        """
        Finds the TAG of the most dangerous enemy unit for the squad to focus fire.
        Returns a tag to prevent using stale Unit objects from previous frames.
        """
        for priority_id in MARINE_TARGET_PRIORITIES:
            priority_targets = enemies.of_type(priority_id)
            if priority_targets.exists:
                return priority_targets.closest_to(marines.center).tag

        attackable_enemies = enemies.filter(
            lambda e: not e.is_flying and e.can_be_attacked
        )
        if attackable_enemies:
            return min(attackable_enemies, key=lambda e: e.health).tag

        return None

    def _should_stim(
        self, marines: "Units", enemies: "Units", cache: "GlobalCache"
    ) -> bool:
        """
        Determines if it is strategically sound to use Stimpack based on health and threat.
        """
        if marines.amount == 0:
            return False

        if (sum(m.health for m in marines) / marines.amount) < 35:
            return False

        stimmed_count = marines.filter(lambda m: m.has_buff(BuffId.STIMPACK)).amount
        if stimmed_count / marines.amount > 0.5:
            return False

        enemy_threat_value = sum(calculate_threat_value(e.type_id) for e in enemies)
        if enemy_threat_value > 30:
            return True

        return False
