"""Window management commands."""

from typing import List, Tuple, Optional, Dict
from ttodo.database.models import db
import json


def calculate_panel_layout(panel_count: int) -> List[Dict[str, any]]:
    """Calculate panel positions and sizes based on count.

    Layout Priority (from brief.md):
    - 1 panel: full screen
    - 2 panels: side by side (50/50)
    - 3 panels: left (50%) + right top/bottom (25% each)
    - 4 panels: 2x2 grid
    - 5 panels: left (50%) + right 3 stacked (16.6% each)
    - 6 panels: 2x3 grid
    - 7 panels: left 3 stacked + right 4 stacked
    - 8 panels: left 4 stacked + right 4 stacked (max)

    Args:
        panel_count: Number of panels (1-8)

    Returns:
        List of panel layout specs with position and size info
        Each spec: {"index": int, "width": str, "height": str, "column": int, "row": int}
    """
    if panel_count < 1 or panel_count > 8:
        raise ValueError("Panel count must be between 1 and 8")

    layouts = []

    if panel_count == 1:
        # Full screen
        layouts = [{"index": 0, "width": "100%", "height": "100%", "column": 0, "row": 0}]

    elif panel_count == 2:
        # Side by side (50/50)
        layouts = [
            {"index": 0, "width": "50%", "height": "100%", "column": 0, "row": 0},
            {"index": 1, "width": "50%", "height": "100%", "column": 1, "row": 0}
        ]

    elif panel_count == 3:
        # Left 50% + right 2 stacked (50% each)
        layouts = [
            {"index": 0, "width": "50%", "height": "100%", "column": 0, "row": 0},
            {"index": 1, "width": "50%", "height": "50%", "column": 1, "row": 0},
            {"index": 2, "width": "50%", "height": "50%", "column": 1, "row": 1}
        ]

    elif panel_count == 4:
        # 2x2 grid (50% x 50% each)
        layouts = [
            {"index": 0, "width": "50%", "height": "50%", "column": 0, "row": 0},
            {"index": 1, "width": "50%", "height": "50%", "column": 1, "row": 0},
            {"index": 2, "width": "50%", "height": "50%", "column": 0, "row": 1},
            {"index": 3, "width": "50%", "height": "50%", "column": 1, "row": 1}
        ]

    elif panel_count == 5:
        # Left 50% + right 3 stacked (33.3% each)
        layouts = [
            {"index": 0, "width": "50%", "height": "100%", "column": 0, "row": 0},
            {"index": 1, "width": "50%", "height": "33.33%", "column": 1, "row": 0},
            {"index": 2, "width": "50%", "height": "33.33%", "column": 1, "row": 1},
            {"index": 3, "width": "50%", "height": "33.34%", "column": 1, "row": 2},
            {"index": 4, "width": "50%", "height": "100%", "column": 0, "row": 1}  # Takes row 1-3
        ]

    elif panel_count == 6:
        # 2x3 grid (50% x 33.3% each)
        layouts = [
            {"index": 0, "width": "50%", "height": "33.33%", "column": 0, "row": 0},
            {"index": 1, "width": "50%", "height": "33.33%", "column": 1, "row": 0},
            {"index": 2, "width": "50%", "height": "33.33%", "column": 0, "row": 1},
            {"index": 3, "width": "50%", "height": "33.33%", "column": 1, "row": 1},
            {"index": 4, "width": "50%", "height": "33.34%", "column": 0, "row": 2},
            {"index": 5, "width": "50%", "height": "33.34%", "column": 1, "row": 2}
        ]

    elif panel_count == 7:
        # Left 3 stacked (33.3%) + right 4 stacked (25%)
        layouts = [
            {"index": 0, "width": "50%", "height": "33.33%", "column": 0, "row": 0},
            {"index": 1, "width": "50%", "height": "25%", "column": 1, "row": 0},
            {"index": 2, "width": "50%", "height": "33.33%", "column": 0, "row": 1},
            {"index": 3, "width": "50%", "height": "25%", "column": 1, "row": 1},
            {"index": 4, "width": "50%", "height": "33.34%", "column": 0, "row": 2},
            {"index": 5, "width": "50%", "height": "25%", "column": 1, "row": 2},
            {"index": 6, "width": "50%", "height": "25%", "column": 1, "row": 3}
        ]

    elif panel_count == 8:
        # Left 4 stacked + right 4 stacked (25% each)
        layouts = [
            {"index": 0, "width": "50%", "height": "25%", "column": 0, "row": 0},
            {"index": 1, "width": "50%", "height": "25%", "column": 1, "row": 0},
            {"index": 2, "width": "50%", "height": "25%", "column": 0, "row": 1},
            {"index": 3, "width": "50%", "height": "25%", "column": 1, "row": 1},
            {"index": 4, "width": "50%", "height": "25%", "column": 0, "row": 2},
            {"index": 5, "width": "50%", "height": "25%", "column": 1, "row": 2},
            {"index": 6, "width": "50%", "height": "25%", "column": 0, "row": 3},
            {"index": 7, "width": "50%", "height": "25%", "column": 1, "row": 3}
        ]

    return layouts


def save_window_layout(panel_count: int, panel_roles: List[int]) -> None:
    """Save window layout to database.

    Args:
        panel_count: Number of panels
        panel_roles: List of role IDs in panel order
    """
    panel_roles_json = json.dumps(panel_roles)

    # Check if layout exists
    existing = db.fetchone("SELECT id FROM window_layout WHERE id = 1")

    if existing:
        # Update existing
        db.execute(
            "UPDATE window_layout SET panel_count = ?, panel_roles = ? WHERE id = 1",
            (panel_count, panel_roles_json)
        )
    else:
        # Insert new
        db.execute(
            "INSERT INTO window_layout (id, panel_count, panel_roles) VALUES (1, ?, ?)",
            (panel_count, panel_roles_json)
        )

    db.commit()


def load_window_layout() -> Optional[Tuple[int, List[int]]]:
    """Load window layout from database.

    Returns:
        Tuple of (panel_count, panel_roles) or None if no layout exists
    """
    result = db.fetchone("SELECT panel_count, panel_roles FROM window_layout WHERE id = 1")

    if result:
        panel_count = result["panel_count"]
        panel_roles = json.loads(result["panel_roles"])
        return (panel_count, panel_roles)

    return None


def clear_window_layout() -> None:
    """Clear window layout from database."""
    db.execute("DELETE FROM window_layout WHERE id = 1")
    db.commit()


def remove_panel_from_layout(panel_index: int) -> Optional[Tuple[int, List[int]]]:
    """Remove a panel from the current layout.

    Args:
        panel_index: Index of panel to remove (0-based)

    Returns:
        New (panel_count, panel_roles) tuple or None if no layout
    """
    layout = load_window_layout()
    if not layout:
        return None

    panel_count, panel_roles = layout

    # Remove panel at index
    if 0 <= panel_index < len(panel_roles):
        new_panel_roles = panel_roles[:panel_index] + panel_roles[panel_index + 1:]
        new_panel_count = len(new_panel_roles)

        if new_panel_count > 0:
            save_window_layout(new_panel_count, new_panel_roles)
            return (new_panel_count, new_panel_roles)
        else:
            # No panels left, clear layout
            clear_window_layout()
            return None

    return layout


def validate_role_ids(role_ids: List[int]) -> bool:
    """Validate that all role IDs exist in database.

    Args:
        role_ids: List of role IDs to validate

    Returns:
        True if all role IDs exist, False otherwise
    """
    from ttodo.commands.role_commands import get_role_by_id

    for role_id in role_ids:
        if role_id is None:  # Allow None for empty panels
            continue
        role = get_role_by_id(role_id)
        if not role:
            return False

    return True
