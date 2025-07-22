from __future__ import annotations
from typing import TYPE_CHECKING, List, Dict, Set, Tuple

from sc2.ids.unit_typeid import UnitTypeId
from sc2.units import Units
from sc2.position import Point2

from core.interfaces.manager_abc import Manager
from core.frame_plan import ArmyStance
from core.types import CommandFunctor

# Import the specialist micro-controllers
from terran.specialists.micro.marine_controller import MarineController
from terran.specialists.micro.medivac_controller import MedivacController
from terran.specialists.micro.tank_controller import TankController

if TYPE_CHECKING:
    from sc2.bot_ai import BotAI
    from sc2.unit import Unit
    from core.global_cache import GlobalCache
    from core.event_bus import EventBus
    from core.frame_plan import FramePlan

# Define which units belong to which squad type for automatic assignment.
BIO_UNIT_TYPES = {
    UnitTypeId.MARINE,
    UnitTypeId.MARAUDER,
    UnitTypeId.REAPER,
    UnitTypeId.GHOST,
}
MECH_UNIT_TYPES = {
    UnitTypeId.SIEGETANK,
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

    This manager orchestrates the army's high-level movements and actions.
    It translates the TacticalDirector's plan (stance and target) into concrete
    squad-based commands, delegating the complex micro-management to specialist
    controllers.
    """

    def __init__(self, bot: "BotAI"):
        super().__init__(bot)
        # Squads are stateful, stored as a dictionary mapping a squad name to a Units object.
        self.squads: Dict[str, Units] = {}

        # Instantiate micro-controllers once to maintain their state if needed.
        self.marine_controller = MarineController()
        self.medivac_controller = MedivacController()
        self.tank_controller = TankController()

    async def execute(
        self, cache: "GlobalCache", plan: "FramePlan", bus: "EventBus"
    ) -> List[CommandFunctor]:
        """
        Updates squads, determines targets based on stance, and delegates control.
        """
        # 1. Maintain Squads: Update unit membership based on new/dead units.
        self._update_squads(cache)

        # 2. Determine Target: Decide where each squad should be going this frame.
        target = self._get_squad_target(plan, cache)
        if not target:
            return []  # No valid target this frame.

        # 3. Delegate to Micro-Controllers and Issue Commands.
        actions: List[CommandFunctor] = []
        handled_tags: Set[int] = set()

        # Get primary combat squads
        bio_squad = self.squads.get("bio_squad_1")
        mech_squad = self.squads.get("mech_squad_1")
        support_squad = self.squads.get("support_squad_1")

        # --- Delegate Bio Control ---
        if bio_squad:
            marines = bio_squad.of_type(UnitTypeId.MARINE)
            if marines:
                marine_actions, marine_tags = self.marine_controller.execute(
                    marines, target, cache
                )
                actions.extend(marine_actions)
                handled_tags.update(marine_tags)
            # Add other bio controllers (e.g., MarauderController) here in the future.

        # --- Delegate Support Control ---
        if support_squad and bio_squad:
            medivacs = support_squad.of_type(UnitTypeId.MEDIVAC)
            if medivacs:
                medivac_actions, medivac_tags = self.medivac_controller.execute(
                    medivacs, bio_squad, target, cache
                )
                actions.extend(medivac_actions)
                handled_tags.update(medivac_tags)

        # --- Delegate Mech Control ---
        if mech_squad:
            tanks = mech_squad.of_type(
                {UnitTypeId.SIEGETANK, UnitTypeId.SIEGETANKSIEGED}
            )
            if tanks:
                tank_actions, tank_tags = self.tank_controller.execute(
                    tanks, target, cache
                )
                actions.extend(tank_actions)
                handled_tags.update(tank_tags)

        # --- Fallback for unhandled units ---
        # Any unit in a squad not handled by a micro-controller gets a default attack command.
        for squad in self.squads.values():
            unhandled_units = squad.tags_not_in(handled_tags)
            if unhandled_units.exists:
                # Generate one lambda FOR EACH unit in the unhandled group.
                actions.extend(
                    [lambda u=unit, t=target: u.attack(t) for unit in unhandled_units]
                )

        return actions

    def _update_squads(self, cache: "GlobalCache"):
        """Maintains squad compositions, removing dead units and assigning new ones."""
        all_army_tags = cache.friendly_army_units.tags

        # Remove dead units from squads by rebuilding them with only alive units.
        for squad_name, squad in self.squads.items():
            current_tags = squad.tags
            alive_tags = current_tags.intersection(all_army_tags)
            if len(alive_tags) < len(current_tags):
                self.squads[squad_name] = cache.friendly_army_units.tags_in(alive_tags)

        # Find and assign new (unassigned) units.
        assigned_tags = {tag for squad in self.squads.values() for tag in squad.tags}
        new_unit_tags = all_army_tags - assigned_tags

        if new_unit_tags:
            new_units = cache.friendly_army_units.tags_in(new_unit_tags)
            for unit in new_units:
                squad_name = self._get_squad_name_for_unit(unit)
                if squad_name not in self.squads:
                    self.squads[squad_name] = Units([], self.bot)
                self.squads[squad_name].append(unit)
                cache.logger.info(f"Assigned new {unit.name} to squad '{squad_name}'.")

    def _get_squad_name_for_unit(self, unit: "Unit") -> str:
        """Classifies a unit into a squad category."""
        if unit.type_id in BIO_UNIT_TYPES:
            return "bio_squad_1"
        if unit.type_id in MECH_UNIT_TYPES:
            return "mech_squad_1"
        if unit.type_id in AIR_UNIT_TYPES:
            return "air_squad_1"
        if unit.type_id in SUPPORT_UNIT_TYPES:
            return "support_squad_1"
        return "default_squad"

    def _get_squad_target(
        self, plan: "FramePlan", cache: "GlobalCache"
    ) -> "Point2" | None:
        """
        Determines the correct target point based on army stance. This implements
        the crucial logic for rallying, staging, and attacking.
        """
        stance = plan.army_stance

        if stance == ArmyStance.DEFENSIVE:
            return getattr(plan, "defensive_position", None)

        if stance == ArmyStance.AGGRESSIVE:
            final_target_pos = getattr(plan, "target_location", None)
            staging_point = getattr(plan, "staging_point", None)

            # If no staging point is defined (e.g., early game), attack directly.
            if not staging_point or not final_target_pos:
                return final_target_pos

            # Use the main combat squad to determine the army's center of mass.
            main_army = self.squads.get("bio_squad_1") or self.squads.get(
                "mech_squad_1"
            )

            # If no army exists yet, the first units should move to the staging point.
            if not main_army or not main_army.exists:
                return staging_point

            # Smart Staging Logic: If the army is not yet at the staging point, the target IS the staging point.
            # Once gathered, the target becomes the final enemy location.
            if main_army.center.distance_to(staging_point) > 15:
                cache.logger.debug("Army moving to staging point.")
                return staging_point
            else:
                cache.logger.debug("Army is staged. Attacking final target.")
                return final_target_pos

        # Default for any other stance (or if no specific target is set).
        return getattr(plan, "rally_point", None)
