"""Main TUI application using Textual."""
from textual.app import App, ComposeResult
from textual.widgets import Input, Static, Header
from textual.containers import Container, Vertical
from textual.binding import Binding
from ttodo.commands.parser import parser
from ttodo.database.models import db
from ttodo.database.migrations import initialize_database


class CommandInput(Input):
    """Custom command input widget."""

    def __init__(self):
        super().__init__(placeholder="Type a command... (type 'help' for commands)")
        self.command_history = []
        self.history_index = -1

    def add_to_history(self, command: str):
        """Add command to history."""
        if command and (not self.command_history or command != self.command_history[-1]):
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

        if not command_str:
            return

        # Add to history
        self.command_input.add_to_history(command_str)

        # Parse and handle command
        self.handle_command(command_str)

        # Clear input
        self.command_input.value = ""

    def handle_command(self, command_str: str) -> None:
        """Handle a command.

        Args:
            command_str: Command string to handle
        """
        command, args = parser.parse(command_str)

        # For now, just echo the command
        if command == "exit":
            self.exit()
        elif command == "help":
            self.show_help()
        elif command == "hello":
            self.update_content(f"Hello! You typed: {command_str}")
        elif command == "empty":
            pass  # Do nothing for empty commands
        else:
            self.update_content(f"Command received: {command_str}\n\nType 'help' for available commands.")

    def show_help(self) -> None:
        """Display help information."""
        help_text = """
Terminal Todo - Help

Available Commands:
  help                 Show this help message
  exit                 Exit the application (or press Ctrl+C)
  new role             Create a new role (coming in Iteration 2)

Navigation:
  Ctrl+C               Quit application
  Esc                  Clear command input
  �/�                  Navigate command history (coming soon)

Status: Iteration 1 - Foundation Complete
"""
        self.update_content(help_text)

    def update_content(self, text: str) -> None:
        """Update main content area.

        Args:
            text: Text to display
        """
        self.main_content.update(text)

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
