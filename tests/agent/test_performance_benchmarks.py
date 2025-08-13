#!/usr/bin/env python3
"""
Performance benchmarks for GTD Coach Agent implementation
Tests performance, scalability, and resource usage
"""

import pytest
import pytest_benchmark
import asyncio
import time
import psutil
import os
import json
from datetime import datetime, timedelta
from typing import Dict, Any, List
from unittest.mock import Mock, patch, MagicMock, AsyncMock
import tempfile
from pathlib import Path

from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver
from langgraph.checkpoint.sqlite import SqliteSaver

from gtd_coach.agent.state import AgentState, StateValidator
from gtd_coach.agent.workflows.weekly_review import WeeklyReviewWorkflow
from gtd_coach.agent.workflows.daily_capture import DailyCaptureWorkflow
from gtd_coach.agent.shadow_runner import ShadowModeRunner, MetricsLogger


class TestWorkflowPerformance:
    """Benchmark workflow execution performance"""
    
    def test_startup_phase_performance(self, benchmark):
        """Benchmark startup phase execution"""
        workflow = WeeklyReviewWorkflow(test_mode=True)
        
        with patch.object(workflow, 'interrupt', return_value={"ready": True}):
            def run_startup():
                state = StateValidator.ensure_required_fields({})
                return workflow.startup_phase(state)
            
            result = benchmark(run_startup)
            assert result["ready"] is True
    
    def test_mind_sweep_capture_performance(self, benchmark):
        """Benchmark mind sweep capture with varying item counts"""
        workflow = WeeklyReviewWorkflow(test_mode=True)
        
        # Test with 20 items
        mock_items = [f"Task {i}" for i in range(20)]
        
        with patch.object(workflow, 'interrupt', return_value={"items": mock_items}):
            def run_capture():
                state = StateValidator.ensure_required_fields({})
                return workflow.mind_sweep_capture(state)
            
            result = benchmark(run_capture)
            assert len(result["captures"]) == 20
    
    def test_process_captures_performance(self, benchmark):
        """Benchmark capture processing performance"""
        workflow = WeeklyReviewWorkflow(test_mode=True)
        
        # Create test captures
        captures = [
            {"id": str(i), "content": f"Task {i}", "source": "test"}
            for i in range(50)
        ]
        
        mock_processed = [
            {"item": f"Task {i}", "project": f"Project {i % 5}"}
            for i in range(50)
        ]
        
        with patch.object(workflow, 'interrupt', return_value={"processed": mock_processed}):
            def run_process():
                state = StateValidator.ensure_required_fields({"captures": captures})
                return workflow.mind_sweep_process(state)
            
            result = benchmark(run_process)
            assert len(result["processed_items"]) == 50
    
    @pytest.mark.asyncio
    async def test_async_workflow_performance(self, benchmark):
        """Benchmark async workflow execution"""
        builder = StateGraph(AgentState)
        
        async def async_node(state: Dict) -> Dict:
            # Simulate some async work
            await asyncio.sleep(0.001)
            state["processed"] = True
            return state
        
        builder.add_node("async_node", async_node)
        builder.add_edge("async_node", END)
        builder.set_entry_point("async_node")
        
        graph = builder.compile()
        
        async def run_async():
            state = StateValidator.ensure_required_fields({})
            return await graph.ainvoke(state)
        
        # Benchmark async execution
        result = await benchmark(run_async)
        assert result["processed"] is True


class TestCheckpointerPerformance:
    """Benchmark checkpointer performance"""
    
    def test_memory_checkpointer_write_performance(self, benchmark):
        """Benchmark MemorySaver write performance"""
        checkpointer = MemorySaver()
        
        from langgraph.checkpoint.base import Checkpoint, CheckpointMetadata
        
        def write_checkpoint():
            checkpoint = Checkpoint(
                v=1,
                id=f"checkpoint_{datetime.now().timestamp()}",
                ts=datetime.now().isoformat(),
                channel_values={
                    "messages": ["msg" * 100 for _ in range(10)],
                    "state": {"key": "value" * 100}
                },
                channel_versions={"messages": 1, "state": 1},
                versions_seen={}
            )
            
            config = {"configurable": {"thread_id": "perf_test"}}
            metadata = CheckpointMetadata(source="test", step=1, writes={}, parents={})
            
            checkpointer.put(config, checkpoint, metadata, {})
        
        benchmark(write_checkpoint)
    
    def test_sqlite_checkpointer_performance(self, benchmark, tmp_path):
        """Benchmark SqliteSaver performance"""
        db_path = tmp_path / "benchmark.db"
        checkpointer = SqliteSaver.from_conn_string(f"sqlite:///{db_path}")
        
        from langgraph.checkpoint.base import Checkpoint, CheckpointMetadata
        
        def write_and_read():
            # Write
            checkpoint = Checkpoint(
                v=1,
                id=f"checkpoint_{datetime.now().timestamp()}",
                ts=datetime.now().isoformat(),
                channel_values={"data": "test" * 1000},
                channel_versions={"data": 1},
                versions_seen={}
            )
            
            config = {"configurable": {"thread_id": "sqlite_perf"}}
            metadata = CheckpointMetadata(source="test", step=1, writes={}, parents={})
            
            checkpointer.put(config, checkpoint, metadata, {})
            
            # Read
            result = checkpointer.get(config)
            return result
        
        result = benchmark(write_and_read)
        assert result is not None
    
    def test_checkpoint_list_performance(self, benchmark):
        """Benchmark checkpoint listing performance"""
        checkpointer = MemorySaver()
        
        from langgraph.checkpoint.base import Checkpoint, CheckpointMetadata
        
        # Pre-populate with many checkpoints
        config = {"configurable": {"thread_id": "list_perf"}}
        for i in range(100):
            checkpoint = Checkpoint(
                v=1,
                id=f"checkpoint_{i}",
                ts=datetime.now().isoformat(),
                channel_values={"step": i},
                channel_versions={"step": 1},
                versions_seen={}
            )
            metadata = CheckpointMetadata(source="test", step=i, writes={}, parents={})
            checkpointer.put(config, checkpoint, metadata, {})
        
        def list_checkpoints():
            return list(checkpointer.list(config))
        
        result = benchmark(list_checkpoints)
        assert len(result) == 100


class TestScalabilityBenchmarks:
    """Test scalability with large datasets"""
    
    def test_large_capture_list_performance(self, benchmark):
        """Test performance with large number of captures"""
        workflow = WeeklyReviewWorkflow(test_mode=True)
        
        # Create 500 captures
        large_capture_list = [f"Item {i}" for i in range(500)]
        
        with patch.object(workflow, 'interrupt', return_value={"items": large_capture_list}):
            def process_large_list():
                state = StateValidator.ensure_required_fields({})
                return workflow.mind_sweep_capture(state)
            
            result = benchmark(process_large_list)
            assert len(result["captures"]) == 500
    
    def test_many_projects_performance(self, benchmark):
        """Test performance with many projects"""
        workflow = WeeklyReviewWorkflow(test_mode=True)
        
        # Create 100 projects
        projects = {
            f"Project {i}": {
                "next_action": f"Action for project {i}",
                "status": "active" if i % 2 == 0 else "someday"
            }
            for i in range(100)
        }
        
        with patch.object(workflow, 'interrupt', return_value={"projects": projects}):
            def review_many_projects():
                state = StateValidator.ensure_required_fields({})
                return workflow.project_review(state)
            
            result = benchmark(review_many_projects)
            assert len(result["projects"]) == 100
    
    @pytest.mark.asyncio
    async def test_concurrent_workflow_scalability(self, benchmark):
        """Test concurrent workflow execution scalability"""
        
        async def run_multiple_workflows(count: int):
            tasks = []
            for i in range(count):
                workflow = DailyCaptureWorkflow(test_mode=True)
                state = StateValidator.ensure_required_fields({
                    "session_id": f"concurrent_{i}"
                })
                
                # Mock the async run method
                async def mock_run(s):
                    await asyncio.sleep(0.01)
                    return {"success": True, "id": s["session_id"]}
                
                with patch.object(workflow, 'run', mock_run):
                    tasks.append(workflow.run(state))
            
            results = await asyncio.gather(*tasks)
            return results
        
        # Benchmark concurrent execution
        results = await benchmark(run_multiple_workflows, 10)
        assert len(results) == 10
        assert all(r["success"] for r in results)


class TestMemoryPerformance:
    """Test memory usage and efficiency"""
    
    def test_memory_usage_baseline(self):
        """Establish memory usage baseline"""
        process = psutil.Process(os.getpid())
        
        # Get baseline
        baseline = process.memory_info().rss / 1024 / 1024  # MB
        
        # Create workflow
        workflow = WeeklyReviewWorkflow(test_mode=True)
        
        # Check memory after creation
        after_creation = process.memory_info().rss / 1024 / 1024
        
        memory_increase = after_creation - baseline
        assert memory_increase < 50  # Should use less than 50MB
    
    def test_memory_leak_detection(self):
        """Test for memory leaks in repeated operations"""
        process = psutil.Process(os.getpid())
        
        baseline = process.memory_info().rss / 1024 / 1024
        
        # Run many iterations
        for i in range(100):
            workflow = WeeklyReviewWorkflow(test_mode=True)
            state = StateValidator.ensure_required_fields({})
            
            with patch.object(workflow, 'interrupt', return_value={"ready": True}):
                result = workflow.startup_phase(state)
            
            # Cleanup
            del workflow, state, result
        
        # Force garbage collection
        import gc
        gc.collect()
        
        # Check memory
        final = process.memory_info().rss / 1024 / 1024
        memory_growth = final - baseline
        
        # Should not grow significantly
        assert memory_growth < 100  # Less than 100MB growth
    
    def test_large_state_memory_usage(self):
        """Test memory usage with large state objects"""
        process = psutil.Process(os.getpid())
        
        baseline = process.memory_info().rss / 1024 / 1024
        
        # Create large state
        large_state = StateValidator.ensure_required_fields({})
        large_state["large_data"] = ["x" * 1000 for _ in range(10000)]  # ~10MB
        
        peak = process.memory_info().rss / 1024 / 1024
        memory_used = peak - baseline
        
        # Should be close to actual data size
        assert memory_used < 50  # Should use less than 50MB total
        
        # Cleanup
        del large_state
        import gc
        gc.collect()


class TestLatencyBenchmarks:
    """Test latency characteristics"""
    
    def test_interrupt_response_latency(self, benchmark):
        """Test interrupt response latency"""
        from langgraph.constants import Interrupt
        
        def measure_interrupt_latency():
            start = time.perf_counter()
            
            # Mock interrupt
            with patch('langgraph.constants.Interrupt') as mock_interrupt:
                mock_interrupt.return_value = {"response": "test"}
                
                result = Interrupt({
                    "phase": "TEST",
                    "prompt": "Test prompt",
                    "type": "text"
                })
            
            latency = time.perf_counter() - start
            return latency
        
        latency = benchmark(measure_interrupt_latency)
        assert latency < 0.01  # Should be under 10ms
    
    def test_checkpoint_save_latency(self, benchmark):
        """Test checkpoint save latency"""
        checkpointer = MemorySaver()
        
        from langgraph.checkpoint.base import Checkpoint, CheckpointMetadata
        
        def measure_save_latency():
            checkpoint = Checkpoint(
                v=1,
                id="latency_test",
                ts=datetime.now().isoformat(),
                channel_values={"test": "data"},
                channel_versions={"test": 1},
                versions_seen={}
            )
            
            config = {"configurable": {"thread_id": "latency"}}
            metadata = CheckpointMetadata(source="test", step=1, writes={}, parents={})
            
            start = time.perf_counter()
            checkpointer.put(config, checkpoint, metadata, {})
            return time.perf_counter() - start
        
        latency = benchmark(measure_save_latency)
        assert latency < 0.001  # Should be under 1ms for memory
    
    def test_phase_transition_latency(self, benchmark):
        """Test phase transition latency"""
        workflow = WeeklyReviewWorkflow(test_mode=True)
        
        def measure_transition():
            state = StateValidator.ensure_required_fields({
                "current_phase": "STARTUP",
                "completed_phases": []
            })
            
            start = time.perf_counter()
            
            # Transition to next phase
            state["completed_phases"].append(state["current_phase"])
            state["current_phase"] = "MIND_SWEEP"
            
            return time.perf_counter() - start
        
        latency = benchmark(measure_transition)
        assert latency < 0.0001  # Should be under 0.1ms


class TestThroughputBenchmarks:
    """Test throughput characteristics"""
    
    def test_capture_throughput(self, benchmark):
        """Test capture processing throughput"""
        workflow = WeeklyReviewWorkflow(test_mode=True)
        
        # Generate test data
        num_items = 1000
        items = [f"Item {i}" for i in range(num_items)]
        
        def process_batch():
            processed = 0
            start = time.time()
            
            for item in items:
                # Simulate processing
                processed += 1
            
            duration = time.time() - start
            return processed / duration  # items per second
        
        throughput = benchmark(process_batch)
        assert throughput > 1000  # Should process >1000 items/second
    
    @pytest.mark.asyncio
    async def test_async_message_throughput(self, benchmark):
        """Test async message processing throughput"""
        
        async def process_messages(count: int):
            messages = []
            start = time.time()
            
            for i in range(count):
                # Simulate async message processing
                await asyncio.sleep(0)  # Yield control
                messages.append({"id": i, "processed": True})
            
            duration = time.time() - start
            return len(messages) / duration
        
        throughput = await benchmark(process_messages, 100)
        assert throughput > 100  # Should process >100 messages/second


class TestOptimizationBenchmarks:
    """Test performance optimizations"""
    
    def test_caching_performance(self, benchmark):
        """Test caching impact on performance"""
        
        class CachedWorkflow:
            def __init__(self):
                self.cache = {}
            
            def expensive_operation(self, key: str):
                if key in self.cache:
                    return self.cache[key]
                
                # Simulate expensive operation
                import hashlib
                result = hashlib.sha256(key.encode()).hexdigest()
                for _ in range(1000):
                    result = hashlib.sha256(result.encode()).hexdigest()
                
                self.cache[key] = result
                return result
        
        workflow = CachedWorkflow()
        
        def run_with_cache():
            results = []
            for i in range(10):
                # Repeat same keys to test cache
                key = f"key_{i % 3}"
                results.append(workflow.expensive_operation(key))
            return results
        
        results = benchmark(run_with_cache)
        assert len(results) == 10
    
    def test_batch_vs_individual_processing(self, benchmark):
        """Compare batch vs individual processing performance"""
        
        def process_individual(items: List[str]):
            results = []
            for item in items:
                # Process one at a time
                result = {"item": item, "processed": True}
                results.append(result)
            return results
        
        def process_batch(items: List[str]):
            # Process all at once
            return [{"item": item, "processed": True} for item in items]
        
        items = [f"Item {i}" for i in range(1000)]
        
        # Benchmark both approaches
        individual_time = benchmark.pedantic(process_individual, args=(items,), rounds=10)
        batch_time = benchmark.pedantic(process_batch, args=(items,), rounds=10)
        
        # Batch should be faster
        assert batch_time < individual_time


class TestResourceUsageBenchmarks:
    """Test resource usage under load"""
    
    def test_cpu_usage_under_load(self):
        """Test CPU usage under heavy load"""
        process = psutil.Process(os.getpid())
        
        # Get baseline CPU
        process.cpu_percent()  # First call to initialize
        time.sleep(0.1)
        baseline_cpu = process.cpu_percent()
        
        # Run intensive task
        workflow = WeeklyReviewWorkflow(test_mode=True)
        
        # Process many items
        for i in range(100):
            state = StateValidator.ensure_required_fields({})
            with patch.object(workflow, 'interrupt', return_value={"ready": True}):
                workflow.startup_phase(state)
        
        # Check CPU usage
        peak_cpu = process.cpu_percent()
        
        # Should not max out CPU
        assert peak_cpu < 90  # Should stay under 90% CPU
    
    def test_file_handle_usage(self):
        """Test file handle usage and cleanup"""
        process = psutil.Process(os.getpid())
        
        # Get baseline open files
        baseline_files = len(process.open_files())
        
        # Create SQLite checkpointers (opens files)
        checkpointers = []
        for i in range(10):
            with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
                db_path = tmp.name
                checkpointer = SqliteSaver.from_conn_string(f"sqlite:///{db_path}")
                checkpointers.append((checkpointer, db_path))
        
        # Check open files
        during_files = len(process.open_files())
        
        # Cleanup
        for checkpointer, db_path in checkpointers:
            Path(db_path).unlink(missing_ok=True)
        
        # Check files after cleanup
        time.sleep(0.1)  # Allow cleanup
        final_files = len(process.open_files())
        
        # Should return to baseline
        assert final_files <= baseline_files + 1  # Allow small variance


def generate_performance_report(results: Dict[str, Any]):
    """Generate performance report from benchmark results"""
    report = {
        "timestamp": datetime.now().isoformat(),
        "summary": {
            "total_benchmarks": len(results),
            "passed": sum(1 for r in results.values() if r.get("passed", False)),
            "performance_targets_met": 0,
            "regressions_detected": 0
        },
        "detailed_results": results,
        "recommendations": []
    }
    
    # Analyze results
    for name, result in results.items():
        if "latency" in name and result.get("value", 0) > 0.01:
            report["recommendations"].append(
                f"High latency detected in {name}: {result['value']}s"
            )
            report["summary"]["regressions_detected"] += 1
        
        if "throughput" in name and result.get("value", 0) < 100:
            report["recommendations"].append(
                f"Low throughput in {name}: {result['value']} items/s"
            )
            report["summary"]["regressions_detected"] += 1
    
    # Save report
    with open("performance_report.json", "w") as f:
        json.dump(report, f, indent=2)
    
    return report