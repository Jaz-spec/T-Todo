"""Database models and connection management for Terminal Todo."""
import sqlite3
from pathlib import Path
from typing import Optional
import json


class Database:
    """Manages database connection and operations."""

    def __init__(self, db_path: str = "todo.db"):
        """Initialize database connection.

        Args:
            db_path: Path to the SQLite database file
        """
        self.db_path = db_path
        self.conn: Optional[sqlite3.Connection] = None

    def connect(self):
        """Establish database connection."""
        self.conn = sqlite3.connect(self.db_path)
        self.conn.row_factory = sqlite3.Row  # Enable column access by name
        # Enable foreign key constraints
        self.conn.execute("PRAGMA foreign_keys = ON")

    def close(self):
        """Close database connection."""
        if self.conn:
            self.conn.close()
            self.conn = None

    def execute(self, query: str, params: tuple = ()):
        """Execute a query and return cursor.

        Args:
            query: SQL query string
            params: Query parameters

        Returns:
            Cursor object
        """
        if not self.conn:
            self.connect()
        return self.conn.execute(query, params)

    def commit(self):
        """Commit current transaction."""
        if self.conn:
            self.conn.commit()

    def fetchone(self, query: str, params: tuple = ()):
        """Execute query and fetch one result.

        Args:
            query: SQL query string
            params: Query parameters

        Returns:
            Single row result or None
        """
        cursor = self.execute(query, params)
        return cursor.fetchone()

    def fetchall(self, query: str, params: tuple = ()):
        """Execute query and fetch all results.

        Args:
            query: SQL query string
            params: Query parameters

        Returns:
            List of row results
        """
        cursor = self.execute(query, params)
        return cursor.fetchall()


# Global database instance
db = Database()
