#!/usr/bin/env python3
"""
Shared fixtures for agent tests
"""

import pytest
import pytest_asyncio
from unittest.mock import Mock, AsyncMock, MagicMock
import os
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))


@pytest.fixture
def clean_env():
    """Clean environment variables for testing"""
    env_backup = os.environ.copy()
    
    # Remove sensitive keys
    keys_to_remove = [
        'LANGFUSE_PUBLIC_KEY',
        'LANGFUSE_SECRET_KEY',
        'LANGFUSE_HOST',
        'TIMING_API_KEY',
        'NEO4J_PASSWORD',
        'OPENAI_API_KEY'
    ]
    
    for key in keys_to_remove:
        os.environ.pop(key, None)
    
    yield
    
    # Restore environment
    os.environ.clear()
    os.environ.update(env_backup)


@pytest.fixture
def mock_lm_studio():
    """Mock LM Studio API client"""
    client = AsyncMock()
    client.chat = AsyncMock()
    client.chat.completions = AsyncMock()
    client.chat.completions.create = AsyncMock(return_value={
        'id': 'test_completion',
        'object': 'chat.completion',
        'created': 1234567890,
        'model': 'meta-llama-3.1-8b-instruct',
        'choices': [{
            'index': 0,
            'message': {
                'role': 'assistant',
                'content': 'Test response from LLM'
            },
            'finish_reason': 'stop'
        }],
        'usage': {
            'prompt_tokens': 100,
            'completion_tokens': 50,
            'total_tokens': 150
        }
    })
    return client


@pytest.fixture
def mock_timing_api():
    """Mock Timing API responses"""
    return {
        'time_entries': [
            {
                'project': {'name': 'Email', 'color': 'blue'},
                'duration': 1800,
                'start': '2025-01-01T09:00:00Z',
                'end': '2025-01-01T09:30:00Z'
            },
            {
                'project': {'name': 'Coding', 'color': 'green'},
                'duration': 3600,
                'start': '2025-01-01T09:30:00Z',
                'end': '2025-01-01T10:30:00Z'
            }
        ],
        'focus_score': 72.5,
        'context_switches': 5
    }


@pytest.fixture
def mock_graphiti():
    """Mock Graphiti memory client"""
    memory = AsyncMock()
    
    # Mock methods
    memory.add_episode = AsyncMock(return_value='episode_123')
    memory.search_nodes = AsyncMock(return_value=[
        {
            'id': 'node_1',
            'type': 'GTDAction',
            'description': 'Review quarterly report',
            'properties': {'context': '@computer', 'priority': 'high'}
        }
    ])
    memory.search_facts = AsyncMock(return_value=[
        {
            'subject': 'User',
            'predicate': 'frequently_captures',
            'object': 'email tasks',
            'confidence': 0.8
        }
    ])
    memory.get_user_context = AsyncMock(return_value={
        'user_id': 'test_user',
        'adhd_severity': 'medium',
        'preferred_accountability': 'adaptive',
        'average_capture_count': 12,
        'focus_trend': 65
    })
    memory.is_configured = MagicMock(return_value=True)
    
    return memory


@pytest.fixture
def sample_state():
    """Sample state for testing"""
    return {
        'messages': [],
        'session_id': 'test_session_123',
        'workflow_type': 'daily_capture',
        'user_id': 'test_user',
        'user_context': {
            'adhd_severity': 'medium',
            'preferred_accountability': 'adaptive'
        },
        'adhd_patterns': [],
        'accountability_mode': 'adaptive',
        'captures': [],
        'processed_items': [],
        'projects': [],
        'focus_score': None,
        'context_switches': [],
        'current_phase': 'startup',
        'completed_phases': [],
        'phase_durations': {},
        'tool_history': [],
        'interventions': [],
        'behavior_adjustments': [],
        'pattern_analysis': {},
        'stress_indicators': [],
        'recurring_patterns': [],
        'graphiti_episode_ids': [],
        'test_mode': True
    }


@pytest.fixture
def sample_captures():
    """Sample captures for testing"""
    return [
        {
            'id': '1',
            'content': 'Review Q1 financial report',
            'source': 'email',
            'created_at': '2025-01-01T10:00:00Z',
            'capture_method': 'inbox_scan',
            'adhd_flag': False
        },
        {
            'id': '2',
            'content': 'Schedule team meeting for project kickoff',
            'source': 'brain_dump',
            'created_at': '2025-01-01T10:01:00Z',
            'capture_method': 'brain_dump',
            'adhd_flag': False
        },
        {
            'id': '3',
            'content': 'Fix bug in authentication module',
            'source': 'slack',
            'created_at': '2025-01-01T10:02:00Z',
            'capture_method': 'inbox_scan',
            'adhd_flag': True
        }
    ]


@pytest.fixture
def sample_processed_items():
    """Sample processed items for testing"""
    return [
        {
            'id': '1',
            'content': 'Review Q1 financial report',
            'type': 'action',
            'context': '@computer',
            'priority': 'high',
            'time_estimate': 60,
            'energy_required': 'high'
        },
        {
            'id': '2',
            'content': 'Schedule team meeting',
            'type': 'action',
            'context': '@calendar',
            'priority': 'medium',
            'time_estimate': 15,
            'energy_required': 'low'
        },
        {
            'id': '3',
            'content': 'Bug Fix Project',
            'type': 'project',
            'outcome': 'Authentication working reliably',
            'next_action': 'Review error logs',
            'area_of_focus': 'Development'
        }
    ]


@pytest_asyncio.fixture
async def async_mock_session():
    """Async mock for aiohttp session"""
    session = AsyncMock()
    response = AsyncMock()
    response.status = 200
    response.json = AsyncMock(return_value={'data': []})
    response.text = AsyncMock(return_value='OK')
    
    session.get = AsyncMock(return_value=response)
    session.post = AsyncMock(return_value=response)
    session.put = AsyncMock(return_value=response)
    session.delete = AsyncMock(return_value=response)
    
    return session


@pytest.fixture
def mock_checkpointer():
    """Mock checkpointer for testing"""
    from langgraph.checkpoint.memory import MemorySaver
    return MemorySaver()


@pytest.fixture
def mock_sqlite_checkpointer(tmp_path):
    """Mock SQLite checkpointer with temp file"""
    from langgraph.checkpoint.sqlite import SqliteSaver
    db_path = tmp_path / "test.db"
    return SqliteSaver.from_conn_string(f"sqlite:///{db_path}")


@pytest.fixture
def mock_interrupt_responses():
    """Standard mock responses for interrupt testing"""
    return {
        "STARTUP": {"ready": True, "user_id": "test_user"},
        "MIND_SWEEP_CAPTURE": {
            "items": ["Task 1", "Task 2", "Task 3"]
        },
        "MIND_SWEEP_PROCESS": {
            "processed": [
                {"item": "Task 1", "project": "Project A"},
                {"item": "Task 2", "project": "Project B"},
                {"item": "Task 3", "project": "Project A"}
            ]
        },
        "PROJECT_REVIEW": {
            "projects": {
                "Project A": {"next_action": "Start Task 1", "status": "active"},
                "Project B": {"next_action": "Research Task 2", "status": "someday"}
            }
        },
        "PRIORITIZATION": {
            "priorities": {
                "A": ["Start Task 1"],
                "B": ["Research Task 2"],
                "C": []
            }
        },
        "WRAP_UP": {"satisfied": True, "feedback": "Session was helpful"}
    }


@pytest.fixture
def mock_phase_timer():
    """Mock PhaseTimer for testing"""
    timer = MagicMock()
    timer.start_phase = MagicMock()
    timer.stop = MagicMock()
    timer.pause = MagicMock()
    timer.resume = MagicMock()
    timer.get_remaining_time = MagicMock(return_value=300)
    timer.is_running = MagicMock(return_value=True)
    return timer


@pytest.fixture
def workflow_test_config():
    """Standard config for workflow testing"""
    return {
        "configurable": {
            "thread_id": "test_thread_123",
            "checkpoint_ns": "test",
            "user_id": "test_user"
        },
        "metadata": {
            "session_id": "test_session_123",
            "test_mode": True
        }
    }


@pytest.fixture
def mock_langgraph_command():
    """Mock Command object for resume testing"""
    from unittest.mock import MagicMock
    
    command = MagicMock()
    command.resume = {"user_input": "test_input"}
    command.update = {}
    return command


@pytest.fixture  
def mock_node_interrupt():
    """Mock NodeInterrupt exception"""
    from langgraph.errors import NodeInterrupt
    return NodeInterrupt("Test interrupt")