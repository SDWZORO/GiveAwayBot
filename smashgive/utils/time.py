"""
Time utilities for IST handling and duration formatting.
"""

from datetime import datetime, timedelta
import pytz

IST = pytz.timezone("Asia/Kolkata")


def now_ist() -> datetime:
    """Get current time in IST."""
    return datetime.now(IST)


def parse_ist(time_str: str) -> datetime:
    """Parse a time string as IST. Format: YYYY-MM-DD HH:MM"""
    naive = datetime.strptime(time_str.strip(), "%Y-%m-%d %H:%M")
    return IST.localize(naive)


def format_ist(dt_str: str) -> str:
    """Format an ISO datetime string to human-readable IST."""
    try:
        dt = datetime.fromisoformat(dt_str)
        if dt.tzinfo is None:
            dt = IST.localize(dt)
        return dt.strftime("%Y-%m-%d %I:%M %p IST")
    except Exception:
        return dt_str


def format_duration(start_str: str, end_str: str) -> str:
    """Calculate and format the duration between two ISO time strings."""
    try:
        start = datetime.fromisoformat(start_str)
        end = datetime.fromisoformat(end_str)
        delta = end - start
        days = delta.days
        hours, rem = divmod(delta.seconds, 3600)
        minutes = rem // 60

        parts = []
        if days > 0:
            parts.append(f"{days} day{'s' if days > 1 else ''}")
        if hours > 0:
            parts.append(f"{hours} hour{'s' if hours > 1 else ''}")
        if minutes > 0:
            parts.append(f"{minutes} minute{'s' if minutes > 1 else ''}")
        return ", ".join(parts) if parts else "< 1 minute"
    except Exception:
        return "Unknown"


def format_runtime(start_str: str) -> str:
    """Format runtime from start until now."""
    try:
        start = datetime.fromisoformat(start_str)
        if start.tzinfo is None:
            start = IST.localize(start)
        now = now_ist()
        delta = now - start
        days = delta.days
        hours, rem = divmod(delta.seconds, 3600)
        minutes = rem // 60

        parts = []
        if days > 0:
            parts.append(f"{days}d")
        if hours > 0:
            parts.append(f"{hours}h")
        parts.append(f"{minutes}m")
        return " ".join(parts)
    except Exception:
        return "Unknown"
