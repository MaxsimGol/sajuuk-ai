# terran/specialists/micro/raven_controller.py
from __future__ import annotations
from typing import TYPE_CHECKING, List, Set, Tuple

from sc2.ids.unit_typeid import UnitTypeId
from sc2.ids.ability_id import AbilityId
from sc2.position import Point2
from sc2.unit import Unit

from core.interfaces.controller_abc import ControllerABC
from core.types import CommandFunctor
from terran.tactics.micro_context import MicroContext

if TYPE_CHECKING:
    from sc2.units import Units

# --- Tunable Constants ---
ENGAGEMENT_RANGE = 18
LEASH_DISTANCE = 8  # Ravens should stay far back
ANTI_ARMOR_ENERGY = 75
INTERFERENCE_MATRIX_ENERGY = 50
AUTO_TURRET_ENERGY = 50
AUTO_TURRET_DUMP_ENERGY = 125  # Use turrets if energy is high

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
INTERFERENCE_MATRIX_TARGETS: Set[UnitTypeId] = {
    UnitTypeId.SIEGETANK,
    UnitTypeId.SIEGETANKSIEGED,
    UnitTypeId.THOR,
    UnitTypeId.BATTLECRUISER,
    UnitTypeId.CARRIER,
    UnitTypeId.MOTHERSHIP,
    UnitTypeId.TEMPEST,
    UnitTypeId.COLOSSUS,
    UnitTypeId.IMMORTAL,
    UnitTypeId.HIGHTEMPLAR,
    UnitTypeId.INFESTOR,
}


class RavenController(ControllerABC):
    """
    Support Caster Specialist. Manages Ravens to deploy turrets and debuff
    the enemy army while staying at a safe distance.
    """

    def execute(self, context: "MicroContext") -> Tuple[List[CommandFunctor], Set[int]]:
        """
        Executes micro-management for a squad of Ravens.
        """
        # --- Unpack Context ---
        ravens = context.units_to_control
        strategic_target = context.target
        cache = context.cache
        plan = context.plan

        actions: List[CommandFunctor] = []
        if not ravens:
            return [], set()

        # Get main army squad for positioning
        main_army = context.bio_squad or context.mech_squad or Units([], self.bot)
        nearby_enemies = cache.enemy_units.closer_than(ENGAGEMENT_RANGE, ravens.center)

        for raven in ravens:
            action = self._handle_single_raven(
                raven, nearby_enemies, strategic_target, main_army, cache, plan
            )
            if action:
                actions.append(action)

        return actions, ravens.tags

    def _handle_single_raven(
        self,
        raven: Unit,
        nearby_enemies: "Units",
        strategic_target: "Point2",
        main_army: "Units",
        cache: "GlobalCache",
        plan: "FramePlan",
    ) -> CommandFunctor | None:
        """The core decision tree for an individual Raven."""

        # 1. Survival: Retreat if directly threatened by anti-air.
        air_threats = nearby_enemies.of_type(ANTI_AIR_THREATS)
        if air_threats.closer_than(9, raven).exists:
            safe_position = raven.position.towards(air_threats.center, -5)
            return lambda r=raven, p=safe_position: r.move(p)

        # 2. Spell Usage: Find the best spell to cast.
        spell_action = self._use_spells(raven, nearby_enemies, main_army, cache)
        if spell_action:
            return spell_action

        # 3. Positioning: Leash behind the main army.
        if main_army.exists:
            safe_position = self._calculate_safe_leash_point(
                raven, main_army, nearby_enemies
            )
            if raven.distance_to(safe_position) > 3:
                return lambda r=raven, p=safe_position: r.move(p)

        return None

    def _use_spells(
        self,
        raven: Unit,
        nearby_enemies: "Units",
        main_army: "Units",
        cache: "GlobalCache",
    ) -> CommandFunctor | None:
        """Selects and executes the best spell for the current situation."""

        # Priority 1: Anti-Armor Missile on valuable clumps.
        if raven.energy >= ANTI_ARMOR_ENERGY:
            target_point = self._find_best_anti_armor_target(raven, nearby_enemies)
            if target_point:
                cache.logger.info(f"Raven {raven.tag} casting Anti-Armor Missile.")
                return lambda r=raven, p=target_point: r(
                    AbilityId.EFFECT_ANTIARMORMISSILE, p
                )

        # Priority 2: Interference Matrix on a key unit.
        if raven.energy >= INTERFERENCE_MATRIX_ENERGY:
            target_unit = self._find_best_interference_matrix_target(
                raven, nearby_enemies
            )
            if target_unit:
                cache.logger.info(
                    f"Raven {raven.tag} casting Interference Matrix on {target_unit.name}."
                )
                return lambda r=raven, t=target_unit: r(
                    AbilityId.EFFECT_INTERFERENCEMATRIX, t
                )

        # Priority 3: Auto-Turret as an energy dump or for extra DPS.
        if raven.energy >= AUTO_TURRET_DUMP_ENERGY:
            placement_pos = self._find_best_turret_position(raven, main_army)
            if placement_pos:
                cache.logger.info(f"Raven {raven.tag} deploying Auto-Turret.")
                return lambda r=raven, p=placement_pos: r(
                    AbilityId.BUILDAUTOTURRET_AUTOTURRET, p
                )

        return None

    def _find_best_anti_armor_target(
        self, raven: Unit, nearby_enemies: "Units"
    ) -> Point2 | None:
        """Finds the densest clump of armored units."""
        armored_enemies = nearby_enemies.filter(lambda u: u.is_armored).closer_than(
            10, raven
        )
        if armored_enemies.amount < 4:
            return None

        return armored_enemies.center

    def _find_best_interference_matrix_target(
        self, raven: Unit, nearby_enemies: "Units"
    ) -> Unit | None:
        """Finds the highest-priority mechanical or psionic unit in range."""
        targets_in_range = nearby_enemies.of_type(
            INTERFERENCE_MATRIX_TARGETS
        ).closer_than(9, raven)
        return (
            targets_in_range.sorted(lambda u: u.cost, reverse=True).first
            if targets_in_range.exists
            else None
        )

    def _find_best_turret_position(
        self, raven: Unit, main_army: "Units"
    ) -> Point2 | None:
        """Finds a forward position to drop a turret."""
        if main_army.exists:
            return main_army.center.towards(self.bot.enemy_start_locations[0], 5)
        return None

    def _calculate_safe_leash_point(
        self, raven: Unit, main_army: "Units", enemies: "Units"
    ) -> Point2:
        """Calculates a follow position behind the main army, away from threats."""
        target_center = main_army.center
        if not enemies.exists:
            return target_center.towards(raven.position, -LEASH_DISTANCE)

        safe_vector = enemies.center.direction_vector(target_center)
        if safe_vector.x == 0 and safe_vector.y == 0:
            return target_center.towards(self.bot.start_location, -LEASH_DISTANCE)

        return target_center + (safe_vector * LEASH_DISTANCE)
