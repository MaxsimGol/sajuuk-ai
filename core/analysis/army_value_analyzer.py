from typing import TYPE_CHECKING

from core.interfaces.analysis_task_abc import AnalysisTask
from core.utilities.unit_value import calculate_army_value

if TYPE_CHECKING:
    from sc2.bot_ai import BotAI
    from core.game_analysis import GameAnalyzer


class FriendlyArmyValueAnalyzer(AnalysisTask):
    """Calculates the resource value of all friendly non-worker, non-structure units."""

    def execute(self, analyzer: "GameAnalyzer", bot: "BotAI"):
        if analyzer.friendly_army_units is not None:
            analyzer.friendly_army_value = calculate_army_value(
                analyzer.friendly_army_units, bot.game_data
            )


class EnemyArmyValueAnalyzer(AnalysisTask):
    """Calculates the resource value of all known visible enemy units."""

    def execute(self, analyzer: "GameAnalyzer", bot: "BotAI"):
        # Note: This uses bot.enemy_units (visible) for performance, not analyzer.known_enemy_units (persistent).
        # This gives a "current threat" value rather than a "total known army" value.
        analyzer.enemy_army_value = calculate_army_value(bot.enemy_units, bot.game_data)
