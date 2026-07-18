# 12 — Coding Guidelines

## Purpose

Định nghĩa các tiêu chuẩn code bắt buộc để đảm bảo consistency, maintainability và correctness trong toàn bộ codebase.

---

## Python Standards

### Version & Tooling

```
Python: 3.12+
Package manager: uv (fast, lockfile-based)
Linter: ruff
Formatter: ruff format
Type checker: mypy (strict mode)
Test: pytest + pytest-asyncio
```

### Type Hints — Mandatory

```python
# CORRECT
async def get_document(document_id: UUID) -> Document:
    ...

async def search(query: str, top_k: int = 5) -> list[ScoredChunk]:
    ...

# WRONG — no type hints
async def get_document(document_id):
    ...
```

All functions must have complete type annotations. `mypy --strict` must pass.

---

## Async Rules

### Rule 1: Async All The Way

Every function that touches I/O must be async:

```python
# CORRECT
async def get_by_id(self, id: UUID) -> Document | None:
    result = await self.session.execute(
        select(DocumentModel).where(DocumentModel.id == id)
    )
    return result.scalar_one_or_none()

# WRONG — blocking call inside async function
async def get_by_id(self, id: UUID) -> Document | None:
    return self.session.query(DocumentModel).filter_by(id=id).first()
```

### Rule 2: Parallel I/O with gather

```python
# CORRECT — parallel
vector_results, bm25_results = await asyncio.gather(
    self.vector_retriever.search(embedding, doc_ids),
    self.bm25_retriever.search(tokens, doc_ids),
)

# WRONG — sequential when parallel is possible
vector_results = await self.vector_retriever.search(embedding, doc_ids)
bm25_results = await self.bm25_retriever.search(tokens, doc_ids)
```

### Rule 3: Never Block Event Loop

```python
# WRONG — blocks event loop
import time
time.sleep(1)

# CORRECT
await asyncio.sleep(1)

# WRONG — sync file I/O
with open("file.txt") as f:
    content = f.read()

# CORRECT — use aiofiles or run in executor
import aiofiles
async with aiofiles.open("file.txt") as f:
    content = await f.read()
```

---

## Clean Architecture Rules

### Rule: Dependency Direction

```
presentation → application → domain ← infrastructure
```

```python
# WRONG — domain importing from infrastructure
# domain/entities/document.py
from app.infrastructure.database.models import DocumentModel  # FORBIDDEN

# CORRECT — infrastructure implements domain interface
# infrastructure/database/repositories/pg_document_repo.py
from app.domain.repositories.document_repo import DocumentRepository
class PgDocumentRepository(DocumentRepository):
    ...
```

### Rule: Repository Interface in Domain

```python
# domain/repositories/document_repo.py
from abc import ABC, abstractmethod
from uuid import UUID
from app.domain.entities.document import Document

class DocumentRepository(ABC):
    @abstractmethod
    async def get_by_id(self, id: UUID) -> Document | None: ...

    @abstractmethod
    async def save(self, document: Document) -> Document: ...

    @abstractmethod
    async def delete(self, id: UUID) -> None: ...
```

### Rule: Use Cases Depend Only on Domain

```python
# application/commands/ingest_document.py
from app.domain.repositories.document_repo import DocumentRepository  # OK
from app.domain.entities.document import Document  # OK
# from app.infrastructure.database.models import DocumentModel  # FORBIDDEN
```

---

## Pydantic v2 Patterns

### Request/Response Schemas

```python
from pydantic import BaseModel, Field, field_validator
from uuid import UUID
from datetime import date

class DocumentResponse(BaseModel):
    id: UUID
    title: str
    doc_number: str | None = None
    doc_type: str
    authority_level: str
    issued_date: date | None = None
    status: str
    chunk_count: int

    model_config = {"from_attributes": True}  # Pydantic v2 ORM mode

class QueryRequest(BaseModel):
    question: str = Field(..., min_length=3, max_length=2000)
    top_k: int = Field(default=5, ge=1, le=20)
    filters: QueryFilter | None = None

    @field_validator("question")
    @classmethod
    def clean_question(cls, v: str) -> str:
        return v.strip()
```

---

## SQLAlchemy Async Patterns

### Session Management

```python
# CORRECT — use async context manager
async with async_session() as session:
    async with session.begin():
        repo = PgDocumentRepository(session)
        document = await repo.get_by_id(id)

# CORRECT — dependency injection in FastAPI
async def get_db():
    async with async_session() as session:
        async with session.begin():
            yield session

@router.get("/documents/{id}")
async def get_document(id: UUID, session: AsyncSession = Depends(get_db)):
    ...
```

### Bulk Inserts

```python
# CORRECT — bulk insert for chunks
await session.execute(
    insert(ChunkModel),
    [chunk.to_dict() for chunk in chunks]
)
# NOT: session.add(chunk) in a loop
```

---

## Error Handling

### Domain Exceptions

```python
# domain/exceptions.py
class DomainError(Exception): ...
class DocumentNotFoundError(DomainError): ...
class DuplicateDocumentError(DomainError): ...
class InvalidDocumentError(DomainError): ...
```

### FastAPI Exception Handlers

```python
@app.exception_handler(DocumentNotFoundError)
async def not_found_handler(request: Request, exc: DocumentNotFoundError):
    return JSONResponse(
        status_code=404,
        content={"error": "DOCUMENT_NOT_FOUND", "message": str(exc)}
    )
```

---

## Dependency Injection

### FastAPI DI Pattern

```python
# dependencies.py
def get_document_repository(
    session: AsyncSession = Depends(get_db)
) -> DocumentRepository:
    return PgDocumentRepository(session)

def get_ingest_use_case(
    doc_repo: DocumentRepository = Depends(get_document_repository),
    chunk_repo: ChunkRepository = Depends(get_chunk_repository),
    embedder: EmbeddingClient = Depends(get_embedder),
) -> IngestDocumentUseCase:
    return IngestDocumentUseCase(doc_repo, chunk_repo, embedder)
```

---

## Naming Conventions

| Item | Convention | Example |
|---|---|---|
| File | snake_case | `document_repository.py` |
| Class | PascalCase | `DocumentRepository` |
| Function | snake_case | `get_by_id` |
| Async function | snake_case | `async def search()` |
| Constant | UPPER_SNAKE | `MAX_CHUNK_SIZE = 512` |
| Pydantic schema | PascalCase + suffix | `DocumentResponse`, `QueryRequest` |
| DB model | PascalCase + Model | `DocumentModel` |
| Domain entity | PascalCase | `Document` |

---

## Testing Standards

```python
# CORRECT — async test
import pytest
from httpx import AsyncClient

@pytest.mark.asyncio
async def test_query_endpoint(client: AsyncClient):
    response = await client.post("/api/v1/query", json={
        "question": "Thông tư 48 quy định gì?",
        "top_k": 3
    })
    assert response.status_code == 200
    data = response.json()
    assert "answer" in data
    assert "citations" in data
```

---

## Constraints

- `mypy --strict` must pass on entire codebase
- `ruff check` must pass (zero warnings)
- No `# type: ignore` without explanation comment
- No bare `except:` — always catch specific exceptions
- All DB queries parameterized — no f-string SQL

---

## Future Extensibility

- Add `pre-commit` hooks for ruff + mypy
- Add coverage requirement: ≥ 80% for domain + application layers
- Consider `beartype` for runtime type checking in critical paths
