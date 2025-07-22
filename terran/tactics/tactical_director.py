# terran/tactics/tactical_director.py
from __future__ import annotations
from typing import TYPE_CHECKING, List

from core.frame_plan import ArmyStance
from core.interfaces.director_abc import Director
from core.interfaces.manager_abc import Manager
from core.types import CommandFunctor
from .scouting_manager import ScoutingManager
from .positioning_manager import PositioningManager
from .army_control_manager import ArmyControlManager

if TYPE_CHECKING:
    from sc2.bot_ai import BotAI
    from core.global_cache import GlobalCache
    from core.event_bus import EventBus
    from core.frame_plan import FramePlan

# --- Strategic Timing Constants ---
# Launch a major attack when the bot reaches this supply count.
PRIMARY_ATTACK_SUPPLY_TRIGGER = 140


class TacticalDirector(Director):
    def __init__(self, bot: "BotAI"):
        super().__init__(bot)
        self.scouting_manager = ScoutingManager(bot)
        self.positioning_manager = PositioningManager(bot)
        self.army_control_manager = ArmyControlManager(bot)

        self.managers: List[Manager] = [
            self.positioning_manager,
            self.scouting_manager,
            self.army_control_manager,
        ]
        self.has_launched_main_attack = False

    def _determine_stance_and_target(self, cache: "GlobalCache", plan: "FramePlan"):
        if cache.base_is_under_attack:
            plan.set_army_stance(ArmyStance.DEFENSIVE)
            setattr(plan, "target_location", cache.threat_location)
            cache.logger.warning(
                f"BASE UNDER ATTACK! Stance: DEFENSIVE. Target: {cache.threat_location.rounded}"
            )
            return

        # --- MODIFICATION: Proactive Timing Attack Logic ---
        # Trigger a major attack at a specific supply count.
        if (
            not self.has_launched_main_attack
            and cache.supply_used >= PRIMARY_ATTACK_SUPPLY_TRIGGER
        ):
            plan.set_army_stance(ArmyStance.AGGRESSIVE)
            self.has_launched_main_attack = True
            cache.logger.warning(
                f"SUPPLY TRIGGER MET ({PRIMARY_ATTACK_SUPPLY_TRIGGER})! LAUNCHING MAIN ATTACK."
            )

        # --- Reactive Stance Logic ---
        else:
            is_currently_aggressive = plan.army_stance == ArmyStance.AGGRESSIVE
            # Be more willing to attack
            go_aggressive_threshold = cache.enemy_army_value * 1.35
            # Fall back if we are losing the advantage
            go_defensive_threshold = cache.enemy_army_value * 1.1

            stance = plan.army_stance
            if is_currently_aggressive:
                if cache.friendly_army_value < go_defensive_threshold:
                    stance = ArmyStance.DEFENSIVE
            else:  # Defensive
                no_known_enemy_army = (
                    cache.enemy_army_value == 0 and cache.friendly_army_value > 1500
                )
                if (
                    cache.friendly_army_value > go_aggressive_threshold
                    or no_known_enemy_army
                ):
                    stance = ArmyStance.AGGRESSIVE

            plan.set_army_stance(stance)

        # --- Target Selection ---
        if plan.army_stance == ArmyStance.AGGRESSIVE:
            if cache.known_enemy_townhalls.exists:
                target = cache.known_enemy_townhalls.closest_to(
                    self.bot.start_location
                ).position
            elif cache.known_enemy_structures.exists:
                target = cache.known_enemy_structures.closest_to(
                    self.bot.enemy_start_locations[0]
                ).position
            else:
                target = self.bot.enemy_start_locations[0]
            setattr(plan, "target_location", target)
        else:  # Defensive
            target = getattr(plan, "rally_point", self.bot.main_base_ramp.top_center)
            setattr(plan, "target_location", target)

        cache.logger.debug(
            f"Stance: {plan.army_stance.name}. Target: {getattr(plan, 'target_location', 'None').rounded if getattr(plan, 'target_location', None) else 'None'}"
        )

    async def execute(
        self, cache: "GlobalCache", plan: "FramePlan", bus: "EventBus"
    ) -> list[CommandFunctor]:
        self._determine_stance_and_target(cache, plan)
        actions: list[CommandFunctor] = []
        for manager in self.managers:
            manager_actions = await manager.execute(cache, plan, bus)
            actions.extend(manager_actions)
        return actions
