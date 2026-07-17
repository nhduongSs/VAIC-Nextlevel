# 11 — Deployment

## Purpose

Thiết kế deployment với Docker Compose cho hackathon — đơn giản, reproducible, chạy được trên một máy duy nhất.

---

## Architecture Deployment

```mermaid
graph TB
    subgraph Docker Compose Network
        NGINX[nginx:alpine\nPort 80/443\nReverse Proxy]
        BACKEND[backend:python3.12\nPort 8000\nFastAPI]
        FRONTEND[frontend:node\nPort 3000\nReact]
        DB[(postgres:16\nPort 5432\nPostgreSQL + pgvector)]
        EMBED[embedding-service\nPort 8001\nBGE-M3 HTTP API]
    end

    NGINX -->|/api/*| BACKEND
    NGINX -->|/*| FRONTEND
    BACKEND --> DB
    BACKEND --> EMBED
    BACKEND -->|HTTPS| DEEPSEEK[DeepSeek API\nexternal]
```

---

## docker-compose.yml

```yaml
version: "3.9"

services:
  postgres:
    image: pgvector/pgvector:pg16
    environment:
      POSTGRES_DB: vaic_db
      POSTGRES_USER: vaic_user
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
    volumes:
      - postgres_data:/var/lib/postgresql/data
      - ./docker/init.sql:/docker-entrypoint-initdb.d/init.sql
    ports:
      - "5432:5432"
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U vaic_user -d vaic_db"]
      interval: 10s
      timeout: 5s
      retries: 5

  embedding-service:
    build:
      context: ./backend
      dockerfile: ../docker/embedding.Dockerfile
    ports:
      - "8001:8001"
    volumes:
      - model_cache:/root/.cache/huggingface
    environment:
      MODEL_NAME: BAAI/bge-m3
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8001/health"]
      interval: 30s
      timeout: 10s
      retries: 3

  backend:
    build:
      context: ./backend
      dockerfile: ../docker/backend.Dockerfile
    ports:
      - "8000:8000"
    environment:
      DATABASE_URL: postgresql+asyncpg://vaic_user:${POSTGRES_PASSWORD}@postgres:5432/vaic_db
      EMBEDDING_SERVICE_URL: http://embedding-service:8001
      DEEPSEEK_API_KEY: ${DEEPSEEK_API_KEY}
      JWT_SECRET_KEY: ${JWT_SECRET_KEY}
      ENV: production
    depends_on:
      postgres:
        condition: service_healthy
      embedding-service:
        condition: service_healthy
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 15s
      timeout: 5s
      retries: 5

  frontend:
    build:
      context: ./frontend
      dockerfile: ../docker/frontend.Dockerfile
    ports:
      - "3000:3000"
    environment:
      REACT_APP_API_URL: http://localhost/api
    depends_on:
      - backend

  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
    volumes:
      - ./docker/nginx.conf:/etc/nginx/nginx.conf:ro
    depends_on:
      - backend
      - frontend

volumes:
  postgres_data:
  model_cache:
```

---

## docker-compose.dev.yml (Development override)

```yaml
version: "3.9"

services:
  backend:
    volumes:
      - ./backend:/app
    command: uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
    environment:
      ENV: development

  frontend:
    volumes:
      - ./frontend:/app
    command: npm run dev
```

Run: `docker compose -f docker-compose.yml -f docker-compose.dev.yml up`

---

## Dockerfiles

### backend.Dockerfile

```dockerfile
FROM python:3.12-slim

WORKDIR /app

RUN pip install uv

COPY pyproject.toml .
RUN uv pip install --system -e ".[prod]"

COPY app/ ./app/
COPY alembic/ ./alembic/
COPY alembic.ini .

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "2"]
```

### embedding.Dockerfile

```dockerfile
FROM python:3.12-slim

WORKDIR /app

RUN pip install fastapi uvicorn sentence-transformers torch --index-url https://download.pytorch.org/whl/cpu

COPY docker/embedding_server.py .

EXPOSE 8001

CMD ["uvicorn", "embedding_server:app", "--host", "0.0.0.0", "--port", "8001"]
```

### frontend.Dockerfile

```dockerfile
FROM node:20-alpine AS builder
WORKDIR /app
COPY package*.json .
RUN npm ci
COPY . .
RUN npm run build

FROM nginx:alpine
COPY --from=builder /app/dist /usr/share/nginx/html
EXPOSE 3000
```

---

## nginx.conf

```nginx
events { worker_connections 1024; }

http {
    upstream backend {
        server backend:8000;
    }

    upstream frontend {
        server frontend:3000;
    }

    server {
        listen 80;

        # API routes
        location /api/ {
            proxy_pass http://backend/api/;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_read_timeout 120s;  # Allow for long LLM generation
        }

        location /auth/ {
            proxy_pass http://backend/auth/;
            proxy_set_header Host $host;
        }

        location /docs {
            proxy_pass http://backend/docs;
        }

        # Frontend
        location / {
            proxy_pass http://frontend/;
            proxy_set_header Host $host;
        }
    }
}
```

---

## Environment Variables (.env)

```bash
# Database
POSTGRES_PASSWORD=<strong-random-password>

# AI
DEEPSEEK_API_KEY=<deepseek-api-key>

# Security
JWT_SECRET_KEY=<256-bit-random-hex>

# App
ENV=production
```

`.env` is NEVER committed to git. Template: `.env.example`

---

## Database Initialization

### Alembic Migrations

```bash
# Run migrations on startup
alembic upgrade head
```

### init.sql (PostgreSQL extensions)

```sql
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS pg_trgm;
```

---

## Deployment Commands

```bash
# First time setup
cp .env.example .env
# Edit .env with real credentials

# Start all services
docker compose up -d

# Run DB migrations
docker compose exec backend alembic upgrade head

# Check status
docker compose ps

# View logs
docker compose logs -f backend

# Stop
docker compose down

# Full reset (wipe data)
docker compose down -v
```

---

## Health Checks

| Service | Endpoint | Expected |
|---|---|---|
| backend | GET /health | `{"status": "ok"}` |
| embedding-service | GET /health | `{"status": "ok", "model": "bge-m3"}` |
| postgres | pg_isready | exit 0 |
| nginx | port 80 | HTTP 200 |

---

## Observability

### Structured Logging

Tất cả log phải là JSON format để dễ parse:

```python
import structlog

logger = structlog.get_logger()

# Usage
logger.info("query_completed",
    query_id=str(query_id),
    user_id=str(user_id),
    latency_ms=latency,
    chunk_count=len(chunks),
    model="deepseek-chat",
)
```

Cấu hình structlog trong `app/main.py`:
```python
import structlog
structlog.configure(
    processors=[
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.JSONRenderer(),
    ]
)
```

### Request ID Tracing

Mỗi request phải có `request_id` duy nhất, gắn vào toàn bộ log:

```python
@app.middleware("http")
async def request_id_middleware(request: Request, call_next):
    request_id = request.headers.get("X-Request-ID", str(uuid4()))
    with structlog.contextvars.bound_contextvars(request_id=request_id):
        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        return response
```

### Metrics Endpoint (Basic)

```python
@app.get("/metrics")
async def metrics():
    """Basic metrics for monitoring. No Prometheus dependency required."""
    return {
        "uptime_seconds": time.time() - START_TIME,
        "total_queries": QUERY_COUNTER,
        "avg_latency_ms": AVG_LATENCY,
    }
```

---

## Resource Requirements

| Service | CPU | RAM | Disk |
|---|---|---|---|
| postgres | 1 core | 2 GB | 20 GB |
| embedding-service (CPU) | 4 cores | 4 GB | 5 GB (model) |
| backend | 2 cores | 1 GB | 500 MB |
| frontend | 0.5 core | 256 MB | 200 MB |
| nginx | 0.1 core | 64 MB | — |
| **Total** | **~8 cores** | **~7.5 GB** | **~26 GB** |

---

## Constraints

- Embedding service phải healthy trước khi backend start
- DB phải healthy trước khi backend start (alembic migrations)
- Tất cả secrets qua env vars, không hardcode
- BGE-M3 chạy CPU mode trong hackathon (không cần GPU)

---

## Trade-offs

| Choice | Benefit | Cost |
|---|---|---|
| Single Docker Compose | Easy to run, no K8s needed | Not horizontally scalable |
| CPU-based embedding | No GPU dependency | 3-5x slower embedding |
| nginx reverse proxy | Single entry point, path routing | Extra hop |

---

## Future Extensibility

- Add GPU support for embedding-service (`runtime: nvidia` in compose)
- Migrate to Kubernetes (Helm chart) for production
- Add horizontal scaling for backend (multiple replicas)
- Add Redis for caching frequent queries
- Add Prometheus + Grafana for monitoring
