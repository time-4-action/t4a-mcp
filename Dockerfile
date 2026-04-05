# Multi-stage build for fast builds and small image size
FROM python:3.11-slim AS builder

# Install build dependencies (includes headers for unstructured/libmagic)
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    libmagic-dev \
    poppler-utils \
    tesseract-ocr \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .

# Install Python dependencies in a virtual environment
# Install torch CPU-only first (avoids pulling CUDA variant)
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"
# Install everything in one pass: PyTorch CPU index is primary so torch/torchvision
# resolve to CPU-only wheels; all other packages fall back to PyPI.
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir \
        --index-url https://download.pytorch.org/whl/cpu \
        --extra-index-url https://pypi.org/simple \
        -r requirements.txt

# ============================================
# Final stage - runtime image
FROM python:3.11-slim

# Runtime system deps (shared libs needed by unstructured, trafilatura, etc.)
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    curl \
    libmagic1 \
    poppler-utils \
    tesseract-ocr \
    && rm -rf /var/lib/apt/lists/*

RUN mkdir -p /app/chroma_db /app/uploads /app/bm25_indexes

WORKDIR /app

# Copy virtual environment from builder
COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Copy runtime-required code
COPY src/ ./src/
COPY app/ ./app/

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

CMD ["python", "-m", "uvicorn", "src.server.app:api", "--host", "0.0.0.0", "--port", "8000", "--proxy-headers", "--forwarded-allow-ips=*"]
