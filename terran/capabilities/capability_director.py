# terran/capabilities/capability_director.py
from __future__ import annotations
from typing import TYPE_CHECKING, List, Dict

from sc2.ids.unit_typeid import UnitTypeId
from sc2.ids.upgrade_id import UpgradeId

from core.interfaces.director_abc import Director
from core.interfaces.manager_abc import Manager
from core.types import CommandFunctor
from .units.army_unit_manager import ArmyUnitManager
from .structures.tech_structure_manager import TechStructureManager
from .structures.addon_manager import AddonManager
from .upgrades.research_manager import ResearchManager

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
    def __init__(self, bot: "BotAI"):
        super().__init__(bot)
        self.army_unit_manager = ArmyUnitManager(bot)
        self.tech_structure_manager = TechStructureManager(bot)
        self.addon_manager = AddonManager(bot)
        self.research_manager = ResearchManager(bot)
        self.managers: List[Manager] = [
            self.tech_structure_manager,
            self.addon_manager,
            self.research_manager,
            self.army_unit_manager,
        ]
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
        self._set_production_goals(cache, plan)
        actions: list[CommandFunctor] = []
        for manager in self.managers:
            manager_actions = await manager.execute(cache, plan, bus)
            actions.extend(manager_actions)
        return actions

    def _set_production_goals(self, cache: "GlobalCache", plan: "FramePlan"):
        num_bases = self.bot.townhalls.amount
        s = cache.friendly_structures
        p = self.bot.already_pending

        target_army_supply = TARGET_ARMY_SUPPLY_CAP.get(num_bases, 180)
        plan.unit_composition_goal = self._calculate_unit_deficits(
            target_army_supply, cache
        )

        target_structs = self.tech_tree_targets.get(
            num_bases, self.tech_tree_targets[3]
        )
        plan.tech_goals = set()
        for building_id, target_count in target_structs.items():
            current_count = s.of_type(building_id).amount + p(building_id)
            if (
                current_count < target_count
                and self.bot.tech_requirement_progress(building_id) >= 1
            ):
                plan.tech_goals.add(building_id)

        plan.upgrade_goal = self._get_next_upgrade_and_tech(cache, plan)

        target_addons = self.addon_targets.get(num_bases, self.addon_targets[3])
        setattr(plan, "addon_goal", target_addons)

    def _calculate_unit_deficits(
        self, target_army_supply: int, cache: "GlobalCache"
    ) -> Dict[UnitTypeId, int]:
        """Calculates the number of each unit needed to reach the target ratio."""
        deficits = {}

        # --- THIS IS THE CORRECTED LINE ---
        # The 'Unit' object doesn't have supply_cost, we must get it from game_data via the unit's type_id.
        current_army_supply = sum(
            self.bot.game_data.units[u.type_id.value]._proto.food_required
            for u in cache.friendly_army_units
        )
        # --- END OF FIX ---

        if current_army_supply >= target_army_supply:
            return {}

        for unit_id, ratio in TARGET_UNIT_RATIOS.items():
            unit_supply_cost = self.bot.game_data.units[
                unit_id.value
            ]._proto.food_required
            if unit_supply_cost == 0:
                continue

            target_count = int(target_army_supply * ratio / unit_supply_cost)
            current_count = cache.friendly_army_units(
                unit_id
            ).amount + self.bot.already_pending(unit_id)

            if current_count < target_count:
                deficits[unit_id] = target_count

        return deficits

    def _get_next_upgrade_and_tech(
        self, cache: "GlobalCache", plan: "FramePlan"
    ) -> List[UpgradeId]:
        """Finds the next upgrade in the path and ensures its tech requirements are met."""
        upgrades = cache.friendly_upgrades
        p_up = self.bot.already_pending_upgrade

        for upgrade_id in UPGRADE_PRIORITY_PATH:
            if upgrade_id not in upgrades and p_up(upgrade_id) == 0:
                if upgrade_id in {
                    UpgradeId.TERRANINFANTRYWEAPONSLEVEL2,
                    UpgradeId.TERRANINFANTRYARMORSLEVEL2,
                    UpgradeId.TERRANINFANTRYWEAPONSLEVEL3,
                    UpgradeId.TERRANINFANTRYARMORSLEVEL3,
                }:
                    if not (
                        cache.friendly_structures(UnitTypeId.ARMORY).ready.exists
                        or self.bot.already_pending(UnitTypeId.ARMORY)
                    ):
                        plan.tech_goals.add(UnitTypeId.ARMORY)

                return [upgrade_id]
        return []
