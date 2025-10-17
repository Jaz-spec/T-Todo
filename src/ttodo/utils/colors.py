"""Color management system with autumnal palette."""
from typing import Tuple


# Autumnal color palette (hex values)
ROLE_COLORS = [
    "#D4A574",  # Tan
    "#C17817",  # Dark Orange
    "#8B4513",  # Saddle Brown
    "#CD853F",  # Peru
    "#A0522D",  # Sienna
    "#DAA520",  # Goldenrod
    "#B8860B",  # Dark Goldenrod
    "#8B7355",  # Burlywood Dark
]


def hex_to_rgb(hex_color: str) -> Tuple[int, int, int]:
    """Convert hex color to RGB tuple.

    Args:
        hex_color: Hex color string (e.g., "#D4A574")

    Returns:
        Tuple of (r, g, b) values (0-255)
    """
    hex_color = hex_color.lstrip('#')
    return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))


def rgb_to_hex(r: int, g: int, b: int) -> str:
    """Convert RGB values to hex color string.

    Args:
        r: Red value (0-255)
        g: Green value (0-255)
        b: Blue value (0-255)

    Returns:
        Hex color string (e.g., "#D4A574")
    """
    return f"#{r:02x}{g:02x}{b:02x}"


def adjust_brightness(hex_color: str, factor: float) -> str:
    """Adjust brightness of a color by a factor.

    Args:
        hex_color: Hex color string (e.g., "#D4A574")
        factor: Brightness factor (e.g., 0.7 for 70%, 1.2 for 120%)

    Returns:
        Adjusted hex color string
    """
    r, g, b = hex_to_rgb(hex_color)

    # Adjust each component
    r = min(255, int(r * factor))
    g = min(255, int(g * factor))
    b = min(255, int(b * factor))

    return rgb_to_hex(r, g, b)


def get_role_color(index: int) -> str:
    """Get role color by index (cycles through palette).

    Args:
        index: Color index (0-based)

    Returns:
        Hex color string
    """
    return ROLE_COLORS[index % len(ROLE_COLORS)]


def get_active_color(hex_color: str) -> str:
    """Get brightened color for active/focused state (120% brightness).

    Args:
        hex_color: Base hex color string

    Returns:
        Brightened hex color string
    """
    return adjust_brightness(hex_color, 1.2)


def get_blocked_color(hex_color: str) -> str:
    """Get dulled color for blocked task state (70% brightness).

    Args:
        hex_color: Base hex color string

    Returns:
        Dulled hex color string
    """
    return adjust_brightness(hex_color, 0.7)


def format_color_for_terminal(hex_color: str) -> str:
    """Format hex color for terminal display (Rich/Textual format).

    Args:
        hex_color: Hex color string

    Returns:
        Color string in format suitable for Rich/Textual
    """
    return hex_color  # Rich/Textual accept hex colors directly


if __name__ == "__main__":
    # Test color functions
    print("Autumnal Color Palette:")
    for i, color in enumerate(ROLE_COLORS):
        print(f"  {i+1}. {color}")

    print("\nBrightness adjustments for first color:")
    base = ROLE_COLORS[0]
    print(f"  Base (100%):    {base}")
    print(f"  Active (120%):  {get_active_color(base)}")
    print(f"  Blocked (70%):  {get_blocked_color(base)}")
