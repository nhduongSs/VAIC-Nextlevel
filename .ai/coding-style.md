# Coding Style

This document defines how code should be written.

The goal is readability, maintainability and production quality.

---

# General Principles

Prefer readability over cleverness.

Explicit is better than implicit.

Simple is better than complex.

Small modules.

Small functions.

Small classes.

---

# Function Size

Ideal

10–30 lines.

Maximum

50 lines.

If longer

Refactor.

---

# Class Size

Each class should have one responsibility.

Avoid God Objects.

---

# Dependency Injection

Always inject dependencies.

Never instantiate services directly inside services.

Good

DocumentService(
    repository,
    embedding_service
)

Bad

repository = DocumentRepository()

---

# Async Programming

Use async everywhere possible.

Never block the event loop.

Avoid sync database operations.

---

# Type Hints

Always use type hints.

Good

async def search(
    query: str
) -> list[Document]:

Never omit types.

---

# Docstrings

Public functions should include docstrings.

Explain

Purpose

Arguments

Returns

Raises

---

# Logging

Log meaningful events.

Examples

Document uploaded

Embedding generated

Search completed

Never

Log every variable.

Never

Log API keys.

---

# Error Handling

Catch only expected exceptions.

Raise meaningful domain exceptions.

Bad

except Exception:

Good

except SQLAlchemyError:

---

# Validation

Validate at API boundary.

Business validation inside services.

Database constraints inside database.

---

# ORM

Repositories return domain models.

Services should not manipulate ORM internals.

---

# SQL

Prefer ORM.

Raw SQL only when necessary.

Document why.

---

# Comments

Write comments explaining WHY.

Avoid comments explaining WHAT.

Bad

Increment counter

Good

Prevent duplicate processing when retry occurs.

---

# Magic Numbers

Avoid magic numbers.

Use constants.

---

# Configuration

No hardcoded values.

Everything configurable.

---

# Imports

Standard library

↓

Third-party

↓

Local packages

One blank line between groups.

Avoid wildcard imports.

---

# API Design

Always return consistent response models.

Never expose internal database objects.

---

# Response Models

Use DTOs.

Never return ORM entities.

---

# Transactions

Keep transactions short.

Rollback on failure.

Never leave partial writes.

---

# Performance

Avoid unnecessary database queries.

Avoid N+1 queries.

Batch operations when possible.

---

# AI Services

LLM clients

Embedding clients

Retrievers

must be isolated behind interfaces.

Never call providers directly from business logic.

---

# Prompt Building

Never concatenate strings manually.

Use PromptBuilder.

Keep prompts versioned.

---

# Retrieval

Never call Vector Search directly from routers.

Always use RetrievalService.

---

# Testing

Every new service requires

Unit tests.

Critical workflows require

Integration tests.

---

# Review Checklist

Before committing

✓ Ruff passes

✓ MyPy passes

✓ Pytest passes

✓ No TODO left

✓ No commented code

✓ No duplicated logic

✓ Documentation updated

---

# Definition of Done

Code is complete only if

- Clean
- Typed
- Tested
- Logged
- Documented
- Reviewed
- Production ready