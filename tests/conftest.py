#!/usr/bin/env python3
"""
Comprehensive test fixtures for GTD Coach test suite.
Provides mocks for all external dependencies to ensure tests run without real connections.
"""

import os
import sys
import pytest
import asyncio
from pathlib import Path
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from datetime import datetime, timezone
import json

# Add project root to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

# Force test environment
os.environ['TEST_MODE'] = 'true'
os.environ['PYTHONPATH'] = str(Path(__file__).parent.parent)


# ==================== Environment Fixtures ====================

@pytest.fixture(autouse=True)
def mock_env(monkeypatch):
    """Automatically set mock environment variables for all tests."""
    # Load .env.test file
    env_test_path = Path(__file__).parent.parent / '.env.test'
    if env_test_path.exists():
        with open(env_test_path) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    monkeypatch.setenv(key, value)
    
    # Ensure we're in test mode
    monkeypatch.setenv('TEST_MODE', 'true')
    monkeypatch.setenv('IN_DOCKER', 'false')
    
    # Set Python path
    monkeypatch.setenv('PYTHONPATH', str(Path(__file__).parent.parent))
    
    yield monkeypatch


@pytest.fixture
def temp_data_dir(tmp_path):
    """Create a temporary data directory for tests."""
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    return data_dir


# ==================== Async Support ====================

@pytest.fixture
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


# ==================== LangGraph v0.6 Support ====================

@pytest.fixture
def langgraph_config():
    """Provide proper LangGraph configuration for tests."""
    import uuid
    return {
        "configurable": {
            "thread_id": str(uuid.uuid4()),
            "checkpoint_ns": "test"
        }
    }


@pytest.fixture
def mock_checkpointer():
    """Provide InMemorySaver for tests requiring checkpointing."""
    with patch('langgraph.checkpoint.memory.InMemorySaver') as MockSaver:
        checkpointer = Mock()
        checkpointer.get = AsyncMock(return_value=None)
        checkpointer.put = AsyncMock()
        checkpointer.list = AsyncMock(return_value=[])
        MockSaver.return_value = checkpointer
        yield checkpointer


@pytest.fixture
def mock_tool_with_injected_state():
    """Create a proper mock tool that handles InjectedState."""
    from unittest.mock import Mock
    
    # Create a mock tool with proper structure
    mock_tool = Mock()
    mock_tool.name = "mock_tool"
    mock_tool.description = "A mock tool for testing"
    
    # Mock the invoke method (tools use invoke, not run)
    mock_tool.invoke = Mock(return_value={"result": "mocked"})
    
    # Mock the schema method to hide InjectedState
    schema = Mock()
    schema.schema = Mock(return_value={
        "properties": {
            "query": {"type": "string", "description": "Query input"}
        },
        "required": ["query"]
    })
    mock_tool.get_input_schema = Mock(return_value=schema)
    
    return mock_tool


@pytest.fixture
def mock_interrupt_result():
    """Mock result with interrupt for testing interrupt patterns."""
    return {
        "messages": [],
        "__interrupt__": [
            {
                "value": {"query": "test interrupt"},
                "resumable": True,
                "ns": ["test_node:123"],
                "when": "during"
            }
        ]
    }


@pytest.fixture  
def mock_command():
    """Mock Command object for resume testing."""
    with patch('langgraph.types.Command') as MockCommand:
        command = Mock()
        command.resume = "test_resume_value"
        command.update = {}
        MockCommand.return_value = command
        MockCommand.resume = lambda value: MockCommand(resume=value)
        yield MockCommand


# ==================== FalkorDB / Graphiti Mocks ====================

@pytest.fixture
def mock_falkordb_driver():
    """Mock FalkorDB driver."""
    driver = Mock()
    driver.close = AsyncMock()
    
    # Mock graph operations
    driver.query = AsyncMock(return_value=[])
    driver.execute = AsyncMock()
    driver.create_index = AsyncMock()
    
    return driver


@pytest.fixture
async def mock_graphiti_client():
    """Mock Graphiti client with async methods."""
    with patch('gtd_coach.integrations.graphiti_client.GraphitiClient') as MockClient:
        client = AsyncMock()
        
        # Mock initialization
        client.initialize = AsyncMock(return_value=client)
        client.health_check = AsyncMock(return_value=True)
        client.close = AsyncMock()
        
        # Mock episode operations
        client.add_episode = AsyncMock(return_value={"uuid": "mock-uuid-123"})
        client.search = AsyncMock(return_value=[])
        client.get_episodes = AsyncMock(return_value=[])
        
        # Mock search with context
        client.search_with_context = AsyncMock(return_value=[])
        
        # Configure the class mock
        MockClient.return_value = client
        MockClient.get_instance = AsyncMock(return_value=client)
        
        yield client


@pytest.fixture
def mock_graphiti_memory(mock_graphiti_client):
    """Mock GraphitiMemory class."""
    with patch('gtd_coach.integrations.graphiti.GraphitiMemory') as MockMemory:
        memory = Mock()
        memory.initialize = AsyncMock()
        memory.queue_episode = AsyncMock()
        memory.add_interaction = AsyncMock()
        memory.add_phase_transition = AsyncMock()
        memory.add_behavior_pattern = AsyncMock()
        memory.add_mindsweep_batch = AsyncMock()
        memory.add_timing_analysis = AsyncMock()
        memory.flush_episodes = AsyncMock(return_value=0)
        memory.create_session_summary = AsyncMock()
        memory.search_with_context = AsyncMock(return_value=[])
        
        MockMemory.return_value = memory
        yield memory


# ==================== Langfuse Mocks ====================

@pytest.fixture
def mock_langfuse():
    """Mock Langfuse client."""
    with patch('langfuse.Langfuse') as MockLangfuse:
        client = Mock()
        
        # Mock prompt operations
        prompt = Mock()
        prompt.compile = Mock(return_value="Compiled prompt text")
        prompt.config = {"model": "mock-model", "temperature": 0.7}
        prompt.version = 1
        
        client.get_prompt = Mock(return_value=prompt)
        client.fetch_prompt = Mock(return_value=prompt)
        
        # Mock trace operations
        trace = Mock()
        trace.id = "mock-trace-id"
        client.trace = Mock(return_value=trace)
        
        # Mock scoring
        client.score = Mock()
        
        MockLangfuse.return_value = client
        yield client


@pytest.fixture
def mock_openai_client():
    """Mock OpenAI client for Langfuse integration."""
    with patch('langfuse.openai.OpenAI') as MockOpenAI:
        client = Mock()
        
        # Mock completion
        completion = Mock()
        completion.choices = [Mock(message=Mock(content="Mock response"))]
        completion.usage = Mock(total_tokens=100)
        
        client.chat = Mock()
        client.chat.completions = Mock()
        client.chat.completions.create = Mock(return_value=completion)
        
        MockOpenAI.return_value = client
        yield client


# ==================== Timing API Mocks ====================

@pytest.fixture
def mock_timing_api():
    """Mock Timing API."""
    with patch('gtd_coach.integrations.timing.TimingAPI') as MockAPI:
        api = Mock()
        
        # Mock project data
        mock_projects = [
            {
                'name': 'Mock Project 1',
                'duration': 3600,
                'color': '#FF0000'
            },
            {
                'name': 'Mock Project 2', 
                'duration': 1800,
                'color': '#00FF00'
            }
        ]
        
        api.fetch_projects_last_week = Mock(return_value=mock_projects)
        api.get_mock_projects = Mock(return_value=mock_projects)
        api.analyze_timing_patterns_async = AsyncMock(return_value={
            'data_type': 'mock',
            'focus_metrics': {
                'focus_score': 75,
                'switches_per_hour': 2.5,
                'focus_periods_count': 3,
                'interpretation': 'Mock focus pattern'
            },
            'switch_analysis': {
                'total_switches': 10,
                'switches_per_hour': 2.5,
                'switch_patterns': []
            }
        })
        
        MockAPI.return_value = api
        yield api


# ==================== LM Studio Mocks ====================

@pytest.fixture
def mock_lm_studio():
    """Mock LM Studio API responses."""
    with patch('requests.post') as mock_post:
        response = Mock()
        response.status_code = 200
        response.json = Mock(return_value={
            'choices': [{
                'message': {
                    'content': 'Mock LLM response'
                }
            }]
        })
        mock_post.return_value = response
        yield mock_post


# ==================== File System Mocks ====================

@pytest.fixture
def mock_data_files(temp_data_dir):
    """Create mock data files for testing."""
    # Create mock mindsweep file
    mindsweep_data = {
        "session_id": "20250810_120000",
        "items": ["Test task 1", "Test task 2"],
        "timestamp": datetime.now().isoformat()
    }
    
    mindsweep_file = temp_data_dir / "mindsweep_20250810_120000.json"
    with open(mindsweep_file, 'w') as f:
        json.dump(mindsweep_data, f)
    
    # Create mock priorities file
    priorities_data = {
        "A": ["High priority task"],
        "B": ["Medium priority task"],
        "C": ["Low priority task"]
    }
    
    priorities_file = temp_data_dir / "priorities_20250810_120000.json"
    with open(priorities_file, 'w') as f:
        json.dump(priorities_data, f)
    
    return {
        'mindsweep': mindsweep_file,
        'priorities': priorities_file,
        'data_dir': temp_data_dir
    }


# ==================== GTD Coach Mocks ====================

@pytest.fixture
def mock_gtd_coach():
    """Mock GTD Coach instance."""
    with patch('gtd_coach.coach.GTDCoach') as MockCoach:
        coach = Mock()
        coach.start_review = AsyncMock()
        coach.run_phase = AsyncMock()
        coach.get_llm_response = AsyncMock(return_value="Mock coach response")
        coach.save_session_data = Mock()
        
        MockCoach.return_value = coach
        yield coach


# ==================== Test Utilities ====================

@pytest.fixture
def assert_async():
    """Helper for asserting async function calls."""
    async def _assert_called(mock_func, *args, **kwargs):
        """Assert an async mock was called with specific arguments."""
        assert mock_func.called
        if args or kwargs:
            mock_func.assert_called_with(*args, **kwargs)
    return _assert_called


@pytest.fixture
def capture_logs():
    """Capture log output for testing."""
    import logging
    from io import StringIO
    
    log_capture = StringIO()
    handler = logging.StreamHandler(log_capture)
    handler.setLevel(logging.DEBUG)
    
    # Add handler to root logger
    root_logger = logging.getLogger()
    root_logger.addHandler(handler)
    
    yield log_capture
    
    # Clean up
    root_logger.removeHandler(handler)


# ==================== Auto-Applied External Service Mocks ====================

@pytest.fixture(autouse=True)
def mock_external_services(request):
    """Automatically mock external services for all tests except integration tests."""
    # Skip mocking for integration tests that need real services
    if hasattr(request, 'node'):
        markers = request.node.iter_markers()
        if any(marker.name in ['requires_falkordb', 'requires_api_keys', 'integration', 'agent_behavior'] for marker in markers):
            return
    
    # Also skip mocking if analyzing agent behavior
    if os.getenv("ANALYZE_AGENT_BEHAVIOR", "false").lower() == "true":
        return
    
    with patch('requests.post') as mock_post, \
         patch('langfuse.Langfuse') as mock_langfuse_cls, \
         patch('gtd_coach.integrations.timing.TimingAPI') as mock_timing_cls:
        
        # Mock LM Studio responses
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json = Mock(return_value={
            'choices': [{
                'message': {
                    'content': 'Mock LLM response for testing'
                }
            }]
        })
        mock_post.return_value = mock_response
        
        # Mock Langfuse client
        mock_langfuse = Mock()
        mock_langfuse.trace = Mock(return_value=Mock(id="test-trace-id"))
        mock_langfuse.score = Mock()
        mock_langfuse.get_prompt = Mock(return_value=Mock(
            compile=Mock(return_value="Test prompt"),
            config={"model": "test-model"}
        ))
        mock_langfuse_cls.return_value = mock_langfuse
        
        # Mock Timing API
        mock_timing = Mock()
        mock_timing.is_configured = Mock(return_value=False)
        mock_timing.fetch_projects_last_week = Mock(return_value=[])
        mock_timing.fetch_time_entries_last_week = Mock(return_value=[])
        mock_timing.detect_context_switches = Mock(return_value={
            'total_switches': 0,
            'switches_per_hour': 0,
            'switch_patterns': [],
            'focus_periods': [],
            'scatter_periods': []
        })
        mock_timing_cls.return_value = mock_timing
        
        yield


# ==================== Langfuse Test Analysis ====================

@pytest.fixture
def langfuse_analyzer(request, monkeypatch):
    """
    Fixture that conditionally enables real Langfuse for agent behavior tests
    and automatically analyzes traces on test failure.
    
    Activated by setting ANALYZE_AGENT_BEHAVIOR=true
    """
    import uuid
    
    # Check if we should analyze agent behavior
    analyze_behavior = os.getenv("ANALYZE_AGENT_BEHAVIOR", "false").lower() == "true"
    
    if not analyze_behavior:
        # Return mock as usual
        yield None
        return
    
    # Load real API keys from ~/.env if available
    home_env = os.path.expanduser("~/.env")
    if os.path.exists(home_env):
        from dotenv import load_dotenv
        load_dotenv(home_env)
    
    # Generate unique session ID for this test
    test_session_id = f"test-{request.node.name}-{uuid.uuid4().hex[:8]}"
    
    # Set session ID in environment for the test
    monkeypatch.setenv("LANGFUSE_SESSION_ID", test_session_id)
    
    # Don't mock Langfuse - use real client
    # The mock_external_services fixture will be skipped for these tests
    
    yield test_session_id
    
    # After test completes, check if it failed
    if hasattr(request.node, "rep_call") and request.node.rep_call.failed:
        # Test failed - analyze traces
        print("\n" + "="*80)
        print("TEST FAILED - ANALYZING LANGFUSE TRACES")
        print("="*80)
        
        # Import and use the analysis function
        sys.path.insert(0, str(Path(__file__).parent.parent))
        from scripts.analyze_langfuse_traces import analyze_test_failure
        
        try:
            analyze_test_failure(test_session_id)
        except Exception as e:
            print(f"Error analyzing traces: {e}")
            import traceback
            traceback.print_exc()


@pytest.hookimpl(tryfirst=True, hookwrapper=True)
def pytest_runtest_makereport(item, call):
    """
    Hook to capture test results for the langfuse_analyzer fixture
    """
    outcome = yield
    rep = outcome.get_result()
    setattr(item, f"rep_{rep.when}", rep)


# ==================== Skip Markers ====================

def pytest_configure(config):
    """Register custom markers."""
    config.addinivalue_line(
        "markers", "unit: Unit tests with no external dependencies"
    )
    config.addinivalue_line(
        "markers", "integration: Integration tests that may require mocking"
    )
    config.addinivalue_line(
        "markers", "requires_falkordb: Tests requiring FalkorDB connection"
    )
    config.addinivalue_line(
        "markers", "requires_api_keys: Tests requiring real API keys (will be skipped)"
    )
    config.addinivalue_line(
        "markers", "agent_behavior: Tests that analyze agent behavior with Langfuse"
    )


def pytest_collection_modifyitems(config, items):
    """Automatically skip tests that require real services."""
    skip_falkordb = pytest.mark.skip(reason="FalkorDB not available in test environment")
    skip_api_keys = pytest.mark.skip(reason="Real API keys not available in test environment")
    
    for item in items:
        # Skip tests requiring FalkorDB
        if "requires_falkordb" in item.keywords:
            item.add_marker(skip_falkordb)
        
        # Skip tests requiring real API keys
        if "requires_api_keys" in item.keywords:
            item.add_marker(skip_api_keys)
        
        # Auto-mark async tests
        if asyncio.iscoroutinefunction(item.function):
            item.add_marker(pytest.mark.asyncio)