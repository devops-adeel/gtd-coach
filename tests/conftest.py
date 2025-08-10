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


# ==================== Neo4j / Graphiti Mocks ====================

@pytest.fixture
def mock_neo4j_driver():
    """Mock Neo4j driver."""
    driver = Mock()
    driver.verify_connectivity = Mock(return_value=True)
    driver.close = Mock()
    
    # Mock session
    session = Mock()
    session.run = Mock(return_value=Mock(data=Mock(return_value=[])))
    session.close = Mock()
    driver.session = Mock(return_value=session)
    
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
        "markers", "requires_neo4j: Tests requiring Neo4j (will be skipped)"
    )
    config.addinivalue_line(
        "markers", "requires_api_keys: Tests requiring real API keys (will be skipped)"
    )


def pytest_collection_modifyitems(config, items):
    """Automatically skip tests that require real services."""
    skip_neo4j = pytest.mark.skip(reason="Neo4j not available in test environment")
    skip_api_keys = pytest.mark.skip(reason="Real API keys not available in test environment")
    
    for item in items:
        # Skip tests requiring Neo4j
        if "requires_neo4j" in item.keywords:
            item.add_marker(skip_neo4j)
        
        # Skip tests requiring real API keys
        if "requires_api_keys" in item.keywords:
            item.add_marker(skip_api_keys)
        
        # Auto-mark async tests
        if asyncio.iscoroutinefunction(item.function):
            item.add_marker(pytest.mark.asyncio)