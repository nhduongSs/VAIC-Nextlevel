from uuid import UUID


class DomainException(Exception):
    """Base class for all domain-layer exceptions."""

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


class EntityNotFound(DomainException):
    def __init__(self, entity: str, entity_id: UUID | str) -> None:
        super().__init__(f"{entity} with id '{entity_id}' not found")
        self.entity = entity
        self.entity_id = entity_id


class InvalidEmbeddingDimension(DomainException):
    def __init__(self, expected: int, actual: int) -> None:
        super().__init__(f"Embedding dimension mismatch: expected {expected}, got {actual}")
        self.expected = expected
        self.actual = actual


class InvalidDocumentStatus(DomainException):
    def __init__(self, current: str, target: str) -> None:
        super().__init__(f"Cannot transition document status from '{current}' to '{target}'")
        self.current = current
        self.target = target


class ChunkLimitExceeded(DomainException):
    def __init__(self, max_chunks: int) -> None:
        super().__init__(f"Document exceeds maximum chunk limit of {max_chunks}")
        self.max_chunks = max_chunks


class DuplicateEntity(DomainException):
    def __init__(self, entity: str, field: str, value: str) -> None:
        super().__init__(f"{entity} with {field}='{value}' already exists")
        self.entity = entity
        self.field = field
        self.value = value


class InvariantViolation(DomainException):
    """Raised when a domain invariant is violated."""
