# terran/specialists/micro/medivac_controller.py
from __future__ import annotations
from typing import TYPE_CHECKING, List, Set, Tuple

from sc2.ids.ability_id import AbilityId
from sc2.ids.unit_typeid import UnitTypeId
from sc2.ids.buff_id import BuffId
from sc2.position import Point2
from sc2.unit import Unit

from core.interfaces.controller_abc import ControllerABC
from core.types import CommandFunctor
from terran.tactics.micro_context import MicroContext

if TYPE_CHECKING:
    from sc2.units import Units
    from core.global_cache import GlobalCache
    from core.frame_plan import FramePlan

# --- Tunable Constants ---
THREAT_ASSESSMENT_RANGE = 18
LEASH_DISTANCE = 3
PRIORITY_HEAL_THRESHOLD = 0.6
BOOST_HEALTH_MINIMUM = 0.75

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
}


class MedivacController(ControllerABC):
    """
    Combat Medic and Transport Pilot. Manages Medivacs by "leashing" them
    to the bio squad for healing and safe positioning.
    """

    def execute(self, context: "MicroContext") -> Tuple[List[CommandFunctor], Set[int]]:
        """
        Executes intelligent micro for a squad of Medivacs using a shared context.
        """
        # --- Unpack Context ---
        medivacs = context.units_to_control
        bio_squad = context.bio_squad
        target = context.target
        cache = context.cache
        plan = context.plan

        actions: List[CommandFunctor] = []
        if not medivacs:
            return [], set()

        # Retreat if the bio squad is wiped out
        if not bio_squad or not bio_squad.exists:
            rally_point = plan.rally_point or cache.bot.start_location
            for medivac in medivacs:
                if medivac.distance_to(rally_point) > 3:
                    actions.append(lambda m=medivac, p=rally_point: m.move(p))
            return actions, medivacs.tags

        army_center = (medivacs.center + bio_squad.center) / 2
        nearby_enemies = cache.enemy_units.closer_than(
            THREAT_ASSESSMENT_RANGE, army_center
        )

        use_boost = self._should_boost(
            medivacs, bio_squad, target, nearby_enemies, cache
        )

        for medivac in medivacs:
            support_target = self._get_support_target(medivac, bio_squad)
            safe_position = self._calculate_safe_leash_point(
                medivac, support_target, nearby_enemies
            )

            if use_boost and medivac.energy >= 10:
                actions.append(
                    lambda m=medivac: m(AbilityId.EFFECT_MEDIVACIGNITEAFTERBURNERS)
                )

            # Use 'attack' move to ensure auto-healing while repositioning.
            if medivac.distance_to(safe_position) > 1.5:
                actions.append(lambda m=medivac, p=safe_position: m.attack(p))

        return actions, medivacs.tags

    def _get_support_target(self, medivac: Unit, bio_squad: "Units") -> Unit | "Units":
        """Determines if the Medivac should follow a single critical unit or the squad."""
        critically_wounded = bio_squad.filter(
            lambda u: u.health_percentage < PRIORITY_HEAL_THRESHOLD
        ).closer_than(10, medivac)

        if critically_wounded.exists:
            return min(critically_wounded, key=lambda u: u.health)
        return bio_squad

    def _calculate_safe_leash_point(
        self, medivac: Unit, support_target: Unit | "Units", enemies: "Units"
    ) -> Point2:
        """Calculates a follow position behind the support target, away from enemies."""
        target_center = (
            support_target.position
            if isinstance(support_target, Unit)
            else support_target.center
        )

        if not enemies.exists:
            return target_center.towards(medivac.position, -LEASH_DISTANCE)

        safe_vector = enemies.center.direction_vector(target_center)

        if safe_vector.x == 0 and safe_vector.y == 0:
            return target_center.towards(self.bot.start_location, -LEASH_DISTANCE)

        return target_center + (safe_vector * LEASH_DISTANCE)

    def _should_boost(
        self,
        medivacs: "Units",
        bio_squad: "Units",
        target: Point2,
        enemies: "Units",
        cache: "GlobalCache",
    ) -> bool:
        """Decides if the Medivac squad should use its boost ability."""
        if medivacs.filter(
            lambda m: m.energy >= 10 and not m.has_buff(BuffId.MEDIVACSPEEDBOOST)
        ).empty:
            return False

        avg_health = sum(u.health_percentage for u in bio_squad) / bio_squad.amount

        if avg_health < 0.6 and enemies.exists:
            cache.logger.info("Medivacs boosting to retreat.")
            return True

        if (
            avg_health > BOOST_HEALTH_MINIMUM
            and bio_squad.center.distance_to(target) > 25
        ):
            enemies_at_target = cache.known_enemy_units.closer_than(15, target)
            if enemies_at_target.of_type(ANTI_AIR_THREATS).amount < 3:
                cache.logger.info("Medivacs boosting to engage.")
                return True

        return False
