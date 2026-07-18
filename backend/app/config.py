from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # ── Application ────────────────────────────────────────────────────────
    APP_NAME: str = "VAIC Banking RAG API"
    APP_VERSION: str = "1.0.0"
    ENV: str = "development"
    DEBUG: bool = False

    # ── Database ───────────────────────────────────────────────────────────
    DATABASE_URL: str = "postgresql+asyncpg://vaic_nextlevel:12345678@localhost:5434/vaic_nextlevel_db"
    DB_POOL_SIZE: int = 10
    DB_MAX_OVERFLOW: int = 20
    DB_POOL_TIMEOUT: int = 30

    # ── AI Services ────────────────────────────────────────────────────────
    EMBEDDING_SERVICE_URL: str = "http://embedding-service:8001"
    EMBEDDING_BATCH_SIZE: int = 32
    EMBEDDING_MAX_CONCURRENCY: int = 4
    EMBEDDING_MAX_RETRIES: int = 2
    EMBEDDING_RETRY_DELAY: float = 2.0
    EMBEDDING_TIMEOUT: float = 60.0  # seconds per batch HTTP call
    EMBEDDING_BATCH_TIMEOUT: float = 120.0  # seconds per asyncio task (includes network + GPU)
    DEEPSEEK_API_KEY: str = ""

    # ── Security ───────────────────────────────────────────────────────────
    JWT_SECRET_KEY: str = "dev-secret-key-change-in-production"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    BCRYPT_ROUNDS: int = 12

    # ── Logging ────────────────────────────────────────────────────────────
    LOG_LEVEL: str = "INFO"

    # ── CORS ───────────────────────────────────────────────────────────────
    ALLOWED_ORIGINS: list[str] = ["http://localhost:3000", "http://localhost"]
    ALLOWED_HOSTS: list[str] = ["localhost", "127.0.0.1"]

    # ── File Upload ────────────────────────────────────────────────────────
    UPLOAD_DIR: str = "uploads"
    MAX_UPLOAD_SIZE_MB: int = 50
    ALLOWED_CONTENT_TYPES: list[str] = [
        "application/pdf",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "application/msword",
        "text/plain",
    ]

    # ── Rate Limiting ──────────────────────────────────────────────────────
    RATE_LIMIT_QUERY: str = "10/minute"
    RATE_LIMIT_UPLOAD: str = "5/minute"

    model_config = SettingsConfigDict(
        env_file=".env",
        case_sensitive=True,
        extra="ignore",
    )

    @property
    def is_production(self) -> bool:
        return self.ENV == "production"

    @property
    def json_logs(self) -> bool:
        return self.is_production

    @property
    def max_upload_size_bytes(self) -> int:
        return self.MAX_UPLOAD_SIZE_MB * 1024 * 1024


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings: Settings = get_settings()
