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

ARMORY_UPGRADES: Set[UpgradeId] = {
    UpgradeId.TERRANVEHICLEWEAPONSLEVEL1,
    UpgradeId.TERRANVEHICLEWEAPONSLEVEL2,
    UpgradeId.TERRANVEHICLEWEAPONSLEVEL3,
    UpgradeId.TERRANSHIPWEAPONSLEVEL1,
    UpgradeId.TERRANSHIPWEAPONSLEVEL2,
    UpgradeId.TERRANSHIPWEAPONSLEVEL3,
    UpgradeId.TERRANVEHICLEANDSHIPARMORSLEVEL1,
    UpgradeId.TERRANVEHICLEANDSHIPARMORSLEVEL2,
    UpgradeId.TERRANVEHICLEANDSHIPARMORSLEVEL3,
}


class ArmoryManager(Manager):
    """
    Manages all Armories and the vehicle/ship upgrades they provide.
    """

    def __init__(self, bot: "BotAI"):
        super().__init__(bot)

    async def execute(
        self, cache: "GlobalCache", plan: "FramePlan", bus: "EventBus"
    ) -> List[CommandFunctor]:
        """
        Checks the FramePlan for a prioritized upgrade and starts it if possible.
        """
        armories = cache.friendly_structures.of_type(UnitTypeId.ARMORY).ready
        if not armories.exists:
            return []

        upgrade_priority_list = getattr(plan, "upgrade_goal", [])
        if not upgrade_priority_list:
            return []

        next_upgrade = upgrade_priority_list[0]

        # This manager only handles upgrades researched at the Armory.
        if next_upgrade not in ARMORY_UPGRADES:
            return []

        # Check affordability and if an Armory is available.
        if self.bot.can_afford(next_upgrade):
            idle_armories = armories.idle
            if idle_armories.exists:
                armory_to_use = idle_armories.first
                cache.logger.info(
                    f"ArmoryManager starting research: {next_upgrade.name}"
                )
                return [lambda a=armory_to_use, u=next_upgrade: a.research(u)]

        return []
