from __future__ import annotations
from typing import TYPE_CHECKING, List, Dict

from sc2.ids.unit_typeid import UnitTypeId
from sc2.dicts.unit_trained_from import UNIT_TRAINED_FROM
from sc2.dicts.unit_train_build_abilities import TRAIN_INFO

from core.interfaces.manager_abc import Manager
from core.types import CommandFunctor
from sc2.unit import Unit

if TYPE_CHECKING:
    from sc2.bot_ai import BotAI
    from sc2.units import Units
    from core.global_cache import GlobalCache
    from core.event_bus import EventBus
    from core.frame_plan import FramePlan


class ArmyUnitManager(Manager):
    """
    Unit Production Line Foreman.

    This manager is responsible for training army units. It reads the desired
    unit composition from the FramePlan, calculates the production deficit,
    and then attempts to train units from available, idle production structures
    within the bot's current resource and supply limits.
    """

    def __init__(self, bot: "BotAI"):
        super().__init__(bot)

    async def execute(
        self, cache: "GlobalCache", plan: "FramePlan", bus: "EventBus"
    ) -> List[CommandFunctor]:
        """
        Executes the logic to train army units based on the director's goals.
        """
        actions: List[CommandFunctor] = []
        unit_goal = getattr(plan, "unit_composition_goal", {})
        if not unit_goal:
            return []

        # Use a copy to safely modify the list of available producers for this frame
        idle_producers = cache.idle_production_structures.copy()
        if not idle_producers:
            return []

        # --- Calculate Production Deficit ---
        deficits: Dict[UnitTypeId, int] = {}
        for unit_id, target_count in unit_goal.items():
            current_count = cache.friendly_army_units(
                unit_id
            ).amount + self.bot.already_pending(unit_id)
            if current_count < target_count:
                deficits[unit_id] = target_count - current_count

        if not deficits:
            return []

        # --- Fulfill Deficit ---
        # Iterate through the needed units and try to build them
        for unit_id, count_needed in deficits.items():
            for _ in range(count_needed):
                # We can't afford it, so no point in continuing for this unit type
                if not self.bot.can_afford(unit_id):
                    break

                producer = self._find_producer_for(unit_id, idle_producers)
                if not producer:
                    # No available building to produce this unit, move to next unit type
                    break

                # Found a producer, queue the training command
                actions.append(lambda p=producer, u=unit_id: p.train(u))
                idle_producers.remove(producer)  # Mark as used for this frame

                # If the producer has a reactor, try to queue a second unit
                if producer.has_reactor and self.bot.can_afford(unit_id):
                    actions.append(lambda p=producer, u=unit_id: p.train(u, queue=True))

        return actions

    def _find_producer_for(
        self, unit_id: UnitTypeId, available_producers: "Units"
    ) -> Unit | None:
        """
        Finds a suitable, available production building for a given unit type.
        Considers required add-ons and prefers reactors for non-tech units.

        :param unit_id: The UnitTypeId of the unit to be trained.
        :param available_producers: A Units object of idle production structures.
        :return: A suitable Unit object if one is found, otherwise None.
        """
        # Determine the building type that can train this unit.
        required_producer_types = UNIT_TRAINED_FROM.get(unit_id)
        if not required_producer_types:
            return None

        # For Terran army units, there's typically only one producer type.
        producer_type = next(iter(required_producer_types))

        # Check if a TechLab is required for this unit.
        needs_techlab = TRAIN_INFO[producer_type][unit_id].get(
            "requires_techlab", False
        )

        # Filter the available producers to match the required building type.
        candidates = available_producers.of_type(producer_type)
        if not candidates:
            return None

        # --- Find a specific building based on add-on requirements ---
        if needs_techlab:
            # Find any candidate that has a TechLab.
            for producer in candidates:
                if producer.has_techlab:
                    return producer
        else:
            # For non-tech units, prefer buildings with Reactors, then naked ones.
            # Sorting by boolean `has_reactor` (True > False) in reverse puts reactors first.
            sorted_candidates = candidates.sorted(
                key=lambda p: p.has_reactor, reverse=True
            )
            if sorted_candidates:
                return sorted_candidates.first

        # No suitable producer was found.
        return None
