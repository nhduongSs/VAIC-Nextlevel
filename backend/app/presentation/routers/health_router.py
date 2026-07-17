from datetime import UTC, datetime

from fastapi import APIRouter
from sqlalchemy import text

from app.config import settings
from app.dependencies import DBSession
from app.presentation.schemas.common_schema import HealthResponse

router = APIRouter(prefix="/health", tags=["Health"])


def _health_response() -> HealthResponse:
    return HealthResponse(
        status="ok",
        version=settings.APP_VERSION,
        environment=settings.ENV,
        timestamp=datetime.now(tz=UTC),
    )


@router.get("", response_model=HealthResponse, summary="Health check")
async def health() -> HealthResponse:
    """Basic health check — confirms process is running."""
    return _health_response()


@router.get("/live", response_model=HealthResponse, summary="Liveness probe")
async def liveness() -> HealthResponse:
    """Liveness probe — for container orchestrators."""
    return _health_response()


@router.get("/ready", response_model=HealthResponse, summary="Readiness probe")
async def readiness(session: DBSession) -> HealthResponse:
    """Readiness probe — verifies database connectivity."""
    await session.execute(text("SELECT 1"))
    return _health_response()
