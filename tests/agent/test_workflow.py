#!/usr/bin/env python3
"""
Tests for workflow graph execution
"""

import pytest
import pytest_asyncio
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from datetime import datetime
import os

from gtd_coach.agent.workflows.daily_capture import DailyCaptureWorkflow, create_daily_capture_workflow
from gtd_coach.agent.state import StateValidator


@pytest.fixture
def mock_llm_client():
    """Create a mock LLM client"""
    client = AsyncMock()
    client.ainvoke = AsyncMock(return_value={'content': 'Test response'})
    return client


@pytest.fixture
def workflow_no_agent():
    """Create workflow without agent decisions"""
    return DailyCaptureWorkflow(llm_client=None, use_agent_decisions=False)


@pytest.fixture
def workflow_with_agent(mock_llm_client):
    """Create workflow with agent decisions"""
    return DailyCaptureWorkflow(llm_client=mock_llm_client, use_agent_decisions=True)


class TestDailyCaptureWorkflow:
    """Test daily capture workflow"""
    
    def test_workflow_initialization(self, workflow_no_agent):
        """Test workflow initialization"""
        assert workflow_no_agent.llm_client is None
        assert workflow_no_agent.use_agent_decisions is False
        assert workflow_no_agent.graph is not None
        assert len(workflow_no_agent.tools) > 0
    
    def test_workflow_tools_loaded(self, workflow_no_agent):
        """Test that all required tools are loaded"""
        tool_names = [tool.name for tool in workflow_no_agent.tools]
        
        # Check key tools are present
        assert 'analyze_timing_tool' in tool_names
        assert 'scan_inbox_tool' in tool_names
        assert 'clarify_items_tool' in tool_names
        assert 'save_memory_tool' in tool_names
        assert 'detect_patterns_tool' in tool_names
    
    @pytest.mark.asyncio
    async def test_startup_node(self, workflow_no_agent):
        """Test startup node execution"""
        state = {}
        result = await workflow_no_agent.startup_node(state)
        
        assert 'session_id' in result
        assert 'workflow_type' in result
        assert result['workflow_type'] == 'daily_capture'
        assert 'messages' in result
        assert len(result['messages']) > 0
        assert 'completed_phases' in result
    
    @pytest.mark.asyncio
    @patch.dict(os.environ, {'TIMING_API_KEY': ''})
    async def test_should_review_timing_no_key(self, workflow_no_agent):
        """Test timing review decision without API key"""
        state = StateValidator.ensure_required_fields({})
        
        decision = workflow_no_agent.should_review_timing(state)
        assert decision == 'skip'
    
    @pytest.mark.asyncio
    @patch.dict(os.environ, {'TIMING_API_KEY': 'test_key'})
    async def test_should_review_timing_with_key(self, workflow_no_agent):
        """Test timing review decision with API key"""
        state = StateValidator.ensure_required_fields({})
        
        decision = workflow_no_agent.should_review_timing(state)
        assert decision == 'timing'
    
    def test_should_review_timing_skip_flag(self, workflow_no_agent):
        """Test timing review skip with explicit flag"""
        state = StateValidator.ensure_required_fields({})
        state['skip_timing'] = True
        
        decision = workflow_no_agent.should_review_timing(state)
        assert decision == 'skip'
    
    def test_check_intervention_needed(self, workflow_no_agent):
        """Test intervention decision logic"""
        # No intervention needed
        state = {'pattern_analysis': {'intervention_needed': False}}
        decision = workflow_no_agent.check_intervention_needed(state)
        assert decision == 'continue'
        
        # Intervention needed
        state = {'pattern_analysis': {'intervention_needed': True}}
        decision = workflow_no_agent.check_intervention_needed(state)
        assert decision == 'intervene'
    
    def test_should_save_memory_test_mode(self, workflow_no_agent):
        """Test memory save decision in test mode"""
        state = {'test_mode': True, 'processed_items': ['item1']}
        decision = workflow_no_agent.should_save_memory(state)
        assert decision == 'skip'
    
    def test_should_save_memory_no_items(self, workflow_no_agent):
        """Test memory save decision with no items"""
        state = {'test_mode': False, 'processed_items': []}
        decision = workflow_no_agent.should_save_memory(state)
        assert decision == 'skip'
    
    @patch.dict(os.environ, {'NEO4J_PASSWORD': 'test_pass'})
    def test_should_save_memory_with_items(self, workflow_no_agent):
        """Test memory save decision with items and Graphiti configured"""
        state = {'test_mode': False, 'processed_items': ['item1']}
        decision = workflow_no_agent.should_save_memory(state)
        assert decision == 'save'
    
    @pytest.mark.asyncio
    async def test_pattern_check_node(self, workflow_no_agent):
        """Test pattern check node"""
        state = StateValidator.ensure_required_fields({})
        state['captures'] = [
            {'content': 'Task 1', 'id': '1'},
            {'content': 'Task 2', 'id': '2'}
        ]
        
        # Mock the detect_patterns_tool
        with patch('gtd_coach.agent.workflows.daily_capture.detect_patterns_tool') as mock_tool:
            mock_tool.ainvoke = AsyncMock(return_value={
                'severity': 'low',
                'patterns': {}
            })
            
            result = await workflow_no_agent.pattern_check_node(state)
            
            assert 'pattern_analysis' in result
            assert result['current_phase'] == 'pattern_check'
    
    @pytest.mark.asyncio
    async def test_wrapup_node(self, workflow_no_agent):
        """Test wrapup node"""
        state = StateValidator.ensure_required_fields({})
        state['captures'] = [{'content': 'Task 1', 'id': '1'}]
        state['processed_items'] = [{'content': 'Action 1', 'id': '1'}]
        state['focus_score'] = 75
        
        # Mock assess_user_state_tool
        with patch('gtd_coach.agent.workflows.daily_capture.assess_user_state_tool') as mock_tool:
            mock_tool.ainvoke = AsyncMock(return_value={
                'energy': 'medium',
                'focus': 'focused',
                'recommendations': ['Take a break', 'Stay hydrated']
            })
            
            result = await workflow_no_agent.wrapup_node(state)
            
            assert 'messages' in result
            assert 'completed_phases' in result
            assert 'wrapup' in result['completed_phases']
            assert result['current_phase'] == 'complete'
            
            # Check summary message
            last_message = result['messages'][-1]
            assert 'Daily Capture Complete' in last_message.content


class TestWorkflowIntegration:
    """Test full workflow integration"""
    
    @pytest.mark.asyncio
    @patch('gtd_coach.agent.workflows.daily_capture.load_context_tool')
    @patch('gtd_coach.agent.workflows.daily_capture.scan_inbox_tool')
    @patch('gtd_coach.agent.workflows.daily_capture.brain_dump_tool')
    @patch('gtd_coach.agent.workflows.daily_capture.detect_patterns_tool')
    @patch('gtd_coach.agent.workflows.daily_capture.clarify_items_tool')
    @patch('gtd_coach.agent.workflows.daily_capture.organize_tool')
    @patch('gtd_coach.agent.workflows.daily_capture.assess_user_state_tool')
    async def test_full_workflow_execution(
        self,
        mock_assess,
        mock_organize,
        mock_clarify,
        mock_detect,
        mock_brain_dump,
        mock_scan,
        mock_load,
        workflow_no_agent
    ):
        """Test complete workflow execution with mocked tools"""
        
        # Setup mocks
        mock_load.ainvoke = AsyncMock(return_value={'patterns_found': 0})
        mock_scan.ainvoke = AsyncMock(return_value={'guidance': 'Check emails'})
        mock_brain_dump.ainvoke = AsyncMock(return_value={'prompt': 'What\'s on your mind?'})
        mock_detect.ainvoke = AsyncMock(return_value={'severity': 'low', 'patterns': {}})
        mock_clarify.ainvoke = AsyncMock(return_value={
            'clarified_count': 3,
            'actions': ['Action 1'],
            'projects': [],
            'someday_maybe': []
        })
        mock_organize.ainvoke = AsyncMock(return_value={
            'organized_count': 1,
            'summary': 'Organized 1 item'
        })
        mock_assess.ainvoke = AsyncMock(return_value={
            'energy': 'medium',
            'focus': 'moderate',
            'recommendations': ['Keep going']
        })
        
        # Run workflow
        initial_state = {'test_mode': True}  # Skip memory save
        result = await # Compile workflow first
        from langgraph.checkpoint.memory import InMemorySaver
        checkpointer = InMemorySaver()
        graph = workflow_no_agent.compile(checkpointer=checkpointer)
        config = {"configurable": {"thread_id": "test_thread"}}
        result = graph.invoke(initial_state, config)
        
        assert 'session_id' in result
        assert 'completed_phases' in result
        assert result['current_phase'] == 'complete'
    
    @pytest.mark.asyncio
    async def test_workflow_error_handling(self, workflow_no_agent):
        """Test workflow error handling"""
        # Create a state that will cause an error
        with patch('gtd_coach.agent.workflows.daily_capture.load_context_tool') as mock_tool:
            mock_tool.ainvoke = AsyncMock(side_effect=Exception("Test error"))
            
            initial_state = {}
            
            # Should raise the exception
            with pytest.raises(Exception) as exc_info:
                await # Compile workflow first
        from langgraph.checkpoint.memory import InMemorySaver
        checkpointer = InMemorySaver()
        graph = workflow_no_agent.compile(checkpointer=checkpointer)
        config = {"configurable": {"thread_id": "test_thread"}}
        result = graph.invoke(initial_state, config)
            
            assert "Test error" in str(exc_info.value)


class TestWorkflowFactory:
    """Test workflow factory functions"""
    
    def test_create_daily_capture_workflow(self):
        """Test factory function for daily capture workflow"""
        workflow = create_daily_capture_workflow()
        
        assert isinstance(workflow, DailyCaptureWorkflow)
        assert workflow.use_agent_decisions is True
        
        # With custom settings
        workflow = create_daily_capture_workflow(use_agent_decisions=False)
        assert workflow.use_agent_decisions is False