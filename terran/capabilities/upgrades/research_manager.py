# terran/capabilities/upgrades/research_manager.py
from __future__ import annotations
from typing import TYPE_CHECKING, List

from sc2.ids.upgrade_id import UpgradeId
from sc2.dicts.upgrade_researched_from import UPGRADE_RESEARCHED_FROM
from sc2.dicts.unit_research_abilities import RESEARCH_INFO

from core.interfaces.manager_abc import Manager
from core.types import CommandFunctor

if TYPE_CHECKING:
    from sc2.bot_ai import BotAI
    from core.global_cache import GlobalCache
    from core.event_bus import EventBus
    from core.frame_plan import FramePlan


class ResearchManager(Manager):
    """
    Technology Researcher.

    This manager is responsible for executing the research plan laid out by the
    CapabilityDirector. It reads the prioritized list of desired upgrades from
    the FramePlan and attempts to start the highest-priority research that is
    currently possible and affordable.
    """

    def __init__(self, bot: "BotAI"):
        super().__init__(bot)

    async def execute(
        self, cache: "GlobalCache", plan: "FramePlan", bus: "EventBus"
    ) -> List[CommandFunctor]:
        """
        Processes the upgrade priority list from the FramePlan and initiates
        the first available research.
        """
        upgrade_priority_list = getattr(plan, "upgrade_goal", [])
        if not upgrade_priority_list:
            return []

        for upgrade_id in upgrade_priority_list:
            # 1. Check if the upgrade is already complete or in progress.
            # a value > 0 means it's either in progress or complete.
            if self.bot.already_pending_upgrade(upgrade_id) > 0:
                continue

            # 2. Check if we can afford the upgrade.
            if not self.bot.can_afford(upgrade_id):
                continue

            # 3. Determine the required research structure.
            research_structure_type = UPGRADE_RESEARCHED_FROM.get(upgrade_id)
            if not research_structure_type:
                cache.logger.warning(
                    f"ResearchManager: No building defined for researching {upgrade_id.name}"
                )
                continue

            # 4. Find an available building to start the research.
            # Get all completed buildings of the required type.
            available_buildings = cache.friendly_structures.of_type(
                research_structure_type
            ).ready

            # Prioritize using a truly idle building. If none are idle,
            # select the first available (busy) one to queue the research.
            building_to_use = available_buildings.idle.first_or(
                available_buildings.first
            )

            if not building_to_use:
                continue  # No ready building of the required type is available.

            # 5. Check for tech prerequisites (e.g., Armory for Level 2 upgrades).
            research_details = RESEARCH_INFO.get(research_structure_type, {}).get(
                upgrade_id
            )
            if research_details:
                required_building = research_details.get("required_building")
                if (
                    required_building
                    and self.bot.structure_type_build_progress(required_building) < 1
                ):
                    continue  # Prerequisite building not ready.

            # 6. All checks passed. Issue the research command and exit for this frame.
            cache.logger.info(
                f"Starting research for {upgrade_id.name} at {building_to_use.type_id.name}."
            )
            # We return immediately to ensure only one research is started per frame.
            return [lambda b=building_to_use, u=upgrade_id: b.research(u)]

        # If the loop completes, no upgrades could be started this frame.
        return []
