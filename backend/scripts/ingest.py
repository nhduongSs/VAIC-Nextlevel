"""
Chạy: python -m scripts.ingest
Nạp toàn bộ văn bản trong data/raw/ (đã chuẩn hóa theo điều/khoản, xem
app/repositories/document_loader.py) vào Supabase/pgvector.

Gợi ý cấu trúc data/raw/:
  data/raw/lai_suat/        -> biểu lãi suất tiền gửi
  data/raw/rut_truoc_han/   -> quy định rút trước hạn
  data/raw/kyc/             -> quy định KYC
  data/raw/bao_hiem/        -> bảo hiểm tiền gửi
"""
from sentence_transformers import SentenceTransformer

from app.core.config import get_settings
from app.repositories.document_loader import load_documents
from app.repositories.vector_store import get_vector_store

settings = get_settings()


def main():
    clauses = load_documents(settings.data_dir)
    if not clauses:
        print(f"Không tìm thấy văn bản nào trong {settings.data_dir}. Kiểm tra lại đường dẫn/định dạng.")
        return

    embedder = SentenceTransformer(settings.embedding_model)
    embeddings = embedder.encode([c.content for c in clauses]).tolist()

    store = get_vector_store()
    store.add_clauses(clauses, embeddings)
    print(f"Đã nạp {len(clauses)} điều/khoản vào vector store.")


if __name__ == "__main__":
    main()
