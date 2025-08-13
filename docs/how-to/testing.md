# How to Test GTD Coach

## Running Tests

### Quick Test Commands

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=gtd_coach

# Run specific test file
pytest tests/unit/test_coach.py

# Run integration tests only
pytest tests/integration/

# Run with real APIs (requires .env configuration)
pytest tests/integration/ --real-apis
```

### Docker Testing

```bash
# Run tests in Docker
docker compose run test

# Run specific test suite
docker compose run gtd-coach pytest tests/unit/
```

## Testing Philosophy

GTD Coach uses a **mock-first approach**:
- Primary tests use mocks for reliability
- Optional integration tests with real services
- Graceful degradation when services unavailable

## Test Organization

```
tests/
├── unit/           # Fast, isolated component tests
├── integration/    # Service integration tests
└── agent/          # LangGraph workflow tests
```

## Writing Tests

### Unit Test Example

```python
def test_phase_transition():
    coach = GTDCoach()
    coach.start_phase("MIND_SWEEP")
    assert coach.current_phase == "MIND_SWEEP"
```

### Integration Test Example

```python
@pytest.mark.integration
def test_langfuse_tracking():
    # Requires LANGFUSE_PUBLIC_KEY in environment
    tracker = LangfuseTracker()
    tracker.track_event("test")
```

## Continuous Integration

Tests run automatically on:
- Every push to main branch
- All pull requests
- Nightly scheduled runs

See `.github/workflows/ci.yml` for configuration.