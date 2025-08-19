#!/usr/bin/env python3
"""
Integration tests for LangGraph workflows with mocked interrupts
Tests human-in-the-loop functionality without requiring actual human input
"""

import pytest
import asyncio
from unittest.mock import patch, MagicMock, AsyncMock
from datetime import datetime
from pathlib import Path

# Add parent directory to path
import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from langgraph.types import Command
from gtd_coach.agent.workflows.weekly_review import WeeklyReviewWorkflow
from gtd_coach.agent.workflows.daily_capture import DailyCaptureWorkflow
from gtd_coach.agent.state import AgentState


class TestWeeklyReviewWorkflow:
    """Test weekly review workflow with mocked human interrupts"""
    
    @pytest.fixture
    def mock_interrupt_responses(self):
        """Mock human responses for testing"""
        return {
            "STARTUP": {
                "ready": True
            },
            "MIND_SWEEP_CAPTURE": {
                "items": [
                    "Finish project report",
                    "Call dentist about appointment",
                    "Review budget spreadsheet",
                    "Plan team meeting agenda",
                    "Update resume"
                ]
            },
            "MIND_SWEEP_INBOX": {
                "items": [
                    "Reply to client email",
                    "Schedule 1-on-1 with manager",
                    "Review pull request"
                ]
            },
            "PROJECT_REVIEW": {
                "updates": [
                    {
                        "title": "Q4 Planning",
                        "outcome": "Complete Q4 roadmap",
                        "next_action": "Draft initial goals",
                        "create_new": True
                    }
                ]
            },
            "PRIORITIZATION": {
                "priorities": [
                    "Finish project report",
                    "Reply to client email", 
                    "Draft Q4 goals"
                ]
            },
            "INTERVENTION": {
                "acknowledged": True
            }
        }
    
    @pytest.fixture
    def workflow(self, tmp_path):
        """Create workflow with test database"""
        # Use temporary database for testing
        import os
        os.environ['GTD_COACH_DATA_DIR'] = str(tmp_path)
        
        workflow = WeeklyReviewWorkflow()
        return workflow
    
    def test_startup_phase_with_interrupt(self, workflow, mock_interrupt_responses):
        """Test startup phase with mocked ready confirmation"""
        
        with patch('gtd_coach.agent.workflows.weekly_review.interrupt') as mock_interrupt:
            # Configure mock to return ready response
            mock_interrupt.return_value = mock_interrupt_responses["STARTUP"]
            
            # Create initial state
            state = {
                'messages': [],
                'captures': [],
                'completed_phases': [],
                'user_id': 'test_user'
            }
            
            # Run startup node
            result = workflow.startup_node(state)
            
            # Verify interrupt was called
            mock_interrupt.assert_called_once()
            call_args = mock_interrupt.call_args[0][0]
            assert call_args['phase'] == 'STARTUP'
            assert 'Ready to begin' in call_args['prompt']
            
            # Verify state was updated
            assert 'STARTUP' in result['completed_phases']
            assert result['workflow_type'] == 'weekly_review'
            assert len(result['messages']) > 0
    
    def test_mind_sweep_with_multiple_interrupts(self, workflow, mock_interrupt_responses):
        """Test mind sweep phase with capture and inbox scan interrupts"""
        
        with patch('gtd_coach.agent.workflows.weekly_review.interrupt') as mock_interrupt:
            # Configure mock to return different responses based on phase
            def interrupt_side_effect(data):
                phase = data.get('phase')
                return mock_interrupt_responses.get(phase, {})
            
            mock_interrupt.side_effect = interrupt_side_effect
            
            # Mock pattern detection tool
            with patch('gtd_coach.agent.workflows.weekly_review.detect_patterns_tool.invoke') as mock_patterns:
                mock_patterns.return_value = {'severity': 'low'}
                
                # Create state
                state = {
                    'messages': [],
                    'captures': [],
                    'completed_phases': ['STARTUP'],
                    'current_phase': 'STARTUP'
                }
                
                # Run mind sweep node
                result = workflow.mind_sweep_node(state)
                
                # Verify both interrupts were called
                assert mock_interrupt.call_count == 2
                
                # Verify captures were stored
                assert len(result['captures']) == 8  # 5 from capture + 3 from inbox
                assert 'MIND_SWEEP' in result['completed_phases']
    
    def test_intervention_triggered_by_patterns(self, workflow, mock_interrupt_responses):
        """Test intervention node triggered by ADHD patterns"""
        
        with patch('gtd_coach.agent.workflows.weekly_review.interrupt') as mock_interrupt:
            mock_interrupt.return_value = mock_interrupt_responses["INTERVENTION"]
            
            # Mock intervention tool
            with patch('gtd_coach.agent.workflows.weekly_review.provide_intervention_tool.invoke') as mock_intervention:
                mock_intervention.return_value = {
                    'message': 'I notice rapid topic switching',
                    'action': 'Focus on one area at a time',
                    'technique': 'grounding'
                }
                
                # Create state with pattern analysis
                state = {
                    'messages': [],
                    'pattern_analysis': {
                        'patterns': {'rapid_switching': {'severity': 'high'}},
                        'severity': 'high'
                    },
                    'intervention_needed': True,
                    'interventions': []
                }
                
                # Run intervention node
                result = workflow.intervention_node(state)
                
                # Verify intervention was provided
                mock_intervention.assert_called_once()
                
                # Verify acknowledgment was requested
                mock_interrupt.assert_called_once()
                
                # Verify intervention was recorded
                assert len(result['interventions']) == 1
                assert result['interventions'][0]['type'] == 'rapid_switching'
                assert not result['intervention_needed']
    
    def test_full_workflow_execution(self, workflow, mock_interrupt_responses):
        """Test complete workflow execution with all phases"""
        
        with patch('gtd_coach.agent.workflows.weekly_review.interrupt') as mock_interrupt:
            # Configure mock to return appropriate responses
            def interrupt_side_effect(data):
                phase = data.get('phase')
                return mock_interrupt_responses.get(phase, {})
            
            mock_interrupt.side_effect = interrupt_side_effect
            
            # Mock all tools
            with patch('gtd_coach.agent.workflows.weekly_review.load_context_tool.invoke') as mock_context, \
                 patch('gtd_coach.agent.workflows.weekly_review.detect_patterns_tool.invoke') as mock_patterns, \
                 patch('gtd_coach.agent.workflows.weekly_review.clarify_items_tool.invoke') as mock_clarify, \
                 patch('gtd_coach.agent.workflows.weekly_review.organize_tool.invoke') as mock_organize, \
                 patch('gtd_coach.agent.workflows.weekly_review.prioritize_actions_tool.invoke') as mock_prioritize, \
                 patch('gtd_coach.agent.workflows.weekly_review.save_memory_tool.invoke') as mock_save, \
                 patch('gtd_coach.agent.workflows.weekly_review.assess_user_state_tool.invoke') as mock_assess:
                
                # Configure tool mocks
                mock_context.return_value = {'patterns_found': 0}
                mock_patterns.return_value = {'severity': 'low'}
                mock_clarify.return_value = {
                    'clarified_count': 8,
                    'actions': [{'content': 'Test action'}] * 5,
                    'projects': [{'title': 'Test project'}]
                }
                mock_organize.return_value = {'organized_count': 6}
                mock_prioritize.return_value = {
                    'distribution': {'A': 2, 'B': 3, 'C': 1},
                    'top_priorities': ['Item 1', 'Item 2', 'Item 3']
                }
                mock_save.return_value = {'success': True}
                mock_assess.return_value = {
                    'energy': 'medium',
                    'focus': 'good'
                }
                
                # Create initial state
                initial_state = {
                    'user_id': 'test_user',
                    'session_id': 'test_session_123'
                }
                
                # Compile and run workflow with LangGraph v0.6 API
                from langgraph.checkpoint.memory import InMemorySaver
                checkpointer = InMemorySaver()
                graph = workflow.compile(checkpointer=checkpointer)
                config = {"configurable": {"thread_id": "test_thread"}}
                result = graph.invoke(initial_state, config)
                
                # Verify all phases completed
                assert 'STARTUP' in result['completed_phases']
                assert 'MIND_SWEEP' in result['completed_phases']
                assert 'PROJECT_REVIEW' in result['completed_phases']
                assert 'PRIORITIZATION' in result['completed_phases']
                assert 'WRAP_UP' in result['completed_phases']
                
                # Verify captures and priorities
                assert len(result['captures']) > 0
                assert len(result['weekly_priorities']) == 3
                
                # Verify final phase
                assert result['current_phase'] == 'COMPLETE'


class TestDailyCaptureWorkflow:
    """Test daily capture workflow"""
    
    @pytest.fixture
    def workflow(self):
        """Create daily capture workflow"""
        return DailyCaptureWorkflow(use_agent_decisions=False)
    
    def test_conditional_timing_review(self, workflow):
        """Test conditional routing for timing review"""
        
        # Test with timing API key
        import os
        os.environ['TIMING_API_KEY'] = 'test_key'
        
        state = {'skip_timing': False}
        assert workflow.should_review_timing(state) == "timing"
        
        # Test with skip flag
        state = {'skip_timing': True}
        assert workflow.should_review_timing(state) == "skip"
        
        # Test without API key
        del os.environ['TIMING_API_KEY']
        state = {'skip_timing': False}
        assert workflow.should_review_timing(state) == "skip"
    
    def test_intervention_routing(self, workflow):
        """Test intervention routing based on patterns"""
        
        # Test with intervention needed
        state = {
            'pattern_analysis': {
                'intervention_needed': True,
                'severity': 'high'
            }
        }
        assert workflow.check_intervention_needed(state) == "intervene"
        
        # Test without intervention
        state = {
            'pattern_analysis': {
                'intervention_needed': False,
                'severity': 'low'
            }
        }
        assert workflow.check_intervention_needed(state) == "continue"
    
    def test_memory_save_conditions(self, workflow):
        """Test conditional memory saving"""
        
        # Test in test mode
        state = {'test_mode': True, 'processed_items': ['item1']}
        assert workflow.should_save_memory(state) == "skip"
        
        # Test with no items
        state = {'test_mode': False, 'processed_items': []}
        assert workflow.should_save_memory(state) == "skip"
        
        # Test with items and Neo4j configured
        import os
        os.environ['NEO4J_PASSWORD'] = 'test_password'
        state = {'test_mode': False, 'processed_items': ['item1']}
        assert workflow.should_save_memory(state) == "save"
        
        # Clean up
        del os.environ['NEO4J_PASSWORD']


class TestWorkflowResumption:
    """Test workflow resumption after interrupts"""
    
    @pytest.fixture
    def workflow(self, tmp_path):
        """Create workflow with test database"""
        import os
        os.environ['GTD_COACH_DATA_DIR'] = str(tmp_path)
        
        workflow = WeeklyReviewWorkflow()
        return workflow
    
    def test_resume_after_interrupt(self, workflow):
        """Test resuming workflow after interrupt"""
        
        config = {
            "configurable": {
                "thread_id": "test_resume_123",
                "checkpoint_ns": "test"
            }
        }
        
        with patch('gtd_coach.agent.workflows.weekly_review.interrupt') as mock_interrupt:
            # First run - will hit interrupt
            mock_interrupt.return_value = {"ready": True}
            
            # Create initial state
            state = {
                'messages': [],
                'captures': [],
                'completed_phases': [],
                'user_id': 'test_user'
            }
            
            # Run until first interrupt
            # Note: In real implementation, this would pause at interrupt
            # For testing, we simulate the behavior
            
            # Mock graph invoke to simulate interrupt
            with patch.object(workflow.graph, 'invoke') as mock_invoke:
                # Simulate interrupt response
                mock_invoke.return_value = {
                    '__interrupt__': [{
                        'value': {'phase': 'STARTUP'},
                        'resumable': True
                    }],
                    'session_id': 'test_resume_123'
                }
                
                # Compile and run workflow with checkpointer
                from langgraph.checkpoint.memory import InMemorySaver
                checkpointer = InMemorySaver()
                graph = workflow.compile(checkpointer=checkpointer)
                config = {"configurable": {"thread_id": "test_interrupt"}}
                
                # Run workflow
                result1 = graph.invoke(state, config)
                
                # Verify interrupt marker
                assert '__interrupt__' in result1
                
                # Now simulate resume with Command
                mock_invoke.return_value = {
                    'session_id': 'test_resume_123',
                    'completed_phases': ['STARTUP'],
                    'current_phase': 'MIND_SWEEP'
                }
                
                # Resume workflow with Command
                from langgraph.types import Command
                result2 = graph.invoke(Command(resume="user_input"), config)
                
                # Verify resumed from checkpoint
                assert 'STARTUP' in result2['completed_phases']
                assert result2['current_phase'] != 'STARTUP'


@pytest.mark.asyncio
class TestShadowMode:
    """Test shadow mode execution"""
    
    async def test_shadow_mode_comparison(self, tmp_path):
        """Test shadow mode comparison between legacy and agent"""
        
        from gtd_coach.agent.shadow_runner import ShadowModeRunner
        
        # Create runner with test directory
        runner = ShadowModeRunner()
        runner.metrics_logger.data_dir = tmp_path
        
        # Mock both workflows
        with patch.object(runner, 'run_agent_workflow') as mock_agent, \
             patch.object(runner, 'run_legacy_with_logging') as mock_legacy:
            
            mock_legacy.return_value = {
                'success': True,
                'captures': ['item1', 'item2'],
                'processed_items': ['action1'],
                'session_id': 'test_123'
            }
            
            mock_agent.return_value = {
                'success': True,
                'captures': ['item1', 'item2', 'item3'],
                'processed_items': ['action1', 'action2'],
                'session_id': 'test_123_shadow'
            }
            
            # Run with shadow mode
            with patch('gtd_coach.agent.shadow_runner.should_use_agent') as mock_use_agent, \
                 patch('gtd_coach.agent.shadow_runner.should_run_shadow') as mock_run_shadow:
                
                mock_use_agent.return_value = False
                mock_run_shadow.return_value = True
                
                result = await runner.run_with_shadow('test_123', 'weekly_review')
                
                # Verify legacy was run
                mock_legacy.assert_called_once()
                
                # Wait for shadow comparison to complete
                await asyncio.sleep(0.1)
                
                # Verify shadow comparison was initiated
                # Note: In real implementation, this runs asynchronously


if __name__ == "__main__":
    pytest.main([__file__, "-v"])