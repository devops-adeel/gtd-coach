# GTD Coach Architecture

## System Overview

GTD Coach implements a phase-based state machine that guides ADHD users through structured weekly reviews. The architecture prioritizes external executive function support through strict time-boxing and audio alerts.

## Core Components

### GTDCoach Class
Central orchestrator managing the review lifecycle:
- Phase transitions with strict timing
- Timer subprocess management
- Data persistence
- Integration coordination

### Phase State Machine
```
STARTUP → MIND_SWEEP → PROJECT_REVIEW → PRIORITIZATION → WRAP_UP
```

Each phase has:
- Fixed duration (non-negotiable)
- Specific prompts and coaching style
- Audio alerts at 50%, 20%, 10% remaining
- Automatic data capture

### LLM Integration
- **Protocol**: OpenAI-compatible API
- **Provider**: LM Studio (local) or any compatible endpoint
- **Model**: Llama 3.1 8B (32K context)
- **Fallback**: Simplified prompts on timeout

## Data Flow

1. **User Input** → Python captures via `input()`
2. **Processing** → LLM provides coaching responses
3. **Storage** → JSON files with timestamps
4. **Integration** → Optional services receive events
5. **Summary** → Weekly insights generated

## Integration Architecture

### Timing App (Synchronous)
- Fetches during STARTUP phase
- Calculates focus metrics
- Stores in Graphiti if available

### Langfuse (Async)
- Wraps all LLM calls
- Tracks latency and retries
- Links prompts to traces

### Graphiti (Async)
- Queues episodes during session
- Batch processes to reduce API calls
- Extracts GTD entities

### Todoist (Synchronous)
- Exports during WRAP-UP
- Creates tasks with labels
- Updates existing projects

## Key Design Decisions

### Why Phase-Based?
ADHD brains struggle with open-ended tasks. Fixed phases provide:
- Clear boundaries
- Reduced decision fatigue
- Predictable structure
- Momentum maintenance

### Why Local LLM?
- **Privacy**: Sensitive data stays local
- **Consistency**: Same model behavior
- **Cost**: No API fees
- **Control**: No rate limits

### Why Audio Alerts?
ADHD time blindness requires external cues:
- Non-visual interruption
- Progressive urgency
- Platform-native (no dependencies)

### Why JSON Storage?
- Human-readable
- Version control friendly
- Easy to process
- No database required

## Extension Points

### Adding New Phases
1. Define in `PhaseConfig`
2. Add transition logic
3. Create phase-specific prompts
4. Update timer calculations

### Adding Integrations
1. Create integration class
2. Add environment variables
3. Hook into phase transitions
4. Handle failures gracefully

### Custom ADHD Patterns
1. Extend `ADHDPatternDetector`
2. Define detection algorithm
3. Add to Graphiti entities
4. Create interventions

## Performance Considerations

- **LLM Timeout**: 30 seconds max per call
- **Batch Size**: 5 episodes for Graphiti
- **Context Limit**: 32K tokens for Llama 3.1
- **Memory Usage**: ~500MB Python + LM Studio

## Security Model

- API keys in environment only
- No hardcoded secrets
- Git history cleaned
- Pre-commit hooks for scanning
- Docker runs as non-root user