from httpx import AsyncClient

from app.presentation.exceptions import NotFoundException


async def test_404_returns_structured_error(client: AsyncClient) -> None:
    response = await client.get("/api/v1/does-not-exist")
    assert response.status_code == 404


async def test_error_response_has_request_id(client: AsyncClient) -> None:
    response = await client.get(
        "/this-does-not-exist",
        headers={"X-Request-ID": "test-request-123"},
    )
    assert response.headers.get("X-Request-ID") == "test-request-123"


async def test_domain_exception_hierarchy() -> None:
    exc = NotFoundException("Document not found")
    assert exc.status_code == 404
    assert exc.error == "NOT_FOUND"
    assert exc.message == "Document not found"
