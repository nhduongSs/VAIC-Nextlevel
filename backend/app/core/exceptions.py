"""Combined exceptions from domain/exceptions.py and presentation/exceptions.py."""

from uuid import UUID

from fastapi import status

# ── Domain Exceptions ─────────────────────────────────────────────────────────


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
        super().__init__(
            f"Embedding dimension mismatch: expected {expected}, got {actual}"
        )
        self.expected = expected
        self.actual = actual


class InvalidDocumentStatus(DomainException):
    def __init__(self, current: str, target: str) -> None:
        super().__init__(
            f"Cannot transition document status from '{current}' to '{target}'"
        )
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


# ── HTTP / Application Exceptions ─────────────────────────────────────────────


class AppException(Exception):
    """Base HTTP exception with structured error info."""

    def __init__(
        self,
        status_code: int,
        error: str,
        message: str,
    ) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.error = error
        self.message = message


class NotFoundException(AppException):
    def __init__(self, message: str = "Resource not found") -> None:
        super().__init__(status.HTTP_404_NOT_FOUND, "NOT_FOUND", message)


class ConflictException(AppException):
    def __init__(self, message: str = "Resource already exists") -> None:
        super().__init__(status.HTTP_409_CONFLICT, "CONFLICT", message)


class UnauthorizedException(AppException):
    def __init__(self, message: str = "Authentication required") -> None:
        super().__init__(status.HTTP_401_UNAUTHORIZED, "UNAUTHORIZED", message)


class ForbiddenException(AppException):
    def __init__(self, message: str = "Access denied") -> None:
        super().__init__(status.HTTP_403_FORBIDDEN, "FORBIDDEN", message)


class ValidationException(AppException):
    def __init__(self, message: str = "Validation failed") -> None:
        super().__init__(
            status.HTTP_422_UNPROCESSABLE_ENTITY, "VALIDATION_ERROR", message
        )


class DatabaseException(AppException):
    def __init__(self, message: str = "Database operation failed") -> None:
        super().__init__(status.HTTP_503_SERVICE_UNAVAILABLE, "DATABASE_ERROR", message)


class InternalServerException(AppException):
    def __init__(self, message: str = "Internal server error") -> None:
        super().__init__(
            status.HTTP_500_INTERNAL_SERVER_ERROR, "INTERNAL_ERROR", message
        )
