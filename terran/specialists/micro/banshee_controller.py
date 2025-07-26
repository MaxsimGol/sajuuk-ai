# terran/specialists/micro/banshee_controller.py
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
HARASS_ENGAGEMENT_RANGE = 20
CLOAK_ENERGY_COST = 50
# Enemy units that can detect cloaked units.
DETECTOR_UNITS: Set[UnitTypeId] = {
    UnitTypeId.MISSILETURRET,
    UnitTypeId.SPORECRAWLER,
    UnitTypeId.PHOTONCANNON,
    UnitTypeId.OBSERVER,
    UnitTypeId.RAVEN,
    UnitTypeId.OVERSEER,
}
# Priority targets for harassment.
HARASS_TARGET_PRIORITIES: Set[UnitTypeId] = WORKER_TYPES | {
    UnitTypeId.QUEEN,
    UnitTypeId.SPAWNINGPOOL,
    UnitTypeId.PYLON,  # Specifically ones powering production
}


class BansheeController(ControllerABC):
    """
    Harassment Specialist. Manages Banshees for surprise attacks on enemy
    worker lines and key tech structures.
    """

    def execute(self, context: "MicroContext") -> Tuple[List[CommandFunctor], Set[int]]:
        """
        Executes harassment micro for a squad of Banshees.
        """
        # --- Unpack Context ---
        banshees = context.units_to_control
        strategic_target = context.target
        cache = context.cache
        plan = context.plan

        actions: List[CommandFunctor] = []
        if not banshees:
            return [], set()

        nearby_enemies = cache.enemy_units.closer_than(
            HARASS_ENGAGEMENT_RANGE, banshees.center
        )

        for banshee in banshees:
            action = self._handle_single_banshee(
                banshee, nearby_enemies, strategic_target, cache, plan
            )
            if action:
                actions.append(action)

        return actions, banshees.tags

    def _handle_single_banshee(
        self,
        banshee: Unit,
        nearby_enemies: "Units",
        strategic_target: "Point2",
        cache: "GlobalCache",
        plan: "FramePlan",
    ) -> CommandFunctor | None:
        """The core decision tree for an individual Banshee."""

        # 1. Survival: Retreat if detected by an anti-air threat.
        detectors = nearby_enemies.of_type(DETECTOR_UNITS).filter(lambda u: u.is_ready)
        if detectors.exists and detectors.closer_than(11, banshee).exists:
            # Retreat to the rally point if detected.
            retreat_position = plan.rally_point or self.bot.start_location
            cache.logger.warning(f"Banshee {banshee.tag} detected. Retreating.")
            return lambda b=banshee, p=retreat_position: b.move(p)

        # 2. Cloak Management
        cloak_action = self._handle_cloak(banshee, nearby_enemies)
        if cloak_action:
            return cloak_action

        # 3. Target Selection and Engagement
        best_target = self._find_best_target(banshee, nearby_enemies)

        if best_target:
            # If a priority target is found, attack it.
            return lambda b=banshee, t=best_target: b.attack(t)
        else:
            # If no priority targets are in sight, move towards the strategic target.
            # Using 'attack' allows it to engage targets of opportunity.
            if banshee.distance_to(strategic_target) > 5:
                return lambda b=banshee, t=strategic_target: b.attack(t)

        return None

    def _handle_cloak(
        self, banshee: Unit, nearby_enemies: "Units"
    ) -> CommandFunctor | None:
        """Manages the Banshee's cloak ability to conserve energy."""
        has_cloak = self.bot.already_pending_upgrade(UpgradeId.BANSHEECLOAK) == 1
        if not has_cloak:
            return None

        # Cloak if approaching enemies and have enough energy.
        if (
            not banshee.is_cloaked
            and banshee.energy >= CLOAK_ENERGY_COST
            and nearby_enemies.closer_than(10, banshee).exists
        ):
            return lambda b=banshee: b(AbilityId.BEHAVIOR_CLOAKON_BANSHEE)

        # Uncloak if out of combat and energy is getting low to regenerate.
        if (
            banshee.is_cloaked
            and banshee.energy < 75
            and not nearby_enemies.closer_than(12, banshee).exists
        ):
            return lambda b=banshee: b(AbilityId.BEHAVIOR_CLOAKOFF_BANSHEE)

        return None

    def _find_best_target(
        self, banshee: Unit, nearby_enemies: "Units", context: "MicroContext"
    ) -> Unit | None:
        """Finds the highest-priority harassment target in range."""
        attackable_enemies = nearby_enemies.filter(
            lambda u: u.can_be_attacked and not u.is_flying
        )
        if not attackable_enemies:
            return None

        # 1. Obey focus fire if it's a priority harassment target
        focus_target = context.focus_fire_target
        if (
            focus_target
            and focus_target in attackable_enemies
            and focus_target.type_id in HARASS_TARGET_PRIORITIES
        ):
            return focus_target

        # 2. Fallback: Prioritize key harassment targets.
        priority_targets = attackable_enemies.of_type(HARASS_TARGET_PRIORITIES)
        if priority_targets.exists:
            return priority_targets.closest_to(banshee)

        # 3. Fallback: Attack any non-threatening ground unit.
        non_threatening = attackable_enemies.filter(lambda u: u.can_attack_air is False)
        if non_threatening.exists:
            return non_threatening.closest_to(banshee)

        return None
