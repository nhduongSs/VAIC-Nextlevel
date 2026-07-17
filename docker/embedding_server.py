"""
BGE-M3 Embedding + Reranking HTTP Service.

Runs as a standalone FastAPI app inside the embedding-service container.
Exposes:
  POST /embed   — encode texts to 1024-dim vectors
  POST /rerank  — cross-encoder reranking scores
  GET  /health  — liveness check
"""

from __future__ import annotations

import logging
from typing import Any

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from sentence_transformers import CrossEncoder, SentenceTransformer

logger = logging.getLogger(__name__)

app = FastAPI(title="BGE-M3 Embedding Service", version="1.0.0")

# Loaded once at startup; cached in memory for the container lifetime
_embedding_model: SentenceTransformer | None = None
_reranker_model: CrossEncoder | None = None  # type: ignore[type-arg]

EMBEDDING_MODEL_NAME = "BAAI/bge-m3"
RERANKER_MODEL_NAME = "BAAI/bge-reranker-v2-m3"


@app.on_event("startup")
async def load_models() -> None:
    global _embedding_model, _reranker_model
    logger.info("Loading embedding model: %s", EMBEDDING_MODEL_NAME)
    _embedding_model = SentenceTransformer(EMBEDDING_MODEL_NAME)
    logger.info("Loading reranker model: %s", RERANKER_MODEL_NAME)
    _reranker_model = CrossEncoder(RERANKER_MODEL_NAME)
    logger.info("Models loaded successfully")


# ── Request / Response Schemas ────────────────────────────────────────────────


class EmbedRequest(BaseModel):
    texts: list[str]


class EmbedResponse(BaseModel):
    embeddings: list[list[float]]
    model: str = EMBEDDING_MODEL_NAME


class RerankRequest(BaseModel):
    query: str
    passages: list[str]


class RerankResponse(BaseModel):
    scores: list[float]
    model: str = RERANKER_MODEL_NAME


class HealthResponse(BaseModel):
    status: str
    model: str


# ── Endpoints ─────────────────────────────────────────────────────────────────


@app.post("/embed", response_model=EmbedResponse)
async def embed(request: EmbedRequest) -> EmbedResponse:
    if _embedding_model is None:
        raise HTTPException(status_code=503, detail="Embedding model not loaded")
    if not request.texts:
        raise HTTPException(status_code=400, detail="texts must be non-empty")

    embeddings: list[list[float]] = (
        _embedding_model.encode(
            request.texts,
            normalize_embeddings=True,
            show_progress_bar=False,
        )
        .tolist()
    )
    return EmbedResponse(embeddings=embeddings)


@app.post("/rerank", response_model=RerankResponse)
async def rerank(request: RerankRequest) -> RerankResponse:
    if _reranker_model is None:
        raise HTTPException(status_code=503, detail="Reranker model not loaded")
    if not request.passages:
        return RerankResponse(scores=[])

    pairs = [[request.query, passage] for passage in request.passages]
    scores: list[float] = _reranker_model.predict(pairs).tolist()  # type: ignore[union-attr]
    return RerankResponse(scores=scores)


@app.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    if _embedding_model is None:
        raise HTTPException(status_code=503, detail="Model not ready")
    return HealthResponse(status="ok", model=EMBEDDING_MODEL_NAME)
