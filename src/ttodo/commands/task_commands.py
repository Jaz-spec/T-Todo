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
