"""
A declarative configuration registry for all analysis tasks in the system.
"""

from __future__ import annotations
from typing import List, Type

from core.interfaces.analysis_task_abc import AnalysisTask
from core.analysis.army_value_analyzer import (
    FriendlyArmyValueAnalyzer,
    EnemyArmyValueAnalyzer,
)
from core.analysis.expansion_analyzer import ExpansionAnalyzer
from core.analysis.known_enemy_townhall_analyzer import KnownEnemyTownhallAnalyzer
from core.analysis.threat_map_analyzer import ThreatMapAnalyzer
from core.analysis.units_analyzer import UnitsAnalyzer

# --- Task Configuration ---

# PRE_ANALYSIS: Run EVERY frame before all other tasks.
# For foundational tasks that other analyzers depend on.
PRE_ANALYSIS_TASK_CLASSES: List[Type[AnalysisTask]] = [
    UnitsAnalyzer,
]

# HIGH_FREQUENCY: Run one task per frame in a round-robin cycle.
# For lightweight tasks that need to be reasonably fresh.
HIGH_FREQUENCY_TASK_CLASSES: List[Type[AnalysisTask]] = [
    FriendlyArmyValueAnalyzer,
    EnemyArmyValueAnalyzer,
]

# LOW_FREQUENCY: Run one task per frame periodically.
# For heavyweight tasks that are expensive to compute.
LOW_FREQUENCY_TASK_CLASSES: List[Type[AnalysisTask]] = [
    ThreatMapAnalyzer,
    ExpansionAnalyzer,
    KnownEnemyTownhallAnalyzer,
]
