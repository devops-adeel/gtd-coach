# Multi-stage Dockerfile for GTD Coach
# Supports both production and testing environments

# Stage 1: Base image with system dependencies
FROM python:3.11-slim-bookworm AS base

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    DEBIAN_FRONTEND=noninteractive

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    git \
    curl \
    make \
    libffi-dev \
    libssl-dev \
    && rm -rf /var/lib/apt/lists/*

# Stage 2: Dependencies installation
FROM base AS dependencies

WORKDIR /app

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --upgrade pip setuptools wheel && \
    pip install --no-cache-dir -r requirements.txt

# Install additional test dependencies
RUN pip install --no-cache-dir \
    pytest-xdist \
    pytest-json-report \
    pytest-cov \
    pytest-timeout \
    pytest-env \
    pytest-benchmark

# Stage 3: Application
FROM dependencies AS app

WORKDIR /app

# Copy application code
COPY . .

# Create necessary directories
RUN mkdir -p /app/data \
    /app/logs \
    /app/summaries \
    /app/test-results \
    /app/.pytest_cache

# Set Python path
ENV PYTHONPATH=/app:$PYTHONPATH

# Stage 4: Development/Testing environment
FROM app AS development

# Install development tools
RUN pip install --no-cache-dir \
    ipython \
    ipdb \
    black \
    flake8 \
    mypy \
    pre-commit

# Set development environment variables
ENV ENVIRONMENT=development \
    TEST_MODE=false \
    DEBUG=true

# Default command for development
CMD ["python", "-m", "gtd_coach"]

# Stage 5: Testing environment
FROM app AS testing

# Set testing environment variables
ENV ENVIRONMENT=testing \
    TEST_MODE=true \
    MOCK_EXTERNAL_APIS=true \
    PYTEST_WORKERS=auto

# Run tests by default
CMD ["python", "-m", "pytest", "tests/", "-v", "--tb=short"]

# Stage 6: Production environment
FROM app AS production

# Create non-root user for security
RUN useradd -m -u 1000 appuser && \
    chown -R appuser:appuser /app

USER appuser

# Set production environment variables
ENV ENVIRONMENT=production \
    TEST_MODE=false \
    DEBUG=false

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import sys; sys.exit(0)"

# Default command for production
CMD ["python", "-m", "gtd_coach"]