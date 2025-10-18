"""Main TUI application using Textual."""

from textual.app import App, ComposeResult
from textual.widgets import Input, Static, Header
from textual.containers import Container, Vertical
from textual.binding import Binding
from ttodo.commands.parser import parser
from ttodo.commands import role_commands, task_commands
from ttodo.database.models import db
from ttodo.database.migrations import initialize_database
from ttodo.ui.panels import RolePanel
from ttodo.ui.task_detail import render_task_detail
from ttodo.utils.colors import ROLE_COLORS, get_role_color
import re


class CommandInput(Input):
    """Custom command input widget."""

    def __init__(self):
        super().__init__(placeholder="Type a command... (type 'help' for commands)")
        self.command_history = []
        self.history_index = -1

    def add_to_history(self, command: str):
        """Add command to history."""
        if command and (
            not self.command_history or command != self.command_history[-1]
        ):
            self.command_history.append(command)
            if len(self.command_history) > 50:  # Max 50 commands
                self.command_history.pop(0)
        self.history_index = len(self.command_history)


class MainContent(Static):
    """Main content area for panels/views."""

    def __init__(self):
        super().__init__("Welcome to Terminal Todo!\n\nType 'new role' to get started.")
        self.add_class("main-content")


class TodoApp(App):
    """Terminal Todo TUI Application."""

    CSS = """
    Screen {
        background: $surface;
    }

    .main-content {
        height: 1fr;
        padding: 1;
        background: $surface;
        color: $text;
    }

    .input-container {
        height: auto;
        dock: bottom;
        background: $surface;
        padding: 1;
    }

    CommandInput {
        width: 100%;
    }

    .error {
        color: $error;
    }

    .success {
        color: $success;
    }
    """

    BINDINGS = [
        Binding("ctrl+c", "quit", "Quit", show=True),
        Binding("escape", "clear_input", "Clear", show=False),
    ]

    def __init__(self):
        super().__init__()
        self.main_content = None
        self.command_input = None
        self.active_role_id = None  # Currently selected role
        self.current_panel = None  # Currently displayed panel widget
        # State flags for interactive input
        self._awaiting_role_name = False
        self._awaiting_task_title = False
        self._awaiting_task_due_date = False
        self._pending_task_title = None
        self._in_task_detail_view = False  # Track if we're in detail view
        self._awaiting_delete_confirmation = False
        self._pending_delete_task = None
        self._awaiting_edit_title = False
        self._awaiting_edit_due_date = False
        self._pending_edit_task = None

    def compose(self) -> ComposeResult:
        """Compose the UI layout."""
        self.main_content = MainContent()
        self.command_input = CommandInput()

        yield self.main_content

        # Input container at bottom
        with Container(classes="input-container"):
            yield Static("> ", id="prompt")
            yield self.command_input

    def on_mount(self) -> None:
        """Called when app is mounted."""
        # Initialize database
        initialize_database()

        # Focus the input
        self.command_input.focus()

    def on_input_submitted(self, event: Input.Submitted) -> None:
        """Handle command submission."""
        command_str = event.value.strip()

        # Clear input first
        self.command_input.value = ""

        # If in task detail view, any key press returns to panel
        if self._in_task_detail_view:
            self._exit_task_detail_view()
            return

        if not command_str and (self._awaiting_task_due_date):
            # Allow empty input for skipping due date
            self._handle_task_due_date_input("")
            return

        if not command_str and (self._awaiting_edit_title):
            # Allow empty input to keep current title
            self._handle_edit_title_input("")
            return

        if not command_str and (self._awaiting_edit_due_date):
            # Allow empty input to keep current due date
            self._handle_edit_due_date_input("")
            return

        if not command_str:
            return

        # Check if we're waiting for specific input
        if self._awaiting_role_name:
            self._handle_role_name_input(command_str)
            return

        if self._awaiting_task_title:
            self._handle_task_title_input(command_str)
            return

        if self._awaiting_task_due_date:
            self._handle_task_due_date_input(command_str)
            return

        if self._awaiting_delete_confirmation:
            self._handle_delete_confirmation(command_str)
            return

        if self._awaiting_edit_title:
            self._handle_edit_title_input(command_str)
            return

        if self._awaiting_edit_due_date:
            self._handle_edit_due_date_input(command_str)
            return

        # Add to history
        self.command_input.add_to_history(command_str)

        # Parse and handle command
        self.handle_command(command_str)

    def handle_command(self, command_str: str) -> None:
        """Handle a command.

        Args:
            command_str: Command string to handle
        """
        command, args = parser.parse(command_str)
        parts = args.get("parts", [])

        # Exit command
        if command == "exit":
            self.exit()
            return

        # Help command
        elif command == "help":
            self.show_help()
            return

        # New role command
        elif command == "new" and parts and parts[0] == "role":
            self.create_new_role()
            return

        # Role selection (r1, r2, etc.)
        elif command.startswith("r") and len(command) > 1:
            try:
                role_num = int(command[1:])
                self.select_role(role_num)
            except ValueError:
                self.show_error(f"Invalid role number: {command}")
            return

        # Add task command
        elif command == "add":
            if not self.active_role_id:
                self.show_error(
                    "No role selected. Use 'r1' to select a role or 'new role' to create one."
                )
            else:
                self.create_new_task()
            return

        # Task commands (t1 view, t2 edit, t3 delete, t4 doing, etc.)
        elif command == "task":
            self.handle_task_command(args)
            return

        # Undo command
        elif command == "undo":
            self.undo_last_deletion()
            return

        # Empty command
        elif command == "empty":
            pass

        # Unknown command
        else:
            self.show_error(
                f"Unknown command: {command_str}\n\nType 'help' for available commands."
            )

    def show_help(self) -> None:
        """Display help information."""
        help_text = """
Terminal Todo - Help

Role Management:
  new role             Create a new role (interactive prompts)
  r[number]            Select a role (e.g., r1, r2)

Task Management:
  add                  Add a task to the active role (interactive prompts)
  t[number] view       View full task details (e.g., t1 view)
  t[number] edit       Edit a task (e.g., t2 edit)
  t[number] delete     Delete a task (e.g., t3 delete)
  t[number] doing      Mark task as in progress (e.g., t4 doing)
  t[number] done       Mark task as completed (e.g., t5 done)
  t[number] todo       Mark task as to-do (e.g., t6 todo)

Utility:
  undo                 Undo last deletion
  help                 Show this help message
  exit                 Exit the application (or press Ctrl+C)

Keyboard Shortcuts:
  Ctrl+C               Quit application
  Esc                  Clear command input

Status: Iteration 3 - Task Lifecycle Management
"""
        self.update_content(help_text)

    def create_new_role(self) -> None:
        """Create a new role with prompted input."""
        # For Iteration 2, use simple approach - show instruction, then wait for input
        self.update_content(
            "Creating new role...\n\nEnter role name in the command box below:"
        )
        self.command_input.placeholder = "Enter role name..."
        self._awaiting_role_name = True

    def _handle_role_name_input(self, role_name: str) -> None:
        """Handle role name input.

        Args:
            role_name: The role name entered by user
        """
        self._awaiting_role_name = False
        self.command_input.placeholder = "Type a command... (type 'help' for commands)"

        if not role_name or not role_name.strip():
            self.show_error("Role name cannot be empty")
            return

        # Auto-assign next color
        color_index = role_commands.get_next_color_index()
        color = get_role_color(color_index)

        # Create role
        role_id = role_commands.create_role(role_name, color)

        if role_id:
            # Automatically select the new role
            role = role_commands.get_role_by_id(role_id)
            self.active_role_id = role_id
            self.display_role_panel(role)
        else:
            self.show_error("Failed to create role")

    def select_role(self, display_number: int) -> None:
        """Select a role by display number.

        Args:
            display_number: Role display number (1, 2, 3, etc.)
        """
        role = role_commands.get_role_by_number(display_number)

        if not role:
            self.show_error(f"Role r{display_number} not found")
            return

        self.active_role_id = role["id"]
        self.display_role_panel(role)

    def display_role_panel(self, role) -> None:
        """Display a role panel in the main content area.

        Args:
            role: Role database row
        """
        # Create or update role panel
        panel = RolePanel(
            role_id=role["id"],
            role_name=role["name"],
            display_number=role["display_number"],
            color=role["color"],
            is_active=True,
        )

        self.current_panel = panel
        self.main_content.update(panel.render())

    def refresh_current_panel(self) -> None:
        """Refresh the currently displayed panel."""
        if self.current_panel:
            self.main_content.update(self.current_panel.render())

    def create_new_task(self) -> None:
        """Start task creation process."""
        if not self.active_role_id:
            self.show_error("No active role selected")
            return

        self.update_content(
            "Creating new task...\n\nEnter task title in the command box below:"
        )
        self.command_input.placeholder = "Enter task title..."
        self._awaiting_task_title = True

    def _handle_task_title_input(self, title: str) -> None:
        """Handle task title input.

        Args:
            title: Task title
        """
        self._awaiting_task_title = False
        self.command_input.placeholder = "Due date (or press Enter to skip)..."

        if not title or not title.strip():
            self.show_error("Task title cannot be empty")
            self.command_input.placeholder = (
                "Type a command... (type 'help' for commands)"
            )
            return

        self._pending_task_title = title
        self._awaiting_task_due_date = True
        self.update_content(
            f"Task title: {title}\n\nEnter due date (optional, press Enter to skip):\nFormats: 'tomorrow', 'today', 'DD MM YY', or '+3d'"
        )

    def _handle_task_due_date_input(self, due_date_str: str) -> None:
        """Handle task due date input.

        Args:
            due_date_str: Due date string
        """
        self._awaiting_task_due_date = False
        self.command_input.placeholder = "Type a command... (type 'help' for commands)"

        # Create task
        task_id = task_commands.create_task(
            role_id=self.active_role_id,
            title=self._pending_task_title,
            due_date=due_date_str if due_date_str.strip() else None,
        )

        if task_id:
            self.refresh_current_panel()
        else:
            self.show_error("Failed to create task")

        # Clean up
        self._pending_task_title = None

    def show_error(self, message: str) -> None:
        """Show an error message.

        Args:
            message: Error message to display
        """
        self.update_content(f"[red]Error:[/red] {message}")

    def show_success(self, message: str) -> None:
        """Show a success message.

        Args:
            message: Success message to display
        """
        self.update_content(f"[green]Success:[/green] {message}")

    def update_content(self, text: str) -> None:
        """Update main content area.

        Args:
            text: Text to display
        """
        self.main_content.update(text)

    def handle_task_command(self, args: dict) -> None:
        """Handle task-related commands.

        Args:
            args: Parsed command arguments containing task_number and action
        """
        if not self.active_role_id:
            self.show_error("No role selected. Select a role first.")
            return

        task_number = args.get("task_number")
        action = args.get("action")

        if not action:
            self.show_error(f"No action specified for task t{task_number}. Try 't{task_number} view'")
            return

        # Get the task
        task = task_commands.get_task_by_number(self.active_role_id, task_number)
        if not task:
            self.show_error(f"Task t{task_number} not found in the active role")
            return

        # Handle different actions
        if action == "view":
            self.view_task(task)
        elif action in ("doing", "done", "todo"):
            self.update_task_status(task, action)
        elif action == "delete":
            self.delete_task(task)
        elif action == "edit":
            self.edit_task(task)
        else:
            self.show_error(f"Unknown action: {action}")

    def view_task(self, task) -> None:
        """View task details.

        Args:
            task: Task database row
        """
        # Get role info for display
        role = role_commands.get_role_by_id(self.active_role_id)
        if not role:
            self.show_error("Role not found")
            return

        # Render task detail view
        detail_panel = render_task_detail(task, role['name'], role['color'])
        self.main_content.update(detail_panel)

        # Set state flag
        self._in_task_detail_view = True
        self.command_input.placeholder = "Press Enter to return to role view..."

    def _exit_task_detail_view(self) -> None:
        """Exit task detail view and return to role panel."""
        self._in_task_detail_view = False
        self.command_input.placeholder = "Type a command... (type 'help' for commands)"

        # Refresh the current panel
        if self.active_role_id:
            role = role_commands.get_role_by_id(self.active_role_id)
            if role:
                self.display_role_panel(role)

    def update_task_status(self, task, status: str) -> None:
        """Update task status.

        Args:
            task: Task database row
            status: New status (doing/done/todo)
        """
        success = task_commands.update_task_status(task['id'], status)
        if success:
            self.refresh_current_panel()
        else:
            self.show_error(f"Failed to update task status to {status}")

    def delete_task(self, task) -> None:
        """Delete a task with confirmation.

        Args:
            task: Task database row
        """
        self._pending_delete_task = task
        self._awaiting_delete_confirmation = True

        # Show confirmation prompt
        task_title = task['title']
        task_num = task['task_number']
        self.update_content(
            f"Are you sure you want to delete task t{task_num}?\n"
            f"'{task_title}'\n\n"
            f"Type 'yes' to confirm or 'no' to cancel:"
        )
        self.command_input.placeholder = "yes or no?"

    def _handle_delete_confirmation(self, response: str) -> None:
        """Handle delete confirmation response.

        Args:
            response: User's response (yes/no)
        """
        self._awaiting_delete_confirmation = False
        self.command_input.placeholder = "Type a command... (type 'help' for commands)"

        response = response.strip().lower()

        if response == 'yes':
            # Delete the task
            task = self._pending_delete_task
            task_commands.delete_task(task['id'], save_to_undo=True)

            # Show success message
            self.show_success(f"Task t{task['task_number']} deleted. Use 'undo' to restore.")

            # Refresh panel
            self.refresh_current_panel()
        else:
            # Cancelled
            self.show_success("Delete cancelled")
            self.refresh_current_panel()

        # Clean up
        self._pending_delete_task = None

    def undo_last_deletion(self) -> None:
        """Undo the last deleted task."""
        restored_task = task_commands.undo_last_deletion()

        if restored_task:
            task_num = restored_task['task_number']
            task_title = restored_task['title']
            self.show_success(f"Restored task t{task_num}: '{task_title}'")

            # Refresh panel if restored task belongs to active role
            if self.active_role_id == restored_task['role_id']:
                self.refresh_current_panel()
        else:
            self.show_error("No deletions to undo")

    def edit_task(self, task) -> None:
        """Edit a task with pre-filled values.

        Args:
            task: Task database row
        """
        self._pending_edit_task = task
        self._awaiting_edit_title = True

        # Show current values and prompt
        current_title = task['title']
        current_due_date = task['due_date']
        due_date_display = f" (current: {current_due_date})" if current_due_date else " (no due date set)"

        self.update_content(
            f"Editing task t{task['task_number']}\n\n"
            f"Current title: {current_title}\n"
            f"Enter new title (or press Enter to keep current):"
        )
        self.command_input.placeholder = "New title or Enter to skip..."

    def _handle_edit_title_input(self, title: str) -> None:
        """Handle edit title input.

        Args:
            title: New task title (empty to keep current)
        """
        self._awaiting_edit_title = False

        # Use new title if provided, otherwise keep current
        task = self._pending_edit_task
        new_title = title.strip() if title.strip() else None

        # Move to due date prompt
        current_due_date = task['due_date']
        due_date_display = current_due_date if current_due_date else "none"

        self.update_content(
            f"Current due date: {due_date_display}\n"
            f"Enter new due date (or press Enter to keep current):\n"
            f"Formats: 'tomorrow', 'today', 'DD MM YY', or '+3d'\n"
            f"Type 'clear' to remove due date"
        )
        self.command_input.placeholder = "New due date or Enter to skip..."
        self._awaiting_edit_due_date = True

        # Store the new title temporarily
        if new_title:
            self._pending_task_title = new_title

    def _handle_edit_due_date_input(self, due_date_str: str) -> None:
        """Handle edit due date input.

        Args:
            due_date_str: New due date string (empty to keep current, 'clear' to remove)
        """
        self._awaiting_edit_due_date = False
        self.command_input.placeholder = "Type a command... (type 'help' for commands)"

        task = self._pending_edit_task
        new_title = self._pending_task_title if self._pending_task_title else task['title']

        # Determine new due date
        new_due_date = task['due_date']  # Default to current
        if due_date_str.strip().lower() == 'clear':
            new_due_date = ""  # Clear the due date
        elif due_date_str.strip():
            new_due_date = due_date_str.strip()
        # else: keep current (new_due_date already set)

        # Update the task
        success = task_commands.update_task(
            task_id=task['id'],
            title=new_title,
            due_date=new_due_date
        )

        if success:
            self.show_success(f"Task t{task['task_number']} updated")
            self.refresh_current_panel()
        else:
            self.show_error("Failed to update task")

        # Clean up
        self._pending_edit_task = None
        self._pending_task_title = None

    def action_clear_input(self) -> None:
        """Clear the command input."""
        self.command_input.value = ""

    def action_quit(self) -> None:
        """Quit the application."""
        db.close()
        self.exit()


def run():
    """Run the application."""
    app = TodoApp()
    app.run()


if __name__ == "__main__":
    run()
