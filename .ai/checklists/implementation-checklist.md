# Implementation Checklist

## Phase 0 — Infrastructure

- [ ] `docker-compose.yml` created
- [ ] `pgvector/pgvector:pg16` image used for PostgreSQL
- [ ] PostgreSQL starts healthy (`pg_isready`)
- [ ] `pgvector` extension installed: `CREATE EXTENSION IF NOT EXISTS vector`
- [ ] `uuid-ossp` extension installed
- [ ] Alembic configured with async engine
- [ ] All 5 migration tables created: `documents`, `chunks`, `document_relations`, `users`, `query_logs`
- [ ] `.env.example` committed, `.env` in `.gitignore`

## Phase 1 — Domain

- [ ] `Document` entity defined (pure Python, no SQLAlchemy)
- [ ] All enums: `DocumentType`, `AuthorityLevel`, `DocumentStatus`, `RelationType`, `ChunkType`
- [ ] `Chunk` entity with `Embedding` value object
- [ ] `DocumentRelation` entity
- [ ] `Query` entity + `QueryFilter` value object
- [ ] `Citation` value object with `to_reference_string()`
- [ ] Abstract `DocumentRepository` (ABC)
- [ ] Abstract `ChunkRepository` (ABC)
- [ ] Domain exceptions defined
- [ ] mypy passes on domain layer

## Phase 2 — Ingestion

- [ ] `DocxParser` handles NHNN thông tư structure
- [ ] Parser preserves Chương/Điều/Khoản/Điểm hierarchy
- [ ] `MetadataExtractor` extracts doc_number via regex
- [ ] Relation patterns detect REPLACES/AMENDS/REFERENCES
- [ ] `HierarchicalChunker` creates one chunk per Điều
- [ ] Chunk size check: oversized Điều split by Khoản
- [ ] `BgeM3Client` connects to embedding-service HTTP endpoint
- [ ] Batch embedding: 32 chunks per batch
- [ ] `PgDocumentRepository.save()` implemented
- [ ] `PgChunkRepository.bulk_insert()` implemented
- [ ] Content hash duplicate detection works
- [ ] `IngestDocumentUseCase` runs full pipeline
- [ ] `POST /api/v1/documents` returns 201 with chunk_count
- [ ] Test: ingest `48_2024_TT-NHNN.docx` → chunks in DB

## Phase 3 — Retrieval

- [ ] `MetadataFilter.build()` generates correct SQL WHERE clause
- [ ] `VectorRetriever` uses HNSW index (not full scan)
- [ ] `VectorRetriever` pre-filters by candidate doc_ids
- [ ] `BM25Retriever` uses `plainto_tsquery('simple', ...)`
- [ ] Vector and BM25 run in parallel (asyncio.gather)
- [ ] `RRFusion` combines results correctly
- [ ] `BgeRerankClient` reranks top-20 to top-5
- [ ] Authority boost applied post-rerank
- [ ] SUPERSEDED docs penalized (score × 0.3)
- [ ] Test: query "điều kiện cho vay tiêu dùng" → retrieves from thông tư 48

## Phase 4 — LLM

- [ ] `DeepSeekClient` handles API key from env var
- [ ] Retry logic: 2 retries, exponential backoff
- [ ] Temperature set to 0.1
- [ ] System prompt loaded from `.ai/prompts/`
- [ ] Context assembled with `[Đoạn N]` markers
- [ ] Citations extracted from LLM response
- [ ] Fallback message when no chunks retrieved
- [ ] `SearchKnowledgeQueryHandler` end-to-end works
- [ ] Manual test: answer has correct citation format

## Phase 5 — API

- [ ] `POST /api/v1/query` returns `QueryResponse` schema
- [ ] `POST /api/v1/documents` (multipart) works
- [ ] `GET /api/v1/documents` with filter params works
- [ ] `GET /api/v1/documents/{id}` returns 404 if not found
- [ ] `GET /api/v1/documents/{id}/relations` returns relation graph
- [ ] `GET /health` returns `{"status": "ok"}`
- [ ] `POST /auth/token` returns JWT
- [ ] Protected endpoints return 401 without token
- [ ] Rate limiting active on `/api/v1/query`
- [ ] OpenAPI docs accessible at `/docs`
- [ ] CORS configured for frontend origin

## Phase 6 — Knowledge Intelligence

- [ ] `RelationExpander` traverses up to 2 hops
- [ ] Score decay: 0.7 per hop for REFERENCES
- [ ] `VersionResolver` detects SUPERSEDED documents
- [ ] Version note added to response when applicable
- [ ] `ConflictDetector` checks `document_relations` for CONFLICTS_WITH
- [ ] `CitationBuilder` produces correct `to_reference_string()`
- [ ] `TimelineBuilder` builds version chain via REPLACES relations
- [ ] `GET /api/v1/documents/{id}/timeline` returns sorted timeline
- [ ] Test: query about "thông tư 48" triggers version note

## Phase 7 — Frontend

- [ ] Chat interface renders answer with citation markers
- [ ] Citation panel shows excerpt on click
- [ ] Document upload UI: drag & drop, progress indicator
- [ ] Document list shows status badges
- [ ] Auth flow: login page, token stored in localStorage
- [ ] Error states handled gracefully

## Phase 8 — Demo Ready

- [ ] All 4 thông tư 48 ingested (2014, 2018, 2024, 2025)
- [ ] Document relations entered: 2014→2018→2024→2025 (REPLACES chain)
- [ ] Demo query 1: "Điều kiện vay tiêu dùng" → correct answer + citation
- [ ] Demo query 2: "So sánh phiên bản thông tư 48" → timeline + version notes
- [ ] Demo query 3: "Mức cho vay tối đa" → authority-ranked answer
- [ ] Demo query 4: "TCTD phải kiểm tra gì trước khi cho vay?" → cited Điều
- [ ] Demo query 5: "Thông tư 48 hiện hành là phiên bản nào?" → 2025 version
- [ ] `docker compose up` → all services healthy
- [ ] Full demo walkthrough completed without errors

## Pre-Demo Security Check

- [ ] No API keys in source code
- [ ] `.env` not committed to git
- [ ] JWT secret is ≥ 32 random chars
- [ ] Default admin password changed
- [ ] SQL injection test passed (parameterized queries verified)
