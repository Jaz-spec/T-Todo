"""Date parsing and formatting utilities."""
from datetime import datetime, timedelta
from typing import Optional
import re


def parse_date(date_str: str) -> Optional[str]:
    """Parse various date formats into ISO format (YYYY-MM-DD).

    Supported formats:
    - DD MM YY (e.g., "15 10 25")
    - DD MM YYYY (e.g., "15 10 2025")
    - +Xd (e.g., "+3d" for 3 days from now)
    - "tomorrow"
    - "today"

    Args:
        date_str: Input date string

    Returns:
        ISO format date string (YYYY-MM-DD) or None if invalid
    """
    date_str = date_str.strip().lower()

    if not date_str:
        return None

    # Handle relative dates
    if date_str == "today":
        return datetime.now().strftime("%Y-%m-%d")

    if date_str == "tomorrow":
        return (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")

    # Handle +Xd format
    if match := re.match(r'\+(\d+)d', date_str):
        days = int(match.group(1))
        return (datetime.now() + timedelta(days=days)).strftime("%Y-%m-%d")

    # Handle DD MM YY or DD MM YYYY
    parts = date_str.split()
    if len(parts) == 3:
        try:
            day = int(parts[0])
            month = int(parts[1])
            year = int(parts[2])

            # Handle 2-digit years
            if year < 100:
                year += 2000

            # Validate date
            date_obj = datetime(year, month, day)
            return date_obj.strftime("%Y-%m-%d")
        except (ValueError, IndexError):
            return None

    return None


def format_relative_date(iso_date: str) -> str:
    """Format ISO date as relative display string.

    Display rules:
    - Same day: "Today"
    - Next day: "Tomorrow"
    - Previous day: "Yesterday"
    - Within 7 days future: "Next Monday", "Next Friday", etc.
    - Same week past: "Monday", "Tuesday", etc.
    - Beyond 7 days: "Tues 15 Oct", "Wed 23 Oct", etc.

    Args:
        iso_date: ISO format date string (YYYY-MM-DD)

    Returns:
        Formatted relative date string
    """
    if not iso_date:
        return ""

    try:
        date_obj = datetime.fromisoformat(iso_date)
    except (ValueError, TypeError):
        return iso_date  # Return as-is if invalid

    today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    target = date_obj.replace(hour=0, minute=0, second=0, microsecond=0)
    delta = (target - today).days

    # Same day
    if delta == 0:
        return "Today"

    # Tomorrow
    if delta == 1:
        return "Tomorrow"

    # Yesterday
    if delta == -1:
        return "Yesterday"

    # Within current week (past)
    if -7 < delta < 0:
        return date_obj.strftime("%A")  # "Monday", "Tuesday", etc.

    # Within next 7 days
    if 1 < delta <= 7:
        return f"Next {date_obj.strftime('%A')}"  # "Next Monday", etc.

    # Beyond 7 days - show abbreviated day and date
    # Format: "Tues 15 Oct"
    day_abbr = date_obj.strftime("%a")  # Mon, Tue, Wed, etc.
    day_num = date_obj.strftime("%-d")  # 1, 2, ..., 31 (no padding)
    month_abbr = date_obj.strftime("%b")  # Jan, Feb, etc.

    return f"{day_abbr} {day_num} {month_abbr}"


def validate_date_format(date_str: str) -> tuple[bool, str]:
    """Validate date format.

    Args:
        date_str: Date string to validate

    Returns:
        Tuple of (is_valid, error_message)
    """
    if not date_str:
        return (True, "")  # Optional field

    result = parse_date(date_str)
    if result is None:
        return (False, "Invalid date format. Use: DD MM YY, 'tomorrow', 'today', or '+3d'")

    return (True, "")
