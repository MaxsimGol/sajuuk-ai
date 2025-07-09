from sc2.bot_ai import BotAI
from sc2.unit_command import UnitCommand

from core.global_cache import GlobalCache
from core.event_bus import EventBus
from core.interfaces.race_general_abc import RaceGeneral

# We import the manager classes
from terran.managers.economy_manager import TerranEconomyManager
from terran.managers.production_manager import TerranProductionManager
from terran.managers.military_manager import TerranMilitaryManager


class TerranGeneral(RaceGeneral):
    """
    The central orchestrator for all Terran-specific strategy and logic.

    Its 'execute_step' method is the heart of the bot's decision-making.
    It calls its managers in a strategic order, passing them the current
    game state via the cache, and aggregates their requested actions.
    """

    def __init__(self, bot_object: BotAI):
        """
        Initializes the General and all its subordinate managers.
        Managers are instantiated here but do not receive the bot object.
        """
        self.bot = bot_object
        self.economy_manager = TerranEconomyManager(bot_object)
        self.production_manager = TerranProductionManager(bot_object)
        self.military_manager = TerranMilitaryManager(bot_object)

    async def on_start(self):
        """
        One-time setup tasks at the beginning of the game.
        """
        # Example: await self.economy_manager.initialize_gas_sites(self.bot.vespene_geyser)
        pass

    async def execute_step(
        self, cache: GlobalCache, bus: EventBus
    ) -> list[UnitCommand]:
        """
        Orchestrates managers and aggregates their requested actions.

        :param cache: The GlobalCache object with the current frame's state.
        :param bus: The EventBus for reactive messaging.
        :return: A list of UnitCommand objects to be executed.
        """
        # The order of execution is a key strategic decision.
        # Economy first, then spend the money, then use the army.
        actions = []
        actions.extend(await self.economy_manager.execute(cache, bus))
        actions.extend(await self.production_manager.execute(cache, bus))
        actions.extend(await self.military_manager.execute(cache, bus))

        return actions
