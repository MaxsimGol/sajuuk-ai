from typing import TYPE_CHECKING

from sc2.data import race_townhalls

from core.interfaces.analysis_task_abc import AnalysisTask

if TYPE_CHECKING:
    from sc2.bot_ai import BotAI
    from core.game_analysis import GameAnalyzer


class KnownEnemyTownhallAnalyzer(AnalysisTask):
    """
    A stateless task that filters the list of all known enemy structures
    (provided by the UnitAnalyzer) to find townhalls.
    """

    def execute(self, analyzer: "GameAnalyzer", bot: "BotAI"):
        """
        Filters the known_enemy_structures from the analyzer to populate the
        known_enemy_townhalls field.
        """
        if analyzer.known_enemy_structures is None:
            return

        enemy_th_types = race_townhalls.get(bot.enemy_race, set())

        if not enemy_th_types:
            analyzer.known_enemy_townhalls = bot.enemy_structures.subgroup([])
            return

        analyzer.known_enemy_townhalls = analyzer.known_enemy_structures.of_type(
            enemy_th_types
        )
