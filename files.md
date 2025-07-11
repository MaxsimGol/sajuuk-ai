sajuuk_ai/
├── run.py                          # Main entry point to launch a game with the Sajuuk bot.
├── run_tests.py                    # Discovers and runs all unit and integration tests.
├── sajuuk.py                       # The Main BotAI Conductor.
├── requirements.txt                # Lists all Python project dependencies (burnysc2, numpy, etc.).
└── README.md                       # Project overview, setup instructions, and contribution guidelines.

#=============================================================================#
#   CORE: Shared, Race-Agnostic Components & Architectural Blueprints
#=============================================================================#
├── core/
│   ├── __init__.py
│   │
│   ├── interfaces/
│   │   ├── __init__.py
│   │   ├── race_general_abc.py     # Contract for top-level Race Generals.
│   │   ├── director_abc.py         # Contract for high-level functional Directors.
│   │   └── manager_abc.py          # Contract for specialized, stateful Managers.
│   │
│   ├── global_cache.py             # READ-ONLY memory of the world state (updated once by Sajuuk).
│   ├── event_bus.py                # Nervous system for instant reflexes. Manages namespaced event channels.
│   ├── frame_plan.py               # Ephemeral "scratchpad" for the current frame's strategic intentions.
│   │
│   └── utilities/
│       ├── __init__.py
│       ├── events.py               # NEW: Central registry defining all event types and their payload schemas.
│       ├── geometry.py             # Shared math for positioning, kiting, and distance calculations.
│       ├── unit_value.py           # Functions to assess unit threat and army value.
│       └── constants.py            # Bot-specific constants (e.g., HARASS_SQUAD_SIZE).

#=============================================================================#
#   RACE-SPECIFIC MODULES: TERRAN (Detailed Hybrid Structure)
#=============================================================================#
├── terran/
│   ├── __init__.py
│   │
│   ├── general/
│   │   └── terran_general.py       # Top-level orchestrator. Creates FramePlan, manages Directors.
│   │
│   ├── infrastructure/
│   │   # RESPONSIBILITY: Build and maintain the bot's economic engine.
│   │   ├── __init__.py
│   │   ├── infrastructure_director.py    # Sets economic stance, WRITES resource budget to FramePlan.
│   │   │
│   │   ├── units/
│   │   │   ├── __init__.py
│   │   │   ├── scv_manager.py          # Manages SCV production goals and mineral/gas saturation.
│   │   │   └── mule_manager.py         # Manages MULE calls on Orbitals.
│   │   │
│   │   └── structures/
│   │       ├── __init__.py
│   │       ├── supply_manager.py       # Manages building Supply Depots to prevent blocks.
│   │       ├── expansion_manager.py    # Decides WHEN and WHERE to expand, publishes BuildRequest.
│   │       ├── repair_manager.py       # Subscribes to damage events, manages SCV repair tasks.
│   │       └── construction_manager.py   # Specialist service: Subscribes to ALL BuildRequests and executes them.
│   │
│   ├── capabilities/
│   │   # RESPONSIBILITY: Spend resources to create army power and new tech options.
│   │   ├── __init__.py
│   │   ├── capability_director.py      # READS budget from FramePlan, sets production goals for managers.
│   │   │
│   │   ├── units/
│   │   │   ├── __init__.py
│   │   │   └── army_unit_manager.py    # Manages training queues for ALL army units.
│   │   │
│   │   ├── structures/
│   │   │   ├── __init__.py
│   │   │   ├── tech_structure_manager.py # Manages building Factories, Starports, etc. Publishes BuildRequest.
│   │   │   └── addon_manager.py          # Manages building Reactors and Tech Labs. Publishes BuildRequest.
│   │   │
│   │   └── upgrades/
│   │       ├── __init__.py
│   │       └── research_manager.py     # Manages ALL research queues (Stim, Shields, etc.).
│   │
│   ├── tactics/
│   │   # RESPONSIBILITY: Information gathering and battlefield control.
│   │   ├── __init__.py
│   │   ├── tactical_director.py          # Sets army stance (Attack, Defend) in FramePlan.
│   │   │
│   │   ├── scouting_manager.py           # Controls scout units and publishes intel to the EventBus.
│   │   ├── army_control_manager.py       # Composes squads and gives them high-level orders.
│   │   └── positioning_manager.py        # Calculates optimal defensive positions and rally points.
│   │
│   └── specialists/
│       # RESPONSIBILITY: Single-purpose, low-level execution logic ("tools").
│       ├── __init__.py
│       │
│       ├── build_orders/
│       │   ├── __init__.py
│       │   └── two_rax_reaper.py       # Example starting build order.
│       │
│       └── micro/
│           ├── __init__.py
│           ├── marine_controller.py    # Handles stutter-step micro for a squad of marines.
│           ├── tank_controller.py      # Handles siege/unsiege logic for a squad of tanks.
│           └── medivac_controller.py   # Handles healing and boosting for a squad of medivacs.

#=============================================================================#
#   RACE-SPECIFIC MODULES: ZERG & PROTOSS (High-Level Placeholders)
#=============================================================================#
├── zerg/
│   └── __init__.py # ... (Structure will mirror terran/ with race-specific components)
│
├── protoss/
│   └── __init__.py # ... (Structure will mirror terran/ with race-specific components)

#=============================================================================#
#   TESTS: Mirroring the Project Structure for Comprehensive Coverage
#=============================================================================#
└── tests/
    ├── __init__.py
    ├── test_core/
    │   ├── __init__.py
    │   ├── test_global_cache.py
    │   ├── test_event_bus.py
    │   └── test_frame_plan.py
    │
    └── test_terran/
        ├── __init__.py
        │
        ├── test_general/
        │   └── test_terran_general.py
        │
        ├── test_infrastructure/
        │   ├── __init__.py
        │   ├── test_infrastructure_director.py
        │   ├── test_units/
        │   │   ├── __init__.py
        │   │   ├── test_scv_manager.py
        │   │   └── test_mule_manager.py
        │   └── test_structures/
        │       ├── __init__.py
        │       ├── test_supply_manager.py
        │       ├── test_expansion_manager.py
        │       ├── test_repair_manager.py
        │       └── test_construction_manager.py
        │
        ├── test_capabilities/
        │   ├── __init__.py
        │   ├── test_capability_director.py
        │   ├── test_units/
        │   │   ├── __init__.py
        │   │   └── test_army_unit_manager.py
        │   ├── test_structures/
        │   │   ├── __init__.py
        │   │   ├── test_tech_structure_manager.py
        │   │   └── test_addon_manager.py
        │   └── test_upgrades/
        │       ├── __init__.py
        │       └── test_research_manager.py
        │
        ├── test_tactics/
        │   ├── __init__.py
        │   ├── test_tactical_director.py
        │   ├── test_scouting_manager.py
        │   ├── test_army_control_manager.py
        │   └── test_positioning_manager.py
        │
        └── test_specialists/
            └── test_micro/
                ├── __init__.py
                └── test_marine_controller.py