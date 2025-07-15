## **Design Document: Sajuuk AI (Final Blueprint)**

**Version:** 4.0 - "The Crucible"
**Date:** 7/9/25
**Author:** Sajuuk, The Oracle

### 1. Core Philosophy & Guiding Principles

The mission remains: to create an **Adaptive Organism**, not a clockwork machine. This metaphor is not abstract; it is a technical directive grounded in three concrete systems:

1.  **Sensing (The `GlobalCache`):** The bot's ability to build a comprehensive, read-only model of the world state each frame.
2.  **Reacting (The `EventBus`):** The bot's "nervous system," allowing for instantaneous, reflexive responses to critical threats that bypass the main cognitive loop.
3.  **Adapting (The `FramePlan` & Strategy Patterns):** The bot's "frontal lobe," enabling it to change its high-level strategic intentions frame-by-frame and even alter its entire decision-making hierarchy in response to its environment.

To ensure this organism is resilient and maintainable, its development will be governed by the following inviolable architectural principles:

*   **Unidirectional Data Flow:** Information flows in one direction. The `GlobalCache` and `FramePlan` are passed *down* the hierarchy (`General` -> `Director` -> `Manager`). Intentions (`UnitCommand` actions) are returned *up* the hierarchy. A component never directly modifies its parent or sibling; it only reads from the plan it was given and returns its intent.
*   **Dependency Injection:** Components are given their dependencies (like the `cache` or `plan`) during their `execute` call. They do not hold persistent references to high-level services, making them highly decoupled and testable in isolation.
*   **Stateless Methods, Stateful Objects:** Managers are designed to be stateful. A `ResearchManager` will maintain an internal queue of upgrades it needs to research. However, its `execute()` method will be functionally pure: given the same cache and plan, it will always return the same list of actions. All state changes are self-contained within the manager's own attributes.
*   **Formal Action Resolution Policy:** The `General` is responsible for resolving action conflicts. If two managers issue a command for the same unit, a "last-writer-wins" policy is applied, based on the execution order of the Directors. Critical actions (like micro commands from the `Tactics` directorate) are executed last, giving them final authority for a frame. All conflicts will be logged in debug mode.

### 2. The Hardened Core Services

The three core services are the foundation of the bot's intelligence. They are implemented with specific safeguards to address performance, debugging, and state management risks.

*   **`GlobalCache` (The Read-Only Memory):**
    *   **Responsibility:** Provides a consistent snapshot of the world for a single frame.
    *   **Hardening:** To manage performance, the cache update process is **tiered**.
        *   **Fast Cache (Every Frame):** Unit positions, health, resources.
        *   **Detailed Cache (Every N Frames):** Computationally expensive data like global threat maps or complex pathing grids are updated on a less frequent cycle to ensure high frame rates.

*   **`EventBus` (The Reflexive Nervous System):**
    *   **Responsibility:** Enables instant, decoupled reactions.
    *   **Hardening:**
        *   **Strict Registry & Namespacing:** All events *must* be defined in a central registry (`core/events.py`). Events are namespaced to their functional domain (e.g., `tactics.ProxyDetected`, `infra.BuildRequest`) to prevent collisions and clarify intent.
        *   **Priority Levels:** Events are assigned a priority (`CRITICAL`, `NORMAL`). The bus will process critical events first, ensuring that a "dodge spell" reflex is handled before a "queue new unit" notification.

*   **`FramePlan` (The Strategic Scratchpad):**
    *   **Responsibility:** To hold the strategic intentions for the current frame.
    *   **Hardening:**
        *   **Feasibility & Constraint Reporting:** Managers can "push back" against the plan. If the `ConstructionManager` receives a `BuildRequest` it cannot fulfill (e.g., no available SCV, location blocked), it will publish a `BuildRequestFailed` event to the `EventBus`. The originating Director can subscribe to this failure event and revise its strategy on the next frame (e.g., try a different location or build something else).

### 3. The Cognitive Loop: How a Decision is Made

A single frame demonstrates the entire architecture in action. **Goal: The bot has just scouted an enemy Stargate.**

1.  **Frame N: PERCEIVE & PUBLISH**
    *   `sajuuk.py` updates the `GlobalCache` with the latest game state.
    *   The `ScoutingManager` runs. It sees the Stargate. It **publishes** a `tactics.EnemyTechScouted` event with the payload `{'tech': 'STARGATE'}` to the `EventBus`. At this moment, nothing else happens. The AI is still "thinking" about its old plan.

2.  **Frame N+1: PLAN & ADAPT**
    *   `sajuuk.py` updates the cache. The `TerranGeneral` creates a new, empty `FramePlan`.
    *   **`InfrastructureDirector` runs:** It analyzes the cache, sees no immediate threat, and **writes its budget to the `FramePlan`**: `plan.set_budget({'army': 60, 'tech': 40})`.
    *   **`CapabilityDirector` runs:**
        *   It first checks the `EventBus` history for relevant events from the last frame. It sees `tactics.EnemyTechScouted`.
        *   This new information **overrides its default logic**.
        *   It reads the budget from the `FramePlan`.
        *   It formulates a new production goal: "We need anti-air. Spend the budget on 1 Viking and 1 Missile Turret."
        *   It passes these goals to its subordinate managers.
    *   **`TacticalDirector` runs:** It also sees the Stargate event. It **writes the army stance to the `FramePlan`**: `plan.set_stance('DEFENSIVE_POSTURE')`.

3.  **Frame N+1: EXECUTE**
    *   The `ArmyUnitManager` (under `Capabilities`) receives the goal "build Viking." It has the internal state `self.queue = {'VIKING': 1}`. It returns a `train(VIKING)` command.
    *   The `TechStructureManager` (under `Capabilities`) receives the goal "build Turret." It publishes a `infra.BuildRequest` for a `MISSILETURRET`.
    *   The `ConstructionManager` (under `Infrastructure`) receives the `BuildRequest` event and returns the necessary `build` command with an SCV.
    *   The `ArmyControlManager` (under `Tactics`) reads `plan.get_stance() == 'DEFENSIVE_POSTURE'` and returns commands to move its existing army to a safe position near its mineral lines.

4.  **Frame N+1: RESOLVE & ACT**
    *   The `TerranGeneral` collects all returned action lists. It resolves any conflicts using its defined policy.
    *   The final, coherent list of actions is sent to `sajuuk.py` and executed.

### 4. Long-Term Adaptability & Growth

The architecture is designed to evolve beyond its initial implementation.

*   **Strategy Patterns:** The `TerranGeneral` will be able to dynamically swap out entire Directorates. For example, upon scouting a Mech opponent, it can replace the default `CapabilityDirector` with a `MechCapabilityDirector` that prioritizes Factories and Thors over Barracks and Marines. This allows for true meta-adaptation.
*   **Graceful Degradation:** Core managers will be built with fallback logic. If the `PositioningManager` fails to find a perfect defensive location, the `ArmyControlManager` will default to a simple "rally at main ramp" command, ensuring the bot remains functional even when a subsystem fails.
*   **Meta-Learning Integration:** A `GameAnalytics` module will be added later. After a game, it will analyze the replay and opponent data. The `TerranGeneral`, at the start of a new game, can query this module to inform its initial choice of strategy, enabling it to learn from past encounters.
*   **Debugging & Auditing:** Every significant decision (Director sets budget, Manager requests build) will be logged with a "reason." This creates a human-readable "decision chain" that makes it possible to trace exactly why the bot chose a specific action, which is invaluable for debugging and improvement.

This document codifies a system that is not only organized and robust but is explicitly designed to house the complex, interconnected, and adaptive logic required to achieve the highest levels of competitive play.