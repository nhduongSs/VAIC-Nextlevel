# VAIC-Nextlevel

## Advanced RAG Knowledge Base — Tiền gửi (SHB Bank)

Brief và tech stack: `doc/`.

## Cấu trúc

```
backend/
  app/
    core/         config.py, logging.py
    models/       schemas.py (Pydantic DTO)
    guardrails/   rules.py (whitelist chủ đề, PII, injection, unsafe, tư vấn tài chính)
    repositories/ document_loader.py, vector_store.py (Supabase/pgvector), relation_store.py
    services/     rag_service, document_relation_service (amendment/supersession/
                  cross-reference/conflict — việc 5-8), llm_service, guardrail_service,
                  chat_service (orchestrator)
    api/          routes.py (FastAPI)
  scripts/ingest.py   -> nạp data/raw vào Supabase/pgvector
  tests/

frontend/         Next.js — 1 màn hình chat + hiển thị trích dẫn/cảnh báo conflict
data/
  raw/            văn bản thô (Huy, Dũng)
  processed/      đã chuẩn hóa theo điều/khoản
  relations/      case cross-reference/amendment/supersession/conflict

doc/              Brief, TechStack, API_CONTRACT.md
```

## Luồng xử lý 1 câu hỏi (chat_service.py)

1. **Input guard**: chặn injection, unsafe request, PII, câu hỏi tư vấn tài chính cá nhân.
2. **RAG retrieve**: lấy top-k chunk liên quan từ Supabase/pgvector.
3. **Cross-reference**: mở rộng thêm chunk liên quan qua bảng quan hệ văn bản.
4. **Amendment**: chỉ giữ bản có hiệu lực mới nhất.
5. **Partial supersession**: loại đúng phần điều khoản đã bị thay thế.
6. **Retrieval guard**: nếu không có context đủ liên quan → từ chối trả lời thay vì để LLM bịa.
7. **Conflict detection**: so sánh nội dung chunk còn hiệu lực, phát hiện mâu thuẫn.
8. **LLM generate** (DeepSeek V4): trả lời CHỈ dựa trên context, nêu rõ mâu thuẫn nếu có.
9. **Output guard**: lọc cụm từ cam kết rủi ro.

## Chạy thử

```bash
cd backend
pip install -r requirements.txt
cp ../.env.example .env   # điền DEEPSEEK_API_KEY, SUPABASE_URL, SUPABASE_KEY

# 1. Đưa văn bản vào ../data/raw/<loai>/*.md (định dạng xem app/repositories/document_loader.py)
# 2. Nạp vào vector store
python -m scripts.ingest

# 3. Chạy API
uvicorn app.main:app --reload
```

Gọi thử:
```bash
curl -X POST http://localhost:8000/api/v1/chat \
  -H "Content-Type: application/json" \
  -d '{"session_id":"s1","message":"Lãi suất gửi tiết kiệm 6 tháng hiện nay là bao nhiêu?"}'
```
