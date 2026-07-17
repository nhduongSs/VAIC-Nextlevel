FROM python:3.12-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install non-torch dependencies first (smaller, faster layer)
RUN pip install --no-cache-dir fastapi "uvicorn[standard]" "pydantic>=2.0"

# Install CPU-mode PyTorch separately so --index-url does not affect other packages
RUN pip install --no-cache-dir torch --index-url https://download.pytorch.org/whl/cpu

# sentence-transformers depends on torch; install after torch is present
RUN pip install --no-cache-dir sentence-transformers

COPY embedding_server.py .

EXPOSE 8001

HEALTHCHECK --interval=30s --timeout=10s --start-period=120s --retries=3 \
    CMD curl -f http://localhost:8001/health || exit 1

CMD ["uvicorn", "embedding_server:app", "--host", "0.0.0.0", "--port", "8001"]
