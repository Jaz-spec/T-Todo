"""Task management commands."""
from ttodo.database.models import db
from ttodo.utils.date_utils import parse_date
from typing import Optional
import json


def get_next_task_number(role_id: int) -> int:
    """Get next available task number for a role.

    Args:
        role_id: Role ID

    Returns:
        Next task number (1-based)
    """
    result = db.fetchone(
        "SELECT MAX(task_number) as max_num FROM tasks WHERE role_id = ?",
        (role_id,)
    )
    if result and result['max_num'] is not None:
        return result['max_num'] + 1
    return 1


def create_task(
    role_id: int,
    title: str,
    description: Optional[str] = None,
    due_date: Optional[str] = None,
    priority: Optional[str] = None,
    story_points: Optional[int] = None
) -> Optional[int]:
    """Create a new task.

    Args:
        role_id: Role ID for the task
        title: Task title
        description: Task description (optional)
        due_date: Due date string (will be parsed to ISO format)
        priority: Priority level (High/Medium/Low)
        story_points: Story points (1,2,3,5,8,13)

    Returns:
        Task ID if successful, None otherwise
    """
    if not title or not title.strip():
        return None

    # Parse due date if provided
    iso_date = None
    if due_date:
        iso_date = parse_date(due_date)

    task_number = get_next_task_number(role_id)

    cursor = db.execute(
        """INSERT INTO tasks
           (role_id, task_number, title, description, due_date, priority, story_points, status)
           VALUES (?, ?, ?, ?, ?, ?, ?, 'todo')""",
        (role_id, task_number, title.strip(), description, iso_date, priority, story_points)
    )
    db.commit()

    return cursor.lastrowid


def get_task_by_number(role_id: int, task_number: int):
    """Get task by role ID and task number.

    Args:
        role_id: Role ID
        task_number: Task number

    Returns:
        Task row or None
    """
    return db.fetchone(
        "SELECT * FROM tasks WHERE role_id = ? AND task_number = ?",
        (role_id, task_number)
    )


def get_tasks_for_role(role_id: int, status: Optional[str] = None):
    """Get all tasks for a role, optionally filtered by status.

    Args:
        role_id: Role ID
        status: Optional status filter (todo/doing/done)

    Returns:
        List of task rows
    """
    if status:
        return db.fetchall(
            """SELECT * FROM tasks
               WHERE role_id = ? AND status = ?
               ORDER BY
                   CASE WHEN due_date IS NULL THEN 1 ELSE 0 END,
                   due_date ASC,
                   created_at ASC""",
            (role_id, status)
        )
    else:
        return db.fetchall(
            """SELECT * FROM tasks
               WHERE role_id = ?
               ORDER BY
                   CASE
                       WHEN status = 'doing' THEN 0
                       WHEN status = 'todo' THEN 1
                       WHEN status = 'done' THEN 2
                   END,
                   CASE WHEN due_date IS NULL THEN 1 ELSE 0 END,
                   due_date ASC,
                   created_at ASC""",
            (role_id,)
        )


def update_task(
    task_id: int,
    title: Optional[str] = None,
    description: Optional[str] = None,
    due_date: Optional[str] = None,
    priority: Optional[str] = None,
    story_points: Optional[int] = None
) -> bool:
    """Update task fields.

    Args:
        task_id: Task ID
        title: New title (optional)
        description: New description (optional)
        due_date: New due date string (will be parsed to ISO format)
        priority: New priority level (High/Medium/Low)
        story_points: New story points (1,2,3,5,8,13)

    Returns:
        True if successful, False otherwise
    """
    # Parse due date if provided
    iso_date = None
    if due_date is not None:
        iso_date = parse_date(due_date) if due_date else None

    # Build update query dynamically based on provided fields
    updates = []
    params = []

    if title is not None:
        updates.append("title = ?")
        params.append(title)

    if description is not None:
        updates.append("description = ?")
        params.append(description)

    if due_date is not None:
        updates.append("due_date = ?")
        params.append(iso_date)

    if priority is not None:
        updates.append("priority = ?")
        params.append(priority)

    if story_points is not None:
        updates.append("story_points = ?")
        params.append(story_points)

    if not updates:
        return False  # Nothing to update

    # Add task_id to params
    params.append(task_id)

    # Execute update
    query = f"UPDATE tasks SET {', '.join(updates)} WHERE id = ?"
    db.execute(query, tuple(params))
    db.commit()

    return True


def update_task_status(task_id: int, status: str) -> bool:
    """Update task status.

    Args:
        task_id: Task ID
        status: New status (todo/doing/done)

    Returns:
        True if successful, False otherwise
    """
    if status not in ('todo', 'doing', 'done'):
        return False

    if status == 'done':
        db.execute(
            "UPDATE tasks SET status = ?, completed_at = CURRENT_TIMESTAMP WHERE id = ?",
            (status, task_id)
        )
    else:
        db.execute(
            "UPDATE tasks SET status = ?, completed_at = NULL WHERE id = ?",
            (status, task_id)
        )

    db.commit()
    return True


def delete_task(task_id: int, save_to_undo: bool = True) -> bool:
    """Delete a task.

    Args:
        task_id: Task ID
        save_to_undo: Whether to save to undo stack (default True)

    Returns:
        True if successful, False otherwise
    """
    # Get task data before deletion (for undo)
    if save_to_undo:
        task = db.fetchone("SELECT * FROM tasks WHERE id = ?", (task_id,))
        if task:
            save_task_to_undo(task)

    db.execute("DELETE FROM tasks WHERE id = ?", (task_id,))
    db.commit()
    return True


def save_task_to_undo(task) -> None:
    """Save deleted task to undo stack.

    Args:
        task: Task database row
    """
    # Convert task row to dict
    task_data = dict(task)

    # Serialize to JSON
    data_json = json.dumps(task_data)

    # Insert into undo stack
    db.execute(
        "INSERT INTO undo_stack (action_type, data) VALUES (?, ?)",
        ('delete_task', data_json)
    )
    db.commit()

    # Limit undo stack to 20 items
    db.execute("""
        DELETE FROM undo_stack
        WHERE id NOT IN (
            SELECT id FROM undo_stack
            ORDER BY created_at DESC
            LIMIT 20
        )
    """)
    db.commit()


def undo_last_deletion() -> Optional[dict]:
    """Restore last deleted task from undo stack.

    Returns:
        Restored task data if successful, None otherwise
    """
    # Get most recent delete_task action
    undo_entry = db.fetchone(
        """SELECT * FROM undo_stack
           WHERE action_type = 'delete_task'
           ORDER BY created_at DESC
           LIMIT 1"""
    )

    if not undo_entry:
        return None

    # Parse task data
    task_data = json.loads(undo_entry['data'])

    # Restore task to database
    db.execute(
        """INSERT INTO tasks
           (id, role_id, task_number, title, description, due_date,
            priority, story_points, status, completed_at, created_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            task_data['id'],
            task_data['role_id'],
            task_data['task_number'],
            task_data['title'],
            task_data.get('description'),
            task_data.get('due_date'),
            task_data.get('priority'),
            task_data.get('story_points'),
            task_data['status'],
            task_data.get('completed_at'),
            task_data['created_at']
        )
    )

    # Remove from undo stack
    db.execute("DELETE FROM undo_stack WHERE id = ?", (undo_entry['id'],))
    db.commit()

    return task_data


def add_task_dependency(task_id: int, blocks_task_id: int) -> bool:
    """Add a blocking dependency between tasks.

    Args:
        task_id: ID of the task that blocks another
        blocks_task_id: ID of the task being blocked

    Returns:
        True if successful, False otherwise
    """
    # Prevent self-blocking
    if task_id == blocks_task_id:
        return False

    # Check for circular dependencies
    if would_create_circular_dependency(task_id, blocks_task_id):
        return False

    try:
        db.execute(
            "INSERT INTO task_dependencies (task_id, blocks_task_id) VALUES (?, ?)",
            (task_id, blocks_task_id)
        )
        db.commit()
        return True
    except Exception:
        return False


def remove_task_dependency(task_id: int, blocks_task_id: int) -> bool:
    """Remove a blocking dependency between tasks.

    Args:
        task_id: ID of the task that blocks another
        blocks_task_id: ID of the task being blocked

    Returns:
        True if successful, False otherwise
    """
    db.execute(
        "DELETE FROM task_dependencies WHERE task_id = ? AND blocks_task_id = ?",
        (task_id, blocks_task_id)
    )
    db.commit()
    return True


def get_tasks_blocked_by(task_id: int) -> list:
    """Get all tasks blocked by this task.

    Args:
        task_id: Task ID

    Returns:
        List of task IDs that are blocked by this task
    """
    results = db.fetchall(
        "SELECT blocks_task_id FROM task_dependencies WHERE task_id = ?",
        (task_id,)
    )
    return [row['blocks_task_id'] for row in results]


def get_tasks_blocking(task_id: int) -> list:
    """Get all tasks that block this task.

    Args:
        task_id: Task ID

    Returns:
        List of task IDs that block this task
    """
    results = db.fetchall(
        "SELECT task_id FROM task_dependencies WHERE blocks_task_id = ?",
        (task_id,)
    )
    return [row['task_id'] for row in results]


def is_task_blocked(task_id: int) -> bool:
    """Check if a task is blocked by any other tasks.

    Args:
        task_id: Task ID

    Returns:
        True if task is blocked, False otherwise
    """
    result = db.fetchone(
        "SELECT COUNT(*) as count FROM task_dependencies WHERE blocks_task_id = ?",
        (task_id,)
    )
    return result['count'] > 0


def would_create_circular_dependency(task_id: int, blocks_task_id: int) -> bool:
    """Check if adding a dependency would create a circular dependency.

    This checks if blocks_task_id (directly or transitively) blocks task_id.
    If so, adding task_id blocks blocks_task_id would create a cycle.

    Args:
        task_id: ID of the task that would block another
        blocks_task_id: ID of the task that would be blocked

    Returns:
        True if it would create a circular dependency, False otherwise
    """
    # Check if blocks_task_id already blocks task_id (directly or transitively)
    visited = set()
    to_check = [blocks_task_id]

    while to_check:
        current = to_check.pop()
        if current in visited:
            continue
        visited.add(current)

        # If current blocks task_id, we have a cycle
        if current == task_id:
            return True

        # Get all tasks that current blocks
        blocked_tasks = get_tasks_blocked_by(current)
        to_check.extend(blocked_tasks)

    return False


def validate_blocking_task_ids(role_id: int, blocking_ids_str: Optional[str]) -> tuple[list[int], Optional[str]]:
    """Validate and parse blocking task IDs.

    Args:
        role_id: Role ID (tasks must be in same role)
        blocking_ids_str: Comma-separated task numbers (e.g., "1,3,5")

    Returns:
        Tuple of (list of valid task IDs, error message or None)
    """
    if not blocking_ids_str or not blocking_ids_str.strip():
        return ([], None)

    valid_task_ids = []
    invalid_numbers = []

    # Parse comma-separated numbers
    parts = [p.strip() for p in blocking_ids_str.split(',')]
    for part in parts:
        if not part:
            continue

        try:
            task_number = int(part)
            task = get_task_by_number(role_id, task_number)
            if task:
                valid_task_ids.append(task['id'])
            else:
                invalid_numbers.append(part)
        except ValueError:
            invalid_numbers.append(part)

    if invalid_numbers:
        return ([], f"Invalid task numbers: {', '.join(invalid_numbers)}")

    return (valid_task_ids, None)
