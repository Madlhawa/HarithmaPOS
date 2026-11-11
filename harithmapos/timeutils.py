"""Time helpers.

The database stores naive UTC timestamps (the model defaults use utcnow).
Everything a person reads on screen should be in shop time, and "today"
should mean the shop's calendar day rather than the server's.
"""

from datetime import datetime, timedelta, timezone

try:
    from zoneinfo import ZoneInfo
except ImportError:  # pragma: no cover - Python < 3.9
    ZoneInfo = None

DEFAULT_TZ_NAME = 'Asia/Colombo'
# Sri Lanka has no daylight saving, so a fixed offset is a safe fallback
# on servers that do not ship the tz database.
_FALLBACK_TZ = timezone(timedelta(hours=5, minutes=30), 'Asia/Colombo')


def get_tz(name=DEFAULT_TZ_NAME):
    if ZoneInfo is not None:
        try:
            return ZoneInfo(name)
        except Exception:
            pass
    return _FALLBACK_TZ


def utcnow():
    """Naive UTC 'now', matching what the model column defaults store."""
    return datetime.now(timezone.utc).replace(tzinfo=None)


def to_local(dt, tz_name=DEFAULT_TZ_NAME):
    """Convert a naive UTC datetime from the database to shop time."""
    if dt is None:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(get_tz(tz_name))


def local_today(tz_name=DEFAULT_TZ_NAME):
    return to_local(utcnow(), tz_name).date()


def local_day_bounds_utc(day=None, tz_name=DEFAULT_TZ_NAME):
    """Start and end of a shop calendar day, as naive UTC datetimes.

    Use these to filter UTC timestamp columns for "today":
        start, end = local_day_bounds_utc()
        query.filter(Model.created_dttm >= start, Model.created_dttm < end)
    """
    tz = get_tz(tz_name)
    if day is None:
        day = local_today(tz_name)
    start_local = datetime(day.year, day.month, day.day, tzinfo=tz)
    end_local = start_local + timedelta(days=1)
    start = start_local.astimezone(timezone.utc).replace(tzinfo=None)
    end = end_local.astimezone(timezone.utc).replace(tzinfo=None)
    return start, end


def elapsed_text(since, now=None):
    """'2h 15m' / '12m' since a naive UTC datetime."""
    if since is None:
        return ''
    now = now or utcnow()
    seconds = max(int((now - since).total_seconds()), 0)
    hours, remainder = divmod(seconds, 3600)
    minutes = remainder // 60
    if hours >= 24:
        days, hours = divmod(hours, 24)
        return f"{days}d {hours}h"
    if hours:
        return f"{hours}h {minutes:02d}m"
    return f"{minutes}m"
