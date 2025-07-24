# terran/capabilities/upgrades/engineering_bay_manager.py
from __future__ import annotations
from typing import TYPE_CHECKING, List, Set

from sc2.ids.unit_typeid import UnitTypeId
from sc2.ids.upgrade_id import UpgradeId

from core.interfaces.manager_abc import Manager
from core.types import CommandFunctor

if TYPE_CHECKING:
    from sc2.bot_ai import BotAI
    from core.global_cache import GlobalCache
    from core.event_bus import EventBus
    from core.frame_plan import FramePlan

ENGINEERINGBAY_UPGRADES: Set[UpgradeId] = {
    UpgradeId.TERRANINFANTRYWEAPONSLEVEL1,
    UpgradeId.TERRANINFANTRYWEAPONSLEVEL2,
    UpgradeId.TERRANINFANTRYWEAPONSLEVEL3,
    UpgradeId.TERRANINFANTRYARMORSLEVEL1,
    UpgradeId.TERRANINFANTRYARMORSLEVEL2,
    UpgradeId.TERRANINFANTRYARMORSLEVEL3,
    UpgradeId.HISECAUTOTRACKING,
    UpgradeId.TERRANBUILDINGARMOR,
}


class EngineeringBayManager(Manager):
    """
    Manages all Engineering Bays and the upgrades they provide.
    """

    def __init__(self, bot: "BotAI"):
        super().__init__(bot)

    async def execute(
        self, cache: "GlobalCache", plan: "FramePlan", bus: "EventBus"
    ) -> List[CommandFunctor]:
        """
        Checks the FramePlan for a prioritized upgrade and starts it if possible.
        """
        eng_bays = cache.friendly_structures.of_type(UnitTypeId.ENGINEERINGBAY).ready
        if not eng_bays.exists:
            return []

        upgrade_priority_list = getattr(plan, "upgrade_goal", [])
        if not upgrade_priority_list:
            return []

        next_upgrade = upgrade_priority_list[0]

        # This manager only handles upgrades researched at the Engineering Bay.
        if next_upgrade not in ENGINEERINGBAY_UPGRADES:
            return []

        # Check affordability and if an Eng Bay is available.
        if self.bot.can_afford(next_upgrade):
            idle_bays = eng_bays.idle
            if idle_bays.exists:
                bay_to_use = idle_bays.first
                cache.logger.info(
                    f"EngineeringBayManager starting research: {next_upgrade.name}"
                )
                return [lambda b=bay_to_use, u=next_upgrade: b.research(u)]

        return []
