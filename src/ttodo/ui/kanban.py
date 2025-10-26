"""Kanban board view widget for task visualization."""
from textual.widgets import Static
from textual.containers import Horizontal
from rich.text import Text
from rich.panel import Panel as RichPanel
from rich.console import Group
from ttodo.commands.task_commands import get_tasks_for_role, is_task_blocked
from ttodo.utils.date_utils import format_relative_date
from ttodo.utils.colors import get_active_color, get_blocked_color


class KanbanColumn(Static):
    """Widget for a single kanban column with its own border."""

    def __init__(self, column_name: str, status: str, role_id: int, color: str):
        """Initialize kanban column.

        Args:
            column_name: Column title (TODO/DOING/DONE)
            status: Task status to filter by (todo/doing/done)
            role_id: Role ID to fetch tasks for
            color: Hex color string for the role
        """
        super().__init__()
        self.column_name = column_name
        self.status = status
        self.role_id = role_id
        self.color = color
        self.add_class("kanban-column")

    def render(self) -> RichPanel:
        """Render the kanban column with border.

        Returns:
            Rich Panel with column content
        """
        # Get tasks for this role and status
        all_tasks = get_tasks_for_role(self.role_id)
        tasks = sorted(
            [t for t in all_tasks if t['status'] == self.status],
            key=lambda x: (x['due_date'] or '9999-12-31')  # Tasks without due date go last
        )

        lines = []

        # Add tasks
        if tasks:
            for i, task in enumerate(tasks):
                # Check if task is blocked - use dulled color if so
                is_blocked = is_task_blocked(task['id'])
                task_color = get_blocked_color(self.color) if is_blocked else self.color

                # Task number and title
                title_line = Text()
                title_line.append(f"t{task['task_number']}: ", style=f"bold {task_color}")
                title_line.append(task['title'], style=task_color)
                lines.append(title_line)

                # Due date (if exists)
                if task['due_date']:
                    due_line = Text()
                    due_line.append("  Due: ", style=f"dim {task_color}")
                    due_line.append(format_relative_date(task['due_date']), style=task_color)
                    lines.append(due_line)

                # Priority (if exists)
                if task['priority']:
                    pri_line = Text()
                    pri_line.append("  Pri: ", style=f"dim {task_color}")
                    pri_line.append(task['priority'], style=task_color)
                    lines.append(pri_line)

                # Story points (if exists)
                if task['story_points']:
                    sp_line = Text()
                    sp_line.append("  SP: ", style=f"dim {task_color}")
                    sp_line.append(str(task['story_points']), style=task_color)
                    lines.append(sp_line)

                # Add spacing between cards
                if i < len(tasks) - 1:
                    lines.append("")  # Empty line between cards

        # Empty state
        if not tasks:
            lines.append(Text("No tasks", style="dim italic"))

        content = Group(*lines) if lines else Text("No tasks", style="dim italic")

        # Create column panel with border and title
        panel = RichPanel(
            content,
            title=self.column_name,
            title_align="center",
            border_style=self.color,
            padding=(1, 2),
        )

        return panel


class KanbanBoard(Horizontal):
    """Container for three kanban columns displayed side by side."""

    def __init__(self, role_id: int, role_name: str, display_number: int, color: str):
        """Initialize kanban board.

        Args:
            role_id: Database ID of the role
            role_name: Name of the role
            display_number: Display number (r1, r2, etc.)
            color: Hex color string for the role
        """
        super().__init__()
        self.role_id = role_id
        self.role_name = role_name
        self.display_number = display_number
        self.color = color
        self.add_class("kanban-board")

    def compose(self):
        """Compose the three kanban columns."""
        yield KanbanColumn("TODO", "todo", self.role_id, self.color)
        yield KanbanColumn("DOING", "doing", self.role_id, self.color)
        yield KanbanColumn("DONE", "done", self.role_id, self.color)

    def refresh_columns(self):
        """Refresh all three columns to show updated tasks."""
        # Remove existing columns
        for child in list(self.children):
            child.remove()

        # Re-mount fresh columns
        self.mount(KanbanColumn("TODO", "todo", self.role_id, self.color))
        self.mount(KanbanColumn("DOING", "doing", self.role_id, self.color))
        self.mount(KanbanColumn("DONE", "done", self.role_id, self.color))
