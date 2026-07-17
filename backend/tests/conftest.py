from collections.abc import AsyncGenerator
from unittest.mock import AsyncMock

import pytest
from httpx import ASGITransport, AsyncClient

from app.infrastructure.database.base import get_db_session
from app.main import app


@pytest.fixture
async def mock_db_session() -> AsyncGenerator[AsyncMock, None]:
    session = AsyncMock()
    session.execute = AsyncMock(return_value=AsyncMock(scalar_one_or_none=lambda: None))
    session.commit = AsyncMock()
    session.rollback = AsyncMock()
    yield session


@pytest.fixture
async def client(mock_db_session: AsyncMock) -> AsyncGenerator[AsyncClient, None]:
    async def override_get_db() -> AsyncGenerator[AsyncMock, None]:
        yield mock_db_session

    app.dependency_overrides[get_db_session] = override_get_db

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as c:
        yield c

    app.dependency_overrides.clear()
