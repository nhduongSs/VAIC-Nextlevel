from __future__ import annotations

import httpx
import structlog

from app.infrastructure.ai.embedding.embedding_provider import EmbeddingProvider

log = structlog.get_logger(__name__)

_MODEL_NAME = "BAAI/bge-m3"
_DIMENSIONS = 1024
_DEFAULT_TIMEOUT = 60.0  # seconds; BGE-M3 can be slow on first batch


class BgeM3Client(EmbeddingProvider):
    def __init__(self, base_url: str, timeout: float = _DEFAULT_TIMEOUT) -> None:
        self._base_url = base_url.rstrip("/")
        self._timeout = timeout

    @property
    def model_name(self) -> str:
        return _MODEL_NAME

    @property
    def dimensions(self) -> int:
        return _DIMENSIONS

    async def embed(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        async with httpx.AsyncClient(timeout=self._timeout) as client:
            response = await client.post(
                f"{self._base_url}/embed",
                json={"texts": texts},
            )
            response.raise_for_status()
            data = response.json()
        embeddings: list[list[float]] = data["embeddings"]
        if len(embeddings) != len(texts):
            raise ValueError(
                f"Embedding count mismatch: expected {len(texts)}, got {len(embeddings)}"
            )
        for i, vec in enumerate(embeddings):
            if len(vec) != _DIMENSIONS:
                raise ValueError(
                    f"Embedding[{i}] has {len(vec)} dimensions, expected {_DIMENSIONS}"
                )
        return embeddings

    async def health_check(self) -> bool:
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                resp = await client.get(f"{self._base_url}/health")
                return resp.status_code == 200
        except Exception:
            log.warning("bge_m3_health_check_failed", base_url=self._base_url)
            return False
