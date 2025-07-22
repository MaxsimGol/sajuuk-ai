# terran/specialists/micro/medivac_controller.py
from __future__ import annotations
from typing import TYPE_CHECKING, List, Set, Tuple

from sc2.ids.ability_id import AbilityId
from sc2.ids.unit_typeid import UnitTypeId
from sc2.ids.buff_id import BuffId
from sc2.position import Point2
from sc2.unit import Unit

from core.types import CommandFunctor

if TYPE_CHECKING:
    from sc2.units import Units
    from core.global_cache import GlobalCache
    from core.frame_plan import FramePlan

# --- Tunable Constants ---
# How far Medivacs will look for enemies to assess threat.
THREAT_ASSESSMENT_RANGE = 18
# Ideal distance a Medivac should stay behind its support target (squad or individual).
LEASH_DISTANCE = 3
# Health percentage of a bio unit to be considered a high-priority heal target.
PRIORITY_HEAL_THRESHOLD = 0.6
# Don't boost if average bio health is below this, unless retreating.
BOOST_HEALTH_MINIMUM = 0.75

# High-priority anti-air threats that Medivacs must respect.
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
DODGE_BUFFS: Set[BuffId] = {BuffId.PSISTORM, BuffId.FUNGALGROWTH}


class MedivacController:
    """
    Combat Medic and Transport Pilot.

    This controller manages Medivacs by "leashing" them to the bio squad. It
    dynamically calculates a safe follow position behind the bio ball, preventing
    the Medivacs from outrunning their escort and dying needlessly.
    """

    def execute(
        self,
        medivacs: "Units",
        bio_squad: "Units",
        target: Point2,
        cache: "GlobalCache",
        plan: "FramePlan",
    ) -> Tuple[List[CommandFunctor], Set[int]]:
        """
        Executes intelligent micro for a squad of Medivacs.

        :param medivacs: The Units object of Medivacs to be controlled.
        :param bio_squad: The Units object of bio units the Medivacs are supporting.
        :param target: The high-level target position for the army.
        :param cache: The global cache for accessing game state.
        :param plan: The frame plan for accessing tactical positions.
        :return: A tuple containing (list of command functors, set of handled unit tags).
        """
        actions: List[CommandFunctor] = []
        if not medivacs:
            return [], set()

        # Retreat protocol if the bio squad is wiped out.
        if not bio_squad.exists:
            rally_point = getattr(plan, "rally_point", cache.bot.start_location)
            for medivac in medivacs:
                if medivac.is_idle or medivac.order_target != rally_point:
                    actions.append(lambda m=medivac, p=rally_point: m.move(p))
            return actions, medivacs.tags

        # Find all enemies near the combined army.
        army_center = (medivacs.center + bio_squad.center) / 2
        nearby_enemies = cache.enemy_units.closer_than(
            THREAT_ASSESSMENT_RANGE, army_center
        )

        # Squad-level decision to boost.
        use_boost = self._should_boost(
            medivacs, bio_squad, target, nearby_enemies, cache
        )

        for medivac in medivacs:
            # 1. Survival: Dodge immediate area-of-effect threats.
            if any(medivac.has_buff(b) for b in DODGE_BUFFS) and nearby_enemies.exists:
                retreat_pos = medivac.position.towards(nearby_enemies.center, -5)
                actions.append(lambda m=medivac, p=retreat_pos: m.move(p))
                if medivac.energy >= 10:
                    actions.append(
                        lambda m=medivac: m(AbilityId.EFFECT_MEDIVACIGNITEAFTERBURNERS)
                    )
                continue

            # 2. Determine the support target: either a critical unit or the whole squad.
            support_target = self._get_support_target(medivac, bio_squad)

            # 3. Calculate the safe "leash" position behind the support target.
            safe_position = self._calculate_safe_leash_point(
                medivac, support_target, nearby_enemies
            )

            # 4. Issue commands.
            if use_boost and medivac.energy >= 10:
                actions.append(
                    lambda m=medivac: m(AbilityId.EFFECT_MEDIVACIGNITEAFTERBURNERS)
                )

            # Move to the safe position. Using 'attack' is safer than 'move' as it
            # allows Medivacs to auto-heal units they pass.
            if medivac.distance_to(safe_position) > 1.5:
                actions.append(lambda m=medivac, p=safe_position: m.attack(p))

        return actions, medivacs.tags

    def _get_support_target(self, medivac: Unit, bio_squad: "Units") -> Unit | "Units":
        """
        Determines what the Medivac should be following.
        Returns a single high-priority unit, or the entire bio_squad.
        """
        # Find nearby, critically wounded bio units.
        critically_wounded = bio_squad.filter(
            lambda u: u.health_percentage < PRIORITY_HEAL_THRESHOLD
        ).closer_than(10, medivac)

        if critically_wounded.exists:
            # Return the single most damaged unit to focus on.
            return min(critically_wounded, key=lambda u: u.health)

        # If no one is critically hurt, support the entire squad.
        return bio_squad

    def _calculate_safe_leash_point(
        self, medivac: Unit, support_target: Unit | "Units", enemies: "Units"
    ) -> Point2:
        """
        Calculates a safe follow position behind the support target, away from enemies.
        """
        target_center = (
            support_target.position
            if isinstance(support_target, Unit)
            else support_target.center
        )

        if not enemies.exists:
            # No enemies nearby, just follow the target closely.
            return target_center.towards(medivac.position, LEASH_DISTANCE)

        # Vector from the center of enemies towards our support target defines the "safe" direction.
        safe_vector = enemies.center.direction_vector(target_center)

        if safe_vector.x == 0 and safe_vector.y == 0:
            # Fallback if centers overlap (e.g., surrounded by zerglings).
            # Move towards the bot's own start location as a simple retreat vector.
            return target_center.towards(self.bot.start_location, LEASH_DISTANCE)

        # The ideal position is a few units behind the target along the safe vector.
        return target_center + (safe_vector * LEASH_DISTANCE)

    def _should_boost(
        self,
        medivacs: "Units",
        bio_squad: "Units",
        target: Point2,
        enemies: "Units",
        cache: "GlobalCache",
    ) -> bool:
        """Makes a squad-level decision on whether to use boost."""
        # Don't boost if no energy or already boosting.
        if medivacs.filter(
            lambda m: m.energy >= 10 and not m.has_buff(BuffId.MEDIVACSPEEDBOOST)
        ).empty:
            return False

        avg_health = (
            sum(u.shield_health_percentage for u in bio_squad) / bio_squad.amount
        )

        # Retreat Boost: If the squad is hurt and under fire, boost to escape.
        if avg_health < 0.6 and enemies.exists:
            cache.logger.info("Medivacs boosting to retreat.")
            return True

        # Engage Boost: If squad is healthy and far from target, boost to engage.
        if (
            avg_health > BOOST_HEALTH_MINIMUM
            and bio_squad.center.distance_to(target) > 25
        ):
            # Safety check: Don't boost into a known anti-air nest.
            enemies_at_target = cache.known_enemy_units.closer_than(15, target)
            aa_threats = enemies_at_target.of_type(ANTI_AIR_THREATS)
            if aa_threats.amount >= 3:
                cache.logger.warning(
                    f"Medivac boost cancelled: {aa_threats.amount} AA threats at target."
                )
                return False
            cache.logger.info("Medivacs boosting to engage.")
            return True

        return False
