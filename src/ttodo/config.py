"""Configuration constants for Terminal Todo."""

# Database
DATABASE_PATH = "todo.db"

# UI Constants
MIN_TERMINAL_WIDTH = 80
MIN_TERMINAL_HEIGHT = 24
PANEL_GAP = 2  # Character spacing between panels
INPUT_BOX_HEIGHT = 3  # Height of command input box

# Command History
MAX_COMMAND_HISTORY = 50
MAX_UNDO_STACK = 20

# Auto-archive
ARCHIVE_AFTER_HOURS = 24
ARCHIVE_CHECK_INTERVAL = 3600  # Check every hour (in seconds)

# Auto-save debounce
AUTOSAVE_DEBOUNCE_MS = 300

# Date formats
DATE_INPUT_FORMAT = "%d %m %y"
DATE_STORAGE_FORMAT = "%Y-%m-%d"

# Task status
STATUS_TODO = "todo"
STATUS_DOING = "doing"
STATUS_DONE = "done"

# Priority levels
PRIORITY_HIGH = "High"
PRIORITY_MEDIUM = "Medium"
PRIORITY_LOW = "Low"

# Story points (Fibonacci)
STORY_POINTS = [1, 2, 3, 5, 8, 13]
