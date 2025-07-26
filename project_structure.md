### Project File Structure

```
.
├── core
│   ├── __init__.py
│   ├── analysis
│   │   ├── analysis_configuration.py
│   │   ├── army_value_analyzer.py
│   │   ├── base_threat_analyzer.py
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
│   ├── logger.py
│   ├── types.py
│   └── utilities
│       ├── __init__.py
│       ├── constants.py
│       ├── events.py
│       ├── geometry.py
│       ├── unit_types.py
│       └── unit_value.py
├── create_context.py
├── logs
│   ├── sajuuk_2025-07-23_08-30-24.log
│   ├── sajuuk_2025-07-23_08-31-13.log
│   └── sajuuk_2025-07-23_08-41-33.log
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
│   │   ├── production
│   │   │   ├── barracks_manager.py
│   │   │   ├── factory_manager.py
│   │   │   └── starport_manager.py
│   │   ├── structures
│   │   │   ├── __init__.py
│   │   │   └── production_structure_manager.py
│   │   └── upgrades
│   │       ├── __init__.py
│   │       ├── armory_manager.py
│   │       └── engineering_bay_manager.py
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
│   │   │   ├── refinery_manager.py
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
│       ├── squad.py
│       └── tactical_director.py
├── tests
│   ├── __init__.py
│   ├── test_core
│   │   ├── __init__.py
│   │   ├── analysis
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
├── try.py
└── zerg
    └── __init__.py
```