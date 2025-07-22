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


class CapabilityDirector(Director):
    """
    The Quartermaster. Plans all production and technology.
    This director now uses a target-based system to define the desired
    number of tech buildings, allowing for parallel and scalable construction goals.
    """

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

        # --- Desired Tech Tree Targets ---
        # Defines the target count for each structure based on number of bases.
        self.tech_tree_targets: Dict[int, Dict[UnitTypeId, int]] = {
            1: {  # On 1 base
                UnitTypeId.BARRACKS: 1,
                UnitTypeId.FACTORY: 1,
                UnitTypeId.ENGINEERINGBAY: 1,
            },
            2: {  # On 2 bases
                UnitTypeId.BARRACKS: 3,
                UnitTypeId.FACTORY: 1,
                UnitTypeId.STARPORT: 1,
                UnitTypeId.ENGINEERINGBAY: 1,
                UnitTypeId.ARMORY: 1,
            },
            3: {  # On 3+ bases
                UnitTypeId.BARRACKS: 5,
                UnitTypeId.FACTORY: 1,
                UnitTypeId.STARPORT: 2,
                UnitTypeId.ENGINEERINGBAY: 2,
                UnitTypeId.ARMORY: 1,
                UnitTypeId.FUSIONCORE: 1,
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
        """
        Determines ALL immediate production needs and writes them to the FramePlan.
        """
        s = cache.friendly_structures
        p = self.bot.already_pending

        # --- Unit Composition Goal ---
        plan.unit_composition_goal = {
            UnitTypeId.MARINE: 20,
            UnitTypeId.MARAUDER: 5,
            UnitTypeId.MEDIVAC: 3,
            UnitTypeId.VIKINGFIGHTER: 2,
            UnitTypeId.SIEGETANK: 2,
        }

        # --- Tech Structure Goals ---
        num_bases = self.bot.townhalls.amount
        target_counts = self.tech_tree_targets.get(num_bases, self.tech_tree_targets[3])

        plan.tech_goals = set()
        for building_id, target_count in target_counts.items():
            current_count = s.of_type(building_id).amount + p(building_id)
            if (
                current_count < target_count
                and self.bot.tech_requirement_progress(building_id) >= 1
            ):
                plan.tech_goals.add(building_id)

        # --- Upgrade Goals ---
        plan.upgrade_goal = self._get_upgrade_priorities(cache)

    def _get_upgrade_priorities(self, cache: "GlobalCache") -> List[UpgradeId]:
        """Calculates the prioritized list of upgrades to research."""
        s = cache.friendly_structures
        upgrades = cache.friendly_upgrades
        p_up = self.bot.already_pending_upgrade

        priority_list = []

        # Stim and Shields are top priority
        if s.of_type(UnitTypeId.BARRACKSTECHLAB).ready.exists:
            if UpgradeId.STIMPACK not in upgrades and p_up(UpgradeId.STIMPACK) == 0:
                priority_list.append(UpgradeId.STIMPACK)
            if UpgradeId.SHIELDWALL not in upgrades and p_up(UpgradeId.SHIELDWALL) == 0:
                priority_list.append(UpgradeId.SHIELDWALL)

        # Infantry Weapons and Armor
        if s.of_type(UnitTypeId.ENGINEERINGBAY).ready.exists:
            if (
                UpgradeId.TERRANINFANTRYWEAPONSLEVEL1 not in upgrades
                and p_up(UpgradeId.TERRANINFANTRYWEAPONSLEVEL1) == 0
            ):
                priority_list.append(UpgradeId.TERRANINFANTRYWEAPONSLEVEL1)
            elif (
                UpgradeId.TERRANINFANTRYARMORSLEVEL1 not in upgrades
                and p_up(UpgradeId.TERRANINFANTRYARMORSLEVEL1) == 0
            ):
                priority_list.append(UpgradeId.TERRANINFANTRYARMORSLEVEL1)

        # Add more logic for Level 2/3 upgrades which require an Armory
        if s.of_type(UnitTypeId.ARMORY).ready.exists:
            if (
                UpgradeId.TERRANINFANTRYWEAPONSLEVEL1 in upgrades
                and UpgradeId.TERRANINFANTRYWEAPONSLEVEL2 not in upgrades
                and p_up(UpgradeId.TERRANINFANTRYWEAPONSLEVEL2) == 0
            ):
                priority_list.append(UpgradeId.TERRANINFANTRYWEAPONSLEVEL2)
            if (
                UpgradeId.TERRANINFANTRYARMORSLEVEL1 in upgrades
                and UpgradeId.TERRANINFANTRYARMORSLEVEL2 not in upgrades
                and p_up(UpgradeId.TERRANINFANTRYARMORSLEVEL2) == 0
            ):
                priority_list.append(UpgradeId.TERRANINFANTRYARMORSLEVEL2)

        return priority_list
