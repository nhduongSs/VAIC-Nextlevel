from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # ── Application ────────────────────────────────────────────────────────
    APP_NAME: str = "VAIC Banking RAG API"
    APP_VERSION: str = "1.0.0"
    ENV: str = "development"
    DEBUG: bool = False

    # ── Database ───────────────────────────────────────────────────────────
    DATABASE_URL: str = "postgresql+asyncpg://vaic_user:password@localhost:5432/vaic_db"
    DB_POOL_SIZE: int = 10
    DB_MAX_OVERFLOW: int = 20
    DB_POOL_TIMEOUT: int = 30

    # ── AI Services ────────────────────────────────────────────────────────
    EMBEDDING_SERVICE_URL: str = "http://embedding-service:8001"
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


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings: Settings = get_settings()
