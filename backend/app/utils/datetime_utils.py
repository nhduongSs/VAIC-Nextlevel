from datetime import UTC, datetime


def utcnow() -> datetime:
    """Return current UTC datetime (timezone-aware)."""
    return datetime.now(tz=UTC)


def to_utc(dt: datetime) -> datetime:
    """Convert a naive or tz-aware datetime to UTC."""
    if dt.tzinfo is None:
        return dt.replace(tzinfo=UTC)
    return dt.astimezone(UTC)
