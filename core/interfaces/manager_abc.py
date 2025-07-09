# terran/managers/economy_manager.py

from sc2.bot_ai import BotAI
from sc2.unit_command import UnitCommand

from core.interfaces.manager_abc import Manager
from core.global_cache import GlobalCache
from core.event_bus import EventBus


class TerranEconomyManager(Manager):
    """
    Manages the Terran economy, including SCV production, MULEs,
    and expansion timing.
    """

    def __init__(self, bot: BotAI):
        self.bot = bot  # Needed as an action factory, e.g., self.bot.train(...)

    async def execute(self, cache: GlobalCache, bus: EventBus) -> list[UnitCommand]:
        """
        Reads from the cache and decides on economic actions.

        :param cache: The current game state analysis.
        :param bus: The event bus for reactive actions.
        :return: A list of commands to be executed.
        """
        # Logic for managing SCVs, MULEs, and expansions will go here.
        return []
