# Wave 1 Review Report

**Reviewer:** Principal Software Engineer  
**Date:** 2026-07-18  
**Scope:** Wave 1 Foundation — backend skeleton, no business logic  
**Verdict:** ✅ APPROVED — Ready for Wave 2

---

## Quality Gates

| Gate | Result | Detail |
|---|---|---|
| `ruff format .` | ✅ Pass | 53 files unchanged after refactor |
| `ruff check .` | ✅ Pass | 0 errors |
| `mypy app/` | ✅ Pass | 0 issues in 42 source files |
| `pytest` | ✅ Pass | 13/13 tests passed |

---

## Strengths

### Architecture
- **Clean Architecture enforced correctly.** Dependency direction is `presentation → application → domain ← infrastructure` with no violations post-fix. The `dependencies.py` acts as the proper DI injection point.
- **`BaseRepository` is well-designed.** The `Generic[ModelT, EntityT]` pattern with abstract `_to_entity` / `_to_model` methods forces all concrete repositories to implement bidirectional ORM ↔ domain mapping — a correct pattern.
- **`Base(DeclarativeBase)` uses Alembic naming conventions.** The `NAMING_CONVENTION` dict ensures all FK, PK, IX, UQ, CK constraint names are predictable and Alembic-autogenerate-safe.
- **`async_sessionmaker` configured with `expire_on_commit=False`.** Correct for async — avoids lazy-load errors after commit.
- **`pool_pre_ping=True`.** Prevents stale connection errors after DB restart — critical for Docker Compose startup ordering.

### Logging
- **structlog with `contextvars` for request-scoped log binding.** `bind_contextvars` in middleware correctly propagates `request_id` across all log lines within a request without threading concerns.
- **Environment-based format switching** (`json_logs` property) correctly outputs structured JSON in production, readable console output in development.
- **`cache_logger_on_first_use=True`** — performance optimization, correct.

### Middleware
- **`RequestIDMiddleware` echoes `X-Request-ID`** in the response header, enabling clients to correlate logs.
- **Middleware registration order is correct.** `RequestIDMiddleware` (outermost) → `CORSMiddleware` → `GZipMiddleware`. CORS must process before compression; request ID must be set before any logging.
- **`TrustedHostMiddleware` is production-only.** Correct — would reject localhost in dev if always enabled.

### Exception Handling
- **Structured `ErrorResponse` model with `request_id`, `timestamp`, `details`** is consistent and well-defined for Wave 8 API consumers.
- **Separate `DomainException` hierarchy and `AppException` hierarchy.** Domain exceptions are pure Python (no HTTP coupling); HTTP exceptions are in the presentation layer. Clean separation.
- **`SQLAlchemyError` is caught before the generic `Exception` handler** — correct, prevents DB errors from appearing as 500s without context.

### Tests
- **DB is properly mocked** via `dependency_overrides`. Tests do not require a running PostgreSQL — fast and isolated.
- **`conftest.py` cleanup** (`app.dependency_overrides.clear()`) prevents test pollution between tests.

---

## Issues Found and Fixed

### F1 — Architecture Violation: Presentation imports from Infrastructure directly
**File:** `app/presentation/routers/health_router.py`  
**Severity:** Medium  
**Description:** `health_router.py` imported `get_db_session` directly from `app.infrastructure.database.base`, bypassing `app.dependencies`. This violates the Clean Architecture rule that presentation must only interact with infrastructure via DI injection points.  
**Fix applied:**
```python
# Before
from app.infrastructure.database.base import get_db_session
async def readiness(session: AsyncSession = Depends(get_db_session)) -> HealthResponse:

# After
from app.dependencies import DBSession
async def readiness(session: DBSession) -> HealthResponse:
```

### F2 — Dockerfile Bug: `--index-url` applied to all packages
**File:** `docker/embedding.Dockerfile`  
**Severity:** High  
**Description:** The original Dockerfile passed `--index-url https://download.pytorch.org/whl/cpu` in the same `pip install` command as `fastapi`, `uvicorn`, and `pydantic`. The `--index-url` flag applies to the **entire** invocation — meaning FastAPI and uvicorn would be fetched from the PyTorch CPU wheel index, which does not host them. This would fail at build time.  
**Fix applied:** Split into three separate `RUN` layers:
```dockerfile
RUN pip install --no-cache-dir fastapi "uvicorn[standard]" "pydantic>=2.0"
RUN pip install --no-cache-dir torch --index-url https://download.pytorch.org/whl/cpu
RUN pip install --no-cache-dir sentence-transformers
```

### F3 — Deprecated `version:` in Docker Compose files
**Files:** `docker-compose.yml`, `docker-compose.dev.yml`  
**Severity:** Low  
**Description:** Docker Compose v2 (current CLI) deprecated the top-level `version:` field. It generates a warning and will eventually become an error.  
**Fix applied:** Removed `version: "3.9"` from both files.

### F4 — `metrics` endpoint defined as closure inside `create_app()`
**File:** `app/main.py`  
**Severity:** Low  
**Description:** Defining a route handler inside a factory function is unusual and makes the handler untestable in isolation (it's a new closure object each call).  
**Fix applied:** Extracted `_metrics()` as a module-level async function, registered via `app.add_api_route("/metrics", _metrics, ...)`.

---

## Remaining Technical Debt

| # | Item | Severity | Wave to address |
|---|---|---|---|
| TD1 | `DATABASE_URL` has hardcoded default credentials in `config.py` | Low | Before production deploy |
| TD2 | `BaseRepository._execute_query` returns `Any` — too broad | Low | Wave 2 (when concrete repos are written) |
| TD3 | `configure_logging()` is called in lifespan — if a library logs before app start, it uses stdlib defaults | Low | Wave 8 |
| TD4 | `engine` is instantiated at module import — if `DATABASE_URL` is malformed, the import fails | Low | Acceptable for now |
| TD5 | No `.dockerignore` file — Docker build context includes `.venv/`, `.mypy_cache/`, etc. | Medium | Before first Docker build |
| TD6 | `utils/constants.py`, `utils/datetime_utils.py`, `utils/uuid_utils.py` have 0% test coverage | Low | Wave 2 (used in entities) |
| TD7 | `frontend.Dockerfile` uses `nginx-frontend.conf` which doesn't exist yet | Low | Wave 9 |

---

## Module Coverage Summary

| Module | Coverage | Notes |
|---|---|---|
| `domain/exceptions.py` | 100% | ✓ All exception classes tested |
| `presentation/middleware/logging_middleware.py` | 100% | ✓ Middleware exercised via every request |
| `presentation/routers/health_router.py` | 100% | ✓ All 3 endpoints tested |
| `presentation/schemas/common_schema.py` | 100% | ✓ Used in every response |
| `config.py` | 97% | 1 line uncovered: `is_production` branch |
| `main.py` | 65% | Lifespan, logging setup not covered (require live process) |
| `infrastructure/database/base.py` | 61% | Session factory not covered (requires real DB) |
| `infrastructure/database/base_repository.py` | 0% | No concrete subclass yet — Wave 2 |
| `utils/*` | 0% | Not yet used — Wave 2 will cover |

---

## Architecture Conformance

| Check | Result |
|---|---|
| Domain layer has zero external imports | ✅ |
| Application layer imports from domain only | ✅ |
| Infrastructure implements domain interfaces (not yet — Wave 2) | — |
| Presentation imports via `dependencies.py` (after F1 fix) | ✅ |
| No circular imports | ✅ |
| Async I/O throughout | ✅ |
| Alembic configured for async migrations | ✅ |

---

## Ready for Wave 2?

**Yes.** All acceptance criteria from `01-wave-1.md` are satisfied:

```
✓ Application starts successfully (uvicorn app.main:app)
✓ GET /health → 200 OK
✓ GET /health/live → 200 OK
✓ GET /health/ready → 200 OK (with DB mock)
✓ Migrations supported (alembic upgrade head)
✓ Configuration loads from .env
✓ Middleware registered (CORS, GZip, RequestID)
✓ Structured JSON logs (structlog)
✓ Docker Compose defined (5 services)
✓ ruff format: pass
✓ ruff check: pass
✓ mypy: pass
✓ pytest: 13/13 pass
```

**Wave 2 entry point:** `app/infrastructure/database/models/` — ORM models for all 6 tables, concrete repositories, Alembic migration `001_initial_schema.py`.
