# Sajuuk AI Project Context

---

### File: `Files description.md`

```markdown
### **Directory: `terran/general/`**

#### **File: `terran_general.py`**
*   **Role:** The Field Marshal. This is the highest-level strategic component for the Terran race, acting as the bridge between the race-agnostic Conductor (`sajuuk.py`) and the bot's functional Directorates.
*   **Core Responsibilities:**
    1.  **Orchestration:** Its primary job is to call the `execute()` method on each of its three main Directors (`Infrastructure`, `Capability`, `Tactics`) in a strict, strategically significant order on every game step.
    2.  **`FramePlan` Creation:** At the beginning of each `execute_step` call, it instantiates a new, empty `FramePlan` object. This "scratchpad" is then passed down through the hierarchy, ensuring all decisions for that frame are based on a clean slate of intentions.
    3.  **Action Aggregation:** It collects the lists of `CommandFunctor` actions returned by each Director and aggregates them into a single master list, which is then returned to the Conductor for final execution.
*   **Key Interactions:**
    *   **Receives:** The `GlobalCache`, a new `FramePlan`, and the `EventBus` from the Conductor.
    *   **Calls:** `infrastructure_director.execute()`, `capability_director.execute()`, `tactical_director.execute()`.
    *   **Returns:** A `list[CommandFunctor]` to the Conductor.

---

### **Directory: `terran/infrastructure/`**

This directorate is responsible for building and maintaining the bot's entire economic engine.

#### **File: `infrastructure_director.py`**
*   **Role:** The Chancellor. It manages the overall economic strategy and allocates resources.
*   **Core Responsibilities:**
    1.  **Budget Allocation:** Its most critical task is to analyze the game state via the `GlobalCache` and **write the official resource budget for the frame to the `FramePlan`** (e.g., `plan.set_budget(infra=20, capa=80)`). This decision dictates the spending priorities for the entire AI on that step.
    2.  **Goal Setting:** It sets high-level economic goals, which are read by its subordinate managers from the `FramePlan` (e.g., "Our target worker count is 66," "Our stance is 'Greedy'").
    3.  **Orchestration:** It calls the `execute()` method on its subordinate managers (`SCVManager`, `ExpansionManager`, etc.).
*   **Key Interactions:**
    *   **Reads:** `GlobalCache` for income, worker counts, etc.
    *   **Writes:** The `ResourceBudget` to the `FramePlan`.
    *   **Calls:** All managers within the `infrastructure` directorate.
    *   **Returns:** An aggregated list of `CommandFunctor`s from its managers.

#### **File: `units/scv_manager.py`**
*   **Role:** Workforce Manager.
*   **Core Responsibilities:**
    1.  **SCV Production:** Checks if the current worker count (from `GlobalCache`) is below the target set by the Director. If so, and if affordable, it returns a `CommandFunctor` to train an SCV.
    2.  **Worker Assignment:** Identifies idle SCVs from the `GlobalCache` and assigns them to the most undersaturated mineral line, returning `gather` command functors.
*   **Key Interactions:**
    *   **Reads:** `GlobalCache` for worker count, townhall locations, and mineral saturation. `FramePlan` for the target worker count goal.
    *   **Returns:** `CommandFunctor`s for training and gathering.

#### **File: `units/mule_manager.py`**
*   **Role:** Orbital Energy Specialist.
*   **Core Responsibilities:**
    1.  Monitors all Orbital Commands via the `GlobalCache` to find any with 50 or more energy.
    2.  Identifies the mineral line that would most benefit from a MULE.
    3.  Returns a `CommandFunctor` to call down a MULE on that mineral line.
*   **Key Interactions:**
    *   **Reads:** `GlobalCache` for Orbital Commands, their energy, and mineral patch locations.
    *   **Returns:** `CommandFunctor`s for MULE calls.

#### **File: `structures/supply_manager.py`**
*   **Role:** Supply Management.
*   **Core Responsibilities:**
    1.  Calculates the current supply buffer needed based on the number of production structures in the `GlobalCache`.
    2.  Checks if `supply_left` is below this calculated buffer.
    3.  If supply is low, it **publishes** a high-priority `infra.BuildRequest` event to the `EventBus` for a `SUPPLYDEPOT`.
*   **Key Interactions:**
    *   **Reads:** `GlobalCache` for `supply_left` and the list of production structures.
    *   **Writes:** An `Event` to the `EventBus`.
    *   **Returns:** An empty list (it does not issue direct commands).

#### **File: `structures/expansion_manager.py`**
*   **Role:** Strategic Expansion Planner.
*   **Core Responsibilities:**
    1.  Reads the economic stance (e.g., `'Greedy'`) from the `FramePlan`.
    2.  If cleared to expand, it analyzes the `cache.available_expansion_locations` to determine the next safest and closest base location.
    3.  It **publishes** a normal-priority `infra.BuildRequest` event for a `COMMANDCENTER` at that location.
*   **Key Interactions:**
    *   **Reads:** `FramePlan` for its strategic clearance. `GlobalCache` for available expansion locations.
    *   **Writes:** An `Event` to the `EventBus`.
    *   **Returns:** An empty list.

#### **File: `structures/repair_manager.py`**
*   **Role:** Damage Control.
*   **Core Responsibilities:**
    1.  **Subscribes** to the `tactics.UnitTookDamage` event on the `EventBus`.
    2.  When the event handler is triggered, it checks if the damaged unit is a structure or a mechanical unit.
    3.  If so, it finds the nearest idle SCV from the `GlobalCache` and returns a `CommandFunctor` to repair the damaged unit.
*   **Key Interactions:**
    *   **Receives:** Events from the `EventBus`.
    *   **Reads:** `GlobalCache` to find idle SCVs.
    *   **Returns:** `CommandFunctor`s for repair actions (during its `execute` call, which is separate from the event handling).

#### **File: `structures/construction_manager.py`**
*   **Role:** Civil Engineering Service. This is a crucial "service" manager.
*   **Core Responsibilities:**
    1.  **Subscribes** to all `infra.BuildRequest` events on the `EventBus`.
    2.  Maintains an internal queue of all build requests it has received.
    3.  During its `execute` method, it processes its queue. For the highest priority request it can afford, it performs the complex logic of finding a buildable location (`find_placement`) and selecting an appropriate worker.
    4.  It returns the final `build` `CommandFunctor`.
*   **Key Interactions:**
    *   **Receives:** Events from the `EventBus`.
    *   **Reads:** `GlobalCache` for resources and worker locations.
    *   **Returns:** `CommandFunctor`s for all building construction.


### **Directory: `terran/capabilities/`**

This directorate's sole responsibility is to convert the bot's economic resources into tangible military power and technological advantages. It acts as the bot's "industrial-military complex."

#### **File: `capability_director.py`**
*   **Role:** The Quartermaster. This is the central planner for all production and technology.
*   **Core Responsibilities:**
    1.  **Budget Consumption:** Its primary job is to **read the `ResourceBudget` from the `FramePlan`**. This budget, set by the `InfrastructureDirector`, dictates how many resources are available for spending on capabilities this frame.
    2.  **Strategic Goal Translation:** It translates the bot's overall strategy (e.g., "Execute a bio timing attack") into concrete production goals for its subordinate managers. It determines the desired unit composition, tech path, and upgrade priorities.
    3.  **Goal Assignment:** It passes these goals to its managers. For example: `"ArmyUnitManager`, our target unit mix is 70% Marines, 30% Marauders." `"ResearchManager`, prioritize `Stimpack`."
    4.  **Orchestration:** It calls the `execute()` method on its subordinate managers and aggregates their returned actions.
*   **Key Interactions:**
    *   **Reads:** `FramePlan` for the resource budget and strategic goals. `GlobalCache` to understand the current tech tree and unit composition. `EventBus` for scouting alerts that might change production priorities (e.g., `tactics.EnemyTechScouted`).
    *   **Calls:** All managers within the `capabilities` directorate.
    *   **Returns:** An aggregated list of `CommandFunctor`s from its managers.

#### **File: `units/army_unit_manager.py`**
*   **Role:** Unit Production Line Foreman.
*   **Core Responsibilities:**
    1.  **Queue Management:** Maintains an internal, stateful queue of desired army units based on the goals set by the `CapabilityDirector`.
    2.  **Execution:** On each frame, it attempts to fulfill its queue. It checks for idle production structures (`Barracks`, `Factory`, `Starport`) in the `GlobalCache`.
    3.  If an appropriate structure is idle and the bot can afford the unit, it returns a `CommandFunctor` to train that unit (e.g., `lambda: barracks.train(MARINE)`).
*   **Key Interactions:**
    *   **Reads:** `GlobalCache` for available resources and idle production structures. Receives its production goals from the `CapabilityDirector`.
    *   **Returns:** A list of `CommandFunctor`s for training army units.

#### **File: `structures/tech_structure_manager.py`**
*   **Role:** Tech Path Planner.
*   **Core Responsibilities:**
    1.  Determines the next necessary technology structure based on the strategic goals from the `CapabilityDirector` (e.g., "To build Vikings, we need a Starport").
    2.  It checks the `GlobalCache` to see if the required prerequisite structures already exist.
    3.  Once the prerequisites are met, it **publishes** an `infra.BuildRequest` event to the `EventBus` for the required tech building (e.g., `FACTORY`, `STARPORT`, `ARMORY`).
*   **Key Interactions:**
    *   **Reads:** `GlobalCache` to verify existing tech structures. Receives goals from the `CapabilityDirector`.
    *   **Writes:** An `Event` to the `EventBus`.
    *   **Returns:** An empty list.

#### **File: `structures/addon_manager.py`**
*   **Role:** Add-on Specialist.
*   **Core Responsibilities:**
    1.  Manages the construction of `TechLabs` and `Reactors` on production structures.
    2.  It identifies "naked" Barracks, Factories, or Starports from the `GlobalCache` that are idle.
    3.  Based on the production goals (e.g., "we need Marauders, which requires a Tech Lab"), it **publishes** a `infra.BuildRequest` event for the appropriate add-on. The `ConstructionManager` cannot handle add-on requests, so this manager must issue the command directly.
*   **Key Interactions:**
    *   **Reads:** `GlobalCache` for idle, add-on-less production structures. Receives goals from the `CapabilityDirector`.
    *   **Returns:** A list of `CommandFunctor`s for building add-ons (e.g., `lambda: barracks.build(TECHLAB)`). This is an exception to the event-based building rule, as add-ons are abilities of existing structures, not new builds handled by SCVs.

#### **File: `upgrades/research_manager.py`**
*   **Role:** Technology Researcher.
*   **Core Responsibilities:**
    1.  **Queue Management:** Maintains an internal, stateful queue of upgrades to be researched, prioritized by the `CapabilityDirector`.
    2.  **Execution:** On each frame, it checks for the required research structure (e.g., `EngineeringBay`, `Armory`) and ensures it is idle.
    3.  If the structure is ready and the bot can afford the upgrade, it returns a `CommandFunctor` to begin the research (e.g., `lambda: eng_bay.research(TERRANINFANTRYWEAPONSLEVEL1)`).
*   **Key Interactions:**
    *   **Reads:** `GlobalCache` for available resources and idle research structures. Receives upgrade priorities from the `CapabilityDirector`.
    *   **Returns:** A list of `CommandFunctor`s for researching upgrades.


### **Directory: `terran/tactics/`**

This directorate is responsible for controlling the army on the map, gathering information, and making high-level combat decisions. It does not produce anything; it only uses what the `Capabilities` directorate has built.

#### **File: `tactical_director.py`**
*   **Role:** The Grand Tactician. It is the highest-level military authority, making the final call on what the army's overall objective should be for the current frame.
*   **Core Responsibilities:**
    1.  **Stance Determination:** Its most critical task is to analyze the `GlobalCache` (comparing `friendly_army_value` vs. `enemy_army_value`, checking `threat_map`, etc.) and the bot's overall strategy. Based on this, it **writes the official `ArmyStance` to the `FramePlan`** (e.g., `plan.set_army_stance(ArmyStance.AGGRESSIVE)`).
    2.  **Target Prioritization:** It identifies the most strategically valuable target for the army to focus on (e.g., the enemy's newest expansion, a vulnerable tech structure, or a defensive position at home). It writes this target to the `FramePlan`.
    3.  **Orchestration:** It calls the `execute()` method on its subordinate managers to carry out its tactical plan.
*   **Key Interactions:**
    *   **Reads:** `GlobalCache` for army values, threat maps, and enemy positions. `EventBus` for critical alerts.
    *   **Writes:** The `ArmyStance` and primary `target_location` to the `FramePlan`.
    *   **Calls:** All managers within the `tactics` directorate.
    *   **Returns:** An aggregated list of `CommandFunctor`s from its managers.

#### **File: `scouting_manager.py`**
*   **Role:** Intelligence Agency.
*   **Core Responsibilities:**
    1.  **Scout Dispatch:** Manages dedicated scouting units (e.g., an early SCV, a Reaper, or periodic scans). It assigns them patrol routes to key locations like enemy expansion points.
    2.  **Information Publishing:** This manager's primary output is not commands, but **information**. When its scouts discover key enemy buildings or army movements, it **publishes rich, specific events to the `EventBus`** (e.g., `tactics.EnemyTechScouted`, `tactics.EnemyArmyMoved`). These events are crucial triggers for the other Directors to adapt their strategies.
*   **Key Interactions:**
    *   **Reads:** `GlobalCache` to find available units to assign as scouts.
    *   **Writes:** High-value intelligence `Event`s to the `EventBus`.
    *   **Returns:** `CommandFunctor`s for moving its scout units.

#### **File: `army_control_manager.py`**
*   **Role:** Field Commander.
*   **Core Responsibilities:**
    1.  **Squad Management:** It groups individual army units from the `GlobalCache` into logical squads (e.g., "Bio Ball 1," "Tank Line," "Viking Patrol"). This is where the bot's control groups are managed.
    2.  **Order Dispatch:** It reads the `ArmyStance` and `target_location` from the `FramePlan`. It then issues high-level orders to its squads, such as "Squad Bio Ball 1, attack this position."
    3.  **Micro Delegation:** It does **not** handle the fine-grained control of units. Instead, it delegates this to the appropriate `MicroController` specialist. For example, it will pass the "Bio Ball 1" squad object to the `MarineController` and `MedivacController` to execute the actual attack movements and spell-casting.
*   **Key Interactions:**
    *   **Reads:** `GlobalCache` for all available army units. `FramePlan` for the current stance and target.
    *   **Calls:** Specialist micro-controllers from the `specialists/micro/` directory.
    *   **Returns:** A list of `CommandFunctor`s for high-level squad movements and attacks.

#### **File: `positioning_manager.py`**
*   **Role:** Battlefield Topographer. This is a "service" manager that performs analysis for other components.
*   **Core Responsibilities:**
    1.  **Defensive Positions:** Reads the `threat_map` from the `GlobalCache` and identifies the safest, most effective choke points or high-ground positions near friendly bases to use for defense.
    2.  **Rally Points:** Calculates the safest rally point for new units from production buildings, keeping them out of immediate danger.
    3.  **Staging Areas:** When the army stance is `AGGRESSIVE`, it identifies a safe forward position outside the enemy's base to use as a staging area before launching the final attack.
*   **Key Interactions:**
    *   **Reads:** `GlobalCache` for the `threat_map` and map terrain information (`map_ramps`).
    *   **Writes:** Its findings (e.g., `defensive_position`, `rally_point`) to the `FramePlan` for the `ArmyControlManager` to use.
    *   **Returns:** An empty list (its job is analysis, not action).


### **Directory: `terran/specialists/`**

This directory holds small, single-purpose classes that are not part of the main Director-Manager hierarchy. They do not run on every frame by default. Instead, they are instantiated and called upon by Directors or Managers when a specific, complex piece of logic needs to be executed. They are the "how" to the Managers' "what."

#### **Directory: `build_orders/`**

This subdirectory contains various opening strategies for the bot. In the early game, the `CapabilityDirector` will delegate its decision-making to one of these specialists.

##### **File: `two_rax_reaper.py`**
*   **Role:** Strategic Recipe. This class is essentially a data container that represents a specific, timed sequence of production goals.
*   **Core Responsibilities:**
    1.  **Provide a Build Sequence:** It stores a list of build steps, typically as tuples of `(supply_count, item_to_build)`.
    2.  **Act as an Iterator:** It implements the `build_order_abc.py` interface, allowing the `CapabilityDirector` to iterate through it and get the next production goal when the required supply is met.
    3.  Once the build order is complete, it signals this to the `CapabilityDirector`, which then takes over production decisions with its own dynamic logic.
*   **Key Interactions:**
    *   **Instantiated and Used by:** The `CapabilityDirector` during the first few minutes of the game.
    *   **Reads:** Nothing. It is a static data provider.
    *   **Returns:** A sequence of production goals (e.g., `UnitTypeId.BARRACKS`, `UpgradeId.REAPERSPEED`).

#### **Directory: `micro/`**

This subdirectory contains the complex, real-time logic for controlling specific units or abilities on the battlefield. Each controller is an expert in one thing.

##### **File: `marine_controller.py`**
*   **Role:** Infantry Micro Expert.
*   **Core Responsibilities:**
    1.  **Stutter-Stepping:** Manages the "move-shoot-move" animation-canceling micro for a squad of Marines. It will check each Marine's weapon cooldown (`weapon_cooldown`) from the `Unit` object to time its movements perfectly.
    2.  **Stimpack Management:** Decides when it is optimal for the squad to use Stimpack. It analyzes the `threat_map` from the `GlobalCache` and the health of nearby units. It will only stim if the engagement is favorable or necessary for survival, preventing wasteful use of health.
    3.  **Target Prioritization:** For a given squad, it identifies the highest-threat, lowest-health enemy unit (e.g., a Baneling or a High Templar) and focuses fire on it.
*   **Key Interactions:**
    *   **Called by:** The `ArmyControlManager`.
    *   **Receives:** A `squad` (a `Units` object containing only Marines) and the `GlobalCache`.
    *   **Returns:** A list of very specific, low-level `CommandFunctor`s for each Marine in the squad (`attack`, `move`, `stim`).

##### **File: `tank_controller.py`**
*   **Role:** Siege Artillery Specialist.
*   **Core Responsibilities:**
    1.  **Siege/Unsiege Logic:** Its primary job is to decide the optimal time to switch between Tank Mode and Siege Mode.
    2.  It analyzes the `threat_map` and the distance to the nearest enemy units. If a significant number of enemy ground units enter its siege range, it will return a `siege` command. If the threats are gone or are air units, it will `unsiege` to reposition.
*   **Key Interactions:**
    *   **Called by:** The `ArmyControlManager`.
    *   **Receives:** A `squad` of Siege Tanks and the `GlobalCache`.
    *   **Returns:** `CommandFunctor`s for `siege` and `unsiege` abilities.

##### **File: `medivac_controller.py`**
*   **Role:** Combat Medic and Transport Pilot.
*   **Core Responsibilities:**
    1.  **Healing Prioritization:** It scans its assigned bio squad for units with missing health and automatically follows the most damaged unit to provide healing.
    2.  **Boost Management:** When the squad is ordered to move a long distance or needs to escape a bad fight, it will activate `MedivacIgniteAfterburners` to speed up the squad.
    3.  **(Future) Drop Micro:** Manages loading and unloading units for harassment drops.
*   **Key Interactions:**
    *   **Called by:** The `ArmyControlManager`.
    *   **Receives:** A `squad` of Medivacs, the bio squad they are supporting, and the `GlobalCache`.
    *   **Returns:** `CommandFunctor`s for `move`, `heal`, and `boost` abilities.
```

---

### File: `project_structure.md`

```markdown
### Project File Structure

```
.
├── core
│   ├── __init__.py
│   ├── analysis
│   │   ├── analysis_configuration.py
│   │   ├── army_value_analyzer.py
│   │   ├── expansion_analyzer.py
│   │   ├── known_enemy_townhall_analyzer.py
│   │   ├── threat_map_analyzer.py
│   │   └── units_analyzer.py
│   ├── event_bus.py
│   ├── frame_plan.py
│   ├── game_analysis.py
│   ├── global_cache.py
│   ├── interfaces
│   │   ├── __init__.py
│   │   ├── analysis_task_abc.py
│   │   ├── director_abc.py
│   │   ├── manager_abc.py
│   │   └── race_general_abc.py
│   ├── types.py
│   └── utilities
│       ├── __init__.py
│       ├── constants.py
│       ├── events.py
│       ├── geometry.py
│       ├── unit_types.py
│       └── unit_value.py
├── create_context.py
├── Design Document.md
├── Files description.md
├── files.md
├── protoss
│   └── __init__.py
├── python_sc2_library_context.md
├── README.md
├── requirements.txt
├── run.py
├── run_tests.py
├── Sajuuk-vs-EasyZerg.SC2Replay
├── sajuuk.py
├── scrape_sc2_library.py
├── terran
│   ├── __init__.py
│   ├── capabilities
│   │   ├── __init__.py
│   │   ├── capability_director.py
│   │   ├── structures
│   │   │   ├── __init__.py
│   │   │   ├── addon_manager.py
│   │   │   └── tech_structure_manager.py
│   │   ├── units
│   │   │   ├── __init__.py
│   │   │   └── army_unit_manager.py
│   │   └── upgrades
│   │       ├── __init__.py
│   │       └── research_manager.py
│   ├── general
│   │   ├── __init__.py
│   │   └── terran_general.py
│   ├── infrastructure
│   │   ├── __init__.py
│   │   ├── infrastructure_director.py
│   │   ├── structures
│   │   │   ├── __init__.py
│   │   │   ├── construction_manager.py
│   │   │   ├── expansion_manager.py
│   │   │   ├── repair_manager.py
│   │   │   └── supply_manager.py
│   │   └── units
│   │       ├── __init__.py
│   │       ├── mule_manager.py
│   │       └── scv_manager.py
│   ├── specialists
│   │   ├── __init__.py
│   │   ├── build_orders
│   │   │   ├── __init__.py
│   │   │   └── two_rax_reaper.py
│   │   └── micro
│   │       ├── __init__.py
│   │       ├── marine_controller.py
│   │       ├── medivac_controller.py
│   │       └── tank_controller.py
│   └── tactics
│       ├── __init__.py
│       ├── army_control_manager.py
│       ├── positioning_manager.py
│       ├── scouting_manager.py
│       └── tactical_director.py
├── tests
│   ├── __init__.py
│   ├── test_core
│   │   ├── __init__.py
│   │   ├── test_event_bus.py
│   │   ├── test_frame_plan.py
│   │   ├── test_game_analysis.py
│   │   └── test_global_cache.py
│   └── test_terran
│       ├── __init__.py
│       ├── test_capabilities
│       │   ├── __init__.py
│       │   ├── test_capability_director.py
│       │   ├── test_structures
│       │   │   ├── __init__.py
│       │   │   ├── test_addon_manager.py
│       │   │   └── test_tech_structure_manager.py
│       │   ├── test_units
│       │   │   ├── __init__.py
│       │   │   └── test_army_unit_manager.py
│       │   └── test_upgrades
│       │       ├── __init__.py
│       │       └── test_research_manager.py
│       ├── test_general
│       │   ├── __init__.py
│       │   └── test_terran_general.py
│       ├── test_infrastructure
│       │   ├── __init__.py
│       │   ├── test_infrastructure_director.py
│       │   ├── test_structures
│       │   │   ├── __init__.py
│       │   │   ├── test_construction_manager.py
│       │   │   ├── test_expansion_manager.py
│       │   │   ├── test_repair_manager.py
│       │   │   └── test_supply_manager.py
│       │   └── test_units
│       │       ├── __init__.py
│       │       ├── test_mule_manager.py
│       │       └── test_scv_manager.py
│       ├── test_specialists
│       │   ├── __init__.py
│       │   └── test_micro
│       │       ├── __init__.py
│       │       └── test_marine_controller.py
│       └── test_tactics
│           ├── __init__.py
│           ├── test_army_control_manager.py
│           ├── test_positioning_manager.py
│           ├── test_scouting_manager.py
│           └── test_tactical_director.py
└── zerg
    └── __init__.py
```
```

---

### File: `python_sc2_library_context.md`

```markdown
# Python-SC2 Library Source Code Context


---
## Package: `sc2`
---

### File: `sc2/__init__.py`

```python
from pathlib import Path


def is_submodule(path):
    if path.is_file():
        return path.suffix == ".py" and path.stem != "__init__"
    if path.is_dir():
        return (path / "__init__.py").exists()
    return False


__all__ = [p.stem for p in Path(__file__).parent.iterdir() if is_submodule(p)]
```

### File: `sc2/action.py`

```python
from __future__ import annotations

from itertools import groupby
from typing import TYPE_CHECKING

# pyre-ignore[21]
from s2clientprotocol import raw_pb2 as raw_pb

from sc2.position import Point2
from sc2.unit import Unit

if TYPE_CHECKING:
    from sc2.ids.ability_id import AbilityId
    from sc2.unit_command import UnitCommand


def combine_actions(action_iter):
    """
    Example input:
    [
        # Each entry in the list is a unit command, with an ability, unit, target, and queue=boolean
        UnitCommand(AbilityId.TRAINQUEEN_QUEEN, Unit(name='Hive', tag=4353687554), None, False),
        UnitCommand(AbilityId.TRAINQUEEN_QUEEN, Unit(name='Lair', tag=4359979012), None, False),
        UnitCommand(AbilityId.TRAINQUEEN_QUEEN, Unit(name='Hatchery', tag=4359454723), None, False),
    ]
    """
    for key, items in groupby(action_iter, key=lambda a: a.combining_tuple):
        ability: AbilityId
        target: None | Point2 | Unit
        queue: bool
        # See constants.py for combineable abilities
        combineable: bool
        ability, target, queue, combineable = key

        if combineable:
            # Combine actions with no target, e.g. lift, burrowup, burrowdown, siege, unsiege, uproot spines
            cmd = raw_pb.ActionRawUnitCommand(
                ability_id=ability.value, unit_tags={u.unit.tag for u in items}, queue_command=queue
            )
            # Combine actions with target point, e.g. attack_move or move commands on a position
            if isinstance(target, Point2):
                cmd.target_world_space_pos.x = target.x
                cmd.target_world_space_pos.y = target.y
            # Combine actions with target unit, e.g. attack commands directly on a unit
            elif isinstance(target, Unit):
                cmd.target_unit_tag = target.tag
            elif target is not None:
                raise RuntimeError(f"Must target a unit, point or None, found '{target!r}'")

            yield raw_pb.ActionRaw(unit_command=cmd)

        else:
            """
            Return one action for each unit; this is required for certain commands that would otherwise be grouped, and only executed once
            Examples:
            Select 3 hatcheries, build a queen with each hatch - the grouping function would group these unit tags and only issue one train command once to all 3 unit tags - resulting in one total train command
            I imagine the same thing would happen to certain other abilities: Battlecruiser yamato on same target, queen transfuse on same target, ghost snipe on same target, all build commands with the same unit type and also all morphs (zergling to banelings)
            However, other abilities can and should be grouped, see constants.py 'COMBINEABLE_ABILITIES'
            """
            u: UnitCommand
            if target is None:
                for u in items:
                    cmd = raw_pb.ActionRawUnitCommand(
                        ability_id=ability.value, unit_tags={u.unit.tag}, queue_command=queue
                    )
                    yield raw_pb.ActionRaw(unit_command=cmd)
            elif isinstance(target, Point2):
                for u in items:
                    cmd = raw_pb.ActionRawUnitCommand(
                        ability_id=ability.value,
                        unit_tags={u.unit.tag},
                        queue_command=queue,
                        target_world_space_pos=target.as_Point2D,
                    )
                    yield raw_pb.ActionRaw(unit_command=cmd)

            elif isinstance(target, Unit):
                for u in items:
                    cmd = raw_pb.ActionRawUnitCommand(
                        ability_id=ability.value,
                        unit_tags={u.unit.tag},
                        queue_command=queue,
                        target_unit_tag=target.tag,
                    )
                    yield raw_pb.ActionRaw(unit_command=cmd)
            else:
                raise RuntimeError(f"Must target a unit, point or None, found '{target!r}'")
```

### File: `sc2/bot_ai.py`

```python
# pyre-ignore-all-errors[6, 16]
from __future__ import annotations

import math
import random
import warnings
from collections import Counter
from functools import cached_property
from typing import TYPE_CHECKING

from loguru import logger

from sc2.bot_ai_internal import BotAIInternal
from sc2.cache import property_cache_once_per_frame
from sc2.constants import (
    CREATION_ABILITY_FIX,
    EQUIVALENTS_FOR_TECH_PROGRESS,
    PROTOSS_TECH_REQUIREMENT,
    TERRAN_STRUCTURES_REQUIRE_SCV,
    TERRAN_TECH_REQUIREMENT,
    ZERG_TECH_REQUIREMENT,
)
from sc2.data import Alert, Race, Result, Target
from sc2.dicts.unit_research_abilities import RESEARCH_INFO
from sc2.dicts.unit_train_build_abilities import TRAIN_INFO
from sc2.dicts.unit_trained_from import UNIT_TRAINED_FROM
from sc2.dicts.upgrade_researched_from import UPGRADE_RESEARCHED_FROM
from sc2.game_data import AbilityData, Cost
from sc2.ids.ability_id import AbilityId
from sc2.ids.unit_typeid import UnitTypeId
from sc2.ids.upgrade_id import UpgradeId
from sc2.position import Point2
from sc2.unit import Unit
from sc2.units import Units

if TYPE_CHECKING:
    from sc2.game_info import Ramp


class BotAI(BotAIInternal):
    """Base class for bots."""

    EXPANSION_GAP_THRESHOLD = 15

    @property
    def time(self) -> float:
        """Returns time in seconds, assumes the game is played on 'faster'"""
        return self.state.game_loop / 22.4  # / (1/1.4) * (1/16)

    @property
    def time_formatted(self) -> str:
        """Returns time as string in min:sec format"""
        t = self.time
        return f"{int(t // 60):02}:{int(t % 60):02}"

    @property
    def step_time(self) -> tuple[float, float, float, float]:
        """Returns a tuple of step duration in milliseconds.
        First value is the minimum step duration - the shortest the bot ever took
        Second value is the average step duration
        Third value is the maximum step duration - the longest the bot ever took (including on_start())
        Fourth value is the step duration the bot took last iteration
        If called in the first iteration, it returns (inf, 0, 0, 0)"""
        avg_step_duration = (
            (self._total_time_in_on_step / self._total_steps_iterations) if self._total_steps_iterations else 0
        )
        return (
            self._min_step_time * 1000,
            avg_step_duration * 1000,
            self._max_step_time * 1000,
            self._last_step_step_time * 1000,
        )

    # pyre-ignore[11]
    def alert(self, alert_code: Alert) -> bool:
        """
        Check if alert is triggered in the current step.
        Possible alerts are listed here https://github.com/Blizzard/s2client-proto/blob/e38efed74c03bec90f74b330ea1adda9215e655f/s2clientprotocol/sc2api.proto#L679-L702

        Example use::

            from sc2.data import Alert
            if self.alert(Alert.AddOnComplete):
                print("Addon Complete")

        Alert codes::

            AlertError
            AddOnComplete
            BuildingComplete
            BuildingUnderAttack
            LarvaHatched
            MergeComplete
            MineralsExhausted
            MorphComplete
            MothershipComplete
            MULEExpired
            NuclearLaunchDetected
            NukeComplete
            NydusWormDetected
            ResearchComplete
            TrainError
            TrainUnitComplete
            TrainWorkerComplete
            TransformationComplete
            UnitUnderAttack
            UpgradeComplete
            VespeneExhausted
            WarpInComplete

        :param alert_code:
        """
        assert isinstance(alert_code, Alert), f"alert_code {alert_code} is no Alert"
        return alert_code.value in self.state.alerts

    @property
    def start_location(self) -> Point2:
        """
        Returns the spawn location of the bot, using the position of the first created townhall.
        This will be None if the bot is run on an arcade or custom map that does not feature townhalls at game start.
        """
        return self.game_info.player_start_location

    @property
    def enemy_start_locations(self) -> list[Point2]:
        """Possible start locations for enemies."""
        return self.game_info.start_locations

    @cached_property
    def main_base_ramp(self) -> Ramp:
        """Returns the Ramp instance of the closest main-ramp to start location.
        Look in game_info.py for more information about the Ramp class

        Example: See terran ramp wall bot
        """
        # The reason for len(ramp.upper) in {2, 5} is:
        # ParaSite map has 5 upper points, and most other maps have 2 upper points at the main ramp.
        # The map Acolyte has 4 upper points at the wrong ramp (which is closest to the start position).
        try:
            found_main_base_ramp = min(
                (ramp for ramp in self.game_info.map_ramps if len(ramp.upper) in {2, 5}),
                key=lambda r: self.start_location.distance_to(r.top_center),
            )
        except ValueError:
            # Hardcoded hotfix for Honorgrounds LE map, as that map has a large main base ramp with inbase natural
            found_main_base_ramp = min(
                (ramp for ramp in self.game_info.map_ramps if len(ramp.upper) in {4, 9}),
                key=lambda r: self.start_location.distance_to(r.top_center),
            )
        return found_main_base_ramp

    @property_cache_once_per_frame
    def expansion_locations_list(self) -> list[Point2]:
        """Returns a list of expansion positions, not sorted in any way."""
        assert self._expansion_positions_list, (
            "self._find_expansion_locations() has not been run yet, so accessing the list of expansion locations is pointless."
        )
        return self._expansion_positions_list

    @property_cache_once_per_frame
    def expansion_locations_dict(self) -> dict[Point2, Units]:
        """
        Returns dict with the correct expansion position Point2 object as key,
        resources as Units (mineral fields and vespene geysers) as value.

        Caution: This function is slow. If you only need the expansion locations, use the property above.
        """
        assert self._expansion_positions_list, (
            "self._find_expansion_locations() has not been run yet, so accessing the list of expansion locations is pointless."
        )
        expansion_locations: dict[Point2, Units] = {pos: Units([], self) for pos in self._expansion_positions_list}
        for resource in self.resources:
            # It may be that some resources are not mapped to an expansion location
            exp_position: Point2 | None = self._resource_location_to_expansion_position_dict.get(
                resource.position, None
            )
            if exp_position:
                assert exp_position in expansion_locations
                expansion_locations[exp_position].append(resource)
        return expansion_locations

    @property
    def units_created(self) -> Counter[UnitTypeId]:
        """Returns a Counter for all your units and buildings you have created so far.

        This may be used for statistics (at the end of the game) or for strategic decision making.

        CAUTION: This does not properly work at the moment for morphing units and structures. Please use the 'on_unit_type_changed' event to add these morphing unit types manually to 'self._units_created'.
        Issues would arrise in e.g. siege tank morphing to sieged tank, and then morphing back (suddenly the counter counts 2 tanks have been created).

        Examples::

            # Give attack command to enemy base every time 10 marines have been trained
            async def on_unit_created(self, unit: Unit):
                if unit.type_id == UnitTypeId.MARINE:
                    if self.units_created[MARINE] % 10 == 0:
                        for marine in self.units(UnitTypeId.MARINE):
                            marine.attack(self.enemy_start_locations[0])
        """
        return self._units_created

    async def get_available_abilities(
        self, units: list[Unit] | Units, ignore_resource_requirements: bool = False
    ) -> list[list[AbilityId]]:
        """Returns available abilities of one or more units. Right now only checks cooldown, energy cost, and whether the ability has been researched.

        Examples::

            units_abilities = await self.get_available_abilities(self.units)

        or::

            units_abilities = await self.get_available_abilities([self.units.random])

        :param units:
        :param ignore_resource_requirements:"""
        return await self.client.query_available_abilities(units, ignore_resource_requirements)

    async def expand_now(
        self,
        building: UnitTypeId | None = None,
        max_distance: int = 10,
        location: Point2 | None = None,
    ) -> None:
        """Finds the next possible expansion via 'self.get_next_expansion()'. If the target expansion is blocked (e.g. an enemy unit), it will misplace the expansion.

        :param building:
        :param max_distance:
        :param location:"""

        if building is None:
            # self.race is never Race.Random
            start_townhall_type = {
                Race.Protoss: UnitTypeId.NEXUS,
                Race.Terran: UnitTypeId.COMMANDCENTER,
                Race.Zerg: UnitTypeId.HATCHERY,
            }
            building = start_townhall_type[self.race]

        assert isinstance(building, UnitTypeId), f"{building} is no UnitTypeId"

        if not location:
            location = await self.get_next_expansion()
        if not location:
            # All expansions are used up or mined out
            logger.warning("Trying to expand_now() but bot is out of locations to expand to")
            return
        await self.build(building, near=location, max_distance=max_distance, random_alternative=False, placement_step=1)

    async def get_next_expansion(self) -> Point2 | None:
        """Find next expansion location."""

        closest = None
        distance = math.inf
        for el in self.expansion_locations_list:

            def is_near_to_expansion(t):
                return t.distance_to(el) < self.EXPANSION_GAP_THRESHOLD

            if any(map(is_near_to_expansion, self.townhalls)):
                # already taken
                continue

            startp = self.game_info.player_start_location
            d = await self.client.query_pathing(startp, el)
            if d is None:
                continue

            if d < distance:
                distance = d
                closest = el

        return closest

    async def distribute_workers(self, resource_ratio: float = 2) -> None:
        """
        Distributes workers across all the bases taken.
        Keyword `resource_ratio` takes a float. If the current minerals to gas
        ratio is bigger than `resource_ratio`, this function prefer filling gas_buildings
        first, if it is lower, it will prefer sending workers to minerals first.

        NOTE: This function is far from optimal, if you really want to have
        refined worker control, you should write your own distribution function.
        For example long distance mining control and moving workers if a base was killed
        are not being handled.

        WARNING: This is quite slow when there are lots of workers or multiple bases.

        :param resource_ratio:"""
        if not self.mineral_field or not self.workers or not self.townhalls.ready:
            return
        worker_pool = self.workers.idle
        bases = self.townhalls.ready
        gas_buildings = self.gas_buildings.ready

        # list of places that need more workers
        deficit_mining_places = []

        for mining_place in bases | gas_buildings:
            difference = mining_place.surplus_harvesters
            # perfect amount of workers, skip mining place
            if not difference:
                continue
            if mining_place.has_vespene:
                # get all workers that target the gas extraction site
                # or are on their way back from it
                local_workers = self.workers.filter(
                    lambda unit: unit.order_target == mining_place.tag
                    or (unit.is_carrying_vespene and unit.order_target == bases.closest_to(mining_place).tag)
                )
            else:
                # get tags of minerals around expansion
                local_minerals_tags = {
                    mineral.tag for mineral in self.mineral_field if mineral.distance_to(mining_place) <= 8
                }
                # get all target tags a worker can have
                # tags of the minerals he could mine at that base
                # get workers that work at that gather site
                local_workers = self.workers.filter(
                    lambda unit: unit.order_target in local_minerals_tags
                    or (unit.is_carrying_minerals and unit.order_target == mining_place.tag)
                )
            # too many workers
            if difference > 0:
                for worker in local_workers[:difference]:
                    worker_pool.append(worker)
            # too few workers
            # add mining place to deficit bases for every missing worker
            else:
                deficit_mining_places += [mining_place for _ in range(-difference)]

        # prepare all minerals near a base if we have too many workers
        # and need to send them to the closest patch
        all_minerals_near_base = []
        if len(worker_pool) > len(deficit_mining_places):
            all_minerals_near_base = [
                mineral
                for mineral in self.mineral_field
                if any(mineral.distance_to(base) <= 8 for base in self.townhalls.ready)
            ]
        # distribute every worker in the pool
        for worker in worker_pool:
            # as long as have workers and mining places
            if deficit_mining_places:
                # choose only mineral fields first if current mineral to gas ratio is less than target ratio
                if self.vespene and self.minerals / self.vespene < resource_ratio:
                    possible_mining_places = [place for place in deficit_mining_places if not place.vespene_contents]
                # else prefer gas
                else:
                    possible_mining_places = [place for place in deficit_mining_places if place.vespene_contents]
                # if preferred type is not available any more, get all other places
                if not possible_mining_places:
                    possible_mining_places = deficit_mining_places
                # find closest mining place
                current_place = min(deficit_mining_places, key=lambda place: place.distance_to(worker))
                # remove it from the list
                deficit_mining_places.remove(current_place)
                # if current place is a gas extraction site, go there
                if current_place.vespene_contents:
                    worker.gather(current_place)
                # if current place is a gas extraction site,
                # go to the mineral field that is near and has the most minerals left
                else:
                    local_minerals = (
                        mineral for mineral in self.mineral_field if mineral.distance_to(current_place) <= 8
                    )
                    # local_minerals can be empty if townhall is misplaced
                    target_mineral = max(local_minerals, key=lambda mineral: mineral.mineral_contents, default=None)
                    if target_mineral:
                        worker.gather(target_mineral)
            # more workers to distribute than free mining spots
            # send to closest if worker is doing nothing
            elif worker.is_idle and all_minerals_near_base:
                target_mineral = min(all_minerals_near_base, key=lambda mineral: mineral.distance_to(worker))
                worker.gather(target_mineral)
            else:
                # there are no deficit mining places and worker is not idle
                # so dont move him
                pass

    @property_cache_once_per_frame
    def owned_expansions(self) -> dict[Point2, Unit]:
        """Dict of expansions owned by the player with mapping {expansion_location: townhall_structure}."""
        owned = {}
        for el in self.expansion_locations_list:

            def is_near_to_expansion(t):
                return t.distance_to(el) < self.EXPANSION_GAP_THRESHOLD

            th = next((x for x in self.townhalls if is_near_to_expansion(x)), None)
            if th:
                owned[el] = th
        return owned

    def calculate_supply_cost(self, unit_type: UnitTypeId) -> float:
        """
        This function calculates the required supply to train or morph a unit.
        The total supply of a baneling is 0.5, but a zergling already uses up 0.5 supply, so the morph supply cost is 0.
        The total supply of a ravager is 3, but a roach already uses up 2 supply, so the morph supply cost is 1.
        The required supply to build zerglings is 1 because they pop in pairs, so this function returns 1 because the larva morph command requires 1 free supply.

        Example::

            roach_supply_cost = self.calculate_supply_cost(UnitTypeId.ROACH) # Is 2
            ravager_supply_cost = self.calculate_supply_cost(UnitTypeId.RAVAGER) # Is 1
            baneling_supply_cost = self.calculate_supply_cost(UnitTypeId.BANELING) # Is 0

        :param unit_type:"""
        if unit_type in {UnitTypeId.ZERGLING}:
            return 1
        if unit_type in {UnitTypeId.BANELING}:
            return 0
        unit_supply_cost = self.game_data.units[unit_type.value]._proto.food_required
        if unit_supply_cost > 0 and unit_type in UNIT_TRAINED_FROM and len(UNIT_TRAINED_FROM[unit_type]) == 1:
            producer: UnitTypeId
            for producer in UNIT_TRAINED_FROM[unit_type]:
                producer_unit_data = self.game_data.units[producer.value]
                if producer_unit_data._proto.food_required <= unit_supply_cost:
                    producer_supply_cost = producer_unit_data._proto.food_required
                    unit_supply_cost -= producer_supply_cost
        return unit_supply_cost

    def can_feed(self, unit_type: UnitTypeId) -> bool:
        """Checks if you have enough free supply to build the unit

        Example::

            cc = self.townhalls.idle.random_or(None)
            # self.townhalls can be empty or there are no idle townhalls
            if cc and self.can_feed(UnitTypeId.SCV):
                cc.train(UnitTypeId.SCV)

        :param unit_type:"""
        required = self.calculate_supply_cost(unit_type)
        # "required <= 0" in case self.supply_left is negative
        return required <= 0 or self.supply_left >= required

    def calculate_unit_value(self, unit_type: UnitTypeId) -> Cost:
        """
        Unlike the function below, this function returns the value of a unit given by the API (e.g. the resources lost value on kill).

        Examples::

            self.calculate_value(UnitTypeId.ORBITALCOMMAND) == Cost(550, 0)
            self.calculate_value(UnitTypeId.RAVAGER) == Cost(100, 100)
            self.calculate_value(UnitTypeId.ARCHON) == Cost(175, 275)

        :param unit_type:
        """
        unit_data = self.game_data.units[unit_type.value]
        return Cost(unit_data._proto.mineral_cost, unit_data._proto.vespene_cost)

    def calculate_cost(self, item_id: UnitTypeId | UpgradeId | AbilityId) -> Cost:
        """
        Calculate the required build, train or morph cost of a unit. It is recommended to use the UnitTypeId instead of the ability to create the unit.
        The total cost to create a ravager is 100/100, but the actual morph cost from roach to ravager is only 25/75, so this function returns 25/75.

        It is adviced to use the UnitTypeId instead of the AbilityId. Instead of::

            self.calculate_cost(AbilityId.UPGRADETOORBITAL_ORBITALCOMMAND)

        use::

            self.calculate_cost(UnitTypeId.ORBITALCOMMAND)

        More examples::

            from sc2.game_data import Cost

            self.calculate_cost(UnitTypeId.BROODLORD) == Cost(150, 150)
            self.calculate_cost(UnitTypeId.RAVAGER) == Cost(25, 75)
            self.calculate_cost(UnitTypeId.BANELING) == Cost(25, 25)
            self.calculate_cost(UnitTypeId.ORBITALCOMMAND) == Cost(150, 0)
            self.calculate_cost(UnitTypeId.REACTOR) == Cost(50, 50)
            self.calculate_cost(UnitTypeId.TECHLAB) == Cost(50, 25)
            self.calculate_cost(UnitTypeId.QUEEN) == Cost(150, 0)
            self.calculate_cost(UnitTypeId.HATCHERY) == Cost(300, 0)
            self.calculate_cost(UnitTypeId.LAIR) == Cost(150, 100)
            self.calculate_cost(UnitTypeId.HIVE) == Cost(200, 150)

        :param item_id:
        """
        if isinstance(item_id, UnitTypeId):
            # Fix cost for reactor and techlab where the API returns 0 for both
            if item_id in {UnitTypeId.REACTOR, UnitTypeId.TECHLAB, UnitTypeId.ARCHON, UnitTypeId.BANELING}:
                if item_id == UnitTypeId.REACTOR:
                    return Cost(50, 50)
                if item_id == UnitTypeId.TECHLAB:
                    return Cost(50, 25)
                if item_id == UnitTypeId.BANELING:
                    return Cost(25, 25)
                if item_id == UnitTypeId.ARCHON:
                    return self.calculate_unit_value(UnitTypeId.ARCHON)
            unit_data = self.game_data.units[item_id.value]
            # Cost of morphs is automatically correctly calculated by 'calculate_ability_cost'
            return self.game_data.calculate_ability_cost(unit_data.creation_ability.exact_id)

        if isinstance(item_id, UpgradeId):
            cost = self.game_data.upgrades[item_id.value].cost
        else:
            # Is already AbilityId
            cost = self.game_data.calculate_ability_cost(item_id)
        return cost

    def can_afford(self, item_id: UnitTypeId | UpgradeId | AbilityId, check_supply_cost: bool = True) -> bool:
        """Tests if the player has enough resources to build a unit or structure.

        Example::

            cc = self.townhalls.idle.random_or(None)
            # self.townhalls can be empty or there are no idle townhalls
            if cc and self.can_afford(UnitTypeId.SCV):
                cc.train(UnitTypeId.SCV)

        Example::

            # Current state: we have 150 minerals and one command center and a barracks
            can_afford_morph = self.can_afford(UnitTypeId.ORBITALCOMMAND, check_supply_cost=False)
            # Will be 'True' although the API reports that an orbital is worth 550 minerals, but the morph cost is only 150 minerals

        :param item_id:
        :param check_supply_cost:"""
        cost = self.calculate_cost(item_id)
        if cost.minerals > self.minerals or cost.vespene > self.vespene:
            return False
        if check_supply_cost and isinstance(item_id, UnitTypeId):
            supply_cost = self.calculate_supply_cost(item_id)
            if supply_cost and supply_cost > self.supply_left:
                return False
        return True

    async def can_cast(
        self,
        unit: Unit,
        ability_id: AbilityId,
        target: Unit | Point2 | None = None,
        only_check_energy_and_cooldown: bool = False,
        cached_abilities_of_unit: list[AbilityId] | None = None,
    ) -> bool:
        """Tests if a unit has an ability available and enough energy to cast it.

        Example::

            stalkers = self.units(UnitTypeId.STALKER)
            stalkers_that_can_blink = stalkers.filter(lambda unit: unit.type_id == UnitTypeId.STALKER and (await self.can_cast(unit, AbilityId.EFFECT_BLINK_STALKER, only_check_energy_and_cooldown=True)))

        See data_pb2.py (line 161) for the numbers 1-5 to make sense

        :param unit:
        :param ability_id:
        :param target:
        :param only_check_energy_and_cooldown:
        :param cached_abilities_of_unit:"""
        assert isinstance(unit, Unit), f"{unit} is no Unit object"
        assert isinstance(ability_id, AbilityId), f"{ability_id} is no AbilityId"
        assert isinstance(target, (type(None), Unit, Point2))
        # check if unit has enough energy to cast or if ability is on cooldown
        if cached_abilities_of_unit:
            abilities = cached_abilities_of_unit
        else:
            abilities = (await self.get_available_abilities([unit], ignore_resource_requirements=False))[0]

        if ability_id in abilities:
            if only_check_energy_and_cooldown:
                return True
            cast_range = self.game_data.abilities[ability_id.value]._proto.cast_range
            ability_target: int = self.game_data.abilities[ability_id.value]._proto.target
            # Check if target is in range (or is a self cast like stimpack)
            if (
                ability_target == 1
                or ability_target == Target.PointOrNone.value
                and isinstance(target, Point2)
                and unit.distance_to(target) <= unit.radius + target.radius + cast_range
            ):  # cant replace 1 with "Target.None.value" because ".None" doesnt seem to be a valid enum name
                return True
            # Check if able to use ability on a unit
            if (
                ability_target in {Target.Unit.value, Target.PointOrUnit.value}
                and isinstance(target, Unit)
                and unit.distance_to(target) <= unit.radius + target.radius + cast_range
            ):
                return True
            # Check if able to use ability on a position
            if (
                ability_target in {Target.Point.value, Target.PointOrUnit.value}
                and isinstance(target, Point2)
                and unit.distance_to(target) <= unit.radius + cast_range
            ):
                return True
        return False

    def select_build_worker(self, pos: Unit | Point2, force: bool = False) -> Unit | None:
        """Select a worker to build a building with.

        Example::

            barracks_placement_position = self.main_base_ramp.barracks_correct_placement
            worker = self.select_build_worker(barracks_placement_position)
            # Can return None
            if worker:
                worker.build(UnitTypeId.BARRACKS, barracks_placement_position)

        :param pos:
        :param force:"""
        workers = (
            self.workers.filter(lambda w: (w.is_gathering or w.is_idle) and w.distance_to(pos) < 20) or self.workers
        )
        if workers:
            for worker in workers.sorted_by_distance_to(pos).prefer_idle:
                if (
                    worker not in self.unit_tags_received_action
                    and not worker.orders
                    or len(worker.orders) == 1
                    and worker.orders[0].ability.id in {AbilityId.MOVE, AbilityId.HARVEST_GATHER}
                ):
                    return worker

            return workers.random if force else None
        return None

    async def can_place_single(self, building: AbilityId | UnitTypeId, position: Point2) -> bool:
        """Checks the placement for only one position."""
        if isinstance(building, UnitTypeId):
            creation_ability = self.game_data.units[building.value].creation_ability.id
            return (await self.client._query_building_placement_fast(creation_ability, [position]))[0]
        return (await self.client._query_building_placement_fast(building, [position]))[0]

    async def can_place(self, building: AbilityData | AbilityId | UnitTypeId, positions: list[Point2]) -> list[bool]:
        """Tests if a building can be placed in the given locations.

        Example::

            barracks_placement_position = self.main_base_ramp.barracks_correct_placement
            worker = self.select_build_worker(barracks_placement_position)
            # Can return None
            if worker and (await self.can_place(UnitTypeId.BARRACKS, [barracks_placement_position])[0]:
                worker.build(UnitTypeId.BARRACKS, barracks_placement_position)

        :param building:
        :param position:"""
        building_type = type(building)
        assert type(building) in {AbilityData, AbilityId, UnitTypeId}, f"{building}, {building_type}"
        if building_type == UnitTypeId:
            building = self.game_data.units[building.value].creation_ability.id
        elif building_type == AbilityData:
            warnings.warn(
                "Using AbilityData is deprecated and may be removed soon. Please use AbilityId or UnitTypeId instead.",
                DeprecationWarning,
                stacklevel=2,
            )
            building = building_type.id

        if isinstance(positions, (Point2, tuple)):
            warnings.warn(
                "The support for querying single entries will be removed soon. Please use either 'await self.can_place_single(building, position)' or 'await (self.can_place(building, [position]))[0]",
                DeprecationWarning,
                stacklevel=2,
            )
            return await self.can_place_single(building, positions)
        assert isinstance(positions, list), f"Expected an iterable (list, tuple), but was: {positions}"
        assert isinstance(positions[0], Point2), (
            f"List is expected to have Point2, but instead had: {positions[0]} {type(positions[0])}"
        )
        return await self.client._query_building_placement_fast(building, positions)

    async def find_placement(
        self,
        building: UnitTypeId | AbilityId,
        near: Point2,
        max_distance: int = 20,
        random_alternative: bool = True,
        placement_step: int = 2,
        addon_place: bool = False,
    ) -> Point2 | None:
        """Finds a placement location for building.

        Example::

            if self.townhalls:
                cc = self.townhalls[0]
                depot_position = await self.find_placement(UnitTypeId.SUPPLYDEPOT, near=cc)

        :param building:
        :param near:
        :param max_distance:
        :param random_alternative:
        :param placement_step:
        :param addon_place:"""

        assert isinstance(building, (AbilityId, UnitTypeId))
        assert isinstance(near, Point2), f"{near} is no Point2 object"

        if isinstance(building, UnitTypeId):
            building = self.game_data.units[building.value].creation_ability.id

        if await self.can_place_single(building, near) and (
            not addon_place or await self.can_place_single(UnitTypeId.SUPPLYDEPOT, near.offset((2.5, -0.5)))
        ):
            return near

        if max_distance == 0:
            return None

        for distance in range(placement_step, max_distance, placement_step):
            possible_positions = [
                Point2(p).offset(near).to2
                for p in (
                    [(dx, -distance) for dx in range(-distance, distance + 1, placement_step)]
                    + [(dx, distance) for dx in range(-distance, distance + 1, placement_step)]
                    + [(-distance, dy) for dy in range(-distance, distance + 1, placement_step)]
                    + [(distance, dy) for dy in range(-distance, distance + 1, placement_step)]
                )
            ]
            res = await self.client._query_building_placement_fast(building, possible_positions)
            # Filter all positions if building can be placed
            possible = [p for r, p in zip(res, possible_positions) if r]

            if addon_place:
                # Filter remaining positions if addon can be placed
                res = await self.client._query_building_placement_fast(
                    AbilityId.TERRANBUILDDROP_SUPPLYDEPOTDROP,
                    [p.offset((2.5, -0.5)) for p in possible],
                )
                possible = [p for r, p in zip(res, possible) if r]

            if not possible:
                continue

            if random_alternative:
                return random.choice(possible)
            return min(possible, key=lambda p: p.distance_to_point2(near))
        return None

    # TODO: improve using cache per frame
    def already_pending_upgrade(self, upgrade_type: UpgradeId) -> float:
        """Check if an upgrade is being researched

        Returns values are::

            0 # not started
            0 < x < 1 # researching
            1 # completed

        Example::

            stim_completion_percentage = self.already_pending_upgrade(UpgradeId.STIMPACK)

        :param upgrade_type:
        """
        assert isinstance(upgrade_type, UpgradeId), f"{upgrade_type} is no UpgradeId"
        if upgrade_type in self.state.upgrades:
            return 1
        creationAbilityID = self.game_data.upgrades[upgrade_type.value].research_ability.exact_id
        for structure in self.structures.filter(lambda unit: unit.is_ready):
            for order in structure.orders:
                if order.ability.exact_id == creationAbilityID:
                    return order.progress
        return 0

    def structure_type_build_progress(self, structure_type: UnitTypeId | int) -> float:
        """
        Returns the build progress of a structure type.

        Return range: 0 <= x <= 1 where
            0: no such structure exists
            0 < x < 1: at least one structure is under construction, returns the progress of the one with the highest progress
            1: we have at least one such structure complete

        Example::

            # Assuming you have one barracks building at 0.5 build progress:
            progress = self.structure_type_build_progress(UnitTypeId.BARRACKS)
            print(progress)
            # This prints out 0.5

            # If you want to save up money for mutalisks, you can now save up once the spire is nearly completed:
            spire_almost_completed: bool = self.structure_type_build_progress(UnitTypeId.SPIRE) > 0.75

            # If you have a Hive completed but no lair, this function returns 1.0 for the following:
            self.structure_type_build_progress(UnitTypeId.LAIR)

            # Assume you have 2 command centers in production, one has 0.5 build_progress and the other 0.2, the following returns 0.5
            highest_progress_of_command_center: float = self.structure_type_build_progress(UnitTypeId.COMMANDCENTER)

        :param structure_type:
        """
        assert isinstance(structure_type, (int, UnitTypeId)), (
            f"Needs to be int or UnitTypeId, but was: {type(structure_type)}"
        )
        if isinstance(structure_type, int):
            structure_type_value: int = structure_type
            structure_type = UnitTypeId(structure_type_value)
        else:
            structure_type_value = structure_type.value
        assert structure_type_value, f"structure_type can not be 0 or NOTAUNIT, but was: {structure_type_value}"
        equiv_values: set[int] = {structure_type_value} | {
            s_type.value for s_type in EQUIVALENTS_FOR_TECH_PROGRESS.get(structure_type, set())
        }
        # SUPPLYDEPOTDROP is not in self.game_data.units, so bot_ai should not check the build progress via creation ability (worker abilities)
        if structure_type_value not in self.game_data.units:
            return max((s.build_progress for s in self.structures if s._proto.unit_type in equiv_values), default=0)
        creation_ability_data: AbilityData = self.game_data.units[structure_type_value].creation_ability
        if creation_ability_data is None:
            return 0
        creation_ability: AbilityId = creation_ability_data.exact_id
        max_value = max(
            [s.build_progress for s in self.structures if s._proto.unit_type in equiv_values]
            + [self._abilities_count_and_build_progress[1].get(creation_ability, 0)],
            default=0,
        )
        return max_value

    def tech_requirement_progress(self, structure_type: UnitTypeId) -> float:
        """Returns the tech requirement progress for a specific building

        Example::

            # Current state: supply depot is at 50% completion
            tech_requirement = self.tech_requirement_progress(UnitTypeId.BARRACKS)
            print(tech_requirement) # Prints 0.5 because supply depot is half way done

        Example::

            # Current state: your bot has one hive, no lair
            tech_requirement = self.tech_requirement_progress(UnitTypeId.HYDRALISKDEN)
            print(tech_requirement) # Prints 1 because a hive exists even though only a lair is required

        Example::

            # Current state: One factory is flying and one is half way done
            tech_requirement = self.tech_requirement_progress(UnitTypeId.STARPORT)
            print(tech_requirement) # Prints 1 because even though the type id of the flying factory is different, it still has build progress of 1 and thus tech requirement is completed

        :param structure_type:"""
        race_dict = {
            Race.Protoss: PROTOSS_TECH_REQUIREMENT,
            Race.Terran: TERRAN_TECH_REQUIREMENT,
            Race.Zerg: ZERG_TECH_REQUIREMENT,
        }
        unit_info_id = race_dict[self.race][structure_type]
        unit_info_id_value = unit_info_id.value
        # The following commented out line is unreliable for ghost / thor as they return 0 which is incorrect
        # unit_info_id_value = self.game_data.units[structure_type.value]._proto.tech_requirement
        if not unit_info_id_value:  # Equivalent to "if unit_info_id_value == 0:"
            return 1
        progresses: list[float] = [self.structure_type_build_progress(unit_info_id_value)]
        for equiv_structure in EQUIVALENTS_FOR_TECH_PROGRESS.get(unit_info_id, []):
            progresses.append(self.structure_type_build_progress(equiv_structure.value))
        return max(progresses)

    def already_pending(self, unit_type: UpgradeId | UnitTypeId) -> float:
        """
        Returns a number of buildings or units already in progress, or if a
        worker is en route to build it. This also includes queued orders for
        workers and build queues of buildings.

        Example::

            amount_of_scv_in_production: int = self.already_pending(UnitTypeId.SCV)
            amount_of_CCs_in_queue_and_production: int = self.already_pending(UnitTypeId.COMMANDCENTER)
            amount_of_lairs_morphing: int = self.already_pending(UnitTypeId.LAIR)

        :param unit_type:
        """
        if isinstance(unit_type, UpgradeId):
            return self.already_pending_upgrade(unit_type)
        try:
            ability = self.game_data.units[unit_type.value].creation_ability.exact_id
        except AttributeError:
            if unit_type in CREATION_ABILITY_FIX:
                # Hotfix for checking pending archons
                if unit_type == UnitTypeId.ARCHON:
                    return self._abilities_count_and_build_progress[0][AbilityId.ARCHON_WARP_TARGET] / 2
                # Hotfix for rich geysirs
                return self._abilities_count_and_build_progress[0][CREATION_ABILITY_FIX[unit_type]]
            logger.error(f"Uncaught UnitTypeId: {unit_type}")
            return 0
        return self._abilities_count_and_build_progress[0][ability]

    def worker_en_route_to_build(self, unit_type: UnitTypeId) -> float:
        """This function counts how many workers are on the way to start the construction a building.

        :param unit_type:"""
        ability = self.game_data.units[unit_type.value].creation_ability.exact_id
        return self._worker_orders[ability]

    @property_cache_once_per_frame
    def structures_without_construction_SCVs(self) -> Units:
        """Returns all structures that do not have an SCV constructing it.
        Warning: this function may move to become a Units filter."""
        worker_targets: set[int | Point2] = set()
        for worker in self.workers:
            # Ignore repairing workers
            if not worker.is_constructing_scv:
                continue
            for order in worker.orders:
                # When a construction is resumed, the worker.orders[0].target is the tag of the structure, else it is a Point2
                worker_targets.add(order.target)
        return self.structures.filter(
            lambda structure: structure.build_progress < 1
            # Redundant check?
            and structure.type_id in TERRAN_STRUCTURES_REQUIRE_SCV
            and structure.position not in worker_targets
            and structure.tag not in worker_targets
            and structure.tag in self._structures_previous_map
            and self._structures_previous_map[structure.tag].build_progress == structure.build_progress
        )

    async def build(
        self,
        building: UnitTypeId,
        near: Unit | Point2,
        max_distance: int = 20,
        build_worker: Unit | None = None,
        random_alternative: bool = True,
        placement_step: int = 2,
    ) -> bool:
        """Not recommended as this function checks many positions if it "can place" on them until it found a valid
        position. Also if the given position is not placeable, this function tries to find a nearby position to place
        the structure. Then orders the worker to start the construction.

        :param building:
        :param near:
        :param max_distance:
        :param build_worker:
        :param random_alternative:
        :param placement_step:"""

        assert isinstance(near, (Unit, Point2))
        if not self.can_afford(building):
            return False
        p = None
        gas_buildings = {UnitTypeId.EXTRACTOR, UnitTypeId.ASSIMILATOR, UnitTypeId.REFINERY}
        if isinstance(near, Unit) and building not in gas_buildings:
            near = near.position
        if isinstance(near, Point2):
            near = near.to2
        if isinstance(near, Point2):
            p = await self.find_placement(building, near, max_distance, random_alternative, placement_step)
            if p is None:
                return False
        builder = build_worker or self.select_build_worker(near)
        if builder is None:
            return False
        if building in gas_buildings:
            assert isinstance(near, Unit)
            builder.build_gas(near)
            return True
        self.do(builder.build(building, p), subtract_cost=True, ignore_warning=True)
        return True

    def train(
        self,
        unit_type: UnitTypeId,
        amount: int = 1,
        closest_to: Point2 | None = None,
        train_only_idle_buildings: bool = True,
    ) -> int:
        """Trains a specified number of units. Trains only one if amount is not specified.
        Warning: currently has issues with warp gate warp ins

        Very generic function. Please use with caution and report any bugs!

        Example Zerg::

            self.train(UnitTypeId.QUEEN, 5)
            # This should queue 5 queens in 5 different townhalls if you have enough townhalls, enough minerals and enough free supply left

        Example Terran::

            # Assuming you have 2 idle barracks with reactors, one barracks without addon and one with techlab
            # It should only queue 4 marines in the 2 idle barracks with reactors
            self.train(UnitTypeId.MARINE, 4)

        Example distance to::

            # If you want to train based on distance to a certain point, you can use "closest_to"
            self.train(UnitTypeId.MARINE, 4, closest_to = self.game_info.map_center)


        :param unit_type:
        :param amount:
        :param closest_to:
        :param train_only_idle_buildings:"""
        # Tech requirement not met
        if self.tech_requirement_progress(unit_type) < 1:
            race_dict = {
                Race.Protoss: PROTOSS_TECH_REQUIREMENT,
                Race.Terran: TERRAN_TECH_REQUIREMENT,
                Race.Zerg: ZERG_TECH_REQUIREMENT,
            }
            unit_info_id = race_dict[self.race][unit_type]
            logger.warning(
                f"{self.time_formatted} Trying to produce unit {unit_type} in self.train() but tech requirement is not met: {unit_info_id}"
            )
            return 0

        # Not affordable
        if not self.can_afford(unit_type):
            return 0

        trained_amount = 0
        # All train structure types: queen can made from hatchery, lair, hive
        train_structure_type: set[UnitTypeId] = UNIT_TRAINED_FROM[unit_type]
        train_structures = self.structures if self.race != Race.Zerg else self.structures | self.larva
        requires_techlab = any(
            TRAIN_INFO[structure_type][unit_type].get("requires_techlab", False)
            for structure_type in train_structure_type
        )
        is_protoss = self.race == Race.Protoss
        is_terran = self.race == Race.Terran
        can_have_addons = any(
            u in train_structure_type for u in {UnitTypeId.BARRACKS, UnitTypeId.FACTORY, UnitTypeId.STARPORT}
        )
        # Sort structures closest to a point
        if closest_to is not None:
            train_structures = train_structures.sorted_by_distance_to(closest_to)
        elif can_have_addons:
            # This should sort the structures in ascending order: first structures with reactor, then naked, then with techlab
            train_structures = train_structures.sorted(
                key=lambda structure: -1 * (structure.add_on_tag in self.reactor_tags)
                + 1 * (structure.add_on_tag in self.techlab_tags)
            )

        structure: Unit
        for structure in train_structures:
            # Exit early if we can't afford
            if not self.can_afford(unit_type):
                return trained_amount
            if (
                # If structure hasn't received an action/order this frame
                structure.tag not in self.unit_tags_received_action
                # If structure can train this unit at all
                and structure.type_id in train_structure_type
                # Structure has to be completed to be able to train
                and structure.build_progress == 1
                # If structure is protoss, it needs to be powered to train
                and (not is_protoss or structure.is_powered or structure.type_id == UnitTypeId.NEXUS)
                # Either parameter "train_only_idle_buildings" is False or structure is idle or structure has less than 2 orders and has reactor
                and (
                    not train_only_idle_buildings
                    or len(structure.orders) < 1 + int(structure.add_on_tag in self.reactor_tags)
                )
                # If structure type_id does not accept addons, it cant require a techlab
                # Else we have to check if building has techlab as addon
                and (not requires_techlab or structure.add_on_tag in self.techlab_tags)
            ):
                # Warp in at location
                # TODO: find fast warp in locations either random location or closest to the given parameter "closest_to"
                # TODO: find out which pylons have fast warp in by checking distance to nexus and warpgates.ready
                if structure.type_id == UnitTypeId.WARPGATE:
                    pylons = self.structures(UnitTypeId.PYLON)
                    location = pylons.random.position.random_on_distance(4)
                    successfully_trained = structure.warp_in(unit_type, location)
                else:
                    # Normal train a unit from larva or inside a structure
                    successfully_trained = self.do(
                        structure.train(unit_type),
                        subtract_cost=True,
                        subtract_supply=True,
                        ignore_warning=True,
                    )
                    # Check if structure has reactor: queue same unit again
                    if (
                        # Only terran can have reactors
                        is_terran
                        # Check if we have enough cost or supply for this unit type
                        and self.can_afford(unit_type)
                        # Structure needs to be idle in the current frame
                        and not structure.orders
                        # We are at least 2 away from goal
                        and trained_amount + 1 < amount
                        # Unit type does not require techlab
                        and not requires_techlab
                        # Train structure has reactor
                        and structure.add_on_tag in self.reactor_tags
                    ):
                        trained_amount += 1
                        # With one command queue=False and one queue=True, you can queue 2 marines in a reactored barracks in one frame
                        successfully_trained = self.do(
                            structure.train(unit_type, queue=True),
                            subtract_cost=True,
                            subtract_supply=True,
                            ignore_warning=True,
                        )

                if successfully_trained:
                    trained_amount += 1
                    if trained_amount == amount:
                        # Target unit train amount reached
                        return trained_amount
                else:
                    # Some error occured and we couldn't train the unit
                    return trained_amount
        return trained_amount

    def research(self, upgrade_type: UpgradeId) -> bool:
        """
        Researches an upgrade from a structure that can research it, if it is idle and powered (protoss).
        Returns True if the research was started.
        Return False if the requirement was not met, or the bot did not have enough resources to start the upgrade,
        or the building to research the upgrade was missing or not idle.

        New function. Please report any bugs!

        Example::

            # Try to research zergling movement speed if we can afford it
            # and if at least one pool is at build_progress == 1
            # and we are not researching it yet
            if self.already_pending_upgrade(UpgradeId.ZERGLINGMOVEMENTSPEED) == 0 and self.can_afford(UpgradeId.ZERGLINGMOVEMENTSPEED):
                spawning_pools_ready = self.structures(UnitTypeId.SPAWNINGPOOL).ready
                if spawning_pools_ready:
                    self.research(UpgradeId.ZERGLINGMOVEMENTSPEED)

        :param upgrade_type:
        """
        assert upgrade_type in UPGRADE_RESEARCHED_FROM, (
            f"Could not find upgrade {upgrade_type} in 'research from'-dictionary"
        )

        # Not affordable
        if not self.can_afford(upgrade_type):
            return False

        research_structure_type: UnitTypeId = UPGRADE_RESEARCHED_FROM[upgrade_type]
        # pyre-ignore[9]
        required_tech_building: UnitTypeId | None = RESEARCH_INFO[research_structure_type][upgrade_type].get(
            "required_building", None
        )

        requirement_met = (
            required_tech_building is None or self.structure_type_build_progress(required_tech_building) == 1
        )
        if not requirement_met:
            return False

        is_protoss = self.race == Race.Protoss

        # All upgrades right now that can be researched in spire and hatch can also be researched in their morphs
        equiv_structures = {
            UnitTypeId.SPIRE: {UnitTypeId.SPIRE, UnitTypeId.GREATERSPIRE},
            UnitTypeId.GREATERSPIRE: {UnitTypeId.SPIRE, UnitTypeId.GREATERSPIRE},
            UnitTypeId.HATCHERY: {UnitTypeId.HATCHERY, UnitTypeId.LAIR, UnitTypeId.HIVE},
            UnitTypeId.LAIR: {UnitTypeId.HATCHERY, UnitTypeId.LAIR, UnitTypeId.HIVE},
            UnitTypeId.HIVE: {UnitTypeId.HATCHERY, UnitTypeId.LAIR, UnitTypeId.HIVE},
        }
        # Convert to a set, or equivalent structures are chosen
        # Overlord speed upgrade can be researched from hatchery, lair or hive
        research_structure_types: set[UnitTypeId] = equiv_structures.get(
            research_structure_type, {research_structure_type}
        )

        structure: Unit
        for structure in self.structures:
            if (
                # Structure can research this upgrade
                structure.type_id in research_structure_types
                # If structure hasn't received an action/order this frame
                and structure.tag not in self.unit_tags_received_action
                # Structure is ready / completed
                and structure.is_ready
                # Structure is idle
                and structure.is_idle
                # Structure belongs to protoss and is powered (near pylon)
                and (not is_protoss or structure.is_powered)
            ):
                # Can_afford check was already done earlier in this function
                successful_action: bool = self.do(
                    structure.research(upgrade_type),
                    subtract_cost=True,
                    ignore_warning=True,
                )
                return successful_action
        return False

    async def chat_send(self, message: str, team_only: bool = False) -> None:
        """Send a chat message to the SC2 Client.

        Example::

            await self.chat_send("Hello, this is a message from my bot!")

        :param message:
        :param team_only:"""
        assert isinstance(message, str), f"{message} is not a string"
        await self.client.chat_send(message, team_only)

    def in_map_bounds(self, pos: Point2 | tuple | list) -> bool:
        """Tests if a 2 dimensional point is within the map boundaries of the pixelmaps.

        :param pos:"""
        return (
            self.game_info.playable_area.x
            <= pos[0]
            < self.game_info.playable_area.x + self.game_info.playable_area.width
            and self.game_info.playable_area.y
            <= pos[1]
            < self.game_info.playable_area.y + self.game_info.playable_area.height
        )

    # For the functions below, make sure you are inside the boundaries of the map size.
    def get_terrain_height(self, pos: Point2 | Unit) -> int:
        """Returns terrain height at a position.
        Caution: terrain height is different from a unit's z-coordinate.

        :param pos:"""
        assert isinstance(pos, (Point2, Unit)), "pos is not of type Point2 or Unit"
        pos = pos.position.rounded
        return self.game_info.terrain_height[pos]

    def get_terrain_z_height(self, pos: Point2 | Unit) -> float:
        """Returns terrain z-height at a position.

        :param pos:"""
        assert isinstance(pos, (Point2, Unit)), "pos is not of type Point2 or Unit"
        pos = pos.position.rounded
        return -16 + 32 * self.game_info.terrain_height[pos] / 255

    def in_placement_grid(self, pos: Point2 | Unit) -> bool:
        """Returns True if you can place something at a position.
        Remember, buildings usually use 2x2, 3x3 or 5x5 of these grid points.
        Caution: some x and y offset might be required, see ramp code in game_info.py

        :param pos:"""
        assert isinstance(pos, (Point2, Unit)), "pos is not of type Point2 or Unit"
        pos = pos.position.rounded
        return self.game_info.placement_grid[pos] == 1

    def in_pathing_grid(self, pos: Point2 | Unit) -> bool:
        """Returns True if a ground unit can pass through a grid point.

        :param pos:"""
        assert isinstance(pos, (Point2, Unit)), "pos is not of type Point2 or Unit"
        pos = pos.position.rounded
        return self.game_info.pathing_grid[pos] == 1

    def is_visible(self, pos: Point2 | Unit) -> bool:
        """Returns True if you have vision on a grid point.

        :param pos:"""
        # more info: https://github.com/Blizzard/s2client-proto/blob/9906df71d6909511907d8419b33acc1a3bd51ec0/s2clientprotocol/spatial.proto#L19
        assert isinstance(pos, (Point2, Unit)), "pos is not of type Point2 or Unit"
        pos = pos.position.rounded
        return self.state.visibility[pos] == 2

    def has_creep(self, pos: Point2 | Unit) -> bool:
        """Returns True if there is creep on the grid point.

        :param pos:"""
        assert isinstance(pos, (Point2, Unit)), "pos is not of type Point2 or Unit"
        pos = pos.position.rounded
        return self.state.creep[pos] == 1

    async def on_unit_destroyed(self, unit_tag: int) -> None:
        """
        Override this in your bot class.
        Note that this function uses unit tags and not the unit objects
        because the unit does not exist any more.
        This will event will be called when a unit (or structure, friendly or enemy) dies.
        For enemy units, this only works if the enemy unit was in vision on death.

        :param unit_tag:
        """

    async def on_unit_created(self, unit: Unit) -> None:
        """Override this in your bot class. This function is called when a unit is created.

        :param unit:"""

    async def on_unit_type_changed(self, unit: Unit, previous_type: UnitTypeId) -> None:
        """Override this in your bot class. This function is called when a unit type has changed. To get the current UnitTypeId of the unit, use 'unit.type_id'

        This may happen when a larva morphed to an egg, siege tank sieged, a zerg unit burrowed, a hatchery morphed to lair,
        a corruptor morphed to broodlordcocoon, etc..

        Examples::

            print(f"My unit changed type: {unit} from {previous_type} to {unit.type_id}")

        :param unit:
        :param previous_type:
        """

    async def on_building_construction_started(self, unit: Unit) -> None:
        """
        Override this in your bot class.
        This function is called when a building construction has started.

        :param unit:
        """

    async def on_building_construction_complete(self, unit: Unit) -> None:
        """
        Override this in your bot class. This function is called when a building
        construction is completed.

        :param unit:
        """

    async def on_upgrade_complete(self, upgrade: UpgradeId) -> None:
        """
        Override this in your bot class. This function is called with the upgrade id of an upgrade that was not finished last step and is now.

        :param upgrade:
        """

    async def on_unit_took_damage(self, unit: Unit, amount_damage_taken: float) -> None:
        """
        Override this in your bot class. This function is called when your own unit (unit or structure) took damage.
        It will not be called if the unit died this frame.

        This may be called frequently for terran structures that are burning down, or zerg buildings that are off creep,
        or terran bio units that just used stimpack ability.
        TODO: If there is a demand for it, then I can add a similar event for when enemy units took damage

        Examples::

            print(f"My unit took damage: {unit} took {amount_damage_taken} damage")

        :param unit:
        :param amount_damage_taken:
        """

    async def on_enemy_unit_entered_vision(self, unit: Unit) -> None:
        """
        Override this in your bot class. This function is called when an enemy unit (unit or structure) entered vision (which was not visible last frame).

        :param unit:
        """

    async def on_enemy_unit_left_vision(self, unit_tag: int) -> None:
        """
        Override this in your bot class. This function is called when an enemy unit (unit or structure) left vision (which was visible last frame).
        Same as the self.on_unit_destroyed event, this function is called with the unit's tag because the unit is no longer visible anymore.
        If you want to store a snapshot of the unit, use self._enemy_units_previous_map[unit_tag] for units or self._enemy_structures_previous_map[unit_tag] for structures.

        Examples::

            last_known_unit = self._enemy_units_previous_map.get(unit_tag, None) or self._enemy_structures_previous_map[unit_tag]
            print(f"Enemy unit left vision, last known location: {last_known_unit.position}")

        :param unit_tag:
        """

    async def on_before_start(self) -> None:
        """
        Override this in your bot class. This function is called before "on_start"
        and before "prepare_first_step" that calculates expansion locations.
        Not all data is available yet.
        This function is useful in realtime=True mode to split your workers or start producing the first worker.
        """

    async def on_start(self) -> None:
        """
        Override this in your bot class.
        At this point, game_data, game_info and the first iteration of game_state (self.state) are available.
        """

    async def on_step(self, iteration: int):
        """
        You need to implement this function!
        Override this in your bot class.
        This function is called on every game step (looped in realtime mode).

        :param iteration:
        """
        raise NotImplementedError

    # pyre-ignore[11]
    async def on_end(self, game_result: Result) -> None:
        """Override this in your bot class. This function is called at the end of a game.
        Unsure if this function will be called on the laddermanager client as the bot process may forcefully be terminated.

        :param game_result:"""
```

### File: `sc2/bot_ai_internal.py`

```python
# pyre-ignore-all-errors[6, 16, 29]
from __future__ import annotations

import itertools
import math
import time
import warnings
from abc import ABC
from collections import Counter
from collections.abc import Generator, Iterable
from contextlib import suppress
from typing import TYPE_CHECKING, Any, final

import numpy as np
from loguru import logger

# pyre-ignore[21]
from s2clientprotocol import sc2api_pb2 as sc_pb

from sc2.cache import property_cache_once_per_frame
from sc2.constants import (
    ALL_GAS,
    CREATION_ABILITY_FIX,
    IS_PLACEHOLDER,
    TERRAN_STRUCTURES_REQUIRE_SCV,
    FakeEffectID,
    abilityid_to_unittypeid,
    geyser_ids,
    mineral_ids,
)
from sc2.data import ActionResult, Race, race_townhalls
from sc2.game_data import Cost, GameData
from sc2.game_state import Blip, EffectData, GameState
from sc2.ids.ability_id import AbilityId
from sc2.ids.unit_typeid import UnitTypeId
from sc2.ids.upgrade_id import UpgradeId
from sc2.pixel_map import PixelMap
from sc2.position import Point2
from sc2.unit import Unit
from sc2.unit_command import UnitCommand
from sc2.units import Units

with warnings.catch_warnings():
    warnings.simplefilter("ignore")
    # pyre-ignore[21]
    from scipy.spatial.distance import cdist, pdist

if TYPE_CHECKING:
    from sc2.client import Client
    from sc2.game_info import GameInfo


class BotAIInternal(ABC):
    """Base class for bots."""

    def __init__(self) -> None:
        self._initialize_variables()

    @final
    def _initialize_variables(self) -> None:
        """Called from main.py internally"""
        self.cache: dict[str, Any] = {}
        # Specific opponent bot ID used in sc2ai ladder games http://sc2ai.net/ and on ai arena https://aiarena.net
        # The bot ID will stay the same each game so your bot can "adapt" to the opponent
        if not hasattr(self, "opponent_id"):
            # Prevent overwriting the opponent_id which is set here https://github.com/Hannessa/python-sc2-ladderbot/blob/master/__init__.py#L40
            # otherwise set it to None
            self.opponent_id: str | None = None
        # Select distance calculation method, see _distances_override_functions function
        if not hasattr(self, "distance_calculation_method"):
            self.distance_calculation_method: int = 2
        # Select if the Unit.command should return UnitCommand objects. Set this to True if your bot uses 'unit(ability, target)'
        if not hasattr(self, "unit_command_uses_self_do"):
            self.unit_command_uses_self_do: bool = False
        # This value will be set to True by main.py in self._prepare_start if game is played in realtime (if true, the bot will have limited time per step)
        self.realtime: bool = False
        self.base_build: int = -1
        self.all_units: Units = Units([], self)
        self.units: Units = Units([], self)
        self.workers: Units = Units([], self)
        self.larva: Units = Units([], self)
        self.structures: Units = Units([], self)
        self.townhalls: Units = Units([], self)
        self.gas_buildings: Units = Units([], self)
        self.all_own_units: Units = Units([], self)
        self.enemy_units: Units = Units([], self)
        self.enemy_structures: Units = Units([], self)
        self.all_enemy_units: Units = Units([], self)
        self.resources: Units = Units([], self)
        self.destructables: Units = Units([], self)
        self.watchtowers: Units = Units([], self)
        self.mineral_field: Units = Units([], self)
        self.vespene_geyser: Units = Units([], self)
        self.placeholders: Units = Units([], self)
        self.techlab_tags: set[int] = set()
        self.reactor_tags: set[int] = set()
        self.minerals: int = 50
        self.vespene: int = 0
        self.supply_army: float = 0
        self.supply_workers: float = 12  # Doesn't include workers in production
        self.supply_cap: float = 15
        self.supply_used: float = 12
        self.supply_left: float = 3
        self.idle_worker_count: int = 0
        self.army_count: int = 0
        self.warp_gate_count: int = 0
        self.actions: list[UnitCommand] = []
        self.blips: set[Blip] = set()
        # pyre-ignore[11]
        self.race: Race | None = None
        self.enemy_race: Race | None = None
        self._generated_frame = -100
        self._units_created: Counter = Counter()
        self._unit_tags_seen_this_game: set[int] = set()
        self._units_previous_map: dict[int, Unit] = {}
        self._structures_previous_map: dict[int, Unit] = {}
        self._enemy_units_previous_map: dict[int, Unit] = {}
        self._enemy_structures_previous_map: dict[int, Unit] = {}
        self._all_units_previous_map: dict[int, Unit] = {}
        self._previous_upgrades: set[UpgradeId] = set()
        self._expansion_positions_list: list[Point2] = []
        self._resource_location_to_expansion_position_dict: dict[Point2, Point2] = {}
        self._time_before_step: float = 0
        self._time_after_step: float = 0
        self._min_step_time: float = math.inf
        self._max_step_time: float = 0
        self._last_step_step_time: float = 0
        self._total_time_in_on_step: float = 0
        self._total_steps_iterations: int = 0
        # Internally used to keep track which units received an action in this frame, so that self.train() function does not give the same larva two orders - cleared every frame
        self.unit_tags_received_action: set[int] = set()

    @final
    @property
    def _game_info(self) -> GameInfo:
        """See game_info.py"""
        warnings.warn(
            "Using self._game_info is deprecated and may be removed soon. Please use self.game_info directly.",
            DeprecationWarning,
            stacklevel=2,
        )
        return self.game_info

    @final
    @property
    def _game_data(self) -> GameData:
        """See game_data.py"""
        warnings.warn(
            "Using self._game_data is deprecated and may be removed soon. Please use self.game_data directly.",
            DeprecationWarning,
            stacklevel=2,
        )
        return self.game_data

    @final
    @property
    def _client(self) -> Client:
        """See client.py"""
        warnings.warn(
            "Using self._client is deprecated and may be removed soon. Please use self.client directly.",
            DeprecationWarning,
            stacklevel=2,
        )
        return self.client

    @final
    @property_cache_once_per_frame
    def expansion_locations(self) -> dict[Point2, Units]:
        """Same as the function above."""
        assert self._expansion_positions_list, (
            "self._find_expansion_locations() has not been run yet, so accessing the list of expansion locations is pointless."
        )
        warnings.warn(
            "You are using 'self.expansion_locations', please use 'self.expansion_locations_list' (fast) or 'self.expansion_locations_dict' (slow) instead.",
            DeprecationWarning,
            stacklevel=2,
        )
        return self.expansion_locations_dict

    @final
    def _find_expansion_locations(self) -> None:
        """Ran once at the start of the game to calculate expansion locations."""
        # Idea: create a group for every resource, then merge these groups if
        # any resource in a group is closer than a threshold to any resource of another group

        # Distance we group resources by
        resource_spread_threshold: float = 8.5
        # Create a group for every resource
        resource_groups: list[list[Unit]] = [
            [resource]
            for resource in self.resources
            if resource.name != "MineralField450"  # dont use low mineral count patches
        ]
        # Loop the merging process as long as we change something
        merged_group = True
        height_grid: PixelMap = self.game_info.terrain_height
        while merged_group:
            merged_group = False
            # Check every combination of two groups
            for group_a, group_b in itertools.combinations(resource_groups, 2):
                # Check if any pair of resource of these groups is closer than threshold together
                # And that they are on the same terrain level
                if any(
                    resource_a.distance_to(resource_b) <= resource_spread_threshold
                    # check if terrain height measurement at resources is within 10 units
                    # this is since some older maps have inconsistent terrain height
                    # tiles at certain expansion locations
                    and abs(height_grid[resource_a.position.rounded] - height_grid[resource_b.position.rounded]) <= 10
                    for resource_a, resource_b in itertools.product(group_a, group_b)
                ):
                    # Remove the single groups and add the merged group
                    resource_groups.remove(group_a)
                    resource_groups.remove(group_b)
                    resource_groups.append(group_a + group_b)
                    merged_group = True
                    break
        # Distance offsets we apply to center of each resource group to find expansion position
        offset_range = 7
        offsets = [
            (x, y)
            for x, y in itertools.product(range(-offset_range, offset_range + 1), repeat=2)
            if 4 < math.hypot(x, y) <= 8
        ]
        # Dict we want to return
        centers = {}
        # For every resource group:
        for resources in resource_groups:
            # Possible expansion points
            amount = len(resources)
            # Calculate center, round and add 0.5 because expansion location will have (x.5, y.5)
            # coordinates because bases have size 5.
            center_x = int(sum(resource.position.x for resource in resources) / amount) + 0.5
            center_y = int(sum(resource.position.y for resource in resources) / amount) + 0.5
            possible_points = (Point2((offset[0] + center_x, offset[1] + center_y)) for offset in offsets)
            # Filter out points that are too near
            possible_points = (
                point
                for point in possible_points
                # Check if point can be built on
                if self.game_info.placement_grid[point.rounded] == 1
                # Check if all resources have enough space to point
                and all(
                    point.distance_to(resource) >= (7 if resource._proto.unit_type in geyser_ids else 6)
                    for resource in resources
                )
            )
            # Choose best fitting point
            result: Point2 = min(
                possible_points, key=lambda point: sum(point.distance_to(resource_) for resource_ in resources)
            )
            centers[result] = resources
            # Put all expansion locations in a list
            self._expansion_positions_list.append(result)
            # Maps all resource positions to the expansion position
            for resource in resources:
                self._resource_location_to_expansion_position_dict[resource.position] = result

    @final
    def _correct_zerg_supply(self) -> None:
        """The client incorrectly rounds zerg supply down instead of up (see
        https://github.com/Blizzard/s2client-proto/issues/123), so self.supply_used
        and friends return the wrong value when there are an odd number of zerglings
        and banelings. This function corrects the bad values."""
        # TODO: remove when Blizzard/sc2client-proto#123 gets fixed.
        half_supply_units = {
            UnitTypeId.ZERGLING,
            UnitTypeId.ZERGLINGBURROWED,
            UnitTypeId.BANELING,
            UnitTypeId.BANELINGBURROWED,
            UnitTypeId.BANELINGCOCOON,
        }
        correction = self.units(half_supply_units).amount % 2
        self.supply_used += correction
        self.supply_army += correction
        self.supply_left -= correction

    @final
    @property_cache_once_per_frame
    def _abilities_count_and_build_progress(self) -> tuple[Counter[AbilityId], dict[AbilityId, float]]:
        """Cache for the already_pending function, includes protoss units warping in,
        all units in production and all structures, and all morphs"""
        abilities_amount: Counter[AbilityId] = Counter()
        max_build_progress: dict[AbilityId, float] = {}
        unit: Unit
        for unit in self.units + self.structures:
            for order in unit.orders:
                abilities_amount[order.ability.exact_id] += 1
            if not unit.is_ready and (self.race != Race.Terran or not unit.is_structure):
                # If an SCV is constructing a building, already_pending would count this structure twice
                # (once from the SCV order, and once from "not structure.is_ready")
                if unit.type_id in CREATION_ABILITY_FIX:
                    if unit.type_id == UnitTypeId.ARCHON:
                        # Hotfix for archons in morph state
                        creation_ability = AbilityId.ARCHON_WARP_TARGET
                        abilities_amount[creation_ability] += 2
                    else:
                        # Hotfix for rich geysirs
                        creation_ability = CREATION_ABILITY_FIX[unit.type_id]
                        abilities_amount[creation_ability] += 1
                else:
                    creation_ability: AbilityId = self.game_data.units[unit.type_id.value].creation_ability.exact_id
                    abilities_amount[creation_ability] += 1
                max_build_progress[creation_ability] = max(
                    max_build_progress.get(creation_ability, 0), unit.build_progress
                )

        return abilities_amount, max_build_progress

    @final
    @property_cache_once_per_frame
    def _worker_orders(self) -> Counter[AbilityId]:
        """This function is used internally, do not use! It is to store all worker abilities."""
        abilities_amount: Counter[AbilityId] = Counter()
        structures_in_production: set[Point2 | int] = set()
        for structure in self.structures:
            if structure.type_id in TERRAN_STRUCTURES_REQUIRE_SCV:
                structures_in_production.add(structure.position)
                structures_in_production.add(structure.tag)
        for worker in self.workers:
            for order in worker.orders:
                # Skip if the SCV is constructing (not isinstance(order.target, int))
                # or resuming construction (isinstance(order.target, int))
                if order.target in structures_in_production:
                    continue
                abilities_amount[order.ability.exact_id] += 1
        return abilities_amount

    @final
    def do(
        self,
        action: UnitCommand,
        subtract_cost: bool = False,
        subtract_supply: bool = False,
        can_afford_check: bool = False,
        ignore_warning: bool = False,
    ) -> bool:
        """Adds a unit action to the 'self.actions' list which is then executed at the end of the frame.

        Training a unit::

            # Train an SCV from a random idle command center
            cc = self.townhalls.idle.random_or(None)
            # self.townhalls can be empty or there are no idle townhalls
            if cc and self.can_afford(UnitTypeId.SCV):
                cc.train(UnitTypeId.SCV)

        Building a building::

            # Building a barracks at the main ramp, requires 150 minerals and a depot
            worker = self.workers.random_or(None)
            barracks_placement_position = self.main_base_ramp.barracks_correct_placement
            if worker and self.can_afford(UnitTypeId.BARRACKS):
                worker.build(UnitTypeId.BARRACKS, barracks_placement_position)

        Moving a unit::

            # Move a random worker to the center of the map
            worker = self.workers.random_or(None)
            # worker can be None if all are dead
            if worker:
                worker.move(self.game_info.map_center)

        :param action:
        :param subtract_cost:
        :param subtract_supply:
        :param can_afford_check:
        """
        if not self.unit_command_uses_self_do and isinstance(action, bool):
            if not ignore_warning:
                warnings.warn(
                    "You have used self.do(). Please consider putting 'self.unit_command_uses_self_do = True' in your bot __init__() function or removing self.do().",
                    DeprecationWarning,
                    stacklevel=2,
                )
            return action

        assert isinstance(action, UnitCommand), (
            f"Given unit command is not a command, but instead of type {type(action)}"
        )
        if subtract_cost:
            cost: Cost = self.game_data.calculate_ability_cost(action.ability)
            if can_afford_check and not (self.minerals >= cost.minerals and self.vespene >= cost.vespene):
                # Dont do action if can't afford
                return False
            self.minerals -= cost.minerals
            self.vespene -= cost.vespene
        if subtract_supply and action.ability in abilityid_to_unittypeid:
            unit_type = abilityid_to_unittypeid[action.ability]
            required_supply = self.calculate_supply_cost(unit_type)
            # Overlord has -8
            if required_supply > 0:
                self.supply_used += required_supply
                self.supply_left -= required_supply
        self.actions.append(action)
        self.unit_tags_received_action.add(action.unit.tag)
        return True

    @final
    async def synchronous_do(self, action: UnitCommand):
        """
        Not recommended. Use self.do instead to reduce lag.
        This function is only useful for realtime=True in the first frame of the game to instantly produce a worker
        and split workers on the mineral patches.
        """
        assert isinstance(action, UnitCommand), (
            f"Given unit command is not a command, but instead of type {type(action)}"
        )
        if not self.can_afford(action.ability):
            logger.warning(f"Cannot afford action {action}")
            return ActionResult.Error
        r = await self.client.actions(action)
        if not r:  # success
            cost = self.game_data.calculate_ability_cost(action.ability)
            self.minerals -= cost.minerals
            self.vespene -= cost.vespene
            self.unit_tags_received_action.add(action.unit.tag)
        else:
            logger.error(f"Error: {r} (action: {action})")
        return r

    @final
    async def _do_actions(self, actions: list[UnitCommand], prevent_double: bool = True):
        """Used internally by main.py after each step

        :param actions:
        :param prevent_double:"""
        if not actions:
            return None
        if prevent_double:
            actions = list(filter(self.prevent_double_actions, actions))
        result = await self.client.actions(actions)
        return result

    @final
    @staticmethod
    def prevent_double_actions(action) -> bool:
        """
        :param action:
        """
        # Always add actions if queued
        if action.queue:
            return True
        if action.unit.orders:
            # action: UnitCommand
            # current_action: UnitOrder
            current_action = action.unit.orders[0]
            if action.ability not in {current_action.ability.id, current_action.ability.exact_id}:
                # Different action, return True
                return True
            with suppress(AttributeError):
                if current_action.target == action.target.tag:
                    # Same action, remove action if same target unit
                    return False
            with suppress(AttributeError):
                if action.target.x == current_action.target.x and action.target.y == current_action.target.y:
                    # Same action, remove action if same target position
                    return False
            return True
        return True

    @final
    def _prepare_start(
        self, client, player_id: int, game_info, game_data, realtime: bool = False, base_build: int = -1
    ) -> None:
        """
        Ran until game start to set game and player data.

        :param client:
        :param player_id:
        :param game_info:
        :param game_data:
        :param realtime:
        """
        self.client: Client = client
        self.player_id: int = player_id
        self.game_info: GameInfo = game_info
        self.game_data: GameData = game_data
        self.realtime: bool = realtime
        self.base_build: int = base_build

        # Get the player's race. As observer, get Race.NoRace=0
        self.race: Race = Race(self.game_info.player_races.get(self.player_id, 0))
        # Get the enemy's race only if we are not observer (replay) and the game has 2 players
        if self.player_id > 0 and len(self.game_info.player_races) == 2:
            self.enemy_race: Race = Race(self.game_info.player_races[3 - self.player_id])

        self._distances_override_functions(self.distance_calculation_method)

    @final
    def _prepare_first_step(self) -> None:
        """First step extra preparations. Must not be called before _prepare_step."""
        if self.townhalls:
            self.game_info.player_start_location = self.townhalls.first.position
            # Calculate and cache expansion locations forever inside 'self._cache_expansion_locations', this is done to prevent a bug when this is run and cached later in the game
            self._find_expansion_locations()
        self.game_info.map_ramps, self.game_info.vision_blockers = self.game_info._find_ramps_and_vision_blockers()
        self._time_before_step: float = time.perf_counter()

    @final
    def _prepare_step(self, state, proto_game_info) -> None:
        """
        :param state:
        :param proto_game_info:
        """
        # Set attributes from new state before on_step."""
        self.state: GameState = state  # See game_state.py
        # update pathing grid, which unfortunately is in GameInfo instead of GameState
        self.game_info.pathing_grid = PixelMap(proto_game_info.game_info.start_raw.pathing_grid, in_bits=True)
        # Required for events, needs to be before self.units are initialized so the old units are stored
        self._units_previous_map: dict[int, Unit] = {unit.tag: unit for unit in self.units}
        self._structures_previous_map: dict[int, Unit] = {structure.tag: structure for structure in self.structures}
        self._enemy_units_previous_map: dict[int, Unit] = {unit.tag: unit for unit in self.enemy_units}
        self._enemy_structures_previous_map: dict[int, Unit] = {
            structure.tag: structure for structure in self.enemy_structures
        }
        self._all_units_previous_map: dict[int, Unit] = {unit.tag: unit for unit in self.all_units}

        self._prepare_units()
        self.minerals: int = state.common.minerals
        self.vespene: int = state.common.vespene
        self.supply_army: int = state.common.food_army
        self.supply_workers: int = state.common.food_workers  # Doesn't include workers in production
        self.supply_cap: int = state.common.food_cap
        self.supply_used: int = state.common.food_used
        self.supply_left: int = self.supply_cap - self.supply_used

        if self.race == Race.Zerg:
            # Workaround Zerg supply rounding bug
            self._correct_zerg_supply()
        elif self.race == Race.Protoss:
            self.warp_gate_count: int = state.common.warp_gate_count

        self.idle_worker_count: int = state.common.idle_worker_count
        self.army_count: int = state.common.army_count
        self._time_before_step: float = time.perf_counter()

        if self.enemy_race == Race.Random and self.all_enemy_units:
            self.enemy_race = Race(self.all_enemy_units.first.race)

    @final
    def _prepare_units(self) -> None:
        # Set of enemy units detected by own sensor tower, as blips have less unit information than normal visible units
        self.blips: set[Blip] = set()
        self.all_units: Units = Units([], self)
        self.units: Units = Units([], self)
        self.workers: Units = Units([], self)
        self.larva: Units = Units([], self)
        self.structures: Units = Units([], self)
        self.townhalls: Units = Units([], self)
        self.gas_buildings: Units = Units([], self)
        self.all_own_units: Units = Units([], self)
        self.enemy_units: Units = Units([], self)
        self.enemy_structures: Units = Units([], self)
        self.all_enemy_units: Units = Units([], self)
        self.resources: Units = Units([], self)
        self.destructables: Units = Units([], self)
        self.watchtowers: Units = Units([], self)
        self.mineral_field: Units = Units([], self)
        self.vespene_geyser: Units = Units([], self)
        self.placeholders: Units = Units([], self)
        self.techlab_tags: set[int] = set()
        self.reactor_tags: set[int] = set()

        worker_types: set[UnitTypeId] = {UnitTypeId.DRONE, UnitTypeId.DRONEBURROWED, UnitTypeId.SCV, UnitTypeId.PROBE}

        index: int = 0
        for unit in self.state.observation_raw.units:
            if unit.is_blip:
                self.blips.add(Blip(unit))
            else:
                unit_type: int = unit.unit_type
                # Convert these units to effects: reaper grenade, parasitic bomb dummy, forcefield
                if unit_type in FakeEffectID:
                    self.state.effects.add(EffectData(unit, fake=True))
                    continue
                unit_obj = Unit(unit, self, distance_calculation_index=index, base_build=self.base_build)
                index += 1
                self.all_units.append(unit_obj)
                if unit.display_type == IS_PLACEHOLDER:
                    self.placeholders.append(unit_obj)
                    continue
                alliance = unit.alliance
                # Alliance.Neutral.value = 3
                if alliance == 3:
                    # XELNAGATOWER = 149
                    if unit_type == 149:
                        self.watchtowers.append(unit_obj)
                    # mineral field enums
                    elif unit_type in mineral_ids:
                        self.mineral_field.append(unit_obj)
                        self.resources.append(unit_obj)
                    # geyser enums
                    elif unit_type in geyser_ids:
                        self.vespene_geyser.append(unit_obj)
                        self.resources.append(unit_obj)
                    # all destructable rocks
                    else:
                        self.destructables.append(unit_obj)
                # Alliance.Self.value = 1
                elif alliance == 1:
                    self.all_own_units.append(unit_obj)
                    unit_id: UnitTypeId = unit_obj.type_id
                    if unit_obj.is_structure:
                        self.structures.append(unit_obj)
                        if unit_id in race_townhalls[self.race]:
                            self.townhalls.append(unit_obj)
                        elif unit_id in ALL_GAS or unit_obj.vespene_contents:
                            # TODO: remove "or unit_obj.vespene_contents" when a new linux client newer than version 4.10.0 is released
                            self.gas_buildings.append(unit_obj)
                        elif unit_id in {
                            UnitTypeId.TECHLAB,
                            UnitTypeId.BARRACKSTECHLAB,
                            UnitTypeId.FACTORYTECHLAB,
                            UnitTypeId.STARPORTTECHLAB,
                        }:
                            self.techlab_tags.add(unit_obj.tag)
                        elif unit_id in {
                            UnitTypeId.REACTOR,
                            UnitTypeId.BARRACKSREACTOR,
                            UnitTypeId.FACTORYREACTOR,
                            UnitTypeId.STARPORTREACTOR,
                        }:
                            self.reactor_tags.add(unit_obj.tag)
                    else:
                        self.units.append(unit_obj)
                        if unit_id in worker_types:
                            self.workers.append(unit_obj)
                        elif unit_id == UnitTypeId.LARVA:
                            self.larva.append(unit_obj)
                # Alliance.Enemy.value = 4
                elif alliance == 4:
                    self.all_enemy_units.append(unit_obj)
                    if unit_obj.is_structure:
                        self.enemy_structures.append(unit_obj)
                    else:
                        self.enemy_units.append(unit_obj)

        # Force distance calculation and caching on all units using scipy pdist or cdist
        if self.distance_calculation_method == 1:
            _ = self._pdist
        elif self.distance_calculation_method in {2, 3}:
            _ = self._cdist

    @final
    async def _after_step(self) -> int:
        """Executed by main.py after each on_step function."""
        # Keep track of the bot on_step duration
        self._time_after_step: float = time.perf_counter()
        step_duration = self._time_after_step - self._time_before_step
        self._min_step_time = min(step_duration, self._min_step_time)
        self._max_step_time = max(step_duration, self._max_step_time)
        self._last_step_step_time = step_duration
        self._total_time_in_on_step += step_duration
        self._total_steps_iterations += 1
        # Commit and clear bot actions
        if self.actions:
            await self._do_actions(self.actions)
            self.actions.clear()
        # Clear set of unit tags that were given an order this frame
        self.unit_tags_received_action.clear()
        # Commit debug queries
        await self.client._send_debug()

        return self.state.game_loop

    @final
    async def _advance_steps(self, steps: int) -> None:
        """Advances the game loop by amount of 'steps'. This function is meant to be used as a debugging and testing tool only.
        If you are using this, please be aware of the consequences, e.g. 'self.units' will be filled with completely new data."""
        await self._after_step()
        # Advance simulation by exactly "steps" frames
        await self.client.step(steps)
        state = await self.client.observation()
        gs = GameState(state.observation)
        proto_game_info = await self.client._execute(game_info=sc_pb.RequestGameInfo())
        self._prepare_step(gs, proto_game_info)
        await self.issue_events()

    @final
    async def issue_events(self) -> None:
        """This function will be automatically run from main.py and triggers the following functions:
        - on_unit_created
        - on_unit_destroyed
        - on_building_construction_started
        - on_building_construction_complete
        - on_upgrade_complete
        """
        await self._issue_unit_dead_events()
        await self._issue_unit_added_events()
        await self._issue_building_events()
        await self._issue_upgrade_events()
        await self._issue_vision_events()

    @final
    async def _issue_unit_added_events(self) -> None:
        for unit in self.units:
            if unit.tag not in self._units_previous_map and unit.tag not in self._unit_tags_seen_this_game:
                self._unit_tags_seen_this_game.add(unit.tag)
                self._units_created[unit.type_id] += 1
                await self.on_unit_created(unit)
            elif unit.tag in self._units_previous_map:
                previous_frame_unit: Unit = self._units_previous_map[unit.tag]
                # Check if a unit took damage this frame and then trigger event
                if unit.health < previous_frame_unit.health or unit.shield < previous_frame_unit.shield:
                    damage_amount = previous_frame_unit.health - unit.health + previous_frame_unit.shield - unit.shield
                    await self.on_unit_took_damage(unit, damage_amount)
                # Check if a unit type has changed
                if previous_frame_unit.type_id != unit.type_id:
                    await self.on_unit_type_changed(unit, previous_frame_unit.type_id)

    @final
    async def _issue_upgrade_events(self) -> None:
        difference = self.state.upgrades - self._previous_upgrades
        for upgrade_completed in difference:
            await self.on_upgrade_complete(upgrade_completed)
        self._previous_upgrades = self.state.upgrades

    @final
    async def _issue_building_events(self) -> None:
        for structure in self.structures:
            if structure.tag not in self._structures_previous_map:
                if structure.build_progress < 1:
                    await self.on_building_construction_started(structure)
                else:
                    # Include starting townhall
                    self._units_created[structure.type_id] += 1
                    await self.on_building_construction_complete(structure)
            elif structure.tag in self._structures_previous_map:
                # Check if a structure took damage this frame and then trigger event
                previous_frame_structure: Unit = self._structures_previous_map[structure.tag]
                if (
                    structure.health < previous_frame_structure.health
                    or structure.shield < previous_frame_structure.shield
                ):
                    damage_amount = (
                        previous_frame_structure.health
                        - structure.health
                        + previous_frame_structure.shield
                        - structure.shield
                    )
                    await self.on_unit_took_damage(structure, damage_amount)
                # Check if a structure changed its type
                if previous_frame_structure.type_id != structure.type_id:
                    await self.on_unit_type_changed(structure, previous_frame_structure.type_id)
                # Check if structure completed
                if structure.build_progress == 1 and previous_frame_structure.build_progress < 1:
                    self._units_created[structure.type_id] += 1
                    await self.on_building_construction_complete(structure)

    @final
    async def _issue_vision_events(self) -> None:
        # Call events for enemy unit entered vision
        for enemy_unit in self.enemy_units:
            if enemy_unit.tag not in self._enemy_units_previous_map:
                await self.on_enemy_unit_entered_vision(enemy_unit)
        for enemy_structure in self.enemy_structures:
            if enemy_structure.tag not in self._enemy_structures_previous_map:
                await self.on_enemy_unit_entered_vision(enemy_structure)

        # Call events for enemy unit left vision
        enemy_units_left_vision: set[int] = set(self._enemy_units_previous_map) - self.enemy_units.tags
        for enemy_unit_tag in enemy_units_left_vision:
            await self.on_enemy_unit_left_vision(enemy_unit_tag)
        enemy_structures_left_vision: set[int] = set(self._enemy_structures_previous_map) - self.enemy_structures.tags
        for enemy_structure_tag in enemy_structures_left_vision:
            await self.on_enemy_unit_left_vision(enemy_structure_tag)

    @final
    async def _issue_unit_dead_events(self) -> None:
        for unit_tag in self.state.dead_units & set(self._all_units_previous_map):
            await self.on_unit_destroyed(unit_tag)

    # DISTANCE CALCULATION

    @final
    @property
    def _units_count(self) -> int:
        return len(self.all_units)

    @final
    @property
    def _pdist(self) -> np.ndarray:
        """As property, so it will be recalculated each time it is called, or return from cache if it is called multiple times in teh same game_loop."""
        if self._generated_frame != self.state.game_loop:
            return self.calculate_distances()
        return self._cached_pdist

    @final
    @property
    def _cdist(self) -> np.ndarray:
        """As property, so it will be recalculated each time it is called, or return from cache if it is called multiple times in teh same game_loop."""
        if self._generated_frame != self.state.game_loop:
            return self.calculate_distances()
        return self._cached_cdist

    @final
    def _calculate_distances_method1(self) -> np.ndarray:
        self._generated_frame = self.state.game_loop
        # Converts tuple [(1, 2), (3, 4)] to flat list like [1, 2, 3, 4]
        flat_positions = (coord for unit in self.all_units for coord in unit.position_tuple)
        # Converts to numpy array, then converts the flat array back to shape (n, 2): [[1, 2], [3, 4]]
        positions_array: np.ndarray = np.fromiter(
            flat_positions,
            dtype=float,
            count=2 * self._units_count,
        ).reshape((self._units_count, 2))
        assert len(positions_array) == self._units_count
        # See performance benchmarks
        self._cached_pdist = pdist(positions_array, "sqeuclidean")

        return self._cached_pdist

    @final
    def _calculate_distances_method2(self) -> np.ndarray:
        self._generated_frame = self.state.game_loop
        # Converts tuple [(1, 2), (3, 4)] to flat list like [1, 2, 3, 4]
        flat_positions = (coord for unit in self.all_units for coord in unit.position_tuple)
        # Converts to numpy array, then converts the flat array back to shape (n, 2): [[1, 2], [3, 4]]
        positions_array: np.ndarray = np.fromiter(
            flat_positions,
            dtype=float,
            count=2 * self._units_count,
        ).reshape((self._units_count, 2))
        assert len(positions_array) == self._units_count
        # See performance benchmarks
        self._cached_cdist = cdist(positions_array, positions_array, "sqeuclidean")

        return self._cached_cdist

    @final
    def _calculate_distances_method3(self) -> np.ndarray:
        """Nearly same as above, but without asserts"""
        self._generated_frame = self.state.game_loop
        flat_positions = (coord for unit in self.all_units for coord in unit.position_tuple)
        positions_array: np.ndarray = np.fromiter(
            flat_positions,
            dtype=float,
            count=2 * self._units_count,
        ).reshape((-1, 2))
        # See performance benchmarks
        self._cached_cdist = cdist(positions_array, positions_array, "sqeuclidean")

        return self._cached_cdist

    # Helper functions

    @final
    def square_to_condensed(self, i, j) -> int:
        # Converts indices of a square matrix to condensed matrix
        # https://stackoverflow.com/a/36867493/10882657
        assert i != j, "No diagonal elements in condensed matrix! Diagonal elements are zero"
        if i < j:
            i, j = j, i
        return self._units_count * j - j * (j + 1) // 2 + i - 1 - j

    @final
    @staticmethod
    def convert_tuple_to_numpy_array(pos: tuple[float, float]) -> np.ndarray:
        """Converts a single position to a 2d numpy array with 1 row and 2 columns."""
        return np.fromiter(pos, dtype=float, count=2).reshape((1, 2))

    # Fast and simple calculation functions

    @final
    @staticmethod
    def distance_math_hypot(
        p1: tuple[float, float] | Point2,
        p2: tuple[float, float] | Point2,
    ) -> float:
        return math.hypot(p1[0] - p2[0], p1[1] - p2[1])

    @final
    @staticmethod
    def distance_math_hypot_squared(
        p1: tuple[float, float] | Point2,
        p2: tuple[float, float] | Point2,
    ) -> float:
        return pow(p1[0] - p2[0], 2) + pow(p1[1] - p2[1], 2)

    @final
    def _distance_squared_unit_to_unit_method0(self, unit1: Unit, unit2: Unit) -> float:
        return self.distance_math_hypot_squared(unit1.position_tuple, unit2.position_tuple)

    # Distance calculation using the pre-calculated matrix above

    @final
    def _distance_squared_unit_to_unit_method1(self, unit1: Unit, unit2: Unit) -> float:
        # If checked on units if they have the same tag, return distance 0 as these are not in the 1 dimensional pdist array - would result in an error otherwise
        if unit1.tag == unit2.tag:
            return 0
        # Calculate index, needs to be after pdist has been calculated and cached
        condensed_index = self.square_to_condensed(unit1.distance_calculation_index, unit2.distance_calculation_index)
        assert condensed_index < len(self._cached_pdist), (
            f"Condensed index is larger than amount of calculated distances: {condensed_index} < {len(self._cached_pdist)}, units that caused the assert error: {unit1} and {unit2}"
        )
        distance = self._pdist[condensed_index]
        return distance

    @final
    def _distance_squared_unit_to_unit_method2(self, unit1: Unit, unit2: Unit) -> float:
        # Calculate index, needs to be after cdist has been calculated and cached
        return self._cdist[unit1.distance_calculation_index, unit2.distance_calculation_index]

    # Distance calculation using the fastest distance calculation functions

    @final
    def _distance_pos_to_pos(
        self,
        pos1: tuple[float, float] | Point2,
        pos2: tuple[float, float] | Point2,
    ) -> float:
        return self.distance_math_hypot(pos1, pos2)

    @final
    def _distance_units_to_pos(
        self,
        units: Units,
        pos: tuple[float, float] | Point2,
    ) -> Generator[float, None, None]:
        """This function does not scale well, if len(units) > 100 it gets fairly slow"""
        return (self.distance_math_hypot(u.position_tuple, pos) for u in units)

    @final
    def _distance_unit_to_points(
        self,
        unit: Unit,
        points: Iterable[tuple[float, float]],
    ) -> Generator[float, None, None]:
        """This function does not scale well, if len(points) > 100 it gets fairly slow"""
        pos = unit.position_tuple
        return (self.distance_math_hypot(p, pos) for p in points)

    @final
    def _distances_override_functions(self, method: int = 0) -> None:
        """Overrides the internal distance calculation functions at game start in bot_ai.py self._prepare_start() function
        method 0: Use python's math.hypot
        The following methods calculate the distances between all units once:
        method 1: Use scipy's pdist condensed matrix (1d array)
        method 2: Use scipy's cidst square matrix (2d array)
        method 3: Use scipy's cidst square matrix (2d array) without asserts (careful: very weird error messages, but maybe slightly faster)"""
        assert 0 <= method <= 3, f"Selected method was: {method}"
        if method == 0:
            self._distance_squared_unit_to_unit = self._distance_squared_unit_to_unit_method0
        elif method == 1:
            self._distance_squared_unit_to_unit = self._distance_squared_unit_to_unit_method1
            self.calculate_distances = self._calculate_distances_method1
        elif method == 2:
            self._distance_squared_unit_to_unit = self._distance_squared_unit_to_unit_method2
            self.calculate_distances = self._calculate_distances_method2
        elif method == 3:
            self._distance_squared_unit_to_unit = self._distance_squared_unit_to_unit_method2
            self.calculate_distances = self._calculate_distances_method3
```

### File: `sc2/cache.py`

```python
from __future__ import annotations

from collections.abc import Callable, Hashable
from typing import TYPE_CHECKING, TypeVar

if TYPE_CHECKING:
    from sc2.bot_ai import BotAI

T = TypeVar("T")


class CacheDict(dict):
    def retrieve_and_set(self, key: Hashable, func: Callable[[], T]) -> T:
        """Either return the value at a certain key,
        or set the return value of a function to that key, then return that value."""
        if key not in self:
            self[key] = func()
        return self[key]


class property_cache_once_per_frame(property):  # noqa: N801
    """This decorator caches the return value for one game loop,
    then clears it if it is accessed in a different game loop.
    Only works on properties of the bot object, because it requires
    access to self.state.game_loop

    This decorator compared to the above runs a little faster, however you should only use this decorator if you are sure that you do not modify the mutable once it is calculated and cached.

    Copied and modified from https://tedboy.github.io/flask/_modules/werkzeug/utils.html#cached_property
    #"""

    def __init__(self, func: Callable[[BotAI], T], name=None) -> None:
        self.__name__ = name or func.__name__
        self.__frame__ = f"__frame__{self.__name__}"
        self.func = func

    def __set__(self, obj: BotAI, value: T) -> None:
        obj.cache[self.__name__] = value
        # pyre-ignore[16]
        obj.cache[self.__frame__] = obj.state.game_loop

    # pyre-fixme[34]
    def __get__(self, obj: BotAI, _type=None) -> T:
        value = obj.cache.get(self.__name__, None)
        # pyre-ignore[16]
        bot_frame = obj.state.game_loop
        if value is None or obj.cache[self.__frame__] < bot_frame:
            value = self.func(obj)
            obj.cache[self.__name__] = value
            obj.cache[self.__frame__] = bot_frame
        return value
```

### File: `sc2/client.py`

```python
# pyre-ignore-all-errors[6, 9, 16, 29, 58]
from __future__ import annotations

from collections.abc import Iterable
from pathlib import Path

from loguru import logger

# pyre-ignore[21]
from s2clientprotocol import debug_pb2 as debug_pb
from s2clientprotocol import query_pb2 as query_pb
from s2clientprotocol import raw_pb2 as raw_pb
from s2clientprotocol import sc2api_pb2 as sc_pb
from s2clientprotocol import spatial_pb2 as spatial_pb

from sc2.action import combine_actions
from sc2.data import ActionResult, ChatChannel, Race, Result, Status
from sc2.game_data import AbilityData, GameData
from sc2.game_info import GameInfo
from sc2.ids.ability_id import AbilityId
from sc2.ids.unit_typeid import UnitTypeId
from sc2.position import Point2, Point3
from sc2.protocol import ConnectionAlreadyClosedError, Protocol, ProtocolError
from sc2.renderer import Renderer
from sc2.unit import Unit
from sc2.units import Units


class Client(Protocol):
    def __init__(self, ws, save_replay_path: str = None) -> None:
        """
        :param ws:
        """
        super().__init__(ws)
        # How many frames will be waited between iterations before the next one is called
        self.game_step: int = 4
        self.save_replay_path: str | None = save_replay_path
        self._player_id = None
        self._game_result = None
        # Store a hash value of all the debug requests to prevent sending the same ones again if they haven't changed last frame
        self._debug_hash_tuple_last_iteration: tuple[int, int, int, int] = (0, 0, 0, 0)
        self._debug_draw_last_frame = False
        self._debug_texts = []
        self._debug_lines = []
        self._debug_boxes = []
        self._debug_spheres = []

        self._renderer = None
        self.raw_affects_selection = False

    @property
    def in_game(self) -> bool:
        return self._status in {Status.in_game, Status.in_replay}

    async def join_game(self, name=None, race=None, observed_player_id=None, portconfig=None, rgb_render_config=None):
        ifopts = sc_pb.InterfaceOptions(
            raw=True,
            score=True,
            show_cloaked=True,
            show_burrowed_shadows=True,
            raw_affects_selection=self.raw_affects_selection,
            raw_crop_to_playable_area=False,
            show_placeholders=True,
        )

        if rgb_render_config:
            assert isinstance(rgb_render_config, dict)
            assert "window_size" in rgb_render_config and "minimap_size" in rgb_render_config
            window_size = rgb_render_config["window_size"]
            minimap_size = rgb_render_config["minimap_size"]
            self._renderer = Renderer(self, window_size, minimap_size)
            map_width, map_height = window_size
            minimap_width, minimap_height = minimap_size

            ifopts.render.resolution.x = map_width
            ifopts.render.resolution.y = map_height
            ifopts.render.minimap_resolution.x = minimap_width
            ifopts.render.minimap_resolution.y = minimap_height

        if race is None:
            assert isinstance(observed_player_id, int), f"observed_player_id is of type {type(observed_player_id)}"
            # join as observer
            req = sc_pb.RequestJoinGame(observed_player_id=observed_player_id, options=ifopts)
        else:
            assert isinstance(race, Race)
            req = sc_pb.RequestJoinGame(race=race.value, options=ifopts)

        if portconfig:
            req.server_ports.game_port = portconfig.server[0]
            req.server_ports.base_port = portconfig.server[1]

            for ppc in portconfig.players:
                p = req.client_ports.add()
                p.game_port = ppc[0]
                p.base_port = ppc[1]

        if name is not None:
            assert isinstance(name, str), f"name is of type {type(name)}"
            req.player_name = name

        result = await self._execute(join_game=req)
        self._game_result = None
        self._player_id = result.join_game.player_id
        return result.join_game.player_id

    async def leave(self) -> None:
        """You can use 'await self.client.leave()' to surrender midst game."""
        is_resign = self._game_result is None

        if is_resign:
            # For all clients that can leave, result of leaving the game either
            # loss, or the client will ignore the result
            self._game_result = {self._player_id: Result.Defeat}

        try:
            if self.save_replay_path is not None:
                await self.save_replay(self.save_replay_path)
                self.save_replay_path = None
            await self._execute(leave_game=sc_pb.RequestLeaveGame())
        except (ProtocolError, ConnectionAlreadyClosedError):
            if is_resign:
                raise

    async def save_replay(self, path) -> None:
        logger.debug("Requesting replay from server")
        result = await self._execute(save_replay=sc_pb.RequestSaveReplay())
        with Path(path).open("wb") as f:
            f.write(result.save_replay.data)
        logger.info(f"Saved replay to {path}")

    async def observation(self, game_loop: int = None):
        if game_loop is not None:
            result = await self._execute(observation=sc_pb.RequestObservation(game_loop=game_loop))
        else:
            result = await self._execute(observation=sc_pb.RequestObservation())
        assert result.HasField("observation")

        if not self.in_game or result.observation.player_result:
            # Sometimes game ends one step before results are available
            if not result.observation.player_result:
                result = await self._execute(observation=sc_pb.RequestObservation())
                assert result.observation.player_result

            player_id_to_result = {}
            for pr in result.observation.player_result:
                player_id_to_result[pr.player_id] = Result(pr.result)
            self._game_result = player_id_to_result

        # if render_data is available, then RGB rendering was requested
        if self._renderer and result.observation.observation.HasField("render_data"):
            await self._renderer.render(result.observation)

        return result

    async def step(self, step_size: int = None):
        """EXPERIMENTAL: Change self._client.game_step during the step function to increase or decrease steps per second"""
        step_size = step_size or self.game_step
        return await self._execute(step=sc_pb.RequestStep(count=step_size))

    async def get_game_data(self) -> GameData:
        result = await self._execute(
            data=sc_pb.RequestData(ability_id=True, unit_type_id=True, upgrade_id=True, buff_id=True, effect_id=True)
        )
        return GameData(result.data)

    async def dump_data(
        self,
        ability_id: bool = True,
        unit_type_id: bool = True,
        upgrade_id: bool = True,
        buff_id: bool = True,
        effect_id: bool = True,
    ) -> None:
        """
        Dump the game data files
        choose what data to dump in the keywords
        this function writes to a text file
        call it one time in on_step with:
        await self._client.dump_data()
        """
        result = await self._execute(
            data=sc_pb.RequestData(
                ability_id=ability_id,
                unit_type_id=unit_type_id,
                upgrade_id=upgrade_id,
                buff_id=buff_id,
                effect_id=effect_id,
            )
        )
        with Path("data_dump.txt").open("a") as file:
            file.write(str(result.data))

    async def get_game_info(self) -> GameInfo:
        result = await self._execute(game_info=sc_pb.RequestGameInfo())
        return GameInfo(result.game_info)

    async def actions(self, actions, return_successes: bool = False):
        if not actions:
            return None
        if not isinstance(actions, list):
            actions = [actions]

        # On realtime=True, might get an error here: sc2.protocol.ProtocolError: ['Not in a game']
        try:
            res = await self._execute(
                action=sc_pb.RequestAction(actions=(sc_pb.Action(action_raw=a) for a in combine_actions(actions)))
            )
        except ProtocolError:
            return []
        if return_successes:
            return [ActionResult(r) for r in res.action.result]
        return [ActionResult(r) for r in res.action.result if ActionResult(r) != ActionResult.Success]

    async def query_pathing(self, start: Unit | Point2 | Point3, end: Point2 | Point3) -> int | float | None:
        """Caution: returns "None" when path not found
        Try to combine queries with the function below because the pathing query is generally slow.

        :param start:
        :param end:"""
        assert isinstance(start, (Point2, Unit))
        assert isinstance(end, Point2)
        if isinstance(start, Point2):
            path = [query_pb.RequestQueryPathing(start_pos=start.as_Point2D, end_pos=end.as_Point2D)]
        else:
            path = [query_pb.RequestQueryPathing(unit_tag=start.tag, end_pos=end.as_Point2D)]
        result = await self._execute(query=query_pb.RequestQuery(pathing=path))
        distance = float(result.query.pathing[0].distance)
        if distance <= 0.0:
            return None
        return distance

    async def query_pathings(self, zipped_list: list[list[Unit | Point2 | Point3]]) -> list[float]:
        """Usage: await self.query_pathings([[unit1, target2], [unit2, target2]])
        -> returns [distance1, distance2]
        Caution: returns 0 when path not found

        :param zipped_list:
        """
        assert zipped_list, "No zipped_list"
        assert isinstance(zipped_list, list), f"{type(zipped_list)}"
        assert isinstance(zipped_list[0], list), f"{type(zipped_list[0])}"
        assert len(zipped_list[0]) == 2, f"{len(zipped_list[0])}"
        assert isinstance(zipped_list[0][0], (Point2, Unit)), f"{type(zipped_list[0][0])}"
        assert isinstance(zipped_list[0][1], Point2), f"{type(zipped_list[0][1])}"
        if isinstance(zipped_list[0][0], Point2):
            path = (
                query_pb.RequestQueryPathing(start_pos=p1.as_Point2D, end_pos=p2.as_Point2D) for p1, p2 in zipped_list
            )
        else:
            path = (query_pb.RequestQueryPathing(unit_tag=p1.tag, end_pos=p2.as_Point2D) for p1, p2 in zipped_list)
        results = await self._execute(query=query_pb.RequestQuery(pathing=path))
        return [float(d.distance) for d in results.query.pathing]

    async def _query_building_placement_fast(
        self, ability: AbilityId, positions: list[Point2 | Point3], ignore_resources: bool = True
    ) -> list[bool]:
        """
        Returns a list of booleans. Return True for positions that are valid, False otherwise.

        :param ability:
        :param positions:
        :param ignore_resources:
        """
        result = await self._execute(
            query=query_pb.RequestQuery(
                placements=(
                    query_pb.RequestQueryBuildingPlacement(ability_id=ability.value, target_pos=position.as_Point2D)
                    for position in positions
                ),
                ignore_resource_requirements=ignore_resources,
            )
        )
        # Success enum value is 1, see https://github.com/Blizzard/s2client-proto/blob/9906df71d6909511907d8419b33acc1a3bd51ec0/s2clientprotocol/error.proto#L7
        return [p.result == 1 for p in result.query.placements]

    async def query_building_placement(
        self,
        ability: AbilityData,
        positions: list[Point2 | Point3],
        ignore_resources: bool = True,
        # pyre-fixme[11]
    ) -> list[ActionResult]:
        """This function might be deleted in favor of the function above (_query_building_placement_fast).

        :param ability:
        :param positions:
        :param ignore_resources:"""
        assert isinstance(ability, AbilityData)
        result = await self._execute(
            query=query_pb.RequestQuery(
                placements=(
                    query_pb.RequestQueryBuildingPlacement(ability_id=ability.id.value, target_pos=position.as_Point2D)
                    for position in positions
                ),
                ignore_resource_requirements=ignore_resources,
            )
        )
        # Unnecessary converting to ActionResult?
        return [ActionResult(p.result) for p in result.query.placements]

    async def query_available_abilities(
        self, units: list[Unit] | Units, ignore_resource_requirements: bool = False
    ) -> list[list[AbilityId]]:
        """Query abilities of multiple units"""
        input_was_a_list = True
        if not isinstance(units, list):
            """ Deprecated, accepting a single unit may be removed in the future, query a list of units instead """
            assert isinstance(units, Unit)
            units = [units]
            input_was_a_list = False
        assert units
        result = await self._execute(
            query=query_pb.RequestQuery(
                abilities=(query_pb.RequestQueryAvailableAbilities(unit_tag=unit.tag) for unit in units),
                ignore_resource_requirements=ignore_resource_requirements,
            )
        )
        """ Fix for bots that only query a single unit, may be removed soon """
        if not input_was_a_list:
            # pyre-fixme[7]
            return [[AbilityId(a.ability_id) for a in b.abilities] for b in result.query.abilities][0]
        return [[AbilityId(a.ability_id) for a in b.abilities] for b in result.query.abilities]

    async def query_available_abilities_with_tag(
        self, units: list[Unit] | Units, ignore_resource_requirements: bool = False
    ) -> dict[int, set[AbilityId]]:
        """Query abilities of multiple units"""

        result = await self._execute(
            query=query_pb.RequestQuery(
                abilities=(query_pb.RequestQueryAvailableAbilities(unit_tag=unit.tag) for unit in units),
                ignore_resource_requirements=ignore_resource_requirements,
            )
        )
        return {b.unit_tag: {AbilityId(a.ability_id) for a in b.abilities} for b in result.query.abilities}

    async def chat_send(self, message: str, team_only: bool) -> None:
        """Writes a message to the chat"""
        ch = ChatChannel.Team if team_only else ChatChannel.Broadcast
        await self._execute(
            action=sc_pb.RequestAction(
                actions=[sc_pb.Action(action_chat=sc_pb.ActionChat(channel=ch.value, message=message))]
            )
        )

    async def toggle_autocast(self, units: list[Unit] | Units, ability: AbilityId) -> None:
        """Toggle autocast of all specified units

        :param units:
        :param ability:"""
        assert units
        assert isinstance(units, list)
        assert all(isinstance(u, Unit) for u in units)
        assert isinstance(ability, AbilityId)

        await self._execute(
            action=sc_pb.RequestAction(
                actions=[
                    sc_pb.Action(
                        action_raw=raw_pb.ActionRaw(
                            toggle_autocast=raw_pb.ActionRawToggleAutocast(
                                ability_id=ability.value, unit_tags=(u.tag for u in units)
                            )
                        )
                    )
                ]
            )
        )

    async def debug_create_unit(self, unit_spawn_commands: list[list[UnitTypeId | int | Point2 | Point3]]) -> None:
        """Usage example (will spawn 5 marines in the center of the map for player ID 1):
        await self._client.debug_create_unit([[UnitTypeId.MARINE, 5, self._game_info.map_center, 1]])

        :param unit_spawn_commands:"""
        assert isinstance(unit_spawn_commands, list)
        assert unit_spawn_commands
        assert isinstance(unit_spawn_commands[0], list)
        assert len(unit_spawn_commands[0]) == 4
        assert isinstance(unit_spawn_commands[0][0], UnitTypeId)
        assert unit_spawn_commands[0][1] > 0  # careful, in realtime=True this function may create more units
        assert isinstance(unit_spawn_commands[0][2], (Point2, Point3))
        assert 1 <= unit_spawn_commands[0][3] <= 2

        await self._execute(
            debug=sc_pb.RequestDebug(
                debug=(
                    debug_pb.DebugCommand(
                        create_unit=debug_pb.DebugCreateUnit(
                            unit_type=unit_type.value,
                            owner=owner_id,
                            pos=position.as_Point2D,
                            quantity=amount_of_units,
                        )
                    )
                    for unit_type, amount_of_units, position, owner_id in unit_spawn_commands
                )
            )
        )

    async def debug_kill_unit(self, unit_tags: Unit | Units | list[int] | set[int]) -> None:
        """
        :param unit_tags:
        """
        if isinstance(unit_tags, Units):
            unit_tags = unit_tags.tags
        if isinstance(unit_tags, Unit):
            unit_tags = [unit_tags.tag]
        assert unit_tags

        await self._execute(
            debug=sc_pb.RequestDebug(debug=[debug_pb.DebugCommand(kill_unit=debug_pb.DebugKillUnit(tag=unit_tags))])
        )

    async def move_camera(self, position: Unit | Units | Point2 | Point3) -> None:
        """Moves camera to the target position

        :param position:"""
        assert isinstance(position, (Unit, Units, Point2, Point3))
        if isinstance(position, Units):
            position = position.center
        if isinstance(position, Unit):
            position = position.position
        await self._execute(
            action=sc_pb.RequestAction(
                actions=[
                    sc_pb.Action(
                        action_raw=raw_pb.ActionRaw(
                            camera_move=raw_pb.ActionRawCameraMove(center_world_space=position.to3.as_Point)
                        )
                    )
                ]
            )
        )

    async def obs_move_camera(self, position: Unit | Units | Point2 | Point3, distance: float = 0) -> None:
        """Moves observer camera to the target position. Only works when observing (e.g. watching the replay).

        :param position:"""
        assert isinstance(position, (Unit, Units, Point2, Point3))
        if isinstance(position, Units):
            position = position.center
        if isinstance(position, Unit):
            position = position.position
        await self._execute(
            obs_action=sc_pb.RequestObserverAction(
                actions=[
                    sc_pb.ObserverAction(
                        camera_move=sc_pb.ActionObserverCameraMove(world_pos=position.as_Point2D, distance=distance)
                    )
                ]
            )
        )

    async def move_camera_spatial(self, position: Point2 | Point3) -> None:
        """Moves camera to the target position using the spatial aciton interface

        :param position:"""
        assert isinstance(position, (Point2, Point3))
        action = sc_pb.Action(
            action_render=spatial_pb.ActionSpatial(
                camera_move=spatial_pb.ActionSpatialCameraMove(center_minimap=position.as_PointI)
            )
        )
        await self._execute(action=sc_pb.RequestAction(actions=[action]))

    def debug_text_simple(self, text: str) -> None:
        """Draws a text in the top left corner of the screen (up to a max of 6 messages fit there)."""
        self._debug_texts.append(DrawItemScreenText(text=text, color=None, start_point=Point2((0, 0)), font_size=8))

    def debug_text_screen(
        self,
        text: str,
        pos: Point2 | Point3 | tuple | list,
        color: tuple | list | Point3 = None,
        size: int = 8,
    ) -> None:
        """
        Draws a text on the screen (monitor / game window) with coordinates 0 <= x, y <= 1.

        :param text:
        :param pos:
        :param color:
        :param size:
        """
        assert len(pos) >= 2
        assert 0 <= pos[0] <= 1
        assert 0 <= pos[1] <= 1
        pos = Point2((pos[0], pos[1]))
        self._debug_texts.append(DrawItemScreenText(text=text, color=color, start_point=pos, font_size=size))

    def debug_text_2d(
        self,
        text: str,
        pos: Point2 | Point3 | tuple | list,
        color: tuple | list | Point3 = None,
        size: int = 8,
    ):
        return self.debug_text_screen(text, pos, color, size)

    def debug_text_world(
        self, text: str, pos: Unit | Point3, color: tuple | list | Point3 = None, size: int = 8
    ) -> None:
        """
        Draws a text at Point3 position in the game world.
        To grab a unit's 3d position, use unit.position3d
        Usually the Z value of a Point3 is between 8 and 14 (except for flying units). Use self.get_terrain_z_height() from bot_ai.py to get the Z value (height) of the terrain at a 2D position.

        :param text:
        :param color:
        :param size:
        """
        if isinstance(pos, Unit):
            pos = pos.position3d
        assert isinstance(pos, Point3)
        self._debug_texts.append(DrawItemWorldText(text=text, color=color, start_point=pos, font_size=size))

    def debug_text_3d(self, text: str, pos: Unit | Point3, color: tuple | list | Point3 = None, size: int = 8):
        return self.debug_text_world(text, pos, color, size)

    def debug_line_out(self, p0: Unit | Point3, p1: Unit | Point3, color: tuple | list | Point3 = None) -> None:
        """
        Draws a line from p0 to p1.

        :param p0:
        :param p1:
        :param color:
        """
        if isinstance(p0, Unit):
            p0 = p0.position3d
        assert isinstance(p0, Point3)
        if isinstance(p1, Unit):
            p1 = p1.position3d
        assert isinstance(p1, Point3)
        self._debug_lines.append(DrawItemLine(color=color, start_point=p0, end_point=p1))

    def debug_box_out(
        self,
        p_min: Unit | Point3,
        p_max: Unit | Point3,
        color: tuple | list | Point3 = None,
    ) -> None:
        """
        Draws a box with p_min and p_max as corners of the box.

        :param p_min:
        :param p_max:
        :param color:
        """
        if isinstance(p_min, Unit):
            p_min = p_min.position3d
        assert isinstance(p_min, Point3)
        if isinstance(p_max, Unit):
            p_max = p_max.position3d
        assert isinstance(p_max, Point3)
        self._debug_boxes.append(DrawItemBox(start_point=p_min, end_point=p_max, color=color))

    def debug_box2_out(
        self,
        pos: Unit | Point3,
        half_vertex_length: float = 0.25,
        color: tuple | list | Point3 = None,
    ) -> None:
        """
        Draws a box center at a position 'pos', with box side lengths (vertices) of two times 'half_vertex_length'.

        :param pos:
        :param half_vertex_length:
        :param color:
        """
        if isinstance(pos, Unit):
            pos = pos.position3d
        assert isinstance(pos, Point3)
        p0 = pos + Point3((-half_vertex_length, -half_vertex_length, -half_vertex_length))
        p1 = pos + Point3((half_vertex_length, half_vertex_length, half_vertex_length))
        self._debug_boxes.append(DrawItemBox(start_point=p0, end_point=p1, color=color))

    def debug_sphere_out(self, p: Unit | Point3, r: float, color: tuple | list | Point3 = None) -> None:
        """
        Draws a sphere at point p with radius r.

        :param p:
        :param r:
        :param color:
        """
        if isinstance(p, Unit):
            p = p.position3d
        assert isinstance(p, Point3)
        self._debug_spheres.append(DrawItemSphere(start_point=p, radius=r, color=color))

    async def _send_debug(self) -> None:
        """Sends the debug draw execution. This is run by main.py now automatically, if there is any items in the list. You do not need to run this manually any longer.
        Check examples/terran/ramp_wall.py for example drawing. Each draw request needs to be sent again in every single on_step iteration.
        """
        debug_hash = (
            sum(hash(item) for item in self._debug_texts),
            sum(hash(item) for item in self._debug_lines),
            sum(hash(item) for item in self._debug_boxes),
            sum(hash(item) for item in self._debug_spheres),
        )
        if debug_hash != (0, 0, 0, 0):
            if debug_hash != self._debug_hash_tuple_last_iteration:
                # Something has changed, either more or less is to be drawn, or a position of a drawing changed (e.g. when drawing on a moving unit)
                self._debug_hash_tuple_last_iteration = debug_hash
                try:
                    await self._execute(
                        debug=sc_pb.RequestDebug(
                            debug=[
                                debug_pb.DebugCommand(
                                    draw=debug_pb.DebugDraw(
                                        text=[text.to_proto() for text in self._debug_texts]
                                        if self._debug_texts
                                        else None,
                                        lines=[line.to_proto() for line in self._debug_lines]
                                        if self._debug_lines
                                        else None,
                                        boxes=[box.to_proto() for box in self._debug_boxes]
                                        if self._debug_boxes
                                        else None,
                                        spheres=[sphere.to_proto() for sphere in self._debug_spheres]
                                        if self._debug_spheres
                                        else None,
                                    )
                                )
                            ]
                        )
                    )
                except ProtocolError:
                    return
            self._debug_draw_last_frame = True
            self._debug_texts.clear()
            self._debug_lines.clear()
            self._debug_boxes.clear()
            self._debug_spheres.clear()
        elif self._debug_draw_last_frame:
            # Clear drawing if we drew last frame but nothing to draw this frame
            self._debug_hash_tuple_last_iteration = (0, 0, 0, 0)
            await self._execute(
                debug=sc_pb.RequestDebug(
                    debug=[
                        debug_pb.DebugCommand(draw=debug_pb.DebugDraw(text=None, lines=None, boxes=None, spheres=None))
                    ]
                )
            )
            self._debug_draw_last_frame = False

    async def debug_leave(self) -> None:
        await self._execute(debug=sc_pb.RequestDebug(debug=[debug_pb.DebugCommand(end_game=debug_pb.DebugEndGame())]))

    async def debug_set_unit_value(
        self, unit_tags: Iterable[int] | Units | Unit, unit_value: int, value: float
    ) -> None:
        """Sets a "unit value" (Energy, Life or Shields) of the given units to the given value.
        Can't set the life of a unit to 0, use "debug_kill_unit" for that. Also can't set the life above the unit's maximum.
        The following example sets the health of all your workers to 1:
        await self.debug_set_unit_value(self.workers, 2, value=1)"""
        if isinstance(unit_tags, Units):
            unit_tags = unit_tags.tags
        if isinstance(unit_tags, Unit):
            unit_tags = [unit_tags.tag]
        assert hasattr(unit_tags, "__iter__"), (
            f"unit_tags argument needs to be an iterable (list, dict, set, Units), given argument is {type(unit_tags).__name__}"
        )
        assert 1 <= unit_value <= 3, (
            f"unit_value needs to be between 1 and 3 (1 for energy, 2 for life, 3 for shields), given argument is {unit_value}"
        )
        assert all(tag > 0 for tag in unit_tags), f"Unit tags have invalid value: {unit_tags}"
        assert isinstance(value, (int, float)), "Value needs to be of type int or float"
        assert value >= 0, "Value can't be negative"
        await self._execute(
            debug=sc_pb.RequestDebug(
                debug=(
                    debug_pb.DebugCommand(
                        unit_value=debug_pb.DebugSetUnitValue(
                            unit_value=unit_value, value=float(value), unit_tag=unit_tag
                        )
                    )
                    for unit_tag in unit_tags
                )
            )
        )

    async def debug_hang(self, delay_in_seconds: float) -> None:
        """Freezes the SC2 client. Not recommended to be used."""
        delay_in_ms = int(round(delay_in_seconds * 1000))
        await self._execute(
            debug=sc_pb.RequestDebug(
                debug=[debug_pb.DebugCommand(test_process=debug_pb.DebugTestProcess(test=1, delay_ms=delay_in_ms))]
            )
        )

    async def debug_show_map(self) -> None:
        """Reveals the whole map for the bot. Using it a second time disables it again."""
        await self._execute(debug=sc_pb.RequestDebug(debug=[debug_pb.DebugCommand(game_state=1)]))

    async def debug_control_enemy(self) -> None:
        """Allows control over enemy units and structures similar to team games control - does not allow the bot to spend the opponent's ressources. Using it a second time disables it again."""
        await self._execute(debug=sc_pb.RequestDebug(debug=[debug_pb.DebugCommand(game_state=2)]))

    async def debug_food(self) -> None:
        """Should disable food usage (does not seem to work?). Using it a second time disables it again."""
        await self._execute(debug=sc_pb.RequestDebug(debug=[debug_pb.DebugCommand(game_state=3)]))

    async def debug_free(self) -> None:
        """Units, structures and upgrades are free of mineral and gas cost. Using it a second time disables it again."""
        await self._execute(debug=sc_pb.RequestDebug(debug=[debug_pb.DebugCommand(game_state=4)]))

    async def debug_all_resources(self) -> None:
        """Gives 5000 minerals and 5000 vespene to the bot."""
        await self._execute(debug=sc_pb.RequestDebug(debug=[debug_pb.DebugCommand(game_state=5)]))

    async def debug_god(self) -> None:
        """Your units and structures no longer take any damage. Using it a second time disables it again."""
        await self._execute(debug=sc_pb.RequestDebug(debug=[debug_pb.DebugCommand(game_state=6)]))

    async def debug_minerals(self) -> None:
        """Gives 5000 minerals to the bot."""
        await self._execute(debug=sc_pb.RequestDebug(debug=[debug_pb.DebugCommand(game_state=7)]))

    async def debug_gas(self) -> None:
        """Gives 5000 vespene to the bot. This does not seem to be working."""
        await self._execute(debug=sc_pb.RequestDebug(debug=[debug_pb.DebugCommand(game_state=8)]))

    async def debug_cooldown(self) -> None:
        """Disables cooldowns of unit abilities for the bot. Using it a second time disables it again."""
        await self._execute(debug=sc_pb.RequestDebug(debug=[debug_pb.DebugCommand(game_state=9)]))

    async def debug_tech_tree(self) -> None:
        """Removes all tech requirements (e.g. can build a factory without having a barracks). Using it a second time disables it again."""
        await self._execute(debug=sc_pb.RequestDebug(debug=[debug_pb.DebugCommand(game_state=10)]))

    async def debug_upgrade(self) -> None:
        """Researches all currently available upgrades. E.g. using it once unlocks combat shield, stimpack and 1-1. Using it a second time unlocks 2-2 and all other upgrades stay researched."""
        await self._execute(debug=sc_pb.RequestDebug(debug=[debug_pb.DebugCommand(game_state=11)]))

    async def debug_fast_build(self) -> None:
        """Sets the build time of units and structures and upgrades to zero. Using it a second time disables it again."""
        await self._execute(debug=sc_pb.RequestDebug(debug=[debug_pb.DebugCommand(game_state=12)]))

    async def quick_save(self) -> None:
        """Saves the current game state to an in-memory bookmark.
        See: https://github.com/Blizzard/s2client-proto/blob/eeaf5efaea2259d7b70247211dff98da0a2685a2/s2clientprotocol/sc2api.proto#L93"""
        await self._execute(quick_save=sc_pb.RequestQuickSave())

    async def quick_load(self) -> None:
        """Loads the game state from the previously stored in-memory bookmark.
        Caution:
            - The SC2 Client will crash if the game wasn't quicksaved
            - The bot step iteration counter will not reset
            - self.state.game_loop will be set to zero after the quickload, and self.time is dependant on it"""
        await self._execute(quick_load=sc_pb.RequestQuickLoad())


class DrawItem:
    @staticmethod
    def to_debug_color(color: tuple | Point3):
        """Helper function for color conversion"""
        if color is None:
            return debug_pb.Color(r=255, g=255, b=255)
        # Need to check if not of type Point3 because Point3 inherits from tuple
        if isinstance(color, (tuple, list)) and not isinstance(color, Point3) and len(color) == 3:
            return debug_pb.Color(r=color[0], g=color[1], b=color[2])
        # In case color is of type Point3
        r = getattr(color, "r", getattr(color, "x", 255))
        g = getattr(color, "g", getattr(color, "y", 255))
        b = getattr(color, "b", getattr(color, "z", 255))
        # pyre-ignore[20]
        if max(r, g, b) <= 1:
            r *= 255
            g *= 255
            b *= 255

        return debug_pb.Color(r=int(r), g=int(g), b=int(b))


class DrawItemScreenText(DrawItem):
    def __init__(self, start_point: Point2 = None, color: Point3 = None, text: str = "", font_size: int = 8) -> None:
        self._start_point: Point2 = start_point
        self._color: Point3 = color
        self._text: str = text
        self._font_size: int = font_size

    def to_proto(self):
        return debug_pb.DebugText(
            color=self.to_debug_color(self._color),
            text=self._text,
            virtual_pos=self._start_point.to3.as_Point,
            world_pos=None,
            size=self._font_size,
        )

    def __hash__(self) -> int:
        return hash((self._start_point, self._color, self._text, self._font_size))


class DrawItemWorldText(DrawItem):
    def __init__(self, start_point: Point3 = None, color: Point3 = None, text: str = "", font_size: int = 8) -> None:
        self._start_point: Point3 = start_point
        self._color: Point3 = color
        self._text: str = text
        self._font_size: int = font_size

    def to_proto(self):
        return debug_pb.DebugText(
            color=self.to_debug_color(self._color),
            text=self._text,
            virtual_pos=None,
            world_pos=self._start_point.as_Point,
            size=self._font_size,
        )

    def __hash__(self) -> int:
        return hash((self._start_point, self._text, self._font_size, self._color))


class DrawItemLine(DrawItem):
    def __init__(self, start_point: Point3 = None, end_point: Point3 = None, color: Point3 = None) -> None:
        self._start_point: Point3 = start_point
        self._end_point: Point3 = end_point
        self._color: Point3 = color

    def to_proto(self):
        return debug_pb.DebugLine(
            line=debug_pb.Line(p0=self._start_point.as_Point, p1=self._end_point.as_Point),
            color=self.to_debug_color(self._color),
        )

    def __hash__(self) -> int:
        return hash((self._start_point, self._end_point, self._color))


class DrawItemBox(DrawItem):
    def __init__(self, start_point: Point3 = None, end_point: Point3 = None, color: Point3 = None) -> None:
        self._start_point: Point3 = start_point
        self._end_point: Point3 = end_point
        self._color: Point3 = color

    def to_proto(self):
        return debug_pb.DebugBox(
            min=self._start_point.as_Point,
            max=self._end_point.as_Point,
            color=self.to_debug_color(self._color),
        )

    def __hash__(self) -> int:
        return hash((self._start_point, self._end_point, self._color))


class DrawItemSphere(DrawItem):
    def __init__(self, start_point: Point3 = None, radius: float = None, color: Point3 = None) -> None:
        self._start_point: Point3 = start_point
        self._radius: float = radius
        self._color: Point3 = color

    def to_proto(self):
        return debug_pb.DebugSphere(
            p=self._start_point.as_Point, r=self._radius, color=self.to_debug_color(self._color)
        )

    def __hash__(self) -> int:
        return hash((self._start_point, self._radius, self._color))
```

### File: `sc2/constants.py`

```python
# pyre-ignore-all-errors[16]
from __future__ import annotations

from collections import defaultdict
from typing import Any

from sc2.data import Alliance, Attribute, CloakState, DisplayType, TargetType
from sc2.ids.ability_id import AbilityId
from sc2.ids.buff_id import BuffId
from sc2.ids.unit_typeid import UnitTypeId
from sc2.ids.upgrade_id import UpgradeId

mineral_ids: set[int] = {
    UnitTypeId.RICHMINERALFIELD.value,
    UnitTypeId.RICHMINERALFIELD750.value,
    UnitTypeId.MINERALFIELD.value,
    UnitTypeId.MINERALFIELD450.value,
    UnitTypeId.MINERALFIELD750.value,
    UnitTypeId.LABMINERALFIELD.value,
    UnitTypeId.LABMINERALFIELD750.value,
    UnitTypeId.PURIFIERRICHMINERALFIELD.value,
    UnitTypeId.PURIFIERRICHMINERALFIELD750.value,
    UnitTypeId.PURIFIERMINERALFIELD.value,
    UnitTypeId.PURIFIERMINERALFIELD750.value,
    UnitTypeId.BATTLESTATIONMINERALFIELD.value,
    UnitTypeId.BATTLESTATIONMINERALFIELD750.value,
    UnitTypeId.MINERALFIELDOPAQUE.value,
    UnitTypeId.MINERALFIELDOPAQUE900.value,
}
geyser_ids: set[int] = {
    UnitTypeId.VESPENEGEYSER.value,
    UnitTypeId.SPACEPLATFORMGEYSER.value,
    UnitTypeId.RICHVESPENEGEYSER.value,
    UnitTypeId.PROTOSSVESPENEGEYSER.value,
    UnitTypeId.PURIFIERVESPENEGEYSER.value,
    UnitTypeId.SHAKURASVESPENEGEYSER.value,
}
transforming: dict[UnitTypeId, AbilityId] = {
    # Terran structures
    UnitTypeId.BARRACKS: AbilityId.LAND_BARRACKS,
    UnitTypeId.BARRACKSFLYING: AbilityId.LAND_BARRACKS,
    UnitTypeId.COMMANDCENTER: AbilityId.LAND_COMMANDCENTER,
    UnitTypeId.COMMANDCENTERFLYING: AbilityId.LAND_COMMANDCENTER,
    UnitTypeId.ORBITALCOMMAND: AbilityId.LAND_ORBITALCOMMAND,
    UnitTypeId.ORBITALCOMMANDFLYING: AbilityId.LAND_ORBITALCOMMAND,
    UnitTypeId.FACTORY: AbilityId.LAND_FACTORY,
    UnitTypeId.FACTORYFLYING: AbilityId.LAND_FACTORY,
    UnitTypeId.STARPORT: AbilityId.LAND_STARPORT,
    UnitTypeId.STARPORTFLYING: AbilityId.LAND_STARPORT,
    UnitTypeId.SUPPLYDEPOT: AbilityId.MORPH_SUPPLYDEPOT_RAISE,
    UnitTypeId.SUPPLYDEPOTLOWERED: AbilityId.MORPH_SUPPLYDEPOT_LOWER,
    # Terran units
    UnitTypeId.HELLION: AbilityId.MORPH_HELLION,
    UnitTypeId.HELLIONTANK: AbilityId.MORPH_HELLBAT,
    UnitTypeId.LIBERATOR: AbilityId.MORPH_LIBERATORAAMODE,
    UnitTypeId.LIBERATORAG: AbilityId.MORPH_LIBERATORAGMODE,
    UnitTypeId.SIEGETANK: AbilityId.UNSIEGE_UNSIEGE,
    UnitTypeId.SIEGETANKSIEGED: AbilityId.SIEGEMODE_SIEGEMODE,
    UnitTypeId.THOR: AbilityId.MORPH_THOREXPLOSIVEMODE,
    UnitTypeId.THORAP: AbilityId.MORPH_THORHIGHIMPACTMODE,
    UnitTypeId.VIKINGASSAULT: AbilityId.MORPH_VIKINGASSAULTMODE,
    UnitTypeId.VIKINGFIGHTER: AbilityId.MORPH_VIKINGFIGHTERMODE,
    UnitTypeId.WIDOWMINE: AbilityId.BURROWUP,
    UnitTypeId.WIDOWMINEBURROWED: AbilityId.BURROWDOWN,
    # Protoss structures
    UnitTypeId.GATEWAY: AbilityId.MORPH_GATEWAY,
    UnitTypeId.WARPGATE: AbilityId.MORPH_WARPGATE,
    # Protoss units
    UnitTypeId.OBSERVER: AbilityId.MORPH_OBSERVERMODE,
    UnitTypeId.OBSERVERSIEGEMODE: AbilityId.MORPH_SURVEILLANCEMODE,
    UnitTypeId.WARPPRISM: AbilityId.MORPH_WARPPRISMTRANSPORTMODE,
    UnitTypeId.WARPPRISMPHASING: AbilityId.MORPH_WARPPRISMPHASINGMODE,
    # Zerg structures
    UnitTypeId.SPINECRAWLER: AbilityId.SPINECRAWLERROOT_SPINECRAWLERROOT,
    UnitTypeId.SPINECRAWLERUPROOTED: AbilityId.SPINECRAWLERUPROOT_SPINECRAWLERUPROOT,
    UnitTypeId.SPORECRAWLER: AbilityId.SPORECRAWLERROOT_SPORECRAWLERROOT,
    UnitTypeId.SPORECRAWLERUPROOTED: AbilityId.SPORECRAWLERUPROOT_SPORECRAWLERUPROOT,
    # Zerg units
    UnitTypeId.BANELING: AbilityId.BURROWUP_BANELING,
    UnitTypeId.BANELINGBURROWED: AbilityId.BURROWDOWN_BANELING,
    UnitTypeId.DRONE: AbilityId.BURROWUP_DRONE,
    UnitTypeId.DRONEBURROWED: AbilityId.BURROWDOWN_DRONE,
    UnitTypeId.HYDRALISK: AbilityId.BURROWUP_HYDRALISK,
    UnitTypeId.HYDRALISKBURROWED: AbilityId.BURROWDOWN_HYDRALISK,
    UnitTypeId.INFESTOR: AbilityId.BURROWUP_INFESTOR,
    UnitTypeId.INFESTORBURROWED: AbilityId.BURROWDOWN_INFESTOR,
    UnitTypeId.INFESTORTERRAN: AbilityId.BURROWUP_INFESTORTERRAN,
    UnitTypeId.INFESTORTERRANBURROWED: AbilityId.BURROWDOWN_INFESTORTERRAN,
    UnitTypeId.LURKERMP: AbilityId.BURROWUP_LURKER,
    UnitTypeId.LURKERMPBURROWED: AbilityId.BURROWDOWN_LURKER,
    UnitTypeId.OVERSEER: AbilityId.MORPH_OVERSEERMODE,
    UnitTypeId.OVERSEERSIEGEMODE: AbilityId.MORPH_OVERSIGHTMODE,
    UnitTypeId.QUEEN: AbilityId.BURROWUP_QUEEN,
    UnitTypeId.QUEENBURROWED: AbilityId.BURROWDOWN_QUEEN,
    UnitTypeId.ROACH: AbilityId.BURROWUP_ROACH,
    UnitTypeId.ROACHBURROWED: AbilityId.BURROWDOWN_ROACH,
    UnitTypeId.SWARMHOSTBURROWEDMP: AbilityId.BURROWDOWN_SWARMHOST,
    UnitTypeId.SWARMHOSTMP: AbilityId.BURROWUP_SWARMHOST,
    UnitTypeId.ULTRALISK: AbilityId.BURROWUP_ULTRALISK,
    UnitTypeId.ULTRALISKBURROWED: AbilityId.BURROWDOWN_ULTRALISK,
    UnitTypeId.ZERGLING: AbilityId.BURROWUP_ZERGLING,
    UnitTypeId.ZERGLINGBURROWED: AbilityId.BURROWDOWN_ZERGLING,
}
# For now only contains units that cost supply
abilityid_to_unittypeid: dict[AbilityId, UnitTypeId] = {
    # Protoss
    AbilityId.NEXUSTRAIN_PROBE: UnitTypeId.PROBE,
    AbilityId.GATEWAYTRAIN_ZEALOT: UnitTypeId.ZEALOT,
    AbilityId.WARPGATETRAIN_ZEALOT: UnitTypeId.ZEALOT,
    AbilityId.TRAIN_ADEPT: UnitTypeId.ADEPT,
    AbilityId.TRAINWARP_ADEPT: UnitTypeId.ADEPT,
    AbilityId.GATEWAYTRAIN_STALKER: UnitTypeId.STALKER,
    AbilityId.WARPGATETRAIN_STALKER: UnitTypeId.STALKER,
    AbilityId.GATEWAYTRAIN_SENTRY: UnitTypeId.SENTRY,
    AbilityId.WARPGATETRAIN_SENTRY: UnitTypeId.SENTRY,
    AbilityId.GATEWAYTRAIN_DARKTEMPLAR: UnitTypeId.DARKTEMPLAR,
    AbilityId.WARPGATETRAIN_DARKTEMPLAR: UnitTypeId.DARKTEMPLAR,
    AbilityId.GATEWAYTRAIN_HIGHTEMPLAR: UnitTypeId.HIGHTEMPLAR,
    AbilityId.WARPGATETRAIN_HIGHTEMPLAR: UnitTypeId.HIGHTEMPLAR,
    AbilityId.ROBOTICSFACILITYTRAIN_OBSERVER: UnitTypeId.OBSERVER,
    AbilityId.ROBOTICSFACILITYTRAIN_COLOSSUS: UnitTypeId.COLOSSUS,
    AbilityId.ROBOTICSFACILITYTRAIN_IMMORTAL: UnitTypeId.IMMORTAL,
    AbilityId.ROBOTICSFACILITYTRAIN_WARPPRISM: UnitTypeId.WARPPRISM,
    AbilityId.STARGATETRAIN_CARRIER: UnitTypeId.CARRIER,
    AbilityId.STARGATETRAIN_ORACLE: UnitTypeId.ORACLE,
    AbilityId.STARGATETRAIN_PHOENIX: UnitTypeId.PHOENIX,
    AbilityId.STARGATETRAIN_TEMPEST: UnitTypeId.TEMPEST,
    AbilityId.STARGATETRAIN_VOIDRAY: UnitTypeId.VOIDRAY,
    AbilityId.NEXUSTRAINMOTHERSHIP_MOTHERSHIP: UnitTypeId.MOTHERSHIP,
    # Terran
    AbilityId.COMMANDCENTERTRAIN_SCV: UnitTypeId.SCV,
    AbilityId.BARRACKSTRAIN_MARINE: UnitTypeId.MARINE,
    AbilityId.BARRACKSTRAIN_GHOST: UnitTypeId.GHOST,
    AbilityId.BARRACKSTRAIN_MARAUDER: UnitTypeId.MARAUDER,
    AbilityId.BARRACKSTRAIN_REAPER: UnitTypeId.REAPER,
    AbilityId.FACTORYTRAIN_HELLION: UnitTypeId.HELLION,
    AbilityId.FACTORYTRAIN_SIEGETANK: UnitTypeId.SIEGETANK,
    AbilityId.FACTORYTRAIN_THOR: UnitTypeId.THOR,
    AbilityId.FACTORYTRAIN_WIDOWMINE: UnitTypeId.WIDOWMINE,
    AbilityId.TRAIN_HELLBAT: UnitTypeId.HELLIONTANK,
    AbilityId.TRAIN_CYCLONE: UnitTypeId.CYCLONE,
    AbilityId.STARPORTTRAIN_RAVEN: UnitTypeId.RAVEN,
    AbilityId.STARPORTTRAIN_VIKINGFIGHTER: UnitTypeId.VIKINGFIGHTER,
    AbilityId.STARPORTTRAIN_MEDIVAC: UnitTypeId.MEDIVAC,
    AbilityId.STARPORTTRAIN_BATTLECRUISER: UnitTypeId.BATTLECRUISER,
    AbilityId.STARPORTTRAIN_BANSHEE: UnitTypeId.BANSHEE,
    AbilityId.STARPORTTRAIN_LIBERATOR: UnitTypeId.LIBERATOR,
    # Zerg
    AbilityId.LARVATRAIN_DRONE: UnitTypeId.DRONE,
    AbilityId.LARVATRAIN_OVERLORD: UnitTypeId.OVERLORD,
    AbilityId.LARVATRAIN_ZERGLING: UnitTypeId.ZERGLING,
    AbilityId.LARVATRAIN_ROACH: UnitTypeId.ROACH,
    AbilityId.LARVATRAIN_HYDRALISK: UnitTypeId.HYDRALISK,
    AbilityId.LARVATRAIN_MUTALISK: UnitTypeId.MUTALISK,
    AbilityId.LARVATRAIN_CORRUPTOR: UnitTypeId.CORRUPTOR,
    AbilityId.LARVATRAIN_ULTRALISK: UnitTypeId.ULTRALISK,
    AbilityId.LARVATRAIN_INFESTOR: UnitTypeId.INFESTOR,
    AbilityId.LARVATRAIN_VIPER: UnitTypeId.VIPER,
    AbilityId.LOCUSTTRAIN_SWARMHOST: UnitTypeId.SWARMHOSTMP,
    AbilityId.TRAINQUEEN_QUEEN: UnitTypeId.QUEEN,
}

IS_STRUCTURE: int = Attribute.Structure.value
IS_LIGHT: int = Attribute.Light.value
IS_ARMORED: int = Attribute.Armored.value
IS_BIOLOGICAL: int = Attribute.Biological.value
IS_MECHANICAL: int = Attribute.Mechanical.value
IS_MASSIVE: int = Attribute.Massive.value
IS_PSIONIC: int = Attribute.Psionic.value
UNIT_BATTLECRUISER: UnitTypeId = UnitTypeId.BATTLECRUISER
UNIT_ORACLE: UnitTypeId = UnitTypeId.ORACLE
TARGET_GROUND: set[int] = {TargetType.Ground.value, TargetType.Any.value}
TARGET_AIR: set[int] = {TargetType.Air.value, TargetType.Any.value}
TARGET_BOTH: set[int] = TARGET_GROUND | TARGET_AIR
IS_SNAPSHOT = DisplayType.Snapshot.value
IS_VISIBLE = DisplayType.Visible.value
IS_PLACEHOLDER = DisplayType.Placeholder.value
IS_MINE = Alliance.Self.value
IS_ENEMY = Alliance.Enemy.value
IS_CLOAKED: set[int] = {CloakState.Cloaked.value, CloakState.CloakedDetected.value, CloakState.CloakedAllied.value}
IS_REVEALED: int = CloakState.CloakedDetected.value
CAN_BE_ATTACKED: set[int] = {CloakState.NotCloaked.value, CloakState.CloakedDetected.value}
IS_CARRYING_MINERALS: set[BuffId] = {BuffId.CARRYMINERALFIELDMINERALS, BuffId.CARRYHIGHYIELDMINERALFIELDMINERALS}
IS_CARRYING_VESPENE: set[BuffId] = {
    BuffId.CARRYHARVESTABLEVESPENEGEYSERGAS,
    BuffId.CARRYHARVESTABLEVESPENEGEYSERGASPROTOSS,
    BuffId.CARRYHARVESTABLEVESPENEGEYSERGASZERG,
}
IS_CARRYING_RESOURCES: set[BuffId] = IS_CARRYING_MINERALS | IS_CARRYING_VESPENE
IS_ATTACKING: set[AbilityId] = {
    AbilityId.ATTACK,
    AbilityId.ATTACK_ATTACK,
    AbilityId.ATTACK_ATTACKTOWARDS,
    AbilityId.ATTACK_ATTACKBARRAGE,
    AbilityId.SCAN_MOVE,
}
IS_PATROLLING: AbilityId = AbilityId.PATROL_PATROL
IS_GATHERING: AbilityId = AbilityId.HARVEST_GATHER
IS_RETURNING: AbilityId = AbilityId.HARVEST_RETURN
IS_COLLECTING: set[AbilityId] = {IS_GATHERING, IS_RETURNING}
IS_CONSTRUCTING_SCV: set[AbilityId] = {
    AbilityId.TERRANBUILD_ARMORY,
    AbilityId.TERRANBUILD_BARRACKS,
    AbilityId.TERRANBUILD_BUNKER,
    AbilityId.TERRANBUILD_COMMANDCENTER,
    AbilityId.TERRANBUILD_ENGINEERINGBAY,
    AbilityId.TERRANBUILD_FACTORY,
    AbilityId.TERRANBUILD_FUSIONCORE,
    AbilityId.TERRANBUILD_GHOSTACADEMY,
    AbilityId.TERRANBUILD_MISSILETURRET,
    AbilityId.TERRANBUILD_REFINERY,
    AbilityId.TERRANBUILD_SENSORTOWER,
    AbilityId.TERRANBUILD_STARPORT,
    AbilityId.TERRANBUILD_SUPPLYDEPOT,
}
IS_REPAIRING: set[AbilityId] = {AbilityId.EFFECT_REPAIR, AbilityId.EFFECT_REPAIR_MULE, AbilityId.EFFECT_REPAIR_SCV}
IS_DETECTOR: set[UnitTypeId] = {
    UnitTypeId.OBSERVER,
    UnitTypeId.OBSERVERSIEGEMODE,
    UnitTypeId.RAVEN,
    UnitTypeId.MISSILETURRET,
    UnitTypeId.OVERSEER,
    UnitTypeId.OVERSEERSIEGEMODE,
    UnitTypeId.SPORECRAWLER,
}
SPEED_UPGRADE_DICT: dict[UnitTypeId, UpgradeId] = {
    # Terran
    UnitTypeId.MEDIVAC: UpgradeId.MEDIVACRAPIDDEPLOYMENT,
    UnitTypeId.BANSHEE: UpgradeId.BANSHEESPEED,
    # Protoss
    UnitTypeId.ZEALOT: UpgradeId.CHARGE,
    UnitTypeId.OBSERVER: UpgradeId.OBSERVERGRAVITICBOOSTER,
    UnitTypeId.WARPPRISM: UpgradeId.GRAVITICDRIVE,
    UnitTypeId.VOIDRAY: UpgradeId.VOIDRAYSPEEDUPGRADE,
    # Zerg
    UnitTypeId.OVERLORD: UpgradeId.OVERLORDSPEED,
    UnitTypeId.OVERSEER: UpgradeId.OVERLORDSPEED,
    UnitTypeId.ZERGLING: UpgradeId.ZERGLINGMOVEMENTSPEED,
    UnitTypeId.BANELING: UpgradeId.CENTRIFICALHOOKS,
    UnitTypeId.ROACH: UpgradeId.GLIALRECONSTITUTION,
    UnitTypeId.LURKERMP: UpgradeId.DIGGINGCLAWS,
}
SPEED_INCREASE_DICT: dict[UnitTypeId, float] = {
    # Terran
    UnitTypeId.MEDIVAC: 1.18,
    UnitTypeId.BANSHEE: 1.3636,
    # Protoss
    UnitTypeId.ZEALOT: 1.5,
    UnitTypeId.OBSERVER: 2,
    UnitTypeId.WARPPRISM: 1.3,
    UnitTypeId.VOIDRAY: 1.328,
    # Zerg
    UnitTypeId.OVERLORD: 2.915,
    UnitTypeId.OVERSEER: 1.8015,
    UnitTypeId.ZERGLING: 1.6,
    UnitTypeId.BANELING: 1.18,
    UnitTypeId.ROACH: 1.3333333333,
    UnitTypeId.LURKERMP: 1.1,
}
temp1 = set(SPEED_UPGRADE_DICT)
temp2 = set(SPEED_INCREASE_DICT)
assert temp1 == temp2, f"{temp1.symmetric_difference(temp2)}"
del temp1
del temp2
SPEED_INCREASE_ON_CREEP_DICT: dict[UnitTypeId, float] = {
    UnitTypeId.QUEEN: 2.67,
    UnitTypeId.ZERGLING: 1.3,
    UnitTypeId.BANELING: 1.3,
    UnitTypeId.ROACH: 1.3,
    UnitTypeId.RAVAGER: 1.3,
    UnitTypeId.HYDRALISK: 1.3,
    UnitTypeId.LURKERMP: 1.3,
    UnitTypeId.ULTRALISK: 1.3,
    UnitTypeId.INFESTOR: 1.3,
    UnitTypeId.INFESTORTERRAN: 1.3,
    UnitTypeId.SWARMHOSTMP: 1.3,
    UnitTypeId.LOCUSTMP: 1.4,
    UnitTypeId.SPINECRAWLER: 2.5,
    UnitTypeId.SPORECRAWLER: 2.5,
}
OFF_CREEP_SPEED_UPGRADE_DICT: dict[UnitTypeId, UpgradeId] = {
    UnitTypeId.HYDRALISK: UpgradeId.EVOLVEMUSCULARAUGMENTS,
    UnitTypeId.ULTRALISK: UpgradeId.ANABOLICSYNTHESIS,
}
OFF_CREEP_SPEED_INCREASE_DICT: dict[UnitTypeId, float] = {
    UnitTypeId.HYDRALISK: 1.25,
    UnitTypeId.ULTRALISK: 1.2,
}
temp1 = set(OFF_CREEP_SPEED_UPGRADE_DICT)
temp2 = set(OFF_CREEP_SPEED_INCREASE_DICT)
assert temp1 == temp2, f"{temp1.symmetric_difference(temp2)}"
del temp1
del temp2
# Movement speed gets altered by this factor if it is affected by this buff
SPEED_ALTERING_BUFFS: dict[BuffId, float] = {
    # Stimpack increases speed by 1.5
    BuffId.STIMPACK: 1.5,
    BuffId.STIMPACKMARAUDER: 1.5,
    BuffId.CHARGEUP: 2.2,  # x2.8 speed up in pre version 4.11
    # Concussive shells of Marauder reduce speed by 50%
    BuffId.DUTCHMARAUDERSLOW: 0.5,
    # Time Warp of Mothership reduces speed by 50%
    BuffId.TIMEWARPPRODUCTION: 0.5,
    # Fungal Growth of Infestor reduces speed by 75%
    BuffId.FUNGALGROWTH: 0.25,
    # Inhibitor Zones reduce speed by 35%
    BuffId.INHIBITORZONETEMPORALFIELD: 0.65,
    # TODO there is a new zone coming (acceleration zone) which increase movement speed, ultralisk will be affected by this
}
UNIT_PHOTONCANNON: UnitTypeId = UnitTypeId.PHOTONCANNON
UNIT_COLOSSUS: UnitTypeId = UnitTypeId.COLOSSUS
# Used in unit_command.py and action.py to combine only certain abilities
COMBINEABLE_ABILITIES: set[AbilityId] = {
    AbilityId.MOVE,
    AbilityId.ATTACK,
    AbilityId.SCAN_MOVE,
    AbilityId.STOP,
    AbilityId.HOLDPOSITION,
    AbilityId.PATROL,
    AbilityId.HARVEST_GATHER,
    AbilityId.HARVEST_RETURN,
    AbilityId.EFFECT_REPAIR,
    AbilityId.LIFT,
    AbilityId.BURROWDOWN,
    AbilityId.BURROWUP,
    AbilityId.SIEGEMODE_SIEGEMODE,
    AbilityId.UNSIEGE_UNSIEGE,
    AbilityId.MORPH_LIBERATORAAMODE,
    AbilityId.EFFECT_STIM,
    AbilityId.MORPH_UPROOT,
    AbilityId.EFFECT_BLINK,
    AbilityId.MORPH_ARCHON,
}
FakeEffectRadii: dict[int, float] = {
    UnitTypeId.KD8CHARGE.value: 2,
    UnitTypeId.PARASITICBOMBDUMMY.value: 3,
    UnitTypeId.FORCEFIELD.value: 1.5,
}
FakeEffectID: dict[int, str] = {
    UnitTypeId.KD8CHARGE.value: "KD8CHARGE",
    UnitTypeId.PARASITICBOMBDUMMY.value: "PARASITICBOMB",
    UnitTypeId.FORCEFIELD.value: "FORCEFIELD",
}

TERRAN_STRUCTURES_REQUIRE_SCV: set[UnitTypeId] = {
    UnitTypeId.ARMORY,
    UnitTypeId.BARRACKS,
    UnitTypeId.BUNKER,
    UnitTypeId.COMMANDCENTER,
    UnitTypeId.ENGINEERINGBAY,
    UnitTypeId.FACTORY,
    UnitTypeId.FUSIONCORE,
    UnitTypeId.GHOSTACADEMY,
    UnitTypeId.MISSILETURRET,
    UnitTypeId.REFINERY,
    UnitTypeId.REFINERYRICH,
    UnitTypeId.SENSORTOWER,
    UnitTypeId.STARPORT,
    UnitTypeId.SUPPLYDEPOT,
}


def return_NOTAUNIT() -> UnitTypeId:
    # NOTAUNIT = 0
    return UnitTypeId.NOTAUNIT


# Hotfix for structures and units as the API does not seem to return the correct values, e.g. ghost and thor have None in the requirements
TERRAN_TECH_REQUIREMENT: dict[UnitTypeId, UnitTypeId] = defaultdict(
    return_NOTAUNIT,
    {
        UnitTypeId.MISSILETURRET: UnitTypeId.ENGINEERINGBAY,
        UnitTypeId.SENSORTOWER: UnitTypeId.ENGINEERINGBAY,
        UnitTypeId.PLANETARYFORTRESS: UnitTypeId.ENGINEERINGBAY,
        UnitTypeId.BARRACKS: UnitTypeId.SUPPLYDEPOT,
        UnitTypeId.ORBITALCOMMAND: UnitTypeId.BARRACKS,
        UnitTypeId.BUNKER: UnitTypeId.BARRACKS,
        UnitTypeId.GHOST: UnitTypeId.GHOSTACADEMY,
        UnitTypeId.GHOSTACADEMY: UnitTypeId.BARRACKS,
        UnitTypeId.FACTORY: UnitTypeId.BARRACKS,
        UnitTypeId.ARMORY: UnitTypeId.FACTORY,
        UnitTypeId.HELLIONTANK: UnitTypeId.ARMORY,
        UnitTypeId.THOR: UnitTypeId.ARMORY,
        UnitTypeId.STARPORT: UnitTypeId.FACTORY,
        UnitTypeId.FUSIONCORE: UnitTypeId.STARPORT,
        UnitTypeId.BATTLECRUISER: UnitTypeId.FUSIONCORE,
    },
)
PROTOSS_TECH_REQUIREMENT: dict[UnitTypeId, UnitTypeId] = defaultdict(
    return_NOTAUNIT,
    {
        UnitTypeId.PHOTONCANNON: UnitTypeId.FORGE,
        UnitTypeId.CYBERNETICSCORE: UnitTypeId.GATEWAY,
        UnitTypeId.SENTRY: UnitTypeId.CYBERNETICSCORE,
        UnitTypeId.STALKER: UnitTypeId.CYBERNETICSCORE,
        UnitTypeId.ADEPT: UnitTypeId.CYBERNETICSCORE,
        UnitTypeId.TWILIGHTCOUNCIL: UnitTypeId.CYBERNETICSCORE,
        UnitTypeId.SHIELDBATTERY: UnitTypeId.CYBERNETICSCORE,
        UnitTypeId.TEMPLARARCHIVE: UnitTypeId.TWILIGHTCOUNCIL,
        UnitTypeId.DARKSHRINE: UnitTypeId.TWILIGHTCOUNCIL,
        UnitTypeId.HIGHTEMPLAR: UnitTypeId.TEMPLARARCHIVE,
        UnitTypeId.DARKTEMPLAR: UnitTypeId.DARKSHRINE,
        UnitTypeId.STARGATE: UnitTypeId.CYBERNETICSCORE,
        UnitTypeId.TEMPEST: UnitTypeId.FLEETBEACON,
        UnitTypeId.CARRIER: UnitTypeId.FLEETBEACON,
        UnitTypeId.MOTHERSHIP: UnitTypeId.FLEETBEACON,
        UnitTypeId.ROBOTICSFACILITY: UnitTypeId.CYBERNETICSCORE,
        UnitTypeId.ROBOTICSBAY: UnitTypeId.ROBOTICSFACILITY,
        UnitTypeId.COLOSSUS: UnitTypeId.ROBOTICSBAY,
        UnitTypeId.DISRUPTOR: UnitTypeId.ROBOTICSBAY,
    },
)
ZERG_TECH_REQUIREMENT: dict[UnitTypeId, UnitTypeId] = defaultdict(
    return_NOTAUNIT,
    {
        UnitTypeId.ZERGLING: UnitTypeId.SPAWNINGPOOL,
        UnitTypeId.QUEEN: UnitTypeId.SPAWNINGPOOL,
        UnitTypeId.ROACHWARREN: UnitTypeId.SPAWNINGPOOL,
        UnitTypeId.BANELINGNEST: UnitTypeId.SPAWNINGPOOL,
        UnitTypeId.SPINECRAWLER: UnitTypeId.SPAWNINGPOOL,
        UnitTypeId.SPORECRAWLER: UnitTypeId.SPAWNINGPOOL,
        UnitTypeId.ROACH: UnitTypeId.ROACHWARREN,
        UnitTypeId.BANELING: UnitTypeId.BANELINGNEST,
        UnitTypeId.LAIR: UnitTypeId.SPAWNINGPOOL,
        UnitTypeId.OVERSEER: UnitTypeId.LAIR,
        UnitTypeId.OVERLORDTRANSPORT: UnitTypeId.LAIR,
        UnitTypeId.INFESTATIONPIT: UnitTypeId.LAIR,
        UnitTypeId.INFESTOR: UnitTypeId.INFESTATIONPIT,
        UnitTypeId.SWARMHOSTMP: UnitTypeId.INFESTATIONPIT,
        UnitTypeId.HYDRALISKDEN: UnitTypeId.LAIR,
        UnitTypeId.HYDRALISK: UnitTypeId.HYDRALISKDEN,
        UnitTypeId.LURKERDENMP: UnitTypeId.HYDRALISKDEN,
        UnitTypeId.LURKERMP: UnitTypeId.LURKERDENMP,
        UnitTypeId.SPIRE: UnitTypeId.LAIR,
        UnitTypeId.MUTALISK: UnitTypeId.SPIRE,
        UnitTypeId.CORRUPTOR: UnitTypeId.SPIRE,
        UnitTypeId.NYDUSNETWORK: UnitTypeId.LAIR,
        UnitTypeId.HIVE: UnitTypeId.INFESTATIONPIT,
        UnitTypeId.VIPER: UnitTypeId.HIVE,
        UnitTypeId.ULTRALISKCAVERN: UnitTypeId.HIVE,
        UnitTypeId.GREATERSPIRE: UnitTypeId.HIVE,
        UnitTypeId.BROODLORD: UnitTypeId.GREATERSPIRE,
    },
)
# Required in 'tech_requirement_progress' bot_ai.py function
EQUIVALENTS_FOR_TECH_PROGRESS: dict[UnitTypeId, set[UnitTypeId]] = {
    # Protoss
    UnitTypeId.GATEWAY: {UnitTypeId.WARPGATE},
    UnitTypeId.WARPPRISM: {UnitTypeId.WARPPRISMPHASING},
    UnitTypeId.OBSERVER: {UnitTypeId.OBSERVERSIEGEMODE},
    # Terran
    UnitTypeId.SUPPLYDEPOT: {UnitTypeId.SUPPLYDEPOTLOWERED, UnitTypeId.SUPPLYDEPOTDROP},
    UnitTypeId.BARRACKS: {UnitTypeId.BARRACKSFLYING},
    UnitTypeId.FACTORY: {UnitTypeId.FACTORYFLYING},
    UnitTypeId.STARPORT: {UnitTypeId.STARPORTFLYING},
    UnitTypeId.COMMANDCENTER: {
        UnitTypeId.COMMANDCENTERFLYING,
        UnitTypeId.PLANETARYFORTRESS,
        UnitTypeId.ORBITALCOMMAND,
        UnitTypeId.ORBITALCOMMANDFLYING,
    },
    UnitTypeId.ORBITALCOMMAND: {UnitTypeId.ORBITALCOMMANDFLYING},
    UnitTypeId.HELLION: {UnitTypeId.HELLIONTANK},
    UnitTypeId.WIDOWMINE: {UnitTypeId.WIDOWMINEBURROWED},
    UnitTypeId.SIEGETANK: {UnitTypeId.SIEGETANKSIEGED},
    UnitTypeId.THOR: {UnitTypeId.THORAP},
    UnitTypeId.VIKINGFIGHTER: {UnitTypeId.VIKINGASSAULT},
    UnitTypeId.LIBERATOR: {UnitTypeId.LIBERATORAG},
    # Zerg
    UnitTypeId.LAIR: {UnitTypeId.HIVE},
    UnitTypeId.HATCHERY: {UnitTypeId.LAIR, UnitTypeId.HIVE},
    UnitTypeId.SPIRE: {UnitTypeId.GREATERSPIRE},
    UnitTypeId.SPINECRAWLER: {UnitTypeId.SPINECRAWLERUPROOTED},
    UnitTypeId.SPORECRAWLER: {UnitTypeId.SPORECRAWLERUPROOTED},
    UnitTypeId.OVERLORD: {UnitTypeId.OVERLORDTRANSPORT},
    UnitTypeId.OVERSEER: {UnitTypeId.OVERSEERSIEGEMODE},
    UnitTypeId.DRONE: {UnitTypeId.DRONEBURROWED},
    UnitTypeId.ZERGLING: {UnitTypeId.ZERGLINGBURROWED},
    UnitTypeId.ROACH: {UnitTypeId.ROACHBURROWED},
    UnitTypeId.RAVAGER: {UnitTypeId.RAVAGERBURROWED},
    UnitTypeId.HYDRALISK: {UnitTypeId.HYDRALISKBURROWED},
    UnitTypeId.LURKERMP: {UnitTypeId.LURKERMPBURROWED},
    UnitTypeId.SWARMHOSTMP: {UnitTypeId.SWARMHOSTBURROWEDMP},
    UnitTypeId.INFESTOR: {UnitTypeId.INFESTORBURROWED},
    UnitTypeId.ULTRALISK: {UnitTypeId.ULTRALISKBURROWED},
    # TODO What about morphing untis? E.g. roach to ravager, overlord to drop-overlord or overseer
}
ALL_GAS: set[UnitTypeId] = {
    UnitTypeId.ASSIMILATOR,
    UnitTypeId.ASSIMILATORRICH,
    UnitTypeId.REFINERY,
    UnitTypeId.REFINERYRICH,
    UnitTypeId.EXTRACTOR,
    UnitTypeId.EXTRACTORRICH,
}
# pyre-ignore[11]
DAMAGE_BONUS_PER_UPGRADE: dict[UnitTypeId, dict[TargetType, Any]] = {
    #
    # Protoss
    #
    UnitTypeId.PROBE: {TargetType.Ground.value: {None: 0}},
    # Gateway Units
    UnitTypeId.ADEPT: {TargetType.Ground.value: {IS_LIGHT: 1}},
    UnitTypeId.STALKER: {TargetType.Any.value: {IS_ARMORED: 1}},
    UnitTypeId.DARKTEMPLAR: {TargetType.Ground.value: {None: 5}},
    UnitTypeId.ARCHON: {TargetType.Any.value: {None: 3, IS_BIOLOGICAL: 1}},
    # Robo Units
    UnitTypeId.IMMORTAL: {TargetType.Ground.value: {None: 2, IS_ARMORED: 3}},
    UnitTypeId.COLOSSUS: {TargetType.Ground.value: {IS_LIGHT: 1}},
    # Stargate Units
    UnitTypeId.ORACLE: {TargetType.Ground.value: {None: 0}},
    UnitTypeId.TEMPEST: {TargetType.Ground.value: {None: 4}, TargetType.Air.value: {None: 3, IS_MASSIVE: 2}},
    #
    # Terran
    #
    UnitTypeId.SCV: {TargetType.Ground.value: {None: 0}},
    # Barracks Units
    UnitTypeId.MARAUDER: {TargetType.Ground.value: {IS_ARMORED: 1}},
    UnitTypeId.GHOST: {TargetType.Any.value: {IS_LIGHT: 1}},
    # Factory Units
    UnitTypeId.HELLION: {TargetType.Ground.value: {IS_LIGHT: 1}},
    UnitTypeId.HELLIONTANK: {TargetType.Ground.value: {None: 2, IS_LIGHT: 1}},
    UnitTypeId.CYCLONE: {TargetType.Any.value: {None: 2}},
    UnitTypeId.SIEGETANK: {TargetType.Ground.value: {None: 2, IS_ARMORED: 1}},
    UnitTypeId.SIEGETANKSIEGED: {TargetType.Ground.value: {None: 4, IS_ARMORED: 1}},
    UnitTypeId.THOR: {TargetType.Ground.value: {None: 3}, TargetType.Air.value: {IS_LIGHT: 1}},
    UnitTypeId.THORAP: {TargetType.Ground.value: {None: 3}, TargetType.Air.value: {None: 3, IS_MASSIVE: 1}},
    # Starport Units
    UnitTypeId.VIKINGASSAULT: {TargetType.Ground.value: {IS_MECHANICAL: 1}},
    UnitTypeId.LIBERATORAG: {TargetType.Ground.value: {None: 5}},
    #
    # Zerg
    #
    UnitTypeId.DRONE: {TargetType.Ground.value: {None: 0}},
    # Hatch Tech Units (Queen, Ling, Bane, Roach, Ravager)
    UnitTypeId.BANELING: {TargetType.Ground.value: {None: 2, IS_LIGHT: 2, IS_STRUCTURE: 3}},
    UnitTypeId.ROACH: {TargetType.Ground.value: {None: 2}},
    UnitTypeId.RAVAGER: {TargetType.Ground.value: {None: 2}},
    # Lair Tech Units (Hydra, Lurker, Ultra)
    UnitTypeId.LURKERMPBURROWED: {TargetType.Ground.value: {None: 2, IS_ARMORED: 1}},
    UnitTypeId.ULTRALISK: {TargetType.Ground.value: {None: 3}},
    # Spire Units (Muta, Corruptor, BL)
    UnitTypeId.CORRUPTOR: {TargetType.Air.value: {IS_MASSIVE: 1}},
    UnitTypeId.BROODLORD: {TargetType.Ground.value: {None: 2}},
}
TARGET_HELPER = {
    1: "no target",
    2: "Point2",
    3: "Unit",
    4: "Point2 or Unit",
    5: "Point2 or no target",
}
CREATION_ABILITY_FIX: dict[UnitTypeId, AbilityId] = {
    UnitTypeId.ARCHON: AbilityId.ARCHON_WARP_TARGET,
    UnitTypeId.ASSIMILATORRICH: AbilityId.PROTOSSBUILD_ASSIMILATOR,
    UnitTypeId.BANELINGCOCOON: AbilityId.MORPHZERGLINGTOBANELING_BANELING,
    UnitTypeId.CHANGELING: AbilityId.SPAWNCHANGELING_SPAWNCHANGELING,
    UnitTypeId.EXTRACTORRICH: AbilityId.ZERGBUILD_EXTRACTOR,
    UnitTypeId.INTERCEPTOR: AbilityId.BUILD_INTERCEPTORS,
    UnitTypeId.LURKERMPEGG: AbilityId.MORPH_LURKER,
    UnitTypeId.MULE: AbilityId.CALLDOWNMULE_CALLDOWNMULE,
    UnitTypeId.RAVAGERCOCOON: AbilityId.MORPHTORAVAGER_RAVAGER,
    UnitTypeId.REFINERYRICH: AbilityId.TERRANBUILD_REFINERY,
    UnitTypeId.TECHLAB: AbilityId.BUILD_TECHLAB,
}
```

### File: `sc2/controller.py`

```python
import platform
from pathlib import Path

from loguru import logger

# pyre-ignore[21]
from s2clientprotocol import sc2api_pb2 as sc_pb

from sc2.player import Computer
from sc2.protocol import Protocol


class Controller(Protocol):
    def __init__(self, ws, process) -> None:
        super().__init__(ws)
        self._process = process

    @property
    def running(self) -> bool:
        return self._process._process is not None

    async def create_game(self, game_map, players, realtime: bool, random_seed=None, disable_fog=None):
        req = sc_pb.RequestCreateGame(
            local_map=sc_pb.LocalMap(map_path=str(game_map.relative_path)), realtime=realtime, disable_fog=disable_fog
        )
        if random_seed is not None:
            req.random_seed = random_seed

        for player in players:
            p = req.player_setup.add()
            p.type = player.type.value
            if isinstance(player, Computer):
                p.race = player.race.value
                p.difficulty = player.difficulty.value
                p.ai_build = player.ai_build.value

        logger.info("Creating new game")
        logger.info(f"Map:     {game_map.name}")
        logger.info(f"Players: {', '.join(str(p) for p in players)}")
        result = await self._execute(create_game=req)
        return result

    async def request_available_maps(self):
        req = sc_pb.RequestAvailableMaps()
        result = await self._execute(available_maps=req)
        return result

    async def request_save_map(self, download_path: str):
        """Not working on linux."""
        req = sc_pb.RequestSaveMap(map_path=download_path)
        result = await self._execute(save_map=req)
        return result

    async def request_replay_info(self, replay_path: str):
        """Not working on linux."""
        req = sc_pb.RequestReplayInfo(replay_path=replay_path, download_data=False)
        result = await self._execute(replay_info=req)
        return result

    async def start_replay(self, replay_path: str, realtime: bool, observed_id: int = 0):
        ifopts = sc_pb.InterfaceOptions(
            raw=True, score=True, show_cloaked=True, raw_affects_selection=True, raw_crop_to_playable_area=False
        )
        if platform.system() == "Linux":
            replay_name = Path(replay_path).name
            home_replay_folder = Path.home() / "Documents" / "StarCraft II" / "Replays"
            if str(home_replay_folder / replay_name) != replay_path:
                logger.warning(
                    f"Linux detected, please put your replay in your home directory at {home_replay_folder}. It was detected at {replay_path}"
                )
                raise FileNotFoundError
            replay_path = replay_name

        req = sc_pb.RequestStartReplay(
            replay_path=replay_path, observed_player_id=observed_id, realtime=realtime, options=ifopts
        )

        result = await self._execute(start_replay=req)
        assert result.status == 4, f"{result.start_replay.error} - {result.start_replay.error_details}"
        return result
```

### File: `sc2/data.py`

```python
# pyre-ignore-all-errors[16, 19]
"""For the list of enums, see here

https://github.com/Blizzard/s2client-api/blob/d9ba0a33d6ce9d233c2a4ee988360c188fbe9dbf/include/sc2api/sc2_gametypes.h
https://github.com/Blizzard/s2client-api/blob/d9ba0a33d6ce9d233c2a4ee988360c188fbe9dbf/include/sc2api/sc2_action.h
https://github.com/Blizzard/s2client-api/blob/d9ba0a33d6ce9d233c2a4ee988360c188fbe9dbf/include/sc2api/sc2_unit.h
https://github.com/Blizzard/s2client-api/blob/d9ba0a33d6ce9d233c2a4ee988360c188fbe9dbf/include/sc2api/sc2_data.h
"""

from __future__ import annotations

import enum

# pyre-ignore[21]
from s2clientprotocol import common_pb2 as common_pb
from s2clientprotocol import data_pb2 as data_pb
from s2clientprotocol import error_pb2 as error_pb
from s2clientprotocol import raw_pb2 as raw_pb
from s2clientprotocol import sc2api_pb2 as sc_pb

from sc2.ids.ability_id import AbilityId
from sc2.ids.unit_typeid import UnitTypeId

CreateGameError = enum.Enum("CreateGameError", sc_pb.ResponseCreateGame.Error.items())

PlayerType = enum.Enum("PlayerType", sc_pb.PlayerType.items())
Difficulty = enum.Enum("Difficulty", sc_pb.Difficulty.items())
AIBuild = enum.Enum("AIBuild", sc_pb.AIBuild.items())
Status = enum.Enum("Status", sc_pb.Status.items())
Result = enum.Enum("Result", sc_pb.Result.items())
Alert = enum.Enum("Alert", sc_pb.Alert.items())
ChatChannel = enum.Enum("ChatChannel", sc_pb.ActionChat.Channel.items())

Race = enum.Enum("Race", common_pb.Race.items())

DisplayType = enum.Enum("DisplayType", raw_pb.DisplayType.items())
Alliance = enum.Enum("Alliance", raw_pb.Alliance.items())
CloakState = enum.Enum("CloakState", raw_pb.CloakState.items())

Attribute = enum.Enum("Attribute", data_pb.Attribute.items())
TargetType = enum.Enum("TargetType", data_pb.Weapon.TargetType.items())
Target = enum.Enum("Target", data_pb.AbilityData.Target.items())

ActionResult = enum.Enum("ActionResult", error_pb.ActionResult.items())

# pyre-ignore[11]
race_worker: dict[Race, UnitTypeId] = {
    Race.Protoss: UnitTypeId.PROBE,
    Race.Terran: UnitTypeId.SCV,
    Race.Zerg: UnitTypeId.DRONE,
}

race_townhalls: dict[Race, set[UnitTypeId]] = {
    Race.Protoss: {UnitTypeId.NEXUS},
    Race.Terran: {
        UnitTypeId.COMMANDCENTER,
        UnitTypeId.ORBITALCOMMAND,
        UnitTypeId.PLANETARYFORTRESS,
        UnitTypeId.COMMANDCENTERFLYING,
        UnitTypeId.ORBITALCOMMANDFLYING,
    },
    Race.Zerg: {UnitTypeId.HATCHERY, UnitTypeId.LAIR, UnitTypeId.HIVE},
    Race.Random: {
        # Protoss
        UnitTypeId.NEXUS,
        # Terran
        UnitTypeId.COMMANDCENTER,
        UnitTypeId.ORBITALCOMMAND,
        UnitTypeId.PLANETARYFORTRESS,
        UnitTypeId.COMMANDCENTERFLYING,
        UnitTypeId.ORBITALCOMMANDFLYING,
        # Zerg
        UnitTypeId.HATCHERY,
        UnitTypeId.LAIR,
        UnitTypeId.HIVE,
    },
}

warpgate_abilities: dict[AbilityId, AbilityId] = {
    AbilityId.GATEWAYTRAIN_ZEALOT: AbilityId.WARPGATETRAIN_ZEALOT,
    AbilityId.GATEWAYTRAIN_STALKER: AbilityId.WARPGATETRAIN_STALKER,
    AbilityId.GATEWAYTRAIN_HIGHTEMPLAR: AbilityId.WARPGATETRAIN_HIGHTEMPLAR,
    AbilityId.GATEWAYTRAIN_DARKTEMPLAR: AbilityId.WARPGATETRAIN_DARKTEMPLAR,
    AbilityId.GATEWAYTRAIN_SENTRY: AbilityId.WARPGATETRAIN_SENTRY,
    AbilityId.TRAIN_ADEPT: AbilityId.TRAINWARP_ADEPT,
}

race_gas: dict[Race, UnitTypeId] = {
    Race.Protoss: UnitTypeId.ASSIMILATOR,
    Race.Terran: UnitTypeId.REFINERY,
    Race.Zerg: UnitTypeId.EXTRACTOR,
}
```

### File: `sc2/expiring_dict.py`

```python
# pyre-ignore-all-errors[14, 15, 58]
from __future__ import annotations

from collections import OrderedDict
from collections.abc import Iterable
from threading import RLock
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from sc2.bot_ai import BotAI


class ExpiringDict(OrderedDict):
    """
    An expiring dict that uses the bot.state.game_loop to only return items that are valid for a specific amount of time.

    Example usages::

        async def on_step(iteration: int):
            # This dict will hold up to 10 items and only return values that have been added up to 20 frames ago
            my_dict = ExpiringDict(self, max_age_frames=20)
            if iteration == 0:
                # Add item
                my_dict["test"] = "something"
            if iteration == 2:
                # On default, one iteration is called every 8 frames
                if "test" in my_dict:
                    print("test is in dict")
            if iteration == 20:
                if "test" not in my_dict:
                    print("test is not anymore in dict")
    """

    def __init__(self, bot: BotAI, max_age_frames: int = 1) -> None:
        assert max_age_frames >= -1
        assert bot

        OrderedDict.__init__(self)
        self.bot: BotAI = bot
        self.max_age: int | float = max_age_frames
        self.lock: RLock = RLock()

    @property
    def frame(self) -> int:
        # pyre-ignore[16]
        return self.bot.state.game_loop

    def __contains__(self, key) -> bool:
        """Return True if dict has key, else False, e.g. 'key in dict'"""
        with self.lock:
            if OrderedDict.__contains__(self, key):
                # Each item is a list of [value, frame time]
                item = OrderedDict.__getitem__(self, key)
                if self.frame - item[1] < self.max_age:
                    return True
                del self[key]
        return False

    def __getitem__(self, key, with_age: bool = False) -> Any:
        """Return the item of the dict using d[key]"""
        with self.lock:
            # Each item is a list of [value, frame time]
            item = OrderedDict.__getitem__(self, key)
            if self.frame - item[1] < self.max_age:
                if with_age:
                    return item[0], item[1]
                return item[0]
            OrderedDict.__delitem__(self, key)
        raise KeyError(key)

    def __setitem__(self, key, value) -> None:
        """Set d[key] = value"""
        with self.lock:
            OrderedDict.__setitem__(self, key, (value, self.frame))

    def __repr__(self) -> str:
        """Printable version of the dict instead of getting memory adress"""
        print_list = []
        with self.lock:
            for key, value in OrderedDict.items(self):
                if self.frame - value[1] < self.max_age:
                    print_list.append(f"{repr(key)}: {repr(value)}")
        print_str = ", ".join(print_list)
        return f"ExpiringDict({print_str})"

    def __str__(self):
        return self.__repr__()

    def __iter__(self):
        """Override 'for key in dict:'"""
        with self.lock:
            return self.keys()

    # TODO find a way to improve len
    def __len__(self) -> int:
        """Override len method as key value pairs aren't instantly being deleted, but only on __get__(item).
        This function is slow because it has to check if each element is not expired yet."""
        with self.lock:
            count = 0
            for _ in self.values():
                count += 1
            return count

    def pop(self, key, default=None, with_age: bool = False):
        """Return the item and remove it"""
        with self.lock:
            if OrderedDict.__contains__(self, key):
                item = OrderedDict.__getitem__(self, key)
                if self.frame - item[1] < self.max_age:
                    del self[key]
                    if with_age:
                        return item[0], item[1]
                    return item[0]
                del self[key]
            if default is None:
                raise KeyError(key)
            if with_age:
                return default, self.frame
            return default

    def get(self, key, default=None, with_age: bool = False):
        """Return the value for key if key is in dict, else default"""
        with self.lock:
            if OrderedDict.__contains__(self, key):
                item = OrderedDict.__getitem__(self, key)
                if self.frame - item[1] < self.max_age:
                    if with_age:
                        return item[0], item[1]
                    return item[0]
            if default is None:
                raise KeyError(key)
            if with_age:
                return default, self.frame
            return None
        return None

    def update(self, other_dict: dict) -> None:
        with self.lock:
            for key, value in other_dict.items():
                self[key] = value

    def items(self) -> Iterable:
        """Return iterator of zipped list [keys, values]"""
        with self.lock:
            for key, value in OrderedDict.items(self):
                if self.frame - value[1] < self.max_age:
                    yield key, value[0]

    def keys(self) -> Iterable:
        """Return iterator of keys"""
        with self.lock:
            for key, value in OrderedDict.items(self):
                if self.frame - value[1] < self.max_age:
                    yield key

    def values(self) -> Iterable:
        """Return iterator of values"""
        with self.lock:
            for value in OrderedDict.values(self):
                if self.frame - value[1] < self.max_age:
                    yield value[0]
```

### File: `sc2/game_data.py`

```python
# pyre-ignore-all-errors[29]
from __future__ import annotations

from bisect import bisect_left
from contextlib import suppress
from dataclasses import dataclass
from functools import lru_cache

from sc2.data import Attribute, Race
from sc2.ids.ability_id import AbilityId
from sc2.ids.unit_typeid import UnitTypeId
from sc2.unit_command import UnitCommand

with suppress(ImportError):
    from sc2.dicts.unit_trained_from import UNIT_TRAINED_FROM

# Set of parts of names of abilities that have no cost
# E.g every ability that has 'Hold' in its name is free
FREE_ABILITIES = {"Lower", "Raise", "Land", "Lift", "Hold", "Harvest"}


class GameData:
    def __init__(self, data) -> None:
        """
        :param data:
        """
        ids = {a.value for a in AbilityId if a.value != 0}
        self.abilities: dict[int, AbilityData] = {
            a.ability_id: AbilityData(self, a) for a in data.abilities if a.ability_id in ids
        }
        self.units: dict[int, UnitTypeData] = {u.unit_id: UnitTypeData(self, u) for u in data.units if u.available}
        self.upgrades: dict[int, UpgradeData] = {u.upgrade_id: UpgradeData(self, u) for u in data.upgrades}
        # Cached UnitTypeIds so that conversion does not take long. This needs to be moved elsewhere if a new GameData object is created multiple times per game

    @lru_cache(maxsize=256)
    def calculate_ability_cost(self, ability: AbilityData | AbilityId | UnitCommand) -> Cost:
        if isinstance(ability, AbilityId):
            ability = self.abilities[ability.value]
        elif isinstance(ability, UnitCommand):
            ability = self.abilities[ability.ability.value]

        assert isinstance(ability, AbilityData), f"Ability is not of type 'AbilityData', but was {type(ability)}"

        for unit in self.units.values():
            if unit.creation_ability is None:
                continue

            if not AbilityData.id_exists(unit.creation_ability.id.value):
                continue

            # pyre-ignore[16]
            if unit.creation_ability.is_free_morph:
                continue

            if unit.creation_ability == ability:
                if unit.id == UnitTypeId.ZERGLING:
                    # HARD CODED: zerglings are generated in pairs
                    return Cost(unit.cost.minerals * 2, unit.cost.vespene * 2, unit.cost.time)
                if unit.id == UnitTypeId.BANELING:
                    # HARD CODED: banelings don't cost 50/25 as described in the API, but 25/25
                    return Cost(25, 25, unit.cost.time)
                # Correction for morphing units, e.g. orbital would return 550/0 instead of actual 150/0
                morph_cost = unit.morph_cost
                if morph_cost:  # can be None
                    return morph_cost
                # Correction for zerg structures without morph: Extractor would return 75 instead of actual 25
                return unit.cost_zerg_corrected

        for upgrade in self.upgrades.values():
            if upgrade.research_ability == ability:
                return upgrade.cost

        return Cost(0, 0)


class AbilityData:
    ability_ids: list[int] = [ability_id.value for ability_id in AbilityId][1:]  # sorted list

    @classmethod
    def id_exists(cls, ability_id):
        assert isinstance(ability_id, int), f"Wrong type: {ability_id} is not int"
        if ability_id == 0:
            return False
        i = bisect_left(cls.ability_ids, ability_id)  # quick binary search
        return i != len(cls.ability_ids) and cls.ability_ids[i] == ability_id

    def __init__(self, game_data, proto) -> None:
        self._game_data = game_data
        self._proto = proto

        # What happens if we comment this out? Should this not be commented out? What is its purpose?
        assert self.id != 0

    def __repr__(self) -> str:
        return f"AbilityData(name={self._proto.button_name})"

    @property
    def id(self) -> AbilityId:
        """Returns the generic remap ID. See sc2/dicts/generic_redirect_abilities.py"""
        if self._proto.remaps_to_ability_id:
            return AbilityId(self._proto.remaps_to_ability_id)
        return AbilityId(self._proto.ability_id)

    @property
    def exact_id(self) -> AbilityId:
        """Returns the exact ID of the ability"""
        return AbilityId(self._proto.ability_id)

    @property
    def link_name(self) -> str:
        """For Stimpack this returns 'BarracksTechLabResearch'"""
        return self._proto.link_name

    @property
    def button_name(self) -> str:
        """For Stimpack this returns 'Stimpack'"""
        return self._proto.button_name

    @property
    def friendly_name(self) -> str:
        """For Stimpack this returns 'Research Stimpack'"""
        return self._proto.friendly_name

    @property
    def is_free_morph(self) -> bool:
        return any(free in self._proto.link_name for free in FREE_ABILITIES)

    @property
    def cost(self) -> Cost:
        return self._game_data.calculate_ability_cost(self.id)


class UnitTypeData:
    def __init__(self, game_data: GameData, proto) -> None:
        """
        :param game_data:
        :param proto:
        """
        # The ability_id for lurkers is
        # LURKERASPECTMPFROMHYDRALISKBURROWED_LURKERMPFROMHYDRALISKBURROWED
        # instead of the correct MORPH_LURKER.
        if proto.unit_id == UnitTypeId.LURKERMP.value:
            proto.ability_id = AbilityId.MORPH_LURKER.value

        self._game_data = game_data
        self._proto = proto

    def __repr__(self) -> str:
        return f"UnitTypeData(name={self.name})"

    @property
    def id(self) -> UnitTypeId:
        return UnitTypeId(self._proto.unit_id)

    @property
    def name(self) -> str:
        return self._proto.name

    @property
    def creation_ability(self) -> AbilityData | None:
        if self._proto.ability_id == 0:
            return None
        if self._proto.ability_id not in self._game_data.abilities:
            return None
        return self._game_data.abilities[self._proto.ability_id]

    @property
    def footprint_radius(self) -> float | None:
        """See unit.py footprint_radius"""
        if self.creation_ability is None:
            return None
        return self.creation_ability._proto.footprint_radius

    @property
    # pyre-ignore[11]
    def attributes(self) -> list[Attribute]:
        return self._proto.attributes

    def has_attribute(self, attr) -> bool:
        # pyre-ignore[6]
        assert isinstance(attr, Attribute)
        return attr in self.attributes

    @property
    def has_minerals(self) -> bool:
        return self._proto.has_minerals

    @property
    def has_vespene(self) -> bool:
        return self._proto.has_vespene

    @property
    def cargo_size(self) -> int:
        """How much cargo this unit uses up in cargo_space"""
        return self._proto.cargo_size

    @property
    def tech_requirement(self) -> UnitTypeId | None:
        """Tech-building requirement of buildings - may work for units but unreliably"""
        if self._proto.tech_requirement == 0:
            return None
        if self._proto.tech_requirement not in self._game_data.units:
            return None
        return UnitTypeId(self._proto.tech_requirement)

    @property
    def tech_alias(self) -> list[UnitTypeId] | None:
        """Building tech equality, e.g. OrbitalCommand is the same as CommandCenter
        Building tech equality, e.g. Hive is the same as Lair and Hatchery
        For Hive, this returns [UnitTypeId.Hatchery, UnitTypeId.Lair]
        For SCV, this returns None"""
        return_list = [
            UnitTypeId(tech_alias) for tech_alias in self._proto.tech_alias if tech_alias in self._game_data.units
        ]
        return return_list if return_list else None

    @property
    def unit_alias(self) -> UnitTypeId | None:
        """Building type equality, e.g. FlyingOrbitalCommand is the same as OrbitalCommand"""
        if self._proto.unit_alias == 0:
            return None
        if self._proto.unit_alias not in self._game_data.units:
            return None
        """ For flying OrbitalCommand, this returns UnitTypeId.OrbitalCommand """
        return UnitTypeId(self._proto.unit_alias)

    @property
    # pyre-ignore[11]
    def race(self) -> Race:
        return Race(self._proto.race)

    @property
    def cost(self) -> Cost:
        return Cost(self._proto.mineral_cost, self._proto.vespene_cost, self._proto.build_time)

    @property
    def cost_zerg_corrected(self) -> Cost:
        """This returns 25 for extractor and 200 for spawning pool instead of 75 and 250 respectively"""
        # pyre-ignore[16]
        if self.race == Race.Zerg and Attribute.Structure.value in self.attributes:
            return Cost(self._proto.mineral_cost - 50, self._proto.vespene_cost, self._proto.build_time)
        return self.cost

    @property
    def morph_cost(self) -> Cost | None:
        """This returns 150 minerals for OrbitalCommand instead of 550"""
        # Morphing units
        supply_cost = self._proto.food_required
        if supply_cost > 0 and self.id in UNIT_TRAINED_FROM and len(UNIT_TRAINED_FROM[self.id]) == 1:
            producer: UnitTypeId
            for producer in UNIT_TRAINED_FROM[self.id]:
                producer_unit_data = self._game_data.units[producer.value]
                if 0 < producer_unit_data._proto.food_required <= supply_cost:
                    if producer == UnitTypeId.ZERGLING:
                        producer_cost = Cost(25, 0)
                    else:
                        producer_cost = self._game_data.calculate_ability_cost(producer_unit_data.creation_ability)
                    return Cost(
                        self._proto.mineral_cost - producer_cost.minerals,
                        self._proto.vespene_cost - producer_cost.vespene,
                        self._proto.build_time,
                    )
        # Fix for BARRACKSREACTOR which has tech alias [REACTOR] which has (0, 0) cost
        if self.tech_alias is None or self.tech_alias[0] in {UnitTypeId.TECHLAB, UnitTypeId.REACTOR}:
            return None
        # Morphing a HIVE would have HATCHERY and LAIR in the tech alias - now subtract HIVE cost from LAIR cost instead of from HATCHERY cost
        tech_alias_cost_minerals = max(
            self._game_data.units[tech_alias.value].cost.minerals for tech_alias in self.tech_alias
        )
        tech_alias_cost_vespene = max(
            self._game_data.units[tech_alias.value].cost.vespene
            # pyre-ignore[16]
            for tech_alias in self.tech_alias
        )
        return Cost(
            self._proto.mineral_cost - tech_alias_cost_minerals,
            self._proto.vespene_cost - tech_alias_cost_vespene,
            self._proto.build_time,
        )


class UpgradeData:
    def __init__(self, game_data: GameData, proto) -> None:
        """
        :param game_data:
        :param proto:
        """
        self._game_data = game_data
        self._proto = proto

    def __repr__(self) -> str:
        return f"UpgradeData({self.name} - research ability: {self.research_ability}, {self.cost})"

    @property
    def name(self) -> str:
        return self._proto.name

    @property
    def research_ability(self) -> AbilityData | None:
        if self._proto.ability_id == 0:
            return None
        if self._proto.ability_id not in self._game_data.abilities:
            return None
        return self._game_data.abilities[self._proto.ability_id]

    @property
    def cost(self) -> Cost:
        return Cost(self._proto.mineral_cost, self._proto.vespene_cost, self._proto.research_time)


@dataclass
class Cost:
    """
    The cost of an action, a structure, a unit or a research upgrade.
    The time is given in frames (22.4 frames per game second).
    """

    minerals: int
    vespene: int
    time: float | None = None

    def __repr__(self) -> str:
        return f"Cost({self.minerals}, {self.vespene})"

    def __eq__(self, other: Cost) -> bool:
        return self.minerals == other.minerals and self.vespene == other.vespene

    def __ne__(self, other: Cost) -> bool:
        return self.minerals != other.minerals or self.vespene != other.vespene

    def __bool__(self) -> bool:
        return self.minerals != 0 or self.vespene != 0

    def __add__(self, other: Cost) -> Cost:
        if not other:
            return self
        if not self:
            return other
        time = (self.time or 0) + (other.time or 0)
        return Cost(self.minerals + other.minerals, self.vespene + other.vespene, time=time)

    def __sub__(self, other: Cost) -> Cost:
        time = (self.time or 0) + (other.time or 0)
        return Cost(self.minerals - other.minerals, self.vespene - other.vespene, time=time)

    def __mul__(self, other: int) -> Cost:
        return Cost(self.minerals * other, self.vespene * other, time=self.time)

    def __rmul__(self, other: int) -> Cost:
        return Cost(self.minerals * other, self.vespene * other, time=self.time)
```

### File: `sc2/game_info.py`

```python
# pyre-ignore-all-errors[6, 11, 16, 58]
from __future__ import annotations

import heapq
from collections import deque
from collections.abc import Iterable
from dataclasses import dataclass
from functools import cached_property

import numpy as np

from sc2.pixel_map import PixelMap
from sc2.player import Player
from sc2.position import Point2, Rect, Size


@dataclass
class Ramp:
    points: frozenset[Point2]
    game_info: GameInfo

    @property
    def x_offset(self) -> float:
        # Tested by printing actual building locations vs calculated depot positions
        return 0.5

    @property
    def y_offset(self) -> float:
        # Tested by printing actual building locations vs calculated depot positions
        return 0.5

    @cached_property
    def _height_map(self):
        return self.game_info.terrain_height

    @cached_property
    def size(self) -> int:
        return len(self.points)

    def height_at(self, p: Point2) -> int:
        return self._height_map[p]

    @cached_property
    def upper(self) -> frozenset[Point2]:
        """Returns the upper points of a ramp."""
        current_max = -10000
        result = set()
        for p in self.points:
            height = self.height_at(p)
            if height > current_max:
                current_max = height
                result = {p}
            elif height == current_max:
                result.add(p)
        return frozenset(result)

    @cached_property
    def upper2_for_ramp_wall(self) -> frozenset[Point2]:
        """Returns the 2 upper ramp points of the main base ramp required for the supply depot and barracks placement properties used in this file."""
        # From bottom center, find 2 points that are furthest away (within the same ramp)
        return frozenset(heapq.nlargest(2, self.upper, key=lambda x: x.distance_to_point2(self.bottom_center)))

    @cached_property
    def top_center(self) -> Point2:
        length = len(self.upper)
        pos = Point2((sum(p.x for p in self.upper) / length, sum(p.y for p in self.upper) / length))
        return pos

    @cached_property
    def lower(self) -> frozenset[Point2]:
        current_min = 10000
        result = set()
        for p in self.points:
            height = self.height_at(p)
            if height < current_min:
                current_min = height
                result = {p}
            elif height == current_min:
                result.add(p)
        return frozenset(result)

    @cached_property
    def bottom_center(self) -> Point2:
        length = len(self.lower)
        pos = Point2((sum(p.x for p in self.lower) / length, sum(p.y for p in self.lower) / length))
        return pos

    @cached_property
    def barracks_in_middle(self) -> Point2 | None:
        """Barracks position in the middle of the 2 depots"""
        if len(self.upper) not in {2, 5}:
            return None
        if len(self.upper2_for_ramp_wall) == 2:
            points = set(self.upper2_for_ramp_wall)
            p1 = points.pop().offset((self.x_offset, self.y_offset))
            p2 = points.pop().offset((self.x_offset, self.y_offset))
            # Offset from top point to barracks center is (2, 1)
            intersects = p1.circle_intersection(p2, 5**0.5)
            any_lower_point = next(iter(self.lower))
            return max(intersects, key=lambda p: p.distance_to_point2(any_lower_point))

        raise Exception("Not implemented. Trying to access a ramp that has a wrong amount of upper points.")

    @cached_property
    def depot_in_middle(self) -> Point2 | None:
        """Depot in the middle of the 3 depots"""
        if len(self.upper) not in {2, 5}:
            return None
        if len(self.upper2_for_ramp_wall) == 2:
            points = set(self.upper2_for_ramp_wall)
            p1 = points.pop().offset((self.x_offset, self.y_offset))
            p2 = points.pop().offset((self.x_offset, self.y_offset))
            # Offset from top point to depot center is (1.5, 0.5)
            try:
                intersects = p1.circle_intersection(p2, 2.5**0.5)
            except AssertionError:
                # Returns None when no placement was found, this is the case on the map Honorgrounds LE with an exceptionally large main base ramp
                return None
            any_lower_point = next(iter(self.lower))
            return max(intersects, key=lambda p: p.distance_to_point2(any_lower_point))

        raise Exception("Not implemented. Trying to access a ramp that has a wrong amount of upper points.")

    @cached_property
    def corner_depots(self) -> frozenset[Point2]:
        """Finds the 2 depot positions on the outside"""
        if not self.upper2_for_ramp_wall:
            return frozenset()
        if len(self.upper2_for_ramp_wall) == 2:
            points = set(self.upper2_for_ramp_wall)
            p1 = points.pop().offset((self.x_offset, self.y_offset))
            p2 = points.pop().offset((self.x_offset, self.y_offset))
            center = p1.towards(p2, p1.distance_to_point2(p2) / 2)
            depot_position = self.depot_in_middle
            if depot_position is None:
                return frozenset()
            # Offset from middle depot to corner depots is (2, 1)
            intersects = center.circle_intersection(depot_position, 5**0.5)
            return intersects

        raise Exception("Not implemented. Trying to access a ramp that has a wrong amount of upper points.")

    @cached_property
    def barracks_can_fit_addon(self) -> bool:
        """Test if a barracks can fit an addon at natural ramp"""
        # https://i.imgur.com/4b2cXHZ.png
        if len(self.upper2_for_ramp_wall) == 2:
            return self.barracks_in_middle.x + 1 > max(self.corner_depots, key=lambda depot: depot.x).x

        raise Exception("Not implemented. Trying to access a ramp that has a wrong amount of upper points.")

    @cached_property
    def barracks_correct_placement(self) -> Point2 | None:
        """Corrected placement so that an addon can fit"""
        if self.barracks_in_middle is None:
            return None
        if len(self.upper2_for_ramp_wall) == 2:
            if self.barracks_can_fit_addon:
                return self.barracks_in_middle
            return self.barracks_in_middle.offset((-2, 0))

        raise Exception("Not implemented. Trying to access a ramp that has a wrong amount of upper points.")

    @cached_property
    def protoss_wall_pylon(self) -> Point2 | None:
        """
        Pylon position that powers the two wall buildings and the warpin position.
        """
        if len(self.upper) not in {2, 5}:
            return None
        if len(self.upper2_for_ramp_wall) != 2:
            raise Exception("Not implemented. Trying to access a ramp that has a wrong amount of upper points.")
        middle = self.depot_in_middle
        # direction up the ramp
        direction = self.barracks_in_middle.negative_offset(middle)
        # pyre-ignore[7]
        return middle + 6 * direction

    @cached_property
    def protoss_wall_buildings(self) -> frozenset[Point2]:
        """
        List of two positions for 3x3 buildings that form a wall with a spot for a one unit block.
        These buildings can be powered by a pylon on the protoss_wall_pylon position.
        """
        if len(self.upper) not in {2, 5}:
            return frozenset()
        if len(self.upper2_for_ramp_wall) == 2:
            middle = self.depot_in_middle
            # direction up the ramp
            direction = self.barracks_in_middle.negative_offset(middle)
            # sort depots based on distance to start to get wallin orientation
            sorted_depots = sorted(
                self.corner_depots, key=lambda depot: depot.distance_to(self.game_info.player_start_location)
            )
            wall1: Point2 = sorted_depots[1].offset(direction)
            wall2 = middle + direction + (middle - wall1) / 1.5
            return frozenset([wall1, wall2])

        raise Exception("Not implemented. Trying to access a ramp that has a wrong amount of upper points.")

    @cached_property
    def protoss_wall_warpin(self) -> Point2 | None:
        """
        Position for a unit to block the wall created by protoss_wall_buildings.
        Powered by protoss_wall_pylon.
        """
        if len(self.upper) not in {2, 5}:
            return None
        if len(self.upper2_for_ramp_wall) != 2:
            raise Exception("Not implemented. Trying to access a ramp that has a wrong amount of upper points.")
        middle = self.depot_in_middle
        # direction up the ramp
        direction = self.barracks_in_middle.negative_offset(middle)
        # sort depots based on distance to start to get wallin orientation
        sorted_depots = sorted(self.corner_depots, key=lambda x: x.distance_to(self.game_info.player_start_location))
        return sorted_depots[0].negative_offset(direction)


class GameInfo:
    def __init__(self, proto) -> None:
        self._proto = proto
        self.players: list[Player] = [Player.from_proto(p) for p in self._proto.player_info]
        self.map_name: str = self._proto.map_name
        self.local_map_path: str = self._proto.local_map_path
        # pyre-ignore[8]
        self.map_size: Size = Size.from_proto(self._proto.start_raw.map_size)

        # self.pathing_grid[point]: if 0, point is not pathable, if 1, point is pathable
        self.pathing_grid: PixelMap = PixelMap(self._proto.start_raw.pathing_grid, in_bits=True)
        # self.terrain_height[point]: returns the height in range of 0 to 255 at that point
        self.terrain_height: PixelMap = PixelMap(self._proto.start_raw.terrain_height)
        # self.placement_grid[point]: if 0, point is not placeable, if 1, point is pathable
        self.placement_grid: PixelMap = PixelMap(self._proto.start_raw.placement_grid, in_bits=True)
        self.playable_area = Rect.from_proto(self._proto.start_raw.playable_area)
        self.map_center = self.playable_area.center
        # pyre-ignore[8]
        self.map_ramps: list[Ramp] = None  # Filled later by BotAI._prepare_first_step
        # pyre-ignore[8]
        self.vision_blockers: frozenset[Point2] = None  # Filled later by BotAI._prepare_first_step
        self.player_races: dict[int, int] = {
            p.player_id: p.race_actual or p.race_requested for p in self._proto.player_info
        }
        self.start_locations: list[Point2] = [
            Point2.from_proto(sl).round(decimals=1) for sl in self._proto.start_raw.start_locations
        ]
        # pyre-ignore[8]
        self.player_start_location: Point2 = None  # Filled later by BotAI._prepare_first_step

    def _find_ramps_and_vision_blockers(self) -> tuple[list[Ramp], frozenset[Point2]]:
        """Calculate points that are pathable but not placeable.
        Then divide them into ramp points if not all points around the points are equal height
        and into vision blockers if they are."""

        def equal_height_around(tile):
            # mask to slice array 1 around tile
            sliced = self.terrain_height.data_numpy[tile[1] - 1 : tile[1] + 2, tile[0] - 1 : tile[0] + 2]
            return len(np.unique(sliced)) == 1

        map_area = self.playable_area
        # all points in the playable area that are pathable but not placable
        points = [
            Point2((a, b))
            for (b, a), value in np.ndenumerate(self.pathing_grid.data_numpy)
            if value == 1
            and map_area.x <= a < map_area.x + map_area.width
            and map_area.y <= b < map_area.y + map_area.height
            and self.placement_grid[(a, b)] == 0
        ]
        # divide points into ramp points and vision blockers
        ramp_points = [point for point in points if not equal_height_around(point)]
        vision_blockers = frozenset(point for point in points if equal_height_around(point))
        ramps = [Ramp(group, self) for group in self._find_groups(ramp_points)]
        return ramps, vision_blockers

    def _find_groups(self, points: frozenset[Point2], minimum_points_per_group: int = 8) -> Iterable[frozenset[Point2]]:
        """
        From a set of points, this function will try to group points together by
        painting clusters of points in a rectangular map using flood fill algorithm.
        Returns groups of points as list, like [{p1, p2, p3}, {p4, p5, p6, p7, p8}]
        """
        # TODO do we actually need colors here? the ramps will never touch anyways.
        NOT_COLORED_YET = -1
        map_width = self.pathing_grid.width
        map_height = self.pathing_grid.height
        current_color: int = NOT_COLORED_YET
        picture: list[list[int]] = [[-2 for _ in range(map_width)] for _ in range(map_height)]

        def paint(pt: Point2) -> None:
            picture[pt.y][pt.x] = current_color

        nearby: list[tuple[int, int]] = [(a, b) for a in [-1, 0, 1] for b in [-1, 0, 1] if a != 0 or b != 0]

        remaining: set[Point2] = set(points)
        for point in remaining:
            paint(point)
        current_color = 1
        queue: deque[Point2] = deque()
        while remaining:
            current_group: set[Point2] = set()
            if not queue:
                start = remaining.pop()
                paint(start)
                queue.append(start)
                current_group.add(start)
            while queue:
                base: Point2 = queue.popleft()
                for offset in nearby:
                    px, py = base.x + offset[0], base.y + offset[1]
                    # Do we ever reach out of map bounds?
                    if not (0 <= px < map_width and 0 <= py < map_height):
                        continue
                    if picture[py][px] != NOT_COLORED_YET:
                        continue
                    point: Point2 = Point2((px, py))
                    remaining.discard(point)
                    paint(point)
                    queue.append(point)
                    current_group.add(point)
            if len(current_group) >= minimum_points_per_group:
                yield frozenset(current_group)
```

### File: `sc2/game_state.py`

```python
# pyre-ignore-all-errors[11, 16]
from __future__ import annotations

from dataclasses import dataclass
from functools import cached_property
from itertools import chain

from loguru import logger

from sc2.constants import IS_ENEMY, IS_MINE, FakeEffectID, FakeEffectRadii
from sc2.data import Alliance, DisplayType
from sc2.ids.ability_id import AbilityId
from sc2.ids.effect_id import EffectId
from sc2.ids.upgrade_id import UpgradeId
from sc2.pixel_map import PixelMap
from sc2.position import Point2, Point3
from sc2.power_source import PsionicMatrix
from sc2.score import ScoreDetails

try:
    from sc2.dicts.generic_redirect_abilities import GENERIC_REDIRECT_ABILITIES
except ImportError:
    logger.info('Unable to import "GENERIC_REDIRECT_ABILITIES"')
    GENERIC_REDIRECT_ABILITIES = {}


class Blip:
    def __init__(self, proto) -> None:
        """
        :param proto:
        """
        self._proto = proto

    @property
    def is_blip(self) -> bool:
        """Detected by sensor tower."""
        return self._proto.is_blip

    @property
    def is_snapshot(self) -> bool:
        return self._proto.display_type == DisplayType.Snapshot.value

    @property
    def is_visible(self) -> bool:
        return self._proto.display_type == DisplayType.Visible.value

    @property
    def alliance(self) -> Alliance:
        return self._proto.alliance

    @property
    def is_mine(self) -> bool:
        return self._proto.alliance == Alliance.Self.value

    @property
    def is_enemy(self) -> bool:
        return self._proto.alliance == Alliance.Enemy.value

    @property
    def position(self) -> Point2:
        """2d position of the blip."""
        return Point2.from_proto(self._proto.pos)

    @property
    def position3d(self) -> Point3:
        """3d position of the blip."""
        return Point3.from_proto(self._proto.pos)


class Common:
    ATTRIBUTES = [
        "player_id",
        "minerals",
        "vespene",
        "food_cap",
        "food_used",
        "food_army",
        "food_workers",
        "idle_worker_count",
        "army_count",
        "warp_gate_count",
        "larva_count",
    ]

    def __init__(self, proto) -> None:
        self._proto = proto

    def __getattr__(self, attr) -> int:
        assert attr in self.ATTRIBUTES, f"'{attr}' is not a valid attribute"
        return int(getattr(self._proto, attr))


class EffectData:
    def __init__(self, proto, fake: bool = False) -> None:
        """
        :param proto:
        :param fake:
        """
        self._proto = proto
        self.fake = fake

    @property
    def id(self) -> EffectId | str:
        if self.fake:
            # Returns the string from constants.py, e.g. "KD8CHARGE"
            return FakeEffectID[self._proto.unit_type]
        return EffectId(self._proto.effect_id)

    @property
    def positions(self) -> set[Point2]:
        if self.fake:
            return {Point2.from_proto(self._proto.pos)}
        return {Point2.from_proto(p) for p in self._proto.pos}

    @property
    def alliance(self) -> Alliance:
        return self._proto.alliance

    @property
    def is_mine(self) -> bool:
        """Checks if the effect is caused by me."""
        return self._proto.alliance == IS_MINE

    @property
    def is_enemy(self) -> bool:
        """Checks if the effect is hostile."""
        return self._proto.alliance == IS_ENEMY

    @property
    def owner(self) -> int:
        return self._proto.owner

    @property
    def radius(self) -> float:
        if self.fake:
            return FakeEffectRadii[self._proto.unit_type]
        return self._proto.radius

    def __repr__(self) -> str:
        return f"{self.id} with radius {self.radius} at {self.positions}"


@dataclass
class ChatMessage:
    player_id: int
    message: str


@dataclass
class AbilityLookupTemplateClass:
    @property
    def exact_id(self) -> AbilityId:
        return AbilityId(self.ability_id)

    @property
    def generic_id(self) -> AbilityId:
        """
        See https://github.com/BurnySc2/python-sc2/blob/511c34f6b7ae51bd11e06ba91b6a9624dc04a0c0/sc2/dicts/generic_redirect_abilities.py#L13
        """
        return GENERIC_REDIRECT_ABILITIES.get(self.exact_id, self.exact_id)


@dataclass
class ActionRawUnitCommand(AbilityLookupTemplateClass):
    game_loop: int
    ability_id: int
    unit_tags: list[int]
    queue_command: bool
    target_world_space_pos: Point2 | None
    target_unit_tag: int | None = None


@dataclass
class ActionRawToggleAutocast(AbilityLookupTemplateClass):
    game_loop: int
    ability_id: int
    unit_tags: list[int]


@dataclass
class ActionRawCameraMove:
    center_world_space: Point2


@dataclass
class ActionError(AbilityLookupTemplateClass):
    ability_id: int
    unit_tag: int
    # See here for the codes of 'result': https://github.com/Blizzard/s2client-proto/blob/01ab351e21c786648e4c6693d4aad023a176d45c/s2clientprotocol/error.proto#L6
    result: int


class GameState:
    def __init__(self, response_observation, previous_observation=None) -> None:
        """
        :param response_observation:
        :param previous_observation:
        """
        # Only filled in realtime=True in case the bot skips frames
        self.previous_observation = previous_observation
        self.response_observation = response_observation

        # https://github.com/Blizzard/s2client-proto/blob/51662231c0965eba47d5183ed0a6336d5ae6b640/s2clientprotocol/sc2api.proto#L575
        self.observation = response_observation.observation
        self.observation_raw = self.observation.raw_data
        self.player_result = response_observation.player_result
        self.common: Common = Common(self.observation.player_common)

        # Area covered by Pylons and Warpprisms
        self.psionic_matrix: PsionicMatrix = PsionicMatrix.from_proto(self.observation_raw.player.power_sources)
        # 22.4 per second on faster game speed
        self.game_loop: int = self.observation.game_loop

        # https://github.com/Blizzard/s2client-proto/blob/33f0ecf615aa06ca845ffe4739ef3133f37265a9/s2clientprotocol/score.proto#L31
        self.score: ScoreDetails = ScoreDetails(self.observation.score)
        self.abilities = self.observation.abilities  # abilities of selected units
        self.upgrades: set[UpgradeId] = {UpgradeId(upgrade) for upgrade in self.observation_raw.player.upgrade_ids}

        # self.visibility[point]: 0=Hidden, 1=Fogged, 2=Visible
        self.visibility: PixelMap = PixelMap(self.observation_raw.map_state.visibility)
        # self.creep[point]: 0=No creep, 1=creep
        self.creep: PixelMap = PixelMap(self.observation_raw.map_state.creep, in_bits=True)

        # Effects like ravager bile shot, lurker attack, everything in effect_id.py
        self.effects: set[EffectData] = {EffectData(effect) for effect in self.observation_raw.effects}
        """ Usage:
        for effect in self.state.effects:
            if effect.id == EffectId.RAVAGERCORROSIVEBILECP:
                positions = effect.positions
                # dodge the ravager biles
        """

    @cached_property
    def dead_units(self) -> set[int]:
        """A set of unit tags that died this frame"""
        _dead_units = set(self.observation_raw.event.dead_units)
        if self.previous_observation:
            return _dead_units | set(self.previous_observation.observation.raw_data.event.dead_units)
        return _dead_units

    @cached_property
    def chat(self) -> list[ChatMessage]:
        """List of chat messages sent this frame (by either player)."""
        previous_frame_chat = self.previous_observation.chat if self.previous_observation else []
        return [
            ChatMessage(message.player_id, message.message)
            for message in chain(previous_frame_chat, self.response_observation.chat)
        ]

    @cached_property
    def alerts(self) -> list[int]:
        """
        Game alerts, see https://github.com/Blizzard/s2client-proto/blob/01ab351e21c786648e4c6693d4aad023a176d45c/s2clientprotocol/sc2api.proto#L683-L706
        """
        if self.previous_observation:
            return list(chain(self.previous_observation.observation.alerts, self.observation.alerts))
        return self.observation.alerts

    @cached_property
    def actions(self) -> list[ActionRawUnitCommand | ActionRawToggleAutocast | ActionRawCameraMove]:
        """
        List of successful actions since last frame.
        See https://github.com/Blizzard/s2client-proto/blob/01ab351e21c786648e4c6693d4aad023a176d45c/s2clientprotocol/sc2api.proto#L630-L637

        Each action is converted into Python dataclasses: ActionRawUnitCommand, ActionRawToggleAutocast, ActionRawCameraMove
        """
        previous_frame_actions = self.previous_observation.actions if self.previous_observation else []
        actions = []
        for action in chain(previous_frame_actions, self.response_observation.actions):
            action_raw = action.action_raw
            game_loop = action.game_loop
            if action_raw.HasField("unit_command"):
                # Unit commands
                raw_unit_command = action_raw.unit_command
                if raw_unit_command.HasField("target_world_space_pos"):
                    # Actions that have a point as target
                    actions.append(
                        ActionRawUnitCommand(
                            game_loop,
                            raw_unit_command.ability_id,
                            raw_unit_command.unit_tags,
                            raw_unit_command.queue_command,
                            Point2.from_proto(raw_unit_command.target_world_space_pos),
                        )
                    )
                else:
                    # Actions that have a unit as target
                    actions.append(
                        ActionRawUnitCommand(
                            game_loop,
                            raw_unit_command.ability_id,
                            raw_unit_command.unit_tags,
                            raw_unit_command.queue_command,
                            None,
                            raw_unit_command.target_unit_tag,
                        )
                    )
            elif action_raw.HasField("toggle_autocast"):
                # Toggle autocast actions
                raw_toggle_autocast_action = action_raw.toggle_autocast
                actions.append(
                    ActionRawToggleAutocast(
                        game_loop,
                        raw_toggle_autocast_action.ability_id,
                        raw_toggle_autocast_action.unit_tags,
                    )
                )
            else:
                # Camera move actions
                actions.append(ActionRawCameraMove(Point2.from_proto(action.action_raw.camera_move.center_world_space)))
        return actions

    @cached_property
    def actions_unit_commands(self) -> list[ActionRawUnitCommand]:
        """
        List of successful unit actions since last frame.
        See https://github.com/Blizzard/s2client-proto/blob/01ab351e21c786648e4c6693d4aad023a176d45c/s2clientprotocol/raw.proto#L185-L193
        """
        # pyre-ignore[7]
        return list(filter(lambda action: isinstance(action, ActionRawUnitCommand), self.actions))

    @cached_property
    def actions_toggle_autocast(self) -> list[ActionRawToggleAutocast]:
        """
        List of successful autocast toggle actions since last frame.
        See https://github.com/Blizzard/s2client-proto/blob/01ab351e21c786648e4c6693d4aad023a176d45c/s2clientprotocol/raw.proto#L199-L202
        """
        # pyre-ignore[7]
        return list(filter(lambda action: isinstance(action, ActionRawToggleAutocast), self.actions))

    @cached_property
    def action_errors(self) -> list[ActionError]:
        """
        List of erroneous actions since last frame.
        See https://github.com/Blizzard/s2client-proto/blob/01ab351e21c786648e4c6693d4aad023a176d45c/s2clientprotocol/sc2api.proto#L648-L652
        """
        previous_frame_errors = self.previous_observation.action_errors if self.previous_observation else []
        return [
            ActionError(error.ability_id, error.unit_tag, error.result)
            for error in chain(self.response_observation.action_errors, previous_frame_errors)
        ]
```

### File: `sc2/generate_ids.py`

```python
from __future__ import annotations

import importlib
import json
import platform
import sys
from pathlib import Path
from typing import Any

from loguru import logger

from sc2.game_data import GameData

try:
    from sc2.ids.id_version import ID_VERSION_STRING
except ImportError:
    ID_VERSION_STRING = "4.11.4.78285"


class IdGenerator:
    def __init__(
        self, game_data: GameData | None = None, game_version: str | None = None, verbose: bool = False
    ) -> None:
        self.game_data = game_data
        self.game_version = game_version
        self.verbose = verbose

        self.HEADER = f"""# pyre-ignore-all-errors[14]
from __future__ import annotations
# DO NOT EDIT!
# This file was automatically generated by "{Path(__file__).name}"
"""

        self.PF = platform.system()

        self.HOME_DIR = str(Path.home())
        self.DATA_JSON = {
            "Darwin": self.HOME_DIR + "/Library/Application Support/Blizzard/StarCraft II/stableid.json",
            "Windows": self.HOME_DIR + "/Documents/StarCraft II/stableid.json",
            "Linux": self.HOME_DIR + "/Documents/StarCraft II/stableid.json",
        }

        self.ENUM_TRANSLATE = {
            "Units": "UnitTypeId",
            "Abilities": "AbilityId",
            "Upgrades": "UpgradeId",
            "Buffs": "BuffId",
            "Effects": "EffectId",
        }

        self.FILE_TRANSLATE = {
            "Units": "unit_typeid",
            "Abilities": "ability_id",
            "Upgrades": "upgrade_id",
            "Buffs": "buff_id",
            "Effects": "effect_id",
        }

    @staticmethod
    def make_key(key: str) -> str:
        if key[0].isdigit():
            key = "_" + key
        # In patch 5.0, the key has "@" character in it which is not possible with python enums
        return key.upper().replace(" ", "_").replace("@", "")

    def parse_data(self, data) -> dict[str, Any]:
        # for d in data:  # Units, Abilities, Upgrades, Buffs, Effects

        units = self.parse_simple("Units", data)
        upgrades = self.parse_simple("Upgrades", data)
        effects = self.parse_simple("Effects", data)
        buffs = self.parse_simple("Buffs", data)

        abilities = {}
        for v in data["Abilities"]:
            key = v["buttonname"]
            remapid = v.get("remapid")

            if key == "" and v["index"] == 0:
                key = v["name"]

            if (not key) and (remapid is None):
                assert v["buttonname"] == ""
                continue

            if not key:
                if v["friendlyname"] != "":
                    key = v["friendlyname"]
                else:
                    sys.exit(f"Not mapped: {v!r}")

            key = key.upper().replace(" ", "_").replace("@", "")

            if "name" in v:
                key = f"{v['name'].upper().replace(' ', '_')}_{key}"

            if "friendlyname" in v:
                key = v["friendlyname"].upper().replace(" ", "_")

            if key[0].isdigit():
                key = "_" + key

            if key in abilities and v["index"] == 0:
                logger.info(f"{key} has value 0 and id {v['id']}, overwriting {key}: {abilities[key]}")
                # Commented out to try to fix: 3670 is not a valid AbilityId
                abilities[key] = v["id"]
            elif key in abilities:
                logger.info(f"{key} has appeared a second time with id={v['id']}")
            else:
                abilities[key] = v["id"]

        abilities["SMART"] = 1

        enums = {}
        enums["Units"] = units
        enums["Abilities"] = abilities
        enums["Upgrades"] = upgrades
        enums["Buffs"] = buffs
        enums["Effects"] = effects

        return enums

    def parse_simple(self, d, data):
        units = {}
        for v in data[d]:
            key = v["name"]

            if not key:
                continue
            key_to_insert = self.make_key(key)
            if key_to_insert in units:
                index = 2
                tmp = f"{key_to_insert}_{index}"
                while tmp in units:
                    index += 1
                    tmp = f"{key_to_insert}_{index}"
                key_to_insert = tmp
            units[key_to_insert] = v["id"]

        return units

    def generate_python_code(self, enums) -> None:
        assert {"Units", "Abilities", "Upgrades", "Buffs", "Effects"} <= enums.keys()

        sc2dir = Path(__file__).parent
        idsdir = sc2dir / "ids"
        idsdir.mkdir(exist_ok=True)

        with (idsdir / "__init__.py").open("w") as f:
            initstring = f"__all__ = {[n.lower() for n in self.FILE_TRANSLATE.values()]!r}\n".replace("'", '"')
            f.write("\n".join([self.HEADER, initstring]))

        for name, body in enums.items():
            class_name = self.ENUM_TRANSLATE[name]

            code = [self.HEADER, "import enum", "\n", f"class {class_name}(enum.Enum):"]

            for key, value in sorted(body.items(), key=lambda p: p[1]):
                code.append(f"    {key} = {value}")

            # Add repr function to more easily dump enums to dict
            code += f"""
    def __repr__(self) -> str:
        return f"{class_name}.{{self.name}}"
""".split("\n")

            # Add missing ids function to not make the game crash when unknown BuffId was detected
            if class_name == "BuffId":
                code += f"""
    @classmethod
    def _missing_(cls, value: int) -> {class_name}:
        return cls.NULL
""".split("\n")

            if class_name == "AbilityId":
                code += f"""
    @classmethod
    def _missing_(cls, value: int) -> {class_name}:
        return cls.NULL_NULL
""".split("\n")

            code += f"""
for item in {class_name}:
    globals()[item.name] = item
""".split("\n")

            ids_file_path = (idsdir / self.FILE_TRANSLATE[name]).with_suffix(".py")
            with ids_file_path.open("w") as f:
                f.write("\n".join(code))

        if self.game_version is not None:
            version_path = Path(__file__).parent / "ids" / "id_version.py"
            with Path(version_path).open("w") as f:
                f.write(f'ID_VERSION_STRING = "{self.game_version}"\n')

    def update_ids_from_stableid_json(self) -> None:
        if self.game_version is None or ID_VERSION_STRING is None or self.game_version != ID_VERSION_STRING:
            if self.verbose and self.game_version is not None and ID_VERSION_STRING is not None:
                logger.info(
                    f"Game version is different (Old: {self.game_version}, new: {ID_VERSION_STRING}. Updating ids to match game version"
                )
            stable_id_path = Path(self.DATA_JSON[self.PF])
            assert stable_id_path.is_file(), f'stable_id.json was not found at path "{stable_id_path}"'
            with stable_id_path.open(encoding="utf-8") as data_file:
                data = json.loads(data_file.read())
            self.generate_python_code(self.parse_data(data))

    @staticmethod
    def reimport_ids() -> None:
        # Reload the newly written "id" files
        # TODO This only re-imports modules, but if they haven't been imported, it will yield an error
        importlib.reload(sys.modules["sc2.ids.ability_id"])

        importlib.reload(sys.modules["sc2.ids.unit_typeid"])

        importlib.reload(sys.modules["sc2.ids.upgrade_id"])

        importlib.reload(sys.modules["sc2.ids.effect_id"])

        importlib.reload(sys.modules["sc2.ids.buff_id"])

        # importlib.reload(sys.modules["sc2.ids.id_version"])

        importlib.reload(sys.modules["sc2.constants"])


if __name__ == "__main__":
    updater = IdGenerator()
    updater.update_ids_from_stableid_json()
```

### File: `sc2/main.py`

```python
# pyre-ignore-all-errors[6, 11, 16, 21, 29]
from __future__ import annotations

import asyncio
import json
import platform
import signal
import sys
from contextlib import suppress
from dataclasses import dataclass
from io import BytesIO
from pathlib import Path

import mpyq
import portpicker
from aiohttp import ClientSession, ClientWebSocketResponse
from loguru import logger
from s2clientprotocol import sc2api_pb2 as sc_pb

from sc2.bot_ai import BotAI
from sc2.client import Client
from sc2.controller import Controller
from sc2.data import CreateGameError, Result, Status
from sc2.game_state import GameState
from sc2.maps import Map
from sc2.player import AbstractPlayer, Bot, BotProcess, Human
from sc2.portconfig import Portconfig
from sc2.protocol import ConnectionAlreadyClosedError, ProtocolError
from sc2.proxy import Proxy
from sc2.sc2process import KillSwitch, SC2Process

# Set the global logging level
logger.remove()
logger.add(sys.stdout, level="INFO")


@dataclass
class GameMatch:
    """Dataclass for hosting a match of SC2.
    This contains all of the needed information for RequestCreateGame.
    :param sc2_config: dicts of arguments to unpack into sc2process's construction, one per player
        second sc2_config will be ignored if only one sc2_instance is spawned
        e.g. sc2_args=[{"fullscreen": True}, {}]: only player 1's sc2instance will be fullscreen
    :param game_time_limit: The time (in seconds) until a match is artificially declared a Tie
    """

    map_sc2: Map
    players: list[AbstractPlayer]
    realtime: bool = False
    random_seed: int | None = None
    disable_fog: bool | None = None
    sc2_config: list[dict] | None = None
    game_time_limit: int | None = None

    def __post_init__(self) -> None:
        # avoid players sharing names
        if len(self.players) > 1 and self.players[0].name is not None and self.players[0].name == self.players[1].name:
            self.players[1].name += "2"

        if self.sc2_config is not None:
            if isinstance(self.sc2_config, dict):
                self.sc2_config = [self.sc2_config]
            if len(self.sc2_config) == 0:
                self.sc2_config = [{}]
            while len(self.sc2_config) < len(self.players):
                self.sc2_config += self.sc2_config
            self.sc2_config = self.sc2_config[: len(self.players)]

    @property
    def needed_sc2_count(self) -> int:
        return sum(player.needs_sc2 for player in self.players)

    @property
    def host_game_kwargs(self) -> dict:
        return {
            "map_settings": self.map_sc2,
            "players": self.players,
            "realtime": self.realtime,
            "random_seed": self.random_seed,
            "disable_fog": self.disable_fog,
        }

    def __repr__(self) -> str:
        p1 = self.players[0]
        p1 = p1.name if p1.name else p1
        p2 = self.players[1]
        p2 = p2.name if p2.name else p2
        return f"Map: {self.map_sc2.name}, {p1} vs {p2}, realtime={self.realtime}, seed={self.random_seed}"


async def _play_game_human(client, player_id, realtime, game_time_limit):
    while True:
        state = await client.observation()
        if client._game_result:
            return client._game_result[player_id]

        if game_time_limit and state.observation.observation.game_loop / 22.4 > game_time_limit:
            logger.info(state.observation.game_loop, state.observation.game_loop / 22.4)
            return Result.Tie

        if not realtime:
            await client.step()


async def _play_game_ai(
    client: Client, player_id: int, ai: BotAI, realtime: bool, game_time_limit: int | None
) -> Result:
    gs: GameState | None = None

    async def initialize_first_step() -> Result | None:
        nonlocal gs
        ai._initialize_variables()

        game_data = await client.get_game_data()
        game_info = await client.get_game_info()
        ping_response = await client.ping()

        # This game_data will become self.game_data in botAI
        ai._prepare_start(
            client, player_id, game_info, game_data, realtime=realtime, base_build=ping_response.ping.base_build
        )
        state = await client.observation()
        # check game result every time we get the observation
        if client._game_result:
            await ai.on_end(client._game_result[player_id])
            return client._game_result[player_id]
        gs = GameState(state.observation)
        proto_game_info = await client._execute(game_info=sc_pb.RequestGameInfo())
        try:
            ai._prepare_step(gs, proto_game_info)
            await ai.on_before_start()
            ai._prepare_first_step()
            await ai.on_start()
        # TODO Catching too general exception Exception (broad-except)

        except Exception as e:
            logger.exception(f"Caught unknown exception in AI on_start: {e}")
            logger.error("Resigning due to previous error")
            await ai.on_end(Result.Defeat)
            return Result.Defeat

    result = await initialize_first_step()
    if result is not None:
        return result

    async def run_bot_iteration(iteration: int):
        nonlocal gs
        logger.debug(f"Running AI step, it={iteration} {gs.game_loop / 22.4:.2f}s")
        # Issue event like unit created or unit destroyed
        await ai.issue_events()
        # In on_step various errors can occur - log properly
        try:
            await ai.on_step(iteration)
        except (AttributeError,) as e:
            logger.exception(f"Caught exception: {e}")
            raise
        except Exception as e:
            logger.exception(f"Caught unknown exception: {e}")
            raise
        await ai._after_step()
        logger.debug("Running AI step: done")

    # Only used in realtime=True
    previous_state_observation = None
    for iteration in range(10**10):
        if realtime and gs:
            # On realtime=True, might get an error here: sc2.protocol.ProtocolError: ['Not in a game']
            with suppress(ProtocolError):
                requested_step = gs.game_loop + client.game_step
                state = await client.observation(requested_step)
                # If the bot took too long in the previous observation, request another observation one frame after
                if state.observation.observation.game_loop > requested_step:
                    logger.debug("Skipped a step in realtime=True")
                    previous_state_observation = state.observation
                    state = await client.observation(state.observation.observation.game_loop + 1)
        else:
            state = await client.observation()

        # check game result every time we get the observation
        if client._game_result:
            await ai.on_end(client._game_result[player_id])
            return client._game_result[player_id]
        gs = GameState(state.observation, previous_state_observation)
        previous_state_observation = None
        logger.debug(f"Score: {gs.score.score}")

        if game_time_limit and gs.game_loop / 22.4 > game_time_limit:
            await ai.on_end(Result.Tie)
            return Result.Tie
        proto_game_info = await client._execute(game_info=sc_pb.RequestGameInfo())
        ai._prepare_step(gs, proto_game_info)

        await run_bot_iteration(iteration)  # Main bot loop

        if not realtime:
            if not client.in_game:  # Client left (resigned) the game
                await ai.on_end(client._game_result[player_id])
                return client._game_result[player_id]

            # TODO: In bot vs bot, if the other bot ends the game, this bot gets stuck in requesting an observation when using main.py:run_multiple_games
            await client.step()
    return Result.Undecided


async def _play_game(
    player: AbstractPlayer, client: Client, realtime, portconfig, game_time_limit=None, rgb_render_config=None
) -> Result:
    assert isinstance(realtime, bool), repr(realtime)

    player_id = await client.join_game(
        player.name, player.race, portconfig=portconfig, rgb_render_config=rgb_render_config
    )
    logger.info(f"Player {player_id} - {player.name if player.name else str(player)}")

    if isinstance(player, Human):
        result = await _play_game_human(client, player_id, realtime, game_time_limit)
    else:
        result = await _play_game_ai(client, player_id, player.ai, realtime, game_time_limit)

    logger.info(
        f"Result for player {player_id} - {player.name if player.name else str(player)}: "
        f"{result._name_ if isinstance(result, Result) else result}"
    )

    return result


async def _play_replay(client, ai, realtime: bool = False, player_id: int = 0):
    ai._initialize_variables()

    game_data = await client.get_game_data()
    game_info = await client.get_game_info()
    ping_response = await client.ping()

    client.game_step = 1
    # This game_data will become self._game_data in botAI
    ai._prepare_start(
        client, player_id, game_info, game_data, realtime=realtime, base_build=ping_response.ping.base_build
    )
    state = await client.observation()
    # Check game result every time we get the observation
    if client._game_result:
        await ai.on_end(client._game_result[player_id])
        return client._game_result[player_id]
    gs = GameState(state.observation)
    proto_game_info = await client._execute(game_info=sc_pb.RequestGameInfo())
    ai._prepare_step(gs, proto_game_info)
    ai._prepare_first_step()
    try:
        await ai.on_start()
    # TODO Catching too general exception Exception (broad-except)

    except Exception as e:
        logger.exception(f"Caught unknown exception in AI replay on_start: {e}")
        await ai.on_end(Result.Defeat)
        return Result.Defeat

    iteration = 0
    while True:
        if iteration != 0:
            if realtime:
                # TODO: check what happens if a bot takes too long to respond, so that the requested
                #  game_loop might already be in the past
                state = await client.observation(gs.game_loop + client.game_step)
            else:
                state = await client.observation()
            # check game result every time we get the observation
            if client._game_result:
                try:
                    await ai.on_end(client._game_result[player_id])
                except TypeError:
                    return client._game_result[player_id]
                return client._game_result[player_id]
            gs = GameState(state.observation)
            logger.debug(f"Score: {gs.score.score}")

            proto_game_info = await client._execute(game_info=sc_pb.RequestGameInfo())
            ai._prepare_step(gs, proto_game_info)

        logger.debug(f"Running AI step, it={iteration} {gs.game_loop * 0.725 * (1 / 16):.2f}s")

        try:
            # Issue event like unit created or unit destroyed
            await ai.issue_events()
            await ai.on_step(iteration)
            await ai._after_step()

        # TODO Catching too general exception Exception (broad-except)
        except Exception as e:
            if isinstance(e, ProtocolError) and e.is_game_over_error:
                if realtime:
                    return None
                await ai.on_end(Result.Victory)
                return None
            # NOTE: this message is caught by pytest suite
            logger.exception("AI step threw an error")  # DO NOT EDIT!
            logger.error(f"Error: {e}")
            logger.error("Resigning due to previous error")
            try:
                await ai.on_end(Result.Defeat)
            except TypeError:
                return Result.Defeat
            return Result.Defeat

        logger.debug("Running AI step: done")

        if not realtime and not client.in_game:  # Client left (resigned) the game
            await ai.on_end(Result.Victory)
            return Result.Victory

        await client.step()  # unindent one line to work in realtime

        iteration += 1


async def _setup_host_game(
    server: Controller, map_settings, players, realtime, random_seed=None, disable_fog=None, save_replay_as=None
):
    r = await server.create_game(map_settings, players, realtime, random_seed, disable_fog)
    if r.create_game.HasField("error"):
        err = f"Could not create game: {CreateGameError(r.create_game.error)}"
        if r.create_game.HasField("error_details"):
            err += f": {r.create_game.error_details}"
        logger.critical(err)
        raise RuntimeError(err)

    return Client(server._ws, save_replay_as)


async def _host_game(
    map_settings,
    players,
    realtime: bool = False,
    portconfig=None,
    save_replay_as=None,
    game_time_limit=None,
    rgb_render_config=None,
    random_seed=None,
    sc2_version=None,
    disable_fog=None,
):
    assert players, "Can't create a game without players"

    assert any((isinstance(p, (Human, Bot))) for p in players)

    async with SC2Process(
        fullscreen=players[0].fullscreen, render=rgb_render_config is not None, sc2_version=sc2_version
    ) as server:
        await server.ping()

        client = await _setup_host_game(
            server, map_settings, players, realtime, random_seed, disable_fog, save_replay_as
        )
        # Bot can decide if it wants to launch with 'raw_affects_selection=True'
        if not isinstance(players[0], Human) and getattr(players[0].ai, "raw_affects_selection", None) is not None:
            client.raw_affects_selection = players[0].ai.raw_affects_selection

        result = await _play_game(players[0], client, realtime, portconfig, game_time_limit, rgb_render_config)
        if client.save_replay_path is not None:
            await client.save_replay(client.save_replay_path)
        try:
            await client.leave()
        except ConnectionAlreadyClosedError:
            logger.error("Connection was closed before the game ended")
        await client.quit()

        return result


async def _host_game_aiter(
    map_settings,
    players,
    realtime,
    portconfig=None,
    save_replay_as=None,
    game_time_limit=None,
):
    assert players, "Can't create a game without players"

    assert any(isinstance(p, (Human, Bot)) for p in players)

    async with SC2Process() as server:
        while True:
            await server.ping()

            client = await _setup_host_game(server, map_settings, players, realtime)
            if not isinstance(players[0], Human) and getattr(players[0].ai, "raw_affects_selection", None) is not None:
                client.raw_affects_selection = players[0].ai.raw_affects_selection

            try:
                result = await _play_game(players[0], client, realtime, portconfig, game_time_limit)

                if save_replay_as is not None:
                    await client.save_replay(save_replay_as)
                await client.leave()
            except ConnectionAlreadyClosedError:
                logger.error("Connection was closed before the game ended")
                return

            new_players = yield result
            if new_players is not None:
                players = new_players


def _host_game_iter(*args, **kwargs):
    game = _host_game_aiter(*args, **kwargs)
    new_playerconfig = None
    while True:
        new_playerconfig = yield asyncio.get_event_loop().run_until_complete(game.asend(new_playerconfig))


async def _join_game(
    players,
    realtime,
    portconfig,
    save_replay_as=None,
    game_time_limit=None,
    sc2_version=None,
):
    async with SC2Process(fullscreen=players[1].fullscreen, sc2_version=sc2_version) as server:
        await server.ping()

        client = Client(server._ws)
        # Bot can decide if it wants to launch with 'raw_affects_selection=True'
        if not isinstance(players[1], Human) and getattr(players[1].ai, "raw_affects_selection", None) is not None:
            client.raw_affects_selection = players[1].ai.raw_affects_selection

        result = await _play_game(players[1], client, realtime, portconfig, game_time_limit)
        if save_replay_as is not None:
            await client.save_replay(save_replay_as)
        try:
            await client.leave()
        except ConnectionAlreadyClosedError:
            logger.error("Connection was closed before the game ended")
        await client.quit()

        return result


async def _setup_replay(server, replay_path, realtime, observed_id):
    await server.start_replay(replay_path, realtime, observed_id)
    return Client(server._ws)


async def _host_replay(replay_path, ai, realtime, _portconfig, base_build, data_version, observed_id):
    async with SC2Process(fullscreen=False, base_build=base_build, data_hash=data_version) as server:
        client = await _setup_replay(server, replay_path, realtime, observed_id)
        result = await _play_replay(client, ai, realtime)
        return result


def get_replay_version(replay_path: str | Path) -> tuple[str, str]:
    with Path(replay_path).open("rb") as f:
        replay_data = f.read()
        replay_io = BytesIO()
        replay_io.write(replay_data)
        replay_io.seek(0)
        archive = mpyq.MPQArchive(replay_io).extract()
        metadata = json.loads(archive[b"replay.gamemetadata.json"].decode("utf-8"))
        return metadata["BaseBuild"], metadata["DataVersion"]


# TODO Deprecate run_game function in favor of run_multiple_games
def run_game(map_settings, players, **kwargs) -> Result | list[Result | None]:
    """
    Returns a single Result enum if the game was against the built-in computer.
    Returns a list of two Result enums if the game was "Human vs Bot" or "Bot vs Bot".
    """
    if sum(isinstance(p, (Human, Bot)) for p in players) > 1:
        host_only_args = ["save_replay_as", "rgb_render_config", "random_seed", "disable_fog"]
        join_kwargs = {k: v for k, v in kwargs.items() if k not in host_only_args}

        portconfig = Portconfig()

        async def run_host_and_join():
            return await asyncio.gather(
                _host_game(map_settings, players, **kwargs, portconfig=portconfig),
                _join_game(players, **join_kwargs, portconfig=portconfig),
                return_exceptions=True,
            )

        result: list[Result] = asyncio.run(run_host_and_join())
        assert isinstance(result, list)
        assert all(isinstance(r, Result) for r in result)
    else:
        result: Result = asyncio.run(_host_game(map_settings, players, **kwargs))
        assert isinstance(result, Result)
    return result


def run_replay(ai, replay_path: Path | str, realtime: bool = False, observed_id: int = 0):
    portconfig = Portconfig()
    assert Path(replay_path).is_file(), f"Replay does not exist at the given path: {replay_path}"
    assert Path(replay_path).is_absolute(), (
        f'Replay path has to be an absolute path, e.g. "C:/replays/my_replay.SC2Replay" but given path was "{replay_path}"'
    )
    base_build, data_version = get_replay_version(replay_path)
    result = asyncio.get_event_loop().run_until_complete(
        _host_replay(replay_path, ai, realtime, portconfig, base_build, data_version, observed_id)
    )
    return result


async def play_from_websocket(
    ws_connection: str | ClientWebSocketResponse,
    player: AbstractPlayer,
    realtime: bool = False,
    portconfig: Portconfig | None = None,
    save_replay_as: str | None = None,
    game_time_limit: int | None = None,
    should_close: bool = True,
):
    """Use this to play when the match is handled externally e.g. for bot ladder games.
    Portconfig MUST be specified if not playing vs Computer.
    :param ws_connection: either a string("ws://{address}:{port}/sc2api") or a ClientWebSocketResponse object
    :param should_close: closes the connection if True. Use False if something else will reuse the connection

    e.g. ladder usage: play_from_websocket("ws://127.0.0.1:5162/sc2api", MyBot, False, portconfig=my_PC)
    """
    session = None
    try:
        if isinstance(ws_connection, str):
            session = ClientSession()
            ws_connection = await session.ws_connect(ws_connection, timeout=120)
            should_close = True
        client = Client(ws_connection)
        result = await _play_game(player, client, realtime, portconfig, game_time_limit=game_time_limit)
        if save_replay_as is not None:
            await client.save_replay(save_replay_as)
    except ConnectionAlreadyClosedError:
        logger.error("Connection was closed before the game ended")
        return None
    finally:
        if should_close:
            await ws_connection.close()
            if session:
                await session.close()

    return result


async def run_match(controllers: list[Controller], match: GameMatch, close_ws: bool = True):
    await _setup_host_game(controllers[0], **match.host_game_kwargs)

    # Setup portconfig beforehand, so all players use the same ports
    startport = None
    portconfig = None
    if match.needed_sc2_count > 1:
        if any(isinstance(player, BotProcess) for player in match.players):
            portconfig = Portconfig.contiguous_ports()
            # Most ladder bots generate their server and client ports as [s+2, s+3], [s+4, s+5]
            startport = portconfig.server[0] - 2
        else:
            portconfig = Portconfig()

    proxies = []
    coros = []
    players_that_need_sc2 = filter(lambda lambda_player: lambda_player.needs_sc2, match.players)
    for i, player in enumerate(players_that_need_sc2):
        if isinstance(player, BotProcess):
            pport = portpicker.pick_unused_port()
            p = Proxy(controllers[i], player, pport, match.game_time_limit, match.realtime)
            proxies.append(p)
            coros.append(p.play_with_proxy(startport))
        else:
            coros.append(
                play_from_websocket(
                    controllers[i]._ws,
                    player,
                    match.realtime,
                    portconfig,
                    should_close=close_ws,
                    game_time_limit=match.game_time_limit,
                )
            )

    async_results = await asyncio.gather(*coros, return_exceptions=True)

    if not isinstance(async_results, list):
        async_results = [async_results]
    for i, a in enumerate(async_results):
        if isinstance(a, Exception):
            logger.error(f"Exception[{a}] thrown by {[p for p in match.players if p.needs_sc2][i]}")

    return process_results(match.players, async_results)


def process_results(players: list[AbstractPlayer], async_results: list[Result]) -> dict[AbstractPlayer, Result]:
    opp_res = {Result.Victory: Result.Defeat, Result.Defeat: Result.Victory, Result.Tie: Result.Tie}
    result: dict[AbstractPlayer, Result] = {}
    i = 0
    for player in players:
        if player.needs_sc2:
            if sum(r == Result.Victory for r in async_results) <= 1:
                result[player] = async_results[i]
            else:
                result[player] = Result.Undecided
            i += 1
        else:  # computer
            other_result = async_results[0]
            result[player] = None
            if other_result in opp_res:
                result[player] = opp_res[other_result]

    return result


async def maintain_SCII_count(count: int, controllers: list[Controller], proc_args: list[dict] | None = None) -> None:
    """Modifies the given list of controllers to reflect the desired amount of SCII processes"""
    # kill unhealthy ones.
    if controllers:
        to_remove = []
        alive = await asyncio.wait_for(
            asyncio.gather(*(c.ping() for c in controllers if not c._ws.closed), return_exceptions=True), timeout=20
        )
        i = 0  # for alive
        for controller in controllers:
            if controller._ws.closed:
                if not controller._process._session.closed:
                    await controller._process._session.close()
                to_remove.append(controller)
            else:
                if not isinstance(alive[i], sc_pb.Response):
                    try:
                        await controller._process._close_connection()
                    finally:
                        to_remove.append(controller)
                i += 1
        for c in to_remove:
            c._process._clean(verbose=False)
            if c._process in KillSwitch._to_kill:
                KillSwitch._to_kill.remove(c._process)
            controllers.remove(c)

    # spawn more
    if len(controllers) < count:
        needed = count - len(controllers)
        if proc_args:
            index = len(controllers) % len(proc_args)
        else:
            proc_args = [{} for _ in range(needed)]
            index = 0
        extra = [SC2Process(**proc_args[(index + _) % len(proc_args)]) for _ in range(needed)]
        logger.info(f"Creating {needed} more SC2 Processes")
        for _ in range(3):
            if platform.system() == "Linux":
                # Works on linux: start one client after the other

                new_controllers = [await asyncio.wait_for(sc.__aenter__(), timeout=50) for sc in extra]
            else:
                # Doesnt seem to work on linux: starting 2 clients nearly at the same time
                new_controllers = await asyncio.wait_for(
                    asyncio.gather(*[sc.__aenter__() for sc in extra], return_exceptions=True),
                    timeout=50,
                )

            controllers.extend(c for c in new_controllers if isinstance(c, Controller))
            if len(controllers) == count:
                await asyncio.wait_for(asyncio.gather(*(c.ping() for c in controllers)), timeout=20)
                break
            extra = [
                extra[i] for i, result in enumerate(new_controllers) if not isinstance(new_controllers, Controller)
            ]
        else:
            logger.critical("Could not launch sufficient SC2")
            raise RuntimeError

    # kill excess
    while len(controllers) > count:
        proc = controllers.pop()
        proc = proc._process
        logger.info(f"Removing SCII listening to {proc._port}")
        await proc._close_connection()
        proc._clean(verbose=False)
        if proc in KillSwitch._to_kill:
            KillSwitch._to_kill.remove(proc)


def run_multiple_games(matches: list[GameMatch]):
    return asyncio.get_event_loop().run_until_complete(a_run_multiple_games(matches))


# TODO Catching too general exception Exception (broad-except)


async def a_run_multiple_games(matches: list[GameMatch]) -> list[dict[AbstractPlayer, Result]]:
    """Run multiple matches.
    Non-python bots are supported.
    When playing bot vs bot, this is less likely to fatally crash than repeating run_game()
    """
    if not matches:
        return []

    results = []
    controllers = []
    for m in matches:
        result = None
        dont_restart = m.needed_sc2_count == 2
        try:
            await maintain_SCII_count(m.needed_sc2_count, controllers, m.sc2_config)
            result = await run_match(controllers, m, close_ws=dont_restart)
        except SystemExit as e:
            logger.info(f"Game exit'ed as {e} during match {m}")
        except Exception as e:
            logger.exception(f"Caught unknown exception: {e}")
            logger.info(f"Exception {e} thrown in match {m}")
        finally:
            if dont_restart:  # Keeping them alive after a non-computer match can cause crashes
                await maintain_SCII_count(0, controllers, m.sc2_config)
            results.append(result)
    KillSwitch.kill_all()
    return results


# TODO Catching too general exception Exception (broad-except)


async def a_run_multiple_games_nokill(matches: list[GameMatch]) -> list[dict[AbstractPlayer, Result]]:
    """Run multiple matches while reusing SCII processes.
    Prone to crashes and stalls
    """
    # FIXME: check whether crashes between bot-vs-bot are avoidable or not
    if not matches:
        return []

    # Start the matches
    results = []
    controllers = []
    for m in matches:
        logger.info(f"Starting match {1 + len(results)} / {len(matches)}: {m}")
        result = None
        try:
            await maintain_SCII_count(m.needed_sc2_count, controllers, m.sc2_config)
            result = await run_match(controllers, m, close_ws=False)
        except SystemExit as e:
            logger.critical(f"Game sys.exit'ed as {e} during match {m}")
        except Exception as e:
            logger.exception(f"Caught unknown exception: {e}")
            logger.info(f"Exception {e} thrown in match {m}")
        finally:
            for c in controllers:
                try:
                    await c.ping()
                    if c._status != Status.launched:
                        await c._execute(leave_game=sc_pb.RequestLeaveGame())
                except Exception as e:
                    logger.exception(f"Caught unknown exception: {e}")
                    if not (isinstance(e, ProtocolError) and e.is_game_over_error):
                        logger.info(f"controller {c.__dict__} threw {e}")

            results.append(result)

    # Fire the killswitch manually, instead of letting the winning player fire it.
    await asyncio.wait_for(asyncio.gather(*(c._process._close_connection() for c in controllers)), timeout=50)
    KillSwitch.kill_all()
    signal.signal(signal.SIGINT, signal.SIG_DFL)

    return results
```

### File: `sc2/maps.py`

```python
from __future__ import annotations

from pathlib import Path

from loguru import logger

from sc2.paths import Paths


def get(name: str) -> Map:
    # Iterate through 2 folder depths
    for map_dir in (p for p in Paths.MAPS.iterdir()):
        if map_dir.is_dir():
            for map_file in (p for p in map_dir.iterdir()):
                if Map.matches_target_map_name(map_file, name):
                    return Map(map_file)
        elif Map.matches_target_map_name(map_dir, name):
            return Map(map_dir)

    raise KeyError(f"Map '{name}' was not found. Please put the map file in \"/StarCraft II/Maps/\".")


class Map:
    def __init__(self, path: Path) -> None:
        self.path = path

        if self.path.is_absolute():
            try:
                self.relative_path = self.path.relative_to(Paths.MAPS)
            except ValueError:  # path not relative to basedir
                logger.warning(f"Using absolute path: {self.path}")
                self.relative_path = self.path
        else:
            self.relative_path = self.path

    @property
    def name(self) -> str:
        return self.path.stem

    @property
    def data(self) -> bytes:
        with Path(self.path).open("rb") as f:
            return f.read()

    def __repr__(self) -> str:
        return f"Map({self.path})"

    @classmethod
    def is_map_file(cls, file: Path) -> bool:
        return file.is_file() and file.suffix == ".SC2Map"

    @classmethod
    def matches_target_map_name(cls, file: Path, name: str) -> bool:
        return cls.is_map_file(file) and file.stem == name
```

### File: `sc2/observer_ai.py`

```python
# pyre-ignore-all-errors[6, 11, 16]
"""
This class is very experimental and probably not up to date and needs to be refurbished.
If it works, you can watch replays with it.
"""

from __future__ import annotations

from sc2.bot_ai_internal import BotAIInternal
from sc2.data import Alert, Result
from sc2.ids.ability_id import AbilityId
from sc2.ids.upgrade_id import UpgradeId
from sc2.position import Point2
from sc2.unit import Unit
from sc2.units import Units


class ObserverAI(BotAIInternal):
    """Base class for bots."""

    @property
    def time(self) -> float:
        """Returns time in seconds, assumes the game is played on 'faster'"""
        return self.state.game_loop / 22.4  # / (1/1.4) * (1/16)

    @property
    def time_formatted(self) -> str:
        """Returns time as string in min:sec format"""
        t = self.time
        return f"{int(t // 60):02}:{int(t % 60):02}"

    def alert(self, alert_code: Alert) -> bool:
        """
        Check if alert is triggered in the current step.
        Possible alerts are listed here https://github.com/Blizzard/s2client-proto/blob/e38efed74c03bec90f74b330ea1adda9215e655f/s2clientprotocol/sc2api.proto#L679-L702

        Example use:

            from sc2.data import Alert
            if self.alert(Alert.AddOnComplete):
                print("Addon Complete")

        Alert codes::

            AlertError
            AddOnComplete
            BuildingComplete
            BuildingUnderAttack
            LarvaHatched
            MergeComplete
            MineralsExhausted
            MorphComplete
            MothershipComplete
            MULEExpired
            NuclearLaunchDetected
            NukeComplete
            NydusWormDetected
            ResearchComplete
            TrainError
            TrainUnitComplete
            TrainWorkerComplete
            TransformationComplete
            UnitUnderAttack
            UpgradeComplete
            VespeneExhausted
            WarpInComplete

        :param alert_code:
        """
        assert isinstance(alert_code, Alert), f"alert_code {alert_code} is no Alert"
        return alert_code.value in self.state.alerts

    @property
    def start_location(self) -> Point2:
        """
        Returns the spawn location of the bot, using the position of the first created townhall.
        This will be None if the bot is run on an arcade or custom map that does not feature townhalls at game start.
        """
        return self.game_info.player_start_location

    @property
    def enemy_start_locations(self) -> list[Point2]:
        """Possible start locations for enemies."""
        return self.game_info.start_locations

    async def get_available_abilities(
        self, units: list[Unit] | Units, ignore_resource_requirements: bool = False
    ) -> list[list[AbilityId]]:
        """Returns available abilities of one or more units. Right now only checks cooldown, energy cost, and whether the ability has been researched.

        Examples::

            units_abilities = await self.get_available_abilities(self.units)

        or::

            units_abilities = await self.get_available_abilities([self.units.random])

        :param units:
        :param ignore_resource_requirements:"""
        return await self.client.query_available_abilities(units, ignore_resource_requirements)

    async def on_unit_destroyed(self, unit_tag: int) -> None:
        """
        Override this in your bot class.
        This will event will be called when a unit (or structure, friendly or enemy) dies.
        For enemy units, this only works if the enemy unit was in vision on death.

        :param unit_tag:
        """

    async def on_unit_created(self, unit: Unit) -> None:
        """Override this in your bot class. This function is called when a unit is created.

        :param unit:"""

    async def on_building_construction_started(self, unit: Unit) -> None:
        """
        Override this in your bot class.
        This function is called when a building construction has started.

        :param unit:
        """

    async def on_building_construction_complete(self, unit: Unit) -> None:
        """
        Override this in your bot class. This function is called when a building
        construction is completed.

        :param unit:
        """

    async def on_upgrade_complete(self, upgrade: UpgradeId) -> None:
        """
        Override this in your bot class. This function is called with the upgrade id of an upgrade that was not finished last step and is now.

        :param upgrade:
        """

    async def on_start(self) -> None:
        """
        Override this in your bot class. This function is called after "on_start".
        At this point, game_data, game_info and the first iteration of game_state (self.state) are available.
        """

    async def on_step(self, iteration: int):
        """
        You need to implement this function!
        Override this in your bot class.
        This function is called on every game step (looped in realtime mode).

        :param iteration:
        """
        raise NotImplementedError

    async def on_end(self, game_result: Result) -> None:
        """Override this in your bot class. This function is called at the end of a game.

        :param game_result:"""
```

### File: `sc2/paths.py`

```python
from __future__ import annotations

import os
import platform
import re
import sys
from contextlib import suppress
from pathlib import Path

from loguru import logger

from sc2 import wsl

BASEDIR = {
    "Windows": "C:/Program Files (x86)/StarCraft II",
    "WSL1": "/mnt/c/Program Files (x86)/StarCraft II",
    "WSL2": "/mnt/c/Program Files (x86)/StarCraft II",
    "Darwin": "/Applications/StarCraft II",
    "Linux": "~/StarCraftII",
    "WineLinux": "~/.wine/drive_c/Program Files (x86)/StarCraft II",
}

USERPATH: dict[str, str | None] = {
    "Windows": "Documents\\StarCraft II\\ExecuteInfo.txt",
    "WSL1": "Documents/StarCraft II/ExecuteInfo.txt",
    "WSL2": "Documents/StarCraft II/ExecuteInfo.txt",
    "Darwin": "Library/Application Support/Blizzard/StarCraft II/ExecuteInfo.txt",
    "Linux": None,
    "WineLinux": None,
}

BINPATH = {
    "Windows": "SC2_x64.exe",
    "WSL1": "SC2_x64.exe",
    "WSL2": "SC2_x64.exe",
    "Darwin": "SC2.app/Contents/MacOS/SC2",
    "Linux": "SC2_x64",
    "WineLinux": "SC2_x64.exe",
}

CWD: dict[str, str | None] = {
    "Windows": "Support64",
    "WSL1": "Support64",
    "WSL2": "Support64",
    "Darwin": None,
    "Linux": None,
    "WineLinux": "Support64",
}


def platform_detect():
    pf = os.environ.get("SC2PF", platform.system())
    if pf == "Linux":
        return wsl.detect() or pf
    return pf


PF = platform_detect()


def get_home():
    """Get home directory of user, using Windows home directory for WSL."""
    if PF in {"WSL1", "WSL2"}:
        return wsl.get_wsl_home() or Path.home().expanduser()
    return Path.home().expanduser()


def get_user_sc2_install():
    """Attempts to find a user's SC2 install if their OS has ExecuteInfo.txt"""
    if USERPATH[PF]:
        einfo = str(get_home() / Path(USERPATH[PF]))
        if Path(einfo).is_file():
            with Path(einfo).open() as f:
                content = f.read()
            if content:
                base = re.search(r" = (.*)Versions", content).group(1)
                if PF in {"WSL1", "WSL2"}:
                    base = str(wsl.win_path_to_wsl_path(base))

                if Path(base).exists():
                    return base
    return None


def get_env() -> None:
    # TODO: Linux env conf from: https://github.com/deepmind/pysc2/blob/master/pysc2/run_configs/platforms.py
    return None


def get_runner_args(cwd):
    if "WINE" in os.environ:
        runner_file = Path(os.environ.get("WINE"))
        runner_file = runner_file if runner_file.is_file() else runner_file / "wine"
        """
        TODO Is converting linux path really necessary?
        That would convert
        '/home/burny/Games/battlenet/drive_c/Program Files (x86)/StarCraft II/Support64'
        to
        'Z:\\home\\burny\\Games\\battlenet\\drive_c\\Program Files (x86)\\StarCraft II\\Support64'
        """
        return [runner_file, "start", "/d", cwd, "/unix"]
    return []


def latest_executeble(versions_dir, base_build=None):
    latest = None

    if base_build is not None:
        with suppress(ValueError):
            latest = (
                int(base_build[4:]),
                max(p for p in versions_dir.iterdir() if p.is_dir() and p.name.startswith(str(base_build))),
            )

    if base_build is None or latest is None:
        latest = max((int(p.name[4:]), p) for p in versions_dir.iterdir() if p.is_dir() and p.name.startswith("Base"))

    version, path = latest

    if version < 55958:
        logger.critical("Your SC2 binary is too old. Upgrade to 3.16.1 or newer.")
        sys.exit(1)
    return path / BINPATH[PF]


class _MetaPaths(type):
    """ "Lazily loads paths to allow importing the library even if SC2 isn't installed."""

    def __setup(cls):
        if PF not in BASEDIR:
            logger.critical(f"Unsupported platform '{PF}'")
            sys.exit(1)

        try:
            base = os.environ.get("SC2PATH") or get_user_sc2_install() or BASEDIR[PF]
            cls.BASE = Path(base).expanduser()
            cls.EXECUTABLE = latest_executeble(cls.BASE / "Versions")
            cls.CWD = cls.BASE / CWD[PF] if CWD[PF] else None

            cls.REPLAYS = cls.BASE / "Replays"

            if (cls.BASE / "maps").exists():
                cls.MAPS = cls.BASE / "maps"
            else:
                cls.MAPS = cls.BASE / "Maps"
        except FileNotFoundError as e:
            logger.critical(f"SC2 installation not found: File '{e.filename}' does not exist.")
            sys.exit(1)

    def __getattr__(cls, attr):
        cls.__setup()
        return getattr(cls, attr)


class Paths(metaclass=_MetaPaths):
    """Paths for SC2 folders, lazily loaded using the above metaclass."""
```

### File: `sc2/pixel_map.py`

```python
from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

import numpy as np

from sc2.position import Point2


class PixelMap:
    def __init__(self, proto, in_bits: bool = False) -> None:
        """
        :param proto:
        :param in_bits:
        """
        self._proto = proto
        # Used for copying pixelmaps
        self._in_bits: bool = in_bits

        assert self.width * self.height == (8 if in_bits else 1) * len(self._proto.data), (
            f"{self.width * self.height} {(8 if in_bits else 1) * len(self._proto.data)}"
        )
        buffer_data = np.frombuffer(self._proto.data, dtype=np.uint8)
        if in_bits:
            buffer_data = np.unpackbits(buffer_data)
        self.data_numpy = buffer_data.reshape(self._proto.size.y, self._proto.size.x)

    @property
    def width(self) -> int:
        return self._proto.size.x

    @property
    def height(self) -> int:
        return self._proto.size.y

    @property
    def bits_per_pixel(self) -> int:
        return self._proto.bits_per_pixel

    @property
    def bytes_per_pixel(self) -> int:
        return self._proto.bits_per_pixel // 8

    def __getitem__(self, pos: tuple[int, int]) -> int:
        """Example usage: is_pathable = self._game_info.pathing_grid[Point2((20, 20))] != 0"""
        assert 0 <= pos[0] < self.width, f"x is {pos[0]}, self.width is {self.width}"
        assert 0 <= pos[1] < self.height, f"y is {pos[1]}, self.height is {self.height}"
        return int(self.data_numpy[pos[1], pos[0]])

    def __setitem__(self, pos: tuple[int, int], value: int) -> None:
        """Example usage: self._game_info.pathing_grid[Point2((20, 20))] = 255"""
        assert 0 <= pos[0] < self.width, f"x is {pos[0]}, self.width is {self.width}"
        assert 0 <= pos[1] < self.height, f"y is {pos[1]}, self.height is {self.height}"
        assert 0 <= value <= 254 * self._in_bits + 1, (
            f"value is {value}, it should be between 0 and {254 * self._in_bits + 1}"
        )
        assert isinstance(value, int), f"value is of type {type(value)}, it should be an integer"
        self.data_numpy[pos[1], pos[0]] = value

    def is_set(self, p: tuple[int, int]) -> bool:
        return self[p] != 0

    def is_empty(self, p: tuple[int, int]) -> bool:
        return not self.is_set(p)

    def copy(self) -> PixelMap:
        return PixelMap(self._proto, in_bits=self._in_bits)

    def flood_fill(self, start_point: Point2, pred: Callable[[int], bool]) -> set[Point2]:
        nodes: set[Point2] = set()
        queue: list[Point2] = [start_point]

        while queue:
            x, y = queue.pop()

            if not (0 <= x < self.width and 0 <= y < self.height):
                continue

            if Point2((x, y)) in nodes:
                continue

            if pred(self[x, y]):
                nodes.add(Point2((x, y)))
                queue += [Point2((x + a, y + b)) for a in [-1, 0, 1] for b in [-1, 0, 1] if not (a == 0 and b == 0)]
        return nodes

    def flood_fill_all(self, pred: Callable[[int], bool]) -> set[frozenset[Point2]]:
        groups: set[frozenset[Point2]] = set()

        for x in range(self.width):
            for y in range(self.height):
                if any((x, y) in g for g in groups):
                    continue

                if pred(self[x, y]):
                    groups.add(frozenset(self.flood_fill(Point2((x, y)), pred)))

        return groups

    def print(self, wide: bool = False) -> None:
        for y in range(self.height):
            for x in range(self.width):
                print("#" if self.is_set((x, y)) else " ", end=(" " if wide else ""))
            print("")

    def save_image(self, filename: str | Path) -> None:
        data = [(0, 0, self[x, y]) for y in range(self.height) for x in range(self.width)]

        from PIL import Image

        im = Image.new("RGB", (self.width, self.height))
        im.putdata(data)
        im.save(filename)

    def plot(self) -> None:
        import matplotlib.pyplot as plt

        plt.imshow(self.data_numpy, origin="lower")
        plt.show()
```

### File: `sc2/player.py`

```python
# pyre-ignore-all-errors[6, 11, 16, 29]
from __future__ import annotations

from abc import ABC
from pathlib import Path

from sc2.bot_ai import BotAI
from sc2.data import AIBuild, Difficulty, PlayerType, Race


class AbstractPlayer(ABC):
    def __init__(
        self,
        p_type: PlayerType,
        race: Race = None,
        name: str | None = None,
        difficulty=None,
        ai_build=None,
        fullscreen: bool = False,
    ) -> None:
        assert isinstance(p_type, PlayerType), f"p_type is of type {type(p_type)}"
        assert name is None or isinstance(name, str), f"name is of type {type(name)}"

        self.name = name
        self.type = p_type
        self.fullscreen = fullscreen
        if race is not None:
            self.race = race
        if p_type == PlayerType.Computer:
            assert isinstance(difficulty, Difficulty), f"difficulty is of type {type(difficulty)}"
            # Workaround, proto information does not carry ai_build info
            # We cant set that in the Player classmethod
            assert ai_build is None or isinstance(ai_build, AIBuild), f"ai_build is of type {type(ai_build)}"
            self.difficulty = difficulty
            self.ai_build = ai_build

        elif p_type == PlayerType.Observer:
            assert race is None
            assert difficulty is None
            assert ai_build is None

        else:
            assert isinstance(race, Race), f"race is of type {type(race)}"
            assert difficulty is None
            assert ai_build is None

    @property
    def needs_sc2(self) -> bool:
        return not isinstance(self, Computer)


class Human(AbstractPlayer):
    def __init__(self, race, name: str | None = None, fullscreen: bool = False) -> None:
        super().__init__(PlayerType.Participant, race, name=name, fullscreen=fullscreen)

    def __str__(self) -> str:
        if self.name is not None:
            return f"Human({self.race._name_}, name={self.name!r})"
        return f"Human({self.race._name_})"


class Bot(AbstractPlayer):
    def __init__(self, race, ai, name: str | None = None, fullscreen: bool = False) -> None:
        """
        AI can be None if this player object is just used to inform the
        server about player types.
        """
        assert isinstance(ai, BotAI) or ai is None, f"ai is of type {type(ai)}, inherit BotAI from bot_ai.py"
        super().__init__(PlayerType.Participant, race, name=name, fullscreen=fullscreen)
        self.ai = ai

    def __str__(self) -> str:
        if self.name is not None:
            return f"Bot {self.ai.__class__.__name__}({self.race._name_}), name={self.name!r})"
        return f"Bot {self.ai.__class__.__name__}({self.race._name_})"


class Computer(AbstractPlayer):
    def __init__(self, race, difficulty=Difficulty.Easy, ai_build=AIBuild.RandomBuild) -> None:
        super().__init__(PlayerType.Computer, race, difficulty=difficulty, ai_build=ai_build)

    def __str__(self) -> str:
        return f"Computer {self.difficulty._name_}({self.race._name_}, {self.ai_build.name})"


class Observer(AbstractPlayer):
    def __init__(self) -> None:
        super().__init__(PlayerType.Observer)

    def __str__(self) -> str:
        return "Observer"


class Player(AbstractPlayer):
    def __init__(
        self,
        player_id: int,
        p_type,
        requested_race,
        difficulty=None,
        actual_race=None,
        name: str | None = None,
        ai_build=None,
    ) -> None:
        super().__init__(p_type, requested_race, difficulty=difficulty, name=name, ai_build=ai_build)
        self.id: int = player_id
        self.actual_race: Race = actual_race

    @classmethod
    def from_proto(cls, proto) -> Player:
        if PlayerType(proto.type) == PlayerType.Observer:
            return cls(proto.player_id, PlayerType(proto.type), None, None, None)
        return cls(
            proto.player_id,
            PlayerType(proto.type),
            Race(proto.race_requested),
            Difficulty(proto.difficulty) if proto.HasField("difficulty") else None,
            Race(proto.race_actual) if proto.HasField("race_actual") else None,
            proto.player_name if proto.HasField("player_name") else None,
        )


class BotProcess(AbstractPlayer):
    """
    Class for handling bots launched externally, including non-python bots.
    Default parameters comply with sc2ai and aiarena ladders.

    :param path: the executable file's path
    :param launch_list: list of strings that launches the bot e.g. ["python", "run.py"] or ["run.exe"]
    :param race: bot's race
    :param name: bot's name
    :param sc2port_arg: the accepted argument name for the port of the sc2 instance to listen to
    :param hostaddress_arg: the accepted argument name for the address of the sc2 instance to listen to
    :param match_arg: the accepted argument name for the starting port to generate a portconfig from
    :param realtime_arg: the accepted argument name for specifying realtime
    :param other_args: anything else that is needed

    e.g. to call a bot capable of running on the bot ladders:
        BotProcess(os.getcwd(), "python run.py", Race.Terran, "INnoVation")
    """

    def __init__(
        self,
        path: str | Path,
        launch_list: list[str],
        race: Race,
        name: str | None = None,
        sc2port_arg: str = "--GamePort",
        hostaddress_arg: str = "--LadderServer",
        match_arg: str = "--StartPort",
        realtime_arg: str = "--RealTime",
        other_args: str | None = None,
        stdout: str | None = None,
    ) -> None:
        super().__init__(PlayerType.Participant, race, name=name)
        assert Path(path).exists()
        self.path = path
        self.launch_list = launch_list
        self.sc2port_arg = sc2port_arg
        self.match_arg = match_arg
        self.hostaddress_arg = hostaddress_arg
        self.realtime_arg = realtime_arg
        self.other_args = other_args
        self.stdout = stdout

    def __repr__(self) -> str:
        if self.name is not None:
            return f"Bot {self.name}({self.race.name} from {self.launch_list})"
        return f"Bot({self.race.name} from {self.launch_list})"

    def cmd_line(self, sc2port: int | str, matchport: int | str, hostaddress: str, realtime: bool = False) -> list[str]:
        """

        :param sc2port: the port that the launched sc2 instance listens to
        :param matchport: some starting port that both bots use to generate identical portconfigs.
                Note: This will not be sent if playing vs computer
        :param hostaddress: the address the sc2 instances used
        :param realtime: 1 or 0, indicating whether the match is played in realtime or not
        :return: string that will be used to start the bot's process
        """
        cmd_line = [
            *self.launch_list,
            self.sc2port_arg,
            str(sc2port),
            self.hostaddress_arg,
            hostaddress,
        ]
        if matchport is not None:
            cmd_line.extend([self.match_arg, str(matchport)])
        if self.other_args is not None:
            cmd_line.append(self.other_args)
        if realtime:
            cmd_line.extend([self.realtime_arg])
        return cmd_line
```

### File: `sc2/portconfig.py`

```python
from __future__ import annotations

import json

# pyre-fixme[21]
import portpicker


class Portconfig:
    """
    A data class for ports used by participants to join a match.

    EVERY participant joining the match must send the same sets of ports to join successfully.
    SC2 needs 2 ports per connection (one for data, one as a 'header'), which is why the ports come in pairs.

    :param guests: number of non-hosting participants in a match (i.e. 1 less than the number of participants)
    :param server_ports: [int portA, int portB]
    :param player_ports: [[int port1A, int port1B], [int port2A, int port2B], ... ]

    .shared is deprecated, and should TODO be removed soon (once ladderbots' __init__.py doesnt specify them).

    .server contains the pair of ports used by the participant 'hosting' the match

    .players contains a pair of ports for every 'guest' (non-hosting participants) in the match
    E.g. for 1v1, there will be only 1 guest. For 2v2 (coming soonTM), there would be 3 guests.
    """

    def __init__(self, guests: int = 1, server_ports=None, player_ports=None) -> None:
        self.shared = None
        self._picked_ports = []
        if server_ports:
            self.server = server_ports
        else:
            self.server = [portpicker.pick_unused_port() for _ in range(2)]
            self._picked_ports.extend(self.server)
        if player_ports:
            self.players = player_ports
        else:
            self.players = [[portpicker.pick_unused_port() for _ in range(2)] for _ in range(guests)]
            self._picked_ports.extend(port for player in self.players for port in player)

    def clean(self) -> None:
        while self._picked_ports:
            portpicker.return_port(self._picked_ports.pop())

    def __str__(self) -> str:
        return f"Portconfig(shared={self.shared}, server={self.server}, players={self.players})"

    @property
    def as_json(self) -> str:
        return json.dumps({"shared": self.shared, "server": self.server, "players": self.players})

    @classmethod
    def contiguous_ports(cls, guests: int = 1, attempts: int = 40) -> Portconfig:
        """Returns a Portconfig with adjacent ports"""
        for _ in range(attempts):
            start = portpicker.pick_unused_port()
            others = [start + j for j in range(1, 2 + guests * 2)]
            if all(portpicker.is_port_free(p) for p in others):
                server_ports = [start, others.pop(0)]
                player_ports = []
                while others:
                    player_ports.append([others.pop(0), others.pop(0)])
                pc = cls(server_ports=server_ports, player_ports=player_ports)
                pc._picked_ports.append(start)
                return pc
        raise portpicker.NoFreePortFoundError()

    @classmethod
    def from_json(cls, json_data: bytearray | bytes | str) -> Portconfig:
        data = json.loads(json_data)
        return cls(server_ports=data["server"], player_ports=data["players"])
```

### File: `sc2/position.py`

```python
# pyre-ignore-all-errors[6, 14, 15, 58]
from __future__ import annotations

import itertools
import math
import random
from collections.abc import Iterable
from typing import TYPE_CHECKING, SupportsFloat, SupportsIndex

# pyre-fixme[21]
from s2clientprotocol import common_pb2 as common_pb

if TYPE_CHECKING:
    from sc2.unit import Unit
    from sc2.units import Units

EPSILON: float = 10**-8


def _sign(num: SupportsFloat | SupportsIndex) -> float:
    return math.copysign(1, num)


class Pointlike(tuple):
    @property
    def position(self) -> Pointlike:
        return self

    def distance_to(self, target: Unit | Point2) -> float:
        """Calculate a single distance from a point or unit to another point or unit

        :param target:"""
        p = target.position
        return math.hypot(self[0] - p[0], self[1] - p[1])

    def distance_to_point2(self, p: Point2 | tuple[float, float]) -> float:
        """Same as the function above, but should be a bit faster because of the dropped asserts
        and conversion.

        :param p:"""
        return math.hypot(self[0] - p[0], self[1] - p[1])

    def _distance_squared(self, p2: Point2) -> float:
        """Function used to not take the square root as the distances will stay proportionally the same.
        This is to speed up the sorting process.

        :param p2:"""
        return (self[0] - p2[0]) ** 2 + (self[1] - p2[1]) ** 2

    def sort_by_distance(self, ps: Units | Iterable[Point2]) -> list[Point2]:
        """This returns the target points sorted as list.
        You should not pass a set or dict since those are not sortable.
        If you want to sort your units towards a point, use 'units.sorted_by_distance_to(point)' instead.

        :param ps:"""
        return sorted(ps, key=lambda p: self.distance_to_point2(p.position))

    def closest(self, ps: Units | Iterable[Point2]) -> Unit | Point2:
        """This function assumes the 2d distance is meant

        :param ps:"""
        assert ps, "ps is empty"

        return min(ps, key=lambda p: self.distance_to(p))

    def distance_to_closest(self, ps: Units | Iterable[Point2]) -> float:
        """This function assumes the 2d distance is meant
        :param ps:"""
        assert ps, "ps is empty"
        closest_distance = math.inf
        for p2 in ps:
            p2 = p2.position
            distance = self.distance_to(p2)
            if distance <= closest_distance:
                closest_distance = distance
        return closest_distance

    def furthest(self, ps: Units | Iterable[Point2]) -> Unit | Pointlike:
        """This function assumes the 2d distance is meant

        :param ps: Units object, or iterable of Unit or Point2"""
        assert ps, "ps is empty"

        return max(ps, key=lambda p: self.distance_to(p))

    def distance_to_furthest(self, ps: Units | Iterable[Point2]) -> float:
        """This function assumes the 2d distance is meant

        :param ps:"""
        assert ps, "ps is empty"
        furthest_distance = -math.inf
        for p2 in ps:
            p2 = p2.position
            distance = self.distance_to(p2)
            if distance >= furthest_distance:
                furthest_distance = distance
        return furthest_distance

    def offset(self, p) -> Pointlike:
        """

        :param p:
        """
        return self.__class__(a + b for a, b in itertools.zip_longest(self, p[: len(self)], fillvalue=0))

    def unit_axes_towards(self, p) -> Pointlike:
        """

        :param p:
        """
        return self.__class__(_sign(b - a) for a, b in itertools.zip_longest(self, p[: len(self)], fillvalue=0))

    def towards(self, p: Unit | Pointlike, distance: int | float = 1, limit: bool = False) -> Pointlike:
        """

        :param p:
        :param distance:
        :param limit:
        """
        p = p.position
        # assert self != p, f"self is {self}, p is {p}"
        # TODO test and fix this if statement
        if self == p:
            return self
        # end of test
        d = self.distance_to(p)
        if limit:
            distance = min(d, distance)
        return self.__class__(
            a + (b - a) / d * distance for a, b in itertools.zip_longest(self, p[: len(self)], fillvalue=0)
        )

    def __eq__(self, other: object) -> bool:
        try:
            return all(abs(a - b) <= EPSILON for a, b in itertools.zip_longest(self, other, fillvalue=0))
        except TypeError:
            return False

    def __hash__(self) -> int:
        return hash(tuple(self))


class Point2(Pointlike):
    @classmethod
    def from_proto(cls, data) -> Point2:
        """
        :param data:
        """
        return cls((data.x, data.y))

    @property
    # pyre-fixme[11]
    def as_Point2D(self) -> common_pb.Point2D:
        return common_pb.Point2D(x=self.x, y=self.y)

    @property
    # pyre-fixme[11]
    def as_PointI(self) -> common_pb.PointI:
        """Represents points on the minimap. Values must be between 0 and 64."""
        return common_pb.PointI(x=self.x, y=self.y)

    @property
    def rounded(self) -> Point2:
        return Point2((math.floor(self[0]), math.floor(self[1])))

    @property
    def length(self) -> float:
        """This property exists in case Point2 is used as a vector."""
        return math.hypot(self[0], self[1])

    @property
    def normalized(self) -> Point2:
        """This property exists in case Point2 is used as a vector."""
        length = self.length
        # Cannot normalize if length is zero
        assert length
        return self.__class__((self[0] / length, self[1] / length))

    @property
    def x(self) -> float:
        return self[0]

    @property
    def y(self) -> float:
        return self[1]

    @property
    def to2(self) -> Point2:
        return Point2(self[:2])

    @property
    def to3(self) -> Point3:
        return Point3((*self, 0))

    def round(self, decimals: int) -> Point2:
        """Rounds each number in the tuple to the amount of given decimals."""
        return Point2((round(self[0], decimals), round(self[1], decimals)))

    def offset(self, p: Point2) -> Point2:
        return Point2((self[0] + p[0], self[1] + p[1]))

    def random_on_distance(self, distance) -> Point2:
        if isinstance(distance, (tuple, list)):  # interval
            distance = distance[0] + random.random() * (distance[1] - distance[0])

        assert distance > 0, "Distance is not greater than 0"
        angle = random.random() * 2 * math.pi

        dx, dy = math.cos(angle), math.sin(angle)
        return Point2((self.x + dx * distance, self.y + dy * distance))

    def towards_with_random_angle(
        self,
        p: Point2 | Point3,
        distance: int | float = 1,
        max_difference: int | float = (math.pi / 4),
    ) -> Point2:
        tx, ty = self.to2.towards(p.to2, 1)
        angle = math.atan2(ty - self.y, tx - self.x)
        angle = (angle - max_difference) + max_difference * 2 * random.random()
        return Point2((self.x + math.cos(angle) * distance, self.y + math.sin(angle) * distance))

    def circle_intersection(self, p: Point2, r: int | float) -> set[Point2]:
        """self is point1, p is point2, r is the radius for circles originating in both points
        Used in ramp finding

        :param p:
        :param r:"""
        assert self != p, "self is equal to p"
        distance_between_points = self.distance_to(p)
        assert r >= distance_between_points / 2
        # remaining distance from center towards the intersection, using pythagoras
        remaining_distance_from_center = (r**2 - (distance_between_points / 2) ** 2) ** 0.5
        # center of both points
        offset_to_center = Point2(((p.x - self.x) / 2, (p.y - self.y) / 2))
        center = self.offset(offset_to_center)

        # stretch offset vector in the ratio of remaining distance from center to intersection
        vector_stretch_factor = remaining_distance_from_center / (distance_between_points / 2)
        v = offset_to_center
        offset_to_center_stretched = Point2((v.x * vector_stretch_factor, v.y * vector_stretch_factor))

        # rotate vector by 90° and -90°
        vector_rotated_1 = Point2((offset_to_center_stretched.y, -offset_to_center_stretched.x))
        vector_rotated_2 = Point2((-offset_to_center_stretched.y, offset_to_center_stretched.x))
        intersect1 = center.offset(vector_rotated_1)
        intersect2 = center.offset(vector_rotated_2)
        return {intersect1, intersect2}

    @property
    def neighbors4(self) -> set:
        return {
            Point2((self.x - 1, self.y)),
            Point2((self.x + 1, self.y)),
            Point2((self.x, self.y - 1)),
            Point2((self.x, self.y + 1)),
        }

    @property
    def neighbors8(self) -> set:
        return self.neighbors4 | {
            Point2((self.x - 1, self.y - 1)),
            Point2((self.x - 1, self.y + 1)),
            Point2((self.x + 1, self.y - 1)),
            Point2((self.x + 1, self.y + 1)),
        }

    def negative_offset(self, other: Point2) -> Point2:
        return self.__class__((self[0] - other[0], self[1] - other[1]))

    def __add__(self, other: Point2) -> Point2:
        return self.offset(other)

    def __sub__(self, other: Point2) -> Point2:
        return self.negative_offset(other)

    def __neg__(self) -> Point2:
        return self.__class__(-a for a in self)

    def __abs__(self) -> float:
        return math.hypot(self.x, self.y)

    def __bool__(self) -> bool:
        return self.x != 0 or self.y != 0

    def __mul__(self, other: int | float | Point2) -> Point2:
        try:
            # pyre-ignore[16]
            return self.__class__((self.x * other.x, self.y * other.y))
        except AttributeError:
            return self.__class__((self.x * other, self.y * other))

    def __rmul__(self, other: int | float | Point2) -> Point2:
        return self.__mul__(other)

    def __truediv__(self, other: int | float | Point2) -> Point2:
        if isinstance(other, self.__class__):
            return self.__class__((self.x / other.x, self.y / other.y))
        return self.__class__((self.x / other, self.y / other))

    def is_same_as(self, other: Point2, dist: float = 0.001) -> bool:
        return self.distance_to_point2(other) <= dist

    def direction_vector(self, other: Point2) -> Point2:
        """Converts a vector to a direction that can face vertically, horizontally or diagonal or be zero, e.g. (0, 0), (1, -1), (1, 0)"""
        return self.__class__((_sign(other.x - self.x), _sign(other.y - self.y)))

    def manhattan_distance(self, other: Point2) -> float:
        """
        :param other:
        """
        return abs(other.x - self.x) + abs(other.y - self.y)

    @staticmethod
    def center(points: list[Point2]) -> Point2:
        """Returns the central point for points in list

        :param points:"""
        s = Point2((0, 0))
        for p in points:
            s += p
        return s / len(points)


class Point3(Point2):
    @classmethod
    def from_proto(cls, data) -> Point3:
        """
        :param data:
        """
        return cls((data.x, data.y, data.z))

    @property
    # pyre-fixme[11]
    def as_Point(self) -> common_pb.Point:
        return common_pb.Point(x=self.x, y=self.y, z=self.z)

    @property
    def rounded(self) -> Point3:
        return Point3((math.floor(self[0]), math.floor(self[1]), math.floor(self[2])))

    @property
    def z(self) -> float:
        return self[2]

    @property
    def to3(self) -> Point3:
        return Point3(self)

    def __add__(self, other: Point2 | Point3) -> Point3:
        if not isinstance(other, Point3) and isinstance(other, Point2):
            return Point3((self.x + other.x, self.y + other.y, self.z))
        # pyre-ignore[16]
        return Point3((self.x + other.x, self.y + other.y, self.z + other.z))


class Size(Point2):
    @property
    def width(self) -> float:
        return self[0]

    @property
    def height(self) -> float:
        return self[1]


class Rect(tuple):
    @classmethod
    def from_proto(cls, data) -> Rect:
        """
        :param data:
        """
        assert data.p0.x < data.p1.x and data.p0.y < data.p1.y
        return cls((data.p0.x, data.p0.y, data.p1.x - data.p0.x, data.p1.y - data.p0.y))

    @property
    def x(self) -> float:
        return self[0]

    @property
    def y(self) -> float:
        return self[1]

    @property
    def width(self) -> float:
        return self[2]

    @property
    def height(self) -> float:
        return self[3]

    @property
    def right(self) -> float:
        """Returns the x-coordinate of the rectangle of its right side."""
        return self.x + self.width

    @property
    def top(self) -> float:
        """Returns the y-coordinate of the rectangle of its top side."""
        return self.y + self.height

    @property
    def size(self) -> Size:
        return Size((self[2], self[3]))

    @property
    def center(self) -> Point2:
        return Point2((self.x + self.width / 2, self.y + self.height / 2))

    def offset(self, p) -> Rect:
        return self.__class__((self[0] + p[0], self[1] + p[1], self[2], self[3]))
```

### File: `sc2/power_source.py`

```python
from __future__ import annotations

from dataclasses import dataclass

from sc2.position import Point2


@dataclass
class PowerSource:
    position: Point2
    radius: float
    unit_tag: int

    def __post_init__(self) -> None:
        assert self.radius > 0

    @classmethod
    def from_proto(cls, proto) -> PowerSource:
        return PowerSource(Point2.from_proto(proto.pos), proto.radius, proto.tag)

    def covers(self, position: Point2) -> bool:
        return self.position.distance_to(position) <= self.radius

    def __repr__(self) -> str:
        return f"PowerSource({self.position}, {self.radius})"


@dataclass
class PsionicMatrix:
    sources: list[PowerSource]

    @classmethod
    def from_proto(cls, proto) -> PsionicMatrix:
        return PsionicMatrix([PowerSource.from_proto(p) for p in proto])

    def covers(self, position: Point2) -> bool:
        return any(source.covers(position) for source in self.sources)
```

### File: `sc2/protocol.py`

```python
from __future__ import annotations

import asyncio
import sys
from contextlib import suppress

from aiohttp.client_ws import ClientWebSocketResponse
from loguru import logger

# pyre-fixme[21]
from s2clientprotocol import sc2api_pb2 as sc_pb

from sc2.data import Status


class ProtocolError(Exception):
    @property
    def is_game_over_error(self) -> bool:
        return self.args[0] in ["['Game has already ended']", "['Not supported if game has already ended']"]


class ConnectionAlreadyClosedError(ProtocolError):
    pass


class Protocol:
    def __init__(self, ws: ClientWebSocketResponse) -> None:
        """
        A class for communicating with an SCII application.
        :param ws: the websocket (type: aiohttp.ClientWebSocketResponse) used to communicate with a specific SCII app
        """
        assert ws
        self._ws: ClientWebSocketResponse = ws
        # pyre-fixme[11]
        self._status: Status | None = None

    async def __request(self, request):
        logger.debug(f"Sending request: {request!r}")
        try:
            await self._ws.send_bytes(request.SerializeToString())
        except TypeError as exc:
            logger.exception("Cannot send: Connection already closed.")
            raise ConnectionAlreadyClosedError("Connection already closed.") from exc
        logger.debug("Request sent")

        response = sc_pb.Response()
        try:
            response_bytes = await self._ws.receive_bytes()
        except TypeError as exc:
            if self._status == Status.ended:
                logger.info("Cannot receive: Game has already ended.")
                raise ConnectionAlreadyClosedError("Game has already ended") from exc
            logger.error("Cannot receive: Connection already closed.")
            raise ConnectionAlreadyClosedError("Connection already closed.") from exc
        except asyncio.CancelledError:
            # If request is sent, the response must be received before reraising cancel
            try:
                await self._ws.receive_bytes()
            except asyncio.CancelledError:
                logger.critical("Requests must not be cancelled multiple times")
                sys.exit(2)
            raise

        response.ParseFromString(response_bytes)
        logger.debug("Response received")
        return response

    async def _execute(self, **kwargs):
        assert len(kwargs) == 1, "Only one request allowed by the API"

        response = await self.__request(sc_pb.Request(**kwargs))

        new_status = Status(response.status)
        if new_status != self._status:
            logger.info(f"Client status changed to {new_status} (was {self._status})")
        self._status = new_status

        if response.error:
            logger.debug(f"Response contained an error: {response.error}")
            raise ProtocolError(f"{response.error}")

        return response

    async def ping(self):
        result = await self._execute(ping=sc_pb.RequestPing())
        return result

    async def quit(self) -> None:
        with suppress(ConnectionAlreadyClosedError, ConnectionResetError):
            await self._execute(quit=sc_pb.RequestQuit())
```

### File: `sc2/proxy.py`

```python
# pyre-ignore-all-errors[16, 29]
from __future__ import annotations

import asyncio
import os
import platform
import subprocess
import time
import traceback
from pathlib import Path

from aiohttp import WSMsgType, web
from aiohttp.web_ws import WebSocketResponse
from loguru import logger

# pyre-fixme[21]
from s2clientprotocol import sc2api_pb2 as sc_pb

from sc2.controller import Controller
from sc2.data import Result, Status
from sc2.player import BotProcess


class Proxy:
    """
    Class for handling communication between sc2 and an external bot.
    This "middleman" is needed for enforcing time limits, collecting results, and closing things properly.
    """

    def __init__(
        self,
        controller: Controller,
        player: BotProcess,
        proxyport: int,
        game_time_limit: int | None = None,
        realtime: bool = False,
    ) -> None:
        self.controller = controller
        self.player = player
        self.port = proxyport
        self.timeout_loop = game_time_limit * 22.4 if game_time_limit else None
        self.realtime = realtime
        logger.debug(
            f"Proxy Inited with ctrl {controller}({controller._process._port}), player {player}, proxyport {proxyport}, lim {game_time_limit}"
        )

        self.result = None
        self.player_id: int | None = None
        self.done = False

    async def parse_request(self, msg) -> None:
        request = sc_pb.Request()
        request.ParseFromString(msg.data)
        if request.HasField("quit"):
            request = sc_pb.Request(leave_game=sc_pb.RequestLeaveGame())
        if request.HasField("leave_game"):
            if self.controller._status == Status.in_game:
                logger.info(f"Proxy: player {self.player.name}({self.player_id}) surrenders")
                self.result = {self.player_id: Result.Defeat}
            elif self.controller._status == Status.ended:
                await self.get_response()
        elif request.HasField("join_game") and not request.join_game.HasField("player_name"):
            request.join_game.player_name = self.player.name
        await self.controller._ws.send_bytes(request.SerializeToString())

    # TODO Catching too general exception Exception (broad-except)

    async def get_response(self):
        response_bytes = None
        try:
            response_bytes = await self.controller._ws.receive_bytes()
        except TypeError as e:
            logger.exception("Cannot receive: SC2 Connection already closed.")
            tb = traceback.format_exc()
            logger.error(f"Exception {e}: {tb}")
        except asyncio.CancelledError:
            logger.info(f"Proxy({self.player.name}), caught receive from sc2")
            try:
                x = await self.controller._ws.receive_bytes()
                if response_bytes is None:
                    response_bytes = x
            except (asyncio.CancelledError, asyncio.TimeoutError, Exception) as e:
                logger.exception(f"Exception {e}")
        except Exception as e:
            logger.exception(f"Caught unknown exception: {e}")
        return response_bytes

    async def parse_response(self, response_bytes):
        response = sc_pb.Response()
        response.ParseFromString(response_bytes)

        if not response.HasField("status"):
            logger.critical("Proxy: RESPONSE HAS NO STATUS {response}")
        else:
            new_status = Status(response.status)
            if new_status != self.controller._status:
                logger.info(f"Controller({self.player.name}): {self.controller._status}->{new_status}")
                self.controller._status = new_status

        if self.player_id is None and response.HasField("join_game"):
            self.player_id = response.join_game.player_id
            logger.info(f"Proxy({self.player.name}): got join_game for {self.player_id}")

        if self.result is None and response.HasField("observation"):
            obs: sc_pb.ResponseObservation = response.observation
            if obs.player_result:
                self.result = {pr.player_id: Result(pr.result) for pr in obs.player_result}
            elif self.timeout_loop and obs.HasField("observation") and obs.observation.game_loop > self.timeout_loop:
                self.result = {i: Result.Tie for i in range(1, 3)}  # noqa: C420
                logger.info(f"Proxy({self.player.name}) timing out")
                act = [sc_pb.Action(action_chat=sc_pb.ActionChat(message="Proxy: Timing out"))]
                await self.controller._execute(action=sc_pb.RequestAction(actions=act))
        return response

    async def get_result(self) -> None:
        try:
            res = await self.controller.ping()
            if res.status in {Status.in_game, Status.in_replay, Status.ended}:
                res = await self.controller._execute(observation=sc_pb.RequestObservation())
                if res.HasField("observation") and res.observation.player_result:
                    self.result = {pr.player_id: Result(pr.result) for pr in res.observation.player_result}

        # TODO Catching too general exception Exception (broad-except)
        except Exception as e:
            logger.exception(f"Caught unknown exception: {e}")

    async def proxy_handler(self, request) -> WebSocketResponse:
        bot_ws = web.WebSocketResponse(receive_timeout=30)
        await bot_ws.prepare(request)
        try:
            async for msg in bot_ws:
                if msg.data is None:
                    raise TypeError(f"data is None, {msg}")
                if msg.data and msg.type == WSMsgType.BINARY:
                    await self.parse_request(msg)

                    response_bytes = await self.get_response()
                    if response_bytes is None:
                        raise ConnectionError("Could not get response_bytes")

                    new_response = await self.parse_response(response_bytes)
                    await bot_ws.send_bytes(new_response.SerializeToString())

                elif msg.type == WSMsgType.CLOSED:
                    logger.error("Client shutdown")
                else:
                    logger.error("Incorrect message type")

        # TODO Catching too general exception Exception (broad-except)
        except Exception as e:
            logger.exception(f"Caught unknown exception: {e}")
            ignored_errors = {ConnectionError, asyncio.CancelledError}
            if not any(isinstance(e, E) for E in ignored_errors):
                tb = traceback.format_exc()
                logger.info(f"Proxy({self.player.name}): Caught {e} traceback: {tb}")
        finally:
            try:
                if self.controller._status in {Status.in_game, Status.in_replay}:
                    await self.controller._execute(leave_game=sc_pb.RequestLeaveGame())
                await bot_ws.close()

            # TODO Catching too general exception Exception (broad-except)
            except Exception as e:
                logger.exception(f"Caught unknown exception during surrender: {e}")
            self.done = True
        return bot_ws

    async def play_with_proxy(self, startport):
        logger.info(f"Proxy({self.port}): Starting app")
        app = web.Application()
        app.router.add_route("GET", "/sc2api", self.proxy_handler)
        apprunner = web.AppRunner(app, access_log=None)
        await apprunner.setup()
        appsite = web.TCPSite(apprunner, self.controller._process._host, self.port)
        await appsite.start()

        subproc_args = {"cwd": str(self.player.path), "stderr": subprocess.STDOUT}
        if platform.system() == "Linux":
            subproc_args["preexec_fn"] = os.setpgrp
        elif platform.system() == "Windows":
            subproc_args["creationflags"] = subprocess.CREATE_NEW_PROCESS_GROUP

        player_command_line = self.player.cmd_line(self.port, startport, self.controller._process._host, self.realtime)
        logger.info(f"Starting bot with command: {' '.join(player_command_line)}")
        if self.player.stdout is None:
            bot_process = subprocess.Popen(player_command_line, stdout=subprocess.DEVNULL, **subproc_args)
        else:
            with Path(self.player.stdout).open("w+") as out:
                bot_process = subprocess.Popen(player_command_line, stdout=out, **subproc_args)

        while self.result is None:
            bot_alive = bot_process and bot_process.poll() is None
            sc2_alive = self.controller.running
            if self.done or not (bot_alive and sc2_alive):
                logger.info(
                    f"Proxy({self.port}): {self.player.name} died, "
                    f"bot{(not bot_alive) * ' not'} alive, sc2{(not sc2_alive) * ' not'} alive"
                )
                # Maybe its still possible to retrieve a result
                if sc2_alive and not self.done:
                    await self.get_response()
                logger.info(f"Proxy({self.port}): breaking, result {self.result}")
                break
            await asyncio.sleep(5)

        # cleanup
        logger.info(f"({self.port}): cleaning up {self.player!r}")
        for _i in range(3):
            if isinstance(bot_process, subprocess.Popen):
                if bot_process.stdout and not bot_process.stdout.closed:  # should not run anymore
                    logger.info(f"==================output for player {self.player.name}")
                    for line in bot_process.stdout.readlines():
                        logger.opt(raw=True).info(line.decode("utf-8"))
                    bot_process.stdout.close()
                    logger.info("==================")
                bot_process.terminate()
                bot_process.wait()
            time.sleep(0.5)
            if not bot_process or bot_process.poll() is not None:
                break
        else:
            bot_process.terminate()
            bot_process.wait()
        try:
            await apprunner.cleanup()

        # TODO Catching too general exception Exception (broad-except)
        except Exception as e:
            logger.exception(f"Caught unknown exception during cleaning: {e}")
        if isinstance(self.result, dict):
            self.result[None] = None
            return self.result[self.player_id]
        return self.result
```

### File: `sc2/renderer.py`

```python
import datetime

# pyre-ignore[21]
from s2clientprotocol import score_pb2 as score_pb

from sc2.position import Point2


class Renderer:
    def __init__(self, client, map_size, minimap_size) -> None:
        self._client = client

        self._window = None
        self._map_size = map_size
        self._map_image = None
        self._minimap_size = minimap_size
        self._minimap_image = None
        self._mouse_x, self._mouse_y = None, None
        self._text_supply = None
        self._text_vespene = None
        self._text_minerals = None
        self._text_score = None
        self._text_time = None

    async def render(self, observation) -> None:
        render_data = observation.observation.render_data

        map_size = render_data.map.size
        map_data = render_data.map.data
        minimap_size = render_data.minimap.size
        minimap_data = render_data.minimap.data

        map_width, map_height = map_size.x, map_size.y
        map_pitch = -map_width * 3

        minimap_width, minimap_height = minimap_size.x, minimap_size.y
        minimap_pitch = -minimap_width * 3

        if not self._window:
            from pyglet.image import ImageData
            from pyglet.text import Label
            from pyglet.window import Window

            self._window = Window(width=map_width, height=map_height)
            # pyre-fixme[16]
            self._window.on_mouse_press = self._on_mouse_press
            # pyre-fixme[16]
            self._window.on_mouse_release = self._on_mouse_release
            # pyre-fixme[16]
            self._window.on_mouse_drag = self._on_mouse_drag
            self._map_image = ImageData(map_width, map_height, "RGB", map_data, map_pitch)
            self._minimap_image = ImageData(minimap_width, minimap_height, "RGB", minimap_data, minimap_pitch)
            self._text_supply = Label(
                "",
                font_name="Arial",
                font_size=16,
                anchor_x="right",
                anchor_y="top",
                x=self._map_size[0] - 10,
                y=self._map_size[1] - 10,
                color=(200, 200, 200, 255),
            )
            self._text_vespene = Label(
                "",
                font_name="Arial",
                font_size=16,
                anchor_x="right",
                anchor_y="top",
                x=self._map_size[0] - 130,
                y=self._map_size[1] - 10,
                color=(28, 160, 16, 255),
            )
            self._text_minerals = Label(
                "",
                font_name="Arial",
                font_size=16,
                anchor_x="right",
                anchor_y="top",
                x=self._map_size[0] - 200,
                y=self._map_size[1] - 10,
                color=(68, 140, 255, 255),
            )
            self._text_score = Label(
                "",
                font_name="Arial",
                font_size=16,
                anchor_x="left",
                anchor_y="top",
                x=10,
                y=self._map_size[1] - 10,
                color=(219, 30, 30, 255),
            )
            self._text_time = Label(
                "",
                font_name="Arial",
                font_size=16,
                anchor_x="right",
                anchor_y="bottom",
                x=self._minimap_size[0] - 10,
                y=self._minimap_size[1] + 10,
                color=(255, 255, 255, 255),
            )
        else:
            self._map_image.set_data("RGB", map_pitch, map_data)
            self._minimap_image.set_data("RGB", minimap_pitch, minimap_data)
            self._text_time.text = str(datetime.timedelta(seconds=(observation.observation.game_loop * 0.725) // 16))
            if observation.observation.HasField("player_common"):
                self._text_supply.text = f"{observation.observation.player_common.food_used} / {observation.observation.player_common.food_cap}"
                self._text_vespene.text = str(observation.observation.player_common.vespene)
                self._text_minerals.text = str(observation.observation.player_common.minerals)
            if observation.observation.HasField("score"):
                self._text_score.text = f"{score_pb._SCORE_SCORETYPE.values_by_number[observation.observation.score.score_type].name} score: {observation.observation.score.score}"

        await self._update_window()

        if self._client.in_game and (not observation.player_result) and self._mouse_x and self._mouse_y:
            await self._client.move_camera_spatial(Point2((self._mouse_x, self._minimap_size[0] - self._mouse_y)))
            self._mouse_x, self._mouse_y = None, None

    async def _update_window(self) -> None:
        self._window.switch_to()
        self._window.dispatch_events()

        self._window.clear()

        self._map_image.blit(0, 0)
        self._minimap_image.blit(0, 0)
        self._text_time.draw()
        self._text_score.draw()
        self._text_minerals.draw()
        self._text_vespene.draw()
        self._text_supply.draw()

        self._window.flip()

    def _on_mouse_press(self, x, y, button, _modifiers) -> None:
        if button != 1:  # 1: mouse.LEFT
            return
        if x > self._minimap_size[0] or y > self._minimap_size[1]:
            return
        self._mouse_x, self._mouse_y = x, y

    def _on_mouse_release(self, x, y, button, _modifiers) -> None:
        if button != 1:  # 1: mouse.LEFT
            return
        if x > self._minimap_size[0] or y > self._minimap_size[1]:
            return
        self._mouse_x, self._mouse_y = x, y

    def _on_mouse_drag(self, x, y, _dx, _dy, buttons, _modifiers) -> None:
        if not buttons & 1:  # 1: mouse.LEFT
            return
        if x > self._minimap_size[0] or y > self._minimap_size[1]:
            return
        self._mouse_x, self._mouse_y = x, y
```

### File: `sc2/sc2process.py`

```python
from __future__ import annotations

import asyncio
import os
import os.path
import shutil
import signal
import subprocess
import sys
import tempfile
import time
from contextlib import suppress
from pathlib import Path
from typing import Any

import aiohttp

# pyre-ignore[21]
import portpicker
from aiohttp.client_ws import ClientWebSocketResponse
from loguru import logger

from sc2 import paths, wsl
from sc2.controller import Controller
from sc2.paths import Paths
from sc2.versions import VERSIONS


class KillSwitch:
    _to_kill: list[Any] = []

    @classmethod
    def add(cls, value) -> None:
        logger.debug("kill_switch: Add switch")
        cls._to_kill.append(value)

    @classmethod
    def kill_all(cls) -> None:
        logger.info(f"kill_switch: Process cleanup for {len(cls._to_kill)} processes")
        for p in cls._to_kill:
            p._clean(verbose=False)


class SC2Process:
    """
    A class for handling SCII applications.

    :param host: hostname for the url the SCII application will listen to
    :param port: the websocket port the SCII application will listen to
    :param fullscreen: whether to launch the SCII application in fullscreen or not, defaults to False
    :param resolution: (window width, window height) in pixels, defaults to (1024, 768)
    :param placement: (x, y) the distances of the SCII app's top left corner from the top left corner of the screen
                       e.g. (20, 30) is 20 to the right of the screen's left border, and 30 below the top border
    :param render:
    :param sc2_version:
    :param base_build:
    :param data_hash:
    """

    def __init__(
        self,
        host: str | None = None,
        port: int | None = None,
        fullscreen: bool = False,
        resolution: list[int] | tuple[int, int] | None = None,
        placement: list[int] | tuple[int, int] | None = None,
        render: bool = False,
        sc2_version: str | None = None,
        base_build: str | None = None,
        data_hash: str | None = None,
    ) -> None:
        assert isinstance(host, str) or host is None
        assert isinstance(port, int) or port is None

        self._render = render
        self._arguments: dict[str, str] = {"-displayMode": str(int(fullscreen))}
        if not fullscreen:
            if resolution and len(resolution) == 2:
                self._arguments["-windowwidth"] = str(resolution[0])
                self._arguments["-windowheight"] = str(resolution[1])
            if placement and len(placement) == 2:
                self._arguments["-windowx"] = str(placement[0])
                self._arguments["-windowy"] = str(placement[1])

        self._host = host or os.environ.get("SC2CLIENTHOST", "127.0.0.1")
        self._serverhost = os.environ.get("SC2SERVERHOST", self._host)

        if port is None:
            self._port = portpicker.pick_unused_port()
        else:
            self._port = port
        self._used_portpicker = bool(port is None)
        self._tmp_dir = tempfile.mkdtemp(prefix="SC2_")
        self._process: subprocess.Popen | None = None
        self._session = None
        self._ws = None
        self._sc2_version = sc2_version
        self._base_build = base_build
        self._data_hash = data_hash

    async def __aenter__(self) -> Controller:
        KillSwitch.add(self)

        def signal_handler(*_args):
            # unused arguments: signal handling library expects all signal
            # callback handlers to accept two positional arguments
            KillSwitch.kill_all()

        signal.signal(signal.SIGINT, signal_handler)

        try:
            self._process = self._launch()
            self._ws = await self._connect()
        except:
            await self._close_connection()
            self._clean()
            raise

        return Controller(self._ws, self)

    async def __aexit__(self, *args) -> None:
        await self._close_connection()
        KillSwitch.kill_all()
        signal.signal(signal.SIGINT, signal.SIG_DFL)

    @property
    def ws_url(self) -> str:
        return f"ws://{self._host}:{self._port}/sc2api"

    @property
    def versions(self):
        """Opens the versions.json file which origins from
        https://github.com/Blizzard/s2client-proto/blob/master/buildinfo/versions.json"""
        return VERSIONS

    def find_data_hash(self, target_sc2_version: str) -> str | None:
        """Returns the data hash from the matching version string."""
        version: dict
        for version in self.versions:
            if version["label"] == target_sc2_version:
                return version["data-hash"]
        return None

    def find_base_dir(self, target_sc2_version: str) -> str | None:
        """Returns the base directory from the matching version string."""
        version: dict
        for version in self.versions:
            if version["label"] == target_sc2_version:
                return "Base" + str(version["base-version"])
        return None

    def _launch(self):
        if self._sc2_version and not self._base_build:
            self._base_build = self.find_base_dir(self._sc2_version)

        if self._base_build:
            executable = str(paths.latest_executeble(Paths.BASE / "Versions", self._base_build))
        else:
            executable = str(Paths.EXECUTABLE)

        if self._port is None:
            self._port = portpicker.pick_unused_port()
            self._used_portpicker = True
        args = paths.get_runner_args(Paths.CWD) + [
            executable,
            "-listen",
            self._serverhost,
            "-port",
            str(self._port),
            "-dataDir",
            str(Paths.BASE),
            "-tempDir",
            self._tmp_dir,
        ]
        for arg, value in self._arguments.items():
            args.append(arg)
            args.append(value)
        if self._sc2_version:

            def special_match(strg: str):
                """Tests if the specified version is in the versions.py dict."""
                return any(version["label"] == strg for version in self.versions)

            valid_version_string = special_match(self._sc2_version)
            if valid_version_string:
                self._data_hash = self.find_data_hash(self._sc2_version)
                assert self._data_hash is not None, (
                    f"StarCraft 2 Client version ({self._sc2_version}) was not found inside sc2/versions.py file. Please check your spelling or check the versions.py file."
                )

            else:
                logger.warning(
                    f'The submitted version string in sc2.rungame() function call (sc2_version="{self._sc2_version}") was not found in versions.py. Running latest version instead.'
                )

        if self._data_hash:
            args.extend(["-dataVersion", self._data_hash])

        if self._render:
            args.extend(["-eglpath", "libEGL.so"])

        # if logger.getEffectiveLevel() <= logging.DEBUG:
        args.append("-verbose")

        sc2_cwd = str(Paths.CWD) if Paths.CWD else None

        if paths.PF in {"WSL1", "WSL2"}:
            return wsl.run(args, sc2_cwd)

        return subprocess.Popen(
            args,
            cwd=sc2_cwd,
            # Suppress Wine error messages
            stderr=subprocess.DEVNULL,
            # , env=run_config.env
        )

    async def _connect(self) -> ClientWebSocketResponse:
        # How long it waits for SC2 to start (in seconds)
        for i in range(180):
            if self._process is None:
                # The ._clean() was called, clearing the process
                logger.debug("Process cleanup complete, exit")
                sys.exit()

            await asyncio.sleep(1)
            try:
                self._session = aiohttp.ClientSession()
                ws = await self._session.ws_connect(self.ws_url, timeout=120)
                # FIXME fix deprecation warning in for future aiohttp version
                # ws = await self._session.ws_connect(
                #     self.ws_url, timeout=aiohttp.client_ws.ClientWSTimeout(ws_close=120)
                # )
                logger.debug("Websocket connection ready")
                return ws
            except aiohttp.client_exceptions.ClientConnectorError:
                await self._session.close()
                if i > 15:
                    logger.debug("Connection refused (startup not complete (yet))")

        logger.debug("Websocket connection to SC2 process timed out")
        raise TimeoutError("Websocket")

    async def _close_connection(self) -> None:
        logger.info(f"Closing connection at {self._port}...")

        if self._ws is not None:
            await self._ws.close()

        if self._session is not None:
            await self._session.close()

    def _clean(self, verbose: bool = True) -> None:
        if verbose:
            logger.info("Cleaning up...")

        if self._process is not None:
            assert isinstance(self._process, subprocess.Popen)
            if paths.PF in {"WSL1", "WSL2"}:
                if wsl.kill(self._process):
                    logger.error("KILLED")
            elif self._process.poll() is None:
                for _ in range(3):
                    self._process.terminate()
                    time.sleep(0.5)
                    if not self._process or self._process.poll() is not None:
                        break
            else:
                self._process.kill()
                self._process.wait()
                logger.error("KILLED")
            # Try to kill wineserver on linux
            if paths.PF in {"Linux", "WineLinux"}:
                # Command wineserver not detected
                with suppress(FileNotFoundError), subprocess.Popen(["wineserver", "-k"]) as p:
                    p.wait()

        if Path(self._tmp_dir).exists():
            shutil.rmtree(self._tmp_dir)

        self._process = None
        self._ws = None
        if self._used_portpicker and self._port is not None:
            portpicker.return_port(self._port)
            self._port = None
        if verbose:
            logger.info("Cleanup complete")
```

### File: `sc2/score.py`

```python
class ScoreDetails:
    """Accessable in self.state.score during step function
    For more information, see https://github.com/Blizzard/s2client-proto/blob/master/s2clientprotocol/score.proto
    """

    def __init__(self, proto) -> None:
        self._data = proto
        self._proto = proto.score_details

    @property
    def summary(self):
        """
        TODO this is super ugly, how can we improve this summary?
        Print summary to file with:
        In on_step:

        with open("stats.txt", "w+") as file:
            for stat in self.state.score.summary:
                file.write(f"{stat[0]:<35} {float(stat[1]):>35.3f}\n")
        """
        values = [
            "score_type",
            "score",
            "idle_production_time",
            "idle_worker_time",
            "total_value_units",
            "total_value_structures",
            "killed_value_units",
            "killed_value_structures",
            "collected_minerals",
            "collected_vespene",
            "collection_rate_minerals",
            "collection_rate_vespene",
            "spent_minerals",
            "spent_vespene",
            "food_used_none",
            "food_used_army",
            "food_used_economy",
            "food_used_technology",
            "food_used_upgrade",
            "killed_minerals_none",
            "killed_minerals_army",
            "killed_minerals_economy",
            "killed_minerals_technology",
            "killed_minerals_upgrade",
            "killed_vespene_none",
            "killed_vespene_army",
            "killed_vespene_economy",
            "killed_vespene_technology",
            "killed_vespene_upgrade",
            "lost_minerals_none",
            "lost_minerals_army",
            "lost_minerals_economy",
            "lost_minerals_technology",
            "lost_minerals_upgrade",
            "lost_vespene_none",
            "lost_vespene_army",
            "lost_vespene_economy",
            "lost_vespene_technology",
            "lost_vespene_upgrade",
            "friendly_fire_minerals_none",
            "friendly_fire_minerals_army",
            "friendly_fire_minerals_economy",
            "friendly_fire_minerals_technology",
            "friendly_fire_minerals_upgrade",
            "friendly_fire_vespene_none",
            "friendly_fire_vespene_army",
            "friendly_fire_vespene_economy",
            "friendly_fire_vespene_technology",
            "friendly_fire_vespene_upgrade",
            "used_minerals_none",
            "used_minerals_army",
            "used_minerals_economy",
            "used_minerals_technology",
            "used_minerals_upgrade",
            "used_vespene_none",
            "used_vespene_army",
            "used_vespene_economy",
            "used_vespene_technology",
            "used_vespene_upgrade",
            "total_used_minerals_none",
            "total_used_minerals_army",
            "total_used_minerals_economy",
            "total_used_minerals_technology",
            "total_used_minerals_upgrade",
            "total_used_vespene_none",
            "total_used_vespene_army",
            "total_used_vespene_economy",
            "total_used_vespene_technology",
            "total_used_vespene_upgrade",
            "total_damage_dealt_life",
            "total_damage_dealt_shields",
            "total_damage_dealt_energy",
            "total_damage_taken_life",
            "total_damage_taken_shields",
            "total_damage_taken_energy",
            "total_healed_life",
            "total_healed_shields",
            "total_healed_energy",
            "current_apm",
            "current_effective_apm",
        ]
        return [[value, getattr(self, value)] for value in values]

    @property
    def score_type(self):
        return self._data.score_type

    @property
    def score(self):
        return self._data.score

    @property
    def idle_production_time(self):
        return self._proto.idle_production_time

    @property
    def idle_worker_time(self):
        return self._proto.idle_worker_time

    @property
    def total_value_units(self):
        return self._proto.total_value_units

    @property
    def total_value_structures(self):
        return self._proto.total_value_structures

    @property
    def killed_value_units(self):
        return self._proto.killed_value_units

    @property
    def killed_value_structures(self):
        return self._proto.killed_value_structures

    @property
    def collected_minerals(self):
        return self._proto.collected_minerals

    @property
    def collected_vespene(self):
        return self._proto.collected_vespene

    @property
    def collection_rate_minerals(self):
        return self._proto.collection_rate_minerals

    @property
    def collection_rate_vespene(self):
        return self._proto.collection_rate_vespene

    @property
    def spent_minerals(self):
        return self._proto.spent_minerals

    @property
    def spent_vespene(self):
        return self._proto.spent_vespene

    @property
    def food_used_none(self):
        return self._proto.food_used.none

    @property
    def food_used_army(self):
        return self._proto.food_used.army

    @property
    def food_used_economy(self):
        return self._proto.food_used.economy

    @property
    def food_used_technology(self):
        return self._proto.food_used.technology

    @property
    def food_used_upgrade(self):
        return self._proto.food_used.upgrade

    @property
    def killed_minerals_none(self):
        return self._proto.killed_minerals.none

    @property
    def killed_minerals_army(self):
        return self._proto.killed_minerals.army

    @property
    def killed_minerals_economy(self):
        return self._proto.killed_minerals.economy

    @property
    def killed_minerals_technology(self):
        return self._proto.killed_minerals.technology

    @property
    def killed_minerals_upgrade(self):
        return self._proto.killed_minerals.upgrade

    @property
    def killed_vespene_none(self):
        return self._proto.killed_vespene.none

    @property
    def killed_vespene_army(self):
        return self._proto.killed_vespene.army

    @property
    def killed_vespene_economy(self):
        return self._proto.killed_vespene.economy

    @property
    def killed_vespene_technology(self):
        return self._proto.killed_vespene.technology

    @property
    def killed_vespene_upgrade(self):
        return self._proto.killed_vespene.upgrade

    @property
    def lost_minerals_none(self):
        return self._proto.lost_minerals.none

    @property
    def lost_minerals_army(self):
        return self._proto.lost_minerals.army

    @property
    def lost_minerals_economy(self):
        return self._proto.lost_minerals.economy

    @property
    def lost_minerals_technology(self):
        return self._proto.lost_minerals.technology

    @property
    def lost_minerals_upgrade(self):
        return self._proto.lost_minerals.upgrade

    @property
    def lost_vespene_none(self):
        return self._proto.lost_vespene.none

    @property
    def lost_vespene_army(self):
        return self._proto.lost_vespene.army

    @property
    def lost_vespene_economy(self):
        return self._proto.lost_vespene.economy

    @property
    def lost_vespene_technology(self):
        return self._proto.lost_vespene.technology

    @property
    def lost_vespene_upgrade(self):
        return self._proto.lost_vespene.upgrade

    @property
    def friendly_fire_minerals_none(self):
        return self._proto.friendly_fire_minerals.none

    @property
    def friendly_fire_minerals_army(self):
        return self._proto.friendly_fire_minerals.army

    @property
    def friendly_fire_minerals_economy(self):
        return self._proto.friendly_fire_minerals.economy

    @property
    def friendly_fire_minerals_technology(self):
        return self._proto.friendly_fire_minerals.technology

    @property
    def friendly_fire_minerals_upgrade(self):
        return self._proto.friendly_fire_minerals.upgrade

    @property
    def friendly_fire_vespene_none(self):
        return self._proto.friendly_fire_vespene.none

    @property
    def friendly_fire_vespene_army(self):
        return self._proto.friendly_fire_vespene.army

    @property
    def friendly_fire_vespene_economy(self):
        return self._proto.friendly_fire_vespene.economy

    @property
    def friendly_fire_vespene_technology(self):
        return self._proto.friendly_fire_vespene.technology

    @property
    def friendly_fire_vespene_upgrade(self):
        return self._proto.friendly_fire_vespene.upgrade

    @property
    def used_minerals_none(self):
        return self._proto.used_minerals.none

    @property
    def used_minerals_army(self):
        return self._proto.used_minerals.army

    @property
    def used_minerals_economy(self):
        return self._proto.used_minerals.economy

    @property
    def used_minerals_technology(self):
        return self._proto.used_minerals.technology

    @property
    def used_minerals_upgrade(self):
        return self._proto.used_minerals.upgrade

    @property
    def used_vespene_none(self):
        return self._proto.used_vespene.none

    @property
    def used_vespene_army(self):
        return self._proto.used_vespene.army

    @property
    def used_vespene_economy(self):
        return self._proto.used_vespene.economy

    @property
    def used_vespene_technology(self):
        return self._proto.used_vespene.technology

    @property
    def used_vespene_upgrade(self):
        return self._proto.used_vespene.upgrade

    @property
    def total_used_minerals_none(self):
        return self._proto.total_used_minerals.none

    @property
    def total_used_minerals_army(self):
        return self._proto.total_used_minerals.army

    @property
    def total_used_minerals_economy(self):
        return self._proto.total_used_minerals.economy

    @property
    def total_used_minerals_technology(self):
        return self._proto.total_used_minerals.technology

    @property
    def total_used_minerals_upgrade(self):
        return self._proto.total_used_minerals.upgrade

    @property
    def total_used_vespene_none(self):
        return self._proto.total_used_vespene.none

    @property
    def total_used_vespene_army(self):
        return self._proto.total_used_vespene.army

    @property
    def total_used_vespene_economy(self):
        return self._proto.total_used_vespene.economy

    @property
    def total_used_vespene_technology(self):
        return self._proto.total_used_vespene.technology

    @property
    def total_used_vespene_upgrade(self):
        return self._proto.total_used_vespene.upgrade

    @property
    def total_damage_dealt_life(self):
        return self._proto.total_damage_dealt.life

    @property
    def total_damage_dealt_shields(self):
        return self._proto.total_damage_dealt.shields

    @property
    def total_damage_dealt_energy(self):
        return self._proto.total_damage_dealt.energy

    @property
    def total_damage_taken_life(self):
        return self._proto.total_damage_taken.life

    @property
    def total_damage_taken_shields(self):
        return self._proto.total_damage_taken.shields

    @property
    def total_damage_taken_energy(self):
        return self._proto.total_damage_taken.energy

    @property
    def total_healed_life(self):
        return self._proto.total_healed.life

    @property
    def total_healed_shields(self):
        return self._proto.total_healed.shields

    @property
    def total_healed_energy(self):
        return self._proto.total_healed.energy

    @property
    def current_apm(self):
        return self._proto.current_apm

    @property
    def current_effective_apm(self):
        return self._proto.current_effective_apm
```

### File: `sc2/unit.py`

```python
# pyre-ignore-all-errors[11, 16, 29]
from __future__ import annotations

import math
import warnings
from dataclasses import dataclass
from functools import cached_property
from typing import TYPE_CHECKING, Any

from sc2.cache import CacheDict
from sc2.constants import (
    CAN_BE_ATTACKED,
    DAMAGE_BONUS_PER_UPGRADE,
    IS_ARMORED,
    IS_ATTACKING,
    IS_BIOLOGICAL,
    IS_CARRYING_MINERALS,
    IS_CARRYING_RESOURCES,
    IS_CARRYING_VESPENE,
    IS_CLOAKED,
    IS_COLLECTING,
    IS_CONSTRUCTING_SCV,
    IS_DETECTOR,
    IS_ENEMY,
    IS_GATHERING,
    IS_LIGHT,
    IS_MASSIVE,
    IS_MECHANICAL,
    IS_MINE,
    IS_PATROLLING,
    IS_PLACEHOLDER,
    IS_PSIONIC,
    IS_REPAIRING,
    IS_RETURNING,
    IS_REVEALED,
    IS_SNAPSHOT,
    IS_STRUCTURE,
    IS_VISIBLE,
    OFF_CREEP_SPEED_INCREASE_DICT,
    OFF_CREEP_SPEED_UPGRADE_DICT,
    SPEED_ALTERING_BUFFS,
    SPEED_INCREASE_DICT,
    SPEED_INCREASE_ON_CREEP_DICT,
    SPEED_UPGRADE_DICT,
    TARGET_AIR,
    TARGET_BOTH,
    TARGET_GROUND,
    TARGET_HELPER,
    UNIT_BATTLECRUISER,
    UNIT_COLOSSUS,
    UNIT_ORACLE,
    UNIT_PHOTONCANNON,
    transforming,
)
from sc2.data import Alliance, Attribute, CloakState, Race, Target, race_gas, warpgate_abilities
from sc2.ids.ability_id import AbilityId
from sc2.ids.buff_id import BuffId
from sc2.ids.unit_typeid import UnitTypeId
from sc2.ids.upgrade_id import UpgradeId
from sc2.position import Point2, Point3
from sc2.unit_command import UnitCommand

if TYPE_CHECKING:
    from sc2.bot_ai import BotAI
    from sc2.game_data import AbilityData, UnitTypeData


@dataclass
class RallyTarget:
    point: Point2
    tag: int | None = None

    @classmethod
    def from_proto(cls, proto: Any) -> RallyTarget:
        return cls(
            Point2.from_proto(proto.point),
            proto.tag if proto.HasField("tag") else None,
        )


@dataclass
class UnitOrder:
    ability: AbilityData  # TODO: Should this be AbilityId instead?
    target: int | Point2 | None = None
    progress: float = 0

    @classmethod
    def from_proto(cls, proto: Any, bot_object: BotAI) -> UnitOrder:
        target: int | Point2 | None = proto.target_unit_tag
        if proto.HasField("target_world_space_pos"):
            target = Point2.from_proto(proto.target_world_space_pos)
        elif proto.HasField("target_unit_tag"):
            target = proto.target_unit_tag
        return cls(
            ability=bot_object.game_data.abilities[proto.ability_id],
            target=target,
            progress=proto.progress,
        )

    def __repr__(self) -> str:
        return f"UnitOrder({self.ability}, {self.target}, {self.progress})"


class Unit:
    class_cache = CacheDict()

    def __init__(
        self,
        proto_data,
        bot_object: BotAI,
        distance_calculation_index: int = -1,
        base_build: int = -1,
    ) -> None:
        """
        :param proto_data:
        :param bot_object:
        :param distance_calculation_index:
        :param base_build:
        """
        self._proto = proto_data
        self._bot_object: BotAI = bot_object
        self.game_loop: int = bot_object.state.game_loop
        self.base_build = base_build
        # Index used in the 2D numpy array to access the 2D distance between two units
        self.distance_calculation_index: int = distance_calculation_index

    def __repr__(self) -> str:
        """Returns string of this form: Unit(name='SCV', tag=4396941328)."""
        return f"Unit(name={self.name!r}, tag={self.tag})"

    @property
    def type_id(self) -> UnitTypeId:
        """UnitTypeId found in sc2/ids/unit_typeid."""
        unit_type: int = self._proto.unit_type
        return self.class_cache.retrieve_and_set(unit_type, lambda: UnitTypeId(unit_type))

    @cached_property
    def _type_data(self) -> UnitTypeData:
        """Provides the unit type data."""
        return self._bot_object.game_data.units[self._proto.unit_type]

    @cached_property
    def _creation_ability(self) -> AbilityData | None:
        """Provides the AbilityData of the creation ability of this unit."""
        return self._type_data.creation_ability

    @property
    def name(self) -> str:
        """Returns the name of the unit."""
        return self._type_data.name

    @cached_property
    def race(self) -> Race:
        """Returns the race of the unit"""
        return Race(self._type_data._proto.race)

    @cached_property
    def tag(self) -> int:
        """Returns the unique tag of the unit."""
        return self._proto.tag

    @property
    def is_structure(self) -> bool:
        """Checks if the unit is a structure."""
        return IS_STRUCTURE in self._type_data.attributes

    @property
    def is_light(self) -> bool:
        """Checks if the unit has the 'light' attribute."""
        return IS_LIGHT in self._type_data.attributes

    @property
    def is_armored(self) -> bool:
        """Checks if the unit has the 'armored' attribute."""
        return IS_ARMORED in self._type_data.attributes

    @property
    def is_biological(self) -> bool:
        """Checks if the unit has the 'biological' attribute."""
        return IS_BIOLOGICAL in self._type_data.attributes

    @property
    def is_mechanical(self) -> bool:
        """Checks if the unit has the 'mechanical' attribute."""
        return IS_MECHANICAL in self._type_data.attributes

    @property
    def is_massive(self) -> bool:
        """Checks if the unit has the 'massive' attribute."""
        return IS_MASSIVE in self._type_data.attributes

    @property
    def is_psionic(self) -> bool:
        """Checks if the unit has the 'psionic' attribute."""
        return IS_PSIONIC in self._type_data.attributes

    @cached_property
    def tech_alias(self) -> list[UnitTypeId] | None:
        """Building tech equality, e.g. OrbitalCommand is the same as CommandCenter
        For Hive, this returns [UnitTypeId.Hatchery, UnitTypeId.Lair]
        For SCV, this returns None"""
        return self._type_data.tech_alias

    @cached_property
    def unit_alias(self) -> UnitTypeId | None:
        """Building type equality, e.g. FlyingOrbitalCommand is the same as OrbitalCommand
        For flying OrbitalCommand, this returns UnitTypeId.OrbitalCommand
        For SCV, this returns None"""
        return self._type_data.unit_alias

    @cached_property
    def _weapons(self):
        """Returns the weapons of the unit."""
        return self._type_data._proto.weapons

    @cached_property
    def can_attack(self) -> bool:
        """Checks if the unit can attack at all."""
        # TODO BATTLECRUISER doesnt have weapons in proto?!
        return bool(self._weapons) or self.type_id in {UNIT_BATTLECRUISER, UNIT_ORACLE}

    @property
    def can_attack_both(self) -> bool:
        """Checks if the unit can attack both ground and air units."""
        return self.can_attack_ground and self.can_attack_air

    @cached_property
    def can_attack_ground(self) -> bool:
        """Checks if the unit can attack ground units."""
        if self.type_id in {UNIT_BATTLECRUISER, UNIT_ORACLE}:
            return True
        if self._weapons:
            return any(weapon.type in TARGET_GROUND for weapon in self._weapons)
        return False

    @cached_property
    def ground_dps(self) -> float:
        """Returns the dps against ground units. Does not include upgrades."""
        if self.can_attack_ground:
            weapon = next((weapon for weapon in self._weapons if weapon.type in TARGET_GROUND), None)
            if weapon:
                return (weapon.damage * weapon.attacks) / weapon.speed
        return 0

    @cached_property
    def ground_range(self) -> float:
        """Returns the range against ground units. Does not include upgrades."""
        if self.type_id == UNIT_ORACLE:
            return 4
        if self.type_id == UNIT_BATTLECRUISER:
            return 6
        if self.can_attack_ground:
            weapon = next((weapon for weapon in self._weapons if weapon.type in TARGET_GROUND), None)
            if weapon:
                return weapon.range
        return 0

    @cached_property
    def can_attack_air(self) -> bool:
        """Checks if the unit can air attack at all. Does not include upgrades."""
        if self.type_id == UNIT_BATTLECRUISER:
            return True
        if self._weapons:
            return any(weapon.type in TARGET_AIR for weapon in self._weapons)
        return False

    @cached_property
    def air_dps(self) -> float:
        """Returns the dps against air units. Does not include upgrades."""
        if self.can_attack_air:
            weapon = next((weapon for weapon in self._weapons if weapon.type in TARGET_AIR), None)
            if weapon:
                return (weapon.damage * weapon.attacks) / weapon.speed
        return 0

    @cached_property
    def air_range(self) -> float:
        """Returns the range against air units. Does not include upgrades."""
        if self.type_id == UNIT_BATTLECRUISER:
            return 6
        if self.can_attack_air:
            weapon = next((weapon for weapon in self._weapons if weapon.type in TARGET_AIR), None)
            if weapon:
                return weapon.range
        return 0

    @cached_property
    def bonus_damage(self) -> tuple[int, str] | None:
        """Returns a tuple of form '(bonus damage, armor type)' if unit does 'bonus damage' against 'armor type'.
        Possible armor typs are: 'Light', 'Armored', 'Biological', 'Mechanical', 'Psionic', 'Massive', 'Structure'."""
        # TODO: Consider units with ability attacks (Oracle, Baneling) or multiple attacks (Thor).
        if self._weapons:
            for weapon in self._weapons:
                if weapon.damage_bonus:
                    b = weapon.damage_bonus[0]
                    return b.bonus, Attribute(b.attribute).name
        return None

    @property
    def armor(self) -> float:
        """Returns the armor of the unit. Does not include upgrades"""
        return self._type_data._proto.armor

    @property
    def sight_range(self) -> float:
        """Returns the sight range of the unit."""
        return self._type_data._proto.sight_range

    @property
    def movement_speed(self) -> float:
        """Returns the movement speed of the unit.
        This is the unit movement speed on game speed 'normal'. To convert it to 'faster' movement speed, multiply it by a factor of '1.4'. E.g. reaper movement speed is listed here as 3.75, but should actually be 5.25.
        Does not include upgrades or buffs."""
        return self._type_data._proto.movement_speed

    @cached_property
    def real_speed(self) -> float:
        """See 'calculate_speed'."""
        return self.calculate_speed()

    def calculate_speed(self, upgrades: set[UpgradeId] | None = None) -> float:
        """Calculates the movement speed of the unit including buffs and upgrades.
        Note: Upgrades only work with own units. Use "upgrades" param to set expected enemy upgrades.

        :param upgrades:
        """
        speed: float = self.movement_speed
        unit_type: UnitTypeId = self.type_id

        # ---- Upgrades ----
        if upgrades is None and self.is_mine:
            upgrades = self._bot_object.state.upgrades

        if upgrades and unit_type in SPEED_UPGRADE_DICT:
            upgrade_id: UpgradeId | None = SPEED_UPGRADE_DICT.get(unit_type, None)
            if upgrade_id and upgrade_id in upgrades:
                speed *= SPEED_INCREASE_DICT.get(unit_type, 1)

        # ---- Creep ----
        if unit_type in SPEED_INCREASE_ON_CREEP_DICT or unit_type in OFF_CREEP_SPEED_UPGRADE_DICT:
            # On creep
            x, y = self.position_tuple
            if self._bot_object.state.creep[(int(x), int(y))]:
                speed *= SPEED_INCREASE_ON_CREEP_DICT.get(unit_type, 1)

            # Off creep upgrades
            elif upgrades:
                upgrade_id2: UpgradeId | None = OFF_CREEP_SPEED_UPGRADE_DICT.get(unit_type, None)
                if upgrade_id2:
                    speed *= OFF_CREEP_SPEED_INCREASE_DICT[unit_type]

            # Ultralisk has passive ability "Frenzied" which makes it immune to speed altering buffs
            if unit_type == UnitTypeId.ULTRALISK:
                return speed

        # ---- Buffs ----
        # Hard reset movement speed: medivac boost, void ray charge
        if self.buffs and unit_type in {UnitTypeId.MEDIVAC, UnitTypeId.VOIDRAY}:
            if BuffId.MEDIVACSPEEDBOOST in self.buffs:
                speed = self.movement_speed * 1.7
            elif BuffId.VOIDRAYSWARMDAMAGEBOOST in self.buffs:
                speed = self.movement_speed * 0.75

        # Speed altering buffs, e.g. stimpack, zealot charge, concussive shell, time warp, fungal growth, inhibitor zone
        for buff in self.buffs:
            speed *= SPEED_ALTERING_BUFFS.get(buff, 1)
        return speed

    @property
    def distance_per_step(self) -> float:
        """The distance a unit can move in one step. This does not take acceleration into account.
        Useful for micro-retreat/pathfinding"""
        return (self.real_speed / 22.4) * self._bot_object.client.game_step

    @property
    def distance_to_weapon_ready(self) -> float:
        """Distance a unit can travel before it's weapon is ready to be fired again."""
        return (self.real_speed / 22.4) * self.weapon_cooldown

    @property
    def is_mineral_field(self) -> bool:
        """Checks if the unit is a mineral field."""
        return self._type_data.has_minerals

    @property
    def is_vespene_geyser(self) -> bool:
        """Checks if the unit is a non-empty vespene geyser or gas extraction building."""
        return self._type_data.has_vespene

    @property
    def health(self) -> float:
        """Returns the health of the unit. Does not include shields."""
        return self._proto.health

    @property
    def health_max(self) -> float:
        """Returns the maximum health of the unit. Does not include shields."""
        return self._proto.health_max

    @cached_property
    def health_percentage(self) -> float:
        """Returns the percentage of health the unit has. Does not include shields."""
        if not self._proto.health_max:
            return 0
        return self._proto.health / self._proto.health_max

    @property
    def shield(self) -> float:
        """Returns the shield points the unit has. Returns 0 for non-protoss units."""
        return self._proto.shield

    @property
    def shield_max(self) -> float:
        """Returns the maximum shield points the unit can have. Returns 0 for non-protoss units."""
        return self._proto.shield_max

    @cached_property
    def shield_percentage(self) -> float:
        """Returns the percentage of shield points the unit has. Returns 0 for non-protoss units."""
        if not self._proto.shield_max:
            return 0
        return self._proto.shield / self._proto.shield_max

    @cached_property
    def shield_health_percentage(self) -> float:
        """Returns the percentage of combined shield + hp points the unit has.
        Also takes build progress into account."""
        max_ = (self._proto.shield_max + self._proto.health_max) * self.build_progress
        if max_ == 0:
            return 0
        return (self._proto.shield + self._proto.health) / max_

    @property
    def energy(self) -> float:
        """Returns the amount of energy the unit has. Returns 0 for units without energy."""
        return self._proto.energy

    @property
    def energy_max(self) -> float:
        """Returns the maximum amount of energy the unit can have. Returns 0 for units without energy."""
        return self._proto.energy_max

    @cached_property
    def energy_percentage(self) -> float:
        """Returns the percentage of amount of energy the unit has. Returns 0 for units without energy."""
        if not self._proto.energy_max:
            return 0
        return self._proto.energy / self._proto.energy_max

    @property
    def age_in_frames(self) -> int:
        """Returns how old the unit object data is (in game frames). This age does not reflect the unit was created / trained / morphed!"""
        return self._bot_object.state.game_loop - self.game_loop

    @property
    def age(self) -> float:
        """Returns how old the unit object data is (in game seconds). This age does not reflect when the unit was created / trained / morphed!"""
        return (self._bot_object.state.game_loop - self.game_loop) / 22.4

    @property
    def is_memory(self) -> bool:
        """Returns True if this Unit object is referenced from the future and is outdated."""
        return self.game_loop != self._bot_object.state.game_loop

    @cached_property
    def is_snapshot(self) -> bool:
        """Checks if the unit is only available as a snapshot for the bot.
        Enemy buildings that have been scouted and are in the fog of war or
        attacking enemy units on higher, not visible ground appear this way."""
        if self.base_build >= 82457:
            return self._proto.display_type == IS_SNAPSHOT
        # TODO: Fixed in version 5.0.4, remove if a new linux binary is released: https://github.com/Blizzard/s2client-proto/issues/167
        position = self.position.rounded
        return self._bot_object.state.visibility.data_numpy[position[1], position[0]] != 2

    @cached_property
    def is_visible(self) -> bool:
        """Checks if the unit is visible for the bot.
        NOTE: This means the bot has vision of the position of the unit!
        It does not give any information about the cloak status of the unit."""
        if self.base_build >= 82457:
            return self._proto.display_type == IS_VISIBLE
        # TODO: Remove when a new linux binary (5.0.4 or newer) is released
        return self._proto.display_type == IS_VISIBLE and not self.is_snapshot

    @property
    def is_placeholder(self) -> bool:
        """Checks if the unit is a placerholder for the bot.
        Raw information about placeholders:
            display_type: Placeholder
            alliance: Self
            unit_type: 86
            owner: 1
            pos {
              x: 29.5
              y: 53.5
              z: 7.98828125
            }
            radius: 2.75
            is_on_screen: false
        """
        return self._proto.display_type == IS_PLACEHOLDER

    @property
    def alliance(self) -> Alliance:
        """Returns the team the unit belongs to."""
        return self._proto.alliance

    @property
    def is_mine(self) -> bool:
        """Checks if the unit is controlled by the bot."""
        return self._proto.alliance == IS_MINE

    @property
    def is_enemy(self) -> bool:
        """Checks if the unit is hostile."""
        return self._proto.alliance == IS_ENEMY

    @property
    def owner_id(self) -> int:
        """Returns the owner of the unit. This is a value of 1 or 2 in a two player game."""
        return self._proto.owner

    @property
    def position_tuple(self) -> tuple[float, float]:
        """Returns the 2d position of the unit as tuple without conversion to Point2."""
        return self._proto.pos.x, self._proto.pos.y

    @cached_property
    def position(self) -> Point2:
        """Returns the 2d position of the unit."""
        return Point2.from_proto(self._proto.pos)

    @cached_property
    def position3d(self) -> Point3:
        """Returns the 3d position of the unit."""
        return Point3.from_proto(self._proto.pos)

    def distance_to(self, p: Unit | Point2) -> float:
        """Using the 2d distance between self and p.
        To calculate the 3d distance, use unit.position3d.distance_to(p)

        :param p:
        """
        if isinstance(p, Unit):
            return self._bot_object._distance_squared_unit_to_unit(self, p) ** 0.5
        return self._bot_object.distance_math_hypot(self.position_tuple, p)

    def distance_to_squared(self, p: Unit | Point2) -> float:
        """Using the 2d distance squared between self and p. Slightly faster than distance_to, so when filtering a lot of units, this function is recommended to be used.
        To calculate the 3d distance, use unit.position3d.distance_to(p)

        :param p:
        """
        if isinstance(p, Unit):
            return self._bot_object._distance_squared_unit_to_unit(self, p)
        return self._bot_object.distance_math_hypot_squared(self.position_tuple, p)

    def target_in_range(self, target: Unit, bonus_distance: float = 0) -> bool:
        """Checks if the target is in range.
        Includes the target's radius when calculating distance to target.

        :param target:
        :param bonus_distance:
        """
        # TODO: Fix this because immovable units (sieged tank, planetary fortress etc.) have a little lower range than this formula
        if self.can_attack_ground and not target.is_flying:
            unit_attack_range = self.ground_range
        elif self.can_attack_air and (target.is_flying or target.type_id == UNIT_COLOSSUS):
            unit_attack_range = self.air_range
        else:
            return False
        return (
            self._bot_object._distance_squared_unit_to_unit(self, target)
            <= (self.radius + target.radius + unit_attack_range + bonus_distance) ** 2
        )

    def in_ability_cast_range(self, ability_id: AbilityId, target: Unit | Point2, bonus_distance: float = 0) -> bool:
        """Test if a unit is able to cast an ability on the target without checking ability cooldown (like stalker blink) or if ability is made available through research (like HT storm).

        :param ability_id:
        :param target:
        :param bonus_distance:
        """
        cast_range = self._bot_object.game_data.abilities[ability_id.value]._proto.cast_range
        assert cast_range > 0, f"Checking for an ability ({ability_id}) that has no cast range"
        ability_target_type = self._bot_object.game_data.abilities[ability_id.value]._proto.target
        # For casting abilities that target other units, like transfuse, feedback, snipe, yamato
        if ability_target_type in {Target.Unit.value, Target.PointOrUnit.value} and isinstance(target, Unit):
            return (
                self._bot_object._distance_squared_unit_to_unit(self, target)
                <= (cast_range + self.radius + target.radius + bonus_distance) ** 2
            )
        # For casting abilities on the ground, like queen creep tumor, ravager bile, HT storm
        if ability_target_type in {Target.Point.value, Target.PointOrUnit.value} and isinstance(
            target, (Point2, tuple)
        ):
            return (
                self._bot_object._distance_pos_to_pos(self.position_tuple, target)
                <= cast_range + self.radius + bonus_distance
            )
        return False

    def calculate_damage_vs_target(
        self,
        target: Unit,
        ignore_armor: bool = False,
        include_overkill_damage: bool = True,
    ) -> tuple[float, float, float]:
        """Returns a tuple of: [potential damage against target, attack speed, attack range]
        Returns the properly calculated damage per full-attack against the target unit.
        Returns (0, 0, 0) if this unit can't attack the target unit.

        If 'include_overkill_damage=True' and the unit deals 10 damage, the target unit has 5 hp and 0 armor,
        the target unit would result in -5hp, so the returning damage would be 10.
        For 'include_overkill_damage=False' this function would return 5.

        If 'ignore_armor=False' and the unit deals 10 damage, the target unit has 20 hp and 5 armor,
        the target unit would result in 15hp, so the returning damage would be 5.
        For 'ignore_armor=True' this function would return 10.

        :param target:
        :param ignore_armor:
        :param include_overkill_damage:
        """
        if self.type_id not in {UnitTypeId.BATTLECRUISER, UnitTypeId.BUNKER}:
            if not self.can_attack:
                return 0, 0, 0
            if target.type_id != UnitTypeId.COLOSSUS:
                if not self.can_attack_ground and not target.is_flying:
                    return 0, 0, 0
                if not self.can_attack_air and target.is_flying:
                    return 0, 0, 0
        # Structures that are not completed can't attack
        if not self.is_ready:
            return 0, 0, 0
        target_has_guardian_shield: bool = False
        if ignore_armor:
            enemy_armor: float = 0
            enemy_shield_armor: float = 0
        else:
            # TODO: enemy is under influence of anti armor missile -> reduce armor and shield armor
            enemy_armor = target.armor + target.armor_upgrade_level
            enemy_shield_armor = target.shield_upgrade_level
            # Ultralisk armor upgrade, only works if target belongs to the bot calling this function
            if (
                target.type_id in {UnitTypeId.ULTRALISK, UnitTypeId.ULTRALISKBURROWED}
                and target.is_mine
                and UpgradeId.CHITINOUSPLATING in target._bot_object.state.upgrades
            ):
                enemy_armor += 2
            # Guardian shield adds 2 armor
            if BuffId.GUARDIANSHIELD in target.buffs:
                target_has_guardian_shield = True
            # Anti armor missile of raven
            if BuffId.RAVENSHREDDERMISSILETINT in target.buffs:
                enemy_armor -= 2
                enemy_shield_armor -= 2

        # Hard coded return for battlecruiser because they have no weapon in the API
        if self.type_id == UnitTypeId.BATTLECRUISER:
            if target_has_guardian_shield:
                enemy_armor += 2
                enemy_shield_armor += 2
            weapon_damage: float = (5 if target.is_flying else 8) + self.attack_upgrade_level
            weapon_damage = weapon_damage - enemy_shield_armor if target.shield else weapon_damage - enemy_armor
            return weapon_damage, 0.224, 6

        # Fast return for bunkers, since they don't have a weapon similar to BCs
        if self.type_id == UnitTypeId.BUNKER and self.is_enemy:
            if self.is_active:
                # Expect fully loaded bunker with marines
                return (24, 0.854, 6)
            return (0, 0, 0)
            # TODO if bunker belongs to us, use passengers and upgrade level to calculate damage

        required_target_type: set[int] = (
            TARGET_BOTH
            if target.type_id == UnitTypeId.COLOSSUS
            else TARGET_GROUND
            if not target.is_flying
            else TARGET_AIR
        )
        # Contains total damage, attack speed and attack range
        damages: list[tuple[float, float, float]] = []
        for weapon in self._weapons:
            if weapon.type not in required_target_type:
                continue
            enemy_health: float = target.health
            enemy_shield: float = target.shield
            total_attacks: int = weapon.attacks
            weapon_speed: float = weapon.speed
            weapon_range: float = weapon.range
            bonus_damage_per_upgrade = (
                0
                if not self.attack_upgrade_level
                else DAMAGE_BONUS_PER_UPGRADE.get(self.type_id, {}).get(weapon.type, {}).get(None, 1)
            )
            damage_per_attack: float = weapon.damage + self.attack_upgrade_level * bonus_damage_per_upgrade
            # Remaining damage after all damage is dealt to shield
            remaining_damage: float = 0

            # Calculate bonus damage against target
            boni: list[float] = []
            # TODO: hardcode hellbats when they have blueflame or attack upgrades
            for bonus in weapon.damage_bonus:
                # More about damage bonus https://github.com/Blizzard/s2client-proto/blob/b73eb59ac7f2c52b2ca585db4399f2d3202e102a/s2clientprotocol/data.proto#L55
                if bonus.attribute in target._type_data.attributes:
                    bonus_damage_per_upgrade = (
                        0
                        if not self.attack_upgrade_level
                        else DAMAGE_BONUS_PER_UPGRADE.get(self.type_id, {}).get(weapon.type, {}).get(bonus.attribute, 0)
                    )
                    # Hardcode blueflame damage bonus from hellions
                    if (
                        bonus.attribute == IS_LIGHT
                        and self.type_id == UnitTypeId.HELLION
                        and UpgradeId.HIGHCAPACITYBARRELS in self._bot_object.state.upgrades
                    ):
                        bonus_damage_per_upgrade += 5
                    # TODO buffs e.g. void ray charge beam vs armored
                    boni.append(bonus.bonus + self.attack_upgrade_level * bonus_damage_per_upgrade)
            if boni:
                damage_per_attack += max(boni)

            # Subtract enemy unit's shield
            if target.shield > 0:
                # Fix for ranged units + guardian shield
                enemy_shield_armor_temp = (
                    enemy_shield_armor + 2 if target_has_guardian_shield and weapon_range >= 2 else enemy_shield_armor
                )
                # Shield-armor has to be applied
                while total_attacks > 0 and enemy_shield > 0:
                    # Guardian shield correction
                    enemy_shield -= max(0.5, damage_per_attack - enemy_shield_armor_temp)
                    total_attacks -= 1
                if enemy_shield < 0:
                    remaining_damage = -enemy_shield
                    enemy_shield = 0

            # TODO roach and hydra in melee range are not affected by guardian shield
            # Fix for ranged units if enemy has guardian shield buff
            enemy_armor_temp = enemy_armor + 2 if target_has_guardian_shield and weapon_range >= 2 else enemy_armor
            # Subtract enemy unit's HP
            if remaining_damage > 0:
                enemy_health -= max(0.5, remaining_damage - enemy_armor_temp)
            while total_attacks > 0 and (include_overkill_damage or enemy_health > 0):
                # Guardian shield correction
                enemy_health -= max(0.5, damage_per_attack - enemy_armor_temp)
                total_attacks -= 1

            # Calculate the final damage
            if not include_overkill_damage:
                enemy_health = max(0, enemy_health)
                enemy_shield = max(0, enemy_shield)
            total_damage_dealt = target.health + target.shield - enemy_health - enemy_shield
            # Unit modifiers: buffs and upgrades that affect weapon speed and weapon range
            if self.type_id in {
                UnitTypeId.ZERGLING,
                UnitTypeId.MARINE,
                UnitTypeId.MARAUDER,
                UnitTypeId.ADEPT,
                UnitTypeId.HYDRALISK,
                UnitTypeId.PHOENIX,
                UnitTypeId.PLANETARYFORTRESS,
                UnitTypeId.MISSILETURRET,
                UnitTypeId.AUTOTURRET,
            }:
                upgrades: set[UpgradeId] = self._bot_object.state.upgrades
                if (
                    self.type_id == UnitTypeId.ZERGLING
                    # Attack speed calculation only works for our unit
                    and self.is_mine
                    and UpgradeId.ZERGLINGATTACKSPEED in upgrades
                ):
                    # 0.696044921875 for zerglings divided through 1.4 equals (+40% attack speed bonus from the upgrade):
                    weapon_speed /= 1.4
                elif (
                    # Adept ereceive 45% attack speed bonus from glaives
                    self.type_id == UnitTypeId.ADEPT and self.is_mine and UpgradeId.ADEPTPIERCINGATTACK in upgrades
                ):
                    # TODO next patch: if self.type_id is adept: check if attack speed buff is active, instead of upgrade
                    weapon_speed /= 1.45
                elif self.type_id == UnitTypeId.MARINE and BuffId.STIMPACK in self.buffs:
                    # Marine and marauder receive 50% attack speed bonus from stim
                    weapon_speed /= 1.5
                elif self.type_id == UnitTypeId.MARAUDER and BuffId.STIMPACKMARAUDER in self.buffs:
                    weapon_speed /= 1.5
                elif (
                    # TODO always assume that the enemy has the range upgrade researched
                    self.type_id == UnitTypeId.HYDRALISK and self.is_mine and UpgradeId.EVOLVEGROOVEDSPINES in upgrades
                ):
                    weapon_range += 1
                elif self.type_id == UnitTypeId.PHOENIX and self.is_mine and UpgradeId.PHOENIXRANGEUPGRADE in upgrades:
                    weapon_range += 2
                elif (
                    self.type_id in {UnitTypeId.PLANETARYFORTRESS, UnitTypeId.MISSILETURRET, UnitTypeId.AUTOTURRET}
                    and self.is_mine
                    and UpgradeId.HISECAUTOTRACKING in upgrades
                ):
                    weapon_range += 1

            # Append it to the list of damages, e.g. both thor and queen attacks work on colossus
            damages.append((total_damage_dealt, weapon_speed, weapon_range))

        # If no attack was found, return (0, 0, 0)
        if not damages:
            return 0, 0, 0
        # Returns: total potential damage, attack speed, attack range
        return max(damages, key=lambda damage_tuple: damage_tuple[0])

    def calculate_dps_vs_target(
        self,
        target: Unit,
        ignore_armor: bool = False,
        include_overkill_damage: bool = True,
    ) -> float:
        """Returns the DPS against the given target.

        :param target:
        :param ignore_armor:
        :param include_overkill_damage:
        """
        calc_tuple: tuple[float, float, float] = self.calculate_damage_vs_target(
            target, ignore_armor, include_overkill_damage
        )
        # TODO fix for real time? The result may have to be multiplied by 1.4 because of game_speed=normal
        if calc_tuple[1] == 0:
            return 0
        return calc_tuple[0] / calc_tuple[1]

    @property
    def facing(self) -> float:
        """Returns direction the unit is facing as a float in range [0,2π). 0 is in direction of x axis."""
        return self._proto.facing

    def is_facing(self, other_unit: Unit, angle_error: float = 0.05) -> bool:
        """Check if this unit is facing the target unit. If you make angle_error too small, there might be rounding errors. If you make angle_error too big, this function might return false positives.

        :param other_unit:
        :param angle_error:
        """
        # TODO perhaps return default True for units that cannot 'face' another unit? e.g. structures (planetary fortress, bunker, missile turret, photon cannon, spine, spore) or sieged tanks
        angle = math.atan2(
            other_unit.position_tuple[1] - self.position_tuple[1], other_unit.position_tuple[0] - self.position_tuple[0]
        )
        if angle < 0:
            angle += math.pi * 2
        angle_difference = math.fabs(angle - self.facing)
        return angle_difference < angle_error

    @property
    def footprint_radius(self) -> float | None:
        """For structures only.
        For townhalls this returns 2.5
        For barracks, spawning pool, gateway, this returns 1.5
        For supply depot, this returns 1
        For sensor tower, creep tumor, this return 0.5

        NOTE: This can be None if a building doesn't have a creation ability.
        For rich vespene buildings, flying terran buildings, this returns None"""
        return self._type_data.footprint_radius

    @property
    def radius(self) -> float:
        """Half of unit size. See https://liquipedia.net/starcraft2/Unit_Statistics_(Legacy_of_the_Void)"""
        return self._proto.radius

    @property
    def build_progress(self) -> float:
        """Returns completion in range [0,1]."""
        return self._proto.build_progress

    @property
    def is_ready(self) -> bool:
        """Checks if the unit is completed."""
        return self.build_progress == 1

    @property
    def cloak(self) -> CloakState:
        """Returns cloak state.
        See https://github.com/Blizzard/s2client-api/blob/d9ba0a33d6ce9d233c2a4ee988360c188fbe9dbf/include/sc2api/sc2_unit.h#L95
        """
        return CloakState(self._proto.cloak)

    @property
    def is_cloaked(self) -> bool:
        """Checks if the unit is cloaked."""
        return self._proto.cloak in IS_CLOAKED

    @property
    def is_revealed(self) -> bool:
        """Checks if the unit is revealed."""
        return self._proto.cloak == IS_REVEALED

    @property
    def can_be_attacked(self) -> bool:
        """Checks if the unit is revealed or not cloaked and therefore can be attacked."""
        return self._proto.cloak in CAN_BE_ATTACKED

    @cached_property
    def buffs(self) -> frozenset[BuffId]:
        """Returns the set of current buffs the unit has."""
        return frozenset(BuffId(buff_id) for buff_id in self._proto.buff_ids)

    @cached_property
    def is_carrying_minerals(self) -> bool:
        """Checks if a worker or MULE is carrying (gold-)minerals."""
        return not IS_CARRYING_MINERALS.isdisjoint(self.buffs)

    @cached_property
    def is_carrying_vespene(self) -> bool:
        """Checks if a worker is carrying vespene gas."""
        return not IS_CARRYING_VESPENE.isdisjoint(self.buffs)

    @cached_property
    def is_carrying_resource(self) -> bool:
        """Checks if a worker is carrying a resource."""
        return not IS_CARRYING_RESOURCES.isdisjoint(self.buffs)

    @property
    def detect_range(self) -> float:
        """Returns the detection distance of the unit."""
        return self._proto.detect_range

    @cached_property
    def is_detector(self) -> bool:
        """Checks if the unit is a detector. Has to be completed
        in order to detect and Photoncannons also need to be powered."""
        return self.is_ready and (self.type_id in IS_DETECTOR or self.type_id == UNIT_PHOTONCANNON and self.is_powered)

    @property
    def radar_range(self) -> float:
        return self._proto.radar_range

    @property
    def is_selected(self) -> bool:
        """Checks if the unit is currently selected."""
        return self._proto.is_selected

    @property
    def is_on_screen(self) -> bool:
        """Checks if the unit is on the screen."""
        return self._proto.is_on_screen

    @property
    def is_blip(self) -> bool:
        """Checks if the unit is detected by a sensor tower."""
        return self._proto.is_blip

    @property
    def is_powered(self) -> bool:
        """Checks if the unit is powered by a pylon or warppism."""
        return self._proto.is_powered

    @property
    def is_active(self) -> bool:
        """Checks if the unit has an order (e.g. unit is currently moving or attacking, structure is currently training or researching)."""
        return self._proto.is_active

    # PROPERTIES BELOW THIS COMMENT ARE NOT POPULATED FOR SNAPSHOTS

    @property
    def mineral_contents(self) -> int:
        """Returns the amount of minerals remaining in a mineral field."""
        return self._proto.mineral_contents

    @property
    def vespene_contents(self) -> int:
        """Returns the amount of gas remaining in a geyser."""
        return self._proto.vespene_contents

    @property
    def has_vespene(self) -> bool:
        """Checks if a geyser has any gas remaining.
        You can't build extractors on empty geysers."""
        return bool(self._proto.vespene_contents)

    @property
    def is_flying(self) -> bool:
        """Checks if the unit is flying."""
        return self._proto.is_flying or self.has_buff(BuffId.GRAVITONBEAM)

    @property
    def is_burrowed(self) -> bool:
        """Checks if the unit is burrowed."""
        return self._proto.is_burrowed

    @property
    def is_hallucination(self) -> bool:
        """Returns True if the unit is your own hallucination or detected."""
        return self._proto.is_hallucination

    @property
    def attack_upgrade_level(self) -> int:
        """Returns the upgrade level of the units attack.
        # NOTE: Returns 0 for units without a weapon."""
        return self._proto.attack_upgrade_level

    @property
    def armor_upgrade_level(self) -> int:
        """Returns the upgrade level of the units armor."""
        return self._proto.armor_upgrade_level

    @property
    def shield_upgrade_level(self) -> int:
        """Returns the upgrade level of the units shield.
        # NOTE: Returns 0 for units without a shield."""
        return self._proto.shield_upgrade_level

    @property
    def buff_duration_remain(self) -> int:
        """Returns the amount of remaining frames of the visible timer bar.
        # NOTE: Returns 0 for units without a timer bar."""
        return self._proto.buff_duration_remain

    @property
    def buff_duration_max(self) -> int:
        """Returns the maximum amount of frames of the visible timer bar.
        # NOTE: Returns 0 for units without a timer bar."""
        return self._proto.buff_duration_max

    # PROPERTIES BELOW THIS COMMENT ARE NOT POPULATED FOR ENEMIES

    @cached_property
    def orders(self) -> list[UnitOrder]:
        """Returns the a list of the current orders."""
        # TODO: add examples on how to use unit orders
        return [UnitOrder.from_proto(order, self._bot_object) for order in self._proto.orders]

    @cached_property
    def order_target(self) -> int | Point2 | None:
        """Returns the target tag (if it is a Unit) or Point2 (if it is a Position)
        from the first order, returns None if the unit is idle"""
        if self.orders:
            target = self.orders[0].target
            if isinstance(target, int):
                return target
            return Point2.from_proto(target)
        return None

    @property
    def is_idle(self) -> bool:
        """Checks if unit is idle."""
        return not self._proto.orders

    def is_using_ability(self, abilities: AbilityId | set[AbilityId]) -> bool:
        """Check if the unit is using one of the given abilities.
        Only works for own units."""
        if not self.orders:
            return False
        if isinstance(abilities, AbilityId):
            abilities = {abilities}
        return self.orders[0].ability.id in abilities

    @cached_property
    def is_moving(self) -> bool:
        """Checks if the unit is moving.
        Only works for own units."""
        return self.is_using_ability(AbilityId.MOVE)

    @cached_property
    def is_attacking(self) -> bool:
        """Checks if the unit is attacking.
        Only works for own units."""
        return self.is_using_ability(IS_ATTACKING)

    @cached_property
    def is_patrolling(self) -> bool:
        """Checks if a unit is patrolling.
        Only works for own units."""
        return self.is_using_ability(IS_PATROLLING)

    @cached_property
    def is_gathering(self) -> bool:
        """Checks if a unit is on its way to a mineral field or vespene geyser to mine.
        Only works for own units."""
        return self.is_using_ability(IS_GATHERING)

    @cached_property
    def is_returning(self) -> bool:
        """Checks if a unit is returning from mineral field or vespene geyser to deliver resources to townhall.
        Only works for own units."""
        return self.is_using_ability(IS_RETURNING)

    @cached_property
    def is_collecting(self) -> bool:
        """Checks if a unit is gathering or returning.
        Only works for own units."""
        return self.is_using_ability(IS_COLLECTING)

    @cached_property
    def is_constructing_scv(self) -> bool:
        """Checks if the unit is an SCV that is currently building.
        Only works for own units."""
        return self.is_using_ability(IS_CONSTRUCTING_SCV)

    @cached_property
    def is_transforming(self) -> bool:
        """Checks if the unit transforming.
        Only works for own units."""
        return self.type_id in transforming and self.is_using_ability(transforming[self.type_id])

    @cached_property
    def is_repairing(self) -> bool:
        """Checks if the unit is an SCV or MULE that is currently repairing.
        Only works for own units."""
        return self.is_using_ability(IS_REPAIRING)

    @property
    def add_on_tag(self) -> int:
        """Returns the tag of the addon of unit. If the unit has no addon, returns 0."""
        return self._proto.add_on_tag

    @property
    def has_add_on(self) -> bool:
        """Checks if unit has an addon attached."""
        return bool(self._proto.add_on_tag)

    @cached_property
    def has_techlab(self) -> bool:
        """Check if a structure is connected to a techlab addon. This should only ever return True for BARRACKS, FACTORY, STARPORT."""
        return self.add_on_tag in self._bot_object.techlab_tags

    @cached_property
    def has_reactor(self) -> bool:
        """Check if a structure is connected to a reactor addon. This should only ever return True for BARRACKS, FACTORY, STARPORT."""
        return self.add_on_tag in self._bot_object.reactor_tags

    @cached_property
    def add_on_land_position(self) -> Point2:
        """If this unit is an addon (techlab, reactor), returns the position
        where a terran building (BARRACKS, FACTORY, STARPORT) has to land to connect to this addon.

        Why offset (-2.5, 0.5)? See description in 'add_on_position'
        """
        return self.position.offset(Point2((-2.5, 0.5)))

    @cached_property
    def add_on_position(self) -> Point2:
        """If this unit is a terran production building (BARRACKS, FACTORY, STARPORT),
        this property returns the position of where the addon should be, if it should build one or has one attached.

        Why offset (2.5, -0.5)?
        A barracks is of size 3x3. The distance from the center to the edge is 1.5.
        An addon is 2x2 and the distance from the edge to center is 1.
        The total distance from center to center on the x-axis is 2.5.
        The distance from center to center on the y-axis is -0.5.
        """
        return self.position.offset(Point2((2.5, -0.5)))

    @cached_property
    def passengers(self) -> set[Unit]:
        """Returns the units inside a Bunker, CommandCenter, PlanetaryFortress, Medivac, Nydus, Overlord or WarpPrism."""
        return {Unit(unit, self._bot_object) for unit in self._proto.passengers}

    @cached_property
    def passengers_tags(self) -> set[int]:
        """Returns the tags of the units inside a Bunker, CommandCenter, PlanetaryFortress, Medivac, Nydus, Overlord or WarpPrism."""
        return {unit.tag for unit in self._proto.passengers}

    @property
    def cargo_used(self) -> int:
        """Returns how much cargo space is currently used in the unit.
        Note that some units take up more than one space."""
        return self._proto.cargo_space_taken

    @property
    def has_cargo(self) -> bool:
        """Checks if this unit has any units loaded."""
        return bool(self._proto.cargo_space_taken)

    @property
    def cargo_size(self) -> int:
        """Returns the amount of cargo space the unit needs."""
        return self._type_data.cargo_size

    @property
    def cargo_max(self) -> int:
        """How much cargo space is available at maximum."""
        return self._proto.cargo_space_max

    @property
    def cargo_left(self) -> int:
        """Returns how much cargo space is currently left in the unit."""
        return self._proto.cargo_space_max - self._proto.cargo_space_taken

    @property
    def assigned_harvesters(self) -> int:
        """Returns the number of workers currently gathering resources at a geyser or mining base."""
        return self._proto.assigned_harvesters

    @property
    def ideal_harvesters(self) -> int:
        """Returns the ideal harverster count for unit.
        3 for gas buildings, 2*n for n mineral patches on that base."""
        return self._proto.ideal_harvesters

    @property
    def surplus_harvesters(self) -> int:
        """Returns a positive int if unit has too many harvesters mining,
        a negative int if it has too few mining.
        Will only works on townhalls, and gas buildings.
        """
        return self._proto.assigned_harvesters - self._proto.ideal_harvesters

    @property
    def weapon_cooldown(self) -> float:
        """Returns the time until the unit can fire again,
        returns -1 for units that can't attack.
        Usage:
        if unit.weapon_cooldown == 0:
            unit.attack(target)
        elif unit.weapon_cooldown < 0:
            unit.move(closest_allied_unit_because_cant_attack)
        else:
            unit.move(retreatPosition)"""
        if self.can_attack:
            return self._proto.weapon_cooldown
        return -1

    @property
    def weapon_ready(self) -> bool:
        """Checks if the weapon is ready to be fired."""
        return self.weapon_cooldown == 0

    @property
    def engaged_target_tag(self) -> int:
        # TODO What does this do?
        return self._proto.engaged_target_tag

    @cached_property
    def rally_targets(self) -> list[RallyTarget]:
        """Returns the queue of rallytargets of the structure."""
        return [RallyTarget.from_proto(rally_target) for rally_target in self._proto.rally_targets]

    # Unit functions

    def has_buff(self, buff: BuffId) -> bool:
        """Checks if unit has buff 'buff'.

        :param buff:
        """
        assert isinstance(buff, BuffId), f"{buff} is no BuffId"
        return buff in self.buffs

    def train(
        self,
        unit: UnitTypeId,
        queue: bool = False,
        can_afford_check: bool = False,
    ) -> UnitCommand | bool:
        """Orders unit to train another 'unit'.
        Usage: COMMANDCENTER.train(SCV)

        :param unit:
        :param queue:
        :param can_afford_check:
        """
        return self(
            self._bot_object.game_data.units[unit.value].creation_ability.id,
            queue=queue,
            subtract_cost=True,
            can_afford_check=can_afford_check,
        )

    def build(
        self,
        unit: UnitTypeId,
        position: Point2 | Unit | None = None,
        queue: bool = False,
        can_afford_check: bool = False,
    ) -> UnitCommand | bool:
        """Orders unit to build another 'unit' at 'position'.
        Usage::

            SCV.build(COMMANDCENTER, position)
            hatchery.build(UnitTypeId.LAIR)
            # Target for refinery, assimilator and extractor needs to be the vespene geysir unit, not its position
            SCV.build(REFINERY, target_vespene_geysir)

        :param unit:
        :param position:
        :param queue:
        :param can_afford_check:
        """
        if unit in {UnitTypeId.EXTRACTOR, UnitTypeId.ASSIMILATOR, UnitTypeId.REFINERY}:
            assert isinstance(position, Unit), (
                "When building the gas structure, the target needs to be a unit (the vespene geysir) not the position of the vespene geysir."
            )
        return self(
            self._bot_object.game_data.units[unit.value].creation_ability.id,
            target=position,
            queue=queue,
            subtract_cost=True,
            can_afford_check=can_afford_check,
        )

    def build_gas(
        self,
        target_geysir: Unit,
        queue: bool = False,
        can_afford_check: bool = False,
    ) -> UnitCommand | bool:
        """Orders unit to build another 'unit' at 'position'.
        Usage::

            # Target for refinery, assimilator and extractor needs to be the vespene geysir unit, not its position
            SCV.build_gas(target_vespene_geysir)

        :param target_geysir:
        :param queue:
        :param can_afford_check:
        """
        gas_structure_type_id: UnitTypeId = race_gas[self._bot_object.race]
        assert isinstance(target_geysir, Unit), (
            "When building the gas structure, the target needs to be a unit (the vespene geysir) not the position of the vespene geysir."
        )
        return self(
            self._bot_object.game_data.units[gas_structure_type_id.value].creation_ability.id,
            target=target_geysir,
            queue=queue,
            subtract_cost=True,
            can_afford_check=can_afford_check,
        )

    def research(
        self,
        upgrade: UpgradeId,
        queue: bool = False,
        can_afford_check: bool = False,
    ) -> UnitCommand | bool:
        """Orders unit to research 'upgrade'.
        Requires UpgradeId to be passed instead of AbilityId.

        :param upgrade:
        :param queue:
        :param can_afford_check:
        """
        return self(
            self._bot_object.game_data.upgrades[upgrade.value].research_ability.exact_id,
            queue=queue,
            subtract_cost=True,
            can_afford_check=can_afford_check,
        )

    def warp_in(
        self,
        unit: UnitTypeId,
        position: Point2,
        can_afford_check: bool = False,
    ) -> UnitCommand | bool:
        """Orders Warpgate to warp in 'unit' at 'position'.

        :param unit:
        :param queue:
        :param can_afford_check:
        """
        normal_creation_ability = self._bot_object.game_data.units[unit.value].creation_ability.id
        return self(
            warpgate_abilities[normal_creation_ability],
            target=position,
            subtract_cost=True,
            subtract_supply=True,
            can_afford_check=can_afford_check,
        )

    def attack(self, target: Unit | Point2, queue: bool = False) -> UnitCommand | bool:
        """Orders unit to attack. Target can be a Unit or Point2.
        Attacking a position will make the unit move there and attack everything on its way.

        :param target:
        :param queue:
        """
        return self(AbilityId.ATTACK, target=target, queue=queue)

    def smart(self, target: Unit | Point2, queue: bool = False) -> UnitCommand | bool:
        """Orders the smart command. Equivalent to a right-click order.

        :param target:
        :param queue:
        """
        return self(AbilityId.SMART, target=target, queue=queue)

    def gather(self, target: Unit, queue: bool = False) -> UnitCommand | bool:
        """Orders a unit to gather minerals or gas.
        'Target' must be a mineral patch or a gas extraction building.

        :param target:
        :param queue:
        """
        return self(AbilityId.HARVEST_GATHER, target=target, queue=queue)

    def return_resource(self, queue: bool = False) -> UnitCommand | bool:
        """Orders the unit to return resource to the nearest townhall.

        :param queue:
        """
        return self(AbilityId.HARVEST_RETURN, target=None, queue=queue)

    def move(self, position: Unit | Point2, queue: bool = False) -> UnitCommand | bool:
        """Orders the unit to move to 'position'.
        Target can be a Unit (to follow that unit) or Point2.

        :param position:
        :param queue:
        """
        return self(AbilityId.MOVE_MOVE, target=position, queue=queue)

    def hold_position(self, queue: bool = False) -> UnitCommand | bool:
        """Orders a unit to stop moving. It will not move until it gets new orders.

        :param queue:
        """
        return self(AbilityId.HOLDPOSITION, queue=queue)

    def stop(self, queue: bool = False) -> UnitCommand | bool:
        """Orders a unit to stop, but can start to move on its own
        if it is attacked, enemy unit is in range or other friendly
        units need the space.

        :param queue:
        """
        return self(AbilityId.STOP, queue=queue)

    def patrol(self, position: Point2, queue: bool = False) -> UnitCommand | bool:
        """Orders a unit to patrol between position it has when the command starts and the target position.
        Can be queued up to seven patrol points. If the last point is the same as the starting
        point, the unit will patrol in a circle.

        :param position:
        :param queue:
        """
        return self(AbilityId.PATROL, target=position, queue=queue)

    def repair(self, repair_target: Unit, queue: bool = False) -> UnitCommand | bool:
        """Order an SCV or MULE to repair.

        :param repair_target:
        :param queue:
        """
        return self(AbilityId.EFFECT_REPAIR, target=repair_target, queue=queue)

    def __hash__(self) -> int:
        return self.tag

    def __eq__(self, other: Unit | Any) -> bool:
        """
        :param other:
        """
        return self.tag == getattr(other, "tag", -1)

    def __call__(
        self,
        ability: AbilityId,
        target: Point2 | Unit | None = None,
        queue: bool = False,
        subtract_cost: bool = False,
        subtract_supply: bool = False,
        can_afford_check: bool = False,
    ) -> UnitCommand | bool:
        """Deprecated: Stop using self.do() - This may be removed in the future.

        :param ability:
        :param target:
        :param queue:
        :param subtract_cost:
        :param subtract_supply:
        :param can_afford_check:
        """
        if self._bot_object.unit_command_uses_self_do:
            return UnitCommand(ability, self, target=target, queue=queue)
        expected_target: int = self._bot_object.game_data.abilities[ability.value]._proto.target
        # 1: None, 2: Point, 3: Unit, 4: PointOrUnit, 5: PointOrNone
        if target is None and expected_target not in {1, 5}:
            warnings.warn(
                f"{self} got {ability} with no target but expected {TARGET_HELPER[expected_target]}",
                RuntimeWarning,
                stacklevel=2,
            )
        elif isinstance(target, Point2) and expected_target not in {2, 4, 5}:
            warnings.warn(
                f"{self} got {ability} with Point2 as target but expected {TARGET_HELPER[expected_target]}",
                RuntimeWarning,
                stacklevel=2,
            )
        elif isinstance(target, Unit) and expected_target not in {3, 4}:
            warnings.warn(
                f"{self} got {ability} with Unit as target but expected {TARGET_HELPER[expected_target]}",
                RuntimeWarning,
                stacklevel=2,
            )
        return self._bot_object.do(
            UnitCommand(ability, self, target=target, queue=queue),
            subtract_cost=subtract_cost,
            subtract_supply=subtract_supply,
            can_afford_check=can_afford_check,
        )
```

### File: `sc2/unit_command.py`

```python
from __future__ import annotations

from typing import TYPE_CHECKING

from sc2.constants import COMBINEABLE_ABILITIES
from sc2.ids.ability_id import AbilityId
from sc2.position import Point2

if TYPE_CHECKING:
    from sc2.unit import Unit


class UnitCommand:
    def __init__(
        self, ability: AbilityId, unit: Unit, target: Unit | Point2 | None = None, queue: bool = False
    ) -> None:
        """
        :param ability:
        :param unit:
        :param target:
        :param queue:
        """
        assert ability in AbilityId, f"ability {ability} is not in AbilityId"
        assert unit.__class__.__name__ == "Unit", f"unit {unit} is of type {type(unit)}"
        assert any(
            [
                target is None,
                isinstance(target, Point2),
                unit.__class__.__name__ == "Unit",
            ]
        ), f"target {target} is of type {type(target)}"
        assert isinstance(queue, bool), f"queue flag {queue} is of type {type(queue)}"
        self.ability = ability
        self.unit = unit
        self.target = target
        self.queue = queue

    @property
    def combining_tuple(self) -> tuple[AbilityId, Unit | Point2 | None, bool, bool]:
        return self.ability, self.target, self.queue, self.ability in COMBINEABLE_ABILITIES

    def __repr__(self) -> str:
        return f"UnitCommand({self.ability}, {self.unit}, {self.target}, {self.queue})"
```

### File: `sc2/units.py`

```python
# pyre-ignore-all-errors[14, 15, 16]
from __future__ import annotations

import random
from collections.abc import Callable, Generator, Iterable
from itertools import chain
from typing import TYPE_CHECKING, Any

from sc2.ids.unit_typeid import UnitTypeId
from sc2.position import Point2
from sc2.unit import Unit

if TYPE_CHECKING:
    from sc2.bot_ai import BotAI


class Units(list):
    """A collection of Unit objects. Makes it easy to select units by selectors."""

    @classmethod
    def from_proto(cls, units, bot_object: BotAI) -> Units:
        return cls((Unit(raw_unit, bot_object=bot_object) for raw_unit in units), bot_object)

    def __init__(self, units: Iterable[Unit], bot_object: BotAI) -> None:
        """
        :param units:
        :param bot_object:
        """
        super().__init__(units)
        self._bot_object = bot_object

    def __call__(self, unit_types: UnitTypeId | Iterable[UnitTypeId]) -> Units:
        """Creates a new mutable Units object from Units or list object.

        :param unit_types:
        """
        return self.of_type(unit_types)

    def __iter__(self) -> Generator[Unit, None, None]:
        return (item for item in super().__iter__())

    def copy(self) -> Units:
        """Creates a new mutable Units object from Units or list object.

        :param units:
        """
        return Units(self, self._bot_object)

    def __or__(self, other: Units) -> Units:
        """
        :param other:
        """
        return Units(
            chain(
                iter(self),
                (other_unit for other_unit in other if other_unit.tag not in (self_unit.tag for self_unit in self)),
            ),
            self._bot_object,
        )

    def __add__(self, other: Units) -> Units:
        """
        :param other:
        """
        return Units(
            chain(
                iter(self),
                (other_unit for other_unit in other if other_unit.tag not in (self_unit.tag for self_unit in self)),
            ),
            self._bot_object,
        )

    def __and__(self, other: Units) -> Units:
        """
        :param other:
        """
        return Units(
            (other_unit for other_unit in other if other_unit.tag in (self_unit.tag for self_unit in self)),
            self._bot_object,
        )

    def __sub__(self, other: Units) -> Units:
        """
        :param other:
        """
        return Units(
            (self_unit for self_unit in self if self_unit.tag not in (other_unit.tag for other_unit in other)),
            self._bot_object,
        )

    def __hash__(self) -> int:
        return hash(unit.tag for unit in self)

    @property
    def amount(self) -> int:
        return len(self)

    @property
    def empty(self) -> bool:
        return not bool(self)

    @property
    def exists(self) -> bool:
        return bool(self)

    def find_by_tag(self, tag: int) -> Unit | None:
        """
        :param tag:
        """
        for unit in self:
            if unit.tag == tag:
                return unit
        return None

    def by_tag(self, tag: int) -> Unit:
        """
        :param tag:
        """
        unit = self.find_by_tag(tag)
        if unit is None:
            raise KeyError("Unit not found")
        return unit

    @property
    def first(self) -> Unit:
        assert self, "Units object is empty"
        return self[0]

    def take(self, n: int) -> Units:
        """
        :param n:
        """
        if n >= self.amount:
            return self
        return self.subgroup(self[:n])

    @property
    def random(self) -> Unit:
        assert self, "Units object is empty"
        return random.choice(self)

    def random_or(self, other: Any) -> Unit:
        return random.choice(self) if self else other

    def random_group_of(self, n: int) -> Units:
        """Returns self if n >= self.amount."""
        if n < 1:
            return Units([], self._bot_object)
        if n >= self.amount:
            return self
        return self.subgroup(random.sample(self, n))

    def in_attack_range_of(self, unit: Unit, bonus_distance: float = 0) -> Units:
        """Filters units that are in attack range of the given unit.
        This uses the unit and target unit.radius when calculating the distance, so it should be accurate.
        Caution: This may not work well for static structures (bunker, sieged tank, planetary fortress, photon cannon, spine and spore crawler) because it seems attack ranges differ for static / immovable units.

        Example::

            enemy_zerglings = self.enemy_units(UnitTypeId.ZERGLING)
            my_marine = next((unit for unit in self.units if unit.type_id == UnitTypeId.MARINE), None)
            if my_marine:
                all_zerglings_my_marine_can_attack = enemy_zerglings.in_attack_range_of(my_marine)

        Example::

            enemy_mutalisks = self.enemy_units(UnitTypeId.MUTALISK)
            my_marauder = next((unit for unit in self.units if unit.type_id == UnitTypeId.MARAUDER), None)
            if my_marauder:
                all_mutalisks_my_marauder_can_attack = enemy_mutaliskss.in_attack_range_of(my_marauder)
                # Is empty because mutalisk are flying and marauder cannot attack air

        :param unit:
        :param bonus_distance:
        """
        return self.filter(lambda x: unit.target_in_range(x, bonus_distance=bonus_distance))

    def closest_distance_to(self, position: Unit | Point2) -> float:
        """Returns the distance between the closest unit from this group to the target unit.

        Example::

            enemy_zerglings = self.enemy_units(UnitTypeId.ZERGLING)
            my_marine = next((unit for unit in self.units if unit.type_id == UnitTypeId.MARINE), None)
            if my_marine:
                closest_zergling_distance = enemy_zerglings.closest_distance_to(my_marine)
            # Contains the distance between the marine and the closest zergling

        :param position:
        """
        assert self, "Units object is empty"
        if isinstance(position, Unit):
            return min(self._bot_object._distance_squared_unit_to_unit(unit, position) for unit in self) ** 0.5
        return min(self._bot_object._distance_units_to_pos(self, position))

    def furthest_distance_to(self, position: Unit | Point2) -> float:
        """Returns the distance between the furthest unit from this group to the target unit


        Example::

            enemy_zerglings = self.enemy_units(UnitTypeId.ZERGLING)
            my_marine = next((unit for unit in self.units if unit.type_id == UnitTypeId.MARINE), None)
            if my_marine:
                furthest_zergling_distance = enemy_zerglings.furthest_distance_to(my_marine)
                # Contains the distance between the marine and the furthest away zergling

        :param position:
        """
        assert self, "Units object is empty"
        if isinstance(position, Unit):
            return max(self._bot_object._distance_squared_unit_to_unit(unit, position) for unit in self) ** 0.5
        return max(self._bot_object._distance_units_to_pos(self, position))

    def closest_to(self, position: Unit | Point2) -> Unit:
        """Returns the closest unit (from this Units object) to the target unit or position.

        Example::

            enemy_zerglings = self.enemy_units(UnitTypeId.ZERGLING)
            my_marine = next((unit for unit in self.units if unit.type_id == UnitTypeId.MARINE), None)
            if my_marine:
                closest_zergling = enemy_zerglings.closest_to(my_marine)
                # Contains the zergling that is closest to the target marine

        :param position:
        """
        assert self, "Units object is empty"
        if isinstance(position, Unit):
            return min(
                (unit1 for unit1 in self),
                key=lambda unit2: self._bot_object._distance_squared_unit_to_unit(unit2, position),
            )

        distances = self._bot_object._distance_units_to_pos(self, position)
        return min(((unit, dist) for unit, dist in zip(self, distances)), key=lambda my_tuple: my_tuple[1])[0]

    def furthest_to(self, position: Unit | Point2) -> Unit:
        """Returns the furhest unit (from this Units object) to the target unit or position.

        Example::

            enemy_zerglings = self.enemy_units(UnitTypeId.ZERGLING)
            my_marine = next((unit for unit in self.units if unit.type_id == UnitTypeId.MARINE), None)
            if my_marine:
                furthest_zergling = enemy_zerglings.furthest_to(my_marine)
                # Contains the zergling that is furthest away to the target marine

        :param position:
        """
        assert self, "Units object is empty"
        if isinstance(position, Unit):
            return max(
                (unit1 for unit1 in self),
                key=lambda unit2: self._bot_object._distance_squared_unit_to_unit(unit2, position),
            )
        distances = self._bot_object._distance_units_to_pos(self, position)
        return max(((unit, dist) for unit, dist in zip(self, distances)), key=lambda my_tuple: my_tuple[1])[0]

    def closer_than(self, distance: float, position: Unit | Point2) -> Units:
        """Returns all units (from this Units object) that are closer than 'distance' away from target unit or position.

        Example::

            enemy_zerglings = self.enemy_units(UnitTypeId.ZERGLING)
            my_marine = next((unit for unit in self.units if unit.type_id == UnitTypeId.MARINE), None)
            if my_marine:
                close_zerglings = enemy_zerglings.closer_than(3, my_marine)
                # Contains all zerglings that are distance 3 or less away from the marine (does not include unit radius in calculation)

        :param distance:
        :param position:
        """
        if not self:
            return self
        if isinstance(position, Unit):
            distance_squared = distance**2
            return self.subgroup(
                unit
                for unit in self
                if self._bot_object._distance_squared_unit_to_unit(unit, position) < distance_squared
            )
        distances = self._bot_object._distance_units_to_pos(self, position)
        return self.subgroup(unit for unit, dist in zip(self, distances) if dist < distance)

    def further_than(self, distance: float, position: Unit | Point2) -> Units:
        """Returns all units (from this Units object) that are further than 'distance' away from target unit or position.

        Example::

            enemy_zerglings = self.enemy_units(UnitTypeId.ZERGLING)
            my_marine = next((unit for unit in self.units if unit.type_id == UnitTypeId.MARINE), None)
            if my_marine:
                far_zerglings = enemy_zerglings.further_than(3, my_marine)
                # Contains all zerglings that are distance 3 or more away from the marine (does not include unit radius in calculation)

        :param distance:
        :param position:
        """
        if not self:
            return self
        if isinstance(position, Unit):
            distance_squared = distance**2
            return self.subgroup(
                unit
                for unit in self
                if distance_squared < self._bot_object._distance_squared_unit_to_unit(unit, position)
            )
        distances = self._bot_object._distance_units_to_pos(self, position)
        return self.subgroup(unit for unit, dist in zip(self, distances) if distance < dist)

    def in_distance_between(
        self, position: Unit | Point2 | tuple[float, float], distance1: float, distance2: float
    ) -> Units:
        """Returns units that are further than distance1 and closer than distance2 to unit or position.

        Example::

            enemy_zerglings = self.enemy_units(UnitTypeId.ZERGLING)
            my_marine = next((unit for unit in self.units if unit.type_id == UnitTypeId.MARINE), None)
            if my_marine:
                zerglings_filtered = enemy_zerglings.in_distance_between(my_marine, 3, 5)
                # Contains all zerglings that are between distance 3 and 5 away from the marine (does not include unit radius in calculation)

        :param position:
        :param distance1:
        :param distance2:
        """
        if not self:
            return self
        if isinstance(position, Unit):
            distance1_squared = distance1**2
            distance2_squared = distance2**2
            return self.subgroup(
                unit
                for unit in self
                if distance1_squared
                < self._bot_object._distance_squared_unit_to_unit(unit, position)
                < distance2_squared
            )
        distances = self._bot_object._distance_units_to_pos(self, position)
        return self.subgroup(unit for unit, dist in zip(self, distances) if distance1 < dist < distance2)

    def closest_n_units(self, position: Unit | Point2, n: int) -> Units:
        """Returns the n closest units in distance to position.

        Example::

            enemy_zerglings = self.enemy_units(UnitTypeId.ZERGLING)
            my_marine = next((unit for unit in self.units if unit.type_id == UnitTypeId.MARINE), None)
            if my_marine:
                zerglings_filtered = enemy_zerglings.closest_n_units(my_marine, 5)
                # Contains 5 zerglings that are the closest to the marine

        :param position:
        :param n:
        """
        if not self:
            return self
        return self.subgroup(self._list_sorted_by_distance_to(position)[:n])

    def furthest_n_units(self, position: Unit | Point2, n: int) -> Units:
        """Returns the n furhest units in distance to position.

        Example::

            enemy_zerglings = self.enemy_units(UnitTypeId.ZERGLING)
            my_marine = next((unit for unit in self.units if unit.type_id == UnitTypeId.MARINE), None)
            if my_marine:
                zerglings_filtered = enemy_zerglings.furthest_n_units(my_marine, 5)
                # Contains 5 zerglings that are the furthest to the marine

        :param position:
        :param n:
        """
        if not self:
            return self
        return self.subgroup(self._list_sorted_by_distance_to(position)[-n:])

    def in_distance_of_group(self, other_units: Units, distance: float) -> Units:
        """Returns units that are closer than distance from any unit in the other units object.

        :param other_units:
        :param distance:
        """
        assert other_units, "Other units object is empty"
        # Return self because there are no enemies
        if not self:
            return self
        distance_squared = distance**2
        if len(self) == 1:
            if any(
                self._bot_object._distance_squared_unit_to_unit(self[0], target) < distance_squared
                for target in other_units
            ):
                return self
            return self.subgroup([])

        return self.subgroup(
            self_unit
            for self_unit in self
            if any(
                self._bot_object._distance_squared_unit_to_unit(self_unit, other_unit) < distance_squared
                for other_unit in other_units
            )
        )

    def in_closest_distance_to_group(self, other_units: Units) -> Unit:
        """Returns unit in shortest distance from any unit in self to any unit in group.

        Loops over all units in self, then loops over all units in other_units and calculates the shortest distance. Returns the units that is closest to any unit of 'other_units'.

        :param other_units:
        """
        assert self, "Units object is empty"
        assert other_units, "Given units object is empty"
        return min(
            self,
            key=lambda self_unit: min(
                self._bot_object._distance_squared_unit_to_unit(self_unit, other_unit) for other_unit in other_units
            ),
        )

    def _list_sorted_closest_to_distance(self, position: Unit | Point2, distance: float) -> list[Unit]:
        """This function should be a bit faster than using units.sorted(key=lambda u: u.distance_to(position))

        :param position:
        :param distance:
        """
        if isinstance(position, Unit):
            return sorted(
                self,
                key=lambda unit: abs(self._bot_object._distance_squared_unit_to_unit(unit, position) - distance),
                reverse=True,
            )
        distances = self._bot_object._distance_units_to_pos(self, position)
        unit_dist_dict = {unit.tag: dist for unit, dist in zip(self, distances)}
        return sorted(self, key=lambda unit2: abs(unit_dist_dict[unit2.tag] - distance), reverse=True)

    def n_closest_to_distance(self, position: Point2, distance: float, n: int) -> Units:
        """Returns n units that are the closest to distance away.
        For example if the distance is set to 5 and you want 3 units, from units with distance [3, 4, 5, 6, 7] to position,
        the units with distance [4, 5, 6] will be returned

        :param position:
        :param distance:
        """
        return self.subgroup(self._list_sorted_closest_to_distance(position=position, distance=distance)[:n])

    def n_furthest_to_distance(self, position: Point2, distance: float, n: int) -> Units:
        """Inverse of the function 'n_closest_to_distance', returns the furthest units instead

        :param position:
        :param distance:
        """
        return self.subgroup(self._list_sorted_closest_to_distance(position=position, distance=distance)[-n:])

    def subgroup(self, units: Iterable[Unit]) -> Units:
        """Creates a new mutable Units object from Units or list object.

        :param units:
        """
        return Units(units, self._bot_object)

    def filter(self, pred: Callable[[Unit], Any]) -> Units:
        """Filters the current Units object and returns a new Units object.

        Example::

            from sc2.ids.unit_typeid import UnitTypeId
            my_marines = self.units.filter(lambda unit: unit.type_id == UnitTypeId.MARINE)

            completed_structures = self.structures.filter(lambda structure: structure.is_ready)

            queens_with_energy_to_inject = self.units.filter(lambda unit: unit.type_id == UnitTypeId.QUEEN and unit.energy >= 25)

            orbitals_with_energy_to_mule = self.structures.filter(lambda structure: structure.type_id == UnitTypeId.ORBITALCOMMAND and structure.energy >= 50)

            my_units_that_can_shoot_up = self.units.filter(lambda unit: unit.can_attack_air)

        See more unit properties in unit.py

        :param pred:
        """
        assert callable(pred), "Function is not callable"
        return self.subgroup(filter(pred, self))

    def sorted(self, key: Callable[[Unit], Any], reverse: bool = False) -> Units:
        return self.subgroup(sorted(self, key=key, reverse=reverse))

    def _list_sorted_by_distance_to(self, position: Unit | Point2, reverse: bool = False) -> list[Unit]:
        """This function should be a bit faster than using units.sorted(key=lambda u: u.distance_to(position))

        :param position:
        :param reverse:
        """
        if isinstance(position, Unit):
            return sorted(
                self, key=lambda unit: self._bot_object._distance_squared_unit_to_unit(unit, position), reverse=reverse
            )
        distances = self._bot_object._distance_units_to_pos(self, position)
        unit_dist_dict = {unit.tag: dist for unit, dist in zip(self, distances)}
        return sorted(self, key=lambda unit2: unit_dist_dict[unit2.tag], reverse=reverse)

    def sorted_by_distance_to(self, position: Unit | Point2, reverse: bool = False) -> Units:
        """This function should be a bit faster than using units.sorted(key=lambda u: u.distance_to(position))

        :param position:
        :param reverse:
        """
        return self.subgroup(self._list_sorted_by_distance_to(position, reverse=reverse))

    def tags_in(self, other: Iterable[int]) -> Units:
        """Filters all units that have their tags in the 'other' set/list/dict

        Example::

            my_inject_queens = self.units.tags_in(self.queen_tags_assigned_to_do_injects)

            # Do not use the following as it is slower because it first loops over all units to filter out if they are queens and loops over those again to check if their tags are in the list/set
            my_inject_queens_slow = self.units(QUEEN).tags_in(self.queen_tags_assigned_to_do_injects)

        :param other:
        """
        return self.filter(lambda unit: unit.tag in other)

    def tags_not_in(self, other: Iterable[int]) -> Units:
        """Filters all units that have their tags not in the 'other' set/list/dict

        Example::

            my_non_inject_queens = self.units.tags_not_in(self.queen_tags_assigned_to_do_injects)

            # Do not use the following as it is slower because it first loops over all units to filter out if they are queens and loops over those again to check if their tags are in the list/set
            my_non_inject_queens_slow = self.units(QUEEN).tags_not_in(self.queen_tags_assigned_to_do_injects)

        :param other:
        """
        return self.filter(lambda unit: unit.tag not in other)

    def of_type(self, other: UnitTypeId | Iterable[UnitTypeId]) -> Units:
        """Filters all units that are of a specific type

        Example::

            # Use a set instead of lists in the argument
            some_attack_units = self.units.of_type({ZERGLING, ROACH, HYDRALISK, BROODLORD})

        :param other:
        """
        if isinstance(other, UnitTypeId):
            other = {other}
        elif isinstance(other, list):
            other = set(other)
        return self.filter(lambda unit: unit.type_id in other)

    def exclude_type(self, other: UnitTypeId | Iterable[UnitTypeId]) -> Units:
        """Filters all units that are not of a specific type

        Example::

            # Use a set instead of lists in the argument
            ignore_units = self.enemy_units.exclude_type({LARVA, EGG, OVERLORD})

        :param other:
        """
        if isinstance(other, UnitTypeId):
            other = {other}
        elif isinstance(other, list):
            other = set(other)
        return self.filter(lambda unit: unit.type_id not in other)

    def same_tech(self, other: set[UnitTypeId]) -> Units:
        """Returns all structures that have the same base structure.

        Untested: This should return the equivalents for WarpPrism, Observer, Overseer, SupplyDepot and others

        Example::

            # All command centers, flying command centers, orbital commands, flying orbital commands, planetary fortress
            terran_townhalls = self.townhalls.same_tech(UnitTypeId.COMMANDCENTER)

            # All hatcheries, lairs and hives
            zerg_townhalls = self.townhalls.same_tech({UnitTypeId.HATCHERY})

            # All spires and greater spires
            spires = self.townhalls.same_tech({UnitTypeId.SPIRE})
            # The following returns the same
            spires = self.townhalls.same_tech({UnitTypeId.GREATERSPIRE})

            # This also works with multiple unit types
            zerg_townhalls_and_spires = self.structures.same_tech({UnitTypeId.HATCHERY, UnitTypeId.SPIRE})

        :param other:
        """
        assert isinstance(other, set), (
            "Please use a set as this filter function is already fairly slow. For example"
            + " 'self.units.same_tech({UnitTypeId.LAIR})'"
        )
        tech_alias_types: set[int] = {u.value for u in other}
        unit_data = self._bot_object.game_data.units
        for unit_type in other:
            for same in unit_data[unit_type.value]._proto.tech_alias:
                tech_alias_types.add(same)
        return self.filter(
            lambda unit: unit._proto.unit_type in tech_alias_types
            or any(same in tech_alias_types for same in unit._type_data._proto.tech_alias)
        )

    def same_unit(self, other: UnitTypeId | Iterable[UnitTypeId]) -> Units:
        """Returns all units that have the same base unit while being in different modes.

        Untested: This should return the equivalents for WarpPrism, Observer, Overseer, SupplyDepot and other units that have different modes but still act as the same unit

        Example::

            # All command centers on the ground and flying
            ccs = self.townhalls.same_unit(UnitTypeId.COMMANDCENTER)

            # All orbital commands on the ground and flying
            ocs = self.townhalls.same_unit(UnitTypeId.ORBITALCOMMAND)

            # All roaches and burrowed roaches
            roaches = self.units.same_unit(UnitTypeId.ROACH)
            # This is useful because roach has a different type id when burrowed
            burrowed_roaches = self.units(UnitTypeId.ROACHBURROWED)

        :param other:
        """
        if isinstance(other, UnitTypeId):
            other = {other}
        unit_alias_types: set[int] = {u.value for u in other}
        unit_data = self._bot_object.game_data.units
        for unit_type in other:
            unit_alias_types.add(unit_data[unit_type.value]._proto.unit_alias)
        unit_alias_types.discard(0)
        return self.filter(
            lambda unit: unit._proto.unit_type in unit_alias_types
            or unit._type_data._proto.unit_alias in unit_alias_types
        )

    @property
    def center(self) -> Point2:
        """Returns the central position of all units."""
        assert self, "Units object is empty"
        return Point2(
            (
                sum(unit._proto.pos.x for unit in self) / self.amount,
                sum(unit._proto.pos.y for unit in self) / self.amount,
            )
        )

    @property
    def selected(self) -> Units:
        """Returns all units that are selected by the human player."""
        return self.filter(lambda unit: unit.is_selected)

    @property
    def tags(self) -> set[int]:
        """Returns all unit tags as a set."""
        return {unit.tag for unit in self}

    @property
    def ready(self) -> Units:
        """Returns all structures that are ready (construction complete)."""
        return self.filter(lambda unit: unit.is_ready)

    @property
    def not_ready(self) -> Units:
        """Returns all structures that are not ready (construction not complete)."""
        return self.filter(lambda unit: not unit.is_ready)

    @property
    def idle(self) -> Units:
        """Returns all units or structures that are doing nothing (unit is standing still, structure is doing nothing)."""
        return self.filter(lambda unit: unit.is_idle)

    @property
    def owned(self) -> Units:
        """Deprecated: All your units."""
        return self.filter(lambda unit: unit.is_mine)

    @property
    def enemy(self) -> Units:
        """Deprecated: All enemy units."""
        return self.filter(lambda unit: unit.is_enemy)

    @property
    def flying(self) -> Units:
        """Returns all units that are flying."""
        return self.filter(lambda unit: unit.is_flying)

    @property
    def not_flying(self) -> Units:
        """Returns all units that not are flying."""
        return self.filter(lambda unit: not unit.is_flying)

    @property
    def structure(self) -> Units:
        """Deprecated: All structures."""
        return self.filter(lambda unit: unit.is_structure)

    @property
    def not_structure(self) -> Units:
        """Deprecated: All units that are not structures."""
        return self.filter(lambda unit: not unit.is_structure)

    @property
    def gathering(self) -> Units:
        """Returns all workers that are mining minerals or vespene (gather command)."""
        return self.filter(lambda unit: unit.is_gathering)

    @property
    def returning(self) -> Units:
        """Returns all workers that are carrying minerals or vespene and are returning to a townhall."""
        return self.filter(lambda unit: unit.is_returning)

    @property
    def collecting(self) -> Units:
        """Returns all workers that are mining or returning resources."""
        return self.filter(lambda unit: unit.is_collecting)

    @property
    def visible(self) -> Units:
        """Returns all units or structures that are visible.
        TODO: add proper description on which units are exactly visible (not snapshots?)"""
        return self.filter(lambda unit: unit.is_visible)

    @property
    def mineral_field(self) -> Units:
        """Returns all units that are mineral fields."""
        return self.filter(lambda unit: unit.is_mineral_field)

    @property
    def vespene_geyser(self) -> Units:
        """Returns all units that are vespene geysers."""
        return self.filter(lambda unit: unit.is_vespene_geyser)

    @property
    def prefer_idle(self) -> Units:
        """Sorts units based on if they are idle. Idle units come first."""
        return self.sorted(lambda unit: unit.is_idle, reverse=True)
```

### File: `sc2/versions.py`

```python
VERSIONS = [
    {
        "base-version": 52910,
        "data-hash": "8D9FEF2E1CF7C6C9CBE4FBCA830DDE1C",
        "fixed-hash": "009BC85EF547B51EBF461C83A9CBAB30",
        "label": "3.13",
        "replay-hash": "47BFE9D10F26B0A8B74C637D6327BF3C",
        "version": 52910,
    },
    {
        "base-version": 53644,
        "data-hash": "CA275C4D6E213ED30F80BACCDFEDB1F5",
        "fixed-hash": "29198786619C9011735BCFD378E49CB6",
        "label": "3.14",
        "replay-hash": "5AF236FC012ADB7289DB493E63F73FD5",
        "version": 53644,
    },
    {
        "base-version": 54518,
        "data-hash": "BBF619CCDCC80905350F34C2AF0AB4F6",
        "fixed-hash": "D5963F25A17D9E1EA406FF6BBAA9B736",
        "label": "3.15",
        "replay-hash": "43530321CF29FD11482AB9CBA3EB553D",
        "version": 54518,
    },
    {
        "base-version": 54518,
        "data-hash": "6EB25E687F8637457538F4B005950A5E",
        "fixed-hash": "D5963F25A17D9E1EA406FF6BBAA9B736",
        "label": "3.15.1",
        "replay-hash": "43530321CF29FD11482AB9CBA3EB553D",
        "version": 54724,
    },
    {
        "base-version": 55505,
        "data-hash": "60718A7CA50D0DF42987A30CF87BCB80",
        "fixed-hash": "0189B2804E2F6BA4C4591222089E63B2",
        "label": "3.16",
        "replay-hash": "B11811B13F0C85C29C5D4597BD4BA5A4",
        "version": 55505,
    },
    {
        "base-version": 55958,
        "data-hash": "5BD7C31B44525DAB46E64C4602A81DC2",
        "fixed-hash": "717B05ACD26C108D18A219B03710D06D",
        "label": "3.16.1",
        "replay-hash": "21C8FA403BB1194E2B6EB7520016B958",
        "version": 55958,
    },
    {
        "base-version": 56787,
        "data-hash": "DFD1F6607F2CF19CB4E1C996B2563D9B",
        "fixed-hash": "4E1C17AB6A79185A0D87F68D1C673CD9",
        "label": "3.17",
        "replay-hash": "D0296961C9EA1356F727A2468967A1E2",
        "version": 56787,
    },
    {
        "base-version": 56787,
        "data-hash": "3F2FCED08798D83B873B5543BEFA6C4B",
        "fixed-hash": "4474B6B7B0D1423DAA76B9623EF2E9A9",
        "label": "3.17.1",
        "replay-hash": "D0296961C9EA1356F727A2468967A1E2",
        "version": 57218,
    },
    {
        "base-version": 56787,
        "data-hash": "C690FC543082D35EA0AAA876B8362BEA",
        "fixed-hash": "4474B6B7B0D1423DAA76B9623EF2E9A9",
        "label": "3.17.2",
        "replay-hash": "D0296961C9EA1356F727A2468967A1E2",
        "version": 57490,
    },
    {
        "base-version": 57507,
        "data-hash": "1659EF34997DA3470FF84A14431E3A86",
        "fixed-hash": "95666060F129FD267C5A8135A8920AA2",
        "label": "3.18",
        "replay-hash": "06D650F850FDB2A09E4B01D2DF8C433A",
        "version": 57507,
    },
    {
        "base-version": 58400,
        "data-hash": "2B06AEE58017A7DF2A3D452D733F1019",
        "fixed-hash": "2CFE1B8757DA80086DD6FD6ECFF21AC6",
        "label": "3.19",
        "replay-hash": "227B6048D55535E0FF5607746EBCC45E",
        "version": 58400,
    },
    {
        "base-version": 58400,
        "data-hash": "D9B568472880CC4719D1B698C0D86984",
        "fixed-hash": "CE1005E9B145BDFC8E5E40CDEB5E33BB",
        "label": "3.19.1",
        "replay-hash": "227B6048D55535E0FF5607746EBCC45E",
        "version": 58600,
    },
    {
        "base-version": 59587,
        "data-hash": "9B4FD995C61664831192B7DA46F8C1A1",
        "fixed-hash": "D5D5798A9CCD099932C8F855C8129A7C",
        "label": "4.0",
        "replay-hash": "BB4DA41B57D490BD13C13A594E314BA4",
        "version": 59587,
    },
    {
        "base-version": 60196,
        "data-hash": "1B8ACAB0C663D5510941A9871B3E9FBE",
        "fixed-hash": "9327F9AF76CF11FC43D20E3E038B1B7A",
        "label": "4.1",
        "replay-hash": "AEA0C2A9D56E02C6B7D21E889D6B9B2F",
        "version": 60196,
    },
    {
        "base-version": 60321,
        "data-hash": "5C021D8A549F4A776EE9E9C1748FFBBC",
        "fixed-hash": "C53FA3A7336EDF320DCEB0BC078AEB0A",
        "label": "4.1.1",
        "replay-hash": "8EE054A8D98C7B0207E709190A6F3953",
        "version": 60321,
    },
    {
        "base-version": 60321,
        "data-hash": "33D9FE28909573253B7FC352CE7AEA40",
        "fixed-hash": "FEE6F86A211380DF509F3BBA58A76B87",
        "label": "4.1.2",
        "replay-hash": "8EE054A8D98C7B0207E709190A6F3953",
        "version": 60604,
    },
    {
        "base-version": 60321,
        "data-hash": "F486693E00B2CD305B39E0AB254623EB",
        "fixed-hash": "AF7F5499862F497C7154CB59167FEFB3",
        "label": "4.1.3",
        "replay-hash": "8EE054A8D98C7B0207E709190A6F3953",
        "version": 61021,
    },
    {
        "base-version": 60321,
        "data-hash": "2E2A3F6E0BAFE5AC659C4D39F13A938C",
        "fixed-hash": "F9A68CF1FBBF867216FFECD9EAB72F4A",
        "label": "4.1.4",
        "replay-hash": "8EE054A8D98C7B0207E709190A6F3953",
        "version": 61545,
    },
    {
        "base-version": 62347,
        "data-hash": "C0C0E9D37FCDBC437CE386C6BE2D1F93",
        "fixed-hash": "A5C4BE991F37F1565097AAD2A707FC4C",
        "label": "4.2",
        "replay-hash": "2167A7733637F3AFC49B210D165219A7",
        "version": 62347,
    },
    {
        "base-version": 62848,
        "data-hash": "29BBAC5AFF364B6101B661DB468E3A37",
        "fixed-hash": "ABAF9318FE79E84485BEC5D79C31262C",
        "label": "4.2.1",
        "replay-hash": "A7ACEC5759ADB459A5CEC30A575830EC",
        "version": 62848,
    },
    {
        "base-version": 63454,
        "data-hash": "3CB54C86777E78557C984AB1CF3494A0",
        "fixed-hash": "A9DCDAA97F7DA07F6EF29C0BF4DFC50D",
        "label": "4.2.2",
        "replay-hash": "A7ACEC5759ADB459A5CEC30A575830EC",
        "version": 63454,
    },
    {
        "base-version": 64469,
        "data-hash": "C92B3E9683D5A59E08FC011F4BE167FF",
        "fixed-hash": "DDF3E0A6C00DC667F59BF90F793C71B8",
        "label": "4.3",
        "replay-hash": "6E80072968515101AF08D3953FE3EEBA",
        "version": 64469,
    },
    {
        "base-version": 65094,
        "data-hash": "E5A21037AA7A25C03AC441515F4E0644",
        "fixed-hash": "09EF8E9B96F14C5126F1DB5378D15F3A",
        "label": "4.3.1",
        "replay-hash": "DD9B57C516023B58F5B588377880D93A",
        "version": 65094,
    },
    {
        "base-version": 65384,
        "data-hash": "B6D73C85DFB70F5D01DEABB2517BF11C",
        "fixed-hash": "615C1705E4C7A5FD8690B3FD376C1AFE",
        "label": "4.3.2",
        "replay-hash": "DD9B57C516023B58F5B588377880D93A",
        "version": 65384,
    },
    {
        "base-version": 65895,
        "data-hash": "BF41339C22AE2EDEBEEADC8C75028F7D",
        "fixed-hash": "C622989A4C0AF7ED5715D472C953830B",
        "label": "4.4",
        "replay-hash": "441BBF1A222D5C0117E85B118706037F",
        "version": 65895,
    },
    {
        "base-version": 66668,
        "data-hash": "C094081D274A39219061182DBFD7840F",
        "fixed-hash": "1C236A42171AAC6DD1D5E50D779C522D",
        "label": "4.4.1",
        "replay-hash": "21D5B4B4D5175C562CF4C4A803C995C6",
        "version": 66668,
    },
    {
        "base-version": 67188,
        "data-hash": "2ACF84A7ECBB536F51FC3F734EC3019F",
        "fixed-hash": "2F0094C990E0D4E505570195F96C2A0C",
        "label": "4.5",
        "replay-hash": "E9873B3A3846F5878CEE0D1E2ADD204A",
        "version": 67188,
    },
    {
        "base-version": 67188,
        "data-hash": "6D239173B8712461E6A7C644A5539369",
        "fixed-hash": "A1BC35751ACC34CF887321A357B40158",
        "label": "4.5.1",
        "replay-hash": "E9873B3A3846F5878CEE0D1E2ADD204A",
        "version": 67344,
    },
    {
        "base-version": 67926,
        "data-hash": "7DE59231CBF06F1ECE9A25A27964D4AE",
        "fixed-hash": "570BEB69151F40D010E89DE1825AE680",
        "label": "4.6",
        "replay-hash": "DA662F9091DF6590A5E323C21127BA5A",
        "version": 67926,
    },
    {
        "base-version": 67926,
        "data-hash": "BEA99B4A8E7B41E62ADC06D194801BAB",
        "fixed-hash": "309E45F53690F8D1108F073ABB4D4734",
        "label": "4.6.1",
        "replay-hash": "DA662F9091DF6590A5E323C21127BA5A",
        "version": 68195,
    },
    {
        "base-version": 69232,
        "data-hash": "B3E14058F1083913B80C20993AC965DB",
        "fixed-hash": "21935E776237EF12B6CC73E387E76D6E",
        "label": "4.6.2",
        "replay-hash": "A230717B315D83ACC3697B6EC28C3FF6",
        "version": 69232,
    },
    {
        "base-version": 70154,
        "data-hash": "8E216E34BC61ABDE16A59A672ACB0F3B",
        "fixed-hash": "09CD819C667C67399F5131185334243E",
        "label": "4.7",
        "replay-hash": "9692B04D6E695EF08A2FB920979E776C",
        "version": 70154,
    },
    {
        "base-version": 70154,
        "data-hash": "94596A85191583AD2EBFAE28C5D532DB",
        "fixed-hash": "0AE50F82AC1A7C0DCB6A290D7FBA45DB",
        "label": "4.7.1",
        "replay-hash": "D74FBB3CB0897A3EE8F44E78119C4658",
        "version": 70326,
    },
    {
        "base-version": 71061,
        "data-hash": "760581629FC458A1937A05ED8388725B",
        "fixed-hash": "815C099DF1A17577FDC186FDB1381B16",
        "label": "4.8",
        "replay-hash": "BD692311442926E1F0B7C17E9ABDA34B",
        "version": 71061,
    },
    {
        "base-version": 71523,
        "data-hash": "FCAF3F050B7C0CC7ADCF551B61B9B91E",
        "fixed-hash": "4593CC331691620509983E92180A309A",
        "label": "4.8.1",
        "replay-hash": "BD692311442926E1F0B7C17E9ABDA34B",
        "version": 71523,
    },
    {
        "base-version": 71663,
        "data-hash": "FE90C92716FC6F8F04B74268EC369FA5",
        "fixed-hash": "1DBF3819F3A7367592648632CC0D5BFD",
        "label": "4.8.2",
        "replay-hash": "E43A9885B3EFAE3D623091485ECCCB6C",
        "version": 71663,
    },
    {
        "base-version": 72282,
        "data-hash": "0F14399BBD0BA528355FF4A8211F845B",
        "fixed-hash": "E9958B2CB666DCFE101D23AF87DB8140",
        "label": "4.8.3",
        "replay-hash": "3AF3657F55AB961477CE268F5CA33361",
        "version": 72282,
    },
    {
        "base-version": 73286,
        "data-hash": "CD040C0675FD986ED37A4CA3C88C8EB5",
        "fixed-hash": "62A146F7A0D19A8DD05BF011631B31B8",
        "label": "4.8.4",
        "replay-hash": "EE3A89F443BE868EBDA33A17C002B609",
        "version": 73286,
    },
    {
        "base-version": 73559,
        "data-hash": "B2465E73AED597C74D0844112D582595",
        "fixed-hash": "EF0A43C33413613BC7343B86C0A7CC92",
        "label": "4.8.5",
        "replay-hash": "147388D35E76861BD4F590F8CC5B7B0B",
        "version": 73559,
    },
    {
        "base-version": 73620,
        "data-hash": "AA18FEAD6573C79EF707DF44ABF1BE61",
        "fixed-hash": "4D76491CCAE756F0498D1C5B2973FF9C",
        "label": "4.8.6",
        "replay-hash": "147388D35E76861BD4F590F8CC5B7B0B",
        "version": 73620,
    },
    {
        "base-version": 74071,
        "data-hash": "70C74A2DCA8A0D8E7AE8647CAC68ACCA",
        "fixed-hash": "C4A3F01B4753245296DC94BC1B5E9B36",
        "label": "4.9",
        "replay-hash": "19D15E5391FACB379BFCA262CA8FD208",
        "version": 74071,
    },
    {
        "base-version": 74456,
        "data-hash": "218CB2271D4E2FA083470D30B1A05F02",
        "fixed-hash": "E82051387C591CAB1212B64073759826",
        "label": "4.9.1",
        "replay-hash": "1586ADF060C26219FF3404673D70245B",
        "version": 74456,
    },
    {
        "base-version": 74741,
        "data-hash": "614480EF79264B5BD084E57F912172FF",
        "fixed-hash": "500CC375B7031C8272546B78E9BE439F",
        "label": "4.9.2",
        "replay-hash": "A7FAC56F940382E05157EAB19C932E3A",
        "version": 74741,
    },
    {
        "base-version": 75025,
        "data-hash": "C305368C63621480462F8F516FB64374",
        "fixed-hash": "DEE7842C8BCB6874EC254AA3D45365F7",
        "label": "4.9.3",
        "replay-hash": "A7FAC56F940382E05157EAB19C932E3A",
        "version": 75025,
    },
    {
        "base-version": 75689,
        "data-hash": "B89B5D6FA7CBF6452E721311BFBC6CB2",
        "fixed-hash": "2B2097DC4AD60A2D1E1F38691A1FF111",
        "label": "4.10",
        "replay-hash": "6A60E59031A7DB1B272EE87E51E4C7CD",
        "version": 75689,
    },
    {
        "base-version": 75800,
        "data-hash": "DDFFF9EC4A171459A4F371C6CC189554",
        "fixed-hash": "1FB8FAF4A87940621B34F0B8F6FDDEA6",
        "label": "4.10.1",
        "replay-hash": "6A60E59031A7DB1B272EE87E51E4C7CD",
        "version": 75800,
    },
    {
        "base-version": 76052,
        "data-hash": "D0F1A68AA88BA90369A84CD1439AA1C3",
        "fixed-hash": "",
        "label": "4.10.2",
        "replay-hash": "",
        "version": 76052,
    },
    {
        "base-version": 76114,
        "data-hash": "CDB276D311F707C29BA664B7754A7293",
        "fixed-hash": "",
        "label": "4.10.3",
        "replay-hash": "",
        "version": 76114,
    },
    {
        "base-version": 76811,
        "data-hash": "FF9FA4EACEC5F06DEB27BD297D73ED67",
        "fixed-hash": "",
        "label": "4.10.4",
        "replay-hash": "",
        "version": 76811,
    },
    {
        "base-version": 77379,
        "data-hash": "70E774E722A58287EF37D487605CD384",
        "fixed-hash": "",
        "label": "4.11.0",
        "replay-hash": "",
        "version": 77379,
    },
    {
        "base-version": 77379,
        "data-hash": "F92D1127A291722120AC816F09B2E583",
        "fixed-hash": "",
        "label": "4.11.1",
        "replay-hash": "",
        "version": 77474,
    },
    {
        "base-version": 77535,
        "data-hash": "FC43E0897FCC93E4632AC57CBC5A2137",
        "fixed-hash": "",
        "label": "4.11.2",
        "replay-hash": "",
        "version": 77535,
    },
    {
        "base-version": 77661,
        "data-hash": "A15B8E4247434B020086354F39856C51",
        "fixed-hash": "",
        "label": "4.11.3",
        "replay-hash": "",
        "version": 77661,
    },
    {
        "base-version": 78285,
        "data-hash": "69493AFAB5C7B45DDB2F3442FD60F0CF",
        "fixed-hash": "21D2EBD5C79DECB3642214BAD4A7EF56",
        "label": "4.11.4",
        "replay-hash": "CAB5C056EDBDA415C552074BF363CC85",
        "version": 78285,
    },
    {
        "base-version": 79998,
        "data-hash": "B47567DEE5DC23373BFF57194538DFD3",
        "fixed-hash": "0A698A1B072BC4B087F44DDEF0BE361E",
        "label": "4.12.0",
        "replay-hash": "9E15AA09E15FE3AF3655126CEEC7FF42",
        "version": 79998,
    },
    {
        "base-version": 80188,
        "data-hash": "44DED5AED024D23177C742FC227C615A",
        "fixed-hash": "0A698A1B072BC4B087F44DDEF0BE361E",
        "label": "4.12.1",
        "replay-hash": "9E15AA09E15FE3AF3655126CEEC7FF42",
        "version": 80188,
    },
    {
        "base-version": 80949,
        "data-hash": "9AE39C332883B8BF6AA190286183ED72",
        "fixed-hash": "DACEAFAB8B983C08ACD31ABC085A0052",
        "label": "5.0.0",
        "replay-hash": "28C41277C5837AABF9838B64ACC6BDCF",
        "version": 80949,
    },
    {
        "base-version": 81009,
        "data-hash": "0D28678BC32E7F67A238F19CD3E0A2CE",
        "fixed-hash": "DACEAFAB8B983C08ACD31ABC085A0052",
        "label": "5.0.1",
        "replay-hash": "28C41277C5837AABF9838B64ACC6BDCF",
        "version": 81009,
    },
    {
        "base-version": 81102,
        "data-hash": "DC0A1182FB4ABBE8E29E3EC13CF46F68",
        "fixed-hash": "0C193BD5F63BBAB79D798278F8B2548E",
        "label": "5.0.2",
        "replay-hash": "08BB9D4CAE25B57160A6E4AD7B8E1A5A",
        "version": 81102,
    },
    {
        "base-version": 81433,
        "data-hash": "5FD8D4B6B52723B44862DF29F232CF31",
        "fixed-hash": "4FC35CEA63509AB06AA80AACC1B3B700",
        "label": "5.0.3",
        "replay-hash": "0920F1BD722655B41DA096B98CC0912D",
        "version": 81433,
    },
    {
        "base-version": 82457,
        "data-hash": "D2707E265785612D12B381AF6ED9DBF4",
        "fixed-hash": "ED05F0DB335D003FBC3C7DEF69911114",
        "label": "5.0.4",
        "replay-hash": "7D9EE968AAD81761334BD9076BFD9EFF",
        "version": 82457,
    },
    {
        "base-version": 82893,
        "data-hash": "D795328C01B8A711947CC62AA9750445",
        "fixed-hash": "ED05F0DB335D003FBC3C7DEF69911114",
        "label": "5.0.5",
        "replay-hash": "7D9EE968AAD81761334BD9076BFD9EFF",
        "version": 82893,
    },
    {
        "base-version": 83830,
        "data-hash": "B4745D6A4F982A3143C183D8ACB6C3E3",
        "fixed-hash": "ed05f0db335d003fbc3c7def69911114",
        "label": "5.0.6",
        "replay-hash": "7D9EE968AAD81761334BD9076BFD9EFF",
        "version": 83830,
    },
    {
        "base-version": 84643,
        "data-hash": "A389D1F7DF9DD792FBE980533B7119FF",
        "fixed-hash": "368DE29820A74F5BE747543AC02DB3F8",
        "label": "5.0.7",
        "replay-hash": "7D9EE968AAD81761334BD9076BFD9EFF",
        "version": 84643,
    },
    {
        "base-version": 86383,
        "data-hash": "22EAC562CD0C6A31FB2C2C21E3AA3680",
        "fixed-hash": "B19F4D8B87A2835F9447CA17EDD40C1E",
        "label": "5.0.8",
        "replay-hash": "7D9EE968AAD81761334BD9076BFD9EFF",
        "version": 86383,
    },
    {
        "base-version": 87702,
        "data-hash": "F799E093428D419FD634CCE9B925218C",
        "fixed-hash": "B19F4D8B87A2835F9447CA17EDD40C1E",
        "label": "5.0.9",
        "replay-hash": "7D9EE968AAD81761334BD9076BFD9EFF",
        "version": 87702,
    },
    {
        "base-version": 88500,
        "data-hash": "F38043A301B034A78AD13F558257DCF8",
        "fixed-hash": "F3853B6E3B6013415CAC30EF3B27564B",
        "label": "5.0.10",
        "replay-hash": "A79CD3B6C6DADB0ECAEFA06E6D18E47B",
        "version": 88500,
    },
    {
        "base-version": 89720,
        "data-hash": "D371D4D7D1E6C131B24A09FC0E758547",
        "fixed-hash": "F3853B6E3B6013415CAC30EF3B27564B",
        "label": "5.0.11",
        "replay-hash": "A79CD3B6C6DADB0ECAEFA06E6D18E47B",
        "version": 89720,
    },
    {
        "base-version": 91115,
        "data-hash": "7857A76754FEB47C823D18993C476BF0",
        "fixed-hash": "99E19D19DA59112C1744A83CB49614A5",
        "label": "5.0.12",
        "replay-hash": "BE64E420B329BD2A7D10EEBC0039D6E5",
        "version": 89720,
    },
    {
        "base-version": 92028,
        "data-hash": "2B7746A6706F919775EF1BADFC95EA1C",
        "fixed-hash": "163B1CDF46F09B621F6312CD6901228E",
        "label": "5.0.13",
        "replay-hash": "BE64E420B329BD2A7D10EEBC0039D6E5",
        "version": 92028,
    },
    {
        "base-version": 93333,
        "data-hash": "446907060311fb1cc29eb31e547bb9fd",
        "fixed-hash": "BE86048D1DCE8650E1655D2FE2B665A8",
        "label": "5.0.14.93333",
        "replay-hash": "BE64E420B329BD2A7D10EEBC0039D6E5",
        "version": 93333,
    },
    {
        "base-version": 94137,
        "data-hash": "519EE8D06E384469C652DD58FC6016AC",
        "fixed-hash": "B100C340B3D0797CBE914AE091A68653",
        "label": "5.0.14.94137",
        "replay-hash": "BE64E420B329BD2A7D10EEBC0039D6E5",
        "version": 94137,
    },
]
```

### File: `sc2/wsl.py`

```python
from __future__ import annotations

import os
import re
import subprocess
from pathlib import Path, PureWindowsPath

from loguru import logger

## This file is used for compatibility with WSL and shouldn't need to be
## accessed directly by any bot clients


def win_path_to_wsl_path(path) -> Path:
    """Convert a path like C:\\foo to /mnt/c/foo"""
    return Path("/mnt") / PureWindowsPath(re.sub("^([A-Z]):", lambda m: m.group(1).lower(), path))


def wsl_path_to_win_path(path) -> PureWindowsPath:
    """Convert a path like /mnt/c/foo to C:\\foo"""
    return PureWindowsPath(re.sub("^/mnt/([a-z])", lambda m: m.group(1).upper() + ":", path))


def get_wsl_home():
    """Get home directory of from Windows, even if run in WSL"""
    proc = subprocess.run(["powershell.exe", "-Command", "Write-Host -NoNewLine $HOME"], capture_output=True)

    if proc.returncode != 0:
        return None

    return win_path_to_wsl_path(proc.stdout.decode("utf-8"))


RUN_SCRIPT = """$proc = Start-Process -NoNewWindow -PassThru "%s" "%s"
if ($proc) {
    Write-Host $proc.id
    exit $proc.ExitCode
} else {
    exit 1
}"""


def run(popen_args, sc2_cwd) -> subprocess.Popen[str]:
    """Run SC2 in Windows and get the pid so that it can be killed later."""
    path = wsl_path_to_win_path(popen_args[0])
    args = " ".join(popen_args[1:])

    return subprocess.Popen(
        ["powershell.exe", "-Command", RUN_SCRIPT % (path, args)],
        cwd=sc2_cwd,
        stdout=subprocess.PIPE,
        universal_newlines=True,
        bufsize=1,
    )


def kill(wsl_process) -> bool:
    """Needed to kill a process started with WSL. Returns true if killed successfully."""
    # HACK: subprocess and WSL1 appear to have a nasty interaction where
    # any streams are never closed and the process is never considered killed,
    # despite having an exit code (this works on WSL2 as well, but isn't
    # necessary). As a result,
    # 1: We need to read using readline (to make sure we block long enough to
    #    get the exit code in the rare case where the user immediately hits ^C)
    out = wsl_process.stdout.readline().rstrip()
    # 2: We need to use __exit__, since kill() calls send_signal(), which thinks
    #    the process has already exited!
    wsl_process.__exit__(None, None, None)
    proc = subprocess.run(["taskkill.exe", "-f", "-pid", out], capture_output=True)
    return proc.returncode == 0  # Returns 128 on failure


def detect() -> str | None:
    """Detect the current running version of WSL, and bail out if it doesn't exist"""
    # Allow disabling WSL detection with an environment variable
    if os.getenv("SC2_WSL_DETECT", "1") == "0":
        return None

    wsl_name = os.environ.get("WSL_DISTRO_NAME")
    if not wsl_name:
        return None

    try:
        wsl_proc = subprocess.run(["wsl.exe", "--list", "--running", "--verbose"], capture_output=True)
    except (OSError, ValueError):
        return None
    if wsl_proc.returncode != 0:
        return None

    # WSL.exe returns a bunch of null characters for some reason, as well as
    # windows-style linebreaks. It's inconsistent about how many \rs it uses
    # and this could change in the future, so strip out all junk and split by
    # Unix-style newlines for safety's sake.
    lines = re.sub(r"\000|\r", "", wsl_proc.stdout.decode("utf-8")).split("\n")

    def line_has_proc(ln):
        return re.search("^\\s*[*]?\\s+" + wsl_name, ln)

    def line_version(ln):
        return re.sub("^.*\\s+(\\d+)\\s*$", "\\1", ln)

    versions = [line_version(ln) for ln in lines if line_has_proc(ln)]

    try:
        version = versions[0]
        if int(version) not in [1, 2]:
            return None
    except (ValueError, IndexError):
        return None

    logger.info(f"WSL version {version} detected")

    if version == "2" and not (os.environ.get("SC2CLIENTHOST") and os.environ.get("SC2SERVERHOST")):
        logger.warning("You appear to be running WSL2 without your hosts configured correctly.")
        logger.warning("This may result in SC2 staying on a black screen and not connecting to your bot.")
        logger.warning("Please see the python-sc2 README for WSL2 configuration instructions.")

    return "WSL" + version
```

### File: `sc2/dicts/__init__.py`

```python
# DO NOT EDIT!
# This file was automatically generated by "generate_dicts_from_data_json.py"

__all__ = [
    "generic_redirect_abilities",
    "unit_abilities",
    "unit_research_abilities",
    "unit_tech_alias",
    "unit_train_build_abilities",
    "unit_trained_from",
    "unit_unit_alias",
    "upgrade_researched_from",
]
```

### File: `sc2/dicts/generic_redirect_abilities.py`

```python
# THIS FILE WAS AUTOMATICALLY GENERATED BY "generate_dicts_from_data_json.py" DO NOT CHANGE MANUALLY!
# ANY CHANGE WILL BE OVERWRITTEN

from sc2.ids.ability_id import AbilityId

# from sc2.ids.buff_id import BuffId
# from sc2.ids.effect_id import EffectId


GENERIC_REDIRECT_ABILITIES: dict[AbilityId, AbilityId] = {
    AbilityId.ARMORYRESEARCH_TERRANSHIPWEAPONSLEVEL1: AbilityId.RESEARCH_TERRANSHIPWEAPONS,
    AbilityId.ARMORYRESEARCH_TERRANSHIPWEAPONSLEVEL2: AbilityId.RESEARCH_TERRANSHIPWEAPONS,
    AbilityId.ARMORYRESEARCH_TERRANSHIPWEAPONSLEVEL3: AbilityId.RESEARCH_TERRANSHIPWEAPONS,
    AbilityId.ARMORYRESEARCH_TERRANVEHICLEANDSHIPPLATINGLEVEL1: AbilityId.RESEARCH_TERRANVEHICLEANDSHIPPLATING,
    AbilityId.ARMORYRESEARCH_TERRANVEHICLEANDSHIPPLATINGLEVEL2: AbilityId.RESEARCH_TERRANVEHICLEANDSHIPPLATING,
    AbilityId.ARMORYRESEARCH_TERRANVEHICLEANDSHIPPLATINGLEVEL3: AbilityId.RESEARCH_TERRANVEHICLEANDSHIPPLATING,
    AbilityId.ARMORYRESEARCH_TERRANVEHICLEWEAPONSLEVEL1: AbilityId.RESEARCH_TERRANVEHICLEWEAPONS,
    AbilityId.ARMORYRESEARCH_TERRANVEHICLEWEAPONSLEVEL2: AbilityId.RESEARCH_TERRANVEHICLEWEAPONS,
    AbilityId.ARMORYRESEARCH_TERRANVEHICLEWEAPONSLEVEL3: AbilityId.RESEARCH_TERRANVEHICLEWEAPONS,
    AbilityId.ATTACKPROTOSSBUILDING_ATTACKBUILDING: AbilityId.ATTACK,
    AbilityId.ATTACK_ATTACK: AbilityId.ATTACK,
    AbilityId.ATTACK_BATTLECRUISER: AbilityId.ATTACK,
    AbilityId.ATTACK_REDIRECT: AbilityId.ATTACK,
    AbilityId.BEHAVIOR_CLOAKOFF_BANSHEE: AbilityId.BEHAVIOR_CLOAKOFF,
    AbilityId.BEHAVIOR_CLOAKOFF_GHOST: AbilityId.BEHAVIOR_CLOAKOFF,
    AbilityId.BEHAVIOR_CLOAKON_BANSHEE: AbilityId.BEHAVIOR_CLOAKON,
    AbilityId.BEHAVIOR_CLOAKON_GHOST: AbilityId.BEHAVIOR_CLOAKON,
    AbilityId.BEHAVIOR_HOLDFIREOFF_GHOST: AbilityId.BEHAVIOR_HOLDFIREOFF,
    AbilityId.BEHAVIOR_HOLDFIREOFF_LURKER: AbilityId.BEHAVIOR_HOLDFIREOFF,
    AbilityId.BEHAVIOR_HOLDFIREON_GHOST: AbilityId.BEHAVIOR_HOLDFIREON,
    AbilityId.BEHAVIOR_HOLDFIREON_LURKER: AbilityId.BEHAVIOR_HOLDFIREON,
    AbilityId.BROODLORDQUEUE2_CANCEL: AbilityId.CANCEL_LAST,
    AbilityId.BROODLORDQUEUE2_CANCELSLOT: AbilityId.CANCEL_SLOT,
    AbilityId.BUILDINPROGRESSNYDUSCANAL_CANCEL: AbilityId.CANCEL,
    AbilityId.BUILDNYDUSCANAL_CANCEL: AbilityId.HALT,
    AbilityId.BUILD_CREEPTUMOR_QUEEN: AbilityId.BUILD_CREEPTUMOR,
    AbilityId.BUILD_CREEPTUMOR_TUMOR: AbilityId.BUILD_CREEPTUMOR,
    AbilityId.BUILD_REACTOR_BARRACKS: AbilityId.BUILD_REACTOR,
    AbilityId.BUILD_REACTOR_FACTORY: AbilityId.BUILD_REACTOR,
    AbilityId.BUILD_REACTOR_STARPORT: AbilityId.BUILD_REACTOR,
    AbilityId.BUILD_TECHLAB_BARRACKS: AbilityId.BUILD_TECHLAB,
    AbilityId.BUILD_TECHLAB_FACTORY: AbilityId.BUILD_TECHLAB,
    AbilityId.BUILD_TECHLAB_STARPORT: AbilityId.BUILD_TECHLAB,
    AbilityId.BURROWBANELINGDOWN_CANCEL: AbilityId.CANCEL,
    AbilityId.BURROWCREEPTUMORDOWN_BURROWDOWN: AbilityId.BURROWDOWN,
    AbilityId.BURROWDOWN_BANELING: AbilityId.BURROWDOWN,
    AbilityId.BURROWDOWN_DRONE: AbilityId.BURROWDOWN,
    AbilityId.BURROWDOWN_HYDRALISK: AbilityId.BURROWDOWN,
    AbilityId.BURROWDOWN_INFESTOR: AbilityId.BURROWDOWN,
    AbilityId.BURROWDOWN_INFESTORTERRAN: AbilityId.BURROWDOWN,
    AbilityId.BURROWDOWN_LURKER: AbilityId.BURROWDOWN,
    AbilityId.BURROWDOWN_QUEEN: AbilityId.BURROWDOWN,
    AbilityId.BURROWDOWN_RAVAGER: AbilityId.BURROWDOWN,
    AbilityId.BURROWDOWN_ROACH: AbilityId.BURROWDOWN,
    AbilityId.BURROWDOWN_SWARMHOST: AbilityId.BURROWDOWN,
    AbilityId.BURROWDOWN_ULTRALISK: AbilityId.BURROWDOWN,
    AbilityId.BURROWDOWN_WIDOWMINE: AbilityId.BURROWDOWN,
    AbilityId.BURROWDOWN_ZERGLING: AbilityId.BURROWDOWN,
    AbilityId.BURROWDRONEDOWN_CANCEL: AbilityId.CANCEL,
    AbilityId.BURROWHYDRALISKDOWN_CANCEL: AbilityId.CANCEL,
    AbilityId.BURROWINFESTORDOWN_CANCEL: AbilityId.CANCEL,
    AbilityId.BURROWLURKERMPDOWN_CANCEL: AbilityId.CANCEL,
    AbilityId.BURROWQUEENDOWN_CANCEL: AbilityId.CANCEL,
    AbilityId.BURROWRAVAGERDOWN_CANCEL: AbilityId.CANCEL,
    AbilityId.BURROWROACHDOWN_CANCEL: AbilityId.CANCEL,
    AbilityId.BURROWUP_BANELING: AbilityId.BURROWUP,
    AbilityId.BURROWUP_DRONE: AbilityId.BURROWUP,
    AbilityId.BURROWUP_HYDRALISK: AbilityId.BURROWUP,
    AbilityId.BURROWUP_INFESTOR: AbilityId.BURROWUP,
    AbilityId.BURROWUP_INFESTORTERRAN: AbilityId.BURROWUP,
    AbilityId.BURROWUP_LURKER: AbilityId.BURROWUP,
    AbilityId.BURROWUP_QUEEN: AbilityId.BURROWUP,
    AbilityId.BURROWUP_RAVAGER: AbilityId.BURROWUP,
    AbilityId.BURROWUP_ROACH: AbilityId.BURROWUP,
    AbilityId.BURROWUP_SWARMHOST: AbilityId.BURROWUP,
    AbilityId.BURROWUP_ULTRALISK: AbilityId.BURROWUP,
    AbilityId.BURROWUP_WIDOWMINE: AbilityId.BURROWUP,
    AbilityId.BURROWUP_ZERGLING: AbilityId.BURROWUP,
    AbilityId.BURROWZERGLINGDOWN_CANCEL: AbilityId.CANCEL,
    AbilityId.CANCELSLOT_ADDON: AbilityId.CANCEL_SLOT,
    AbilityId.CANCELSLOT_HANGARQUEUE5: AbilityId.CANCEL_SLOT,
    AbilityId.CANCELSLOT_QUEUE1: AbilityId.CANCEL_SLOT,
    AbilityId.CANCELSLOT_QUEUE5: AbilityId.CANCEL_SLOT,
    AbilityId.CANCELSLOT_QUEUECANCELTOSELECTION: AbilityId.CANCEL_SLOT,
    AbilityId.CANCELSLOT_QUEUEPASSIVE: AbilityId.CANCEL_SLOT,
    AbilityId.CANCELSLOT_QUEUEPASSIVECANCELTOSELECTION: AbilityId.CANCEL_SLOT,
    AbilityId.CANCEL_ADEPTPHASESHIFT: AbilityId.CANCEL,
    AbilityId.CANCEL_ADEPTSHADEPHASESHIFT: AbilityId.CANCEL,
    AbilityId.CANCEL_BARRACKSADDON: AbilityId.CANCEL,
    AbilityId.CANCEL_BUILDINPROGRESS: AbilityId.CANCEL,
    AbilityId.CANCEL_CREEPTUMOR: AbilityId.CANCEL,
    AbilityId.CANCEL_FACTORYADDON: AbilityId.CANCEL,
    AbilityId.CANCEL_GRAVITONBEAM: AbilityId.CANCEL,
    AbilityId.CANCEL_HANGARQUEUE5: AbilityId.CANCEL_LAST,
    AbilityId.CANCEL_LOCKON: AbilityId.CANCEL,
    AbilityId.CANCEL_MORPHBROODLORD: AbilityId.CANCEL,
    AbilityId.CANCEL_MORPHGREATERSPIRE: AbilityId.CANCEL,
    AbilityId.CANCEL_MORPHHIVE: AbilityId.CANCEL,
    AbilityId.CANCEL_MORPHLAIR: AbilityId.CANCEL,
    AbilityId.CANCEL_MORPHLURKER: AbilityId.CANCEL,
    AbilityId.CANCEL_MORPHMOTHERSHIP: AbilityId.CANCEL,
    AbilityId.CANCEL_MORPHORBITAL: AbilityId.CANCEL,
    AbilityId.CANCEL_MORPHOVERLORDTRANSPORT: AbilityId.CANCEL,
    AbilityId.CANCEL_MORPHOVERSEER: AbilityId.CANCEL,
    AbilityId.CANCEL_MORPHPLANETARYFORTRESS: AbilityId.CANCEL,
    AbilityId.CANCEL_MORPHRAVAGER: AbilityId.CANCEL,
    AbilityId.CANCEL_MORPHTHOREXPLOSIVEMODE: AbilityId.CANCEL,
    AbilityId.CANCEL_NEURALPARASITE: AbilityId.CANCEL,
    AbilityId.CANCEL_NUKE: AbilityId.CANCEL,
    AbilityId.CANCEL_QUEUE1: AbilityId.CANCEL_LAST,
    AbilityId.CANCEL_QUEUE5: AbilityId.CANCEL_LAST,
    AbilityId.CANCEL_QUEUEADDON: AbilityId.CANCEL_LAST,
    AbilityId.CANCEL_QUEUECANCELTOSELECTION: AbilityId.CANCEL_LAST,
    AbilityId.CANCEL_QUEUEPASIVE: AbilityId.CANCEL_LAST,
    AbilityId.CANCEL_QUEUEPASSIVECANCELTOSELECTION: AbilityId.CANCEL_LAST,
    AbilityId.CANCEL_SPINECRAWLERROOT: AbilityId.CANCEL,
    AbilityId.CANCEL_SPORECRAWLERROOT: AbilityId.CANCEL,
    AbilityId.CANCEL_STARPORTADDON: AbilityId.CANCEL,
    AbilityId.CANCEL_STASISTRAP: AbilityId.CANCEL,
    AbilityId.CANCEL_VOIDRAYPRISMATICALIGNMENT: AbilityId.CANCEL,
    AbilityId.CHANNELSNIPE_CANCEL: AbilityId.CANCEL,
    AbilityId.COMMANDCENTERTRANSPORT_COMMANDCENTERTRANSPORT: AbilityId.LOAD,
    AbilityId.CYBERNETICSCORERESEARCH_PROTOSSAIRARMORLEVEL1: AbilityId.RESEARCH_PROTOSSAIRARMOR,
    AbilityId.CYBERNETICSCORERESEARCH_PROTOSSAIRARMORLEVEL2: AbilityId.RESEARCH_PROTOSSAIRARMOR,
    AbilityId.CYBERNETICSCORERESEARCH_PROTOSSAIRARMORLEVEL3: AbilityId.RESEARCH_PROTOSSAIRARMOR,
    AbilityId.CYBERNETICSCORERESEARCH_PROTOSSAIRWEAPONSLEVEL1: AbilityId.RESEARCH_PROTOSSAIRWEAPONS,
    AbilityId.CYBERNETICSCORERESEARCH_PROTOSSAIRWEAPONSLEVEL2: AbilityId.RESEARCH_PROTOSSAIRWEAPONS,
    AbilityId.CYBERNETICSCORERESEARCH_PROTOSSAIRWEAPONSLEVEL3: AbilityId.RESEARCH_PROTOSSAIRWEAPONS,
    AbilityId.DEFILERMPBURROW_BURROWDOWN: AbilityId.BURROWDOWN,
    AbilityId.DEFILERMPBURROW_CANCEL: AbilityId.CANCEL,
    AbilityId.DEFILERMPUNBURROW_BURROWUP: AbilityId.BURROWUP,
    AbilityId.EFFECT_BLINK_STALKER: AbilityId.EFFECT_BLINK,
    AbilityId.EFFECT_MASSRECALL_MOTHERSHIPCORE: AbilityId.EFFECT_MASSRECALL,
    AbilityId.EFFECT_MASSRECALL_NEXUS: AbilityId.EFFECT_MASSRECALL,
    AbilityId.EFFECT_MASSRECALL_STRATEGICRECALL: AbilityId.EFFECT_MASSRECALL,
    AbilityId.EFFECT_REPAIR_MULE: AbilityId.EFFECT_REPAIR,
    AbilityId.EFFECT_REPAIR_REPAIRDRONE: AbilityId.EFFECT_REPAIR,
    AbilityId.EFFECT_REPAIR_SCV: AbilityId.EFFECT_REPAIR,
    AbilityId.EFFECT_SHADOWSTRIDE: AbilityId.EFFECT_BLINK,
    AbilityId.EFFECT_SPRAY_PROTOSS: AbilityId.EFFECT_SPRAY,
    AbilityId.EFFECT_SPRAY_TERRAN: AbilityId.EFFECT_SPRAY,
    AbilityId.EFFECT_SPRAY_ZERG: AbilityId.EFFECT_SPRAY,
    AbilityId.EFFECT_STIM_MARAUDER: AbilityId.EFFECT_STIM,
    AbilityId.EFFECT_STIM_MARAUDER_REDIRECT: AbilityId.EFFECT_STIM,
    AbilityId.EFFECT_STIM_MARINE: AbilityId.EFFECT_STIM,
    AbilityId.EFFECT_STIM_MARINE_REDIRECT: AbilityId.EFFECT_STIM,
    AbilityId.ENGINEERINGBAYRESEARCH_TERRANINFANTRYARMORLEVEL1: AbilityId.RESEARCH_TERRANINFANTRYARMOR,
    AbilityId.ENGINEERINGBAYRESEARCH_TERRANINFANTRYARMORLEVEL2: AbilityId.RESEARCH_TERRANINFANTRYARMOR,
    AbilityId.ENGINEERINGBAYRESEARCH_TERRANINFANTRYARMORLEVEL3: AbilityId.RESEARCH_TERRANINFANTRYARMOR,
    AbilityId.ENGINEERINGBAYRESEARCH_TERRANINFANTRYWEAPONSLEVEL1: AbilityId.RESEARCH_TERRANINFANTRYWEAPONS,
    AbilityId.ENGINEERINGBAYRESEARCH_TERRANINFANTRYWEAPONSLEVEL2: AbilityId.RESEARCH_TERRANINFANTRYWEAPONS,
    AbilityId.ENGINEERINGBAYRESEARCH_TERRANINFANTRYWEAPONSLEVEL3: AbilityId.RESEARCH_TERRANINFANTRYWEAPONS,
    AbilityId.FORCEFIELD_CANCEL: AbilityId.CANCEL,
    AbilityId.FORGERESEARCH_PROTOSSGROUNDARMORLEVEL1: AbilityId.RESEARCH_PROTOSSGROUNDARMOR,
    AbilityId.FORGERESEARCH_PROTOSSGROUNDARMORLEVEL2: AbilityId.RESEARCH_PROTOSSGROUNDARMOR,
    AbilityId.FORGERESEARCH_PROTOSSGROUNDARMORLEVEL3: AbilityId.RESEARCH_PROTOSSGROUNDARMOR,
    AbilityId.FORGERESEARCH_PROTOSSGROUNDWEAPONSLEVEL1: AbilityId.RESEARCH_PROTOSSGROUNDWEAPONS,
    AbilityId.FORGERESEARCH_PROTOSSGROUNDWEAPONSLEVEL2: AbilityId.RESEARCH_PROTOSSGROUNDWEAPONS,
    AbilityId.FORGERESEARCH_PROTOSSGROUNDWEAPONSLEVEL3: AbilityId.RESEARCH_PROTOSSGROUNDWEAPONS,
    AbilityId.FORGERESEARCH_PROTOSSSHIELDSLEVEL1: AbilityId.RESEARCH_PROTOSSSHIELDS,
    AbilityId.FORGERESEARCH_PROTOSSSHIELDSLEVEL2: AbilityId.RESEARCH_PROTOSSSHIELDS,
    AbilityId.FORGERESEARCH_PROTOSSSHIELDSLEVEL3: AbilityId.RESEARCH_PROTOSSSHIELDS,
    AbilityId.HALT_BUILDING: AbilityId.HALT,
    AbilityId.HALT_TERRANBUILD: AbilityId.HALT,
    AbilityId.HARVEST_GATHER_DRONE: AbilityId.HARVEST_GATHER,
    AbilityId.HARVEST_GATHER_MULE: AbilityId.HARVEST_GATHER,
    AbilityId.HARVEST_GATHER_PROBE: AbilityId.HARVEST_GATHER,
    AbilityId.HARVEST_GATHER_SCV: AbilityId.HARVEST_GATHER,
    AbilityId.HARVEST_RETURN_DRONE: AbilityId.HARVEST_RETURN,
    AbilityId.HARVEST_RETURN_MULE: AbilityId.HARVEST_RETURN,
    AbilityId.HARVEST_RETURN_PROBE: AbilityId.HARVEST_RETURN,
    AbilityId.HARVEST_RETURN_SCV: AbilityId.HARVEST_RETURN,
    AbilityId.HOLDPOSITION_BATTLECRUISER: AbilityId.HOLDPOSITION,
    AbilityId.HOLDPOSITION_HOLD: AbilityId.HOLDPOSITION,
    AbilityId.LAND_BARRACKS: AbilityId.LAND,
    AbilityId.LAND_COMMANDCENTER: AbilityId.LAND,
    AbilityId.LAND_FACTORY: AbilityId.LAND,
    AbilityId.LAND_ORBITALCOMMAND: AbilityId.LAND,
    AbilityId.LAND_STARPORT: AbilityId.LAND,
    AbilityId.LIFT_BARRACKS: AbilityId.LIFT,
    AbilityId.LIFT_COMMANDCENTER: AbilityId.LIFT,
    AbilityId.LIFT_FACTORY: AbilityId.LIFT,
    AbilityId.LIFT_ORBITALCOMMAND: AbilityId.LIFT,
    AbilityId.LIFT_STARPORT: AbilityId.LIFT,
    AbilityId.LOADALL_COMMANDCENTER: AbilityId.LOADALL,
    AbilityId.LOAD_BUNKER: AbilityId.LOAD,
    AbilityId.LOAD_MEDIVAC: AbilityId.LOAD,
    AbilityId.LOAD_NYDUSNETWORK: AbilityId.LOAD,
    AbilityId.LOAD_NYDUSWORM: AbilityId.LOAD,
    AbilityId.LOAD_OVERLORD: AbilityId.LOAD,
    AbilityId.LOAD_WARPPRISM: AbilityId.LOAD,
    AbilityId.MERGEABLE_CANCEL: AbilityId.CANCEL,
    AbilityId.MORPHBACKTOGATEWAY_CANCEL: AbilityId.CANCEL,
    AbilityId.MORPHTOBANELING_CANCEL: AbilityId.CANCEL,
    AbilityId.MORPHTOCOLLAPSIBLEPURIFIERTOWERDEBRIS_CANCEL: AbilityId.CANCEL,
    AbilityId.MORPHTOCOLLAPSIBLEROCKTOWERDEBRISRAMPLEFTGREEN_CANCEL: AbilityId.CANCEL,
    AbilityId.MORPHTOCOLLAPSIBLEROCKTOWERDEBRISRAMPLEFT_CANCEL: AbilityId.CANCEL,
    AbilityId.MORPHTOCOLLAPSIBLEROCKTOWERDEBRISRAMPRIGHTGREEN_CANCEL: AbilityId.CANCEL,
    AbilityId.MORPHTOCOLLAPSIBLEROCKTOWERDEBRISRAMPRIGHT_CANCEL: AbilityId.CANCEL,
    AbilityId.MORPHTOCOLLAPSIBLEROCKTOWERDEBRIS_CANCEL: AbilityId.CANCEL,
    AbilityId.MORPHTOCOLLAPSIBLETERRANTOWERDEBRISRAMPLEFT_CANCEL: AbilityId.CANCEL,
    AbilityId.MORPHTOCOLLAPSIBLETERRANTOWERDEBRISRAMPRIGHT_CANCEL: AbilityId.CANCEL,
    AbilityId.MORPHTOCOLLAPSIBLETERRANTOWERDEBRIS_CANCEL: AbilityId.CANCEL,
    AbilityId.MORPHTODEVOURERMP_CANCEL: AbilityId.CANCEL,
    AbilityId.MORPHTOGUARDIANMP_CANCEL: AbilityId.CANCEL,
    AbilityId.MORPHTOSWARMHOSTBURROWEDMP_CANCEL: AbilityId.CANCEL,
    AbilityId.MOVE_BATTLECRUISER: AbilityId.MOVE,
    AbilityId.MOVE_MOVE: AbilityId.MOVE,
    AbilityId.PATROL_BATTLECRUISER: AbilityId.PATROL,
    AbilityId.PATROL_PATROL: AbilityId.PATROL,
    AbilityId.PHASINGMODE_CANCEL: AbilityId.CANCEL,
    AbilityId.PROTOSSBUILD_CANCEL: AbilityId.HALT,
    AbilityId.QUEENBUILD_CANCEL: AbilityId.HALT,
    AbilityId.RALLY_BUILDING: AbilityId.RALLY_UNITS,
    AbilityId.RALLY_COMMANDCENTER: AbilityId.RALLY_WORKERS,
    AbilityId.RALLY_HATCHERY_UNITS: AbilityId.RALLY_UNITS,
    AbilityId.RALLY_HATCHERY_WORKERS: AbilityId.RALLY_WORKERS,
    AbilityId.RALLY_MORPHING_UNIT: AbilityId.RALLY_UNITS,
    AbilityId.RALLY_NEXUS: AbilityId.RALLY_WORKERS,
    AbilityId.RESEARCH_ZERGFLYERARMORLEVEL1: AbilityId.RESEARCH_ZERGFLYERARMOR,
    AbilityId.RESEARCH_ZERGFLYERARMORLEVEL2: AbilityId.RESEARCH_ZERGFLYERARMOR,
    AbilityId.RESEARCH_ZERGFLYERARMORLEVEL3: AbilityId.RESEARCH_ZERGFLYERARMOR,
    AbilityId.RESEARCH_ZERGFLYERATTACKLEVEL1: AbilityId.RESEARCH_ZERGFLYERATTACK,
    AbilityId.RESEARCH_ZERGFLYERATTACKLEVEL2: AbilityId.RESEARCH_ZERGFLYERATTACK,
    AbilityId.RESEARCH_ZERGFLYERATTACKLEVEL3: AbilityId.RESEARCH_ZERGFLYERATTACK,
    AbilityId.RESEARCH_ZERGGROUNDARMORLEVEL1: AbilityId.RESEARCH_ZERGGROUNDARMOR,
    AbilityId.RESEARCH_ZERGGROUNDARMORLEVEL2: AbilityId.RESEARCH_ZERGGROUNDARMOR,
    AbilityId.RESEARCH_ZERGGROUNDARMORLEVEL3: AbilityId.RESEARCH_ZERGGROUNDARMOR,
    AbilityId.RESEARCH_ZERGMELEEWEAPONSLEVEL1: AbilityId.RESEARCH_ZERGMELEEWEAPONS,
    AbilityId.RESEARCH_ZERGMELEEWEAPONSLEVEL2: AbilityId.RESEARCH_ZERGMELEEWEAPONS,
    AbilityId.RESEARCH_ZERGMELEEWEAPONSLEVEL3: AbilityId.RESEARCH_ZERGMELEEWEAPONS,
    AbilityId.RESEARCH_ZERGMISSILEWEAPONSLEVEL1: AbilityId.RESEARCH_ZERGMISSILEWEAPONS,
    AbilityId.RESEARCH_ZERGMISSILEWEAPONSLEVEL2: AbilityId.RESEARCH_ZERGMISSILEWEAPONS,
    AbilityId.RESEARCH_ZERGMISSILEWEAPONSLEVEL3: AbilityId.RESEARCH_ZERGMISSILEWEAPONS,
    AbilityId.SCAN_MOVE: AbilityId.ATTACK,
    AbilityId.SHIELDBATTERYRECHARGEEX5_STOP: AbilityId.CANCEL,
    AbilityId.SPINECRAWLERROOT_SPINECRAWLERROOT: AbilityId.MORPH_ROOT,
    AbilityId.SPINECRAWLERUPROOT_CANCEL: AbilityId.CANCEL,
    AbilityId.SPINECRAWLERUPROOT_SPINECRAWLERUPROOT: AbilityId.MORPH_UPROOT,
    AbilityId.SPORECRAWLERROOT_SPORECRAWLERROOT: AbilityId.MORPH_ROOT,
    AbilityId.SPORECRAWLERUPROOT_CANCEL: AbilityId.CANCEL,
    AbilityId.SPORECRAWLERUPROOT_SPORECRAWLERUPROOT: AbilityId.MORPH_UPROOT,
    AbilityId.STOP_BATTLECRUISER: AbilityId.STOP,
    AbilityId.STOP_BUILDING: AbilityId.STOP,
    AbilityId.STOP_CHEER: AbilityId.STOP,
    AbilityId.STOP_DANCE: AbilityId.STOP,
    AbilityId.STOP_HOLDFIRESPECIAL: AbilityId.STOP,
    AbilityId.STOP_REDIRECT: AbilityId.STOP,
    AbilityId.STOP_STOP: AbilityId.STOP,
    AbilityId.TESTZERG_CANCEL: AbilityId.CANCEL,
    AbilityId.THORAPMODE_CANCEL: AbilityId.CANCEL,
    AbilityId.TRANSPORTMODE_CANCEL: AbilityId.CANCEL,
    AbilityId.UNLOADALLAT_MEDIVAC: AbilityId.UNLOADALLAT,
    AbilityId.UNLOADALLAT_OVERLORD: AbilityId.UNLOADALLAT,
    AbilityId.UNLOADALLAT_WARPPRISM: AbilityId.UNLOADALLAT,
    AbilityId.UNLOADALL_BUNKER: AbilityId.UNLOADALL,
    AbilityId.UNLOADALL_COMMANDCENTER: AbilityId.UNLOADALL,
    AbilityId.UNLOADALL_NYDASNETWORK: AbilityId.UNLOADALL,
    AbilityId.UNLOADALL_NYDUSWORM: AbilityId.UNLOADALL,
    AbilityId.UNLOADALL_WARPPRISM: AbilityId.UNLOADALL,
    AbilityId.UNLOADUNIT_BUNKER: AbilityId.UNLOADUNIT,
    AbilityId.UNLOADUNIT_COMMANDCENTER: AbilityId.UNLOADUNIT,
    AbilityId.UNLOADUNIT_MEDIVAC: AbilityId.UNLOADUNIT,
    AbilityId.UNLOADUNIT_NYDASNETWORK: AbilityId.UNLOADUNIT,
    AbilityId.UNLOADUNIT_OVERLORD: AbilityId.UNLOADUNIT,
    AbilityId.UNLOADUNIT_WARPPRISM: AbilityId.UNLOADUNIT,
    AbilityId.UPGRADETOWARPGATE_CANCEL: AbilityId.CANCEL,
    AbilityId.WARPABLE_CANCEL: AbilityId.CANCEL,
    AbilityId.WIDOWMINEBURROW_CANCEL: AbilityId.CANCEL,
    AbilityId.ZERGBUILD_CANCEL: AbilityId.HALT,
}
```

### File: `sc2/dicts/unit_abilities.py`

```python
# THIS FILE WAS AUTOMATICALLY GENERATED BY "generate_dicts_from_data_json.py" DO NOT CHANGE MANUALLY!
# ANY CHANGE WILL BE OVERWRITTEN

from sc2.ids.ability_id import AbilityId
from sc2.ids.unit_typeid import UnitTypeId

# from sc2.ids.buff_id import BuffId
# from sc2.ids.effect_id import EffectId


UNIT_ABILITIES: dict[UnitTypeId, set[AbilityId]] = {
    UnitTypeId.ADEPT: {
        AbilityId.ADEPTPHASESHIFT_ADEPTPHASESHIFT,
        AbilityId.ATTACK_ATTACK,
        AbilityId.HOLDPOSITION_HOLD,
        AbilityId.MOVE_MOVE,
        AbilityId.PATROL_PATROL,
        AbilityId.SMART,
        AbilityId.STOP_STOP,
    },
    UnitTypeId.ADEPTPHASESHIFT: {
        AbilityId.ATTACK_ATTACK,
        AbilityId.CANCEL_ADEPTSHADEPHASESHIFT,
        AbilityId.HOLDPOSITION_HOLD,
        AbilityId.MOVE_MOVE,
        AbilityId.PATROL_PATROL,
        AbilityId.SCAN_MOVE,
        AbilityId.SMART,
        AbilityId.STOP_STOP,
    },
    UnitTypeId.ARBITERMP: {
        AbilityId.ARBITERMPRECALL_ARBITERMPRECALL,
        AbilityId.ARBITERMPSTASISFIELD_ARBITERMPSTASISFIELD,
        AbilityId.ATTACK_ATTACK,
        AbilityId.HOLDPOSITION_HOLD,
        AbilityId.MOVE_MOVE,
        AbilityId.PATROL_PATROL,
        AbilityId.SMART,
        AbilityId.STOP_STOP,
    },
    UnitTypeId.ARCHON: {
        AbilityId.ATTACK_ATTACK,
        AbilityId.HOLDPOSITION_HOLD,
        AbilityId.MOVE_MOVE,
        AbilityId.PATROL_PATROL,
        AbilityId.SMART,
        AbilityId.STOP_STOP,
    },
    UnitTypeId.ARMORY: {
        AbilityId.ARMORYRESEARCH_TERRANSHIPWEAPONSLEVEL1,
        AbilityId.ARMORYRESEARCH_TERRANSHIPWEAPONSLEVEL2,
        AbilityId.ARMORYRESEARCH_TERRANSHIPWEAPONSLEVEL3,
        AbilityId.ARMORYRESEARCH_TERRANVEHICLEANDSHIPPLATINGLEVEL1,
        AbilityId.ARMORYRESEARCH_TERRANVEHICLEANDSHIPPLATINGLEVEL2,
        AbilityId.ARMORYRESEARCH_TERRANVEHICLEANDSHIPPLATINGLEVEL3,
        AbilityId.ARMORYRESEARCH_TERRANVEHICLEWEAPONSLEVEL1,
        AbilityId.ARMORYRESEARCH_TERRANVEHICLEWEAPONSLEVEL2,
        AbilityId.ARMORYRESEARCH_TERRANVEHICLEWEAPONSLEVEL3,
    },
    UnitTypeId.AUTOTURRET: {AbilityId.ATTACK_ATTACK, AbilityId.SMART, AbilityId.STOP_STOP},
    UnitTypeId.BANELING: {
        AbilityId.ATTACK_ATTACK,
        AbilityId.BEHAVIOR_BUILDINGATTACKON,
        AbilityId.BURROWDOWN_BANELING,
        AbilityId.EXPLODE_EXPLODE,
        AbilityId.HOLDPOSITION_HOLD,
        AbilityId.MOVE_MOVE,
        AbilityId.PATROL_PATROL,
        AbilityId.SMART,
        AbilityId.STOP_STOP,
    },
    UnitTypeId.BANELINGBURROWED: {AbilityId.BURROWUP_BANELING, AbilityId.EXPLODE_EXPLODE},
    UnitTypeId.BANELINGCOCOON: {AbilityId.RALLY_BUILDING, AbilityId.SMART},
    UnitTypeId.BANELINGNEST: {AbilityId.RESEARCH_CENTRIFUGALHOOKS},
    UnitTypeId.BANSHEE: {
        AbilityId.ATTACK_ATTACK,
        AbilityId.BEHAVIOR_CLOAKON_BANSHEE,
        AbilityId.HOLDPOSITION_HOLD,
        AbilityId.MOVE_MOVE,
        AbilityId.PATROL_PATROL,
        AbilityId.SMART,
        AbilityId.STOP_STOP,
    },
    UnitTypeId.BARRACKS: {
        AbilityId.BARRACKSTRAIN_GHOST,
        AbilityId.BARRACKSTRAIN_MARAUDER,
        AbilityId.BARRACKSTRAIN_MARINE,
        AbilityId.BARRACKSTRAIN_REAPER,
        AbilityId.BUILD_REACTOR_BARRACKS,
        AbilityId.BUILD_TECHLAB_BARRACKS,
        AbilityId.LIFT_BARRACKS,
        AbilityId.RALLY_BUILDING,
        AbilityId.SMART,
    },
    UnitTypeId.BARRACKSFLYING: {
        AbilityId.BUILD_REACTOR_BARRACKS,
        AbilityId.BUILD_TECHLAB_BARRACKS,
        AbilityId.HOLDPOSITION_HOLD,
        AbilityId.LAND_BARRACKS,
        AbilityId.MOVE_MOVE,
        AbilityId.PATROL_PATROL,
        AbilityId.SMART,
        AbilityId.STOP_STOP,
    },
    UnitTypeId.BARRACKSTECHLAB: {
        AbilityId.BARRACKSTECHLABRESEARCH_STIMPACK,
        AbilityId.RESEARCH_COMBATSHIELD,
        AbilityId.RESEARCH_CONCUSSIVESHELLS,
    },
    UnitTypeId.BATTLECRUISER: {
        AbilityId.ATTACK_BATTLECRUISER,
        AbilityId.EFFECT_TACTICALJUMP,
        AbilityId.HOLDPOSITION_BATTLECRUISER,
        AbilityId.MOVE_BATTLECRUISER,
        AbilityId.PATROL_BATTLECRUISER,
        AbilityId.SMART,
        AbilityId.STOP_BATTLECRUISER,
        AbilityId.YAMATO_YAMATOGUN,
    },
    UnitTypeId.BROODLING: {
        AbilityId.ATTACK_ATTACK,
        AbilityId.HOLDPOSITION_HOLD,
        AbilityId.MOVE_MOVE,
        AbilityId.PATROL_PATROL,
        AbilityId.SMART,
        AbilityId.STOP_STOP,
    },
    UnitTypeId.BROODLORD: {
        AbilityId.ATTACK_ATTACK,
        AbilityId.HOLDPOSITION_HOLD,
        AbilityId.MOVE_MOVE,
        AbilityId.PATROL_PATROL,
        AbilityId.SMART,
        AbilityId.STOP_STOP,
    },
    UnitTypeId.BUNKER: {
        AbilityId.LOAD_BUNKER,
        AbilityId.RALLY_BUILDING,
        AbilityId.SALVAGEEFFECT_SALVAGE,
        AbilityId.SMART,
    },
    UnitTypeId.BYPASSARMORDRONE: {AbilityId.ATTACK_ATTACK, AbilityId.MOVE_MOVE, AbilityId.SMART, AbilityId.STOP_STOP},
    UnitTypeId.CARRIER: {
        AbilityId.ATTACK_ATTACK,
        AbilityId.BUILD_INTERCEPTORS,
        AbilityId.CANCEL_HANGARQUEUE5,
        AbilityId.HOLDPOSITION_HOLD,
        AbilityId.MOVE_MOVE,
        AbilityId.PATROL_PATROL,
        AbilityId.SMART,
        AbilityId.STOP_STOP,
    },
    UnitTypeId.CHANGELING: {
        AbilityId.HOLDPOSITION_HOLD,
        AbilityId.MOVE_MOVE,
        AbilityId.PATROL_PATROL,
        AbilityId.SCAN_MOVE,
        AbilityId.SMART,
        AbilityId.STOP_STOP,
    },
    UnitTypeId.CHANGELINGMARINE: {
        AbilityId.HOLDPOSITION_HOLD,
        AbilityId.MOVE_MOVE,
        AbilityId.PATROL_PATROL,
        AbilityId.SCAN_MOVE,
        AbilityId.SMART,
        AbilityId.STOP_STOP,
    },
    UnitTypeId.CHANGELINGMARINESHIELD: {
        AbilityId.HOLDPOSITION_HOLD,
        AbilityId.MOVE_MOVE,
        AbilityId.PATROL_PATROL,
        AbilityId.SCAN_MOVE,
        AbilityId.SMART,
        AbilityId.STOP_STOP,
    },
    UnitTypeId.CHANGELINGZEALOT: {
        AbilityId.HOLDPOSITION_HOLD,
        AbilityId.MOVE_MOVE,
        AbilityId.PATROL_PATROL,
        AbilityId.SCAN_MOVE,
        AbilityId.SMART,
        AbilityId.STOP_STOP,
    },
    UnitTypeId.CHANGELINGZERGLING: {
        AbilityId.HOLDPOSITION_HOLD,
        AbilityId.MOVE_MOVE,
        AbilityId.PATROL_PATROL,
        AbilityId.SCAN_MOVE,
        AbilityId.SMART,
        AbilityId.STOP_STOP,
    },
    UnitTypeId.CHANGELINGZERGLINGWINGS: {
        AbilityId.HOLDPOSITION_HOLD,
        AbilityId.MOVE_MOVE,
        AbilityId.PATROL_PATROL,
        AbilityId.SCAN_MOVE,
        AbilityId.SMART,
        AbilityId.STOP_STOP,
    },
    UnitTypeId.COLOSSUS: {
        AbilityId.ATTACK_ATTACK,
        AbilityId.HOLDPOSITION_HOLD,
        AbilityId.MOVE_MOVE,
        AbilityId.PATROL_PATROL,
        AbilityId.SMART,
        AbilityId.STOP_STOP,
    },
    UnitTypeId.COMMANDCENTER: {
        AbilityId.COMMANDCENTERTRAIN_SCV,
        AbilityId.LIFT_COMMANDCENTER,
        AbilityId.LOADALL_COMMANDCENTER,
        AbilityId.RALLY_COMMANDCENTER,
        AbilityId.SMART,
        AbilityId.UPGRADETOORBITAL_ORBITALCOMMAND,
        AbilityId.UPGRADETOPLANETARYFORTRESS_PLANETARYFORTRESS,
    },
    UnitTypeId.COMMANDCENTERFLYING: {
        AbilityId.HOLDPOSITION_HOLD,
        AbilityId.LAND_COMMANDCENTER,
        AbilityId.LOADALL_COMMANDCENTER,
        AbilityId.MOVE_MOVE,
        AbilityId.PATROL_PATROL,
        AbilityId.SMART,
        AbilityId.STOP_STOP,
    },
    UnitTypeId.CORRUPTOR: {
        AbilityId.ATTACK_ATTACK,
        AbilityId.CAUSTICSPRAY_CAUSTICSPRAY,
        AbilityId.HOLDPOSITION_HOLD,
        AbilityId.MORPHTOBROODLORD_BROODLORD,
        AbilityId.MOVE_MOVE,
        AbilityId.PATROL_PATROL,
        AbilityId.SMART,
        AbilityId.STOP_STOP,
    },
    UnitTypeId.CORSAIRMP: {
        AbilityId.ATTACK_ATTACK,
        AbilityId.CORSAIRMPDISRUPTIONWEB_CORSAIRMPDISRUPTIONWEB,
        AbilityId.HOLDPOSITION_HOLD,
        AbilityId.MOVE_MOVE,
        AbilityId.PATROL_PATROL,
        AbilityId.SMART,
        AbilityId.STOP_STOP,
    },
    UnitTypeId.CREEPTUMORBURROWED: {AbilityId.BUILD_CREEPTUMOR, AbilityId.BUILD_CREEPTUMOR_TUMOR, AbilityId.SMART},
    UnitTypeId.CYBERNETICSCORE: {
        AbilityId.CYBERNETICSCORERESEARCH_PROTOSSAIRARMORLEVEL1,
        AbilityId.CYBERNETICSCORERESEARCH_PROTOSSAIRARMORLEVEL2,
        AbilityId.CYBERNETICSCORERESEARCH_PROTOSSAIRARMORLEVEL3,
        AbilityId.CYBERNETICSCORERESEARCH_PROTOSSAIRWEAPONSLEVEL1,
        AbilityId.CYBERNETICSCORERESEARCH_PROTOSSAIRWEAPONSLEVEL2,
        AbilityId.CYBERNETICSCORERESEARCH_PROTOSSAIRWEAPONSLEVEL3,
        AbilityId.RESEARCH_WARPGATE,
    },
    UnitTypeId.CYCLONE: {
        AbilityId.ATTACK_ATTACK,
        AbilityId.HOLDPOSITION_HOLD,
        AbilityId.LOCKON_LOCKON,
        AbilityId.MOVE_MOVE,
        AbilityId.PATROL_PATROL,
        AbilityId.SMART,
        AbilityId.STOP_STOP,
    },
    UnitTypeId.DARKSHRINE: {AbilityId.RESEARCH_SHADOWSTRIKE},
    UnitTypeId.DARKTEMPLAR: {
        AbilityId.ATTACK_ATTACK,
        AbilityId.EFFECT_SHADOWSTRIDE,
        AbilityId.HOLDPOSITION_HOLD,
        AbilityId.MORPH_ARCHON,
        AbilityId.MOVE_MOVE,
        AbilityId.PATROL_PATROL,
        AbilityId.SMART,
        AbilityId.STOP_STOP,
    },
    UnitTypeId.DEFILERMP: {
        AbilityId.DEFILERMPBURROW_BURROWDOWN,
        AbilityId.DEFILERMPCONSUME_DEFILERMPCONSUME,
        AbilityId.DEFILERMPDARKSWARM_DEFILERMPDARKSWARM,
        AbilityId.DEFILERMPPLAGUE_DEFILERMPPLAGUE,
        AbilityId.HOLDPOSITION_HOLD,
        AbilityId.MOVE_MOVE,
        AbilityId.PATROL_PATROL,
        AbilityId.SCAN_MOVE,
        AbilityId.SMART,
        AbilityId.STOP_STOP,
    },
    UnitTypeId.DEFILERMPBURROWED: {AbilityId.DEFILERMPUNBURROW_BURROWUP},
    UnitTypeId.DEVOURERMP: {
        AbilityId.ATTACK_ATTACK,
        AbilityId.HOLDPOSITION_HOLD,
        AbilityId.MOVE_MOVE,
        AbilityId.PATROL_PATROL,
        AbilityId.SMART,
        AbilityId.STOP_STOP,
    },
    UnitTypeId.DISRUPTOR: {
        AbilityId.EFFECT_PURIFICATIONNOVA,
        AbilityId.HOLDPOSITION_HOLD,
        AbilityId.MOVE_MOVE,
        AbilityId.PATROL_PATROL,
        AbilityId.SCAN_MOVE,
        AbilityId.SMART,
        AbilityId.STOP_STOP,
    },
    UnitTypeId.DISRUPTORPHASED: {
        AbilityId.HOLDPOSITION_HOLD,
        AbilityId.MOVE_MOVE,
        AbilityId.PATROL_PATROL,
        AbilityId.SCAN_MOVE,
        AbilityId.SMART,
        AbilityId.STOP_STOP,
    },
    UnitTypeId.DRONE: {
        AbilityId.ATTACK_ATTACK,
        AbilityId.BUILD_LURKERDEN,
        AbilityId.BURROWDOWN_DRONE,
        AbilityId.EFFECT_SPRAY_ZERG,
        AbilityId.HARVEST_GATHER_DRONE,
        AbilityId.HOLDPOSITION_HOLD,
        AbilityId.MOVE_MOVE,
        AbilityId.PATROL_PATROL,
        AbilityId.SMART,
        AbilityId.STOP_STOP,
        AbilityId.ZERGBUILD_BANELINGNEST,
        AbilityId.ZERGBUILD_EVOLUTIONCHAMBER,
        AbilityId.ZERGBUILD_EXTRACTOR,
        AbilityId.ZERGBUILD_HATCHERY,
        AbilityId.ZERGBUILD_HYDRALISKDEN,
        AbilityId.ZERGBUILD_INFESTATIONPIT,
        AbilityId.ZERGBUILD_NYDUSNETWORK,
        AbilityId.ZERGBUILD_ROACHWARREN,
        AbilityId.ZERGBUILD_SPAWNINGPOOL,
        AbilityId.ZERGBUILD_SPINECRAWLER,
        AbilityId.ZERGBUILD_SPIRE,
        AbilityId.ZERGBUILD_SPORECRAWLER,
        AbilityId.ZERGBUILD_ULTRALISKCAVERN,
    },
    UnitTypeId.DRONEBURROWED: {AbilityId.BURROWUP_DRONE},
    UnitTypeId.EGG: {AbilityId.RALLY_BUILDING, AbilityId.SMART},
    UnitTypeId.ELSECARO_COLONIST_HUT: {AbilityId.RALLY_BUILDING, AbilityId.SMART},
    UnitTypeId.ENGINEERINGBAY: {
        AbilityId.ENGINEERINGBAYRESEARCH_TERRANINFANTRYARMORLEVEL1,
        AbilityId.ENGINEERINGBAYRESEARCH_TERRANINFANTRYARMORLEVEL2,
        AbilityId.ENGINEERINGBAYRESEARCH_TERRANINFANTRYARMORLEVEL3,
        AbilityId.ENGINEERINGBAYRESEARCH_TERRANINFANTRYWEAPONSLEVEL1,
        AbilityId.ENGINEERINGBAYRESEARCH_TERRANINFANTRYWEAPONSLEVEL2,
        AbilityId.ENGINEERINGBAYRESEARCH_TERRANINFANTRYWEAPONSLEVEL3,
        AbilityId.RESEARCH_HISECAUTOTRACKING,
        AbilityId.RESEARCH_TERRANSTRUCTUREARMORUPGRADE,
    },
    UnitTypeId.EVOLUTIONCHAMBER: {
        AbilityId.RESEARCH_ZERGGROUNDARMORLEVEL1,
        AbilityId.RESEARCH_ZERGGROUNDARMORLEVEL2,
        AbilityId.RESEARCH_ZERGGROUNDARMORLEVEL3,
        AbilityId.RESEARCH_ZERGMELEEWEAPONSLEVEL1,
        AbilityId.RESEARCH_ZERGMELEEWEAPONSLEVEL2,
        AbilityId.RESEARCH_ZERGMELEEWEAPONSLEVEL3,
        AbilityId.RESEARCH_ZERGMISSILEWEAPONSLEVEL1,
        AbilityId.RESEARCH_ZERGMISSILEWEAPONSLEVEL2,
        AbilityId.RESEARCH_ZERGMISSILEWEAPONSLEVEL3,
    },
    UnitTypeId.FACTORY: {
        AbilityId.BUILD_REACTOR_FACTORY,
        AbilityId.BUILD_TECHLAB_FACTORY,
        AbilityId.FACTORYTRAIN_HELLION,
        AbilityId.FACTORYTRAIN_SIEGETANK,
        AbilityId.FACTORYTRAIN_THOR,
        AbilityId.FACTORYTRAIN_WIDOWMINE,
        AbilityId.LIFT_FACTORY,
        AbilityId.RALLY_BUILDING,
        AbilityId.SMART,
        AbilityId.TRAIN_CYCLONE,
        AbilityId.TRAIN_HELLBAT,
    },
    UnitTypeId.FACTORYFLYING: {
        AbilityId.BUILD_REACTOR_FACTORY,
        AbilityId.BUILD_TECHLAB_FACTORY,
        AbilityId.HOLDPOSITION_HOLD,
        AbilityId.LAND_FACTORY,
        AbilityId.MOVE_MOVE,
        AbilityId.PATROL_PATROL,
        AbilityId.SMART,
        AbilityId.STOP_STOP,
    },
    UnitTypeId.FACTORYTECHLAB: {
        AbilityId.RESEARCH_CYCLONELOCKONDAMAGE,
        AbilityId.RESEARCH_DRILLINGCLAWS,
        AbilityId.RESEARCH_INFERNALPREIGNITER,
        AbilityId.RESEARCH_SMARTSERVOS,
    },
    UnitTypeId.FLEETBEACON: {
        AbilityId.FLEETBEACONRESEARCH_RESEARCHVOIDRAYSPEEDUPGRADE,
        AbilityId.FLEETBEACONRESEARCH_TEMPESTRESEARCHGROUNDATTACKUPGRADE,
        AbilityId.RESEARCH_PHOENIXANIONPULSECRYSTALS,
    },
    UnitTypeId.FORGE: {
        AbilityId.FORGERESEARCH_PROTOSSGROUNDARMORLEVEL1,
        AbilityId.FORGERESEARCH_PROTOSSGROUNDARMORLEVEL2,
        AbilityId.FORGERESEARCH_PROTOSSGROUNDARMORLEVEL3,
        AbilityId.FORGERESEARCH_PROTOSSGROUNDWEAPONSLEVEL1,
        AbilityId.FORGERESEARCH_PROTOSSGROUNDWEAPONSLEVEL2,
        AbilityId.FORGERESEARCH_PROTOSSGROUNDWEAPONSLEVEL3,
        AbilityId.FORGERESEARCH_PROTOSSSHIELDSLEVEL1,
        AbilityId.FORGERESEARCH_PROTOSSSHIELDSLEVEL2,
        AbilityId.FORGERESEARCH_PROTOSSSHIELDSLEVEL3,
    },
    UnitTypeId.FUSIONCORE: {
        AbilityId.FUSIONCORERESEARCH_RESEARCHBALLISTICRANGE,
        AbilityId.FUSIONCORERESEARCH_RESEARCHMEDIVACENERGYUPGRADE,
        AbilityId.RESEARCH_BATTLECRUISERWEAPONREFIT,
    },
    UnitTypeId.GATEWAY: {
        AbilityId.GATEWAYTRAIN_DARKTEMPLAR,
        AbilityId.GATEWAYTRAIN_HIGHTEMPLAR,
        AbilityId.GATEWAYTRAIN_SENTRY,
        AbilityId.GATEWAYTRAIN_STALKER,
        AbilityId.GATEWAYTRAIN_ZEALOT,
        AbilityId.MORPH_WARPGATE,
        AbilityId.RALLY_BUILDING,
        AbilityId.SMART,
        AbilityId.TRAIN_ADEPT,
    },
    UnitTypeId.GHOST: {
        AbilityId.ATTACK_ATTACK,
        AbilityId.BEHAVIOR_CLOAKON_GHOST,
        AbilityId.BEHAVIOR_HOLDFIREON_GHOST,
        AbilityId.EFFECT_GHOSTSNIPE,
        AbilityId.EMP_EMP,
        AbilityId.HOLDPOSITION_HOLD,
        AbilityId.MOVE_MOVE,
        AbilityId.PATROL_PATROL,
        AbilityId.SMART,
        AbilityId.STOP_STOP,
    },
    UnitTypeId.GHOSTACADEMY: {AbilityId.BUILD_NUKE, AbilityId.RESEARCH_PERSONALCLOAKING},
    UnitTypeId.GHOSTNOVA: {
        AbilityId.ATTACK_ATTACK,
        AbilityId.BEHAVIOR_CLOAKON_GHOST,
        AbilityId.BEHAVIOR_HOLDFIREON_GHOST,
        AbilityId.EFFECT_GHOSTSNIPE,
        AbilityId.EMP_EMP,
        AbilityId.HOLDPOSITION_HOLD,
        AbilityId.MOVE_MOVE,
        AbilityId.PATROL_PATROL,
        AbilityId.SMART,
        AbilityId.STOP_STOP,
    },
    UnitTypeId.GREATERSPIRE: {
        AbilityId.RESEARCH_ZERGFLYERARMORLEVEL1,
        AbilityId.RESEARCH_ZERGFLYERARMORLEVEL2,
        AbilityId.RESEARCH_ZERGFLYERARMORLEVEL3,
        AbilityId.RESEARCH_ZERGFLYERATTACKLEVEL1,
        AbilityId.RESEARCH_ZERGFLYERATTACKLEVEL2,
        AbilityId.RESEARCH_ZERGFLYERATTACKLEVEL3,
    },
    UnitTypeId.GUARDIANMP: {
        AbilityId.ATTACK_ATTACK,
        AbilityId.HOLDPOSITION_HOLD,
        AbilityId.MOVE_MOVE,
        AbilityId.PATROL_PATROL,
        AbilityId.SMART,
        AbilityId.STOP_STOP,
    },
    UnitTypeId.HATCHERY: {
        AbilityId.RALLY_HATCHERY_UNITS,
        AbilityId.RALLY_HATCHERY_WORKERS,
        AbilityId.RESEARCH_BURROW,
        AbilityId.RESEARCH_PNEUMATIZEDCARAPACE,
        AbilityId.SMART,
        AbilityId.TRAINQUEEN_QUEEN,
        AbilityId.UPGRADETOLAIR_LAIR,
    },
    UnitTypeId.HELLION: {
        AbilityId.ATTACK_ATTACK,
        AbilityId.HOLDPOSITION_HOLD,
        AbilityId.MORPH_HELLBAT,
        AbilityId.MOVE_MOVE,
        AbilityId.PATROL_PATROL,
        AbilityId.SMART,
        AbilityId.STOP_STOP,
    },
    UnitTypeId.HELLIONTANK: {
        AbilityId.ATTACK_ATTACK,
        AbilityId.HOLDPOSITION_HOLD,
        AbilityId.MORPH_HELLION,
        AbilityId.MOVE_MOVE,
        AbilityId.PATROL_PATROL,
        AbilityId.SMART,
        AbilityId.STOP_STOP,
    },
    UnitTypeId.HERC: {
        AbilityId.ATTACK_ATTACK,
        AbilityId.HOLDPOSITION_HOLD,
        AbilityId.MOVE_MOVE,
        AbilityId.PATROL_PATROL,
        AbilityId.SMART,
        AbilityId.STOP_STOP,
    },
    UnitTypeId.HERCPLACEMENT: {
        AbilityId.ATTACK_ATTACK,
        AbilityId.HOLDPOSITION_HOLD,
        AbilityId.MOVE_MOVE,
        AbilityId.PATROL_PATROL,
        AbilityId.SMART,
        AbilityId.STOP_STOP,
    },
    UnitTypeId.HIGHTEMPLAR: {
        AbilityId.ATTACK_ATTACK,
        AbilityId.FEEDBACK_FEEDBACK,
        AbilityId.HOLDPOSITION_HOLD,
        AbilityId.MORPH_ARCHON,
        AbilityId.MOVE_MOVE,
        AbilityId.PATROL_PATROL,
        AbilityId.PSISTORM_PSISTORM,
        AbilityId.SCAN_MOVE,
        AbilityId.SMART,
        AbilityId.STOP_STOP,
    },
    UnitTypeId.HIVE: {
        AbilityId.RALLY_HATCHERY_UNITS,
        AbilityId.RALLY_HATCHERY_WORKERS,
        AbilityId.RESEARCH_BURROW,
        AbilityId.RESEARCH_PNEUMATIZEDCARAPACE,
        AbilityId.SMART,
        AbilityId.TRAINQUEEN_QUEEN,
    },
    UnitTypeId.HYDRALISK: {
        AbilityId.ATTACK_ATTACK,
        AbilityId.BURROWDOWN_HYDRALISK,
        AbilityId.HOLDPOSITION_HOLD,
        AbilityId.HYDRALISKFRENZY_HYDRALISKFRENZY,
        AbilityId.MORPH_LURKER,
        AbilityId.MOVE_MOVE,
        AbilityId.PATROL_PATROL,
        AbilityId.SMART,
        AbilityId.STOP_STOP,
    },
    UnitTypeId.HYDRALISKBURROWED: {AbilityId.BURROWUP_HYDRALISK},
    UnitTypeId.HYDRALISKDEN: {
        AbilityId.HYDRALISKDENRESEARCH_RESEARCHFRENZY,
        AbilityId.RESEARCH_GROOVEDSPINES,
        AbilityId.RESEARCH_MUSCULARAUGMENTS,
    },
    UnitTypeId.IMMORTAL: {
        AbilityId.ATTACK_ATTACK,
        AbilityId.HOLDPOSITION_HOLD,
        AbilityId.MOVE_MOVE,
        AbilityId.PATROL_PATROL,
        AbilityId.SMART,
        AbilityId.STOP_STOP,
    },
    UnitTypeId.INFESTATIONPIT: {AbilityId.RESEARCH_NEURALPARASITE},
    UnitTypeId.INFESTOR: {
        AbilityId.AMORPHOUSARMORCLOUD_AMORPHOUSARMORCLOUD,
        AbilityId.BURROWDOWN_INFESTOR,
        AbilityId.BURROWDOWN_INFESTORTERRAN,
        AbilityId.FUNGALGROWTH_FUNGALGROWTH,
        AbilityId.HOLDPOSITION_HOLD,
        AbilityId.MOVE_MOVE,
        AbilityId.NEURALPARASITE_NEURALPARASITE,
        AbilityId.PATROL_PATROL,
        AbilityId.SCAN_MOVE,
        AbilityId.SMART,
        AbilityId.STOP_STOP,
    },
    UnitTypeId.INFESTORBURROWED: {
        AbilityId.BURROWUP_INFESTOR,
        AbilityId.BURROWUP_INFESTORTERRAN,
        AbilityId.HOLDPOSITION_HOLD,
        AbilityId.MOVE_MOVE,
        AbilityId.NEURALPARASITE_NEURALPARASITE,
        AbilityId.PATROL_PATROL,
        AbilityId.SCAN_MOVE,
        AbilityId.SMART,
        AbilityId.STOP_STOP,
    },
    UnitTypeId.INFESTORTERRAN: {
        AbilityId.ATTACK_ATTACK,
        AbilityId.BURROWDOWN_INFESTORTERRAN,
        AbilityId.HOLDPOSITION_HOLD,
        AbilityId.MOVE_MOVE,
        AbilityId.PATROL_PATROL,
        AbilityId.SMART,
        AbilityId.STOP_STOP,
    },
    UnitTypeId.INFESTORTERRANBURROWED: {AbilityId.BURROWUP_INFESTORTERRAN},
    UnitTypeId.INTERCEPTOR: {
        AbilityId.ATTACK_ATTACK,
        AbilityId.HOLDPOSITION_HOLD,
        AbilityId.MOVE_MOVE,
        AbilityId.PATROL_PATROL,
        AbilityId.SMART,
        AbilityId.STOP_STOP,
    },
    UnitTypeId.LAIR: {
        AbilityId.RALLY_HATCHERY_UNITS,
        AbilityId.RALLY_HATCHERY_WORKERS,
        AbilityId.RESEARCH_BURROW,
        AbilityId.RESEARCH_PNEUMATIZEDCARAPACE,
        AbilityId.SMART,
        AbilityId.TRAINQUEEN_QUEEN,
        AbilityId.UPGRADETOHIVE_HIVE,
    },
    UnitTypeId.LARVA: {
        AbilityId.LARVATRAIN_CORRUPTOR,
        AbilityId.LARVATRAIN_DRONE,
        AbilityId.LARVATRAIN_HYDRALISK,
        AbilityId.LARVATRAIN_INFESTOR,
        AbilityId.LARVATRAIN_MUTALISK,
        AbilityId.LARVATRAIN_OVERLORD,
        AbilityId.LARVATRAIN_ROACH,
        AbilityId.LARVATRAIN_ULTRALISK,
        AbilityId.LARVATRAIN_VIPER,
        AbilityId.LARVATRAIN_ZERGLING,
        AbilityId.TRAIN_SWARMHOST,
    },
    UnitTypeId.LIBERATOR: {
        AbilityId.ATTACK_ATTACK,
        AbilityId.HOLDPOSITION_HOLD,
        AbilityId.MORPH_LIBERATORAGMODE,
        AbilityId.MOVE_MOVE,
        AbilityId.PATROL_PATROL,
        AbilityId.SMART,
        AbilityId.STOP_STOP,
    },
    UnitTypeId.LIBERATORAG: {
        AbilityId.ATTACK_ATTACK,
        AbilityId.MORPH_LIBERATORAAMODE,
        AbilityId.SMART,
        AbilityId.STOP_STOP,
    },
    UnitTypeId.LOCUSTMP: {
        AbilityId.ATTACK_ATTACK,
        AbilityId.HOLDPOSITION_HOLD,
        AbilityId.MOVE_MOVE,
        AbilityId.PATROL_PATROL,
        AbilityId.SMART,
        AbilityId.STOP_STOP,
    },
    UnitTypeId.LOCUSTMPFLYING: {
        AbilityId.ATTACK_ATTACK,
        AbilityId.EFFECT_LOCUSTSWOOP,
        AbilityId.HOLDPOSITION_HOLD,
        AbilityId.MOVE_MOVE,
        AbilityId.PATROL_PATROL,
        AbilityId.SMART,
        AbilityId.STOP_STOP,
    },
    UnitTypeId.LURKERDENMP: {AbilityId.LURKERDENRESEARCH_RESEARCHLURKERRANGE, AbilityId.RESEARCH_ADAPTIVETALONS},
    UnitTypeId.LURKERMP: {
        AbilityId.ATTACK_ATTACK,
        AbilityId.BURROWDOWN_LURKER,
        AbilityId.HOLDPOSITION_HOLD,
        AbilityId.MOVE_MOVE,
        AbilityId.PATROL_PATROL,
        AbilityId.SCAN_MOVE,
        AbilityId.SMART,
        AbilityId.STOP_STOP,
    },
    UnitTypeId.LURKERMPBURROWED: {
        AbilityId.ATTACK_ATTACK,
        AbilityId.BEHAVIOR_HOLDFIREON_LURKER,
        AbilityId.BURROWUP_LURKER,
        AbilityId.SMART,
        AbilityId.STOP_STOP,
    },
    UnitTypeId.LURKERMPEGG: {AbilityId.RALLY_BUILDING, AbilityId.SMART},
    UnitTypeId.MARAUDER: {
        AbilityId.ATTACK_ATTACK,
        AbilityId.EFFECT_STIM_MARAUDER,
        AbilityId.HOLDPOSITION_HOLD,
        AbilityId.MOVE_MOVE,
        AbilityId.PATROL_PATROL,
        AbilityId.SMART,
        AbilityId.STOP_STOP,
    },
    UnitTypeId.MARINE: {
        AbilityId.ATTACK_ATTACK,
        AbilityId.EFFECT_STIM_MARINE,
        AbilityId.HOLDPOSITION_HOLD,
        AbilityId.MOVE_MOVE,
        AbilityId.PATROL_PATROL,
        AbilityId.SMART,
        AbilityId.STOP_STOP,
    },
    UnitTypeId.MEDIVAC: {
        AbilityId.EFFECT_MEDIVACIGNITEAFTERBURNERS,
        AbilityId.HOLDPOSITION_HOLD,
        AbilityId.LOAD_MEDIVAC,
        AbilityId.MEDIVACHEAL_HEAL,
        AbilityId.MOVE_MOVE,
        AbilityId.PATROL_PATROL,
        AbilityId.SCAN_MOVE,
        AbilityId.SMART,
        AbilityId.STOP_STOP,
    },
    UnitTypeId.MISSILETURRET: {AbilityId.ATTACK_ATTACK, AbilityId.SMART, AbilityId.STOP_STOP},
    UnitTypeId.MOTHERSHIP: {
        AbilityId.ATTACK_ATTACK,
        AbilityId.EFFECT_MASSRECALL_STRATEGICRECALL,
        AbilityId.EFFECT_TIMEWARP,
        AbilityId.HOLDPOSITION_HOLD,
        AbilityId.MOTHERSHIPCLOAK_ORACLECLOAKFIELD,
        AbilityId.MOVE_MOVE,
        AbilityId.PATROL_PATROL,
        AbilityId.SMART,
        AbilityId.STOP_STOP,
    },
    UnitTypeId.MOTHERSHIPCORE: {
        AbilityId.ATTACK_ATTACK,
        AbilityId.EFFECT_MASSRECALL_MOTHERSHIPCORE,
        AbilityId.EFFECT_PHOTONOVERCHARGE,
        AbilityId.EFFECT_TIMEWARP,
        AbilityId.HOLDPOSITION_HOLD,
        AbilityId.MORPH_MOTHERSHIP,
        AbilityId.MOVE_MOVE,
        AbilityId.PATROL_PATROL,
        AbilityId.SMART,
        AbilityId.STOP_STOP,
    },
    UnitTypeId.MULE: {
        AbilityId.EFFECT_REPAIR_MULE,
        AbilityId.HARVEST_GATHER_MULE,
        AbilityId.HOLDPOSITION_HOLD,
        AbilityId.MOVE_MOVE,
        AbilityId.PATROL_PATROL,
        AbilityId.SCAN_MOVE,
        AbilityId.SMART,
        AbilityId.STOP_STOP,
    },
    UnitTypeId.MUTALISK: {
        AbilityId.ATTACK_ATTACK,
        AbilityId.HOLDPOSITION_HOLD,
        AbilityId.MOVE_MOVE,
        AbilityId.PATROL_PATROL,
        AbilityId.SMART,
        AbilityId.STOP_STOP,
    },
    UnitTypeId.NEXUS: {
        AbilityId.EFFECT_CHRONOBOOSTENERGYCOST,
        AbilityId.EFFECT_MASSRECALL_NEXUS,
        AbilityId.ENERGYRECHARGE_ENERGYRECHARGE,
        AbilityId.NEXUSTRAINMOTHERSHIP_MOTHERSHIP,
        AbilityId.NEXUSTRAIN_PROBE,
        AbilityId.RALLY_NEXUS,
        AbilityId.SMART,
    },
    UnitTypeId.NYDUSCANAL: {AbilityId.LOAD_NYDUSWORM, AbilityId.RALLY_BUILDING, AbilityId.SMART, AbilityId.STOP_STOP},
    UnitTypeId.NYDUSCANALATTACKER: {AbilityId.ATTACK_ATTACK, AbilityId.SMART, AbilityId.STOP_STOP},
    UnitTypeId.NYDUSCANALCREEPER: {
        AbilityId.ATTACK_ATTACK,
        AbilityId.DIGESTERCREEPSPRAY_DIGESTERCREEPSPRAY,
        AbilityId.SMART,
        AbilityId.STOP_STOP,
    },
    UnitTypeId.NYDUSNETWORK: {
        AbilityId.BUILD_NYDUSWORM,
        AbilityId.LOAD_NYDUSNETWORK,
        AbilityId.RALLY_BUILDING,
        AbilityId.SMART,
        AbilityId.STOP_STOP,
    },
    UnitTypeId.OBSERVER: {
        AbilityId.HOLDPOSITION_HOLD,
        AbilityId.MORPH_SURVEILLANCEMODE,
        AbilityId.MOVE_MOVE,
        AbilityId.PATROL_PATROL,
        AbilityId.SCAN_MOVE,
        AbilityId.SMART,
        AbilityId.STOP_STOP,
    },
    UnitTypeId.OBSERVERSIEGEMODE: {AbilityId.MORPH_OBSERVERMODE, AbilityId.STOP_STOP},
    UnitTypeId.ORACLE: {
        AbilityId.ATTACK_ATTACK,
        AbilityId.BEHAVIOR_PULSARBEAMON,
        AbilityId.BUILD_STASISTRAP,
        AbilityId.HOLDPOSITION_HOLD,
        AbilityId.MOVE_MOVE,
        AbilityId.ORACLEREVELATION_ORACLEREVELATION,
        AbilityId.PATROL_PATROL,
        AbilityId.SCAN_MOVE,
        AbilityId.SMART,
        AbilityId.STOP_STOP,
    },
    UnitTypeId.ORBITALCOMMAND: {
        AbilityId.CALLDOWNMULE_CALLDOWNMULE,
        AbilityId.COMMANDCENTERTRAIN_SCV,
        AbilityId.LIFT_ORBITALCOMMAND,
        AbilityId.RALLY_COMMANDCENTER,
        AbilityId.SCANNERSWEEP_SCAN,
        AbilityId.SMART,
        AbilityId.SUPPLYDROP_SUPPLYDROP,
    },
    UnitTypeId.ORBITALCOMMANDFLYING: {
        AbilityId.HOLDPOSITION_HOLD,
        AbilityId.LAND_ORBITALCOMMAND,
        AbilityId.MOVE_MOVE,
        AbilityId.PATROL_PATROL,
        AbilityId.SMART,
        AbilityId.STOP_STOP,
    },
    UnitTypeId.OVERLORD: {
        AbilityId.BEHAVIOR_GENERATECREEPON,
        AbilityId.HOLDPOSITION_HOLD,
        AbilityId.MORPH_OVERLORDTRANSPORT,
        AbilityId.MORPH_OVERSEER,
        AbilityId.MOVE_MOVE,
        AbilityId.PATROL_PATROL,
        AbilityId.SCAN_MOVE,
        AbilityId.SMART,
        AbilityId.STOP_STOP,
    },
    UnitTypeId.OVERLORDTRANSPORT: {
        AbilityId.BEHAVIOR_GENERATECREEPON,
        AbilityId.HOLDPOSITION_HOLD,
        AbilityId.LOAD_OVERLORD,
        AbilityId.MORPH_OVERSEER,
        AbilityId.MOVE_MOVE,
        AbilityId.PATROL_PATROL,
        AbilityId.SCAN_MOVE,
        AbilityId.SMART,
        AbilityId.STOP_STOP,
    },
    UnitTypeId.OVERSEER: {
        AbilityId.CONTAMINATE_CONTAMINATE,
        AbilityId.HOLDPOSITION_HOLD,
        AbilityId.MORPH_OVERSIGHTMODE,
        AbilityId.MOVE_MOVE,
        AbilityId.PATROL_PATROL,
        AbilityId.SCAN_MOVE,
        AbilityId.SMART,
        AbilityId.SPAWNCHANGELING_SPAWNCHANGELING,
        AbilityId.STOP_STOP,
    },
    UnitTypeId.OVERSEERSIEGEMODE: {
        AbilityId.CONTAMINATE_CONTAMINATE,
        AbilityId.MORPH_OVERSEERMODE,
        AbilityId.SMART,
        AbilityId.SPAWNCHANGELING_SPAWNCHANGELING,
        AbilityId.STOP_STOP,
    },
    UnitTypeId.PHOENIX: {
        AbilityId.ATTACK_ATTACK,
        AbilityId.GRAVITONBEAM_GRAVITONBEAM,
        AbilityId.HOLDPOSITION_HOLD,
        AbilityId.MOVE_MOVE,
        AbilityId.PATROL_PATROL,
        AbilityId.SMART,
        AbilityId.STOP_STOP,
    },
    UnitTypeId.PHOTONCANNON: {AbilityId.ATTACK_ATTACK, AbilityId.SMART, AbilityId.STOP_STOP},
    UnitTypeId.PLANETARYFORTRESS: {
        AbilityId.ATTACK_ATTACK,
        AbilityId.COMMANDCENTERTRAIN_SCV,
        AbilityId.LOADALL_COMMANDCENTER,
        AbilityId.RALLY_COMMANDCENTER,
        AbilityId.SMART,
        AbilityId.STOP_STOP,
    },
    UnitTypeId.PROBE: {
        AbilityId.ATTACK_ATTACK,
        AbilityId.BUILD_SHIELDBATTERY,
        AbilityId.EFFECT_SPRAY_PROTOSS,
        AbilityId.HARVEST_GATHER_PROBE,
        AbilityId.HOLDPOSITION_HOLD,
        AbilityId.MOVE_MOVE,
        AbilityId.PATROL_PATROL,
        AbilityId.PROTOSSBUILD_ASSIMILATOR,
        AbilityId.PROTOSSBUILD_CYBERNETICSCORE,
        AbilityId.PROTOSSBUILD_DARKSHRINE,
        AbilityId.PROTOSSBUILD_FLEETBEACON,
        AbilityId.PROTOSSBUILD_FORGE,
        AbilityId.PROTOSSBUILD_GATEWAY,
        AbilityId.PROTOSSBUILD_NEXUS,
        AbilityId.PROTOSSBUILD_PHOTONCANNON,
        AbilityId.PROTOSSBUILD_PYLON,
        AbilityId.PROTOSSBUILD_ROBOTICSBAY,
        AbilityId.PROTOSSBUILD_ROBOTICSFACILITY,
        AbilityId.PROTOSSBUILD_STARGATE,
        AbilityId.PROTOSSBUILD_TEMPLARARCHIVE,
        AbilityId.PROTOSSBUILD_TWILIGHTCOUNCIL,
        AbilityId.SMART,
        AbilityId.STOP_STOP,
    },
    UnitTypeId.QUEEN: {
        AbilityId.ATTACK_ATTACK,
        AbilityId.BUILD_CREEPTUMOR,
        AbilityId.BUILD_CREEPTUMOR_QUEEN,
        AbilityId.BURROWDOWN_QUEEN,
        AbilityId.EFFECT_INJECTLARVA,
        AbilityId.HOLDPOSITION_HOLD,
        AbilityId.MOVE_MOVE,
        AbilityId.PATROL_PATROL,
        AbilityId.SMART,
        AbilityId.STOP_STOP,
        AbilityId.TRANSFUSION_TRANSFUSION,
    },
    UnitTypeId.QUEENBURROWED: {AbilityId.BURROWUP_QUEEN},
    UnitTypeId.QUEENMP: {
        AbilityId.ATTACK_ATTACK,
        AbilityId.HOLDPOSITION_HOLD,
        AbilityId.MOVE_MOVE,
        AbilityId.PATROL_PATROL,
        AbilityId.QUEENMPENSNARE_QUEENMPENSNARE,
        AbilityId.QUEENMPINFESTCOMMANDCENTER_QUEENMPINFESTCOMMANDCENTER,
        AbilityId.QUEENMPSPAWNBROODLINGS_QUEENMPSPAWNBROODLINGS,
        AbilityId.SMART,
        AbilityId.STOP_STOP,
    },
    UnitTypeId.RAVAGER: {
        AbilityId.ATTACK_ATTACK,
        AbilityId.BURROWDOWN_RAVAGER,
        AbilityId.EFFECT_CORROSIVEBILE,
        AbilityId.HOLDPOSITION_HOLD,
        AbilityId.MOVE_MOVE,
        AbilityId.PATROL_PATROL,
        AbilityId.SMART,
        AbilityId.STOP_STOP,
    },
    UnitTypeId.RAVAGERBURROWED: {AbilityId.BURROWUP_RAVAGER},
    UnitTypeId.RAVAGERCOCOON: {AbilityId.RALLY_BUILDING, AbilityId.SMART},
    UnitTypeId.RAVEN: {
        AbilityId.BUILDAUTOTURRET_AUTOTURRET,
        AbilityId.EFFECT_ANTIARMORMISSILE,
        AbilityId.EFFECT_INTERFERENCEMATRIX,
        AbilityId.HOLDPOSITION_HOLD,
        AbilityId.MOVE_MOVE,
        AbilityId.PATROL_PATROL,
        AbilityId.SCAN_MOVE,
        AbilityId.SMART,
        AbilityId.STOP_STOP,
    },
    UnitTypeId.RAVENREPAIRDRONE: {AbilityId.EFFECT_REPAIR_REPAIRDRONE, AbilityId.SMART, AbilityId.STOP_STOP},
    UnitTypeId.REAPER: {
        AbilityId.ATTACK_ATTACK,
        AbilityId.HOLDPOSITION_HOLD,
        AbilityId.KD8CHARGE_KD8CHARGE,
        AbilityId.MOVE_MOVE,
        AbilityId.PATROL_PATROL,
        AbilityId.SMART,
        AbilityId.STOP_STOP,
    },
    UnitTypeId.REPLICANT: {
        AbilityId.ATTACK_ATTACK,
        AbilityId.HOLDPOSITION_HOLD,
        AbilityId.MOVE_MOVE,
        AbilityId.PATROL_PATROL,
        AbilityId.SMART,
        AbilityId.STOP_STOP,
    },
    UnitTypeId.ROACH: {
        AbilityId.ATTACK_ATTACK,
        AbilityId.BURROWDOWN_ROACH,
        AbilityId.HOLDPOSITION_HOLD,
        AbilityId.MORPHTORAVAGER_RAVAGER,
        AbilityId.MOVE_MOVE,
        AbilityId.PATROL_PATROL,
        AbilityId.SMART,
        AbilityId.STOP_STOP,
    },
    UnitTypeId.ROACHBURROWED: {
        AbilityId.BURROWUP_ROACH,
        AbilityId.HOLDPOSITION_HOLD,
        AbilityId.MOVE_MOVE,
        AbilityId.PATROL_PATROL,
        AbilityId.SCAN_MOVE,
        AbilityId.SMART,
        AbilityId.STOP_STOP,
    },
    UnitTypeId.ROACHWARREN: {AbilityId.RESEARCH_GLIALREGENERATION, AbilityId.RESEARCH_TUNNELINGCLAWS},
    UnitTypeId.ROBOTICSBAY: {
        AbilityId.RESEARCH_EXTENDEDTHERMALLANCE,
        AbilityId.RESEARCH_GRAVITICBOOSTER,
        AbilityId.RESEARCH_GRAVITICDRIVE,
    },
    UnitTypeId.ROBOTICSFACILITY: {
        AbilityId.RALLY_BUILDING,
        AbilityId.ROBOTICSFACILITYTRAIN_COLOSSUS,
        AbilityId.ROBOTICSFACILITYTRAIN_IMMORTAL,
        AbilityId.ROBOTICSFACILITYTRAIN_OBSERVER,
        AbilityId.ROBOTICSFACILITYTRAIN_WARPPRISM,
        AbilityId.SMART,
        AbilityId.TRAIN_DISRUPTOR,
    },
    UnitTypeId.SCOURGEMP: {
        AbilityId.ATTACK_ATTACK,
        AbilityId.HOLDPOSITION_HOLD,
        AbilityId.MOVE_MOVE,
        AbilityId.PATROL_PATROL,
        AbilityId.SMART,
        AbilityId.STOP_STOP,
    },
    UnitTypeId.SCOUTMP: {
        AbilityId.ATTACK_ATTACK,
        AbilityId.HOLDPOSITION_HOLD,
        AbilityId.MOVE_MOVE,
        AbilityId.PATROL_PATROL,
        AbilityId.SMART,
        AbilityId.STOP_STOP,
    },
    UnitTypeId.SCV: {
        AbilityId.ATTACK_ATTACK,
        AbilityId.EFFECT_REPAIR_SCV,
        AbilityId.EFFECT_SPRAY_TERRAN,
        AbilityId.HARVEST_GATHER_SCV,
        AbilityId.HOLDPOSITION_HOLD,
        AbilityId.MOVE_MOVE,
        AbilityId.PATROL_PATROL,
        AbilityId.SMART,
        AbilityId.STOP_STOP,
        AbilityId.TERRANBUILD_ARMORY,
        AbilityId.TERRANBUILD_BARRACKS,
        AbilityId.TERRANBUILD_BUNKER,
        AbilityId.TERRANBUILD_COMMANDCENTER,
        AbilityId.TERRANBUILD_ENGINEERINGBAY,
        AbilityId.TERRANBUILD_FACTORY,
        AbilityId.TERRANBUILD_FUSIONCORE,
        AbilityId.TERRANBUILD_GHOSTACADEMY,
        AbilityId.TERRANBUILD_MISSILETURRET,
        AbilityId.TERRANBUILD_REFINERY,
        AbilityId.TERRANBUILD_SENSORTOWER,
        AbilityId.TERRANBUILD_STARPORT,
        AbilityId.TERRANBUILD_SUPPLYDEPOT,
    },
    UnitTypeId.SENSORTOWER: {AbilityId.SALVAGEEFFECT_SALVAGE},
    UnitTypeId.SENTRY: {
        AbilityId.ATTACK_ATTACK,
        AbilityId.FORCEFIELD_FORCEFIELD,
        AbilityId.GUARDIANSHIELD_GUARDIANSHIELD,
        AbilityId.HALLUCINATION_ADEPT,
        AbilityId.HALLUCINATION_ARCHON,
        AbilityId.HALLUCINATION_COLOSSUS,
        AbilityId.HALLUCINATION_DISRUPTOR,
        AbilityId.HALLUCINATION_HIGHTEMPLAR,
        AbilityId.HALLUCINATION_IMMORTAL,
        AbilityId.HALLUCINATION_ORACLE,
        AbilityId.HALLUCINATION_PHOENIX,
        AbilityId.HALLUCINATION_PROBE,
        AbilityId.HALLUCINATION_STALKER,
        AbilityId.HALLUCINATION_VOIDRAY,
        AbilityId.HALLUCINATION_WARPPRISM,
        AbilityId.HALLUCINATION_ZEALOT,
        AbilityId.HOLDPOSITION_HOLD,
        AbilityId.MOVE_MOVE,
        AbilityId.PATROL_PATROL,
        AbilityId.SMART,
        AbilityId.STOP_STOP,
    },
    UnitTypeId.SHIELDBATTERY: {AbilityId.SHIELDBATTERYRECHARGEEX5_SHIELDBATTERYRECHARGE, AbilityId.SMART},
    UnitTypeId.SIEGETANK: {
        AbilityId.ATTACK_ATTACK,
        AbilityId.HOLDPOSITION_HOLD,
        AbilityId.MOVE_MOVE,
        AbilityId.PATROL_PATROL,
        AbilityId.SIEGEMODE_SIEGEMODE,
        AbilityId.SMART,
        AbilityId.STOP_STOP,
    },
    UnitTypeId.SIEGETANKSIEGED: {
        AbilityId.ATTACK_ATTACK,
        AbilityId.SMART,
        AbilityId.STOP_STOP,
        AbilityId.UNSIEGE_UNSIEGE,
    },
    UnitTypeId.SPAWNINGPOOL: {AbilityId.RESEARCH_ZERGLINGADRENALGLANDS, AbilityId.RESEARCH_ZERGLINGMETABOLICBOOST},
    UnitTypeId.SPINECRAWLER: {
        AbilityId.ATTACK_ATTACK,
        AbilityId.SMART,
        AbilityId.SPINECRAWLERUPROOT_SPINECRAWLERUPROOT,
        AbilityId.STOP_STOP,
    },
    UnitTypeId.SPINECRAWLERUPROOTED: {
        AbilityId.HOLDPOSITION_HOLD,
        AbilityId.MOVE_MOVE,
        AbilityId.PATROL_PATROL,
        AbilityId.SCAN_MOVE,
        AbilityId.SMART,
        AbilityId.SPINECRAWLERROOT_SPINECRAWLERROOT,
        AbilityId.STOP_STOP,
    },
    UnitTypeId.SPIRE: {
        AbilityId.RESEARCH_ZERGFLYERARMORLEVEL1,
        AbilityId.RESEARCH_ZERGFLYERARMORLEVEL2,
        AbilityId.RESEARCH_ZERGFLYERARMORLEVEL3,
        AbilityId.RESEARCH_ZERGFLYERATTACKLEVEL1,
        AbilityId.RESEARCH_ZERGFLYERATTACKLEVEL2,
        AbilityId.RESEARCH_ZERGFLYERATTACKLEVEL3,
        AbilityId.UPGRADETOGREATERSPIRE_GREATERSPIRE,
    },
    UnitTypeId.SPORECRAWLER: {
        AbilityId.ATTACK_ATTACK,
        AbilityId.SMART,
        AbilityId.SPORECRAWLERUPROOT_SPORECRAWLERUPROOT,
        AbilityId.STOP_STOP,
    },
    UnitTypeId.SPORECRAWLERUPROOTED: {
        AbilityId.HOLDPOSITION_HOLD,
        AbilityId.MOVE_MOVE,
        AbilityId.PATROL_PATROL,
        AbilityId.SCAN_MOVE,
        AbilityId.SMART,
        AbilityId.SPORECRAWLERROOT_SPORECRAWLERROOT,
        AbilityId.STOP_STOP,
    },
    UnitTypeId.STALKER: {
        AbilityId.ATTACK_ATTACK,
        AbilityId.EFFECT_BLINK_STALKER,
        AbilityId.HOLDPOSITION_HOLD,
        AbilityId.MOVE_MOVE,
        AbilityId.PATROL_PATROL,
        AbilityId.SMART,
        AbilityId.STOP_STOP,
    },
    UnitTypeId.STARGATE: {
        AbilityId.RALLY_BUILDING,
        AbilityId.SMART,
        AbilityId.STARGATETRAIN_CARRIER,
        AbilityId.STARGATETRAIN_ORACLE,
        AbilityId.STARGATETRAIN_PHOENIX,
        AbilityId.STARGATETRAIN_TEMPEST,
        AbilityId.STARGATETRAIN_VOIDRAY,
    },
    UnitTypeId.STARPORT: {
        AbilityId.BUILD_REACTOR_STARPORT,
        AbilityId.BUILD_TECHLAB_STARPORT,
        AbilityId.LIFT_STARPORT,
        AbilityId.RALLY_BUILDING,
        AbilityId.SMART,
        AbilityId.STARPORTTRAIN_BANSHEE,
        AbilityId.STARPORTTRAIN_BATTLECRUISER,
        AbilityId.STARPORTTRAIN_LIBERATOR,
        AbilityId.STARPORTTRAIN_MEDIVAC,
        AbilityId.STARPORTTRAIN_RAVEN,
        AbilityId.STARPORTTRAIN_VIKINGFIGHTER,
    },
    UnitTypeId.STARPORTFLYING: {
        AbilityId.BUILD_REACTOR_STARPORT,
        AbilityId.BUILD_TECHLAB_STARPORT,
        AbilityId.HOLDPOSITION_HOLD,
        AbilityId.LAND_STARPORT,
        AbilityId.MOVE_MOVE,
        AbilityId.PATROL_PATROL,
        AbilityId.SMART,
        AbilityId.STOP_STOP,
    },
    UnitTypeId.STARPORTTECHLAB: {
        AbilityId.RESEARCH_BANSHEECLOAKINGFIELD,
        AbilityId.RESEARCH_BANSHEEHYPERFLIGHTROTORS,
        AbilityId.STARPORTTECHLABRESEARCH_RESEARCHRAVENINTERFERENCEMATRIX,
    },
    UnitTypeId.SUPPLYDEPOT: {AbilityId.MORPH_SUPPLYDEPOT_LOWER},
    UnitTypeId.SUPPLYDEPOTLOWERED: {AbilityId.MORPH_SUPPLYDEPOT_RAISE},
    UnitTypeId.SWARMHOSTBURROWEDMP: {AbilityId.EFFECT_SPAWNLOCUSTS, AbilityId.SMART},
    UnitTypeId.SWARMHOSTMP: {
        AbilityId.BURROWDOWN_SWARMHOST,
        AbilityId.EFFECT_SPAWNLOCUSTS,
        AbilityId.HOLDPOSITION_HOLD,
        AbilityId.MOVE_MOVE,
        AbilityId.PATROL_PATROL,
        AbilityId.SCAN_MOVE,
        AbilityId.SMART,
        AbilityId.STOP_STOP,
    },
    UnitTypeId.TECHLAB: {
        AbilityId.BARRACKSTECHLABRESEARCH_STIMPACK,
        AbilityId.RESEARCH_BANSHEECLOAKINGFIELD,
        AbilityId.RESEARCH_COMBATSHIELD,
        AbilityId.RESEARCH_CONCUSSIVESHELLS,
        AbilityId.RESEARCH_DRILLINGCLAWS,
        AbilityId.RESEARCH_INFERNALPREIGNITER,
        AbilityId.RESEARCH_RAVENCORVIDREACTOR,
    },
    UnitTypeId.TEMPEST: {
        AbilityId.ATTACK_ATTACK,
        AbilityId.HOLDPOSITION_HOLD,
        AbilityId.MOVE_MOVE,
        AbilityId.PATROL_PATROL,
        AbilityId.SMART,
        AbilityId.STOP_STOP,
    },
    UnitTypeId.TEMPLARARCHIVE: {AbilityId.RESEARCH_PSISTORM},
    UnitTypeId.THOR: {
        AbilityId.ATTACK_ATTACK,
        AbilityId.HOLDPOSITION_HOLD,
        AbilityId.MORPH_THORHIGHIMPACTMODE,
        AbilityId.MOVE_MOVE,
        AbilityId.PATROL_PATROL,
        AbilityId.SMART,
        AbilityId.STOP_STOP,
    },
    UnitTypeId.THORAP: {
        AbilityId.ATTACK_ATTACK,
        AbilityId.HOLDPOSITION_HOLD,
        AbilityId.MORPH_THOREXPLOSIVEMODE,
        AbilityId.MOVE_MOVE,
        AbilityId.PATROL_PATROL,
        AbilityId.SMART,
        AbilityId.STOP_STOP,
    },
    UnitTypeId.TWILIGHTCOUNCIL: {
        AbilityId.RESEARCH_ADEPTRESONATINGGLAIVES,
        AbilityId.RESEARCH_BLINK,
        AbilityId.RESEARCH_CHARGE,
    },
    UnitTypeId.ULTRALISK: {
        AbilityId.ATTACK_ATTACK,
        AbilityId.BURROWDOWN_ULTRALISK,
        AbilityId.HOLDPOSITION_HOLD,
        AbilityId.MOVE_MOVE,
        AbilityId.PATROL_PATROL,
        AbilityId.SMART,
        AbilityId.STOP_STOP,
    },
    UnitTypeId.ULTRALISKBURROWED: {AbilityId.BURROWUP_ULTRALISK},
    UnitTypeId.ULTRALISKCAVERN: {AbilityId.RESEARCH_ANABOLICSYNTHESIS, AbilityId.RESEARCH_CHITINOUSPLATING},
    UnitTypeId.VIKINGASSAULT: {
        AbilityId.ATTACK_ATTACK,
        AbilityId.HOLDPOSITION_HOLD,
        AbilityId.MORPH_VIKINGFIGHTERMODE,
        AbilityId.MOVE_MOVE,
        AbilityId.PATROL_PATROL,
        AbilityId.SMART,
        AbilityId.STOP_STOP,
    },
    UnitTypeId.VIKINGFIGHTER: {
        AbilityId.ATTACK_ATTACK,
        AbilityId.HOLDPOSITION_HOLD,
        AbilityId.MORPH_VIKINGASSAULTMODE,
        AbilityId.MOVE_MOVE,
        AbilityId.PATROL_PATROL,
        AbilityId.SMART,
        AbilityId.STOP_STOP,
    },
    UnitTypeId.VIPER: {
        AbilityId.BLINDINGCLOUD_BLINDINGCLOUD,
        AbilityId.EFFECT_ABDUCT,
        AbilityId.HOLDPOSITION_HOLD,
        AbilityId.MOVE_MOVE,
        AbilityId.PARASITICBOMB_PARASITICBOMB,
        AbilityId.PATROL_PATROL,
        AbilityId.SCAN_MOVE,
        AbilityId.SMART,
        AbilityId.STOP_STOP,
        AbilityId.VIPERCONSUMESTRUCTURE_VIPERCONSUME,
    },
    UnitTypeId.VOIDMPIMMORTALREVIVECORPSE: {
        AbilityId.RALLY_BUILDING,
        AbilityId.SMART,
        AbilityId.VOIDMPIMMORTALREVIVEREBUILD_IMMORTAL,
    },
    UnitTypeId.VOIDRAY: {
        AbilityId.ATTACK_ATTACK,
        AbilityId.EFFECT_VOIDRAYPRISMATICALIGNMENT,
        AbilityId.HOLDPOSITION_HOLD,
        AbilityId.MOVE_MOVE,
        AbilityId.PATROL_PATROL,
        AbilityId.SMART,
        AbilityId.STOP_STOP,
    },
    UnitTypeId.WARHOUND: {
        AbilityId.ATTACK_ATTACK,
        AbilityId.HOLDPOSITION_HOLD,
        AbilityId.MOVE_MOVE,
        AbilityId.PATROL_PATROL,
        AbilityId.SMART,
        AbilityId.STOP_STOP,
        AbilityId.TORNADOMISSILE_TORNADOMISSILE,
    },
    UnitTypeId.WARPGATE: {
        AbilityId.MORPH_GATEWAY,
        AbilityId.SMART,
        AbilityId.TRAINWARP_ADEPT,
        AbilityId.WARPGATETRAIN_DARKTEMPLAR,
        AbilityId.WARPGATETRAIN_HIGHTEMPLAR,
        AbilityId.WARPGATETRAIN_SENTRY,
        AbilityId.WARPGATETRAIN_STALKER,
        AbilityId.WARPGATETRAIN_ZEALOT,
    },
    UnitTypeId.WARPPRISM: {
        AbilityId.HOLDPOSITION_HOLD,
        AbilityId.LOAD_WARPPRISM,
        AbilityId.MORPH_WARPPRISMPHASINGMODE,
        AbilityId.MOVE_MOVE,
        AbilityId.PATROL_PATROL,
        AbilityId.SCAN_MOVE,
        AbilityId.SMART,
        AbilityId.STOP_STOP,
    },
    UnitTypeId.WARPPRISMPHASING: {
        AbilityId.LOAD_WARPPRISM,
        AbilityId.MORPH_WARPPRISMTRANSPORTMODE,
        AbilityId.SMART,
        AbilityId.STOP_STOP,
    },
    UnitTypeId.WIDOWMINE: {
        AbilityId.BURROWDOWN_WIDOWMINE,
        AbilityId.HOLDPOSITION_HOLD,
        AbilityId.MOVE_MOVE,
        AbilityId.PATROL_PATROL,
        AbilityId.SCAN_MOVE,
        AbilityId.SMART,
        AbilityId.STOP_STOP,
    },
    UnitTypeId.WIDOWMINEBURROWED: {
        AbilityId.BURROWUP_WIDOWMINE,
        AbilityId.SMART,
        AbilityId.WIDOWMINEATTACK_WIDOWMINEATTACK,
    },
    UnitTypeId.ZEALOT: {
        AbilityId.ATTACK_ATTACK,
        AbilityId.EFFECT_CHARGE,
        AbilityId.HOLDPOSITION_HOLD,
        AbilityId.MOVE_MOVE,
        AbilityId.PATROL_PATROL,
        AbilityId.SMART,
        AbilityId.STOP_STOP,
    },
    UnitTypeId.ZERGLING: {
        AbilityId.ATTACK_ATTACK,
        AbilityId.BURROWDOWN_ZERGLING,
        AbilityId.HOLDPOSITION_HOLD,
        AbilityId.MORPHTOBANELING_BANELING,
        AbilityId.MOVE_MOVE,
        AbilityId.PATROL_PATROL,
        AbilityId.SMART,
        AbilityId.STOP_STOP,
    },
    UnitTypeId.ZERGLINGBURROWED: {AbilityId.BURROWUP_ZERGLING},
}
```

### File: `sc2/dicts/unit_research_abilities.py`

```python
# THIS FILE WAS AUTOMATICALLY GENERATED BY "generate_dicts_from_data_json.py" DO NOT CHANGE MANUALLY!
# ANY CHANGE WILL BE OVERWRITTEN

# from sc2.ids.buff_id import BuffId
# from sc2.ids.effect_id import EffectId
from typing import Union

from sc2.ids.ability_id import AbilityId
from sc2.ids.unit_typeid import UnitTypeId
from sc2.ids.upgrade_id import UpgradeId

RESEARCH_INFO: dict[UnitTypeId, dict[UpgradeId, dict[str, Union[AbilityId, bool, UnitTypeId, UpgradeId]]]] = {
    UnitTypeId.ARMORY: {
        UpgradeId.TERRANSHIPWEAPONSLEVEL1: {"ability": AbilityId.ARMORYRESEARCH_TERRANSHIPWEAPONSLEVEL1},
        UpgradeId.TERRANSHIPWEAPONSLEVEL2: {
            "ability": AbilityId.ARMORYRESEARCH_TERRANSHIPWEAPONSLEVEL2,
            "required_upgrade": UpgradeId.TERRANSHIPWEAPONSLEVEL1,
        },
        UpgradeId.TERRANSHIPWEAPONSLEVEL3: {
            "ability": AbilityId.ARMORYRESEARCH_TERRANSHIPWEAPONSLEVEL3,
            "required_upgrade": UpgradeId.TERRANSHIPWEAPONSLEVEL2,
        },
        UpgradeId.TERRANVEHICLEANDSHIPARMORSLEVEL1: {
            "ability": AbilityId.ARMORYRESEARCH_TERRANVEHICLEANDSHIPPLATINGLEVEL1
        },
        UpgradeId.TERRANVEHICLEANDSHIPARMORSLEVEL2: {
            "ability": AbilityId.ARMORYRESEARCH_TERRANVEHICLEANDSHIPPLATINGLEVEL2,
            "required_upgrade": UpgradeId.TERRANVEHICLEANDSHIPARMORSLEVEL1,
        },
        UpgradeId.TERRANVEHICLEANDSHIPARMORSLEVEL3: {
            "ability": AbilityId.ARMORYRESEARCH_TERRANVEHICLEANDSHIPPLATINGLEVEL3,
            "required_upgrade": UpgradeId.TERRANVEHICLEANDSHIPARMORSLEVEL2,
        },
        UpgradeId.TERRANVEHICLEWEAPONSLEVEL1: {"ability": AbilityId.ARMORYRESEARCH_TERRANVEHICLEWEAPONSLEVEL1},
        UpgradeId.TERRANVEHICLEWEAPONSLEVEL2: {
            "ability": AbilityId.ARMORYRESEARCH_TERRANVEHICLEWEAPONSLEVEL2,
            "required_upgrade": UpgradeId.TERRANVEHICLEWEAPONSLEVEL1,
        },
        UpgradeId.TERRANVEHICLEWEAPONSLEVEL3: {
            "ability": AbilityId.ARMORYRESEARCH_TERRANVEHICLEWEAPONSLEVEL3,
            "required_upgrade": UpgradeId.TERRANVEHICLEWEAPONSLEVEL2,
        },
    },
    UnitTypeId.BANELINGNEST: {
        UpgradeId.CENTRIFICALHOOKS: {
            "ability": AbilityId.RESEARCH_CENTRIFUGALHOOKS,
            "required_building": UnitTypeId.LAIR,
        }
    },
    UnitTypeId.BARRACKSTECHLAB: {
        UpgradeId.PUNISHERGRENADES: {"ability": AbilityId.RESEARCH_CONCUSSIVESHELLS},
        UpgradeId.SHIELDWALL: {"ability": AbilityId.RESEARCH_COMBATSHIELD},
        UpgradeId.STIMPACK: {"ability": AbilityId.BARRACKSTECHLABRESEARCH_STIMPACK},
    },
    UnitTypeId.CYBERNETICSCORE: {
        UpgradeId.PROTOSSAIRARMORSLEVEL1: {
            "ability": AbilityId.CYBERNETICSCORERESEARCH_PROTOSSAIRARMORLEVEL1,
            "requires_power": True,
        },
        UpgradeId.PROTOSSAIRARMORSLEVEL2: {
            "ability": AbilityId.CYBERNETICSCORERESEARCH_PROTOSSAIRARMORLEVEL2,
            "required_building": UnitTypeId.FLEETBEACON,
            "required_upgrade": UpgradeId.PROTOSSAIRARMORSLEVEL1,
            "requires_power": True,
        },
        UpgradeId.PROTOSSAIRARMORSLEVEL3: {
            "ability": AbilityId.CYBERNETICSCORERESEARCH_PROTOSSAIRARMORLEVEL3,
            "required_building": UnitTypeId.FLEETBEACON,
            "required_upgrade": UpgradeId.PROTOSSAIRARMORSLEVEL2,
            "requires_power": True,
        },
        UpgradeId.PROTOSSAIRWEAPONSLEVEL1: {
            "ability": AbilityId.CYBERNETICSCORERESEARCH_PROTOSSAIRWEAPONSLEVEL1,
            "requires_power": True,
        },
        UpgradeId.PROTOSSAIRWEAPONSLEVEL2: {
            "ability": AbilityId.CYBERNETICSCORERESEARCH_PROTOSSAIRWEAPONSLEVEL2,
            "required_building": UnitTypeId.FLEETBEACON,
            "required_upgrade": UpgradeId.PROTOSSAIRWEAPONSLEVEL1,
            "requires_power": True,
        },
        UpgradeId.PROTOSSAIRWEAPONSLEVEL3: {
            "ability": AbilityId.CYBERNETICSCORERESEARCH_PROTOSSAIRWEAPONSLEVEL3,
            "required_building": UnitTypeId.FLEETBEACON,
            "required_upgrade": UpgradeId.PROTOSSAIRWEAPONSLEVEL2,
            "requires_power": True,
        },
        UpgradeId.WARPGATERESEARCH: {"ability": AbilityId.RESEARCH_WARPGATE, "requires_power": True},
    },
    UnitTypeId.DARKSHRINE: {
        UpgradeId.DARKTEMPLARBLINKUPGRADE: {"ability": AbilityId.RESEARCH_SHADOWSTRIKE, "requires_power": True}
    },
    UnitTypeId.ENGINEERINGBAY: {
        UpgradeId.HISECAUTOTRACKING: {"ability": AbilityId.RESEARCH_HISECAUTOTRACKING},
        UpgradeId.TERRANBUILDINGARMOR: {"ability": AbilityId.RESEARCH_TERRANSTRUCTUREARMORUPGRADE},
        UpgradeId.TERRANINFANTRYARMORSLEVEL1: {"ability": AbilityId.ENGINEERINGBAYRESEARCH_TERRANINFANTRYARMORLEVEL1},
        UpgradeId.TERRANINFANTRYARMORSLEVEL2: {
            "ability": AbilityId.ENGINEERINGBAYRESEARCH_TERRANINFANTRYARMORLEVEL2,
            "required_building": UnitTypeId.ARMORY,
            "required_upgrade": UpgradeId.TERRANINFANTRYARMORSLEVEL1,
        },
        UpgradeId.TERRANINFANTRYARMORSLEVEL3: {
            "ability": AbilityId.ENGINEERINGBAYRESEARCH_TERRANINFANTRYARMORLEVEL3,
            "required_building": UnitTypeId.ARMORY,
            "required_upgrade": UpgradeId.TERRANINFANTRYARMORSLEVEL2,
        },
        UpgradeId.TERRANINFANTRYWEAPONSLEVEL1: {
            "ability": AbilityId.ENGINEERINGBAYRESEARCH_TERRANINFANTRYWEAPONSLEVEL1
        },
        UpgradeId.TERRANINFANTRYWEAPONSLEVEL2: {
            "ability": AbilityId.ENGINEERINGBAYRESEARCH_TERRANINFANTRYWEAPONSLEVEL2,
            "required_building": UnitTypeId.ARMORY,
            "required_upgrade": UpgradeId.TERRANINFANTRYWEAPONSLEVEL1,
        },
        UpgradeId.TERRANINFANTRYWEAPONSLEVEL3: {
            "ability": AbilityId.ENGINEERINGBAYRESEARCH_TERRANINFANTRYWEAPONSLEVEL3,
            "required_building": UnitTypeId.ARMORY,
            "required_upgrade": UpgradeId.TERRANINFANTRYWEAPONSLEVEL2,
        },
    },
    UnitTypeId.EVOLUTIONCHAMBER: {
        UpgradeId.ZERGGROUNDARMORSLEVEL1: {"ability": AbilityId.RESEARCH_ZERGGROUNDARMORLEVEL1},
        UpgradeId.ZERGGROUNDARMORSLEVEL2: {
            "ability": AbilityId.RESEARCH_ZERGGROUNDARMORLEVEL2,
            "required_building": UnitTypeId.LAIR,
            "required_upgrade": UpgradeId.ZERGGROUNDARMORSLEVEL1,
        },
        UpgradeId.ZERGGROUNDARMORSLEVEL3: {
            "ability": AbilityId.RESEARCH_ZERGGROUNDARMORLEVEL3,
            "required_building": UnitTypeId.HIVE,
            "required_upgrade": UpgradeId.ZERGGROUNDARMORSLEVEL2,
        },
        UpgradeId.ZERGMELEEWEAPONSLEVEL1: {"ability": AbilityId.RESEARCH_ZERGMELEEWEAPONSLEVEL1},
        UpgradeId.ZERGMELEEWEAPONSLEVEL2: {
            "ability": AbilityId.RESEARCH_ZERGMELEEWEAPONSLEVEL2,
            "required_building": UnitTypeId.LAIR,
            "required_upgrade": UpgradeId.ZERGMELEEWEAPONSLEVEL1,
        },
        UpgradeId.ZERGMELEEWEAPONSLEVEL3: {
            "ability": AbilityId.RESEARCH_ZERGMELEEWEAPONSLEVEL3,
            "required_building": UnitTypeId.HIVE,
            "required_upgrade": UpgradeId.ZERGMELEEWEAPONSLEVEL2,
        },
        UpgradeId.ZERGMISSILEWEAPONSLEVEL1: {"ability": AbilityId.RESEARCH_ZERGMISSILEWEAPONSLEVEL1},
        UpgradeId.ZERGMISSILEWEAPONSLEVEL2: {
            "ability": AbilityId.RESEARCH_ZERGMISSILEWEAPONSLEVEL2,
            "required_building": UnitTypeId.LAIR,
            "required_upgrade": UpgradeId.ZERGMISSILEWEAPONSLEVEL1,
        },
        UpgradeId.ZERGMISSILEWEAPONSLEVEL3: {
            "ability": AbilityId.RESEARCH_ZERGMISSILEWEAPONSLEVEL3,
            "required_building": UnitTypeId.HIVE,
            "required_upgrade": UpgradeId.ZERGMISSILEWEAPONSLEVEL2,
        },
    },
    UnitTypeId.FACTORYTECHLAB: {
        UpgradeId.CYCLONELOCKONDAMAGEUPGRADE: {"ability": AbilityId.RESEARCH_CYCLONELOCKONDAMAGE},
        UpgradeId.DRILLCLAWS: {"ability": AbilityId.RESEARCH_DRILLINGCLAWS, "required_building": UnitTypeId.ARMORY},
        UpgradeId.HIGHCAPACITYBARRELS: {"ability": AbilityId.RESEARCH_INFERNALPREIGNITER},
        UpgradeId.SMARTSERVOS: {"ability": AbilityId.RESEARCH_SMARTSERVOS, "required_building": UnitTypeId.ARMORY},
    },
    UnitTypeId.FLEETBEACON: {
        UpgradeId.PHOENIXRANGEUPGRADE: {
            "ability": AbilityId.RESEARCH_PHOENIXANIONPULSECRYSTALS,
            "requires_power": True,
        },
        UpgradeId.TEMPESTGROUNDATTACKUPGRADE: {
            "ability": AbilityId.FLEETBEACONRESEARCH_TEMPESTRESEARCHGROUNDATTACKUPGRADE,
            "requires_power": True,
        },
        UpgradeId.VOIDRAYSPEEDUPGRADE: {
            "ability": AbilityId.FLEETBEACONRESEARCH_RESEARCHVOIDRAYSPEEDUPGRADE,
            "requires_power": True,
        },
    },
    UnitTypeId.FORGE: {
        UpgradeId.PROTOSSGROUNDARMORSLEVEL1: {
            "ability": AbilityId.FORGERESEARCH_PROTOSSGROUNDARMORLEVEL1,
            "requires_power": True,
        },
        UpgradeId.PROTOSSGROUNDARMORSLEVEL2: {
            "ability": AbilityId.FORGERESEARCH_PROTOSSGROUNDARMORLEVEL2,
            "required_building": UnitTypeId.TWILIGHTCOUNCIL,
            "required_upgrade": UpgradeId.PROTOSSGROUNDARMORSLEVEL1,
            "requires_power": True,
        },
        UpgradeId.PROTOSSGROUNDARMORSLEVEL3: {
            "ability": AbilityId.FORGERESEARCH_PROTOSSGROUNDARMORLEVEL3,
            "required_building": UnitTypeId.TWILIGHTCOUNCIL,
            "required_upgrade": UpgradeId.PROTOSSGROUNDARMORSLEVEL2,
            "requires_power": True,
        },
        UpgradeId.PROTOSSGROUNDWEAPONSLEVEL1: {
            "ability": AbilityId.FORGERESEARCH_PROTOSSGROUNDWEAPONSLEVEL1,
            "requires_power": True,
        },
        UpgradeId.PROTOSSGROUNDWEAPONSLEVEL2: {
            "ability": AbilityId.FORGERESEARCH_PROTOSSGROUNDWEAPONSLEVEL2,
            "required_building": UnitTypeId.TWILIGHTCOUNCIL,
            "required_upgrade": UpgradeId.PROTOSSGROUNDWEAPONSLEVEL1,
            "requires_power": True,
        },
        UpgradeId.PROTOSSGROUNDWEAPONSLEVEL3: {
            "ability": AbilityId.FORGERESEARCH_PROTOSSGROUNDWEAPONSLEVEL3,
            "required_building": UnitTypeId.TWILIGHTCOUNCIL,
            "required_upgrade": UpgradeId.PROTOSSGROUNDWEAPONSLEVEL2,
            "requires_power": True,
        },
        UpgradeId.PROTOSSSHIELDSLEVEL1: {
            "ability": AbilityId.FORGERESEARCH_PROTOSSSHIELDSLEVEL1,
            "requires_power": True,
        },
        UpgradeId.PROTOSSSHIELDSLEVEL2: {
            "ability": AbilityId.FORGERESEARCH_PROTOSSSHIELDSLEVEL2,
            "required_building": UnitTypeId.TWILIGHTCOUNCIL,
            "required_upgrade": UpgradeId.PROTOSSSHIELDSLEVEL1,
            "requires_power": True,
        },
        UpgradeId.PROTOSSSHIELDSLEVEL3: {
            "ability": AbilityId.FORGERESEARCH_PROTOSSSHIELDSLEVEL3,
            "required_building": UnitTypeId.TWILIGHTCOUNCIL,
            "required_upgrade": UpgradeId.PROTOSSSHIELDSLEVEL2,
            "requires_power": True,
        },
    },
    UnitTypeId.FUSIONCORE: {
        UpgradeId.BATTLECRUISERENABLESPECIALIZATIONS: {"ability": AbilityId.RESEARCH_BATTLECRUISERWEAPONREFIT},
        UpgradeId.LIBERATORAGRANGEUPGRADE: {"ability": AbilityId.FUSIONCORERESEARCH_RESEARCHBALLISTICRANGE},
        UpgradeId.MEDIVACCADUCEUSREACTOR: {"ability": AbilityId.FUSIONCORERESEARCH_RESEARCHMEDIVACENERGYUPGRADE},
    },
    UnitTypeId.GHOSTACADEMY: {UpgradeId.PERSONALCLOAKING: {"ability": AbilityId.RESEARCH_PERSONALCLOAKING}},
    UnitTypeId.GREATERSPIRE: {
        UpgradeId.ZERGFLYERARMORSLEVEL1: {"ability": AbilityId.RESEARCH_ZERGFLYERARMORLEVEL1},
        UpgradeId.ZERGFLYERARMORSLEVEL2: {
            "ability": AbilityId.RESEARCH_ZERGFLYERARMORLEVEL2,
            "required_building": UnitTypeId.LAIR,
            "required_upgrade": UpgradeId.ZERGFLYERARMORSLEVEL1,
        },
        UpgradeId.ZERGFLYERARMORSLEVEL3: {
            "ability": AbilityId.RESEARCH_ZERGFLYERARMORLEVEL3,
            "required_building": UnitTypeId.HIVE,
            "required_upgrade": UpgradeId.ZERGFLYERARMORSLEVEL2,
        },
        UpgradeId.ZERGFLYERWEAPONSLEVEL1: {"ability": AbilityId.RESEARCH_ZERGFLYERATTACKLEVEL1},
        UpgradeId.ZERGFLYERWEAPONSLEVEL2: {
            "ability": AbilityId.RESEARCH_ZERGFLYERATTACKLEVEL2,
            "required_building": UnitTypeId.LAIR,
            "required_upgrade": UpgradeId.ZERGFLYERWEAPONSLEVEL1,
        },
        UpgradeId.ZERGFLYERWEAPONSLEVEL3: {
            "ability": AbilityId.RESEARCH_ZERGFLYERATTACKLEVEL3,
            "required_building": UnitTypeId.HIVE,
            "required_upgrade": UpgradeId.ZERGFLYERWEAPONSLEVEL2,
        },
    },
    UnitTypeId.HATCHERY: {
        UpgradeId.BURROW: {"ability": AbilityId.RESEARCH_BURROW},
        UpgradeId.OVERLORDSPEED: {"ability": AbilityId.RESEARCH_PNEUMATIZEDCARAPACE},
    },
    UnitTypeId.HIVE: {
        UpgradeId.BURROW: {"ability": AbilityId.RESEARCH_BURROW},
        UpgradeId.OVERLORDSPEED: {"ability": AbilityId.RESEARCH_PNEUMATIZEDCARAPACE},
    },
    UnitTypeId.HYDRALISKDEN: {
        UpgradeId.EVOLVEGROOVEDSPINES: {"ability": AbilityId.RESEARCH_GROOVEDSPINES},
        UpgradeId.EVOLVEMUSCULARAUGMENTS: {"ability": AbilityId.RESEARCH_MUSCULARAUGMENTS},
        UpgradeId.FRENZY: {
            "ability": AbilityId.HYDRALISKDENRESEARCH_RESEARCHFRENZY,
            "required_building": UnitTypeId.HIVE,
        },
    },
    UnitTypeId.INFESTATIONPIT: {UpgradeId.NEURALPARASITE: {"ability": AbilityId.RESEARCH_NEURALPARASITE}},
    UnitTypeId.LAIR: {
        UpgradeId.BURROW: {"ability": AbilityId.RESEARCH_BURROW},
        UpgradeId.OVERLORDSPEED: {"ability": AbilityId.RESEARCH_PNEUMATIZEDCARAPACE},
    },
    UnitTypeId.LURKERDENMP: {
        UpgradeId.DIGGINGCLAWS: {"ability": AbilityId.RESEARCH_ADAPTIVETALONS, "required_building": UnitTypeId.HIVE},
        UpgradeId.LURKERRANGE: {
            "ability": AbilityId.LURKERDENRESEARCH_RESEARCHLURKERRANGE,
            "required_building": UnitTypeId.HIVE,
        },
    },
    UnitTypeId.ROACHWARREN: {
        UpgradeId.GLIALRECONSTITUTION: {
            "ability": AbilityId.RESEARCH_GLIALREGENERATION,
            "required_building": UnitTypeId.LAIR,
        },
        UpgradeId.TUNNELINGCLAWS: {"ability": AbilityId.RESEARCH_TUNNELINGCLAWS, "required_building": UnitTypeId.LAIR},
    },
    UnitTypeId.ROBOTICSBAY: {
        UpgradeId.EXTENDEDTHERMALLANCE: {"ability": AbilityId.RESEARCH_EXTENDEDTHERMALLANCE, "requires_power": True},
        UpgradeId.GRAVITICDRIVE: {"ability": AbilityId.RESEARCH_GRAVITICDRIVE, "requires_power": True},
        UpgradeId.OBSERVERGRAVITICBOOSTER: {"ability": AbilityId.RESEARCH_GRAVITICBOOSTER, "requires_power": True},
    },
    UnitTypeId.SPAWNINGPOOL: {
        UpgradeId.ZERGLINGATTACKSPEED: {
            "ability": AbilityId.RESEARCH_ZERGLINGADRENALGLANDS,
            "required_building": UnitTypeId.HIVE,
        },
        UpgradeId.ZERGLINGMOVEMENTSPEED: {"ability": AbilityId.RESEARCH_ZERGLINGMETABOLICBOOST},
    },
    UnitTypeId.SPIRE: {
        UpgradeId.ZERGFLYERARMORSLEVEL1: {"ability": AbilityId.RESEARCH_ZERGFLYERARMORLEVEL1},
        UpgradeId.ZERGFLYERARMORSLEVEL2: {
            "ability": AbilityId.RESEARCH_ZERGFLYERARMORLEVEL2,
            "required_building": UnitTypeId.LAIR,
            "required_upgrade": UpgradeId.ZERGFLYERARMORSLEVEL1,
        },
        UpgradeId.ZERGFLYERARMORSLEVEL3: {
            "ability": AbilityId.RESEARCH_ZERGFLYERARMORLEVEL3,
            "required_building": UnitTypeId.HIVE,
            "required_upgrade": UpgradeId.ZERGFLYERARMORSLEVEL2,
        },
        UpgradeId.ZERGFLYERWEAPONSLEVEL1: {"ability": AbilityId.RESEARCH_ZERGFLYERATTACKLEVEL1},
        UpgradeId.ZERGFLYERWEAPONSLEVEL2: {
            "ability": AbilityId.RESEARCH_ZERGFLYERATTACKLEVEL2,
            "required_building": UnitTypeId.LAIR,
            "required_upgrade": UpgradeId.ZERGFLYERWEAPONSLEVEL1,
        },
        UpgradeId.ZERGFLYERWEAPONSLEVEL3: {
            "ability": AbilityId.RESEARCH_ZERGFLYERATTACKLEVEL3,
            "required_building": UnitTypeId.HIVE,
            "required_upgrade": UpgradeId.ZERGFLYERWEAPONSLEVEL2,
        },
    },
    UnitTypeId.STARPORTTECHLAB: {
        UpgradeId.BANSHEECLOAK: {"ability": AbilityId.RESEARCH_BANSHEECLOAKINGFIELD},
        UpgradeId.BANSHEESPEED: {"ability": AbilityId.RESEARCH_BANSHEEHYPERFLIGHTROTORS},
        UpgradeId.INTERFERENCEMATRIX: {"ability": AbilityId.STARPORTTECHLABRESEARCH_RESEARCHRAVENINTERFERENCEMATRIX},
    },
    UnitTypeId.TEMPLARARCHIVE: {
        UpgradeId.PSISTORMTECH: {"ability": AbilityId.RESEARCH_PSISTORM, "requires_power": True}
    },
    UnitTypeId.TWILIGHTCOUNCIL: {
        UpgradeId.ADEPTPIERCINGATTACK: {"ability": AbilityId.RESEARCH_ADEPTRESONATINGGLAIVES, "requires_power": True},
        UpgradeId.BLINKTECH: {"ability": AbilityId.RESEARCH_BLINK, "requires_power": True},
        UpgradeId.CHARGE: {"ability": AbilityId.RESEARCH_CHARGE, "requires_power": True},
    },
    UnitTypeId.ULTRALISKCAVERN: {
        UpgradeId.ANABOLICSYNTHESIS: {"ability": AbilityId.RESEARCH_ANABOLICSYNTHESIS},
        UpgradeId.CHITINOUSPLATING: {"ability": AbilityId.RESEARCH_CHITINOUSPLATING},
    },
}
```

### File: `sc2/dicts/unit_tech_alias.py`

```python
# THIS FILE WAS AUTOMATICALLY GENERATED BY "generate_dicts_from_data_json.py" DO NOT CHANGE MANUALLY!
# ANY CHANGE WILL BE OVERWRITTEN

from sc2.ids.unit_typeid import UnitTypeId

# from sc2.ids.buff_id import BuffId
# from sc2.ids.effect_id import EffectId


UNIT_TECH_ALIAS: dict[UnitTypeId, set[UnitTypeId]] = {
    UnitTypeId.BARRACKSFLYING: {UnitTypeId.BARRACKS},
    UnitTypeId.BARRACKSREACTOR: {UnitTypeId.REACTOR},
    UnitTypeId.BARRACKSTECHLAB: {UnitTypeId.TECHLAB},
    UnitTypeId.COMMANDCENTERFLYING: {UnitTypeId.COMMANDCENTER},
    UnitTypeId.CREEPTUMORBURROWED: {UnitTypeId.CREEPTUMOR},
    UnitTypeId.CREEPTUMORQUEEN: {UnitTypeId.CREEPTUMOR},
    UnitTypeId.FACTORYFLYING: {UnitTypeId.FACTORY},
    UnitTypeId.FACTORYREACTOR: {UnitTypeId.REACTOR},
    UnitTypeId.FACTORYTECHLAB: {UnitTypeId.TECHLAB},
    UnitTypeId.GREATERSPIRE: {UnitTypeId.SPIRE},
    UnitTypeId.HIVE: {UnitTypeId.HATCHERY, UnitTypeId.LAIR},
    UnitTypeId.LAIR: {UnitTypeId.HATCHERY},
    UnitTypeId.LIBERATORAG: {UnitTypeId.LIBERATOR},
    UnitTypeId.ORBITALCOMMAND: {UnitTypeId.COMMANDCENTER},
    UnitTypeId.ORBITALCOMMANDFLYING: {UnitTypeId.COMMANDCENTER},
    UnitTypeId.OVERLORDTRANSPORT: {UnitTypeId.OVERLORD},
    UnitTypeId.OVERSEER: {UnitTypeId.OVERLORD},
    UnitTypeId.OVERSEERSIEGEMODE: {UnitTypeId.OVERLORD},
    UnitTypeId.PLANETARYFORTRESS: {UnitTypeId.COMMANDCENTER},
    UnitTypeId.PYLONOVERCHARGED: {UnitTypeId.PYLON},
    UnitTypeId.QUEENBURROWED: {UnitTypeId.QUEEN},
    UnitTypeId.SIEGETANKSIEGED: {UnitTypeId.SIEGETANK},
    UnitTypeId.STARPORTFLYING: {UnitTypeId.STARPORT},
    UnitTypeId.STARPORTREACTOR: {UnitTypeId.REACTOR},
    UnitTypeId.STARPORTTECHLAB: {UnitTypeId.TECHLAB},
    UnitTypeId.SUPPLYDEPOTLOWERED: {UnitTypeId.SUPPLYDEPOT},
    UnitTypeId.THORAP: {UnitTypeId.THOR},
    UnitTypeId.VIKINGASSAULT: {UnitTypeId.VIKING},
    UnitTypeId.VIKINGFIGHTER: {UnitTypeId.VIKING},
    UnitTypeId.WARPGATE: {UnitTypeId.GATEWAY},
    UnitTypeId.WARPPRISMPHASING: {UnitTypeId.WARPPRISM},
    UnitTypeId.WIDOWMINEBURROWED: {UnitTypeId.WIDOWMINE},
}
```

### File: `sc2/dicts/unit_train_build_abilities.py`

```python
# THIS FILE WAS AUTOMATICALLY GENERATED BY "generate_dicts_from_data_json.py" DO NOT CHANGE MANUALLY!
# ANY CHANGE WILL BE OVERWRITTEN

# from sc2.ids.buff_id import BuffId
# from sc2.ids.effect_id import EffectId
from typing import Union

from sc2.ids.ability_id import AbilityId
from sc2.ids.unit_typeid import UnitTypeId

TRAIN_INFO: dict[UnitTypeId, dict[UnitTypeId, dict[str, Union[AbilityId, bool, UnitTypeId]]]] = {
    UnitTypeId.BARRACKS: {
        UnitTypeId.GHOST: {
            "ability": AbilityId.BARRACKSTRAIN_GHOST,
            "requires_techlab": True,
            "required_building": UnitTypeId.GHOSTACADEMY,
        },
        UnitTypeId.MARAUDER: {"ability": AbilityId.BARRACKSTRAIN_MARAUDER, "requires_techlab": True},
        UnitTypeId.MARINE: {"ability": AbilityId.BARRACKSTRAIN_MARINE},
        UnitTypeId.REAPER: {"ability": AbilityId.BARRACKSTRAIN_REAPER},
    },
    UnitTypeId.COMMANDCENTER: {
        UnitTypeId.ORBITALCOMMAND: {
            "ability": AbilityId.UPGRADETOORBITAL_ORBITALCOMMAND,
            "required_building": UnitTypeId.BARRACKS,
        },
        UnitTypeId.PLANETARYFORTRESS: {
            "ability": AbilityId.UPGRADETOPLANETARYFORTRESS_PLANETARYFORTRESS,
            "required_building": UnitTypeId.ENGINEERINGBAY,
        },
        UnitTypeId.SCV: {"ability": AbilityId.COMMANDCENTERTRAIN_SCV},
    },
    UnitTypeId.CORRUPTOR: {
        UnitTypeId.BROODLORD: {
            "ability": AbilityId.MORPHTOBROODLORD_BROODLORD,
            "required_building": UnitTypeId.GREATERSPIRE,
        }
    },
    UnitTypeId.CREEPTUMOR: {
        UnitTypeId.CREEPTUMOR: {"ability": AbilityId.BUILD_CREEPTUMOR_TUMOR, "requires_placement_position": True}
    },
    UnitTypeId.CREEPTUMORBURROWED: {
        UnitTypeId.CREEPTUMOR: {"ability": AbilityId.BUILD_CREEPTUMOR, "requires_placement_position": True}
    },
    UnitTypeId.DRONE: {
        UnitTypeId.BANELINGNEST: {
            "ability": AbilityId.ZERGBUILD_BANELINGNEST,
            "required_building": UnitTypeId.SPAWNINGPOOL,
            "requires_placement_position": True,
        },
        UnitTypeId.EVOLUTIONCHAMBER: {
            "ability": AbilityId.ZERGBUILD_EVOLUTIONCHAMBER,
            "required_building": UnitTypeId.HATCHERY,
            "requires_placement_position": True,
        },
        UnitTypeId.EXTRACTOR: {"ability": AbilityId.ZERGBUILD_EXTRACTOR},
        UnitTypeId.HATCHERY: {"ability": AbilityId.ZERGBUILD_HATCHERY, "requires_placement_position": True},
        UnitTypeId.HYDRALISKDEN: {
            "ability": AbilityId.ZERGBUILD_HYDRALISKDEN,
            "required_building": UnitTypeId.LAIR,
            "requires_placement_position": True,
        },
        UnitTypeId.INFESTATIONPIT: {
            "ability": AbilityId.ZERGBUILD_INFESTATIONPIT,
            "required_building": UnitTypeId.LAIR,
            "requires_placement_position": True,
        },
        UnitTypeId.LURKERDENMP: {
            "ability": AbilityId.BUILD_LURKERDEN,
            "required_building": UnitTypeId.HYDRALISKDEN,
            "requires_placement_position": True,
        },
        UnitTypeId.NYDUSNETWORK: {
            "ability": AbilityId.ZERGBUILD_NYDUSNETWORK,
            "required_building": UnitTypeId.LAIR,
            "requires_placement_position": True,
        },
        UnitTypeId.ROACHWARREN: {
            "ability": AbilityId.ZERGBUILD_ROACHWARREN,
            "required_building": UnitTypeId.SPAWNINGPOOL,
            "requires_placement_position": True,
        },
        UnitTypeId.SPAWNINGPOOL: {
            "ability": AbilityId.ZERGBUILD_SPAWNINGPOOL,
            "required_building": UnitTypeId.HATCHERY,
            "requires_placement_position": True,
        },
        UnitTypeId.SPINECRAWLER: {
            "ability": AbilityId.ZERGBUILD_SPINECRAWLER,
            "required_building": UnitTypeId.SPAWNINGPOOL,
            "requires_placement_position": True,
        },
        UnitTypeId.SPIRE: {
            "ability": AbilityId.ZERGBUILD_SPIRE,
            "required_building": UnitTypeId.LAIR,
            "requires_placement_position": True,
        },
        UnitTypeId.SPORECRAWLER: {
            "ability": AbilityId.ZERGBUILD_SPORECRAWLER,
            "required_building": UnitTypeId.SPAWNINGPOOL,
            "requires_placement_position": True,
        },
        UnitTypeId.ULTRALISKCAVERN: {
            "ability": AbilityId.ZERGBUILD_ULTRALISKCAVERN,
            "required_building": UnitTypeId.HIVE,
            "requires_placement_position": True,
        },
    },
    UnitTypeId.FACTORY: {
        UnitTypeId.CYCLONE: {"ability": AbilityId.TRAIN_CYCLONE, "requires_techlab": True},
        UnitTypeId.HELLION: {"ability": AbilityId.FACTORYTRAIN_HELLION},
        UnitTypeId.HELLIONTANK: {"ability": AbilityId.TRAIN_HELLBAT, "required_building": UnitTypeId.ARMORY},
        UnitTypeId.SIEGETANK: {"ability": AbilityId.FACTORYTRAIN_SIEGETANK, "requires_techlab": True},
        UnitTypeId.THOR: {
            "ability": AbilityId.FACTORYTRAIN_THOR,
            "requires_techlab": True,
            "required_building": UnitTypeId.ARMORY,
        },
        UnitTypeId.WIDOWMINE: {"ability": AbilityId.FACTORYTRAIN_WIDOWMINE},
    },
    UnitTypeId.GATEWAY: {
        UnitTypeId.ADEPT: {
            "ability": AbilityId.TRAIN_ADEPT,
            "required_building": UnitTypeId.CYBERNETICSCORE,
            "requires_power": True,
        },
        UnitTypeId.DARKTEMPLAR: {
            "ability": AbilityId.GATEWAYTRAIN_DARKTEMPLAR,
            "required_building": UnitTypeId.DARKSHRINE,
            "requires_power": True,
        },
        UnitTypeId.HIGHTEMPLAR: {
            "ability": AbilityId.GATEWAYTRAIN_HIGHTEMPLAR,
            "required_building": UnitTypeId.TEMPLARARCHIVE,
            "requires_power": True,
        },
        UnitTypeId.SENTRY: {
            "ability": AbilityId.GATEWAYTRAIN_SENTRY,
            "required_building": UnitTypeId.CYBERNETICSCORE,
            "requires_power": True,
        },
        UnitTypeId.STALKER: {
            "ability": AbilityId.GATEWAYTRAIN_STALKER,
            "required_building": UnitTypeId.CYBERNETICSCORE,
            "requires_power": True,
        },
        UnitTypeId.ZEALOT: {"ability": AbilityId.GATEWAYTRAIN_ZEALOT, "requires_power": True},
    },
    UnitTypeId.HATCHERY: {
        UnitTypeId.LAIR: {"ability": AbilityId.UPGRADETOLAIR_LAIR, "required_building": UnitTypeId.SPAWNINGPOOL},
        UnitTypeId.QUEEN: {"ability": AbilityId.TRAINQUEEN_QUEEN, "required_building": UnitTypeId.SPAWNINGPOOL},
    },
    UnitTypeId.HIVE: {
        UnitTypeId.QUEEN: {"ability": AbilityId.TRAINQUEEN_QUEEN, "required_building": UnitTypeId.SPAWNINGPOOL}
    },
    UnitTypeId.HYDRALISK: {
        UnitTypeId.LURKERMP: {"ability": AbilityId.MORPH_LURKER, "required_building": UnitTypeId.LURKERDENMP}
    },
    UnitTypeId.LAIR: {
        UnitTypeId.HIVE: {"ability": AbilityId.UPGRADETOHIVE_HIVE, "required_building": UnitTypeId.INFESTATIONPIT},
        UnitTypeId.QUEEN: {"ability": AbilityId.TRAINQUEEN_QUEEN, "required_building": UnitTypeId.SPAWNINGPOOL},
    },
    UnitTypeId.LARVA: {
        UnitTypeId.CORRUPTOR: {"ability": AbilityId.LARVATRAIN_CORRUPTOR, "required_building": UnitTypeId.SPIRE},
        UnitTypeId.DRONE: {"ability": AbilityId.LARVATRAIN_DRONE},
        UnitTypeId.HYDRALISK: {"ability": AbilityId.LARVATRAIN_HYDRALISK, "required_building": UnitTypeId.HYDRALISKDEN},
        UnitTypeId.INFESTOR: {"ability": AbilityId.LARVATRAIN_INFESTOR, "required_building": UnitTypeId.INFESTATIONPIT},
        UnitTypeId.MUTALISK: {"ability": AbilityId.LARVATRAIN_MUTALISK, "required_building": UnitTypeId.SPIRE},
        UnitTypeId.OVERLORD: {"ability": AbilityId.LARVATRAIN_OVERLORD},
        UnitTypeId.ROACH: {"ability": AbilityId.LARVATRAIN_ROACH, "required_building": UnitTypeId.ROACHWARREN},
        UnitTypeId.SWARMHOSTMP: {"ability": AbilityId.TRAIN_SWARMHOST, "required_building": UnitTypeId.INFESTATIONPIT},
        UnitTypeId.ULTRALISK: {
            "ability": AbilityId.LARVATRAIN_ULTRALISK,
            "required_building": UnitTypeId.ULTRALISKCAVERN,
        },
        UnitTypeId.VIPER: {"ability": AbilityId.LARVATRAIN_VIPER, "required_building": UnitTypeId.HIVE},
        UnitTypeId.ZERGLING: {"ability": AbilityId.LARVATRAIN_ZERGLING, "required_building": UnitTypeId.SPAWNINGPOOL},
    },
    UnitTypeId.NEXUS: {
        UnitTypeId.MOTHERSHIP: {
            "ability": AbilityId.NEXUSTRAINMOTHERSHIP_MOTHERSHIP,
            "required_building": UnitTypeId.FLEETBEACON,
        },
        UnitTypeId.PROBE: {"ability": AbilityId.NEXUSTRAIN_PROBE},
    },
    UnitTypeId.NYDUSNETWORK: {
        UnitTypeId.NYDUSCANAL: {"ability": AbilityId.BUILD_NYDUSWORM, "requires_placement_position": True}
    },
    UnitTypeId.ORACLE: {
        UnitTypeId.ORACLESTASISTRAP: {"ability": AbilityId.BUILD_STASISTRAP, "requires_placement_position": True}
    },
    UnitTypeId.ORBITALCOMMAND: {UnitTypeId.SCV: {"ability": AbilityId.COMMANDCENTERTRAIN_SCV}},
    UnitTypeId.OVERLORD: {
        UnitTypeId.OVERLORDTRANSPORT: {
            "ability": AbilityId.MORPH_OVERLORDTRANSPORT,
            "required_building": UnitTypeId.LAIR,
        },
        UnitTypeId.OVERSEER: {"ability": AbilityId.MORPH_OVERSEER, "required_building": UnitTypeId.LAIR},
    },
    UnitTypeId.OVERLORDTRANSPORT: {
        UnitTypeId.OVERSEER: {"ability": AbilityId.MORPH_OVERSEER, "required_building": UnitTypeId.LAIR}
    },
    UnitTypeId.OVERSEER: {UnitTypeId.CHANGELING: {"ability": AbilityId.SPAWNCHANGELING_SPAWNCHANGELING}},
    UnitTypeId.OVERSEERSIEGEMODE: {UnitTypeId.CHANGELING: {"ability": AbilityId.SPAWNCHANGELING_SPAWNCHANGELING}},
    UnitTypeId.PLANETARYFORTRESS: {UnitTypeId.SCV: {"ability": AbilityId.COMMANDCENTERTRAIN_SCV}},
    UnitTypeId.PROBE: {
        UnitTypeId.ASSIMILATOR: {"ability": AbilityId.PROTOSSBUILD_ASSIMILATOR},
        UnitTypeId.CYBERNETICSCORE: {
            "ability": AbilityId.PROTOSSBUILD_CYBERNETICSCORE,
            "required_building": UnitTypeId.GATEWAY,
            "requires_placement_position": True,
        },
        UnitTypeId.DARKSHRINE: {
            "ability": AbilityId.PROTOSSBUILD_DARKSHRINE,
            "required_building": UnitTypeId.TWILIGHTCOUNCIL,
            "requires_placement_position": True,
        },
        UnitTypeId.FLEETBEACON: {
            "ability": AbilityId.PROTOSSBUILD_FLEETBEACON,
            "required_building": UnitTypeId.STARGATE,
            "requires_placement_position": True,
        },
        UnitTypeId.FORGE: {
            "ability": AbilityId.PROTOSSBUILD_FORGE,
            "required_building": UnitTypeId.PYLON,
            "requires_placement_position": True,
        },
        UnitTypeId.GATEWAY: {
            "ability": AbilityId.PROTOSSBUILD_GATEWAY,
            "required_building": UnitTypeId.PYLON,
            "requires_placement_position": True,
        },
        UnitTypeId.NEXUS: {"ability": AbilityId.PROTOSSBUILD_NEXUS, "requires_placement_position": True},
        UnitTypeId.PHOTONCANNON: {
            "ability": AbilityId.PROTOSSBUILD_PHOTONCANNON,
            "required_building": UnitTypeId.FORGE,
            "requires_placement_position": True,
        },
        UnitTypeId.PYLON: {"ability": AbilityId.PROTOSSBUILD_PYLON, "requires_placement_position": True},
        UnitTypeId.ROBOTICSBAY: {
            "ability": AbilityId.PROTOSSBUILD_ROBOTICSBAY,
            "required_building": UnitTypeId.ROBOTICSFACILITY,
            "requires_placement_position": True,
        },
        UnitTypeId.ROBOTICSFACILITY: {
            "ability": AbilityId.PROTOSSBUILD_ROBOTICSFACILITY,
            "required_building": UnitTypeId.CYBERNETICSCORE,
            "requires_placement_position": True,
        },
        UnitTypeId.SHIELDBATTERY: {
            "ability": AbilityId.BUILD_SHIELDBATTERY,
            "required_building": UnitTypeId.CYBERNETICSCORE,
            "requires_placement_position": True,
        },
        UnitTypeId.STARGATE: {
            "ability": AbilityId.PROTOSSBUILD_STARGATE,
            "required_building": UnitTypeId.CYBERNETICSCORE,
            "requires_placement_position": True,
        },
        UnitTypeId.TEMPLARARCHIVE: {
            "ability": AbilityId.PROTOSSBUILD_TEMPLARARCHIVE,
            "required_building": UnitTypeId.TWILIGHTCOUNCIL,
            "requires_placement_position": True,
        },
        UnitTypeId.TWILIGHTCOUNCIL: {
            "ability": AbilityId.PROTOSSBUILD_TWILIGHTCOUNCIL,
            "required_building": UnitTypeId.CYBERNETICSCORE,
            "requires_placement_position": True,
        },
    },
    UnitTypeId.QUEEN: {
        UnitTypeId.CREEPTUMOR: {"ability": AbilityId.BUILD_CREEPTUMOR, "requires_placement_position": True},
        UnitTypeId.CREEPTUMORQUEEN: {"ability": AbilityId.BUILD_CREEPTUMOR_QUEEN, "requires_placement_position": True},
    },
    UnitTypeId.RAVEN: {UnitTypeId.AUTOTURRET: {"ability": AbilityId.BUILDAUTOTURRET_AUTOTURRET}},
    UnitTypeId.ROACH: {
        UnitTypeId.RAVAGER: {"ability": AbilityId.MORPHTORAVAGER_RAVAGER, "required_building": UnitTypeId.HATCHERY}
    },
    UnitTypeId.ROBOTICSFACILITY: {
        UnitTypeId.COLOSSUS: {
            "ability": AbilityId.ROBOTICSFACILITYTRAIN_COLOSSUS,
            "required_building": UnitTypeId.ROBOTICSBAY,
            "requires_power": True,
        },
        UnitTypeId.DISRUPTOR: {
            "ability": AbilityId.TRAIN_DISRUPTOR,
            "required_building": UnitTypeId.ROBOTICSBAY,
            "requires_power": True,
        },
        UnitTypeId.IMMORTAL: {"ability": AbilityId.ROBOTICSFACILITYTRAIN_IMMORTAL, "requires_power": True},
        UnitTypeId.OBSERVER: {"ability": AbilityId.ROBOTICSFACILITYTRAIN_OBSERVER, "requires_power": True},
        UnitTypeId.WARPPRISM: {"ability": AbilityId.ROBOTICSFACILITYTRAIN_WARPPRISM, "requires_power": True},
    },
    UnitTypeId.SCV: {
        UnitTypeId.ARMORY: {
            "ability": AbilityId.TERRANBUILD_ARMORY,
            "required_building": UnitTypeId.FACTORY,
            "requires_placement_position": True,
        },
        UnitTypeId.BARRACKS: {
            "ability": AbilityId.TERRANBUILD_BARRACKS,
            "required_building": UnitTypeId.SUPPLYDEPOT,
            "requires_placement_position": True,
        },
        UnitTypeId.BUNKER: {
            "ability": AbilityId.TERRANBUILD_BUNKER,
            "required_building": UnitTypeId.BARRACKS,
            "requires_placement_position": True,
        },
        UnitTypeId.COMMANDCENTER: {"ability": AbilityId.TERRANBUILD_COMMANDCENTER, "requires_placement_position": True},
        UnitTypeId.ENGINEERINGBAY: {
            "ability": AbilityId.TERRANBUILD_ENGINEERINGBAY,
            "required_building": UnitTypeId.COMMANDCENTER,
            "requires_placement_position": True,
        },
        UnitTypeId.FACTORY: {
            "ability": AbilityId.TERRANBUILD_FACTORY,
            "required_building": UnitTypeId.BARRACKS,
            "requires_placement_position": True,
        },
        UnitTypeId.FUSIONCORE: {
            "ability": AbilityId.TERRANBUILD_FUSIONCORE,
            "required_building": UnitTypeId.STARPORT,
            "requires_placement_position": True,
        },
        UnitTypeId.GHOSTACADEMY: {
            "ability": AbilityId.TERRANBUILD_GHOSTACADEMY,
            "required_building": UnitTypeId.BARRACKS,
            "requires_placement_position": True,
        },
        UnitTypeId.MISSILETURRET: {
            "ability": AbilityId.TERRANBUILD_MISSILETURRET,
            "required_building": UnitTypeId.ENGINEERINGBAY,
            "requires_placement_position": True,
        },
        UnitTypeId.REFINERY: {"ability": AbilityId.TERRANBUILD_REFINERY},
        UnitTypeId.SENSORTOWER: {
            "ability": AbilityId.TERRANBUILD_SENSORTOWER,
            "required_building": UnitTypeId.ENGINEERINGBAY,
            "requires_placement_position": True,
        },
        UnitTypeId.STARPORT: {
            "ability": AbilityId.TERRANBUILD_STARPORT,
            "required_building": UnitTypeId.FACTORY,
            "requires_placement_position": True,
        },
        UnitTypeId.SUPPLYDEPOT: {"ability": AbilityId.TERRANBUILD_SUPPLYDEPOT, "requires_placement_position": True},
    },
    UnitTypeId.SPIRE: {
        UnitTypeId.GREATERSPIRE: {
            "ability": AbilityId.UPGRADETOGREATERSPIRE_GREATERSPIRE,
            "required_building": UnitTypeId.HIVE,
        }
    },
    UnitTypeId.STARGATE: {
        UnitTypeId.CARRIER: {
            "ability": AbilityId.STARGATETRAIN_CARRIER,
            "required_building": UnitTypeId.FLEETBEACON,
            "requires_power": True,
        },
        UnitTypeId.ORACLE: {"ability": AbilityId.STARGATETRAIN_ORACLE, "requires_power": True},
        UnitTypeId.PHOENIX: {"ability": AbilityId.STARGATETRAIN_PHOENIX, "requires_power": True},
        UnitTypeId.TEMPEST: {
            "ability": AbilityId.STARGATETRAIN_TEMPEST,
            "required_building": UnitTypeId.FLEETBEACON,
            "requires_power": True,
        },
        UnitTypeId.VOIDRAY: {"ability": AbilityId.STARGATETRAIN_VOIDRAY, "requires_power": True},
    },
    UnitTypeId.STARPORT: {
        UnitTypeId.BANSHEE: {"ability": AbilityId.STARPORTTRAIN_BANSHEE, "requires_techlab": True},
        UnitTypeId.BATTLECRUISER: {
            "ability": AbilityId.STARPORTTRAIN_BATTLECRUISER,
            "requires_techlab": True,
            "required_building": UnitTypeId.FUSIONCORE,
        },
        UnitTypeId.LIBERATOR: {"ability": AbilityId.STARPORTTRAIN_LIBERATOR},
        UnitTypeId.MEDIVAC: {"ability": AbilityId.STARPORTTRAIN_MEDIVAC},
        UnitTypeId.RAVEN: {"ability": AbilityId.STARPORTTRAIN_RAVEN, "requires_techlab": True},
        UnitTypeId.VIKINGFIGHTER: {"ability": AbilityId.STARPORTTRAIN_VIKINGFIGHTER},
    },
    UnitTypeId.SWARMHOSTBURROWEDMP: {UnitTypeId.LOCUSTMPFLYING: {"ability": AbilityId.EFFECT_SPAWNLOCUSTS}},
    UnitTypeId.SWARMHOSTMP: {UnitTypeId.LOCUSTMPFLYING: {"ability": AbilityId.EFFECT_SPAWNLOCUSTS}},
    UnitTypeId.WARPGATE: {
        UnitTypeId.ADEPT: {
            "ability": AbilityId.TRAINWARP_ADEPT,
            "required_building": UnitTypeId.CYBERNETICSCORE,
            "requires_placement_position": True,
            "requires_power": True,
        },
        UnitTypeId.DARKTEMPLAR: {
            "ability": AbilityId.WARPGATETRAIN_DARKTEMPLAR,
            "required_building": UnitTypeId.DARKSHRINE,
            "requires_placement_position": True,
            "requires_power": True,
        },
        UnitTypeId.HIGHTEMPLAR: {
            "ability": AbilityId.WARPGATETRAIN_HIGHTEMPLAR,
            "required_building": UnitTypeId.TEMPLARARCHIVE,
            "requires_placement_position": True,
            "requires_power": True,
        },
        UnitTypeId.SENTRY: {
            "ability": AbilityId.WARPGATETRAIN_SENTRY,
            "required_building": UnitTypeId.CYBERNETICSCORE,
            "requires_placement_position": True,
            "requires_power": True,
        },
        UnitTypeId.STALKER: {
            "ability": AbilityId.WARPGATETRAIN_STALKER,
            "required_building": UnitTypeId.CYBERNETICSCORE,
            "requires_placement_position": True,
            "requires_power": True,
        },
        UnitTypeId.ZEALOT: {
            "ability": AbilityId.WARPGATETRAIN_ZEALOT,
            "requires_placement_position": True,
            "requires_power": True,
        },
    },
    UnitTypeId.ZERGLING: {
        UnitTypeId.BANELING: {
            "ability": AbilityId.MORPHTOBANELING_BANELING,
            "required_building": UnitTypeId.BANELINGNEST,
        }
    },
}
```

### File: `sc2/dicts/unit_trained_from.py`

```python
# THIS FILE WAS AUTOMATICALLY GENERATED BY "generate_dicts_from_data_json.py" DO NOT CHANGE MANUALLY!
# ANY CHANGE WILL BE OVERWRITTEN

from sc2.ids.unit_typeid import UnitTypeId

# from sc2.ids.buff_id import BuffId
# from sc2.ids.effect_id import EffectId


UNIT_TRAINED_FROM: dict[UnitTypeId, set[UnitTypeId]] = {
    UnitTypeId.ADEPT: {UnitTypeId.GATEWAY, UnitTypeId.WARPGATE},
    UnitTypeId.ARMORY: {UnitTypeId.SCV},
    UnitTypeId.ASSIMILATOR: {UnitTypeId.PROBE},
    UnitTypeId.AUTOTURRET: {UnitTypeId.RAVEN},
    UnitTypeId.BANELING: {UnitTypeId.ZERGLING},
    UnitTypeId.BANELINGNEST: {UnitTypeId.DRONE},
    UnitTypeId.BANSHEE: {UnitTypeId.STARPORT},
    UnitTypeId.BARRACKS: {UnitTypeId.SCV},
    UnitTypeId.BATTLECRUISER: {UnitTypeId.STARPORT},
    UnitTypeId.BROODLORD: {UnitTypeId.CORRUPTOR},
    UnitTypeId.BUNKER: {UnitTypeId.SCV},
    UnitTypeId.CARRIER: {UnitTypeId.STARGATE},
    UnitTypeId.CHANGELING: {UnitTypeId.OVERSEER, UnitTypeId.OVERSEERSIEGEMODE},
    UnitTypeId.COLOSSUS: {UnitTypeId.ROBOTICSFACILITY},
    UnitTypeId.COMMANDCENTER: {UnitTypeId.SCV},
    UnitTypeId.CORRUPTOR: {UnitTypeId.LARVA},
    UnitTypeId.CREEPTUMOR: {UnitTypeId.CREEPTUMORBURROWED, UnitTypeId.QUEEN},
    UnitTypeId.CREEPTUMORQUEEN: {UnitTypeId.QUEEN},
    UnitTypeId.CYBERNETICSCORE: {UnitTypeId.PROBE},
    UnitTypeId.CYCLONE: {UnitTypeId.FACTORY},
    UnitTypeId.DARKSHRINE: {UnitTypeId.PROBE},
    UnitTypeId.DARKTEMPLAR: {UnitTypeId.GATEWAY, UnitTypeId.WARPGATE},
    UnitTypeId.DISRUPTOR: {UnitTypeId.ROBOTICSFACILITY},
    UnitTypeId.DRONE: {UnitTypeId.LARVA},
    UnitTypeId.ENGINEERINGBAY: {UnitTypeId.SCV},
    UnitTypeId.EVOLUTIONCHAMBER: {UnitTypeId.DRONE},
    UnitTypeId.EXTRACTOR: {UnitTypeId.DRONE},
    UnitTypeId.FACTORY: {UnitTypeId.SCV},
    UnitTypeId.FLEETBEACON: {UnitTypeId.PROBE},
    UnitTypeId.FORGE: {UnitTypeId.PROBE},
    UnitTypeId.FUSIONCORE: {UnitTypeId.SCV},
    UnitTypeId.GATEWAY: {UnitTypeId.PROBE},
    UnitTypeId.GHOST: {UnitTypeId.BARRACKS},
    UnitTypeId.GHOSTACADEMY: {UnitTypeId.SCV},
    UnitTypeId.GREATERSPIRE: {UnitTypeId.SPIRE},
    UnitTypeId.HATCHERY: {UnitTypeId.DRONE},
    UnitTypeId.HELLION: {UnitTypeId.FACTORY},
    UnitTypeId.HELLIONTANK: {UnitTypeId.FACTORY},
    UnitTypeId.HIGHTEMPLAR: {UnitTypeId.GATEWAY, UnitTypeId.WARPGATE},
    UnitTypeId.HIVE: {UnitTypeId.LAIR},
    UnitTypeId.HYDRALISK: {UnitTypeId.LARVA},
    UnitTypeId.HYDRALISKDEN: {UnitTypeId.DRONE},
    UnitTypeId.IMMORTAL: {UnitTypeId.ROBOTICSFACILITY},
    UnitTypeId.INFESTATIONPIT: {UnitTypeId.DRONE},
    UnitTypeId.INFESTOR: {UnitTypeId.LARVA},
    UnitTypeId.LAIR: {UnitTypeId.HATCHERY},
    UnitTypeId.LIBERATOR: {UnitTypeId.STARPORT},
    UnitTypeId.LOCUSTMPFLYING: {UnitTypeId.SWARMHOSTBURROWEDMP, UnitTypeId.SWARMHOSTMP},
    UnitTypeId.LURKERDENMP: {UnitTypeId.DRONE},
    UnitTypeId.LURKERMP: {UnitTypeId.HYDRALISK},
    UnitTypeId.MARAUDER: {UnitTypeId.BARRACKS},
    UnitTypeId.MARINE: {UnitTypeId.BARRACKS},
    UnitTypeId.MEDIVAC: {UnitTypeId.STARPORT},
    UnitTypeId.MISSILETURRET: {UnitTypeId.SCV},
    UnitTypeId.MOTHERSHIP: {UnitTypeId.NEXUS},
    UnitTypeId.MUTALISK: {UnitTypeId.LARVA},
    UnitTypeId.NEXUS: {UnitTypeId.PROBE},
    UnitTypeId.NYDUSCANAL: {UnitTypeId.NYDUSNETWORK},
    UnitTypeId.NYDUSNETWORK: {UnitTypeId.DRONE},
    UnitTypeId.OBSERVER: {UnitTypeId.ROBOTICSFACILITY},
    UnitTypeId.ORACLE: {UnitTypeId.STARGATE},
    UnitTypeId.ORACLESTASISTRAP: {UnitTypeId.ORACLE},
    UnitTypeId.ORBITALCOMMAND: {UnitTypeId.COMMANDCENTER},
    UnitTypeId.OVERLORD: {UnitTypeId.LARVA},
    UnitTypeId.OVERLORDTRANSPORT: {UnitTypeId.OVERLORD},
    UnitTypeId.OVERSEER: {UnitTypeId.OVERLORD, UnitTypeId.OVERLORDTRANSPORT},
    UnitTypeId.PHOENIX: {UnitTypeId.STARGATE},
    UnitTypeId.PHOTONCANNON: {UnitTypeId.PROBE},
    UnitTypeId.PLANETARYFORTRESS: {UnitTypeId.COMMANDCENTER},
    UnitTypeId.PROBE: {UnitTypeId.NEXUS},
    UnitTypeId.PYLON: {UnitTypeId.PROBE},
    UnitTypeId.QUEEN: {UnitTypeId.HATCHERY, UnitTypeId.HIVE, UnitTypeId.LAIR},
    UnitTypeId.RAVAGER: {UnitTypeId.ROACH},
    UnitTypeId.RAVEN: {UnitTypeId.STARPORT},
    UnitTypeId.REAPER: {UnitTypeId.BARRACKS},
    UnitTypeId.REFINERY: {UnitTypeId.SCV},
    UnitTypeId.ROACH: {UnitTypeId.LARVA},
    UnitTypeId.ROACHWARREN: {UnitTypeId.DRONE},
    UnitTypeId.ROBOTICSBAY: {UnitTypeId.PROBE},
    UnitTypeId.ROBOTICSFACILITY: {UnitTypeId.PROBE},
    UnitTypeId.SCV: {UnitTypeId.COMMANDCENTER, UnitTypeId.ORBITALCOMMAND, UnitTypeId.PLANETARYFORTRESS},
    UnitTypeId.SENSORTOWER: {UnitTypeId.SCV},
    UnitTypeId.SENTRY: {UnitTypeId.GATEWAY, UnitTypeId.WARPGATE},
    UnitTypeId.SHIELDBATTERY: {UnitTypeId.PROBE},
    UnitTypeId.SIEGETANK: {UnitTypeId.FACTORY},
    UnitTypeId.SPAWNINGPOOL: {UnitTypeId.DRONE},
    UnitTypeId.SPINECRAWLER: {UnitTypeId.DRONE},
    UnitTypeId.SPIRE: {UnitTypeId.DRONE},
    UnitTypeId.SPORECRAWLER: {UnitTypeId.DRONE},
    UnitTypeId.STALKER: {UnitTypeId.GATEWAY, UnitTypeId.WARPGATE},
    UnitTypeId.STARGATE: {UnitTypeId.PROBE},
    UnitTypeId.STARPORT: {UnitTypeId.SCV},
    UnitTypeId.SUPPLYDEPOT: {UnitTypeId.SCV},
    UnitTypeId.SWARMHOSTMP: {UnitTypeId.LARVA},
    UnitTypeId.TEMPEST: {UnitTypeId.STARGATE},
    UnitTypeId.TEMPLARARCHIVE: {UnitTypeId.PROBE},
    UnitTypeId.THOR: {UnitTypeId.FACTORY},
    UnitTypeId.TWILIGHTCOUNCIL: {UnitTypeId.PROBE},
    UnitTypeId.ULTRALISK: {UnitTypeId.LARVA},
    UnitTypeId.ULTRALISKCAVERN: {UnitTypeId.DRONE},
    UnitTypeId.VIKINGFIGHTER: {UnitTypeId.STARPORT},
    UnitTypeId.VIPER: {UnitTypeId.LARVA},
    UnitTypeId.VOIDRAY: {UnitTypeId.STARGATE},
    UnitTypeId.WARPPRISM: {UnitTypeId.ROBOTICSFACILITY},
    UnitTypeId.WIDOWMINE: {UnitTypeId.FACTORY},
    UnitTypeId.ZEALOT: {UnitTypeId.GATEWAY, UnitTypeId.WARPGATE},
    UnitTypeId.ZERGLING: {UnitTypeId.LARVA},
}
```

### File: `sc2/dicts/unit_unit_alias.py`

```python
# THIS FILE WAS AUTOMATICALLY GENERATED BY "generate_dicts_from_data_json.py" DO NOT CHANGE MANUALLY!
# ANY CHANGE WILL BE OVERWRITTEN

from sc2.ids.unit_typeid import UnitTypeId

# from sc2.ids.buff_id import BuffId
# from sc2.ids.effect_id import EffectId


UNIT_UNIT_ALIAS: dict[UnitTypeId, UnitTypeId] = {
    UnitTypeId.ADEPTPHASESHIFT: UnitTypeId.ADEPT,
    UnitTypeId.BANELINGBURROWED: UnitTypeId.BANELING,
    UnitTypeId.BARRACKSFLYING: UnitTypeId.BARRACKS,
    UnitTypeId.CHANGELINGMARINE: UnitTypeId.CHANGELING,
    UnitTypeId.CHANGELINGMARINESHIELD: UnitTypeId.CHANGELING,
    UnitTypeId.CHANGELINGZEALOT: UnitTypeId.CHANGELING,
    UnitTypeId.CHANGELINGZERGLING: UnitTypeId.CHANGELING,
    UnitTypeId.CHANGELINGZERGLINGWINGS: UnitTypeId.CHANGELING,
    UnitTypeId.COMMANDCENTERFLYING: UnitTypeId.COMMANDCENTER,
    UnitTypeId.CREEPTUMORBURROWED: UnitTypeId.CREEPTUMOR,
    UnitTypeId.CREEPTUMORQUEEN: UnitTypeId.CREEPTUMOR,
    UnitTypeId.DRONEBURROWED: UnitTypeId.DRONE,
    UnitTypeId.FACTORYFLYING: UnitTypeId.FACTORY,
    UnitTypeId.GHOSTNOVA: UnitTypeId.GHOST,
    UnitTypeId.HERCPLACEMENT: UnitTypeId.HERC,
    UnitTypeId.HYDRALISKBURROWED: UnitTypeId.HYDRALISK,
    UnitTypeId.INFESTORBURROWED: UnitTypeId.INFESTOR,
    UnitTypeId.INFESTORTERRANBURROWED: UnitTypeId.INFESTORTERRAN,
    UnitTypeId.LIBERATORAG: UnitTypeId.LIBERATOR,
    UnitTypeId.LOCUSTMPFLYING: UnitTypeId.LOCUSTMP,
    UnitTypeId.LURKERMPBURROWED: UnitTypeId.LURKERMP,
    UnitTypeId.OBSERVERSIEGEMODE: UnitTypeId.OBSERVER,
    UnitTypeId.ORBITALCOMMANDFLYING: UnitTypeId.ORBITALCOMMAND,
    UnitTypeId.OVERSEERSIEGEMODE: UnitTypeId.OVERSEER,
    UnitTypeId.PYLONOVERCHARGED: UnitTypeId.PYLON,
    UnitTypeId.QUEENBURROWED: UnitTypeId.QUEEN,
    UnitTypeId.RAVAGERBURROWED: UnitTypeId.RAVAGER,
    UnitTypeId.ROACHBURROWED: UnitTypeId.ROACH,
    UnitTypeId.SIEGETANKSIEGED: UnitTypeId.SIEGETANK,
    UnitTypeId.SPINECRAWLERUPROOTED: UnitTypeId.SPINECRAWLER,
    UnitTypeId.SPORECRAWLERUPROOTED: UnitTypeId.SPORECRAWLER,
    UnitTypeId.STARPORTFLYING: UnitTypeId.STARPORT,
    UnitTypeId.SUPPLYDEPOTLOWERED: UnitTypeId.SUPPLYDEPOT,
    UnitTypeId.SWARMHOSTBURROWEDMP: UnitTypeId.SWARMHOSTMP,
    UnitTypeId.THORAP: UnitTypeId.THOR,
    UnitTypeId.ULTRALISKBURROWED: UnitTypeId.ULTRALISK,
    UnitTypeId.VIKINGASSAULT: UnitTypeId.VIKINGFIGHTER,
    UnitTypeId.WARPPRISMPHASING: UnitTypeId.WARPPRISM,
    UnitTypeId.WIDOWMINEBURROWED: UnitTypeId.WIDOWMINE,
    UnitTypeId.ZERGLINGBURROWED: UnitTypeId.ZERGLING,
}
```

### File: `sc2/dicts/upgrade_researched_from.py`

```python
# THIS FILE WAS AUTOMATICALLY GENERATED BY "generate_dicts_from_data_json.py" DO NOT CHANGE MANUALLY!
# ANY CHANGE WILL BE OVERWRITTEN

from sc2.ids.unit_typeid import UnitTypeId
from sc2.ids.upgrade_id import UpgradeId

# from sc2.ids.buff_id import BuffId
# from sc2.ids.effect_id import EffectId


UPGRADE_RESEARCHED_FROM: dict[UpgradeId, UnitTypeId] = {
    UpgradeId.ADEPTPIERCINGATTACK: UnitTypeId.TWILIGHTCOUNCIL,
    UpgradeId.ANABOLICSYNTHESIS: UnitTypeId.ULTRALISKCAVERN,
    UpgradeId.BANSHEECLOAK: UnitTypeId.STARPORTTECHLAB,
    UpgradeId.BANSHEESPEED: UnitTypeId.STARPORTTECHLAB,
    UpgradeId.BATTLECRUISERENABLESPECIALIZATIONS: UnitTypeId.FUSIONCORE,
    UpgradeId.BLINKTECH: UnitTypeId.TWILIGHTCOUNCIL,
    UpgradeId.BURROW: UnitTypeId.HATCHERY,
    UpgradeId.CENTRIFICALHOOKS: UnitTypeId.BANELINGNEST,
    UpgradeId.CHARGE: UnitTypeId.TWILIGHTCOUNCIL,
    UpgradeId.CHITINOUSPLATING: UnitTypeId.ULTRALISKCAVERN,
    UpgradeId.CYCLONELOCKONDAMAGEUPGRADE: UnitTypeId.FACTORYTECHLAB,
    UpgradeId.DARKTEMPLARBLINKUPGRADE: UnitTypeId.DARKSHRINE,
    UpgradeId.DIGGINGCLAWS: UnitTypeId.LURKERDENMP,
    UpgradeId.DRILLCLAWS: UnitTypeId.FACTORYTECHLAB,
    UpgradeId.EVOLVEGROOVEDSPINES: UnitTypeId.HYDRALISKDEN,
    UpgradeId.EVOLVEMUSCULARAUGMENTS: UnitTypeId.HYDRALISKDEN,
    UpgradeId.EXTENDEDTHERMALLANCE: UnitTypeId.ROBOTICSBAY,
    UpgradeId.FRENZY: UnitTypeId.HYDRALISKDEN,
    UpgradeId.GLIALRECONSTITUTION: UnitTypeId.ROACHWARREN,
    UpgradeId.GRAVITICDRIVE: UnitTypeId.ROBOTICSBAY,
    UpgradeId.HIGHCAPACITYBARRELS: UnitTypeId.FACTORYTECHLAB,
    UpgradeId.HISECAUTOTRACKING: UnitTypeId.ENGINEERINGBAY,
    UpgradeId.INTERFERENCEMATRIX: UnitTypeId.STARPORTTECHLAB,
    UpgradeId.LIBERATORAGRANGEUPGRADE: UnitTypeId.FUSIONCORE,
    UpgradeId.LURKERRANGE: UnitTypeId.LURKERDENMP,
    UpgradeId.MEDIVACCADUCEUSREACTOR: UnitTypeId.FUSIONCORE,
    UpgradeId.NEURALPARASITE: UnitTypeId.INFESTATIONPIT,
    UpgradeId.OBSERVERGRAVITICBOOSTER: UnitTypeId.ROBOTICSBAY,
    UpgradeId.OVERLORDSPEED: UnitTypeId.HATCHERY,
    UpgradeId.PERSONALCLOAKING: UnitTypeId.GHOSTACADEMY,
    UpgradeId.PHOENIXRANGEUPGRADE: UnitTypeId.FLEETBEACON,
    UpgradeId.PROTOSSAIRARMORSLEVEL1: UnitTypeId.CYBERNETICSCORE,
    UpgradeId.PROTOSSAIRARMORSLEVEL2: UnitTypeId.CYBERNETICSCORE,
    UpgradeId.PROTOSSAIRARMORSLEVEL3: UnitTypeId.CYBERNETICSCORE,
    UpgradeId.PROTOSSAIRWEAPONSLEVEL1: UnitTypeId.CYBERNETICSCORE,
    UpgradeId.PROTOSSAIRWEAPONSLEVEL2: UnitTypeId.CYBERNETICSCORE,
    UpgradeId.PROTOSSAIRWEAPONSLEVEL3: UnitTypeId.CYBERNETICSCORE,
    UpgradeId.PROTOSSGROUNDARMORSLEVEL1: UnitTypeId.FORGE,
    UpgradeId.PROTOSSGROUNDARMORSLEVEL2: UnitTypeId.FORGE,
    UpgradeId.PROTOSSGROUNDARMORSLEVEL3: UnitTypeId.FORGE,
    UpgradeId.PROTOSSGROUNDWEAPONSLEVEL1: UnitTypeId.FORGE,
    UpgradeId.PROTOSSGROUNDWEAPONSLEVEL2: UnitTypeId.FORGE,
    UpgradeId.PROTOSSGROUNDWEAPONSLEVEL3: UnitTypeId.FORGE,
    UpgradeId.PROTOSSSHIELDSLEVEL1: UnitTypeId.FORGE,
    UpgradeId.PROTOSSSHIELDSLEVEL2: UnitTypeId.FORGE,
    UpgradeId.PROTOSSSHIELDSLEVEL3: UnitTypeId.FORGE,
    UpgradeId.PSISTORMTECH: UnitTypeId.TEMPLARARCHIVE,
    UpgradeId.PUNISHERGRENADES: UnitTypeId.BARRACKSTECHLAB,
    UpgradeId.SHIELDWALL: UnitTypeId.BARRACKSTECHLAB,
    UpgradeId.SMARTSERVOS: UnitTypeId.FACTORYTECHLAB,
    UpgradeId.STIMPACK: UnitTypeId.BARRACKSTECHLAB,
    UpgradeId.TEMPESTGROUNDATTACKUPGRADE: UnitTypeId.FLEETBEACON,
    UpgradeId.TERRANBUILDINGARMOR: UnitTypeId.ENGINEERINGBAY,
    UpgradeId.TERRANINFANTRYARMORSLEVEL1: UnitTypeId.ENGINEERINGBAY,
    UpgradeId.TERRANINFANTRYARMORSLEVEL2: UnitTypeId.ENGINEERINGBAY,
    UpgradeId.TERRANINFANTRYARMORSLEVEL3: UnitTypeId.ENGINEERINGBAY,
    UpgradeId.TERRANINFANTRYWEAPONSLEVEL1: UnitTypeId.ENGINEERINGBAY,
    UpgradeId.TERRANINFANTRYWEAPONSLEVEL2: UnitTypeId.ENGINEERINGBAY,
    UpgradeId.TERRANINFANTRYWEAPONSLEVEL3: UnitTypeId.ENGINEERINGBAY,
    UpgradeId.TERRANSHIPWEAPONSLEVEL1: UnitTypeId.ARMORY,
    UpgradeId.TERRANSHIPWEAPONSLEVEL2: UnitTypeId.ARMORY,
    UpgradeId.TERRANSHIPWEAPONSLEVEL3: UnitTypeId.ARMORY,
    UpgradeId.TERRANVEHICLEANDSHIPARMORSLEVEL1: UnitTypeId.ARMORY,
    UpgradeId.TERRANVEHICLEANDSHIPARMORSLEVEL2: UnitTypeId.ARMORY,
    UpgradeId.TERRANVEHICLEANDSHIPARMORSLEVEL3: UnitTypeId.ARMORY,
    UpgradeId.TERRANVEHICLEWEAPONSLEVEL1: UnitTypeId.ARMORY,
    UpgradeId.TERRANVEHICLEWEAPONSLEVEL2: UnitTypeId.ARMORY,
    UpgradeId.TERRANVEHICLEWEAPONSLEVEL3: UnitTypeId.ARMORY,
    UpgradeId.TUNNELINGCLAWS: UnitTypeId.ROACHWARREN,
    UpgradeId.VOIDRAYSPEEDUPGRADE: UnitTypeId.FLEETBEACON,
    UpgradeId.WARPGATERESEARCH: UnitTypeId.CYBERNETICSCORE,
    UpgradeId.ZERGFLYERARMORSLEVEL1: UnitTypeId.SPIRE,
    UpgradeId.ZERGFLYERARMORSLEVEL2: UnitTypeId.SPIRE,
    UpgradeId.ZERGFLYERARMORSLEVEL3: UnitTypeId.SPIRE,
    UpgradeId.ZERGFLYERWEAPONSLEVEL1: UnitTypeId.SPIRE,
    UpgradeId.ZERGFLYERWEAPONSLEVEL2: UnitTypeId.SPIRE,
    UpgradeId.ZERGFLYERWEAPONSLEVEL3: UnitTypeId.SPIRE,
    UpgradeId.ZERGGROUNDARMORSLEVEL1: UnitTypeId.EVOLUTIONCHAMBER,
    UpgradeId.ZERGGROUNDARMORSLEVEL2: UnitTypeId.EVOLUTIONCHAMBER,
    UpgradeId.ZERGGROUNDARMORSLEVEL3: UnitTypeId.EVOLUTIONCHAMBER,
    UpgradeId.ZERGLINGATTACKSPEED: UnitTypeId.SPAWNINGPOOL,
    UpgradeId.ZERGLINGMOVEMENTSPEED: UnitTypeId.SPAWNINGPOOL,
    UpgradeId.ZERGMELEEWEAPONSLEVEL1: UnitTypeId.EVOLUTIONCHAMBER,
    UpgradeId.ZERGMELEEWEAPONSLEVEL2: UnitTypeId.EVOLUTIONCHAMBER,
    UpgradeId.ZERGMELEEWEAPONSLEVEL3: UnitTypeId.EVOLUTIONCHAMBER,
    UpgradeId.ZERGMISSILEWEAPONSLEVEL1: UnitTypeId.EVOLUTIONCHAMBER,
    UpgradeId.ZERGMISSILEWEAPONSLEVEL2: UnitTypeId.EVOLUTIONCHAMBER,
    UpgradeId.ZERGMISSILEWEAPONSLEVEL3: UnitTypeId.EVOLUTIONCHAMBER,
}
```

### File: `sc2/ids/__init__.py`

```python
# pyre-ignore-all-errors[14]
from __future__ import annotations

# DO NOT EDIT!
# This file was automatically generated by "generate_ids.py"

__all__ = ["unit_typeid", "ability_id", "upgrade_id", "buff_id", "effect_id"]
```

### File: `sc2/ids/ability_id.py`

```python
# pyre-ignore-all-errors[14]
from __future__ import annotations

# DO NOT EDIT!
# This file was automatically generated by "generate_ids.py"
import enum


class AbilityId(enum.Enum):
    NULL_NULL = 0
    SMART = 1
    TAUNT_TAUNT = 2
    STOP_STOP = 4
    STOP_HOLDFIRESPECIAL = 5
    STOP_CHEER = 6
    STOP_DANCE = 7
    HOLDFIRE_STOPSPECIAL = 10
    HOLDFIRE_HOLDFIRE = 11
    MOVE_MOVE = 16
    PATROL_PATROL = 17
    HOLDPOSITION_HOLD = 18
    SCAN_MOVE = 19
    MOVE_TURN = 20
    BEACON_CANCEL = 21
    BEACON_BEACONMOVE = 22
    ATTACK_ATTACK = 23
    ATTACK_ATTACKTOWARDS = 24
    ATTACK_ATTACKBARRAGE = 25
    EFFECT_SPRAY_TERRAN = 26
    EFFECT_SPRAY_ZERG = 28
    EFFECT_SPRAY_PROTOSS = 30
    EFFECT_SALVAGE = 32
    CORRUPTION_CORRUPTIONABILITY = 34
    CORRUPTION_CANCEL = 35
    BEHAVIOR_HOLDFIREON_GHOST = 36
    BEHAVIOR_HOLDFIREOFF_GHOST = 38
    MORPHTOINFESTEDTERRAN_INFESTEDTERRANS = 40
    EXPLODE_EXPLODE = 42
    RESEARCH_INTERCEPTORGRAVITONCATAPULT = 44
    FLEETBEACONRESEARCH_RESEARCHINTERCEPTORLAUNCHSPEEDUPGRADE = 45
    RESEARCH_PHOENIXANIONPULSECRYSTALS = 46
    FLEETBEACONRESEARCH_TEMPESTRANGEUPGRADE = 47
    FLEETBEACONRESEARCH_RESEARCHVOIDRAYSPEEDUPGRADE = 48
    FLEETBEACONRESEARCH_TEMPESTRESEARCHGROUNDATTACKUPGRADE = 49
    FUNGALGROWTH_FUNGALGROWTH = 74
    GUARDIANSHIELD_GUARDIANSHIELD = 76
    EFFECT_REPAIR_MULE = 78
    MORPHZERGLINGTOBANELING_BANELING = 80
    NEXUSTRAINMOTHERSHIP_MOTHERSHIP = 110
    FEEDBACK_FEEDBACK = 140
    EFFECT_MASSRECALL_STRATEGICRECALL = 142
    PLACEPOINTDEFENSEDRONE_POINTDEFENSEDRONE = 144
    HALLUCINATION_ARCHON = 146
    HALLUCINATION_COLOSSUS = 148
    HALLUCINATION_HIGHTEMPLAR = 150
    HALLUCINATION_IMMORTAL = 152
    HALLUCINATION_PHOENIX = 154
    HALLUCINATION_PROBE = 156
    HALLUCINATION_STALKER = 158
    HALLUCINATION_VOIDRAY = 160
    HALLUCINATION_WARPPRISM = 162
    HALLUCINATION_ZEALOT = 164
    HARVEST_GATHER_MULE = 166
    HARVEST_RETURN_MULE = 167
    SEEKERMISSILE_HUNTERSEEKERMISSILE = 169
    CALLDOWNMULE_CALLDOWNMULE = 171
    GRAVITONBEAM_GRAVITONBEAM = 173
    CANCEL_GRAVITONBEAM = 174
    BUILDINPROGRESSNYDUSCANAL_CANCEL = 175
    SIPHON_SIPHON = 177
    SIPHON_CANCEL = 178
    LEECH_LEECH = 179
    SPAWNCHANGELING_SPAWNCHANGELING = 181
    DISGUISEASZEALOT_ZEALOT = 183
    DISGUISEASMARINEWITHSHIELD_MARINE = 185
    DISGUISEASMARINEWITHOUTSHIELD_MARINE = 187
    DISGUISEASZERGLINGWITHWINGS_ZERGLING = 189
    DISGUISEASZERGLINGWITHOUTWINGS_ZERGLING = 191
    PHASESHIFT_PHASESHIFT = 193
    RALLY_BUILDING = 195
    RALLY_MORPHING_UNIT = 199
    RALLY_COMMANDCENTER = 203
    RALLY_NEXUS = 207
    RALLY_HATCHERY_UNITS = 211
    RALLY_HATCHERY_WORKERS = 212
    ROACHWARRENRESEARCH_ROACHWARRENRESEARCH = 215
    RESEARCH_GLIALREGENERATION = 216
    RESEARCH_TUNNELINGCLAWS = 217
    ROACHWARRENRESEARCH_ROACHSUPPLY = 218
    SAPSTRUCTURE_SAPSTRUCTURE = 245
    INFESTEDTERRANS_INFESTEDTERRANS = 247
    NEURALPARASITE_NEURALPARASITE = 249
    CANCEL_NEURALPARASITE = 250
    EFFECT_INJECTLARVA = 251
    EFFECT_STIM_MARAUDER = 253
    SUPPLYDROP_SUPPLYDROP = 255
    _250MMSTRIKECANNONS_250MMSTRIKECANNONS = 257
    _250MMSTRIKECANNONS_CANCEL = 258
    TEMPORALRIFT_TEMPORALRIFT = 259
    EFFECT_CHRONOBOOST = 261
    RESEARCH_ANABOLICSYNTHESIS = 263
    RESEARCH_CHITINOUSPLATING = 265
    WORMHOLETRANSIT_WORMHOLETRANSIT = 293
    HARVEST_GATHER_SCV = 295
    HARVEST_RETURN_SCV = 296
    HARVEST_GATHER_PROBE = 298
    HARVEST_RETURN_PROBE = 299
    ATTACKWARPPRISM_ATTACKWARPPRISM = 301
    ATTACKWARPPRISM_ATTACKTOWARDS = 302
    ATTACKWARPPRISM_ATTACKBARRAGE = 303
    CANCEL_QUEUE1 = 304
    CANCELSLOT_QUEUE1 = 305
    CANCEL_QUEUE5 = 306
    CANCELSLOT_QUEUE5 = 307
    CANCEL_QUEUECANCELTOSELECTION = 308
    CANCELSLOT_QUEUECANCELTOSELECTION = 309
    QUE5LONGBLEND_CANCEL = 310
    QUE5LONGBLEND_CANCELSLOT = 311
    CANCEL_QUEUEADDON = 312
    CANCELSLOT_ADDON = 313
    CANCEL_BUILDINPROGRESS = 314
    HALT_BUILDING = 315
    EFFECT_REPAIR_SCV = 316
    TERRANBUILD_COMMANDCENTER = 318
    TERRANBUILD_SUPPLYDEPOT = 319
    TERRANBUILD_REFINERY = 320
    TERRANBUILD_BARRACKS = 321
    TERRANBUILD_ENGINEERINGBAY = 322
    TERRANBUILD_MISSILETURRET = 323
    TERRANBUILD_BUNKER = 324
    TERRANBUILD_SENSORTOWER = 326
    TERRANBUILD_GHOSTACADEMY = 327
    TERRANBUILD_FACTORY = 328
    TERRANBUILD_STARPORT = 329
    TERRANBUILD_ARMORY = 331
    TERRANBUILD_FUSIONCORE = 333
    HALT_TERRANBUILD = 348
    RAVENBUILD_AUTOTURRET = 349
    RAVENBUILD_CANCEL = 379
    EFFECT_STIM_MARINE = 380
    BEHAVIOR_CLOAKON_GHOST = 382
    BEHAVIOR_CLOAKOFF_GHOST = 383
    SNIPE_SNIPE = 384
    MEDIVACHEAL_HEAL = 386
    SIEGEMODE_SIEGEMODE = 388
    UNSIEGE_UNSIEGE = 390
    BEHAVIOR_CLOAKON_BANSHEE = 392
    BEHAVIOR_CLOAKOFF_BANSHEE = 393
    LOAD_MEDIVAC = 394
    UNLOADALLAT_MEDIVAC = 396
    UNLOADUNIT_MEDIVAC = 397
    SCANNERSWEEP_SCAN = 399
    YAMATO_YAMATOGUN = 401
    MORPH_VIKINGASSAULTMODE = 403
    MORPH_VIKINGFIGHTERMODE = 405
    LOAD_BUNKER = 407
    UNLOADALL_BUNKER = 408
    UNLOADUNIT_BUNKER = 410
    COMMANDCENTERTRANSPORT_COMMANDCENTERTRANSPORT = 412
    UNLOADALL_COMMANDCENTER = 413
    UNLOADUNIT_COMMANDCENTER = 415
    LOADALL_COMMANDCENTER = 416
    LIFT_COMMANDCENTER = 417
    LAND_COMMANDCENTER = 419
    BUILD_TECHLAB_BARRACKS = 421
    BUILD_REACTOR_BARRACKS = 422
    CANCEL_BARRACKSADDON = 451
    LIFT_BARRACKS = 452
    BUILD_TECHLAB_FACTORY = 454
    BUILD_REACTOR_FACTORY = 455
    CANCEL_FACTORYADDON = 484
    LIFT_FACTORY = 485
    BUILD_TECHLAB_STARPORT = 487
    BUILD_REACTOR_STARPORT = 488
    CANCEL_STARPORTADDON = 517
    LIFT_STARPORT = 518
    LAND_FACTORY = 520
    LAND_STARPORT = 522
    COMMANDCENTERTRAIN_SCV = 524
    LAND_BARRACKS = 554
    MORPH_SUPPLYDEPOT_LOWER = 556
    MORPH_SUPPLYDEPOT_RAISE = 558
    BARRACKSTRAIN_MARINE = 560
    BARRACKSTRAIN_REAPER = 561
    BARRACKSTRAIN_GHOST = 562
    BARRACKSTRAIN_MARAUDER = 563
    FACTORYTRAIN_FACTORYTRAIN = 590
    FACTORYTRAIN_SIEGETANK = 591
    FACTORYTRAIN_THOR = 594
    FACTORYTRAIN_HELLION = 595
    TRAIN_HELLBAT = 596
    TRAIN_CYCLONE = 597
    FACTORYTRAIN_WIDOWMINE = 614
    STARPORTTRAIN_MEDIVAC = 620
    STARPORTTRAIN_BANSHEE = 621
    STARPORTTRAIN_RAVEN = 622
    STARPORTTRAIN_BATTLECRUISER = 623
    STARPORTTRAIN_VIKINGFIGHTER = 624
    STARPORTTRAIN_LIBERATOR = 626
    RESEARCH_HISECAUTOTRACKING = 650
    RESEARCH_TERRANSTRUCTUREARMORUPGRADE = 651
    ENGINEERINGBAYRESEARCH_TERRANINFANTRYWEAPONSLEVEL1 = 652
    ENGINEERINGBAYRESEARCH_TERRANINFANTRYWEAPONSLEVEL2 = 653
    ENGINEERINGBAYRESEARCH_TERRANINFANTRYWEAPONSLEVEL3 = 654
    RESEARCH_NEOSTEELFRAME = 655
    ENGINEERINGBAYRESEARCH_TERRANINFANTRYARMORLEVEL1 = 656
    ENGINEERINGBAYRESEARCH_TERRANINFANTRYARMORLEVEL2 = 657
    ENGINEERINGBAYRESEARCH_TERRANINFANTRYARMORLEVEL3 = 658
    MERCCOMPOUNDRESEARCH_MERCCOMPOUNDRESEARCH = 680
    MERCCOMPOUNDRESEARCH_REAPERSPEED = 683
    BUILD_NUKE = 710
    BARRACKSTECHLABRESEARCH_STIMPACK = 730
    RESEARCH_COMBATSHIELD = 731
    RESEARCH_CONCUSSIVESHELLS = 732
    FACTORYTECHLABRESEARCH_FACTORYTECHLABRESEARCH = 760
    RESEARCH_INFERNALPREIGNITER = 761
    FACTORYTECHLABRESEARCH_RESEARCHTRANSFORMATIONSERVOS = 763
    RESEARCH_DRILLINGCLAWS = 764
    FACTORYTECHLABRESEARCH_RESEARCHLOCKONRANGEUPGRADE = 765
    RESEARCH_SMARTSERVOS = 766
    FACTORYTECHLABRESEARCH_RESEARCHARMORPIERCINGROCKETS = 767
    RESEARCH_CYCLONERAPIDFIRELAUNCHERS = 768
    RESEARCH_CYCLONELOCKONDAMAGE = 769
    FACTORYTECHLABRESEARCH_CYCLONERESEARCHHURRICANETHRUSTERS = 770
    RESEARCH_BANSHEECLOAKINGFIELD = 790
    STARPORTTECHLABRESEARCH_RESEARCHMEDIVACENERGYUPGRADE = 792
    RESEARCH_RAVENCORVIDREACTOR = 793
    STARPORTTECHLABRESEARCH_RESEARCHSEEKERMISSILE = 796
    STARPORTTECHLABRESEARCH_RESEARCHDURABLEMATERIALS = 797
    RESEARCH_BANSHEEHYPERFLIGHTROTORS = 799
    STARPORTTECHLABRESEARCH_RESEARCHLIBERATORAGMODE = 800
    STARPORTTECHLABRESEARCH_RESEARCHRAPIDDEPLOYMENT = 802
    RESEARCH_RAVENRECALIBRATEDEXPLOSIVES = 803
    RESEARCH_HIGHCAPACITYFUELTANKS = 804
    RESEARCH_ADVANCEDBALLISTICS = 805
    STARPORTTECHLABRESEARCH_RAVENRESEARCHENHANCEDMUNITIONS = 806
    STARPORTTECHLABRESEARCH_RESEARCHRAVENINTERFERENCEMATRIX = 807
    RESEARCH_PERSONALCLOAKING = 820
    ARMORYRESEARCH_ARMORYRESEARCH = 850
    ARMORYRESEARCH_TERRANVEHICLEPLATINGLEVEL1 = 852
    ARMORYRESEARCH_TERRANVEHICLEPLATINGLEVEL2 = 853
    ARMORYRESEARCH_TERRANVEHICLEPLATINGLEVEL3 = 854
    ARMORYRESEARCH_TERRANVEHICLEWEAPONSLEVEL1 = 855
    ARMORYRESEARCH_TERRANVEHICLEWEAPONSLEVEL2 = 856
    ARMORYRESEARCH_TERRANVEHICLEWEAPONSLEVEL3 = 857
    ARMORYRESEARCH_TERRANSHIPPLATINGLEVEL1 = 858
    ARMORYRESEARCH_TERRANSHIPPLATINGLEVEL2 = 859
    ARMORYRESEARCH_TERRANSHIPPLATINGLEVEL3 = 860
    ARMORYRESEARCH_TERRANSHIPWEAPONSLEVEL1 = 861
    ARMORYRESEARCH_TERRANSHIPWEAPONSLEVEL2 = 862
    ARMORYRESEARCH_TERRANSHIPWEAPONSLEVEL3 = 863
    ARMORYRESEARCH_TERRANVEHICLEANDSHIPPLATINGLEVEL1 = 864
    ARMORYRESEARCH_TERRANVEHICLEANDSHIPPLATINGLEVEL2 = 865
    ARMORYRESEARCH_TERRANVEHICLEANDSHIPPLATINGLEVEL3 = 866
    PROTOSSBUILD_NEXUS = 880
    PROTOSSBUILD_PYLON = 881
    PROTOSSBUILD_ASSIMILATOR = 882
    PROTOSSBUILD_GATEWAY = 883
    PROTOSSBUILD_FORGE = 884
    PROTOSSBUILD_FLEETBEACON = 885
    PROTOSSBUILD_TWILIGHTCOUNCIL = 886
    PROTOSSBUILD_PHOTONCANNON = 887
    PROTOSSBUILD_STARGATE = 889
    PROTOSSBUILD_TEMPLARARCHIVE = 890
    PROTOSSBUILD_DARKSHRINE = 891
    PROTOSSBUILD_ROBOTICSBAY = 892
    PROTOSSBUILD_ROBOTICSFACILITY = 893
    PROTOSSBUILD_CYBERNETICSCORE = 894
    BUILD_SHIELDBATTERY = 895
    PROTOSSBUILD_CANCEL = 910
    LOAD_WARPPRISM = 911
    UNLOADALL_WARPPRISM = 912
    UNLOADALLAT_WARPPRISM = 913
    UNLOADUNIT_WARPPRISM = 914
    GATEWAYTRAIN_ZEALOT = 916
    GATEWAYTRAIN_STALKER = 917
    GATEWAYTRAIN_HIGHTEMPLAR = 919
    GATEWAYTRAIN_DARKTEMPLAR = 920
    GATEWAYTRAIN_SENTRY = 921
    TRAIN_ADEPT = 922
    STARGATETRAIN_PHOENIX = 946
    STARGATETRAIN_CARRIER = 948
    STARGATETRAIN_VOIDRAY = 950
    STARGATETRAIN_ORACLE = 954
    STARGATETRAIN_TEMPEST = 955
    ROBOTICSFACILITYTRAIN_WARPPRISM = 976
    ROBOTICSFACILITYTRAIN_OBSERVER = 977
    ROBOTICSFACILITYTRAIN_COLOSSUS = 978
    ROBOTICSFACILITYTRAIN_IMMORTAL = 979
    TRAIN_DISRUPTOR = 994
    NEXUSTRAIN_PROBE = 1006
    PSISTORM_PSISTORM = 1036
    CANCEL_HANGARQUEUE5 = 1038
    CANCELSLOT_HANGARQUEUE5 = 1039
    BROODLORDQUEUE2_CANCEL = 1040
    BROODLORDQUEUE2_CANCELSLOT = 1041
    BUILD_INTERCEPTORS = 1042
    FORGERESEARCH_PROTOSSGROUNDWEAPONSLEVEL1 = 1062
    FORGERESEARCH_PROTOSSGROUNDWEAPONSLEVEL2 = 1063
    FORGERESEARCH_PROTOSSGROUNDWEAPONSLEVEL3 = 1064
    FORGERESEARCH_PROTOSSGROUNDARMORLEVEL1 = 1065
    FORGERESEARCH_PROTOSSGROUNDARMORLEVEL2 = 1066
    FORGERESEARCH_PROTOSSGROUNDARMORLEVEL3 = 1067
    FORGERESEARCH_PROTOSSSHIELDSLEVEL1 = 1068
    FORGERESEARCH_PROTOSSSHIELDSLEVEL2 = 1069
    FORGERESEARCH_PROTOSSSHIELDSLEVEL3 = 1070
    ROBOTICSBAYRESEARCH_ROBOTICSBAYRESEARCH = 1092
    RESEARCH_GRAVITICBOOSTER = 1093
    RESEARCH_GRAVITICDRIVE = 1094
    RESEARCH_EXTENDEDTHERMALLANCE = 1097
    ROBOTICSBAYRESEARCH_RESEARCHIMMORTALREVIVE = 1099
    TEMPLARARCHIVESRESEARCH_TEMPLARARCHIVESRESEARCH = 1122
    RESEARCH_PSISTORM = 1126
    ZERGBUILD_HATCHERY = 1152
    ZERGBUILD_CREEPTUMOR = 1153
    ZERGBUILD_EXTRACTOR = 1154
    ZERGBUILD_SPAWNINGPOOL = 1155
    ZERGBUILD_EVOLUTIONCHAMBER = 1156
    ZERGBUILD_HYDRALISKDEN = 1157
    ZERGBUILD_SPIRE = 1158
    ZERGBUILD_ULTRALISKCAVERN = 1159
    ZERGBUILD_INFESTATIONPIT = 1160
    ZERGBUILD_NYDUSNETWORK = 1161
    ZERGBUILD_BANELINGNEST = 1162
    BUILD_LURKERDEN = 1163
    ZERGBUILD_ROACHWARREN = 1165
    ZERGBUILD_SPINECRAWLER = 1166
    ZERGBUILD_SPORECRAWLER = 1167
    ZERGBUILD_CANCEL = 1182
    HARVEST_GATHER_DRONE = 1183
    HARVEST_RETURN_DRONE = 1184
    RESEARCH_ZERGMELEEWEAPONSLEVEL1 = 1186
    RESEARCH_ZERGMELEEWEAPONSLEVEL2 = 1187
    RESEARCH_ZERGMELEEWEAPONSLEVEL3 = 1188
    RESEARCH_ZERGGROUNDARMORLEVEL1 = 1189
    RESEARCH_ZERGGROUNDARMORLEVEL2 = 1190
    RESEARCH_ZERGGROUNDARMORLEVEL3 = 1191
    RESEARCH_ZERGMISSILEWEAPONSLEVEL1 = 1192
    RESEARCH_ZERGMISSILEWEAPONSLEVEL2 = 1193
    RESEARCH_ZERGMISSILEWEAPONSLEVEL3 = 1194
    EVOLUTIONCHAMBERRESEARCH_EVOLVEPROPULSIVEPERISTALSIS = 1195
    UPGRADETOLAIR_LAIR = 1216
    CANCEL_MORPHLAIR = 1217
    UPGRADETOHIVE_HIVE = 1218
    CANCEL_MORPHHIVE = 1219
    UPGRADETOGREATERSPIRE_GREATERSPIRE = 1220
    CANCEL_MORPHGREATERSPIRE = 1221
    LAIRRESEARCH_LAIRRESEARCH = 1222
    RESEARCH_PNEUMATIZEDCARAPACE = 1223
    LAIRRESEARCH_EVOLVEVENTRALSACKS = 1224
    RESEARCH_BURROW = 1225
    RESEARCH_ZERGLINGADRENALGLANDS = 1252
    RESEARCH_ZERGLINGMETABOLICBOOST = 1253
    RESEARCH_GROOVEDSPINES = 1282
    RESEARCH_MUSCULARAUGMENTS = 1283
    HYDRALISKDENRESEARCH_RESEARCHFRENZY = 1284
    HYDRALISKDENRESEARCH_RESEARCHLURKERRANGE = 1286
    RESEARCH_ZERGFLYERATTACKLEVEL1 = 1312
    RESEARCH_ZERGFLYERATTACKLEVEL2 = 1313
    RESEARCH_ZERGFLYERATTACKLEVEL3 = 1314
    RESEARCH_ZERGFLYERARMORLEVEL1 = 1315
    RESEARCH_ZERGFLYERARMORLEVEL2 = 1316
    RESEARCH_ZERGFLYERARMORLEVEL3 = 1317
    LARVATRAIN_DRONE = 1342
    LARVATRAIN_ZERGLING = 1343
    LARVATRAIN_OVERLORD = 1344
    LARVATRAIN_HYDRALISK = 1345
    LARVATRAIN_MUTALISK = 1346
    LARVATRAIN_ULTRALISK = 1348
    LARVATRAIN_ROACH = 1351
    LARVATRAIN_INFESTOR = 1352
    LARVATRAIN_CORRUPTOR = 1353
    LARVATRAIN_VIPER = 1354
    TRAIN_SWARMHOST = 1356
    MORPHTOBROODLORD_BROODLORD = 1372
    CANCEL_MORPHBROODLORD = 1373
    BURROWDOWN_BANELING = 1374
    BURROWBANELINGDOWN_CANCEL = 1375
    BURROWUP_BANELING = 1376
    BURROWDOWN_DRONE = 1378
    BURROWDRONEDOWN_CANCEL = 1379
    BURROWUP_DRONE = 1380
    BURROWDOWN_HYDRALISK = 1382
    BURROWHYDRALISKDOWN_CANCEL = 1383
    BURROWUP_HYDRALISK = 1384
    BURROWDOWN_ROACH = 1386
    BURROWROACHDOWN_CANCEL = 1387
    BURROWUP_ROACH = 1388
    BURROWDOWN_ZERGLING = 1390
    BURROWZERGLINGDOWN_CANCEL = 1391
    BURROWUP_ZERGLING = 1392
    BURROWDOWN_INFESTORTERRAN = 1394
    BURROWUP_INFESTORTERRAN = 1396
    REDSTONELAVACRITTERBURROW_BURROWDOWN = 1398
    REDSTONELAVACRITTERINJUREDBURROW_BURROWDOWN = 1400
    REDSTONELAVACRITTERUNBURROW_BURROWUP = 1402
    REDSTONELAVACRITTERINJUREDUNBURROW_BURROWUP = 1404
    LOAD_OVERLORD = 1406
    UNLOADALLAT_OVERLORD = 1408
    UNLOADUNIT_OVERLORD = 1409
    MERGEABLE_CANCEL = 1411
    WARPABLE_CANCEL = 1412
    WARPGATETRAIN_ZEALOT = 1413
    WARPGATETRAIN_STALKER = 1414
    WARPGATETRAIN_HIGHTEMPLAR = 1416
    WARPGATETRAIN_DARKTEMPLAR = 1417
    WARPGATETRAIN_SENTRY = 1418
    TRAINWARP_ADEPT = 1419
    BURROWDOWN_QUEEN = 1433
    BURROWQUEENDOWN_CANCEL = 1434
    BURROWUP_QUEEN = 1435
    LOAD_NYDUSNETWORK = 1437
    UNLOADALL_NYDASNETWORK = 1438
    UNLOADUNIT_NYDASNETWORK = 1440
    EFFECT_BLINK_STALKER = 1442
    BURROWDOWN_INFESTOR = 1444
    BURROWINFESTORDOWN_CANCEL = 1445
    BURROWUP_INFESTOR = 1446
    MORPH_OVERSEER = 1448
    CANCEL_MORPHOVERSEER = 1449
    UPGRADETOPLANETARYFORTRESS_PLANETARYFORTRESS = 1450
    CANCEL_MORPHPLANETARYFORTRESS = 1451
    INFESTATIONPITRESEARCH_INFESTATIONPITRESEARCH = 1452
    RESEARCH_NEURALPARASITE = 1455
    INFESTATIONPITRESEARCH_RESEARCHLOCUSTLIFETIMEINCREASE = 1456
    INFESTATIONPITRESEARCH_EVOLVEAMORPHOUSARMORCLOUD = 1457
    RESEARCH_CENTRIFUGALHOOKS = 1482
    BURROWDOWN_ULTRALISK = 1512
    BURROWUP_ULTRALISK = 1514
    UPGRADETOORBITAL_ORBITALCOMMAND = 1516
    CANCEL_MORPHORBITAL = 1517
    MORPH_WARPGATE = 1518
    UPGRADETOWARPGATE_CANCEL = 1519
    MORPH_GATEWAY = 1520
    MORPHBACKTOGATEWAY_CANCEL = 1521
    LIFT_ORBITALCOMMAND = 1522
    LAND_ORBITALCOMMAND = 1524
    FORCEFIELD_FORCEFIELD = 1526
    FORCEFIELD_CANCEL = 1527
    MORPH_WARPPRISMPHASINGMODE = 1528
    PHASINGMODE_CANCEL = 1529
    MORPH_WARPPRISMTRANSPORTMODE = 1530
    TRANSPORTMODE_CANCEL = 1531
    RESEARCH_BATTLECRUISERWEAPONREFIT = 1532
    FUSIONCORERESEARCH_RESEARCHBALLISTICRANGE = 1533
    FUSIONCORERESEARCH_RESEARCHRAPIDREIGNITIONSYSTEM = 1534
    FUSIONCORERESEARCH_RESEARCHMEDIVACENERGYUPGRADE = 1535
    CYBERNETICSCORERESEARCH_PROTOSSAIRWEAPONSLEVEL1 = 1562
    CYBERNETICSCORERESEARCH_PROTOSSAIRWEAPONSLEVEL2 = 1563
    CYBERNETICSCORERESEARCH_PROTOSSAIRWEAPONSLEVEL3 = 1564
    CYBERNETICSCORERESEARCH_PROTOSSAIRARMORLEVEL1 = 1565
    CYBERNETICSCORERESEARCH_PROTOSSAIRARMORLEVEL2 = 1566
    CYBERNETICSCORERESEARCH_PROTOSSAIRARMORLEVEL3 = 1567
    RESEARCH_WARPGATE = 1568
    CYBERNETICSCORERESEARCH_RESEARCHHALLUCINATION = 1571
    RESEARCH_CHARGE = 1592
    RESEARCH_BLINK = 1593
    RESEARCH_ADEPTRESONATINGGLAIVES = 1594
    TWILIGHTCOUNCILRESEARCH_RESEARCHPSIONICSURGE = 1595
    TWILIGHTCOUNCILRESEARCH_RESEARCHAMPLIFIEDSHIELDING = 1596
    TWILIGHTCOUNCILRESEARCH_RESEARCHPSIONICAMPLIFIERS = 1597
    TACNUKESTRIKE_NUKECALLDOWN = 1622
    CANCEL_NUKE = 1623
    SALVAGEBUNKERREFUND_SALVAGE = 1624
    SALVAGEBUNKER_SALVAGE = 1626
    EMP_EMP = 1628
    VORTEX_VORTEX = 1630
    TRAINQUEEN_QUEEN = 1632
    BURROWCREEPTUMORDOWN_BURROWDOWN = 1662
    TRANSFUSION_TRANSFUSION = 1664
    TECHLABMORPH_TECHLABMORPH = 1666
    BARRACKSTECHLABMORPH_TECHLABBARRACKS = 1668
    FACTORYTECHLABMORPH_TECHLABFACTORY = 1670
    STARPORTTECHLABMORPH_TECHLABSTARPORT = 1672
    REACTORMORPH_REACTORMORPH = 1674
    BARRACKSREACTORMORPH_REACTOR = 1676
    FACTORYREACTORMORPH_REACTOR = 1678
    STARPORTREACTORMORPH_REACTOR = 1680
    ATTACK_REDIRECT = 1682
    EFFECT_STIM_MARINE_REDIRECT = 1683
    EFFECT_STIM_MARAUDER_REDIRECT = 1684
    BURROWEDSTOP_STOPROACHBURROWED = 1685
    BURROWEDSTOP_HOLDFIRESPECIAL = 1686
    STOP_REDIRECT = 1691
    BEHAVIOR_GENERATECREEPON = 1692
    BEHAVIOR_GENERATECREEPOFF = 1693
    BUILD_CREEPTUMOR_QUEEN = 1694
    QUEENBUILD_CANCEL = 1724
    SPINECRAWLERUPROOT_SPINECRAWLERUPROOT = 1725
    SPINECRAWLERUPROOT_CANCEL = 1726
    SPORECRAWLERUPROOT_SPORECRAWLERUPROOT = 1727
    SPORECRAWLERUPROOT_CANCEL = 1728
    SPINECRAWLERROOT_SPINECRAWLERROOT = 1729
    CANCEL_SPINECRAWLERROOT = 1730
    SPORECRAWLERROOT_SPORECRAWLERROOT = 1731
    CANCEL_SPORECRAWLERROOT = 1732
    BUILD_CREEPTUMOR_TUMOR = 1733
    CANCEL_CREEPTUMOR = 1763
    BUILDAUTOTURRET_AUTOTURRET = 1764
    MORPH_ARCHON = 1766
    ARCHON_WARP_TARGET = 1767
    BUILD_NYDUSWORM = 1768
    BUILDNYDUSCANAL_SUMMONNYDUSCANALATTACKER = 1769
    BUILDNYDUSCANAL_CANCEL = 1798
    BROODLORDHANGAR_BROODLORDHANGAR = 1799
    EFFECT_CHARGE = 1819
    TOWERCAPTURE_TOWERCAPTURE = 1820
    HERDINTERACT_HERD = 1821
    FRENZY_FRENZY = 1823
    CONTAMINATE_CONTAMINATE = 1825
    SHATTER_SHATTER = 1827
    INFESTEDTERRANSLAYEGG_INFESTEDTERRANS = 1829
    CANCEL_QUEUEPASIVE = 1831
    CANCELSLOT_QUEUEPASSIVE = 1832
    CANCEL_QUEUEPASSIVECANCELTOSELECTION = 1833
    CANCELSLOT_QUEUEPASSIVECANCELTOSELECTION = 1834
    MORPHTOGHOSTALTERNATE_MOVE = 1835
    MORPHTOGHOSTNOVA_MOVE = 1837
    DIGESTERCREEPSPRAY_DIGESTERCREEPSPRAY = 1839
    MORPHTOCOLLAPSIBLETERRANTOWERDEBRIS_MORPHTOCOLLAPSIBLETERRANTOWERDEBRIS = 1841
    MORPHTOCOLLAPSIBLETERRANTOWERDEBRIS_CANCEL = 1842
    MORPHTOCOLLAPSIBLETERRANTOWERDEBRISRAMPLEFT_MORPHTOCOLLAPSIBLETERRANTOWERDEBRISRAMPLEFT = 1843
    MORPHTOCOLLAPSIBLETERRANTOWERDEBRISRAMPLEFT_CANCEL = 1844
    MORPHTOCOLLAPSIBLETERRANTOWERDEBRISRAMPRIGHT_MORPHTOCOLLAPSIBLETERRANTOWERDEBRISRAMPRIGHT = 1845
    MORPHTOCOLLAPSIBLETERRANTOWERDEBRISRAMPRIGHT_CANCEL = 1846
    MORPH_MOTHERSHIP = 1847
    CANCEL_MORPHMOTHERSHIP = 1848
    MOTHERSHIPSTASIS_MOTHERSHIPSTASIS = 1849
    CANCEL_MOTHERSHIPSTASIS = 1850
    MOTHERSHIPCOREWEAPON_MOTHERSHIPSTASIS = 1851
    NEXUSTRAINMOTHERSHIPCORE_MOTHERSHIPCORE = 1853
    MOTHERSHIPCORETELEPORT_MOTHERSHIPCORETELEPORT = 1883
    SALVAGEDRONEREFUND_SALVAGE = 1885
    SALVAGEDRONE_SALVAGE = 1887
    SALVAGEZERGLINGREFUND_SALVAGE = 1889
    SALVAGEZERGLING_SALVAGE = 1891
    SALVAGEQUEENREFUND_SALVAGE = 1893
    SALVAGEQUEEN_SALVAGE = 1895
    SALVAGEROACHREFUND_SALVAGE = 1897
    SALVAGEROACH_SALVAGE = 1899
    SALVAGEBANELINGREFUND_SALVAGE = 1901
    SALVAGEBANELING_SALVAGE = 1903
    SALVAGEHYDRALISKREFUND_SALVAGE = 1905
    SALVAGEHYDRALISK_SALVAGE = 1907
    SALVAGEINFESTORREFUND_SALVAGE = 1909
    SALVAGEINFESTOR_SALVAGE = 1911
    SALVAGESWARMHOSTREFUND_SALVAGE = 1913
    SALVAGESWARMHOST_SALVAGE = 1915
    SALVAGEULTRALISKREFUND_SALVAGE = 1917
    SALVAGEULTRALISK_SALVAGE = 1919
    DIGESTERTRANSPORT_LOADDIGESTER = 1921
    SPECTRESHIELD_SPECTRESHIELD = 1926
    XELNAGAHEALINGSHRINE_XELNAGAHEALINGSHRINE = 1928
    NEXUSINVULNERABILITY_NEXUSINVULNERABILITY = 1930
    NEXUSPHASESHIFT_NEXUSPHASESHIFT = 1932
    SPAWNCHANGELINGTARGET_SPAWNCHANGELING = 1934
    QUEENLAND_QUEENLAND = 1936
    QUEENFLY_QUEENFLY = 1938
    ORACLECLOAKFIELD_ORACLECLOAKFIELD = 1940
    FLYERSHIELD_FLYERSHIELD = 1942
    LOCUSTTRAIN_SWARMHOST = 1944
    EFFECT_MASSRECALL_MOTHERSHIPCORE = 1974
    SINGLERECALL_SINGLERECALL = 1976
    MORPH_HELLION = 1978
    RESTORESHIELDS_RESTORESHIELDS = 1980
    SCRYER_SCRYER = 1982
    BURROWCHARGETRIAL_BURROWCHARGETRIAL = 1984
    LEECHRESOURCES_LEECHRESOURCES = 1986
    LEECHRESOURCES_CANCEL = 1987
    SNIPEDOT_SNIPEDOT = 1988
    SWARMHOSTSPAWNLOCUSTS_LOCUSTMP = 1990
    CLONE_CLONE = 1992
    BUILDINGSHIELD_BUILDINGSHIELD = 1994
    MORPHTOCOLLAPSIBLEROCKTOWERDEBRIS_MORPHTOCOLLAPSIBLEROCKTOWERDEBRIS = 1996
    MORPHTOCOLLAPSIBLEROCKTOWERDEBRIS_CANCEL = 1997
    MORPH_HELLBAT = 1998
    BUILDINGSTASIS_BUILDINGSTASIS = 2000
    RESOURCEBLOCKER_RESOURCEBLOCKER = 2002
    RESOURCESTUN_RESOURCESTUN = 2004
    MAXIUMTHRUST_MAXIMUMTHRUST = 2006
    SACRIFICE_SACRIFICE = 2008
    BURROWCHARGEMP_BURROWCHARGEMP = 2010
    BURROWCHARGEREVD_BURROWCHARGEREVD = 2012
    BURROWDOWN_SWARMHOST = 2014
    MORPHTOSWARMHOSTBURROWEDMP_CANCEL = 2015
    BURROWUP_SWARMHOST = 2016
    SPAWNINFESTEDTERRAN_LOCUSTMP = 2018
    ATTACKPROTOSSBUILDING_ATTACKBUILDING = 2048
    ATTACKPROTOSSBUILDING_ATTACKTOWARDS = 2049
    ATTACKPROTOSSBUILDING_ATTACKBARRAGE = 2050
    BURROWEDBANELINGSTOP_STOPROACHBURROWED = 2051
    BURROWEDBANELINGSTOP_HOLDFIRESPECIAL = 2052
    STOP_BUILDING = 2057
    STOPPROTOSSBUILDING_HOLDFIRE = 2058
    STOPPROTOSSBUILDING_CHEER = 2059
    STOPPROTOSSBUILDING_DANCE = 2060
    BLINDINGCLOUD_BLINDINGCLOUD = 2063
    EYESTALK_EYESTALK = 2065
    EYESTALK_CANCEL = 2066
    EFFECT_ABDUCT = 2067
    VIPERCONSUME_VIPERCONSUME = 2069
    VIPERCONSUMEMINERALS_VIPERCONSUME = 2071
    VIPERCONSUMESTRUCTURE_VIPERCONSUME = 2073
    CANCEL_PROTOSSBUILDINGQUEUE = 2075
    PROTOSSBUILDINGQUEUE_CANCELSLOT = 2076
    QUE8_CANCEL = 2077
    QUE8_CANCELSLOT = 2078
    TESTZERG_TESTZERG = 2079
    TESTZERG_CANCEL = 2080
    BEHAVIOR_BUILDINGATTACKON = 2081
    BEHAVIOR_BUILDINGATTACKOFF = 2082
    PICKUPSCRAPSMALL_PICKUPSCRAPSMALL = 2083
    PICKUPSCRAPMEDIUM_PICKUPSCRAPMEDIUM = 2085
    PICKUPSCRAPLARGE_PICKUPSCRAPLARGE = 2087
    PICKUPPALLETGAS_PICKUPPALLETGAS = 2089
    PICKUPPALLETMINERALS_PICKUPPALLETMINERALS = 2091
    MASSIVEKNOCKOVER_MASSIVEKNOCKOVER = 2093
    BURROWDOWN_WIDOWMINE = 2095
    WIDOWMINEBURROW_CANCEL = 2096
    BURROWUP_WIDOWMINE = 2097
    WIDOWMINEATTACK_WIDOWMINEATTACK = 2099
    TORNADOMISSILE_TORNADOMISSILE = 2101
    MOTHERSHIPCOREENERGIZE_MOTHERSHIPCOREENERGIZE = 2102
    MOTHERSHIPCOREENERGIZE_CANCEL = 2103
    LURKERASPECTMPFROMHYDRALISKBURROWED_LURKERMPFROMHYDRALISKBURROWED = 2104
    LURKERASPECTMPFROMHYDRALISKBURROWED_CANCEL = 2105
    LURKERASPECTMP_LURKERMP = 2106
    LURKERASPECTMP_CANCEL = 2107
    BURROWDOWN_LURKER = 2108
    BURROWLURKERMPDOWN_CANCEL = 2109
    BURROWUP_LURKER = 2110
    MORPH_LURKERDEN = 2112
    CANCEL_MORPHLURKERDEN = 2113
    HALLUCINATION_ORACLE = 2114
    EFFECT_MEDIVACIGNITEAFTERBURNERS = 2116
    EXTENDINGBRIDGENEWIDE8OUT_BRIDGEEXTEND = 2118
    EXTENDINGBRIDGENEWIDE8_BRIDGERETRACT = 2120
    EXTENDINGBRIDGENWWIDE8OUT_BRIDGEEXTEND = 2122
    EXTENDINGBRIDGENWWIDE8_BRIDGERETRACT = 2124
    EXTENDINGBRIDGENEWIDE10OUT_BRIDGEEXTEND = 2126
    EXTENDINGBRIDGENEWIDE10_BRIDGERETRACT = 2128
    EXTENDINGBRIDGENWWIDE10OUT_BRIDGEEXTEND = 2130
    EXTENDINGBRIDGENWWIDE10_BRIDGERETRACT = 2132
    EXTENDINGBRIDGENEWIDE12OUT_BRIDGEEXTEND = 2134
    EXTENDINGBRIDGENEWIDE12_BRIDGERETRACT = 2136
    EXTENDINGBRIDGENWWIDE12OUT_BRIDGEEXTEND = 2138
    EXTENDINGBRIDGENWWIDE12_BRIDGERETRACT = 2140
    INVULNERABILITYSHIELD_INVULNERABILITYSHIELD = 2142
    CRITTERFLEE_CRITTERFLEE = 2144
    ORACLEREVELATION_ORACLEREVELATION = 2146
    ORACLEREVELATIONMODE_ORACLEREVELATIONMODE = 2148
    ORACLEREVELATIONMODE_CANCEL = 2149
    ORACLENORMALMODE_ORACLENORMALMODE = 2150
    ORACLENORMALMODE_CANCEL = 2151
    MORPHTOCOLLAPSIBLEROCKTOWERDEBRISRAMPRIGHT_MORPHTOCOLLAPSIBLEROCKTOWERDEBRISRAMPRIGHT = 2152
    MORPHTOCOLLAPSIBLEROCKTOWERDEBRISRAMPRIGHT_CANCEL = 2153
    MORPHTOCOLLAPSIBLEROCKTOWERDEBRISRAMPLEFT_MORPHTOCOLLAPSIBLEROCKTOWERDEBRISRAMPLEFT = 2154
    MORPHTOCOLLAPSIBLEROCKTOWERDEBRISRAMPLEFT_CANCEL = 2155
    VOIDSIPHON_VOIDSIPHON = 2156
    ULTRALISKWEAPONCOOLDOWN_ULTRALISKWEAPONCOOLDOWN = 2158
    MOTHERSHIPCOREPURIFYNEXUSCANCEL_CANCEL = 2160
    EFFECT_PHOTONOVERCHARGE = 2162
    XELNAGA_CAVERNS_DOORE_XELNAGA_CAVERNS_DOORDEFAULTCLOSE = 2164
    XELNAGA_CAVERNS_DOOREOPENED_XELNAGA_CAVERNS_DOORDEFAULTCLOSE = 2166
    XELNAGA_CAVERNS_DOORN_XELNAGA_CAVERNS_DOORDEFAULTCLOSE = 2168
    XELNAGA_CAVERNS_DOORNE_XELNAGA_CAVERNS_DOORDEFAULTCLOSE = 2170
    XELNAGA_CAVERNS_DOORNEOPENED_XELNAGA_CAVERNS_DOORDEFAULTOPEN = 2172
    XELNAGA_CAVERNS_DOORNOPENED_XELNAGA_CAVERNS_DOORDEFAULTOPEN = 2174
    XELNAGA_CAVERNS_DOORNW_XELNAGA_CAVERNS_DOORDEFAULTCLOSE = 2176
    XELNAGA_CAVERNS_DOORNWOPENED_XELNAGA_CAVERNS_DOORDEFAULTOPEN = 2178
    XELNAGA_CAVERNS_DOORS_XELNAGA_CAVERNS_DOORDEFAULTCLOSE = 2180
    XELNAGA_CAVERNS_DOORSE_XELNAGA_CAVERNS_DOORDEFAULTCLOSE = 2182
    XELNAGA_CAVERNS_DOORSEOPENED_XELNAGA_CAVERNS_DOORDEFAULTOPEN = 2184
    XELNAGA_CAVERNS_DOORSOPENED_XELNAGA_CAVERNS_DOORDEFAULTOPEN = 2186
    XELNAGA_CAVERNS_DOORSW_XELNAGA_CAVERNS_DOORDEFAULTCLOSE = 2188
    XELNAGA_CAVERNS_DOORSWOPENED_XELNAGA_CAVERNS_DOORDEFAULTOPEN = 2190
    XELNAGA_CAVERNS_DOORW_XELNAGA_CAVERNS_DOORDEFAULTCLOSE = 2192
    XELNAGA_CAVERNS_DOORWOPENED_XELNAGA_CAVERNS_DOORDEFAULTOPEN = 2194
    XELNAGA_CAVERNS_FLOATING_BRIDGENE8OUT_BRIDGEEXTEND = 2196
    XELNAGA_CAVERNS_FLOATING_BRIDGENE8_BRIDGERETRACT = 2198
    XELNAGA_CAVERNS_FLOATING_BRIDGENW8OUT_BRIDGEEXTEND = 2200
    XELNAGA_CAVERNS_FLOATING_BRIDGENW8_BRIDGERETRACT = 2202
    XELNAGA_CAVERNS_FLOATING_BRIDGENE10OUT_BRIDGEEXTEND = 2204
    XELNAGA_CAVERNS_FLOATING_BRIDGENE10_BRIDGERETRACT = 2206
    XELNAGA_CAVERNS_FLOATING_BRIDGENW10OUT_BRIDGEEXTEND = 2208
    XELNAGA_CAVERNS_FLOATING_BRIDGENW10_BRIDGERETRACT = 2210
    XELNAGA_CAVERNS_FLOATING_BRIDGENE12OUT_BRIDGEEXTEND = 2212
    XELNAGA_CAVERNS_FLOATING_BRIDGENE12_BRIDGERETRACT = 2214
    XELNAGA_CAVERNS_FLOATING_BRIDGENW12OUT_BRIDGEEXTEND = 2216
    XELNAGA_CAVERNS_FLOATING_BRIDGENW12_BRIDGERETRACT = 2218
    XELNAGA_CAVERNS_FLOATING_BRIDGEH8OUT_BRIDGEEXTEND = 2220
    XELNAGA_CAVERNS_FLOATING_BRIDGEH8_BRIDGERETRACT = 2222
    XELNAGA_CAVERNS_FLOATING_BRIDGEV8OUT_BRIDGEEXTEND = 2224
    XELNAGA_CAVERNS_FLOATING_BRIDGEV8_BRIDGERETRACT = 2226
    XELNAGA_CAVERNS_FLOATING_BRIDGEH10OUT_BRIDGEEXTEND = 2228
    XELNAGA_CAVERNS_FLOATING_BRIDGEH10_BRIDGERETRACT = 2230
    XELNAGA_CAVERNS_FLOATING_BRIDGEV10OUT_BRIDGEEXTEND = 2232
    XELNAGA_CAVERNS_FLOATING_BRIDGEV10_BRIDGERETRACT = 2234
    XELNAGA_CAVERNS_FLOATING_BRIDGEH12OUT_BRIDGEEXTEND = 2236
    XELNAGA_CAVERNS_FLOATING_BRIDGEH12_BRIDGERETRACT = 2238
    XELNAGA_CAVERNS_FLOATING_BRIDGEV12OUT_BRIDGEEXTEND = 2240
    XELNAGA_CAVERNS_FLOATING_BRIDGEV12_BRIDGERETRACT = 2242
    EFFECT_TIMEWARP = 2244
    SNOWREFINERY_TERRAN_EXTENDINGBRIDGENESHORT8OUT_BRIDGEEXTEND = 2246
    SNOWREFINERY_TERRAN_EXTENDINGBRIDGENESHORT8_BRIDGERETRACT = 2248
    SNOWREFINERY_TERRAN_EXTENDINGBRIDGENWSHORT8OUT_BRIDGEEXTEND = 2250
    SNOWREFINERY_TERRAN_EXTENDINGBRIDGENWSHORT8_BRIDGERETRACT = 2252
    SNOWREFINERY_TERRAN_EXTENDINGBRIDGENESHORT10OUT_BRIDGEEXTEND = 2254
    SNOWREFINERY_TERRAN_EXTENDINGBRIDGENESHORT10_BRIDGERETRACT = 2256
    SNOWREFINERY_TERRAN_EXTENDINGBRIDGENWSHORT10OUT_BRIDGEEXTEND = 2258
    SNOWREFINERY_TERRAN_EXTENDINGBRIDGENWSHORT10_BRIDGERETRACT = 2260
    TARSONIS_DOORN_TARSONIS_DOORN = 2262
    TARSONIS_DOORNLOWERED_TARSONIS_DOORNLOWERED = 2264
    TARSONIS_DOORNE_TARSONIS_DOORNE = 2266
    TARSONIS_DOORNELOWERED_TARSONIS_DOORNELOWERED = 2268
    TARSONIS_DOORE_TARSONIS_DOORE = 2270
    TARSONIS_DOORELOWERED_TARSONIS_DOORELOWERED = 2272
    TARSONIS_DOORNW_TARSONIS_DOORNW = 2274
    TARSONIS_DOORNWLOWERED_TARSONIS_DOORNWLOWERED = 2276
    COMPOUNDMANSION_DOORN_COMPOUNDMANSION_DOORN = 2278
    COMPOUNDMANSION_DOORNLOWERED_COMPOUNDMANSION_DOORNLOWERED = 2280
    COMPOUNDMANSION_DOORNE_COMPOUNDMANSION_DOORNE = 2282
    COMPOUNDMANSION_DOORNELOWERED_COMPOUNDMANSION_DOORNELOWERED = 2284
    COMPOUNDMANSION_DOORE_COMPOUNDMANSION_DOORE = 2286
    COMPOUNDMANSION_DOORELOWERED_COMPOUNDMANSION_DOORELOWERED = 2288
    COMPOUNDMANSION_DOORNW_COMPOUNDMANSION_DOORNW = 2290
    COMPOUNDMANSION_DOORNWLOWERED_COMPOUNDMANSION_DOORNWLOWERED = 2292
    ARMORYRESEARCHSWARM_TERRANVEHICLEANDSHIPWEAPONSLEVEL1 = 2294
    ARMORYRESEARCHSWARM_TERRANVEHICLEANDSHIPWEAPONSLEVEL2 = 2295
    ARMORYRESEARCHSWARM_TERRANVEHICLEANDSHIPWEAPONSLEVEL3 = 2296
    ARMORYRESEARCHSWARM_TERRANVEHICLEANDSHIPPLATINGLEVEL1 = 2297
    ARMORYRESEARCHSWARM_TERRANVEHICLEANDSHIPPLATINGLEVEL2 = 2298
    ARMORYRESEARCHSWARM_TERRANVEHICLEANDSHIPPLATINGLEVEL3 = 2299
    CAUSTICSPRAY_CAUSTICSPRAY = 2324
    ORACLECLOAKINGFIELDTARGETED_ORACLECLOAKINGFIELDTARGETED = 2326
    EFFECT_IMMORTALBARRIER = 2328
    MORPHTORAVAGER_RAVAGER = 2330
    CANCEL_MORPHRAVAGER = 2331
    MORPH_LURKER = 2332
    CANCEL_MORPHLURKER = 2333
    ORACLEPHASESHIFT_ORACLEPHASESHIFT = 2334
    RELEASEINTERCEPTORS_RELEASEINTERCEPTORS = 2336
    EFFECT_CORROSIVEBILE = 2338
    BURROWDOWN_RAVAGER = 2340
    BURROWRAVAGERDOWN_CANCEL = 2341
    BURROWUP_RAVAGER = 2342
    PURIFICATIONNOVA_PURIFICATIONNOVA = 2344
    EFFECT_PURIFICATIONNOVA = 2346
    IMPALE_IMPALE = 2348
    LOCKON_LOCKON = 2350
    LOCKONAIR_LOCKONAIR = 2352
    CANCEL_LOCKON = 2354
    CORRUPTIONBOMB_CORRUPTIONBOMB = 2356
    CORRUPTIONBOMB_CANCEL = 2357
    EFFECT_TACTICALJUMP = 2358
    OVERCHARGE_OVERCHARGE = 2360
    MORPH_THORHIGHIMPACTMODE = 2362
    THORAPMODE_CANCEL = 2363
    MORPH_THOREXPLOSIVEMODE = 2364
    CANCEL_MORPHTHOREXPLOSIVEMODE = 2365
    LIGHTOFAIUR_LIGHTOFAIUR = 2366
    EFFECT_MASSRECALL_MOTHERSHIP = 2368
    LOAD_NYDUSWORM = 2370
    UNLOADALL_NYDUSWORM = 2371
    BEHAVIOR_PULSARBEAMON = 2375
    BEHAVIOR_PULSARBEAMOFF = 2376
    PULSARBEAM_RIPFIELD = 2377
    PULSARCANNON_PULSARCANNON = 2379
    VOIDSWARMHOSTSPAWNLOCUST_VOIDSWARMHOSTSPAWNLOCUST = 2381
    LOCUSTMPFLYINGMORPHTOGROUND_LOCUSTMPFLYINGSWOOP = 2383
    LOCUSTMPMORPHTOAIR_LOCUSTMPFLYINGSWOOP = 2385
    EFFECT_LOCUSTSWOOP = 2387
    HALLUCINATION_DISRUPTOR = 2389
    HALLUCINATION_ADEPT = 2391
    EFFECT_VOIDRAYPRISMATICALIGNMENT = 2393
    SEEKERDUMMYCHANNEL_SEEKERDUMMYCHANNEL = 2395
    AIURLIGHTBRIDGENE8OUT_BRIDGEEXTEND = 2397
    AIURLIGHTBRIDGENE8_BRIDGERETRACT = 2399
    AIURLIGHTBRIDGENE10OUT_BRIDGEEXTEND = 2401
    AIURLIGHTBRIDGENE10_BRIDGERETRACT = 2403
    AIURLIGHTBRIDGENE12OUT_BRIDGEEXTEND = 2405
    AIURLIGHTBRIDGENE12_BRIDGERETRACT = 2407
    AIURLIGHTBRIDGENW8OUT_BRIDGEEXTEND = 2409
    AIURLIGHTBRIDGENW8_BRIDGERETRACT = 2411
    AIURLIGHTBRIDGENW10OUT_BRIDGEEXTEND = 2413
    AIURLIGHTBRIDGENW10_BRIDGERETRACT = 2415
    AIURLIGHTBRIDGENW12OUT_BRIDGEEXTEND = 2417
    AIURLIGHTBRIDGENW12_BRIDGERETRACT = 2419
    AIURTEMPLEBRIDGENE8OUT_BRIDGEEXTEND = 2421
    AIURTEMPLEBRIDGENE8_BRIDGERETRACT = 2423
    AIURTEMPLEBRIDGENE10OUT_BRIDGEEXTEND = 2425
    AIURTEMPLEBRIDGENE10_BRIDGERETRACT = 2427
    AIURTEMPLEBRIDGENE12OUT_BRIDGEEXTEND = 2429
    AIURTEMPLEBRIDGENE12_BRIDGERETRACT = 2431
    AIURTEMPLEBRIDGENW8OUT_BRIDGEEXTEND = 2433
    AIURTEMPLEBRIDGENW8_BRIDGERETRACT = 2435
    AIURTEMPLEBRIDGENW10OUT_BRIDGEEXTEND = 2437
    AIURTEMPLEBRIDGENW10_BRIDGERETRACT = 2439
    AIURTEMPLEBRIDGENW12OUT_BRIDGEEXTEND = 2441
    AIURTEMPLEBRIDGENW12_BRIDGERETRACT = 2443
    SHAKURASLIGHTBRIDGENE8OUT_BRIDGEEXTEND = 2445
    SHAKURASLIGHTBRIDGENE8_BRIDGERETRACT = 2447
    SHAKURASLIGHTBRIDGENE10OUT_BRIDGEEXTEND = 2449
    SHAKURASLIGHTBRIDGENE10_BRIDGERETRACT = 2451
    SHAKURASLIGHTBRIDGENE12OUT_BRIDGEEXTEND = 2453
    SHAKURASLIGHTBRIDGENE12_BRIDGERETRACT = 2455
    SHAKURASLIGHTBRIDGENW8OUT_BRIDGEEXTEND = 2457
    SHAKURASLIGHTBRIDGENW8_BRIDGERETRACT = 2459
    SHAKURASLIGHTBRIDGENW10OUT_BRIDGEEXTEND = 2461
    SHAKURASLIGHTBRIDGENW10_BRIDGERETRACT = 2463
    SHAKURASLIGHTBRIDGENW12OUT_BRIDGEEXTEND = 2465
    SHAKURASLIGHTBRIDGENW12_BRIDGERETRACT = 2467
    VOIDMPIMMORTALREVIVEREBUILD_IMMORTAL = 2469
    VOIDMPIMMORTALREVIVEDEATH_IMMORTAL = 2471
    ARBITERMPSTASISFIELD_ARBITERMPSTASISFIELD = 2473
    ARBITERMPRECALL_ARBITERMPRECALL = 2475
    CORSAIRMPDISRUPTIONWEB_CORSAIRMPDISRUPTIONWEB = 2477
    MORPHTOGUARDIANMP_MORPHTOGUARDIANMP = 2479
    MORPHTOGUARDIANMP_CANCEL = 2480
    MORPHTODEVOURERMP_MORPHTODEVOURERMP = 2481
    MORPHTODEVOURERMP_CANCEL = 2482
    DEFILERMPCONSUME_DEFILERMPCONSUME = 2483
    DEFILERMPDARKSWARM_DEFILERMPDARKSWARM = 2485
    DEFILERMPPLAGUE_DEFILERMPPLAGUE = 2487
    DEFILERMPBURROW_BURROWDOWN = 2489
    DEFILERMPBURROW_CANCEL = 2490
    DEFILERMPUNBURROW_BURROWUP = 2491
    QUEENMPENSNARE_QUEENMPENSNARE = 2493
    QUEENMPSPAWNBROODLINGS_QUEENMPSPAWNBROODLINGS = 2495
    QUEENMPINFESTCOMMANDCENTER_QUEENMPINFESTCOMMANDCENTER = 2497
    LIGHTNINGBOMB_LIGHTNINGBOMB = 2499
    GRAPPLE_GRAPPLE = 2501
    ORACLESTASISTRAP_ORACLEBUILDSTASISTRAP = 2503
    BUILD_STASISTRAP = 2505
    CANCEL_STASISTRAP = 2535
    ORACLESTASISTRAPACTIVATE_ACTIVATESTASISWARD = 2536
    SELFREPAIR_SELFREPAIR = 2538
    SELFREPAIR_CANCEL = 2539
    AGGRESSIVEMUTATION_AGGRESSIVEMUTATION = 2540
    PARASITICBOMB_PARASITICBOMB = 2542
    ADEPTPHASESHIFT_ADEPTPHASESHIFT = 2544
    PURIFICATIONNOVAMORPH_PURIFICATIONNOVA = 2546
    PURIFICATIONNOVAMORPHBACK_PURIFICATIONNOVA = 2548
    BEHAVIOR_HOLDFIREON_LURKER = 2550
    BEHAVIOR_HOLDFIREOFF_LURKER = 2552
    LIBERATORMORPHTOAG_LIBERATORAGMODE = 2554
    LIBERATORMORPHTOAA_LIBERATORAAMODE = 2556
    MORPH_LIBERATORAGMODE = 2558
    MORPH_LIBERATORAAMODE = 2560
    TIMESTOP_TIMESTOP = 2562
    TIMESTOP_CANCEL = 2563
    AIURLIGHTBRIDGEABANDONEDNE8OUT_BRIDGEEXTEND = 2564
    AIURLIGHTBRIDGEABANDONEDNE8_BRIDGERETRACT = 2566
    AIURLIGHTBRIDGEABANDONEDNE10OUT_BRIDGEEXTEND = 2568
    AIURLIGHTBRIDGEABANDONEDNE10_BRIDGERETRACT = 2570
    AIURLIGHTBRIDGEABANDONEDNE12OUT_BRIDGEEXTEND = 2572
    AIURLIGHTBRIDGEABANDONEDNE12_BRIDGERETRACT = 2574
    AIURLIGHTBRIDGEABANDONEDNW8OUT_BRIDGEEXTEND = 2576
    AIURLIGHTBRIDGEABANDONEDNW8_BRIDGERETRACT = 2578
    AIURLIGHTBRIDGEABANDONEDNW10OUT_BRIDGEEXTEND = 2580
    AIURLIGHTBRIDGEABANDONEDNW10_BRIDGERETRACT = 2582
    AIURLIGHTBRIDGEABANDONEDNW12OUT_BRIDGEEXTEND = 2584
    AIURLIGHTBRIDGEABANDONEDNW12_BRIDGERETRACT = 2586
    KD8CHARGE_KD8CHARGE = 2588
    PENETRATINGSHOT_PENETRATINGSHOT = 2590
    CLOAKINGDRONE_CLOAKINGDRONE = 2592
    CANCEL_ADEPTPHASESHIFT = 2594
    CANCEL_ADEPTSHADEPHASESHIFT = 2596
    SLAYNELEMENTALGRAB_SLAYNELEMENTALGRAB = 2598
    MORPHTOCOLLAPSIBLEPURIFIERTOWERDEBRIS_MORPHTOCOLLAPSIBLEPURIFIERTOWERDEBRIS = 2600
    MORPHTOCOLLAPSIBLEPURIFIERTOWERDEBRIS_CANCEL = 2601
    PORTCITY_BRIDGE_UNITNE8OUT_BRIDGEEXTEND = 2602
    PORTCITY_BRIDGE_UNITNE8_BRIDGERETRACT = 2604
    PORTCITY_BRIDGE_UNITSE8OUT_BRIDGEEXTEND = 2606
    PORTCITY_BRIDGE_UNITSE8_BRIDGERETRACT = 2608
    PORTCITY_BRIDGE_UNITNW8OUT_BRIDGEEXTEND = 2610
    PORTCITY_BRIDGE_UNITNW8_BRIDGERETRACT = 2612
    PORTCITY_BRIDGE_UNITSW8OUT_BRIDGEEXTEND = 2614
    PORTCITY_BRIDGE_UNITSW8_BRIDGERETRACT = 2616
    PORTCITY_BRIDGE_UNITNE10OUT_BRIDGEEXTEND = 2618
    PORTCITY_BRIDGE_UNITNE10_BRIDGERETRACT = 2620
    PORTCITY_BRIDGE_UNITSE10OUT_BRIDGEEXTEND = 2622
    PORTCITY_BRIDGE_UNITSE10_BRIDGERETRACT = 2624
    PORTCITY_BRIDGE_UNITNW10OUT_BRIDGEEXTEND = 2626
    PORTCITY_BRIDGE_UNITNW10_BRIDGERETRACT = 2628
    PORTCITY_BRIDGE_UNITSW10OUT_BRIDGEEXTEND = 2630
    PORTCITY_BRIDGE_UNITSW10_BRIDGERETRACT = 2632
    PORTCITY_BRIDGE_UNITNE12OUT_BRIDGEEXTEND = 2634
    PORTCITY_BRIDGE_UNITNE12_BRIDGERETRACT = 2636
    PORTCITY_BRIDGE_UNITSE12OUT_BRIDGEEXTEND = 2638
    PORTCITY_BRIDGE_UNITSE12_BRIDGERETRACT = 2640
    PORTCITY_BRIDGE_UNITNW12OUT_BRIDGEEXTEND = 2642
    PORTCITY_BRIDGE_UNITNW12_BRIDGERETRACT = 2644
    PORTCITY_BRIDGE_UNITSW12OUT_BRIDGEEXTEND = 2646
    PORTCITY_BRIDGE_UNITSW12_BRIDGERETRACT = 2648
    PORTCITY_BRIDGE_UNITN8OUT_BRIDGEEXTEND = 2650
    PORTCITY_BRIDGE_UNITN8_BRIDGERETRACT = 2652
    PORTCITY_BRIDGE_UNITS8OUT_BRIDGEEXTEND = 2654
    PORTCITY_BRIDGE_UNITS8_BRIDGERETRACT = 2656
    PORTCITY_BRIDGE_UNITE8OUT_BRIDGEEXTEND = 2658
    PORTCITY_BRIDGE_UNITE8_BRIDGERETRACT = 2660
    PORTCITY_BRIDGE_UNITW8OUT_BRIDGEEXTEND = 2662
    PORTCITY_BRIDGE_UNITW8_BRIDGERETRACT = 2664
    PORTCITY_BRIDGE_UNITN10OUT_BRIDGEEXTEND = 2666
    PORTCITY_BRIDGE_UNITN10_BRIDGERETRACT = 2668
    PORTCITY_BRIDGE_UNITS10OUT_BRIDGEEXTEND = 2670
    PORTCITY_BRIDGE_UNITS10_BRIDGERETRACT = 2672
    PORTCITY_BRIDGE_UNITE10OUT_BRIDGEEXTEND = 2674
    PORTCITY_BRIDGE_UNITE10_BRIDGERETRACT = 2676
    PORTCITY_BRIDGE_UNITW10OUT_BRIDGEEXTEND = 2678
    PORTCITY_BRIDGE_UNITW10_BRIDGERETRACT = 2680
    PORTCITY_BRIDGE_UNITN12OUT_BRIDGEEXTEND = 2682
    PORTCITY_BRIDGE_UNITN12_BRIDGERETRACT = 2684
    PORTCITY_BRIDGE_UNITS12OUT_BRIDGEEXTEND = 2686
    PORTCITY_BRIDGE_UNITS12_BRIDGERETRACT = 2688
    PORTCITY_BRIDGE_UNITE12OUT_BRIDGEEXTEND = 2690
    PORTCITY_BRIDGE_UNITE12_BRIDGERETRACT = 2692
    PORTCITY_BRIDGE_UNITW12OUT_BRIDGEEXTEND = 2694
    PORTCITY_BRIDGE_UNITW12_BRIDGERETRACT = 2696
    TEMPESTDISRUPTIONBLAST_TEMPESTDISRUPTIONBLAST = 2698
    CANCEL_TEMPESTDISRUPTIONBLAST = 2699
    EFFECT_SHADOWSTRIDE = 2700
    LAUNCHINTERCEPTORS_LAUNCHINTERCEPTORS = 2702
    EFFECT_SPAWNLOCUSTS = 2704
    LOCUSTMPFLYINGSWOOPATTACK_LOCUSTMPFLYINGSWOOP = 2706
    MORPH_OVERLORDTRANSPORT = 2708
    CANCEL_MORPHOVERLORDTRANSPORT = 2709
    BYPASSARMOR_BYPASSARMOR = 2710
    BYPASSARMORDRONECU_BYPASSARMORDRONECU = 2712
    EFFECT_GHOSTSNIPE = 2714
    CHANNELSNIPE_CANCEL = 2715
    PURIFYMORPHPYLON_MOTHERSHIPCOREWEAPON = 2716
    PURIFYMORPHPYLONBACK_MOTHERSHIPCOREWEAPON = 2718
    RESEARCH_SHADOWSTRIKE = 2720
    HEAL_MEDICHEAL = 2750
    LURKERASPECT_LURKER = 2752
    LURKERASPECT_CANCEL = 2753
    BURROWLURKERDOWN_BURROWDOWN = 2754
    BURROWLURKERDOWN_CANCEL = 2755
    BURROWLURKERUP_BURROWUP = 2756
    D8CHARGE_D8CHARGE = 2758
    DEFENSIVEMATRIX_DEFENSIVEMATRIX = 2760
    MISSILEPODS_MISSILEPODS = 2762
    LOKIMISSILEPODS_MISSILEPODS = 2764
    HUTTRANSPORT_HUTLOAD = 2766
    HUTTRANSPORT_HUTUNLOADALL = 2767
    MORPHTOTECHREACTOR_MORPHTOTECHREACTOR = 2771
    LEVIATHANSPAWNBROODLORD_SPAWNBROODLORD = 2773
    SS_CARRIERBOSSATTACKLAUNCH_SS_SHOOTING = 2775
    SS_CARRIERSPAWNINTERCEPTOR_SS_CARRIERSPAWNINTERCEPTOR = 2777
    SS_CARRIERBOSSATTACKTARGET_SS_SHOOTING = 2779
    SS_FIGHTERBOMB_SS_FIGHTERBOMB = 2781
    SS_LIGHTNINGPROJECTORTOGGLE_SS_LIGHTNINGPROJECTORTOGGLE = 2783
    SS_PHOENIXSHOOTING_SS_SHOOTING = 2785
    SS_POWERUPMORPHTOBOMB_SS_POWERUPMORPHTOBOMB = 2787
    SS_BATTLECRUISERMISSILEATTACK_SS_SHOOTING = 2789
    SS_LEVIATHANSPAWNBOMBS_SS_LEVIATHANSPAWNBOMBS = 2791
    SS_BATTLECRUISERHUNTERSEEKERATTACK_SS_SHOOTING = 2793
    SS_POWERUPMORPHTOHEALTH_SS_POWERUPMORPHTOHEALTH = 2795
    SS_LEVIATHANTENTACLEATTACKL1NODELAY_SS_LEVIATHANTENTACLEATTACKL1NODELAY = 2797
    SS_LEVIATHANTENTACLEATTACKL2NODELAY_SS_LEVIATHANTENTACLEATTACKL2NODELAY = 2799
    SS_LEVIATHANTENTACLEATTACKR1NODELAY_SS_LEVIATHANTENTACLEATTACKR1NODELAY = 2801
    SS_LEVIATHANTENTACLEATTACKR2NODELAY_SS_LEVIATHANTENTACLEATTACKR2NODELAY = 2803
    SS_SCIENCEVESSELTELEPORT_ZERATULBLINK = 2805
    SS_TERRATRONBEAMATTACK_SS_TERRATRONBEAMATTACK = 2807
    SS_TERRATRONSAWATTACK_SS_TERRATRONSAWATTACK = 2809
    SS_WRAITHATTACK_SS_SHOOTING = 2811
    SS_SWARMGUARDIANATTACK_SS_SHOOTING = 2813
    SS_POWERUPMORPHTOSIDEMISSILES_SS_POWERUPMORPHTOSIDEMISSILES = 2815
    SS_POWERUPMORPHTOSTRONGERMISSILES_SS_POWERUPMORPHTOSTRONGERMISSILES = 2817
    SS_SCOUTATTACK_SS_SHOOTING = 2819
    SS_INTERCEPTORATTACK_SS_SHOOTING = 2821
    SS_CORRUPTORATTACK_SS_SHOOTING = 2823
    SS_LEVIATHANTENTACLEATTACKL2_SS_LEVIATHANTENTACLEATTACKL2 = 2825
    SS_LEVIATHANTENTACLEATTACKR1_SS_LEVIATHANTENTACLEATTACKR1 = 2827
    SS_LEVIATHANTENTACLEATTACKL1_SS_LEVIATHANTENTACLEATTACKL1 = 2829
    SS_LEVIATHANTENTACLEATTACKR2_SS_LEVIATHANTENTACLEATTACKR2 = 2831
    SS_SCIENCEVESSELATTACK_SS_SHOOTING = 2833
    HEALREDIRECT_HEALREDIRECT = 2835
    LURKERASPECTFROMHYDRALISKBURROWED_LURKERFROMHYDRALISKBURROWED = 2836
    LURKERASPECTFROMHYDRALISKBURROWED_CANCEL = 2837
    UPGRADETOLURKERDEN_LURKERDEN = 2838
    UPGRADETOLURKERDEN_CANCEL = 2839
    ADVANCEDCONSTRUCTION_CANCEL = 2840
    BUILDINPROGRESSNONCANCELLABLE_CANCEL = 2842
    INFESTEDVENTSPAWNCORRUPTOR_SPAWNCORRUPTOR = 2844
    INFESTEDVENTSPAWNBROODLORD_SPAWNBROODLORD = 2846
    IRRADIATE_IRRADIATE = 2848
    IRRADIATE_CANCEL = 2849
    INFESTEDVENTSPAWNMUTALISK_LEVIATHANSPAWNMUTALISK = 2850
    MAKEVULTURESPIDERMINES_SPIDERMINEREPLENISH = 2852
    MEDIVACDOUBLEBEAMHEAL_HEAL = 2872
    MINDCONTROL_MINDCONTROL = 2874
    OBLITERATE_OBLITERATE = 2876
    VOODOOSHIELD_VOODOOSHIELD = 2878
    RELEASEMINION_RELEASEMINION = 2880
    ULTRASONICPULSE_ULTRASONICPULSE = 2882
    ARCHIVESEAL_ARCHIVESEAL = 2884
    ARTANISVORTEX_VORTEX = 2886
    ARTANISWORMHOLETRANSIT_WORMHOLETRANSIT = 2888
    BUNKERATTACK_BUNKERATTACK = 2890
    BUNKERATTACK_ATTACKTOWARDS = 2891
    BUNKERATTACK_ATTACKBARRAGE = 2892
    BUNKERSTOP_STOPBUNKER = 2893
    BUNKERSTOP_HOLDFIRESPECIAL = 2894
    CANCELTERRAZINEHARVEST_CANCEL = 2899
    LEVIATHANSPAWNMUTALISK_LEVIATHANSPAWNMUTALISK = 2901
    PARKCOLONISTVEHICLE_PARKCOLONISTVEHICLE = 2903
    STARTCOLONISTVEHICLE_STARTCOLONISTVEHICLE = 2905
    CONSUMPTION_CONSUMPTION = 2907
    CONSUMEDNA_CONSUMEDNA = 2909
    EGGPOP_EGGPOP = 2911
    EXPERIMENTALPLASMAGUN_EXPERIMENTALPLASMAGUN = 2913
    GATHERSPECIALOBJECT_GATHERSPECIALOBJECT = 2915
    KERRIGANSEARCH_KERRIGANSEARCH = 2917
    LOKIUNDOCK_LIFT = 2919
    MINDBLAST_MINDBLAST = 2921
    MORPHTOINFESTEDCIVILIAN_MORPHTOINFESTEDCIVILIAN = 2923
    QUEENSHOCKWAVE_QUEENSHOCKWAVE = 2925
    TAURENOUTHOUSELIFTOFF_TAURENOUTHOUSEFLY = 2927
    TAURENOUTHOUSETRANSPORT_LOADTAURENOUTHOUSE = 2929
    TAURENOUTHOUSETRANSPORT_UNLOADTAURENOUTHOUSE = 2930
    TYCHUS03OMEGASTORM_OMEGASTORM = 2934
    RAYNORSNIPE_RAYNORSNIPE = 2936
    BONESHEAL_BONESHEAL = 2938
    BONESTOSSGRENADE_TOSSGRENADETYCHUS = 2940
    HERCULESTRANSPORT_MEDIVACLOAD = 2942
    HERCULESTRANSPORT_MEDIVACUNLOADALL = 2944
    SPECOPSDROPSHIPTRANSPORT_MEDIVACLOAD = 2947
    SPECOPSDROPSHIPTRANSPORT_MEDIVACUNLOADALL = 2949
    DUSKWINGBANSHEECLOAKINGFIELD_CLOAKONBANSHEE = 2952
    DUSKWINGBANSHEECLOAKINGFIELD_CLOAKOFF = 2953
    HYPERIONYAMATOSPECIAL_HYPERIONYAMATOGUN = 2954
    INFESTABLEHUTTRANSPORT_HUTLOAD = 2956
    INFESTABLEHUTTRANSPORT_HUTUNLOADALL = 2957
    DUTCHPLACETURRET_DUTCHPLACETURRET = 2961
    BURROWINFESTEDCIVILIANDOWN_BURROWDOWN = 2963
    BURROWINFESTEDCIVILIANUP_BURROWUP = 2965
    SELENDISHANGAR_INTERCEPTOR = 2967
    FORCEFIELDBEAM_FORCEFIELDBEAM = 2987
    SIEGEBREAKERSIEGE_SIEGEMODE = 2989
    SIEGEBREAKERUNSIEGE_UNSIEGE = 2991
    SOULCHANNEL_SOULCHANNEL = 2993
    SOULCHANNEL_CANCEL = 2994
    PERDITIONTURRETBURROW_PERDITIONTURRETBURROW = 2995
    PERDITIONTURRETUNBURROW_PERDITIONTURRETUNBURROW = 2997
    SENTRYGUNBURROW_BURROWTURRET = 2999
    SENTRYGUNUNBURROW_UNBURROWTURRET = 3001
    SPIDERMINEUNBURROWRANGEDUMMY_SPIDERMINEUNBURROWRANGEDUMMY = 3003
    GRAVITONPRISON_GRAVITONPRISON = 3005
    IMPLOSION_IMPLOSION = 3007
    OMEGASTORM_OMEGASTORM = 3009
    PSIONICSHOCKWAVE_PSIONICSHOCKWAVE = 3011
    HYBRIDFAOESTUN_HYBRIDFAOESTUN = 3013
    SUMMONMERCENARIES_HIREKELMORIANMINERS = 3015
    SUMMONMERCENARIES_HIREDEVILDOGS = 3016
    SUMMONMERCENARIES_HIRESPARTANCOMPANY = 3017
    SUMMONMERCENARIES_HIREHAMMERSECURITIES = 3018
    SUMMONMERCENARIES_HIRESIEGEBREAKERS = 3019
    SUMMONMERCENARIES_HIREHELSANGELS = 3020
    SUMMONMERCENARIES_HIREDUSKWING = 3021
    SUMMONMERCENARIES_HIREDUKESREVENGE = 3022
    SUMMONMERCENARIESPH_HIREKELMORIANMINERSPH = 3045
    ENERGYNOVA_ENERGYNOVA = 3075
    THEMOROSDEVICE_THEMOROSDEVICE = 3077
    TOSSGRENADE_TOSSGRENADE = 3079
    VOIDSEEKERTRANSPORT_MEDIVACLOAD = 3081
    VOIDSEEKERTRANSPORT_MEDIVACUNLOADALL = 3083
    TERRANBUILDDROP_SUPPLYDEPOTDROP = 3086
    TERRANBUILDDROP_CANCEL = 3116
    ODINNUCLEARSTRIKE_ODINNUKECALLDOWN = 3117
    ODINNUCLEARSTRIKE_CANCEL = 3118
    ODINWRECKAGE_ODIN = 3119
    RESEARCHLABTRANSPORT_HUTLOAD = 3121
    RESEARCHLABTRANSPORT_HUTUNLOADALL = 3122
    COLONYSHIPTRANSPORT_MEDIVACLOAD = 3126
    COLONYSHIPTRANSPORT_MEDIVACUNLOADALL = 3128
    COLONYINFESTATION_COLONYINFESTATION = 3131
    DOMINATION_DOMINATION = 3133
    DOMINATION_CANCEL = 3134
    KARASSPLASMASURGE_KARASSPLASMASURGE = 3135
    KARASSPSISTORM_PSISTORM = 3137
    HYBRIDBLINK_ZERATULBLINK = 3139
    HYBRIDCPLASMABLAST_HYBRIDCPLASMABLAST = 3141
    HEROARMNUKE_NUKEARM = 3143
    HERONUCLEARSTRIKE_NUKECALLDOWN = 3163
    HERONUCLEARSTRIKE_CANCEL = 3164
    ODINBARRAGE_ODINBARRAGE = 3165
    ODINBARRAGE_CANCEL = 3166
    PURIFIERTOGGLEPOWER_PURIFIERPOWERDOWN = 3167
    PURIFIERTOGGLEPOWER_PURIFIERPOWERUP = 3168
    PHASEMINEBLAST_PHASEMINEBLAST = 3169
    VOIDSEEKERPHASEMINEBLAST_PHASEMINEBLAST = 3171
    TRANSPORTTRUCKTRANSPORT_TRANSPORTTRUCKLOAD = 3173
    TRANSPORTTRUCKTRANSPORT_TRANSPORTTRUCKUNLOADALL = 3174
    VAL03QUEENOFBLADESBURROW_BURROWDOWN = 3178
    VAL03QUEENOFBLADESDEEPTUNNEL_DEEPTUNNEL = 3180
    VAL03QUEENOFBLADESUNBURROW_BURROWUP = 3182
    VULTURESPIDERMINEBURROW_VULTURESPIDERMINEBURROW = 3184
    VULTURESPIDERMINEUNBURROW_VULTURESPIDERMINEUNBURROW = 3186
    LOKIYAMATO_LOKIYAMATOGUN = 3188
    DUKESREVENGEYAMATO_YAMATOGUN = 3190
    ZERATULBLINK_ZERATULBLINK = 3192
    ROGUEGHOSTCLOAK_CLOAKONSPECTRE = 3194
    ROGUEGHOSTCLOAK_CLOAKOFF = 3195
    VULTURESPIDERMINES_SPIDERMINE = 3196
    VULTUREQUEUE3_CANCEL = 3198
    VULTUREQUEUE3_CANCELSLOT = 3199
    SUPERWARPGATETRAIN_ZEALOT = 3200
    SUPERWARPGATETRAIN_STALKER = 3201
    SUPERWARPGATETRAIN_IMMORTAL = 3202
    SUPERWARPGATETRAIN_HIGHTEMPLAR = 3203
    SUPERWARPGATETRAIN_DARKTEMPLAR = 3204
    SUPERWARPGATETRAIN_SENTRY = 3205
    SUPERWARPGATETRAIN_CARRIER = 3206
    SUPERWARPGATETRAIN_PHOENIX = 3207
    SUPERWARPGATETRAIN_VOIDRAY = 3208
    SUPERWARPGATETRAIN_ARCHON = 3209
    SUPERWARPGATETRAIN_WARPINZERATUL = 3210
    SUPERWARPGATETRAIN_WARPINURUN = 3211
    SUPERWARPGATETRAIN_WARPINMOHANDAR = 3212
    SUPERWARPGATETRAIN_WARPINSELENDIS = 3213
    SUPERWARPGATETRAIN_WARPINSCOUT = 3214
    SUPERWARPGATETRAIN_COLOSSUS = 3215
    SUPERWARPGATETRAIN_WARPPRISM = 3216
    BURROWOMEGALISKDOWN_BURROWDOWN = 3220
    BURROWOMEGALISKUP_BURROWUP = 3222
    BURROWINFESTEDABOMINATIONDOWN_BURROWDOWN = 3224
    BURROWINFESTEDABOMINATIONUP_BURROWUP = 3226
    BURROWHUNTERKILLERDOWN_BURROWDOWN = 3228
    BURROWHUNTERKILLERDOWN_CANCEL = 3229
    BURROWHUNTERKILLERUP_BURROWUP = 3230
    NOVASNIPE_NOVASNIPE = 3232
    VORTEXPURIFIER_VORTEX = 3234
    TALDARIMVORTEX_VORTEX = 3236
    PURIFIERPLANETCRACKER_PLANETCRACKER = 3238
    BURROWINFESTEDTERRANCAMPAIGNDOWN_BURROWDOWN = 3240
    BURROWINFESTEDTERRANCAMPAIGNUP_BURROWUP = 3242
    INFESTEDMONSTERTRAIN_INFESTEDCIVILIAN = 3244
    INFESTEDMONSTERTRAIN_INFESTEDTERRANCAMPAIGN = 3245
    INFESTEDMONSTERTRAIN_INFESTEDABOMINATION = 3246
    BIODOMETRANSPORT_BIODOMELOAD = 3274
    BIODOMETRANSPORT_BIODOMEUNLOADALL = 3275
    CHECKSTATION_CHECKSTATION = 3279
    CHECKSTATIONDIAGONALBLUR_CHECKSTATIONDIAGONALBLUR = 3281
    CHECKSTATIONDIAGONALULBR_CHECKSTATIONDIAGONALULBR = 3283
    CHECKSTATIONVERTICAL_CHECKSTATIONVERTICAL = 3285
    CHECKSTATIONOPENED_CHECKSTATIONOPENED = 3287
    CHECKSTATIONDIAGONALBLUROPENED_CHECKSTATIONDIAGONALBLUROPENED = 3289
    CHECKSTATIONDIAGONALULBROPENED_CHECKSTATIONDIAGONALULBROPENED = 3291
    CHECKSTATIONVERTICALOPENED_CHECKSTATIONVERTICALOPENED = 3293
    ATTACKALLOWSINVULNERABLE_ATTACKALLOWSINVULNERABLE = 3295
    ATTACKALLOWSINVULNERABLE_ATTACKTOWARDS = 3296
    ATTACKALLOWSINVULNERABLE_ATTACKBARRAGE = 3297
    ZERATULSTUN_ZERATULSTUN = 3298
    WRAITHCLOAK_WRAITHCLOAK = 3300
    WRAITHCLOAK_CLOAKOFF = 3301
    TECHREACTORMORPH_TECHREACTORMORPH = 3302
    BARRACKSTECHREACTORMORPH_TECHLABBARRACKS = 3304
    FACTORYTECHREACTORMORPH_TECHLABFACTORY = 3306
    STARPORTTECHREACTORMORPH_TECHLABSTARPORT = 3308
    SS_FIGHTERSHOOTING_SS_SHOOTING = 3310
    RAYNORC4_PLANTC4CHARGE = 3312
    DUKESREVENGEDEFENSIVEMATRIX_DEFENSIVEMATRIX = 3314
    DUKESREVENGEMISSILEPODS_MISSILEPODS = 3316
    THORWRECKAGE_THOR = 3318
    _330MMBARRAGECANNONS_330MMBARRAGECANNONS = 3320
    _330MMBARRAGECANNONS_CANCEL = 3321
    THORREBORN_THOR = 3322
    THORREBORN_CANCEL = 3323
    SPECTRENUKE_SPECTRENUKECALLDOWN = 3324
    SPECTRENUKE_CANCEL = 3325
    SPECTRENUKESILOARMMAGAZINE_SPECTRENUKESILOARMMAGAZINE = 3326
    SPECTRENUKESILOARMMAGAZINE_SPECTRENUKEARM = 3327
    COLONISTSHIPLIFTOFF_LIFT = 3346
    COLONISTSHIPLAND_LAND = 3348
    BIODOMECOMMANDLIFTOFF_LIFT = 3350
    BIODOMECOMMANDLAND_LAND = 3352
    HERCULESLIFTOFF_LIFT = 3354
    HERCULESLAND_HERCULESLAND = 3356
    LIGHTBRIDGEOFF_LIGHTBRIDGEOFF = 3358
    LIGHTBRIDGEON_LIGHTBRIDGEON = 3360
    LIBRARYDOWN_LIBRARYDOWN = 3362
    LIBRARYUP_LIBRARYUP = 3364
    TEMPLEDOORDOWN_TEMPLEDOORDOWN = 3366
    TEMPLEDOORUP_TEMPLEDOORUP = 3368
    TEMPLEDOORDOWNURDL_TEMPLEDOORDOWNURDL = 3370
    TEMPLEDOORUPURDL_TEMPLEDOORUPURDL = 3372
    PSYTROUSOXIDE_PSYTROUSOXIDEON = 3374
    PSYTROUSOXIDE_PSYTROUSOXIDEOFF = 3375
    VOIDSEEKERDOCK_VOIDSEEKERDOCK = 3376
    BIOPLASMIDDISCHARGE_BIOPLASMIDDISCHARGE = 3378
    WRECKINGCREWASSAULTMODE_ASSAULTMODE = 3380
    WRECKINGCREWFIGHTERMODE_FIGHTERMODE = 3382
    BIOSTASIS_BIOSTASIS = 3384
    COLONISTTRANSPORTTRANSPORT_COLONISTTRANSPORTLOAD = 3386
    COLONISTTRANSPORTTRANSPORT_COLONISTTRANSPORTUNLOADALL = 3387
    DROPTOSUPPLYDEPOT_RAISE = 3391
    REFINERYTOAUTOMATEDREFINERY_RAISE = 3393
    HELIOSCRASHMORPH_CRASHMORPH = 3395
    NANOREPAIR_HEAL = 3397
    PICKUP_PICKUP = 3399
    PICKUPARCADE_PICKUP = 3401
    PICKUPGAS100_PICKUPGAS100 = 3403
    PICKUPMINERALS100_PICKUPMINERALS100 = 3405
    PICKUPHEALTH25_PICKUPHEALTH25 = 3407
    PICKUPHEALTH50_PICKUPHEALTH50 = 3409
    PICKUPHEALTH100_PICKUPHEALTH100 = 3411
    PICKUPHEALTHFULL_PICKUPHEALTHFULL = 3413
    PICKUPENERGY25_PICKUPENERGY25 = 3415
    PICKUPENERGY50_PICKUPENERGY50 = 3417
    PICKUPENERGY100_PICKUPENERGY100 = 3419
    PICKUPENERGYFULL_PICKUPENERGYFULL = 3421
    TAURENSTIMPACK_STIM = 3423
    TESTINVENTORY_TESTINVENTORY = 3425
    TESTPAWN_TESTPAWN = 3434
    TESTREVIVE_SCV = 3454
    TESTSELL_TESTSELL = 3484
    TESTINTERACT_DESIGNATE = 3514
    CLIFFDOOROPEN0_SPACEPLATFORMDOOROPEN = 3515
    CLIFFDOORCLOSE0_SPACEPLATFORMDOORCLOSE = 3517
    CLIFFDOOROPEN1_SPACEPLATFORMDOOROPEN = 3519
    CLIFFDOORCLOSE1_SPACEPLATFORMDOORCLOSE = 3521
    DESTRUCTIBLEGATEDIAGONALBLURLOWERED_GATEOPEN = 3523
    DESTRUCTIBLEGATEDIAGONALULBRLOWERED_GATEOPEN = 3525
    DESTRUCTIBLEGATESTRAIGHTHORIZONTALBFLOWERED_GATEOPEN = 3527
    DESTRUCTIBLEGATESTRAIGHTHORIZONTALLOWERED_GATEOPEN = 3529
    DESTRUCTIBLEGATESTRAIGHTVERTICALLFLOWERED_GATEOPEN = 3531
    DESTRUCTIBLEGATESTRAIGHTVERTICALLOWERED_GATEOPEN = 3533
    DESTRUCTIBLEGATEDIAGONALBLUR_GATECLOSE = 3535
    DESTRUCTIBLEGATEDIAGONALULBR_GATECLOSE = 3537
    DESTRUCTIBLEGATESTRAIGHTHORIZONTALBF_GATECLOSE = 3539
    DESTRUCTIBLEGATESTRAIGHTHORIZONTAL_GATECLOSE = 3541
    DESTRUCTIBLEGATESTRAIGHTVERTICALLF_GATECLOSE = 3543
    DESTRUCTIBLEGATESTRAIGHTVERTICAL_GATECLOSE = 3545
    TESTLEARN_TESTLEARN = 3547
    TESTLEVELEDSPELL_YAMATOGUN = 3567
    METALGATEDIAGONALBLURLOWERED_GATEOPEN = 3569
    METALGATEDIAGONALULBRLOWERED_GATEOPEN = 3571
    METALGATESTRAIGHTHORIZONTALBFLOWERED_GATEOPEN = 3573
    METALGATESTRAIGHTHORIZONTALLOWERED_GATEOPEN = 3575
    METALGATESTRAIGHTVERTICALLFLOWERED_GATEOPEN = 3577
    METALGATESTRAIGHTVERTICALLOWERED_GATEOPEN = 3579
    METALGATEDIAGONALBLUR_GATECLOSE = 3581
    METALGATEDIAGONALULBR_GATECLOSE = 3583
    METALGATESTRAIGHTHORIZONTALBF_GATECLOSE = 3585
    METALGATESTRAIGHTHORIZONTAL_GATECLOSE = 3587
    METALGATESTRAIGHTVERTICALLF_GATECLOSE = 3589
    METALGATESTRAIGHTVERTICAL_GATECLOSE = 3591
    SECURITYGATEDIAGONALBLURLOWERED_GATEOPEN = 3593
    SECURITYGATEDIAGONALULBRLOWERED_GATEOPEN = 3595
    SECURITYGATESTRAIGHTHORIZONTALBFLOWERED_GATEOPEN = 3597
    SECURITYGATESTRAIGHTHORIZONTALLOWERED_GATEOPEN = 3599
    SECURITYGATESTRAIGHTVERTICALLFLOWERED_GATEOPEN = 3601
    SECURITYGATESTRAIGHTVERTICALLOWERED_GATEOPEN = 3603
    SECURITYGATEDIAGONALBLUR_GATECLOSE = 3605
    SECURITYGATEDIAGONALULBR_GATECLOSE = 3607
    SECURITYGATESTRAIGHTHORIZONTALBF_GATECLOSE = 3609
    SECURITYGATESTRAIGHTHORIZONTAL_GATECLOSE = 3611
    SECURITYGATESTRAIGHTVERTICALLF_GATECLOSE = 3613
    SECURITYGATESTRAIGHTVERTICAL_GATECLOSE = 3615
    CHANGESHRINETERRAN_CHANGESHRINETERRAN = 3617
    CHANGESHRINEPROTOSS_CHANGESHRINEPROTOSS = 3619
    SPECTREHOLDFIRE_SPECTREHOLDFIRE = 3621
    SPECTREWEAPONSFREE_WEAPONSFREE = 3623
    GWALEARN_TESTLEARN = 3625
    REAPERPLACEMENTMORPH_REAPERPLACEMENTMORPH = 3645
    LIGHTBRIDGEOFFTOPRIGHT_LIGHTBRIDGEOFF = 3647
    LIGHTBRIDGEONTOPRIGHT_LIGHTBRIDGEON = 3649
    TESTHEROGRAB_GRABZERGLING = 3651
    TESTHEROTHROW_THROWZERGLING = 3653
    TESTHERODEBUGMISSILEABILITY_TESTHERODEBUGMISSILEABILITY = 3655
    TESTHERODEBUGTRACKINGABILITY_TESTHERODEBUGTRACKINGABILITY = 3657
    TESTHERODEBUGTRACKINGABILITY_CANCEL = 3658
    CANCEL = 3659
    HALT = 3660
    BURROWDOWN = 3661
    BURROWUP = 3662
    LOADALL = 3663
    UNLOADALL = 3664
    STOP = 3665
    HARVEST_GATHER = 3666
    HARVEST_RETURN = 3667
    LOAD = 3668
    UNLOADALLAT = 3669
    CANCEL_LAST = 3671
    CANCEL_SLOT = 3672
    RALLY_UNITS = 3673
    ATTACK = 3674
    EFFECT_STIM = 3675
    BEHAVIOR_CLOAKON = 3676
    BEHAVIOR_CLOAKOFF = 3677
    LAND = 3678
    LIFT = 3679
    MORPH_ROOT = 3680
    MORPH_UPROOT = 3681
    BUILD_TECHLAB = 3682
    BUILD_REACTOR = 3683
    EFFECT_SPRAY = 3684
    EFFECT_REPAIR = 3685
    EFFECT_MASSRECALL = 3686
    EFFECT_BLINK = 3687
    BEHAVIOR_HOLDFIREON = 3688
    BEHAVIOR_HOLDFIREOFF = 3689
    RALLY_WORKERS = 3690
    BUILD_CREEPTUMOR = 3691
    RESEARCH_PROTOSSAIRARMOR = 3692
    RESEARCH_PROTOSSAIRWEAPONS = 3693
    RESEARCH_PROTOSSGROUNDARMOR = 3694
    RESEARCH_PROTOSSGROUNDWEAPONS = 3695
    RESEARCH_PROTOSSSHIELDS = 3696
    RESEARCH_TERRANINFANTRYARMOR = 3697
    RESEARCH_TERRANINFANTRYWEAPONS = 3698
    RESEARCH_TERRANSHIPWEAPONS = 3699
    RESEARCH_TERRANVEHICLEANDSHIPPLATING = 3700
    RESEARCH_TERRANVEHICLEWEAPONS = 3701
    RESEARCH_ZERGFLYERARMOR = 3702
    RESEARCH_ZERGFLYERATTACK = 3703
    RESEARCH_ZERGGROUNDARMOR = 3704
    RESEARCH_ZERGMELEEWEAPONS = 3705
    RESEARCH_ZERGMISSILEWEAPONS = 3706
    CANCEL_VOIDRAYPRISMATICALIGNMENT = 3707
    RESEARCH_ADAPTIVETALONS = 3709
    LURKERDENRESEARCH_RESEARCHLURKERRANGE = 3710
    MORPH_OBSERVERMODE = 3739
    MORPH_SURVEILLANCEMODE = 3741
    MORPH_OVERSIGHTMODE = 3743
    MORPH_OVERSEERMODE = 3745
    EFFECT_INTERFERENCEMATRIX = 3747
    EFFECT_REPAIRDRONE = 3749
    EFFECT_REPAIR_REPAIRDRONE = 3751
    EFFECT_ANTIARMORMISSILE = 3753
    EFFECT_CHRONOBOOSTENERGYCOST = 3755
    EFFECT_MASSRECALL_NEXUS = 3757
    NEXUSSHIELDRECHARGE_NEXUSSHIELDRECHARGE = 3759
    NEXUSSHIELDRECHARGEONPYLON_NEXUSSHIELDRECHARGEONPYLON = 3761
    INFESTORENSNARE_INFESTORENSNARE = 3763
    EFFECT_RESTORE = 3765
    NEXUSSHIELDOVERCHARGE_NEXUSSHIELDOVERCHARGE = 3767
    NEXUSSHIELDOVERCHARGEOFF_NEXUSSHIELDOVERCHARGEOFF = 3769
    ATTACK_BATTLECRUISER = 3771
    BATTLECRUISERATTACK_ATTACKTOWARDS = 3772
    BATTLECRUISERATTACK_ATTACKBARRAGE = 3773
    BATTLECRUISERATTACKEVALUATOR_MOTHERSHIPCOREATTACK = 3774
    MOVE_BATTLECRUISER = 3776
    PATROL_BATTLECRUISER = 3777
    HOLDPOSITION_BATTLECRUISER = 3778
    BATTLECRUISERMOVE_ACQUIREMOVE = 3779
    BATTLECRUISERMOVE_TURN = 3780
    BATTLECRUISERSTOPEVALUATOR_STOP = 3781
    STOP_BATTLECRUISER = 3783
    BATTLECRUISERSTOP_HOLDFIRE = 3784
    BATTLECRUISERSTOP_CHEER = 3785
    BATTLECRUISERSTOP_DANCE = 3786
    VIPERPARASITICBOMBRELAY_PARASITICBOMB = 3789
    PARASITICBOMBRELAYDODGE_PARASITICBOMB = 3791
    HOLDPOSITION = 3793
    MOVE = 3794
    PATROL = 3795
    UNLOADUNIT = 3796
    LOADOUTSPRAY_LOADOUTSPRAY1 = 3797
    LOADOUTSPRAY_LOADOUTSPRAY2 = 3798
    LOADOUTSPRAY_LOADOUTSPRAY3 = 3799
    LOADOUTSPRAY_LOADOUTSPRAY4 = 3800
    LOADOUTSPRAY_LOADOUTSPRAY5 = 3801
    LOADOUTSPRAY_LOADOUTSPRAY6 = 3802
    LOADOUTSPRAY_LOADOUTSPRAY7 = 3803
    LOADOUTSPRAY_LOADOUTSPRAY8 = 3804
    LOADOUTSPRAY_LOADOUTSPRAY9 = 3805
    LOADOUTSPRAY_LOADOUTSPRAY10 = 3806
    LOADOUTSPRAY_LOADOUTSPRAY11 = 3807
    LOADOUTSPRAY_LOADOUTSPRAY12 = 3808
    LOADOUTSPRAY_LOADOUTSPRAY13 = 3809
    LOADOUTSPRAY_LOADOUTSPRAY14 = 3810
    MORPHTOCOLLAPSIBLEROCKTOWERDEBRISRAMPLEFTGREEN_MORPHTOCOLLAPSIBLEROCKTOWERDEBRISRAMPLEFTGREEN = 3966
    MORPHTOCOLLAPSIBLEROCKTOWERDEBRISRAMPLEFTGREEN_CANCEL = 3967
    MORPHTOCOLLAPSIBLEROCKTOWERDEBRISRAMPRIGHTGREEN_MORPHTOCOLLAPSIBLEROCKTOWERDEBRISRAMPRIGHTGREEN = 3969
    MORPHTOCOLLAPSIBLEROCKTOWERDEBRISRAMPRIGHTGREEN_CANCEL = 3970
    BATTERYOVERCHARGE_BATTERYOVERCHARGE = 4107
    HYDRALISKFRENZY_HYDRALISKFRENZY = 4109
    AMORPHOUSARMORCLOUD_AMORPHOUSARMORCLOUD = 4111
    SHIELDBATTERYRECHARGEEX5_SHIELDBATTERYRECHARGE = 4113
    SHIELDBATTERYRECHARGEEX5_STOP = 4114
    MORPHTOBANELING_BANELING = 4121
    MORPHTOBANELING_CANCEL = 4122
    MOTHERSHIPCLOAK_ORACLECLOAKFIELD = 4124
    ENERGYRECHARGE_ENERGYRECHARGE = 4126
    SALVAGEEFFECT_SALVAGE = 4128
    SALVAGESENSORTOWERREFUND_SALVAGE = 4130
    WORKERSTOPIDLEABILITYVESPENE_GATHER = 4132

    def __repr__(self) -> str:
        return f"AbilityId.{self.name}"

    @classmethod
    def _missing_(cls, value: int) -> AbilityId:
        return cls.NULL_NULL


for item in AbilityId:
    globals()[item.name] = item
```

### File: `sc2/ids/buff_id.py`

```python
# pyre-ignore-all-errors[14]
from __future__ import annotations

# DO NOT EDIT!
# This file was automatically generated by "generate_ids.py"
import enum


class BuffId(enum.Enum):
    NULL = 0
    RADAR25 = 1
    TAUNTB = 2
    DISABLEABILS = 3
    TRANSIENTMORPH = 4
    GRAVITONBEAM = 5
    GHOSTCLOAK = 6
    BANSHEECLOAK = 7
    POWERUSERWARPABLE = 8
    VORTEXBEHAVIORENEMY = 9
    CORRUPTION = 10
    QUEENSPAWNLARVATIMER = 11
    GHOSTHOLDFIRE = 12
    GHOSTHOLDFIREB = 13
    LEECH = 14
    LEECHDISABLEABILITIES = 15
    EMPDECLOAK = 16
    FUNGALGROWTH = 17
    GUARDIANSHIELD = 18
    SEEKERMISSILETIMEOUT = 19
    TIMEWARPPRODUCTION = 20
    ETHEREAL = 21
    NEURALPARASITE = 22
    NEURALPARASITEWAIT = 23
    STIMPACKMARAUDER = 24
    SUPPLYDROP = 25
    _250MMSTRIKECANNONS = 26
    STIMPACK = 27
    PSISTORM = 28
    CLOAKFIELDEFFECT = 29
    CHARGING = 30
    AIDANGERBUFF = 31
    VORTEXBEHAVIOR = 32
    SLOW = 33
    TEMPORALRIFTUNIT = 34
    SHEEPBUSY = 35
    CONTAMINATED = 36
    TIMESCALECONVERSIONBEHAVIOR = 37
    BLINDINGCLOUDSTRUCTURE = 38
    COLLAPSIBLEROCKTOWERCONJOINEDSEARCH = 39
    COLLAPSIBLEROCKTOWERRAMPDIAGONALCONJOINEDSEARCH = 40
    COLLAPSIBLETERRANTOWERCONJOINEDSEARCH = 41
    COLLAPSIBLETERRANTOWERRAMPDIAGONALCONJOINEDSEARCH = 42
    DIGESTERCREEPSPRAYVISION = 43
    INVULNERABILITYSHIELD = 44
    MINEDRONECOUNTDOWN = 45
    MOTHERSHIPSTASIS = 46
    MOTHERSHIPSTASISCASTER = 47
    MOTHERSHIPCOREENERGIZEVISUAL = 48
    ORACLEREVELATION = 49
    GHOSTSNIPEDOT = 50
    NEXUSPHASESHIFT = 51
    NEXUSINVULNERABILITY = 52
    ROUGHTERRAINSEARCH = 53
    ROUGHTERRAINSLOW = 54
    ORACLECLOAKFIELD = 55
    ORACLECLOAKFIELDEFFECT = 56
    SCRYERFRIENDLY = 57
    SPECTRESHIELD = 58
    VIPERCONSUMESTRUCTURE = 59
    RESTORESHIELDS = 60
    MERCENARYCYCLONEMISSILES = 61
    MERCENARYSENSORDISH = 62
    MERCENARYSHIELD = 63
    SCRYER = 64
    STUNROUNDINITIALBEHAVIOR = 65
    BUILDINGSHIELD = 66
    LASERSIGHT = 67
    PROTECTIVEBARRIER = 68
    CORRUPTORGROUNDATTACKDEBUFF = 69
    BATTLECRUISERANTIAIRDISABLE = 70
    BUILDINGSTASIS = 71
    STASIS = 72
    RESOURCESTUN = 73
    MAXIMUMTHRUST = 74
    CHARGEUP = 75
    CLOAKUNIT = 76
    NULLFIELD = 77
    RESCUE = 78
    BENIGN = 79
    LASERTARGETING = 80
    ENGAGE = 81
    CAPRESOURCE = 82
    BLINDINGCLOUD = 83
    DOOMDAMAGEDELAY = 84
    EYESTALK = 85
    BURROWCHARGE = 86
    HIDDEN = 87
    MINEDRONEDOT = 88
    MEDIVACSPEEDBOOST = 89
    EXTENDBRIDGEEXTENDINGBRIDGENEWIDE8OUT = 90
    EXTENDBRIDGEEXTENDINGBRIDGENWWIDE8OUT = 91
    EXTENDBRIDGEEXTENDINGBRIDGENEWIDE10OUT = 92
    EXTENDBRIDGEEXTENDINGBRIDGENWWIDE10OUT = 93
    EXTENDBRIDGEEXTENDINGBRIDGENEWIDE12OUT = 94
    EXTENDBRIDGEEXTENDINGBRIDGENWWIDE12OUT = 95
    PHASESHIELD = 96
    PURIFY = 97
    VOIDSIPHON = 98
    ORACLEWEAPON = 99
    ANTIAIRWEAPONSWITCHCOOLDOWN = 100
    ARBITERMPSTASISFIELD = 101
    IMMORTALOVERLOAD = 102
    CLOAKINGFIELDTARGETED = 103
    LIGHTNINGBOMB = 104
    ORACLEPHASESHIFT = 105
    RELEASEINTERCEPTORSCOOLDOWN = 106
    RELEASEINTERCEPTORSTIMEDLIFEWARNING = 107
    RELEASEINTERCEPTORSWANDERDELAY = 108
    RELEASEINTERCEPTORSBEACON = 109
    ARBITERMPCLOAKFIELDEFFECT = 110
    PURIFICATIONNOVA = 111
    CORRUPTIONBOMBDAMAGE = 112
    CORSAIRMPDISRUPTIONWEB = 113
    DISRUPTORPUSH = 114
    LIGHTOFAIUR = 115
    LOCKON = 116
    OVERCHARGE = 117
    OVERCHARGEDAMAGE = 118
    OVERCHARGESPEEDBOOST = 119
    SEEKERMISSILE = 120
    TEMPORALFIELD = 121
    VOIDRAYSWARMDAMAGEBOOST = 122
    VOIDMPIMMORTALREVIVESUPRESSED = 123
    DEVOURERMPACIDSPORES = 124
    DEFILERMPCONSUME = 125
    DEFILERMPDARKSWARM = 126
    DEFILERMPPLAGUE = 127
    QUEENMPENSNARE = 128
    ORACLESTASISTRAPTARGET = 129
    SELFREPAIR = 130
    AGGRESSIVEMUTATION = 131
    PARASITICBOMB = 132
    PARASITICBOMBUNITKU = 133
    PARASITICBOMBSECONDARYUNITSEARCH = 134
    ADEPTDEATHCHECK = 135
    LURKERHOLDFIRE = 136
    LURKERHOLDFIREB = 137
    TIMESTOPSTUN = 138
    SLAYNELEMENTALGRABSTUN = 139
    PURIFICATIONNOVAPOST = 140
    DISABLEINTERCEPTORS = 141
    BYPASSARMORDEBUFFONE = 142
    BYPASSARMORDEBUFFTWO = 143
    BYPASSARMORDEBUFFTHREE = 144
    CHANNELSNIPECOMBAT = 145
    TEMPESTDISRUPTIONBLASTSTUNBEHAVIOR = 146
    GRAVITONPRISON = 147
    INFESTORDISEASE = 148
    SS_LIGHTNINGPROJECTOR = 149
    PURIFIERPLANETCRACKERCHARGE = 150
    SPECTRECLOAKING = 151
    WRAITHCLOAK = 152
    PSYTROUSOXIDE = 153
    BANSHEECLOAKCROSSSPECTRUMDAMPENERS = 154
    SS_BATTLECRUISERHUNTERSEEKERTIMEOUT = 155
    SS_STRONGERENEMYBUFF = 156
    SS_TERRATRONARMMISSILETARGETCHECK = 157
    SS_MISSILETIMEOUT = 158
    SS_LEVIATHANBOMBCOLLISIONCHECK = 159
    SS_LEVIATHANBOMBEXPLODETIMER = 160
    SS_LEVIATHANBOMBMISSILETARGETCHECK = 161
    SS_TERRATRONCOLLISIONCHECK = 162
    SS_CARRIERBOSSCOLLISIONCHECK = 163
    SS_CORRUPTORMISSILETARGETCHECK = 164
    SS_INVULNERABLE = 165
    SS_LEVIATHANTENTACLEMISSILETARGETCHECK = 166
    SS_LEVIATHANTENTACLEMISSILETARGETCHECKINVERTED = 167
    SS_LEVIATHANTENTACLETARGETDEATHDELAY = 168
    SS_LEVIATHANTENTACLEMISSILESCANSWAPDELAY = 169
    SS_POWERUPDIAGONAL2 = 170
    SS_BATTLECRUISERCOLLISIONCHECK = 171
    SS_TERRATRONMISSILESPINNERMISSILELAUNCHER = 172
    SS_TERRATRONMISSILESPINNERCOLLISIONCHECK = 173
    SS_TERRATRONMISSILELAUNCHER = 174
    SS_BATTLECRUISERMISSILELAUNCHER = 175
    SS_TERRATRONSTUN = 176
    SS_VIKINGRESPAWN = 177
    SS_WRAITHCOLLISIONCHECK = 178
    SS_SCOURGEMISSILETARGETCHECK = 179
    SS_SCOURGEDEATH = 180
    SS_SWARMGUARDIANCOLLISIONCHECK = 181
    SS_FIGHTERBOMBMISSILEDEATH = 182
    SS_FIGHTERDRONEDAMAGERESPONSE = 183
    SS_INTERCEPTORCOLLISIONCHECK = 184
    SS_CARRIERCOLLISIONCHECK = 185
    SS_MISSILETARGETCHECKVIKINGDRONE = 186
    SS_MISSILETARGETCHECKVIKINGSTRONG1 = 187
    SS_MISSILETARGETCHECKVIKINGSTRONG2 = 188
    SS_POWERUPHEALTH1 = 189
    SS_POWERUPHEALTH2 = 190
    SS_POWERUPSTRONG = 191
    SS_POWERUPMORPHTOBOMB = 192
    SS_POWERUPMORPHTOHEALTH = 193
    SS_POWERUPMORPHTOSIDEMISSILES = 194
    SS_POWERUPMORPHTOSTRONGERMISSILES = 195
    SS_CORRUPTORCOLLISIONCHECK = 196
    SS_SCOUTCOLLISIONCHECK = 197
    SS_PHOENIXCOLLISIONCHECK = 198
    SS_SCOURGECOLLISIONCHECK = 199
    SS_LEVIATHANCOLLISIONCHECK = 200
    SS_SCIENCEVESSELCOLLISIONCHECK = 201
    SS_TERRATRONSAWCOLLISIONCHECK = 202
    SS_LIGHTNINGPROJECTORCOLLISIONCHECK = 203
    SHIFTDELAY = 204
    BIOSTASIS = 205
    PERSONALCLOAKINGFREE = 206
    EMPDRAIN = 207
    MINDBLASTSTUN = 208
    _330MMBARRAGECANNONS = 209
    VOODOOSHIELD = 210
    SPECTRECLOAKINGFREE = 211
    ULTRASONICPULSESTUN = 212
    IRRADIATE = 213
    NYDUSWORMLAVAINSTANTDEATH = 214
    PREDATORCLOAKING = 215
    PSIDISRUPTION = 216
    MINDCONTROL = 217
    QUEENKNOCKDOWN = 218
    SCIENCEVESSELCLOAKFIELD = 219
    SPORECANNONMISSILE = 220
    ARTANISTEMPORALRIFTUNIT = 221
    ARTANISCLOAKINGFIELDEFFECT = 222
    ARTANISVORTEXBEHAVIOR = 223
    INCAPACITATED = 224
    KARASSPSISTORM = 225
    DUTCHMARAUDERSLOW = 226
    JUMPSTOMPSTUN = 227
    JUMPSTOMPFSTUN = 228
    RAYNORMISSILETIMEDLIFE = 229
    PSIONICSHOCKWAVEHEIGHTANDSTUN = 230
    SHADOWCLONE = 231
    AUTOMATEDREPAIR = 232
    SLIMED = 233
    RAYNORTIMEBOMBMISSILE = 234
    RAYNORTIMEBOMBUNIT = 235
    TYCHUSCOMMANDOSTIMPACK = 236
    VIRALPLASMA = 237
    NAPALM = 238
    BURSTCAPACITORSDAMAGEBUFF = 239
    COLONYINFESTATION = 240
    DOMINATION = 241
    EMPBURST = 242
    HYBRIDCZERGYROOTS = 243
    HYBRIDFZERGYROOTS = 244
    LOCKDOWNB = 245
    SPECTRELOCKDOWNB = 246
    VOODOOLOCKDOWN = 247
    ZERATULSTUN = 248
    BUILDINGSCARAB = 249
    VORTEXBEHAVIORERADICATOR = 250
    GHOSTBLAST = 251
    HEROICBUFF03 = 252
    CANNONRADAR = 253
    SS_MISSILETARGETCHECKVIKING = 254
    SS_MISSILETARGETCHECK = 255
    SS_MAXSPEED = 256
    SS_MAXACCELERATION = 257
    SS_POWERUPDIAGONAL1 = 258
    WATER = 259
    DEFENSIVEMATRIX = 260
    TESTATTRIBUTE = 261
    TESTVETERANCY = 262
    SHREDDERSWARMDAMAGEAPPLY = 263
    CORRUPTORINFESTING = 264
    MERCGROUNDDROPDELAY = 265
    MERCGROUNDDROP = 266
    MERCAIRDROPDELAY = 267
    SPECTREHOLDFIRE = 268
    SPECTREHOLDFIREB = 269
    ITEMGRAVITYBOMBS = 270
    CARRYMINERALFIELDMINERALS = 271
    CARRYHIGHYIELDMINERALFIELDMINERALS = 272
    CARRYHARVESTABLEVESPENEGEYSERGAS = 273
    CARRYHARVESTABLEVESPENEGEYSERGASPROTOSS = 274
    CARRYHARVESTABLEVESPENEGEYSERGASZERG = 275
    PERMANENTLYCLOAKED = 276
    RAVENSCRAMBLERMISSILE = 277
    RAVENSHREDDERMISSILETIMEOUT = 278
    RAVENSHREDDERMISSILETINT = 279
    RAVENSHREDDERMISSILEARMORREDUCTION = 280
    CHRONOBOOSTENERGYCOST = 281
    NEXUSSHIELDRECHARGEONPYLONBEHAVIOR = 282
    NEXUSSHIELDRECHARGEONPYLONBEHAVIORSECONDARYONTARGET = 283
    INFESTORENSNARE = 284
    INFESTORENSNAREMAKEPRECURSORREHEIGHTSOURCE = 285
    NEXUSSHIELDOVERCHARGE = 286
    PARASITICBOMBDELAYTIMEDLIFE = 287
    TRANSFUSION = 288
    ACCELERATIONZONETEMPORALFIELD = 289
    ACCELERATIONZONEFLYINGTEMPORALFIELD = 290
    INHIBITORZONEFLYINGTEMPORALFIELD = 291
    LOADOUTSPRAYTRACKER = 292
    INHIBITORZONETEMPORALFIELD = 293
    CLOAKFIELD = 294
    RESONATINGGLAIVESPHASESHIFT = 295
    NEURALPARASITECHILDREN = 296
    AMORPHOUSARMORCLOUD = 297
    RAVENSHREDDERMISSILEARMORREDUCTIONUISUBTRUCT = 298
    TAKENDAMAGE = 299
    RAVENSCRAMBLERMISSILECARRIER = 300
    BATTERYOVERCHARGE = 301
    HYDRALISKFRENZY = 302

    def __repr__(self) -> str:
        return f"BuffId.{self.name}"

    @classmethod
    def _missing_(cls, value: int) -> BuffId:
        return cls.NULL


for item in BuffId:
    globals()[item.name] = item
```

### File: `sc2/ids/effect_id.py`

```python
# pyre-ignore-all-errors[14]
from __future__ import annotations

# DO NOT EDIT!
# This file was automatically generated by "generate_ids.py"
import enum


class EffectId(enum.Enum):
    NULL = 0
    PSISTORMPERSISTENT = 1
    GUARDIANSHIELDPERSISTENT = 2
    TEMPORALFIELDGROWINGBUBBLECREATEPERSISTENT = 3
    TEMPORALFIELDAFTERBUBBLECREATEPERSISTENT = 4
    THERMALLANCESFORWARD = 5
    SCANNERSWEEP = 6
    NUKEPERSISTENT = 7
    LIBERATORTARGETMORPHDELAYPERSISTENT = 8
    LIBERATORTARGETMORPHPERSISTENT = 9
    BLINDINGCLOUDCP = 10
    RAVAGERCORROSIVEBILECP = 11
    LURKERMP = 12

    def __repr__(self) -> str:
        return f"EffectId.{self.name}"


for item in EffectId:
    globals()[item.name] = item
```

### File: `sc2/ids/id_version.py`

```python
ID_VERSION_STRING = "4.11.4.78285"
```

### File: `sc2/ids/unit_typeid.py`

```python
# pyre-ignore-all-errors[14]
from __future__ import annotations

# DO NOT EDIT!
# This file was automatically generated by "generate_ids.py"
import enum


class UnitTypeId(enum.Enum):
    NOTAUNIT = 0
    SYSTEM_SNAPSHOT_DUMMY = 1
    BALL = 2
    STEREOSCOPICOPTIONSUNIT = 3
    COLOSSUS = 4
    TECHLAB = 5
    REACTOR = 6
    INFESTORTERRAN = 7
    BANELINGCOCOON = 8
    BANELING = 9
    MOTHERSHIP = 10
    POINTDEFENSEDRONE = 11
    CHANGELING = 12
    CHANGELINGZEALOT = 13
    CHANGELINGMARINESHIELD = 14
    CHANGELINGMARINE = 15
    CHANGELINGZERGLINGWINGS = 16
    CHANGELINGZERGLING = 17
    COMMANDCENTER = 18
    SUPPLYDEPOT = 19
    REFINERY = 20
    BARRACKS = 21
    ENGINEERINGBAY = 22
    MISSILETURRET = 23
    BUNKER = 24
    SENSORTOWER = 25
    GHOSTACADEMY = 26
    FACTORY = 27
    STARPORT = 28
    ARMORY = 29
    FUSIONCORE = 30
    AUTOTURRET = 31
    SIEGETANKSIEGED = 32
    SIEGETANK = 33
    VIKINGASSAULT = 34
    VIKINGFIGHTER = 35
    COMMANDCENTERFLYING = 36
    BARRACKSTECHLAB = 37
    BARRACKSREACTOR = 38
    FACTORYTECHLAB = 39
    FACTORYREACTOR = 40
    STARPORTTECHLAB = 41
    STARPORTREACTOR = 42
    FACTORYFLYING = 43
    STARPORTFLYING = 44
    SCV = 45
    BARRACKSFLYING = 46
    SUPPLYDEPOTLOWERED = 47
    MARINE = 48
    REAPER = 49
    GHOST = 50
    MARAUDER = 51
    THOR = 52
    HELLION = 53
    MEDIVAC = 54
    BANSHEE = 55
    RAVEN = 56
    BATTLECRUISER = 57
    NUKE = 58
    NEXUS = 59
    PYLON = 60
    ASSIMILATOR = 61
    GATEWAY = 62
    FORGE = 63
    FLEETBEACON = 64
    TWILIGHTCOUNCIL = 65
    PHOTONCANNON = 66
    STARGATE = 67
    TEMPLARARCHIVE = 68
    DARKSHRINE = 69
    ROBOTICSBAY = 70
    ROBOTICSFACILITY = 71
    CYBERNETICSCORE = 72
    ZEALOT = 73
    STALKER = 74
    HIGHTEMPLAR = 75
    DARKTEMPLAR = 76
    SENTRY = 77
    PHOENIX = 78
    CARRIER = 79
    VOIDRAY = 80
    WARPPRISM = 81
    OBSERVER = 82
    IMMORTAL = 83
    PROBE = 84
    INTERCEPTOR = 85
    HATCHERY = 86
    CREEPTUMOR = 87
    EXTRACTOR = 88
    SPAWNINGPOOL = 89
    EVOLUTIONCHAMBER = 90
    HYDRALISKDEN = 91
    SPIRE = 92
    ULTRALISKCAVERN = 93
    INFESTATIONPIT = 94
    NYDUSNETWORK = 95
    BANELINGNEST = 96
    ROACHWARREN = 97
    SPINECRAWLER = 98
    SPORECRAWLER = 99
    LAIR = 100
    HIVE = 101
    GREATERSPIRE = 102
    EGG = 103
    DRONE = 104
    ZERGLING = 105
    OVERLORD = 106
    HYDRALISK = 107
    MUTALISK = 108
    ULTRALISK = 109
    ROACH = 110
    INFESTOR = 111
    CORRUPTOR = 112
    BROODLORDCOCOON = 113
    BROODLORD = 114
    BANELINGBURROWED = 115
    DRONEBURROWED = 116
    HYDRALISKBURROWED = 117
    ROACHBURROWED = 118
    ZERGLINGBURROWED = 119
    INFESTORTERRANBURROWED = 120
    REDSTONELAVACRITTERBURROWED = 121
    REDSTONELAVACRITTERINJUREDBURROWED = 122
    REDSTONELAVACRITTER = 123
    REDSTONELAVACRITTERINJURED = 124
    QUEENBURROWED = 125
    QUEEN = 126
    INFESTORBURROWED = 127
    OVERLORDCOCOON = 128
    OVERSEER = 129
    PLANETARYFORTRESS = 130
    ULTRALISKBURROWED = 131
    ORBITALCOMMAND = 132
    WARPGATE = 133
    ORBITALCOMMANDFLYING = 134
    FORCEFIELD = 135
    WARPPRISMPHASING = 136
    CREEPTUMORBURROWED = 137
    CREEPTUMORQUEEN = 138
    SPINECRAWLERUPROOTED = 139
    SPORECRAWLERUPROOTED = 140
    ARCHON = 141
    NYDUSCANAL = 142
    BROODLINGESCORT = 143
    GHOSTALTERNATE = 144
    GHOSTNOVA = 145
    RICHMINERALFIELD = 146
    RICHMINERALFIELD750 = 147
    URSADON = 148
    XELNAGATOWER = 149
    INFESTEDTERRANSEGG = 150
    LARVA = 151
    REAPERPLACEHOLDER = 152
    MARINEACGLUESCREENDUMMY = 153
    FIREBATACGLUESCREENDUMMY = 154
    MEDICACGLUESCREENDUMMY = 155
    MARAUDERACGLUESCREENDUMMY = 156
    VULTUREACGLUESCREENDUMMY = 157
    SIEGETANKACGLUESCREENDUMMY = 158
    VIKINGACGLUESCREENDUMMY = 159
    BANSHEEACGLUESCREENDUMMY = 160
    BATTLECRUISERACGLUESCREENDUMMY = 161
    ORBITALCOMMANDACGLUESCREENDUMMY = 162
    BUNKERACGLUESCREENDUMMY = 163
    BUNKERUPGRADEDACGLUESCREENDUMMY = 164
    MISSILETURRETACGLUESCREENDUMMY = 165
    HELLBATACGLUESCREENDUMMY = 166
    GOLIATHACGLUESCREENDUMMY = 167
    CYCLONEACGLUESCREENDUMMY = 168
    WRAITHACGLUESCREENDUMMY = 169
    SCIENCEVESSELACGLUESCREENDUMMY = 170
    HERCULESACGLUESCREENDUMMY = 171
    THORACGLUESCREENDUMMY = 172
    PERDITIONTURRETACGLUESCREENDUMMY = 173
    FLAMINGBETTYACGLUESCREENDUMMY = 174
    DEVASTATIONTURRETACGLUESCREENDUMMY = 175
    BLASTERBILLYACGLUESCREENDUMMY = 176
    SPINNINGDIZZYACGLUESCREENDUMMY = 177
    ZERGLINGKERRIGANACGLUESCREENDUMMY = 178
    RAPTORACGLUESCREENDUMMY = 179
    QUEENCOOPACGLUESCREENDUMMY = 180
    HYDRALISKACGLUESCREENDUMMY = 181
    HYDRALISKLURKERACGLUESCREENDUMMY = 182
    MUTALISKBROODLORDACGLUESCREENDUMMY = 183
    BROODLORDACGLUESCREENDUMMY = 184
    ULTRALISKACGLUESCREENDUMMY = 185
    TORRASQUEACGLUESCREENDUMMY = 186
    OVERSEERACGLUESCREENDUMMY = 187
    LURKERACGLUESCREENDUMMY = 188
    SPINECRAWLERACGLUESCREENDUMMY = 189
    SPORECRAWLERACGLUESCREENDUMMY = 190
    NYDUSNETWORKACGLUESCREENDUMMY = 191
    OMEGANETWORKACGLUESCREENDUMMY = 192
    ZERGLINGZAGARAACGLUESCREENDUMMY = 193
    SWARMLINGACGLUESCREENDUMMY = 194
    BANELINGACGLUESCREENDUMMY = 195
    SPLITTERLINGACGLUESCREENDUMMY = 196
    ABERRATIONACGLUESCREENDUMMY = 197
    SCOURGEACGLUESCREENDUMMY = 198
    CORRUPTORACGLUESCREENDUMMY = 199
    BILELAUNCHERACGLUESCREENDUMMY = 200
    SWARMQUEENACGLUESCREENDUMMY = 201
    ROACHACGLUESCREENDUMMY = 202
    ROACHVILEACGLUESCREENDUMMY = 203
    RAVAGERACGLUESCREENDUMMY = 204
    SWARMHOSTACGLUESCREENDUMMY = 205
    MUTALISKACGLUESCREENDUMMY = 206
    GUARDIANACGLUESCREENDUMMY = 207
    DEVOURERACGLUESCREENDUMMY = 208
    VIPERACGLUESCREENDUMMY = 209
    BRUTALISKACGLUESCREENDUMMY = 210
    LEVIATHANACGLUESCREENDUMMY = 211
    ZEALOTACGLUESCREENDUMMY = 212
    ZEALOTAIURACGLUESCREENDUMMY = 213
    DRAGOONACGLUESCREENDUMMY = 214
    HIGHTEMPLARACGLUESCREENDUMMY = 215
    ARCHONACGLUESCREENDUMMY = 216
    IMMORTALACGLUESCREENDUMMY = 217
    OBSERVERACGLUESCREENDUMMY = 218
    PHOENIXAIURACGLUESCREENDUMMY = 219
    REAVERACGLUESCREENDUMMY = 220
    TEMPESTACGLUESCREENDUMMY = 221
    PHOTONCANNONACGLUESCREENDUMMY = 222
    ZEALOTVORAZUNACGLUESCREENDUMMY = 223
    ZEALOTSHAKURASACGLUESCREENDUMMY = 224
    STALKERSHAKURASACGLUESCREENDUMMY = 225
    DARKTEMPLARSHAKURASACGLUESCREENDUMMY = 226
    CORSAIRACGLUESCREENDUMMY = 227
    VOIDRAYACGLUESCREENDUMMY = 228
    VOIDRAYSHAKURASACGLUESCREENDUMMY = 229
    ORACLEACGLUESCREENDUMMY = 230
    DARKARCHONACGLUESCREENDUMMY = 231
    DARKPYLONACGLUESCREENDUMMY = 232
    ZEALOTPURIFIERACGLUESCREENDUMMY = 233
    SENTRYPURIFIERACGLUESCREENDUMMY = 234
    IMMORTALKARAXACGLUESCREENDUMMY = 235
    COLOSSUSACGLUESCREENDUMMY = 236
    COLOSSUSPURIFIERACGLUESCREENDUMMY = 237
    PHOENIXPURIFIERACGLUESCREENDUMMY = 238
    CARRIERACGLUESCREENDUMMY = 239
    CARRIERAIURACGLUESCREENDUMMY = 240
    KHAYDARINMONOLITHACGLUESCREENDUMMY = 241
    SHIELDBATTERYACGLUESCREENDUMMY = 242
    ELITEMARINEACGLUESCREENDUMMY = 243
    MARAUDERCOMMANDOACGLUESCREENDUMMY = 244
    SPECOPSGHOSTACGLUESCREENDUMMY = 245
    HELLBATRANGERACGLUESCREENDUMMY = 246
    STRIKEGOLIATHACGLUESCREENDUMMY = 247
    HEAVYSIEGETANKACGLUESCREENDUMMY = 248
    RAIDLIBERATORACGLUESCREENDUMMY = 249
    RAVENTYPEIIACGLUESCREENDUMMY = 250
    COVERTBANSHEEACGLUESCREENDUMMY = 251
    RAILGUNTURRETACGLUESCREENDUMMY = 252
    BLACKOPSMISSILETURRETACGLUESCREENDUMMY = 253
    SUPPLICANTACGLUESCREENDUMMY = 254
    STALKERTALDARIMACGLUESCREENDUMMY = 255
    SENTRYTALDARIMACGLUESCREENDUMMY = 256
    HIGHTEMPLARTALDARIMACGLUESCREENDUMMY = 257
    IMMORTALTALDARIMACGLUESCREENDUMMY = 258
    COLOSSUSTALDARIMACGLUESCREENDUMMY = 259
    WARPPRISMTALDARIMACGLUESCREENDUMMY = 260
    PHOTONCANNONTALDARIMACGLUESCREENDUMMY = 261
    NEEDLESPINESWEAPON = 262
    CORRUPTIONWEAPON = 263
    INFESTEDTERRANSWEAPON = 264
    NEURALPARASITEWEAPON = 265
    POINTDEFENSEDRONERELEASEWEAPON = 266
    HUNTERSEEKERWEAPON = 267
    MULE = 268
    THORAAWEAPON = 269
    PUNISHERGRENADESLMWEAPON = 270
    VIKINGFIGHTERWEAPON = 271
    ATALASERBATTERYLMWEAPON = 272
    ATSLASERBATTERYLMWEAPON = 273
    LONGBOLTMISSILEWEAPON = 274
    D8CHARGEWEAPON = 275
    YAMATOWEAPON = 276
    IONCANNONSWEAPON = 277
    ACIDSALIVAWEAPON = 278
    SPINECRAWLERWEAPON = 279
    SPORECRAWLERWEAPON = 280
    GLAIVEWURMWEAPON = 281
    GLAIVEWURMM2WEAPON = 282
    GLAIVEWURMM3WEAPON = 283
    STALKERWEAPON = 284
    EMP2WEAPON = 285
    BACKLASHROCKETSLMWEAPON = 286
    PHOTONCANNONWEAPON = 287
    PARASITESPOREWEAPON = 288
    BROODLING = 289
    BROODLORDBWEAPON = 290
    AUTOTURRETRELEASEWEAPON = 291
    LARVARELEASEMISSILE = 292
    ACIDSPINESWEAPON = 293
    FRENZYWEAPON = 294
    CONTAMINATEWEAPON = 295
    BEACONRALLY = 296
    BEACONARMY = 297
    BEACONATTACK = 298
    BEACONDEFEND = 299
    BEACONHARASS = 300
    BEACONIDLE = 301
    BEACONAUTO = 302
    BEACONDETECT = 303
    BEACONSCOUT = 304
    BEACONCLAIM = 305
    BEACONEXPAND = 306
    BEACONCUSTOM1 = 307
    BEACONCUSTOM2 = 308
    BEACONCUSTOM3 = 309
    BEACONCUSTOM4 = 310
    ADEPT = 311
    ROCKS2X2NONCONJOINED = 312
    FUNGALGROWTHMISSILE = 313
    NEURALPARASITETENTACLEMISSILE = 314
    BEACON_PROTOSS = 315
    BEACON_PROTOSSSMALL = 316
    BEACON_TERRAN = 317
    BEACON_TERRANSMALL = 318
    BEACON_ZERG = 319
    BEACON_ZERGSMALL = 320
    LYOTE = 321
    CARRIONBIRD = 322
    KARAKMALE = 323
    KARAKFEMALE = 324
    URSADAKFEMALEEXOTIC = 325
    URSADAKMALE = 326
    URSADAKFEMALE = 327
    URSADAKCALF = 328
    URSADAKMALEEXOTIC = 329
    UTILITYBOT = 330
    COMMENTATORBOT1 = 331
    COMMENTATORBOT2 = 332
    COMMENTATORBOT3 = 333
    COMMENTATORBOT4 = 334
    SCANTIPEDE = 335
    DOG = 336
    SHEEP = 337
    COW = 338
    INFESTEDTERRANSEGGPLACEMENT = 339
    INFESTORTERRANSWEAPON = 340
    MINERALFIELD = 341
    VESPENEGEYSER = 342
    SPACEPLATFORMGEYSER = 343
    RICHVESPENEGEYSER = 344
    DESTRUCTIBLESEARCHLIGHT = 345
    DESTRUCTIBLEBULLHORNLIGHTS = 346
    DESTRUCTIBLESTREETLIGHT = 347
    DESTRUCTIBLESPACEPLATFORMSIGN = 348
    DESTRUCTIBLESTOREFRONTCITYPROPS = 349
    DESTRUCTIBLEBILLBOARDTALL = 350
    DESTRUCTIBLEBILLBOARDSCROLLINGTEXT = 351
    DESTRUCTIBLESPACEPLATFORMBARRIER = 352
    DESTRUCTIBLESIGNSDIRECTIONAL = 353
    DESTRUCTIBLESIGNSCONSTRUCTION = 354
    DESTRUCTIBLESIGNSFUNNY = 355
    DESTRUCTIBLESIGNSICONS = 356
    DESTRUCTIBLESIGNSWARNING = 357
    DESTRUCTIBLEGARAGE = 358
    DESTRUCTIBLEGARAGELARGE = 359
    DESTRUCTIBLETRAFFICSIGNAL = 360
    TRAFFICSIGNAL = 361
    BRAXISALPHADESTRUCTIBLE1X1 = 362
    BRAXISALPHADESTRUCTIBLE2X2 = 363
    DESTRUCTIBLEDEBRIS4X4 = 364
    DESTRUCTIBLEDEBRIS6X6 = 365
    DESTRUCTIBLEROCK2X4VERTICAL = 366
    DESTRUCTIBLEROCK2X4HORIZONTAL = 367
    DESTRUCTIBLEROCK2X6VERTICAL = 368
    DESTRUCTIBLEROCK2X6HORIZONTAL = 369
    DESTRUCTIBLEROCK4X4 = 370
    DESTRUCTIBLEROCK6X6 = 371
    DESTRUCTIBLERAMPDIAGONALHUGEULBR = 372
    DESTRUCTIBLERAMPDIAGONALHUGEBLUR = 373
    DESTRUCTIBLERAMPVERTICALHUGE = 374
    DESTRUCTIBLERAMPHORIZONTALHUGE = 375
    DESTRUCTIBLEDEBRISRAMPDIAGONALHUGEULBR = 376
    DESTRUCTIBLEDEBRISRAMPDIAGONALHUGEBLUR = 377
    OVERLORDGENERATECREEPKEYBIND = 378
    MENGSKSTATUEALONE = 379
    MENGSKSTATUE = 380
    WOLFSTATUE = 381
    GLOBESTATUE = 382
    WEAPON = 383
    GLAIVEWURMBOUNCEWEAPON = 384
    BROODLORDWEAPON = 385
    BROODLORDAWEAPON = 386
    CREEPBLOCKER1X1 = 387
    PERMANENTCREEPBLOCKER1X1 = 388
    PATHINGBLOCKER1X1 = 389
    PATHINGBLOCKER2X2 = 390
    AUTOTESTATTACKTARGETGROUND = 391
    AUTOTESTATTACKTARGETAIR = 392
    AUTOTESTATTACKER = 393
    HELPEREMITTERSELECTIONARROW = 394
    MULTIKILLOBJECT = 395
    SHAPEGOLFBALL = 396
    SHAPECONE = 397
    SHAPECUBE = 398
    SHAPECYLINDER = 399
    SHAPEDODECAHEDRON = 400
    SHAPEICOSAHEDRON = 401
    SHAPEOCTAHEDRON = 402
    SHAPEPYRAMID = 403
    SHAPEROUNDEDCUBE = 404
    SHAPESPHERE = 405
    SHAPETETRAHEDRON = 406
    SHAPETHICKTORUS = 407
    SHAPETHINTORUS = 408
    SHAPETORUS = 409
    SHAPE4POINTSTAR = 410
    SHAPE5POINTSTAR = 411
    SHAPE6POINTSTAR = 412
    SHAPE8POINTSTAR = 413
    SHAPEARROWPOINTER = 414
    SHAPEBOWL = 415
    SHAPEBOX = 416
    SHAPECAPSULE = 417
    SHAPECRESCENTMOON = 418
    SHAPEDECAHEDRON = 419
    SHAPEDIAMOND = 420
    SHAPEFOOTBALL = 421
    SHAPEGEMSTONE = 422
    SHAPEHEART = 423
    SHAPEJACK = 424
    SHAPEPLUSSIGN = 425
    SHAPESHAMROCK = 426
    SHAPESPADE = 427
    SHAPETUBE = 428
    SHAPEEGG = 429
    SHAPEYENSIGN = 430
    SHAPEX = 431
    SHAPEWATERMELON = 432
    SHAPEWONSIGN = 433
    SHAPETENNISBALL = 434
    SHAPESTRAWBERRY = 435
    SHAPESMILEYFACE = 436
    SHAPESOCCERBALL = 437
    SHAPERAINBOW = 438
    SHAPESADFACE = 439
    SHAPEPOUNDSIGN = 440
    SHAPEPEAR = 441
    SHAPEPINEAPPLE = 442
    SHAPEORANGE = 443
    SHAPEPEANUT = 444
    SHAPEO = 445
    SHAPELEMON = 446
    SHAPEMONEYBAG = 447
    SHAPEHORSESHOE = 448
    SHAPEHOCKEYSTICK = 449
    SHAPEHOCKEYPUCK = 450
    SHAPEHAND = 451
    SHAPEGOLFCLUB = 452
    SHAPEGRAPE = 453
    SHAPEEUROSIGN = 454
    SHAPEDOLLARSIGN = 455
    SHAPEBASKETBALL = 456
    SHAPECARROT = 457
    SHAPECHERRY = 458
    SHAPEBASEBALL = 459
    SHAPEBASEBALLBAT = 460
    SHAPEBANANA = 461
    SHAPEAPPLE = 462
    SHAPECASHLARGE = 463
    SHAPECASHMEDIUM = 464
    SHAPECASHSMALL = 465
    SHAPEFOOTBALLCOLORED = 466
    SHAPELEMONSMALL = 467
    SHAPEORANGESMALL = 468
    SHAPETREASURECHESTOPEN = 469
    SHAPETREASURECHESTCLOSED = 470
    SHAPEWATERMELONSMALL = 471
    UNBUILDABLEROCKSDESTRUCTIBLE = 472
    UNBUILDABLEBRICKSDESTRUCTIBLE = 473
    UNBUILDABLEPLATESDESTRUCTIBLE = 474
    DEBRIS2X2NONCONJOINED = 475
    ENEMYPATHINGBLOCKER1X1 = 476
    ENEMYPATHINGBLOCKER2X2 = 477
    ENEMYPATHINGBLOCKER4X4 = 478
    ENEMYPATHINGBLOCKER8X8 = 479
    ENEMYPATHINGBLOCKER16X16 = 480
    SCOPETEST = 481
    SENTRYACGLUESCREENDUMMY = 482
    MINERALFIELD750 = 483
    HELLIONTANK = 484
    COLLAPSIBLETERRANTOWERDEBRIS = 485
    DEBRISRAMPLEFT = 486
    DEBRISRAMPRIGHT = 487
    MOTHERSHIPCORE = 488
    LOCUSTMP = 489
    COLLAPSIBLEROCKTOWERDEBRIS = 490
    NYDUSCANALATTACKER = 491
    NYDUSCANALCREEPER = 492
    SWARMHOSTBURROWEDMP = 493
    SWARMHOSTMP = 494
    ORACLE = 495
    TEMPEST = 496
    WARHOUND = 497
    WIDOWMINE = 498
    VIPER = 499
    WIDOWMINEBURROWED = 500
    LURKERMPEGG = 501
    LURKERMP = 502
    LURKERMPBURROWED = 503
    LURKERDENMP = 504
    EXTENDINGBRIDGENEWIDE8OUT = 505
    EXTENDINGBRIDGENEWIDE8 = 506
    EXTENDINGBRIDGENWWIDE8OUT = 507
    EXTENDINGBRIDGENWWIDE8 = 508
    EXTENDINGBRIDGENEWIDE10OUT = 509
    EXTENDINGBRIDGENEWIDE10 = 510
    EXTENDINGBRIDGENWWIDE10OUT = 511
    EXTENDINGBRIDGENWWIDE10 = 512
    EXTENDINGBRIDGENEWIDE12OUT = 513
    EXTENDINGBRIDGENEWIDE12 = 514
    EXTENDINGBRIDGENWWIDE12OUT = 515
    EXTENDINGBRIDGENWWIDE12 = 516
    COLLAPSIBLEROCKTOWERDEBRISRAMPRIGHT = 517
    COLLAPSIBLEROCKTOWERDEBRISRAMPLEFT = 518
    XELNAGA_CAVERNS_DOORE = 519
    XELNAGA_CAVERNS_DOOREOPENED = 520
    XELNAGA_CAVERNS_DOORN = 521
    XELNAGA_CAVERNS_DOORNE = 522
    XELNAGA_CAVERNS_DOORNEOPENED = 523
    XELNAGA_CAVERNS_DOORNOPENED = 524
    XELNAGA_CAVERNS_DOORNW = 525
    XELNAGA_CAVERNS_DOORNWOPENED = 526
    XELNAGA_CAVERNS_DOORS = 527
    XELNAGA_CAVERNS_DOORSE = 528
    XELNAGA_CAVERNS_DOORSEOPENED = 529
    XELNAGA_CAVERNS_DOORSOPENED = 530
    XELNAGA_CAVERNS_DOORSW = 531
    XELNAGA_CAVERNS_DOORSWOPENED = 532
    XELNAGA_CAVERNS_DOORW = 533
    XELNAGA_CAVERNS_DOORWOPENED = 534
    XELNAGA_CAVERNS_FLOATING_BRIDGENE8OUT = 535
    XELNAGA_CAVERNS_FLOATING_BRIDGENE8 = 536
    XELNAGA_CAVERNS_FLOATING_BRIDGENW8OUT = 537
    XELNAGA_CAVERNS_FLOATING_BRIDGENW8 = 538
    XELNAGA_CAVERNS_FLOATING_BRIDGENE10OUT = 539
    XELNAGA_CAVERNS_FLOATING_BRIDGENE10 = 540
    XELNAGA_CAVERNS_FLOATING_BRIDGENW10OUT = 541
    XELNAGA_CAVERNS_FLOATING_BRIDGENW10 = 542
    XELNAGA_CAVERNS_FLOATING_BRIDGENE12OUT = 543
    XELNAGA_CAVERNS_FLOATING_BRIDGENE12 = 544
    XELNAGA_CAVERNS_FLOATING_BRIDGENW12OUT = 545
    XELNAGA_CAVERNS_FLOATING_BRIDGENW12 = 546
    XELNAGA_CAVERNS_FLOATING_BRIDGEH8OUT = 547
    XELNAGA_CAVERNS_FLOATING_BRIDGEH8 = 548
    XELNAGA_CAVERNS_FLOATING_BRIDGEV8OUT = 549
    XELNAGA_CAVERNS_FLOATING_BRIDGEV8 = 550
    XELNAGA_CAVERNS_FLOATING_BRIDGEH10OUT = 551
    XELNAGA_CAVERNS_FLOATING_BRIDGEH10 = 552
    XELNAGA_CAVERNS_FLOATING_BRIDGEV10OUT = 553
    XELNAGA_CAVERNS_FLOATING_BRIDGEV10 = 554
    XELNAGA_CAVERNS_FLOATING_BRIDGEH12OUT = 555
    XELNAGA_CAVERNS_FLOATING_BRIDGEH12 = 556
    XELNAGA_CAVERNS_FLOATING_BRIDGEV12OUT = 557
    XELNAGA_CAVERNS_FLOATING_BRIDGEV12 = 558
    COLLAPSIBLETERRANTOWERPUSHUNITRAMPLEFT = 559
    COLLAPSIBLETERRANTOWERPUSHUNITRAMPRIGHT = 560
    COLLAPSIBLEROCKTOWERPUSHUNIT = 561
    COLLAPSIBLETERRANTOWERPUSHUNIT = 562
    COLLAPSIBLEROCKTOWERPUSHUNITRAMPRIGHT = 563
    COLLAPSIBLEROCKTOWERPUSHUNITRAMPLEFT = 564
    DIGESTERCREEPSPRAYTARGETUNIT = 565
    DIGESTERCREEPSPRAYUNIT = 566
    NYDUSCANALATTACKERWEAPON = 567
    VIPERCONSUMESTRUCTUREWEAPON = 568
    RESOURCEBLOCKER = 569
    TEMPESTWEAPON = 570
    YOINKMISSILE = 571
    YOINKVIKINGAIRMISSILE = 572
    YOINKVIKINGGROUNDMISSILE = 573
    YOINKSIEGETANKMISSILE = 574
    WARHOUNDWEAPON = 575
    EYESTALKWEAPON = 576
    WIDOWMINEWEAPON = 577
    WIDOWMINEAIRWEAPON = 578
    MOTHERSHIPCOREWEAPONWEAPON = 579
    TORNADOMISSILEWEAPON = 580
    TORNADOMISSILEDUMMYWEAPON = 581
    TALONSMISSILEWEAPON = 582
    CREEPTUMORMISSILE = 583
    LOCUSTMPEGGAMISSILEWEAPON = 584
    LOCUSTMPEGGBMISSILEWEAPON = 585
    LOCUSTMPWEAPON = 586
    REPULSORCANNONWEAPON = 587
    COLLAPSIBLEROCKTOWERDIAGONAL = 588
    COLLAPSIBLETERRANTOWERDIAGONAL = 589
    COLLAPSIBLETERRANTOWERRAMPLEFT = 590
    COLLAPSIBLETERRANTOWERRAMPRIGHT = 591
    ICE2X2NONCONJOINED = 592
    ICEPROTOSSCRATES = 593
    PROTOSSCRATES = 594
    TOWERMINE = 595
    PICKUPPALLETGAS = 596
    PICKUPPALLETMINERALS = 597
    PICKUPSCRAPSALVAGE1X1 = 598
    PICKUPSCRAPSALVAGE2X2 = 599
    PICKUPSCRAPSALVAGE3X3 = 600
    ROUGHTERRAIN = 601
    UNBUILDABLEBRICKSSMALLUNIT = 602
    UNBUILDABLEPLATESSMALLUNIT = 603
    UNBUILDABLEPLATESUNIT = 604
    UNBUILDABLEROCKSSMALLUNIT = 605
    XELNAGAHEALINGSHRINE = 606
    INVISIBLETARGETDUMMY = 607
    PROTOSSVESPENEGEYSER = 608
    COLLAPSIBLEROCKTOWER = 609
    COLLAPSIBLETERRANTOWER = 610
    THORNLIZARD = 611
    CLEANINGBOT = 612
    DESTRUCTIBLEROCK6X6WEAK = 613
    PROTOSSSNAKESEGMENTDEMO = 614
    PHYSICSCAPSULE = 615
    PHYSICSCUBE = 616
    PHYSICSCYLINDER = 617
    PHYSICSKNOT = 618
    PHYSICSL = 619
    PHYSICSPRIMITIVES = 620
    PHYSICSSPHERE = 621
    PHYSICSSTAR = 622
    CREEPBLOCKER4X4 = 623
    DESTRUCTIBLECITYDEBRIS2X4VERTICAL = 624
    DESTRUCTIBLECITYDEBRIS2X4HORIZONTAL = 625
    DESTRUCTIBLECITYDEBRIS2X6VERTICAL = 626
    DESTRUCTIBLECITYDEBRIS2X6HORIZONTAL = 627
    DESTRUCTIBLECITYDEBRIS4X4 = 628
    DESTRUCTIBLECITYDEBRIS6X6 = 629
    DESTRUCTIBLECITYDEBRISHUGEDIAGONALBLUR = 630
    DESTRUCTIBLECITYDEBRISHUGEDIAGONALULBR = 631
    TESTZERG = 632
    PATHINGBLOCKERRADIUS1 = 633
    DESTRUCTIBLEROCKEX12X4VERTICAL = 634
    DESTRUCTIBLEROCKEX12X4HORIZONTAL = 635
    DESTRUCTIBLEROCKEX12X6VERTICAL = 636
    DESTRUCTIBLEROCKEX12X6HORIZONTAL = 637
    DESTRUCTIBLEROCKEX14X4 = 638
    DESTRUCTIBLEROCKEX16X6 = 639
    DESTRUCTIBLEROCKEX1DIAGONALHUGEULBR = 640
    DESTRUCTIBLEROCKEX1DIAGONALHUGEBLUR = 641
    DESTRUCTIBLEROCKEX1VERTICALHUGE = 642
    DESTRUCTIBLEROCKEX1HORIZONTALHUGE = 643
    DESTRUCTIBLEICE2X4VERTICAL = 644
    DESTRUCTIBLEICE2X4HORIZONTAL = 645
    DESTRUCTIBLEICE2X6VERTICAL = 646
    DESTRUCTIBLEICE2X6HORIZONTAL = 647
    DESTRUCTIBLEICE4X4 = 648
    DESTRUCTIBLEICE6X6 = 649
    DESTRUCTIBLEICEDIAGONALHUGEULBR = 650
    DESTRUCTIBLEICEDIAGONALHUGEBLUR = 651
    DESTRUCTIBLEICEVERTICALHUGE = 652
    DESTRUCTIBLEICEHORIZONTALHUGE = 653
    DESERTPLANETSEARCHLIGHT = 654
    DESERTPLANETSTREETLIGHT = 655
    UNBUILDABLEBRICKSUNIT = 656
    UNBUILDABLEROCKSUNIT = 657
    ZERUSDESTRUCTIBLEARCH = 658
    ARTOSILOPE = 659
    ANTEPLOTT = 660
    LABBOT = 661
    CRABEETLE = 662
    COLLAPSIBLEROCKTOWERRAMPRIGHT = 663
    COLLAPSIBLEROCKTOWERRAMPLEFT = 664
    LABMINERALFIELD = 665
    LABMINERALFIELD750 = 666
    SNOWREFINERY_TERRAN_EXTENDINGBRIDGENESHORT8OUT = 667
    SNOWREFINERY_TERRAN_EXTENDINGBRIDGENESHORT8 = 668
    SNOWREFINERY_TERRAN_EXTENDINGBRIDGENWSHORT8OUT = 669
    SNOWREFINERY_TERRAN_EXTENDINGBRIDGENWSHORT8 = 670
    TARSONIS_DOORN = 671
    TARSONIS_DOORNLOWERED = 672
    TARSONIS_DOORNE = 673
    TARSONIS_DOORNELOWERED = 674
    TARSONIS_DOORE = 675
    TARSONIS_DOORELOWERED = 676
    TARSONIS_DOORNW = 677
    TARSONIS_DOORNWLOWERED = 678
    COMPOUNDMANSION_DOORN = 679
    COMPOUNDMANSION_DOORNLOWERED = 680
    COMPOUNDMANSION_DOORNE = 681
    COMPOUNDMANSION_DOORNELOWERED = 682
    COMPOUNDMANSION_DOORE = 683
    COMPOUNDMANSION_DOORELOWERED = 684
    COMPOUNDMANSION_DOORNW = 685
    COMPOUNDMANSION_DOORNWLOWERED = 686
    RAVAGERCOCOON = 687
    RAVAGER = 688
    LIBERATOR = 689
    RAVAGERBURROWED = 690
    THORAP = 691
    CYCLONE = 692
    LOCUSTMPFLYING = 693
    DISRUPTOR = 694
    AIURLIGHTBRIDGENE8OUT = 695
    AIURLIGHTBRIDGENE8 = 696
    AIURLIGHTBRIDGENE10OUT = 697
    AIURLIGHTBRIDGENE10 = 698
    AIURLIGHTBRIDGENE12OUT = 699
    AIURLIGHTBRIDGENE12 = 700
    AIURLIGHTBRIDGENW8OUT = 701
    AIURLIGHTBRIDGENW8 = 702
    AIURLIGHTBRIDGENW10OUT = 703
    AIURLIGHTBRIDGENW10 = 704
    AIURLIGHTBRIDGENW12OUT = 705
    AIURLIGHTBRIDGENW12 = 706
    AIURTEMPLEBRIDGENE8OUT = 707
    AIURTEMPLEBRIDGENE10OUT = 708
    AIURTEMPLEBRIDGENE12OUT = 709
    AIURTEMPLEBRIDGENW8OUT = 710
    AIURTEMPLEBRIDGENW10OUT = 711
    AIURTEMPLEBRIDGENW12OUT = 712
    SHAKURASLIGHTBRIDGENE8OUT = 713
    SHAKURASLIGHTBRIDGENE8 = 714
    SHAKURASLIGHTBRIDGENE10OUT = 715
    SHAKURASLIGHTBRIDGENE10 = 716
    SHAKURASLIGHTBRIDGENE12OUT = 717
    SHAKURASLIGHTBRIDGENE12 = 718
    SHAKURASLIGHTBRIDGENW8OUT = 719
    SHAKURASLIGHTBRIDGENW8 = 720
    SHAKURASLIGHTBRIDGENW10OUT = 721
    SHAKURASLIGHTBRIDGENW10 = 722
    SHAKURASLIGHTBRIDGENW12OUT = 723
    SHAKURASLIGHTBRIDGENW12 = 724
    VOIDMPIMMORTALREVIVECORPSE = 725
    GUARDIANCOCOONMP = 726
    GUARDIANMP = 727
    DEVOURERCOCOONMP = 728
    DEVOURERMP = 729
    DEFILERMPBURROWED = 730
    DEFILERMP = 731
    ORACLESTASISTRAP = 732
    DISRUPTORPHASED = 733
    LIBERATORAG = 734
    AIURLIGHTBRIDGEABANDONEDNE8OUT = 735
    AIURLIGHTBRIDGEABANDONEDNE8 = 736
    AIURLIGHTBRIDGEABANDONEDNE10OUT = 737
    AIURLIGHTBRIDGEABANDONEDNE10 = 738
    AIURLIGHTBRIDGEABANDONEDNE12OUT = 739
    AIURLIGHTBRIDGEABANDONEDNE12 = 740
    AIURLIGHTBRIDGEABANDONEDNW8OUT = 741
    AIURLIGHTBRIDGEABANDONEDNW8 = 742
    AIURLIGHTBRIDGEABANDONEDNW10OUT = 743
    AIURLIGHTBRIDGEABANDONEDNW10 = 744
    AIURLIGHTBRIDGEABANDONEDNW12OUT = 745
    AIURLIGHTBRIDGEABANDONEDNW12 = 746
    COLLAPSIBLEPURIFIERTOWERDEBRIS = 747
    PORTCITY_BRIDGE_UNITNE8OUT = 748
    PORTCITY_BRIDGE_UNITNE8 = 749
    PORTCITY_BRIDGE_UNITSE8OUT = 750
    PORTCITY_BRIDGE_UNITSE8 = 751
    PORTCITY_BRIDGE_UNITNW8OUT = 752
    PORTCITY_BRIDGE_UNITNW8 = 753
    PORTCITY_BRIDGE_UNITSW8OUT = 754
    PORTCITY_BRIDGE_UNITSW8 = 755
    PORTCITY_BRIDGE_UNITNE10OUT = 756
    PORTCITY_BRIDGE_UNITNE10 = 757
    PORTCITY_BRIDGE_UNITSE10OUT = 758
    PORTCITY_BRIDGE_UNITSE10 = 759
    PORTCITY_BRIDGE_UNITNW10OUT = 760
    PORTCITY_BRIDGE_UNITNW10 = 761
    PORTCITY_BRIDGE_UNITSW10OUT = 762
    PORTCITY_BRIDGE_UNITSW10 = 763
    PORTCITY_BRIDGE_UNITNE12OUT = 764
    PORTCITY_BRIDGE_UNITNE12 = 765
    PORTCITY_BRIDGE_UNITSE12OUT = 766
    PORTCITY_BRIDGE_UNITSE12 = 767
    PORTCITY_BRIDGE_UNITNW12OUT = 768
    PORTCITY_BRIDGE_UNITNW12 = 769
    PORTCITY_BRIDGE_UNITSW12OUT = 770
    PORTCITY_BRIDGE_UNITSW12 = 771
    PORTCITY_BRIDGE_UNITN8OUT = 772
    PORTCITY_BRIDGE_UNITN8 = 773
    PORTCITY_BRIDGE_UNITS8OUT = 774
    PORTCITY_BRIDGE_UNITS8 = 775
    PORTCITY_BRIDGE_UNITE8OUT = 776
    PORTCITY_BRIDGE_UNITE8 = 777
    PORTCITY_BRIDGE_UNITW8OUT = 778
    PORTCITY_BRIDGE_UNITW8 = 779
    PORTCITY_BRIDGE_UNITN10OUT = 780
    PORTCITY_BRIDGE_UNITN10 = 781
    PORTCITY_BRIDGE_UNITS10OUT = 782
    PORTCITY_BRIDGE_UNITS10 = 783
    PORTCITY_BRIDGE_UNITE10OUT = 784
    PORTCITY_BRIDGE_UNITE10 = 785
    PORTCITY_BRIDGE_UNITW10OUT = 786
    PORTCITY_BRIDGE_UNITW10 = 787
    PORTCITY_BRIDGE_UNITN12OUT = 788
    PORTCITY_BRIDGE_UNITN12 = 789
    PORTCITY_BRIDGE_UNITS12OUT = 790
    PORTCITY_BRIDGE_UNITS12 = 791
    PORTCITY_BRIDGE_UNITE12OUT = 792
    PORTCITY_BRIDGE_UNITE12 = 793
    PORTCITY_BRIDGE_UNITW12OUT = 794
    PORTCITY_BRIDGE_UNITW12 = 795
    PURIFIERRICHMINERALFIELD = 796
    PURIFIERRICHMINERALFIELD750 = 797
    COLLAPSIBLEPURIFIERTOWERPUSHUNIT = 798
    LOCUSTMPPRECURSOR = 799
    RELEASEINTERCEPTORSBEACON = 800
    ADEPTPHASESHIFT = 801
    RAVAGERCORROSIVEBILEMISSILE = 802
    HYDRALISKIMPALEMISSILE = 803
    CYCLONEMISSILELARGEAIR = 804
    CYCLONEMISSILE = 805
    CYCLONEMISSILELARGE = 806
    THORAALANCE = 807
    ORACLEWEAPON = 808
    TEMPESTWEAPONGROUND = 809
    RAVAGERWEAPONMISSILE = 810
    SCOUTMPAIRWEAPONLEFT = 811
    SCOUTMPAIRWEAPONRIGHT = 812
    ARBITERMPWEAPONMISSILE = 813
    GUARDIANMPWEAPON = 814
    DEVOURERMPWEAPONMISSILE = 815
    DEFILERMPDARKSWARMWEAPON = 816
    QUEENMPENSNAREMISSILE = 817
    QUEENMPSPAWNBROODLINGSMISSILE = 818
    LIGHTNINGBOMBWEAPON = 819
    HERCPLACEMENT = 820
    GRAPPLEWEAPON = 821
    CAUSTICSPRAYMISSILE = 822
    PARASITICBOMBMISSILE = 823
    PARASITICBOMBDUMMY = 824
    ADEPTWEAPON = 825
    ADEPTUPGRADEWEAPON = 826
    LIBERATORMISSILE = 827
    LIBERATORDAMAGEMISSILE = 828
    LIBERATORAGMISSILE = 829
    KD8CHARGE = 830
    KD8CHARGEWEAPON = 831
    SLAYNELEMENTALGRABWEAPON = 832
    SLAYNELEMENTALGRABAIRUNIT = 833
    SLAYNELEMENTALGRABGROUNDUNIT = 834
    SLAYNELEMENTALWEAPON = 835
    DESTRUCTIBLEEXPEDITIONGATE6X6 = 836
    DESTRUCTIBLEZERGINFESTATION3X3 = 837
    HERC = 838
    MOOPY = 839
    REPLICANT = 840
    SEEKERMISSILE = 841
    AIURTEMPLEBRIDGEDESTRUCTIBLENE8OUT = 842
    AIURTEMPLEBRIDGEDESTRUCTIBLENE10OUT = 843
    AIURTEMPLEBRIDGEDESTRUCTIBLENE12OUT = 844
    AIURTEMPLEBRIDGEDESTRUCTIBLENW8OUT = 845
    AIURTEMPLEBRIDGEDESTRUCTIBLENW10OUT = 846
    AIURTEMPLEBRIDGEDESTRUCTIBLENW12OUT = 847
    AIURTEMPLEBRIDGEDESTRUCTIBLESW8OUT = 848
    AIURTEMPLEBRIDGEDESTRUCTIBLESW10OUT = 849
    AIURTEMPLEBRIDGEDESTRUCTIBLESW12OUT = 850
    AIURTEMPLEBRIDGEDESTRUCTIBLESE8OUT = 851
    AIURTEMPLEBRIDGEDESTRUCTIBLESE10OUT = 852
    AIURTEMPLEBRIDGEDESTRUCTIBLESE12OUT = 853
    FLYOVERUNIT = 854
    CORSAIRMP = 855
    SCOUTMP = 856
    ARBITERMP = 857
    SCOURGEMP = 858
    DEFILERMPPLAGUEWEAPON = 859
    QUEENMP = 860
    XELNAGADESTRUCTIBLERAMPBLOCKER6S = 861
    XELNAGADESTRUCTIBLERAMPBLOCKER6SE = 862
    XELNAGADESTRUCTIBLERAMPBLOCKER6E = 863
    XELNAGADESTRUCTIBLERAMPBLOCKER6NE = 864
    XELNAGADESTRUCTIBLERAMPBLOCKER6N = 865
    XELNAGADESTRUCTIBLERAMPBLOCKER6NW = 866
    XELNAGADESTRUCTIBLERAMPBLOCKER6W = 867
    XELNAGADESTRUCTIBLERAMPBLOCKER6SW = 868
    XELNAGADESTRUCTIBLERAMPBLOCKER8S = 869
    XELNAGADESTRUCTIBLERAMPBLOCKER8SE = 870
    XELNAGADESTRUCTIBLERAMPBLOCKER8E = 871
    XELNAGADESTRUCTIBLERAMPBLOCKER8NE = 872
    XELNAGADESTRUCTIBLERAMPBLOCKER8N = 873
    XELNAGADESTRUCTIBLERAMPBLOCKER8NW = 874
    XELNAGADESTRUCTIBLERAMPBLOCKER8W = 875
    XELNAGADESTRUCTIBLERAMPBLOCKER8SW = 876
    REPTILECRATE = 877
    SLAYNSWARMHOSTSPAWNFLYER = 878
    SLAYNELEMENTAL = 879
    PURIFIERVESPENEGEYSER = 880
    SHAKURASVESPENEGEYSER = 881
    COLLAPSIBLEPURIFIERTOWERDIAGONAL = 882
    CREEPONLYBLOCKER4X4 = 883
    PURIFIERMINERALFIELD = 884
    PURIFIERMINERALFIELD750 = 885
    BATTLESTATIONMINERALFIELD = 886
    BATTLESTATIONMINERALFIELD750 = 887
    BEACON_NOVA = 888
    BEACON_NOVASMALL = 889
    URSULA = 890
    ELSECARO_COLONIST_HUT = 891
    TRANSPORTOVERLORDCOCOON = 892
    OVERLORDTRANSPORT = 893
    PYLONOVERCHARGED = 894
    BYPASSARMORDRONE = 895
    ADEPTPIERCINGWEAPON = 896
    CORROSIVEPARASITEWEAPON = 897
    INFESTEDTERRAN = 898
    MERCCOMPOUND = 899
    SUPPLYDEPOTDROP = 900
    LURKERDEN = 901
    D8CHARGE = 902
    THORWRECKAGE = 903
    GOLIATH = 904
    TECHREACTOR = 905
    SS_POWERUPBOMB = 906
    SS_POWERUPHEALTH = 907
    SS_POWERUPSIDEMISSILES = 908
    SS_POWERUPSTRONGERMISSILES = 909
    LURKEREGG = 910
    LURKER = 911
    LURKERBURROWED = 912
    ARCHIVESEALED = 913
    INFESTEDCIVILIAN = 914
    FLAMINGBETTY = 915
    INFESTEDCIVILIANBURROWED = 916
    SELENDISINTERCEPTOR = 917
    SIEGEBREAKERSIEGED = 918
    SIEGEBREAKER = 919
    PERDITIONTURRETUNDERGROUND = 920
    PERDITIONTURRET = 921
    SENTRYGUNUNDERGROUND = 922
    SENTRYGUN = 923
    WARPIG = 924
    DEVILDOG = 925
    SPARTANCOMPANY = 926
    HAMMERSECURITY = 927
    HELSANGELFIGHTER = 928
    DUSKWING = 929
    DUKESREVENGE = 930
    ODINWRECKAGE = 931
    HERONUKE = 932
    KERRIGANCHARBURROWED = 933
    KERRIGANCHAR = 934
    SPIDERMINEBURROWED = 935
    SPIDERMINE = 936
    ZERATUL = 937
    URUN = 938
    MOHANDAR = 939
    SELENDIS = 940
    SCOUT = 941
    OMEGALISKBURROWED = 942
    OMEGALISK = 943
    INFESTEDABOMINATIONBURROWED = 944
    INFESTEDABOMINATION = 945
    HUNTERKILLERBURROWED = 946
    HUNTERKILLER = 947
    INFESTEDTERRANCAMPAIGNBURROWED = 948
    INFESTEDTERRANCAMPAIGN = 949
    CHECKSTATION = 950
    CHECKSTATIONDIAGONALBLUR = 951
    CHECKSTATIONDIAGONALULBR = 952
    CHECKSTATIONVERTICAL = 953
    CHECKSTATIONOPENED = 954
    CHECKSTATIONDIAGONALBLUROPENED = 955
    CHECKSTATIONDIAGONALULBROPENED = 956
    CHECKSTATIONVERTICALOPENED = 957
    BARRACKSTECHREACTOR = 958
    FACTORYTECHREACTOR = 959
    STARPORTTECHREACTOR = 960
    SPECTRENUKE = 961
    COLONISTSHIPFLYING = 962
    COLONISTSHIP = 963
    BIODOMECOMMANDFLYING = 964
    BIODOMECOMMAND = 965
    HERCULESLANDERFLYING = 966
    HERCULESLANDER = 967
    ZHAKULDASLIGHTBRIDGEOFF = 968
    ZHAKULDASLIGHTBRIDGE = 969
    ZHAKULDASLIBRARYUNITBURROWED = 970
    ZHAKULDASLIBRARYUNIT = 971
    XELNAGATEMPLEDOORBURROWED = 972
    XELNAGATEMPLEDOOR = 973
    XELNAGATEMPLEDOORURDLBURROWED = 974
    XELNAGATEMPLEDOORURDL = 975
    HELSANGELASSAULT = 976
    AUTOMATEDREFINERY = 977
    BATTLECRUISERHELIOSMORPH = 978
    HEALINGPOTIONTESTINSTANT = 979
    SPACEPLATFORMCLIFFDOOROPEN0 = 980
    SPACEPLATFORMCLIFFDOOR0 = 981
    SPACEPLATFORMCLIFFDOOROPEN1 = 982
    SPACEPLATFORMCLIFFDOOR1 = 983
    DESTRUCTIBLEGATEDIAGONALBLURLOWERED = 984
    DESTRUCTIBLEGATEDIAGONALULBRLOWERED = 985
    DESTRUCTIBLEGATESTRAIGHTHORIZONTALBFLOWERED = 986
    DESTRUCTIBLEGATESTRAIGHTHORIZONTALLOWERED = 987
    DESTRUCTIBLEGATESTRAIGHTVERTICALLFLOWERED = 988
    DESTRUCTIBLEGATESTRAIGHTVERTICALLOWERED = 989
    DESTRUCTIBLEGATEDIAGONALBLUR = 990
    DESTRUCTIBLEGATEDIAGONALULBR = 991
    DESTRUCTIBLEGATESTRAIGHTHORIZONTALBF = 992
    DESTRUCTIBLEGATESTRAIGHTHORIZONTAL = 993
    DESTRUCTIBLEGATESTRAIGHTVERTICALLF = 994
    DESTRUCTIBLEGATESTRAIGHTVERTICAL = 995
    METALGATEDIAGONALBLURLOWERED = 996
    METALGATEDIAGONALULBRLOWERED = 997
    METALGATESTRAIGHTHORIZONTALBFLOWERED = 998
    METALGATESTRAIGHTHORIZONTALLOWERED = 999
    METALGATESTRAIGHTVERTICALLFLOWERED = 1000
    METALGATESTRAIGHTVERTICALLOWERED = 1001
    METALGATEDIAGONALBLUR = 1002
    METALGATEDIAGONALULBR = 1003
    METALGATESTRAIGHTHORIZONTALBF = 1004
    METALGATESTRAIGHTHORIZONTAL = 1005
    METALGATESTRAIGHTVERTICALLF = 1006
    METALGATESTRAIGHTVERTICAL = 1007
    SECURITYGATEDIAGONALBLURLOWERED = 1008
    SECURITYGATEDIAGONALULBRLOWERED = 1009
    SECURITYGATESTRAIGHTHORIZONTALBFLOWERED = 1010
    SECURITYGATESTRAIGHTHORIZONTALLOWERED = 1011
    SECURITYGATESTRAIGHTVERTICALLFLOWERED = 1012
    SECURITYGATESTRAIGHTVERTICALLOWERED = 1013
    SECURITYGATEDIAGONALBLUR = 1014
    SECURITYGATEDIAGONALULBR = 1015
    SECURITYGATESTRAIGHTHORIZONTALBF = 1016
    SECURITYGATESTRAIGHTHORIZONTAL = 1017
    SECURITYGATESTRAIGHTVERTICALLF = 1018
    SECURITYGATESTRAIGHTVERTICAL = 1019
    TERRAZINENODEDEADTERRAN = 1020
    TERRAZINENODEHAPPYPROTOSS = 1021
    ZHAKULDASLIGHTBRIDGEOFFTOPRIGHT = 1022
    ZHAKULDASLIGHTBRIDGETOPRIGHT = 1023
    BATTLECRUISERHELIOS = 1024
    NUKESILONOVA = 1025
    ODIN = 1026
    PYGALISKCOCOON = 1027
    DEVOURERTISSUEDOODAD = 1028
    SS_BATTLECRUISERMISSILELAUNCHER = 1029
    SS_TERRATRONMISSILESPINNERMISSILE = 1030
    SS_TERRATRONSAW = 1031
    SS_BATTLECRUISERHUNTERSEEKERMISSILE = 1032
    SS_LEVIATHANBOMB = 1033
    DEVOURERTISSUEMISSILE = 1034
    SS_INTERCEPTOR = 1035
    SS_LEVIATHANBOMBMISSILE = 1036
    SS_LEVIATHANSPAWNBOMBMISSILE = 1037
    SS_FIGHTERMISSILELEFT = 1038
    SS_FIGHTERMISSILERIGHT = 1039
    SS_INTERCEPTORSPAWNMISSILE = 1040
    SS_CARRIERBOSSMISSILE = 1041
    SS_LEVIATHANTENTACLETARGET = 1042
    SS_LEVIATHANTENTACLEL2MISSILE = 1043
    SS_LEVIATHANTENTACLER1MISSILE = 1044
    SS_LEVIATHANTENTACLER2MISSILE = 1045
    SS_LEVIATHANTENTACLEL1MISSILE = 1046
    SS_TERRATRONMISSILE = 1047
    SS_WRAITHMISSILE = 1048
    SS_SCOURGEMISSILE = 1049
    SS_CORRUPTORMISSILE = 1050
    SS_SWARMGUARDIANMISSILE = 1051
    SS_STRONGMISSILE1 = 1052
    SS_STRONGMISSILE2 = 1053
    SS_FIGHTERDRONEMISSILE = 1054
    SS_PHOENIXMISSILE = 1055
    SS_SCOUTMISSILE = 1056
    SS_INTERCEPTORMISSILE = 1057
    SS_SCIENCEVESSELMISSILE = 1058
    SS_BATTLECRUISERMISSILE = 1059
    D8CLUSTERBOMBWEAPON = 1060
    D8CLUSTERBOMB = 1061
    BROODLORDEGG = 1062
    BROODLORDEGGMISSILE = 1063
    CIVILIANWEAPON = 1064
    BATTLECRUISERHELIOSALMWEAPON = 1065
    BATTLECRUISERLOKILMWEAPON = 1066
    BATTLECRUISERHELIOSGLMWEAPON = 1067
    BIOSTASISMISSILE = 1068
    INFESTEDVENTBROODLORDEGG = 1069
    INFESTEDVENTCORRUPTOREGG = 1070
    TENTACLEAMISSILE = 1071
    TENTACLEBMISSILE = 1072
    TENTACLECMISSILE = 1073
    TENTACLEDMISSILE = 1074
    MUTALISKEGG = 1075
    INFESTEDVENTMUTALISKEGG = 1076
    MUTALISKEGGMISSILE = 1077
    INFESTEDVENTEGGMISSILE = 1078
    SPORECANNONFIREMISSILE = 1079
    EXPERIMENTALPLASMAGUNWEAPON = 1080
    BRUTALISKWEAPON = 1081
    LOKIHURRICANEMISSILELEFT = 1082
    LOKIHURRICANEMISSILERIGHT = 1083
    ODINAAWEAPON = 1084
    DUSKWINGWEAPON = 1085
    KERRIGANWEAPON = 1086
    ULTRASONICPULSEWEAPON = 1087
    KERRIGANCHARWEAPON = 1088
    DEVASTATORMISSILEWEAPON = 1089
    SWANNWEAPON = 1090
    HAMMERSECURITYLMWEAPON = 1091
    CONSUMEDNAFEEDBACKWEAPON = 1092
    URUNWEAPONLEFT = 1093
    URUNWEAPONRIGHT = 1094
    HAILSTORMMISSILESWEAPON = 1095
    COLONYINFESTATIONWEAPON = 1096
    VOIDSEEKERPHASEMINEBLASTWEAPON = 1097
    VOIDSEEKERPHASEMINEBLASTSECONDARYWEAPON = 1098
    TOSSGRENADEWEAPON = 1099
    TYCHUSGRENADEWEAPON = 1100
    VILESTREAMWEAPON = 1101
    WRAITHAIRWEAPONRIGHT = 1102
    WRAITHAIRWEAPONLEFT = 1103
    WRAITHGROUNDWEAPON = 1104
    WEAPONHYBRIDD = 1105
    KARASSWEAPON = 1106
    HYBRIDCPLASMAWEAPON = 1107
    WARBOTBMISSILE = 1108
    LOKIYAMATOWEAPON = 1109
    HYPERIONYAMATOSPECIALWEAPON = 1110
    HYPERIONLMWEAPON = 1111
    HYPERIONALMWEAPON = 1112
    VULTUREWEAPON = 1113
    SCOUTAIRWEAPONLEFT = 1114
    SCOUTAIRWEAPONRIGHT = 1115
    HUNTERKILLERWEAPON = 1116
    GOLIATHAWEAPON = 1117
    SPARTANCOMPANYAWEAPON = 1118
    LEVIATHANSCOURGEMISSILE = 1119
    BIOPLASMIDDISCHARGEWEAPON = 1120
    VOIDSEEKERWEAPON = 1121
    HELSANGELFIGHTERWEAPON = 1122
    DRBATTLECRUISERALMWEAPON = 1123
    DRBATTLECRUISERGLMWEAPON = 1124
    HURRICANEMISSILERIGHT = 1125
    HURRICANEMISSILELEFT = 1126
    HYBRIDSINGULARITYFEEDBACKWEAPON = 1127
    DOMINIONKILLTEAMLMWEAPON = 1128
    ITEMGRENADESWEAPON = 1129
    ITEMGRAVITYBOMBSWEAPON = 1130
    TESTHEROTHROWMISSILE = 1131
    TESTHERODEBUGMISSILEABILITY1WEAPON = 1132
    TESTHERODEBUGMISSILEABILITY2WEAPON = 1133
    SPECTRE = 1134
    VULTURE = 1135
    LOKI = 1136
    WRAITH = 1137
    DOMINIONKILLTEAM = 1138
    FIREBAT = 1139
    DIAMONDBACK = 1140
    G4CHARGEWEAPON = 1141
    SS_BLACKEDGEBORDER = 1142
    DEVOURERTISSUESAMPLETUBE = 1143
    MONOLITH = 1144
    OBELISK = 1145
    ARCHIVE = 1146
    ARTIFACTVAULT = 1147
    AVERNUSGATECONTROL = 1148
    GATECONTROLUNIT = 1149
    BLIMPADS = 1150
    BLOCKER6X6 = 1151
    BLOCKER8X8 = 1152
    BLOCKER16X16 = 1153
    CARGOTRUCKUNITFLATBED = 1154
    CARGOTRUCKUNITTRAILER = 1155
    BLIMP = 1156
    CASTANARWINDOWLARGEDIAGONALULBRUNIT = 1157
    BLOCKER4X4 = 1158
    HOMELARGE = 1159
    HOMESMALL = 1160
    ELEVATORBLOCKER = 1161
    QUESTIONMARK = 1162
    NYDUSWORMLAVADEATH = 1163
    SS_BACKGROUNDSPACELARGE = 1164
    SS_BACKGROUNDSPACETERRAN00 = 1165
    SS_BACKGROUNDSPACETERRAN02 = 1166
    SS_BACKGROUNDSPACEZERG00 = 1167
    SS_BACKGROUNDSPACEZERG02 = 1168
    SS_CARRIERBOSS = 1169
    SS_BATTLECRUISER = 1170
    SS_TERRATRONMISSILESPINNERLAUNCHER = 1171
    SS_TERRATRONMISSILESPINNER = 1172
    SS_TERRATRONBEAMTARGET = 1173
    SS_LIGHTNINGPROJECTORFACERIGHT = 1174
    SS_SCOURGE = 1175
    SS_CORRUPTOR = 1176
    SS_TERRATRONMISSILELAUNCHER = 1177
    SS_LIGHTNINGPROJECTORFACELEFT = 1178
    SS_WRAITH = 1179
    SS_SWARMGUARDIAN = 1180
    SS_SCOUT = 1181
    SS_LEVIATHAN = 1182
    SS_SCIENCEVESSEL = 1183
    SS_TERRATRON = 1184
    SECRETDOCUMENTS = 1185
    PREDATOR = 1186
    DEFILERBONESAMPLE = 1187
    DEVOURERTISSUESAMPLE = 1188
    PROTOSSPSIELEMENTS = 1189
    TASSADAR = 1190
    SCIENCEFACILITY = 1191
    INFESTEDCOCOON = 1192
    FUSIONREACTOR = 1193
    BUBBACOMMERCIAL = 1194
    XELNAGAPRISONHEIGHT2 = 1195
    XELNAGAPRISON = 1196
    XELNAGAPRISONNORTH = 1197
    XELNAGAPRISONNORTHHEIGHT2 = 1198
    ZERGDROPPODCREEP = 1199
    IPISTOLAD = 1200
    L800ETC_AD = 1201
    NUKENOODLESCOMMERCIAL = 1202
    PSIOPSCOMMERCIAL = 1203
    SHIPALARM = 1204
    SPACEPLATFORMDESTRUCTIBLEJUMBOBLOCKER = 1205
    SPACEPLATFORMDESTRUCTIBLELARGEBLOCKER = 1206
    SPACEPLATFORMDESTRUCTIBLEMEDIUMBLOCKER = 1207
    SPACEPLATFORMDESTRUCTIBLESMALLBLOCKER = 1208
    TALDARIMMOTHERSHIP = 1209
    PLASMATORPEDOESWEAPON = 1210
    PSIDISRUPTOR = 1211
    HIVEMINDEMULATOR = 1212
    RAYNOR01 = 1213
    SCIENCEVESSEL = 1214
    SCOURGE = 1215
    SPACEPLATFORMREACTORPATHINGBLOCKER = 1216
    TAURENOUTHOUSE = 1217
    TYCHUSEJECTMISSILE = 1218
    FEEDERLING = 1219
    ULAANSMOKEBRIDGE = 1220
    TALDARIMPRISONCRYSTAL = 1221
    SPACEDIABLO = 1222
    MURLOCMARINE = 1223
    XELNAGAPRISONCONSOLE = 1224
    TALDARIMPRISON = 1225
    ADJUTANTCAPSULE = 1226
    XELNAGAVAULT = 1227
    HOLDINGPEN = 1228
    SCRAPHUGE = 1229
    PRISONERCIVILIAN = 1230
    BIODOMEHALFBUILT = 1231
    BIODOME = 1232
    DESTRUCTIBLEKORHALFLAG = 1233
    DESTRUCTIBLEKORHALPODIUM = 1234
    DESTRUCTIBLEKORHALTREE = 1235
    DESTRUCTIBLEKORHALFOLIAGE = 1236
    DESTRUCTIBLESANDBAGS = 1237
    CASTANARWINDOWLARGEDIAGONALBLURUNIT = 1238
    CARGOTRUCKUNITBARRELS = 1239
    SPORECANNON = 1240
    STETMANN = 1241
    BRIDGEBLOCKER4X12 = 1242
    CIVILIANSHIPWRECKED = 1243
    SWANN = 1244
    DRAKKENLASERDRILL = 1245
    MINDSIPHONRETURNWEAPON = 1246
    KERRIGANEGG = 1247
    CHRYSALISEGG = 1248
    PRISONERSPECTRE = 1249
    PRISONZEALOT = 1250
    SCRAPSALVAGE1X1 = 1251
    SCRAPSALVAGE2X2 = 1252
    SCRAPSALVAGE3X3 = 1253
    RAYNORCOMMANDO = 1254
    OVERMIND = 1255
    OVERMINDREMAINS = 1256
    INFESTEDMERCHAVEN = 1257
    MONLYTHARTIFACTFORCEFIELD = 1258
    MONLYTHFORCEFIELDSTATUE = 1259
    VIROPHAGE = 1260
    PSISHOCKWEAPON = 1261
    TYCHUSCOMMANDO = 1262
    BRUTALISK = 1263
    PYGALISK = 1264
    VALHALLABASEDESTRUCTIBLEDOORDEAD = 1265
    VALHALLABASEDESTRUCTIBLEDOOR = 1266
    VOIDSEEKER = 1267
    MINDSIPHONWEAPON = 1268
    WARBOT = 1269
    PLATFORMCONNECTOR = 1270
    ARTANIS = 1271
    TERRAZINECANISTER = 1272
    HERCULES = 1273
    MERCENARYFORTRESS = 1274
    RAYNOR = 1275
    ARTIFACTPIECE1 = 1276
    ARTIFACTPIECE2 = 1277
    ARTIFACTPIECE4 = 1278
    ARTIFACTPIECE3 = 1279
    ARTIFACTPIECE5 = 1280
    RIPFIELDGENERATOR = 1281
    RIPFIELDGENERATORSMALL = 1282
    XELNAGAWORLDSHIPVAULT = 1283
    TYCHUSCHAINGUN = 1284
    ARTIFACT = 1285
    CELLBLOCKB = 1286
    GHOSTLASERLINES = 1287
    MAINCELLBLOCK = 1288
    KERRIGAN = 1289
    DATACORE = 1290
    SPECIALOPSDROPSHIP = 1291
    TOSH = 1292
    CASTANARULTRALISKSHACKLEDUNIT = 1293
    KARASS = 1294
    INVISIBLEPYLON = 1295
    MAAR = 1296
    HYBRIDDESTROYER = 1297
    HYBRIDREAVER = 1298
    HYBRID = 1299
    TERRAZINENODE = 1300
    TRANSPORTTRUCK = 1301
    WALLOFFIRE = 1302
    WEAPONHYBRIDC = 1303
    XELNAGATEMPLE = 1304
    EXPLODINGBARRELLARGE = 1305
    SUPERWARPGATE = 1306
    TERRAZINETANK = 1307
    XELNAGASHRINE = 1308
    SMCAMERABRIDGE = 1309
    SMMARSARABARTYCHUSCAMERAS = 1310
    SMHYPERIONBRIDGESTAGE1HANSONCAMERAS = 1311
    SMHYPERIONBRIDGESTAGE1HORNERCAMERAS = 1312
    SMHYPERIONBRIDGESTAGE1TYCHUSCAMERAS = 1313
    SMHYPERIONBRIDGESTAGE1TOSHCAMERAS = 1314
    SMHYPERIONARMORYSTAGE1SWANNCAMERAS = 1315
    SMHYPERIONCANTINATOSHCAMERAS = 1316
    SMHYPERIONCANTINATYCHUSCAMERAS = 1317
    SMHYPERIONCANTINAYBARRACAMERAS = 1318
    SMHYPERIONLABADJUTANTCAMERAS = 1319
    SMHYPERIONLABCOWINCAMERAS = 1320
    SMHYPERIONLABHANSONCAMERAS = 1321
    SMHYPERIONBRIDGETRAYNOR03BRIEFINGCAMERA = 1322
    SMTESTCAMERA = 1323
    SMCAMERATERRAN01 = 1324
    SMCAMERATERRAN02A = 1325
    SMCAMERATERRAN02B = 1326
    SMCAMERATERRAN03 = 1327
    SMCAMERATERRAN04 = 1328
    SMCAMERATERRAN04A = 1329
    SMCAMERATERRAN04B = 1330
    SMCAMERATERRAN05 = 1331
    SMCAMERATERRAN06A = 1332
    SMCAMERATERRAN06B = 1333
    SMCAMERATERRAN06C = 1334
    SMCAMERATERRAN07 = 1335
    SMCAMERATERRAN08 = 1336
    SMCAMERATERRAN09 = 1337
    SMCAMERATERRAN10 = 1338
    SMCAMERATERRAN11 = 1339
    SMCAMERATERRAN12 = 1340
    SMCAMERATERRAN13 = 1341
    SMCAMERATERRAN14 = 1342
    SMCAMERATERRAN15 = 1343
    SMCAMERATERRAN16 = 1344
    SMCAMERATERRAN17 = 1345
    SMCAMERATERRAN20 = 1346
    SMFIRSTOFFICER = 1347
    SMHYPERIONBRIDGEBRIEFINGLEFT = 1348
    SMHYPERIONBRIDGEBRIEFINGRIGHT = 1349
    SMHYPERIONMEDLABBRIEFING = 1350
    SMHYPERIONMEDLABBRIEFINGCENTER = 1351
    SMHYPERIONMEDLABBRIEFINGLEFT = 1352
    SMHYPERIONMEDLABBRIEFINGRIGHT = 1353
    SMTOSHSHUTTLESET = 1354
    SMKERRIGANPHOTO = 1355
    SMTOSHSHUTTLESET2 = 1356
    SMMARSARABARJUKEBOXHS = 1357
    SMMARSARABARKERRIGANPHOTOHS = 1358
    SMVALERIANFLAGSHIPCORRIDORSSET = 1359
    SMVALERIANFLAGSHIPCORRIDORSSET2 = 1360
    SMVALERIANFLAGSHIPCORRIDORSSET3 = 1361
    SMVALERIANFLAGSHIPCORRIDORSSET4 = 1362
    SMVALERIANOBSERVATORYSET = 1363
    SMVALERIANOBSERVATORYSET2 = 1364
    SMVALERIANOBSERVATORYSET3 = 1365
    SMVALERIANOBSERVATORYPAINTINGHS = 1366
    SMCHARBATTLEZONEFLAG = 1367
    SMUNNSET = 1368
    SMTERRANREADYROOMSET = 1369
    SMCHARBATTLEZONESET = 1370
    SMCHARBATTLEZONESET2 = 1371
    SMCHARBATTLEZONESET3 = 1372
    SMCHARBATTLEZONESET4 = 1373
    SMCHARBATTLEZONESET5 = 1374
    SMCHARBATTLEZONEARTIFACTHS = 1375
    SMCHARBATTLEZONERADIOHS = 1376
    SMCHARBATTLEZONEDROPSHIPHS = 1377
    SMCHARBATTLEZONEBRIEFCASEHS = 1378
    SMCHARBATTLEZONEBRIEFINGSET = 1379
    SMCHARBATTLEZONEBRIEFINGSET2 = 1380
    SMCHARBATTLEZONEBRIEFINGSETLEFT = 1381
    SMCHARBATTLEZONEBRIEFINGSETRIGHT = 1382
    SMMARSARABARBADGEHS = 1383
    SMHYPERIONCANTINABADGEHS = 1384
    SMHYPERIONCANTINAPOSTER1HS = 1385
    SMHYPERIONCANTINAPOSTER2HS = 1386
    SMHYPERIONCANTINAPOSTER3HS = 1387
    SMHYPERIONCANTINAPOSTER4HS = 1388
    SMHYPERIONCANTINAPOSTER5HS = 1389
    SMFLY = 1390
    SMBRIDGEWINDOWSPACE = 1391
    SMBRIDGEPLANETSPACE = 1392
    SMBRIDGEPLANETSPACEASTEROIDS = 1393
    SMBRIDGEPLANETAGRIA = 1394
    SMBRIDGEPLANETAIUR = 1395
    SMBRIDGEPLANETAVERNUS = 1396
    SMBRIDGEPLANETBELSHIR = 1397
    SMBRIDGEPLANETCASTANAR = 1398
    SMBRIDGEPLANETCHAR = 1399
    SMBRIDGEPLANETHAVEN = 1400
    SMBRIDGEPLANETKORHAL = 1401
    SMBRIDGEPLANETMEINHOFF = 1402
    SMBRIDGEPLANETMONLYTH = 1403
    SMBRIDGEPLANETNEWFOLSOM = 1404
    SMBRIDGEPLANETPORTZION = 1405
    SMBRIDGEPLANETREDSTONE = 1406
    SMBRIDGEPLANETSHAKURAS = 1407
    SMBRIDGEPLANETTARSONIS = 1408
    SMBRIDGEPLANETTYPHON = 1409
    SMBRIDGEPLANETTYRADOR = 1410
    SMBRIDGEPLANETULAAN = 1411
    SMBRIDGEPLANETULNAR = 1412
    SMBRIDGEPLANETVALHALLA = 1413
    SMBRIDGEPLANETXIL = 1414
    SMBRIDGEPLANETZHAKULDAS = 1415
    SMMARSARAPLANET = 1416
    SMNOVA = 1417
    SMHAVENPLANET = 1418
    SMHYPERIONBRIDGEBRIEFING = 1419
    SMHYPERIONBRIDGEBRIEFINGCENTER = 1420
    SMCHARBATTLEFIELDENDPROPS = 1421
    SMCHARBATTLEZONETURRET = 1422
    SMTERRAN01FX = 1423
    SMTERRAN03FX = 1424
    SMTERRAN05FX = 1425
    SMTERRAN05FXMUTALISKS = 1426
    SMTERRAN05PROPS = 1427
    SMTERRAN06AFX = 1428
    SMTERRAN06BFX = 1429
    SMTERRAN06CFX = 1430
    SMTERRAN12FX = 1431
    SMTERRAN14FX = 1432
    SMTERRAN15FX = 1433
    SMTERRAN06APROPS = 1434
    SMTERRAN06BPROPS = 1435
    SMTERRAN07PROPS = 1436
    SMTERRAN07FX = 1437
    SMTERRAN08PROPS = 1438
    SMTERRAN09FX = 1439
    SMTERRAN09PROPS = 1440
    SMTERRAN11FX = 1441
    SMTERRAN11FXMISSILES = 1442
    SMTERRAN11FXEXPLOSIONS = 1443
    SMTERRAN11FXBLOOD = 1444
    SMTERRAN11FXDEBRIS = 1445
    SMTERRAN11FXDEBRIS1 = 1446
    SMTERRAN11FXDEBRIS2 = 1447
    SMTERRAN11PROPS = 1448
    SMTERRAN11PROPSBURROWROCKS = 1449
    SMTERRAN11PROPSRIFLESHELLS = 1450
    SMTERRAN12PROPS = 1451
    SMTERRAN13PROPS = 1452
    SMTERRAN14PROPS = 1453
    SMTERRAN15PROPS = 1454
    SMTERRAN16FX = 1455
    SMTERRAN16FXFLAK = 1456
    SMTERRAN17PROPS = 1457
    SMTERRAN17FX = 1458
    SMMARSARABARPROPS = 1459
    SMHYPERIONCORRIDORPROPS = 1460
    ZERATULCRYSTALCHARGE = 1461
    SMRAYNORHANDS = 1462
    SMPRESSROOMPROPS = 1463
    SMRAYNORGUN = 1464
    SMMARINERIFLE = 1465
    SMTOSHKNIFE = 1466
    SMTOSHSHUTTLEPROPS = 1467
    SMHYPERIONEXTERIOR = 1468
    SMHYPERIONEXTERIORLOW = 1469
    SMHYPERIONEXTERIORHOLOGRAM = 1470
    SMCHARCUTSCENES00 = 1471
    SMCHARCUTSCENES01 = 1472
    SMCHARCUTSCENES02 = 1473
    SMCHARCUTSCENES03 = 1474
    SMMARSARABARBRIEFINGSET = 1475
    SMMARSARABARBRIEFINGSET2 = 1476
    SMMARSARABARBRIEFINGSETLEFT = 1477
    SMMARSARABARBRIEFINGSETRIGHT = 1478
    SMMARSARABARBRIEFINGTVMAIN = 1479
    SMMARSARABARBRIEFINGTVMAIN2 = 1480
    SMMARSARABARBRIEFINGTVMAIN3 = 1481
    SMMARSARABARBRIEFINGTVPORTRAIT1 = 1482
    SMMARSARABARBRIEFINGTVPORTRAIT2 = 1483
    SMMARSARABARBRIEFINGTVPORTRAIT3 = 1484
    SMMARSARABARBRIEFINGTVPORTRAIT4 = 1485
    SMMARSARABARBRIEFINGTVPORTRAIT5 = 1486
    SMMARSARABARSET = 1487
    SMMARSARABARSET2 = 1488
    SMMARSARABARSTARMAPHS = 1489
    SMMARSARABARTVHS = 1490
    SMMARSARABARHYDRALISKSKULLHS = 1491
    SMMARSARABARCORKBOARDHS = 1492
    SMMARSARABARCORKBOARDBACKGROUND = 1493
    SMMARSARABARCORKBOARDITEM1HS = 1494
    SMMARSARABARCORKBOARDITEM2HS = 1495
    SMMARSARABARCORKBOARDITEM3HS = 1496
    SMMARSARABARCORKBOARDITEM4HS = 1497
    SMMARSARABARCORKBOARDITEM5HS = 1498
    SMMARSARABARCORKBOARDITEM6HS = 1499
    SMMARSARABARCORKBOARDITEM7HS = 1500
    SMMARSARABARCORKBOARDITEM8HS = 1501
    SMMARSARABARCORKBOARDITEM9HS = 1502
    SMMARSARABARBOTTLESHS = 1503
    SMVALERIANOBSERVATORYPROPS = 1504
    SMVALERIANOBSERVATORYSTARMAP = 1505
    SMBANSHEE = 1506
    SMVIKING = 1507
    SMARMORYBANSHEE = 1508
    SMARMORYDROPSHIP = 1509
    SMARMORYTANK = 1510
    SMARMORYVIKING = 1511
    SMARMORYSPIDERMINE = 1512
    SMARMORYGHOSTCRATE = 1513
    SMARMORYSPECTRECRATE = 1514
    SMARMORYBANSHEEPHCRATE = 1515
    SMARMORYDROPSHIPPHCRATE = 1516
    SMARMORYTANKPHCRATE = 1517
    SMARMORYVIKINGPHCRATE = 1518
    SMARMORYSPIDERMINEPHCRATE = 1519
    SMARMORYGHOSTCRATEPHCRATE = 1520
    SMARMORYSPECTRECRATEPHCRATE = 1521
    SMARMORYRIFLE = 1522
    SMDROPSHIP = 1523
    SMDROPSHIPBLUE = 1524
    SMHYPERIONARMORYVIKING = 1525
    SMCHARGATLINGGUN = 1526
    SMBOUNTYHUNTER = 1527
    SMCIVILIAN = 1528
    SMZERGEDHANSON = 1529
    SMLABASSISTANT = 1530
    SMHYPERIONARMORER = 1531
    SMUNNSCREEN = 1532
    NEWSARCTURUSINTERVIEWSET = 1533
    NEWSARCTURUSPRESSROOM = 1534
    SMDONNYVERMILLIONSET = 1535
    NEWSMEINHOFFREFUGEECENTER = 1536
    NEWSRAYNORLOGO = 1537
    NEWSTVEFFECT = 1538
    SMUNNCAMERA = 1539
    SMLEEKENOSET = 1540
    SMTVSTATIC = 1541
    SMDONNYVERMILLION = 1542
    SMDONNYVERMILLIONDEATH = 1543
    SMLEEKENO = 1544
    SMKATELOCKWELL = 1545
    SMMIKELIBERTY = 1546
    SMTERRANREADYROOMLEFTTV = 1547
    SMTERRANREADYROOMMAINTV = 1548
    SMTERRANREADYROOMRIGHTTV = 1549
    SMHYPERIONARMORYSTAGE1SET = 1550
    SMHYPERIONARMORYSTAGE1SET01 = 1551
    SMHYPERIONARMORYSTAGE1SET02 = 1552
    SMHYPERIONARMORYSTAGE1SET03 = 1553
    SMHYPERIONARMORYSPACELIGHTING = 1554
    SMHYPERIONARMORYSTAGE1TECHNOLOGYCONSOLEHS = 1555
    SMHYPERIONBRIDGESTAGE1BOW = 1556
    SMHYPERIONBRIDGESTAGE1SET = 1557
    SMHYPERIONBRIDGESTAGE1SET2 = 1558
    SMHYPERIONBRIDGESTAGE1SET3 = 1559
    SMHYPERIONBRIDGEHOLOMAP = 1560
    SMHYPERIONCANTINASTAGE1SET = 1561
    SMHYPERIONCANTINASTAGE1SET2 = 1562
    SMHYPERIONCANTINASTAGE1WALLPIECE = 1563
    SMHYPERIONBRIDGEPROPS = 1564
    SMHYPERIONCANTINAPROPS = 1565
    SMHYPERIONMEDLABPROPS = 1566
    SMHYPERIONMEDLABPROTOSSCRYOTUBE0HS = 1567
    SMHYPERIONMEDLABPROTOSSCRYOTUBE1HS = 1568
    SMHYPERIONMEDLABPROTOSSCRYOTUBE2HS = 1569
    SMHYPERIONMEDLABPROTOSSCRYOTUBE3HS = 1570
    SMHYPERIONMEDLABPROTOSSCRYOTUBE4HS = 1571
    SMHYPERIONMEDLABPROTOSSCRYOTUBE5HS = 1572
    SMHYPERIONMEDLABZERGCRYOTUBE0HS = 1573
    SMHYPERIONMEDLABZERGCRYOTUBE1HS = 1574
    SMHYPERIONMEDLABZERGCRYOTUBE2HS = 1575
    SMHYPERIONMEDLABZERGCRYOTUBE3HS = 1576
    SMHYPERIONMEDLABZERGCRYOTUBE4HS = 1577
    SMHYPERIONMEDLABZERGCRYOTUBE5HS = 1578
    SMHYPERIONMEDLABCRYOTUBEA = 1579
    SMHYPERIONMEDLABCRYOTUBEB = 1580
    SMHYPERIONCANTINASTAGE1EXITHS = 1581
    SMHYPERIONCANTINASTAGE1STAIRCASEHS = 1582
    SMHYPERIONCANTINASTAGE1TVHS = 1583
    SMHYPERIONCANTINASTAGE1ARCADEGAMEHS = 1584
    SMHYPERIONCANTINASTAGE1JUKEBOXHS = 1585
    SMHYPERIONCANTINASTAGE1CORKBOARDHS = 1586
    SMHYPERIONCANTINAPROGRESSFRAME = 1587
    SMHYPERIONCANTINAHYDRACLAWSHS = 1588
    SMHYPERIONCANTINAMERCCOMPUTERHS = 1589
    SMHYPERIONCANTINASTAGE1PROGRESS1HS = 1590
    SMHYPERIONCANTINASTAGE1PROGRESS2HS = 1591
    SMHYPERIONCANTINASTAGE1PROGRESS3HS = 1592
    SMHYPERIONCANTINASTAGE1PROGRESS4HS = 1593
    SMHYPERIONCANTINASTAGE1PROGRESS5HS = 1594
    SMHYPERIONCANTINASTAGE1PROGRESS6HS = 1595
    SMHYPERIONCORRIDORSET = 1596
    SMHYPERIONBRIDGESTAGE1BATTLEREPORTSHS = 1597
    SMHYPERIONBRIDGESTAGE1CENTERCONSOLEHS = 1598
    SMHYPERIONBRIDGESTAGE1BATTLECOMMANDHS = 1599
    SMHYPERIONBRIDGESTAGE1CANTINAHS = 1600
    SMHYPERIONBRIDGESTAGE1WINDOWHS = 1601
    SMHYPERIONMEDLABSTAGE1SET = 1602
    SMHYPERIONMEDLABSTAGE1SET2 = 1603
    SMHYPERIONMEDLABSTAGE1SETLIGHTS = 1604
    SMHYPERIONMEDLABSTAGE1CONSOLEHS = 1605
    SMHYPERIONMEDLABSTAGE1DOORHS = 1606
    SMHYPERIONMEDLABSTAGE1CRYSTALHS = 1607
    SMHYPERIONMEDLABSTAGE1ARTIFACTHS = 1608
    SMHYPERIONLABARTIFACTPART1HS = 1609
    SMHYPERIONLABARTIFACTPART2HS = 1610
    SMHYPERIONLABARTIFACTPART3HS = 1611
    SMHYPERIONLABARTIFACTPART4HS = 1612
    SMHYPERIONLABARTIFACTBASEHS = 1613
    SMSHADOWBOX = 1614
    SMCHARBATTLEZONESHADOWBOX = 1615
    SMCHARINTERACTIVESKYPARALLAX = 1616
    SMCHARINTERACTIVE02SKYPARALLAX = 1617
    SMRAYNORCOMMANDER = 1618
    SMADJUTANT = 1619
    SMADJUTANTHOLOGRAM = 1620
    SMMARAUDER = 1621
    SMFIREBAT = 1622
    SMMARAUDERPHCRATE = 1623
    SMFIREBATPHCRATE = 1624
    SMRAYNORMARINE = 1625
    SMMARINE01 = 1626
    SMMARINE02 = 1627
    SMMARINE02AOD = 1628
    SMMARINE03 = 1629
    SMMARINE04 = 1630
    SMCADE = 1631
    SMHALL = 1632
    SMBRALIK = 1633
    SMANNABELLE = 1634
    SMEARL = 1635
    SMKACHINSKY = 1636
    SMGENERICMALEGREASEMONKEY01 = 1637
    SMGENERICMALEGREASEMONKEY02 = 1638
    SMGENERICMALEOFFICER01 = 1639
    SMGENERICMALEOFFICER02 = 1640
    SMSTETMANN = 1641
    SMCOOPER = 1642
    SMHILL = 1643
    SMYBARRA = 1644
    SMVALERIANMENGSK = 1645
    SMARCTURUSMENGSK = 1646
    SMARCTURUSHOLOGRAM = 1647
    SMZERATUL = 1648
    SMHYDRALISK = 1649
    SMHYDRALISKDEAD = 1650
    SMMUTALISK = 1651
    SMZERGLING = 1652
    SCIENTIST = 1653
    MINERMALE = 1654
    CIVILIAN = 1655
    COLONIST = 1656
    CIVILIANFEMALE = 1657
    COLONISTFEMALE = 1658
    HUT = 1659
    COLONISTHUT = 1660
    INFESTABLEHUT = 1661
    INFESTABLECOLONISTHUT = 1662
    XELNAGASHRINEXIL = 1663
    PROTOSSRELIC = 1664
    PICKUPGRENADES = 1665
    PICKUPPLASMAGUN = 1666
    PICKUPPLASMAROUNDS = 1667
    PICKUPMEDICRECHARGE = 1668
    PICKUPMANARECHARGE = 1669
    PICKUPRESTORATIONCHARGE = 1670
    PICKUPCHRONORIFTDEVICE = 1671
    PICKUPCHRONORIFTCHARGE = 1672
    GASCANISTER = 1673
    GASCANISTERPROTOSS = 1674
    GASCANISTERZERG = 1675
    MINERALCRYSTAL = 1676
    PALLETGAS = 1677
    PALLETMINERALS = 1678
    NATURALGAS = 1679
    NATURALMINERALS = 1680
    NATURALMINERALSRED = 1681
    PICKUPHEALTH25 = 1682
    PICKUPHEALTH50 = 1683
    PICKUPHEALTH100 = 1684
    PICKUPHEALTHFULL = 1685
    PICKUPENERGY25 = 1686
    PICKUPENERGY50 = 1687
    PICKUPENERGY100 = 1688
    PICKUPENERGYFULL = 1689
    PICKUPMINES = 1690
    PICKUPPSISTORM = 1691
    CIVILIANCARSUNIT = 1692
    CRUISERBIKE = 1693
    TERRANBUGGY = 1694
    COLONISTVEHICLEUNIT = 1695
    COLONISTVEHICLEUNIT01 = 1696
    DUMPTRUCK = 1697
    TANKERTRUCK = 1698
    FLATBEDTRUCK = 1699
    COLONISTSHIPTHANSON02A = 1700
    PURIFIER = 1701
    INFESTEDARMORY = 1702
    INFESTEDBARRACKS = 1703
    INFESTEDBUNKER = 1704
    INFESTEDCC = 1705
    INFESTEDENGBAY = 1706
    INFESTEDFACTORY = 1707
    INFESTEDREFINERY = 1708
    INFESTEDSTARPORT = 1709
    INFESTEDMISSILETURRET = 1710
    LOGISTICSHEADQUARTERS = 1711
    INFESTEDSUPPLY = 1712
    TARSONISENGINE = 1713
    TARSONISENGINEFAST = 1714
    FREIGHTCAR = 1715
    CABOOSE = 1716
    HYPERION = 1717
    MENGSKHOLOGRAMBILLBOARD = 1718
    TRAYNOR01SIGNSDESTRUCTIBLE1 = 1719
    ABANDONEDBUILDING = 1720
    NOVA = 1721
    FOOD1000 = 1722
    PSIINDOCTRINATOR = 1723
    JORIUMSTOCKPILE = 1724
    ZERGDROPPOD = 1725
    TERRANDROPPOD = 1726
    COLONISTBIODOME = 1727
    COLONISTBIODOMEHALFBUILT = 1728
    INFESTABLEBIODOME = 1729
    INFESTABLECOLONISTBIODOME = 1730
    MEDIC = 1731
    VIKINGSKY_UNIT = 1732
    SS_FIGHTER = 1733
    SS_PHOENIX = 1734
    SS_CARRIER = 1735
    SS_BACKGROUNDZERG01 = 1736
    SS_BACKGROUNDSPACE00 = 1737
    SS_BACKGROUNDSPACE01 = 1738
    SS_BACKGROUNDSPACE02 = 1739
    SS_BACKGROUNDSPACEPROT00 = 1740
    SS_BACKGROUNDSPACEPROT01 = 1741
    SS_BACKGROUNDSPACEPROT02 = 1742
    SS_BACKGROUNDSPACEPROT03 = 1743
    SS_BACKGROUNDSPACEPROT04 = 1744
    SS_BACKGROUNDSPACEPROTOSSLARGE = 1745
    SS_BACKGROUNDSPACEZERGLARGE = 1746
    SS_BACKGROUNDSPACETERRANLARGE = 1747
    SS_BACKGROUNDSPACEZERG01 = 1748
    SS_BACKGROUNDSPACETERRAN01 = 1749
    BREACHINGCHARGE = 1750
    INFESTATIONSPIRE = 1751
    SPACEPLATFORMVENTSUNIT = 1752
    STONEZEALOT = 1753
    PRESERVERPRISON = 1754
    PORTJUNKER = 1755
    LEVIATHAN = 1756
    SWARMLING = 1757
    VALHALLADESTRUCTIBLEWALL = 1758
    NEWFOLSOMPRISONENTRANCE = 1759
    ODINBUILD = 1760
    NUKEPACK = 1761
    CHARDESTRUCTIBLEROCKCOVER = 1762
    CHARDESTRUCTIBLEROCKCOVERV = 1763
    CHARDESTRUCTIBLEROCKCOVERULDR = 1764
    CHARDESTRUCTIBLEROCKCOVERURDL = 1765
    MAARWARPINUNIT = 1766
    EGGPURPLE = 1767
    TRUCKFLATBEDUNIT = 1768
    TRUCKSEMIUNIT = 1769
    TRUCKUTILITYUNIT = 1770
    INFESTEDCOLONISTSHIP = 1771
    CASTANARDESTRUCTIBLEDEBRIS = 1772
    COLONISTTRANSPORT = 1773
    PRESERVERBASE = 1774
    PRESERVERA = 1775
    PRESERVERB = 1776
    PRESERVERC = 1777
    TAURENSPACEMARINE = 1778
    MARSARABRIDGEBLUR = 1779
    MARSARABRIDGEBRUL = 1780
    SHORTBRIDGEVERTICAL = 1781
    SHORTBRIDGEHORIZONTAL = 1782
    TESTHERO = 1783
    TESTSHOP = 1784
    HEALINGPOTIONTESTTARGET = 1785
    _4SLOTBAG = 1786
    _6SLOTBAG = 1787
    _8SLOTBAG = 1788
    _10SLOTBAG = 1789
    _12SLOTBAG = 1790
    _14SLOTBAG = 1791
    _16SLOTBAG = 1792
    _18SLOTBAG = 1793
    _20SLOTBAG = 1794
    _22SLOTBAG = 1795
    _24SLOTBAG = 1796
    REPULSERFIELD6 = 1797
    REPULSERFIELD8 = 1798
    REPULSERFIELD10 = 1799
    REPULSERFIELD12 = 1800
    DESTRUCTIBLEWALLCORNER45ULBL = 1801
    DESTRUCTIBLEWALLCORNER45ULUR = 1802
    DESTRUCTIBLEWALLCORNER45URBR = 1803
    DESTRUCTIBLEWALLCORNER45 = 1804
    DESTRUCTIBLEWALLCORNER45UR90L = 1805
    DESTRUCTIBLEWALLCORNER45UL90B = 1806
    DESTRUCTIBLEWALLCORNER45BL90R = 1807
    DESTRUCTIBLEWALLCORNER45BR90T = 1808
    DESTRUCTIBLEWALLCORNER90L45BR = 1809
    DESTRUCTIBLEWALLCORNER90T45BL = 1810
    DESTRUCTIBLEWALLCORNER90R45UL = 1811
    DESTRUCTIBLEWALLCORNER90B45UR = 1812
    DESTRUCTIBLEWALLCORNER90TR = 1813
    DESTRUCTIBLEWALLCORNER90BR = 1814
    DESTRUCTIBLEWALLCORNER90LB = 1815
    DESTRUCTIBLEWALLCORNER90LT = 1816
    DESTRUCTIBLEWALLDIAGONALBLUR = 1817
    DESTRUCTIBLEWALLDIAGONALBLURLF = 1818
    DESTRUCTIBLEWALLDIAGONALULBRLF = 1819
    DESTRUCTIBLEWALLDIAGONALULBR = 1820
    DESTRUCTIBLEWALLSTRAIGHTVERTICAL = 1821
    DESTRUCTIBLEWALLVERTICALLF = 1822
    DESTRUCTIBLEWALLSTRAIGHTHORIZONTAL = 1823
    DESTRUCTIBLEWALLSTRAIGHTHORIZONTALBF = 1824
    DEFENSEWALLE = 1825
    DEFENSEWALLS = 1826
    DEFENSEWALLW = 1827
    DEFENSEWALLN = 1828
    DEFENSEWALLNE = 1829
    DEFENSEWALLSW = 1830
    DEFENSEWALLNW = 1831
    DEFENSEWALLSE = 1832
    WRECKEDBATTLECRUISERHELIOSFINAL = 1833
    FIREWORKSBLUE = 1834
    FIREWORKSRED = 1835
    FIREWORKSYELLOW = 1836
    PURIFIERBLASTMARKUNIT = 1837
    ITEMGRAVITYBOMBS = 1838
    ITEMGRENADES = 1839
    ITEMMEDKIT = 1840
    ITEMMINES = 1841
    REAPERPLACEMENT = 1842
    QUEENZAGARAACGLUESCREENDUMMY = 1843
    OVERSEERZAGARAACGLUESCREENDUMMY = 1844
    STUKOVINFESTEDCIVILIANACGLUESCREENDUMMY = 1845
    STUKOVINFESTEDMARINEACGLUESCREENDUMMY = 1846
    STUKOVINFESTEDSIEGETANKACGLUESCREENDUMMY = 1847
    STUKOVINFESTEDDIAMONDBACKACGLUESCREENDUMMY = 1848
    STUKOVINFESTEDBANSHEEACGLUESCREENDUMMY = 1849
    SILIBERATORACGLUESCREENDUMMY = 1850
    STUKOVINFESTEDBUNKERACGLUESCREENDUMMY = 1851
    STUKOVINFESTEDMISSILETURRETACGLUESCREENDUMMY = 1852
    STUKOVBROODQUEENACGLUESCREENDUMMY = 1853
    ZEALOTFENIXACGLUESCREENDUMMY = 1854
    SENTRYFENIXACGLUESCREENDUMMY = 1855
    ADEPTFENIXACGLUESCREENDUMMY = 1856
    IMMORTALFENIXACGLUESCREENDUMMY = 1857
    COLOSSUSFENIXACGLUESCREENDUMMY = 1858
    DISRUPTORACGLUESCREENDUMMY = 1859
    OBSERVERFENIXACGLUESCREENDUMMY = 1860
    SCOUTACGLUESCREENDUMMY = 1861
    CARRIERFENIXACGLUESCREENDUMMY = 1862
    PHOTONCANNONFENIXACGLUESCREENDUMMY = 1863
    PRIMALZERGLINGACGLUESCREENDUMMY = 1864
    RAVASAURACGLUESCREENDUMMY = 1865
    PRIMALROACHACGLUESCREENDUMMY = 1866
    FIREROACHACGLUESCREENDUMMY = 1867
    PRIMALGUARDIANACGLUESCREENDUMMY = 1868
    PRIMALHYDRALISKACGLUESCREENDUMMY = 1869
    PRIMALMUTALISKACGLUESCREENDUMMY = 1870
    PRIMALIMPALERACGLUESCREENDUMMY = 1871
    PRIMALSWARMHOSTACGLUESCREENDUMMY = 1872
    CREEPERHOSTACGLUESCREENDUMMY = 1873
    PRIMALULTRALISKACGLUESCREENDUMMY = 1874
    TYRANNOZORACGLUESCREENDUMMY = 1875
    PRIMALWURMACGLUESCREENDUMMY = 1876
    HHREAPERACGLUESCREENDUMMY = 1877
    HHWIDOWMINEACGLUESCREENDUMMY = 1878
    HHHELLIONTANKACGLUESCREENDUMMY = 1879
    HHWRAITHACGLUESCREENDUMMY = 1880
    HHVIKINGACGLUESCREENDUMMY = 1881
    HHBATTLECRUISERACGLUESCREENDUMMY = 1882
    HHRAVENACGLUESCREENDUMMY = 1883
    HHBOMBERPLATFORMACGLUESCREENDUMMY = 1884
    HHMERCSTARPORTACGLUESCREENDUMMY = 1885
    HHMISSILETURRETACGLUESCREENDUMMY = 1886
    HIGHTEMPLARSKINPREVIEW = 1887
    WARPPRISMSKINPREVIEW = 1888
    SIEGETANKSKINPREVIEW = 1889
    LIBERATORSKINPREVIEW = 1890
    VIKINGSKINPREVIEW = 1891
    STUKOVINFESTEDTROOPERACGLUESCREENDUMMY = 1892
    XELNAGADESTRUCTIBLEBLOCKER6S = 1893
    XELNAGADESTRUCTIBLEBLOCKER6SE = 1894
    XELNAGADESTRUCTIBLEBLOCKER6E = 1895
    XELNAGADESTRUCTIBLEBLOCKER6NE = 1896
    XELNAGADESTRUCTIBLEBLOCKER6N = 1897
    XELNAGADESTRUCTIBLEBLOCKER6NW = 1898
    XELNAGADESTRUCTIBLEBLOCKER6W = 1899
    XELNAGADESTRUCTIBLEBLOCKER6SW = 1900
    XELNAGADESTRUCTIBLEBLOCKER8S = 1901
    XELNAGADESTRUCTIBLEBLOCKER8SE = 1902
    XELNAGADESTRUCTIBLEBLOCKER8E = 1903
    XELNAGADESTRUCTIBLEBLOCKER8NE = 1904
    XELNAGADESTRUCTIBLEBLOCKER8N = 1905
    XELNAGADESTRUCTIBLEBLOCKER8NW = 1906
    XELNAGADESTRUCTIBLEBLOCKER8W = 1907
    XELNAGADESTRUCTIBLEBLOCKER8SW = 1908
    SNOWGLAZESTARTERMP = 1909
    SHIELDBATTERY = 1910
    OBSERVERSIEGEMODE = 1911
    OVERSEERSIEGEMODE = 1912
    RAVENREPAIRDRONE = 1913
    HIGHTEMPLARWEAPONMISSILE = 1914
    CYCLONEMISSILELARGEAIRALTERNATIVE = 1915
    RAVENSCRAMBLERMISSILE = 1916
    RAVENREPAIRDRONERELEASEWEAPON = 1917
    RAVENSHREDDERMISSILEWEAPON = 1918
    INFESTEDACIDSPINESWEAPON = 1919
    INFESTORENSNAREATTACKMISSILE = 1920
    SNARE_PLACEHOLDER = 1921
    TYCHUSREAPERACGLUESCREENDUMMY = 1922
    TYCHUSFIREBATACGLUESCREENDUMMY = 1923
    TYCHUSSPECTREACGLUESCREENDUMMY = 1924
    TYCHUSMEDICACGLUESCREENDUMMY = 1925
    TYCHUSMARAUDERACGLUESCREENDUMMY = 1926
    TYCHUSWARHOUNDACGLUESCREENDUMMY = 1927
    TYCHUSHERCACGLUESCREENDUMMY = 1928
    TYCHUSGHOSTACGLUESCREENDUMMY = 1929
    TYCHUSSCVAUTOTURRETACGLUESCREENDUMMY = 1930
    ZERATULSTALKERACGLUESCREENDUMMY = 1931
    ZERATULSENTRYACGLUESCREENDUMMY = 1932
    ZERATULDARKTEMPLARACGLUESCREENDUMMY = 1933
    ZERATULIMMORTALACGLUESCREENDUMMY = 1934
    ZERATULOBSERVERACGLUESCREENDUMMY = 1935
    ZERATULDISRUPTORACGLUESCREENDUMMY = 1936
    ZERATULWARPPRISMACGLUESCREENDUMMY = 1937
    ZERATULPHOTONCANNONACGLUESCREENDUMMY = 1938
    RENEGADELONGBOLTMISSILEWEAPON = 1939
    VIKING = 1940
    RENEGADEMISSILETURRET = 1941
    PARASITICBOMBRELAYDUMMY = 1942
    REFINERYRICH = 1943
    MECHAZERGLINGACGLUESCREENDUMMY = 1944
    MECHABANELINGACGLUESCREENDUMMY = 1945
    MECHAHYDRALISKACGLUESCREENDUMMY = 1946
    MECHAINFESTORACGLUESCREENDUMMY = 1947
    MECHACORRUPTORACGLUESCREENDUMMY = 1948
    MECHAULTRALISKACGLUESCREENDUMMY = 1949
    MECHAOVERSEERACGLUESCREENDUMMY = 1950
    MECHALURKERACGLUESCREENDUMMY = 1951
    MECHABATTLECARRIERLORDACGLUESCREENDUMMY = 1952
    MECHASPINECRAWLERACGLUESCREENDUMMY = 1953
    MECHASPORECRAWLERACGLUESCREENDUMMY = 1954
    TROOPERMENGSKACGLUESCREENDUMMY = 1955
    MEDIVACMENGSKACGLUESCREENDUMMY = 1956
    BLIMPMENGSKACGLUESCREENDUMMY = 1957
    MARAUDERMENGSKACGLUESCREENDUMMY = 1958
    GHOSTMENGSKACGLUESCREENDUMMY = 1959
    SIEGETANKMENGSKACGLUESCREENDUMMY = 1960
    THORMENGSKACGLUESCREENDUMMY = 1961
    VIKINGMENGSKACGLUESCREENDUMMY = 1962
    BATTLECRUISERMENGSKACGLUESCREENDUMMY = 1963
    BUNKERDEPOTMENGSKACGLUESCREENDUMMY = 1964
    MISSILETURRETMENGSKACGLUESCREENDUMMY = 1965
    ARTILLERYMENGSKACGLUESCREENDUMMY = 1966
    LOADOUTSPRAY1 = 1967
    LOADOUTSPRAY2 = 1968
    LOADOUTSPRAY3 = 1969
    LOADOUTSPRAY4 = 1970
    LOADOUTSPRAY5 = 1971
    LOADOUTSPRAY6 = 1972
    LOADOUTSPRAY7 = 1973
    LOADOUTSPRAY8 = 1974
    LOADOUTSPRAY9 = 1975
    LOADOUTSPRAY10 = 1976
    LOADOUTSPRAY11 = 1977
    LOADOUTSPRAY12 = 1978
    LOADOUTSPRAY13 = 1979
    LOADOUTSPRAY14 = 1980
    PREVIEWBUNKERUPGRADED = 1981
    INHIBITORZONESMALL = 1982
    INHIBITORZONEMEDIUM = 1983
    INHIBITORZONELARGE = 1984
    ACCELERATIONZONESMALL = 1985
    ACCELERATIONZONEMEDIUM = 1986
    ACCELERATIONZONELARGE = 1987
    ACCELERATIONZONEFLYINGSMALL = 1988
    ACCELERATIONZONEFLYINGMEDIUM = 1989
    ACCELERATIONZONEFLYINGLARGE = 1990
    INHIBITORZONEFLYINGSMALL = 1991
    INHIBITORZONEFLYINGMEDIUM = 1992
    INHIBITORZONEFLYINGLARGE = 1993
    ASSIMILATORRICH = 1994
    EXTRACTORRICH = 1995
    MINERALFIELD450 = 1996
    MINERALFIELDOPAQUE = 1997
    MINERALFIELDOPAQUE900 = 1998
    COLLAPSIBLEROCKTOWERDEBRISRAMPLEFTGREEN = 1999
    COLLAPSIBLEROCKTOWERDEBRISRAMPRIGHTGREEN = 2000
    COLLAPSIBLEROCKTOWERPUSHUNITRAMPLEFTGREEN = 2001
    COLLAPSIBLEROCKTOWERPUSHUNITRAMPRIGHTGREEN = 2002
    COLLAPSIBLEROCKTOWERRAMPLEFTGREEN = 2003
    COLLAPSIBLEROCKTOWERRAMPRIGHTGREEN = 2004

    def __repr__(self) -> str:
        return f"UnitTypeId.{self.name}"


for item in UnitTypeId:
    globals()[item.name] = item
```

### File: `sc2/ids/upgrade_id.py`

```python
# pyre-ignore-all-errors[14]
from __future__ import annotations

# DO NOT EDIT!
# This file was automatically generated by "generate_ids.py"
import enum


class UpgradeId(enum.Enum):
    NULL = 0
    CARRIERLAUNCHSPEEDUPGRADE = 1
    GLIALRECONSTITUTION = 2
    TUNNELINGCLAWS = 3
    CHITINOUSPLATING = 4
    HISECAUTOTRACKING = 5
    TERRANBUILDINGARMOR = 6
    TERRANINFANTRYWEAPONSLEVEL1 = 7
    TERRANINFANTRYWEAPONSLEVEL2 = 8
    TERRANINFANTRYWEAPONSLEVEL3 = 9
    NEOSTEELFRAME = 10
    TERRANINFANTRYARMORSLEVEL1 = 11
    TERRANINFANTRYARMORSLEVEL2 = 12
    TERRANINFANTRYARMORSLEVEL3 = 13
    REAPERSPEED = 14
    STIMPACK = 15
    SHIELDWALL = 16
    PUNISHERGRENADES = 17
    SIEGETECH = 18
    HIGHCAPACITYBARRELS = 19
    BANSHEECLOAK = 20
    MEDIVACCADUCEUSREACTOR = 21
    RAVENCORVIDREACTOR = 22
    HUNTERSEEKER = 23
    DURABLEMATERIALS = 24
    PERSONALCLOAKING = 25
    GHOSTMOEBIUSREACTOR = 26
    TERRANVEHICLEARMORSLEVEL1 = 27
    TERRANVEHICLEARMORSLEVEL2 = 28
    TERRANVEHICLEARMORSLEVEL3 = 29
    TERRANVEHICLEWEAPONSLEVEL1 = 30
    TERRANVEHICLEWEAPONSLEVEL2 = 31
    TERRANVEHICLEWEAPONSLEVEL3 = 32
    TERRANSHIPARMORSLEVEL1 = 33
    TERRANSHIPARMORSLEVEL2 = 34
    TERRANSHIPARMORSLEVEL3 = 35
    TERRANSHIPWEAPONSLEVEL1 = 36
    TERRANSHIPWEAPONSLEVEL2 = 37
    TERRANSHIPWEAPONSLEVEL3 = 38
    PROTOSSGROUNDWEAPONSLEVEL1 = 39
    PROTOSSGROUNDWEAPONSLEVEL2 = 40
    PROTOSSGROUNDWEAPONSLEVEL3 = 41
    PROTOSSGROUNDARMORSLEVEL1 = 42
    PROTOSSGROUNDARMORSLEVEL2 = 43
    PROTOSSGROUNDARMORSLEVEL3 = 44
    PROTOSSSHIELDSLEVEL1 = 45
    PROTOSSSHIELDSLEVEL2 = 46
    PROTOSSSHIELDSLEVEL3 = 47
    OBSERVERGRAVITICBOOSTER = 48
    GRAVITICDRIVE = 49
    EXTENDEDTHERMALLANCE = 50
    HIGHTEMPLARKHAYDARINAMULET = 51
    PSISTORMTECH = 52
    ZERGMELEEWEAPONSLEVEL1 = 53
    ZERGMELEEWEAPONSLEVEL2 = 54
    ZERGMELEEWEAPONSLEVEL3 = 55
    ZERGGROUNDARMORSLEVEL1 = 56
    ZERGGROUNDARMORSLEVEL2 = 57
    ZERGGROUNDARMORSLEVEL3 = 58
    ZERGMISSILEWEAPONSLEVEL1 = 59
    ZERGMISSILEWEAPONSLEVEL2 = 60
    ZERGMISSILEWEAPONSLEVEL3 = 61
    OVERLORDSPEED = 62
    OVERLORDTRANSPORT = 63
    BURROW = 64
    ZERGLINGATTACKSPEED = 65
    ZERGLINGMOVEMENTSPEED = 66
    HYDRALISKSPEED = 67
    ZERGFLYERWEAPONSLEVEL1 = 68
    ZERGFLYERWEAPONSLEVEL2 = 69
    ZERGFLYERWEAPONSLEVEL3 = 70
    ZERGFLYERARMORSLEVEL1 = 71
    ZERGFLYERARMORSLEVEL2 = 72
    ZERGFLYERARMORSLEVEL3 = 73
    INFESTORENERGYUPGRADE = 74
    CENTRIFICALHOOKS = 75
    BATTLECRUISERENABLESPECIALIZATIONS = 76
    BATTLECRUISERBEHEMOTHREACTOR = 77
    PROTOSSAIRWEAPONSLEVEL1 = 78
    PROTOSSAIRWEAPONSLEVEL2 = 79
    PROTOSSAIRWEAPONSLEVEL3 = 80
    PROTOSSAIRARMORSLEVEL1 = 81
    PROTOSSAIRARMORSLEVEL2 = 82
    PROTOSSAIRARMORSLEVEL3 = 83
    WARPGATERESEARCH = 84
    HALTECH = 85
    CHARGE = 86
    BLINKTECH = 87
    ANABOLICSYNTHESIS = 88
    OBVERSEINCUBATION = 89
    VIKINGJOTUNBOOSTERS = 90
    ORGANICCARAPACE = 91
    INFESTORPERISTALSIS = 92
    ABDOMINALFORTITUDE = 93
    HYDRALISKSPEEDUPGRADE = 94
    BANELINGBURROWMOVE = 95
    COMBATDRUGS = 96
    STRIKECANNONS = 97
    TRANSFORMATIONSERVOS = 98
    PHOENIXRANGEUPGRADE = 99
    TEMPESTRANGEUPGRADE = 100
    NEURALPARASITE = 101
    LOCUSTLIFETIMEINCREASE = 102
    ULTRALISKBURROWCHARGEUPGRADE = 103
    ORACLEENERGYUPGRADE = 104
    RESTORESHIELDS = 105
    PROTOSSHEROSHIPWEAPON = 106
    PROTOSSHEROSHIPDETECTOR = 107
    PROTOSSHEROSHIPSPELL = 108
    REAPERJUMP = 109
    INCREASEDRANGE = 110
    ZERGBURROWMOVE = 111
    ANIONPULSECRYSTALS = 112
    TERRANVEHICLEANDSHIPWEAPONSLEVEL1 = 113
    TERRANVEHICLEANDSHIPWEAPONSLEVEL2 = 114
    TERRANVEHICLEANDSHIPWEAPONSLEVEL3 = 115
    TERRANVEHICLEANDSHIPARMORSLEVEL1 = 116
    TERRANVEHICLEANDSHIPARMORSLEVEL2 = 117
    TERRANVEHICLEANDSHIPARMORSLEVEL3 = 118
    FLYINGLOCUSTS = 119
    ROACHSUPPLY = 120
    IMMORTALREVIVE = 121
    DRILLCLAWS = 122
    CYCLONELOCKONRANGEUPGRADE = 123
    CYCLONEAIRUPGRADE = 124
    LIBERATORMORPH = 125
    ADEPTSHIELDUPGRADE = 126
    LURKERRANGE = 127
    IMMORTALBARRIER = 128
    ADEPTKILLBOUNCE = 129
    ADEPTPIERCINGATTACK = 130
    CINEMATICMODE = 131
    CURSORDEBUG = 132
    MAGFIELDLAUNCHERS = 133
    EVOLVEGROOVEDSPINES = 134
    EVOLVEMUSCULARAUGMENTS = 135
    BANSHEESPEED = 136
    MEDIVACRAPIDDEPLOYMENT = 137
    RAVENRECALIBRATEDEXPLOSIVES = 138
    MEDIVACINCREASESPEEDBOOST = 139
    LIBERATORAGRANGEUPGRADE = 140
    DARKTEMPLARBLINKUPGRADE = 141
    RAVAGERRANGE = 142
    RAVENDAMAGEUPGRADE = 143
    CYCLONELOCKONDAMAGEUPGRADE = 144
    ARESCLASSWEAPONSSYSTEMVIKING = 145
    AUTOHARVESTER = 146
    HYBRIDCPLASMAUPGRADEHARD = 147
    HYBRIDCPLASMAUPGRADEINSANE = 148
    INTERCEPTORLIMIT4 = 149
    INTERCEPTORLIMIT6 = 150
    _330MMBARRAGECANNONS = 151
    NOTPOSSIBLESIEGEMODE = 152
    NEOSTEELFRAME_2 = 153
    NEOSTEELANDSHRIKETURRETICONUPGRADE = 154
    OCULARIMPLANTS = 155
    CROSSSPECTRUMDAMPENERS = 156
    ORBITALSTRIKE = 157
    CLUSTERBOMB = 158
    SHAPEDHULL = 159
    SPECTRETOOLTIPUPGRADE = 160
    ULTRACAPACITORS = 161
    VANADIUMPLATING = 162
    COMMANDCENTERREACTOR = 163
    REGENERATIVEBIOSTEEL = 164
    CELLULARREACTORS = 165
    BANSHEECLOAKEDDAMAGE = 166
    DISTORTIONBLASTERS = 167
    EMPTOWER = 168
    SUPPLYDEPOTDROP = 169
    HIVEMINDEMULATOR = 170
    FORTIFIEDBUNKERCARAPACE = 171
    PREDATOR = 172
    SCIENCEVESSEL = 173
    DUALFUSIONWELDERS = 174
    ADVANCEDCONSTRUCTION = 175
    ADVANCEDMEDICTRAINING = 176
    PROJECTILEACCELERATORS = 177
    REINFORCEDSUPERSTRUCTURE = 178
    MULE = 179
    ORBITALRELAY = 180
    RAZORWIRE = 181
    ADVANCEDHEALINGAI = 182
    TWINLINKEDFLAMETHROWERS = 183
    NANOCONSTRUCTOR = 184
    CERBERUSMINES = 185
    HYPERFLUXOR = 186
    TRILITHIUMPOWERCELLS = 187
    PERMANENTCLOAKGHOST = 188
    PERMANENTCLOAKSPECTRE = 189
    ULTRASONICPULSE = 190
    SURVIVALPODS = 191
    ENERGYSTORAGE = 192
    FULLBORECANISTERAMMO = 193
    CAMPAIGNJOTUNBOOSTERS = 194
    MICROFILTERING = 195
    PARTICLECANNONAIR = 196
    VULTUREAUTOREPAIR = 197
    PSIDISRUPTOR = 198
    SCIENCEVESSELENERGYMANIPULATION = 199
    SCIENCEVESSELPLASMAWEAPONRY = 200
    SHOWGATLINGGUN = 201
    TECHREACTOR = 202
    TECHREACTORAI = 203
    TERRANDEFENSERANGEBONUS = 204
    X88TNAPALMUPGRADE = 205
    HURRICANEMISSILES = 206
    MECHANICALREBIRTH = 207
    MARINESTIMPACK = 208
    DARKTEMPLARTACTICS = 209
    CLUSTERWARHEADS = 210
    CLOAKDISTORTIONFIELD = 211
    DEVASTATORMISSILES = 212
    DISTORTIONTHRUSTERS = 213
    DYNAMICPOWERROUTING = 214
    IMPALERROUNDS = 215
    KINETICFIELDS = 216
    BURSTCAPACITORS = 217
    HAILSTORMMISSILEPODS = 218
    RAPIDDEPLOYMENT = 219
    REAPERSTIMPACK = 220
    REAPERD8CHARGE = 221
    TYCHUS05BATTLECRUISERPENETRATION = 222
    VIRALPLASMA = 223
    FIREBATJUGGERNAUTPLATING = 224
    MULTILOCKTARGETINGSYSTEMS = 225
    TURBOCHARGEDENGINES = 226
    DISTORTIONSENSORS = 227
    INFERNALPREIGNITERS = 228
    HELLIONCAMPAIGNINFERNALPREIGNITER = 229
    NAPALMFUELTANKS = 230
    AUXILIARYMEDBOTS = 231
    JUGGERNAUTPLATING = 232
    MARAUDERLIFEBOOST = 233
    COMBATSHIELD = 234
    REAPERU238ROUNDS = 235
    MAELSTROMROUNDS = 236
    SIEGETANKSHAPEDBLAST = 237
    TUNGSTENSPIKES = 238
    BEARCLAWNOZZLES = 239
    NANOBOTINJECTORS = 240
    STABILIZERMEDPACKS = 241
    HALOROCKETS = 242
    SCAVENGINGSYSTEMS = 243
    EXTRAMINES = 244
    ARESCLASSWEAPONSSYSTEM = 245
    WHITENAPALM = 246
    VIRALMUNITIONS = 247
    JACKHAMMERCONCUSSIONGRENADES = 248
    FIRESUPPRESSIONSYSTEMS = 249
    FLARERESEARCH = 250
    MODULARCONSTRUCTION = 251
    EXPANDEDHULL = 252
    SHRIKETURRET = 253
    MICROFUSIONREACTORS = 254
    WRAITHCLOAK = 255
    SINGULARITYCHARGE = 256
    GRAVITICTHRUSTERS = 257
    YAMATOCANNON = 258
    DEFENSIVEMATRIX = 259
    DARKPROTOSS = 260
    TERRANINFANTRYWEAPONSULTRACAPACITORSLEVEL1 = 261
    TERRANINFANTRYWEAPONSULTRACAPACITORSLEVEL2 = 262
    TERRANINFANTRYWEAPONSULTRACAPACITORSLEVEL3 = 263
    TERRANINFANTRYARMORSVANADIUMPLATINGLEVEL1 = 264
    TERRANINFANTRYARMORSVANADIUMPLATINGLEVEL2 = 265
    TERRANINFANTRYARMORSVANADIUMPLATINGLEVEL3 = 266
    TERRANVEHICLEWEAPONSULTRACAPACITORSLEVEL1 = 267
    TERRANVEHICLEWEAPONSULTRACAPACITORSLEVEL2 = 268
    TERRANVEHICLEWEAPONSULTRACAPACITORSLEVEL3 = 269
    TERRANVEHICLEARMORSVANADIUMPLATINGLEVEL1 = 270
    TERRANVEHICLEARMORSVANADIUMPLATINGLEVEL2 = 271
    TERRANVEHICLEARMORSVANADIUMPLATINGLEVEL3 = 272
    TERRANSHIPWEAPONSULTRACAPACITORSLEVEL1 = 273
    TERRANSHIPWEAPONSULTRACAPACITORSLEVEL2 = 274
    TERRANSHIPWEAPONSULTRACAPACITORSLEVEL3 = 275
    TERRANSHIPARMORSVANADIUMPLATINGLEVEL1 = 276
    TERRANSHIPARMORSVANADIUMPLATINGLEVEL2 = 277
    TERRANSHIPARMORSVANADIUMPLATINGLEVEL3 = 278
    HIREKELMORIANMINERSPH = 279
    HIREDEVILDOGSPH = 280
    HIRESPARTANCOMPANYPH = 281
    HIREHAMMERSECURITIESPH = 282
    HIRESIEGEBREAKERSPH = 283
    HIREHELSANGELSPH = 284
    HIREDUSKWINGPH = 285
    HIREDUKESREVENGE = 286
    TOSHEASYMODE = 287
    VOIDRAYSPEEDUPGRADE = 288
    SMARTSERVOS = 289
    ARMORPIERCINGROCKETS = 290
    CYCLONERAPIDFIRELAUNCHERS = 291
    RAVENENHANCEDMUNITIONS = 292
    DIGGINGCLAWS = 293
    CARRIERCARRIERCAPACITY = 294
    CARRIERLEASHRANGEUPGRADE = 295
    HURRICANETHRUSTERS = 296
    TEMPESTGROUNDATTACKUPGRADE = 297
    FRENZY = 298
    MICROBIALSHROUD = 299
    INTERFERENCEMATRIX = 300
    SUNDERINGIMPACT = 301
    AMPLIFIEDSHIELDING = 302
    PSIONICAMPLIFIERS = 303
    SECRETEDCOATING = 304
    ENHANCEDSHOCKWAVES = 305

    def __repr__(self) -> str:
        return f"UpgradeId.{self.name}"


for item in UpgradeId:
    globals()[item.name] = item
```
```

---

### File: `run.py`

```python
from sc2 import maps
from sc2.data import Difficulty, Race
from sc2.main import run_game
from sc2.player import Bot, Computer

from sajuuk import Sajuuk


def main():
    """
    Sets up and runs a single game of StarCraft II with the Sajuuk bot.

    This file is the primary entry point for testing the bot locally.
    It configures the map, the players (our bot vs. a computer),
    and launches the game.
    """
    # Use try-except to handle potential game launch errors gracefully.
    try:
        run_game(
            # maps.get() is a utility function to find a map by its name.
            # We are selecting "AbyssalReefLE", a standard ladder map.
            maps.get("AbyssalReefLE"),
            # Define the players. We are Player 1, a bot running our Sajuuk AI.
            [
                Bot(Race.Terran, Sajuuk(), name="Sajuuk"),
                # Player 2 is a computer opponent with an "Easy" difficulty.
                # This is ideal for initial testing and build order validation.
                Computer(Race.Zerg, Difficulty.Hard),
            ],
            # Set realtime=False to run the game as fast as possible.
            # This is standard for bot development and testing.
            realtime=False,
            # Optional: Specify a path to save the replay file.
            # This is extremely useful for debugging and analysis.
            save_replay_as="Sajuuk-vs-EasyZerg.SC2Replay",
        )
    except Exception as e:
        print(f"An error occurred while running the game: {e}")
        # This could be due to a missing map file, a configuration issue,
        # or an error within the bot's on_start() method.
        # Adding more detailed logging here would be a future improvement.


if __name__ == "__main__":
    main()
```

---

### File: `sajuuk.py`

```python
# sajuuk.py
import asyncio
from typing import TYPE_CHECKING, List

from sc2.bot_ai import BotAI
from sc2.data import Race
from sc2.unit import Unit

from core.global_cache import GlobalCache
from core.game_analysis import GameAnalyzer
from core.frame_plan import FramePlan
from core.types import CommandFunctor
from core.interfaces.race_general_abc import RaceGeneral
from core.utilities.events import (
    Event,
    EventType,
    UnitDestroyedPayload,
    EnemyUnitSeenPayload,
)
from terran.general.terran_general import TerranGeneral

if TYPE_CHECKING:
    from core.event_bus import EventBus


class Sajuuk(BotAI):
    """The Conductor. Orchestrates the main Perceive-Analyze-Plan-Act loop."""

    def __init__(self):
        super().__init__()
        self.global_cache = GlobalCache()
        self.logger = self.global_cache.logger
        self.event_bus: "EventBus" = self.global_cache.event_bus
        self.game_analyzer = GameAnalyzer(self.event_bus)
        self.active_general: RaceGeneral | None = None

    async def on_start(self):
        if self.race == Race.Terran:
            self.active_general = TerranGeneral(self)
        else:
            raise NotImplementedError(f"Sajuuk does not support race: {self.race}")
        if self.active_general:
            await self.active_general.on_start()

    async def on_enemy_unit_entered_vision(self, unit: Unit):
        self.event_bus.publish(
            Event(EventType.TACTICS_ENEMY_UNIT_SEEN, EnemyUnitSeenPayload(unit))
        )

    async def on_unit_destroyed(self, unit_tag: int):
        unit = self._all_units_previous_map.get(unit_tag)
        if not unit:
            return
        self.event_bus.publish(
            Event(
                EventType.UNIT_DESTROYED,
                UnitDestroyedPayload(unit.tag, unit.type_id, unit.position),
            )
        )

    async def on_step(self, iteration: int):
        game_time = self.time_formatted
        log = self.logger.bind(game_time=game_time)

        log.debug(f"--- Step {iteration} Start ---")

        await self.event_bus.process_events()

        self.game_analyzer.run(self)

        # 3. CACHE: Populate the GlobalCache with a consistent snapshot for this frame.
        # CHANGED: Pass the 'iteration' variable to the update method.
        self.global_cache.update(self, self.game_analyzer, iteration)

        log.info(
            f"Cache Updated. Army Value: {self.global_cache.friendly_army_value} (F) vs "
            f"{self.global_cache.enemy_army_value} (E). Supply: {self.global_cache.supply_used}/{self.global_cache.supply_cap}"
        )

        frame_plan = FramePlan()

        command_functors: list[CommandFunctor] = await self.active_general.execute_step(
            self.global_cache, frame_plan, self.event_bus
        )

        log.info(
            f"Plan Generated. Budget: [I:{frame_plan.resource_budget.infrastructure}, C:{frame_plan.resource_budget.capabilities}]. "
            f"Stance: {frame_plan.army_stance.name}"
        )

        if command_functors:
            async_tasks: List[asyncio.Task] = []
            for func in command_functors:
                result = func()
                if asyncio.iscoroutine(result):
                    async_tasks.append(result)

            if async_tasks:
                await asyncio.gather(*async_tasks)

        log.debug(f"Executing {len(command_functors)} command functors.")

        await self.event_bus.process_events()

        log.debug(f"--- Step {iteration} End ---")
```

---

### File: `core/event_bus.py`

```python
import asyncio
from collections import defaultdict
from typing import TYPE_CHECKING, Callable, Coroutine

from core.utilities.events import Event, EventType
from core.utilities.constants import (
    EVENT_PRIORITY_CRITICAL,
    EVENT_PRIORITY_HIGH,
    EVENT_PRIORITY_NORMAL,
)

if TYPE_CHECKING:
    from loguru import Logger

    # A handler is an async function that takes an Event and returns nothing.
    # Coroutine[None, None, None] is the precise way to say: "This is an async
    # function that I will await, but I don't expect it to return anything,
    # and I won't be sending data into it while it runs."
    EventHandler = Callable[[Event], Coroutine[None, None, None]]

# This map defines the priority for each event type.
# It is centrally located here to ensure all events are categorized.
EVENT_TYPE_PRIORITIES = {
    # Critical Events (Highest Priority)
    EventType.TACTICS_PROXY_DETECTED: EVENT_PRIORITY_CRITICAL,
    # High Priority Events
    EventType.TACTICS_UNIT_TOOK_DAMAGE: EVENT_PRIORITY_HIGH,
    # Normal Priority Events (Default)
    EventType.INFRA_BUILD_REQUEST: EVENT_PRIORITY_NORMAL,
    EventType.INFRA_BUILD_REQUEST_FAILED: EVENT_PRIORITY_NORMAL,
    EventType.TACTICS_ENEMY_TECH_SCOUTED: EVENT_PRIORITY_NORMAL,
}


class EventBus:
    """
    The bot's prioritized, asynchronous nervous system.

    This class implements a message queue that processes events based on a
    defined priority level. It decouples components, allowing a "scout" to
    report a threat without knowing who or what will handle it.

    Workflow:
    1. Components `subscribe` a handler function to a specific `EventType`.
    2. Components `publish` an `Event` object. This is a non-blocking call
    that adds the event to a priority queue.
    3. The `TerranGeneral` calls `process_events` once per frame. This method
    executes all queued handlers, starting with the highest priority,
    running them concurrently via asyncio.gather.
    """

    def __init__(self, logger: "Logger"):
        self._subscribers: dict[EventType, list[EventHandler]] = defaultdict(list)
        self._queues: dict[int, list[Event]] = {
            EVENT_PRIORITY_CRITICAL: [],
            EVENT_PRIORITY_HIGH: [],
            EVENT_PRIORITY_NORMAL: [],
        }
        self.logger = logger

    def subscribe(self, event_type: EventType, handler: "EventHandler"):
        """
        Subscribes a handler coroutine to a specific event type.

        :param event_type: The EventType to listen for.
        :param handler: The async function to execute when the event is processed.
        """
        self._subscribers[event_type].append(handler)

    def publish(self, event: Event):
        """
        Publishes an event by adding it to the appropriate priority queue.

        This is a non-blocking operation. The event will be processed later
        when process_events() is called.

        :param event: The Event object containing the event_type and payload.
        """
        priority = EVENT_TYPE_PRIORITIES.get(event.event_type, EVENT_PRIORITY_NORMAL)
        self._queues[priority].append(event)
        self.logger.debug(
            f"Event Published: {event.event_type.name} with priority {priority}. Payload: {event.payload}"
        )

    async def process_events(self):
        """
        Executes all queued event handlers, in order of priority.

        This should be called once per game step by the General. It ensures
        that all CRITICAL events are handled before all HIGH events, and so on.
        Handlers within the same priority level are executed concurrently.
        """
        # Iterate through priorities in ascending order (0=CRITICAL, 1=HIGH, etc.)
        for priority in sorted(self._queues.keys()):
            event_queue = self._queues[priority]
            if not event_queue:
                continue

            self.logger.debug(
                f"Processing {len(event_queue)} events with priority {priority}."
            )

            tasks = []
            for event in event_queue:
                if event.event_type in self._subscribers:
                    for handler in self._subscribers[event.event_type]:
                        tasks.append(handler(event))
            if tasks:
                await asyncio.gather(*tasks)

            # Clear the queue for this priority level after processing
            event_queue.clear()
```

---

### File: `core/frame_plan.py`

```python
from __future__ import annotations
from enum import Enum, auto
from dataclasses import dataclass, field
from sc2.ids.unit_typeid import UnitTypeId
from sc2.ids.upgrade_id import UpgradeId

# --- Data Structures for Intentions ---


class ArmyStance(Enum):
    """Defines the high-level tactical stance of the army for the current frame."""

    DEFENSIVE = auto()
    AGGRESSIVE = auto()
    HARASS = auto()


class EconomicStance(Enum):
    """Defines the high-level economic goal for the frame."""

    NORMAL = auto()  # Default behavior, spend as resources become available.
    SAVING_FOR_EXPANSION = auto()  # Prioritize saving for a new base.
    SAVING_FOR_TECH = auto()  # Prioritize saving for a key tech structure.


@dataclass
class ResourceBudget:
    """
    Defines the percentage-based resource allocation for a frame.
    Values should sum to 100.
    """

    infrastructure: int = 20  # Builds your economy (bases, workers, supply).
    capabilities: int = 80  # Army + Tech + Upgrades
    tactics: int = 0  # e.g., for paid scouting like changelings


class FramePlan:
    """
    An ephemeral "scratchpad" for the current frame's strategic intentions.

    This object is created fresh by the General on every game step.
    Directors write their high-level plans to it (e.g., budget, stance),
    and other Directors or Managers can then read those plans to coordinate
    their actions within the same frame.

    This solves the intra-frame state conflict problem by providing a
    clear, one-way flow of intent.
    """

    def __init__(self):
        # The resource allocation plan set by the InfrastructureDirector.
        self.resource_budget: ResourceBudget = ResourceBudget()

        # The tactical plan set by the TacticalDirector.
        self.army_stance: ArmyStance = ArmyStance.DEFENSIVE

        self.economic_stance: EconomicStance = EconomicStance.NORMAL

        # --- CAPABILITY GOALS ---
        # A dictionary defining the desired army composition.
        self.unit_composition_goal: dict[UnitTypeId, int] = field(default_factory=dict)

        # A set of all tech structures the bot wants to build this frame.
        self.tech_goals: set[UnitTypeId] = field(default_factory=set)

        # A prioritized list of upgrades the bot wants to research.
        self.upgrade_goal: list[UpgradeId] = field(default_factory=list)
        # A set of high-priority production requests for the frame.
        self.production_requests: set[object] = set()

    def set_budget(self, infrastructure: int, capabilities: int, tactics: int = 0):
        """
        Sets the resource budget for the frame.
        Called by the InfrastructureDirector.
        Values should sum to 100
        """
        # Basic validation to ensure budget makes sense.
        if (infrastructure + capabilities + tactics) != 100:
            # In a real scenario, this would log a warning.
            # For now, we silently fail or adjust.
            pass
        self.resource_budget = ResourceBudget(infrastructure, capabilities, tactics)

    def set_army_stance(self, stance: ArmyStance):
        """
        Sets the army's tactical stance for the frame.
        Called by the TacticalDirector.
        """
        self.army_stance = stance

    def set_economic_stance(self, stance: EconomicStance):
        """
        Sets the bot's economic focus for the frame.
        Called by the InfrastructureDirector.
        """
        self.economic_stance = stance

    def add_production_request(self, request: object):
        """
        Adds a high-priority production item to the plan.
        Useful for reactive builds (e.g., "Build a turret NOW").
        """
        self.production_requests.add(request)
```

---

### File: `core/game_analysis.py`

```python
# core/game_analysis.py

from typing import TYPE_CHECKING, List
import numpy as np
import inspect

from sc2.units import Units

from core.interfaces.analysis_task_abc import AnalysisTask
from core.event_bus import EventBus
from core.utilities.constants import LOW_FREQUENCY_TASK_RATE
from core.analysis.analysis_configuration import (
    HIGH_FREQUENCY_TASK_CLASSES,
    LOW_FREQUENCY_TASK_CLASSES,
    PRE_ANALYSIS_TASK_CLASSES,
)

if TYPE_CHECKING:
    from sc2.bot_ai import BotAI
    from sc2.position import Point2


class GameAnalyzer:
    """
    The central analysis engine. Owns analytical state and runs a staged,
    scheduled pipeline of tasks to ensure data dependencies and performance.
    """

    def __init__(self, event_bus: EventBus):
        # --- Analytical State Attributes ---
        self.friendly_army_value: int = 0
        self.enemy_army_value: int = 0
        self.friendly_units: Units | None = None
        self.friendly_structures: Units | None = None
        self.friendly_workers: Units | None = None
        self.friendly_army_units: Units | None = None
        self.idle_production_structures: Units | None = None
        self.threat_map: np.ndarray | None = None
        self.known_enemy_units: Units | None = None
        self.known_enemy_structures: Units | None = None
        self.known_enemy_townhalls: Units | None = None
        self.available_expansion_locations: set[Point2] = set()
        self.occupied_locations: set[Point2] = set()
        self.enemy_occupied_locations: set[Point2] = set()

        # --- Task Pipeline and Scheduler ---
        self._pre_analysis_tasks: List[AnalysisTask] = self._instantiate_tasks(
            PRE_ANALYSIS_TASK_CLASSES, event_bus
        )
        self._high_freq_tasks: List[AnalysisTask] = self._instantiate_tasks(
            HIGH_FREQUENCY_TASK_CLASSES, event_bus
        )
        self._low_freq_tasks: List[AnalysisTask] = self._instantiate_tasks(
            LOW_FREQUENCY_TASK_CLASSES, event_bus
        )
        self._high_freq_index: int = 0
        self._low_freq_index: int = 0

    def _instantiate_tasks(
        self, task_classes: List[type[AnalysisTask]], event_bus: EventBus
    ) -> List[AnalysisTask]:
        """
        Factory helper to instantiate tasks and wire up event subscriptions
        for those that require it.
        """
        tasks = []
        for TaskCls in task_classes:
            task = TaskCls()
            # If the task has a subscription method, call it.
            if hasattr(task, "subscribe_to_events"):
                subscribe_method = getattr(task, "subscribe_to_events")
                if callable(subscribe_method):
                    subscribe_method(event_bus)
            tasks.append(task)
        return tasks

    def run(self, bot: "BotAI"):
        """Executes the full analysis pipeline for the current game frame."""
        # STAGE 1: Pre-Analysis (every frame, guaranteed order)
        for task in self._pre_analysis_tasks:
            task.execute(self, bot)

        # STAGE 2: Scheduled High-Frequency Analysis (round-robin)
        if self._high_freq_tasks:
            task_to_run = self._high_freq_tasks[self._high_freq_index]
            task_to_run.execute(self, bot)
            self._high_freq_index = (self._high_freq_index + 1) % len(
                self._high_freq_tasks
            )

        # STAGE 3: Scheduled Low-Frequency Analysis (periodic)
        if self._low_freq_tasks and (
            bot.state.game_loop % LOW_FREQUENCY_TASK_RATE == 0
        ):
            task_to_run = self._low_freq_tasks[self._low_freq_index]
            task_to_run.execute(self, bot)
            self._low_freq_index = (self._low_freq_index + 1) % len(
                self._low_freq_tasks
            )
```

---

### File: `core/global_cache.py`

```python
# core/global_cache.py

from __future__ import annotations
from typing import TYPE_CHECKING
import numpy as np
from sc2.ids.upgrade_id import UpgradeId
from sc2.ids.unit_typeid import UnitTypeId
from sc2.units import Units

if TYPE_CHECKING:
    from sc2.bot_ai import BotAI
    from sc2.game_info import Ramp
    from sc2.position import Point2
    from core.game_analysis import GameAnalyzer

from core.event_bus import EventBus
from core.logger import logger


class GlobalCache:
    """
    A passive data container for the bot's "world state" on a single frame.
    It is populated once per frame by the Sajuuk conductor.
    """

    def __init__(self):
        self.logger = logger
        self.event_bus: EventBus = EventBus(self.logger)

        # Raw Perceived State
        self.bot: "BotAI" | None = None
        self.game_loop: int = 0
        self.iteration: int = 0  # NEW: Add iteration to the cache
        self.minerals: int = 0
        self.vespene: int = 0
        self.supply_left: int = 0
        self.supply_cap: int = 0
        self.supply_used: int = 0
        self.friendly_upgrades: set["UpgradeId"] | None = None
        self.enemy_units: "Units" | None = None
        self.enemy_structures: "Units" | None = None
        self.map_ramps: list["Ramp"] | None = None

        # Analyzed State (Copied from GameAnalyzer)
        self.friendly_units: Units | None = None
        self.friendly_structures: Units | None = None
        self.friendly_workers: Units | None = None
        self.friendly_army_units: Units | None = None
        self.idle_production_structures: Units | None = None
        self.threat_map: np.ndarray | None = None
        self.base_is_under_attack: bool = False
        self.threat_location: "Point2" | None = None
        self.friendly_army_value: int = 0
        self.enemy_army_value: int = 0
        self.known_enemy_units: Units | None = None
        self.known_enemy_structures: Units | None = None
        self.known_enemy_townhalls: Units | None = None
        self.available_expansion_locations: set[Point2] = set()
        self.occupied_locations: set[Point2] = set()
        self.enemy_occupied_locations: set[Point2] = set()

    # CHANGED: Added 'iteration' to the method signature
    def update(self, bot: "BotAI", analyzer: "GameAnalyzer", iteration: int):
        """Populates the cache from the raw bot state and the GameAnalyzer."""
        if self.bot is None:
            self.bot = bot
            self.map_ramps = self.bot.game_info.map_ramps

        # --- Copy Raw Perceived State ---
        self.game_loop = bot.state.game_loop
        self.iteration = iteration  # NEW: Store the current iteration
        self.minerals = bot.minerals
        self.vespene = bot.vespene
        self.supply_used = bot.supply_used
        self.supply_cap = bot.supply_cap
        self.supply_left = bot.supply_left
        self.friendly_upgrades = bot.state.upgrades
        self.enemy_units = bot.enemy_units
        self.enemy_structures = bot.enemy_structures

        # --- Copy Final Analyzed State ---
        self.friendly_units = analyzer.friendly_units
        self.friendly_structures = analyzer.friendly_structures
        self.friendly_workers = analyzer.friendly_workers
        self.friendly_army_units = analyzer.friendly_army_units
        self.idle_production_structures = analyzer.idle_production_structures
        self.threat_map = analyzer.threat_map
        self.base_is_under_attack = getattr(analyzer, "base_is_under_attack", False)
        self.threat_location = getattr(analyzer, "threat_location", None)
        self.friendly_army_value = analyzer.friendly_army_value
        self.enemy_army_value = analyzer.enemy_army_value
        self.known_enemy_units = analyzer.known_enemy_units
        self.known_enemy_structures = analyzer.known_enemy_structures
        self.known_enemy_townhalls = analyzer.known_enemy_townhalls
        self.available_expansion_locations = analyzer.available_expansion_locations
        self.occupied_locations = analyzer.occupied_locations
        self.enemy_occupied_locations = analyzer.enemy_occupied_locations
```

---

### File: `core/logger.py`

```python
from loguru import logger
from sys import stdout
import datetime
from pathlib import Path


def game_time_formatter(record):
    """
    Custom loguru formatter function.
    Adds 'game_time' to the log record if it exists, otherwise pads with spaces.
    This ensures consistent log alignment and prevents KeyErrors.
    """
    game_time_str = record["extra"].get("game_time", " " * 8)  # Default to 8 spaces
    # This is the original format string, but with our safe variable
    return f"{{time:HH:mm:ss.SS}} {{level}} {game_time_str} | {{name}}:{{function}}:{{line}} - {{message}}\n"


def sajuuk_project_filter(record):
    """
    This filter function returns True only for log messages originating
    from the Sajuuk project's own modules.
    """
    # The 'name' of a log record is its module path, e.g., 'core.event_bus'
    module_name = record["name"]
    return (
        module_name.startswith("sajuuk")
        or module_name.startswith("core")
        or module_name.startswith("terran")
        or module_name.startswith("protoss")
        or module_name.startswith("zerg")
    )


def is_external_filter(record):
    """
    This filter returns True for logs that are NOT from the Sajuuk project.
    It's the inverse of the sajuuk_project_filter.
    """
    return not sajuuk_project_filter(record)


# --- START: MODIFIED LOGGING SETUP ---
logger.remove()

# 1. Create a "logs" directory if it doesn't exist
log_dir = Path("logs")
log_dir.mkdir(exist_ok=True)

# 2. Create a unique filename using the current timestamp
timestamp = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
log_file_path = log_dir / f"sajuuk_{timestamp}.log"

# 3. Add the file handler with the new dynamic path
logger.add(
    log_file_path,  # Use the timestamped path
    format=game_time_formatter,
    level="DEBUG",
    filter=sajuuk_project_filter,
    rotation="10 MB",
    enqueue=True,
    backtrace=True,
    diagnose=True,
)

# 4. (Optional) Add your clean console logger
logger.add(stdout, level="WARNING", filter=sajuuk_project_filter)
logger.add(
    stdout,
    level="INFO",  # Set to INFO or DEBUG to see more detail from the library
    filter=is_external_filter,
    backtrace=True,  # Ensure tracebacks are always shown for this handler
    diagnose=True,
)
logger.info(f"Sajuuk logger initialized. Log file: {log_file_path}")
```

---

### File: `core/types.py`

```python
from typing import Callable, Any

# A CommandFunctor is an async, zero-argument function that returns any result.
# It encapsulates a deferred action (e.g., lambda: some_unit.train()).
CommandFunctor = Callable[[], Any]
```

---

### File: `core/analysis/analysis_configuration.py`

```python
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
from core.analysis.base_threat_analyzer import BaseThreatAnalyzer

# --- Task Configuration ---

# PRE_ANALYSIS: Run EVERY frame before all other tasks.
# For foundational tasks that other analyzers depend on.
PRE_ANALYSIS_TASK_CLASSES: List[Type[AnalysisTask]] = [
    UnitsAnalyzer,
]

# HIGH_FREQUENCY: Run one task per frame in a round-robin cycle.
# For lightweight tasks that need to be reasonably fresh.
HIGH_FREQUENCY_TASK_CLASSES: List[Type[AnalysisTask]] = [
    BaseThreatAnalyzer,
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
```

---

### File: `core/analysis/army_value_analyzer.py`

```python
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
```

---

### File: `core/analysis/base_threat_analyzer.py`

```python
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
```

---

### File: `core/analysis/expansion_analyzer.py`

```python
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

    def __init__(self):
        super().__init__()

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
```

---

### File: `core/analysis/known_enemy_townhall_analyzer.py`

```python
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
```

---

### File: `core/analysis/threat_map_analyzer.py`

```python
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
```

---

### File: `core/analysis/units_analyzer.py`

```python
from typing import TYPE_CHECKING, Dict

from sc2.unit import Unit
from sc2.units import Units

from core.interfaces.analysis_task_abc import AnalysisTask
from core.utilities.events import (
    Event,
    EventType,
    UnitDestroyedPayload,
    EnemyUnitSeenPayload,
)
from core.utilities.unit_types import TERRAN_PRODUCTION_TYPES, WORKER_TYPES

if TYPE_CHECKING:
    from sc2.bot_ai import BotAI
    from core.event_bus import EventBus
    from core.game_analysis import GameAnalyzer


class UnitsAnalyzer(AnalysisTask):
    """
    A central, stateful analyzer that maintains a persistent memory of all
    known enemy units, including snapshots in the fog of war.
    """

    def __init__(self):
        super().__init__()
        self._known_enemy_units: Dict[int, Unit] = {}

    def subscribe_to_events(self, event_bus: "EventBus"):
        """Subscribes to the fundamental unit-tracking events."""
        event_bus.subscribe(
            EventType.TACTICS_ENEMY_UNIT_SEEN, self.handle_enemy_unit_seen
        )
        event_bus.subscribe(EventType.UNIT_DESTROYED, self.handle_unit_destroyed)

    def execute(self, analyzer: "GameAnalyzer", bot: "BotAI"):
        """
        On each frame, this method updates the GameAnalyzer with the current
        snapshot of all known units from its persistent memory.
        """
        all_friendly_units = bot.units

        analyzer.friendly_units = all_friendly_units
        analyzer.friendly_structures = bot.structures
        analyzer.friendly_workers = all_friendly_units.filter(
            lambda u: u.type_id in WORKER_TYPES
        )

        analyzer.friendly_army_units = all_friendly_units.filter(
            lambda u: not u.is_structure and not u.type_id in WORKER_TYPES
        )
        analyzer.idle_production_structures = analyzer.friendly_structures.of_type(
            TERRAN_PRODUCTION_TYPES
        ).idle
        analyzer.known_enemy_units = Units(self._known_enemy_units.values(), bot)
        analyzer.known_enemy_structures = analyzer.known_enemy_units.filter(
            lambda u: u.is_structure
        )

    async def handle_enemy_unit_seen(self, event: Event):
        """Adds or updates a unit in our persistent memory when it enters vision."""
        payload: EnemyUnitSeenPayload = event.payload
        self._known_enemy_units[payload.unit.tag] = payload.unit

    async def handle_unit_destroyed(self, event: Event):
        """Removes a unit from our persistent memory when it is destroyed."""
        payload: UnitDestroyedPayload = event.payload
        self._known_enemy_units.pop(payload.unit_tag, None)
```

---

### File: `core/interfaces/analysis_task_abc.py`

```python
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from sc2.bot_ai import BotAI
    from core.game_analysis import GameAnalyzer


class AnalysisTask(ABC):
    """
    Abstract base class for a single, focused analysis task.
    """

    def __init__(self):
        """
        Initializes the task. Subclasses that need to subscribe to events
        should implement a 'subscribe_to_events' method.
        """
        pass

    @abstractmethod
    def execute(self, analyzer: "GameAnalyzer", bot: "BotAI"):
        """
        Executes the analysis task.

        :param analyzer: The GameAnalyzer instance to read from and write to.
        :param bot: The main bot instance, for accessing raw game state.
        """
        pass
```

---

### File: `core/interfaces/director_abc.py`

```python
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from sc2.bot_ai import BotAI
    from core.global_cache import GlobalCache
    from core.event_bus import EventBus
    from core.frame_plan import FramePlan

from core.types import CommandFunctor


class Director(ABC):
    """
    Defines the abstract contract for a high-level functional Director.

    A Director is responsible for a major functional area of the bot
    (e.g., Infrastructure, Capabilities). It orchestrates several related
    Managers to achieve a strategic goal.
    """

    def __init__(self, bot: "BotAI"):
        self.bot = bot

    @abstractmethod
    async def execute(
        self, cache: "GlobalCache", plan: "FramePlan", bus: "EventBus"
    ) -> list[CommandFunctor]:
        """
        The main execution method for the Director, called by its General.

        :param cache: The read-only GlobalCache with the current world state.
        :param plan: The ephemeral "scratchpad" for the current frame's intentions.
        :param bus: The EventBus for reactive messaging.
        :return: A list of all commands requested by its subordinate managers.
        """
        pass
```

---

### File: `core/interfaces/manager_abc.py`

```python
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from sc2.bot_ai import BotAI
    from core.global_cache import GlobalCache
    from core.event_bus import EventBus
    from core.frame_plan import FramePlan

from core.types import CommandFunctor


class Manager(ABC):
    """
    Defines the abstract contract for any specialized, stateful Manager.

    A Manager is responsible for a single, narrow domain of logic
    (e.g., producing SCVs, managing supply). It is orchestrated by a
    higher-level Director.
    """

    def __init__(self, bot: "BotAI"):
        self.bot = bot

    @abstractmethod
    async def execute(
        self, cache: "GlobalCache", plan: "FramePlan", bus: "EventBus"
    ) -> list[CommandFunctor]:
        """
        The main execution method for the manager, called by its Director.

        :param cache: The read-only GlobalCache with the current frame's state.
        :param bus: The EventBus for reactive messaging.
        :return: A list of UnitCommand objects to be executed.
        """
        pass
```

---

### File: `core/interfaces/race_general_abc.py`

```python
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from sc2.bot_ai import BotAI
    from core.global_cache import GlobalCache
    from core.event_bus import EventBus
    from core.frame_plan import FramePlan

from core.types import CommandFunctor


class RaceGeneral(ABC):
    """
    Defines the abstract contract for a race-specific General.

    This is the primary interface the main Sajuuk Conductor interacts with.
    It orchestrates all Directors for a given race.
    """

    def __init__(self, bot: "BotAI"):
        self.bot = bot

    @abstractmethod
    async def on_start(self):
        """
        Called once at the start of the game.
        Responsible for initializing all race-specific Directors.
        """
        pass

    @abstractmethod
    async def execute_step(
        self, cache: "GlobalCache", plan: "FramePlan", bus: "EventBus"
    ) -> list[CommandFunctor]:
        """
        The main logic loop for the General, called every game step.

        It orchestrates its Directors, aggregates their requested actions,
        and returns the final list of commands for the frame.

        :param cache: The read-only GlobalCache with the current frame's state.
        :param bus: The EventBus for reactive messaging.
        :return: A list of UnitCommand objects to be executed by the Conductor.
        """
        pass
```

---

### File: `core/utilities/constants.py`

```python
"""
A central repository for tunable, non-magical constants.

This file allows for easy adjustment of the bot's core behaviors without
needing to modify the underlying logic of the managers or directors.
All values here should be considered a starting point for optimization.
"""

# --- Analysis Scheduling ---
# Determines how often one of the "heavy" analysis tasks is run.
# A value of 8 means one low-frequency task will be executed every 8 frames.
LOW_FREQUENCY_TASK_RATE: int = 8

# --- Event Bus Priorities ---
# Defines the processing order for events within the EventBus.
EVENT_PRIORITY_CRITICAL: int = 0  # e.g., Dodge spell, Proxy detected
EVENT_PRIORITY_HIGH: int = 1  # e.g., Unit took damage
EVENT_PRIORITY_NORMAL: int = 2  # e.g., Build request failed

# --- Economy & Infrastructure ---
# The absolute maximum number of workers the bot will ever produce.
MAX_WORKER_COUNT: int = 75

# The target number of workers per mineral line.
SCVS_PER_MINERAL_LINE: int = 16

# The target number of workers per vespene geyser.
SCVS_PER_GEYSER: int = 3

# The minimum supply buffer to maintain. The bot will request a depot
# when supply_left falls below this number.
SUPPLY_BUFFER_BASE: int = 4

# The supply buffer is increased by this amount for each active
# production structure (Barracks, Factory, Starport).
SUPPLY_BUFFER_PER_PRODUCTION_STRUCTURE: int = 2

# --- Tactics & Military ---
# The supply count at which the first scout (usually an SCV) is sent out.
SCOUT_AT_SUPPLY: int = 14

# The default size of a standard combat squad.
DEFAULT_SQUAD_SIZE: int = 16

# The health percentage at which an army squad will consider retreating
# from a losing engagement.
RETREAT_HEALTH_PERCENTAGE: float = 0.35
```

---

### File: `core/utilities/events.py`

```python
from __future__ import annotations
from enum import Enum, auto
from dataclasses import dataclass
from typing import TYPE_CHECKING
from abc import ABC

# This block was missing. It provides the definitions for type hints.
if TYPE_CHECKING:
    from sc2.ids.unit_typeid import UnitTypeId
    from sc2.position import Point2
    from sc2.unit import Unit

from core.utilities.constants import EVENT_PRIORITY_NORMAL


class EventType(Enum):
    """
    Defines all possible event types in the system.

    This strict registry prevents the use of "magic strings" and makes the
    system's communication patterns discoverable and maintainable.
    Namespacing (e.g., DOMAIN_ACTION) clarifies event ownership.
    """

    # --- Infrastructure Events ---
    # Published by any module needing a structure built.
    # Handled by ConstructionManager.
    INFRA_BUILD_REQUEST = auto()

    # Published by ConstructionManager on failure.
    # Handled by the original requester.
    INFRA_BUILD_REQUEST_FAILED = auto()

    # --- Tactics Events ---
    # Published by ScoutingManager.
    # Handled by various Directors to adapt strategy.
    TACTICS_ENEMY_TECH_SCOUTED = auto()

    # A high-priority version of the above.
    TACTICS_PROXY_DETECTED = auto()

    # Published by the main bot loop's on_unit_took_damage hook.
    # Handled by RepairManager.
    TACTICS_UNIT_TOOK_DAMAGE = auto()

    # Published by the main bot's on_enemy_unit_entered_vision hook.
    # Handled by GameAnalyzer.
    TACTICS_ENEMY_UNIT_SEEN = auto()

    # Published by the main bot loop's on_unit_destroyed hook.
    # Handled by GameAnalyzer.
    UNIT_DESTROYED = auto()


class Payload(ABC):
    """An abstract base class for all event payloads."""

    pass


# --- Payload Data Structures ---


@dataclass
class BuildRequestPayload(Payload):
    """Payload for an INFRA_BUILD_REQUEST event."""

    item_id: "UnitTypeId"
    position: "Point2" | None = None
    priority: int = EVENT_PRIORITY_NORMAL
    unique: bool = False


@dataclass
class BuildRequestFailedPayload(Payload):
    """Payload for an INFRA_BUILD_REQUEST_FAILED event."""

    item_id: "UnitTypeId"
    reason: str


@dataclass
class EnemyTechScoutedPayload(Payload):
    """Payload for a TACTICS_ENEMY_TECH_SCOUTED event."""

    tech_id: "UnitTypeId"


@dataclass
class UnitTookDamagePayload(Payload):
    """Payload for a TACTICS_UNIT_TOOK_DAMAGE event."""

    unit_tag: int
    damage_amount: float


@dataclass
class UnitDestroyedPayload(Payload):
    """Payload for a UNIT_DESTROYED event."""

    unit_tag: int
    unit_type: "UnitTypeId"
    last_known_position: "Point2"


@dataclass
class EnemyUnitSeenPayload(Payload):
    """Payload for a TACTICS_ENEMY_UNIT_SEEN event."""

    unit: "Unit"


# --- The Generic Event Wrapper ---


@dataclass
class Event:
    """
    A generic wrapper for an event published to the EventBus.

    Attributes:
    -----------
    event_type: EventType
        The specific type of the event, which determines which subscribers
        will be notified. This is the primary identifier for the event.

    payload: PayloadT | None
        The data associated with the event, providing context for what
        happened. This is typically one of the specific payload dataclasses
        (e.g., BuildRequestPayload, UnitDestroyedPayload). Its type is
        linked to the event_type through the generic `PayloadT`.
    """

    event_type: EventType
    payload: Payload | None = None
```

---

### File: `core/utilities/geometry.py`

```python
import math
from typing import TYPE_CHECKING, Set

import numpy as np

from sc2.position import Point2

if TYPE_CHECKING:
    from sc2.units import Units


def create_threat_map(
    enemy_units: "Units", map_size: tuple[int, int], threat_radius: int = 15
) -> np.ndarray:
    """
    Generates a 2D numpy array representing a "threat map" of the battlefield.

    Each cell in the map contains a score representing the cumulative threat
    posed by nearby enemy units. This is useful for finding safe locations
    for army positioning or expansion.

    :param enemy_units: A collection of enemy units to source threat from.
    :param map_size: A tuple (width, height) of the map.
    :param threat_radius: The maximum distance from an enemy unit that its
    threat will be projected.
    :return: A 2D numpy array where higher values indicate greater danger.
    """
    threat_map = np.zeros(map_size, dtype=np.float32)

    for unit in enemy_units:
        # For simplicity, we can use a basic threat value or incorporate
        # the calculate_threat_value function from unit_value.py later.
        threat_value = 10 + unit.radius  # Basic threat score
        pos = unit.position.rounded

        # Get a bounding box for the threat area to avoid iterating the whole map
        x_min = max(0, pos.x - threat_radius)
        x_max = min(map_size[0], pos.x + threat_radius + 1)
        y_min = max(0, pos.y - threat_radius)
        y_max = min(map_size[1], pos.y + threat_radius + 1)

        for x in range(x_min, x_max):
            for y in range(y_min, y_max):
                dist_sq = (pos.x - x) ** 2 + (pos.y - y) ** 2
                if dist_sq <= threat_radius**2:
                    # Apply a falloff effect: threat is highest at the center
                    falloff = 1 - (math.sqrt(dist_sq) / threat_radius)
                    threat_map[x, y] += threat_value * falloff

    return threat_map


def find_safe_point_from_threat_map(
    threat_map: np.ndarray, reference_point: "Point2", search_radius: int = 20
) -> "Point2":
    """
    Finds the point with the lowest threat score on the map within a given
    search radius of a reference point.

    :param threat_map: The 2D numpy array generated by create_threat_map.
    :param reference_point: The central point to search around.
    :param search_radius: The radius to search for a safe point.
    :return: The Point2 location with the minimum threat in the area.
    """
    best_point = reference_point
    min_threat = float("inf")

    x_min = max(0, int(reference_point.x - search_radius))
    x_max = min(threat_map.shape[0], int(reference_point.x + search_radius + 1))
    y_min = max(0, int(reference_point.y - search_radius))
    y_max = min(threat_map.shape[1], int(reference_point.y + search_radius + 1))

    for x in range(x_min, x_max):
        for y in range(y_min, y_max):
            threat = threat_map[x, y]
            if threat < min_threat:
                min_threat = threat
                best_point = Point2((x, y))

    return best_point
```

---

### File: `core/utilities/unit_types.py`

```python
"""
A central repository for static collections of UnitTypeIds.

This provides a single, authoritative source for filtering units by their
role or other shared characteristics, ensuring consistency and making the
code easier to read and maintain.
"""

from sc2.ids.unit_typeid import UnitTypeId

TERRAN_PRODUCTION_TYPES = {
    UnitTypeId.BARRACKS,
    UnitTypeId.FACTORY,
    UnitTypeId.STARPORT,
}
GAS_BUILDINGS = {
    UnitTypeId.REFINERY,
    UnitTypeId.EXTRACTOR,
    UnitTypeId.ASSIMILATOR,
}
# A set of all worker types across all races.
WORKER_TYPES = {UnitTypeId.SCV, UnitTypeId.PROBE, UnitTypeId.DRONE}

# A set of all supply provider types across all races.
SUPPLY_PROVIDER_TYPES = {UnitTypeId.SUPPLYDEPOT, UnitTypeId.OVERLORD, UnitTypeId.PYLON}

# --- Terran Specific Types ---
STRUCTURE_TYPES_TERRAN = {
    UnitTypeId.BARRACKS,
    UnitTypeId.BARRACKSFLYING,
    UnitTypeId.BARRACKSREACTOR,
    UnitTypeId.BARRACKSTECHLAB,
    UnitTypeId.COMMANDCENTER,
    UnitTypeId.COMMANDCENTERFLYING,
    UnitTypeId.ORBITALCOMMAND,
    UnitTypeId.ORBITALCOMMANDFLYING,
    UnitTypeId.PLANETARYFORTRESS,
    UnitTypeId.ENGINEERINGBAY,
    UnitTypeId.FACTORY,
    UnitTypeId.FACTORYFLYING,
    UnitTypeId.FACTORYREACTOR,
    UnitTypeId.FACTORYTECHLAB,
    UnitTypeId.STARPORT,
    UnitTypeId.STARPORTFLYING,
    UnitTypeId.STARPORTREACTOR,
    UnitTypeId.STARPORTTECHLAB,
    UnitTypeId.FUSIONCORE,
    UnitTypeId.GHOSTACADEMY,
    UnitTypeId.ARMORY,
    UnitTypeId.SUPPLYDEPOT,
    UnitTypeId.SUPPLYDEPOTLOWERED,
    UnitTypeId.BUNKER,
    UnitTypeId.MISSILETURRET,
    UnitTypeId.SENSORTOWER,
    UnitTypeId.AUTOTURRET,
    UnitTypeId.REFINERY,
}

# --- Zerg Specific Types (Placeholder) ---
STRUCTURE_TYPES_ZERG = set()

# --- Protoss Specific Types (Placeholder) ---
STRUCTURE_TYPES_PROTOSS = set()

# A combined set of all structure types for easy filtering.
ALL_STRUCTURE_TYPES = (
    STRUCTURE_TYPES_TERRAN | STRUCTURE_TYPES_ZERG | STRUCTURE_TYPES_PROTOSS
)
```

---

### File: `core/utilities/unit_value.py`

```python
# core/utilities/unit_value.py

from typing import TYPE_CHECKING
from sc2.ids.unit_typeid import UnitTypeId

# This block was missing. It provides the definitions for type hints.
if TYPE_CHECKING:
    from sc2.game_data import GameData
    from sc2.units import Units

# --- Heuristic Threat Assessment ---
# This dictionary provides a non-resource-based "threat" score for units.
# These are opinionated values based on a unit's potential to do damage,
# its area-of-effect capabilities, and its strategic importance.
# These values are designed to be tuned over time.
# A higher score indicates a higher priority target.
THREAT_SCORE_MAP = {
    # --- Terran ---
    UnitTypeId.SIEGETANKSIEGED: 100,
    UnitTypeId.BATTLECRUISER: 95,
    UnitTypeId.LIBERATORAG: 90,
    UnitTypeId.BANSHEE: 80,
    UnitTypeId.SIEGETANK: 70,
    UnitTypeId.THOR: 65,
    UnitTypeId.MARAUDER: 30,
    UnitTypeId.MARINE: 20,
    UnitTypeId.REAPER: 15,
    UnitTypeId.SCV: 1,
    # --- Zerg ---
    UnitTypeId.LURKERMPBURROWED: 100,
    UnitTypeId.BANELING: 90,  # High threat against bio
    UnitTypeId.INFESTOR: 90,
    UnitTypeId.ULTRALISK: 85,
    UnitTypeId.BROODLORD: 80,
    UnitTypeId.HYDRALISK: 40,
    UnitTypeId.ROACH: 30,
    UnitTypeId.ZERGLING: 10,
    UnitTypeId.DRONE: 1,
    # --- Protoss ---
    UnitTypeId.DISRUPTOR: 100,
    UnitTypeId.HIGHTEMPLAR: 95,
    UnitTypeId.COLOSSUS: 85,
    UnitTypeId.ARCHON: 80,
    UnitTypeId.IMMORTAL: 70,
    UnitTypeId.STALKER: 30,
    UnitTypeId.ADEPT: 25,
    UnitTypeId.ZEALOT: 20,
    UnitTypeId.PROBE: 1,
}
# Default threat for units not in the map (e.g., workers, support units)
DEFAULT_THREAT_SCORE = 5


def calculate_threat_value(unit_type_id: UnitTypeId) -> float:
    """
    Calculates the tactical threat of a single unit based on a heuristic map.

    This value is used to prioritize targets in combat. It is not based
    on resource cost, but on the unit's potential impact on a battle.

    :param unit_type_id: The UnitTypeId of the unit to assess.
    :return: A float representing the unit's threat score.
    """
    return THREAT_SCORE_MAP.get(unit_type_id, DEFAULT_THREAT_SCORE)


def calculate_resource_value(unit_type_id: UnitTypeId, game_data: "GameData") -> int:
    """
    Calculates the combined mineral and vespene cost of a unit.

    :param unit_type_id: The UnitTypeId of the unit.
    :param game_data: The GameData object from the BotAI.
    :return: The total resource cost (minerals + vespene).
    """
    unit_data = game_data.units[unit_type_id.value]
    cost = unit_data.cost
    return cost.minerals + cost.vespene


def calculate_army_value(units: "Units", game_data: "GameData") -> int:
    """
    Calculates the total resource value of a collection of units.

    This is a simple way to estimate the size of an army.

    :param units: A `Units` object (a list-like collection of units).
    :param game_data: The GameData object from the BotAI.
    :return: The sum of the resource values of all units in the collection.
    """
    total_value = 0
    if not units:
        return total_value

    for unit in units:
        total_value += calculate_resource_value(unit.type_id, game_data)
    return total_value
```

---

### File: `terran/capabilities/capability_director.py`

```python
from __future__ import annotations
from typing import TYPE_CHECKING, List, Dict

from sc2.ids.unit_typeid import UnitTypeId
from sc2.ids.upgrade_id import UpgradeId

from core.interfaces.director_abc import Director
from core.interfaces.manager_abc import Manager
from core.types import CommandFunctor
from .units.army_unit_manager import ArmyUnitManager
from .structures.tech_structure_manager import TechStructureManager
from .structures.addon_manager import AddonManager
from .upgrades.research_manager import ResearchManager

if TYPE_CHECKING:
    from sc2.bot_ai import BotAI
    from core.global_cache import GlobalCache
    from core.event_bus import EventBus
    from core.frame_plan import FramePlan


class CapabilityDirector(Director):
    """
    The Quartermaster. Plans all production and technology.
    This director now uses a target-based system to define the desired
    number of tech buildings, allowing for parallel and scalable construction goals.
    """

    def __init__(self, bot: "BotAI"):
        super().__init__(bot)
        self.army_unit_manager = ArmyUnitManager(bot)
        self.tech_structure_manager = TechStructureManager(bot)
        self.addon_manager = AddonManager(bot)
        self.research_manager = ResearchManager(bot)
        self.managers: List[Manager] = [
            self.tech_structure_manager,
            self.addon_manager,
            self.research_manager,
            self.army_unit_manager,
        ]

        # --- Desired Tech Tree Targets ---
        # Defines the target count for each structure based on number of bases.
        self.tech_tree_targets: Dict[int, Dict[UnitTypeId, int]] = {
            1: {  # On 1 base
                UnitTypeId.BARRACKS: 1,
                UnitTypeId.FACTORY: 1,
                UnitTypeId.ENGINEERINGBAY: 1,
            },
            2: {  # On 2 bases
                UnitTypeId.BARRACKS: 3,
                UnitTypeId.FACTORY: 1,
                UnitTypeId.STARPORT: 1,
                UnitTypeId.ENGINEERINGBAY: 1,
                UnitTypeId.ARMORY: 1,
            },
            3: {  # On 3+ bases
                UnitTypeId.BARRACKS: 5,
                UnitTypeId.FACTORY: 1,
                UnitTypeId.STARPORT: 2,
                UnitTypeId.ENGINEERINGBAY: 2,
                UnitTypeId.ARMORY: 1,
                UnitTypeId.FUSIONCORE: 1,
            },
        }

    async def execute(
        self, cache: "GlobalCache", plan: "FramePlan", bus: "EventBus"
    ) -> list[CommandFunctor]:
        self._set_production_goals(cache, plan)
        actions: list[CommandFunctor] = []
        for manager in self.managers:
            manager_actions = await manager.execute(cache, plan, bus)
            actions.extend(manager_actions)
        return actions

    def _set_production_goals(self, cache: "GlobalCache", plan: "FramePlan"):
        """
        Determines ALL immediate production needs and writes them to the FramePlan.
        """
        s = cache.friendly_structures
        p = self.bot.already_pending

        # --- Unit Composition Goal ---
        plan.unit_composition_goal = {
            UnitTypeId.MARINE: 20,
            UnitTypeId.MARAUDER: 5,
            UnitTypeId.MEDIVAC: 3,
            UnitTypeId.VIKINGFIGHTER: 2,
            UnitTypeId.SIEGETANK: 2,
        }

        # --- Tech Structure Goals ---
        num_bases = self.bot.townhalls.amount
        target_counts = self.tech_tree_targets.get(num_bases, self.tech_tree_targets[3])

        plan.tech_goals = set()
        for building_id, target_count in target_counts.items():
            current_count = s.of_type(building_id).amount + p(building_id)
            if (
                current_count < target_count
                and self.bot.tech_requirement_progress(building_id) >= 1
            ):
                plan.tech_goals.add(building_id)

        # --- Upgrade Goals ---
        plan.upgrade_goal = self._get_upgrade_priorities(cache)

    def _get_upgrade_priorities(self, cache: "GlobalCache") -> List[UpgradeId]:
        """Calculates the prioritized list of upgrades to research."""
        s = cache.friendly_structures
        upgrades = cache.friendly_upgrades
        p_up = self.bot.already_pending_upgrade

        priority_list = []

        # Stim and Shields are top priority
        if s.of_type(UnitTypeId.BARRACKSTECHLAB).ready.exists:
            if UpgradeId.STIMPACK not in upgrades and p_up(UpgradeId.STIMPACK) == 0:
                priority_list.append(UpgradeId.STIMPACK)
            if UpgradeId.SHIELDWALL not in upgrades and p_up(UpgradeId.SHIELDWALL) == 0:
                priority_list.append(UpgradeId.SHIELDWALL)

        # Infantry Weapons and Armor
        if s.of_type(UnitTypeId.ENGINEERINGBAY).ready.exists:
            if (
                UpgradeId.TERRANINFANTRYWEAPONSLEVEL1 not in upgrades
                and p_up(UpgradeId.TERRANINFANTRYWEAPONSLEVEL1) == 0
            ):
                priority_list.append(UpgradeId.TERRANINFANTRYWEAPONSLEVEL1)
            elif (
                UpgradeId.TERRANINFANTRYARMORSLEVEL1 not in upgrades
                and p_up(UpgradeId.TERRANINFANTRYARMORSLEVEL1) == 0
            ):
                priority_list.append(UpgradeId.TERRANINFANTRYARMORSLEVEL1)

        # Add more logic for Level 2/3 upgrades which require an Armory
        if s.of_type(UnitTypeId.ARMORY).ready.exists:
            if (
                UpgradeId.TERRANINFANTRYWEAPONSLEVEL1 in upgrades
                and UpgradeId.TERRANINFANTRYWEAPONSLEVEL2 not in upgrades
                and p_up(UpgradeId.TERRANINFANTRYWEAPONSLEVEL2) == 0
            ):
                priority_list.append(UpgradeId.TERRANINFANTRYWEAPONSLEVEL2)
            if (
                UpgradeId.TERRANINFANTRYARMORSLEVEL1 in upgrades
                and UpgradeId.TERRANINFANTRYARMORSLEVEL2 not in upgrades
                and p_up(UpgradeId.TERRANINFANTRYARMORSLEVEL2) == 0
            ):
                priority_list.append(UpgradeId.TERRANINFANTRYARMORSLEVEL2)

        return priority_list
```

---

### File: `terran/capabilities/structures/addon_manager.py`

```python
from __future__ import annotations
from typing import TYPE_CHECKING, List, Dict, Set

from sc2.ids.unit_typeid import UnitTypeId

from core.interfaces.manager_abc import Manager
from core.types import CommandFunctor
from core.utilities.unit_types import TERRAN_PRODUCTION_TYPES

if TYPE_CHECKING:
    from sc2.bot_ai import BotAI
    from core.global_cache import GlobalCache
    from core.event_bus import EventBus
    from core.frame_plan import FramePlan

# Maps units that require a TechLab to the structure that builds them.
TECHLAB_REQUIREMENTS: Dict[UnitTypeId, Set[UnitTypeId]] = {
    UnitTypeId.BARRACKS: {UnitTypeId.MARAUDER, UnitTypeId.GHOST},
    UnitTypeId.FACTORY: {UnitTypeId.SIEGETANK, UnitTypeId.THOR},
    UnitTypeId.STARPORT: {
        UnitTypeId.RAVEN,
        UnitTypeId.BANSHEE,
        UnitTypeId.BATTLECRUISER,
    },
}


class AddonManager(Manager):
    """
    Add-on Specialist.

    This manager is responsible for building TechLabs and Reactors on production
    structures. It reads the production goals from the FramePlan to make an
    intelligent decision about which add-on is needed.

    NOTE: This manager is an exception to the event-based building system.
    Building an add-on is an ability of an existing structure, not a new
    construction handled by an SCV, so it issues commands directly.
    """

    def __init__(self, bot: "BotAI"):
        super().__init__(bot)

    async def execute(
        self, cache: "GlobalCache", plan: "FramePlan", bus: "EventBus"
    ) -> List[CommandFunctor]:
        """
        Identifies idle, add-on-less production buildings and builds the
        appropriate add-on based on the current production goals.
        """
        # Read production goals from the plan. If none, no decisions can be made.
        unit_goal = getattr(plan, "unit_composition_goal", {})
        if not unit_goal:
            return []

        # Find eligible buildings: ready, idle, and without an existing add-on.
        eligible_buildings = cache.friendly_structures.of_type(
            TERRAN_PRODUCTION_TYPES
        ).ready.idle.filter(lambda b: b.add_on_tag == 0)

        if not eligible_buildings:
            return []

        # Process one add-on request per frame to manage resource spending.
        building = eligible_buildings.first
        building_type = building.type_id
        needed_addon = None

        # --- Decision Logic: TechLab or Reactor? ---
        # 1. Check if a TechLab is required for any unit in our goal.
        tech_units_needed = TECHLAB_REQUIREMENTS.get(building_type, set())
        if any(unit_id in unit_goal for unit_id in tech_units_needed):
            needed_addon = UnitTypeId.TECHLAB
        # 2. If no tech is needed, default to a Reactor (if applicable).
        # Barracks and Starports can have Reactors. Factories can too.
        elif building_type in {
            UnitTypeId.BARRACKS,
            UnitTypeId.FACTORY,
            UnitTypeId.STARPORT,
        }:
            needed_addon = UnitTypeId.REACTOR

        if not needed_addon:
            return []

        # 3. Check affordability.
        if not self.bot.can_afford(needed_addon):
            return []

        # 4. Issue the direct build command.
        # The build action for add-ons is an ability of the structure itself.
        # The python-sc2 library handles placement validation internally.
        cache.logger.info(
            f"Building {needed_addon.name} on {building_type.name} at {building.position.rounded}"
        )
        return [lambda b=building, a=needed_addon: b.build(a)]

        # No action was taken this frame.
        return []
```

---

### File: `terran/capabilities/structures/tech_structure_manager.py`

```python
from __future__ import annotations
from typing import TYPE_CHECKING, List

from core.interfaces.manager_abc import Manager
from core.types import CommandFunctor
from core.utilities.events import Event, EventType, BuildRequestPayload
from core.utilities.constants import EVENT_PRIORITY_NORMAL

if TYPE_CHECKING:
    from sc2.bot_ai import BotAI
    from core.global_cache import GlobalCache
    from core.event_bus import EventBus
    from core.frame_plan import FramePlan


class TechStructureManager(Manager):
    """
    Tech Path Planner.

    This manager now reads a set of desired tech buildings from the FramePlan
    and attempts to request one per frame, allowing for parallel tech progression.
    """

    def __init__(self, bot: "BotAI"):
        super().__init__(bot)

    async def execute(
        self, cache: "GlobalCache", plan: "FramePlan", bus: "EventBus"
    ) -> List[CommandFunctor]:
        """
        Reads the tech goals from the FramePlan and, if valid, publishes a BuildRequest.
        Only one request is sent per frame to avoid exhausting resources.
        """
        goal_buildings = getattr(plan, "tech_goals", set())
        if not goal_buildings:
            return []

        # Iterate through the set of desired buildings
        for goal_building in goal_buildings:
            # We already checked for prerequisites and current counts in the director.
            # Here we just need to publish the request.
            # The ConstructionManager will handle affordability.

            cache.logger.info(
                f"Tech goal {goal_building.name} is valid. Publishing build request."
            )

            payload = BuildRequestPayload(
                item_id=goal_building,
                position=self.bot.start_location,
                priority=EVENT_PRIORITY_NORMAL,
                unique=True,
            )
            bus.publish(Event(EventType.INFRA_BUILD_REQUEST, payload))

            # --- IMPORTANT ---
            # Only request ONE building per frame to allow the system to react
            # and manage resources. We break after the first valid request.
            return []

        # No valid requests could be published this frame
        return []
```

---

### File: `terran/capabilities/units/army_unit_manager.py`

```python
from __future__ import annotations
from typing import TYPE_CHECKING, List, Dict

from sc2.ids.unit_typeid import UnitTypeId
from sc2.dicts.unit_trained_from import UNIT_TRAINED_FROM
from sc2.dicts.unit_train_build_abilities import TRAIN_INFO

from core.interfaces.manager_abc import Manager
from core.types import CommandFunctor
from sc2.unit import Unit

if TYPE_CHECKING:
    from sc2.bot_ai import BotAI
    from sc2.units import Units
    from core.global_cache import GlobalCache
    from core.event_bus import EventBus
    from core.frame_plan import FramePlan


class ArmyUnitManager(Manager):
    """
    Unit Production Line Foreman.

    This manager is responsible for training army units. It reads the desired
    unit composition from the FramePlan, calculates the production deficit,
    and then attempts to train units from available, idle production structures
    within the bot's current resource and supply limits.
    """

    def __init__(self, bot: "BotAI"):
        super().__init__(bot)

    async def execute(
        self, cache: "GlobalCache", plan: "FramePlan", bus: "EventBus"
    ) -> List[CommandFunctor]:
        """
        Executes the logic to train army units based on the director's goals.
        """
        actions: List[CommandFunctor] = []
        unit_goal = getattr(plan, "unit_composition_goal", {})
        if not unit_goal:
            return []

        # Use a copy to safely modify the list of available producers for this frame
        idle_producers = cache.idle_production_structures.copy()
        if not idle_producers:
            return []

        # --- Calculate Production Deficit ---
        deficits: Dict[UnitTypeId, int] = {}
        for unit_id, target_count in unit_goal.items():
            current_count = cache.friendly_army_units(
                unit_id
            ).amount + self.bot.already_pending(unit_id)
            if current_count < target_count:
                deficits[unit_id] = target_count - current_count

        if not deficits:
            return []

        # --- Fulfill Deficit ---
        # Iterate through the needed units and try to build them
        for unit_id, count_needed in deficits.items():
            for _ in range(count_needed):
                # We can't afford it, so no point in continuing for this unit type
                if not self.bot.can_afford(unit_id):
                    break

                producer = self._find_producer_for(unit_id, idle_producers)
                if not producer:
                    # No available building to produce this unit, move to next unit type
                    break

                # Found a producer, queue the training command
                actions.append(lambda p=producer, u=unit_id: p.train(u))
                idle_producers.remove(producer)  # Mark as used for this frame

                # If the producer has a reactor, try to queue a second unit
                if producer.has_reactor and self.bot.can_afford(unit_id):
                    actions.append(lambda p=producer, u=unit_id: p.train(u, queue=True))

        return actions

    def _find_producer_for(
        self, unit_id: UnitTypeId, available_producers: "Units"
    ) -> Unit | None:
        """
        Finds a suitable, available production building for a given unit type.
        Considers required add-ons and prefers reactors for non-tech units.

        :param unit_id: The UnitTypeId of the unit to be trained.
        :param available_producers: A Units object of idle production structures.
        :return: A suitable Unit object if one is found, otherwise None.
        """
        # Determine the building type that can train this unit.
        required_producer_types = UNIT_TRAINED_FROM.get(unit_id)
        if not required_producer_types:
            return None

        # For Terran army units, there's typically only one producer type.
        producer_type = next(iter(required_producer_types))

        # Check if a TechLab is required for this unit.
        needs_techlab = TRAIN_INFO[producer_type][unit_id].get(
            "requires_techlab", False
        )

        # Filter the available producers to match the required building type.
        candidates = available_producers.of_type(producer_type)
        if not candidates:
            return None

        # --- Find a specific building based on add-on requirements ---
        if needs_techlab:
            # Find any candidate that has a TechLab.
            for producer in candidates:
                if producer.has_techlab:
                    return producer
        else:
            # For non-tech units, prefer buildings with Reactors, then naked ones.
            # Sorting by boolean `has_reactor` (True > False) in reverse puts reactors first.
            sorted_candidates = candidates.sorted(
                key=lambda p: p.has_reactor, reverse=True
            )
            if sorted_candidates:
                return sorted_candidates.first

        # No suitable producer was found.
        return None
```

---

### File: `terran/capabilities/upgrades/research_manager.py`

```python
from __future__ import annotations
from typing import TYPE_CHECKING, List

from sc2.ids.upgrade_id import UpgradeId
from sc2.dicts.upgrade_researched_from import UPGRADE_RESEARCHED_FROM
from sc2.dicts.unit_research_abilities import RESEARCH_INFO

from core.interfaces.manager_abc import Manager
from core.types import CommandFunctor

if TYPE_CHECKING:
    from sc2.bot_ai import BotAI
    from core.global_cache import GlobalCache
    from core.event_bus import EventBus
    from core.frame_plan import FramePlan


class ResearchManager(Manager):
    """
    Technology Researcher.

    This manager is responsible for executing the research plan laid out by the
    CapabilityDirector. It reads the prioritized list of desired upgrades from
    the FramePlan and attempts to start the highest-priority research that is
    currently possible and affordable.
    """

    def __init__(self, bot: "BotAI"):
        super().__init__(bot)

    async def execute(
        self, cache: "GlobalCache", plan: "FramePlan", bus: "EventBus"
    ) -> List[CommandFunctor]:
        """
        Processes the upgrade priority list from the FramePlan and initiates
        the first available research.
        """
        upgrade_priority_list = getattr(plan, "upgrade_goal", [])
        if not upgrade_priority_list:
            return []

        for upgrade_id in upgrade_priority_list:
            # 1. Check if the upgrade is already complete or in progress.
            if self.bot.already_pending_upgrade(upgrade_id) > 0:
                continue

            # 2. Check if we can afford the upgrade.
            if not self.bot.can_afford(upgrade_id):
                continue

            # 3. Determine the required research structure.
            research_structure_type = UPGRADE_RESEARCHED_FROM.get(upgrade_id)
            if not research_structure_type:
                cache.logger.warning(
                    f"ResearchManager: No building defined for researching {upgrade_id.name}"
                )
                continue

            # 4. Find an available building to start the research.
            # CRITICAL FIX: We do NOT filter for '.idle' here. A building is busy
            # while researching, which would prevent us from ever queueing the next
            # upgrade. The `already_pending_upgrade` check prevents re-queueing
            # the same research. The game client handles rejecting a second
            # research on a single-task building like an Engineering Bay.
            available_buildings = cache.friendly_structures.of_type(
                research_structure_type
            ).ready

            # Prioritize using a truly idle building if one is available.
            building_to_use = available_buildings.idle.first_or(
                available_buildings.first
            )

            if not building_to_use:
                continue  # No ready building of the required type is available.

            # 5. Check for tech prerequisites (e.g., Armory for Level 2 upgrades).
            research_details = RESEARCH_INFO.get(research_structure_type, {}).get(
                upgrade_id
            )
            if research_details:
                required_building = research_details.get("required_building")
                if (
                    required_building
                    and self.bot.structure_type_build_progress(required_building) < 1
                ):
                    continue  # Prerequisite building not ready.

            # 6. All checks passed. Issue the research command and exit for this frame.
            cache.logger.info(
                f"Starting research for {upgrade_id.name} at {building_to_use.type_id.name}."
            )
            return [lambda b=building_to_use, u=upgrade_id: b.research(u)]

        return []
```

---

### File: `terran/general/terran_general.py`

```python
from __future__ import annotations
from typing import TYPE_CHECKING

# Core architectural components
from core.interfaces.race_general_abc import RaceGeneral
from core.types import CommandFunctor

# The Directors this General will orchestrate
from terran.infrastructure.infrastructure_director import InfrastructureDirector
from terran.capabilities.capability_director import CapabilityDirector
from terran.tactics.tactical_director import TacticalDirector

if TYPE_CHECKING:
    from sc2.bot_ai import BotAI
    from core.global_cache import GlobalCache
    from core.event_bus import EventBus
    from core.frame_plan import FramePlan


class TerranGeneral(RaceGeneral):
    """
    The Field Marshal for the Terran race.

    This class is the top-level orchestrator for all Terran-specific logic.
    It does not contain any tactical or economic logic itself. Instead, it
    owns instances of the three core functional Directors and is responsible
    for executing them in a strict, strategic order on each game step.
    """

    def __init__(self, bot: "BotAI"):
        """
        Initializes the General and all its subordinate Directors.

        The `bot` object is passed down to the Directors, as they need it
        to instantiate their own managers. The managers, in turn, use it
        as a "command factory" to create the command functors.
        """
        super().__init__(bot)
        self.infrastructure_director = InfrastructureDirector(bot)
        self.capability_director = CapabilityDirector(bot)
        self.tactical_director = TacticalDirector(bot)

    async def on_start(self):
        """
        Called once at the start of the game. Can be used for one-time
        setup tasks that require async operations.
        """
        # This is a hook for future use, e.g., pre-calculating optimal
        # defensive positions or wall-off locations.
        pass

    async def execute_step(
        self, cache: "GlobalCache", plan: "FramePlan", bus: "EventBus"
    ) -> list[CommandFunctor]:
        """
        Orchestrates the Directors and aggregates their requested actions.

        The order of execution is a critical strategic decision:
        1.  **Infrastructure:** First, assess our economy and set the resource
            budget for the frame. This informs all other decisions.
        2.  **Capabilities:** Second, based on the budget and our goals,
            decide what units, structures, or upgrades to build.
        3.  **Tactics:** Finally, with full knowledge of our economic state and
            production plans, decide how to control the army.

        :param cache: The read-only GlobalCache with the current world state.
        :param plan: The ephemeral "scratchpad" for the current frame's intentions.
        :param bus: The EventBus for reactive messaging.
        :return: An aggregated list of all command functors from all Directors.
        """
        actions: list[CommandFunctor] = []

        # The core orchestration sequence.
        actions.extend(await self.infrastructure_director.execute(cache, plan, bus))
        actions.extend(await self.capability_director.execute(cache, plan, bus))
        actions.extend(await self.tactical_director.execute(cache, plan, bus))

        return actions
```

---

### File: `terran/infrastructure/infrastructure_director.py`

```python
from __future__ import annotations
from typing import TYPE_CHECKING, List

from sc2.ids.unit_typeid import UnitTypeId

from core.interfaces.director_abc import Director
from core.interfaces.manager_abc import Manager
from core.types import CommandFunctor
from core.frame_plan import EconomicStance
from .units.scv_manager import SCVManager
from .units.mule_manager import MuleManager
from .structures.supply_manager import SupplyManager
from .structures.expansion_manager import ExpansionManager
from .structures.repair_manager import RepairManager
from .structures.construction_manager import ConstructionManager

if TYPE_CHECKING:
    from sc2.bot_ai import BotAI
    from core.global_cache import GlobalCache
    from core.event_bus import EventBus
    from core.frame_plan import FramePlan


class InfrastructureDirector(Director):
    """
    The Chancellor. Manages economic strategy and resource allocation.
    Its primary role is to set the budget for the frame and orchestrate its
    subordinate managers to execute the economic plan.
    """

    def __init__(self, bot: "BotAI"):
        super().__init__(bot)
        self.workers_per_base_to_expand = 18

        self.scv_manager = SCVManager(bot)
        self.mule_manager = MuleManager(bot)
        self.supply_manager = SupplyManager(bot)
        self.expansion_manager = ExpansionManager(bot)
        self.repair_manager = RepairManager(bot)
        self.construction_manager = ConstructionManager(bot)

        # The execution order of managers is strategically significant.
        self.managers: List[Manager] = [
            self.scv_manager,
            self.mule_manager,
            self.supply_manager,
            self.expansion_manager,
            self.repair_manager,
            self.construction_manager,  # Construction is last to fulfill requests made this frame.
        ]

    def _set_economic_goals(self, cache: "GlobalCache", plan: "FramePlan"):
        """
        Analyzes the game state to decide the economic priority for the frame
        and sets it in the FramePlan. This is the Director's primary decision.
        """
        num_bases = self.bot.townhalls.amount
        worker_trigger_count = num_bases * self.workers_per_base_to_expand

        # Check if a Command Center is already being built or is in the construction queue.
        # We need to ask the ConstructionManager about its queue.
        is_expansion_in_queue = any(
            req.item_id == UnitTypeId.COMMANDCENTER
            for req in self.construction_manager.build_queue
        )
        is_already_expanding = (
            self.bot.already_pending(UnitTypeId.COMMANDCENTER) > 0
            or is_expansion_in_queue
        )

        # Decision: If we have enough workers and are not already expanding, our goal is to save for one.
        if (
            cache.friendly_workers.amount >= worker_trigger_count
            and not is_already_expanding
        ):
            plan.set_economic_stance(EconomicStance.SAVING_FOR_EXPANSION)
            cache.logger.info("Economic stance set to SAVING_FOR_EXPANSION.")
        else:
            plan.set_economic_stance(EconomicStance.NORMAL)

    async def execute(
        self, cache: "GlobalCache", plan: "FramePlan", bus: "EventBus"
    ) -> list[CommandFunctor]:
        """
        Executes the director's logic and orchestrates its managers.
        """
        # 1. Director's High-Level Logic
        # Sets the official resource budget for the frame.
        if len(self.bot.townhalls) < 3:
            plan.set_budget(infrastructure=70, capabilities=30)
        else:
            plan.set_budget(infrastructure=30, capabilities=70)

        # Sets the economic goal (e.g., should we be saving for an expansion?).
        self._set_economic_goals(cache, plan)

        # 2. Orchestrate Subordinate Managers
        actions: list[CommandFunctor] = []
        for manager in self.managers:
            manager_actions = await manager.execute(cache, plan, bus)
            actions.extend(manager_actions)

        return actions
```

---

### File: `terran/infrastructure/structures/construction_manager.py`

```python
from __future__ import annotations
from typing import TYPE_CHECKING, List

from sc2.ids.unit_typeid import UnitTypeId

from core.interfaces.manager_abc import Manager
from core.types import CommandFunctor
from core.utilities.events import Event, EventType, BuildRequestPayload
from core.utilities.unit_types import WORKER_TYPES

if TYPE_CHECKING:
    from sc2.bot_ai import BotAI
    from core.global_cache import GlobalCache
    from core.event_bus import EventBus
    from core.frame_plan import FramePlan


class ConstructionManager(Manager):
    """
    The Civil Engineering Service. This manager is a service that fulfills
    build requests published to the EventBus. It maintains a prioritized queue
    and handles the low-level logic of finding a placement and assigning a worker.
    """

    def __init__(self, bot: "BotAI"):
        super().__init__(bot)
        self.build_queue: List[BuildRequestPayload] = []
        # Subscribe to build requests from the event bus
        bot.event_bus.subscribe(
            EventType.INFRA_BUILD_REQUEST, self.handle_build_request
        )

    async def handle_build_request(self, event: Event):
        """Event handler that adds a new build request to the queue."""
        payload: BuildRequestPayload = event.payload
        if payload.unique:
            is_duplicate = any(
                req.item_id == payload.item_id for req in self.build_queue
            )
            if is_duplicate:
                self.bot.global_cache.logger.debug(
                    f"Ignoring duplicate build request for unique item: {payload.item_id.name}"
                )
                return
        self.build_queue.append(payload)

    async def execute(
        self, cache: "GlobalCache", plan: "FramePlan", bus: "EventBus"
    ) -> List[CommandFunctor]:
        """
        Processes the build queue, attempting to construct the highest-priority
        affordable building each frame.
        """
        if not self.build_queue:
            return []

        # Sort queue by priority (lower number is higher priority)
        self.build_queue.sort(key=lambda req: req.priority)

        # Attempt to process the highest priority request
        request = self.build_queue[0]

        if not self.bot.can_afford(request.item_id):
            return []  # Can't afford the top priority, wait for more resources

        gas_buildings = {
            UnitTypeId.REFINERY,
            UnitTypeId.EXTRACTOR,
            UnitTypeId.ASSIMILATOR,
        }

        # --- Special logic for Gas Buildings ---
        if request.item_id in gas_buildings:
            # Find an unoccupied geyser near the requested position or any townhall.
            search_point = request.position or self.bot.start_location
            geysers = self.bot.vespene_geyser.filter(
                lambda g: not self.bot.structures.closer_than(1.0, g).exists()
            )
            if geysers.exists:
                geyser = geysers.closest_to(search_point)
                worker = self.bot.select_build_worker(geyser.position)
                if worker:
                    self.build_queue.pop(0)  # Remove fulfilled request
                    # Wrap the command in a lambda to defer execution
                    return [lambda: worker.build_gas(geyser)]
            return []  # No available geyser or worker, retry next frame

        # --- Standard logic for all other buildings ---
        search_origin = request.position or self.bot.start_location
        placement_position = await self.bot.find_placement(
            request.item_id, near=search_origin
        )

        if not placement_position:
            # Can't find placement, maybe the area is blocked. Retry next frame.
            return []

        worker = self.bot.select_build_worker(placement_position)
        if not worker:
            # No worker available, retry next frame.
            return []

        # We have a valid placement, a worker, and can afford it.
        self.build_queue.pop(0)  # Remove fulfilled request
        # Wrap the command in a lambda to defer execution
        return [lambda: worker.build(request.item_id, placement_position)]
```

---

### File: `terran/infrastructure/structures/expansion_manager.py`

```python
from __future__ import annotations
from typing import TYPE_CHECKING, List

from sc2.ids.unit_typeid import UnitTypeId

from core.frame_plan import EconomicStance
from core.interfaces.manager_abc import Manager
from core.types import CommandFunctor
from core.utilities.events import Event, EventType, BuildRequestPayload
from core.utilities.constants import EVENT_PRIORITY_NORMAL

if TYPE_CHECKING:
    from sc2.bot_ai import BotAI
    from core.global_cache import GlobalCache
    from core.event_bus import EventBus
    from core.frame_plan import FramePlan


class ExpansionManager(Manager):
    """
    Manages the bot's strategic expansion timing and location.
    It determines WHEN to expand based on the Director's plan and publishes a
    request for the ConstructionManager to handle.
    """

    def __init__(self, bot: "BotAI"):
        super().__init__(bot)

    async def execute(
        self, cache: "GlobalCache", plan: "FramePlan", bus: "EventBus"
    ) -> List[CommandFunctor]:
        """
        If the director has ordered an expansion, find a location and request it.
        """
        # This manager's only trigger is the Director's economic stance.
        if plan.economic_stance != EconomicStance.SAVING_FOR_EXPANSION:
            return []

        # The director has already determined we are not currently expanding.
        # This manager's job is now simply to find the location and publish the request.
        # The ConstructionManager will handle affordability.

        next_expansion_location = await self.bot.get_next_expansion()

        if next_expansion_location:
            cache.logger.info(
                f"Economic goal is to expand. Requesting COMMANDCENTER at {next_expansion_location.rounded}"
            )
            # Publish a request to build a Command Center.
            # We use 'unique=True' to prevent spamming the build queue on subsequent frames
            # while we are saving up minerals. The ConstructionManager will handle this.
            payload = BuildRequestPayload(
                item_id=UnitTypeId.COMMANDCENTER,
                position=next_expansion_location,
                priority=EVENT_PRIORITY_NORMAL,
                unique=True,
            )
            bus.publish(Event(EventType.INFRA_BUILD_REQUEST, payload))

        # This manager only publishes events, it does not issue direct commands.
        return []
```

---

### File: `terran/infrastructure/structures/repair_manager.py`

```python
from __future__ import annotations
from typing import TYPE_CHECKING, List, Set

from core.interfaces.manager_abc import Manager
from core.types import CommandFunctor
from core.utilities.events import Event, EventType, UnitTookDamagePayload

if TYPE_CHECKING:
    from sc2.bot_ai import BotAI
    from sc2.unit import Unit
    from core.global_cache import GlobalCache
    from core.event_bus import EventBus
    from core.frame_plan import FramePlan


class RepairManager(Manager):
    """
    Damage Control. This manager subscribes to damage events and dispatches
    idle SCVs to repair damaged mechanical units and structures.
    """

    def __init__(self, bot: "BotAI"):
        super().__init__(bot)
        self.repair_targets: Set[int] = set()
        bus = bot.event_bus
        bus.subscribe(EventType.TACTICS_UNIT_TOOK_DAMAGE, self.handle_unit_took_damage)

    async def handle_unit_took_damage(self, event: Event):
        """
        Event handler that adds a damaged unit's tag to a set for future processing.
        """
        payload: UnitTookDamagePayload = event.payload
        self.repair_targets.add(payload.unit_tag)

    async def execute(
        self, cache: "GlobalCache", plan: "FramePlan", bus: "EventBus"
    ) -> List[CommandFunctor]:
        """
        Assigns idle SCVs to repair targets from the queue.
        """
        actions: List[CommandFunctor] = []
        if not self.repair_targets or not cache.friendly_workers.exists:
            return []

        # Identify targets already being repaired to avoid redundant commands
        repairing_workers = cache.friendly_workers.filter(lambda w: w.is_repairing)
        active_repair_targets = {
            order.target for worker in repairing_workers for order in worker.orders
        }

        # Use a copy to allow modification during iteration
        targets_to_process = self.repair_targets.copy()

        available_workers = cache.friendly_workers.idle.copy()

        for unit_tag in targets_to_process:
            if not available_workers:
                break  # No more workers to assign

            if unit_tag in active_repair_targets:
                self.repair_targets.remove(unit_tag)
                continue

            target_unit: Unit | None = cache.friendly_units.find_by_tag(unit_tag)

            # Cleanup invalid or fully repaired targets
            if (
                not target_unit
                or target_unit.health_percentage >= 1
                or not (target_unit.is_mechanical or target_unit.is_structure)
            ):
                self.repair_targets.remove(unit_tag)
                continue

            # Assign the closest available worker
            worker_to_assign = available_workers.closest_to(target_unit)
            # Wrap the command in a lambda to defer execution
            actions.append(lambda t=target_unit, w=worker_to_assign: w.repair(t))

            # Remove worker and target from pools for this frame
            available_workers.remove(worker_to_assign)
            self.repair_targets.remove(unit_tag)

        return actions
```

---

### File: `terran/infrastructure/structures/supply_manager.py`

```python
from __future__ import annotations
from typing import TYPE_CHECKING, List

from sc2.ids.unit_typeid import UnitTypeId

from core.interfaces.manager_abc import Manager
from core.frame_plan import EconomicStance
from core.types import CommandFunctor
from core.utilities.events import Event, EventType, BuildRequestPayload
from core.utilities.constants import (
    SUPPLY_BUFFER_BASE,
    SUPPLY_BUFFER_PER_PRODUCTION_STRUCTURE,
    EVENT_PRIORITY_HIGH,
)
from core.utilities.unit_types import TERRAN_PRODUCTION_TYPES

if TYPE_CHECKING:
    from sc2.bot_ai import BotAI
    from core.global_cache import GlobalCache
    from core.event_bus import EventBus
    from core.frame_plan import FramePlan


class SupplyManager(Manager):
    """
    Manages the bot's supply to prevent it from getting supply blocked.
    It does not issue direct build commands but instead publishes a high-priority
    build request to the EventBus.
    """

    def __init__(self, bot: "BotAI"):
        super().__init__(bot)

    async def execute(
        self, cache: "GlobalCache", plan: "FramePlan", bus: "EventBus"
    ) -> List[CommandFunctor]:
        """
        Checks supply and requests a new Supply Depot if needed.
        """
        if cache.supply_cap >= 200:
            return []

        # Check for pending depots + depots in construction to avoid over-building.
        if (
            self.bot.already_pending(UnitTypeId.SUPPLYDEPOT)
            + self.bot.structures(UnitTypeId.SUPPLYDEPOT).not_ready.amount
            > 0
        ):
            return []

        required_buffer = 0
        if plan.economic_stance == EconomicStance.SAVING_FOR_EXPANSION:
            required_buffer = 2
        else:
            num_production_structures = cache.friendly_structures.of_type(
                TERRAN_PRODUCTION_TYPES
            ).amount
            required_buffer = (
                SUPPLY_BUFFER_BASE
                + num_production_structures * SUPPLY_BUFFER_PER_PRODUCTION_STRUCTURE
            )

        if cache.supply_left < required_buffer:
            # --- CORRECTED: Smarter and Safer Placement Logic ---
            placement_pos = self.bot.start_location  # Default fallback

            # CRITICAL CHECK: Ensure a ready townhall exists before trying to access it.
            ready_townhalls = self.bot.townhalls.ready
            if ready_townhalls.exists:
                main_th = ready_townhalls.first
                mineral_fields = self.bot.mineral_field.closer_than(10, main_th)
                if mineral_fields.exists:
                    # Calculate a point "behind" the townhall, away from the minerals.
                    placement_pos = main_th.position.towards(mineral_fields.center, -8)
            # --- END CORRECTION ---

            payload = BuildRequestPayload(
                item_id=UnitTypeId.SUPPLYDEPOT,
                position=placement_pos,
                priority=EVENT_PRIORITY_HIGH,
                unique=True,
            )
            bus.publish(Event(EventType.INFRA_BUILD_REQUEST, payload))
            cache.logger.info(
                f"Supply low. Requesting SUPPLYDEPOT near {placement_pos.rounded}"
            )

        return []
```

---

### File: `terran/infrastructure/units/mule_manager.py`

```python
from __future__ import annotations
from typing import TYPE_CHECKING, List

from sc2.ids.unit_typeid import UnitTypeId
from sc2.ids.ability_id import AbilityId
from sc2.data import race_townhalls

from core.interfaces.manager_abc import Manager
from core.types import CommandFunctor

if TYPE_CHECKING:
    from sc2.bot_ai import BotAI
    from core.global_cache import GlobalCache
    from core.event_bus import EventBus
    from core.frame_plan import FramePlan


class MuleManager(Manager):
    """
    Manages the usage of Orbital Command energy for calling down MULEs.
    """

    def __init__(self, bot: "BotAI"):
        super().__init__(bot)

    async def execute(
        self, cache: "GlobalCache", plan: "FramePlan", bus: "EventBus"
    ) -> List[CommandFunctor]:
        """
        Finds Orbital Commands with enough energy and calls down MULEs on the
        most effective mineral patches.
        """
        actions: List[CommandFunctor] = []
        terran_townhalls = race_townhalls[self.bot.race]

        # Find OCs with enough energy for a MULE
        orbitals = cache.friendly_structures.of_type(
            UnitTypeId.ORBITALCOMMAND
        ).ready.filter(lambda oc: oc.energy >= 50)

        if not orbitals:
            return []

        # Find ready townhalls to determine which mineral patches are ours
        townhalls = cache.friendly_structures.of_type(terran_townhalls).ready
        if not townhalls:
            return []

        # Select the OC with the most energy to call down the MULE
        oc_to_use = orbitals.sorted(lambda o: o.energy, reverse=True).first

        # Find the best mineral patch to drop the MULE on.
        best_mineral_patch = None
        highest_minerals = 0
        for th in townhalls:
            patches = self.bot.mineral_field.closer_than(10, th)
            if not patches:
                continue
            richest_patch = patches.sorted(
                lambda p: p.mineral_contents, reverse=True
            ).first
            if richest_patch.mineral_contents > highest_minerals:
                highest_minerals = richest_patch.mineral_contents
                best_mineral_patch = richest_patch

        if best_mineral_patch:
            actions.append(
                lambda oc=oc_to_use, patch=best_mineral_patch: oc(
                    AbilityId.CALLDOWNMULE_CALLDOWNMULE, patch
                )
            )

        return actions
```

---

### File: `terran/infrastructure/units/scv_manager.py`

```python
from __future__ import annotations
from typing import TYPE_CHECKING, List

from sc2.ids.unit_typeid import UnitTypeId
from sc2.data import race_townhalls

from core.interfaces.manager_abc import Manager
from core.types import CommandFunctor
from core.utilities.constants import MAX_WORKER_COUNT

if TYPE_CHECKING:
    from sc2.bot_ai import BotAI
    from sc2.units import Units
    from core.global_cache import GlobalCache
    from core.event_bus import EventBus
    from core.frame_plan import FramePlan


class SCVManager(Manager):
    """
    Manages SCV production and worker assignment to mineral lines.
    """

    def __init__(self, bot: "BotAI"):
        super().__init__(bot)

    async def execute(
        self, cache: "GlobalCache", plan: "FramePlan", bus: "EventBus"
    ) -> List[CommandFunctor]:
        """
        Handles SCV training and assigns idle workers to mineral lines.
        """
        actions: List[CommandFunctor] = []
        terran_townhalls = race_townhalls[self.bot.race]

        # --- 1. SCV Production ---
        worker_target = MAX_WORKER_COUNT
        current_worker_count = cache.friendly_workers.amount
        pending_worker_count = self.bot.already_pending(UnitTypeId.SCV)

        if (
            current_worker_count + pending_worker_count < worker_target
            and self.bot.can_afford(UnitTypeId.SCV)
        ):
            # Check for townhalls that are ready and have queue space
            producible_townhalls: Units = cache.friendly_structures.of_type(
                terran_townhalls
            ).ready.filter(lambda th: len(th.orders) < 1)

            if producible_townhalls.exists:
                th = producible_townhalls.first
                cache.logger.debug(
                    f"Training SCV from {th.type_id} at {th.position.rounded}"
                )
                actions.append(lambda: th.train(UnitTypeId.SCV))

        # --- 2. Worker Assignment to Undersaturated Bases ---
        idle_workers = cache.friendly_workers.idle
        if not idle_workers:
            return actions

        all_townhalls = cache.friendly_structures.of_type(terran_townhalls).ready
        if not all_townhalls.exists:
            return actions

        unsaturated_townhalls = all_townhalls.filter(
            lambda th: th.surplus_harvesters < 0
        )

        for worker in idle_workers:
            if unsaturated_townhalls.exists:
                target_th = unsaturated_townhalls.closest_to(worker)
            else:
                target_th = all_townhalls.closest_to(worker)

            local_minerals = self.bot.mineral_field.closer_than(10, target_th)
            if local_minerals.exists:
                target_mineral = local_minerals.sorted(
                    key=lambda mf: mf.assigned_harvesters
                ).first
                actions.append(lambda w=worker, m=target_mineral: w.gather(m))

        return actions
```

---

### File: `terran/specialists/build_orders/two_rax_reaper.py`

```python
from __future__ import annotations
from typing import TYPE_CHECKING, List, Tuple, Union

from sc2.ids.unit_typeid import UnitTypeId
from sc2.ids.upgrade_id import UpgradeId

if TYPE_CHECKING:
    from sc2.bot_ai import BotAI

# A build item can be a UnitTypeId for training/building, or an UpgradeId for research.
BuildItem = Union[UnitTypeId, UpgradeId]


class TwoRaxReaper:
    """
    Strategic Recipe: A standard 2 Barracks Reaper opening build order.

    This class provides a static, timed sequence of production goals. It acts as an
    iterator that the CapabilityDirector can query on each frame. When the bot's
    current supply meets the trigger for the next step, this class provides the
    item to be built and advances its internal state.
    """

    def __init__(self, bot: "BotAI"):
        self.bot = bot
        # The core build order sequence: (supply_trigger, item_to_build)
        self.build_order: List[Tuple[int, BuildItem]] = [
            # --- Opening Phase ---
            (14, UnitTypeId.SUPPLYDEPOT),  # Build first depot at 14 supply
            (15, UnitTypeId.SCV),  # Continue worker production
            (16, UnitTypeId.BARRACKS),  # First Barracks
            (16, UnitTypeId.REFINERY),  # First Gas
            (17, UnitTypeId.SCV),
            (18, UnitTypeId.BARRACKS),  # Second Barracks
            (19, UnitTypeId.SCV),
            (20, UnitTypeId.ORBITALCOMMAND),  # Morph CC to Orbital as soon as it's done
            # --- Reaper Production Phase ---
            (20, UnitTypeId.REAPER),  # First Reaper
            (21, UnitTypeId.REAPER),  # Second Reaper from second Barracks
            (22, UnitTypeId.SUPPLYDEPOT),  # Second Depot to stay ahead
            (23, UnitTypeId.SCV),
            (24, UnitTypeId.REAPER),
            (25, UnitTypeId.REAPER),
            (26, UnitTypeId.REFINERY),  # Second Gas for tech follow-up
            (27, UnitTypeId.SCV),
            # This is where the build order ends. The CapabilityDirector will take over with dynamic logic.
        ]
        self.current_step_index = 0

    def is_complete(self) -> bool:
        """
        Checks if the entire build order sequence has been completed.

        :return: True if all steps have been issued, False otherwise.
        """
        return self.current_step_index >= len(self.build_order)

    def get_next_item(self, current_supply: int) -> BuildItem | None:
        """
        Gets the next item to produce from the build order if the supply trigger is met.

        The CapabilityDirector calls this method every frame. If the bot's current supply
        is high enough for the current step, this method returns the item to build
        and advances to the next step. Otherwise, it returns None.

        :param current_supply: The bot's current supply_used.
        :return: A UnitTypeId or UpgradeId if the condition is met, otherwise None.
        """
        if self.is_complete():
            return None

        # Get the current step from the build order
        supply_trigger, item_to_build = self.build_order[self.current_step_index]

        # Check if the bot has reached the required supply count for this step
        if current_supply >= supply_trigger:
            self.current_step_index += 1
            return item_to_build

        # Supply requirement not yet met
        return None
```

---

### File: `terran/specialists/micro/marine_controller.py`

```python
from __future__ import annotations
from typing import TYPE_CHECKING, List, Set, Tuple

from sc2.ids.unit_typeid import UnitTypeId
from sc2.ids.buff_id import BuffId
from sc2.ids.ability_id import AbilityId
from sc2.position import Point2

from core.types import CommandFunctor
from core.utilities.unit_value import calculate_threat_value

if TYPE_CHECKING:
    from sc2.unit import Unit
    from sc2.units import Units
    from core.global_cache import GlobalCache

# A prioritized list of targets for marines. They will always try to kill the first unit type in this list first.
MARINE_TARGET_PRIORITIES: List[UnitTypeId] = [
    # Highest priority splash threats that can wipe out a bio ball instantly.
    UnitTypeId.BANELING,
    UnitTypeId.HIGHTEMPLAR,
    UnitTypeId.DISRUPTOR,
    UnitTypeId.SIEGETANKSIEGED,
    UnitTypeId.WIDOWMINEBURROWED,
    # Key casters and high-value units that need to be removed quickly.
    UnitTypeId.INFESTOR,
    UnitTypeId.QUEEN,
]


class MarineController:
    """
    Infantry Micro Expert.

    This controller manages the detailed, real-time actions of a squad of Marines.
    It is responsible for stutter-stepping, intelligent Stimpack usage, and
    prioritizing high-threat targets.
    """

    def execute(
        self, marines: "Units", target: Point2, cache: "GlobalCache"
    ) -> Tuple[List[CommandFunctor], Set[int]]:
        """
        Executes micro-management for a squad of marines.

        :param marines: The Units object containing the marines to be controlled.
        :param target: The high-level target position from the ArmyControlManager.
        :param cache: The global cache for accessing game state.
        :return: A tuple containing (list of command functors, set of handled unit tags).
        """
        actions: List[CommandFunctor] = []
        if not marines:
            return [], set()

        # Find all enemies within a generous engagement range of the marine squad's center.
        nearby_enemies = cache.enemy_units.closer_than(15, marines.center)
        if not nearby_enemies:
            # If no enemies are nearby, issue a single attack-move command for each marine.
            return [
                lambda m=marine, t=target: m.attack(t) for marine in marines
            ], marines.tags

        # --- 1. Target Prioritization ---
        # Get the TAG of the best target, then find the fresh Unit object for this frame.
        squad_target_tag = self._get_best_target_tag(marines, nearby_enemies)
        squad_target = (
            nearby_enemies.find_by_tag(squad_target_tag) if squad_target_tag else None
        )

        # --- 2. Stimpack Management ---
        if self._should_stim(marines, nearby_enemies, cache):
            stim_marines = marines.filter(
                lambda m: not m.has_buff(BuffId.STIMPACK) and m.health > 20
            )
            if stim_marines:
                # Create an individual stim command for EACH marine.
                actions.extend(
                    [
                        lambda m=marine: m(AbilityId.EFFECT_STIM)
                        for marine in stim_marines
                    ]
                )
                cache.logger.info("Marines are using Stimpack.")

        # --- 3. Individual Stutter-Step Micro ---
        for marine in marines:
            # A. Survival Instinct: Low health marines should retreat.
            if marine.health_percentage < 0.35 and nearby_enemies.exists:
                retreat_pos = marine.position.towards(nearby_enemies.center, -3)
                actions.append(lambda m=marine, p=retreat_pos: m.move(p))
                continue

            # B. Combat Micro: If a target exists, perform stutter-step logic.
            if squad_target:
                if marine.weapon_cooldown == 0:
                    actions.append(lambda m=marine, t=squad_target: m.attack(t))
                else:
                    if marine.distance_to(squad_target) < marine.ground_range:
                        move_pos = marine.position.towards(squad_target.position, -1)
                    else:
                        move_pos = marine.position.towards(squad_target.position, 1)
                    actions.append(lambda m=marine, p=move_pos: m.move(p))
            # C. Fallback: If no specific target, attack-move towards the strategic objective.
            else:
                actions.append(lambda m=marine, t=target: m.attack(t))

        # This controller handles all marines passed to it.
        return actions, marines.tags

    def _get_best_target_tag(self, marines: "Units", enemies: "Units") -> int | None:
        """
        Finds the TAG of the most dangerous enemy unit for the squad to focus fire.
        Returns a tag to prevent using stale Unit objects from previous frames.
        """
        for priority_id in MARINE_TARGET_PRIORITIES:
            priority_targets = enemies.of_type(priority_id)
            if priority_targets.exists:
                return priority_targets.closest_to(marines.center).tag

        attackable_enemies = enemies.filter(
            lambda e: not e.is_flying and e.can_be_attacked
        )
        if attackable_enemies:
            return min(attackable_enemies, key=lambda e: e.health).tag

        return None

    def _should_stim(
        self, marines: "Units", enemies: "Units", cache: "GlobalCache"
    ) -> bool:
        """
        Determines if it is strategically sound to use Stimpack based on health and threat.
        """
        if marines.amount == 0:
            return False

        if (sum(m.health for m in marines) / marines.amount) < 35:
            return False

        stimmed_count = marines.filter(lambda m: m.has_buff(BuffId.STIMPACK)).amount
        if stimmed_count / marines.amount > 0.5:
            return False

        enemy_threat_value = sum(calculate_threat_value(e.type_id) for e in enemies)
        if enemy_threat_value > 30:
            return True

        return False
```

---

### File: `terran/specialists/micro/medivac_controller.py`

```python
from __future__ import annotations
from typing import TYPE_CHECKING, List, Set, Tuple

from sc2.ids.ability_id import AbilityId
from sc2.ids.unit_typeid import UnitTypeId
from sc2.ids.buff_id import BuffId
from sc2.position import Point2

from core.types import CommandFunctor

if TYPE_CHECKING:
    from sc2.unit import Unit
    from sc2.units import Units
    from core.global_cache import GlobalCache

# A set of high-priority anti-air threats that Medivacs must respect before boosting.
ANTI_AIR_THREATS: Set[UnitTypeId] = {
    UnitTypeId.VIKINGFIGHTER,
    UnitTypeId.CORRUPTOR,
    UnitTypeId.PHOENIX,
    UnitTypeId.MUTALISK,
    UnitTypeId.MISSILETURRET,
    UnitTypeId.SPORECRAWLER,
    UnitTypeId.PHOTONCANNON,
    UnitTypeId.HYDRALISK,
}

# Dangerous area-of-effect buffs/spells to dodge.
DODGE_BUFFS: Set[BuffId] = {
    BuffId.PSISTORM,
    BuffId.FUNGALGROWTH,
}

# The ideal distance a Medivac should stay behind its heal target.
HEAL_FOLLOW_DISTANCE = 2.5


class MedivacController:
    """
    Combat Medic and Transport Pilot.

    This advanced controller manages Medivacs with a focus on survivability and
    efficiency. It uses threat analysis for positioning and ability usage.
    """

    def execute(
        self,
        medivacs: "Units",
        bio_squad: "Units",
        target: Point2,
        cache: "GlobalCache",
    ) -> Tuple[List[CommandFunctor], Set[int]]:
        """
        Executes intelligent micro for a squad of Medivacs.

        :param medivacs: The Units object of Medivacs to be controlled.
        :param bio_squad: The Units object of bio units the Medivacs are supporting.
        :param target: The high-level target position for the army.
        :param cache: The global cache for accessing game state.
        :return: A tuple containing (list of command functors, set of handled unit tags).
        """
        actions: List[CommandFunctor] = []
        if not medivacs or not bio_squad.exists:
            return [], set()

        nearby_enemies = cache.enemy_units.closer_than(15, bio_squad.center)

        for medivac in medivacs:
            # --- 1. Survival: Dodge immediate threats ---
            if any(medivac.has_buff(b) for b in DODGE_BUFFS):
                # If caught in a storm or fungal, boost away immediately.
                if medivac.energy >= 10:  # Energy for boost
                    actions.append(
                        lambda m=medivac: m(AbilityId.EFFECT_MEDIVACIGNITEAFTERBURNERS)
                    )
                retreat_pos = medivac.position.towards(nearby_enemies.center, -5)
                actions.append(lambda m=medivac, p=retreat_pos: m.move(p))
                continue  # Skip other logic for this frame

            # --- 2. Find the best unit to heal ---
            heal_target = self._find_best_heal_target(medivac, bio_squad)

            # --- 3. Determine the best position ---
            if heal_target:
                move_pos = self._calculate_safe_heal_position(
                    medivac, heal_target, nearby_enemies
                )
            else:
                move_pos = self._calculate_safe_squad_position(
                    medivac, bio_squad, nearby_enemies
                )

            # --- 4. Decide whether to use boost ---
            if self._should_boost(medivac, bio_squad, target, nearby_enemies, cache):
                actions.append(
                    lambda m=medivac: m(AbilityId.EFFECT_MEDIVACIGNITEAFTERBURNERS)
                )
                cache.logger.debug(f"Medivac {medivac.tag} boosting.")

            # --- 5. Issue the final move command ---
            if medivac.distance_to(move_pos) > 1.5:
                actions.append(lambda m=medivac, p=move_pos: m.move(p))

        # This controller handles all medivacs passed to it.
        return actions, medivacs.tags

    def _should_boost(
        self,
        medivac: "Unit",
        bio_squad: "Units",
        target: Point2,
        enemies: "Units",
        cache: "GlobalCache",
    ) -> bool:
        """Determines if it's a good time for an individual Medivac to boost."""
        # Don't boost if ability is on cooldown or energy is too low.
        if medivac.energy < 10:
            return False

        # --- Retreat Boost ---
        # If the squad is hurt (<60% avg health) and under fire, boost to escape.
        if bio_squad.amount > 0:
            avg_health = (
                sum(u.shield_health_percentage for u in bio_squad) / bio_squad.amount
            )
            if avg_health < 0.6 and enemies.exists:
                return True

        # --- Engage Boost ---
        # If the army is far from its strategic target, consider boosting.
        if bio_squad.center.distance_to(target) > 20:
            # SAFETY CHECK: Do not boost into a known anti-air nest.
            enemies_at_target = cache.known_enemy_units.closer_than(10, target)
            aa_threats = enemies_at_target.of_type(ANTI_AIR_THREATS)
            if aa_threats.amount > 2:
                cache.logger.warning(
                    f"Medivac boost cancelled: {aa_threats.amount} AA threats detected at target."
                )
                return False
            return True

        return False

    def _find_best_heal_target(
        self, medivac: "Unit", bio_squad: "Units"
    ) -> "Unit" | None:
        """Finds the most wounded, non-full-health bio unit near a Medivac."""
        # A "leash" to prevent medivacs from chasing units too far away.
        leash_range = 12

        damaged_bio = bio_squad.filter(
            lambda u: u.health_percentage < 1 and medivac.distance_to(u) < leash_range
        )

        if not damaged_bio.exists:
            return None

        # Return the unit with the lowest health percentage to prioritize focused healing.
        return min(damaged_bio, key=lambda u: u.health_percentage)

    def _calculate_safe_heal_position(
        self, medivac: "Unit", heal_target: "Unit", enemies: "Units"
    ) -> Point2:
        """Calculates a position behind the heal_target, away from enemies."""
        if not enemies.exists:
            # If no enemies, just follow closely behind the target.
            return heal_target.position.towards(medivac.position, HEAL_FOLLOW_DISTANCE)

        # Vector from the center of enemies towards our healing target. This is the "safe" direction.
        safe_vector = enemies.center.direction_vector(heal_target.position)

        # If the vector is zero (units are on top of each other), default to a simple fallback.
        if safe_vector.x == 0 and safe_vector.y == 0:
            return heal_target.position.towards(medivac.position, HEAL_FOLLOW_DISTANCE)

        # The ideal position is a few units behind the heal target along the safe vector.
        return heal_target.position + (safe_vector * HEAL_FOLLOW_DISTANCE)

    def _calculate_safe_squad_position(
        self, medivac: "Unit", bio_squad: "Units", enemies: "Units"
    ) -> Point2:
        """Calculates a safe position behind the entire bio squad when no specific unit needs healing."""
        squad_center = bio_squad.center
        if not enemies.exists:
            return squad_center

        safe_vector = enemies.center.direction_vector(squad_center)
        if safe_vector.x == 0 and safe_vector.y == 0:
            return squad_center  # Fallback if centers overlap

        return squad_center + (safe_vector * HEAL_FOLLOW_DISTANCE)
```

---

### File: `terran/specialists/micro/tank_controller.py`

```python
from __future__ import annotations
from typing import TYPE_CHECKING, List, Set, Tuple

from sc2.ids.unit_typeid import UnitTypeId
from sc2.position import Point2

from core.frame_plan import ArmyStance
from core.types import CommandFunctor
from core.utilities.geometry import find_safe_point_from_threat_map

if TYPE_CHECKING:
    from sc2.unit import Unit
    from sc2.units import Units
    from core.global_cache import GlobalCache

# --- Tunable Constants for Tank Behavior ---
SIEGE_RANGE = 13
MINIMUM_RANGE = 2
SIEGE_THREAT_THRESHOLD = 3  # Min enemy supply in range to consider sieging.
LEAPFROG_DISTANCE = 6  # How far behind the bio ball tanks should stay.
SPLASH_RADIUS = 1.5  # Estimated splash radius for friendly fire check.
FRIENDLY_FIRE_THRESHOLD = 3  # Don't siege if it would splash this many friendlies.

BIO_UNIT_TYPES = {
    UnitTypeId.MARINE,
    UnitTypeId.MARAUDER,
    UnitTypeId.REAPER,
    UnitTypeId.GHOST,
}


class TankController:
    """
    Siege Artillery Specialist.

    This advanced controller manages Siege Tanks with a focus on intelligent
    positioning, threat assessment, and friendly fire avoidance.
    """

    def execute(
        self, tanks: "Units", target: Point2, cache: "GlobalCache"
    ) -> Tuple[List[CommandFunctor], Set[int]]:
        """
        Executes micro-management for a squad of Siege Tanks.

        :param tanks: The Units object of tanks to be controlled.
        :param target: The high-level target position from the ArmyControlManager.
        :param cache: The global cache for accessing game state.
        :return: A tuple containing (list of command functors, set of handled unit tags).
        """
        actions: List[CommandFunctor] = []
        if not tanks:
            return [], set()

        nearby_enemies = cache.enemy_units.closer_than(SIEGE_RANGE + 5, tanks.center)
        friendly_bio = cache.friendly_army_units.of_type(BIO_UNIT_TYPES)

        for tank in tanks:
            if tank.type_id == UnitTypeId.SIEGETANKSIEGED:
                actions.extend(self._handle_sieged_tank(tank, nearby_enemies, cache))
            else:  # UnitTypeId.SIEGETANK
                actions.extend(
                    self._handle_mobile_tank(tank, nearby_enemies, friendly_bio, cache)
                )

        # This controller provides a command (or a decision not to act) for every tank.
        return actions, tanks.tags

    def _handle_sieged_tank(
        self, tank: "Unit", nearby_enemies: "Units", cache: "GlobalCache"
    ) -> List[CommandFunctor]:
        """Logic for a tank that is already in siege mode."""
        if self._should_unsiege(tank, nearby_enemies, cache):
            return [lambda t=tank: t.unsiege()]
        # If it shouldn't unsiege, do nothing. The game's auto-targeting is efficient.
        return []

    def _handle_mobile_tank(
        self,
        tank: "Unit",
        nearby_enemies: "Units",
        friendly_bio: "Units",
        cache: "GlobalCache",
    ) -> List[CommandFunctor]:
        """Logic for a tank that is in mobile tank mode."""
        # 1. Check if we should siege at our current location.
        if self._should_siege(tank, nearby_enemies, friendly_bio):
            return [lambda t=tank: t.siege()]

        # 2. If not sieging, calculate the best position to move to.
        best_position = self._calculate_best_position(tank, friendly_bio, cache)

        # 3. Only issue a move command if we are not already close to the target position.
        if tank.distance_to(best_position) > 3:
            return [lambda t=tank, p=best_position: t.move(p)]

        return []

    def _should_siege(
        self, tank: "Unit", nearby_enemies: "Units", friendly_bio: "Units"
    ) -> bool:
        """Determines if a mobile tank should transition into siege mode."""
        ground_enemies = nearby_enemies.filter(lambda u: not u.is_flying)
        if not ground_enemies:
            return False

        # Do not siege if dangerous units are already inside the minimum range.
        if ground_enemies.closer_than(MINIMUM_RANGE + 1, tank).exists:
            return False

        # Only consider sieging if there is a significant threat in range.
        enemies_in_range = ground_enemies.closer_than(SIEGE_RANGE, tank)
        threat_value = sum(e.supply_cost for e in enemies_in_range)
        if threat_value < SIEGE_THREAT_THRESHOLD:
            return False

        # CRITICAL: Check for friendly fire before committing.
        if not self._is_safe_to_siege(tank, enemies_in_range, friendly_bio):
            return False

        return True

    def _should_unsiege(
        self, sieged_tank: "Unit", nearby_enemies: "Units", cache: "GlobalCache"
    ) -> bool:
        """Determines if a sieged tank should transition back to mobile mode."""
        army_target = getattr(cache.frame_plan, "target_location", sieged_tank.position)
        if sieged_tank.distance_to(army_target) > SIEGE_RANGE + 5:
            return True

        ground_enemies = nearby_enemies.filter(lambda u: not u.is_flying)

        if ground_enemies.closer_than(MINIMUM_RANGE, sieged_tank).amount >= 2:
            return True

        if not ground_enemies.closer_than(SIEGE_RANGE, sieged_tank).exists:
            return True

        return False

    def _is_safe_to_siege(
        self, tank: "Unit", enemies_in_range: "Units", friendly_bio: "Units"
    ) -> bool:
        """
        Performs a friendly fire check. Returns False if sieging is likely to
        cause significant damage to our own units.
        """
        if not friendly_bio.exists:
            return True

        for enemy in enemies_in_range:
            friendlies_in_splash_zone = friendly_bio.closer_than(
                SPLASH_RADIUS, enemy.position
            ).amount
            if friendlies_in_splash_zone >= FRIENDLY_FIRE_THRESHOLD:
                return False

        return True

    def _calculate_best_position(
        self, tank: "Unit", friendly_bio: "Units", cache: "GlobalCache"
    ) -> Point2:
        """
        Calculates the optimal position for a mobile tank based on army stance and threat.
        """
        stance = cache.frame_plan.army_stance
        army_target = getattr(cache.frame_plan, "target_location", tank.position)

        if stance == ArmyStance.DEFENSIVE:
            ideal_pos = getattr(
                cache.frame_plan, "defensive_position", self.bot.start_location
            )
        else:  # AGGRESSIVE or HARASS
            if not friendly_bio.exists:
                return army_target

            bio_center = friendly_bio.center
            ideal_pos = bio_center.towards(army_target, -LEAPFROG_DISTANCE)

        # Refine the ideal position by finding the safest nearby point using the threat map.
        safe_position = find_safe_point_from_threat_map(
            cache.threat_map, reference_point=ideal_pos, search_radius=5
        )
        return safe_position
```

---

### File: `terran/tactics/army_control_manager.py`

```python
from __future__ import annotations
from typing import TYPE_CHECKING, List, Dict, Set, Tuple

from sc2.ids.unit_typeid import UnitTypeId
from sc2.units import Units
from sc2.position import Point2

from core.interfaces.manager_abc import Manager
from core.frame_plan import ArmyStance
from core.types import CommandFunctor

# Import the specialist micro-controllers
from terran.specialists.micro.marine_controller import MarineController
from terran.specialists.micro.medivac_controller import MedivacController
from terran.specialists.micro.tank_controller import TankController

if TYPE_CHECKING:
    from sc2.bot_ai import BotAI
    from sc2.unit import Unit
    from core.global_cache import GlobalCache
    from core.event_bus import EventBus
    from core.frame_plan import FramePlan

# Define which units belong to which squad type for automatic assignment.
BIO_UNIT_TYPES = {
    UnitTypeId.MARINE,
    UnitTypeId.MARAUDER,
    UnitTypeId.REAPER,
    UnitTypeId.GHOST,
}
MECH_UNIT_TYPES = {
    UnitTypeId.SIEGETANK,
    UnitTypeId.HELLION,
    UnitTypeId.HELLIONTANK,
    UnitTypeId.CYCLONE,
    UnitTypeId.THOR,
}
AIR_UNIT_TYPES = {
    UnitTypeId.VIKINGFIGHTER,
    UnitTypeId.LIBERATOR,
    UnitTypeId.BANSHEE,
    UnitTypeId.BATTLECRUISER,
}
SUPPORT_UNIT_TYPES = {UnitTypeId.MEDIVAC, UnitTypeId.RAVEN}


class ArmyControlManager(Manager):
    """
    Field Commander.

    This manager orchestrates the army's high-level movements and actions.
    It translates the TacticalDirector's plan (stance and target) into concrete
    squad-based commands, delegating the complex micro-management to specialist
    controllers.
    """

    def __init__(self, bot: "BotAI"):
        super().__init__(bot)
        # Squads are stateful, stored as a dictionary mapping a squad name to a Units object.
        self.squads: Dict[str, Units] = {}

        # Instantiate micro-controllers once to maintain their state if needed.
        self.marine_controller = MarineController()
        self.medivac_controller = MedivacController()
        self.tank_controller = TankController()

    async def execute(
        self, cache: "GlobalCache", plan: "FramePlan", bus: "EventBus"
    ) -> List[CommandFunctor]:
        """
        Updates squads, determines targets based on stance, and delegates control.
        """
        # 1. Maintain Squads: Update unit membership based on new/dead units.
        self._update_squads(cache)

        # 2. Determine Target: Decide where each squad should be going this frame.
        target = self._get_squad_target(plan, cache)
        if not target:
            return []  # No valid target this frame.

        # 3. Delegate to Micro-Controllers and Issue Commands.
        actions: List[CommandFunctor] = []
        handled_tags: Set[int] = set()

        # Get primary combat squads
        bio_squad = self.squads.get("bio_squad_1")
        mech_squad = self.squads.get("mech_squad_1")
        support_squad = self.squads.get("support_squad_1")

        # --- Delegate Bio Control ---
        if bio_squad:
            marines = bio_squad.of_type(UnitTypeId.MARINE)
            if marines:
                marine_actions, marine_tags = self.marine_controller.execute(
                    marines, target, cache
                )
                actions.extend(marine_actions)
                handled_tags.update(marine_tags)
            # Add other bio controllers (e.g., MarauderController) here in the future.

        # --- Delegate Support Control ---
        if support_squad and bio_squad:
            medivacs = support_squad.of_type(UnitTypeId.MEDIVAC)
            if medivacs:
                medivac_actions, medivac_tags = self.medivac_controller.execute(
                    medivacs, bio_squad, target, cache
                )
                actions.extend(medivac_actions)
                handled_tags.update(medivac_tags)

        # --- Delegate Mech Control ---
        if mech_squad:
            tanks = mech_squad.of_type(
                {UnitTypeId.SIEGETANK, UnitTypeId.SIEGETANKSIEGED}
            )
            if tanks:
                tank_actions, tank_tags = self.tank_controller.execute(
                    tanks, target, cache
                )
                actions.extend(tank_actions)
                handled_tags.update(tank_tags)

        # --- Fallback for unhandled units ---
        # Any unit in a squad not handled by a micro-controller gets a default attack command.
        for squad in self.squads.values():
            unhandled_units = squad.tags_not_in(handled_tags)
            if unhandled_units.exists:
                # Generate one lambda FOR EACH unit in the unhandled group.
                actions.extend(
                    [lambda u=unit, t=target: u.attack(t) for unit in unhandled_units]
                )

        return actions

    def _update_squads(self, cache: "GlobalCache"):
        """Maintains squad compositions, removing dead units and assigning new ones."""
        all_army_tags = cache.friendly_army_units.tags

        # Remove dead units from squads by rebuilding them with only alive units.
        for squad_name, squad in self.squads.items():
            current_tags = squad.tags
            alive_tags = current_tags.intersection(all_army_tags)
            if len(alive_tags) < len(current_tags):
                self.squads[squad_name] = cache.friendly_army_units.tags_in(alive_tags)

        # Find and assign new (unassigned) units.
        assigned_tags = {tag for squad in self.squads.values() for tag in squad.tags}
        new_unit_tags = all_army_tags - assigned_tags

        if new_unit_tags:
            new_units = cache.friendly_army_units.tags_in(new_unit_tags)
            for unit in new_units:
                squad_name = self._get_squad_name_for_unit(unit)
                if squad_name not in self.squads:
                    self.squads[squad_name] = Units([], self.bot)
                self.squads[squad_name].append(unit)
                cache.logger.info(f"Assigned new {unit.name} to squad '{squad_name}'.")

    def _get_squad_name_for_unit(self, unit: "Unit") -> str:
        """Classifies a unit into a squad category."""
        if unit.type_id in BIO_UNIT_TYPES:
            return "bio_squad_1"
        if unit.type_id in MECH_UNIT_TYPES:
            return "mech_squad_1"
        if unit.type_id in AIR_UNIT_TYPES:
            return "air_squad_1"
        if unit.type_id in SUPPORT_UNIT_TYPES:
            return "support_squad_1"
        return "default_squad"

    def _get_squad_target(
        self, plan: "FramePlan", cache: "GlobalCache"
    ) -> "Point2" | None:
        """
        Determines the correct target point based on army stance. This implements
        the crucial logic for rallying, staging, and attacking.
        """
        stance = plan.army_stance

        if stance == ArmyStance.DEFENSIVE:
            return getattr(plan, "defensive_position", None)

        if stance == ArmyStance.AGGRESSIVE:
            final_target_pos = getattr(plan, "target_location", None)
            staging_point = getattr(plan, "staging_point", None)

            # If no staging point is defined (e.g., early game), attack directly.
            if not staging_point or not final_target_pos:
                return final_target_pos

            # Use the main combat squad to determine the army's center of mass.
            main_army = self.squads.get("bio_squad_1") or self.squads.get(
                "mech_squad_1"
            )

            # If no army exists yet, the first units should move to the staging point.
            if not main_army or not main_army.exists:
                return staging_point

            # Smart Staging Logic: If the army is not yet at the staging point, the target IS the staging point.
            # Once gathered, the target becomes the final enemy location.
            if main_army.center.distance_to(staging_point) > 15:
                cache.logger.debug("Army moving to staging point.")
                return staging_point
            else:
                cache.logger.debug("Army is staged. Attacking final target.")
                return final_target_pos

        # Default for any other stance (or if no specific target is set).
        return getattr(plan, "rally_point", None)
```

---

### File: `terran/tactics/positioning_manager.py`

```python
from __future__ import annotations
from typing import TYPE_CHECKING, List

from sc2.position import Point2

from core.frame_plan import ArmyStance
from core.interfaces.manager_abc import Manager
from core.types import CommandFunctor
from core.utilities.geometry import find_safe_point_from_threat_map
from core.utilities.unit_types import TERRAN_PRODUCTION_TYPES

if TYPE_CHECKING:
    from sc2.bot_ai import BotAI
    from sc2.game_info import Ramp
    from core.global_cache import GlobalCache
    from core.event_bus import EventBus
    from core.frame_plan import FramePlan


class PositioningManager(Manager):
    """
    Battlefield Topographer.

    This is a "service" manager that performs dynamic spatial analysis. It uses the
    threat map and knowledge of base locations to identify the most strategically
    sound locations for defense, rallying, and staging on a frame-by-frame basis.
    """

    def __init__(self, bot: "BotAI"):
        super().__init__(bot)

    async def execute(
        self, cache: "GlobalCache", plan: "FramePlan", bus: "EventBus"
    ) -> List[CommandFunctor]:
        """
        Analyzes the map and writes key tactical positions to the FramePlan.
        """
        self._calculate_defensive_position(cache, plan)
        self._calculate_rally_point(cache, plan)
        self._calculate_staging_point(cache, plan)

        # This is a service manager; its job is analysis, not action.
        return []

    def _calculate_defensive_position(self, cache: "GlobalCache", plan: "FramePlan"):
        """
        Determines the most logical choke point to defend. This is typically the
        ramp of our forward-most expansion.
        """
        if not self.bot.townhalls.ready:
            setattr(plan, "defensive_position", self.bot.start_location)
            return

        # Find the forward-most base (closest to the enemy).
        enemy_start = self.bot.enemy_start_locations[0]
        forward_base = self.bot.townhalls.ready.closest_to(enemy_start)

        # Find the ramp associated with this base.
        # A ramp's "bottom_center" is on the low ground.
        try:
            associated_ramp = min(
                self.bot.game_info.map_ramps,
                key=lambda ramp: ramp.bottom_center.distance_to(forward_base.position),
            )
            defensive_pos = associated_ramp.top_center
        except ValueError:
            # Fallback for maps with no ramps (e.g., flat maps).
            defensive_pos = forward_base.position.towards(enemy_start, -5)

        setattr(plan, "defensive_position", defensive_pos)
        cache.logger.debug(f"Defensive position updated to {defensive_pos.rounded}")

    def _calculate_rally_point(self, cache: "GlobalCache", plan: "FramePlan"):
        """
        Determines a safe point for newly trained units to gather. This point should
        be near our production but away from known threats.
        """
        production_buildings = cache.friendly_structures.of_type(
            TERRAN_PRODUCTION_TYPES
        )
        if not production_buildings:
            # If no production, rally at the defensive position.
            setattr(plan, "rally_point", getattr(plan, "defensive_position"))
            return

        # Calculate the center of our production infrastructure.
        production_center = production_buildings.center

        # Use the threat map to find the safest spot near our production center.
        safe_rally = find_safe_point_from_threat_map(
            cache.threat_map, reference_point=production_center, search_radius=15
        )
        setattr(plan, "rally_point", safe_rally)
        cache.logger.debug(f"Rally point updated to {safe_rally.rounded}")

    def _calculate_staging_point(self, cache: "GlobalCache", plan: "FramePlan"):
        """
        Determines a forward assembly area for an impending attack. This should
        be close to the enemy, but in a low-threat area.
        """
        if plan.army_stance != ArmyStance.AGGRESSIVE:
            setattr(plan, "staging_point", None)
            return

        # Determine the enemy's likely forward position.
        if cache.known_enemy_townhalls.exists:
            enemy_front = cache.known_enemy_townhalls.closest_to(
                self.bot.start_location
            )
        else:
            enemy_front = self.bot.enemy_start_locations[0]

        # Define a point roughly halfway between our main ramp and the enemy front.
        # This gives us a reference area to search for a safe spot.
        midpoint = self.bot.main_base_ramp.top_center.towards(
            enemy_front,
            self.bot.main_base_ramp.top_center.distance_to(enemy_front) * 0.75,
        )

        # Use the threat map to find the safest spot within that forward area.
        safe_staging_point = find_safe_point_from_threat_map(
            cache.threat_map, reference_point=midpoint, search_radius=25
        )
        setattr(plan, "staging_point", safe_staging_point)
        cache.logger.debug(f"Staging point calculated at {safe_staging_point.rounded}")
```

---

### File: `terran/tactics/scouting_manager.py`

```python
from __future__ import annotations
from typing import TYPE_CHECKING, List, Set

from sc2.ids.unit_typeid import UnitTypeId

from core.interfaces.manager_abc import Manager
from core.types import CommandFunctor
from core.utilities.events import Event, EventType, EnemyTechScoutedPayload
from core.utilities.constants import SCOUT_AT_SUPPLY

if TYPE_CHECKING:
    from sc2.bot_ai import BotAI
    from sc2.unit import Unit
    from sc2.units import Units
    from core.global_cache import GlobalCache
    from core.event_bus import EventBus
    from core.frame_plan import FramePlan

KEY_ENEMY_TECH_STRUCTURES: Set[UnitTypeId] = {
    UnitTypeId.SPAWNINGPOOL,
    UnitTypeId.ROACHWARREN,
    UnitTypeId.BANELINGNEST,
    UnitTypeId.LAIR,
    UnitTypeId.HYDRALISKDEN,
    UnitTypeId.SPIRE,
    UnitTypeId.HIVE,
    UnitTypeId.FACTORY,
    UnitTypeId.STARPORT,
    UnitTypeId.ARMORY,
    UnitTypeId.FUSIONCORE,
    UnitTypeId.CYBERNETICSCORE,
    UnitTypeId.TWILIGHTCOUNCIL,
    UnitTypeId.STARGATE,
    UnitTypeId.ROBOTICSFACILITY,
    UnitTypeId.TEMPLARARCHIVE,
    UnitTypeId.DARKSHRINE,
}


class ScoutingManager(Manager):
    """
    Intelligence Agency.
    """

    def __init__(self, bot: "BotAI"):
        super().__init__(bot)
        self.scout_tag: int | None = None
        self._scouting_plan: List[tuple[float, float]] = []
        self._known_enemy_tech: Set[UnitTypeId] = set()

    async def execute(
        self, cache: "GlobalCache", plan: "FramePlan", bus: "EventBus"
    ) -> List[CommandFunctor]:
        if self.scout_tag is None or not cache.friendly_units.find_by_tag(
            self.scout_tag
        ):
            self._assign_new_scout(cache)
            if self.scout_tag is None:
                return []

        scout: Unit | None = cache.friendly_units.find_by_tag(self.scout_tag)
        if not scout:
            self.scout_tag = None
            return []

        self._analyze_and_publish(scout, cache, bus)

        if not self._scouting_plan:
            self._generate_scouting_plan(cache)

        if not self._scouting_plan:
            return []

        target_pos = self._scouting_plan[0]
        if scout.distance_to(target_pos) < 5:
            self._scouting_plan.pop(0)
            if not self._scouting_plan:
                return []

        return [lambda s=scout, t=target_pos: s.move(t)]

    def _assign_new_scout(self, cache: "GlobalCache"):
        """Selects and assigns the best available unit to be the scout."""
        # CHANGED: Use cache.iteration instead of self.bot.iteration
        if cache.supply_used >= SCOUT_AT_SUPPLY and cache.iteration < 22.4 * 120:
            worker = cache.friendly_workers.closest_to(self.bot.game_info.map_center)
            if worker:
                self.scout_tag = worker.tag
                cache.logger.info(
                    f"Assigning SCV (tag: {self.scout_tag}) as the initial scout."
                )
                return

        reapers = cache.friendly_army_units.of_type(UnitTypeId.REAPER)
        if reapers.exists:
            self.scout_tag = reapers.first.tag
            cache.logger.info(f"Assigning Reaper (tag: {self.scout_tag}) as scout.")
            return

    def _generate_scouting_plan(self, cache: "GlobalCache"):
        """Creates a list of points for the scout to visit."""
        enemy_start = self.bot.enemy_start_locations[0]

        expansion_locations = sorted(
            self.bot.expansion_locations_list,
            key=lambda loc: loc.distance_to(enemy_start),
        )

        self._scouting_plan = [enemy_start] + expansion_locations
        cache.logger.info("Generated a new scouting plan.")

    def _analyze_and_publish(self, scout: Unit, cache: "GlobalCache", bus: "EventBus"):
        """Checks what the scout sees and publishes events for new tech."""
        visible_enemies: "Units" = cache.enemy_structures.closer_than(
            scout.sight_range, scout
        )

        for enemy in visible_enemies:
            if enemy.type_id in KEY_ENEMY_TECH_STRUCTURES:
                if enemy.type_id not in self._known_enemy_tech:
                    self._known_enemy_tech.add(enemy.type_id)
                    payload = EnemyTechScoutedPayload(tech_id=enemy.type_id)
                    bus.publish(Event(EventType.TACTICS_ENEMY_TECH_SCOUTED, payload))
                    cache.logger.warning(
                        f"CRITICAL INTEL: Scout discovered new enemy tech: {enemy.type_id.name}"
                    )
```

---

### File: `terran/tactics/tactical_director.py`

```python
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
```

