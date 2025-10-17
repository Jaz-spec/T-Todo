"""Command parsing and routing."""
from typing import Optional, Tuple, Dict, Any


class CommandParser:
    """Parses and routes user commands."""

    def parse(self, command_str: str) -> Tuple[str, Dict[str, Any]]:
        """Parse command string into command name and arguments.

        Args:
            command_str: Raw command string from user

        Returns:
            Tuple of (command_name, arguments_dict)
        """
        command_str = command_str.strip()

        if not command_str:
            return ("empty", {})

        # Split into parts
        parts = command_str.split()
        command = parts[0].lower()

        # For now, just return basic parsing
        # We'll expand this in later iterations
        return (command, {"raw": command_str, "parts": parts[1:]})

    def get_command_type(self, command_str: str) -> str:
        """Determine the type of command.

        Args:
            command_str: Command string

        Returns:
            Command type string
        """
        command, args = self.parse(command_str)
        return command


# Global parser instance
parser = CommandParser()
