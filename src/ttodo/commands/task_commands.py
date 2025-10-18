"""Task management commands."""
from ttodo.database.models import db
from ttodo.utils.date_utils import parse_date
from typing import Optional


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


def delete_task(task_id: int) -> bool:
    """Delete a task.

    Args:
        task_id: Task ID

    Returns:
        True if successful, False otherwise
    """
    db.execute("DELETE FROM tasks WHERE id = ?", (task_id,))
    db.commit()
    return True
