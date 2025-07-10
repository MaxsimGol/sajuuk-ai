# create_sajuuk_project.py

import os
from pathlib import Path

# The definitive list of all files in the Sajuuk AI project structure.
# Paths are relative to the root 'sajuuk_ai' directory.
FILE_STRUCTURE = [
    # Root files
    "run.py",
    "run_tests.py",
    "sajuuk.py",
    "requirements.txt",
    "README.md",
    # Core Services
    "core/__init__.py",
    "core/interfaces/__init__.py",
    "core/interfaces/race_general_abc.py",
    "core/interfaces/director_abc.py",
    "core/interfaces/manager_abc.py",
    "core/global_cache.py",
    "core/event_bus.py",
    "core/frame_plan.py",
    "core/utilities/__init__.py",
    "core/utilities/events.py",
    "core/utilities/geometry.py",
    "core/utilities/unit_value.py",
    "core/utilities/constants.py",
    # Terran General
    "terran/__init__.py",
    "terran/general/__init__.py",
    "terran/general/terran_general.py",
    # Terran Infrastructure Directorate
    "terran/infrastructure/__init__.py",
    "terran/infrastructure/infrastructure_director.py",
    "terran/infrastructure/units/__init__.py",
    "terran/infrastructure/units/scv_manager.py",
    "terran/infrastructure/units/mule_manager.py",
    "terran/infrastructure/structures/__init__.py",
    "terran/infrastructure/structures/supply_manager.py",
    "terran/infrastructure/structures/expansion_manager.py",
    "terran/infrastructure/structures/repair_manager.py",
    "terran/infrastructure/structures/construction_manager.py",
    # Terran Capabilities Directorate
    "terran/capabilities/__init__.py",
    "terran/capabilities/capability_director.py",
    "terran/capabilities/units/__init__.py",
    "terran/capabilities/units/army_unit_manager.py",
    "terran/capabilities/structures/__init__.py",
    "terran/capabilities/structures/tech_structure_manager.py",
    "terran/capabilities/structures/addon_manager.py",
    "terran/capabilities/upgrades/__init__.py",
    "terran/capabilities/upgrades/research_manager.py",
    # Terran Tactics Directorate
    "terran/tactics/__init__.py",
    "terran/tactics/tactical_director.py",
    "terran/tactics/scouting_manager.py",
    "terran/tactics/army_control_manager.py",
    "terran/tactics/positioning_manager.py",
    # Terran Specialists
    "terran/specialists/__init__.py",
    "terran/specialists/build_orders/__init__.py",
    "terran/specialists/build_orders/two_rax_reaper.py",
    "terran/specialists/micro/__init__.py",
    "terran/specialists/micro/marine_controller.py",
    "terran/specialists/micro/tank_controller.py",
    "terran/specialists/micro/medivac_controller.py",
    # Placeholder Race Silos
    "zerg/__init__.py",
    "protoss/__init__.py",
    # Comprehensive Test Suite
    "tests/__init__.py",
    "tests/test_core/__init__.py",
    "tests/test_core/test_global_cache.py",
    "tests/test_core/test_event_bus.py",
    "tests/test_core/test_frame_plan.py",
    "tests/test_terran/__init__.py",
    "tests/test_terran/test_general/__init__.py",
    "tests/test_terran/test_general/test_terran_general.py",
    "tests/test_terran/test_infrastructure/__init__.py",
    "tests/test_terran/test_infrastructure/test_infrastructure_director.py",
    "tests/test_terran/test_infrastructure/test_units/__init__.py",
    "tests/test_terran/test_infrastructure/test_units/test_scv_manager.py",
    "tests/test_terran/test_infrastructure/test_units/test_mule_manager.py",
    "tests/test_terran/test_infrastructure/test_structures/__init__.py",
    "tests/test_terran/test_infrastructure/test_structures/test_supply_manager.py",
    "tests/test_terran/test_infrastructure/test_structures/test_expansion_manager.py",
    "tests/test_terran/test_infrastructure/test_structures/test_repair_manager.py",
    "tests/test_terran/test_infrastructure/test_structures/test_construction_manager.py",
    "tests/test_terran/test_capabilities/__init__.py",
    "tests/test_terran/test_capabilities/test_capability_director.py",
    "tests/test_terran/test_capabilities/test_units/__init__.py",
    "tests/test_terran/test_capabilities/test_units/test_army_unit_manager.py",
    "tests/test_terran/test_capabilities/test_structures/__init__.py",
    "tests/test_terran/test_capabilities/test_structures/test_tech_structure_manager.py",
    "tests/test_terran/test_capabilities/test_structures/test_addon_manager.py",
    "tests/test_terran/test_capabilities/test_upgrades/__init__.py",
    "tests/test_terran/test_capabilities/test_upgrades/test_research_manager.py",
    "tests/test_terran/test_tactics/__init__.py",
    "tests/test_terran/test_tactics/test_tactical_director.py",
    "tests/test_terran/test_tactics/test_scouting_manager.py",
    "tests/test_terran/test_tactics/test_army_control_manager.py",
    "tests/test_terran/test_tactics/test_positioning_manager.py",
    "tests/test_terran/test_specialists/__init__.py",
    "tests/test_terran/test_specialists/test_micro/__init__.py",
    "tests/test_terran/test_specialists/test_micro/test_marine_controller.py",
]

# Content for key files
README_CONTENT = """
# Sajuuk AI - v4.0

This project is a StarCraft II bot built on the "Race General" hybrid architecture.
Its goal is to achieve Grandmaster-level performance through a modular, maintainable, and testable design.

## Setup
1. `pip install -r requirements.txt`
2. Configure your StarCraft II executable path if necessary.
3. Run a test match with `python run.py`.
"""

REQUIREMENTS_CONTENT = """
burnysc2
numpy
"""


def create_project_structure(root_dir="sajuuk_ai"):
    """Creates the directories and empty files for the project."""
    root_path = Path(root_dir)
    if root_path.exists():
        print(
            f"Directory '{root_dir}' already exists. Aborting to prevent overwriting."
        )
        return

    print(f"Creating project root: {root_path}")
    root_path.mkdir()

    for file_path_str in FILE_STRUCTURE:
        file_path = root_path / file_path_str

        # Create parent directories if they don't exist
        file_path.parent.mkdir(parents=True, exist_ok=True)

        # Create the empty file
        print(f"  Creating file: {file_path}")
        file_path.touch()

    # Add initial content to specific files
    print("\nAdding initial content to key files...")
    (root_path / "README.md").write_text(README_CONTENT)
    (root_path / "requirements.txt").write_text(REQUIREMENTS_CONTENT)
    print("  Added content to README.md")
    print("  Added content to requirements.txt")

    print("\nProject structure created successfully.")
    print("The Great Work can now begin.")


if __name__ == "__main__":
    create_project_structure()
