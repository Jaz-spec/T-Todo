"""Task archiving utilities."""
from ttodo.database.models import db
from datetime import datetime, timedelta
import threading
import time


def archive_old_completed_tasks() -> int:
    """Archive tasks that have been completed for more than 24 hours.

    Returns:
        Number of tasks archived
    """
    # Calculate cutoff time (24 hours ago)
    cutoff_time = datetime.now() - timedelta(hours=24)
    cutoff_str = cutoff_time.isoformat()

    # Find tasks to archive (done status, completed more than 24 hours ago)
    tasks_to_archive = db.fetchall(
        """
        SELECT id FROM tasks
        WHERE status = 'done'
        AND completed_at IS NOT NULL
        AND completed_at < ?
        """,
        (cutoff_str,)
    )

    if not tasks_to_archive:
        return 0

    # Archive each task
    archived_count = 0
    for task in tasks_to_archive:
        task_id = task['id']

        # Insert into archived_tasks table
        db.execute(
            "INSERT INTO archived_tasks (task_id, archived_at) VALUES (?, ?)",
            (task_id, datetime.now().isoformat())
        )

        # Delete from tasks table
        db.execute("DELETE FROM tasks WHERE id = ?", (task_id,))

        archived_count += 1

    db.commit()
    return archived_count


class ArchiveScheduler:
    """Background scheduler for automatic task archiving."""

    def __init__(self, interval_hours: int = 1):
        """Initialize the archive scheduler.

        Args:
            interval_hours: How often to run archive check (default: 1 hour)
        """
        self.interval_hours = interval_hours
        self.running = False
        self.thread = None

    def start(self):
        """Start the background archiving thread."""
        if self.running:
            return

        self.running = True
        self.thread = threading.Thread(target=self._run, daemon=True)
        self.thread.start()

    def stop(self):
        """Stop the background archiving thread."""
        self.running = False
        if self.thread:
            self.thread.join(timeout=1)

    def _run(self):
        """Background thread main loop."""
        while self.running:
            try:
                # Run archive operation
                archived_count = archive_old_completed_tasks()

                # Log if tasks were archived (for debugging)
                if archived_count > 0:
                    # Could add logging here if desired
                    pass

            except Exception as e:
                # Silently catch errors to prevent thread crash
                # Could add logging here if desired
                pass

            # Sleep for the specified interval
            # Check every minute to allow clean shutdown
            for _ in range(self.interval_hours * 60):
                if not self.running:
                    break
                time.sleep(60)  # Sleep 1 minute at a time
