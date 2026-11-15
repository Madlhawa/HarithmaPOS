"""Time helpers: one set of rules for moments in time and calendar days.

* A moment (when a payment was taken, when a job started) is a timezone-aware
  datetime in UTC, everywhere: in Python (`utcnow()`), and in the database,
  where the columns are `timestamptz` (see `UTCDateTime` in dbtypes.py).
* A calendar fact (an attendance day, a payroll month, a time of day on a
  rota) is a plain `date` or `time` in shop time. It is never a timestamp.
* "Today" is the shop's day in Asia/Colombo (`local_today()`), and a day's
  moments are found with `local_day_bounds_utc()`. Times are turned into
  shop time only to show them (`to_local()`).
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
    """Now, as a timezone-aware UTC datetime."""
    return datetime.now(timezone.utc)


def as_utc(dt):
    """Any datetime as aware UTC. A naive one is taken to be UTC already (older code and SQLite)."""
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def to_local(dt, tz_name=DEFAULT_TZ_NAME):
    """A moment in shop time, for showing it."""
    if dt is None:
        return None
    return as_utc(dt).astimezone(get_tz(tz_name))


def local_today(tz_name=DEFAULT_TZ_NAME):
    return to_local(utcnow(), tz_name).date()


def local_day_bounds_utc(day=None, tz_name=DEFAULT_TZ_NAME):
    """Start and end of a shop calendar day, as aware UTC datetimes.

    Use these to filter UTC timestamp columns for "today":
        start, end = local_day_bounds_utc()
        query.filter(Model.created_dttm >= start, Model.created_dttm < end)
    """
    tz = get_tz(tz_name)
    if day is None:
        day = local_today(tz_name)
    start_local = datetime(day.year, day.month, day.day, tzinfo=tz)
    end_local = start_local + timedelta(days=1)
    return start_local.astimezone(timezone.utc), end_local.astimezone(timezone.utc)


def local_range_bounds_utc(first_day, last_day, tz_name=DEFAULT_TZ_NAME):
    """[start of first_day, start of the day after last_day) in shop time, as aware UTC datetimes."""
    start, _ = local_day_bounds_utc(first_day, tz_name)
    _, end = local_day_bounds_utc(last_day, tz_name)
    return start, end


def elapsed_text(since, now=None):
    """'2h 15m' / '12m' since a moment."""
    if since is None:
        return ''
    now = as_utc(now) if now is not None else utcnow()
    seconds = max(int((now - as_utc(since)).total_seconds()), 0)
    hours, remainder = divmod(seconds, 3600)
    minutes = remainder // 60
    if hours >= 24:
        days, hours = divmod(hours, 24)
        return f"{days}d {hours}h"
    if hours:
        return f"{hours}h {minutes:02d}m"
    return f"{minutes}m"
