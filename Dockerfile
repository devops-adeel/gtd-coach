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

# Copy application code
COPY *.py ./
COPY prompts/ ./prompts/
COPY scripts/ ./scripts/

# Make scripts executable
RUN chmod +x scripts/timer.sh

# Create directories for data persistence (will be mounted as volumes)
RUN mkdir -p data logs summaries

# Set environment variable to indicate we're running in Docker
ENV IN_DOCKER=true

# Default command - can be overridden
CMD ["python3", "gtd-review.py"]