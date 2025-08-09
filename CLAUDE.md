# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

GTD Coach is an ADHD-optimized Getting Things Done (GTD) weekly review system that uses LM Studio with a local Llama 3.1 8B model. The system provides structured, time-boxed coaching through five phases, with audio alerts and strict time limits designed specifically for ADHD users.

## Essential Commands

### IMPORTANT: Run all Python scripts in Docker/OrbStack
Due to Python environment management, all Python scripts should be run through Docker/OrbStack:

```bash
# Start the full system (handles LM Studio server and model loading)
~/gtd-coach/start-coach.sh

# Test timer functionality (native bash, no Docker needed)
~/gtd-coach/scripts/timer.sh 1 "Test complete!"
```

### Docker/OrbStack Commands (REQUIRED for Python scripts)

```bash
# Run weekly review in Docker
./docker-run.sh

# Test Timing app integration (NEW)
./docker-run.sh timing

# Test Langfuse integration
./docker-run.sh test

# Generate weekly summary
./docker-run.sh summary

# Build/rebuild Docker image (required after dependency changes)
./docker-run.sh build

# Open shell in container for debugging
./docker-run.sh shell

# Using docker-compose directly
docker compose up gtd-coach            # Run review
docker compose run gtd-coach python3 test_timing_integration.py  # Test Timing
docker compose run test-langfuse       # Test Langfuse
docker compose run generate-summary    # Generate summary
```

## Architecture

### Core Design Pattern
The system follows a **Phase-Based State Machine** with strict time boxing:
1. **STARTUP** (2 min) - Welcome and readiness check
2. **MIND SWEEP** (10 min) - Capture (5 min) + Processing (5 min)
3. **PROJECT REVIEW** (12 min) - Quick next-action decisions (45 sec per project)
4. **PRIORITIZATION** (5 min) - ABC priority assignment
5. **WRAP-UP** (3 min) - Save data and celebration

### Key Components
- **gtd-review.py**: Main orchestrator class `GTDCoach` manages the entire review process
- **start-coach.sh**: Handles LM Studio server lifecycle and model loading (now includes Langfuse health check)
- **scripts/timer.sh**: Standalone timer with audio alerts at 50%, 20%, and 10% remaining
- **prompts/**: System prompts (full vs simple) for ADHD-optimized coaching
- **graphiti_integration.py**: Async memory management with episode batching
- **adhd_patterns.py**: ADHD pattern detection algorithms
- **generate_summary.py**: Weekly insights generator
- **langfuse_tracker.py**: Langfuse integration for LLM performance monitoring
- **test_langfuse.py**: Validation script for Langfuse connectivity and scoring

### Data Flow
```
User Input → Python Orchestrator → LM Studio API → Llama Model → Structured Response → JSON Logging
                     ↓                    ↓
             Graphiti Memory (Async)  Langfuse Observability
                     ↓                    ↓
          Pattern Detection & Analysis  Performance Metrics
```

All data is persisted in:
- `data/`: Mindsweep captures, priorities, and Graphiti batches (JSON format with timestamps)
- `logs/`: Complete review session transcripts
- `summaries/`: AI-generated weekly insights (Markdown format)
- **Langfuse UI**: LLM performance metrics, traces, and quality scores (when configured)

### API Integration
- LM Studio server: `http://localhost:1234/v1/chat/completions`
- Uses OpenAI-compatible API format
- Model: `meta-llama-3.1-8b-instruct` (Q4_K_M quantization)

## Development Guidelines

### ADHD-Specific Features (Preserve These)
- **Strict Time Boxing**: 30-minute total with phase-specific limits
- **Audio Alerts**: Progress warnings using macOS `afplay`
- **Structured Phases**: Prevents analysis paralysis
- **External Executive Function**: Coach provides constant time awareness
- **Pattern Tracking**: All sessions logged for behavioral insights

### Known Issues & Workarounds
- **Timeout Issue**: Large system prompts can cause timeouts
  - Current workaround: Using `system-prompt-simple.txt`
  - Future fix: Implement streaming or chunked responses
- **Platform Dependency**: Audio alerts use macOS-specific `afplay`
  - Future fix: Cross-platform audio solution
- **Timing API Parameters**: Fixed in latest version (2025-08-09)
  - Previous issue: Invalid `timespan_grouping_mode` parameter
  - Solution: Updated to use correct API parameters per documentation

### Testing Changes
1. Always test with `demo-review.py` first
2. Verify timer functionality with `scripts/timer.sh`
3. Check LLM connectivity with `test-simple-prompt.py`
4. Ensure all phases maintain their time limits

### Data Structures
All data is JSON-formatted:
- Mindsweep captures: List of strings with timestamps
- Priorities: ABC-categorized actions with project associations
- Session logs: Complete interaction history with timing metadata
- Graphiti episodes: Structured events with type, phase, and pattern data
- Behavior patterns: Task switches, coherence scores, focus indicators

## Critical Implementation Notes

1. **Timer Integration**: The timer runs as a subprocess and must be properly terminated
2. **Error Handling**: System gracefully handles LM Studio connection failures
3. **State Management**: Each phase transition is logged and timed
4. **User Input**: Uses direct `input()` calls - requires interactive terminal
5. **Model Context**: Llama 3.1 8B has 32,768 token context limit

## Memory Integration Architecture

### How Graphiti Integration Works
1. **Async Capture**: All interactions are queued using `asyncio.create_task()` to avoid blocking
2. **Batch Processing**: Episodes are flushed to disk after each phase to minimize I/O
3. **Pattern Detection**: Real-time analysis during mind sweep for task switching and coherence
4. **Session Summary**: Complete review data is compiled and saved at session end

### Adding New Pattern Types
To track additional ADHD patterns, extend `adhd_patterns.py`:
```python
def detect_new_pattern(self, data):
    # Add detection logic
    return pattern_data
```

### Memory Data Format
Episodes follow this structure:
```json
{
  "type": "interaction|phase_transition|behavior_pattern",
  "phase": "MIND_SWEEP",
  "data": {
    // Pattern-specific data
  },
  "timestamp": "ISO-8601",
  "session_id": "20250804_141824"
}
```

## Langfuse Integration Details

### What Gets Tracked
- **Response Latency**: Per-phase timing for each LLM interaction
- **Success/Failure Rates**: Retry patterns and error tracking
- **Quality Scores**: Three dimensions:
  - Binary success/failure
  - Phase-specific latency thresholds
  - Response appropriateness (for manual review)

### Implementation Approach
The integration uses Langfuse's drop-in OpenAI replacement:
1. Wraps LM Studio API calls with automatic tracing
2. Falls back gracefully if Langfuse is unavailable
3. Adds minimal overhead with background batching
4. Preserves all existing retry and error handling logic

### Configuration
Configure Langfuse by copying the example file and adding your keys:
```bash
cp langfuse_tracker.py.example langfuse_tracker.py
# Edit langfuse_tracker.py with your instance details:
# - LANGFUSE_HOST = "http://localhost:3000"
# - LANGFUSE_PUBLIC_KEY = "pk-lf-..."  # Your public key
# - LANGFUSE_SECRET_KEY = "sk-lf-..."  # Your secret key
```

## Timing App Integration ✅ VERIFIED WORKING

### Setup
1. Copy `.env.example` to `.env`
2. Get your API key from https://web.timingapp.com (requires Timing Connect subscription)
3. Add the key to `.env` file:
   ```
   TIMING_API_KEY=your-key-here
   TIMING_MIN_MINUTES=30  # Optional: minimum project time threshold (default: 30)
   ```

### How It Works
- **Pre-fetching**: During STARTUP phase (2 min), the system fetches last week's project data
- **Smart Filtering**: Only shows projects with >30 minutes (configurable via TIMING_MIN_MINUTES)
- **Fallback**: Uses mock data if API unavailable, maintaining ADHD time constraints
- **Organization Guidance**: Detects auto-generated app names and suggests improvements
- **Performance**: API response typically <1 second, well within the 3-second timeout

### Verified Working (2025-08-09)
- Successfully fetches real project data (e.g., Web Browsing: 10.9h, Communication: 8.6h)
- Correctly filters projects by time threshold
- Gracefully handles API errors with fallback to mock data
- Integrates seamlessly with all 5 GTD review phases

### Testing Commands
```bash
# Always use Docker/OrbStack for Python scripts
./docker-run.sh timing  # Test Timing integration (verified working)
./docker-run.sh build   # Rebuild after adding .env file
./docker-run.sh         # Run full review with real Timing data
```

### API Parameters (Corrected)
The Timing API requires specific parameter names:
- `start_date_min` and `start_date_max` (not `start_date`/`end_date`)
- `columns[]`: 'project' (array notation required)
- `include_project_data`: 1 (to get full project details)
- Removed `timespan_grouping_mode` (was causing 422 errors)

## Future Enhancement Opportunities

1. **Timing App Integration**: ✅ IMPLEMENTED - Real project data from Timing.app
2. **Graphiti Memory**: ✅ IMPLEMENTED - Tracks patterns across reviews for insights
3. **Langfuse Observability**: ✅ IMPLEMENTED - LLM performance monitoring
4. **Metrics Dashboard**: Visualize review completion and patterns
5. **Cross-Platform Support**: Replace macOS-specific components
6. **Streaming Responses**: Prevent timeout issues with large prompts
7. **Real-time MCP Integration**: Direct Graphiti API calls instead of batch files