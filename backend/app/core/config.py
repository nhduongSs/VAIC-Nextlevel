"""
Cấu hình tập trung cho toàn hệ thống.
Đọc từ biến môi trường / file .env
"""
from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # --- LLM (DeepSeek V4) ---
    deepseek_api_key: str = ""
    deepseek_base_url: str = "https://api.deepseek.com"
    llm_model: str = "deepseek-chat"
    llm_max_tokens: int = 1024
    llm_temperature: float = 0.2  # thấp để giảm bịa đặt (hallucination)

    # --- Embedding / Vector store (Supabase + pgvector) ---
    embedding_model: str = "BAAI/bge-m3"  # local, hỗ trợ tiếng Việt tốt
    supabase_url: str = ""
    supabase_key: str = ""
    top_k_retrieval: int = 5
    similarity_threshold: float = 0.35  # dưới ngưỡng này -> coi như không có context phù hợp

    # --- Ingestion ---
    data_dir: str = "../data/raw"

    # --- Guardrail ---
    allow_out_of_scope_smalltalk: bool = True  # cho phép chào hỏi xã giao
    max_input_length: int = 1000
    log_blocked_requests: bool = True
    log_dir: str = "./logs"

    # --- App ---
    app_name: str = "RAG Tien Gui SHB"
    debug: bool = False


@lru_cache
def get_settings() -> Settings:
    return Settings()
