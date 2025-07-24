# terran/capabilities/production/barracks_manager.py
from __future__ import annotations
from typing import TYPE_CHECKING, List, Set

from sc2.ids.unit_typeid import UnitTypeId
from sc2.ids.upgrade_id import UpgradeId

from core.interfaces.manager_abc import Manager
from core.types import CommandFunctor

if TYPE_CHECKING:
    from sc2.bot_ai import BotAI
    from sc2.units import Units
    from core.global_cache import GlobalCache
    from core.event_bus import EventBus
    from core.frame_plan import FramePlan

BARRACKS_UNITS: Set[UnitTypeId] = {
    UnitTypeId.MARINE,
    UnitTypeId.MARAUDER,
    UnitTypeId.REAPER,
    UnitTypeId.GHOST,
}
BARRACKS_TECH_UNITS: Set[UnitTypeId] = {UnitTypeId.MARAUDER, UnitTypeId.GHOST}
BARRACKS_UPGRADES: Set[UpgradeId] = {
    UpgradeId.STIMPACK,
    UpgradeId.SHIELDWALL,
    UpgradeId.PUNISHERGRENADES,
}


class BarracksManager(Manager):
    """
    Manages all Barracks buildings, including unit production, addon construction,
    and research. It translates high-level goals from the FramePlan into
    concrete actions.
    """

    def __init__(self, bot: "BotAI"):
        super().__init__(bot)
        # Prioritize units that require tech labs first.
        self.production_priority: List[UnitTypeId] = [
            UnitTypeId.GHOST,
            UnitTypeId.MARAUDER,
            UnitTypeId.MARINE,
            UnitTypeId.REAPER,
        ]

    async def execute(
        self, cache: "GlobalCache", plan: "FramePlan", bus: "EventBus"
    ) -> List[CommandFunctor]:
        """Orchestrates addon, research, and production logic for Barracks."""
        actions: List[CommandFunctor] = []
        self.barracks = cache.friendly_structures.of_type(UnitTypeId.BARRACKS)
        if not self.barracks.exists:
            return []

        actions.extend(self._handle_addons(cache, plan))
        actions.extend(self._handle_research(cache, plan))
        actions.extend(self._handle_production(cache, plan))

        return actions

    def _handle_addons(
        self, cache: "GlobalCache", plan: "FramePlan"
    ) -> List[CommandFunctor]:
        """Builds a Tech Lab or Reactor based on the director's plan."""
        naked_barracks = self.barracks.ready.idle.filter(lambda b: b.add_on_tag == 0)
        if not naked_barracks:
            return []

        # Check addon deficits from the director's plan
        techlab_target = plan.addon_goal.get(UnitTypeId.BARRACKSTECHLAB, 0)
        techlab_current = cache.friendly_structures.of_type(
            UnitTypeId.BARRACKSTECHLAB
        ).amount + self.bot.already_pending(UnitTypeId.BARRACKSTECHLAB)

        reactor_target = plan.addon_goal.get(UnitTypeId.BARRACKSREACTOR, 0)
        reactor_current = cache.friendly_structures.of_type(
            UnitTypeId.BARRACKSREACTOR
        ).amount + self.bot.already_pending(UnitTypeId.BARRACKSREACTOR)

        addon_to_build = None
        if techlab_current < techlab_target:
            addon_to_build = UnitTypeId.TECHLAB
        elif reactor_current < reactor_target:
            addon_to_build = UnitTypeId.REACTOR

        if addon_to_build and self.bot.can_afford(addon_to_build):
            builder = naked_barracks.first
            cache.logger.info(
                f"BarracksManager building {addon_to_build.name} on {builder.tag}"
            )
            return [lambda b=builder, a=addon_to_build: b.build(a)]

        return []

    def _handle_research(
        self, cache: "GlobalCache", plan: "FramePlan"
    ) -> List[CommandFunctor]:
        """Initiates upgrades from an available Barracks Tech Lab."""
        next_upgrade = next(
            (upg for upg in plan.upgrade_goal if upg in BARRACKS_UPGRADES), None
        )

        if not next_upgrade or not self.bot.can_afford(next_upgrade):
            return []

        tech_labs = cache.friendly_structures.of_type(
            UnitTypeId.BARRACKSTECHLAB
        ).ready.idle
        if tech_labs.exists:
            lab = tech_labs.first
            cache.logger.info(f"BarracksManager starting research: {next_upgrade.name}")
            return [lambda l=lab, u=next_upgrade: l.research(u)]

        return []

    def _handle_production(
        self, cache: "GlobalCache", plan: "FramePlan"
    ) -> List[CommandFunctor]:
        """Trains units from available Barracks based on composition goals."""
        actions: List[CommandFunctor] = []
        idle_barracks = self.barracks.ready.idle
        if not idle_barracks:
            return []

        # Iterate through available producers, not deficits
        for barracks in idle_barracks:
            # For each barracks, check what it can produce and if there's a need
            for unit_id in self.production_priority:
                # Check if this barracks can build this unit
                needs_techlab = unit_id in BARRACKS_TECH_UNITS
                if needs_techlab and not barracks.has_techlab:
                    continue
                if (
                    not needs_techlab and barracks.has_techlab
                ):  # Techlab can build non-tech units
                    pass

                # Check if we have a deficit for this unit
                target_count = plan.unit_composition_goal.get(unit_id, 0)
                current_count = cache.friendly_army_units(
                    unit_id
                ).amount + self.bot.already_pending(unit_id)

                if current_count >= target_count:
                    continue

                # Check affordability
                if not self.bot.can_afford(
                    unit_id
                ) or self.bot.supply_left < self.bot.calculate_supply_cost(unit_id):
                    continue

                # All checks passed, issue train command
                actions.append(lambda b=barracks, u=unit_id: b.train(u))

                # If it has a reactor, queue a second unit
                if (
                    barracks.has_reactor
                    and self.bot.can_afford(unit_id)
                    and self.bot.supply_left > self.bot.calculate_supply_cost(unit_id)
                ):
                    actions.append(lambda b=barracks, u=unit_id: b.train(u, queue=True))

                # Barracks is now busy, move to the next idle one
                break
        return actions
