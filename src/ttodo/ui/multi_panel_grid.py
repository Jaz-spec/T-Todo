"""Multi-panel grid container for displaying multiple role panels simultaneously."""

from textual.containers import Container, Grid, Vertical, Horizontal
from textual.widgets import Static
from textual.css.query import NoMatches
from ttodo.ui.panels import RolePanel
from ttodo.commands import role_commands
from typing import List, Optional, Dict


class PanelContainer(Static):
    """Container for a single role panel with focus management."""

    def __init__(self, panel_index: int, role_id: Optional[int] = None, is_focused: bool = False):
        super().__init__()
        self.panel_index = panel_index
        self.role_id = role_id
        self.is_focused = is_focused
        self.role_panel = None

        if role_id:
            self._create_panel()

    def _create_panel(self):
        """Create the role panel widget."""
        if not self.role_id:
            self.update("No role assigned")
            return

        role = role_commands.get_role_by_id(self.role_id)
        if not role:
            self.update(f"Role {self.role_id} not found")
            return

        self.role_panel = RolePanel(
            role_id=role["id"],
            role_name=role["name"],
            display_number=role["display_number"],
            color=role["color"],
            is_active=self.is_focused
        )
        self.update(self.role_panel.render())

    def set_focus(self, focused: bool):
        """Update focus state and refresh panel."""
        self.is_focused = focused
        if self.role_panel:
            self.role_panel.is_active = focused
            self.update(self.role_panel.render())

    def refresh_panel(self):
        """Refresh the panel content by recreating it."""
        if self.role_id:
            # Recreate the panel to fetch fresh data
            self._create_panel()

    def set_role(self, role_id: Optional[int]):
        """Set or change the role for this panel."""
        self.role_id = role_id
        self._create_panel()


class MultiPanelGrid(Container):
    """Grid container for managing multiple role panels.

    Supports 1-8 panels with various layout configurations.
    """

    DEFAULT_CSS = """
    MultiPanelGrid {
        width: 100%;
        height: 100%;
    }

    MultiPanelGrid Horizontal {
        width: 100%;
        height: 100%;
    }

    MultiPanelGrid Vertical {
        width: 100%;
        height: 100%;
    }

    MultiPanelGrid PanelContainer {
        width: 1fr;
        height: 1fr;
    }
    """

    def __init__(self, panel_count: int = 1, panel_roles: Optional[List[int]] = None):
        super().__init__()
        self.panel_count = panel_count
        self.panel_roles = panel_roles or [None] * panel_count
        self.panel_containers: List[PanelContainer] = []
        self.focused_panel_index = 0

        # Ensure panel_roles has correct length
        while len(self.panel_roles) < panel_count:
            self.panel_roles.append(None)

    def compose(self):
        """Compose the multi-panel layout based on panel count."""
        from ttodo.commands.window_commands import calculate_panel_layout

        if self.panel_count == 1:
            # Single panel - full screen
            panel = PanelContainer(0, self.panel_roles[0], is_focused=True)
            self.panel_containers.append(panel)
            yield panel

        elif self.panel_count == 2:
            # Side by side
            with Horizontal():
                for i in range(2):
                    panel = PanelContainer(i, self.panel_roles[i], is_focused=(i == 0))
                    self.panel_containers.append(panel)
                    yield panel

        elif self.panel_count == 3:
            # Left 50% + right 2 stacked
            with Horizontal():
                # Left panel
                panel = PanelContainer(0, self.panel_roles[0], is_focused=True)
                self.panel_containers.append(panel)
                yield panel

                # Right panels stacked
                with Vertical():
                    for i in range(1, 3):
                        panel = PanelContainer(i, self.panel_roles[i], is_focused=False)
                        self.panel_containers.append(panel)
                        yield panel

        elif self.panel_count == 4:
            # 2x2 grid
            with Vertical():
                # Top row
                with Horizontal():
                    for i in range(2):
                        panel = PanelContainer(i, self.panel_roles[i], is_focused=(i == 0))
                        self.panel_containers.append(panel)
                        yield panel
                # Bottom row
                with Horizontal():
                    for i in range(2, 4):
                        panel = PanelContainer(i, self.panel_roles[i], is_focused=False)
                        self.panel_containers.append(panel)
                        yield panel

        elif self.panel_count == 5:
            # Left 50% + right 3 stacked
            with Horizontal():
                # Left panel
                panel = PanelContainer(0, self.panel_roles[0], is_focused=True)
                self.panel_containers.append(panel)
                yield panel

                # Right panels stacked
                with Vertical():
                    for i in range(1, 5):
                        panel = PanelContainer(i, self.panel_roles[i], is_focused=False)
                        self.panel_containers.append(panel)
                        yield panel

        elif self.panel_count == 6:
            # 2x3 grid
            with Vertical():
                for row in range(3):
                    with Horizontal():
                        for col in range(2):
                            i = row * 2 + col
                            panel = PanelContainer(i, self.panel_roles[i], is_focused=(i == 0))
                            self.panel_containers.append(panel)
                            yield panel

        elif self.panel_count == 7:
            # Left 3 stacked + right 4 stacked
            with Horizontal():
                # Left panels
                with Vertical():
                    for i in range(3):
                        panel = PanelContainer(i, self.panel_roles[i], is_focused=(i == 0))
                        self.panel_containers.append(panel)
                        yield panel

                # Right panels
                with Vertical():
                    for i in range(3, 7):
                        panel = PanelContainer(i, self.panel_roles[i], is_focused=False)
                        self.panel_containers.append(panel)
                        yield panel

        elif self.panel_count == 8:
            # Left 4 stacked + right 4 stacked
            with Horizontal():
                # Left panels
                with Vertical():
                    for i in range(4):
                        panel = PanelContainer(i, self.panel_roles[i], is_focused=(i == 0))
                        self.panel_containers.append(panel)
                        yield panel

                # Right panels
                with Vertical():
                    for i in range(4, 8):
                        panel = PanelContainer(i, self.panel_roles[i], is_focused=False)
                        self.panel_containers.append(panel)
                        yield panel

    def focus_next_panel(self):
        """Move focus to the next panel (Tab cycling)."""
        # Unfocus current
        if 0 <= self.focused_panel_index < len(self.panel_containers):
            self.panel_containers[self.focused_panel_index].set_focus(False)

        # Move to next
        self.focused_panel_index = (self.focused_panel_index + 1) % len(self.panel_containers)

        # Focus new
        self.panel_containers[self.focused_panel_index].set_focus(True)

        return self.focused_panel_index

    def get_focused_panel(self) -> Optional[PanelContainer]:
        """Get the currently focused panel container."""
        if 0 <= self.focused_panel_index < len(self.panel_containers):
            return self.panel_containers[self.focused_panel_index]
        return None

    def get_focused_role_id(self) -> Optional[int]:
        """Get the role ID of the currently focused panel."""
        panel = self.get_focused_panel()
        return panel.role_id if panel else None

    def refresh_focused_panel(self):
        """Refresh the currently focused panel."""
        panel = self.get_focused_panel()
        if panel:
            panel.refresh_panel()

    def refresh_all_panels(self):
        """Refresh all panels."""
        for panel in self.panel_containers:
            panel.refresh_panel()
