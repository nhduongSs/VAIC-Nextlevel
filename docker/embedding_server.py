"""
BGE-M3 Embedding + Reranking HTTP Service.

Runs as a standalone FastAPI app inside the embedding-service container.
Exposes:
  POST /embed   — encode texts to 1024-dim vectors
  POST /rerank  — cross-encoder reranking scores
  GET  /health  — liveness check
  GET  /ready   — readiness check for preloaded models
"""

from __future__ import annotations

import asyncio
import logging
import os
from threading import Lock

from fastapi import FastAPI, HTTPException, status
from pydantic import BaseModel
from sentence_transformers import CrossEncoder, SentenceTransformer

logger = logging.getLogger(__name__)

app = FastAPI(title="BGE-M3 Embedding Service", version="1.0.0")

# Loaded lazily; cached in memory for the container lifetime.
# Loading BGE-M3 and the reranker during startup can exceed Docker healthcheck
# timeouts on first run because model downloads are large.
_embedding_model: SentenceTransformer | None = None
_reranker_model: CrossEncoder | None = None  # type: ignore[type-arg]
_embedding_lock = Lock()
_reranker_lock = Lock()
_preload_started = False
_preload_complete = False
_preload_error: str | None = None

EMBEDDING_MODEL_NAME = os.getenv("MODEL_NAME", "BAAI/bge-m3")
RERANKER_MODEL_NAME = os.getenv("RERANKER_MODEL_NAME", "BAAI/bge-reranker-v2-m3")
MODEL_LOAD_STRATEGY = os.getenv("MODEL_LOAD_STRATEGY", "lazy").lower()

VALID_LOAD_STRATEGIES = {"lazy", "background", "startup"}


@app.on_event("startup")
async def preload_models_on_startup() -> None:
    if MODEL_LOAD_STRATEGY not in VALID_LOAD_STRATEGIES:
        raise RuntimeError(
            "MODEL_LOAD_STRATEGY must be one of: lazy, background, startup"
        )

    if MODEL_LOAD_STRATEGY == "lazy":
        logger.info("Model load strategy is lazy; models load on first request")
        return

    if MODEL_LOAD_STRATEGY == "startup":
        logger.info("Model load strategy is startup; loading models before serving")
        await _preload_models(raise_on_error=True)
        return

    logger.info("Model load strategy is background; warming models after startup")
    asyncio.create_task(_preload_models())


async def _preload_models(*, raise_on_error: bool = False) -> None:
    global _preload_started, _preload_complete, _preload_error
    _preload_started = True
    _preload_complete = False
    _preload_error = None
    try:
        await asyncio.gather(
            asyncio.to_thread(get_embedding_model),
            asyncio.to_thread(get_reranker_model),
        )
        _preload_complete = True
        logger.info("Model preload completed successfully")
    except Exception as exc:
        _preload_error = str(exc)
        logger.exception("Model preload failed")
        if raise_on_error:
            raise


def get_embedding_model() -> SentenceTransformer:
    global _embedding_model
    if _embedding_model is None:
        with _embedding_lock:
            if _embedding_model is None:
                logger.info("Loading embedding model: %s", EMBEDDING_MODEL_NAME)
                _embedding_model = SentenceTransformer(EMBEDDING_MODEL_NAME)
                logger.info("Embedding model loaded successfully")
    return _embedding_model


def get_reranker_model() -> CrossEncoder:  # type: ignore[type-arg]
    global _reranker_model
    if _reranker_model is None:
        with _reranker_lock:
            if _reranker_model is None:
                logger.info("Loading reranker model: %s", RERANKER_MODEL_NAME)
                _reranker_model = CrossEncoder(RERANKER_MODEL_NAME)
                logger.info("Reranker model loaded successfully")
    return _reranker_model


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
    load_strategy: str
    embedding_loaded: bool = False
    reranker_loaded: bool = False
    preload_started: bool = False
    preload_complete: bool = False
    preload_error: str | None = None


# ── Endpoints ─────────────────────────────────────────────────────────────────


@app.post("/embed", response_model=EmbedResponse)
async def embed(request: EmbedRequest) -> EmbedResponse:
    if not request.texts:
        raise HTTPException(status_code=400, detail="texts must be non-empty")

    embedding_model = get_embedding_model()
    embeddings: list[list[float]] = embedding_model.encode(
        request.texts,
        normalize_embeddings=True,
        show_progress_bar=False,
    ).tolist()
    return EmbedResponse(embeddings=embeddings)


@app.post("/rerank", response_model=RerankResponse)
async def rerank(request: RerankRequest) -> RerankResponse:
    if not request.passages:
        return RerankResponse(scores=[])

    reranker_model = get_reranker_model()
    pairs = [[request.query, passage] for passage in request.passages]
    scores: list[float] = reranker_model.predict(pairs).tolist()  # type: ignore[union-attr]
    return RerankResponse(scores=scores)


@app.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    return HealthResponse(
        status="ok",
        model=EMBEDDING_MODEL_NAME,
        load_strategy=MODEL_LOAD_STRATEGY,
        embedding_loaded=_embedding_model is not None,
        reranker_loaded=_reranker_model is not None,
        preload_started=_preload_started,
        preload_complete=_preload_complete,
        preload_error=_preload_error,
    )


@app.get("/ready", response_model=HealthResponse)
async def readiness() -> HealthResponse:
    response = await health()
    if response.preload_error is not None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=response.preload_error,
        )
    if (
        MODEL_LOAD_STRATEGY in {"background", "startup"}
        and not response.preload_complete
    ):
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Models are still loading",
        )
    return response
