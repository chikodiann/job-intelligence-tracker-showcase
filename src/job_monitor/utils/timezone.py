"""Timezone utilities for Africa/Lagos (WAT, UTC+1)."""

from datetime import datetime, timezone
from typing import Optional
from zoneinfo import ZoneInfo

try:
    LAGOS_TZ = ZoneInfo("Africa/Lagos")
except Exception:
    from datetime import timedelta
    LAGOS_TZ = timezone(timedelta(hours=1))


def get_local_now(tz_name: Optional[str] = None) -> datetime:
    """Returns the current datetime in the specified timezone or system local timezone."""
    if tz_name:
        try:
            return datetime.now(ZoneInfo(tz_name))
        except Exception:
            pass
    return datetime.now().astimezone()


def get_local_date_str(dt: Optional[datetime] = None, tz_name: Optional[str] = None) -> str:
    """Returns 'YYYY-MM-DD' date string in specified timezone or system local timezone."""
    if dt is None:
        dt = get_local_now(tz_name)
    elif dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
        if tz_name:
            try:
                dt = dt.astimezone(ZoneInfo(tz_name))
            except Exception:
                dt = dt.astimezone()
        else:
            dt = dt.astimezone()
    else:
        if tz_name:
            try:
                dt = dt.astimezone(ZoneInfo(tz_name))
            except Exception:
                dt = dt.astimezone()
        else:
            dt = dt.astimezone()
    return dt.strftime("%Y-%m-%d")


def get_lagos_now() -> datetime:
    """Returns current datetime in Africa/Lagos timezone (or system local time fallback)."""
    return datetime.now(LAGOS_TZ)


def get_lagos_date_str(dt: Optional[datetime] = None) -> str:
    """Returns 'YYYY-MM-DD' date string in Africa/Lagos timezone."""
    if dt is None:
        dt = get_lagos_now()
    elif dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc).astimezone(LAGOS_TZ)
    else:
        dt = dt.astimezone(LAGOS_TZ)
    return dt.strftime("%Y-%m-%d")
