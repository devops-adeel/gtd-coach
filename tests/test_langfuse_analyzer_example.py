#!/usr/bin/env python3
"""
Example test file demonstrating how to use the Langfuse analyzer fixture
for debugging agent behavior in tests.

To run with Langfuse analysis:
    export ANALYZE_AGENT_BEHAVIOR=true
    pytest tests/test_langfuse_analyzer_example.py -v

To run without analysis (normal mocked mode):
    pytest tests/test_langfuse_analyzer_example.py -v
"""

import pytest
from unittest.mock import Mock, AsyncMock


@pytest.mark.agent_behavior
def test_example_with_langfuse_analyzer(langfuse_analyzer):
    """
    Example test that uses the langfuse_analyzer fixture.
    
    When ANALYZE_AGENT_BEHAVIOR=true:
    - Real Langfuse client will be used (not mocked)
    - Test session will get a unique session ID
    - If test fails, traces will be automatically analyzed
    
    Args:
        langfuse_analyzer: Session ID if analyzing, None otherwise
    """
    if langfuse_analyzer:
        print(f"Running test with Langfuse session: {langfuse_analyzer}")
        # This test would run with real Langfuse tracking
        # Your agent behavior test code here
    else:
        print("Running test with mocked Langfuse")
        # This test runs with mocked services
    
    # Example assertion (change to False to see failure analysis)
    assert True, "This test should pass"


@pytest.mark.agent_behavior
def test_failing_example_for_demo(langfuse_analyzer):
    """
    Example of a failing test to demonstrate trace analysis.
    
    Uncomment the assertion to see how Langfuse traces are analyzed
    when a test fails with ANALYZE_AGENT_BEHAVIOR=true.
    """
    if langfuse_analyzer:
        print(f"Test session ID: {langfuse_analyzer}")
    
    # Simulate some agent behavior that would generate traces
    # In a real test, this would be your agent code
    
    # Uncomment to see failure analysis:
    # assert False, "Intentional failure to demonstrate trace analysis"
    
    assert True, "Comment this out and uncomment above to see failure analysis"


@pytest.mark.agent_behavior
async def test_async_agent_behavior(langfuse_analyzer):
    """
    Example async test with Langfuse analysis support.
    
    The fixture works with both sync and async tests.
    """
    if langfuse_analyzer:
        print(f"Async test with session: {langfuse_analyzer}")
    
    # Your async agent test code here
    # await agent.process_message("test")
    
    assert True


def test_normal_unit_test():
    """
    Regular unit test without agent behavior analysis.
    
    This test will always use mocked services regardless of
    ANALYZE_AGENT_BEHAVIOR setting since it doesn't use the fixture.
    """
    # Normal unit test code
    assert 1 + 1 == 2


if __name__ == "__main__":
    print(__doc__)