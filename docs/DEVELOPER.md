# GTD Coach Developer Documentation

## Architecture Overview

GTD Coach is a phase-based CLI application designed specifically for ADHD users to complete Getting Things Done (GTD) weekly reviews. It uses a local LLM (via LM Studio) for coaching and integrates with optional services for enhanced functionality.

### Core Design Principles
1. **Time-boxed phases**: Strict 30-minute limit with phase transitions
2. **ADHD-optimized**: External executive function, pattern detection
3. **Local-first**: Core functionality works offline with local LLM
4. **Extensible**: Optional integrations enhance but don't break core

## Project Structure

```
gtd_coach/                    # Main package
├── __init__.py
├── __main__.py              # Entry point
├── coach.py                 # Main GTDCoach class
├── phases.py                # Phase state machine
├── timer.py                 # Timer functionality
├── patterns/                # ADHD pattern detection
│   ├── detector.py          # Pattern detection logic
│   ├── adhd_metrics.py      # ADHD-specific analysis
│   └── memory_enhancer.py   # Memory augmentation
└── integrations/            # Optional external services
    ├── graphiti.py          # Knowledge graph integration
    ├── langfuse.py          # Observability/monitoring
    └── timing.py            # Time tracking integration
```

## Development Setup

### Prerequisites
- Python 3.10+
- LM Studio with Llama 3.1 8B model
- Optional: Docker for testing
- Optional: Neo4j for Graphiti memory

### Installation

```bash
# Clone repository
git clone https://github.com/yourusername/gtd-coach.git
cd gtd-coach

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Copy environment template
cp config/.env.example .env
# Edit .env with your settings
```

### Running in Development

```bash
# Run directly
python -m gtd_coach

# Run with debug logging
LOG_LEVEL=DEBUG python -m gtd_coach

# Run with specific phase
python -m gtd_coach --phase MIND_SWEEP

# Resume interrupted session
python -m gtd_coach --resume
```

## Core Components

### GTDCoach Class (`coach.py`)

The main orchestrator that manages the review session:

```python
class GTDCoach:
    def __init__(self):
        self.phase = Phase.STARTUP
        self.timer = Timer()
        self.memory = GraphitiMemory()  # Optional
        self.patterns = ADHDPatternDetector()
        
    def run_review(self):
        """Main entry point for review session"""
        
    def transition_phase(self):
        """Handle phase transitions with time boxing"""
        
    def call_llm(self, prompt, context):
        """Interface with LM Studio API"""
```

### Phase State Machine

Phases are strictly time-boxed:

```python
class Phase(Enum):
    STARTUP = (2, "startup")        # 2 minutes
    MIND_SWEEP = (10, "mind_sweep")  # 10 minutes
    PROJECT_REVIEW = (12, "review")  # 12 minutes
    PRIORITIZATION = (5, "prioritize") # 5 minutes
    WRAP_UP = (3, "wrap_up")         # 3 minutes
```

### Timer System

Provides audio alerts at percentage thresholds:

```python
class Timer:
    def start(self, duration_minutes):
        """Start timer with background alerts"""
        
    def alert_at_percentage(self, percentage):
        """Trigger audio alert at time threshold"""
```

## Pattern Detection

### ADHD Patterns Tracked

The system monitors several ADHD-specific patterns:

1. **Task Switching**: Frequency of topic changes
2. **Hyperfocus**: Extended time on single items
3. **Incomplete Tasks**: Accumulation over sessions
4. **Context Switches**: Cost of transitions
5. **Overwhelm Indicators**: Too many priorities

### Pattern Detection Algorithm

```python
class ADHDPatternDetector:
    def analyze_mindsweep(self, items):
        """Detect patterns in brain dump"""
        return {
            'switch_rate': self.calculate_switch_rate(items),
            'coherence': self.measure_coherence(items),
            'overwhelm_score': self.detect_overwhelm(items)
        }
```

## Integrations

### Graphiti Memory (Optional)

Knowledge graph for long-term memory:

```python
# Configuration in .env
NEO4J_URI=bolt://localhost:7687
NEO4J_PASSWORD=yourpassword

# Usage in code
from gtd_coach.integrations.graphiti import GraphitiMemory

memory = GraphitiMemory()
await memory.store_session(session_data)
context = await memory.get_context(user_id)
```

### Langfuse Observability (Optional)

LLM performance monitoring:

```python
# Configuration in .env
LANGFUSE_PUBLIC_KEY=pk-lf-...
LANGFUSE_SECRET_KEY=sk-lf-...

# Automatic tracing
from gtd_coach.integrations.langfuse import trace_llm_call

@trace_llm_call
def call_llm(prompt):
    # Automatically traced
    pass
```

### Timing App Integration (Optional)

Real-time tracking data:

```python
# Configuration in .env
TIMING_API_KEY=your-key-here

# Fetch project data
from gtd_coach.integrations.timing import TimingAPI

timing = TimingAPI()
projects = await timing.get_week_projects()
focus_score = timing.calculate_focus_score()
```

## Testing

### Test Structure

```
tests/
├── test_coach.py           # Core functionality tests
├── test_phases.py          # Phase transition tests
├── test_patterns.py        # Pattern detection tests
├── test_integrations.py    # Integration tests
└── fixtures/               # Test data
```

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=gtd_coach --cov-report=html

# Run specific test file
pytest tests/test_coach.py

# Run with verbose output
pytest -xvs
```

### Writing Tests

```python
import pytest
from gtd_coach import GTDCoach

def test_phase_transition():
    coach = GTDCoach()
    assert coach.phase == Phase.STARTUP
    
    coach.transition_phase()
    assert coach.phase == Phase.MIND_SWEEP
    
@pytest.mark.integration
def test_timing_api():
    # Mark integration tests that require external services
    pass
```

## API Reference

### LM Studio API

The coach interfaces with LM Studio's OpenAI-compatible API:

```python
LM_STUDIO_URL = "http://localhost:1234/v1"

def call_llm(prompt: str, temperature: float = 0.7) -> str:
    response = requests.post(
        f"{LM_STUDIO_URL}/chat/completions",
        json={
            "model": "llama-3.1-8b",
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt}
            ],
            "temperature": temperature,
            "max_tokens": 500
        }
    )
    return response.json()["choices"][0]["message"]["content"]
```

### Data Persistence

Session data is stored in JSON format:

```python
# data/mindsweep/20240315_143022.json
{
    "session_id": "20240315_143022",
    "phase_data": {
        "mind_sweep": {
            "items": ["item1", "item2"],
            "duration": 10.0,
            "patterns": {...}
        }
    }
}
```

## Configuration

### Environment Variables

Complete list of configuration options:

```bash
# Core Settings
LOG_LEVEL=INFO                  # DEBUG, INFO, WARNING, ERROR
COACHING_STYLE=firm             # firm or gentle
PHASE_TIME_MULTIPLIER=1.0       # Adjust phase timing

# LM Studio
LM_STUDIO_URL=http://localhost:1234/v1
LM_STUDIO_MODEL=llama-3.1-8b
LM_STUDIO_TIMEOUT=30

# Optional Integrations
TIMING_API_KEY=...
LANGFUSE_PUBLIC_KEY=...
LANGFUSE_SECRET_KEY=...
NEO4J_URI=...
NEO4J_PASSWORD=...

# Feature Flags
ENABLE_PATTERN_DETECTION=true
ENABLE_AUDIO_ALERTS=true
ENABLE_MEMORY=false
```

### Prompts Configuration

System prompts are stored in `config/prompts/`:
- `firm.txt`: Direct, time-focused coaching
- `gentle.txt`: Supportive, flexible coaching
- `fallback.txt`: Simplified for timeout prevention

## Deployment

### Docker Deployment

```dockerfile
FROM python:3.10-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY gtd_coach/ ./gtd_coach/
COPY config/ ./config/

CMD ["python", "-m", "gtd_coach"]
```

### Docker Compose

```yaml
version: '3.8'

services:
  gtd-coach:
    build: .
    environment:
      - LM_STUDIO_URL=http://host.docker.internal:1234/v1
    volumes:
      - ./data:/app/data
      - ./logs:/app/logs
```

## Contributing

### Code Style

We use Python standard conventions:
- PEP 8 for code style
- Type hints for all functions
- Docstrings for classes and public methods

```python
def process_mindsweep(items: list[str]) -> dict[str, Any]:
    """
    Process mind sweep items for patterns.
    
    Args:
        items: List of captured thoughts
        
    Returns:
        Dictionary of detected patterns
    """
    pass
```

### Pull Request Process

1. Fork the repository
2. Create feature branch (`git checkout -b feature/amazing-feature`)
3. Write tests for new functionality
4. Ensure all tests pass (`pytest`)
5. Update documentation
6. Submit PR with clear description

### Development Workflow

```bash
# Create feature branch
git checkout -b feature/new-integration

# Make changes and test
python -m gtd_coach  # Manual testing
pytest              # Automated tests

# Commit with conventional commits
git commit -m "feat: add new integration for X"

# Push and create PR
git push origin feature/new-integration
```

## Troubleshooting

### Common Issues

**LM Studio Connection Failed**
- Verify LM Studio is running: `lms ps`
- Check model is loaded
- Verify URL in configuration

**Import Errors After Reorganization**
- Ensure virtual environment is activated
- Reinstall in development mode: `pip install -e .`
- Clear Python cache: `find . -type d -name __pycache__ -exec rm -r {} +`

**Timer Audio Not Working**
- macOS: Check terminal audio permissions
- Linux: Install `sox` package
- Windows: Audio alerts not supported

**Integration Timeouts**
- Increase timeout values in `.env`
- Check network connectivity
- Verify API keys are valid

## Architecture Decisions

### Why Local LLM?
- Privacy: User data stays local
- Reliability: No internet dependency
- Cost: No API fees
- Control: Consistent behavior

### Why Phase-Based?
- ADHD needs structure
- Prevents hyperfocus traps
- Creates completion momentum
- Measurable progress

### Why Python?
- Rich ecosystem for AI/ML
- Easy integration with services
- Cross-platform compatibility
- Rapid development

## Future Enhancements

Planned improvements:
- [ ] Web UI option
- [ ] Mobile companion app
- [ ] Voice input/output
- [ ] Calendar integration
- [ ] Multi-user support
- [ ] Plugin system
- [ ] Real-time collaboration

## Support

- GitHub Issues: Bug reports and feature requests
- Documentation: This guide and user guide
- Community: Discord/Slack (if available)

## License

[Your chosen license]

---

For user-focused documentation, see [USER_GUIDE.md](USER_GUIDE.md)
For configuration details, see [CONFIGURATION.md](CONFIGURATION.md)