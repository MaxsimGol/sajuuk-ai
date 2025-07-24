# terran/capabilities/production/factory_manager.py
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

FACTORY_UNITS: Set[UnitTypeId] = {
    UnitTypeId.HELLION,
    UnitTypeId.HELLIONTANK,
    UnitTypeId.WIDOWMINE,
    UnitTypeId.SIEGETANK,
    UnitTypeId.CYCLONE,
    UnitTypeId.THOR,
}
FACTORY_TECH_UNITS: Set[UnitTypeId] = {
    UnitTypeId.SIEGETANK,
    UnitTypeId.CYCLONE,
    UnitTypeId.THOR,
}
FACTORY_UPGRADES: Set[UpgradeId] = {
    UpgradeId.DRILLCLAWS,
    UpgradeId.SMARTSERVOS,
    UpgradeId.HIGHCAPACITYBARRELS,  # Infernal Pre-Igniter
    UpgradeId.CYCLONELOCKONDAMAGEUPGRADE,
}


class FactoryManager(Manager):
    """
    Manages all Factory buildings, handling unit production, addon construction,
    and research. It acts on the high-level goals defined in the FramePlan.
    """

    def __init__(self, bot: "BotAI"):
        super().__init__(bot)
        self.production_priority: List[UnitTypeId] = [
            UnitTypeId.SIEGETANK,
            UnitTypeId.THOR,
            UnitTypeId.CYCLONE,
            UnitTypeId.WIDOWMINE,
            UnitTypeId.HELLION,
            UnitTypeId.HELLIONTANK,
        ]

    async def execute(
        self, cache: "GlobalCache", plan: "FramePlan", bus: "EventBus"
    ) -> List[CommandFunctor]:
        """Orchestrates addon, research, and production logic for Factories."""
        actions: List[CommandFunctor] = []
        self.factories = cache.friendly_structures.of_type(UnitTypeId.FACTORY)
        if not self.factories.exists:
            return []

        actions.extend(self._handle_addons(cache, plan))
        actions.extend(self._handle_research(cache, plan))
        actions.extend(self._handle_production(cache, plan))

        return actions

    def _handle_addons(
        self, cache: "GlobalCache", plan: "FramePlan"
    ) -> List[CommandFunctor]:
        """Builds a Tech Lab or Reactor based on the director's plan."""
        naked_factories = self.factories.ready.idle.filter(lambda f: f.add_on_tag == 0)
        if not naked_factories:
            return []

        techlab_target = plan.addon_goal.get(UnitTypeId.FACTORYTECHLAB, 0)
        techlab_current = cache.friendly_structures.of_type(
            UnitTypeId.FACTORYTECHLAB
        ).amount + self.bot.already_pending(UnitTypeId.FACTORYTECHLAB)

        reactor_target = plan.addon_goal.get(UnitTypeId.FACTORYREACTOR, 0)
        reactor_current = cache.friendly_structures.of_type(
            UnitTypeId.FACTORYREACTOR
        ).amount + self.bot.already_pending(UnitTypeId.FACTORYREACTOR)

        addon_to_build = None
        if techlab_current < techlab_target:
            addon_to_build = UnitTypeId.TECHLAB
        elif reactor_current < reactor_target:
            addon_to_build = UnitTypeId.REACTOR

        if addon_to_build and self.bot.can_afford(addon_to_build):
            builder = naked_factories.first
            cache.logger.info(
                f"FactoryManager building {addon_to_build.name} on {builder.tag}"
            )
            return [lambda b=builder, a=addon_to_build: b.build(a)]

        return []

    def _handle_research(
        self, cache: "GlobalCache", plan: "FramePlan"
    ) -> List[CommandFunctor]:
        """Initiates upgrades from an available Factory Tech Lab."""
        next_upgrade = next(
            (upg for upg in plan.upgrade_goal if upg in FACTORY_UPGRADES), None
        )

        if not next_upgrade or not self.bot.can_afford(next_upgrade):
            return []

        tech_labs = cache.friendly_structures.of_type(
            UnitTypeId.FACTORYTECHLAB
        ).ready.idle
        if tech_labs.exists:
            lab = tech_labs.first
            cache.logger.info(f"FactoryManager starting research: {next_upgrade.name}")
            return [lambda l=lab, u=next_upgrade: l.research(u)]

        return []

    def _handle_production(
        self, cache: "GlobalCache", plan: "FramePlan"
    ) -> List[CommandFunctor]:
        """Trains units from available Factories based on composition goals."""
        actions: List[CommandFunctor] = []
        idle_factories = self.factories.ready.idle
        if not idle_factories:
            return []

        for factory in idle_factories:
            for unit_id in self.production_priority:
                needs_techlab = unit_id in FACTORY_TECH_UNITS
                if needs_techlab and not factory.has_techlab:
                    continue

                target_count = plan.unit_composition_goal.get(unit_id, 0)
                current_count = cache.friendly_army_units(
                    unit_id
                ).amount + self.bot.already_pending(unit_id)

                if current_count >= target_count:
                    continue

                if not self.bot.can_afford(
                    unit_id
                ) or self.bot.supply_left < self.bot.calculate_supply_cost(unit_id):
                    continue

                actions.append(lambda f=factory, u=unit_id: f.train(u))

                if (
                    factory.has_reactor
                    and self.bot.can_afford(unit_id)
                    and self.bot.supply_left > self.bot.calculate_supply_cost(unit_id)
                ):
                    actions.append(lambda f=factory, u=unit_id: f.train(u, queue=True))

                break  # Move to the next idle factory
        return actions
