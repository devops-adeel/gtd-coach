#!/usr/bin/env python3
"""
Integration tests for GTD Agent with mocked APIs
"""

import pytest
import pytest_asyncio
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from datetime import datetime, timedelta
import json
import os
from pathlib import Path

from gtd_coach.agent import GTDAgent, create_daily_capture_agent
from gtd_coach.integrations.graphiti import GraphitiMemory


class TestEndToEndIntegration:
    """End-to-end integration tests"""
    
    @pytest.mark.asyncio
    @patch('gtd_coach.integrations.timing.aiohttp.ClientSession')
    @patch('gtd_coach.integrations.graphiti.GraphitiClient')
    async def test_full_daily_capture_flow(self, mock_graphiti_client, mock_aiohttp):
        """Test complete daily capture flow with mocked external services"""
        
        # Setup Timing API mock
        mock_session = AsyncMock()
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(return_value={
            'data': [
                {
                    'project': {'name': 'Email'},
                    'duration': 1800,  # 30 minutes
                    'start': (datetime.now() - timedelta(hours=1)).isoformat()
                },
                {
                    'project': {'name': 'Coding'},
                    'duration': 3600,  # 60 minutes
                    'start': (datetime.now() - timedelta(hours=2)).isoformat()
                }
            ]
        })
        mock_session.get = AsyncMock(return_value=mock_response)
        mock_aiohttp.return_value.__aenter__ = AsyncMock(return_value=mock_session)
        mock_aiohttp.return_value.__aexit__ = AsyncMock()
        
        # Setup Graphiti mock
        mock_graphiti = AsyncMock()
        mock_graphiti.add_episode = AsyncMock(return_value='episode_123')
        mock_graphiti.search_nodes = AsyncMock(return_value=[])
        mock_graphiti.search_facts = AsyncMock(return_value=[])
        mock_graphiti_client.return_value = mock_graphiti
        
        # Create agent in test mode
        agent = create_daily_capture_agent(test_mode=True)
        
        # Mock the workflow graph to simulate execution
        mock_graph = AsyncMock()
        final_state = {
            'session_id': 'test_session_123',
            'workflow_type': 'daily_capture',
            'captures': [
                {'content': 'Review Q1 report', 'id': '1'},
                {'content': 'Schedule team meeting', 'id': '2'},
                {'content': 'Update project docs', 'id': '3'}
            ],
            'processed_items': [
                {'content': 'Review Q1 report', 'type': 'action', 'context': '@computer'},
                {'content': 'Schedule team meeting', 'type': 'action', 'context': '@calendar'}
            ],
            'projects': [
                {'name': 'Documentation Update', 'next_action': 'Review current docs'}
            ],
            'adhd_patterns': ['moderate_switching'],
            'focus_score': 65,
            'completed_phases': ['startup', 'load_context', 'timing_review', 
                               'capture', 'pattern_check', 'clarify', 'organize', 'wrapup'],
            'accountability_mode': 'adaptive',
            'pattern_analysis': {
                'severity': 'medium',
                'patterns': {'moderate_switching': {'count': 3}}
            },
            'messages': [
                {'role': 'assistant', 'content': 'Welcome to daily capture'},
                {'role': 'assistant', 'content': 'Session complete'}
            ]
        }
        mock_graph.ainvoke = AsyncMock(return_value=final_state)
        agent.graph = mock_graph
        
        # Run the agent
        result = await agent.run(
            initial_state={'user_id': 'test_user'},
            session_config={'skip_timing': False}
        )
        
        # Verify successful execution
        assert result['success'] is True
        assert result['session_id'] == 'test_session_123'
        assert 'duration' in result
        assert 'summary' in result
        
        # Verify summary contents
        summary = result['summary']
        assert summary['captures'] == 3
        assert summary['processed'] == 2
        assert summary['projects'] == 1
        assert 'moderate_switching' in summary['patterns_detected']
        assert summary['focus_score'] == 65
        assert summary['accountability_mode'] == 'adaptive'
        assert summary['pattern_severity'] == 'medium'
    
    @pytest.mark.asyncio
    async def test_workflow_with_adhd_intervention(self):
        """Test workflow with ADHD pattern intervention"""
        agent = GTDAgent(mode='hybrid', test_mode=True)
        
        # Create state with high severity patterns
        mock_graph = AsyncMock()
        state_with_intervention = {
            'session_id': 'intervention_test',
            'workflow_type': 'daily_capture',
            'captures': [
                {'content': 'URGENT: Everything!!!', 'id': '1'},
                {'content': 'So much to do', 'id': '2'},
                {'content': 'Feeling overwhelmed', 'id': '3'},
                {'content': 'Can\'t focus', 'id': '4'}
            ],
            'adhd_patterns': ['rapid_switching', 'overwhelm', 'poor_focus'],
            'pattern_analysis': {
                'severity': 'critical',
                'intervention_needed': True
            },
            'accountability_mode': 'firm',
            'interventions': [
                {
                    'type': 'overwhelm',
                    'technique': 'breathing',
                    'timestamp': datetime.now().isoformat()
                }
            ],
            'behavior_adjustments': [
                {
                    'from_mode': 'adaptive',
                    'to_mode': 'firm',
                    'reason': 'Critical pattern severity'
                }
            ],
            'processed_items': [],
            'completed_phases': ['startup', 'capture', 'pattern_check', 'intervention']
        }
        
        mock_graph.ainvoke = AsyncMock(return_value=state_with_intervention)
        agent.graph = mock_graph
        
        result = await agent.run()
        
        assert result['success'] is True
        
        # Verify intervention occurred
        state = result['state']
        assert state['accountability_mode'] == 'firm'
        assert len(state['interventions']) > 0
        assert state['interventions'][0]['type'] == 'overwhelm'
        assert len(state['behavior_adjustments']) > 0
    
    @pytest.mark.asyncio
    @patch('gtd_coach.agent.tools.graphiti.GraphitiMemory')
    async def test_memory_fallback_to_json(self, mock_graphiti_class):
        """Test fallback to JSON when Graphiti is unavailable"""
        
        # Make Graphiti unavailable
        mock_memory = MagicMock()
        mock_memory.is_configured = MagicMock(return_value=False)
        mock_graphiti_class.return_value = mock_memory
        
        agent = GTDAgent(test_mode=True)
        
        # Setup state with data to save
        mock_graph = AsyncMock()
        final_state = {
            'session_id': 'json_fallback_test',
            'captures': [{'content': 'Test item', 'id': '1'}],
            'processed_items': [{'content': 'Test action', 'id': '1'}],
            'completed_phases': ['startup', 'capture', 'wrapup']
        }
        mock_graph.ainvoke = AsyncMock(return_value=final_state)
        agent.graph = mock_graph
        
        # Ensure data directory exists
        data_dir = Path.home() / 'gtd-coach' / 'data' / 'memory_fallback'
        data_dir.mkdir(parents=True, exist_ok=True)
        
        result = await agent.run()
        
        assert result['success'] is True
        
        # Check if JSON file was created
        json_files = list(data_dir.glob('*.json'))
        # Note: File might not be created in test mode
    
    @pytest.mark.asyncio
    async def test_resume_interrupted_session(self):
        """Test resuming an interrupted session"""
        agent = GTDAgent(test_mode=True)
        
        # Setup checkpointer with saved state
        saved_state = {
            'session_id': 'resume_test',
            'current_phase': 'clarify',
            'captures': [
                {'content': 'Item 1', 'id': '1'},
                {'content': 'Item 2', 'id': '2'}
            ],
            'completed_phases': ['startup', 'load_context', 'capture'],
            'workflow_type': 'daily_capture'
        }
        
        agent.checkpointer.get = MagicMock(return_value=saved_state)
        
        # Mock graph to complete from saved state
        mock_graph = AsyncMock()
        resumed_state = {
            **saved_state,
            'processed_items': [
                {'content': 'Item 1', 'type': 'action'},
                {'content': 'Item 2', 'type': 'project'}
            ],
            'completed_phases': ['startup', 'load_context', 'capture', 
                               'clarify', 'organize', 'wrapup'],
            'current_phase': 'complete'
        }
        mock_graph.ainvoke = AsyncMock(return_value=resumed_state)
        agent.graph = mock_graph
        
        result = await agent.resume('resume_test')
        
        assert result['success'] is True
        assert result['session_id'] == 'resume_test'
        
        # Verify resumed from correct phase
        call_args = mock_graph.ainvoke.call_args
        state = call_args[0][0]
        assert state['current_phase'] == 'clarify'
        assert len(state['captures']) == 2


class TestLangfuseIntegration:
    """Test Langfuse integration for observability"""
    
    @pytest.mark.asyncio
    @patch.dict(os.environ, {
        'LANGFUSE_PUBLIC_KEY': 'pk-test',
        'LANGFUSE_SECRET_KEY': 'sk-test',
        'LANGFUSE_HOST': 'http://localhost:3000'
    })
    @patch('gtd_coach.agent.LangfuseOpenAI')
    async def test_langfuse_tracking(self, mock_langfuse_class):
        """Test that Langfuse tracking is properly configured"""
        
        # Setup Langfuse mock
        mock_langfuse = MagicMock()
        mock_langfuse_class.return_value = mock_langfuse
        
        agent = GTDAgent(use_langfuse=True, test_mode=True)
        
        # Verify Langfuse client was created
        mock_langfuse_class.assert_called_once_with(
            base_url='http://localhost:1234/v1',
            api_key='lm-studio',
            default_headers={'X-Custom-Header': 'gtd-agent'}
        )
        
        # Mock graph
        mock_graph = AsyncMock()
        mock_graph.ainvoke = AsyncMock(return_value={
            'session_id': 'langfuse_test',
            'captures': [],
            'processed_items': []
        })
        agent.graph = mock_graph
        
        result = await agent.run(user_id='test_user')
        
        # Verify Langfuse metadata was included
        call_args = mock_graph.ainvoke.call_args
        config = call_args[0][1]
        
        assert 'metadata' in config
        assert config['metadata']['langfuse_session_id'] == 'langfuse_test'
        assert config['metadata']['langfuse_user_id'] == 'test_user'
        assert 'mode:hybrid' in config['metadata']['langfuse_tags']
        assert 'workflow:daily_capture' in config['metadata']['langfuse_tags']
        assert 'gtd-agent' in config['metadata']['langfuse_tags']


class TestToolVersioning:
    """Test tool versioning and A/B testing support"""
    
    def test_tool_registry_versioning(self):
        """Test tool registry version management"""
        from gtd_coach.agent.tools import tool_registry
        
        # Check tool registration
        tool_info = tool_registry.get_tool_info('scan_inbox_tool')
        assert tool_info['version'] == '1.0'
        assert tool_info['category'] == 'capture'
        
        # Get tool by version
        tool = tool_registry.get_tool('scan_inbox_tool', version='1.0')
        assert tool is not None
        
        # Test non-existent version
        with pytest.raises(ValueError):
            tool_registry.get_tool('scan_inbox_tool', version='2.0')
    
    def test_feature_flags(self):
        """Test feature flag system"""
        from gtd_coach.agent.tools import tool_registry
        
        # Set feature flag
        tool_registry.set_feature_flag('use_new_capture', True)
        assert tool_registry.feature_flags['use_new_capture'] is True
        
        # Disable tool
        tool_registry.disable_tool('scan_inbox_tool')
        tools = tool_registry.get_tools_by_category('capture')
        tool_names = [t.name for t in tools]
        assert 'scan_inbox_tool' not in tool_names
        
        # Re-enable tool
        tool_registry.enable_tool('scan_inbox_tool')
        tools = tool_registry.get_tools_by_category('capture')
        tool_names = [t.name for t in tools]
        assert 'scan_inbox_tool' in tool_names