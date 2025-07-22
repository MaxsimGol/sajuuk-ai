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


class TacticalDirector(Director):
    """
    The Grand Tactician. It is the highest-level military authority, making the
    final call on what the army's overall objective should be for the current frame.
    """

    def __init__(self, bot: "BotAI"):
        super().__init__(bot)
        self.scouting_manager = ScoutingManager(bot)
        self.positioning_manager = PositioningManager(bot)
        self.army_control_manager = ArmyControlManager(bot)

        # The execution order of managers is strategically significant.
        # 1. Positioning analyzes the map to find key locations.
        # 2. Scouting gathers new intel.
        # 3. Army Control uses the director's plan and the other managers'
        #    analysis to issue final commands.
        self.managers: List[Manager] = [
            self.positioning_manager,
            self.scouting_manager,
            self.army_control_manager,
        ]

    def _determine_stance_and_target(self, cache: "GlobalCache", plan: "FramePlan"):
        """
        Sets the official ArmyStance and target_location in the FramePlan.
        This includes a high-priority override for base defense to prevent oscillation.
        """
        # --- 1. EMERGENCY OVERRIDE: Base is under attack! ---
        if cache.base_is_under_attack:
            # Forcibly set stance to DEFENSIVE, overriding all other logic.
            plan.set_army_stance(ArmyStance.DEFENSIVE)
            # The target is NOT a static ramp. It's the location of the enemy attack force.
            setattr(plan, "target_location", cache.threat_location)
            cache.logger.warning(
                f"BASE UNDER ATTACK! Overriding stance to DEFENSIVE. Target: {cache.threat_location.rounded}"
            )
            # End the decision process here to ensure this state is locked in.
            return

        # --- 2. Standard Stance Determination (with Hysteresis) ---
        # Hysteresis prevents rapid flip-flopping between stances.
        # We need a bigger advantage to START attacking than to KEEP attacking.
        is_currently_aggressive = plan.army_stance == ArmyStance.AGGRESSIVE

        # Condition to switch TO aggressive: need a 50% army value advantage.
        go_aggressive_threshold = cache.enemy_army_value * 1.5
        # Condition to fall BACK to defensive: when our advantage shrinks to only 15%.
        go_defensive_threshold = cache.enemy_army_value * 1.15

        stance = plan.army_stance  # Start with current stance

        if is_currently_aggressive:
            if cache.friendly_army_value < go_defensive_threshold:
                stance = ArmyStance.DEFENSIVE
        else:  # Currently Defensive
            # Also be aggressive if we have a big army and the enemy has no known army.
            no_known_enemy_army = (
                cache.enemy_army_value == 0 and cache.friendly_army_value > 1500
            )
            if (
                cache.friendly_army_value > go_aggressive_threshold
                or no_known_enemy_army
            ):
                if cache.supply_left > 10:  # Don't attack if supply blocked
                    stance = ArmyStance.AGGRESSIVE

        plan.set_army_stance(stance)
        cache.logger.debug(f"Army stance set to {stance.name}")

        # --- 3. Target Prioritization based on Final Stance ---
        if stance == ArmyStance.AGGRESSIVE:
            # Target the enemy's most vulnerable known townhall.
            if cache.known_enemy_townhalls.exists:
                target = cache.known_enemy_townhalls.closest_to(
                    self.bot.start_location
                ).position
            # If no townhalls are known, target any known structure.
            elif cache.known_enemy_structures.exists:
                target = cache.known_enemy_structures.closest_to(
                    self.bot.enemy_start_locations[0]
                ).position
            # Fallback to the enemy's starting location.
            else:
                target = self.bot.enemy_start_locations[0]

            setattr(plan, "target_location", target)
            cache.logger.debug(f"Aggressive target set to {target.rounded}")

        else:  # Defensive Stance (when not under attack)
            # Default to the safe rally point calculated by PositioningManager.
            target = getattr(plan, "rally_point", self.bot.main_base_ramp.top_center)
            setattr(plan, "target_location", target)
            cache.logger.debug(f"Defensive rally set to {target.rounded}")

    async def execute(
        self, cache: "GlobalCache", plan: "FramePlan", bus: "EventBus"
    ) -> list[CommandFunctor]:
        """
        Executes the director's logic and orchestrates its managers.
        """
        # 1. Director's High-Level Logic: Set the plan for the frame.
        self._determine_stance_and_target(cache, plan)

        # 2. Orchestrate Subordinate Managers to execute the plan.
        actions: list[CommandFunctor] = []
        for manager in self.managers:
            manager_actions = await manager.execute(cache, plan, bus)
            actions.extend(manager_actions)

        return actions
