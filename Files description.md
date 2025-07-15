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