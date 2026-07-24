# Core EAP v1.0 - single deployable API/Runtime service (MVP1 topology).
FROM python:3.11-slim AS base

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# Install dependencies first for better layer caching.
COPY pyproject.toml README.md ./
COPY src ./src
COPY contracts ./contracts

# Install the package with real backend clients (boto3/psycopg/pymilvus/redis).
RUN pip install --upgrade pip && pip install ".[adapters]"

# Run as a non-root user.
RUN useradd --create-home --uid 10001 eap
USER eap

EXPOSE 8080

# Default configuration targets real CRISIL backends in a cluster; override via env.
ENV EAP_ENV=prod \
    EAP_METADATA_BACKEND=postgres \
    EAP_ARTIFACT_BACKEND=s3 \
    EAP_LLM_BACKEND=gateway \
    EAP_DOCLING_BACKEND=gateway \
    EAP_VECTOR_BACKEND=milvus \
    EAP_OTEL_ENABLED=true \
    EAP_AUTH_ENABLED=true

HEALTHCHECK --interval=30s --timeout=3s --retries=3 \
    CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://localhost:8080/health').status==200 else 1)"

CMD ["uvicorn", "eap.api_gateway.app:app", "--host", "0.0.0.0", "--port", "8080"]
