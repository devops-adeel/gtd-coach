#!/usr/bin/env python3
"""
Comprehensive tests for interrupt/resume patterns in LangGraph workflows
Tests human-in-the-loop functionality with mocked user inputs
"""

import pytest
import asyncio
from datetime import datetime
from typing import Dict, Any, List, Optional
from unittest.mock import Mock, patch, MagicMock, AsyncMock

from langgraph.prebuilt import ToolNode
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver
from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.types import Interrupt, Send, Command
try:
    from langgraph.errors import NodeInterrupt
except ImportError:
    class NodeInterrupt(Exception):
        pass

from gtd_coach.agent.state import AgentState, StateValidator
from gtd_coach.agent.workflows.weekly_review import WeeklyReviewWorkflow, PhaseTimer
from gtd_coach.agent.workflows.daily_capture import DailyCaptureWorkflow


class TestInterruptPatterns:
    """Test various interrupt patterns and user interactions"""
    
    @pytest.fixture
    def mock_interrupt_responses(self):
        """Mock responses for different interrupt types"""
        return {
            "STARTUP": {"ready": True, "user_id": "test_user"},
            "MIND_SWEEP_CAPTURE": {
                "items": [
                    "Review quarterly report",
                    "Schedule team meeting",
                    "Update project documentation",
                    "Fix bug in authentication"
                ]
            },
            "MIND_SWEEP_PROCESS": {
                "processed": [
                    {"item": "Review quarterly report", "project": "Q4 Planning"},
                    {"item": "Schedule team meeting", "project": "Team Management"},
                    {"item": "Update project documentation", "project": "Documentation"},
                    {"item": "Fix bug in authentication", "project": "Backend"}
                ]
            },
            "PROJECT_REVIEW": {
                "projects": {
                    "Q4 Planning": {"next_action": "Read executive summary", "status": "active"},
                    "Team Management": {"next_action": "Send calendar invite", "status": "active"},
                    "Documentation": {"next_action": "Review current docs", "status": "waiting"},
                    "Backend": {"next_action": "Debug auth flow", "status": "active"}
                }
            },
            "PRIORITIZATION": {
                "priorities": {
                    "A": ["Debug auth flow", "Read executive summary"],
                    "B": ["Send calendar invite"],
                    "C": ["Review current docs"]
                }
            },
            "WRAP_UP": {"satisfied": True, "feedback": "Great session!"}
        }
    
    def test_single_interrupt_resume(self, mock_interrupt_responses):
        """Test single interrupt and resume cycle"""
        checkpointer = MemorySaver()
        config = {"configurable": {"thread_id": "single_interrupt_test"}}
        
        # Create a simple workflow with interrupt
        builder = StateGraph(AgentState)
        
        def node_with_interrupt(state: Dict) -> Dict:
            # Simulate interrupt
            user_input = Interrupt({
                "phase": "TEST_PHASE",
                "prompt": "Please provide input",
                "type": "text"
            })
            
            # This would normally block until user provides input
            # In test, we'll simulate the response
            state["user_input"] = user_input
            state["interrupted"] = True
            return state
        
        def process_input(state: Dict) -> Dict:
            # Process the user input after resume
            if state.get("resumed_with"):
                state["processed"] = f"Processed: {state['resumed_with']}"
            state["interrupted"] = False
            return state
        
        builder.add_node("interrupt_node", node_with_interrupt)
        builder.add_node("process_node", process_input)
        builder.add_edge("interrupt_node", "process_node")
        builder.add_edge("process_node", END)
        builder.set_entry_point("interrupt_node")
        
        graph = builder.compile(checkpointer=checkpointer)
        
        # Initial run until interrupt
        initial_state = StateValidator.ensure_required_fields({})
        
        # Simulate interrupt occurring
        with patch('langgraph.constants.Interrupt') as mock_interrupt:
            mock_interrupt.side_effect = NodeInterrupt("User input required")
            
            with pytest.raises(NodeInterrupt):
                result = graph.invoke(initial_state, config)
        
        # Simulate resume with user input
        resume_command = Command(resume={"resumed_with": "User provided input"})
        final_result = graph.invoke(resume_command, config)
        
        # Verify processing completed
        assert final_result.get("interrupted") is False
        assert "processed" in final_result
    
    def test_multiple_interrupts_in_sequence(self, mock_interrupt_responses):
        """Test multiple interrupts in sequence (weekly review flow)"""
        # Mock the workflow with predetermined interrupt responses
        workflow = WeeklyReviewWorkflow(test_mode=True)
        
        # Mock interrupt to return predetermined responses
        def interrupt_side_effect(data):
            phase = data.get('phase')
            return mock_interrupt_responses.get(phase, {})
        
        with patch.object(workflow, 'interrupt', side_effect=interrupt_side_effect):
            # Run through all phases
            state = StateValidator.ensure_required_fields({})
            config = {"configurable": {"thread_id": "multi_interrupt_test"}}
            
            # Each phase should interrupt and resume
            phases_completed = []
            
            # Startup phase
            state = workflow.startup_phase(state)
            assert state.get("ready") is True
            phases_completed.append("STARTUP")
            
            # Mind sweep capture
            state = workflow.mind_sweep_capture(state)
            assert len(state.get("captures", [])) == 4
            phases_completed.append("MIND_SWEEP_CAPTURE")
            
            # Mind sweep process
            state = workflow.mind_sweep_process(state)
            assert len(state.get("processed_items", [])) == 4
            phases_completed.append("MIND_SWEEP_PROCESS")
            
            # Project review
            state = workflow.project_review(state)
            assert len(state.get("projects", {})) == 4
            phases_completed.append("PROJECT_REVIEW")
            
            # Prioritization
            state = workflow.prioritization(state)
            assert "priorities" in state
            phases_completed.append("PRIORITIZATION")
            
            # Wrap up
            state = workflow.wrap_up(state)
            assert state.get("session_complete") is True
            phases_completed.append("WRAP_UP")
            
            # Verify all phases completed
            assert len(phases_completed) == 6
            assert state.get("completed_phases", []) == phases_completed[:-1]  # Wrap-up not in completed list
    
    def test_interrupt_with_timeout(self):
        """Test interrupt with timeout handling"""
        checkpointer = MemorySaver()
        config = {"configurable": {"thread_id": "timeout_test"}}
        
        builder = StateGraph(AgentState)
        
        def node_with_timeout(state: Dict) -> Dict:
            # Simulate interrupt with timeout
            try:
                user_input = Interrupt({
                    "phase": "TIMEOUT_TEST",
                    "prompt": "Provide input within 5 seconds",
                    "type": "text",
                    "timeout": 5
                })
                state["user_input"] = user_input
            except TimeoutError:
                state["timeout_occurred"] = True
                state["user_input"] = None
            
            return state
        
        builder.add_node("timeout_node", node_with_timeout)
        builder.add_edge("timeout_node", END)
        builder.set_entry_point("timeout_node")
        
        graph = builder.compile(checkpointer=checkpointer)
        
        # Test timeout scenario
        with patch('langgraph.constants.Interrupt') as mock_interrupt:
            mock_interrupt.side_effect = TimeoutError("User input timeout")
            
            state = StateValidator.ensure_required_fields({})
            result = graph.invoke(state, config)
            
            assert result.get("timeout_occurred") is True
            assert result.get("user_input") is None
    
    def test_conditional_interrupt(self):
        """Test conditional interrupts based on state"""
        checkpointer = MemorySaver()
        config = {"configurable": {"thread_id": "conditional_test"}}
        
        builder = StateGraph(AgentState)
        
        def conditional_interrupt_node(state: Dict) -> Dict:
            # Only interrupt if certain condition is met
            if state.get("require_user_input", False):
                user_input = Interrupt({
                    "phase": "CONDITIONAL",
                    "prompt": "Additional input needed",
                    "type": "text"
                })
                state["user_provided"] = user_input
            else:
                state["user_provided"] = "auto_generated"
            
            return state
        
        builder.add_node("conditional", conditional_interrupt_node)
        builder.add_edge("conditional", END)
        builder.set_entry_point("conditional")
        
        graph = builder.compile(checkpointer=checkpointer)
        
        # Test without interrupt needed
        state1 = StateValidator.ensure_required_fields({"require_user_input": False})
        result1 = graph.invoke(state1, config)
        assert result1["user_provided"] == "auto_generated"
        
        # Test with interrupt needed
        state2 = StateValidator.ensure_required_fields({"require_user_input": True})
        
        with patch('langgraph.constants.Interrupt') as mock_interrupt:
            mock_interrupt.return_value = "user_input_text"
            result2 = graph.invoke(state2, config)
            assert result2["user_provided"] == "user_input_text"


class TestInterruptTypes:
    """Test different types of interrupt interactions"""
    
    def test_text_input_interrupt(self):
        """Test simple text input interrupt"""
        mock_response = "This is my text input"
        
        with patch('langgraph.constants.Interrupt') as mock_interrupt:
            mock_interrupt.return_value = mock_response
            
            result = Interrupt({
                "phase": "TEST",
                "prompt": "Enter text:",
                "type": "text"
            })
            
            assert result == mock_response
    
    def test_text_list_interrupt(self):
        """Test text list input interrupt (mind sweep)"""
        mock_items = [
            "Item 1",
            "Item 2",
            "Item 3"
        ]
        
        with patch('langgraph.constants.Interrupt') as mock_interrupt:
            mock_interrupt.return_value = {"items": mock_items}
            
            result = Interrupt({
                "phase": "MIND_SWEEP",
                "prompt": "Enter items:",
                "type": "text_list"
            })
            
            assert result["items"] == mock_items
    
    def test_confirmation_interrupt(self):
        """Test yes/no confirmation interrupt"""
        with patch('langgraph.constants.Interrupt') as mock_interrupt:
            # Test positive confirmation
            mock_interrupt.return_value = {"confirmed": True}
            
            result = Interrupt({
                "phase": "CONFIRM",
                "prompt": "Are you ready?",
                "type": "confirmation"
            })
            
            assert result["confirmed"] is True
            
            # Test negative confirmation
            mock_interrupt.return_value = {"confirmed": False}
            
            result = Interrupt({
                "phase": "CONFIRM",
                "prompt": "Continue?",
                "type": "confirmation"
            })
            
            assert result["confirmed"] is False
    
    def test_choice_interrupt(self):
        """Test multiple choice interrupt"""
        choices = ["Option A", "Option B", "Option C"]
        
        with patch('langgraph.constants.Interrupt') as mock_interrupt:
            mock_interrupt.return_value = {"selected": "Option B"}
            
            result = Interrupt({
                "phase": "CHOICE",
                "prompt": "Select an option:",
                "type": "choice",
                "options": choices
            })
            
            assert result["selected"] == "Option B"
    
    def test_structured_input_interrupt(self):
        """Test structured/form input interrupt"""
        mock_form_data = {
            "project_name": "New Project",
            "priority": "A",
            "context": "@office",
            "energy_level": "high"
        }
        
        with patch('langgraph.constants.Interrupt') as mock_interrupt:
            mock_interrupt.return_value = mock_form_data
            
            result = Interrupt({
                "phase": "PROJECT_SETUP",
                "prompt": "Enter project details:",
                "type": "structured",
                "schema": {
                    "project_name": "string",
                    "priority": "string",
                    "context": "string",
                    "energy_level": "string"
                }
            })
            
            assert result == mock_form_data


class TestInterruptStateManagement:
    """Test state management during interrupt/resume cycles"""
    
    def test_state_preservation_across_interrupt(self):
        """Test that state is preserved across interrupt/resume"""
        checkpointer = MemorySaver()
        config = {"configurable": {"thread_id": "preservation_test"}}
        
        # Initial state with data
        initial_state = StateValidator.ensure_required_fields({
            "existing_data": "should_be_preserved",
            "counter": 42,
            "items": ["a", "b", "c"]
        })
        
        # Save checkpoint before interrupt
        from langgraph.checkpoint.base import Checkpoint, CheckpointMetadata
        
        checkpoint = Checkpoint(
            v=1,
            id="before_interrupt",
            ts=datetime.now().isoformat(),
            channel_values=initial_state,
            channel_versions={k: 1 for k in initial_state.keys()},
            versions_seen={}
        )
        
        metadata = CheckpointMetadata(
            source="test",
            step=1,
            writes=initial_state,
            parents={}
        )
        
        checkpointer.put(config, checkpoint, metadata, {})
        
        # Retrieve after "interrupt"
        retrieved = checkpointer.get(config)
        state_after = retrieved["checkpoint"].channel_values
        
        # Verify preservation
        assert state_after["existing_data"] == "should_be_preserved"
        assert state_after["counter"] == 42
        assert state_after["items"] == ["a", "b", "c"]
        
        # Add new data after resume
        state_after["new_data"] = "added_after_resume"
        state_after["counter"] += 1
        
        # Save new checkpoint
        new_checkpoint = Checkpoint(
            v=1,
            id="after_resume",
            ts=datetime.now().isoformat(),
            channel_values=state_after,
            channel_versions={k: 2 for k in state_after.keys()},
            versions_seen={"before_interrupt": {k: 1 for k in initial_state.keys()}}
        )
        
        new_metadata = CheckpointMetadata(
            source="test",
            step=2,
            writes={"new_data": "added_after_resume", "counter": 43},
            parents={"": "before_interrupt"}
        )
        
        checkpointer.put(config, new_checkpoint, new_metadata, {})
        
        # Final verification
        final = checkpointer.get(config)
        final_state = final["checkpoint"].channel_values
        
        assert final_state["existing_data"] == "should_be_preserved"
        assert final_state["new_data"] == "added_after_resume"
        assert final_state["counter"] == 43
    
    def test_interrupt_metadata_tracking(self):
        """Test tracking of interrupt metadata"""
        state = StateValidator.ensure_required_fields({})
        
        # Track interrupt history
        if "interrupt_history" not in state:
            state["interrupt_history"] = []
        
        # First interrupt
        interrupt1 = {
            "phase": "MIND_SWEEP",
            "timestamp": datetime.now().isoformat(),
            "type": "text_list",
            "duration_until_resume": None
        }
        state["interrupt_history"].append(interrupt1)
        
        # Simulate resume after 30 seconds
        import time
        time.sleep(0.1)  # Small delay for testing
        interrupt1["duration_until_resume"] = 0.1
        
        # Second interrupt
        interrupt2 = {
            "phase": "PRIORITIZATION",
            "timestamp": datetime.now().isoformat(),
            "type": "structured",
            "duration_until_resume": None
        }
        state["interrupt_history"].append(interrupt2)
        
        # Verify tracking
        assert len(state["interrupt_history"]) == 2
        assert state["interrupt_history"][0]["phase"] == "MIND_SWEEP"
        assert state["interrupt_history"][0]["duration_until_resume"] is not None
        assert state["interrupt_history"][1]["phase"] == "PRIORITIZATION"
    
    def test_error_recovery_during_interrupt(self):
        """Test error recovery when interrupt fails"""
        checkpointer = MemorySaver()
        config = {"configurable": {"thread_id": "error_recovery_test"}}
        
        builder = StateGraph(AgentState)
        
        def error_prone_interrupt(state: Dict) -> Dict:
            try:
                # Simulate interrupt that might fail
                if state.get("force_error", False):
                    raise RuntimeError("Interrupt failed")
                
                user_input = Interrupt({
                    "phase": "ERROR_TEST",
                    "prompt": "Provide input",
                    "type": "text"
                })
                state["user_input"] = user_input
                state["error_occurred"] = False
                
            except Exception as e:
                # Error recovery
                state["error_occurred"] = True
                state["error_message"] = str(e)
                state["user_input"] = "default_fallback"
            
            return state
        
        builder.add_node("error_node", error_prone_interrupt)
        builder.add_edge("error_node", END)
        builder.set_entry_point("error_node")
        
        graph = builder.compile(checkpointer=checkpointer)
        
        # Test with error
        state_with_error = StateValidator.ensure_required_fields({"force_error": True})
        result = graph.invoke(state_with_error, config)
        
        assert result["error_occurred"] is True
        assert result["user_input"] == "default_fallback"
        assert "error_message" in result
        
        # Test without error
        state_no_error = StateValidator.ensure_required_fields({"force_error": False})
        
        with patch('langgraph.constants.Interrupt') as mock_interrupt:
            mock_interrupt.return_value = "success_input"
            result = graph.invoke(state_no_error, config)
            
            assert result["error_occurred"] is False
            assert result["user_input"] == "success_input"


class TestTimerIntegration:
    """Test timer integration with interrupts"""
    
    @patch('subprocess.Popen')
    def test_timer_during_interrupt(self, mock_popen):
        """Test that timers work correctly during interrupts"""
        # Mock the timer subprocess
        mock_process = MagicMock()
        mock_process.poll.return_value = None  # Timer still running
        mock_popen.return_value = mock_process
        
        # Create phase timer
        timer = PhaseTimer()
        
        # Start timer for mind sweep phase (10 minutes)
        timer.start_phase("MIND_SWEEP", 600)
        
        # Verify timer started
        mock_popen.assert_called_once()
        call_args = mock_popen.call_args[0][0]
        assert "scripts/timer.sh" in call_args[0]
        assert "600" in call_args  # 10 minutes in seconds
        
        # Simulate interrupt occurring
        with patch('langgraph.constants.Interrupt') as mock_interrupt:
            mock_interrupt.return_value = {"items": ["task1", "task2"]}
            
            # Timer should continue running during interrupt
            assert timer.is_running() is True
            
            # Get remaining time
            remaining = timer.get_remaining_time()
            assert remaining > 0
        
        # Stop timer after phase completion
        timer.stop()
        mock_process.terminate.assert_called_once()
    
    def test_timer_pause_resume(self):
        """Test pausing and resuming timer during interrupt"""
        with patch('subprocess.Popen') as mock_popen:
            mock_process = MagicMock()
            mock_process.poll.return_value = None
            mock_popen.return_value = mock_process
            
            timer = PhaseTimer()
            
            # Start timer
            timer.start_phase("PROJECT_REVIEW", 720)  # 12 minutes
            
            # Pause for interrupt
            timer.pause()
            mock_process.terminate.assert_called_once()
            
            # Resume after interrupt
            timer.resume()
            assert mock_popen.call_count == 2  # Initial start + resume
            
            # Stop timer
            timer.stop()


class TestWorkflowInterrupts:
    """Test interrupts in actual workflow implementations"""
    
    def test_weekly_review_full_interrupt_flow(self):
        """Test complete weekly review with all interrupts"""
        workflow = WeeklyReviewWorkflow(test_mode=True)
        
        # Create full mock response set
        full_responses = {
            "STARTUP": {"ready": True},
            "MIND_SWEEP_CAPTURE": {"items": ["task1", "task2", "task3"]},
            "MIND_SWEEP_PROCESS": {
                "processed": [
                    {"item": "task1", "project": "Project A"},
                    {"item": "task2", "project": "Project B"},
                    {"item": "task3", "project": "Project A"}
                ]
            },
            "PROJECT_REVIEW": {
                "projects": {
                    "Project A": {"next_action": "Start task1", "status": "active"},
                    "Project B": {"next_action": "Research task2", "status": "someday"}
                }
            },
            "PRIORITIZATION": {
                "priorities": {
                    "A": ["Start task1"],
                    "B": ["Research task2"],
                    "C": []
                }
            },
            "WRAP_UP": {"satisfied": True}
        }
        
        with patch.object(workflow, 'interrupt', side_effect=lambda x: full_responses.get(x['phase'])):
            state = StateValidator.ensure_required_fields({})
            
            # Run complete workflow
            final_state = workflow.run_full_review(state)
            
            # Verify all phases completed
            assert final_state.get("session_complete") is True
            assert len(final_state.get("captures", [])) == 3
            assert len(final_state.get("projects", {})) == 2
            assert "priorities" in final_state
    
    def test_daily_capture_conditional_interrupt(self):
        """Test daily capture with conditional Timing review interrupt"""
        workflow = DailyCaptureWorkflow(test_mode=True)
        
        # Test without Timing review needed
        state1 = StateValidator.ensure_required_fields({
            "timing_entries": [],  # No significant time tracked
            "focus_score": 85
        })
        
        with patch.object(workflow, 'needs_timing_review', return_value=False):
            result1 = workflow.check_timing_review(state1)
            assert result1.get("timing_review_needed") is False
        
        # Test with Timing review needed
        state2 = StateValidator.ensure_required_fields({
            "timing_entries": [
                {"project": "Email", "duration": 120},
                {"project": "Slack", "duration": 90},
                {"project": "Browsing", "duration": 150}
            ],
            "focus_score": 45
        })
        
        with patch.object(workflow, 'needs_timing_review', return_value=True):
            with patch.object(workflow, 'interrupt') as mock_interrupt:
                mock_interrupt.return_value = {
                    "reviewed": True,
                    "insights": "Need to reduce context switching"
                }
                
                result2 = workflow.check_timing_review(state2)
                assert result2.get("timing_review_needed") is True
                assert "insights" in result2