# =============================================================================
# Verity MVP - Dockerfile
# =============================================================================
# Multi-stage build for production deployment to Cloud Run
# =============================================================================

# Stage 1: Builder
FROM python:3.11-slim as builder

WORKDIR /app

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy project files
COPY pyproject.toml .
COPY src/ src/

# Create wheel
RUN pip install --no-cache-dir build && \
    python -m build --wheel

# Stage 2: Runtime
FROM python:3.11-slim

WORKDIR /app

# Create non-root user
RUN groupadd -r verity && useradd -r -g verity verity

# Install runtime dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Copy wheel from builder
COPY --from=builder /app/dist/*.whl /tmp/

# Install application
RUN pip install --no-cache-dir /tmp/*.whl && \
    rm /tmp/*.whl

# Copy OpenAPI spec (if serving static)
COPY openapi.json /app/

# Set ownership
RUN chown -R verity:verity /app

# Switch to non-root user
USER verity

# Environment variables
ENV PORT=8080
ENV APP_ENV=production
ENV APP_DEBUG=false

# Expose port
EXPOSE 8080

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import httpx; httpx.get('http://localhost:8080/health').raise_for_status()"

# Run application
CMD ["uvicorn", "verity.main:app", "--host", "0.0.0.0", "--port", "8080", "--workers", "2"]
