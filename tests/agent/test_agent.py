#!/usr/bin/env python3
"""
Tests for main GTDAgent class
"""

import pytest
import pytest_asyncio
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from datetime import datetime
import os

from gtd_coach.agent import (
    GTDAgent,
    create_daily_capture_agent,
    create_weekly_review_agent,
    create_ad_hoc_agent
)
from gtd_coach.agent.state import StateValidator


@pytest.fixture
def mock_llm_client():
    """Create a mock LLM client"""
    client = AsyncMock()
    client.chat = AsyncMock()
    client.chat.completions = AsyncMock()
    client.chat.completions.create = AsyncMock(return_value={
        'choices': [{'message': {'content': 'Test response'}}]
    })
    return client


class TestGTDAgentInitialization:
    """Test GTDAgent initialization"""
    
    def test_agent_init_default(self):
        """Test agent initialization with defaults"""
        agent = GTDAgent(test_mode=True)
        
        assert agent.mode == 'hybrid'
        assert agent.workflow_type == 'daily_capture'
        assert agent.test_mode is True
        assert agent.llm_client is not None
        assert len(agent.tools) > 0
        assert agent.graph is not None
    
    def test_agent_init_workflow_mode(self):
        """Test agent in pure workflow mode"""
        agent = GTDAgent(mode='workflow', test_mode=True)
        
        assert agent.mode == 'workflow'
        assert agent.graph is not None
    
    @patch('gtd_coach.agent.create_react_agent')
    def test_agent_init_agent_mode(self, mock_create_agent):
        """Test agent in pure agent mode"""
        mock_create_agent.return_value = MagicMock()
        
        agent = GTDAgent(mode='agent', test_mode=True)
        
        assert agent.mode == 'agent'
        mock_create_agent.assert_called_once()
    
    def test_agent_init_hybrid_mode(self):
        """Test agent in hybrid mode"""
        agent = GTDAgent(mode='hybrid', test_mode=True)
        
        assert agent.mode == 'hybrid'
        assert agent.graph is not None
    
    @patch.dict(os.environ, {'LANGFUSE_PUBLIC_KEY': 'test_key'})
    @patch('gtd_coach.agent.LangfuseOpenAI')
    def test_agent_with_langfuse(self, mock_langfuse):
        """Test agent initialization with Langfuse"""
        mock_langfuse.return_value = MagicMock()
        
        agent = GTDAgent(use_langfuse=True, test_mode=True)
        
        mock_langfuse.assert_called_once()
    
    def test_agent_with_custom_llm(self, mock_llm_client):
        """Test agent with custom LLM client"""
        agent = GTDAgent(llm_client=mock_llm_client, test_mode=True)
        
        assert agent.llm_client == mock_llm_client
    
    def test_agent_weekly_review_workflow(self):
        """Test agent with weekly review workflow"""
        with pytest.raises(NotImplementedError):
            # Weekly review not implemented yet
            agent = GTDAgent(workflow_type='weekly_review', test_mode=True)
    
    def test_get_available_tools(self):
        """Test getting available tools"""
        agent = GTDAgent(test_mode=True)
        tools = agent.get_available_tools()
        
        assert isinstance(tools, list)
        assert len(tools) > 0
        assert all(isinstance(name, str) for name in tools)
    
    def test_get_mode_info(self):
        """Test getting mode information"""
        agent = GTDAgent(test_mode=True)
        info = agent.get_mode_info()
        
        assert info['mode'] == 'hybrid'
        assert info['workflow_type'] == 'daily_capture'
        assert info['test_mode'] is True
        assert 'tools_available' in info
        assert 'tool_names' in info
        assert 'has_llm' in info
        assert 'has_langfuse' in info


class TestGTDAgentExecution:
    """Test GTDAgent execution"""
    
    @pytest.mark.asyncio
    @patch('gtd_coach.agent.workflows.daily_capture.DailyCaptureWorkflow')
    async def test_run_basic(self, mock_workflow_class):
        """Test basic agent run"""
        # Setup mock workflow
        mock_workflow = AsyncMock()
        mock_graph = AsyncMock()
        mock_graph.ainvoke = AsyncMock(return_value={
            'session_id': 'test_123',
            'captures': ['item1'],
            'processed_items': ['action1'],
            'completed_phases': ['startup', 'capture', 'wrapup']
        })
        mock_workflow.graph = mock_graph
        mock_workflow_class.return_value = mock_workflow
        
        agent = GTDAgent(mode='hybrid', test_mode=True)
        agent.graph = mock_graph
        
        result = await agent.run()
        
        assert result['success'] is True
        assert 'session_id' in result
        assert 'duration' in result
        assert 'summary' in result
        assert 'state' in result
    
    @pytest.mark.asyncio
    async def test_run_with_initial_state(self):
        """Test run with initial state"""
        agent = GTDAgent(test_mode=True)
        
        # Mock the graph
        mock_graph = AsyncMock()
        mock_graph.ainvoke = AsyncMock(return_value={
            'session_id': 'custom_123',
            'user_id': 'user_456',
            'captures': [],
            'processed_items': []
        })
        agent.graph = mock_graph
        
        initial_state = {
            'user_id': 'user_456',
            'session_id': 'custom_123'
        }
        
        result = await agent.run(initial_state=initial_state)
        
        assert result['success'] is True
        assert result['session_id'] == 'custom_123'
    
    @pytest.mark.asyncio
    async def test_run_with_session_config(self):
        """Test run with session configuration"""
        agent = GTDAgent(test_mode=True)
        
        # Mock the graph
        mock_graph = AsyncMock()
        mock_graph.ainvoke = AsyncMock(return_value={
            'session_id': 'test_123',
            'accountability_mode': 'firm',
            'captures': [],
            'processed_items': []
        })
        agent.graph = mock_graph
        
        session_config = {
            'accountability_mode': 'firm',
            'skip_timing': True
        }
        
        result = await agent.run(session_config=session_config)
        
        assert result['success'] is True
        
        # Check that config was passed to graph
        call_args = mock_graph.ainvoke.call_args
        state = call_args[0][0]
        assert state['accountability_mode'] == 'firm'
        assert state['skip_timing'] is True
    
    @pytest.mark.asyncio
    @patch.dict(os.environ, {'LANGFUSE_PUBLIC_KEY': 'test_key'})
    async def test_run_with_langfuse_metadata(self):
        """Test run with Langfuse metadata"""
        agent = GTDAgent(test_mode=True)
        
        # Mock the graph
        mock_graph = AsyncMock()
        mock_graph.ainvoke = AsyncMock(return_value={
            'session_id': 'test_123',
            'captures': [],
            'processed_items': []
        })
        agent.graph = mock_graph
        
        result = await agent.run(user_id='user_123')
        
        # Check Langfuse metadata was added
        call_args = mock_graph.ainvoke.call_args
        config = call_args[0][1]
        
        assert 'metadata' in config
        assert config['metadata']['langfuse_user_id'] == 'user_123'
        assert 'gtd-agent' in config['metadata']['langfuse_tags']
    
    @pytest.mark.asyncio
    async def test_run_error_handling(self):
        """Test error handling during run"""
        agent = GTDAgent(test_mode=True)
        
        # Mock graph to raise error
        mock_graph = AsyncMock()
        mock_graph.ainvoke = AsyncMock(side_effect=Exception("Test error"))
        agent.graph = mock_graph
        
        result = await agent.run()
        
        assert result['success'] is False
        assert 'error' in result
        assert "Test error" in result['error']
    
    @pytest.mark.asyncio
    async def test_generate_summary(self):
        """Test summary generation"""
        agent = GTDAgent(test_mode=True)
        
        state = {
            'captures': ['item1', 'item2'],
            'processed_items': ['action1'],
            'projects': ['project1'],
            'adhd_patterns': ['rapid_switching'],
            'focus_score': 65,
            'completed_phases': ['startup', 'capture'],
            'accountability_mode': 'firm',
            'pattern_analysis': {'severity': 'medium'}
        }
        
        summary = agent._generate_summary(state)
        
        assert summary['captures'] == 2
        assert summary['processed'] == 1
        assert summary['projects'] == 1
        assert 'rapid_switching' in summary['patterns_detected']
        assert summary['focus_score'] == 65
        assert summary['accountability_mode'] == 'firm'
        assert summary['pattern_severity'] == 'medium'


class TestGTDAgentResume:
    """Test agent resume functionality"""
    
    @pytest.mark.asyncio
    async def test_resume_session(self):
        """Test resuming a session"""
        agent = GTDAgent(test_mode=True)
        
        # Mock checkpointer
        mock_checkpointer = MagicMock()
        saved_state = {
            'session_id': 'test_123',
            'current_phase': 'capture',
            'captures': ['item1']
        }
        mock_checkpointer.get = MagicMock(return_value=saved_state)
        agent.checkpointer = mock_checkpointer
        
        # Mock graph
        mock_graph = AsyncMock()
        mock_graph.ainvoke = AsyncMock(return_value={
            'session_id': 'test_123',
            'captures': ['item1', 'item2'],
            'processed_items': ['action1']
        })
        agent.graph = mock_graph
        
        result = await agent.resume('test_123')
        
        assert result['success'] is True
        mock_checkpointer.get.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_resume_no_checkpoint(self):
        """Test resume with no checkpoint found"""
        agent = GTDAgent(test_mode=True)
        
        # Mock checkpointer to return None
        mock_checkpointer = MagicMock()
        mock_checkpointer.get = MagicMock(return_value=None)
        agent.checkpointer = mock_checkpointer
        
        result = await agent.resume('nonexistent_123')
        
        assert result['success'] is False
        assert 'No checkpoint found' in result['error']


class TestAgentFactoryFunctions:
    """Test agent factory functions"""
    
    def test_create_daily_capture_agent(self):
        """Test daily capture agent factory"""
        agent = create_daily_capture_agent(test_mode=True)
        
        assert isinstance(agent, GTDAgent)
        assert agent.workflow_type == 'daily_capture'
        assert agent.mode == 'hybrid'
        
        # With custom mode
        agent = create_daily_capture_agent(mode='workflow', test_mode=True)
        assert agent.mode == 'workflow'
    
    def test_create_weekly_review_agent(self):
        """Test weekly review agent factory"""
        with pytest.raises(NotImplementedError):
            # Weekly review not implemented yet
            agent = create_weekly_review_agent(test_mode=True)
    
    @patch('gtd_coach.agent.create_react_agent')
    def test_create_ad_hoc_agent(self, mock_create_agent):
        """Test ad-hoc agent factory"""
        mock_create_agent.return_value = MagicMock()
        
        agent = create_ad_hoc_agent(test_mode=True)
        
        assert isinstance(agent, GTDAgent)
        assert agent.workflow_type == 'ad_hoc'
        assert agent.mode == 'agent'  # Default to pure agent for flexibility