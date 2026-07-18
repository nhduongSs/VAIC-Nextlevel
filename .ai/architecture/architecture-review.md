# Architecture Review

**Reviewer:** Principal Software Architect  
**Date:** 2026-07-18  
**Status:** APPROVED — Ready for Implementation  

---

## Executive Summary

Architecture đã được review toàn diện trên 15 documents. **10 vấn đề** được phát hiện và sửa. Architecture hiện tại là internally consistent và implementation-ready.

---

## Findings & Changes Made

### CRITICAL — Correctness Issues

#### C1: Missing `audit_logs` table in database schema
**File:** `04-database-design.md`  
**Problem:** `10-security.md` references `audit_logs` table và định nghĩa `AuditEvent` dataclass, nhưng bảng này không tồn tại trong DDL.  
**Fix:** Thêm `audit_logs` table đầy đủ với DDL, constraints, và 4 indexes. Thêm vào schema diagram và ERD.

#### C2: Ingestion sequence diagram — FK violation
**File:** `01-system-architecture.md`  
**Problem:** Sequence diagram hiển thị `INSERT chunks` TRƯỚC `INSERT document`. Điều này vi phạm FK constraint (`chunks.document_id REFERENCES documents.id`).  
**Fix:** Sửa sequence diagram — document INSERT trước, chunks sau; thêm note giải thích lý do.

#### C3: BM25 SQL syntax error
**File:** `07-retrieval-design.md`  
**Problem:** BM25 query dùng comma-join và JOIN lẫn lộn trong cùng FROM clause:
```sql
FROM chunks c,
     plainto_tsquery('simple', $1) query
JOIN documents d ON d.id = c.document_id  -- JOIN binds to 'query', not 'c'
```
**Fix:** Viết lại query dùng `plainto_tsquery()` trực tiếp trong WHERE clause và SELECT — cleaner và đúng syntax.

#### C4: LlamaIndex deprecated API
**File:** `09-llm-design.md`  
**Problem:** `ServiceContext.from_defaults()` đã bị deprecated từ LlamaIndex 0.10+ (2024). Nếu implement theo doc cũ sẽ raise `DeprecationWarning` hoặc error hoàn toàn.  
**Fix:** Cập nhật sang `Settings` API (LlamaIndex 0.10+ standard). Thêm note DeepSeek không có official LlamaIndex package — dùng `OpenAILike` (DeepSeek tương thích OpenAI spec).

#### C5: Rate limiting inconsistency
**File:** `10-security.md`  
**Problem:** `05-api-design.md` định nghĩa rate limit "per user" nhưng implementation dùng `get_remote_address` (IP-based). Trong môi trường ngân hàng với VPN/proxy, nhiều users có thể share 1 IP.  
**Fix:** Implement `get_user_identifier()` function — extract `user_id` từ JWT token cho authenticated endpoints, fallback về IP cho `/auth/token` (chưa có JWT).

---

### SIGNIFICANT — Missing Components from Review Scope

#### S1: Missing "Classification" stage in ingestion pipeline
**File:** `06-ingestion-design.md`  
**Problem:** Review scope yêu cầu: `Upload → Parser → Metadata → Classification → Relationship Extraction → Chunking → Embedding`. Classification bị gộp ẩn vào MetadataExtractor, không có giai đoạn riêng.  
**Fix:** 
- Refactor pipeline thành 6 giai đoạn rõ ràng với numbered diagram
- Thêm `DocumentClassifier` class với `DOC_TYPE_KEYWORDS` và `AUTHORITY_MAP` lookup tables
- Tách `RelationshipExtractor` thành class riêng (Stage 4)
- Thêm `document_classifier.py` và `relationship_extractor.py` vào folder structure

#### S2: Missing ContextBuilder component
**File:** `08-knowledge-intelligence.md`  
**Problem:** Review scope yêu cầu: `Conflict Detection → Context Builder`. KI pipeline kết thúc ở Citations/Timeline mà không có component nào đóng gói `EnrichedContext` hoàn chỉnh.  
**Fix:**
- Thêm `ContextBuilder` (Component 7) với `EnrichedContext` dataclass
- `ContextBuilder` chịu trách nhiệm token budget management và trim chunks trước khi truyền vào LLM
- Cập nhật KI pipeline diagram từ 6 thành 7 components
- Cập nhật `Intelligence Pipeline Execution` — Stages 4+5+6 chạy parallel với `asyncio.gather`

#### S3: Missing files in folder structure
**File:** `02-folder-structure.md`  
**Problem:** Nhiều files được reference trong code nhưng thiếu trong folder structure:
- `user_model.py` — SQLAlchemy model cho `users` table
- `audit_log_model.py` — SQLAlchemy model cho `audit_logs` table  
- `pg_user_repo.py` — Concrete UserRepository implementation
- `user_repo.py` — Abstract UserRepository interface (domain)
- `context_builder.py` — ContextBuilder (KI layer)
- `document_classifier.py`, `relationship_extractor.py` — Ingestion
- `qa_pair_chunker.py` — FAQ chunking strategy
- `authenticate_user.py` — Auth use case
- `tests/` directory structure
- `rate_limit_middleware.py`
- `domain/exceptions.py`
- `docker/embedding_server.py`, `docker/init.sql`

**Fix:** Thêm tất cả files còn thiếu vào folder structure với comments mô tả trách nhiệm.

---

### MINOR — Refinements

#### M1: `hnsw.ef_search` session-level setting
**File:** `07-retrieval-design.md`  
**Problem:** `SET hnsw.ef_search = 64` là session-level setting. Trong async connection pool, nếu set toàn cục sẽ bleed across connections.  
**Fix:** Thêm note rõ ràng: dùng `SET LOCAL hnsw.ef_search = 64` trong transaction, scope to current transaction only.

#### M2: Context wrapping template inconsistency
**Files:** `09-llm-design.md`, `10-security.md`  
**Problem:** `09` và `10` định nghĩa context wrapper khác nhau, không nhất quán.  
**Fix:** Chuẩn hóa `CONTEXT_WRAPPER` template trong `09-llm-design.md` sử dụng cùng delimiter `=== BẮT ĐẦU NGỮ CẢNH TÀI LIỆU ===` như `10-security.md`. Template mới bao gồm thêm `effective_date` và `status` của document trong context.

#### M3: Missing observability in deployment
**File:** `11-deployment.md`  
**Problem:** Deployment không có basic observability — chỉ đề cập Prometheus/Grafana như future extensibility.  
**Fix:** Thêm section "Observability" với:
- Structured JSON logging via `structlog`
- Request ID injection middleware
- Basic `/metrics` endpoint (no Prometheus dependency)

---

## Decisions Confirmed

| Decision | Rationale |
|---|---|
| PostgreSQL only, no Neo4j/Redis | Operationally simple, relationship graph via recursive CTE |
| BGE-M3 local inference via HTTP service | Isolated from backend, independently scalable |
| DeepSeek via OpenAI-compatible API | `OpenAILike` wrapper avoids package dependency |
| RRF over weighted fusion | No calibration needed, robust across query types |
| `SET LOCAL hnsw.ef_search` per transaction | Safe in async connection pool |
| User-based rate limiting (JWT user_id) | More accurate than IP in enterprise VPN environment |
| 6-stage ingestion pipeline | Clear separation: Parse → Extract → Classify → RelExtract → Chunk → Embed |
| 7-component KI pipeline | Explicit ContextBuilder ensures token budget control before LLM |

---

## Remaining Risks

| Risk | Severity | Status |
|---|---|---|
| `plainto_tsquery('simple',...)` không handle tốt tiếng Việt có dấu | Medium | Accepted — mitigation: normalize query before BM25 |
| BGE-M3 CPU inference slow (3-5x vs GPU) | Medium | Accepted — batch 32, async embedding service |
| DeepSeek API latency/downtime | High | Mitigated — mock stub in dev, retry 2x |
| Recursive CTE graph traversal slow for deep graphs | Low | Accepted — max 2 hops limit |
| LLM-based conflict detection adds ~500ms | Medium | Accepted — only runs when ≥2 conflicting docs |
| DOCX parsing edge cases in NHNN circular format | High | Action: test all 4 thông tư files early in Phase 2 |
| `hnsw.ef_search` SET LOCAL may not work in all async drivers | Low | Verified: asyncpg supports `SET LOCAL` |

---

## Assumptions

1. BGE-M3 model weights (~2.2GB) được download on first run và cached via Docker volume `model_cache`.
2. DeepSeek API key hợp lệ và có rate limit đủ cho demo (không cần self-hosted DeepSeek).
3. Thông tư 48 DOCX files có encoding UTF-8 và structure chuẩn (có Chương/Điều/Khoản hierarchy).
4. PostgreSQL 16 với pgvector extension ≥ 0.7.0 (để dùng HNSW index).
5. Team có ít nhất 1 người biết Python async, 1 người biết React.
6. Demo machine có ≥ 8GB RAM và ≥ 4 CPU cores cho CPU-based embedding.

---

## Architecture Consistency Matrix

| Component | Defined In | Referenced In | DB Table | Folder Path | Status |
|---|---|---|---|---|---|
| Document | 03 | 01, 04, 05, 06 | `documents` | `domain/entities/document.py` | ✓ |
| Chunk | 03 | 01, 04, 06, 07 | `chunks` | `domain/entities/chunk.py` | ✓ |
| DocumentRelation | 03 | 04, 06, 08 | `document_relations` | `domain/entities/relation.py` | ✓ |
| User | 03 | 04, 10 | `users` | `domain/entities/user.py` | ✓ |
| QueryLog | — | 04, 05 | `query_logs` | `infra/database/models/query_log_model.py` | ✓ |
| AuditLog | 10 | 04 (fixed) | `audit_logs` (fixed) | `infra/database/models/audit_log_model.py` | ✓ Fixed |
| DocumentClassifier | 06 (fixed) | — | — | `infra/ingestion/document_classifier.py` | ✓ Fixed |
| RelationshipExtractor | 06 (fixed) | — | `document_relations` | `infra/ingestion/relationship_extractor.py` | ✓ Fixed |
| ContextBuilder | 08 (fixed) | 09 | — | `infra/knowledge/context_builder.py` | ✓ Fixed |
| VectorRetriever | 07 | 01, 14 | `chunks` | `infra/retrieval/vector_retriever.py` | ✓ |
| BM25Retriever | 07 | 01, 14 | `chunks` | `infra/retrieval/bm25_retriever.py` | ✓ |
| ReRanker | 07 | 01, 08, 14 | — | `infra/retrieval/reranker.py` | ✓ |
| KnowledgeIntelligenceService | 08 | 01, 09 | — | `infra/knowledge/` | ✓ |
| DeepSeekClient | 09 | 01 | — | `infra/ai/llm/deepseek_client.py` | ✓ |
| BgeM3Client | 06, 07 | 01 | — | `infra/ai/embedding/bge_m3_client.py` | ✓ |
| UserRepository | 03, 10 | 12 | `users` | `domain/repositories/user_repo.py` | ✓ Fixed |

---

## Pipeline Completeness Verification

### Ingestion Pipeline (6 stages)
```
Upload (API) → DocxParser → MetadataExtractor → DocumentClassifier 
→ RelationshipExtractor → Chunker (Hierarchical/Semantic/QA) → BGE-M3 Embedder → PostgreSQL
```
✓ All stages defined  
✓ Classification explicitly separated  
✓ Relationship extraction separated  
✓ Strategy selection by doc_type documented  

### Retrieval Pipeline (full chain)
```
QueryPreprocessor → MetadataFilter → [VectorSearch ∥ BM25Search] 
→ RRFusion → CrossEncoderReRanker → AuthorityBoost
```
✓ All stages defined  
✓ Parallel execution specified (asyncio.gather)  
✓ Authority boost post-rerank documented  

### Knowledge Intelligence Pipeline (7 components)
```
RelationExpander → AuthorityRanker → VersionResolver 
→ [ConflictDetector ∥ CitationBuilder ∥ TimelineBuilder] → ContextBuilder
```
✓ All components defined  
✓ ContextBuilder added (previously missing)  
✓ Parallel stages identified  
✓ Token budget management in ContextBuilder  

### LLM Generation Pipeline
```
ContextBuilder.EnrichedContext → PromptAssembler → DeepSeekClient → ResponseValidator
```
✓ PromptAssembler defined  
✓ System prompt template defined  
✓ Context wrapper standardized  
✓ Hallucination mitigations documented  

---

## Security Review Summary

| Control | Status |
|---|---|
| JWT authentication | ✓ Specified |
| RBAC with 4 roles | ✓ Permission matrix complete |
| Rate limiting (user-based) | ✓ Fixed |
| Prompt injection defense | ✓ Context delimiter + input validation |
| SQL injection prevention | ✓ Parameterized queries required |
| Audit logging | ✓ Table added, AuditEvent defined |
| File upload validation | ✓ MIME type + size checks |
| Secrets management | ✓ Env vars only |
| Security headers | ✓ X-Content-Type-Options, X-Frame-Options, HSTS |

---

## Documents Modified in This Review

| Document | Change Type | Summary |
|---|---|---|
| `04-database-design.md` | Added | `audit_logs` table DDL + schema diagram |
| `01-system-architecture.md` | Fixed | Ingestion sequence: document INSERT before chunks |
| `07-retrieval-design.md` | Fixed | BM25 SQL syntax; `ef_search` session note |
| `09-llm-design.md` | Updated | LlamaIndex `Settings` API; standardized context wrapper |
| `10-security.md` | Fixed | User-based rate limiting with JWT extraction |
| `06-ingestion-design.md` | Refactored | 6-stage pipeline; `DocumentClassifier`; `RelationshipExtractor` |
| `08-knowledge-intelligence.md` | Added | `ContextBuilder` (Component 7); updated pipeline diagram |
| `02-folder-structure.md` | Extended | user_model, audit_log_model, user_repo, context_builder, tests/, docker/ |
| `11-deployment.md` | Added | Observability section: structlog, request_id, /metrics |

---

## Final Status

```
Architecture Status:  ✓ FROZEN — Implementation Ready
Consistency:          ✓ All cross-references verified
Completeness:         ✓ All review scope components present
Security:             ✓ No critical gaps
Deployment:           ✓ Docker Compose fully specified
Database:             ✓ All tables defined with DDL
API:                  ✓ All endpoints documented with schemas
```

**Next step:** Begin Phase 0 implementation per `14-roadmap.md`.
