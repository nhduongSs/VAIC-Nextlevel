from fastapi import status


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
        super().__init__(status.HTTP_422_UNPROCESSABLE_CONTENT, "VALIDATION_ERROR", message)


class DatabaseException(AppException):
    def __init__(self, message: str = "Database operation failed") -> None:
        super().__init__(status.HTTP_503_SERVICE_UNAVAILABLE, "DATABASE_ERROR", message)


class InternalServerException(AppException):
    def __init__(self, message: str = "Internal server error") -> None:
        super().__init__(status.HTTP_500_INTERNAL_SERVER_ERROR, "INTERNAL_ERROR", message)
