"""Project-wide constants."""

# ── Embedding ───────────────────────────────────────────────────────────────
EMBEDDING_DIMENSION = 1024
EMBEDDING_MODEL = "BAAI/bge-m3"
RERANKER_MODEL = "BAAI/bge-reranker-v2-m3"

# ── Retrieval ────────────────────────────────────────────────────────────────
RRF_K = 60
VECTOR_TOP_K = 20
BM25_TOP_K = 20
RERANK_TOP_K = 10
FINAL_TOP_K = 5
HNSW_EF_SEARCH = 64

# ── LLM ─────────────────────────────────────────────────────────────────────
MAX_CONTEXT_TOKENS = 6000
MAX_CHUNK_TOKENS = 1200
LLM_TEMPERATURE = 0.1
LLM_MAX_TOKENS = 2048

# ── Ingestion ────────────────────────────────────────────────────────────────
EMBEDDING_BATCH_SIZE = 32
MAX_CHUNKS_PER_DOCUMENT = 2000

# ── Pagination ───────────────────────────────────────────────────────────────
DEFAULT_PAGE_SIZE = 20
MAX_PAGE_SIZE = 100

# ── Rate Limiting ────────────────────────────────────────────────────────────
RATE_LIMIT_QUERY = "10/minute"
RATE_LIMIT_UPLOAD = "5/minute"

# ── API ──────────────────────────────────────────────────────────────────────
API_V1_PREFIX = "/api/v1"
