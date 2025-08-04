# Docker Deployment for GTD Coach

## Overview

This deployment uses Docker/OrbStack to avoid Python "externally managed environment" issues while maintaining full functionality of the GTD Coach with Langfuse integration.

## Architecture

```
┌─────────────────────────────────────────┐
│         Docker Container                 │
│   ┌─────────────────────────────────┐   │
│   │     GTD Coach Application       │   │
│   │  - Python 3.11 (official image) │   │
│   │  - All dependencies installed   │   │
│   │  - Langfuse SDK with OpenAI    │   │
│   └─────────────────────────────────┘   │
│                    │                     │
│         Host Networking Mode             │
│                    │                     │
└────────────────────┼─────────────────────┘
                     │
    ┌────────────────┴────────────────┐
    │                                  │
    ▼                                  ▼
┌──────────────────┐        ┌──────────────────┐
│   LM Studio       │        │    Langfuse      │
│ localhost:1234    │        │ localhost:3000   │
└──────────────────┘        └──────────────────┘
```

## Key Features

1. **Host Networking**: OrbStack's native support allows seamless access to localhost services
2. **Volume Mounts**: Data persistence through mounted directories (data/, logs/, summaries/)
3. **Live Code Updates**: Python files are mounted read-only for development
4. **Audio Alert Handling**: Gracefully disabled in container (visual indicators still work)

## Usage

### Basic Commands

```bash
# Run weekly review
./docker-run.sh

# Test Langfuse integration
./docker-run.sh test

# Generate weekly summary
./docker-run.sh summary

# Rebuild after dependency changes
./docker-run.sh build

# Open shell for debugging
./docker-run.sh shell
```

### Docker Compose Commands

```bash
# Run specific service
docker compose run --rm gtd-coach
docker compose run --rm test-langfuse
docker compose run --rm generate-summary

# View logs
docker compose logs -f gtd-coach

# Stop all services
docker compose down
```

## File Structure

```
gtd-coach/
├── Dockerfile              # Multi-stage build for Python app
├── docker-compose.yml      # Service definitions
├── docker-run.sh          # Convenience wrapper script
├── .dockerignore          # Excludes unnecessary files
└── requirements.txt       # Python dependencies (including langfuse[openai])
```

## Benefits

1. **No Python Environment Issues**: Uses official Python image
2. **Consistent Dependencies**: Same environment every time
3. **Easy Updates**: Just rebuild when requirements change
4. **Development Friendly**: Mount local files for quick iteration
5. **Production Ready**: Can be deployed anywhere Docker runs

## Troubleshooting

### Container can't connect to LM Studio
- Ensure LM Studio is running on host
- Check it's listening on 0.0.0.0:1234, not just 127.0.0.1:1234

### Permission issues with mounted volumes
- Docker creates files as root by default
- Use `sudo` if needed to clean up files

### Slow performance on first run
- Docker needs to download base image and install dependencies
- Subsequent runs use cached layers

### Audio alerts not working
- This is expected - audio is disabled in containers
- Visual progress indicators still function

## Security Notes

- Langfuse keys are stored in `langfuse_tracker.py`
- Consider using environment variables for production
- The `.gitignore` excludes sensitive files
- Always use `langfuse_tracker.py.example` as template

## Next Steps

1. Monitor performance in Langfuse UI
2. Analyze weekly summaries for patterns
3. Adjust phase timings based on data
4. Consider deploying to cloud with proper secrets management