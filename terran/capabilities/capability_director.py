# terran/capabilities/capability_director.py
from __future__ import annotations
from typing import TYPE_CHECKING, List, Dict

from sc2.ids.unit_typeid import UnitTypeId
from sc2.ids.upgrade_id import UpgradeId

from core.interfaces.director_abc import Director
from core.interfaces.manager_abc import Manager
from core.types import CommandFunctor

# Import the new specialized managers
from .structures.production_structure_manager import ProductionStructureManager
from .production.barracks_manager import BarracksManager
from .production.factory_manager import FactoryManager
from .production.starport_manager import StarportManager
from .upgrades.engineering_bay_manager import EngineeringBayManager
from .upgrades.armory_manager import ArmoryManager

if TYPE_CHECKING:
    from sc2.bot_ai import BotAI
    from core.global_cache import GlobalCache
    from core.event_bus import EventBus
    from core.frame_plan import FramePlan

# --- Strategic Production Configuration ---
TARGET_ARMY_SUPPLY_CAP: Dict[int, int] = {1: 40, 2: 100, 3: 160, 4: 180}
TARGET_UNIT_RATIOS: Dict[UnitTypeId, float] = {
    UnitTypeId.MARINE: 0.60,
    UnitTypeId.MARAUDER: 0.20,
    UnitTypeId.MEDIVAC: 0.10,
    UnitTypeId.SIEGETANK: 0.05,
    UnitTypeId.VIKINGFIGHTER: 0.05,
}
UPGRADE_PRIORITY_PATH: List[UpgradeId] = [
    UpgradeId.STIMPACK,
    UpgradeId.SHIELDWALL,
    UpgradeId.TERRANINFANTRYWEAPONSLEVEL1,
    UpgradeId.TERRANINFANTRYARMORSLEVEL1,
    UpgradeId.TERRANINFANTRYWEAPONSLEVEL2,
    UpgradeId.TERRANVEHICLEWEAPONSLEVEL1,
    UpgradeId.TERRANINFANTRYARMORSLEVEL2,
    UpgradeId.TERRANINFANTRYWEAPONSLEVEL3,
    UpgradeId.TERRANINFANTRYARMORSLEVEL3,
]


class CapabilityDirector(Director):
    """
    Orchestrates all production and technology managers.
    This director's role is to define the strategic "what" (what units,
    upgrades, structures, and addons to aim for) and populate the FramePlan.
    It then delegates the "how" (executing the builds and research) to its
    specialized managers.
    """

    def __init__(self, bot: "BotAI"):
        super().__init__(bot)
        # Instantiate all specialized managers
        self.production_structure_manager = ProductionStructureManager(bot)
        self.barracks_manager = BarracksManager(bot)
        self.factory_manager = FactoryManager(bot)
        self.starport_manager = StarportManager(bot)
        self.engineering_bay_manager = EngineeringBayManager(bot)
        self.armory_manager = ArmoryManager(bot)

        # Define the execution order
        self.managers: List[Manager] = [
            self.production_structure_manager,
            self.engineering_bay_manager,
            self.armory_manager,
            self.barracks_manager,
            self.factory_manager,
            self.starport_manager,
        ]

        # Defines which production structures are desired at each base count
        self.tech_tree_targets: Dict[int, Dict[UnitTypeId, int]] = {
            1: {
                UnitTypeId.BARRACKS: 1,
                UnitTypeId.FACTORY: 1,
                UnitTypeId.ENGINEERINGBAY: 1,
            },
            2: {
                UnitTypeId.BARRACKS: 3,
                UnitTypeId.FACTORY: 1,
                UnitTypeId.STARPORT: 1,
                UnitTypeId.ENGINEERINGBAY: 1,
                UnitTypeId.ARMORY: 1,
            },
            3: {
                UnitTypeId.BARRACKS: 5,
                UnitTypeId.FACTORY: 2,
                UnitTypeId.STARPORT: 1,
                UnitTypeId.ENGINEERINGBAY: 1,
                UnitTypeId.ARMORY: 1,
            },
        }
        # Defines the target number of each addon type at each base count
        self.addon_targets: Dict[int, Dict[UnitTypeId, int]] = {
            1: {UnitTypeId.BARRACKSTECHLAB: 1, UnitTypeId.FACTORYTECHLAB: 1},
            2: {
                UnitTypeId.BARRACKSTECHLAB: 1,
                UnitTypeId.BARRACKSREACTOR: 2,
                UnitTypeId.FACTORYTECHLAB: 1,
                UnitTypeId.STARPORTTECHLAB: 1,
            },
            3: {
                UnitTypeId.BARRACKSTECHLAB: 2,
                UnitTypeId.BARRACKSREACTOR: 3,
                UnitTypeId.FACTORYTECHLAB: 1,
                UnitTypeId.STARPORTTECHLAB: 1,
            },
        }

    async def execute(
        self, cache: "GlobalCache", plan: "FramePlan", bus: "EventBus"
    ) -> list[CommandFunctor]:
        # 1. Director-level logic: Determine goals and populate the FramePlan
        self._set_production_goals(cache, plan)

        # 2. Manager execution: Delegate actions to specialized managers
        actions: list[CommandFunctor] = []
        for manager in self.managers:
            manager_actions = await manager.execute(cache, plan, bus)
            actions.extend(manager_actions)
        return actions

    def _set_production_goals(self, cache: "GlobalCache", plan: "FramePlan"):
        """Populates the FramePlan with the strategic goals for this frame."""
        num_bases = self.bot.townhalls.amount
        s = cache.friendly_structures
        p = self.bot.already_pending

        # --- Goal 1: Set desired army composition ---
        target_army_supply = TARGET_ARMY_SUPPLY_CAP.get(num_bases, 180)
        plan.unit_composition_goal = self._calculate_unit_goals(
            target_army_supply, cache
        )

        # --- Goal 2: Set desired tech structures ---
        target_structs = self.tech_tree_targets.get(
            num_bases, self.tech_tree_targets[3]
        )
        plan.tech_goals = set()
        for building_id, target_count in target_structs.items():
            current_count = s.of_type(building_id).amount + p(building_id)
            if current_count < target_count:
                plan.tech_goals.add(building_id)

        # --- Goal 3: Set desired upgrade ---
        plan.upgrade_goal = self._get_next_upgrade(cache)

        # --- Goal 4: Set desired addons ---
        plan.addon_goal = self.addon_targets.get(num_bases, self.addon_targets[3])

    def _calculate_unit_goals(
        self, target_army_supply: int, cache: "GlobalCache"
    ) -> Dict[UnitTypeId, int]:
        """Calculates the target number of each unit based on the desired ratio."""
        goals = {}
        for unit_id, ratio in TARGET_UNIT_RATIOS.items():
            unit_supply_cost = self.bot.game_data.units[
                unit_id.value
            ]._proto.food_required
            if unit_supply_cost > 0:
                goals[unit_id] = int(target_army_supply * ratio / unit_supply_cost)
        return goals

    def _get_next_upgrade(self, cache: "GlobalCache") -> List[UpgradeId]:
        """Finds the next upgrade in the priority path that is not yet started."""
        for upgrade_id in UPGRADE_PRIORITY_PATH:
            if (
                upgrade_id not in cache.friendly_upgrades
                and self.bot.already_pending_upgrade(upgrade_id) == 0
            ):
                return [upgrade_id]
        return []
