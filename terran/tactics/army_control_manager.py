# terran/tactics/army_control_manager.py
from __future__ import annotations
from typing import TYPE_CHECKING, List, Dict, Set

from sc2.ids.unit_typeid import UnitTypeId
from sc2.units import Units
from sc2.position import Point2
from sc2.unit import Unit

from core.interfaces.manager_abc import Manager
from core.types import CommandFunctor
from .squad import Squad, SquadObjective
from .micro_context import MicroContext

# Import all specialist micro-controllers
from terran.specialists.micro.marine_controller import MarineController
from terran.specialists.micro.marauder_controller import MarauderController
from terran.specialists.micro.reaper_controller import ReaperController
from terran.specialists.micro.ghost_controller import GhostController
from terran.specialists.micro.medivac_controller import MedivacController
from terran.specialists.micro.tank_controller import TankController
from terran.specialists.micro.hellion_controller import HellionController
from terran.specialists.micro.cyclone_controller import CycloneController
from terran.specialists.micro.thor_controller import ThorController
from terran.specialists.micro.viking_controller import VikingController
from terran.specialists.micro.liberator_controller import LiberatorController
from terran.specialists.micro.banshee_controller import BansheeController
from terran.specialists.micro.battlecruiser_controller import BattlecruiserController
from terran.specialists.micro.widow_mine_controller import WidowMineController
from terran.specialists.micro.raven_controller import RavenController

if TYPE_CHECKING:
    from sc2.bot_ai import BotAI
    from core.global_cache import GlobalCache
    from core.event_bus import EventBus
    from core.frame_plan import FramePlan

# --- Unit Groupings (Used by TacticalDirector for squad creation) ---
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
    UnitTypeId.WIDOWMINE,
    UnitTypeId.WIDOWMINEBURROWED,
}
AIR_UNIT_TYPES = {
    UnitTypeId.VIKINGFIGHTER,
    UnitTypeId.VIKINGASSAULT,
    UnitTypeId.LIBERATOR,
    UnitTypeId.LIBERATORAG,
    UnitTypeId.BANSHEE,
    UnitTypeId.BATTLECRUISER,
}
SUPPORT_UNIT_TYPES = {UnitTypeId.MEDIVAC, UnitTypeId.RAVEN}

# --- Centralized Army Target Priorities ---
FOCUS_FIRE_PRIORITIES: List[UnitTypeId] = [
    UnitTypeId.SIEGETANKSIEGED,
    UnitTypeId.HIGHTEMPLAR,
    UnitTypeId.DISRUPTOR,
    UnitTypeId.INFESTOR,
    UnitTypeId.BANELING,
    UnitTypeId.LURKERMPBURROWED,
    UnitTypeId.COLOSSUS,
    UnitTypeId.BROODLORD,
    UnitTypeId.CARRIER,
    UnitTypeId.BATTLECRUISER,
    UnitTypeId.ULTRALISK,
    UnitTypeId.THOR,
]


class ArmyControlManager(Manager):
    """
    Field Commander. Orchestrates the army by managing squads, selecting a
    focus-fire target, and delegating control to specialist micro-controllers.
    """

    def __init__(self, bot: "BotAI"):
        super().__init__(bot)
        self.squads: Dict[str, Squad] = {}
        self.controller_map = {
            frozenset({UnitTypeId.MARINE}): MarineController(),
            frozenset({UnitTypeId.MARAUDER}): MarauderController(),
            frozenset({UnitTypeId.REAPER}): ReaperController(),
            frozenset({UnitTypeId.GHOST}): GhostController(),
            frozenset(
                {UnitTypeId.SIEGETANK, UnitTypeId.SIEGETANKSIEGED}
            ): TankController(),
            frozenset(
                {UnitTypeId.HELLION, UnitTypeId.HELLIONTANK}
            ): HellionController(),
            frozenset({UnitTypeId.CYCLONE}): CycloneController(),
            frozenset({UnitTypeId.THOR, UnitTypeId.THORAP}): ThorController(),
            frozenset(
                {UnitTypeId.WIDOWMINE, UnitTypeId.WIDOWMINEBURROWED}
            ): WidowMineController(),
            frozenset(
                {UnitTypeId.VIKINGFIGHTER, UnitTypeId.VIKINGASSAULT}
            ): VikingController(),
            frozenset(
                {UnitTypeId.LIBERATOR, UnitTypeId.LIBERATORAG}
            ): LiberatorController(),
            frozenset({UnitTypeId.BANSHEE}): BansheeController(),
            frozenset({UnitTypeId.BATTLECRUISER}): BattlecruiserController(),
            frozenset({UnitTypeId.RAVEN}): RavenController(),
            frozenset({UnitTypeId.MEDIVAC}): MedivacController(),
        }

    def create_squad(
        self, squad_id: str, units: "Units", objective: SquadObjective, target: "Point2"
    ):
        """Creates a new squad or updates an existing one. Called by the TacticalDirector."""
        if squad_id in self.squads:
            self.squads[squad_id].units.extend(units)
            self.squads[squad_id].objective = objective
            self.squads[squad_id].target = target
        else:
            self.squads[squad_id] = Squad(
                id=squad_id, units=units, objective=objective, target=target
            )
        self.bot.global_cache.logger.info(
            f"Squad '{squad_id}' assigned {len(units)} units. Objective: {objective.name}, Target: {target.rounded if target else 'None'}"
        )

    async def execute(
        self, cache: "GlobalCache", plan: "FramePlan", bus: "EventBus"
    ) -> List[CommandFunctor]:
        self._update_squad_units(cache)
        actions: List[CommandFunctor] = []
        handled_tags: Set[int] = set()

        for squad_id, squad in self.squads.items():
            if squad.is_empty:
                continue

            nearby_enemies = cache.enemy_units.closer_than(20, squad.center)
            focus_target = self._find_focus_fire_target(nearby_enemies, squad.center)

            context = MicroContext(
                units_to_control=Units([], self.bot),
                target=squad.target or plan.rally_point or self.bot.start_location,
                cache=cache,
                plan=plan,
                focus_fire_target=focus_target,
                bio_squad=self.squads.get(
                    "main_bio", Squad("bio", Units([], self.bot))
                ).units,
                mech_squad=self.squads.get(
                    "main_mech", Squad("mech", Units([], self.bot))
                ).units,
                air_squad=self.squads.get(
                    "main_air", Squad("air", Units([], self.bot))
                ).units,
                support_squad=self.squads.get(
                    "main_support", Squad("support", Units([], self.bot))
                ).units,
            )

            for unit_types, controller in self.controller_map.items():
                squad_units_of_type = squad.units.of_type(unit_types)
                if squad_units_of_type.exists:
                    context.units_to_control = squad_units_of_type
                    controller_actions, tags = controller.execute(context)
                    actions.extend(controller_actions)
                    handled_tags.update(tags)

        # Handle any army units that somehow were not assigned to a squad
        unassigned_units = cache.friendly_army_units.tags_not_in(
            self._get_all_assigned_tags()
        )
        if unassigned_units.exists:
            rally = plan.rally_point or self.bot.start_location
            for unit in unassigned_units:
                actions.append(lambda u=unit, t=rally: u.attack(t))

        return actions

    def _get_all_assigned_tags(self) -> Set[int]:
        """Helper to get all tags from all squads."""
        return {tag for squad in self.squads.values() for tag in squad.tags}

    def _update_squad_units(self, cache: "GlobalCache"):
        """Refreshes the units in each squad and removes empty squads."""
        squads_to_remove = []
        for squad_id, squad in self.squads.items():
            squad.units = cache.friendly_army_units.tags_in(squad.tags)
            if squad.is_empty:
                squads_to_remove.append(squad_id)

        for squad_id in squads_to_remove:
            del self.squads[squad_id]
            cache.logger.info(f"Squad '{squad_id}' dissolved as it has no more units.")

    def _find_focus_fire_target(
        self, nearby_enemies: "Units", army_center: Point2
    ) -> Unit | None:
        """Selects the single most important enemy unit for a squad to attack."""
        if not nearby_enemies:
            return None
        for unit_type in FOCUS_FIRE_PRIORITIES:
            targets = nearby_enemies.of_type(unit_type)
            if targets.exists:
                return targets.closest_to(army_center)
        return None
