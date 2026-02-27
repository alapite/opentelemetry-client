# Builder stage - creates virtual environment with all dependencies
FROM python:3.13-slim-bullseye AS builder
LABEL authors="abiola"

# Install build dependencies if needed for compiled packages
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        gcc \
        g++ \
        && apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Copy project files
WORKDIR /app
COPY pyproject.toml README.md ./
COPY src/ src/

# Create virtual environment and install dependencies
RUN python -m venv /venv && \
    /venv/bin/pip install --no-cache-dir --upgrade pip setuptools wheel && \
    /venv/bin/pip install --no-cache-dir -e .

# Production stage - minimal runtime image
FROM python:3.13-slim-bullseye AS production

# Build arguments for versioning and environment
ARG VERSION=latest
ARG TARGET_ENV=prod
ARG BUILD_DATE

# Add metadata labels
LABEL version="${VERSION}" \
      build_date="${BUILD_DATE}" \
      target_env="${TARGET_ENV}" \
      description="Primes Client Load Testing Platform"

# Copy virtual environment from builder
COPY --from=builder /venv /venv

# Set PATH to use venv binaries
ENV PATH="/venv/bin:$PATH"

# Copy source code (not needed in dev mode with volume mount, but needed for prod)
COPY src/ /app/src/
WORKDIR /app

# Default entrypoint for API server (can be overridden by docker-compose command)
# Development mode should use docker-compose.override.yml with volume mounts for hot-reload
# Production mode uses this entrypoint with --reload flag removed
ENTRYPOINT ["/venv/bin/uvicorn"]
CMD ["primes.api.main:app", "--host", "0.0.0.0", "--port", "8000"]

# Health check for production
HEALTHCHECK --interval=30s --timeout=10s --retries=3 --start-period=40s \
    CMD ["/venv/bin/python", "-c", "import requests; requests.get('http://localhost:8000/health', timeout=5)"]
