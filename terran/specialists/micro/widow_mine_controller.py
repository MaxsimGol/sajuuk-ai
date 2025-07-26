# terran/specialists/micro/widow_mine_controller.py
from __future__ import annotations
from typing import TYPE_CHECKING, List, Set, Tuple

from sc2.ids.ability_id import AbilityId
from sc2.unit import Unit
from sc2.position import Point2

from core.frame_plan import ArmyStance
from core.interfaces.controller_abc import ControllerABC
from core.types import CommandFunctor
from terran.tactics.micro_context import MicroContext

if TYPE_CHECKING:
    from sc2.units import Units
    from core.frame_plan import FramePlan

# --- Tunable Constants ---
# How far ahead of the army to place mines when pushing.
OFFENSIVE_LEAPFROG_DISTANCE = 8
# Max distance a burrowed mine can be from its army before repositioning.
REPOSITION_DISTANCE = 15


class WidowMineController(ControllerABC):
    """
    Area Denial Specialist. Manages Widow Mines to create defensive fields
    and provide offensive splash damage by leapfrogging with the army.
    """

    def execute(self, context: "MicroContext") -> Tuple[List[CommandFunctor], Set[int]]:
        """
        Executes micro-management for a squad of Widow Mines.
        """
        # --- Unpack Context ---
        mines = context.units_to_control
        strategic_target = context.target
        cache = context.cache
        plan = context.plan
        main_army = context.bio_squad or context.mech_squad or Units([], self.bot)

        actions: List[CommandFunctor] = []
        if not mines:
            return [], set()

        burrowed_mines = mines.filter(lambda m: m.is_burrowed)
        mobile_mines = mines.filter(lambda m: not m.is_burrowed)

        for mine in burrowed_mines:
            action = self._handle_burrowed_mine(mine, main_army, plan)
            if action:
                actions.append(action)

        for mine in mobile_mines:
            action = self._handle_mobile_mine(mine, strategic_target, main_army, plan)
            if action:
                actions.append(action)

        return actions, mines.tags

    def _handle_burrowed_mine(
        self, mine: Unit, main_army: "Units", plan: "FramePlan"
    ) -> CommandFunctor | None:
        """Decides if a burrowed mine should unburrow to reposition."""

        # Don't unburrow if weapon is still on its initial long cooldown.
        if mine.weapon_cooldown > 20:
            return None

        # Determine the army's current frontline position.
        if not main_army.exists:
            frontline = plan.defensive_position or self.bot.start_location
        else:
            frontline = main_army.center

        # Unburrow if the army has moved too far away.
        if mine.distance_to(frontline) > REPOSITION_DISTANCE:
            return lambda m=mine: m(AbilityId.BURROWUP_WIDOWMINE)

        return None

    def _handle_mobile_mine(
        self,
        mine: Unit,
        strategic_target: "Point2",
        main_army: "Units",
        plan: "FramePlan",
    ) -> CommandFunctor | None:
        """Decides where a mobile mine should move and when it should burrow."""

        # A burrowed mine's attack is an ability, so we can check can_cast.
        if not self.bot.can_cast(mine, AbilityId.WIDOWMINEATTACK_WIDOWMINEATTACK):
            # Weapon is on cooldown, stay mobile.
            if main_army.exists:
                # Follow the army while waiting for cooldown.
                follow_position = main_army.center.towards(mine.position, -3)
                if mine.distance_to(follow_position) > 2:
                    return lambda m=mine, p=follow_position: m.move(p)
            return None  # Wait for cooldown to finish.

        # Determine the target burrow position based on army stance.
        if plan.army_stance == ArmyStance.DEFENSIVE:
            target_pos = plan.defensive_position
        else:  # AGGRESSIVE or HARASS
            if main_army.exists:
                target_pos = main_army.center.towards(
                    strategic_target, OFFENSIVE_LEAPFROG_DISTANCE
                )
            else:
                target_pos = strategic_target

        # If we are close to the target position, burrow.
        if mine.distance_to(target_pos) < 3:
            return lambda m=mine: m(AbilityId.BURROWDOWN_WIDOWMINE)
        # Otherwise, move towards the target position.
        else:
            return lambda m=mine, p=target_pos: m.move(p)
