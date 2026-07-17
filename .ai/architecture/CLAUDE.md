# CLAUDE.md

# Enterprise AI Knowledge Assistant

## Purpose

This repository implements an enterprise-grade AI Knowledge Assistant for the banking domain.

The system enables employees to search enterprise knowledge using natural language through a Hybrid Retrieval pipeline and Large Language Models (LLMs).

This project prioritizes:

- Scalability
- Maintainability
- Extensibility
- Performance
- Production readiness

---

# Source of Truth

Before making any changes, always read the following documents in order:

1. .ai/architecture/architecture-freeze.md
2. .ai/architecture/implementation-plan.md
3. Relevant architecture documents
4. Current implementation wave prompt

Architecture documents are the source of truth.

Do not redesign the architecture unless explicitly instructed.

---

# Project Architecture

This project follows:

- Clean Architecture
- Domain Driven Design (Lightweight)
- SOLID Principles
- Repository Pattern
- Dependency Injection
- Async Programming

Dependency direction must always be respected.

Presentation

↓

Application

↓

Domain

↓

Infrastructure

Never violate this dependency flow.

---

# Technology Stack

## Backend

- Python 3.13+
- FastAPI
- SQLAlchemy Async
- Alembic
- Pydantic v2

## Database

- PostgreSQL
- pgvector

## AI

Embedding

- BAAI/bge-m3

Retrieval

- BM25
- Vector Search
- Hybrid Search
- Cross Encoder Re-ranking

LLM

- DeepSeek

## Infrastructure

- Docker
- Docker Compose

---

# High-Level Pipeline

Knowledge Sources

↓

Document Upload

↓

Document Parsing

↓

Metadata Extraction

↓

Classification

↓

Relationship Extraction

↓

Chunking

↓

Embedding

↓

Knowledge Repository

↓

Hybrid Retrieval

↓

Knowledge Intelligence

↓

Prompt Builder

↓

DeepSeek

↓

Final Response

---

# Frozen Architecture Decisions

The following decisions are considered frozen.

Do not modify unless architecture documents are updated.

- PostgreSQL only
- pgvector only
- No Neo4j
- Async implementation
- Hybrid Retrieval
- BGE-M3 embeddings
- DeepSeek as primary LLM
- Repository Pattern
- Dependency Injection
- Clean Architecture

---

# Layer Responsibilities

## API Layer

Responsible for

- HTTP
- Validation
- Authentication
- Response Models

Must NOT contain business logic.

---

## Application Layer

Responsible for

- Use Cases
- Services
- Orchestration

---

## Domain Layer

Responsible for

- Business Rules
- Entities
- Value Objects
- Domain Exceptions

No infrastructure code allowed.

---

## Infrastructure Layer

Responsible for

- Database
- Repository
- External APIs
- Embedding Models
- LLM Clients

---

# Coding Standards

Always

- Use type hints
- Keep functions small
- Keep classes focused
- Write readable code
- Prefer composition over inheritance
- Use dependency injection
- Add structured logging
- Handle exceptions explicitly

Avoid

- Long methods
- Circular dependencies
- Duplicate code
- Hidden side effects
- Global mutable state

---

# Repository Rules

Repositories only perform data access.

Repositories must NOT

- contain business logic
- call LLMs
- implement workflows
- make application decisions

---

# Service Rules

Services contain business logic.

Services may

- call repositories
- call external AI services
- orchestrate workflows

Services must NOT

- return ORM objects directly
- expose database implementation

---

# API Rules

Routers should only

- validate requests
- invoke services
- return responses

Never

- access repositories directly
- perform business logic
- execute SQL

---

# Database Rules

Always

- use Alembic migrations
- use async SQLAlchemy
- use repositories

Never

- write raw SQL unless necessary
- bypass repositories
- duplicate database models

---

# AI Rules

Embedding model

- BAAI/bge-m3

Retrieval strategy

Metadata Filter

↓

BM25

↓

Vector Search

↓

Hybrid Fusion

↓

Cross Encoder

↓

Knowledge Intelligence

↓

Prompt Builder

↓

LLM

Every AI response should support citations whenever possible.

---

# Development Workflow

Before implementing

1. Read architecture documents
2. Review existing implementation
3. Reuse existing modules
4. Identify reusable abstractions
5. Implement only current scope

Never rewrite working modules unnecessarily.

---

# Quality Gates

Every implementation must satisfy:

## Formatting

- Ruff format

## Lint

- Ruff check

## Typing

- MyPy

## Testing

- Pytest

Implementation is NOT complete until every quality gate passes.

---

# Documentation Rules

Whenever implementation changes architecture

Update architecture documents FIRST.

Whenever implementation changes APIs

Update API documentation.

Whenever implementation changes database

Update migration and schema documentation.

---

# Git Guidelines

Keep commits focused.

Avoid unrelated changes.

One implementation objective per commit whenever practical.

---

# Wave Execution

Implement only the current wave.

Never implement future waves early.

Do not introduce speculative abstractions.

---

# Before Finishing Any Wave

Review

- Architecture consistency
- Layer separation
- Naming consistency
- Error handling
- Logging
- Performance

Run

- Ruff
- MyPy
- Pytest

Fix every issue before stopping.

---

# Completion Definition

A wave is complete only if

- Acceptance criteria satisfied
- Code reviewed
- Ruff passed
- MyPy passed
- Pytest passed
- Documentation updated
- No known critical issues remain

Stop only when the implementation is production-ready for the scope of the current wave.