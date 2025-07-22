# terran/tactics/army_control_manager.py
from __future__ import annotations
from typing import TYPE_CHECKING, List, Dict, Set, Tuple

from sc2.ids.unit_typeid import UnitTypeId
from sc2.units import Units
from sc2.position import Point2

from core.interfaces.manager_abc import Manager
from core.frame_plan import ArmyStance
from core.types import CommandFunctor
from .squad import Squad

from terran.specialists.micro.marine_controller import MarineController
from terran.specialists.micro.medivac_controller import MedivacController
from terran.specialists.micro.tank_controller import TankController

if TYPE_CHECKING:
    from sc2.bot_ai import BotAI
    from sc2.unit import Unit
    from core.global_cache import GlobalCache
    from core.event_bus import EventBus
    from core.frame_plan import FramePlan

BIO_UNIT_TYPES = {
    UnitTypeId.MARINE,
    UnitTypeId.MARAUDER,
    UnitTypeId.REAPER,
    UnitTypeId.GHOST,
}
MECH_UNIT_TYPES = {
    UnitTypeId.SIEGETANK,
    UnitTypeId.SIEGETANKSIEGED,
    UnitTypeId.HELLION,
    UnitTypeId.HELLIONTANK,
    UnitTypeId.CYCLONE,
    UnitTypeId.THOR,
}
AIR_UNIT_TYPES = {
    UnitTypeId.VIKINGFIGHTER,
    UnitTypeId.LIBERATOR,
    UnitTypeId.BANSHEE,
    UnitTypeId.BATTLECRUISER,
}
SUPPORT_UNIT_TYPES = {UnitTypeId.MEDIVAC, UnitTypeId.RAVEN}


class ArmyControlManager(Manager):
    """
    Field Commander.
    Orchestrates the army by managing dynamic squads and delegating control.
    """

    def __init__(self, bot: "BotAI"):
        super().__init__(bot)
        self.squads: Dict[str, Squad] = {}
        self.marine_controller = MarineController()
        self.medivac_controller = MedivacController()
        self.tank_controller = TankController()

    async def execute(
        self, cache: "GlobalCache", plan: "FramePlan", bus: "EventBus"
    ) -> List[CommandFunctor]:
        self._update_squads(cache)
        target = self._get_army_target(plan, cache)
        if not target:
            return []

        actions: List[CommandFunctor] = []
        handled_tags: Set[int] = set()

        bio_squad = next((s.units for s in self.squads.values() if "bio" in s.id), None)
        mech_squad = next(
            (s.units for s in self.squads.values() if "mech" in s.id), None
        )
        support_squad = next(
            (s.units for s in self.squads.values() if "support" in s.id), None
        )

        if bio_squad and bio_squad.exists:
            marines = bio_squad.of_type(UnitTypeId.MARINE)
            if marines.exists:
                marine_actions, tags = self.marine_controller.execute(
                    marines, target, cache
                )
                actions.extend(marine_actions)
                handled_tags.update(tags)

        if support_squad and support_squad.exists and bio_squad:
            medivacs = support_squad.of_type(UnitTypeId.MEDIVAC)
            if medivacs.exists:
                medivac_actions, tags = self.medivac_controller.execute(
                    medivacs, bio_squad, target, cache, plan
                )
                actions.extend(medivac_actions)
                handled_tags.update(tags)

        if mech_squad and mech_squad.exists:
            tanks = mech_squad.of_type(
                {UnitTypeId.SIEGETANK, UnitTypeId.SIEGETANKSIEGED}
            )
            if tanks.exists:
                tank_actions, tags = self.tank_controller.execute(tanks, target, cache)
                actions.extend(tank_actions)
                handled_tags.update(tags)

        unhandled_units = cache.friendly_army_units.tags_not_in(handled_tags)
        if unhandled_units.exists:
            actions.extend(
                [lambda u=unit, t=target: u.attack(t) for unit in unhandled_units]
            )

        return actions

    def _update_squads(self, cache: "GlobalCache"):
        all_army_units = cache.friendly_army_units
        for squad in self.squads.values():
            squad.units = squad.units.tags_in(all_army_units.tags)
        assigned_tags = {tag for squad in self.squads.values() for tag in squad.tags}
        unassigned_units = all_army_units.tags_not_in(assigned_tags)
        if unassigned_units.exists:
            for unit in unassigned_units:
                self._assign_unit_to_squad(unit, cache)

    def _assign_unit_to_squad(self, unit: "Unit", cache: "GlobalCache"):
        squad_role = self._get_squad_role_for_unit(unit)
        target_squad_id = f"{squad_role}_squad_1"
        if target_squad_id not in self.squads:
            self.squads[target_squad_id] = Squad(
                id=target_squad_id, units=Units([], self.bot)
            )
            cache.logger.info(f"Created new squad: {target_squad_id}")
        self.squads[target_squad_id].units.append(unit)
        cache.logger.info(f"Assigned new {unit.name} to squad '{target_squad_id}'.")

    def _get_squad_role_for_unit(self, unit: "Unit") -> str:
        if unit.type_id in BIO_UNIT_TYPES:
            return "bio"
        if unit.type_id in MECH_UNIT_TYPES:
            return "mech"
        if unit.type_id in AIR_UNIT_TYPES:
            return "air"
        if unit.type_id in SUPPORT_UNIT_TYPES:
            return "support"
        return "default"

    def _get_army_target(self, plan: "FramePlan", cache: "GlobalCache") -> "Point2":
        """Determines the correct target point based on army stance."""
        stance = plan.army_stance

        if stance == ArmyStance.DEFENSIVE:
            return getattr(plan, "defensive_position", self.bot.start_location)

        if stance == ArmyStance.AGGRESSIVE:
            final_target = getattr(plan, "target_location")
            staging_point = getattr(plan, "staging_point")

            if not final_target:
                return getattr(plan, "rally_point", self.bot.start_location)

            main_army_squad = self.squads.get("bio_squad_1") or self.squads.get(
                "mech_squad_1"
            )

            if not main_army_squad or not main_army_squad.units.exists:
                return staging_point or final_target

            # --- MODIFICATION: Robust check for when to leave the staging point ---
            # Instead of checking the squad's center, check if a high percentage of the squad
            # has arrived at the staging area. This is more reliable for spread-out armies.
            if staging_point:
                gathered_units_count = main_army_squad.units.closer_than(
                    15, staging_point
                ).amount
                squad_total_count = main_army_squad.units.amount

                # Only attack if more than 80% of the squad is gathered.
                if (gathered_units_count / squad_total_count) < 0.8:
                    cache.logger.debug(
                        f"Army gathering at staging point ({gathered_units_count}/{squad_total_count})."
                    )
                    return staging_point

            cache.logger.debug("Army is staged. Attacking final target.")
            return final_target

        return getattr(plan, "rally_point", self.bot.start_location)
