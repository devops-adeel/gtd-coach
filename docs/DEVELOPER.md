# Developer Guide

## Architecture Overview

GTD Coach uses a modular architecture with clear separation of concerns:

```
gtd_coach/
├── agent/          # LangGraph workflows
├── commands/       # CLI entry points
├── integrations/   # External service adapters
├── patterns/       # ADHD pattern detection
└── persistence/    # Data storage layer
```

See [Architecture Explanation](explanation/architecture.md) for detailed design.

## Development Setup

### Prerequisites
- Python 3.11+
- Docker Desktop
- LM Studio
- Git with pre-commit hooks

### Local Development
```bash
# Clone and setup
git clone https://github.com/yourusername/gtd-coach.git
cd gtd-coach
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt -r requirements-dev.txt

# Install pre-commit hooks
pre-commit install

# Run tests
pytest

# Start development
python -m gtd_coach --debug
```

## Code Standards

### Python Style
- Black for formatting
- Ruff for linting
- Type hints required
- Docstrings for public APIs

### Testing Requirements
- Minimum 80% coverage
- Unit tests for all components
- Integration tests for external services
- Mock-first approach

### Git Workflow
1. Create feature branch from `main`
2. Write tests first (TDD)
3. Implement feature
4. Run full test suite
5. Submit PR with description

## Adding Features

### New Integration
1. Create adapter in `integrations/`
2. Add environment variables
3. Update configuration docs
4. Add integration tests

### New Phase
1. Define in `PhaseConfig`
2. Add prompts
3. Update timer logic
4. Test phase transitions

### New Pattern Detection
1. Extend `ADHDPatternDetector`
2. Define detection algorithm
3. Add intervention logic
4. Update Graphiti entities

## Testing

### Run Tests
```bash
# All tests
pytest

# Specific module
pytest tests/unit/test_coach.py

# With coverage
pytest --cov=gtd_coach

# Integration tests
pytest tests/integration/ --real-apis
```

### Writing Tests
```python
# Unit test example
def test_phase_transition():
    coach = GTDCoach()
    coach.start_phase("MIND_SWEEP")
    assert coach.current_phase == "MIND_SWEEP"

# Integration test example
@pytest.mark.integration
def test_timing_api():
    client = TimingClient()
    entries = client.get_entries()
    assert len(entries) > 0
```

## Debugging

### Enable Debug Mode
```bash
export DEBUG_MODE=true
python -m gtd_coach
```

### Common Issues

**LM Studio Connection**
- Check server running on port 1234
- Verify model loaded
- Test with `curl http://localhost:1234/v1/models`

**Timer Not Working**
- macOS: Check audio permissions
- Linux: Install `sox` package
- Windows: Currently unsupported

**Integration Failures**
- Verify API keys in `.env`
- Check network connectivity
- Review integration logs

## Performance

### Optimization Points
- LLM calls: 30 second timeout
- Batch Graphiti episodes: 5 per batch
- Cache Langfuse prompts: 5 minutes
- JSON file writes: Async when possible

### Monitoring
- Langfuse dashboard for LLM metrics
- Docker logs for application events
- JSON logs for session analysis

## Release Process

1. Update version in `pyproject.toml`
2. Update CHANGELOG.md
3. Run full test suite
4. Build Docker image
5. Tag release
6. Push to registry

## Contributing

### Before Submitting
- [ ] Tests pass locally
- [ ] Coverage maintained/improved
- [ ] Documentation updated
- [ ] Pre-commit hooks pass
- [ ] CHANGELOG entry added

### PR Guidelines
- Clear description of changes
- Link to related issue
- Screenshots if UI changes
- Performance impact noted

## Resources

- [Project Board](https://github.com/yourusername/gtd-coach/projects)
- [Issue Tracker](https://github.com/yourusername/gtd-coach/issues)
- [Discussions](https://github.com/yourusername/gtd-coach/discussions)
- [Security Policy](../SECURITY.md)