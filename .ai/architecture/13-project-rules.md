# 13 — Project Rules

## Purpose

Quy tắc làm việc bắt buộc cho toàn đội — git workflow, review process, commit standards, và communication.

---

## Architecture Rules (Non-Negotiable)

Những quyết định này là FINAL. Không thảo luận lại trong hackathon:

1. **PostgreSQL là database duy nhất** — không thêm Redis, Elasticsearch, Neo4j
2. **pgvector** — embedding stored in PostgreSQL
3. **DeepSeek** — LLM duy nhất, không switch sang OpenAI/Claude trong quá trình build
4. **BGE-M3** — embedding model duy nhất
5. **Clean Architecture** — dependency direction không được vi phạm
6. **Async everywhere** — không dùng sync I/O trong request path

---

## Git Workflow

### Branch Strategy

```
main          — production-ready, protected
feature/backend    — backend feature branches
feature/frontend   — frontend feature branches
feature/rag        — RAG/retrieval work
hotfix/*      — emergency fixes
```

### Branch Naming

```
feature/ingestion-pipeline
feature/hybrid-retrieval
feature/knowledge-intelligence
fix/chunk-embedding-bug
```

### Commit Message Format

```
<type>(<scope>): <short description>

type:
  feat     — new feature
  fix      — bug fix
  refactor — code restructure (no behavior change)
  test     — add/update tests
  docs     — documentation
  chore    — tooling, config

scope: domain | infra | api | retrieval | ingestion | ki | llm | deploy

Examples:
feat(ingestion): add hierarchical chunker for legal documents
fix(retrieval): fix vector score normalization
feat(ki): implement conflict detector with LLM
```

---

## Code Review Rules

### Self-review Checklist (before PR)

- [ ] Type hints complete
- [ ] mypy passes
- [ ] ruff passes
- [ ] Tests written for new code
- [ ] No hardcoded secrets
- [ ] No blocking I/O in async context
- [ ] Repository interface in domain, implementation in infrastructure

### PR Rules

- PR title matches commit convention
- PR description: what + why + how to test
- Max PR size: ~400 lines changed (split if larger)
- All CI checks must pass before merge
- Squash merge to main

---

## File Organization Rules

1. **One class per file** for entities and repositories
2. **One use case per file** in `application/commands/` and `application/queries/`
3. **No utils.py** — if you need a utility, put it in the right module
4. **No `__all__`** unless it's a public API package
5. **Relative imports only within the same layer**

---

## Forbidden Patterns

```python
# FORBIDDEN — mutable default argument
def chunk(items: list = []):  # DON'T
    ...

# FORBIDDEN — bare except
try:
    ...
except:  # DON'T
    pass

# FORBIDDEN — f-string SQL
query = f"SELECT * FROM chunks WHERE id = '{id}'"  # SQL INJECTION

# FORBIDDEN — sync sleep in async
await time.sleep(1)  # time.sleep blocks event loop

# FORBIDDEN — import from wrong layer
# in domain/entities/document.py:
from sqlalchemy import Column  # DON'T — domain must be pure

# FORBIDDEN — print for logging
print("Processing...")  # use logger.info()
```

---

## Logging Standards

```python
import logging
logger = logging.getLogger(__name__)

# Use structured logging
logger.info("Document ingested", extra={
    "doc_id": str(doc_id),
    "chunk_count": chunk_count,
    "duration_ms": duration
})

# Log levels:
# DEBUG   — detailed tracing (dev only)
# INFO    — normal operations
# WARNING — unexpected but handled
# ERROR   — failures requiring attention
# CRITICAL — system-level failures
```

---

## Environment Rules

### .env.example (committed)

```bash
# Database
POSTGRES_PASSWORD=change-me

# AI
DEEPSEEK_API_KEY=your-key-here

# Security
JWT_SECRET_KEY=generate-with-openssl-rand-hex-32

# App
ENV=development
LOG_LEVEL=INFO
```

### .env (NEVER committed)

```bash
POSTGRES_PASSWORD=actual-strong-password
DEEPSEEK_API_KEY=sk-actual-key
JWT_SECRET_KEY=actual-256bit-hex
```

---

## Testing Rules

1. **Domain layer**: 100% unit testable, no DB needed
2. **Application layer**: unit tests with mock repositories
3. **Infrastructure layer**: integration tests with real DB (test DB)
4. **API layer**: integration tests with `httpx.AsyncClient`

### Test File Structure

```
tests/
  unit/
    domain/
      test_document_entity.py
      test_scoring_service.py
    application/
      test_ingest_use_case.py
      test_query_use_case.py
  integration/
    test_pg_document_repo.py
    test_retrieval_pipeline.py
  e2e/
    test_query_api.py
```

---

## Hackathon-Specific Rules

Given 48-hour constraint:

1. **Ship working retrieval first** — P0: query + ingestion working end-to-end
2. **Defer optimization** — don't over-engineer chunking in first pass
3. **Mock LLM if DeepSeek API fails** — have a fallback stub
4. **Skip auth for demo** — implement JWT last if time permits
5. **Single admin user** — no full user management for demo

### Priority Order

```
P0 (must work for demo):
  ✓ Document ingestion (DOCX)
  ✓ Hybrid retrieval (vector + BM25)
  ✓ LLM answer generation
  ✓ Citations in response
  ✓ Basic React chat UI

P1 (if time allows):
  ✓ Re-ranking
  ✓ Knowledge Intelligence (conflict detection, version resolution)
  ✓ Document relations
  ✓ JWT auth

P2 (nice to have):
  ✓ Timeline builder
  ✓ Query history
  ✓ Streaming response
```

---

## Constraints

- Không refactor khi đang implement feature mới
- Không thêm dependency mới mà không thảo luận với team
- Không merge broken code vào main
- Không xóa data trong production DB mà không backup

---

## Communication

- **Blocker**: báo ngay trong team chat
- **Architecture question**: check `.ai/architecture/` docs trước
- **Bug in production data**: không tự ý fix — escalate
