import uuid


def new_uuid() -> uuid.UUID:
    """Generate a new UUID v4."""
    return uuid.uuid4()


def parse_uuid(value: str) -> uuid.UUID:
    """Parse a UUID string, raising ValueError on invalid input."""
    return uuid.UUID(value)
