# VAIC-Nextlevel

Backend API cho hệ thống RAG tài liệu ngân hàng, xây dựng bằng FastAPI, PostgreSQL/pgvector và embedding service chạy local.

## Mục lục

- [1. Yêu cầu](#1-yêu-cầu)
- [2. Cấu trúc chính](#2-cấu-trúc-chính)
- [3. Cấu hình môi trường](#3-cấu-hình-môi-trường)
- [4. Chạy bằng Docker](#4-chạy-bằng-docker)
- [5. Chạy backend local](#5-chạy-backend-local)
- [6. Các lệnh Makefile (tùy chọn)](#6-các-lệnh-makefile-tùy-chọn)
- [7. Chạy test](#7-chạy-test)
- [8. API hiện có](#8-api-hiện-có)
- [9. Quality gates](#9-quality-gates)
- [10. Lỗi thường gặp](#10-lỗi-thường-gặp)
- [11. Ghi chú phát triển](#11-ghi-chú-phát-triển)

---

## 1. Yêu cầu

Cần cài sẵn:

- Docker Desktop
- Python 3.12
- PowerShell trên Windows

Tùy chọn:

- Make, nếu muốn dùng các lệnh trong `Makefile`
- `uv`, nếu muốn cài dependency Python theo cách của project

## 2. Cấu trúc chính

```text
backend/                 FastAPI backend
backend/app/             Source code API
backend/alembic/         Database migrations
backend/tests/           Unit/integration tests
docker/                  Dockerfiles, nginx config, embedding service
data/                    Dữ liệu tài liệu mẫu
docker-compose.yml       Compose production-like
docker-compose.dev.yml   Compose dev override
.env.example             Mẫu biến môi trường
```

Lưu ý: `docker-compose.yml` hiện có khai báo service `frontend`, nhưng repo hiện chưa có thư mục `frontend`. Vì vậy nếu chạy toàn bộ `docker compose up` sẽ lỗi ở bước build frontend. Cách chạy ổn định hiện tại là chạy các service `postgres`, `embedding-service`, `backend`.

## 3. Cấu hình môi trường

Tạo file `.env` từ file mẫu:

```powershell
cd D:\VAIC-Nextlevel
Copy-Item .env.example .env
```

Sửa `.env` tối thiểu như sau:

```env
POSTGRES_USER=vaic_nextlevel
POSTGRES_PASSWORD=12345678
POSTGRES_DB=vaic_nextlevel_db
DATABASE_URL=postgresql+asyncpg://vaic_nextlevel:12345678@localhost:5434/vaic_nextlevel_db
JWT_SECRET_KEY=dev-secret-key-change-me
DEEPSEEK_API_KEY=
```

`MODEL_LOAD_STRATEGY` điều khiển cách embedding service load model:

```env
MODEL_LOAD_STRATEGY=lazy
```

Các giá trị hỗ trợ:

```text
lazy        Local/dev: model chỉ load khi có request đầu tiên tới /embed hoặc /rerank.
background  Production: service start nhanh, sau đó warm model ở background.
startup     Production nghiêm ngặt: load model xong mới cho app startup.
```

Khuyến nghị:

```text
Local:      MODEL_LOAD_STRATEGY=lazy
Production: MODEL_LOAD_STRATEGY=background
```

Nếu chạy backend local, tạo thêm `backend\.env`:

```powershell
Copy-Item .env.example backend\.env
```

Trong `backend\.env`, đảm bảo database trỏ về Postgres trên máy host:

```env
POSTGRES_USER=vaic_nextlevel
POSTGRES_PASSWORD=12345678
POSTGRES_DB=vaic_nextlevel_db
DATABASE_URL=postgresql+asyncpg://vaic_nextlevel:12345678@localhost:5434/vaic_nextlevel_db
JWT_SECRET_KEY=dev-secret-key-change-me
DEEPSEEK_API_KEY=
ENV=development
DEBUG=false
LOG_LEVEL=INFO
```

## 4. Chạy bằng Docker

Đây là cách khuyến nghị để có đủ Postgres, pgvector, embedding service và backend.

```powershell
cd D:\VAIC-Nextlevel
docker compose up -d postgres embedding-service backend
```

Lần đầu chạy `embedding-service` có thể lâu vì container cần cài PyTorch, `sentence-transformers` và tải model:

- `BAAI/bge-m3`
- `BAAI/bge-reranker-v2-m3`

Với local/dev, mặc định `MODEL_LOAD_STRATEGY=lazy`, nên container có thể healthy trước, còn model sẽ load khi request đầu tiên gọi `/embed` hoặc `/rerank`.

Với production, đặt:

```env
MODEL_LOAD_STRATEGY=background
```

Khi đó `/health` dùng để kiểm tra process sống, còn `/ready` dùng để kiểm tra model đã warm xong:

```text
http://localhost:8001/health
http://localhost:8001/ready
```

Sau khi backend đã chạy, migrate database:

```powershell
docker compose exec backend alembic upgrade head
```

Kiểm tra API:

```text
http://localhost:8000/health
http://localhost:8000/health/ready
http://localhost:8000/docs
```

Xem log backend:

```powershell
docker compose logs -f backend
```

Dừng service:

```powershell
docker compose down
```

Xóa toàn bộ container và volume database:

```powershell
docker compose down -v
```

Nếu đổi `POSTGRES_USER`, `POSTGRES_PASSWORD` hoặc `POSTGRES_DB` sau khi Postgres đã từng chạy, cần reset volume để Postgres khởi tạo lại user/database theo cấu hình mới:

```powershell
docker compose down -v
docker compose up -d postgres
```

Thông tin kết nối database theo `.env.example`:

```text
Host: localhost
Port: 5434
Database: vaic_nextlevel_db
Username: vaic_nextlevel
Password: change-me-strong-password
```

## 5. Chạy backend local

Cách này chỉ chạy FastAPI trên máy local, còn Postgres vẫn chạy bằng Docker.

Start Postgres:

```powershell
cd D:\VAIC-Nextlevel
docker compose up -d postgres
```

Kích hoạt môi trường Python có sẵn:

```powershell
.\.venv\Scripts\Activate.ps1
```

### Cài dependency

**Cách 1 — pip (khuyến nghị, không cần tool ngoài):**

```powershell
cd D:\VAIC-Nextlevel\backend
pip install -r requirements-dev.txt
```

**Cách 2 — uv (nhanh hơn nếu đã cài uv):**

```powershell
cd D:\VAIC-Nextlevel\backend
pip install uv
uv pip install -e ".[dev]"
```

**Cài chỉ production dependency (không có test/lint):**

```powershell
pip install -r requirements.txt
```

### Chạy migration

```powershell
cd D:\VAIC-Nextlevel\backend
alembic upgrade head
```

### Chạy backend

```powershell
cd D:\VAIC-Nextlevel\backend
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

Mở:

```text
http://localhost:8000/docs
```

## 6. Các lệnh Makefile (tùy chọn)

Nếu máy có `make`, có thể dùng:

```powershell
make install        # Cài dependency backend
make dev            # Chạy backend hot reload
make migrate-up     # Chạy migration
make test           # Chạy test
make docker-up      # Chạy toàn bộ compose
make docker-dev     # Chạy compose dev override
make docker-down    # Dừng compose
make docker-logs    # Xem log backend
```

Lưu ý: `make docker-up` và `make docker-dev` sẽ cố chạy cả `frontend`. Hiện repo chưa có thư mục `frontend`, nên nên dùng trực tiếp:

```powershell
docker compose up -d postgres embedding-service backend
```

## 7. Chạy test

Chạy toàn bộ test:

```powershell
cd D:\VAIC-Nextlevel\backend
pytest
```

Hoặc dùng Python trong virtualenv ở root:

```powershell
cd D:\VAIC-Nextlevel
.\.venv\Scripts\python.exe -m pytest backend\tests
```

Chạy test có coverage:

```powershell
cd D:\VAIC-Nextlevel\backend
pytest --cov=app --cov-report=html
```

Report HTML nằm ở:

```text
backend/htmlcov/index.html
```

## 8. API hiện có

### Health & Metrics

```text
GET    /health
GET    /health/live
GET    /health/ready
GET    /metrics
```

### Documents (Wave 2.1)

```text
GET    /api/v1/documents                          Danh sách tài liệu (phân trang)
POST   /api/v1/documents                          Upload tài liệu mới
GET    /api/v1/documents/{document_id}            Chi tiết tài liệu
PATCH  /api/v1/documents/{document_id}            Cập nhật metadata
DELETE /api/v1/documents/{document_id}            Xoá tài liệu
```

### Ingestion Pipeline (Wave 2.2)

```text
POST   /api/v1/documents/{document_id}/process         Kích hoạt pipeline ingestion
GET    /api/v1/documents/{document_id}/processing-status  Trạng thái ingestion
GET    /api/v1/documents/{document_id}/chunks          Danh sách chunks (phân trang)
GET    /api/v1/documents/{document_id}/relations       Danh sách quan hệ giữa văn bản
```

### Embedding Pipeline (Wave 2.3)

```text
POST   /api/v1/documents/{document_id}/embeddings           Kích hoạt embedding (async)
GET    /api/v1/documents/{document_id}/embeddings           Danh sách embedding jobs
GET    /api/v1/documents/{document_id}/embeddings/status    Trạng thái job mới nhất
DELETE /api/v1/documents/{document_id}/embeddings/{job_id}  Huỷ embedding job
```

Swagger UI đầy đủ:

```text
http://localhost:8000/docs
```

## 9. Quality gates

Chạy trước khi commit:

```powershell
cd D:\VAIC-Nextlevel\backend

# Format code
python -m ruff format .

# Lint
python -m ruff check .

# Type check
python -m mypy app --ignore-missing-imports

# Test
python -m pytest tests/
```

Chạy tất cả một lệnh:

```powershell
cd D:\VAIC-Nextlevel\backend
python -m ruff format . ; python -m ruff check . ; python -m mypy app --ignore-missing-imports ; python -m pytest tests/
```

## 10. Lỗi thường gặp

### Docker báo thiếu biến môi trường

Nếu thấy warning kiểu `POSTGRES_PASSWORD variable is not set`, kiểm tra file `.env` ở root project.

### `docker compose up` lỗi vì frontend

Repo hiện chưa có thư mục `frontend`. Chạy các service backend-only:

```powershell
docker compose up -d postgres embedding-service backend
```

### `/health/ready` lỗi database

Kiểm tra Postgres đã healthy chưa:

```powershell
docker compose ps
```

Sau đó chạy migration:

```powershell
docker compose exec backend alembic upgrade head
```

### Port bị trùng

Các port mặc định:

```text
Backend:           8000
Embedding service: 8001
Postgres:          5434
Frontend:          3000
Nginx:             80
```

Nếu port bị chiếm, sửa phần `ports` trong `docker-compose.yml`.

## 11. Ghi chú phát triển

- Backend dùng FastAPI.
- Database dùng PostgreSQL với extension `vector`, `uuid-ossp`, `pg_trgm`.
- Migration quản lý bằng Alembic.
- Embedding service là một FastAPI app riêng trong `docker/embedding_server.py`.
- File upload mặc định lưu vào thư mục `uploads`.
