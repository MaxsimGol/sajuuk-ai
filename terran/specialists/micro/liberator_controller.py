# terran/specialists/micro/liberator_controller.py
from __future__ import annotations
from typing import TYPE_CHECKING, List, Set, Tuple

from sc2.ids.unit_typeid import UnitTypeId
from sc2.ids.ability_id import AbilityId
from sc2.unit import Unit
from sc2.position import Point2

from core.interfaces.controller_abc import ControllerABC
from core.types import CommandFunctor
from core.utilities.unit_types import WORKER_TYPES

if TYPE_CHECKING:
    from sc2.units import Units
    from terran.tactics.micro_context import MicroContext

# --- Tunable Constants ---
ENGAGEMENT_RANGE = 15
# High-priority anti-air threats that Liberators must respect.
ANTI_AIR_THREATS: Set[UnitTypeId] = {
    UnitTypeId.VIKINGFIGHTER,
    UnitTypeId.CORRUPTOR,
    UnitTypeId.PHOENIX,
    UnitTypeId.MUTALISK,
    UnitTypeId.MISSILETURRET,
    UnitTypeId.SPORECRAWLER,
    UnitTypeId.PHOTONCANNON,
    UnitTypeId.HYDRALISK,
    UnitTypeId.THOR,
    UnitTypeId.BATTLECRUISER,
    UnitTypeId.CARRIER,
}
# High-priority ground targets that justify sieging.
SIEGE_TARGET_PRIORITIES: Set[UnitTypeId] = WORKER_TYPES | {
    UnitTypeId.SIEGETANK,
    UnitTypeId.SIEGETANKSIEGED,
    UnitTypeId.LURKERMPBURROWED,
    UnitTypeId.DISRUPTOR,
    UnitTypeId.HIGHTEMPLAR,
    UnitTypeId.INFESTOR,
    UnitTypeId.QUEEN,
    UnitTypeId.BUNKER,
}


class LiberatorController(ControllerABC):
    """
    Area Denial Specialist. Manages Liberators to control key areas with their
    Defender Mode, while avoiding significant anti-air threats.
    """

    def execute(self, context: "MicroContext") -> Tuple[List[CommandFunctor], Set[int]]:
        """
        Executes micro-management for a squad of Liberators.
        """
        # --- Unpack Context ---
        liberators = context.units_to_control
        strategic_target = context.target
        cache = context.cache
        plan = context.plan

        actions: List[CommandFunctor] = []
        if not liberators:
            return [], set()

        nearby_enemies = cache.enemy_units.closer_than(
            ENGAGEMENT_RANGE, liberators.center
        )

        # Separate liberators by their current mode
        sieged_libs = liberators.of_type(UnitTypeId.LIBERATORAG)
        mobile_libs = liberators.of_type(UnitTypeId.LIBERATOR)

        for lib in sieged_libs:
            action = self._handle_sieged_liberator(lib, nearby_enemies, plan)
            if action:
                actions.append(action)

        for lib in mobile_libs:
            action = self._handle_mobile_liberator(
                lib, nearby_enemies, strategic_target, cache
            )
            if action:
                actions.append(action)

        return actions, liberators.tags

    def _handle_sieged_liberator(
        self, lib: Unit, nearby_enemies: "Units", plan: "FramePlan"
    ) -> CommandFunctor | None:
        """Logic for a Liberator already in Defender Mode."""

        # Unsiege if significant air threats move in.
        air_threats = nearby_enemies.of_type(ANTI_AIR_THREATS)
        if air_threats.closer_than(10, lib).exists:
            return lambda l=lib: l(AbilityId.MORPH_LIBERATORAAMODE)

        # Unsiege if there are no valuable targets left in the circle.
        ground_targets_in_zone = nearby_enemies.filter(
            lambda u: not u.is_flying and u.distance_to(lib.order_target) <= 5
        )
        if not ground_targets_in_zone.exists:
            return lambda l=lib: l(AbilityId.MORPH_LIBERATORAAMODE)

        return None

    def _handle_mobile_liberator(
        self,
        lib: Unit,
        nearby_enemies: "Units",
        strategic_target: "Point2",
        cache: "GlobalCache",
    ) -> CommandFunctor | None:
        """Logic for a Liberator in Fighter Mode."""

        # 1. Primary Goal: Find a good place to siege up.
        siege_position = self._find_best_siege_position(lib, nearby_enemies, cache)

        if siege_position:
            cache.logger.info(
                f"Liberator {lib.tag} sieging at {siege_position.rounded}."
            )
            return lambda l=lib, p=siege_position: l(AbilityId.MORPH_LIBERATORAGMODE, p)

        # 2. Secondary Goal: Act as anti-air escort if no good siege spot exists.
        air_enemies = nearby_enemies.of_type(cache.enemy_units.flying)
        if air_enemies.exists:
            closest_air_threat = air_enemies.closest_to(lib)
            return lambda l=lib, t=closest_air_threat: l.attack(t)

        # 3. Default: Move to the strategic target.
        if lib.distance_to(strategic_target) > 10:
            return lambda l=lib, p=strategic_target: l.move(p)

        return None

    def _find_best_siege_position(
        self, lib: Unit, nearby_enemies: "Units", cache: "GlobalCache"
    ) -> Point2 | None:
        """
        Evaluates potential siege locations to find one that is both
        high-value and relatively safe.
        """
        potential_targets = nearby_enemies.filter(
            lambda u: u.type_id in SIEGE_TARGET_PRIORITIES and not u.is_flying
        )
        if not potential_targets:
            return None

        best_target_pos = None
        best_score = 0

        # Evaluate the area around each high-priority target
        for target_unit in potential_targets:
            # How many priority units would be in the circle?
            score = potential_targets.closer_than(5, target_unit.position).amount

            # Is the proposed siege location safe from AA?
            # A safe siege location is one where the Liberator itself is outside AA range.
            # We check from a point 5 units away (its siege range).
            siege_location_guess = target_unit.position.towards(lib.position, 5)

            air_threats = nearby_enemies.of_type(ANTI_AIR_THREATS)
            if air_threats.closer_than(8, siege_location_guess).exists:
                score -= 10  # Heavily penalize unsafe positions

            if score > best_score:
                best_score = score
                best_target_pos = target_unit.position

        if best_score > 0:
            return best_target_pos

        return None
