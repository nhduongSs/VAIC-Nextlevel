# 02 — Folder Structure

## Purpose

Định nghĩa cấu trúc thư mục chuẩn cho toàn bộ project, phản ánh Clean Architecture và tách biệt rõ ràng giữa các tầng.

---

## Full Structure

```
VAIC-Nextlevel/
├── .ai/                          # Architecture & design documents
│   ├── architecture/             # Architecture docs (this directory)
│   ├── prompts/                  # LLM prompt templates
│   └── checklists/               # Implementation checklists
│
├── backend/                      # Python FastAPI application
│   ├── pyproject.toml
│   ├── alembic.ini
│   ├── alembic/
│   │   ├── env.py
│   │   └── versions/
│   │
│   └── app/
│       ├── main.py               # FastAPI app factory
│       ├── dependencies.py       # DI container setup
│       ├── config.py             # Settings (Pydantic BaseSettings)
│       │
│       ├── domain/               # PURE DOMAIN — zero external deps
│       │   ├── __init__.py
│       │   ├── entities/
│       │   │   ├── document.py       # Document aggregate root
│       │   │   ├── chunk.py          # Chunk entity
│       │   │   ├── query.py          # Query entity
│       │   │   ├── relation.py       # DocumentRelation entity
│       │   │   └── user.py           # User entity
│       │   ├── value_objects/
│       │   │   ├── document_type.py  # Enum: LAW, CIRCULAR, POLICY, SOP, FAQ
│       │   │   ├── authority_level.py # Enum: NHNN, INTERNAL, DEPARTMENT
│       │   │   ├── relation_type.py  # Enum: REPLACES, AMENDS, REFERENCES
│       │   │   └── embedding.py      # Embedding value object
│       │   ├── repositories/
│       │   │   ├── document_repo.py  # Abstract DocumentRepository
│       │   │   ├── chunk_repo.py     # Abstract ChunkRepository
│       │   │   ├── query_repo.py     # Abstract QueryRepository
│       │   │   └── user_repo.py      # Abstract UserRepository
│       │   ├── exceptions.py         # Domain exceptions hierarchy
│       │   └── services/
│       │       ├── chunking_service.py   # Domain chunking logic
│       │       └── scoring_service.py    # Domain relevance scoring
│       │
│       ├── application/          # Use Cases — orchestration only
│       │   ├── __init__.py
│       │   ├── commands/
│       │   │   ├── ingest_document.py    # IngestDocumentCommand + Handler
│       │   │   ├── delete_document.py
│       │   │   ├── update_document.py
│       │   │   └── admin_command.py      # ReindexCommand, GetStatsCommand
│       │   ├── queries/
│       │   │   ├── search_knowledge.py   # SearchKnowledgeQuery + Handler
│       │   │   ├── get_document.py
│       │   │   └── authenticate_user.py  # AuthenticateUserQuery + Handler
│       │   └── dto/
│       │       ├── document_dto.py
│       │       ├── chunk_dto.py
│       │       └── query_dto.py
│       │
│       ├── infrastructure/       # External integrations
│       │   ├── __init__.py
│       │   ├── services/
│       │   │   └── audit_log_service.py  # Writes to audit_logs table (operational, not domain)
│       │   ├── database/
│       │   │   ├── base.py           # SQLAlchemy Base, async engine
│       │   │   ├── models/           # SQLAlchemy ORM models
│       │   │   │   ├── document_model.py
│       │   │   │   ├── chunk_model.py
│       │   │   │   ├── relation_model.py
│       │   │   │   ├── query_log_model.py
│       │   │   │   ├── user_model.py
│       │   │   │   └── audit_log_model.py
│       │   │   └── repositories/     # Concrete repo implementations
│       │   │       ├── pg_document_repo.py
│       │   │       ├── pg_chunk_repo.py
│       │   │       ├── pg_query_repo.py
│       │   │       └── pg_user_repo.py
│       │   │
│       │   ├── ai/
│       │   │   ├── embedding/
│       │   │   │   └── bge_m3_client.py  # BGE-M3 embedding client
│       │   │   └── llm/
│       │   │       ├── deepseek_client.py   # DeepSeek LLM client (OpenAI-compat)
│       │   │       └── prompt_assembler.py  # Builds system+user prompts for LLM
│       │   │
│       │   ├── ingestion/
│       │   │   ├── parsers/
│       │   │   │   ├── docx_parser.py
│       │   │   │   └── pdf_parser.py
│       │   │   ├── chunkers/
│       │   │   │   ├── semantic_chunker.py
│       │   │   │   ├── hierarchical_chunker.py
│       │   │   │   └── qa_pair_chunker.py
│       │   │   ├── metadata_extractor.py
│       │   │   ├── document_classifier.py  # doc_type + authority_level
│       │   │   └── relationship_extractor.py  # detect doc references
│       │   │
│       │   ├── retrieval/
│       │   │   ├── vector_retriever.py   # pgvector ANN search
│       │   │   ├── bm25_retriever.py     # PostgreSQL tsvector BM25
│       │   │   ├── metadata_filter.py    # Pre-filter by metadata
│       │   │   └── reranker.py           # Cross-encoder re-ranking
│       │   │
│       │   └── knowledge/
│       │       ├── relation_expander.py  # Graph traversal in PG (BFS, 2 hops)
│       │       ├── authority_ranker.py   # Rank by legal authority level
│       │       ├── version_resolver.py   # Resolve latest valid version
│       │       ├── conflict_detector.py  # Detect contradicting clauses
│       │       ├── citation_builder.py   # Build Citation objects from chunks
│       │       ├── timeline_builder.py   # Document version timeline
│       │       └── context_builder.py    # Assemble EnrichedContext for LLM
│       │
│       └── presentation/         # HTTP API layer
│           ├── __init__.py
│           ├── routers/
│           │   ├── query_router.py       # POST /query
│           │   ├── document_router.py    # CRUD /documents
│           │   └── admin_router.py       # Admin endpoints
│           ├── schemas/
│           │   ├── query_schema.py       # Pydantic request/response
│           │   ├── document_schema.py
│           │   └── common_schema.py
│           └── middleware/
│               ├── auth_middleware.py
│               ├── logging_middleware.py   # request_id injection, structured logging
│               └── rate_limit_middleware.py # slowapi limiter setup
│
├── frontend/                     # React application
│   ├── package.json
│   ├── src/
│   │   ├── components/
│   │   │   ├── ChatInterface/
│   │   │   ├── DocumentUpload/
│   │   │   └── CitationPanel/
│   │   ├── pages/
│   │   ├── hooks/
│   │   ├── services/             # API client
│   │   └── types/
│   └── public/
│
├── data/                         # Source documents
│   └── thông tư/
│       ├── base_docs/            # Original documents
│       └── relations/            # Relation metadata
│
├── tests/                            # Mirrors app/ structure
│   ├── unit/
│   │   ├── domain/
│   │   │   ├── test_document_entity.py
│   │   │   ├── test_chunk_entity.py
│   │   │   └── test_scoring_service.py
│   │   └── application/
│   │       ├── test_ingest_use_case.py
│   │       └── test_query_use_case.py
│   ├── integration/
│   │   ├── test_pg_document_repo.py
│   │   ├── test_retrieval_pipeline.py
│   │   └── test_ingestion_pipeline.py
│   ├── e2e/
│   │   └── test_query_api.py
│   └── conftest.py                   # pytest fixtures, test DB setup
│
├── docker/
│   ├── backend.Dockerfile
│   ├── frontend.Dockerfile
│   ├── embedding.Dockerfile
│   ├── embedding_server.py           # Standalone BGE-M3 HTTP inference server
│   ├── init.sql                      # PostgreSQL extension setup
│   └── nginx.conf
│
├── docker-compose.yml
├── docker-compose.dev.yml
├── .env.example
└── README.md
```

---

## Layer Rules

### Domain Layer (`app/domain/`)
- Zero imports from `infrastructure`, `application`, or `presentation`
- No SQLAlchemy, no FastAPI, no HTTP clients
- Pure Python dataclasses and abstract interfaces
- 100% unit testable without DB or network

### Application Layer (`app/application/`)
- Imports from `domain` only (via interfaces)
- No SQLAlchemy models, no HTTP details
- Receives injected Repository implementations
- Houses all orchestration logic

### Infrastructure Layer (`app/infrastructure/`)
- Implements domain repository interfaces
- Contains all external dependencies (SQLAlchemy, httpx, etc.)
- Never imported by domain or application directly (injected via DI)

### Presentation Layer (`app/presentation/`)
- FastAPI routers and Pydantic schemas
- Maps HTTP requests to application commands/queries
- Maps application results to HTTP responses
- No business logic

---

## Naming Conventions

| Type | Convention | Example |
|---|---|---|
| Files | snake_case | `document_repo.py` |
| Classes | PascalCase | `DocumentRepository` |
| Async functions | async def snake_case | `async def get_by_id()` |
| Constants | UPPER_SNAKE | `MAX_CHUNK_SIZE = 512` |
| Pydantic models | PascalCase + Schema/Request/Response | `DocumentResponse` |

---

## Constraints

- No circular imports between layers
- Each module must have a single clear responsibility
- Test files mirror source structure under `tests/`

---

## Trade-offs

| Choice | Benefit | Cost |
|---|---|---|
| Explicit layer directories | Clear boundaries, easy navigation | More folders |
| Separate domain repositories/ | Abstract interfaces in domain | Duplication with infrastructure repos |

---

## Future Extensibility

- Add `app/workers/` for async background tasks (Celery/ARQ)
- Add `app/events/` for domain events / event sourcing
- Add `tests/` mirroring full structure
