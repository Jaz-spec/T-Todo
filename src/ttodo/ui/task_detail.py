"""Task detail view widget."""
from rich.panel import Panel
from rich.text import Text
from rich.console import Group
from rich.markdown import Markdown
from ttodo.utils.date_utils import format_relative_date
from ttodo.commands import task_commands


def render_task_detail(task, role_name: str, role_color: str) -> Panel:
    """Render full-screen task detail view.

    Args:
        task: Task database row
        role_name: Name of the role
        role_color: Hex color for the role

    Returns:
        Rich Panel with task details
    """
    lines = []

    # Task title
    task_num = task['task_number']
    title = task['title']
    title_text = Text()
    title_text.append(f"Task t{task_num}: ", style=f"bold {role_color}")
    title_text.append(title, style=f"bold")
    lines.append(title_text)
    lines.append("")

    # Due date
    if task['due_date']:
        relative_date = format_relative_date(task['due_date'])
        due_text = Text()
        due_text.append("Due: ", style="bold")
        due_text.append(f"{relative_date} ({task['due_date']})", style=role_color)
        lines.append(due_text)
    else:
        lines.append(Text("Due: No due date set", style="dim"))

    # Priority
    if task['priority']:
        priority_text = Text()
        priority_text.append("Priority: ", style="bold")
        priority_text.append(task['priority'], style=role_color)
        lines.append(priority_text)

    # Story points
    if task['story_points']:
        sp_text = Text()
        sp_text.append("Story Points: ", style="bold")
        sp_text.append(str(task['story_points']), style=role_color)
        lines.append(sp_text)

    # Status
    status_text = Text()
    status_text.append("Status: ", style="bold")
    status_map = {
        'todo': 'To Do',
        'doing': 'In Progress',
        'done': 'Completed'
    }
    status_display = status_map.get(task['status'], task['status'])
    status_text.append(status_display, style=role_color)
    lines.append(status_text)

    # Dependencies
    lines.append("")

    # Tasks this task blocks
    blocks_task_ids = task_commands.get_tasks_blocked_by(task['id'])
    if blocks_task_ids:
        blocks_numbers = []
        for blocked_id in blocks_task_ids:
            blocked_task = task_commands.db.fetchone(
                "SELECT task_number FROM tasks WHERE id = ?", (blocked_id,)
            )
            if blocked_task:
                blocks_numbers.append(f"t{blocked_task['task_number']}")

        if blocks_numbers:
            blocks_text = Text()
            blocks_text.append("Blocks: ", style="bold")
            blocks_text.append(", ".join(blocks_numbers), style=role_color)
            lines.append(blocks_text)

    # Tasks that block this task
    blocked_by_ids = task_commands.get_tasks_blocking(task['id'])
    if blocked_by_ids:
        blocked_by_numbers = []
        for blocking_id in blocked_by_ids:
            blocking_task = task_commands.db.fetchone(
                "SELECT task_number FROM tasks WHERE id = ?", (blocking_id,)
            )
            if blocking_task:
                blocked_by_numbers.append(f"t{blocking_task['task_number']}")

        if blocked_by_numbers:
            blocked_by_text = Text()
            blocked_by_text.append("Blocked by: ", style="bold")
            blocked_by_text.append(", ".join(blocked_by_numbers), style=role_color)
            lines.append(blocked_by_text)

    # Description
    if task['description']:
        lines.append("")
        lines.append(Text("Description:", style="bold"))
        lines.append(Text("─" * 60, style="dim"))
        md = Markdown(task['description'])
        lines.append(md)

    # Completed timestamp
    if task['completed_at']:
        lines.append("")
        completed_text = Text()
        completed_text.append("Completed: ", style="bold")
        completed_text.append(task['completed_at'], style="dim")
        lines.append(completed_text)

    lines.append("")
    lines.append(Text("[Press any key to return]", style="dim italic", justify="center"))

    # Create panel
    content = Group(*lines)
    panel = Panel(
        content,
        title=f"Task Details - {role_name}",
        title_align="left",
        border_style=role_color,
        padding=(1, 2)
    )

    return panel
