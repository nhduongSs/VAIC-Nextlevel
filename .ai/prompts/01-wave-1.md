# Wave 1 — Foundation

## ROLE

You are a Principal Backend Engineer responsible for implementing the project foundation.

The project architecture has already been designed, reviewed, and frozen.

Your responsibility is to implement ONLY the infrastructure foundation required for future waves.

Do NOT redesign the architecture.

Do NOT implement any AI, RAG, Retrieval, LLM, Document Processing, or Business Features.

---

# Read First

Before writing any code, read the following documents in order:

1. CLAUDE.md

2. .ai/architecture/architecture-freeze.md

3. .ai/architecture/implementation-plan.md

4. All relevant architecture documents

Treat them as immutable specifications.

---

# Existing Code Review

Before implementing:

- Review the existing repository structure.
- Detect duplicate implementations.
- Detect reusable modules.
- Detect unfinished infrastructure.
- Reuse existing abstractions whenever possible.

Never rewrite working modules unnecessarily.

---

# Objective

Build the complete project foundation.

This wave establishes the infrastructure required for every future implementation.

The repository should be production-ready as a backend skeleton after this wave.

No business logic should exist.

---

# Scope

Implement ONLY the following modules.

## Project Structure

Create the complete backend folder structure.

Example

backend/

app/

api/

core/

config/

database/

domain/

application/

infrastructure/

repositories/

services/

schemas/

models/

middleware/

exceptions/

logging/

utils/

tests/

scripts/

---

## Dependency Management

Configure

- pyproject.toml
- uv
- Ruff
- MyPy
- Pytest

Configure development dependencies.

---

## Configuration

Implement

Settings

Environment loader

Configuration validation

Typed configuration

Separate

Development

Testing

Production

---

## Logging

Implement

Structured logging

Request logging

Startup logging

Error logging

JSON logging support

---

## Database

Configure

Async SQLAlchemy

Session Factory

Database Engine

Dependency Injection

Health Check

Database lifespan

---

## Alembic

Configure

Migration environment

Migration template

Base metadata

Migration command support

No business tables yet.

---

## Dependency Injection

Implement

Dependency container

Application dependencies

Repository dependencies

Service dependencies

Database dependencies

---

## Middleware

Implement

Request ID

Exception middleware

Logging middleware

CORS

Trusted Host

Compression

---

## Exception Handling

Implement

Base exception

Validation exception

Database exception

NotFound exception

Conflict exception

InternalServerError

Global exception handler

Standard error response model

---

## Health APIs

Implement

GET /health

GET /health/live

GET /health/ready

Each endpoint should return structured responses.

---

## API Initialization

Configure

FastAPI

Application lifespan

Router registration

OpenAPI metadata

Swagger

ReDoc

Versioning

---

## Base Repository

Implement reusable base repository abstraction.

No business repositories.

---

## Base Service

Implement reusable service abstraction.

No business services.

---

## Utilities

Implement

UUID helper

Datetime helper

Pagination models

Response models

Common constants

---

## Docker

Implement

Dockerfile

docker-compose.yml

Development environment

Database service

Volume mapping

Environment variables

---

## Scripts

Create development scripts.

Examples

Run application

Run migrations

Create migration

Lint

Format

Type check

Test

---

# Explicitly Out of Scope

Do NOT implement

- Upload APIs
- Document Processing
- OCR
- Chunking
- Embedding
- Vector Search
- BM25
- Hybrid Retrieval
- DeepSeek
- Prompt Builder
- Chat
- Authentication
- Authorization
- Knowledge Intelligence
- AI Features

Those belong to later waves.

---

# Deliverables

By the end of this wave, the repository should contain

- Project structure
- Dependency management
- Configuration system
- Logging
- Async database
- Alembic
- Middleware
- Exception handling
- Health APIs
- Docker
- Base repository
- Base service
- Development tooling

---

# Acceptance Criteria

The project should

✓ Start successfully

✓ Connect to PostgreSQL

✓ Expose health endpoints

✓ Support migrations

✓ Load configuration correctly

✓ Register middleware

✓ Produce structured logs

✓ Start via Docker Compose

No business features should exist.

---

# Code Quality Requirements

Follow

- Clean Architecture
- SOLID
- Repository Pattern
- Dependency Injection
- Async Programming

Never violate layer boundaries.

---

# Final Review

Before finishing

Review

- Folder organization
- Naming consistency
- Layer separation
- Dependency direction
- Configuration
- Logging
- Database
- Middleware
- Exception handling

Remove

- Dead code
- Duplicate code
- Temporary implementations
- TODO comments

---

# Quality Gates

Run

ruff format .

ruff check .

mypy .

pytest

Fix every issue until all commands pass.

---

# Documentation

Update documentation if implementation differs from the frozen architecture.

Do not modify architecture unless absolutely necessary.

---

# Completion Definition

Stop only when

✓ All acceptance criteria are satisfied

✓ Ruff passes

✓ MyPy passes

✓ Pytest passes

✓ Docker starts successfully

✓ Health APIs work

✓ Code review completed

✓ Documentation updated

The repository should now be ready for Wave 2.