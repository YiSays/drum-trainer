FROM ghcr.io/astral-sh/uv:python3.11-bookworm-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    gcc \
    g++ \
    ffmpeg \
    libsndfile1 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY pyproject.toml uv.lock README.md .
COPY api/ api/
COPY core/ core/
COPY web_ui/ web_ui/

RUN uv sync --no-dev --frozen

ENV STORAGE_DIR=/tmp/storage
ENV TORCH_HOME=/tmp/torch_cache
ENV HF_HOME=/tmp/hf_cache

EXPOSE 7860

CMD ["uv", "run", "uvicorn", "api.server:app", "--host", "0.0.0.0", "--port", "7860"]
