from __future__ import annotations
from typing import TYPE_CHECKING, List, Set

from sc2.ids.unit_typeid import UnitTypeId

from core.interfaces.manager_abc import Manager
from core.types import CommandFunctor
from core.utilities.events import Event, EventType, EnemyTechScoutedPayload
from core.utilities.constants import SCOUT_AT_SUPPLY

if TYPE_CHECKING:
    from sc2.bot_ai import BotAI
    from sc2.unit import Unit
    from sc2.units import Units
    from core.global_cache import GlobalCache
    from core.event_bus import EventBus
    from core.frame_plan import FramePlan

KEY_ENEMY_TECH_STRUCTURES: Set[UnitTypeId] = {
    UnitTypeId.SPAWNINGPOOL,
    UnitTypeId.ROACHWARREN,
    UnitTypeId.BANELINGNEST,
    UnitTypeId.LAIR,
    UnitTypeId.HYDRALISKDEN,
    UnitTypeId.SPIRE,
    UnitTypeId.HIVE,
    UnitTypeId.FACTORY,
    UnitTypeId.STARPORT,
    UnitTypeId.ARMORY,
    UnitTypeId.FUSIONCORE,
    UnitTypeId.CYBERNETICSCORE,
    UnitTypeId.TWILIGHTCOUNCIL,
    UnitTypeId.STARGATE,
    UnitTypeId.ROBOTICSFACILITY,
    UnitTypeId.TEMPLARARCHIVE,
    UnitTypeId.DARKSHRINE,
}


class ScoutingManager(Manager):
    """
    Intelligence Agency.
    """

    def __init__(self, bot: "BotAI"):
        super().__init__(bot)
        self.scout_tag: int | None = None
        self._scouting_plan: List[tuple[float, float]] = []
        self._known_enemy_tech: Set[UnitTypeId] = set()

    async def execute(
        self, cache: "GlobalCache", plan: "FramePlan", bus: "EventBus"
    ) -> List[CommandFunctor]:
        if self.scout_tag is None or not cache.friendly_units.find_by_tag(
            self.scout_tag
        ):
            self._assign_new_scout(cache)
            if self.scout_tag is None:
                return []

        scout: Unit | None = cache.friendly_units.find_by_tag(self.scout_tag)
        if not scout:
            self.scout_tag = None
            return []

        self._analyze_and_publish(scout, cache, bus)

        if not self._scouting_plan:
            self._generate_scouting_plan(cache)

        if not self._scouting_plan:
            return []

        target_pos = self._scouting_plan[0]
        if scout.distance_to(target_pos) < 5:
            self._scouting_plan.pop(0)
            if not self._scouting_plan:
                return []

        return [lambda s=scout, t=target_pos: s.move(t)]

    def _assign_new_scout(self, cache: "GlobalCache"):
        """Selects and assigns the best available unit to be the scout."""
        # CHANGED: Use cache.iteration instead of self.bot.iteration
        if cache.supply_used >= SCOUT_AT_SUPPLY and cache.iteration < 22.4 * 120:
            worker = cache.friendly_workers.closest_to(self.bot.game_info.map_center)
            if worker:
                self.scout_tag = worker.tag
                cache.logger.info(
                    f"Assigning SCV (tag: {self.scout_tag}) as the initial scout."
                )
                return

        reapers = cache.friendly_army_units.of_type(UnitTypeId.REAPER)
        if reapers.exists:
            self.scout_tag = reapers.first.tag
            cache.logger.info(f"Assigning Reaper (tag: {self.scout_tag}) as scout.")
            return

    def _generate_scouting_plan(self, cache: "GlobalCache"):
        """Creates a list of points for the scout to visit."""
        enemy_start = self.bot.enemy_start_locations[0]

        expansion_locations = sorted(
            self.bot.expansion_locations_list,
            key=lambda loc: loc.distance_to(enemy_start),
        )

        self._scouting_plan = [enemy_start] + expansion_locations
        cache.logger.info("Generated a new scouting plan.")

    def _analyze_and_publish(self, scout: Unit, cache: "GlobalCache", bus: "EventBus"):
        """Checks what the scout sees and publishes events for new tech."""
        visible_enemies: "Units" = cache.enemy_structures.closer_than(
            scout.sight_range, scout
        )

        for enemy in visible_enemies:
            if enemy.type_id in KEY_ENEMY_TECH_STRUCTURES:
                if enemy.type_id not in self._known_enemy_tech:
                    self._known_enemy_tech.add(enemy.type_id)
                    payload = EnemyTechScoutedPayload(tech_id=enemy.type_id)
                    bus.publish(Event(EventType.TACTICS_ENEMY_TECH_SCOUTED, payload))
                    cache.logger.warning(
                        f"CRITICAL INTEL: Scout discovered new enemy tech: {enemy.type_id.name}"
                    )
