# API Contract — RAG ↔ UI

Khoá ở H0-H2 (brief mục 3, Dương). Route thực tế: `backend/app/api/routes.py`.

## POST /api/v1/chat

Request:
```json
{
  "session_id": "string",
  "message": "string"
}
```

Response:
```json
{
  "session_id": "string",
  "answer": "string",
  "sources": [
    {
      "doc_id": "string",
      "title": "string",
      "clause": "string",
      "effective_date": "string"
    }
  ],
  "conflicts": [
    {
      "description": "string",
      "conflicting_sources": ["string"]
    }
  ],
  "blocked": false,
  "block_reason": "none"
}
```

`block_reason` một trong: `none | out_of_scope | pii_detected | unsafe_advice_request | prompt_injection | input_too_long | low_confidence_answer`.

## GET /api/v1/health

Response: `{"status": "ok"}`
