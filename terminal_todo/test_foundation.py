"""Test script for Iteration 1 foundation."""
import sys
from database.models import db
from database.migrations import create_schema
from utils.colors import (
    ROLE_COLORS,
    get_role_color,
    get_active_color,
    get_blocked_color,
    adjust_brightness
)
from commands.parser import parser


def test_database():
    """Test database creation and schema."""
    print("Testing Database...")
    try:
        db.connect()
        create_schema()

        # Verify tables exist
        tables = db.fetchall("SELECT name FROM sqlite_master WHERE type='table'")
        table_names = [row[0] for row in tables]

        required_tables = [
            'roles', 'tasks', 'task_dependencies',
            'window_layout', 'undo_stack', 'archived_tasks'
        ]

        for table in required_tables:
            if table in table_names:
                print(f"  ✓ Table '{table}' exists")
            else:
                print(f"  ✗ Table '{table}' missing")
                return False

        db.close()
        print("  ✓ Database tests passed\n")
        return True
    except Exception as e:
        print(f"  ✗ Database test failed: {e}\n")
        return False


def test_colors():
    """Test color system."""
    print("Testing Color System...")
    try:
        # Test palette
        if len(ROLE_COLORS) != 8:
            print(f"  ✗ Expected 8 colors, got {len(ROLE_COLORS)}")
            return False
        print(f"  ✓ Color palette has 8 colors")

        # Test color retrieval
        color = get_role_color(0)
        if not color.startswith('#'):
            print(f"  ✗ Invalid color format: {color}")
            return False
        print(f"  ✓ Color format valid: {color}")

        # Test brightness adjustments
        active = get_active_color(ROLE_COLORS[0])
        blocked = get_blocked_color(ROLE_COLORS[0])
        print(f"  ✓ Active color (120%): {active}")
        print(f"  ✓ Blocked color (70%): {blocked}")

        # Verify brightness changes
        base = ROLE_COLORS[0]
        bright = adjust_brightness(base, 1.5)
        if bright == base:
            print(f"  ✗ Brightness adjustment failed")
            return False
        print(f"  ✓ Brightness adjustment working")

        print("  ✓ Color tests passed\n")
        return True
    except Exception as e:
        print(f"  ✗ Color test failed: {e}\n")
        return False


def test_parser():
    """Test command parser."""
    print("Testing Command Parser...")
    try:
        # Test basic parsing
        cmd, args = parser.parse("hello world")
        if cmd != "hello":
            print(f"  ✗ Expected command 'hello', got '{cmd}'")
            return False
        print(f"  ✓ Basic command parsing: 'hello' -> '{cmd}'")

        # Test empty command
        cmd, args = parser.parse("")
        if cmd != "empty":
            print(f"  ✗ Expected 'empty' for blank input, got '{cmd}'")
            return False
        print(f"  ✓ Empty command handling")

        # Test multi-word
        cmd, args = parser.parse("new role")
        if cmd != "new":
            print(f"  ✗ Expected command 'new', got '{cmd}'")
            return False
        print(f"  ✓ Multi-word command parsing")

        print("  ✓ Parser tests passed\n")
        return True
    except Exception as e:
        print(f"  ✗ Parser test failed: {e}\n")
        return False


def main():
    """Run all tests."""
    print("=" * 50)
    print("Iteration 1 - Foundation Tests")
    print("=" * 50)
    print()

    results = []
    results.append(("Database", test_database()))
    results.append(("Colors", test_colors()))
    results.append(("Parser", test_parser()))

    print("=" * 50)
    print("Test Summary")
    print("=" * 50)

    all_passed = True
    for name, passed in results:
        status = "✓ PASSED" if passed else "✗ FAILED"
        print(f"  {name}: {status}")
        if not passed:
            all_passed = False

    print()
    if all_passed:
        print("✓ All foundation tests passed!")
        print("\nYou can now run the app with: python main.py")
        return 0
    else:
        print("✗ Some tests failed. Please review errors above.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
