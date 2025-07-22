from __future__ import annotations
from typing import TYPE_CHECKING, List, Tuple, Union

from sc2.ids.unit_typeid import UnitTypeId
from sc2.ids.upgrade_id import UpgradeId

if TYPE_CHECKING:
    from sc2.bot_ai import BotAI

# A build item can be a UnitTypeId for training/building, or an UpgradeId for research.
BuildItem = Union[UnitTypeId, UpgradeId]


class TwoRaxReaper:
    """
    Strategic Recipe: A standard 2 Barracks Reaper opening build order.

    This class provides a static, timed sequence of production goals. It acts as an
    iterator that the CapabilityDirector can query on each frame. When the bot's
    current supply meets the trigger for the next step, this class provides the
    item to be built and advances its internal state.
    """

    def __init__(self, bot: "BotAI"):
        self.bot = bot
        # The core build order sequence: (supply_trigger, item_to_build)
        self.build_order: List[Tuple[int, BuildItem]] = [
            # --- Opening Phase ---
            (14, UnitTypeId.SUPPLYDEPOT),  # Build first depot at 14 supply
            (15, UnitTypeId.SCV),  # Continue worker production
            (16, UnitTypeId.BARRACKS),  # First Barracks
            (16, UnitTypeId.REFINERY),  # First Gas
            (17, UnitTypeId.SCV),
            (18, UnitTypeId.BARRACKS),  # Second Barracks
            (19, UnitTypeId.SCV),
            (20, UnitTypeId.ORBITALCOMMAND),  # Morph CC to Orbital as soon as it's done
            # --- Reaper Production Phase ---
            (20, UnitTypeId.REAPER),  # First Reaper
            (21, UnitTypeId.REAPER),  # Second Reaper from second Barracks
            (22, UnitTypeId.SUPPLYDEPOT),  # Second Depot to stay ahead
            (23, UnitTypeId.SCV),
            (24, UnitTypeId.REAPER),
            (25, UnitTypeId.REAPER),
            (26, UnitTypeId.REFINERY),  # Second Gas for tech follow-up
            (27, UnitTypeId.SCV),
            # This is where the build order ends. The CapabilityDirector will take over with dynamic logic.
        ]
        self.current_step_index = 0

    def is_complete(self) -> bool:
        """
        Checks if the entire build order sequence has been completed.

        :return: True if all steps have been issued, False otherwise.
        """
        return self.current_step_index >= len(self.build_order)

    def get_next_item(self, current_supply: int) -> BuildItem | None:
        """
        Gets the next item to produce from the build order if the supply trigger is met.

        The CapabilityDirector calls this method every frame. If the bot's current supply
        is high enough for the current step, this method returns the item to build
        and advances to the next step. Otherwise, it returns None.

        :param current_supply: The bot's current supply_used.
        :return: A UnitTypeId or UpgradeId if the condition is met, otherwise None.
        """
        if self.is_complete():
            return None

        # Get the current step from the build order
        supply_trigger, item_to_build = self.build_order[self.current_step_index]

        # Check if the bot has reached the required supply count for this step
        if current_supply >= supply_trigger:
            self.current_step_index += 1
            return item_to_build

        # Supply requirement not yet met
        return None
