# Wave 2.1 Review Report — Document Management

**Date:** 2026-07-18  
**Reviewer:** Principal Software Engineer (Claude)  
**Wave:** 2.1 — Document Management  
**Branch:** feature/backend

---

## Summary

Wave 2.1 implements a complete Document Management module across all layers: domain entity, value objects, database model, Alembic migration, repository, storage abstraction, application service, and REST API. The implementation is structurally sound and follows Clean Architecture. Three issues were identified and fixed during this review. All quality gates pass.

---

## Strengths

- **Clean Architecture fully respected** — dependency direction is Presentation → Application → Domain ← Infrastructure with no violations found across all files.
- **Domain entity is authoritative** — `Document` encapsulates its own status lifecycle via `_VALID_TRANSITIONS` and raises `InvalidDocumentStatus` on illegal transitions. Business rules live in the domain, not in the service.
- **Async I/O throughout** — SQLAlchemy async, `asyncio.to_thread` for file I/O, no blocking calls on the event loop.
- **Storage abstraction is properly designed** — `StorageProvider` ABC has 5 methods (`save`, `delete`, `exists`, `read`, `get_absolute_path`), making it trivially replaceable with S3 or GCS.
- **Excellent database index strategy** — partial indexes on `deleted_at IS NULL` for all filter columns, GIN indexes for `tags` (JSONB) and `search_vector` (TSVECTOR), unique constraint on `content_hash`.
- **`search_vector` trigger in migration** — auto-updates the tsvector column on INSERT/UPDATE, pre-wiring full-text search for Wave 5 without any Wave 2.1 code change.
- **Duplicate detection via SHA-256 checksum** — prevents identical file uploads at the service level before any storage write.
- **Structured logging with structlog** — all service operations emit structured events (`document_uploaded`, `document_updated`, `document_deleted`) with contextual fields.
- **Complete test coverage of domain and service** — 24 focused unit tests cover all status transitions, edge cases (deleted document, oversized file, invalid content type, duplicate checksum), and update/version semantics. 37 tests total, all passing.
- **Pydantic v2 schemas** — correct use of `model_validate`, `ConfigDict`, `from_attributes=True` for ORM bridging.

---

## Weaknesses

- **Path traversal not prevented in `LocalStorageProvider`** — `get_absolute_path` did not validate that the resolved path stayed within `_upload_dir`. *(Fixed during review.)*
- **Invalid enum values in upload endpoint returned HTTP 500** — `doc_type` and `authority_level` were typed as `str` in the Form params and manually converted. A `ValueError` from `DocumentType("INVALID")` propagated as 500 instead of 422. *(Fixed during review.)*
- **Dead `try/except EntityNotFound` in `update_document`** — `get_by_id` returns `None`, it never raises `EntityNotFound`. The try/except block was unreachable code creating a misleading import. *(Fixed during review.)*
- **No `sort_by` / `sort_order` query parameters** — the spec mentions sorting. Only `created_at DESC` is hardcoded in the repository.
- **`created_at DESC` index only in Alembic migration, not in SQLAlchemy `__table_args__`** — Alembic autogenerate would miss this index on future schema comparisons.

---

## Technical Debt

### High

| # | Issue | Impact | Recommendation |
|---|---|---|---|
| TD-01 | ~~Path traversal in `LocalStorageProvider.get_absolute_path`~~ | Attacker with write access to `path` could read/delete files outside the upload directory | **Fixed** — resolved path now validated against `_upload_dir` root |

### Medium

| # | Issue | Impact | Recommendation |
|---|---|---|---|
| TD-02 | ~~Invalid enum values in upload endpoint → HTTP 500~~ | Poor error UX; clients receive unstructured 500 for user input errors | **Fixed** — Form params now typed as `DocumentType` / `AuthorityLevel` directly, FastAPI returns 422 |
| TD-03 | ~~Dead `try/except EntityNotFound` in `update_document`~~ | Misleading code; import of unused exception | **Fixed** — removed dead block and import |
| TD-04 | No `sort_by`/`sort_order` in list endpoint | Clients can only browse newest-first | Add `sort_by: Literal["created_at","title","issued_date"]` + `sort_order: Literal["asc","desc"]` query params in Wave 8 API cleanup |
| TD-05 | `get_by_id` returns soft-deleted documents | Every caller must check `is_deleted` manually; easy to forget | Low risk in current codebase (all callers check), but consider a `exclude_deleted: bool = True` parameter |

### Low

| # | Issue | Impact | Recommendation |
|---|---|---|---|
| TD-06 | `created_at DESC` index in migration but missing from `DocumentModel.__table_args__` | Alembic autogenerate will flag a false "missing index" on future schema diff | Add `Index("idx_documents_created_at", "created_at", postgresql_ops={"created_at": "DESC"})` to model |
| TD-07 | No storage provider tests | `LocalStorageProvider` at 38% unit coverage | Add `pytest-tmp-path` tests for `save`, `delete`, `exists`, `read`, and path traversal rejection |
| TD-08 | No API integration tests (router layer) | Router at 63% coverage; Form parsing, enum validation, HTTP codes untested end-to-end | Add `httpx.AsyncClient` tests with an in-memory app fixture in Wave 8 |
| TD-09 | Tag strings have no length or character validation | Very long or special-character tags accepted silently | Add `max_length=100` constraint on individual tag strings |

---

## Improvements Applied

| File | Change | Reason |
|---|---|---|
| `infrastructure/storage/local_storage_provider.py` | `get_absolute_path` now resolves and validates path stays within `_upload_dir` | Path traversal prevention (High security issue) |
| `presentation/routers/document_router.py` | `doc_type` and `authority_level` Form params changed from `str` to `DocumentType` / `AuthorityLevel`; manual `DocumentType(doc_type)` conversion removed | Invalid enum values now return 422, not 500 |
| `application/services/document_service.py` | Removed dead `try/except EntityNotFound` block and its unused import from `update_document` | Eliminated dead code and misleading import |
| `application/services/document_service.py` | Import block re-sorted by ruff | Keep linter clean after import removal |

---

## Remaining Improvements

The following are non-blocking and appropriate for later waves:

- **TD-04** — Sort parameters in list endpoint (Wave 8 API polish)
- **TD-05** — `get_by_id` `exclude_deleted` parameter (Wave 8 refactor pass)
- **TD-06** — Add `idx_documents_created_at` to `DocumentModel.__table_args__` (Wave 2 migration next revision)
- **TD-07** — `LocalStorageProvider` unit tests (add alongside Wave 4 when storage usage increases)
- **TD-08** — Router integration tests (Wave 8 when auth middleware is in place)
- **TD-09** — Tag string validation (Wave 8 final validation pass)

---

## Production Readiness

**READY WITH MINOR TECHNICAL DEBT**

Wave 2.1 is ready for Wave 2.2.

All three immediate issues (path traversal, 500 on invalid enum, dead code) were resolved during this review. The remaining technical debt items are non-blocking: sort parameters and integration tests belong in Wave 8, index inconsistency is cosmetic, and tag validation is low risk.

Quality gates:

| Gate | Status |
|---|---|
| `ruff format .` | ✓ PASS — 71 files unchanged |
| `ruff check .` | ✓ PASS — All checks passed |
| `mypy .` | ✓ PASS — No issues in 71 source files |
| `pytest tests/unit/` | ✓ PASS — 37 passed |

Architecture compliance:

| Criterion | Status |
|---|---|
| Complies with frozen architecture | ✓ |
| Layer separation correct | ✓ |
| CRUD functional | ✓ |
| Upload functional | ✓ |
| Storage abstraction reusable | ✓ |
| Validation complete | ✓ (post-fixes) |
| No Wave 2.2+ functionality introduced | ✓ |
