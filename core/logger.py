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
