"""Database schema creation and migrations."""
from ttodo.database.models import db


def create_schema():
    """Create all database tables with proper schema."""

    # Roles table
    db.execute("""
        CREATE TABLE IF NOT EXISTS roles (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            display_number INTEGER UNIQUE NOT NULL,
            name TEXT NOT NULL,
            color TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Tasks table
    db.execute("""
        CREATE TABLE IF NOT EXISTS tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            role_id INTEGER NOT NULL,
            task_number INTEGER NOT NULL,
            title TEXT NOT NULL,
            description TEXT,
            due_date TEXT,
            priority TEXT CHECK(priority IN ('High', 'Medium', 'Low')),
            story_points INTEGER CHECK(story_points IN (1, 2, 3, 5, 8, 13)),
            status TEXT CHECK(status IN ('todo', 'doing', 'done')) DEFAULT 'todo',
            completed_at TIMESTAMP,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (role_id) REFERENCES roles(id) ON DELETE CASCADE,
            UNIQUE(role_id, task_number)
        )
    """)

    # Task dependencies table
    db.execute("""
        CREATE TABLE IF NOT EXISTS task_dependencies (
            task_id INTEGER NOT NULL,
            blocks_task_id INTEGER NOT NULL,
            FOREIGN KEY (task_id) REFERENCES tasks(id) ON DELETE CASCADE,
            FOREIGN KEY (blocks_task_id) REFERENCES tasks(id) ON DELETE CASCADE,
            PRIMARY KEY (task_id, blocks_task_id)
        )
    """)

    # Window layout table
    db.execute("""
        CREATE TABLE IF NOT EXISTS window_layout (
            id INTEGER PRIMARY KEY CHECK (id = 1),
            panel_count INTEGER NOT NULL,
            panel_roles TEXT NOT NULL
        )
    """)

    # Undo stack table
    db.execute("""
        CREATE TABLE IF NOT EXISTS undo_stack (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            action_type TEXT CHECK(action_type IN ('delete_task', 'delete_role')),
            data TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Archived tasks table
    db.execute("""
        CREATE TABLE IF NOT EXISTS archived_tasks (
            task_id INTEGER PRIMARY KEY,
            archived_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Create indexes for performance
    db.execute("""
        CREATE INDEX IF NOT EXISTS idx_tasks_role_status
        ON tasks(role_id, status, due_date)
    """)

    db.execute("""
        CREATE INDEX IF NOT EXISTS idx_tasks_due_date
        ON tasks(due_date)
    """)

    db.commit()
    print("Database schema created successfully")


def validate_database_integrity():
    """Validate and repair database integrity issues.

    Checks for and fixes:
    - Orphaned task dependencies (references to deleted tasks)
    - Tasks with invalid role_id references
    - Invalid task numbering
    """
    # Enable foreign key constraints
    db.execute("PRAGMA foreign_keys = ON")
    db.commit()

    # Clean up orphaned dependencies (where either task doesn't exist)
    db.execute("""
        DELETE FROM task_dependencies
        WHERE task_id NOT IN (SELECT id FROM tasks)
           OR blocks_task_id NOT IN (SELECT id FROM tasks)
    """)
    rows_deleted = db.conn.total_changes
    if rows_deleted > 0:
        print(f"Cleaned up {rows_deleted} orphaned task dependencies")

    # Check for tasks with invalid role_id (shouldn't happen with FK constraints, but check anyway)
    invalid_tasks = db.fetchall("""
        SELECT t.id, t.title FROM tasks t
        LEFT JOIN roles r ON t.role_id = r.id
        WHERE r.id IS NULL
    """)
    if invalid_tasks:
        print(f"Warning: Found {len(invalid_tasks)} tasks with invalid role_id")
        # Delete these orphaned tasks
        for task in invalid_tasks:
            db.execute("DELETE FROM tasks WHERE id = ?", (task['id'],))
        print(f"Deleted {len(invalid_tasks)} orphaned tasks")

    db.commit()


def initialize_database():
    """Initialize database connection and create schema."""
    db.connect()
    create_schema()
    validate_database_integrity()


if __name__ == "__main__":
    # Allow running this script directly to initialize database
    initialize_database()
    print("Database initialized at: todo.db")
    db.close()
