"""Prompt debugging endpoints — /api/v1/prompt/build and /preview."""
from __future__ import annotations

from typing import Any

import structlog
from fastapi import APIRouter, Depends, HTTPException

from app.core.dependencies import get_prompt_builder
from app.generation.prompt.builder import PromptBuilder
from app.generation.prompt.config import PromptConfig, PromptType
from app.models.schemas import (
    PromptBuildRequest,
    PromptBuildResponse,
    PromptPreviewResponse,
)
from app.services.document_relation_service import ContextPackage

log: structlog.stdlib.BoundLogger = structlog.get_logger(__name__)

router = APIRouter(prefix="/api/v1/prompt", tags=["Prompt"])


def _resolve_prompt_type(raw: str) -> PromptType:
    try:
        return PromptType(raw.lower())
    except ValueError:
        raise HTTPException(
            status_code=422,
            detail=(
                f"Invalid prompt_type '{raw}'. "
                f"Must be one of: {[t.value for t in PromptType]}"
            ),
        )


def _empty_context_package(question: str) -> ContextPackage:
    """Return an empty ContextPackage containing only the question."""
    return ContextPackage(
        query=question,
        ranked_chunks=[],
        citations=[],
        relationships=[],
        conflicts=[],
        timeline=[],
        metadata={},
        statistics={},
    )


@router.post(
    "/build",
    response_model=PromptBuildResponse,
    summary="Build và kiểm tra prompt từ câu hỏi mẫu",
)
async def build_prompt(
    body: PromptBuildRequest,
    builder: PromptBuilder = Depends(get_prompt_builder),
) -> PromptBuildResponse:
    """Build a prompt from *question* (using an empty context package).

    Useful for inspecting the system and user prompt templates without
    running the full retrieval pipeline.
    """
    prompt_type = _resolve_prompt_type(body.prompt_type)

    # Override max_chunks in a fresh config so the builder respects it
    config = PromptConfig(
        prompt_type=prompt_type,
        max_context_chunks=body.max_chunks,
    )
    local_builder = PromptBuilder(config=config)

    context_package = _empty_context_package(body.question)
    package = local_builder.build(context_package, prompt_type=prompt_type)

    log.debug(
        "prompt_build",
        prompt_type=prompt_type.value,
        estimated_total_tokens=package.estimated_total_tokens,
        was_truncated=package.was_truncated,
    )

    return PromptBuildResponse(
        prompt_type=package.prompt_type.value,
        system_prompt=package.system_prompt,
        user_prompt=package.user_prompt,
        estimated_prompt_tokens=package.estimated_prompt_tokens,
        estimated_completion_tokens=package.estimated_completion_tokens,
        estimated_total_tokens=package.estimated_total_tokens,
        context_chunks_used=package.context_chunks_used,
        was_truncated=package.was_truncated,
    )


@router.post(
    "/preview",
    response_model=PromptPreviewResponse,
    summary="Preview prompt với metadata đầy đủ",
)
async def preview_prompt(
    body: PromptBuildRequest,
    builder: PromptBuilder = Depends(get_prompt_builder),
) -> PromptPreviewResponse:
    """Same as ``/build`` but includes the config and an optimization flag."""
    prompt_type = _resolve_prompt_type(body.prompt_type)

    config = PromptConfig(
        prompt_type=prompt_type,
        max_context_chunks=body.max_chunks,
    )
    local_builder = PromptBuilder(config=config)

    context_package = _empty_context_package(body.question)
    package = local_builder.build(context_package, prompt_type=prompt_type)

    config_dict: dict[str, Any] = {
        "prompt_type": config.prompt_type.value,
        "max_prompt_tokens": config.max_prompt_tokens,
        "max_completion_tokens": config.max_completion_tokens,
        "max_context_chunks": config.max_context_chunks,
        "max_citations": config.max_citations,
        "include_timeline": config.include_timeline,
        "include_conflicts": config.include_conflicts,
        "include_relationships": config.include_relationships,
        "language": config.language,
    }

    return PromptPreviewResponse(
        prompt_type=package.prompt_type.value,
        system_prompt=package.system_prompt,
        user_prompt=package.user_prompt,
        estimated_prompt_tokens=package.estimated_prompt_tokens,
        estimated_completion_tokens=package.estimated_completion_tokens,
        estimated_total_tokens=package.estimated_total_tokens,
        context_chunks_used=package.context_chunks_used,
        was_truncated=package.was_truncated,
        config=config_dict,
        optimization_applied=True,
    )
