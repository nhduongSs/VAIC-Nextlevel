# Architecture Review Checklist

## Purpose

Review cuối cùng trước khi freeze architecture và bắt đầu implementation.

---

## Consistency Checks

### Domain Model vs Database Schema

- [ ] All `Document` entity fields have corresponding DB column
- [ ] All `Chunk` entity fields have corresponding DB column
- [ ] `Embedding` value object maps to `VECTOR(1024)` column
- [ ] All enum values in domain match CHECK constraints in DB
- [ ] `DocumentRelation` entity maps to `document_relations` table

### API vs Use Cases

- [ ] `POST /api/v1/query` → `SearchKnowledgeQueryHandler`
- [ ] `POST /api/v1/documents` → `IngestDocumentUseCase`
- [ ] `GET /api/v1/documents/{id}/relations` → repository query
- [ ] `GET /api/v1/documents/{id}/timeline` → `TimelineBuilder`
- [ ] All request fields in API schemas are validated

### Folder Structure vs Architecture Layers

- [ ] `app/domain/` contains only pure Python (no framework imports)
- [ ] `app/application/` only imports from `app/domain/`
- [ ] `app/infrastructure/` implements domain interfaces
- [ ] `app/presentation/` only imports from `app/application/` and schemas

---

## Design Decisions Verified

- [ ] PostgreSQL is the ONLY data store (no Redis, Neo4j, Elasticsearch)
- [ ] pgvector used for embedding storage (no separate vector DB)
- [ ] Relationship graph stored in `document_relations` table (not Neo4j)
- [ ] Retrieval is hybrid: Metadata Filter + BM25 + Vector + Reranking
- [ ] LLM is DeepSeek only
- [ ] Embedding model is BGE-M3 only
- [ ] Clean Architecture dependency rules enforced
- [ ] Repository Pattern used for all data access
- [ ] Async I/O everywhere

---

## Knowledge Intelligence Completeness

- [ ] Relationship Expansion — specified in `08-knowledge-intelligence.md`
- [ ] Authority Ranking — specified with boost table
- [ ] Version Resolution — SUPERSEDED → fetch replacement logic defined
- [ ] Conflict Detection — strategy 1 (explicit) + strategy 2 (LLM) defined
- [ ] Citation Builder — format and `to_reference_string()` defined
- [ ] Timeline Builder — build version chain via REPLACES defined

---

## Security Review

- [ ] JWT auth flow complete in `10-security.md`
- [ ] RBAC roles and permissions matrix complete
- [ ] Prompt injection defense in system prompt
- [ ] Input validation in API schemas
- [ ] File upload validation (type + size)
- [ ] Parameterized queries required (no f-string SQL)
- [ ] Secrets via env vars only

---

## Deployment Completeness

- [ ] All services in `docker-compose.yml`
- [ ] Health checks defined for all services
- [ ] Startup order correct (postgres → embedding → backend → frontend)
- [ ] nginx reverse proxy routes `/api/*` to backend, `/*` to frontend
- [ ] `.env.example` has all required variables documented

---

## Performance Targets Feasible

- [ ] Retrieval latency ≤ 2s: parallel vector + BM25, pre-filtered, HNSW indexed
- [ ] LLM generation ≤ 3s: 2048 max tokens, temperature 0.1
- [ ] Ingestion ≥ 50 docs/hour: batch embedding, bulk insert

---

## Gaps & Risks Identified

- BGE-M3 Vietnamese tokenization via `'simple'` dictionary in tsvector is suboptimal
  - **Mitigation**: acceptable for hackathon; upgrade to `pg_bm25` in production
- Recursive CTE graph traversal slow for deep document networks
  - **Mitigation**: max 2 hops limit; acceptable for current document set size
- LLM-based conflict detection adds ~500ms latency
  - **Mitigation**: only trigger when multiple documents from different sources found
- CPU-based BGE-M3 embedding is slow (no GPU)
  - **Mitigation**: batch size 32, async embedding service, acceptable for hackathon

---

## Architecture Freeze Sign-off

Architecture is FROZEN after this review. Any change requires explicit decision with documented trade-off.

| Document | Status |
|---|---|
| 00-project-overview.md | ✓ Complete |
| 01-system-architecture.md | ✓ Complete |
| 02-folder-structure.md | ✓ Complete |
| 03-domain-model.md | ✓ Complete |
| 04-database-design.md | ✓ Complete |
| 05-api-design.md | ✓ Complete |
| 06-ingestion-design.md | ✓ Complete |
| 07-retrieval-design.md | ✓ Complete |
| 08-knowledge-intelligence.md | ✓ Complete |
| 09-llm-design.md | ✓ Complete |
| 10-security.md | ✓ Complete |
| 11-deployment.md | ✓ Complete |
| 12-coding-guidelines.md | ✓ Complete |
| 13-project-rules.md | ✓ Complete |
| 14-roadmap.md | ✓ Complete |

**Architecture Status: FROZEN — Ready for Implementation**
