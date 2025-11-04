"""Input validation utilities for Terminal Todo."""

from typing import Optional, Tuple
from ttodo.utils.date_utils import parse_date
from ttodo.database.models import db


# Valid values for validation
VALID_PRIORITIES = ('High', 'Medium', 'Low')
VALID_STORY_POINTS = (1, 2, 3, 5, 8, 13)
VALID_STATUSES = ('todo', 'doing', 'done')


class ValidationError(Exception):
    """Custom exception for validation errors with helpful messages."""

    def __init__(self, message: str, field: str = None, attempted_value: str = None):
        """Initialize validation error with context.

        Args:
            message: Error message explaining what went wrong
            field: Name of the field that failed validation
            attempted_value: The value that was attempted
        """
        self.field = field
        self.attempted_value = attempted_value
        super().__init__(message)


def validate_priority(priority: Optional[str]) -> Tuple[bool, str, Optional[str]]:
    """Validate priority value.

    Args:
        priority: Priority string to validate (can be None for optional)

    Returns:
        Tuple of (is_valid, error_message, normalized_value)
    """
    if priority is None or priority == "":
        return (True, "", None)

    # Normalize: strip whitespace and capitalize first letter
    priority_normalized = priority.strip().capitalize()

    if priority_normalized not in VALID_PRIORITIES:
        return (
            False,
            f"Invalid priority '{priority}'. Must be one of: High, Medium, or Low.",
            None
        )

    return (True, "", priority_normalized)


def validate_story_points(story_points: Optional[int]) -> Tuple[bool, str, Optional[int]]:
    """Validate story points value.

    Args:
        story_points: Story points integer to validate (can be None for optional)

    Returns:
        Tuple of (is_valid, error_message, normalized_value)
    """
    if story_points is None:
        return (True, "", None)

    try:
        sp = int(story_points)
        if sp not in VALID_STORY_POINTS:
            return (
                False,
                f"Invalid story points '{story_points}'. Must be a Fibonacci number: 1, 2, 3, 5, 8, or 13.",
                None
            )
        return (True, "", sp)
    except (ValueError, TypeError):
        return (
            False,
            f"Invalid story points '{story_points}'. Must be a number from: 1, 2, 3, 5, 8, or 13.",
            None
        )


def validate_story_points_string(story_points_str: Optional[str]) -> Tuple[bool, str, Optional[int]]:
    """Validate story points from string input.

    Args:
        story_points_str: Story points string to validate (can be None or empty for optional)

    Returns:
        Tuple of (is_valid, error_message, normalized_value)
    """
    if story_points_str is None or story_points_str.strip() == "":
        return (True, "", None)

    try:
        sp = int(story_points_str.strip())
        if sp not in VALID_STORY_POINTS:
            return (
                False,
                f"Invalid story points '{story_points_str}'. Must be a Fibonacci number: 1, 2, 3, 5, 8, or 13.",
                None
            )
        return (True, "", sp)
    except ValueError:
        return (
            False,
            f"Invalid story points '{story_points_str}'. Must be a number from: 1, 2, 3, 5, 8, or 13.",
            None
        )


def validate_date(date_str: Optional[str]) -> Tuple[bool, str, Optional[str]]:
    """Validate date format and return ISO format.

    Args:
        date_str: Date string to validate (can be None or empty for optional)

    Returns:
        Tuple of (is_valid, error_message, iso_date)
    """
    if date_str is None or date_str.strip() == "":
        return (True, "", None)

    iso_date = parse_date(date_str)
    if iso_date is None:
        return (
            False,
            f"Invalid date format '{date_str}'. Use: DD MM YY (e.g., '15 10 25'), 'tomorrow', 'today', or '+3d'.",
            None
        )

    return (True, "", iso_date)


def validate_role_name(role_name: Optional[str]) -> Tuple[bool, str, Optional[str]]:
    """Validate role name.

    Args:
        role_name: Role name to validate

    Returns:
        Tuple of (is_valid, error_message, normalized_value)
    """
    if role_name is None or role_name.strip() == "":
        return (False, "Role name cannot be empty.", None)

    # Check length constraints
    normalized = role_name.strip()
    if len(normalized) > 50:
        return (False, "Role name is too long. Maximum 50 characters.", None)

    return (True, "", normalized)


def validate_task_title(task_title: Optional[str]) -> Tuple[bool, str, Optional[str]]:
    """Validate task title.

    Args:
        task_title: Task title to validate

    Returns:
        Tuple of (is_valid, error_message, normalized_value)
    """
    if task_title is None or task_title.strip() == "":
        return (False, "Task title cannot be empty.", None)

    # Check length constraints
    normalized = task_title.strip()
    if len(normalized) > 200:
        return (False, "Task title is too long. Maximum 200 characters.", None)

    return (True, "", normalized)


def validate_role_exists(role_id: int) -> Tuple[bool, str]:
    """Validate that a role exists.

    Args:
        role_id: Role ID to check

    Returns:
        Tuple of (exists, error_message)
    """
    role = db.fetchone("SELECT id FROM roles WHERE id = ?", (role_id,))
    if not role:
        return (False, f"Role with ID {role_id} does not exist.")
    return (True, "")


def validate_role_exists_by_number(display_number: int) -> Tuple[bool, str]:
    """Validate that a role exists by display number.

    Args:
        display_number: Role display number to check

    Returns:
        Tuple of (exists, error_message)
    """
    role = db.fetchone("SELECT id FROM roles WHERE display_number = ?", (display_number,))
    if not role:
        return (False, f"Role r{display_number} does not exist.")
    return (True, "")


def validate_task_exists(role_id: int, task_number: int) -> Tuple[bool, str]:
    """Validate that a task exists in a role.

    Args:
        role_id: Role ID
        task_number: Task number within the role

    Returns:
        Tuple of (exists, error_message)
    """
    task = db.fetchone(
        "SELECT id FROM tasks WHERE role_id = ? AND task_number = ?",
        (role_id, task_number)
    )
    if not task:
        return (False, f"Task t{task_number} does not exist in the current role.")
    return (True, "")


def validate_task_ids_exist(role_id: int, task_numbers: list) -> Tuple[bool, str, list]:
    """Validate that multiple task IDs exist in a role.

    Args:
        role_id: Role ID
        task_numbers: List of task numbers to validate

    Returns:
        Tuple of (all_exist, error_message, valid_task_ids)
    """
    valid_task_ids = []
    invalid_tasks = []

    for task_num in task_numbers:
        task = db.fetchone(
            "SELECT id FROM tasks WHERE role_id = ? AND task_number = ?",
            (role_id, task_num)
        )
        if task:
            valid_task_ids.append(task['id'])
        else:
            invalid_tasks.append(f"t{task_num}")

    if invalid_tasks:
        return (
            False,
            f"Tasks do not exist: {', '.join(invalid_tasks)}.",
            []
        )

    return (True, "", valid_task_ids)


def detect_circular_dependency(task_id: int, blocks_task_id: int) -> Tuple[bool, str]:
    """Detect if adding a dependency would create a circular dependency.

    A circular dependency exists if:
    - Task A blocks Task B, and Task B already blocks Task A (direct circular)
    - Task A blocks Task B, Task B blocks Task C, and Task C blocks Task A (indirect circular)

    Args:
        task_id: ID of task that will block another task
        blocks_task_id: ID of task that will be blocked

    Returns:
        Tuple of (is_circular, error_message)
    """
    # Cannot block itself
    if task_id == blocks_task_id:
        return (True, "A task cannot block itself.")

    # Check if blocks_task_id already blocks task_id (direct circular)
    direct_circular = db.fetchone(
        "SELECT 1 FROM task_dependencies WHERE task_id = ? AND blocks_task_id = ?",
        (blocks_task_id, task_id)
    )
    if direct_circular:
        return (True, f"Circular dependency detected: tasks would block each other.")

    # Check for indirect circular dependency using recursive traversal
    # We need to check if blocks_task_id eventually leads back to task_id
    visited = set()
    to_check = [blocks_task_id]

    while to_check:
        current = to_check.pop(0)
        if current in visited:
            continue
        visited.add(current)

        # Get all tasks that current task blocks
        blocked_tasks = db.fetchall(
            "SELECT blocks_task_id FROM task_dependencies WHERE task_id = ?",
            (current,)
        )

        for blocked in blocked_tasks:
            blocked_id = blocked['blocks_task_id']
            if blocked_id == task_id:
                return (True, f"Circular dependency detected: would create a dependency loop.")
            to_check.append(blocked_id)

    return (False, "")


def validate_window_panel_count(panel_count: int) -> Tuple[bool, str]:
    """Validate window panel count.

    Args:
        panel_count: Number of panels requested

    Returns:
        Tuple of (is_valid, error_message)
    """
    if not isinstance(panel_count, int):
        return (False, f"Invalid panel count. Must be a number between 1 and 8.")

    if panel_count < 1 or panel_count > 8:
        return (False, f"Invalid panel count '{panel_count}'. Must be between 1 and 8.")

    return (True, "")


def validate_status(status: Optional[str]) -> Tuple[bool, str, Optional[str]]:
    """Validate task status.

    Args:
        status: Status string to validate

    Returns:
        Tuple of (is_valid, error_message, normalized_value)
    """
    if status is None or status == "":
        return (True, "", None)

    status_normalized = status.strip().lower()

    if status_normalized not in VALID_STATUSES:
        return (
            False,
            f"Invalid status '{status}'. Must be one of: todo, doing, or done.",
            None
        )

    return (True, "", status_normalized)


def validate_description(description: Optional[str]) -> Tuple[bool, str, Optional[str]]:
    """Validate task description.

    Args:
        description: Description string to validate

    Returns:
        Tuple of (is_valid, error_message, normalized_value)
    """
    if description is None or description.strip() == "":
        return (True, "", None)

    # Optional length limit (e.g., 2000 characters)
    normalized = description.strip()
    if len(normalized) > 2000:
        return (False, "Description is too long. Maximum 2000 characters.", None)

    return (True, "", normalized)


def format_validation_error(error_message: str, context: str = None) -> str:
    """Format a validation error message with context.

    Args:
        error_message: The validation error message
        context: Optional context about what was being attempted

    Returns:
        Formatted error message
    """
    if context:
        return f"{error_message}\n\nContext: {context}"
    return error_message
