# 05 — API Design

## Purpose

Định nghĩa toàn bộ REST API: endpoints, request/response schemas, authentication, error handling, và versioning strategy.

---

## Design Principles

- REST với JSON payloads
- Versioning qua URL prefix: `/api/v1/`
- JWT Bearer authentication
- Async handlers (FastAPI + asyncio)
- Chuẩn hóa error responses
- OpenAPI docs tự động tại `/docs`

---

## API Overview

```mermaid
graph LR
    subgraph Public["Public Endpoints"]
        AUTH[POST /auth/token]
        HEALTH[GET /health]
    end

    subgraph Query["Query API"]
        SEARCH[POST /api/v1/query]
        SUGGEST[POST /api/v1/query/suggest]
        HISTORY[GET /api/v1/query/history]
    end

    subgraph Documents["Document API"]
        UPLOAD[POST /api/v1/documents]
        LIST[GET /api/v1/documents]
        GET[GET /api/v1/documents/{id}]
        UPDATE[PATCH /api/v1/documents/{id}]
        DELETE[DELETE /api/v1/documents/{id}]
        RELATIONS[GET /api/v1/documents/{id}/relations]
        TIMELINE[GET /api/v1/documents/{id}/timeline]
        CHUNKS[GET /api/v1/documents/{id}/chunks]
    end

    subgraph Admin["Admin API"]
        REINDEX[POST /api/v1/admin/reindex]
        STATS[GET /api/v1/admin/stats]
        USERS[GET /api/v1/admin/users]
    end
```

---

## Authentication

```
POST /auth/token
Content-Type: application/x-www-form-urlencoded

username=user@bank.vn&password=secret

Response 200:
{
  "access_token": "eyJhbGci...",
  "token_type": "bearer",
  "expires_in": 3600
}
```

All protected endpoints require:
```
Authorization: Bearer <access_token>
```

---

## Query Endpoints

### POST /api/v1/query

Truy vấn knowledge base bằng natural language.

**Request:**
```json
{
  "question": "Thông tư 48 quy định gì về cho vay tiêu dùng?",
  "filters": {
    "doc_types": ["CIRCULAR", "LAW"],
    "authority_levels": ["NHNN_CIRCULAR"],
    "date_from": "2018-01-01",
    "date_to": null,
    "active_only": true,
    "tags": ["cho vay", "tiêu dùng"]
  },
  "top_k": 5,
  "include_citations": true,
  "include_related_docs": true
}
```

**Response 200:**
```json
{
  "query_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
  "question": "Thông tư 48 quy định gì về cho vay tiêu dùng?",
  "answer": "Theo Thông tư 48/2018/TT-NHNN...",
  "citations": [
    {
      "chunk_id": "uuid",
      "document_id": "uuid",
      "document_title": "Thông tư 48/2018/TT-NHNN",
      "doc_number": "48/2018/TT-NHNN",
      "section_title": "Điều 3. Nguyên tắc cho vay",
      "section_number": "Điều 3",
      "page_number": 2,
      "relevance_score": 0.92,
      "excerpt": "Tổ chức tín dụng cho vay..."
    }
  ],
  "related_documents": [
    {
      "id": "uuid",
      "title": "Thông tư 48/2024/TT-NHNN",
      "relation_type": "REPLACES",
      "status": "ACTIVE"
    }
  ],
  "conflicts_detected": false,
  "version_note": null,
  "latency_ms": 1240
}
```

**Response 400** (invalid filters):
```json
{
  "error": "INVALID_FILTER",
  "message": "date_from must be before date_to",
  "field": "filters.date_from"
}
```

---

### POST /api/v1/query/suggest

Auto-complete / query suggestions.

**Request:**
```json
{ "partial": "Thông tư 48 quy định" }
```

**Response 200:**
```json
{
  "suggestions": [
    "Thông tư 48 quy định về cho vay tiêu dùng",
    "Thông tư 48 quy định mức lãi suất",
    "Thông tư 48 quy định điều kiện vay"
  ]
}
```

---

### GET /api/v1/query/history

Lịch sử query của user hiện tại.

**Query params:** `?page=1&page_size=20`

**Response 200:**
```json
{
  "items": [
    {
      "id": "uuid",
      "question": "...",
      "created_at": "2026-07-18T03:00:00Z",
      "result_count": 5
    }
  ],
  "total": 42,
  "page": 1,
  "page_size": 20
}
```

---

## Document Endpoints

### POST /api/v1/documents

Upload và ingest tài liệu mới.

**Request:** `multipart/form-data`
```
file: <binary>
title: "Thông tư 48/2024/TT-NHNN"
doc_number: "48/2024/TT-NHNN"
doc_type: CIRCULAR
authority_level: NHNN_CIRCULAR
issued_date: "2024-10-01"
effective_date: "2024-11-01"
issuing_body: "Ngân hàng Nhà nước Việt Nam"
tags: ["cho vay", "tiêu dùng"]
```

**Response 201:**
```json
{
  "document_id": "uuid",
  "title": "Thông tư 48/2024/TT-NHNN",
  "status": "ACTIVE",
  "chunk_count": 87,
  "ingestion_time_ms": 3200
}
```

---

### GET /api/v1/documents

Danh sách tài liệu với filter.

**Query params:**
```
?doc_type=CIRCULAR
&authority_level=NHNN_CIRCULAR
&status=ACTIVE
&q=cho+vay+tiêu+dùng
&page=1&page_size=20
&sort=issued_date:desc
```

**Response 200:**
```json
{
  "items": [
    {
      "id": "uuid",
      "title": "Thông tư 48/2024/TT-NHNN",
      "doc_number": "48/2024/TT-NHNN",
      "doc_type": "CIRCULAR",
      "authority_level": "NHNN_CIRCULAR",
      "issued_date": "2024-10-01",
      "effective_date": "2024-11-01",
      "status": "ACTIVE",
      "chunk_count": 87
    }
  ],
  "total": 15,
  "page": 1,
  "page_size": 20
}
```

---

### GET /api/v1/documents/{id}/relations

Đồ thị quan hệ của một tài liệu.

**Response 200:**
```json
{
  "document_id": "uuid",
  "document_title": "Thông tư 48/2018/TT-NHNN",
  "relations": [
    {
      "target_document": {
        "id": "uuid",
        "title": "Thông tư 48/2024/TT-NHNN",
        "status": "ACTIVE"
      },
      "relation_type": "REPLACES",
      "direction": "inbound",
      "confidence": 1.0
    }
  ]
}
```

---

### GET /api/v1/documents/{id}/timeline

Timeline lịch sử thay đổi của văn bản.

**Response 200:**
```json
{
  "document_id": "uuid",
  "doc_number_family": "48/TT-NHNN",
  "timeline": [
    {
      "version": "48/2014/TT-NHNN",
      "issued_date": "2014-11-25",
      "effective_date": "2015-02-01",
      "status": "SUPERSEDED",
      "superseded_by": "48/2018/TT-NHNN"
    },
    {
      "version": "48/2018/TT-NHNN",
      "issued_date": "2018-12-31",
      "effective_date": "2019-07-01",
      "status": "SUPERSEDED",
      "superseded_by": "48/2024/TT-NHNN"
    },
    {
      "version": "48/2024/TT-NHNN",
      "issued_date": "2024-10-01",
      "effective_date": "2024-11-01",
      "status": "ACTIVE",
      "superseded_by": null
    }
  ]
}
```

---

## Error Response Standard

```json
{
  "error": "DOCUMENT_NOT_FOUND",
  "message": "Document with id 'uuid' not found",
  "request_id": "req-abc123",
  "timestamp": "2026-07-18T03:00:00Z"
}
```

| HTTP Status | Error Code | Meaning |
|---|---|---|
| 400 | INVALID_REQUEST | Malformed request |
| 401 | UNAUTHORIZED | Missing or invalid token |
| 403 | FORBIDDEN | Insufficient permissions |
| 404 | NOT_FOUND | Resource not found |
| 409 | DOCUMENT_DUPLICATE | Document with same content_hash exists |
| 422 | VALIDATION_ERROR | Pydantic validation failed |
| 429 | RATE_LIMITED | Too many requests |
| 500 | INTERNAL_ERROR | Unexpected server error |
| 503 | LLM_UNAVAILABLE | DeepSeek API unreachable |

---

## Rate Limiting

| Endpoint | Limit |
|---|---|
| POST /api/v1/query | 20 req/min per user |
| POST /api/v1/documents | 10 req/min per user |
| GET endpoints | 100 req/min per user |

---

## Constraints

- Max file upload size: 50 MB
- Max question length: 2000 characters
- Max `top_k`: 20
- Response must always include `request_id` for tracing

---

## Trade-offs

| Choice | Benefit | Cost |
|---|---|---|
| multipart/form-data for upload | File + metadata in one call | More complex client |
| JWT stateless auth | No session storage needed | Token revocation harder |
| Synchronous query response | Simple client | Long queries may timeout |

---

## Future Extensibility

- Add WebSocket endpoint for streaming LLM responses
- Add `/api/v1/query/stream` (SSE) for progressive answer
- Add `/api/v1/collections` for multi-tenant document grouping
- Add `/api/v1/feedback` for answer quality ratings
