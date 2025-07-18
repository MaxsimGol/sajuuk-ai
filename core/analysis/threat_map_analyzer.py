from typing import TYPE_CHECKING
import numpy as np

from core.interfaces.analysis_task_abc import AnalysisTask
from core.utilities.geometry import create_threat_map

if TYPE_CHECKING:
    from sc2.bot_ai import BotAI
    from core.game_analysis import GameAnalyzer


class ThreatMapAnalyzer(AnalysisTask):
    """Generates and updates a 2D map representing enemy threat levels."""

    def execute(self, analyzer: "GameAnalyzer", bot: "BotAI"):
        map_size = bot.game_info.map_size
        if bot.enemy_units.exists:
            analyzer.threat_map = create_threat_map(bot.enemy_units, map_size)
        elif analyzer.threat_map is None:
            analyzer.threat_map = np.zeros(map_size, dtype=np.float32)
