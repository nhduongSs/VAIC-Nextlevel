"""Aggregate router — imports all sub-routers and registers them on one APIRouter."""

from fastapi import APIRouter

from app.api import (
    auth,
    chat,
    documents,
    embeddings,
    health,
    ingestion,
    prompt,
    retrieval,
    search,
)

router = APIRouter()

# Health / liveness / readiness probes
router.include_router(health.router)

# Auth (login, current user)
router.include_router(auth.router)

# Document CRUD
router.include_router(documents.router)

# Embedding pipeline
router.include_router(embeddings.router)

# Ingestion pipeline (process, chunks, relationships)
router.include_router(ingestion.router)

# Hybrid search
router.include_router(search.router)

# Retrieval + Knowledge Intelligence
router.include_router(retrieval.router)

# Chat (Wave 4)
router.include_router(chat.router)

# Prompt building / debugging (Wave 4)
router.include_router(prompt.router)
