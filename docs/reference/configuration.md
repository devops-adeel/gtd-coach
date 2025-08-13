# Configuration Reference

## Environment Variables

### Core Settings

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `LM_STUDIO_URL` | Yes | `http://localhost:1234/v1` | LM Studio API endpoint |
| `LM_STUDIO_MODEL` | Yes | `meta-llama-3.1-8b-instruct` | Model name |
| `LM_STUDIO_TIMEOUT` | No | `30` | Request timeout (seconds) |
| `LM_STUDIO_MAX_TOKENS` | No | `500` | Max response tokens |
| `LM_STUDIO_TEMPERATURE` | No | `0.7` | Model temperature |

### Phase Timing

| Variable | Default | Description |
|----------|---------|-------------|
| `PHASE_STARTUP_MINUTES` | `2` | Startup phase duration |
| `PHASE_MINDSWEEP_MINUTES` | `10` | Mind sweep duration |
| `PHASE_PROJECT_MINUTES` | `12` | Project review duration |
| `PHASE_PRIORITY_MINUTES` | `5` | Prioritization duration |
| `PHASE_WRAPUP_MINUTES` | `3` | Wrap-up duration |

### Integration Settings

#### Timing App
| Variable | Required | Description |
|----------|----------|-------------|
| `TIMING_API_KEY` | No | API key from web.timingapp.com |
| `TIMING_MIN_MINUTES` | No | Minimum minutes to include project (default: 30) |

#### Langfuse
| Variable | Required | Description |
|----------|----------|-------------|
| `LANGFUSE_PUBLIC_KEY` | No | Public API key |
| `LANGFUSE_SECRET_KEY` | No | Secret API key |
| `LANGFUSE_HOST` | No | API host (default: cloud.langfuse.com) |

#### Graphiti
| Variable | Required | Description |
|----------|----------|-------------|
| `NEO4J_URI` | No | Neo4j database URI |
| `NEO4J_USERNAME` | No | Database username |
| `NEO4J_PASSWORD` | No | Database password |
| `GRAPHITI_API_KEY` | No | OpenAI API key for entity extraction |
| `GRAPHITI_BATCH_SIZE` | No | Episodes per batch (default: 5) |

#### Todoist
| Variable | Required | Description |
|----------|----------|-------------|
| `TODOIST_API_KEY` | No | Todoist API token |
| `TODOIST_PROJECT_ID` | No | Target project ID |

### Feature Flags

| Variable | Default | Description |
|----------|---------|-------------|
| `ENABLE_TIMING` | `true` | Enable Timing integration if configured |
| `ENABLE_LANGFUSE` | `true` | Enable Langfuse tracking if configured |
| `ENABLE_GRAPHITI` | `true` | Enable Graphiti memory if configured |
| `ENABLE_AUDIO_ALERTS` | `true` | Enable timer audio alerts |
| `DEBUG_MODE` | `false` | Enable debug logging |

## Configuration Files

### .env
Main configuration file. Copy from `config/.env.example`.

### .env.graphiti
Graphiti-specific settings. Keep separate for security.

### prompts/
- `system-prompt.txt`: Full coaching prompt
- `system-prompt-simple.txt`: Simplified fallback prompt

### data/
- `mindsweep_*.json`: Captured thoughts
- `priorities_*.json`: ABC priorities
- `graphiti_batch_*.json`: Memory episodes

## Docker Configuration

### docker-compose.yml
```yaml
environment:
  - LM_STUDIO_URL=${LM_STUDIO_URL:-http://host.docker.internal:1234/v1}
```

### Dockerfile
- Base image: `python:3.11-slim`
- Working directory: `/app`
- User: `appuser` (non-root)