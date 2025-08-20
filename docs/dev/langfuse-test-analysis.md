# Langfuse Test Analysis Guide

## Overview

This guide explains how to use Langfuse trace analysis for debugging agent behavior in tests.

## Quick Start

### 1. Enable Agent Behavior Analysis

```bash
# Enable real Langfuse (not mocked) for agent tests
export ANALYZE_AGENT_BEHAVIOR=true

# Ensure API keys are available (check ~/.env)
export LANGFUSE_PUBLIC_KEY=pk-lf-...
export LANGFUSE_SECRET_KEY=sk-lf-...
```

### 2. Run Tests with Analysis

```bash
# Run specific test with trace analysis
ANALYZE_AGENT_BEHAVIOR=true pytest tests/test_agent_behavior.py -v

# Run all agent behavior tests
ANALYZE_AGENT_BEHAVIOR=true pytest -m agent_behavior -v
```

### 3. Analyze Test Failures

When a test fails with `ANALYZE_AGENT_BEHAVIOR=true`, you'll automatically see:

- Complete agent conversation flow
- Tool calls and responses  
- Interrupt patterns
- State transitions
- Error messages and stack traces

## Using the Langfuse Analyzer Fixture

### Basic Usage

```python
import pytest

@pytest.mark.agent_behavior
def test_my_agent(langfuse_analyzer):
    """Test with automatic trace analysis on failure."""
    
    if langfuse_analyzer:
        # Running with real Langfuse
        print(f"Session ID: {langfuse_analyzer}")
    
    # Your agent test code here
    result = agent.process("test input")
    
    assert result.success  # If this fails, traces are analyzed
```

### Async Tests

```python
@pytest.mark.agent_behavior
async def test_async_agent(langfuse_analyzer):
    """Async test with trace analysis."""
    
    result = await agent.async_process("test")
    assert result.success
```

## Manual Trace Analysis

### Using the Analysis Script

```bash
# Analyze recent traces (last hour)
python scripts/analyze_langfuse_traces.py

# Analyze specific session
python scripts/analyze_langfuse_traces.py --session SESSION_ID

# Analyze test failure with AI-optimized output
python scripts/analyze_langfuse_traces.py --test-failure SESSION_ID

# Get detailed trace information
python scripts/analyze_langfuse_traces.py --trace TRACE_ID
```

### From Python Code

```python
from scripts.analyze_langfuse_traces import analyze_test_failure

# Analyze a test session
analyze_test_failure("test-session-id")

# Get analysis data programmatically
data = analyze_test_failure("test-session-id", return_data=True)
print(f"Errors found: {len(data['errors'])}")
```

## Test Markers

### `@pytest.mark.agent_behavior`

Mark tests that should analyze agent behavior:

```python
@pytest.mark.agent_behavior
def test_agent_behavior(langfuse_analyzer):
    # This test can use real Langfuse when enabled
    pass
```

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `ANALYZE_AGENT_BEHAVIOR` | Enable real Langfuse for agent tests | `false` |
| `LANGFUSE_PUBLIC_KEY` | Langfuse public key | Required |
| `LANGFUSE_SECRET_KEY` | Langfuse secret key | Required |
| `LANGFUSE_HOST` | Langfuse API host | `https://cloud.langfuse.com` |
| `LANGFUSE_SESSION_ID` | Override session ID (set automatically) | Auto-generated |

## Troubleshooting

### No Traces Found

1. Check API keys are correct:
   ```bash
   cat ~/.env | grep LANGFUSE
   ```

2. Verify Langfuse connection:
   ```bash
   python scripts/testing/test_langfuse_integration.py
   ```

3. Check if test is generating traces:
   - Ensure agent code is actually running
   - Verify callbacks are configured

### Traces Not Detailed Enough

1. Check observation level:
   - Tool calls should be tracked
   - State transitions should be logged

2. Verify session ID is set:
   ```python
   print(f"Session: {langfuse_analyzer}")
   ```

### Analysis Script Errors

1. Install dependencies:
   ```bash
   pip install langfuse python-dotenv
   ```

2. Check API key permissions:
   - Need read access to traces
   - Need read access to observations

## Best Practices

1. **Use for debugging only** - Don't enable in CI/CD by default
2. **Clean up old traces** - Langfuse has retention limits
3. **Use descriptive test names** - Session IDs include test names
4. **Add markers consistently** - Mark all agent behavior tests
5. **Check costs** - Real API calls may incur charges

## Example Output

When a test fails with analysis enabled:

```
================================================================================
TEST FAILED - ANALYZING LANGFUSE TRACES
================================================================================

📊 TRACE SUMMARY:
  Total traces: 3
  Errors found: 1
  Tool calls: 5
  Interrupts: 2
  State transitions: 4

❌ ERRORS DETECTED:
  - gtd_coach_review → check_in_with_user
    {
        "error": "TypeError: 'NoneType' object is not iterable",
        "traceback": "..."
    }

🔔 INTERRUPT PATTERNS:
  - gtd_coach_review → wait_for_user_input
    {
        "__interrupt__": [
            {
                "value": {"query": "Ready to continue?"},
                "resumable": true
            }
        ]
    }

🔧 TOOL CALL SEQUENCE:
  - check_in_with_user
    Input: {"message": "Starting MIND SWEEP phase"}
    Output: {"response": "user_input", "value": "yes"}
  
📝 DETAILED TRACE FLOW:
  [Detailed observation data...]

================================================================================
END OF ANALYSIS
================================================================================
```

## Integration with CI/CD

### GitHub Actions Example

```yaml
- name: Run Agent Tests with Trace Analysis
  if: failure()  # Only on failure
  env:
    ANALYZE_AGENT_BEHAVIOR: true
    LANGFUSE_PUBLIC_KEY: ${{ secrets.LANGFUSE_PUBLIC_KEY }}
    LANGFUSE_SECRET_KEY: ${{ secrets.LANGFUSE_SECRET_KEY }}
  run: |
    pytest tests/ -m agent_behavior --tb=short
```

## Further Reading

- [Langfuse Documentation](https://langfuse.com/docs)
- [GTD Coach Architecture](../explanation/architecture.md)
- [Testing Guide](../how-to/testing.md)