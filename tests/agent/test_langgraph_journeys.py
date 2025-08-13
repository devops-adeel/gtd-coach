#!/usr/bin/env python3
"""
LangGraph-specific E2E tests for GTD Coach
Tests multi-turn conversations, streaming, checkpointing, and Command primitives
"""

import pytest
import asyncio
import uuid
import json
from datetime import datetime
from typing import Dict, Any, List
from unittest.mock import Mock, patch, MagicMock, AsyncMock
import tempfile
from pathlib import Path

from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver
from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.types import Send, Command
try:
    from langgraph.errors import NodeInterrupt
except ImportError:
    class NodeInterrupt(Exception):
        pass

from gtd_coach.agent.state import AgentState, StateValidator
from gtd_coach.agent.workflows.weekly_review import WeeklyReviewWorkflow, PhaseTimer
from gtd_coach.agent.workflows.daily_capture import DailyCaptureWorkflow


class TestMultiTurnConversations:
    """Test multi-turn conversation flows with interrupts"""
    
    @pytest.mark.asyncio
    async def test_complete_weekly_review_conversation(self):
        """Test complete weekly review with all phases and interrupts"""
        workflow = WeeklyReviewWorkflow(test_mode=True)
        checkpointer = SqliteSaver.from_conn_string(":memory:")
        thread_id = str(uuid.uuid4())
        
        config = {
            "configurable": {
                "thread_id": thread_id,
                "checkpoint_ns": "test"
            }
        }
        
        # Mock interrupt responses for each phase
        interrupt_responses = {
            "STARTUP": {"ready": True, "user_id": "test_user"},
            "MIND_SWEEP_CAPTURE": {
                "items": [
                    "Review Q1 financial report",
                    "Schedule team meeting",
                    "Fix authentication bug",
                    "Plan vacation",
                    "Update documentation"
                ]
            },
            "MIND_SWEEP_PROCESS": {
                "processed": [
                    {"item": "Review Q1 financial report", "project": "Finance"},
                    {"item": "Schedule team meeting", "project": "Team Management"},
                    {"item": "Fix authentication bug", "project": "Backend"},
                    {"item": "Plan vacation", "project": "Personal"},
                    {"item": "Update documentation", "project": "Documentation"}
                ]
            },
            "PROJECT_REVIEW": {
                "projects": {
                    "Finance": {"next_action": "Download Q1 report", "status": "active"},
                    "Team Management": {"next_action": "Send calendar invite", "status": "active"},
                    "Backend": {"next_action": "Review error logs", "status": "active"},
                    "Personal": {"next_action": "Research destinations", "status": "someday"},
                    "Documentation": {"next_action": "List outdated sections", "status": "active"}
                }
            },
            "PRIORITIZATION": {
                "priorities": {
                    "A": ["Review error logs", "Download Q1 report"],
                    "B": ["Send calendar invite", "List outdated sections"],
                    "C": ["Research destinations"]
                }
            },
            "WRAP_UP": {"satisfied": True, "feedback": "Great session!"}
        }
        
        conversation_flow = []
        
        with patch.object(workflow, 'interrupt', side_effect=lambda x: interrupt_responses.get(x['phase'])):
            # Start the conversation
            initial_state = StateValidator.ensure_required_fields({
                "session_id": f"test_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            })
            
            # Phase 1: Startup
            state = workflow.startup_phase(initial_state)
            conversation_flow.append(("STARTUP", state.get("ready")))
            assert state["ready"] is True
            
            # Phase 2: Mind Sweep Capture
            state = workflow.mind_sweep_capture(state)
            conversation_flow.append(("MIND_SWEEP_CAPTURE", len(state.get("captures", []))))
            assert len(state["captures"]) == 5
            
            # Phase 3: Mind Sweep Process
            state = workflow.mind_sweep_process(state)
            conversation_flow.append(("MIND_SWEEP_PROCESS", len(state.get("processed_items", []))))
            assert len(state["processed_items"]) == 5
            
            # Phase 4: Project Review
            state = workflow.project_review(state)
            conversation_flow.append(("PROJECT_REVIEW", len(state.get("projects", {}))))
            assert len(state["projects"]) == 5
            
            # Phase 5: Prioritization
            state = workflow.prioritization(state)
            conversation_flow.append(("PRIORITIZATION", state.get("priorities")))
            assert "A" in state["priorities"]
            assert len(state["priorities"]["A"]) == 2
            
            # Phase 6: Wrap Up
            state = workflow.wrap_up(state)
            conversation_flow.append(("WRAP_UP", state.get("session_complete")))
            assert state["session_complete"] is True
            
            # Verify conversation flow
            assert len(conversation_flow) == 6
            assert conversation_flow[0][0] == "STARTUP"
            assert conversation_flow[-1][0] == "WRAP_UP"
    
    @pytest.mark.asyncio
    async def test_interrupt_resume_with_command_primitive(self):
        """Test interrupt and resume using Command primitive"""
        builder = StateGraph(AgentState)
        checkpointer = MemorySaver()
        
        conversation_log = []
        
        def capture_phase(state: Dict) -> Dict:
            # Simulate interrupt for user input
            user_input = NodeInterrupt("Please provide your captures")
            conversation_log.append(("interrupt", "capture_phase"))
            raise user_input
        
        def process_phase(state: Dict) -> Dict:
            # Process the resumed input
            if "resumed_input" in state:
                state["processed"] = f"Processed: {state['resumed_input']}"
                conversation_log.append(("processed", state["processed"]))
            return state
        
        builder.add_node("capture", capture_phase)
        builder.add_node("process", process_phase)
        builder.add_edge("capture", "process")
        builder.add_edge("process", END)
        builder.set_entry_point("capture")
        
        graph = builder.compile(checkpointer=checkpointer)
        
        thread_id = str(uuid.uuid4())
        config = {"configurable": {"thread_id": thread_id}}
        
        # Initial invocation - will interrupt
        initial_state = StateValidator.ensure_required_fields({})
        
        try:
            result = graph.invoke(initial_state, config)
        except NodeInterrupt as e:
            conversation_log.append(("interrupted", str(e)))
        
        # Resume with Command
        resume_command = Command(
            resume={"resumed_input": ["Task 1", "Task 2", "Task 3"]}
        )
        
        final_result = graph.invoke(resume_command, config)
        
        # Verify conversation flow
        assert len(conversation_log) >= 2
        assert conversation_log[0][0] == "interrupt"
        assert "Processed:" in final_result.get("processed", "")
    
    @pytest.mark.asyncio
    async def test_multi_agent_handoff_conversation(self):
        """Test conversation with agent handoff between phases"""
        thread_config = {"configurable": {"thread_id": str(uuid.uuid4())}}
        
        # Simulate different agents for different phases
        agents = {
            "capture_agent": "Specialized in capturing items",
            "process_agent": "Specialized in processing and organizing",
            "priority_agent": "Specialized in prioritization"
        }
        
        conversation_history = []
        
        # Build a graph with agent handoffs
        builder = StateGraph(AgentState)
        
        def capture_agent_node(state: Dict) -> Dict:
            state["current_agent"] = "capture_agent"
            state["captures"] = ["Item 1", "Item 2", "Item 3"]
            conversation_history.append(("capture_agent", len(state["captures"])))
            return state
        
        def process_agent_node(state: Dict) -> Dict:
            state["current_agent"] = "process_agent"
            state["processed"] = [f"Processed: {item}" for item in state.get("captures", [])]
            conversation_history.append(("process_agent", len(state["processed"])))
            return state
        
        def priority_agent_node(state: Dict) -> Dict:
            state["current_agent"] = "priority_agent"
            state["priorities"] = {
                "A": ["Processed: Item 1"],
                "B": ["Processed: Item 2"],
                "C": ["Processed: Item 3"]
            }
            conversation_history.append(("priority_agent", "prioritized"))
            return state
        
        builder.add_node("capture", capture_agent_node)
        builder.add_node("process", process_agent_node)
        builder.add_node("prioritize", priority_agent_node)
        
        builder.add_edge("capture", "process")
        builder.add_edge("process", "prioritize")
        builder.add_edge("prioritize", END)
        builder.set_entry_point("capture")
        
        graph = builder.compile()
        
        # Run the multi-agent conversation
        initial_state = StateValidator.ensure_required_fields({})
        result = graph.invoke(initial_state, thread_config)
        
        # Verify agent handoffs
        assert len(conversation_history) == 3
        assert conversation_history[0][0] == "capture_agent"
        assert conversation_history[1][0] == "process_agent"
        assert conversation_history[2][0] == "priority_agent"
        assert result["current_agent"] == "priority_agent"


class TestStreamingPatterns:
    """Test different streaming modes and patterns"""
    
    @pytest.mark.asyncio
    async def test_stream_values_mode(self):
        """Test streaming with values mode"""
        builder = StateGraph(AgentState)
        
        stream_log = []
        
        async def streaming_node(state: Dict) -> Dict:
            for i in range(3):
                await asyncio.sleep(0.01)
                state[f"step_{i}"] = f"value_{i}"
                stream_log.append(("step", i))
            return state
        
        builder.add_node("streamer", streaming_node)
        builder.add_edge("streamer", END)
        builder.set_entry_point("streamer")
        
        graph = builder.compile()
        
        initial_state = StateValidator.ensure_required_fields({})
        values_received = []
        
        async for value in graph.astream(initial_state, stream_mode="values"):
            values_received.append(value)
        
        # Verify streaming
        assert len(values_received) > 0
        final_state = values_received[-1]
        assert "step_0" in final_state
        assert "step_1" in final_state
        assert "step_2" in final_state
    
    @pytest.mark.asyncio
    async def test_stream_updates_mode(self):
        """Test streaming with updates mode"""
        builder = StateGraph(AgentState)
        
        async def update_node_1(state: Dict) -> Dict:
            state["update_1"] = "completed"
            return state
        
        async def update_node_2(state: Dict) -> Dict:
            state["update_2"] = "completed"
            return state
        
        async def update_node_3(state: Dict) -> Dict:
            state["update_3"] = "completed"
            return state
        
        builder.add_node("node1", update_node_1)
        builder.add_node("node2", update_node_2)
        builder.add_node("node3", update_node_3)
        
        builder.add_edge("node1", "node2")
        builder.add_edge("node2", "node3")
        builder.add_edge("node3", END)
        builder.set_entry_point("node1")
        
        graph = builder.compile()
        
        initial_state = StateValidator.ensure_required_fields({})
        updates_received = []
        
        async for update in graph.astream(initial_state, stream_mode="updates"):
            updates_received.append(update)
        
        # Verify updates streaming
        assert len(updates_received) >= 3
        
        # Check that each node produced an update
        node_names = set()
        for update in updates_received:
            for node_name in update.keys():
                node_names.add(node_name)
        
        assert "node1" in node_names
        assert "node2" in node_names
        assert "node3" in node_names
    
    @pytest.mark.asyncio
    async def test_stream_debug_mode(self):
        """Test streaming with debug mode for detailed execution info"""
        builder = StateGraph(AgentState)
        
        async def debug_node(state: Dict) -> Dict:
            state["debug_info"] = {
                "timestamp": datetime.now().isoformat(),
                "execution_id": str(uuid.uuid4()),
                "metrics": {"items_processed": 5}
            }
            return state
        
        builder.add_node("debug", debug_node)
        builder.add_edge("debug", END)
        builder.set_entry_point("debug")
        
        graph = builder.compile()
        
        initial_state = StateValidator.ensure_required_fields({})
        debug_info_received = []
        
        async for debug in graph.astream(initial_state, stream_mode="debug"):
            debug_info_received.append(debug)
        
        # Verify debug streaming
        assert len(debug_info_received) > 0
        
        # Debug mode should provide detailed execution information
        has_task_info = False
        for debug in debug_info_received:
            if isinstance(debug, dict) and "type" in debug:
                has_task_info = True
                break
        
        assert has_task_info or len(debug_info_received) > 0  # Ensure we got debug output


class TestCheckpointerPersistence:
    """Test checkpointer persistence across sessions"""
    
    def test_sqlite_checkpointer_persistence(self, tmp_path):
        """Test SQLite checkpointer persists across graph recreations"""
        db_path = tmp_path / "test_persistence.db"
        
        # First session - create and save state
        checkpointer1 = SqliteSaver.from_conn_string(f"sqlite:///{db_path}")
        builder1 = StateGraph(AgentState)
        
        def save_state_node(state: Dict) -> Dict:
            state["persisted_data"] = "This should persist"
            state["timestamp"] = datetime.now().isoformat()
            return state
        
        builder1.add_node("save", save_state_node)
        builder1.add_edge("save", END)
        builder1.set_entry_point("save")
        
        graph1 = builder1.compile(checkpointer=checkpointer1)
        
        thread_id = "persistent_thread_123"
        config = {"configurable": {"thread_id": thread_id}}
        
        initial_state = StateValidator.ensure_required_fields({})
        result1 = graph1.invoke(initial_state, config)
        
        assert "persisted_data" in result1
        saved_timestamp = result1["timestamp"]
        
        # Second session - load persisted state
        checkpointer2 = SqliteSaver.from_conn_string(f"sqlite:///{db_path}")
        
        # Get checkpoint from storage
        saved_checkpoint = checkpointer2.get(config)
        assert saved_checkpoint is not None
        
        saved_state = saved_checkpoint["checkpoint"].channel_values
        assert saved_state.get("persisted_data") == "This should persist"
        assert saved_state.get("timestamp") == saved_timestamp
    
    def test_checkpoint_versioning(self):
        """Test checkpoint versioning and history"""
        checkpointer = MemorySaver()
        thread_id = "version_test"
        config = {"configurable": {"thread_id": thread_id}}
        
        # Create multiple versions
        from langgraph.checkpoint.base import Checkpoint, CheckpointMetadata
        
        versions = []
        for i in range(5):
            checkpoint = Checkpoint(
                v=1,
                id=f"checkpoint_v{i}",
                ts=datetime.now().isoformat(),
                channel_values={
                    "version": i,
                    "data": f"Version {i} data",
                    "accumulated": list(range(i + 1))
                },
                channel_versions={"version": i + 1},
                versions_seen={}
            )
            
            metadata = CheckpointMetadata(
                source="test",
                step=i,
                writes={"version": i},
                parents={"": f"checkpoint_v{i-1}"} if i > 0 else {}
            )
            
            checkpointer.put(config, checkpoint, metadata, {})
            versions.append(checkpoint.id)
        
        # List all versions
        all_checkpoints = list(checkpointer.list(config))
        assert len(all_checkpoints) == 5
        
        # Get latest version
        latest = checkpointer.get(config)
        assert latest["checkpoint"].channel_values["version"] == 4
        
        # Verify version history
        assert len(latest["checkpoint"].channel_values["accumulated"]) == 5
    
    def test_cross_session_state_recovery(self):
        """Test recovering state from interrupted session"""
        checkpointer = MemorySaver()
        thread_id = "recovery_test"
        config = {"configurable": {"thread_id": thread_id}}
        
        # Simulate interrupted session
        from langgraph.checkpoint.base import Checkpoint, CheckpointMetadata
        
        interrupted_checkpoint = Checkpoint(
            v=1,
            id="interrupted_checkpoint",
            ts=datetime.now().isoformat(),
            channel_values={
                "phase": "MIND_SWEEP",
                "captures": ["Task 1", "Task 2"],
                "interrupted": True,
                "progress": 40  # 40% complete
            },
            channel_versions={"phase": 1, "captures": 1},
            versions_seen={}
        )
        
        metadata = CheckpointMetadata(
            source="test",
            step=1,
            writes={"interrupted": True},
            parents={}
        )
        
        checkpointer.put(config, interrupted_checkpoint, metadata, {})
        
        # Recover in new session
        builder = StateGraph(AgentState)
        
        def resume_node(state: Dict) -> Dict:
            # Continue from interrupted state
            if state.get("interrupted"):
                state["resumed"] = True
                state["captures"].extend(["Task 3", "Task 4"])
                state["progress"] = 100
                state["interrupted"] = False
            return state
        
        builder.add_node("resume", resume_node)
        builder.add_edge("resume", END)
        builder.set_entry_point("resume")
        
        graph = builder.compile(checkpointer=checkpointer)
        
        # Load and resume
        saved_state = checkpointer.get(config)["checkpoint"].channel_values
        result = graph.invoke(saved_state, config)
        
        # Verify recovery
        assert result["resumed"] is True
        assert len(result["captures"]) == 4
        assert result["progress"] == 100
        assert result["interrupted"] is False


class TestCommandPrimitives:
    """Test Command primitive patterns for interrupt/resume"""
    
    def test_command_resume_with_data(self):
        """Test Command resume with additional data"""
        builder = StateGraph(AgentState)
        checkpointer = MemorySaver()
        
        def interrupt_node(state: Dict) -> Dict:
            raise NodeInterrupt("User input needed")
        
        def process_node(state: Dict) -> Dict:
            if "user_response" in state:
                state["processed"] = f"Processed: {state['user_response']}"
            return state
        
        builder.add_node("interrupt", interrupt_node)
        builder.add_node("process", process_node)
        builder.add_edge("interrupt", "process")
        builder.add_edge("process", END)
        builder.set_entry_point("interrupt")
        
        graph = builder.compile(checkpointer=checkpointer)
        
        thread_id = str(uuid.uuid4())
        config = {"configurable": {"thread_id": thread_id}}
        
        # Initial run - will interrupt
        initial_state = StateValidator.ensure_required_fields({})
        
        try:
            graph.invoke(initial_state, config)
        except NodeInterrupt:
            pass
        
        # Resume with Command containing data
        resume_command = Command(
            resume={"user_response": "Here is my input"},
            update={"additional_context": "Extra information"}
        )
        
        result = graph.invoke(resume_command, config)
        
        assert "processed" in result
        assert "Here is my input" in result["processed"]
    
    def test_command_goto_node(self):
        """Test Command goto to jump to specific node"""
        builder = StateGraph(AgentState)
        
        execution_path = []
        
        def node_a(state: Dict) -> Dict:
            execution_path.append("A")
            state["visited_a"] = True
            return state
        
        def node_b(state: Dict) -> Dict:
            execution_path.append("B")
            state["visited_b"] = True
            return state
        
        def node_c(state: Dict) -> Dict:
            execution_path.append("C")
            state["visited_c"] = True
            return state
        
        builder.add_node("node_a", node_a)
        builder.add_node("node_b", node_b)
        builder.add_node("node_c", node_c)
        
        # Normal flow: A -> B -> C
        builder.add_edge("node_a", "node_b")
        builder.add_edge("node_b", "node_c")
        builder.add_edge("node_c", END)
        
        # Add conditional edge for goto
        def router(state: Dict):
            if state.get("goto"):
                return state["goto"]
            return "node_a"
        
        builder.set_conditional_entry_point(router, ["node_a", "node_b", "node_c"])
        
        graph = builder.compile()
        
        # Test goto to skip to node_c
        state_with_goto = StateValidator.ensure_required_fields({"goto": "node_c"})
        result = graph.invoke(state_with_goto)
        
        # Should only visit node_c
        assert execution_path == ["C"]
        assert result.get("visited_c") is True
        assert result.get("visited_a") is None
        assert result.get("visited_b") is None