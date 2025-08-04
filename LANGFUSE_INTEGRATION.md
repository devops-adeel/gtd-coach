# Langfuse Integration for GTD Coach

## Overview

This integration adds LLM performance monitoring to GTD Coach using Langfuse, tracking:
- Response latency per phase
- Success/failure rates  
- Quality scores based on phase-specific thresholds

## Docker Deployment (Recommended)

Since your Python environment is externally managed, we've containerized the GTD Coach using Docker/OrbStack.

### Prerequisites

1. **OrbStack or Docker Desktop** installed and running
2. **LM Studio** running on localhost:1234 with Llama 3.1 8B model loaded
3. **Langfuse** running on localhost:3000 (self-hosted)
4. **Configure your keys**:
   ```bash
   cp langfuse_tracker.py.example langfuse_tracker.py
   # Edit langfuse_tracker.py with your actual keys
   ```

### Quick Start

```bash
# Run the weekly review
./docker-run.sh

# Test Langfuse integration
./docker-run.sh test

# Generate weekly summary
./docker-run.sh summary
```

### How It Works

The Docker setup:
- Uses official Python 3.11 image (avoids "externally managed" issues)
- Uses OrbStack's native host networking to connect to LM Studio and Langfuse
- Mounts your local data/logs/summaries directories for persistence
- Handles audio alerts gracefully (disabled in container)

### Testing the Integration

1. **Test Langfuse connectivity**:
   ```bash
   ./docker-run.sh test
   ```
   
   This will verify:
   - Configuration is valid
   - Can connect to Langfuse
   - Can make tracked LLM calls
   - Scoring works correctly

2. **Run a review with tracking**:
   ```bash
   ./docker-run.sh
   ```
   
   Then check Langfuse UI at http://localhost:3000 to see:
   - Session traces
   - Phase transitions
   - Response latencies
   - Quality scores

## Quality Scoring System

Each LLM response is scored on three dimensions:

1. **Success Score** (0 or 1)
   - 1 if response received without errors
   - 0 if timeout or error occurred

2. **Quality Score** (0 or 1)
   - Based on phase-specific latency thresholds:
   - STARTUP: 5.0s
   - MIND_SWEEP: 3.0s  
   - PROJECT_REVIEW: 2.0s
   - PRIORITIZATION: 3.0s
   - WRAP_UP: 4.0s

3. **Phase Appropriateness** (manual review)
   - Placeholder for reviewing response quality in Langfuse UI

## Architecture

```
Docker Container
     ├── GTD Coach Python Scripts
     ├── Langfuse SDK (installed)
     └── Host Networking
              ├── → LM Studio (localhost:1234)
              └── → Langfuse (localhost:3000)
```

## Troubleshooting

### "Cannot connect to Langfuse"
- Ensure Langfuse is running on localhost:3000
- Check if you can access http://localhost:3000 in browser
- Verify you've copied and configured `langfuse_tracker.py`:
  ```bash
  cp langfuse_tracker.py.example langfuse_tracker.py
  # Edit with your actual keys
  ```

### "LM Studio not found"
- Start LM Studio server: `lms server start`
- Load the model: `lms load meta-llama-3.1-8b-instruct`

### "Permission denied on docker-run.sh"
```bash
chmod +x docker-run.sh
```

### Audio alerts not working
- This is expected - audio is disabled in Docker
- The visual progress indicators still work

## Next Steps

1. Run a few review sessions to collect data
2. Check Langfuse UI for performance insights
3. Use the data to optimize prompts and settings
4. Consider setting up alerts for slow responses