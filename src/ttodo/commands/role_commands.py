"""Role management commands."""
from ttodo.database.models import db
from ttodo.utils.colors import ROLE_COLORS, get_role_color
from typing import Optional


def get_next_display_number() -> int:
    """Get the next available display number for a role.

    Returns:
        Next available display number (1-based)
    """
    result = db.fetchone("SELECT MAX(display_number) as max_num FROM roles")
    if result and result['max_num'] is not None:
        return result['max_num'] + 1
    return 1


def create_role(name: str, color: str) -> Optional[int]:
    """Create a new role.

    Args:
        name: Role name
        color: Hex color string

    Returns:
        Role ID if successful, None otherwise
    """
    if not name or not name.strip():
        return None

    display_number = get_next_display_number()

    cursor = db.execute(
        """INSERT INTO roles (display_number, name, color)
           VALUES (?, ?, ?)""",
        (display_number, name.strip(), color)
    )
    db.commit()

    return cursor.lastrowid


def get_role_by_number(display_number: int):
    """Get role by display number.

    Args:
        display_number: Role display number

    Returns:
        Role row or None
    """
    return db.fetchone(
        "SELECT * FROM roles WHERE display_number = ?",
        (display_number,)
    )


def get_role_by_id(role_id: int):
    """Get role by ID.

    Args:
        role_id: Role ID

    Returns:
        Role row or None
    """
    return db.fetchone(
        "SELECT * FROM roles WHERE id = ?",
        (role_id,)
    )


def get_all_roles():
    """Get all roles ordered by display number.

    Returns:
        List of role rows
    """
    return db.fetchall(
        "SELECT * FROM roles ORDER BY display_number"
    )


def delete_role(role_id: int) -> bool:
    """Delete a role by ID.

    Args:
        role_id: Role ID to delete

    Returns:
        True if successful, False otherwise
    """
    # Check if role has tasks
    task_count = db.fetchone(
        "SELECT COUNT(*) as count FROM tasks WHERE role_id = ?",
        (role_id,)
    )

    if task_count and task_count['count'] > 0:
        return False  # Cannot delete role with tasks

    db.execute("DELETE FROM roles WHERE id = ?", (role_id,))
    db.commit()
    return True


def get_next_color_index() -> int:
    """Get index of next color to assign.

    Returns:
        Index into ROLE_COLORS (cycles through palette)
    """
    role_count = db.fetchone("SELECT COUNT(*) as count FROM roles")
    count = role_count['count'] if role_count else 0
    return count % len(ROLE_COLORS)


def remap_role_numbers(role_mappings: dict) -> bool:
    """Remap role display numbers.

    Args:
        role_mappings: Dict mapping role_id to new display_number

    Returns:
        True if successful, False otherwise
    """
    try:
        # Use a temporary negative offset to avoid unique constraint violations
        # First, set all to negative values
        for role_id, new_number in role_mappings.items():
            db.execute(
                "UPDATE roles SET display_number = ? WHERE id = ?",
                (-new_number, role_id)
            )

        # Then set all to positive values
        for role_id, new_number in role_mappings.items():
            db.execute(
                "UPDATE roles SET display_number = ? WHERE id = ?",
                (new_number, role_id)
            )

        db.commit()
        return True
    except Exception as e:
        db.rollback()
        return False


def get_role(role_id: int):
    """Get role by ID (alias for get_role_by_id for consistency).

    Args:
        role_id: Role ID

    Returns:
        Role row or None
    """
    return get_role_by_id(role_id)


def role_has_tasks(role_id: int) -> bool:
    """Check if a role has any tasks.

    Args:
        role_id: Role ID

    Returns:
        True if role has tasks, False otherwise
    """
    task_count = db.fetchone(
        "SELECT COUNT(*) as count FROM tasks WHERE role_id = ?",
        (role_id,)
    )
    return task_count and task_count['count'] > 0
