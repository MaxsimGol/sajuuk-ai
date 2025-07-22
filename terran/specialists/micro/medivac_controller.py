from __future__ import annotations
from typing import TYPE_CHECKING, List, Set, Tuple

from sc2.ids.ability_id import AbilityId
from sc2.ids.unit_typeid import UnitTypeId
from sc2.ids.buff_id import BuffId
from sc2.position import Point2

from core.types import CommandFunctor

if TYPE_CHECKING:
    from sc2.unit import Unit
    from sc2.units import Units
    from core.global_cache import GlobalCache

# A set of high-priority anti-air threats that Medivacs must respect before boosting.
ANTI_AIR_THREATS: Set[UnitTypeId] = {
    UnitTypeId.VIKINGFIGHTER,
    UnitTypeId.CORRUPTOR,
    UnitTypeId.PHOENIX,
    UnitTypeId.MUTALISK,
    UnitTypeId.MISSILETURRET,
    UnitTypeId.SPORECRAWLER,
    UnitTypeId.PHOTONCANNON,
    UnitTypeId.HYDRALISK,
}

# Dangerous area-of-effect buffs/spells to dodge.
DODGE_BUFFS: Set[BuffId] = {
    BuffId.PSISTORM,
    BuffId.FUNGALGROWTH,
}

# The ideal distance a Medivac should stay behind its heal target.
HEAL_FOLLOW_DISTANCE = 2.5


class MedivacController:
    """
    Combat Medic and Transport Pilot.

    This advanced controller manages Medivacs with a focus on survivability and
    efficiency. It uses threat analysis for positioning and ability usage.
    """

    def execute(
        self,
        medivacs: "Units",
        bio_squad: "Units",
        target: Point2,
        cache: "GlobalCache",
    ) -> Tuple[List[CommandFunctor], Set[int]]:
        """
        Executes intelligent micro for a squad of Medivacs.

        :param medivacs: The Units object of Medivacs to be controlled.
        :param bio_squad: The Units object of bio units the Medivacs are supporting.
        :param target: The high-level target position for the army.
        :param cache: The global cache for accessing game state.
        :return: A tuple containing (list of command functors, set of handled unit tags).
        """
        actions: List[CommandFunctor] = []
        if not medivacs or not bio_squad.exists:
            return [], set()

        nearby_enemies = cache.enemy_units.closer_than(15, bio_squad.center)

        for medivac in medivacs:
            # --- 1. Survival: Dodge immediate threats ---
            if any(medivac.has_buff(b) for b in DODGE_BUFFS):
                # If caught in a storm or fungal, boost away immediately.
                if medivac.energy >= 10:  # Energy for boost
                    actions.append(
                        lambda m=medivac: m(AbilityId.EFFECT_MEDIVACIGNITEAFTERBURNERS)
                    )
                retreat_pos = medivac.position.towards(nearby_enemies.center, -5)
                actions.append(lambda m=medivac, p=retreat_pos: m.move(p))
                continue  # Skip other logic for this frame

            # --- 2. Find the best unit to heal ---
            heal_target = self._find_best_heal_target(medivac, bio_squad)

            # --- 3. Determine the best position ---
            if heal_target:
                move_pos = self._calculate_safe_heal_position(
                    medivac, heal_target, nearby_enemies
                )
            else:
                move_pos = self._calculate_safe_squad_position(
                    medivac, bio_squad, nearby_enemies
                )

            # --- 4. Decide whether to use boost ---
            if self._should_boost(medivac, bio_squad, target, nearby_enemies, cache):
                actions.append(
                    lambda m=medivac: m(AbilityId.EFFECT_MEDIVACIGNITEAFTERBURNERS)
                )
                cache.logger.debug(f"Medivac {medivac.tag} boosting.")

            # --- 5. Issue the final move command ---
            if medivac.distance_to(move_pos) > 1.5:
                actions.append(lambda m=medivac, p=move_pos: m.move(p))

        # This controller handles all medivacs passed to it.
        return actions, medivacs.tags

    def _should_boost(
        self,
        medivac: "Unit",
        bio_squad: "Units",
        target: Point2,
        enemies: "Units",
        cache: "GlobalCache",
    ) -> bool:
        """Determines if it's a good time for an individual Medivac to boost."""
        # Don't boost if ability is on cooldown or energy is too low.
        if medivac.energy < 10:
            return False

        # --- Retreat Boost ---
        # If the squad is hurt (<60% avg health) and under fire, boost to escape.
        if bio_squad.amount > 0:
            avg_health = (
                sum(u.shield_health_percentage for u in bio_squad) / bio_squad.amount
            )
            if avg_health < 0.6 and enemies.exists:
                return True

        # --- Engage Boost ---
        # If the army is far from its strategic target, consider boosting.
        if bio_squad.center.distance_to(target) > 20:
            # SAFETY CHECK: Do not boost into a known anti-air nest.
            enemies_at_target = cache.known_enemy_units.closer_than(10, target)
            aa_threats = enemies_at_target.of_type(ANTI_AIR_THREATS)
            if aa_threats.amount > 2:
                cache.logger.warning(
                    f"Medivac boost cancelled: {aa_threats.amount} AA threats detected at target."
                )
                return False
            return True

        return False

    def _find_best_heal_target(
        self, medivac: "Unit", bio_squad: "Units"
    ) -> "Unit" | None:
        """Finds the most wounded, non-full-health bio unit near a Medivac."""
        # A "leash" to prevent medivacs from chasing units too far away.
        leash_range = 12

        damaged_bio = bio_squad.filter(
            lambda u: u.health_percentage < 1 and medivac.distance_to(u) < leash_range
        )

        if not damaged_bio.exists:
            return None

        # Return the unit with the lowest health percentage to prioritize focused healing.
        return min(damaged_bio, key=lambda u: u.health_percentage)

    def _calculate_safe_heal_position(
        self, medivac: "Unit", heal_target: "Unit", enemies: "Units"
    ) -> Point2:
        """Calculates a position behind the heal_target, away from enemies."""
        if not enemies.exists:
            # If no enemies, just follow closely behind the target.
            return heal_target.position.towards(medivac.position, HEAL_FOLLOW_DISTANCE)

        # Vector from the center of enemies towards our healing target. This is the "safe" direction.
        safe_vector = enemies.center.direction_vector(heal_target.position)

        # If the vector is zero (units are on top of each other), default to a simple fallback.
        if safe_vector.x == 0 and safe_vector.y == 0:
            return heal_target.position.towards(medivac.position, HEAL_FOLLOW_DISTANCE)

        # The ideal position is a few units behind the heal target along the safe vector.
        return heal_target.position + (safe_vector * HEAL_FOLLOW_DISTANCE)

    def _calculate_safe_squad_position(
        self, medivac: "Unit", bio_squad: "Units", enemies: "Units"
    ) -> Point2:
        """Calculates a safe position behind the entire bio squad when no specific unit needs healing."""
        squad_center = bio_squad.center
        if not enemies.exists:
            return squad_center

        safe_vector = enemies.center.direction_vector(squad_center)
        if safe_vector.x == 0 and safe_vector.y == 0:
            return squad_center  # Fallback if centers overlap

        return squad_center + (safe_vector * HEAL_FOLLOW_DISTANCE)
