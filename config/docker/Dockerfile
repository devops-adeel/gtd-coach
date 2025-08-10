# Use official Python image to avoid "externally managed environment" issues
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    bc \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application package
COPY gtd_coach/ ./gtd_coach/

# Copy configuration
COPY config/ ./config/

# Copy scripts
COPY scripts/ ./scripts/

# Copy tests (optional, for testing in container)
COPY tests/ ./tests/

# Make scripts executable
RUN chmod +x scripts/timer.sh scripts/start-coach.sh scripts/docker-run.sh

# Create directories for data persistence (will be mounted as volumes)
RUN mkdir -p data logs summaries

# Set environment variable to indicate we're running in Docker
ENV IN_DOCKER=true

# Set Python path
ENV PYTHONPATH=/app

# Default command - can be overridden
CMD ["python3", "-m", "gtd_coach"]