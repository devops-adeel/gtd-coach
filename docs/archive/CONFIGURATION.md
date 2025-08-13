# GTD Coach Configuration Guide

This document covers all configuration options for GTD Coach, including environment variables, integrations, and customization options.

## Environment Variables

GTD Coach uses environment variables for configuration. Create a `.env` file in the project root:

```bash
cp config/.env.example .env
```

## Core Configuration

### LM Studio Settings

**Required** for core functionality:

```bash
# LM Studio API endpoint
LM_STUDIO_URL=http://localhost:1234/v1

# Model name (must match loaded model in LM Studio)
LM_STUDIO_MODEL=meta-llama-3.1-8b-instruct

# Request timeout in seconds
LM_STUDIO_TIMEOUT=30

# Max tokens per response
LM_STUDIO_MAX_TOKENS=500

# Temperature for response variation (0.0-1.0)
LM_STUDIO_TEMPERATURE=0.7
```

### Coaching Style

```bash
# Coaching tone: 'firm' or 'gentle'
COACHING_STYLE=firm

# Phase time multiplier (1.0 = normal, 0.5 = half time, 2.0 = double time)
PHASE_TIME_MULTIPLIER=1.0

# Enable/disable audio alerts
ENABLE_AUDIO_ALERTS=true

# Audio alert volume (0.0-1.0)
AUDIO_VOLUME=0.7
```

### Logging

```bash
# Log level: DEBUG, INFO, WARNING, ERROR, CRITICAL
LOG_LEVEL=INFO

# Log file location (empty = console only)
LOG_FILE=logs/gtd_coach.log

# Log format
LOG_FORMAT=%(asctime)s - %(name)s - %(levelname)s - %(message)s
```

## Optional Integrations

### Timing App Integration

Track real project time and calculate focus metrics:

```bash
# Enable Timing integration
ENABLE_TIMING=true

# Timing API key (get from https://web.timingapp.com)
TIMING_API_KEY=your-api-key-here

# Minimum minutes to consider a project (filters noise)
TIMING_MIN_MINUTES=30

# Days to look back for project data
TIMING_LOOKBACK_DAYS=7

# Calculate focus scores
TIMING_CALCULATE_FOCUS=true
```

### Langfuse Observability

Monitor LLM performance and track metrics:

```bash
# Enable Langfuse integration
ENABLE_LANGFUSE=true

# Langfuse server URL
LANGFUSE_HOST=http://localhost:3000

# API credentials
LANGFUSE_PUBLIC_KEY=pk-lf-...
LANGFUSE_SECRET_KEY=sk-lf-...

# Cache TTL for prompts (seconds)
LANGFUSE_CACHE_TTL_SECONDS=300

# Flush interval for batched events
LANGFUSE_FLUSH_INTERVAL=1000

# Enable A/B testing
LANGFUSE_AB_TESTING=true
```

### Graphiti Memory

Knowledge graph for long-term memory:

```bash
# Enable Graphiti integration
ENABLE_GRAPHITI=true

# Neo4j connection
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=your-password-here

# Graphiti settings
GRAPHITI_BATCH_SIZE=5
GRAPHITI_SKIP_TRIVIAL=true
SEMAPHORE_LIMIT=2

# Use custom GTD entities
USE_GTD_ENTITIES=true
```

## Data Storage

### File Locations

```bash
# Data directory for captures and priorities
DATA_DIR=./data

# Log directory
LOG_DIR=./logs

# Summary output directory
SUMMARY_DIR=./summaries

# Backup directory
BACKUP_DIR=./backups

# Archive old data after N days
ARCHIVE_AFTER_DAYS=90
```

### Data Format

```bash
# Output format: json, yaml, markdown
OUTPUT_FORMAT=json

# Pretty print JSON
JSON_PRETTY_PRINT=true

# Include timestamps
INCLUDE_TIMESTAMPS=true

# Compress old files
COMPRESS_ARCHIVES=true
```

## Feature Flags

Enable/disable specific features:

```bash
# Pattern detection
ENABLE_PATTERN_DETECTION=true
DETECT_TASK_SWITCHING=true
DETECT_HYPERFOCUS=true
DETECT_OVERWHELM=true

# Memory features
ENABLE_MEMORY_ENHANCEMENT=true
SHOW_RECURRING_PATTERNS=true
CONTEXT_FROM_PREVIOUS_SESSIONS=true

# Summary generation
ENABLE_SUMMARY_GENERATION=true
SUMMARY_INCLUDE_METRICS=true
SUMMARY_INCLUDE_INSIGHTS=true

# Experimental features
ENABLE_VOICE_INPUT=false
ENABLE_WEB_UI=false
ENABLE_CALENDAR_SYNC=false
```

## Prompt Configuration

### Prompt Files

Prompts are stored in `config/prompts/`:

```bash
# System prompt selection
PROMPT_STYLE=firm  # Options: firm, gentle, custom

# Custom prompt file (if PROMPT_STYLE=custom)
CUSTOM_PROMPT_FILE=config/prompts/my_custom.txt

# Fallback prompt for timeouts
FALLBACK_PROMPT_FILE=config/prompts/fallback.txt

# Dynamic prompt variables
PROMPT_INCLUDE_TIME=true
PROMPT_INCLUDE_PATTERNS=true
PROMPT_INCLUDE_HISTORY=true
```

### Prompt Variables

Available variables in prompts:
- `{{phase_name}}`: Current phase
- `{{time_remaining}}`: Minutes left in phase
- `{{total_time}}`: Total review time
- `{{user_name}}`: User's name (if set)
- `{{date}}`: Current date
- `{{previous_patterns}}`: Detected patterns from past

## Docker Configuration

### Docker Environment

For Docker deployments, use environment variables:

```yaml
# docker-compose.yml
version: '3.8'

services:
  gtd-coach:
    image: gtd-coach:latest
    env_file:
      - .env
    environment:
      - LM_STUDIO_URL=http://host.docker.internal:1234/v1
    volumes:
      - ./data:/app/data
      - ./logs:/app/logs
      - ./config:/app/config
```

### Docker-Specific Settings

```bash
# Use host networking (Linux only)
DOCKER_USE_HOST_NETWORK=false

# Volume mount paths
DOCKER_DATA_PATH=./data
DOCKER_LOG_PATH=./logs
DOCKER_CONFIG_PATH=./config
```

## Performance Tuning

### Memory Management

```bash
# Max memory usage (MB)
MAX_MEMORY_MB=512

# Garbage collection threshold
GC_THRESHOLD=100

# Cache size for patterns
PATTERN_CACHE_SIZE=1000
```

### Timeout Settings

```bash
# Phase transition timeout (seconds)
PHASE_TRANSITION_TIMEOUT=5

# User input timeout (seconds)
USER_INPUT_TIMEOUT=300

# LLM retry attempts
LLM_RETRY_ATTEMPTS=3

# Retry delay (seconds)
LLM_RETRY_DELAY=2
```

## Security Configuration

### API Security

```bash
# Enable API key validation
REQUIRE_API_KEY=false

# API key (if required)
API_KEY=your-secure-key

# Enable HTTPS only
HTTPS_ONLY=false

# SSL certificate paths
SSL_CERT_FILE=
SSL_KEY_FILE=
```

### Data Security

```bash
# Encrypt data at rest
ENCRYPT_DATA=false

# Encryption key (if enabled)
ENCRYPTION_KEY=

# Sanitize logs
SANITIZE_LOGS=true

# Mask sensitive data
MASK_SENSITIVE_DATA=true
```

## Advanced Configuration

### Custom Handlers

```bash
# Custom phase handler module
CUSTOM_PHASE_HANDLER=

# Custom pattern detector
CUSTOM_PATTERN_DETECTOR=

# Custom timer implementation
CUSTOM_TIMER_CLASS=
```

### Webhook Notifications

```bash
# Enable webhooks
ENABLE_WEBHOOKS=false

# Webhook URL
WEBHOOK_URL=

# Webhook events
WEBHOOK_ON_START=true
WEBHOOK_ON_COMPLETE=true
WEBHOOK_ON_ERROR=true
```

### Database Configuration

For advanced users using a database:

```bash
# Database URL (SQLAlchemy format)
DATABASE_URL=sqlite:///gtd_coach.db

# Connection pool size
DB_POOL_SIZE=5

# Enable database logging
DB_ECHO=false
```

## Configuration Precedence

Configuration is loaded in this order (later overrides earlier):

1. Default values in code
2. `config/defaults.yaml` (if exists)
3. `.env` file
4. Environment variables
5. Command-line arguments

## Validation

GTD Coach validates configuration on startup:

```python
# Run configuration check
python -m gtd_coach --check-config

# Validate specific integration
python -m gtd_coach --check-integration timing
```

## Troubleshooting Configuration

### Debug Configuration

```bash
# Show all configuration values
python -m gtd_coach --show-config

# Test specific integration
python -m gtd_coach --test-integration graphiti
```

### Common Issues

**Environment variables not loading:**
- Ensure `.env` file is in project root
- Check file permissions
- Verify no syntax errors in `.env`

**Integration not working:**
- Check ENABLE_* flag is true
- Verify API keys are valid
- Test connection independently

**Performance issues:**
- Reduce batch sizes
- Increase timeouts
- Check memory limits

## Migration from Old Configuration

If upgrading from an older version:

```bash
# Migrate old configuration
python scripts/migrate_config.py

# This will:
# 1. Read old configuration files
# 2. Convert to new format
# 3. Create new .env file
# 4. Backup old configuration
```

## Example Configurations

### Minimal Configuration

```bash
# .env.minimal
LM_STUDIO_URL=http://localhost:1234/v1
```

### Full-Featured Configuration

```bash
# .env.full
# Core
LM_STUDIO_URL=http://localhost:1234/v1
COACHING_STYLE=firm
LOG_LEVEL=INFO

# Integrations
ENABLE_TIMING=true
TIMING_API_KEY=xxx
ENABLE_LANGFUSE=true
LANGFUSE_PUBLIC_KEY=xxx
LANGFUSE_SECRET_KEY=xxx
ENABLE_GRAPHITI=true
NEO4J_PASSWORD=xxx

# Features
ENABLE_PATTERN_DETECTION=true
ENABLE_SUMMARY_GENERATION=true
```

### Development Configuration

```bash
# .env.dev
LM_STUDIO_URL=http://localhost:1234/v1
LOG_LEVEL=DEBUG
PHASE_TIME_MULTIPLIER=0.1  # Fast phases for testing
ENABLE_AUDIO_ALERTS=false
```

## Support

For configuration help:
- Check this guide first
- Review `.env.example` for all options
- See troubleshooting section
- Open an issue if needed