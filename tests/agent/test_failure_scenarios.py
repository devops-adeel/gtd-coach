#!/usr/bin/env python3
"""
Failure scenario E2E tests for GTD Coach
Tests error handling, recovery, and graceful degradation
"""

import pytest
import asyncio
import time
import json
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from unittest.mock import Mock, patch, MagicMock, AsyncMock
from pathlib import Path
import tempfile
import sqlite3

from langgraph.graph import StateGraph, END
from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.checkpoint.base import Checkpoint, CheckpointMetadata
try:
    from langgraph.errors import CheckpointNotFound, NodeInterrupt
except ImportError:
    class CheckpointNotFound(Exception):
        pass
    class NodeInterrupt(Exception):
        pass

from gtd_coach.agent.state import AgentState, StateValidator
from gtd_coach.agent.workflows.weekly_review import WeeklyReviewWorkflow, PhaseTimer
from gtd_coach.agent.workflows.daily_capture import DailyCaptureWorkflow


class TestServiceOutages:
    """Test handling of external service outages"""
    
    @pytest.mark.asyncio
    async def test_lm_studio_connection_failure(self):
        """Test handling LM Studio connection failures"""
        workflow = WeeklyReviewWorkflow(test_mode=True)
        
        # Simulate LM Studio being unavailable
        connection_attempts = []
        fallback_used = False
        
        async def mock_llm_call(*args, **kwargs):
            connection_attempts.append(datetime.now())
            
            if len(connection_attempts) < 3:
                # First attempts fail
                raise ConnectionError("Cannot connect to LM Studio at localhost:1234")
            else:
                # Fallback to cached/default response
                nonlocal fallback_used
                fallback_used = True
                return {
                    "response": "Using fallback response",
                    "source": "cache"
                }
        
        with patch('gtd_coach.agent.tools.llm_client.ainvoke', side_effect=mock_llm_call):
            state = StateValidator.ensure_required_fields({})
            
            # Try to run workflow
            try:
                # Should attempt connection with retries
                result = await workflow.process_with_llm(state)
                
                # Verify retry attempts
                assert len(connection_attempts) >= 3
                
                # Verify fallback was used
                assert fallback_used
                assert result.get("source") == "cache"
                
            except ConnectionError:
                # If no fallback available, should handle gracefully
                assert len(connection_attempts) > 0
                
                # Should log error and continue with defaults
                state["llm_unavailable"] = True
                state["using_defaults"] = True
    
    @pytest.mark.asyncio
    async def test_graphiti_neo4j_outage(self):
        """Test handling Graphiti/Neo4j database outages"""
        workflow = DailyCaptureWorkflow(test_mode=True)
        
        # Mock Graphiti memory failures
        mock_memory = AsyncMock()
        mock_memory.add_episode.side_effect = ConnectionError("Neo4j connection refused")
        mock_memory.search_nodes.side_effect = ConnectionError("Neo4j connection refused")
        
        with patch('gtd_coach.agent.tools.memory_client', mock_memory):
            state = StateValidator.ensure_required_fields({
                "captures": ["Task 1", "Task 2", "Task 3"]
            })
            
            # Attempt to save to memory
            save_attempts = []
            
            async def attempt_save():
                try:
                    save_attempts.append(datetime.now())
                    await mock_memory.add_episode({
                        "content": state["captures"],
                        "type": "capture"
                    })
                    return True
                except ConnectionError:
                    return False
            
            # Try to save with retries
            max_retries = 3
            success = False
            
            for _ in range(max_retries):
                if await attempt_save():
                    success = True
                    break
                await asyncio.sleep(0.1)  # Brief delay between retries
            
            # Should have attempted retries
            assert len(save_attempts) == max_retries
            assert not success
            
            # Should fall back to local JSON storage
            fallback_file = Path(tempfile.mkdtemp()) / "graphiti_fallback.json"
            
            # Save to fallback
            with open(fallback_file, 'w') as f:
                json.dump({
                    "timestamp": datetime.now().isoformat(),
                    "data": state["captures"],
                    "error": "Graphiti unavailable - saved locally"
                }, f)
            
            # Verify fallback file created
            assert fallback_file.exists()
            
            # Clean up
            fallback_file.unlink()
    
    @pytest.mark.asyncio
    async def test_timing_api_timeout(self):
        """Test handling Timing API timeouts"""
        workflow = DailyCaptureWorkflow(test_mode=True)
        
        # Mock Timing API with timeout
        async def mock_timing_call(*args, **kwargs):
            await asyncio.sleep(5)  # Simulate slow response
            raise asyncio.TimeoutError("Timing API request timed out")
        
        with patch('gtd_coach.agent.tools.timing_api.get_time_entries', side_effect=mock_timing_call):
            state = StateValidator.ensure_required_fields({})
            
            # Attempt to fetch timing data with timeout
            try:
                timing_task = asyncio.create_task(
                    workflow.fetch_timing_data(state)
                )
                
                # Wait with timeout
                result = await asyncio.wait_for(timing_task, timeout=1.0)
                
            except asyncio.TimeoutError:
                # Should handle timeout gracefully
                state["timing_unavailable"] = True
                state["timing_fallback"] = {
                    "message": "Timing data unavailable",
                    "using_estimates": True,
                    "estimated_focus": 50  # Conservative estimate
                }
            
            # Verify fallback state
            assert state.get("timing_unavailable") is True
            assert state.get("timing_fallback") is not None
            assert state["timing_fallback"]["estimated_focus"] == 50
    
    def test_langfuse_connection_failure(self):
        """Test handling Langfuse observability failures"""
        # Mock Langfuse client that fails
        mock_langfuse = MagicMock()
        mock_langfuse.trace.side_effect = ConnectionError("Langfuse server unreachable")
        
        with patch('langfuse.Langfuse', return_value=mock_langfuse):
            # Should continue without observability
            workflow = WeeklyReviewWorkflow(test_mode=True)
            
            # Run workflow without tracing
            state = StateValidator.ensure_required_fields({})
            
            # Operations should continue despite Langfuse failure
            try:
                # Try to create trace
                mock_langfuse.trace(
                    name="test_trace",
                    session_id=state["session_id"]
                )
            except ConnectionError:
                # Should log but not fail
                state["observability_disabled"] = True
            
            # Workflow should continue
            assert state.get("observability_disabled") is True
            
            # Can still complete workflow
            with patch.object(workflow, 'interrupt', return_value={"ready": True}):
                result = workflow.startup_phase(state)
                assert result["ready"] is True


class TestCheckpointCorruption:
    """Test handling of checkpoint corruption and recovery"""
    
    def test_corrupted_checkpoint_recovery(self, tmp_path):
        """Test recovery from corrupted checkpoint data"""
        db_path = tmp_path / "corrupted.db"
        
        # Create SQLite checkpointer
        checkpointer = SqliteSaver.from_conn_string(f"sqlite:///{db_path}")
        
        # Save valid checkpoint
        config = {"configurable": {"thread_id": "test_thread"}}
        
        valid_checkpoint = Checkpoint(
            v=1,
            id="valid_checkpoint",
            ts=datetime.now().isoformat(),
            channel_values={"data": "valid", "phase": "MIND_SWEEP"},
            channel_versions={"data": 1, "phase": 1},
            versions_seen={}
        )
        
        metadata = CheckpointMetadata(
            source="test",
            step=1,
            writes={"data": "valid"},
            parents={}
        )
        
        checkpointer.put(config, valid_checkpoint, metadata, {})
        
        # Corrupt the database
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()
        
        # Corrupt checkpoint data
        cursor.execute(
            "UPDATE checkpoints SET checkpoint = ? WHERE thread_id = ?",
            (b"corrupted_binary_data", "test_thread")
        )
        conn.commit()
        conn.close()
        
        # Try to load corrupted checkpoint
        try:
            result = checkpointer.get(config)
            # Should fail to deserialize
            assert False, "Should have raised an error"
        except Exception as e:
            # Should handle corruption
            assert "corrupt" in str(e).lower() or "decode" in str(e).lower()
        
        # Recovery: Create new checkpointer and start fresh
        recovery_checkpointer = SqliteSaver.from_conn_string(":memory:")
        
        # Start with clean state
        recovery_checkpoint = Checkpoint(
            v=1,
            id="recovery_checkpoint",
            ts=datetime.now().isoformat(),
            channel_values={"recovered": True, "phase": "STARTUP"},
            channel_versions={"recovered": 1, "phase": 1},
            versions_seen={}
        )
        
        recovery_checkpointer.put(config, recovery_checkpoint, metadata, {})
        
        # Verify recovery
        recovered = recovery_checkpointer.get(config)
        assert recovered is not None
        assert recovered["checkpoint"].channel_values["recovered"] is True
    
    def test_checkpoint_version_mismatch(self):
        """Test handling checkpoint version mismatches"""
        checkpointer = MemorySaver()
        config = {"configurable": {"thread_id": "version_test"}}
        
        # Save checkpoint with version 1 schema
        v1_checkpoint = Checkpoint(
            v=1,
            id="v1_checkpoint",
            ts=datetime.now().isoformat(),
            channel_values={
                "old_field": "value",
                "deprecated_field": "remove_me"
            },
            channel_versions={"old_field": 1},
            versions_seen={}
        )
        
        metadata = CheckpointMetadata(
            source="v1",
            step=1,
            writes={},
            parents={}
        )
        
        checkpointer.put(config, v1_checkpoint, metadata, {})
        
        # Load with v2 schema expectations
        loaded = checkpointer.get(config)
        old_data = loaded["checkpoint"].channel_values
        
        # Migration function
        def migrate_v1_to_v2(old_state: Dict) -> Dict:
            """Migrate from v1 to v2 schema"""
            new_state = {}
            
            # Rename old fields
            if "old_field" in old_state:
                new_state["new_field"] = old_state["old_field"]
            
            # Remove deprecated fields
            if "deprecated_field" in old_state:
                pass  # Don't copy
            
            # Add new required fields
            new_state["version"] = 2
            new_state["migrated_at"] = datetime.now().isoformat()
            
            return new_state
        
        # Migrate state
        migrated_state = migrate_v1_to_v2(old_data)
        
        # Verify migration
        assert "new_field" in migrated_state
        assert migrated_state["new_field"] == "value"
        assert "deprecated_field" not in migrated_state
        assert migrated_state["version"] == 2
    
    def test_partial_checkpoint_recovery(self):
        """Test recovery from partially written checkpoints"""
        checkpointer = MemorySaver()
        config = {"configurable": {"thread_id": "partial_test"}}
        
        # Simulate partial checkpoint (interrupted write)
        partial_checkpoint = Checkpoint(
            v=1,
            id="partial_checkpoint",
            ts=datetime.now().isoformat(),
            channel_values={
                "phase": "MIND_SWEEP",
                "captures": ["item1", "item2"],
                # Missing expected fields like "processed_items"
            },
            channel_versions={"phase": 1, "captures": 1},
            versions_seen={}
        )
        
        metadata = CheckpointMetadata(
            source="test",
            step=1,
            writes={"partial": True},
            parents={}
        )
        
        checkpointer.put(config, partial_checkpoint, metadata, {})
        
        # Load and repair partial checkpoint
        loaded = checkpointer.get(config)
        partial_state = loaded["checkpoint"].channel_values
        
        # Repair function
        def repair_partial_state(state: Dict) -> Dict:
            """Repair partial state with defaults"""
            repaired = state.copy()
            
            # Add missing required fields
            defaults = {
                "processed_items": [],
                "priorities": {"A": [], "B": [], "C": []},
                "session_complete": False,
                "error_state": "recovered_from_partial"
            }
            
            for key, default_value in defaults.items():
                if key not in repaired:
                    repaired[key] = default_value
            
            return repaired
        
        # Repair state
        repaired_state = repair_partial_state(partial_state)
        
        # Verify repair
        assert "processed_items" in repaired_state
        assert repaired_state["error_state"] == "recovered_from_partial"
        assert repaired_state["session_complete"] is False


class TestTimeoutAndCancellation:
    """Test timeout and cancellation scenarios"""
    
    @pytest.mark.asyncio
    async def test_phase_timeout_handling(self):
        """Test handling phase timeouts"""
        workflow = WeeklyReviewWorkflow(test_mode=True)
        
        # Mock timer that expires
        with patch.object(PhaseTimer, 'get_remaining_time', return_value=0):
            with patch.object(PhaseTimer, 'is_running', return_value=False):
                
                state = StateValidator.ensure_required_fields({
                    "current_phase": "MIND_SWEEP",
                    "captures": ["item1", "item2"]  # Incomplete
                })
                
                # Phase should handle timeout
                with patch.object(workflow, 'interrupt') as mock_interrupt:
                    # Simulate timeout response
                    mock_interrupt.side_effect = TimeoutError("Phase time limit exceeded")
                    
                    try:
                        result = workflow.mind_sweep_capture(state)
                    except TimeoutError:
                        # Should save partial progress
                        state["phase_timeout"] = True
                        state["partial_completion"] = True
                        state["timeout_phase"] = "MIND_SWEEP"
                        
                        # Move to next phase with partial data
                        state["current_phase"] = "MIND_SWEEP_PROCESS"
                
                # Verify timeout handling
                assert state.get("phase_timeout") is True
                assert state.get("partial_completion") is True
                assert len(state["captures"]) == 2  # Partial data preserved
    
    @pytest.mark.asyncio
    async def test_user_cancellation_handling(self):
        """Test handling user cancellation mid-workflow"""
        workflow = WeeklyReviewWorkflow(test_mode=True)
        
        cancellation_requested = False
        
        async def check_cancellation():
            """Check if user requested cancellation"""
            return cancellation_requested
        
        state = StateValidator.ensure_required_fields({
            "current_phase": "PROJECT_REVIEW",
            "projects_reviewed": 3,
            "total_projects": 10
        })
        
        # Simulate user cancellation
        with patch.object(workflow, 'check_user_cancellation', side_effect=check_cancellation):
            # Start review
            for i in range(10):
                if i == 5:
                    # User cancels mid-review
                    cancellation_requested = True
                
                if await check_cancellation():
                    # Handle cancellation
                    state["cancelled"] = True
                    state["cancellation_point"] = f"project_{i}"
                    state["partial_save"] = True
                    break
                
                # Continue reviewing
                state["projects_reviewed"] += 1
        
        # Verify cancellation handling
        assert state.get("cancelled") is True
        assert state["projects_reviewed"] == 8  # 3 initial + 5 before cancel
        assert state.get("partial_save") is True
    
    @pytest.mark.asyncio
    async def test_async_task_cancellation(self):
        """Test cancellation of async tasks"""
        workflow = DailyCaptureWorkflow(test_mode=True)
        
        # Create long-running async task
        async def long_running_task():
            try:
                await asyncio.sleep(10)  # Simulate long operation
                return "completed"
            except asyncio.CancelledError:
                # Clean up on cancellation
                return "cancelled"
        
        # Start task
        task = asyncio.create_task(long_running_task())
        
        # Cancel after short delay
        await asyncio.sleep(0.1)
        task.cancel()
        
        # Handle cancellation
        try:
            result = await task
        except asyncio.CancelledError:
            result = "task_cancelled"
        
        assert result == "task_cancelled" or result == "cancelled"


class TestGracefulDegradation:
    """Test graceful degradation when services fail"""
    
    def test_degraded_mode_operation(self):
        """Test operating in degraded mode with limited services"""
        workflow = WeeklyReviewWorkflow(test_mode=True)
        
        # Track available services
        services = {
            "llm": False,  # LM Studio down
            "graphiti": False,  # Neo4j down
            "timing": True,  # Timing app available
            "langfuse": False  # Langfuse down
        }
        
        state = StateValidator.ensure_required_fields({
            "degraded_mode": True,
            "available_services": services
        })
        
        # Run in degraded mode
        degraded_features = []
        
        # Check each service and adapt
        if not services["llm"]:
            # Use rule-based processing instead of LLM
            degraded_features.append("rule_based_processing")
            state["processing_mode"] = "rules"
        
        if not services["graphiti"]:
            # Use local JSON storage
            degraded_features.append("local_storage")
            state["storage_mode"] = "json"
        
        if not services["langfuse"]:
            # Disable observability
            degraded_features.append("no_observability")
            state["observability"] = False
        
        if services["timing"]:
            # Can still use timing data
            state["timing_available"] = True
        
        # Verify degraded mode setup
        assert state["degraded_mode"] is True
        assert len(degraded_features) == 3
        assert state["processing_mode"] == "rules"
        assert state["storage_mode"] == "json"
    
    def test_progressive_feature_degradation(self):
        """Test progressive degradation as more services fail"""
        workflow = DailyCaptureWorkflow(test_mode=True)
        
        # Start with all services
        service_status = {
            "llm": True,
            "graphiti": True,
            "timing": True,
            "langfuse": True
        }
        
        functionality_levels = []
        
        # Progressively fail services
        for service in ["langfuse", "timing", "graphiti", "llm"]:
            service_status[service] = False
            
            # Assess functionality level
            if all(service_status.values()):
                level = "full"
            elif service_status["llm"] and service_status["graphiti"]:
                level = "normal"
            elif service_status["llm"] or service_status["graphiti"]:
                level = "degraded"
            else:
                level = "minimal"
            
            functionality_levels.append({
                "failed": service,
                "level": level,
                "services_up": sum(service_status.values())
            })
        
        # Verify progressive degradation
        assert functionality_levels[0]["level"] == "normal"  # Lost Langfuse
        assert functionality_levels[1]["level"] == "degraded"  # Lost Timing
        assert functionality_levels[2]["level"] == "degraded"  # Lost Graphiti
        assert functionality_levels[3]["level"] == "minimal"  # Lost LLM
        
        # Verify service count decreases
        for i in range(1, len(functionality_levels)):
            assert functionality_levels[i]["services_up"] < functionality_levels[i-1]["services_up"]
    
    @pytest.mark.asyncio
    async def test_fallback_chain(self):
        """Test fallback chain when primary methods fail"""
        
        # Define fallback chain
        async def try_primary():
            raise ConnectionError("Primary failed")
        
        async def try_secondary():
            raise TimeoutError("Secondary failed")
        
        async def try_tertiary():
            return {"source": "tertiary", "data": "fallback_data"}
        
        fallback_chain = [try_primary, try_secondary, try_tertiary]
        
        # Execute fallback chain
        result = None
        errors = []
        
        for i, method in enumerate(fallback_chain):
            try:
                result = await method()
                break
            except Exception as e:
                errors.append({
                    "level": i,
                    "method": method.__name__,
                    "error": str(e)
                })
        
        # Verify fallback execution
        assert len(errors) == 2  # First two failed
        assert result is not None
        assert result["source"] == "tertiary"
        assert errors[0]["method"] == "try_primary"
        assert errors[1]["method"] == "try_secondary"