# Testing Guide for GTD Coach Contributors

## Overview

This guide explains how to write and run tests for the GTD Coach LangGraph agent system. Our testing philosophy prioritizes stability, portability, and comprehensive coverage through a mock-first approach.

## Core Testing Principles

### 1. Mock-First Development
**Always write tests with mocks first.** This ensures:
- Tests run anywhere (CI/CD, local machines)
- No dependency on external services
- Fast execution times
- Predictable results

### 2. Optional Integration Testing
Real API tests are **optional enhancements**, not requirements:
- Use environment variables to enable
- Gracefully skip when services unavailable
- Document service requirements clearly

### 3. Failure Scenario Coverage
Every component should test:
- Happy path (expected behavior)
- Connection failures
- Timeouts
- Invalid inputs
- Edge cases

## Writing Tests

### Test Structure Template

```python
"""Test module for [component name]"""

import pytest
from unittest.mock import Mock, AsyncMock
import os

class TestComponentName:
    """Test suite for ComponentName"""
    
    def test_basic_functionality_with_mock(self, mock_lm_studio):
        """Test basic functionality using mocks - always runs"""
        # Arrange
        component = ComponentName()
        mock_lm_studio.chat.completions.create.return_value = {
            'choices': [{'message': {'content': 'Test response'}}]
        }
        
        # Act
        result = component.process("input")
        
        # Assert
        assert result == "expected output"
        mock_lm_studio.chat.completions.create.assert_called_once()
    
    @pytest.mark.skipif(
        not os.getenv("USE_REAL_APIS"),
        reason="Requires real LM Studio"
    )
    def test_integration_with_real_api(self):
        """Integration test with real service - optional"""
        # This only runs when USE_REAL_APIS=true
        component = ComponentName()
        result = component.process("input")
        assert result is not None
    
    def test_connection_failure_handling(self, mock_lm_studio):
        """Test graceful handling of connection failures"""
        # Arrange
        mock_lm_studio.chat.completions.create.side_effect = ConnectionError()
        component = ComponentName()
        
        # Act & Assert
        with pytest.raises(ConnectionError):
            component.process("input")
        # Or verify fallback behavior
```

### Using Test Fixtures

Our test suite provides comprehensive fixtures in `conftest.py`:

```python
def test_with_fixtures(mock_lm_studio, mock_timing_api, mock_graphiti):
    """Example using multiple fixtures"""
    
    # mock_lm_studio provides OpenAI-compatible responses
    mock_lm_studio.chat.completions.create.return_value = {
        'id': 'test_completion',
        'model': 'meta-llama-3.1-8b-instruct',
        'choices': [{
            'message': {'content': 'Response'},
            'finish_reason': 'stop'
        }],
        'usage': {'total_tokens': 150}
    }
    
    # mock_timing_api provides time tracking data
    mock_timing_api.return_value = {
        'time_entries': [...],
        'focus_score': 72.5
    }
    
    # mock_graphiti provides memory operations
    mock_graphiti.add_episode.return_value = 'episode_123'
```

### Testing Async Code

For async components, use pytest-asyncio:

```python
@pytest.mark.asyncio
async def test_async_operation(mock_graphiti):
    """Test async operations"""
    # Arrange
    mock_graphiti.search_nodes = AsyncMock(return_value=[...])
    
    # Act
    result = await async_component.process()
    
    # Assert
    assert result is not None
    mock_graphiti.search_nodes.assert_awaited_once()
```

## Running Tests

### Local Development

```bash
# Install dependencies
pip install -r requirements.txt

# Run all tests with mocks (default)
pytest tests/

# Run specific test file
pytest tests/agent/test_agent.py -v

# Run with coverage report
pytest tests/agent/ --cov=gtd_coach.agent --cov-report=html

# View coverage report
open htmlcov/index.html
```

### Testing with Real Services

```bash
# 1. Start required services
# - LM Studio on localhost:1234 with meta-llama-3.1-8b-instruct
# - Neo4j database (if testing Graphiti)
# - Ensure Timing API key in .env

# 2. Enable real API testing
export USE_REAL_APIS=true

# 3. Run tests
pytest tests/agent/test_integration.py -v

# Or use the comprehensive script
./run_all_tests_comprehensive.sh
```

### CI/CD Pipeline

Tests run automatically in CI with mocks:

```yaml
# .github/workflows/test.yml
name: Test Suite

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      
      - name: Set up Python
        uses: actions/setup-python@v2
        with:
          python-version: '3.11'
      
      - name: Install dependencies
        run: pip install -r requirements.txt
      
      - name: Run tests
        run: pytest tests/ --cov=gtd_coach --cov-report=xml
        # No external services needed - uses mocks
      
      - name: Upload coverage
        uses: codecov/codecov-action@v2
```

## Test Categories

### Unit Tests
Test individual components in isolation:
- State validation
- Tool execution
- Message trimming
- Token counting

### Integration Tests
Test component interactions:
- Workflow execution
- Tool orchestration
- State persistence
- API communication

### End-to-End Tests
Test complete user journeys:
- Full weekly review
- Daily capture session
- Interrupt and resume
- Migration scenarios

### Performance Tests
Track performance metrics:
- Response latency
- Token usage
- Memory consumption
- Context overflow frequency

## Common Testing Patterns

### 1. Testing LM Studio Integration

```python
def test_lm_studio_with_retry(mock_lm_studio):
    """Test LM Studio with connection retry"""
    # Simulate temporary failure then success
    mock_lm_studio.chat.completions.create.side_effect = [
        ConnectionError("Connection refused"),
        ConnectionError("Connection refused"),
        {'choices': [{'message': {'content': 'Success'}}]}
    ]
    
    agent = GTDAgent()
    # Should retry and eventually succeed
    result = agent.process("input")
    assert result == "Success"
    assert mock_lm_studio.chat.completions.create.call_count == 3
```

### 2. Testing Context Management

```python
def test_context_trimming():
    """Test aggressive context trimming at 4K tokens"""
    agent = GTDAgent()
    
    # Create messages exceeding 4K tokens
    long_messages = [HumanMessage(content="x" * 1000) for _ in range(10)]
    
    # Process through pre-model hook
    trimmed = agent._pre_model_hook({"messages": long_messages})
    
    # Verify trimming occurred
    token_count = count_tokens_approximately(trimmed)
    assert token_count <= 4000
```

### 3. Testing Checkpointing

```python
def test_checkpoint_recovery(tmp_path):
    """Test session recovery from checkpoint"""
    # Create agent with SQLite checkpointer
    checkpoint_dir = tmp_path / "checkpoints"
    agent = GTDAgent(checkpoint_dir=checkpoint_dir)
    
    # Run partial session
    state1 = agent.run(interrupt_after="MIND_SWEEP")
    session_id = state1["session_id"]
    
    # Resume from checkpoint
    state2 = agent.run(resume=True, session_id=session_id)
    
    # Verify continuity
    assert state2["completed_phases"] == ["STARTUP", "MIND_SWEEP", "PROJECT_REVIEW"]
```

## Performance Testing

### Tracking Baselines

```python
@pytest.mark.benchmark
def test_performance_baseline(benchmark):
    """Track performance metrics"""
    agent = GTDAgent(test_mode=True)
    
    # Benchmark context trimming
    result = benchmark(agent._pre_model_hook, large_state)
    
    # Assert performance requirements
    assert benchmark.stats['mean'] < 0.1  # <100ms average
    assert benchmark.stats['max'] < 0.15  # <150ms worst case
```

### Expected Performance Metrics

| Operation | Target | Maximum |
|-----------|--------|---------|
| Context Trim | 100ms | 150ms |
| Tool Execute | 1s | 2s |
| Phase Switch | 500ms | 800ms |
| Checkpoint | 200ms | 300ms |

## Troubleshooting

### Common Issues

1. **Import Errors**
   ```bash
   # Ensure you're in the project root
   cd ~/gtd-coach
   # Install all dependencies
   pip install -r requirements.txt
   ```

2. **Fixture Not Found**
   ```python
   # Check fixture is imported in conftest.py
   # Ensure test file is in correct directory
   ```

3. **Async Test Hanging**
   ```python
   # Add timeout to async tests
   @pytest.mark.asyncio
   @pytest.mark.timeout(10)
   async def test_async():
       ...
   ```

4. **Mock Not Working**
   ```python
   # Ensure proper patching location
   @patch('gtd_coach.agent.core.ChatOpenAI')  # Patch where it's used
   def test_with_patch(mock_client):
       ...
   ```

## Best Practices Checklist

- [ ] Write test with mocks first
- [ ] Add docstring explaining test purpose
- [ ] Test both success and failure paths
- [ ] Use appropriate fixtures
- [ ] Mark tests with correct markers
- [ ] Keep tests focused and independent
- [ ] Avoid testing implementation details
- [ ] Use meaningful assertion messages
- [ ] Clean up resources in teardown
- [ ] Document any special requirements

## Getting Help

- Review existing tests for examples
- Check `conftest.py` for available fixtures
- Run tests with `-vv` for verbose output
- Use `--tb=long` for detailed tracebacks
- Ask in discussions for test strategy questions

## Contributing

When submitting PRs:
1. All tests must pass with mocks
2. Include tests for new features
3. Update baselines if performance changes
4. Document any new fixtures or patterns
5. Ensure CI passes before merge

Remember: **Good tests enable confident refactoring and catch bugs before users do.**