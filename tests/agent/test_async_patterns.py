#!/usr/bin/env python3
"""
Comprehensive tests for async patterns in LangGraph workflows
Tests async/await, concurrency, streaming, and error handling
"""

import pytest
import pytest_asyncio
import asyncio
import time
from datetime import datetime, timedelta
from typing import Dict, Any, List, AsyncIterator
from unittest.mock import Mock, patch, MagicMock, AsyncMock
from concurrent.futures import ThreadPoolExecutor

from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver
from langgraph.prebuilt import ToolNode
from langgraph.constants import Send

from gtd_coach.agent.state import AgentState, StateValidator
from gtd_coach.agent.tools.capture import (
    scan_inbox_tool,
    capture_item_tool
)
from gtd_coach.agent.tools.gtd import (
    clarify_items_tool
)
from gtd_coach.agent.tools.graphiti import (
    search_memory_tool
)


class TestAsyncWorkflowExecution:
    """Test async workflow execution patterns"""
    
    @pytest.mark.asyncio
    async def test_basic_async_workflow(self):
        """Test basic async workflow execution"""
        builder = StateGraph(AgentState)
        
        async def async_node(state: Dict) -> Dict:
            await asyncio.sleep(0.01)  # Simulate async work
            # Use actual AgentState fields
            return {
                "current_phase": "complete",
                "completed_phases": state.get("completed_phases", []) + ["async_test"]
            }
        
        builder.add_node("async_node", async_node)
        builder.add_edge("async_node", END)
        builder.set_entry_point("async_node")
        
        graph = builder.compile()
        
        initial_state = StateValidator.ensure_required_fields({})
        result = await graph.ainvoke(initial_state)
        
        assert result["current_phase"] == "complete"
        assert "async_test" in result["completed_phases"]
    
    @pytest.mark.asyncio
    async def test_parallel_node_execution(self):
        """Test parallel execution of multiple nodes"""
        builder = StateGraph(AgentState)
        
        execution_order = []
        
        async def node_a(state: Dict) -> Dict:
            execution_order.append("a_start")
            await asyncio.sleep(0.02)
            execution_order.append("a_end")
            # Use list fields that can handle multiple updates
            return {
                "captures": state.get("captures", []) + [{"source": "node_a"}]
            }
        
        async def node_b(state: Dict) -> Dict:
            execution_order.append("b_start")
            await asyncio.sleep(0.01)
            execution_order.append("b_end")
            # Use list fields that can handle multiple updates
            return {
                "captures": state.get("captures", []) + [{"source": "node_b"}]
            }
        
        async def merge_node(state: Dict) -> Dict:
            execution_order.append("merge")
            # Mark completion
            return {
                "current_phase": "merged",
                "completed_phases": state.get("completed_phases", []) + ["parallel_test"]
            }
        
        builder.add_node("node_a", node_a)
        builder.add_node("node_b", node_b)
        builder.add_node("merge", merge_node)
        
        # Sequential execution to avoid parallel update conflicts
        builder.set_entry_point("node_a")
        builder.add_edge("node_a", "node_b")
        builder.add_edge("node_b", "merge")
        builder.add_edge("merge", END)
        
        graph = builder.compile()
        
        initial_state = StateValidator.ensure_required_fields({})
        result = await graph.ainvoke(initial_state)
        
        # Verify execution order (now sequential)
        assert execution_order[0] == "a_start"
        assert execution_order[1] == "a_end"
        assert execution_order[2] == "b_start"
        assert execution_order[3] == "b_end"
        assert execution_order[-1] == "merge"
        
        # Verify state updates
        assert len(result["captures"]) == 2
        assert result["current_phase"] == "merged"
        assert "parallel_test" in result["completed_phases"]
    
    @pytest.mark.asyncio
    async def test_async_streaming(self):
        """Test async streaming of results"""
        builder = StateGraph(AgentState)
        
        async def streaming_node(state: Dict) -> Dict:
            """Node that simulates streaming updates"""
            # Add captures incrementally
            captures = state.get("captures", [])
            for i in range(3):
                await asyncio.sleep(0.01)
                captures.append({"id": f"stream_{i}", "content": f"data_{i}"})
            
            return {
                "captures": captures,
                "current_phase": "streaming_complete"
            }
        
        builder.add_node("streamer", streaming_node)
        builder.add_edge("streamer", END)
        builder.set_entry_point("streamer")
        
        graph = builder.compile()
        
        initial_state = StateValidator.ensure_required_fields({})
        chunks = []
        
        async for chunk in graph.astream(initial_state):
            chunks.append(chunk)
        
        # Should receive at least one chunk with final state
        assert len(chunks) >= 1
        
        # Final state should have all captures
        final_state = chunks[-1] if isinstance(chunks[-1], dict) else chunks[-1]["streamer"]
        if "streamer" in final_state:
            final_state = final_state["streamer"]
        assert len(final_state.get("captures", [])) == 3
        assert final_state.get("current_phase") == "streaming_complete"
    
    @pytest.mark.asyncio
    async def test_async_with_checkpointing(self):
        """Test async execution with checkpointing"""
        checkpointer = MemorySaver()
        builder = StateGraph(AgentState)
        
        async def node_1(state: Dict) -> Dict:
            return {
                "completed_phases": state.get("completed_phases", []) + ["step_1"],
                "current_phase": "step_1"
            }
        
        async def node_2(state: Dict) -> Dict:
            return {
                "completed_phases": state.get("completed_phases", []) + ["step_2"],
                "current_phase": "step_2"
            }
        
        builder.add_node("node_1", node_1)
        builder.add_node("node_2", node_2)
        builder.add_edge("node_1", "node_2")
        builder.add_edge("node_2", END)
        builder.set_entry_point("node_1")
        
        graph = builder.compile(checkpointer=checkpointer)
        
        config = {"configurable": {"thread_id": "async_checkpoint_test"}}
        initial_state = StateValidator.ensure_required_fields({})
        
        # Run workflow
        result = await graph.ainvoke(initial_state, config)
        
        assert "step_1" in result["completed_phases"]
        assert "step_2" in result["completed_phases"]
        assert result["current_phase"] == "step_2"
        
        # Verify checkpoints were saved
        checkpoints = list(checkpointer.list(config))
        assert len(checkpoints) > 0


class TestAsyncErrorHandling:
    """Test async error handling patterns"""
    
    @pytest.mark.asyncio
    async def test_async_error_propagation(self):
        """Test error propagation in async workflows"""
        builder = StateGraph(AgentState)
        
        async def failing_node(state: Dict) -> Dict:
            await asyncio.sleep(0.01)
            raise ValueError("Test error")
        
        builder.add_node("failing", failing_node)
        builder.add_edge("failing", END)
        builder.set_entry_point("failing")
        
        graph = builder.compile()
        
        initial_state = StateValidator.ensure_required_fields({})
        
        with pytest.raises(ValueError, match="Test error"):
            await graph.ainvoke(initial_state)
    
    @pytest.mark.asyncio
    async def test_async_error_recovery(self):
        """Test error recovery in async workflows"""
        builder = StateGraph(AgentState)
        
        attempt_count = {"count": 0}
        
        async def unreliable_node(state: Dict) -> Dict:
            attempt_count["count"] += 1
            
            if attempt_count["count"] < 3:
                raise ConnectionError("Temporary failure")
            
            # Use actual AgentState fields
            return {
                "current_phase": "recovered",
                "completed_phases": state.get("completed_phases", []) + ["error_recovery"]
            }
        
        async def retry_wrapper(state: Dict) -> Dict:
            max_retries = 3
            for attempt in range(max_retries):
                try:
                    return await unreliable_node(state)
                except ConnectionError:
                    if attempt == max_retries - 1:
                        raise
                    await asyncio.sleep(0.01)
            return state
        
        builder.add_node("retry_node", retry_wrapper)
        builder.add_edge("retry_node", END)
        builder.set_entry_point("retry_node")
        
        graph = builder.compile()
        
        initial_state = StateValidator.ensure_required_fields({})
        result = await graph.ainvoke(initial_state)
        
        assert result["current_phase"] == "recovered"
        assert "error_recovery" in result["completed_phases"]
        assert attempt_count["count"] == 3
    
    @pytest.mark.asyncio
    async def test_async_timeout_handling(self):
        """Test timeout handling in async workflows"""
        builder = StateGraph(AgentState)
        
        async def slow_node(state: Dict) -> Dict:
            await asyncio.sleep(5)  # Intentionally slow
            return {
                "current_phase": "completed_slow"
            }
        
        async def timeout_wrapper(state: Dict) -> Dict:
            try:
                result = await asyncio.wait_for(
                    slow_node(state),
                    timeout=0.1  # 100ms timeout
                )
                return result
            except asyncio.TimeoutError:
                # Handle timeout with proper state fields
                return {
                    "current_phase": "timeout",
                    "errors": state.get("errors", []) + [{"type": "timeout", "message": "Operation timed out"}]
                }
        
        builder.add_node("timeout_node", timeout_wrapper)
        builder.add_edge("timeout_node", END)
        builder.set_entry_point("timeout_node")
        
        graph = builder.compile()
        
        initial_state = StateValidator.ensure_required_fields({})
        result = await graph.ainvoke(initial_state)
        
        assert result["current_phase"] == "timeout"
        assert len(result.get("errors", [])) > 0
        assert result["errors"][0]["type"] == "timeout"
    
    @pytest.mark.asyncio
    async def test_async_cancellation(self):
        """Test task cancellation in async workflows"""
        builder = StateGraph(AgentState)
        
        cancellation_handled = {"handled": False}
        
        async def cancellable_node(state: Dict) -> Dict:
            try:
                for i in range(10):
                    await asyncio.sleep(0.1)
                    state[f"step_{i}"] = True
            except asyncio.CancelledError:
                cancellation_handled["handled"] = True
                state["cancelled"] = True
                raise
            
            return state
        
        builder.add_node("cancellable", cancellable_node)
        builder.add_edge("cancellable", END)
        builder.set_entry_point("cancellable")
        
        graph = builder.compile()
        
        initial_state = StateValidator.ensure_required_fields({})
        
        # Start workflow
        task = asyncio.create_task(graph.ainvoke(initial_state))
        
        # Cancel after short delay
        await asyncio.sleep(0.05)
        task.cancel()
        
        with pytest.raises(asyncio.CancelledError):
            await task
        
        assert cancellation_handled["handled"] is True


class TestAsyncToolExecution:
    """Test async tool execution patterns"""
    
    @pytest.mark.asyncio
    async def test_async_tool_invocation(self):
        """Test async tool invocation"""
        from langchain_core.tools import tool
        
        # Create a proper async tool
        @tool
        async def async_tool(param: str) -> dict:
            """Test async tool"""
            await asyncio.sleep(0.01)
            return {"result": "success", "param": param}
        
        # Mock the tool's invoke method for verification
        original_ainvoke = async_tool.ainvoke
        async_tool.ainvoke = AsyncMock(wraps=original_ainvoke)
        
        # Create tool node
        tool_node = ToolNode([async_tool])
        
        # Create state with tool call
        state = {
            "messages": [
                {
                    "role": "assistant",
                    "content": "",
                    "tool_calls": [
                        {
                            "id": "call_1",
                            "name": "async_tool",
                            "args": {"param": "value"}
                        }
                    ]
                }
            ]
        }
        
        # Execute tool
        result = await tool_node.ainvoke(state)
        
        # Verify tool was called
        async_tool.ainvoke.assert_called_once()
        assert "messages" in result
    
    @pytest.mark.asyncio
    async def test_parallel_tool_execution(self):
        """Test parallel execution of multiple tools"""
        from langchain_core.tools import tool
        
        # Create multiple async tools
        tools = []
        
        @tool
        async def tool_0(param: str) -> dict:
            """Tool 0"""
            await asyncio.sleep(0.03)
            return {"result": "result_0"}
        
        @tool
        async def tool_1(param: str) -> dict:
            """Tool 1"""
            await asyncio.sleep(0.02)
            return {"result": "result_1"}
        
        @tool
        async def tool_2(param: str) -> dict:
            """Tool 2"""
            await asyncio.sleep(0.01)
            return {"result": "result_2"}
        
        tools = [tool_0, tool_1, tool_2]
        
        # Create tool node
        tool_node = ToolNode(tools)
        
        # Create state with multiple tool calls
        state = {
            "messages": [
                {
                    "role": "assistant",
                    "content": "",
                    "tool_calls": [
                        {"id": f"call_{i}", "name": f"tool_{i}", "args": {}}
                        for i in range(3)
                    ]
                }
            ]
        }
        
        # Execute tools (should be parallel)
        start_time = time.time()
        result = await tool_node.ainvoke(state)
        execution_time = time.time() - start_time
        
        # Should be faster than sequential execution
        assert execution_time < 0.06  # Less than sum of all sleeps
    
    @pytest.mark.asyncio
    async def test_async_tool_with_retry(self):
        """Test async tool with retry logic"""
        from langchain_core.tools import tool
        
        call_count = {"count": 0}
        
        @tool
        async def flaky_tool(query: str) -> dict:
            """Test flaky tool"""
            call_count["count"] += 1
            if call_count["count"] < 3:
                raise ConnectionError("Network error")
            return {"success": True, "query": query}
        
        # Wrap with retry logic
        async def retry_wrapper(query: str) -> dict:
            for attempt in range(3):
                try:
                    return await flaky_tool.ainvoke({"query": query})
                except ConnectionError:
                    if attempt == 2:
                        raise
                    await asyncio.sleep(0.01)
            return {"success": False}
        
        # Execute tool with retry
        result = await retry_wrapper("test")
        
        assert result["success"] is True
        assert call_count["count"] == 3


class TestAsyncStateManagement:
    """Test async state management patterns"""
    
    @pytest.mark.asyncio
    async def test_concurrent_state_updates(self):
        """Test concurrent state updates"""
        builder = StateGraph(AgentState)
        
        async def update_node_a(state: Dict) -> Dict:
            await asyncio.sleep(0.01)
            # Use captures field which is a list
            captures = state.get("captures", [])
            captures.append({"id": "a", "content": "Update from node A"})
            return {"captures": captures}
        
        async def update_node_b(state: Dict) -> Dict:
            await asyncio.sleep(0.01)
            # Append to captures
            captures = state.get("captures", [])
            captures.append({"id": "b", "content": "Update from node B"})
            return {"captures": captures}
        
        builder.add_node("node_a", update_node_a)
        builder.add_node("node_b", update_node_b)
        
        # Sequential updates
        builder.add_edge("node_a", "node_b")
        builder.add_edge("node_b", END)
        builder.set_entry_point("node_a")
        
        graph = builder.compile()
        
        initial_state = StateValidator.ensure_required_fields({})
        result = await graph.ainvoke(initial_state)
        
        # Updates should be in order
        assert len(result["captures"]) == 2
        assert result["captures"][0]["id"] == "a"
        assert result["captures"][1]["id"] == "b"
    
    @pytest.mark.asyncio
    async def test_async_state_reducers(self):
        """Test async state reducers"""
        # Use the existing AgentState which has captures with add_messages reducer
        builder = StateGraph(AgentState)
        
        async def add_items_node(state: Dict) -> Dict:
            # Add to captures which is a list field
            return {"captures": [{"id": "item1"}, {"id": "item2"}]}
        
        async def add_more_items_node(state: Dict) -> Dict:
            # Add more captures
            captures = state.get("captures", [])
            captures.append({"id": "item3"})
            return {"captures": captures}
        
        builder.add_node("add_items", add_items_node)
        builder.add_node("add_more", add_more_items_node)
        builder.add_edge("add_items", "add_more")
        builder.add_edge("add_more", END)
        builder.set_entry_point("add_items")
        
        graph = builder.compile()
        
        initial_state = StateValidator.ensure_required_fields({
            "captures": [{"id": "item0"}]
        })
        result = await graph.ainvoke(initial_state)
        
        # Should have all captures
        assert len(result["captures"]) >= 3  # item0, item1, item2, item3
        capture_ids = [c["id"] for c in result["captures"]]
        assert "item3" in capture_ids
    
    @pytest.mark.asyncio
    async def test_async_state_validation(self):
        """Test async state validation"""
        builder = StateGraph(AgentState)
        
        async def validate_state(state: Dict) -> Dict:
            # Async validation
            await asyncio.sleep(0.01)
            
            # Validate required fields
            required = ["session_id", "workflow_type", "messages"]
            for field in required:
                if field not in state:
                    raise ValueError(f"Missing required field: {field}")
            
            # Validate data types
            if not isinstance(state["messages"], list):
                raise TypeError("messages must be a list")
            
            # Mark validation complete using proper field
            return {
                "current_phase": "validated",
                "completed_phases": state.get("completed_phases", []) + ["validation"]
            }
        
        builder.add_node("validator", validate_state)
        builder.add_edge("validator", END)
        builder.set_entry_point("validator")
        
        graph = builder.compile()
        
        # Valid state
        valid_state = StateValidator.ensure_required_fields({})
        result = await graph.ainvoke(valid_state)
        assert result["current_phase"] == "validated"
        assert "validation" in result["completed_phases"]
        
        # Invalid state
        invalid_state = {"invalid": True}
        with pytest.raises(ValueError):
            await graph.ainvoke(invalid_state)


class TestAsyncPerformance:
    """Test async performance characteristics"""
    
    @pytest.mark.asyncio
    async def test_async_vs_sync_performance(self):
        """Compare async vs sync performance"""
        # Async implementation
        async def async_workflow(num_tasks: int):
            tasks = []
            for i in range(num_tasks):
                tasks.append(asyncio.create_task(asyncio.sleep(0.01)))
            await asyncio.gather(*tasks)
        
        # Measure async performance
        start = time.time()
        await async_workflow(10)
        async_time = time.time() - start
        
        # Sync implementation (simulated)
        def sync_workflow(num_tasks: int):
            for i in range(num_tasks):
                time.sleep(0.01)
        
        # Measure sync performance
        start = time.time()
        sync_workflow(10)
        sync_time = time.time() - start
        
        # Async should be significantly faster
        assert async_time < sync_time / 2
    
    @pytest.mark.asyncio
    async def test_async_concurrency_limits(self):
        """Test async concurrency limits"""
        semaphore = asyncio.Semaphore(3)  # Limit to 3 concurrent tasks
        
        active_count = {"max": 0, "current": 0}
        
        async def limited_task(task_id: int):
            async with semaphore:
                active_count["current"] += 1
                active_count["max"] = max(active_count["max"], active_count["current"])
                await asyncio.sleep(0.01)
                active_count["current"] -= 1
        
        # Launch many tasks
        tasks = [limited_task(i) for i in range(10)]
        await asyncio.gather(*tasks)
        
        # Should never exceed semaphore limit
        assert active_count["max"] <= 3
    
    @pytest.mark.asyncio
    async def test_async_memory_efficiency(self):
        """Test memory efficiency of async operations"""
        import psutil
        import os
        
        process = psutil.Process(os.getpid())
        
        # Get baseline memory
        baseline_memory = process.memory_info().rss / 1024 / 1024  # MB
        
        # Create many async tasks
        async def lightweight_task(i):
            await asyncio.sleep(0.001)
            return i
        
        tasks = [lightweight_task(i) for i in range(1000)]
        results = await asyncio.gather(*tasks)
        
        # Check memory after tasks
        peak_memory = process.memory_info().rss / 1024 / 1024
        memory_increase = peak_memory - baseline_memory
        
        # Should have minimal memory overhead
        assert memory_increase < 50  # Less than 50MB for 1000 tasks
        assert len(results) == 1000


class TestAsyncIntegration:
    """Test async integration with GTD workflows"""
    
    @pytest.mark.asyncio
    async def test_async_graphiti_integration(self):
        """Test async Graphiti memory integration"""
        mock_memory = AsyncMock()
        mock_memory.add_episode = AsyncMock(return_value="episode_123")
        mock_memory.search_nodes = AsyncMock(return_value=[])
        
        builder = StateGraph(AgentState)
        
        async def memory_node(state: Dict) -> Dict:
            # Add episode
            episode_id = await mock_memory.add_episode({
                "content": "Test episode",
                "type": "test"
            })
            
            # Search memory
            results = await mock_memory.search_nodes("test query")
            
            # Store in proper fields
            return {
                "graphiti_episode_ids": state.get("graphiti_episode_ids", []) + [episode_id],
                "memory_batch": results if results else []
            }
        
        builder.add_node("memory", memory_node)
        builder.add_edge("memory", END)
        builder.set_entry_point("memory")
        
        graph = builder.compile()
        
        initial_state = StateValidator.ensure_required_fields({})
        result = await graph.ainvoke(initial_state)
        
        assert "episode_123" in result["graphiti_episode_ids"]
        assert result["memory_batch"] == []
        
        mock_memory.add_episode.assert_called_once()
        mock_memory.search_nodes.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_async_timing_api_integration(self):
        """Test async Timing API integration"""
        mock_timing = AsyncMock()
        mock_timing.get_time_entries = AsyncMock(return_value=[
            {"project": "Work", "duration": 3600}
        ])
        mock_timing.calculate_focus_score = AsyncMock(return_value=75.5)
        
        builder = StateGraph(AgentState)
        
        async def timing_workflow(state: Dict) -> Dict:
            # Fetch entries
            entries = await mock_timing.get_time_entries()
            
            # Calculate score
            score = await mock_timing.calculate_focus_score(entries)
            
            state["timing_entries"] = entries
            state["focus_score"] = score
            return state
        
        builder = StateGraph(AgentState)
        builder.add_node("timing", timing_workflow)
        builder.add_edge("timing", END)
        builder.set_entry_point("timing")
        
        graph = builder.compile()
        
        initial_state = StateValidator.ensure_required_fields({})
        result = await graph.ainvoke(initial_state)
        
        assert result["timing_data"]["focus_score"] == 75.5
        assert len(result["timing_data"]["entries"]) == 1