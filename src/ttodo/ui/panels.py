"""Role panel widgets for displaying tasks."""
from textual.widgets import Static
from rich.text import Text
from rich.panel import Panel as RichPanel
from rich.console import Group
from ttodo.commands.task_commands import get_tasks_for_role
from ttodo.utils.date_utils import format_relative_date
from ttodo.utils.colors import get_active_color


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
            for task in doing_tasks:
                task_line = self._format_task_line(task)
                lines.append(task_line)
            lines.append(Text("─" * 63, style=f"dim {self.base_color}"))
            lines.append("")  # Empty line after separator

        # Todo tasks
        if todo_tasks:
            for task in todo_tasks:
                task_line = self._format_task_line(task)
                lines.append(task_line)

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

    def _format_task_line(self, task) -> Text:
        """Format a single task line.

        Args:
            task: Task database row

        Returns:
            Formatted Rich Text object
        """
        # Format: "t1: Task title - Tomorrow"
        task_num = task['task_number']
        title = task['title']
        due_date = task['due_date']

        line = Text()
        line.append(f"t{task_num}: ", style=f"bold {self.base_color}")
        line.append(title, style=self.base_color)

        if due_date:
            relative_date = format_relative_date(due_date)
            line.append(f" - {relative_date}", style=f"dim {self.base_color}")

        return line

    def update_active_state(self, is_active: bool):
        """Update the active state of the panel.

        Args:
            is_active: Whether this panel should be active
        """
        self.is_active = is_active
        self.refresh()
