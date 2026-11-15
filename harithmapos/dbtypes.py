"""Column types shared by the models."""
from datetime import timezone

from sqlalchemy import DateTime
from sqlalchemy.types import TypeDecorator


class UTCDateTime(TypeDecorator):
    """A moment in time: timezone-aware UTC in Python, `timestamptz` in PostgreSQL.

    Values going in are converted to UTC (a naive value is taken to be UTC).
    Values coming out are always aware UTC, also from SQLite (used by the
    tests), which keeps no time zone.
    """
    impl = DateTime(timezone=True)
    cache_ok = True

    def process_bind_param(self, value, dialect):
        if value is None:
            return None
        if value.tzinfo is None:
            value = value.replace(tzinfo=timezone.utc)
        value = value.astimezone(timezone.utc)
        if dialect.name == 'sqlite':
            return value.replace(tzinfo=None)      # SQLite compares text: store all values the same way
        return value

    def process_result_value(self, value, dialect):
        if value is None:
            return None
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc)
