# How to Configure Integrations

## Timing App Integration

Track actual time spent on projects and correlate with GTD priorities.

### Setup

1. Get API key from [Timing Connect](https://web.timingapp.com)
2. Add to `.env`:
```bash
TIMING_API_KEY=your-key-here
TIMING_MIN_MINUTES=30  # Minimum project time threshold
```

### Testing
```bash
# Test connection
./scripts/deployment/docker-run.sh timing

# Run review with Timing data
./scripts/deployment/docker-run.sh
```

### Features
- Fetches project data during STARTUP phase
- Calculates focus scores (0-100)
- Detects context switches and hyperfocus
- Correlates time with GTD priorities

## Langfuse Observability

Monitor LLM performance and track coaching effectiveness.

### Setup

1. Create account at [Langfuse Cloud](https://cloud.langfuse.com)
2. Add to `.env`:
```bash
LANGFUSE_PUBLIC_KEY=pk-lf-...
LANGFUSE_SECRET_KEY=sk-lf-...
LANGFUSE_HOST=https://cloud.langfuse.com  # Optional
```

### Testing
```bash
# Test connection
./scripts/deployment/docker-run.sh test

# Upload prompts
python3 upload_prompts_to_langfuse.py
```

### Features
- Tracks response latency per phase
- Monitors retry patterns
- A/B tests coaching tones
- Links prompts to traces

## Graphiti Memory

Build a knowledge graph of your GTD history and patterns.

### Setup

1. Set up Neo4j database (local or cloud)
2. Add to `.env.graphiti`:
```bash
NEO4J_URI=bolt://localhost:7687
NEO4J_USERNAME=neo4j
NEO4J_PASSWORD=your-password
GRAPHITI_API_KEY=your-openai-key  # For entity extraction
```

### Testing
```bash
# Test connection
python3 test_graphiti_connection.py

# Validate data
python3 gtd_validation.py
```

### Features
- Stores GTD entities (projects, actions, contexts)
- Tracks ADHD patterns over time
- Enables pattern-based interventions
- Provides memory retrieval at startup

## Todoist Integration

Sync tasks with Todoist for mobile access.

### Setup

1. Get API token from [Todoist Settings](https://todoist.com/app/settings/integrations)
2. Add to `.env`:
```bash
TODOIST_API_KEY=your-token-here
TODOIST_PROJECT_ID=your-project-id  # Optional, defaults to Inbox
```

### Features
- Exports priorities to Todoist
- Syncs project updates
- Creates tasks with GTD labels

## Configuration Priority

When multiple integrations are configured:
1. **Timing**: Runs first during STARTUP
2. **Graphiti**: Captures throughout session
3. **Langfuse**: Tracks all LLM calls
4. **Todoist**: Exports during WRAP-UP

All integrations are optional and the system works without them.