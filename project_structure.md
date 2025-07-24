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
├── Design Document.md
├── files.md
├── logs
│   ├── sajuuk_2025-07-24_08-29-25.log
│   ├── sajuuk_2025-07-24_08-30-26.log
│   ├── sajuuk_2025-07-24_08-31-03.2025-07-24_08-31-03_079829.log
│   ├── sajuuk_2025-07-24_08-31-03.2025-07-24_09-05-29_911488.log
│   ├── sajuuk_2025-07-24_08-31-03.log
│   ├── sajuuk_2025-07-24_14-20-44.log
│   ├── sajuuk_2025-07-24_14-24-44.log
│   ├── sajuuk_2025-07-24_14-25-46.log
│   ├── sajuuk_2025-07-24_14-57-23.log
│   ├── sajuuk_2025-07-24_15-01-40.log
│   ├── sajuuk_2025-07-24_15-13-57.log
│   ├── sajuuk_2025-07-24_16-33-04.log
│   ├── sajuuk_2025-07-24_16-37-00.log
│   ├── sajuuk_2025-07-24_17-11-31.log
│   ├── sajuuk_2025-07-24_18-57-17.log
│   ├── sajuuk_2025-07-24_18-59-26.log
│   ├── sajuuk_2025-07-24_19-01-30.log
│   ├── sajuuk_2025-07-24_19-06-06.log
│   ├── sajuuk_2025-07-24_19-07-45.log
│   ├── sajuuk_2025-07-24_19-12-00.log
│   ├── sajuuk_2025-07-24_19-18-48.log
│   ├── sajuuk_2025-07-24_19-21-33.log
│   ├── sajuuk_2025-07-24_19-30-21.log
│   └── sajuuk_2025-07-24_19-34-47.log
├── protoss
│   └── __init__.py
├── python_sc2_library_context.md
├── README.md
├── requirements.txt
├── run.py
├── run_tests.py
├── Sajuuk-vs-EasyZerg.SC2Replay
├── sajuuk.py
├── sajuuk_ai_context.md
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