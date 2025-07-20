from __future__ import annotations
from typing import TYPE_CHECKING, List

from sc2.ids.unit_typeid import UnitTypeId
from sc2.ids.ability_id import AbilityId
from sc2.data import race_townhalls

from core.interfaces.manager_abc import Manager
from core.types import CommandFunctor

if TYPE_CHECKING:
    from sc2.bot_ai import BotAI
    from core.global_cache import GlobalCache
    from core.event_bus import EventBus
    from core.frame_plan import FramePlan


class MuleManager(Manager):
    """
    Manages the usage of Orbital Command energy for calling down MULEs.
    """

    def __init__(self, bot: "BotAI"):
        super().__init__(bot)

    async def execute(
        self, cache: "GlobalCache", plan: "FramePlan", bus: "EventBus"
    ) -> List[CommandFunctor]:
        """
        Finds Orbital Commands with enough energy and calls down MULEs on the
        most effective mineral patches.
        """
        actions: List[CommandFunctor] = []
        terran_townhalls = race_townhalls[self.bot.race]

        # Find OCs with enough energy for a MULE
        orbitals = cache.friendly_structures.of_type(
            UnitTypeId.ORBITALCOMMAND
        ).ready.filter(lambda oc: oc.energy >= 50)

        if not orbitals:
            return []

        # Find ready townhalls to determine which mineral patches are ours
        townhalls = cache.friendly_structures.of_type(terran_townhalls).ready
        if not townhalls:
            return []

        # Select the OC with the most energy to call down the MULE
        oc_to_use = orbitals.sorted(lambda o: o.energy, reverse=True).first

        # Find the best mineral patch to drop the MULE on.
        best_mineral_patch = None
        highest_minerals = 0
        for th in townhalls:
            patches = self.bot.mineral_field.closer_than(10, th)
            if not patches:
                continue
            richest_patch = patches.sorted(
                lambda p: p.mineral_contents, reverse=True
            ).first
            if richest_patch.mineral_contents > highest_minerals:
                highest_minerals = richest_patch.mineral_contents
                best_mineral_patch = richest_patch

        if best_mineral_patch:
            actions.append(
                lambda oc=oc_to_use, patch=best_mineral_patch: oc(
                    AbilityId.CALLDOWNMULE_CALLDOWNMULE, patch
                )
            )

        return actions
