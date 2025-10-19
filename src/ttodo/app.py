"""Main TUI application using Textual."""

from textual.app import App, ComposeResult
from textual.widgets import Input, Static, Header
from textual.containers import Container, Vertical
from textual.binding import Binding
from ttodo.commands.parser import parser
from ttodo.commands import role_commands, task_commands, window_commands
from ttodo.database.models import db
from ttodo.database.migrations import initialize_database
from ttodo.ui.panels import RolePanel
from ttodo.ui.task_detail import render_task_detail
from ttodo.ui.multi_panel_grid import MultiPanelGrid
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
        height: 3;
        dock: bottom;
        background: transparent;
        border: round #D4A574;
        padding: 0 1;
    }

    CommandInput {
        width: 100%;
        height: 1;
        border: none;
        background: transparent;
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
        Binding("tab", "focus_next_panel", "Next Panel", show=False),
    ]

    def __init__(self):
        super().__init__()
        self.main_content = None
        self.command_input = None
        self.input_container = None  # Container with border title
        self.active_role_id = None  # Currently selected role
        self.current_panel = None  # Currently displayed panel widget (single-panel mode)

        # Multi-panel window management
        self.multi_panel_grid = None  # MultiPanelGrid widget (multi-panel mode)
        self.in_multi_panel_mode = False  # Track if using multi-panel layout
        self._awaiting_window_role_selection = False  # Waiting for role selection for window
        self._pending_window_panel_count = 0  # Number of panels being configured
        self._pending_window_roles = []  # Roles selected for each panel
        self._current_window_panel_index = 0  # Current panel being configured

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

        # Input container at bottom with role label as border title
        self.input_container = Container(classes="input-container", id="input-container")
        with self.input_container:
            yield self.command_input

    def on_mount(self) -> None:
        """Called when app is mounted."""
        # Initialize database
        initialize_database()

        # Load saved window layout if exists
        layout = window_commands.load_window_layout()
        if layout:
            panel_count, panel_roles = layout
            self._create_multi_panel_layout(panel_count, panel_roles)

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

        if self._awaiting_window_role_selection:
            self._handle_window_role_selection(command_str)
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

        # Window command (window [count])
        elif command == "window":
            if parts and parts[0].isdigit():
                panel_count = int(parts[0])
                if 1 <= panel_count <= 8:
                    self.create_window_layout(panel_count)
                else:
                    self.show_error("Panel count must be between 1 and 8")
            else:
                self.show_error("Usage: window [1-8]")
            return

        # Close command (close current panel)
        elif command == "close":
            self.close_focused_panel()
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

Window Management:
  window [1-8]         Create multi-panel layout (e.g., window 2, window 4)
  close                Close currently focused panel
  Tab                  Switch focus between panels

Utility:
  undo                 Undo last deletion
  help                 Show this help message
  exit                 Exit the application (or press Ctrl+C)

Keyboard Shortcuts:
  Ctrl+C               Quit application
  Esc                  Clear command input
  Tab                  Focus next panel (in multi-panel mode)

Status: Iteration 4 - Window Management
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
            self.update_command_placeholder()
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
        self.update_command_placeholder()

        # Only display in single-panel mode
        if not self.in_multi_panel_mode:
            self.display_role_panel(role)

    def display_role_panel(self, role) -> None:
        """Display a role panel in the main content area (single-panel mode).

        Args:
            role: Role database row
        """
        # If in multi-panel mode, exit it first
        if self.in_multi_panel_mode and self.multi_panel_grid:
            self.multi_panel_grid.remove()
            self.multi_panel_grid = None
            self.in_multi_panel_mode = False

            # Create new MainContent static widget
            new_content = MainContent()
            self.main_content = new_content
            self.mount(new_content, before=0)

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
        if self.in_multi_panel_mode and self.multi_panel_grid:
            # Refresh focused panel in multi-panel mode
            self.multi_panel_grid.refresh_focused_panel()
        elif self.current_panel:
            # Refresh single panel
            self.main_content.update(self.current_panel.render())

    def refresh_panel_for_role(self, role_id: int) -> None:
        """Refresh the panel displaying a specific role.

        Args:
            role_id: The role ID to refresh
        """
        if self.in_multi_panel_mode and self.multi_panel_grid:
            # Find and refresh the panel with this role_id
            for panel_container in self.multi_panel_grid.panel_containers:
                if panel_container.role_id == role_id:
                    panel_container.refresh_panel()
                    break
        elif self.current_panel and self.active_role_id == role_id:
            # Refresh single panel if it matches
            self.main_content.update(self.current_panel.render())

    # Window Management Methods

    def update_command_placeholder(self) -> None:
        """Update role label to show active role."""
        if self.active_role_id and self.input_container:
            role = role_commands.get_role_by_id(self.active_role_id)
            if role:
                self.input_container.border_title = f"r{role['display_number']}"
                return

        # Clear label when no role is active
        if self.input_container:
            self.input_container.border_title = ""

    def create_window_layout(self, panel_count: int) -> None:
        """Start creating a multi-panel window layout.

        Args:
            panel_count: Number of panels (1-8)
        """
        self._pending_window_panel_count = panel_count
        self._pending_window_roles = []
        self._current_window_panel_index = 0
        self._awaiting_window_role_selection = True

        # Show role selection prompt
        self._show_window_role_prompt()

    def _show_window_role_prompt(self) -> None:
        """Show prompt for selecting role for current panel."""
        panel_num = self._current_window_panel_index + 1
        total = self._pending_window_panel_count

        # Get list of available roles
        roles = role_commands.get_all_roles()
        if not roles:
            self.show_error("No roles available. Create a role first with 'new role'")
            self._awaiting_window_role_selection = False
            return

        # Format roles list
        roles_text = "\n".join([f"  r{role['display_number']}: {role['name']}" for role in roles])

        prompt_text = f"""Setting up window layout ({panel_num}/{total})

Available roles:
{roles_text}

Enter role number for Panel {panel_num} (e.g., r1, r2):
Or press Enter to leave panel empty"""

        self.update_content(prompt_text)
        self.command_input.placeholder = f"Panel {panel_num} role (e.g., r1)..."

    def _handle_window_role_selection(self, input_str: str) -> None:
        """Handle role selection for window panel.

        Args:
            input_str: User input (e.g., "r1", "r2", or empty)
        """
        role_id = None

        # Parse role selection
        if input_str.strip():
            if input_str.lower().startswith('r'):
                try:
                    role_num = int(input_str[1:])
                    role = role_commands.get_role_by_number(role_num)
                    if role:
                        role_id = role["id"]
                    else:
                        self.show_error(f"Role r{role_num} not found. Try again.")
                        return
                except ValueError:
                    self.show_error(f"Invalid role number: {input_str}. Try again.")
                    return
            else:
                self.show_error(f"Invalid input: {input_str}. Use format 'r1', 'r2', etc.")
                return

        # Add role to pending list
        self._pending_window_roles.append(role_id)
        self._current_window_panel_index += 1

        # Check if we've configured all panels
        if self._current_window_panel_index >= self._pending_window_panel_count:
            # Create the layout
            self._create_multi_panel_layout(
                self._pending_window_panel_count,
                self._pending_window_roles
            )
            # Save to database
            window_commands.save_window_layout(
                self._pending_window_panel_count,
                self._pending_window_roles
            )
            # Reset state
            self._awaiting_window_role_selection = False
            self._pending_window_roles = []
            self._current_window_panel_index = 0
            self.command_input.placeholder = "Type a command... (type 'help' for commands)"
        else:
            # Show prompt for next panel
            self._show_window_role_prompt()

    def _create_multi_panel_layout(self, panel_count: int, panel_roles: list) -> None:
        """Create and display a multi-panel layout.

        Args:
            panel_count: Number of panels
            panel_roles: List of role IDs for each panel
        """
        # Create multi-panel grid
        self.multi_panel_grid = MultiPanelGrid(panel_count, panel_roles)
        self.in_multi_panel_mode = True

        # Remove old content and mount new grid
        if self.main_content:
            self.main_content.remove()

        self.main_content = self.multi_panel_grid
        self.mount(self.multi_panel_grid, before=0)

        # Set active role to first panel's role
        if panel_roles and panel_roles[0]:
            self.active_role_id = panel_roles[0]
            self.update_command_placeholder()

        # Don't show success message - it would replace the multi-panel grid
        # The panels themselves are the visual confirmation of success

    def close_focused_panel(self) -> None:
        """Close the currently focused panel and recalculate layout."""
        if not self.in_multi_panel_mode or not self.multi_panel_grid:
            self.show_error("Not in multi-panel mode. Use 'window [count]' to create layout.")
            return

        focused_index = self.multi_panel_grid.focused_panel_index

        # Remove panel from layout
        result = window_commands.remove_panel_from_layout(focused_index)

        if result is None:
            # No panels left, return to single-panel mode
            self.in_multi_panel_mode = False
            if self.multi_panel_grid:
                self.multi_panel_grid.remove()
            self.multi_panel_grid = None

            # Create new MainContent static widget
            new_content = MainContent()
            new_content.update("All panels closed.\n\nType 'window [count]' to create a new layout.")
            self.main_content = new_content
            self.mount(new_content, before=0)
        else:
            # Recreate layout with remaining panels
            panel_count, panel_roles = result
            self._create_multi_panel_layout(panel_count, panel_roles)
            # Don't show success - the updated layout is the visual confirmation

    def action_focus_next_panel(self) -> None:
        """Action handler for Tab key - focus next panel."""
        if self.in_multi_panel_mode and self.multi_panel_grid:
            new_index = self.multi_panel_grid.focus_next_panel()
            # Update active role to focused panel's role
            new_role_id = self.multi_panel_grid.get_focused_role_id()
            if new_role_id:
                self.active_role_id = new_role_id
                self.update_command_placeholder()
        # In single-panel mode, Tab does nothing (Textual default behavior)

    def create_new_task(self) -> None:
        """Start task creation process."""
        if not self.active_role_id:
            self.show_error("No active role selected")
            return

        self.command_input.placeholder = "Enter task title..."
        self._awaiting_task_title = True

        # Only update content in single-panel mode
        if not self.in_multi_panel_mode:
            self.update_content(
                "Creating new task...\n\nEnter task title in the command box below:"
            )

    def _handle_task_title_input(self, title: str) -> None:
        """Handle task title input.

        Args:
            title: Task title
        """
        self._awaiting_task_title = False

        if not title or not title.strip():
            self.show_error("Task title cannot be empty")
            self.command_input.placeholder = (
                "Type a command... (type 'help' for commands)"
            )
            return

        self._pending_task_title = title
        self._awaiting_task_due_date = True
        self.command_input.placeholder = "Due date (today/tomorrow/DD MM YY or Enter to skip)..."

        # Only update content in single-panel mode
        if not self.in_multi_panel_mode:
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
            # Refresh the panel for the role we just added a task to
            self.refresh_panel_for_role(self.active_role_id)
        else:
            self.show_error("Failed to create task")

        # Clean up
        self._pending_task_title = None

    def show_error(self, message: str) -> None:
        """Show an error message.

        Args:
            message: Error message to display
        """
        # Don't show messages in multi-panel mode - they would replace the grid
        if self.in_multi_panel_mode:
            return
        self.update_content(f"[red]Error:[/red] {message}")

    def show_success(self, message: str) -> None:
        """Show a success message.

        Args:
            message: Success message to display
        """
        # Don't show messages in multi-panel mode - they would replace the grid
        if self.in_multi_panel_mode:
            return
        self.update_content(f"[green]Success:[/green] {message}")

    def update_content(self, text: str) -> None:
        """Update main content area.

        Args:
            text: Text to display
        """
        # If in multi-panel mode, switch back to single-panel mode for messages
        if self.in_multi_panel_mode and isinstance(self.main_content, MultiPanelGrid):
            # Remove multi-panel grid
            self.main_content.remove()
            self.multi_panel_grid = None
            self.in_multi_panel_mode = False

            # Create new MainContent static widget
            new_content = MainContent()
            self.main_content = new_content
            self.mount(new_content, before=0)

        # Now update with text
        if hasattr(self.main_content, 'update'):
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
            # Refresh the panel for this task's role
            self.refresh_panel_for_role(task['role_id'])
        else:
            self.show_error(f"Failed to update task status to {status}")

    def delete_task(self, task) -> None:
        """Delete a task with confirmation.

        Args:
            task: Task database row
        """
        self._pending_delete_task = task
        self._awaiting_delete_confirmation = True

        # Show confirmation prompt in placeholder only (keeps layout intact)
        task_title = task['title']
        task_num = task['task_number']
        self.command_input.placeholder = f"Delete t{task_num} '{task_title}'? Type 'yes' or 'no'"

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

            # Refresh the panel for this task's role
            self.refresh_panel_for_role(task['role_id'])
        else:
            # Cancelled - just refresh to show task still there
            self.refresh_panel_for_role(self._pending_delete_task['role_id'])

        # Clean up
        self._pending_delete_task = None

    def undo_last_deletion(self) -> None:
        """Undo the last deleted task."""
        restored_task = task_commands.undo_last_deletion()

        if restored_task:
            # Refresh the panel for the restored task's role
            self.refresh_panel_for_role(restored_task['role_id'])
        else:
            self.show_error("No deletions to undo")

    def edit_task(self, task) -> None:
        """Edit a task with pre-filled values.

        Args:
            task: Task database row
        """
        self._pending_edit_task = task
        self._awaiting_edit_title = True

        # Show prompt in placeholder only (keeps layout intact)
        current_title = task['title']
        self.command_input.placeholder = f"Edit t{task['task_number']} title (current: '{current_title}') or Enter to skip..."

    def _handle_edit_title_input(self, title: str) -> None:
        """Handle edit title input.

        Args:
            title: New task title (empty to keep current)
        """
        self._awaiting_edit_title = False

        # Use new title if provided, otherwise keep current
        task = self._pending_edit_task
        new_title = title.strip() if title.strip() else None

        # Move to due date prompt (use placeholder only)
        current_due_date = task['due_date']
        due_date_display = current_due_date if current_due_date else "none"

        self.command_input.placeholder = f"Edit due date (current: {due_date_display}) - today/tomorrow/'clear'/Enter to skip..."
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
            # Refresh the panel for this task's role
            self.refresh_panel_for_role(task['role_id'])
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
