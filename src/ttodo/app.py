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
from ttodo.ui.multi_panel_grid import MultiPanelGrid
from ttodo.ui.kanban import KanbanBoard
from ttodo.utils.colors import ROLE_COLORS, get_role_color, get_active_color
from ttodo.utils.archive import ArchiveScheduler
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

    def _on_key(self, event) -> None:
        """Override to prevent Input from consuming Tab key."""
        # Let Tab pass through to app-level bindings - don't handle it at all
        if event.key == "tab":
            # Don't call prevent_default or stop - let it bubble up
            return
        # Let parent handle other keys
        super()._on_key(event)


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

    .kanban-board {
        width: 100%;
        height: 100%;
        background: transparent;
    }

    .kanban-column {
        width: 1fr;
        height: 100%;
        margin: 0 1;
    }
    """

    BINDINGS = [
        Binding("ctrl+c", "quit", "Quit", show=True),
        Binding("escape", "clear_input", "Clear", show=False),
        Binding("tab", "focus_next_panel", "Next Panel", show=False, priority=True),
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
        self._awaiting_task_priority = False
        self._awaiting_task_story_points = False
        self._awaiting_task_description = False
        self._awaiting_task_blocking_ids = False
        self._pending_task_title = None
        self._pending_task_due_date = None
        self._pending_task_priority = None
        self._pending_task_story_points = None
        self._pending_task_description = None
        self._awaiting_delete_confirmation = False
        self._pending_delete_task = None
        self._awaiting_batch_delete_confirmation = False
        self._pending_batch_delete_tasks = None
        self._awaiting_edit_title = False
        self._awaiting_edit_due_date = False
        self._awaiting_edit_priority = False
        self._awaiting_edit_story_points = False
        self._awaiting_edit_description = False
        self._awaiting_edit_blocking_ids = False
        self._pending_edit_task = None

        # Kanban view state
        self._in_kanban_view = False  # Track if we're in kanban view
        self._saved_window_layout = None  # Store window layout when entering kanban

        # Help view state
        self._in_help_view = False  # Track if we're in help view
        self._pre_help_state = None  # Store state before showing help

        # Navigation mode state
        self._in_navigation_mode = False  # Track if in navigation mode
        self._space_pressed = False  # Track if space is currently held down

        # Role remap state
        self._awaiting_role_remap = False  # Track if awaiting role remap input
        self._role_remap_roles = []  # List of roles to remap

        # Role delete state
        self._awaiting_role_delete_confirmation = False  # Track if awaiting delete confirmation
        self._pending_delete_role = None  # Role to be deleted

        # Archive scheduler for auto-archiving completed tasks
        self.archive_scheduler = ArchiveScheduler(interval_hours=1)

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

        # Start archive scheduler for automatic cleanup
        self.archive_scheduler.start()

        # Focus the input
        self.command_input.focus()

    def on_key(self, event) -> None:
        """Handle key presses for navigation mode and command history."""
        # Check if we're waiting for specific input - don't enter nav mode
        if (self._awaiting_role_name or self._awaiting_task_title or
            self._awaiting_task_due_date or self._awaiting_task_priority or
            self._awaiting_task_story_points or self._awaiting_task_description or
            self._awaiting_task_blocking_ids or
            self._awaiting_delete_confirmation or self._awaiting_batch_delete_confirmation or
            self._awaiting_edit_title or self._awaiting_edit_due_date or
            self._awaiting_edit_priority or self._awaiting_edit_story_points or
            self._awaiting_edit_description or self._awaiting_edit_blocking_ids or
            self._awaiting_window_role_selection or
            self._awaiting_role_remap or self._awaiting_role_delete_confirmation):
            # Allow normal text input
            return

        key = event.key

        # Tab key - let it pass through to the binding system for focus_next_panel
        if key == "tab":
            # Don't handle it here, let the binding system handle it
            return

        # Space key handling - track press/release for panel movement
        if key == "space":
            self._space_pressed = True
            if self._in_navigation_mode:
                # Consume space in nav mode to prevent it from going to input
                event.prevent_default()
                event.stop()
            return

        # Handle Escape - toggle to navigation mode
        if key == "escape":
            if self.command_input.value:
                # If there's text in input, ESC clears it (default behavior)
                return
            else:
                # Enter navigation mode
                if not self._in_navigation_mode:
                    self._enter_navigation_mode()
                    event.prevent_default()
                    event.stop()
                return

        # If in navigation mode, handle navigation keys
        if self._in_navigation_mode:
            handled = self._handle_navigation_key(key)
            if handled:
                event.prevent_default()
                event.stop()
                return

        # If in command mode, handle command history with arrow keys
        if not self._in_navigation_mode:
            if key == "up":
                self._command_history_up()
                event.prevent_default()
                event.stop()
                return
            elif key == "down":
                self._command_history_down()
                event.prevent_default()
                event.stop()
                return

        # Any letter key exits navigation mode and returns to command mode
        if self._in_navigation_mode and len(key) == 1 and key.isalpha():
            self._exit_navigation_mode()
            # Don't prevent default - allow the letter to go to input
            return

    def _enter_navigation_mode(self) -> None:
        """Enter navigation mode."""
        self._in_navigation_mode = True
        self._update_input_placeholder()
        # Blur the input so it doesn't capture keys
        self.set_focus(None)

    def _exit_navigation_mode(self) -> None:
        """Exit navigation mode and return to command mode."""
        self._in_navigation_mode = False
        self._space_pressed = False
        self._update_input_placeholder()
        # Focus the input
        self.command_input.focus()

    def _update_input_placeholder(self) -> None:
        """Update the input placeholder to show current mode."""
        if self._in_navigation_mode:
            self.command_input.placeholder = "(nav) - Use arrow keys to scroll, Space+Arrow to move panels, any letter to return to command mode"
        else:
            # Restore normal placeholder
            if self.active_role_id:
                role = role_commands.get_role(self.active_role_id)
                if role:
                    self.command_input.placeholder = f"r{role['display_number']} - Type a command... (type 'help' for commands)"
                else:
                    self.command_input.placeholder = "Type a command... (type 'help' for commands)"
            else:
                self.command_input.placeholder = "Type a command... (type 'help' for commands)"

    def _handle_navigation_key(self, key: str) -> bool:
        """Handle navigation keys when in navigation mode.

        Returns:
            True if key was handled, False otherwise
        """
        # Arrow keys for scrolling (without space) or movement (with space)
        if key in ("up", "down", "left", "right"):
            if self._space_pressed:
                # Space + Arrow = move panel position
                return self._move_panel(key)
            else:
                # Arrow alone = scroll focused panel
                return self._scroll_panel(key)

        return False

    def _scroll_panel(self, direction: str) -> bool:
        """Scroll the focused panel.

        Args:
            direction: One of "up", "down", "left", "right"

        Returns:
            True if scrolling was performed
        """
        # Get the focused panel
        if self.in_multi_panel_mode and self.multi_panel_grid:
            focused_panel = self.multi_panel_grid.get_focused_panel()
            if focused_panel and hasattr(focused_panel, 'scroll_relative'):
                if direction == "up":
                    focused_panel.scroll_relative(y=-1)
                    return True
                elif direction == "down":
                    focused_panel.scroll_relative(y=1)
                    return True
                elif direction == "left":
                    focused_panel.scroll_relative(x=-1)
                    return True
                elif direction == "right":
                    focused_panel.scroll_relative(x=1)
                    return True
        elif self.current_panel and hasattr(self.current_panel, 'scroll_relative'):
            # Single panel mode
            if direction == "up":
                self.current_panel.scroll_relative(y=-1)
                return True
            elif direction == "down":
                self.current_panel.scroll_relative(y=1)
                return True
            elif direction == "left":
                self.current_panel.scroll_relative(x=-1)
                return True
            elif direction == "right":
                self.current_panel.scroll_relative(x=1)
                return True

        return False

    def _move_panel(self, direction: str) -> bool:
        """Move the focused panel in the given direction (swap positions).

        Args:
            direction: One of "up", "down", "left", "right"

        Returns:
            True if panel was moved
        """
        if not self.in_multi_panel_mode or not self.multi_panel_grid:
            return False

        # Get current focused panel index
        focused_index = self.multi_panel_grid.focused_panel_index
        if focused_index is None:
            return False

        # Calculate target index based on direction and layout
        panel_count = len(self.multi_panel_grid.panel_containers)
        target_index = self._calculate_target_panel_index(focused_index, direction, panel_count)

        if target_index is None or target_index == focused_index:
            return False

        # Swap the panels
        self.multi_panel_grid.swap_panels(focused_index, target_index)

        # Update database with new layout
        panel_roles = [pc.role_id for pc in self.multi_panel_grid.panel_containers]
        window_commands.save_window_layout(panel_count, panel_roles)

        return True

    def _calculate_target_panel_index(self, current_index: int, direction: str, panel_count: int) -> int:
        """Calculate the target panel index based on direction and layout.

        Args:
            current_index: Current panel index
            direction: One of "up", "down", "left", "right"
            panel_count: Total number of panels

        Returns:
            Target panel index or None if no valid move
        """
        # Layout-specific logic based on panel_count
        # 1 panel: no movement
        if panel_count == 1:
            return None

        # 2 panels: left-right only
        if panel_count == 2:
            if direction == "left":
                return 0 if current_index == 1 else None
            elif direction == "right":
                return 1 if current_index == 0 else None
            return None

        # 3 panels: left (0) + right top (1) + right bottom (2)
        if panel_count == 3:
            if direction == "left":
                return 0 if current_index in (1, 2) else None
            elif direction == "right":
                return 1 if current_index == 0 else None
            elif direction == "up":
                return 1 if current_index == 2 else None
            elif direction == "down":
                return 2 if current_index == 1 else None
            return None

        # 4 panels: 2x2 grid - [0][1]
        #                       [2][3]
        if panel_count == 4:
            if direction == "left":
                return {1: 0, 3: 2}.get(current_index)
            elif direction == "right":
                return {0: 1, 2: 3}.get(current_index)
            elif direction == "up":
                return {2: 0, 3: 1}.get(current_index)
            elif direction == "down":
                return {0: 2, 1: 3}.get(current_index)
            return None

        # 5 panels: left (0) + right 3 stacked (1, 2, 3)
        if panel_count == 5:
            if direction == "left":
                return 0 if current_index in (1, 2, 3) else None
            elif direction == "right":
                return 1 if current_index == 0 else None
            elif direction == "up":
                if current_index == 2:
                    return 1
                elif current_index == 3:
                    return 2
            elif direction == "down":
                if current_index == 1:
                    return 2
                elif current_index == 2:
                    return 3
            return None

        # 6 panels: 2x3 grid - [0][1]
        #                       [2][3]
        #                       [4][5]
        if panel_count == 6:
            if direction == "left":
                return {1: 0, 3: 2, 5: 4}.get(current_index)
            elif direction == "right":
                return {0: 1, 2: 3, 4: 5}.get(current_index)
            elif direction == "up":
                return {2: 0, 3: 1, 4: 2, 5: 3}.get(current_index)
            elif direction == "down":
                return {0: 2, 1: 3, 2: 4, 3: 5}.get(current_index)
            return None

        # 7 panels: left 3 stacked (0, 1, 2) + right 4 stacked (3, 4, 5, 6)
        if panel_count == 7:
            if direction == "left":
                return 0 if current_index in (3, 4, 5, 6) else None
            elif direction == "right":
                return 3 if current_index in (0, 1, 2) else None
            elif direction == "up":
                if current_index in (1, 4):
                    return current_index - 1
                elif current_index in (2, 5):
                    return current_index - 1
                elif current_index == 6:
                    return 5
            elif direction == "down":
                if current_index in (0, 3):
                    return current_index + 1
                elif current_index in (1, 4):
                    return current_index + 1
                elif current_index == 5:
                    return 6
            return None

        # 8 panels: left 4 stacked (0, 1, 2, 3) + right 4 stacked (4, 5, 6, 7)
        if panel_count == 8:
            if direction == "left":
                return current_index - 4 if current_index in (4, 5, 6, 7) else None
            elif direction == "right":
                return current_index + 4 if current_index in (0, 1, 2, 3) else None
            elif direction == "up":
                if current_index in (1, 2, 3, 5, 6, 7):
                    return current_index - 1
            elif direction == "down":
                if current_index in (0, 1, 2, 4, 5, 6):
                    return current_index + 1
            return None

        return None

    def _command_history_up(self) -> None:
        """Navigate up in command history."""
        if self.command_input.command_history:
            if self.command_input.history_index > 0:
                self.command_input.history_index -= 1
                self.command_input.value = self.command_input.command_history[self.command_input.history_index]

    def _command_history_down(self) -> None:
        """Navigate down in command history."""
        if self.command_input.command_history:
            if self.command_input.history_index < len(self.command_input.command_history) - 1:
                self.command_input.history_index += 1
                self.command_input.value = self.command_input.command_history[self.command_input.history_index]
            else:
                # At the end of history, clear input
                self.command_input.history_index = len(self.command_input.command_history)
                self.command_input.value = ""

    def on_input_submitted(self, event: Input.Submitted) -> None:
        """Handle command submission."""
        command_str = event.value.strip()

        # Clear input first
        self.command_input.value = ""

        if not command_str and (self._awaiting_task_due_date):
            # Allow empty input for skipping due date
            self._handle_task_due_date_input("")
            return

        if not command_str and (self._awaiting_task_priority):
            # Allow empty input for skipping priority
            self._handle_task_priority_input("")
            return

        if not command_str and (self._awaiting_task_story_points):
            # Allow empty input for skipping story points
            self._handle_task_story_points_input("")
            return

        if not command_str and (self._awaiting_task_description):
            # Allow empty input for skipping description
            self._handle_task_description_input("")
            return

        if not command_str and (self._awaiting_task_blocking_ids):
            # Allow empty input for skipping blocking IDs
            self._handle_task_blocking_ids_input("")
            return

        if not command_str and (self._awaiting_edit_title):
            # Allow empty input to keep current title
            self._handle_edit_title_input("")
            return

        if not command_str and (self._awaiting_edit_due_date):
            # Allow empty input to keep current due date
            self._handle_edit_due_date_input("")
            return

        if not command_str and (self._awaiting_edit_priority):
            # Allow empty input to keep current priority
            self._handle_edit_priority_input("")
            return

        if not command_str and (self._awaiting_edit_story_points):
            # Allow empty input to keep current story points
            self._handle_edit_story_points_input("")
            return

        if not command_str and (self._awaiting_edit_description):
            # Allow empty input to keep current description
            self._handle_edit_description_input("")
            return

        if not command_str and (self._awaiting_edit_blocking_ids):
            # Allow empty input to keep current blocking IDs
            self._handle_edit_blocking_ids_input("")
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

        if self._awaiting_task_priority:
            self._handle_task_priority_input(command_str)
            return

        if self._awaiting_task_story_points:
            self._handle_task_story_points_input(command_str)
            return

        if self._awaiting_task_description:
            self._handle_task_description_input(command_str)
            return

        if self._awaiting_task_blocking_ids:
            self._handle_task_blocking_ids_input(command_str)
            return

        if self._awaiting_delete_confirmation:
            self._handle_delete_confirmation(command_str)
            return

        if self._awaiting_batch_delete_confirmation:
            self._handle_batch_delete_confirmation(command_str)
            return

        if self._awaiting_edit_title:
            self._handle_edit_title_input(command_str)
            return

        if self._awaiting_edit_due_date:
            self._handle_edit_due_date_input(command_str)
            return

        if self._awaiting_edit_priority:
            self._handle_edit_priority_input(command_str)
            return

        if self._awaiting_edit_story_points:
            self._handle_edit_story_points_input(command_str)
            return

        if self._awaiting_edit_description:
            self._handle_edit_description_input(command_str)
            return

        if self._awaiting_edit_blocking_ids:
            self._handle_edit_blocking_ids_input(command_str)
            return

        if self._awaiting_window_role_selection:
            self._handle_window_role_selection(command_str)
            return

        if self._awaiting_role_remap:
            self._handle_role_remap_input(command_str)
            return

        if self._awaiting_role_delete_confirmation:
            self._handle_role_delete_confirmation(command_str)
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
            self.action_quit()
            return

        # Help command
        elif command == "help":
            self.show_help()
            return

        # New role command
        elif command == "new" and parts and parts[0] == "role":
            self.create_new_role()
            return

        # Role remap command
        elif command == "role" and parts and parts[0] == "remap":
            self.start_role_remap()
            return

        # Delete command (role or task)
        elif command == "delete":
            self.start_delete_command()
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
                # Check if quick add syntax is used
                raw_command = args.get("raw", "")
                if parts:
                    self.quick_add_task(raw_command)
                else:
                    self.create_new_task()
            return

        # Task commands (t1 view, t2 edit, t3 delete, t4 doing, etc.)
        elif command == "task":
            self.handle_task_command(args)
            return

        # Batch task commands (t1,t3,t5 delete, t2,t4 doing, etc.)
        elif command == "batch_task":
            self.handle_batch_task_command(args)
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

        # Kanban view command
        elif command == "k":
            self.enter_kanban_view()
            return

        # Return to previous view command (also handles 'r' without number)
        elif command == "r" and not args.get("parts"):
            # Priority: Exit help view, then exit kanban view
            if self._in_help_view:
                self.exit_help_view()
            elif self._in_kanban_view:
                self.exit_kanban_view()
            else:
                self.show_error("Already in default view. Use 'k' for kanban or 'help' for help.")
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
        # Save current state before showing help
        if not self._in_help_view:
            self._pre_help_state = {
                'in_kanban_view': self._in_kanban_view,
                'in_multi_panel_mode': self.in_multi_panel_mode,
                'active_role_id': self.active_role_id,
                'current_panel': self.current_panel,
                'multi_panel_grid': self.multi_panel_grid,
                'saved_window_layout': self._saved_window_layout
            }
            self._in_help_view = True

        help_text = """
Terminal Todo - Help

Role Management:
  new role             Create a new role (interactive prompts)
  r[number]            Select a role (e.g., r1, r2)
  role remap           Reassign role numbers
  delete               Delete the currently active role (must have no tasks)

Task Management:
  add                  Add a task to the active role (interactive prompts)
  t[number] edit       Edit a task (e.g., t2 edit)
  t[number] delete     Delete a task (e.g., t3 delete)
  t[number] doing      Mark task as in progress (e.g., t4 doing)
  t[number] done       Mark task as completed (e.g., t5 done)
  t[number] todo       Mark task as to-do (e.g., t6 todo)

View Modes:
  k                    Switch to kanban board view (TODO | DOING | DONE columns)
  r                    Return to previous view (from help or kanban)

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
  Esc                  Enter navigation mode (when input is empty)
  Tab                  Focus next panel (in multi-panel mode)
  Arrow keys           Command history (cmd mode) or scroll panel (nav mode)
  Space+Arrow          Move panel position (in navigation mode)
  Any letter           Exit navigation mode and return to command mode

Status: Iteration 6 - Navigation Mode & Role Management

Press 'r' to return to previous view
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

    def start_role_remap(self) -> None:
        """Start the role remap process."""
        roles = role_commands.get_all_roles()
        if not roles:
            self.show_error("No roles to remap")
            return

        # Store roles for remapping
        self._role_remap_roles = roles

        # Build the remap display
        remap_text = "Role Remap - Enter new numbers for roles\n\n"
        remap_text += "Current mapping:\n"
        for role in roles:
            remap_text += f"  {role['display_number']}: {role['name']}\n"
        remap_text += "\nEnter new mapping as: role_name:new_number\n"
        remap_text += "Example: Work:3  or  Personal:1\n"
        remap_text += "(Press Enter with empty input to cancel)\n"

        self.update_content(remap_text)
        self.command_input.placeholder = "Enter role:number (e.g., Work:3) or press Enter to finish..."
        self._awaiting_role_remap = True

    def _handle_role_remap_input(self, input_str: str) -> None:
        """Handle role remap input.

        Args:
            input_str: Input string in format "role_name:new_number"
        """
        if not input_str or not input_str.strip():
            # Empty input means we're done remapping
            self._finish_role_remap()
            return

        # Parse input (role_name:new_number)
        parts = input_str.strip().split(":")
        if len(parts) != 2:
            self.show_error("Invalid format. Use: role_name:new_number (e.g., Work:3)")
            return

        role_name = parts[0].strip()
        try:
            new_number = int(parts[1].strip())
        except ValueError:
            self.show_error(f"Invalid number: {parts[1]}")
            return

        # Find the role
        role = None
        for r in self._role_remap_roles:
            if r['name'].lower() == role_name.lower():
                role = r
                break

        if not role:
            self.show_error(f"Role not found: {role_name}")
            return

        # Check if new number is already taken
        for r in self._role_remap_roles:
            if r['display_number'] == new_number and r['id'] != role['id']:
                self.show_error(f"Number {new_number} is already assigned to {r['name']}")
                return

        # Update the role's display number in our temporary list
        role['display_number'] = new_number

        # Show updated mapping
        remap_text = "Role Remap - Enter new numbers for roles\n\n"
        remap_text += "Current mapping:\n"
        for r in sorted(self._role_remap_roles, key=lambda x: x['display_number']):
            remap_text += f"  {r['display_number']}: {r['name']}\n"
        remap_text += "\nEnter new mapping as: role_name:new_number\n"
        remap_text += "Example: Work:3  or  Personal:1\n"
        remap_text += "(Press Enter with empty input to finish and save)\n"

        self.update_content(remap_text)

    def _finish_role_remap(self) -> None:
        """Finish role remapping and save to database."""
        self._awaiting_role_remap = False
        self.command_input.placeholder = "Type a command... (type 'help' for commands)"

        if not self._role_remap_roles:
            return

        # Build mapping dict
        role_mappings = {role['id']: role['display_number'] for role in self._role_remap_roles}

        # Save to database
        success = role_commands.remap_role_numbers(role_mappings)

        if success:
            # Refresh all panels to show updated numbers
            if self.in_multi_panel_mode and self.multi_panel_grid:
                self.multi_panel_grid.refresh_all_panels()
            elif self.active_role_id:
                role = role_commands.get_role(self.active_role_id)
                if role:
                    self.display_role_panel(role)
            else:
                self.update_content("Welcome to Terminal Todo!\n\nType 'new role' to get started.")

            # Update placeholder to reflect new numbers
            self.update_command_placeholder()
        else:
            self.show_error("Failed to remap roles")

        # Clean up
        self._role_remap_roles = []

    def start_delete_command(self) -> None:
        """Start the delete command (role or task)."""
        if not self.active_role_id:
            self.show_error("No active role selected")
            return

        # Get the active role
        role = role_commands.get_role(self.active_role_id)
        if not role:
            self.show_error("Active role not found")
            return

        # Check if role has tasks
        if role_commands.role_has_tasks(self.active_role_id):
            self.show_error(
                f"Cannot delete role '{role['name']}'. "
                "It has active tasks. Please delete or move tasks first."
            )
            return

        # Ask for confirmation
        self._pending_delete_role = role
        self._awaiting_role_delete_confirmation = True
        self.command_input.placeholder = f"Delete role '{role['name']}'? (yes/no)..."

        # Show confirmation in content area
        if not self.in_multi_panel_mode:
            self.update_content(
                f"Are you sure you want to delete role '{role['name']}'?\n\n"
                f"Type 'yes' to confirm or 'no' to cancel."
            )

    def _handle_role_delete_confirmation(self, response: str) -> None:
        """Handle role delete confirmation.

        Args:
            response: User response (yes/no)
        """
        self._awaiting_role_delete_confirmation = False
        self.command_input.placeholder = "Type a command... (type 'help' for commands)"

        if not self._pending_delete_role:
            return

        role = self._pending_delete_role
        self._pending_delete_role = None

        if response.lower() == "yes":
            # Save to undo stack
            import json
            role_data = {
                'type': 'role',
                'role_id': role['id'],
                'display_number': role['display_number'],
                'name': role['name'],
                'color': role['color']
            }
            db.execute(
                "INSERT INTO undo_stack (action_type, data) VALUES (?, ?)",
                ('delete_role', json.dumps(role_data))
            )
            db.commit()

            # Delete the role
            success = role_commands.delete_role(role['id'])

            if success:
                # Clear active role if it was the deleted one
                if self.active_role_id == role['id']:
                    self.active_role_id = None
                    self.update_command_placeholder()

                # Close any panels showing this role
                if self.in_multi_panel_mode and self.multi_panel_grid:
                    # Refresh all panels (will show empty for deleted role)
                    self.multi_panel_grid.refresh_all_panels()
                else:
                    self.update_content("Welcome to Terminal Todo!\n\nType 'new role' to get started.")

                # Show success message (briefly, then restore view)
                # For now, just show in status or brief message
            else:
                self.show_error("Failed to delete role")
        else:
            # Cancelled - restore previous view
            if not self.in_multi_panel_mode:
                if self.active_role_id:
                    role = role_commands.get_role(self.active_role_id)
                    if role:
                        self.display_role_panel(role)
                else:
                    self.update_content("Welcome to Terminal Todo!\n\nType 'new role' to get started.")

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

        # If in kanban view, switch to this role's kanban
        if self._in_kanban_view:
            self._switch_kanban_role(role)
        # Only display in single-panel mode
        elif not self.in_multi_panel_mode:
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
        elif self._in_kanban_view and self.current_panel:
            # Refresh kanban board if it's a KanbanBoard instance
            if isinstance(self.current_panel, KanbanBoard) and self.current_panel.role_id == role_id:
                self.current_panel.refresh_columns()
        elif self.current_panel and self.active_role_id == role_id:
            # Refresh single panel if it matches
            self.main_content.update(self.current_panel.render())

    # Kanban View Methods

    def enter_kanban_view(self) -> None:
        """Switch to kanban board view for the active role."""
        if not self.active_role_id:
            self.show_error("No role selected. Use 'r1' to select a role first.")
            return

        # Get role details
        role = role_commands.get_role_by_id(self.active_role_id)
        if not role:
            self.show_error("Active role not found.")
            return

        # Store current window layout if in multi-panel mode
        if self.in_multi_panel_mode:
            # Save current multi-panel state to restore later
            self._saved_window_layout = {
                'panel_count': len(self.multi_panel_grid.panel_containers) if self.multi_panel_grid else 0,
                'panel_roles': [pc.role_id for pc in self.multi_panel_grid.panel_containers] if self.multi_panel_grid else []
            }
            # Remove multi-panel grid
            if self.multi_panel_grid:
                self.multi_panel_grid.remove()

            # Create new MainContent static widget
            new_content = MainContent()
            self.main_content = new_content
            self.mount(new_content, before=0)

            self.multi_panel_grid = None
            self.in_multi_panel_mode = False
        else:
            # In single-panel mode, just clear content
            if hasattr(self.current_panel, 'remove') and self.current_panel:
                self.current_panel.remove()

        # Create and mount kanban board
        kanban_board = KanbanBoard(
            role_id=role['id'],
            role_name=role['name'],
            display_number=role['display_number'],
            color=role['color']
        )

        # Update state
        self._in_kanban_view = True
        self.current_panel = kanban_board

        # Mount kanban board in main content container
        self.main_content.mount(kanban_board)

    def exit_kanban_view(self) -> None:
        """Return to window layout from kanban view."""
        if not self._in_kanban_view:
            return

        # Remove kanban board
        if self.current_panel:
            self.current_panel.remove()
            self.current_panel = None

        # Update state
        self._in_kanban_view = False

        # Restore saved window layout
        if self._saved_window_layout and self._saved_window_layout['panel_count'] > 0:
            panel_count = self._saved_window_layout['panel_count']
            panel_roles = self._saved_window_layout['panel_roles']
            self._create_multi_panel_layout(panel_count, panel_roles)
            self._saved_window_layout = None
        else:
            # No saved layout, check if there's a default layout in database
            layout = window_commands.load_window_layout()
            if layout:
                panel_count, panel_roles = layout
                self._create_multi_panel_layout(panel_count, panel_roles)
            else:
                # No layout at all, show welcome message
                self.main_content.update("Welcome to Terminal Todo!\n\nType 'window 2' to create a window layout, or 'help' for commands.")

    def _switch_kanban_role(self, role) -> None:
        """Switch to a different role's kanban board while staying in kanban view.

        Args:
            role: Role database row to switch to
        """
        # Remove current kanban board
        if self.current_panel:
            self.current_panel.remove()

        # Create new kanban board for the selected role
        kanban_board = KanbanBoard(
            role_id=role['id'],
            role_name=role['name'],
            display_number=role['display_number'],
            color=role['color']
        )

        # Update current panel reference
        self.current_panel = kanban_board

        # Mount new kanban board
        self.main_content.mount(kanban_board)

    # Help View Methods

    def exit_help_view(self) -> None:
        """Return to the view that was active before help was displayed."""
        if not self._in_help_view or not self._pre_help_state:
            return

        # Clear help state
        self._in_help_view = False
        state = self._pre_help_state
        self._pre_help_state = None

        # Restore previous view based on saved state
        if state['in_kanban_view']:
            # Restore kanban view
            self._in_kanban_view = True
            self.current_panel = state['current_panel']
            self._saved_window_layout = state['saved_window_layout']

            # Get role for kanban board
            if self.active_role_id:
                role = role_commands.get_role_by_id(self.active_role_id)
                if role:
                    # Create fresh kanban board
                    kanban_board = KanbanBoard(
                        role_id=role['id'],
                        role_name=role['name'],
                        display_number=role['display_number'],
                        color=role['color']
                    )
                    self.current_panel = kanban_board
                    self.main_content.mount(kanban_board)
        elif state['in_multi_panel_mode'] and state['multi_panel_grid']:
            # Restore multi-panel layout
            self.in_multi_panel_mode = True
            self.multi_panel_grid = state['multi_panel_grid']

            # Load layout from database and recreate
            layout = window_commands.load_window_layout()
            if layout:
                panel_count, panel_roles = layout
                self._create_multi_panel_layout(panel_count, panel_roles)
        else:
            # Restore single panel view
            if self.active_role_id:
                role = role_commands.get_role_by_id(self.active_role_id)
                if role:
                    self.display_role_panel(role)
            else:
                self.main_content.update("Welcome to Terminal Todo!\n\nType 'window 2' to create a window layout, or 'help' for commands.")

    # Window Management Methods

    def update_command_placeholder(self) -> None:
        """Update role label and border color to show active role."""
        if self.active_role_id and self.input_container:
            role = role_commands.get_role_by_id(self.active_role_id)
            if role:
                self.input_container.border_title = f"r{role['display_number']}"
                # Update border color to match focused panel's role color (brightened)
                border_color = get_active_color(role['color'])
                # Update both border style and color
                self.input_container.styles.border = ("round", border_color)
                self.input_container.border_subtitle = f"Focus: {role['name']}"  # Debug
                return

        # Clear label when no role is active - restore default border color
        if self.input_container:
            self.input_container.border_title = ""
            self.input_container.styles.border = ("round", "#D4A574")
            self.input_container.border_subtitle = ""  # Debug

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
                self._update_input_placeholder()
                self.update_command_placeholder()
        # In single-panel mode, Tab does nothing

    def create_new_task(self) -> None:
        """Start task creation process."""
        if not self.active_role_id:
            self.show_error("No active role selected")
            return

        self.command_input.placeholder = "Enter task title..."
        self._awaiting_task_title = True

        # Only update content in single-panel mode (not in multi-panel or kanban)
        if not self.in_multi_panel_mode and not self._in_kanban_view:
            self.update_content(
                "Creating new task...\n\nEnter task title in the command box below:"
            )

    def quick_add_task(self, command_str: str) -> None:
        """Parse and create task using quick add syntax.

        Syntax: add "Task title" [DD MM YY] [Priority] [StoryPoints] [BlockedBy:t1,t3]

        Args:
            command_str: Full command string
        """
        import re

        # Extract quoted title
        title_match = re.search(r'"([^"]+)"', command_str)
        if not title_match:
            self.show_error("Quick add requires quoted title: add \"Task title\"")
            return

        title = title_match.group(1)

        # Get the rest after the title
        rest = command_str[title_match.end():].strip()
        parts = rest.split() if rest else []

        # Parse optional parameters
        due_date = None
        priority = None
        story_points = None
        blocking_ids_str = None

        # Try to parse remaining parts
        i = 0
        while i < len(parts):
            part = parts[i]

            # Check for blocked by syntax: "BlockedBy:t1,t3" or "blockedby:1,3"
            if part.lower().startswith('blockedby:'):
                blocking_ids_str = part.split(':', 1)[1].replace('t', '')
                i += 1
                continue

            # Check for priority (High, Medium, Low)
            if part.capitalize() in ('High', 'Medium', 'Low'):
                priority = part.capitalize()
                i += 1
                continue

            # Check for story points (1, 2, 3, 5, 8, 13)
            if part.isdigit() and int(part) in (1, 2, 3, 5, 8, 13):
                story_points = int(part)
                i += 1
                continue

            # Check for date (DD MM YY - need 3 consecutive numeric parts)
            if i + 2 < len(parts) and parts[i].isdigit() and parts[i+1].isdigit() and parts[i+2].isdigit():
                due_date = f"{parts[i]} {parts[i+1]} {parts[i+2]}"
                i += 3
                continue

            # Unknown part - skip it
            i += 1

        # Validate blocking task IDs if provided
        blocking_task_ids = []
        if blocking_ids_str:
            valid_ids, error = task_commands.validate_blocking_task_ids(
                self.active_role_id, blocking_ids_str
            )
            if error:
                self.show_error(error)
                return
            blocking_task_ids = valid_ids

        # Create task
        task_id = task_commands.create_task(
            role_id=self.active_role_id,
            title=title,
            due_date=due_date,
            priority=priority,
            story_points=story_points
        )

        if task_id:
            # Add dependencies
            for blocking_id in blocking_task_ids:
                task_commands.add_task_dependency(blocking_id, task_id)

            # Refresh the panel
            self.refresh_panel_for_role(self.active_role_id)
        else:
            self.show_error("Failed to create task")

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

        # Only update content in single-panel mode (not in multi-panel or kanban)
        if not self.in_multi_panel_mode and not self._in_kanban_view:
            self.update_content(
                f"Task title: {title}\n\nEnter due date (optional, press Enter to skip):\nFormats: 'tomorrow', 'today', 'DD MM YY', or '+3d'"
            )

    def _handle_task_due_date_input(self, due_date_str: str) -> None:
        """Handle task due date input.

        Args:
            due_date_str: Due date string
        """
        self._awaiting_task_due_date = False
        self._pending_task_due_date = due_date_str if due_date_str.strip() else None

        # Now prompt for priority
        self._awaiting_task_priority = True
        self.command_input.placeholder = "Priority (High/Medium/Low or Enter to skip)..."

    def _handle_task_priority_input(self, priority_str: str) -> None:
        """Handle task priority input.

        Args:
            priority_str: Priority string (High/Medium/Low)
        """
        self._awaiting_task_priority = False

        # Validate priority if provided
        if priority_str.strip():
            priority_capitalized = priority_str.strip().capitalize()
            if priority_capitalized not in ('High', 'Medium', 'Low'):
                self.show_error("Invalid priority. Must be High, Medium, or Low.")
                # Clean up and restart
                self._pending_task_title = None
                self._pending_task_due_date = None
                self._pending_task_priority = None
                self.command_input.placeholder = "Type a command... (type 'help' for commands)"
                return
            self._pending_task_priority = priority_capitalized
        else:
            self._pending_task_priority = None

        # Now prompt for story points
        self._awaiting_task_story_points = True
        self.command_input.placeholder = "Story points (1/2/3/5/8/13 or Enter to skip)..."

    def _handle_task_story_points_input(self, story_points_str: str) -> None:
        """Handle task story points input.

        Args:
            story_points_str: Story points string
        """
        self._awaiting_task_story_points = False

        # Validate story points if provided
        if story_points_str.strip():
            try:
                sp = int(story_points_str.strip())
                if sp not in (1, 2, 3, 5, 8, 13):
                    self.show_error("Invalid story points. Must be 1, 2, 3, 5, 8, or 13.")
                    # Clean up and restart
                    self._pending_task_title = None
                    self._pending_task_due_date = None
                    self._pending_task_priority = None
                    self._pending_task_story_points = None
                    self.command_input.placeholder = "Type a command... (type 'help' for commands)"
                    return
                self._pending_task_story_points = sp
            except ValueError:
                self.show_error("Invalid story points. Must be a number: 1, 2, 3, 5, 8, or 13.")
                # Clean up and restart
                self._pending_task_title = None
                self._pending_task_due_date = None
                self._pending_task_priority = None
                self._pending_task_story_points = None
                self.command_input.placeholder = "Type a command... (type 'help' for commands)"
                return
        else:
            self._pending_task_story_points = None

        # Now prompt for description
        self._awaiting_task_description = True
        self.command_input.placeholder = "Description (or Enter to skip)..."

    def _handle_task_description_input(self, description_str: str) -> None:
        """Handle task description input.

        Args:
            description_str: Description string
        """
        self._awaiting_task_description = False
        self._pending_task_description = description_str if description_str.strip() else None

        # Now prompt for blocking task IDs
        self._awaiting_task_blocking_ids = True
        self.command_input.placeholder = "Blocked by task IDs (e.g., '1,3,5' or Enter to skip)..."

    def _handle_task_blocking_ids_input(self, blocking_ids_str: str) -> None:
        """Handle task blocking IDs input.

        Args:
            blocking_ids_str: Comma-separated task numbers
        """
        self._awaiting_task_blocking_ids = False
        self.command_input.placeholder = "Type a command... (type 'help' for commands)"

        # Validate blocking task IDs if provided
        blocking_task_ids = []
        if blocking_ids_str.strip():
            valid_ids, error = task_commands.validate_blocking_task_ids(
                self.active_role_id, blocking_ids_str
            )
            if error:
                self.show_error(error)
                # Clean up
                self._pending_task_title = None
                self._pending_task_due_date = None
                self._pending_task_priority = None
                self._pending_task_story_points = None
                self._pending_task_description = None
                return
            blocking_task_ids = valid_ids

        # Create task
        task_id = task_commands.create_task(
            role_id=self.active_role_id,
            title=self._pending_task_title,
            due_date=self._pending_task_due_date,
            priority=self._pending_task_priority,
            story_points=self._pending_task_story_points,
            description=self._pending_task_description,
        )

        if task_id:
            # Add dependencies
            for blocking_id in blocking_task_ids:
                task_commands.add_task_dependency(blocking_id, task_id)

            # Refresh the panel for the role we just added a task to
            self.refresh_panel_for_role(self.active_role_id)
        else:
            self.show_error("Failed to create task")

        # Clean up
        self._pending_task_title = None
        self._pending_task_due_date = None
        self._pending_task_priority = None
        self._pending_task_story_points = None
        self._pending_task_description = None

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
        # If in kanban view, remove kanban board first
        if self._in_kanban_view and self.current_panel:
            self.current_panel.remove()
            self.current_panel = None
            self._in_kanban_view = False

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
            self.show_error(f"No action specified for task t{task_number}. Try 't{task_number} edit' or 't{task_number} delete'")
            return

        # Get the task
        task = task_commands.get_task_by_number(self.active_role_id, task_number)
        if not task:
            self.show_error(f"Task t{task_number} not found in the active role")
            return

        # Handle different actions
        if action in ("doing", "done", "todo"):
            self.update_task_status(task, action)
        elif action == "delete":
            self.delete_task(task)
        elif action == "edit":
            self.edit_task(task)
        else:
            self.show_error(f"Unknown action: {action}")

    def handle_batch_task_command(self, args: dict) -> None:
        """Handle batch task commands.

        Args:
            args: Parsed command arguments containing task_numbers and action
        """
        if not self.active_role_id:
            self.show_error("No role selected. Select a role first.")
            return

        task_numbers = args.get("task_numbers", [])
        action = args.get("action")

        if not action:
            task_list = ", ".join(f"t{n}" for n in task_numbers)
            self.show_error(f"No action specified for tasks {task_list}")
            return

        # Batch commands only support: delete, doing, done, todo
        if action not in ("delete", "doing", "done", "todo"):
            self.show_error(f"Batch operation not supported for action: {action}")
            return

        # Get all tasks and validate they exist
        tasks = []
        invalid_numbers = []
        for task_num in task_numbers:
            task = task_commands.get_task_by_number(self.active_role_id, task_num)
            if task:
                tasks.append(task)
            else:
                invalid_numbers.append(task_num)

        if invalid_numbers:
            invalid_str = ", ".join(f"t{n}" for n in invalid_numbers)
            self.show_error(f"Tasks not found: {invalid_str}")
            return

        if not tasks:
            self.show_error("No valid tasks found")
            return

        # Handle different batch actions
        if action == "delete":
            self.batch_delete_tasks(tasks)
        elif action in ("doing", "done", "todo"):
            self.batch_update_status(tasks, action)

    def batch_delete_tasks(self, tasks: list) -> None:
        """Delete multiple tasks with confirmation.

        Args:
            tasks: List of task database rows
        """
        self._pending_batch_delete_tasks = tasks
        self._awaiting_batch_delete_confirmation = True

        # Show confirmation prompt
        task_count = len(tasks)
        task_list = ", ".join(f"t{t['task_number']}" for t in tasks)
        self.command_input.placeholder = f"Delete {task_count} tasks ({task_list})? Type 'yes' or 'no'"

    def batch_update_status(self, tasks: list, status: str) -> None:
        """Update status for multiple tasks.

        Args:
            tasks: List of task database rows
            status: New status (doing/done/todo)
        """
        # Update all tasks
        for task in tasks:
            task_commands.update_task_status(task['id'], status)

        # Refresh the panel
        if tasks:
            self.refresh_panel_for_role(tasks[0]['role_id'])

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

    def _handle_batch_delete_confirmation(self, response: str) -> None:
        """Handle batch delete confirmation response.

        Args:
            response: User's response (yes/no)
        """
        self._awaiting_batch_delete_confirmation = False
        self.command_input.placeholder = "Type a command... (type 'help' for commands)"

        response = response.strip().lower()

        if response == 'yes':
            # Delete all tasks
            tasks = self._pending_batch_delete_tasks
            for task in tasks:
                task_commands.delete_task(task['id'], save_to_undo=True)

            # Refresh the panel
            if tasks:
                self.refresh_panel_for_role(tasks[0]['role_id'])
        else:
            # Cancelled - just refresh to show tasks still there
            if self._pending_batch_delete_tasks:
                self.refresh_panel_for_role(self._pending_batch_delete_tasks[0]['role_id'])

        # Clean up
        self._pending_batch_delete_tasks = None

    def undo_last_deletion(self) -> None:
        """Undo the last deleted task or role."""
        import json

        # Get the last deletion from undo stack
        last_deletion = db.fetchone(
            "SELECT * FROM undo_stack ORDER BY id DESC LIMIT 1"
        )

        if not last_deletion:
            self.show_error("No deletions to undo")
            return

        action_type = last_deletion['action_type']
        data = json.loads(last_deletion['data'])

        if action_type == 'delete_task':
            # Restore task using existing method
            restored_task = task_commands.undo_last_deletion()
            if restored_task:
                # Refresh the panel for the restored task's role
                self.refresh_panel_for_role(restored_task['role_id'])
        elif action_type == 'delete_role':
            # Restore role
            role_data = data
            db.execute(
                """INSERT INTO roles (id, display_number, name, color)
                   VALUES (?, ?, ?, ?)""",
                (role_data['role_id'], role_data['display_number'],
                 role_data['name'], role_data['color'])
            )
            # Remove from undo stack
            db.execute("DELETE FROM undo_stack WHERE id = ?", (last_deletion['id'],))
            db.commit()

            # Refresh view
            if self.in_multi_panel_mode and self.multi_panel_grid:
                self.multi_panel_grid.refresh_all_panels()
            else:
                self.update_content("Welcome to Terminal Todo!\n\nType 'new role' to get started.")
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

        task = self._pending_edit_task

        # Store the new due date temporarily
        if due_date_str.strip().lower() == 'clear':
            self._pending_task_due_date = ""  # Clear the due date
        elif due_date_str.strip():
            self._pending_task_due_date = due_date_str.strip()
        else:
            self._pending_task_due_date = task['due_date']  # Keep current

        # Move to priority prompt
        current_priority = task['priority'] if task['priority'] else "none"
        self.command_input.placeholder = f"Edit priority (current: {current_priority}) - High/Medium/Low/'clear'/Enter to skip..."
        self._awaiting_edit_priority = True

    def _handle_edit_priority_input(self, priority_str: str) -> None:
        """Handle edit priority input.

        Args:
            priority_str: New priority string (empty to keep current, 'clear' to remove)
        """
        self._awaiting_edit_priority = False

        task = self._pending_edit_task

        # Store the new priority temporarily
        if priority_str.strip().lower() == 'clear':
            self._pending_task_priority = ""  # Clear the priority
        elif priority_str.strip():
            priority_capitalized = priority_str.strip().capitalize()
            if priority_capitalized not in ('High', 'Medium', 'Low'):
                self.show_error("Invalid priority. Must be High, Medium, or Low.")
                # Clean up and restart
                self._pending_edit_task = None
                self._pending_task_title = None
                self._pending_task_due_date = None
                self._pending_task_priority = None
                self.command_input.placeholder = "Type a command... (type 'help' for commands)"
                return
            self._pending_task_priority = priority_capitalized
        else:
            self._pending_task_priority = task['priority']  # Keep current

        # Move to story points prompt
        current_sp = task['story_points'] if task['story_points'] else "none"
        self.command_input.placeholder = f"Edit story points (current: {current_sp}) - 1/2/3/5/8/13/'clear'/Enter to skip..."
        self._awaiting_edit_story_points = True

    def _handle_edit_story_points_input(self, story_points_str: str) -> None:
        """Handle edit story points input.

        Args:
            story_points_str: New story points string (empty to keep current, 'clear' to remove)
        """
        self._awaiting_edit_story_points = False

        task = self._pending_edit_task

        # Store the new story points temporarily
        if story_points_str.strip().lower() == 'clear':
            self._pending_task_story_points = 0  # Clear (use 0 as sentinel for None)
        elif story_points_str.strip():
            try:
                sp = int(story_points_str.strip())
                if sp not in (1, 2, 3, 5, 8, 13):
                    self.show_error("Invalid story points. Must be 1, 2, 3, 5, 8, or 13.")
                    # Clean up and restart
                    self._pending_edit_task = None
                    self._pending_task_title = None
                    self._pending_task_due_date = None
                    self._pending_task_priority = None
                    self._pending_task_story_points = None
                    self.command_input.placeholder = "Type a command... (type 'help' for commands)"
                    return
                self._pending_task_story_points = sp
            except ValueError:
                self.show_error("Invalid story points. Must be a number: 1, 2, 3, 5, 8, or 13.")
                # Clean up and restart
                self._pending_edit_task = None
                self._pending_task_title = None
                self._pending_task_due_date = None
                self._pending_task_priority = None
                self._pending_task_story_points = None
                self.command_input.placeholder = "Type a command... (type 'help' for commands)"
                return
        else:
            self._pending_task_story_points = task['story_points']  # Keep current

        # Move to description prompt
        current_desc = task['description'] if task['description'] else "none"
        # Truncate description if too long for display
        if len(current_desc) > 50:
            current_desc = current_desc[:47] + "..."
        self.command_input.placeholder = f"Edit description (current: {current_desc}) - 'clear'/Enter to skip..."
        self._awaiting_edit_description = True

    def _handle_edit_description_input(self, description_str: str) -> None:
        """Handle edit description input.

        Args:
            description_str: New description string (empty to keep current, 'clear' to remove)
        """
        self._awaiting_edit_description = False

        task = self._pending_edit_task

        # Store the new description temporarily
        if description_str.strip().lower() == 'clear':
            self._pending_task_description = ""  # Clear the description
        elif description_str.strip():
            self._pending_task_description = description_str.strip()
        else:
            self._pending_task_description = task['description']  # Keep current

        # Get current blocking task IDs
        blocking_ids = task_commands.get_tasks_blocking(task['id'])
        blocking_numbers = []
        for blocking_id in blocking_ids:
            # Get the task by ID (not task_number)
            blocking_task = task_commands.db.fetchone(
                "SELECT task_number FROM tasks WHERE id = ?", (blocking_id,)
            )
            if blocking_task:
                blocking_numbers.append(str(blocking_task['task_number']))

        current_blocking = ','.join(blocking_numbers) if blocking_numbers else "none"

        # Move to blocking IDs prompt
        self.command_input.placeholder = f"Edit blocked by (current: {current_blocking}) - Enter to skip or 'clear' to remove all..."
        self._awaiting_edit_blocking_ids = True

    def _handle_edit_blocking_ids_input(self, blocking_ids_str: str) -> None:
        """Handle edit blocking IDs input.

        Args:
            blocking_ids_str: Comma-separated task numbers (empty to keep current, 'clear' to remove all)
        """
        self._awaiting_edit_blocking_ids = False
        self.command_input.placeholder = "Type a command... (type 'help' for commands)"

        task = self._pending_edit_task
        new_title = self._pending_task_title if self._pending_task_title else task['title']
        new_due_date = self._pending_task_due_date if self._pending_task_due_date is not None else task['due_date']

        # Handle priority - convert empty string to None for clearing
        if self._pending_task_priority == "":
            new_priority = None
        elif self._pending_task_priority is not None:
            new_priority = self._pending_task_priority
        else:
            new_priority = task['priority']

        # Handle story points - convert 0 to None for clearing
        if self._pending_task_story_points == 0:
            new_story_points = None
        elif self._pending_task_story_points is not None:
            new_story_points = self._pending_task_story_points
        else:
            new_story_points = task['story_points']

        # Handle description - convert empty string to None for clearing
        if self._pending_task_description == "":
            new_description = None
        elif self._pending_task_description is not None:
            new_description = self._pending_task_description
        else:
            new_description = task['description']

        # Update the task
        success = task_commands.update_task(
            task_id=task['id'],
            title=new_title,
            due_date=new_due_date,
            priority=new_priority,
            story_points=new_story_points,
            description=new_description,
        )

        if not success:
            self.show_error("Failed to update task")
            self._pending_edit_task = None
            self._pending_task_title = None
            self._pending_task_due_date = None
            self._pending_task_priority = None
            self._pending_task_story_points = None
            self._pending_task_description = None
            return

        # Update dependencies
        if blocking_ids_str.strip().lower() == 'clear':
            # Remove all blocking dependencies
            current_blocking_ids = task_commands.get_tasks_blocking(task['id'])
            for blocking_id in current_blocking_ids:
                task_commands.remove_task_dependency(blocking_id, task['id'])
        elif blocking_ids_str.strip():
            # Validate and update blocking task IDs
            valid_ids, error = task_commands.validate_blocking_task_ids(
                task['role_id'], blocking_ids_str
            )
            if error:
                self.show_error(error)
            else:
                # Remove all existing dependencies
                current_blocking_ids = task_commands.get_tasks_blocking(task['id'])
                for blocking_id in current_blocking_ids:
                    task_commands.remove_task_dependency(blocking_id, task['id'])

                # Add new dependencies
                for blocking_id in valid_ids:
                    task_commands.add_task_dependency(blocking_id, task['id'])

        # Refresh the panel for this task's role
        self.refresh_panel_for_role(task['role_id'])

        # Clean up
        self._pending_edit_task = None
        self._pending_task_title = None
        self._pending_task_due_date = None
        self._pending_task_priority = None
        self._pending_task_story_points = None
        self._pending_task_description = None

    def action_clear_input(self) -> None:
        """Clear the command input."""
        self.command_input.value = ""

    def action_quit(self) -> None:
        """Quit the application."""
        # Stop the archive scheduler
        self.archive_scheduler.stop()

        # Close database connection
        db.close()

        # Exit the app
        self.exit()


def run():
    """Run the application."""
    app = TodoApp()
    app.run()


if __name__ == "__main__":
    run()
