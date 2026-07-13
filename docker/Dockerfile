# syntax=docker/dockerfile:1

FROM python:3.11-slim AS builder

# Cài uv vào image
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

WORKDIR /app

# System deps for OpenCV (cần cho Phase 1+)
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1 \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

# Copy lockfile + pyproject để cache layer dependencies
COPY pyproject.toml uv.lock ./

# Install dependencies vào /app/.venv
RUN uv sync --frozen --no-dev --no-install-project

# Runtime stage
FROM python:3.11-slim AS runtime

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1 \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

# Copy venv từ builder
COPY --from=builder /app/.venv /app/.venv

# Set PATH để dùng python từ venv
ENV PATH="/app/.venv/bin:$PATH"

COPY app/ ./app/

# DINOv2 compare weights (~330MB) download from HuggingFace on first load.
# To keep the first /compare-images request inside the .NET 5s timeout, either:
#   (a) uncomment the pre-download below to bake weights into the image (needs network at build), or
#   (b) set COMPARE_WARMUP_ON_STARTUP=true so the model loads during app startup.
# ENV HF_HOME=/app/.cache/huggingface
# RUN python -c "from transformers import AutoImageProcessor, AutoModel; \
#     AutoImageProcessor.from_pretrained('facebook/dinov2-base'); \
#     AutoModel.from_pretrained('facebook/dinov2-base')"

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/api/v1/health')"

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
