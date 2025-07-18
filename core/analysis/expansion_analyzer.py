# core/analysis/expansion_analyzer.py

from typing import TYPE_CHECKING

from sc2.data import race_townhalls

from core.interfaces.analysis_task_abc import AnalysisTask
from core.utilities.events import Event, EventType

if TYPE_CHECKING:
    from sc2.bot_ai import BotAI
    from core.event_bus import EventBus
    from core.game_analysis import GameAnalyzer


class ExpansionAnalyzer(AnalysisTask):
    """
    Analyzes and maintains the state of all expansion locations on the map.
    """

    def __init__(self, event_bus: "EventBus"):
        super().__init__(event_bus)

    def subscribe_to_events(self, event_bus: "EventBus"):
        event_bus.subscribe(EventType.UNIT_DESTROYED, self.handle_unit_destruction)

    def execute(self, analyzer: "GameAnalyzer", bot: "BotAI"):
        """Periodically updates the status of all expansion locations."""
        all_expansion_locations = set(bot.expansion_locations_list)

        analyzer.occupied_locations = set(bot.owned_expansions.keys())

        enemy_occupied_locs = set()
        if analyzer.known_enemy_townhalls:
            for th in analyzer.known_enemy_townhalls:
                closest_exp_loc = min(
                    bot.expansion_locations_list,
                    key=lambda loc: loc.distance_to(th.position),
                )
                if th.position.distance_to(closest_exp_loc) < 10:
                    enemy_occupied_locs.add(closest_exp_loc)

        analyzer.enemy_occupied_locations = enemy_occupied_locs

        analyzer.available_expansion_locations = (
            all_expansion_locations
            - analyzer.occupied_locations
            - analyzer.enemy_occupied_locations
        )

    async def handle_unit_destruction(self, event: Event):
        # Hook for future reactive updates.
        pass
