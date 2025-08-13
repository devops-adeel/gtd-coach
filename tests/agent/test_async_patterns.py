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
            state["processed"] = True
            return state
        
        builder.add_node("async_node", async_node)
        builder.add_edge("async_node", END)
        builder.set_entry_point("async_node")
        
        graph = builder.compile()
        
        initial_state = StateValidator.ensure_required_fields({})
        result = await graph.ainvoke(initial_state)
        
        assert result["processed"] is True
    
    @pytest.mark.asyncio
    async def test_parallel_node_execution(self):
        """Test parallel execution of multiple nodes"""
        builder = StateGraph(AgentState)
        
        execution_order = []
        
        async def node_a(state: Dict) -> Dict:
            execution_order.append("a_start")
            await asyncio.sleep(0.02)
            execution_order.append("a_end")
            state["node_a_done"] = True
            return state
        
        async def node_b(state: Dict) -> Dict:
            execution_order.append("b_start")
            await asyncio.sleep(0.01)
            execution_order.append("b_end")
            state["node_b_done"] = True
            return state
        
        async def merge_node(state: Dict) -> Dict:
            execution_order.append("merge")
            state["merged"] = True
            return state
        
        builder.add_node("node_a", node_a)
        builder.add_node("node_b", node_b)
        builder.add_node("merge", merge_node)
        
        # Parallel execution using Send
        def router(state: Dict) -> List[Send]:
            return [
                Send("node_a", state),
                Send("node_b", state)
            ]
        
        builder.add_conditional_edges("__start__", router)
        builder.add_edge("node_a", "merge")
        builder.add_edge("node_b", "merge")
        builder.add_edge("merge", END)
        
        graph = builder.compile()
        
        initial_state = StateValidator.ensure_required_fields({})
        result = await graph.ainvoke(initial_state)
        
        # Verify parallel execution
        assert execution_order[0] in ["a_start", "b_start"]
        assert execution_order[1] in ["a_start", "b_start"]
        assert "b_end" in execution_order  # b should finish first (shorter sleep)
        assert execution_order[-1] == "merge"
        
        assert result["node_a_done"] is True
        assert result["node_b_done"] is True
        assert result["merged"] is True
    
    @pytest.mark.asyncio
    async def test_async_streaming(self):
        """Test async streaming of results"""
        builder = StateGraph(AgentState)
        
        async def streaming_node(state: Dict) -> AsyncIterator[Dict]:
            """Node that yields multiple updates"""
            for i in range(3):
                await asyncio.sleep(0.01)
                state[f"chunk_{i}"] = f"data_{i}"
                yield state
        
        builder.add_node("streamer", streaming_node)
        builder.add_edge("streamer", END)
        builder.set_entry_point("streamer")
        
        graph = builder.compile()
        
        initial_state = StateValidator.ensure_required_fields({})
        chunks = []
        
        async for chunk in graph.astream(initial_state):
            chunks.append(chunk)
        
        # Should receive multiple chunks
        assert len(chunks) >= 3
        
        # Final state should have all chunks
        final_state = chunks[-1]
        assert "chunk_0" in final_state
        assert "chunk_1" in final_state
        assert "chunk_2" in final_state
    
    @pytest.mark.asyncio
    async def test_async_with_checkpointing(self):
        """Test async execution with checkpointing"""
        checkpointer = MemorySaver()
        builder = StateGraph(AgentState)
        
        async def node_1(state: Dict) -> Dict:
            state["step_1"] = "completed"
            return state
        
        async def node_2(state: Dict) -> Dict:
            state["step_2"] = "completed"
            return state
        
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
        
        assert result["step_1"] == "completed"
        assert result["step_2"] == "completed"
        
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
            
            state["success"] = True
            return state
        
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
        
        assert result["success"] is True
        assert attempt_count["count"] == 3
    
    @pytest.mark.asyncio
    async def test_async_timeout_handling(self):
        """Test timeout handling in async workflows"""
        builder = StateGraph(AgentState)
        
        async def slow_node(state: Dict) -> Dict:
            await asyncio.sleep(5)  # Intentionally slow
            state["completed"] = True
            return state
        
        async def timeout_wrapper(state: Dict) -> Dict:
            try:
                result = await asyncio.wait_for(
                    slow_node(state),
                    timeout=0.1  # 100ms timeout
                )
                return result
            except asyncio.TimeoutError:
                state["timeout_occurred"] = True
                state["completed"] = False
                return state
        
        builder.add_node("timeout_node", timeout_wrapper)
        builder.add_edge("timeout_node", END)
        builder.set_entry_point("timeout_node")
        
        graph = builder.compile()
        
        initial_state = StateValidator.ensure_required_fields({})
        result = await graph.ainvoke(initial_state)
        
        assert result["timeout_occurred"] is True
        assert result["completed"] is False
    
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
        # Create mock async tool
        async_tool = AsyncMock()
        async_tool.name = "async_tool"
        async_tool.ainvoke = AsyncMock(return_value={"result": "success"})
        
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
        # Create multiple async tools
        tools = []
        for i in range(3):
            tool = AsyncMock()
            tool.name = f"tool_{i}"
            tool.ainvoke = AsyncMock(
                side_effect=lambda x, i=i: asyncio.sleep(0.01 * (3-i))
                .then(lambda: {"result": f"result_{i}"})
            )
            tools.append(tool)
        
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
        call_count = {"count": 0}
        
        async def flaky_tool_impl(args):
            call_count["count"] += 1
            if call_count["count"] < 3:
                raise ConnectionError("Network error")
            return {"success": True}
        
        tool = AsyncMock()
        tool.name = "flaky_tool"
        tool.ainvoke = AsyncMock(side_effect=flaky_tool_impl)
        
        # Wrap with retry logic
        async def retry_tool_invoke(args):
            for attempt in range(3):
                try:
                    return await tool.ainvoke(args)
                except ConnectionError:
                    if attempt == 2:
                        raise
                    await asyncio.sleep(0.01)
        
        tool.ainvoke = retry_tool_invoke
        
        # Execute tool
        result = await tool.ainvoke({})
        
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
            state["updates"] = state.get("updates", [])
            state["updates"].append("a")
            return state
        
        async def update_node_b(state: Dict) -> Dict:
            await asyncio.sleep(0.01)
            state["updates"] = state.get("updates", [])
            state["updates"].append("b")
            return state
        
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
        assert result["updates"] == ["a", "b"]
    
    @pytest.mark.asyncio
    async def test_async_state_reducers(self):
        """Test async state reducers"""
        from typing import Annotated
        from operator import add
        
        # Define state with reducer
        class ReducerState(AgentState):
            items: Annotated[List[str], add]
        
        builder = StateGraph(ReducerState)
        
        async def add_items_node(state: Dict) -> Dict:
            return {"items": ["item1", "item2"]}
        
        async def add_more_items_node(state: Dict) -> Dict:
            return {"items": ["item3"]}
        
        builder.add_node("add_items", add_items_node)
        builder.add_node("add_more", add_more_items_node)
        builder.add_edge("add_items", "add_more")
        builder.add_edge("add_more", END)
        builder.set_entry_point("add_items")
        
        graph = builder.compile()
        
        initial_state = {"items": ["item0"]}
        result = await graph.ainvoke(initial_state)
        
        # Reducer should combine all items
        assert len(result["items"]) == 4
        assert "item0" in result["items"]
        assert "item3" in result["items"]
    
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
            
            state["validated"] = True
            return state
        
        builder.add_node("validator", validate_state)
        builder.add_edge("validator", END)
        builder.set_entry_point("validator")
        
        graph = builder.compile()
        
        # Valid state
        valid_state = StateValidator.ensure_required_fields({})
        result = await graph.ainvoke(valid_state)
        assert result["validated"] is True
        
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
            
            state["episode_id"] = episode_id
            state["search_results"] = results
            return state
        
        builder.add_node("memory", memory_node)
        builder.add_edge("memory", END)
        builder.set_entry_point("memory")
        
        graph = builder.compile()
        
        initial_state = StateValidator.ensure_required_fields({})
        result = await graph.ainvoke(initial_state)
        
        assert result["episode_id"] == "episode_123"
        assert result["search_results"] == []
        
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
        
        assert result["focus_score"] == 75.5
        assert len(result["timing_entries"]) == 1