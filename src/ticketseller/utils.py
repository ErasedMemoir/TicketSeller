from __future__ import annotations

from datetime import datetime, timezone


def as_utc(value: datetime) -> datetime:
    """Return a timezone-aware UTC datetime."""
    if value.tzinfo is None:
        # Treat naive datetimes as local time before conversion.
        return value.astimezone().astimezone(timezone.utc)
    return value.astimezone(timezone.utc)
