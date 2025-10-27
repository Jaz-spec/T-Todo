"""Role panel widgets for displaying tasks."""
from textual.widgets import Static
from rich.text import Text
from rich.panel import Panel as RichPanel
from rich.console import Group
from ttodo.commands.task_commands import (
    get_tasks_for_role,
    is_task_blocked,
    get_tasks_blocking,
    get_tasks_blocked_by
)
from ttodo.database.models import db
from ttodo.utils.date_utils import format_relative_date
from ttodo.utils.colors import get_active_color, get_blocked_color


class RolePanel(Static):
    """Widget for displaying a role's tasks."""

    def __init__(self, role_id: int, role_name: str, display_number: int, color: str, is_active: bool = False):
        """Initialize role panel.

        Args:
            role_id: Database ID of the role
            role_name: Name of the role
            display_number: Display number (r1, r2, etc.)
            color: Hex color string for the role
            is_active: Whether this is the active role
        """
        super().__init__()
        self.role_id = role_id
        self.role_name = role_name
        self.display_number = display_number
        self.base_color = color
        self.is_active = is_active
        self.add_class("role-panel")

    def render(self) -> RichPanel:
        """Render the role panel with tasks.

        Returns:
            Rich Panel with formatted content
        """
        # Get tasks for this role
        tasks = get_tasks_for_role(self.role_id)

        # Separate tasks by status
        doing_tasks = [t for t in tasks if t['status'] == 'doing']
        todo_tasks = [t for t in tasks if t['status'] == 'todo']

        # Build content
        lines = []

        # In-progress section
        if doing_tasks:
            separator = "─" * 25 + " IN PROGRESS " + "─" * 25
            lines.append(Text(separator, style=f"dim {self.base_color}"))
            for i, task in enumerate(doing_tasks):
                task_lines = self._format_task_block(task)
                lines.extend(task_lines)
                # Add spacing between tasks (but not after last task)
                if i < len(doing_tasks) - 1:
                    lines.append(Text())
            lines.append(Text("─" * 63, style=f"dim {self.base_color}"))
            lines.append("")  # Empty line after separator

        # Todo tasks
        if todo_tasks:
            for i, task in enumerate(todo_tasks):
                task_lines = self._format_task_block(task)
                lines.extend(task_lines)
                # Add spacing between tasks (but not after last task)
                if i < len(todo_tasks) - 1:
                    lines.append(Text())

        # Empty state
        if not doing_tasks and not todo_tasks:
            lines.append(Text("No tasks yet. Use 'add' to create a task.", style="dim italic"))

        # Create panel
        content = Group(*lines) if lines else ""
        title = f"{self.role_name} (r{self.display_number})"

        # Use brighter color if active
        panel_color = get_active_color(self.base_color) if self.is_active else self.base_color

        panel = RichPanel(
            content,
            title=title,
            title_align="left",
            border_style=panel_color,
            padding=(1, 2),
        )

        return panel

    def _format_task_block(self, task) -> list:
        """Format a task as multiple lines with all details.

        Args:
            task: Task database row

        Returns:
            List of Rich Text objects
        """
        lines = []
        task_num = task['task_number']
        title = task['title']
        due_date = task['due_date']
        priority = task['priority']
        story_points = task['story_points']

        # Check if task is blocked
        is_blocked = is_task_blocked(task['id'])
        task_color = get_blocked_color(self.base_color) if is_blocked else self.base_color

        # Title line
        title_line = Text()
        title_line.append(f"t{task_num}: ", style=f"bold {task_color}")
        title_line.append(title, style=f"bold {task_color}")
        lines.append(title_line)

        # Details line (due date, priority, story points)
        details = []
        if due_date:
            relative_date = format_relative_date(due_date)
            details.append(f"Due: {relative_date}")
        if priority:
            details.append(f"Pri: {priority}")
        if story_points:
            details.append(f"SP: {story_points}")

        if details:
            detail_line = Text()
            detail_line.append("  ", style=task_color)  # Indent
            detail_line.append(" | ".join(details), style=f"dim {task_color}")
            lines.append(detail_line)

        # Dependencies line
        blocking_ids = get_tasks_blocking(task['id'])
        blocked_by_ids = get_tasks_blocked_by(task['id'])

        if blocking_ids or blocked_by_ids:
            dep_line = Text()
            dep_line.append("  ", style=task_color)  # Indent
            dep_parts = []

            if blocking_ids:
                blocking_numbers = []
                for blocking_id in blocking_ids:
                    blocking_task = db.fetchone(
                        "SELECT task_number FROM tasks WHERE id = ?", (blocking_id,)
                    )
                    if blocking_task:
                        blocking_numbers.append(f"t{blocking_task['task_number']}")
                if blocking_numbers:
                    dep_parts.append(f"Blocked by: {', '.join(blocking_numbers)}")

            if blocked_by_ids:
                blocked_numbers = []
                for blocked_id in blocked_by_ids:
                    blocked_task = db.fetchone(
                        "SELECT task_number FROM tasks WHERE id = ?", (blocked_id,)
                    )
                    if blocked_task:
                        blocked_numbers.append(f"t{blocked_task['task_number']}")
                if blocked_numbers:
                    dep_parts.append(f"Blocks: {', '.join(blocked_numbers)}")

            if dep_parts:
                dep_line.append(" | ".join(dep_parts), style=f"dim {task_color}")
                lines.append(dep_line)

        # Description (if exists)
        description = task['description']
        if description:
            desc_line = Text()
            desc_line.append("  ", style=task_color)  # Indent
            desc_line.append("Desc: ", style=f"dim {task_color}")
            # Truncate long descriptions
            if len(description) > 80:
                desc_line.append(description[:80] + "...", style=f"dim {task_color}")
            else:
                desc_line.append(description, style=f"dim {task_color}")
            lines.append(desc_line)

        return lines

    def update_active_state(self, is_active: bool):
        """Update the active state of the panel.

        Args:
            is_active: Whether this panel should be active
        """
        self.is_active = is_active
        self.refresh()
