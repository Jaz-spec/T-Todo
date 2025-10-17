"""Database schema creation and migrations."""
from database.models import db


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


def initialize_database():
    """Initialize database connection and create schema."""
    db.connect()
    create_schema()


if __name__ == "__main__":
    # Allow running this script directly to initialize database
    initialize_database()
    print("Database initialized at: todo.db")
    db.close()
