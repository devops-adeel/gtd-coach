# API Reference

## Data Formats

### Mindsweep Capture
`data/mindsweep_YYYYMMDD_HHMMSS.json`

```json
{
  "session_id": "20240810_143022",
  "timestamp": "2024-08-10T14:30:22Z",
  "items": [
    {
      "text": "Review Q3 budget proposal",
      "timestamp": "2024-08-10T14:31:45Z",
      "phase": "MIND_SWEEP"
    }
  ],
  "total_items": 15,
  "duration_seconds": 600
}
```

### Priorities
`data/priorities_YYYYMMDD_HHMMSS.json`

```json
{
  "session_id": "20240810_143022",
  "timestamp": "2024-08-10T14:45:22Z",
  "priorities": {
    "A": ["Complete budget review", "Call team lead"],
    "B": ["Update documentation", "Review PRs"],
    "C": ["Organize desk", "Archive old emails"]
  }
}
```

### Session Log
`logs/review_YYYYMMDD_HHMMSS.json`

```json
{
  "session_id": "20240810_143022",
  "start_time": "2024-08-10T14:30:22Z",
  "end_time": "2024-08-10T15:00:22Z",
  "phases": [
    {
      "name": "STARTUP",
      "duration": 120,
      "completed": true
    }
  ],
  "interactions": [
    {
      "phase": "MIND_SWEEP",
      "user_input": "Review Q3 budget",
      "coach_response": "Great! What else?",
      "timestamp": "2024-08-10T14:31:45Z"
    }
  ]
}
```

## LM Studio API

### Endpoint
```
POST http://localhost:1234/v1/chat/completions
```

### Request Format
```json
{
  "model": "meta-llama-3.1-8b-instruct",
  "messages": [
    {"role": "system", "content": "You are a GTD coach..."},
    {"role": "user", "content": "User input here"}
  ],
  "temperature": 0.7,
  "max_tokens": 500,
  "stream": false
}
```

### Response Format
```json
{
  "choices": [
    {
      "message": {
        "role": "assistant",
        "content": "Coach response here"
      }
    }
  ],
  "usage": {
    "prompt_tokens": 150,
    "completion_tokens": 100
  }
}
```

## Integration APIs

### Timing App
Fetches time entries for focus analysis.

```python
from gtd_coach.integrations.timing import TimingClient

client = TimingClient(api_key="...")
entries = client.get_time_entries(
    start_date="2024-08-03",
    end_date="2024-08-10"
)
```

### Langfuse
Tracks LLM performance metrics.

```python
from langfuse.openai import OpenAI

client = OpenAI(
    base_url="http://localhost:1234/v1",
    api_key="lm-studio"
)
```

### Graphiti
Stores episodes in knowledge graph.

```python
from gtd_coach.integrations.graphiti import GraphitiMemory

memory = GraphitiMemory()
await memory.add_episode(
    name="Weekly Review",
    content="Captured 15 items",
    episode_type="mindsweep"
)
```

## Custom Extensions

### Pattern Detector
```python
from gtd_coach.patterns import ADHDPatternDetector

detector = ADHDPatternDetector()
patterns = detector.analyze_session(session_data)
```

### Intervention System
```python
from gtd_coach.interventions import InterventionManager

manager = InterventionManager()
if manager.should_intervene(pattern_type="rapid_switching"):
    response = manager.get_intervention()
```

## Webhook Events

GTD Coach can send webhooks for key events:

```json
{
  "event": "phase_complete",
  "session_id": "20240810_143022",
  "phase": "MIND_SWEEP",
  "data": {
    "items_captured": 15,
    "duration": 600
  },
  "timestamp": "2024-08-10T14:40:22Z"
}
```

Events:
- `session_start`
- `phase_complete`
- `session_complete`
- `pattern_detected`
- `intervention_triggered`