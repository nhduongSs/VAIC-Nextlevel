# Deploy backend lên GCP (VM + docker-compose)

Runbook deploy cụm **backend + Postgres(pgvector) + embedding-service** lên một VM Compute Engine, chạy bằng `docker-compose.gcp.yml`. Frontend chạy riêng trên Railway.

- Backend công khai qua **HTTPS** nhờ **Caddy** tự cấp cert (Let's Encrypt).
- Không cần mua domain: dùng **nip.io** trỏ theo IP tĩnh của VM.

Ví dụ trong tài liệu dùng giá trị thật của lần deploy này — thay bằng của bạn khi cần:
- VM: `backend`, zone `us-central1-f`
- IP tĩnh: `136.113.232.9` → hostname `136-113-232-9.nip.io`
- Frontend Railway: `https://vaic-nextlevel.up.railway.app`

---

## Kiến trúc

```
Trình duyệt ──HTTPS──> Caddy (VM :443) ──> backend :8000 ──┬─> Postgres :5432 (pgvector)
                                                           └─> embedding-service :8001 (BGE-M3 + reranker)
Frontend (Railway) ──HTTPS──> Caddy (VM) ──> backend
```
Chỉ Caddy (80/443) lộ ra ngoài; postgres/embedding/backend chỉ nói chuyện trong mạng nội bộ của compose.

---

## 0. Chuẩn bị

- 1 GCP project, quyền tạo VM + firewall.
- `DEEPSEEK_API_KEY` (hoặc gateway tương thích OpenAI).
- URL frontend Railway (để cấu hình CORS).

---

## 1. Tạo VM

Compute Engine → Create instance:
- **Machine type: `e2-standard-4`** (4 vCPU / 16GB). Embedding cần RAM cho BGE-M3 + reranker; nhỏ hơn dễ OOM.
- OS: **Ubuntu 22.04 LTS**, **Boot disk ≥ 50GB**. ⚠️ Đĩa mặc định 10GB **không đủ** — model ~5GB + image torch vài GB sẽ làm đầy đĩa và hỏng khi tải model.
- Firewall: tick **Allow HTTP** và **Allow HTTPS**.

Hoặc gcloud:
```bash
gcloud compute instances create backend \
  --zone=us-central1-f --machine-type=e2-standard-4 \
  --image-family=ubuntu-2204-lts --image-project=ubuntu-os-cloud \
  --boot-disk-size=50GB --tags=http-server,https-server
```

---

## 2. IP tĩnh + hostname nip.io

Giữ IP hiện tại của VM thành tĩnh (IP không đổi):
```bash
gcloud compute instances list        # xem EXTERNAL_IP, ví dụ 136.113.232.9
gcloud compute addresses create vaic-backend-ip \
  --addresses=136.113.232.9 --region=us-central1
```

Ghép hostname nip.io: thay dấu `.` bằng `-`, thêm `.nip.io`:
```
136.113.232.9  ->  136-113-232-9.nip.io
```
nip.io tự phân giải về IP, không cần mua domain / tạo DNS. Kiểm tra:
```bash
nslookup 136-113-232-9.nip.io      # phải trả về 136.113.232.9
```

---

## 3. Firewall (mở 80/443)

Caddy cần 80 (HTTP-01 challenge) và 443 (HTTPS). Nếu chưa có rule:
```bash
gcloud compute firewall-rules create allow-http  --allow=tcp:80  --source-ranges=0.0.0.0/0 --target-tags=http-server
gcloud compute firewall-rules create allow-https --allow=tcp:443 --source-ranges=0.0.0.0/0 --target-tags=https-server
gcloud compute instances add-tags backend --zone=us-central1-f --tags=http-server,https-server
```

---

## 4. SSH vào VM + cài Docker

> ⚠️ Chạy các bước sau **TRÊN VM**, không phải Cloud Shell. Cloud Shell là máy tạm khác, không mang IP tĩnh — chạy stack ở đó thì Caddy không xin được cert và không ai truy cập được.

```bash
gcloud compute ssh backend --zone=us-central1-f     # dấu nhắc đổi thành ...@backend:~$
curl -fsSL https://get.docker.com | sudo sh
sudo usermod -aG docker $USER && newgrp docker
```

---

## 5. Clone repo + tạo `.env`

```bash
git clone -b ci-cd_phuongvd https://github.com/nhduongSs/VAIC-Nextlevel.git
cd VAIC-Nextlevel
cp .env.gcp.example .env
nano .env
```

Điền `.env` (giá trị mẫu theo lần deploy này):
```bash
POSTGRES_USER=vaic_nextlevel
POSTGRES_PASSWORD=<mật-khẩu-mạnh>
POSTGRES_DB=vaic_nextlevel_db

DEEPSEEK_API_KEY=<khóa-của-bạn>
DEEPSEEK_BASE_URL=https://api.deepseek.com
LLM_MODEL=deepseek-chat

JWT_SECRET_KEY=<sinh: python3 -c "import secrets; print(secrets.token_hex(32))">

BACKEND_DOMAIN=136-113-232-9.nip.io
# PHẢI có localhost/127.0.0.1 để healthcheck nội bộ không bị chặn 400
ALLOWED_HOSTS=["136-113-232-9.nip.io","localhost","127.0.0.1"]
# PHẢI là URL frontend Railway (https, KHÔNG dấu / cuối) — nếu sai/thiếu -> CORS chặn
ALLOWED_ORIGINS=["https://vaic-nextlevel.up.railway.app"]

MODEL_LOAD_STRATEGY=lazy
```

**Quy tắc dễ sai:**
- `ALLOWED_ORIGINS` = URL **frontend** (có `https://`, không `/` cuối).
- `ALLOWED_HOSTS` + `BACKEND_DOMAIN` = hostname **backend** (không `https://`).

---

## 6. Chạy stack

```bash
docker compose -f docker-compose.gcp.yml up -d --build
```
Lần đầu: build torch vài phút; embedding tải model ~5GB ở request `/embed` đầu tiên.

Caddy sẽ tự xin cert cho `BACKEND_DOMAIN`. Xem tiến trình:
```bash
docker compose -f docker-compose.gcp.yml logs -f caddy   # chờ "certificate obtained successfully"
```

---

## 7. Migration (tạo schema DB)

Extension (`vector`, `uuid-ossp`, `pg_trgm`) được `docker/init.sql` tự tạo khi Postgres khởi tạo lần đầu. Còn bảng thì phải chạy alembic:
```bash
docker compose -f docker-compose.gcp.yml exec backend alembic upgrade head
```

---

## 8. Kiểm tra

```bash
# Trạng thái — tất cả nên Up (healthy)
docker compose -f docker-compose.gcp.yml ps

# HTTPS + health (từ ngoài)
curl https://136-113-232-9.nip.io/health

# Embedding trả vector
docker compose -f docker-compose.gcp.yml exec backend \
  curl -sS -X POST http://embedding-service:8001/embed \
  -H "Content-Type: application/json" -d '{"texts":["xin chào"]}' | head -c 120

# CORS + chat end-to-end (phải có header access-control-allow-origin)
curl -i -X POST https://136-113-232-9.nip.io/api/v1/chat \
  -H "Origin: https://vaic-nextlevel.up.railway.app" \
  -H "Content-Type: application/json" \
  -d '{"session_id":"s1","message":"Lãi suất gửi 6 tháng?"}'
```

---

## 9. Nối frontend Railway

1. Railway → service frontend → **Variables** → `NEXT_PUBLIC_API_URL = https://136-113-232-9.nip.io` (https, không `/` cuối).
2. **Redeploy** frontend — `NEXT_PUBLIC_*` bị nướng vào bundle lúc build, đổi biến phải build lại.
   - Điều kiện: `docker/frontend.Dockerfile` phải có `ARG NEXT_PUBLIC_API_URL` (đã có) để `next build` nhận được biến từ Railway.
3. Verify: DevTools → request tới `https://136-113-232-9.nip.io/api/v1/chat` (không còn `localhost`).

---

## Vận hành

```bash
# Cập nhật code mới
git pull && docker compose -f docker-compose.gcp.yml up -d --build

# Đổi .env rồi áp lại 1 service
docker compose -f docker-compose.gcp.yml up -d backend

# Log / trạng thái
docker compose -f docker-compose.gcp.yml logs -f backend
docker compose -f docker-compose.gcp.yml ps

# Backup dữ liệu Postgres (volume postgres_data)
docker compose -f docker-compose.gcp.yml exec postgres \
  pg_dump -U vaic_nextlevel vaic_nextlevel_db > backup_$(date +%F).sql
```

---

## Troubleshooting (các lỗi đã gặp)

| Triệu chứng | Nguyên nhân | Cách sửa |
|---|---|---|
| Railway build: `npm ... no such file package.json` | Root Directory chưa trỏ vào `frontend` | Railway → Settings → Root Directory = `frontend`; và `RAILWAY_DOCKERFILE_PATH = docker/frontend.Dockerfile` |
| Frontend 502 Bad Gateway | `next start` nghe `localhost`, proxy không vào được | CMD dùng `-H 0.0.0.0` (đã có trong Dockerfile) |
| Caddy cert: `Timeout during connect (likely firewall)` | Chưa mở 80/443 | Tạo firewall rule 80/443 (mục 3) |
| Caddy cert: `Connection refused` liên tục | Stack đang chạy trong **Cloud Shell**, không phải VM | SSH vào VM rồi chạy lại (mục 4) |
| Embedding: `Can't load the model 'BAAI/bge-m3'` | **Hết đĩa** khi tải model | Tăng boot disk lên 50GB: `gcloud compute disks resize backend --size=50 --zone=...` rồi `sudo growpart /dev/sda 1 && sudo resize2fs /dev/sda1`; xóa cache hỏng: `docker volume rm vaic-nextlevel_model_cache` rồi `up -d` |
| Backend `Up (unhealthy)`, log `/health/live 400` | `ALLOWED_HOSTS` thiếu `localhost` (healthcheck curl localhost bị TrustedHostMiddleware chặn) | Thêm `localhost`,`127.0.0.1` vào `ALLOWED_HOSTS`, `up -d backend` |
| Frontend gọi `http://localhost:8000` (ERR_CONNECTION_REFUSED) | `NEXT_PUBLIC_API_URL` không được nạp lúc build | Dockerfile phải có `ARG NEXT_PUBLIC_API_URL` (đã có); set biến trên Railway + **redeploy** |
| Chat: `blocked by CORS policy` | `ALLOWED_ORIGINS` chưa chứa URL frontend | Đặt `ALLOWED_ORIGINS=["https://<frontend>.up.railway.app"]`, `up -d backend` |
| Chat: `Máy chủ trả lỗi: 500` | Chưa migrate DB, hoặc embedding lỗi | `alembic upgrade head`; kiểm embedding trả vector (mục 8); xem `logs backend` |

---

## Ghi chú

- **RAM:** BGE-M3 + reranker ~5GB. Nếu chat chập chờn/OOM (`docker inspect ... OOMKilled=true`), nâng lên `e2-standard-8` (32GB), hoặc giảm `--workers` backend.
- **nip.io** thỉnh thoảng đụng rate-limit cert Let's Encrypt (domain dùng chung) — nếu vướng, đổi `BACKEND_DOMAIN` sang `<ip-dashes>.sslip.io`.
- Chạy demo dùng nip.io là ổn; production nên có domain riêng rồi đổi 3 chỗ: `BACKEND_DOMAIN`, `ALLOWED_HOSTS`, và `NEXT_PUBLIC_API_URL` bên Railway.
