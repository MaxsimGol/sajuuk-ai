from sc2.bot_ai import BotAI
from sc2.data import Race
from sc2.unit_command import UnitCommand

from core.global_cache import GlobalCache
from core.event_bus import EventBus
from core.interfaces.race_general_abc import RaceGeneral
from generals.terran_general import TerranGeneral

# from generals.zerg_general import ZergGeneral
# from generals.protoss_general import ProtossGeneral


class Sajuuk(BotAI):
    """
    The Conductor.

    This is the single BotAI implementation for the Sajuuk project.
    It contains no strategic logic. Its only purpose is to initialize core
    services, detect the player's race, and delegate control.
    """

    def __init__(self):
        super().__init__()
        self.active_general: RaceGeneral | None = None
        self.global_cache: GlobalCache = GlobalCache()
        self.event_bus: EventBus = EventBus()

    async def on_start(self):
        """
        Initializes the correct RaceGeneral based on the player's race.
        """
        if self.race == Race.Terran:
            # The General needs the bot object to create UnitCommands,
            # but it will not pass it down to its managers.
            self.active_general = TerranGeneral(self)
        # ... other races ...
        else:
            raise NotImplementedError(f"Sajuuk does not support race: {self.race}")

        # Asynchronously initialize the chosen General
        if self.active_general:
            await self.active_general.on_start()

    async def on_step(self, iteration: int):
        """
        The main cognitive loop, executed on every game step.
        1. PERCEIVE: Update the GlobalCache with the latest game state.
        2. DECIDE:   Delegate to the General to get a list of actions.
        3. ACT:      Execute the collected actions.
        """
        if not self.active_general:
            return

        # 1. PERCEIVE
        self.global_cache.update(self.state)

        # 2. DECIDE
        # The General receives the cache and bus, and returns its command intentions.
        actions: list[UnitCommand] = await self.active_general.execute_step(
            self.global_cache, self.event_bus
        )

        # 3. ACT
        if actions:
            await self.do_actions(actions)
