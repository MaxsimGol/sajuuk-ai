"""
A central repository for tunable, non-magical constants.

This file allows for easy adjustment of the bot's core behaviors without
needing to modify the underlying logic of the managers or directors.
All values here should be considered a starting point for optimization.
"""

# --- System & Performance ---
# How often, in game frames, to run expensive calculations in the GlobalCache.
# A lower number is more responsive but costs more CPU. (22.4 frames ≈ 1 second)
DETAILED_CACHE_UPDATE_FREQUENCY_FRAMES: int = 8

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
