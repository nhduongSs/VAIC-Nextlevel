from datetime import UTC, datetime
from typing import Generic, TypeVar
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

T = TypeVar("T")


class ErrorDetail(BaseModel):
    field: str | None = None
    message: str


class ErrorResponse(BaseModel):
    error: str
    message: str
    request_id: str | None = None
    details: list[ErrorDetail] = Field(default_factory=list)
    timestamp: datetime = Field(default_factory=lambda: datetime.now(tz=UTC))


class HealthResponse(BaseModel):
    status: str
    version: str
    environment: str
    timestamp: datetime


class PaginationMeta(BaseModel):
    total: int
    limit: int
    offset: int
    has_next: bool
    has_prev: bool


class PaginatedResponse(BaseModel, Generic[T]):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    data: list[T]
    meta: PaginationMeta


class IDResponse(BaseModel):
    id: UUID


class MessageResponse(BaseModel):
    message: str


class OKResponse(BaseModel):
    ok: bool = True
