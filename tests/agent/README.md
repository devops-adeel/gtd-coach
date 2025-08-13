# GTD Agent Test Suite

Comprehensive test suite for the LangGraph-based GTD Agent system.

## Testing Philosophy

This test suite follows a **mock-first approach** with optional real API testing:
- **Primary Testing**: Uses mocks to ensure tests run anywhere (CI/CD, local development)
- **Integration Testing**: Optional tests with real services when available
- **Graceful Degradation**: Tests continue with mocks when services are unavailable

This approach ensures:
- ✅ Stable CI/CD pipelines that don't depend on external services
- ✅ Fast test execution for rapid development cycles
- ✅ Comprehensive coverage of failure scenarios
- ✅ Optional integration testing with real services

## Setup

Install test dependencies:
```bash
pip install -r requirements-test.txt
```

## Running Tests

### Basic Test Execution
```bash
# Run all agent tests
pytest tests/agent/

# Run specific test category
pytest tests/agent/test_integration.py -v

# Tests with coverage
pytest --cov=gtd_coach.agent --cov-report=html

# Parallel execution
pytest -n auto

# Verbose output
pytest -vv
```

### Testing with Real Services (Optional)
```bash
# Test with LM Studio running
# 1. Start LM Studio on localhost:1234
# 2. Load model: meta-llama-3.1-8b-instruct
export USE_REAL_APIS=true
pytest tests/agent/test_integration.py -v

# Test with all services (LM Studio, Neo4j, Timing API)
./run_all_tests_comprehensive.sh
```

### Mock-Only Testing (Default)
```bash
# Tests run with mocks by default - no services required
pytest tests/agent/

# Explicitly use mocks even if services are available
export MOCK_EXTERNAL_APIS=true
pytest tests/agent/
```

### Run specific test files:
```bash
# Test state management
pytest test_state.py

# Test tools
pytest test_tools.py

# Test workflow
pytest test_workflow.py

# Test main agent
pytest test_agent.py

# Integration tests
pytest test_integration.py
```

## Test Structure

### `test_state.py`
Tests for AgentState schema and validation:
- State initialization and defaults
- State validation rules
- Phase transitions
- Capture validation
- State manipulation

### `test_tools.py`
Tests for individual tools with mocked state:
- Adaptive behavior tools (pattern detection, interventions)
- Capture tools (inbox scanning, brain dump)
- GTD processing tools (clarify, organize, prioritize)
- Memory tools (save, load, search) - mocked

### `test_workflow.py`
Tests for workflow graph execution:
- Workflow initialization
- Individual node execution
- Conditional routing decisions
- Error handling
- Full workflow execution

### `test_agent.py`
Tests for main GTDAgent class:
- Agent initialization in all modes (workflow, agent, hybrid)
- Run execution with various configurations
- Resume functionality
- Summary generation
- Factory functions

### `test_integration.py`
End-to-end integration tests:
- Full daily capture flow with mocked APIs
- ADHD intervention scenarios
- Memory fallback to JSON
- Resume interrupted sessions
- Langfuse integration
- Tool versioning and A/B testing

## Test Markers

- `@pytest.mark.unit` - Unit tests without external dependencies
- `@pytest.mark.integration` - Integration tests with mocked services
- `@pytest.mark.slow` - Tests that take longer to run
- `@pytest.mark.requires_env` - Tests requiring environment variables
- `@pytest.mark.langfuse` - Langfuse-specific tests
- `@pytest.mark.timing` - Timing app integration tests
- `@pytest.mark.graphiti` - Graphiti memory tests

## Performance Baselines

Expected performance metrics for the LangGraph agent:

| Metric | Expected Value | Acceptable Range | Notes |
|--------|---------------|------------------|--------|
| Context Trimming | <100ms | 50-150ms | Using trim_messages with 4K limit |
| Phase Transition | <500ms | 200-800ms | Including state persistence |
| Tool Execution | <1s | 500ms-2s | Varies by tool complexity |
| Checkpoint Save | <200ms | 100-300ms | SQLite persistence |
| Total Review Time | 30min | 28-32min | All 5 phases |
| Token Usage/Phase | 2-4K | 1-6K | Conservative 4K trimming |
| Context Overflows | 0-2/session | 0-5/session | Phase summarization helps |
| LM Studio Response | <3s | 1-5s | Local inference with 32K model |

## Mocking Strategy

### External Services
All external services are mocked to ensure tests run without dependencies:
- **LM Studio API**: Mocked with `mock_lm_studio` fixture (realistic OpenAI-compatible responses)
- **Timing API**: Mocked with `mock_timing_api` fixture (includes focus scores)
- **Graphiti Memory**: Mocked with `mock_graphiti` fixture (episode management)
- **Langfuse**: Mocked with patches (observability tracking)

### State Management
- Use `sample_state` fixture for consistent test state
- Use `StateValidator.ensure_required_fields()` for valid states
- Mock state mutations in tools using `InjectedState`

### Async Testing
- All async functions tested with `@pytest.mark.asyncio`
- Use `AsyncMock` for async dependencies
- Proper async context manager mocking

## Coverage Goals

Target coverage: **>80%** for all modules

Current focus areas:
1. State validation and transitions
2. Tool execution with various inputs
3. Workflow routing decisions
4. Error handling paths
5. Integration scenarios

## Debugging Tests

### Run single test with debugging:
```bash
pytest test_agent.py::TestGTDAgentExecution::test_run_basic -vv --tb=long
```

### Run with timeout protection:
```bash
pytest --timeout=10
```

### Generate coverage report:
```bash
pytest --cov=gtd_coach.agent --cov-report=html
open htmlcov/index.html
```

## CI/CD Integration

These tests are designed to run in CI/CD pipelines:
- Fast execution (<30 seconds for unit tests)
- No external dependencies required
- Deterministic results
- Clear failure messages

## Connection & Resilience Testing

The test suite includes comprehensive failure scenario testing:

### LM Studio Connection Tests
- Connection failures with retry logic
- Timeout handling (30s timeout)
- Fallback to cached responses
- Circuit breaker activation

### Test Files for Failure Scenarios
- `test_failure_scenarios.py` - All failure modes
- `test_async_patterns.py` - Async error handling
- `test_checkpointing.py` - Recovery from interruption

Example failure test:
```python
async def test_lm_studio_connection_failure(self):
    """Test handling LM Studio connection failures"""
    # Simulates connection refused
    # Verifies retry attempts (3x with exponential backoff)
    # Checks fallback activation
    # Ensures graceful degradation
```

## Adding New Tests

When adding new tests:
1. **Start with mocks**: Write tests using fixtures first
2. **Add integration tests**: Create optional real API tests
3. **Test failure scenarios**: Connection errors, timeouts
4. **Document dependencies**: Note any special requirements
5. **Update baselines**: If changing performance characteristics
6. **Run full suite**: Ensure no regressions

Example test structure:
```python
def test_new_feature_with_mock(mock_lm_studio):
    """Test with mock - always runs"""
    # Your test here
    
@pytest.mark.skipif(
    not os.getenv("USE_REAL_APIS"),
    reason="Requires real LM Studio"
)
def test_new_feature_with_real_api():
    """Integration test - optional"""
    # Your test here
```