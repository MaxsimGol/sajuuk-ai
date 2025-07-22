from __future__ import annotations
from typing import TYPE_CHECKING

from core.interfaces.analysis_task_abc import AnalysisTask

if TYPE_CHECKING:
    from sc2.bot_ai import BotAI
    from sc2.position import Point2
    from core.game_analysis import GameAnalyzer


class BaseThreatAnalyzer(AnalysisTask):
    """
    Analyzes and detects direct threats to friendly bases.
    This task is critical for triggering a high-priority defensive response.
    """

    def execute(self, analyzer: "GameAnalyzer", bot: "BotAI"):
        """
        Checks for nearby enemies or damaged structures to determine if a base is under attack.
        """
        # Initialize default state for this frame
        setattr(analyzer, "base_is_under_attack", False)
        setattr(analyzer, "threat_location", None)

        if not bot.townhalls.ready.exists:
            return

        for th in bot.townhalls.ready:
            # Check for any enemy ground units within a 15-unit radius of the townhall
            nearby_enemies = bot.enemy_units.filter(
                lambda u: not u.is_flying and th.distance_to(u) < 15
            )

            if nearby_enemies.exists:
                # EMERGENCY: Base is under attack!
                analyzer.base_is_under_attack = True
                # The location of the threat is the center of the attacking force
                analyzer.threat_location = nearby_enemies.center
                # We've found the primary threat, no need to check other bases
                return

        # As a fallback, check if any structure is taking damage
        damaged_structures = bot.structures.filter(lambda s: s.health_percentage < 1)
        if damaged_structures.exists:
            nearby_enemies = bot.enemy_units.closer_than(15, damaged_structures.center)
            if nearby_enemies.exists:
                analyzer.base_is_under_attack = True
                analyzer.threat_location = nearby_enemies.center
                return
