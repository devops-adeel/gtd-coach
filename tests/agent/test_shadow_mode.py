#!/usr/bin/env python3
"""
Comprehensive tests for shadow mode implementation
Tests A/B testing, metrics collection, and decision comparison
"""

import pytest
import asyncio
import json
from datetime import datetime, timedelta
from typing import Dict, Any, List
from unittest.mock import Mock, patch, MagicMock, AsyncMock
import tempfile
from pathlib import Path

from gtd_coach.agent.shadow_runner import ShadowModeRunner, MetricsLogger
from gtd_coach.agent.state import AgentState, StateValidator
from gtd_coach.agent.workflows.weekly_review import WeeklyReviewWorkflow
from gtd_coach.agent.workflows.daily_capture import DailyCaptureWorkflow


class TestMetricsLogger:
    """Test metrics logging functionality"""
    
    @pytest.fixture
    def temp_metrics_file(self):
        """Create temporary metrics file"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            temp_path = f.name
        yield temp_path
        Path(temp_path).unlink(missing_ok=True)
    
    def test_metrics_logger_initialization(self, temp_metrics_file):
        """Test MetricsLogger initialization"""
        logger = MetricsLogger(log_file=temp_metrics_file)
        
        assert logger.log_file == temp_metrics_file
        assert logger.metrics == []
        assert logger.session_id is not None
    
    def test_log_decision_point(self, temp_metrics_file):
        """Test logging decision points"""
        logger = MetricsLogger(log_file=temp_metrics_file)
        
        # Log a decision point
        logger.log_decision_point(
            phase="MIND_SWEEP",
            legacy_decision="capture_all",
            agent_decision="selective_capture",
            context={"item_count": 5}
        )
        
        assert len(logger.metrics) == 1
        metric = logger.metrics[0]
        
        assert metric["phase"] == "MIND_SWEEP"
        assert metric["legacy_decision"] == "capture_all"
        assert metric["agent_decision"] == "selective_capture"
        assert metric["context"]["item_count"] == 5
        assert "timestamp" in metric
    
    def test_log_performance_metric(self, temp_metrics_file):
        """Test logging performance metrics"""
        logger = MetricsLogger(log_file=temp_metrics_file)
        
        logger.log_performance_metric(
            phase="PROJECT_REVIEW",
            legacy_duration=45.2,
            agent_duration=32.1,
            metric_type="phase_completion"
        )
        
        assert len(logger.metrics) == 1
        metric = logger.metrics[0]
        
        assert metric["metric_type"] == "performance"
        assert metric["legacy_duration"] == 45.2
        assert metric["agent_duration"] == 32.1
        assert metric["improvement_percent"] == pytest.approx(29.0, rel=1)
    
    def test_save_metrics(self, temp_metrics_file):
        """Test saving metrics to file"""
        logger = MetricsLogger(log_file=temp_metrics_file)
        
        # Add multiple metrics
        logger.log_decision_point("STARTUP", "standard", "optimized", {})
        logger.log_performance_metric("STARTUP", 2.5, 1.8, "init")
        
        # Save to file
        logger.save()
        
        # Load and verify
        with open(temp_metrics_file) as f:
            saved_data = json.load(f)
        
        assert saved_data["session_id"] == logger.session_id
        assert len(saved_data["metrics"]) == 2
        assert "summary" in saved_data
    
    def test_generate_summary(self, temp_metrics_file):
        """Test summary generation"""
        logger = MetricsLogger(log_file=temp_metrics_file)
        
        # Add varied metrics
        logger.log_performance_metric("PHASE1", 10, 8, "test")
        logger.log_performance_metric("PHASE2", 20, 25, "test")  # Regression
        logger.log_decision_point("PHASE1", "A", "B", {})
        logger.log_decision_point("PHASE2", "X", "X", {})  # Agreement
        
        summary = logger.generate_summary()
        
        assert summary["total_metrics"] == 4
        assert summary["performance_metrics"] == 2
        assert summary["decision_points"] == 2
        assert summary["average_improvement"] == pytest.approx(-2.5, rel=1)
        assert summary["decision_agreement_rate"] == 50.0


class TestShadowModeRunner:
    """Test shadow mode runner functionality"""
    
    @pytest.fixture
    def mock_legacy_workflow(self):
        """Mock legacy workflow"""
        workflow = MagicMock()
        workflow.run = MagicMock(return_value={
            "success": True,
            "captures": ["task1", "task2"],
            "duration": 30.5
        })
        return workflow
    
    @pytest.fixture
    def mock_agent_workflow(self):
        """Mock agent workflow"""
        workflow = AsyncMock()
        workflow.run = AsyncMock(return_value={
            "success": True,
            "captures": ["task1", "task2", "task3"],
            "duration": 25.2
        })
        return workflow
    
    def test_shadow_runner_initialization(self):
        """Test ShadowModeRunner initialization"""
        runner = ShadowModeRunner()
        
        assert runner.metrics_logger is not None
        assert runner.comparison_tasks == []
        assert runner.is_running is False
    
    @pytest.mark.asyncio
    async def test_run_shadow_comparison(self, mock_legacy_workflow, mock_agent_workflow):
        """Test running shadow comparison"""
        runner = ShadowModeRunner()
        
        # Run shadow comparison
        await runner.run_shadow_comparison(
            legacy_workflow=mock_legacy_workflow,
            agent_workflow=mock_agent_workflow,
            state={"test": "state"}
        )
        
        # Wait for async task to complete
        await asyncio.sleep(0.1)
        
        # Verify both workflows were called
        mock_legacy_workflow.run.assert_called_once()
        mock_agent_workflow.run.assert_called_once()
        
        # Check metrics were logged
        assert len(runner.metrics_logger.metrics) > 0
    
    def test_compare_results(self):
        """Test result comparison logic"""
        runner = ShadowModeRunner()
        
        legacy_result = {
            "captures": ["task1", "task2"],
            "priorities": {"A": ["task1"], "B": ["task2"], "C": []},
            "duration": 30
        }
        
        agent_result = {
            "captures": ["task1", "task2", "task3"],
            "priorities": {"A": ["task1", "task3"], "B": ["task2"], "C": []},
            "duration": 25
        }
        
        differences = runner.compare_results(legacy_result, agent_result)
        
        assert "captures" in differences
        assert differences["captures"]["legacy_count"] == 2
        assert differences["captures"]["agent_count"] == 3
        
        assert "priorities" in differences
        assert differences["priorities"]["different_a_items"] is True
        
        assert "performance" in differences
        assert differences["performance"]["improvement_percent"] > 0
    
    def test_should_notify_divergence(self):
        """Test divergence notification logic"""
        runner = ShadowModeRunner()
        
        # Minor differences - no notification
        minor_differences = {
            "captures": {"legacy_count": 10, "agent_count": 11},
            "performance": {"improvement_percent": 5}
        }
        assert runner.should_notify_divergence(minor_differences) is False
        
        # Major differences - should notify
        major_differences = {
            "captures": {"legacy_count": 10, "agent_count": 20},
            "priorities": {"different_a_items": True, "priority_mismatch": 5},
            "performance": {"improvement_percent": -30}  # Regression
        }
        assert runner.should_notify_divergence(major_differences) is True
    
    @pytest.mark.asyncio
    async def test_concurrent_shadow_runs(self):
        """Test handling multiple concurrent shadow runs"""
        runner = ShadowModeRunner()
        
        # Create multiple mock workflows
        workflows = []
        for i in range(3):
            mock_workflow = AsyncMock()
            mock_workflow.run = AsyncMock(return_value={
                "success": True,
                "id": f"workflow_{i}",
                "duration": 10 + i
            })
            workflows.append(mock_workflow)
        
        # Start multiple shadow comparisons
        tasks = []
        for i, workflow in enumerate(workflows):
            task = runner.run_shadow_comparison(
                legacy_workflow=MagicMock(),
                agent_workflow=workflow,
                state={"session": f"session_{i}"}
            )
            tasks.append(task)
        
        # Wait for all to complete
        await asyncio.gather(*tasks)
        
        # Verify all ran
        for workflow in workflows:
            workflow.run.assert_called_once()


class TestDecisionTracking:
    """Test decision point tracking and analysis"""
    
    def test_track_routing_decision(self):
        """Test tracking routing decisions"""
        logger = MetricsLogger()
        
        # Track a routing decision
        legacy_route = "process_all"
        agent_route = "selective_process"
        
        logger.log_decision_point(
            phase="MIND_SWEEP_PROCESS",
            legacy_decision=legacy_route,
            agent_decision=agent_route,
            context={
                "item_count": 15,
                "adhd_severity": "high"
            }
        )
        
        # Verify tracking
        decision = logger.metrics[-1]
        assert decision["phase"] == "MIND_SWEEP_PROCESS"
        assert decision["legacy_decision"] != decision["agent_decision"]
        assert decision["context"]["adhd_severity"] == "high"
    
    def test_track_tool_selection(self):
        """Test tracking tool selection differences"""
        logger = MetricsLogger()
        
        legacy_tools = ["capture_all", "process_basic"]
        agent_tools = ["capture_smart", "process_gtd", "detect_patterns"]
        
        logger.log_decision_point(
            phase="TOOL_SELECTION",
            legacy_decision=legacy_tools,
            agent_decision=agent_tools,
            context={"workflow": "daily_capture"}
        )
        
        decision = logger.metrics[-1]
        assert len(decision["agent_decision"]) > len(decision["legacy_decision"])
    
    def test_analyze_decision_patterns(self):
        """Test analyzing patterns in decisions"""
        logger = MetricsLogger()
        
        # Add multiple decisions
        for i in range(10):
            logger.log_decision_point(
                phase=f"PHASE_{i % 3}",
                legacy_decision="standard",
                agent_decision="optimized" if i % 2 == 0 else "standard",
                context={"iteration": i}
            )
        
        # Analyze patterns
        summary = logger.generate_summary()
        assert summary["decision_agreement_rate"] == 50.0
        
        # Check phase-specific patterns
        phase_decisions = [m for m in logger.metrics if m["phase"] == "PHASE_0"]
        assert len(phase_decisions) == 4  # 0, 3, 6, 9


class TestPerformanceComparison:
    """Test performance comparison between legacy and agent"""
    
    @pytest.mark.asyncio
    async def test_measure_phase_performance(self):
        """Test measuring performance of individual phases"""
        runner = ShadowModeRunner()
        
        # Mock phase execution
        async def mock_legacy_phase():
            await asyncio.sleep(0.05)  # 50ms
            return {"result": "legacy"}
        
        async def mock_agent_phase():
            await asyncio.sleep(0.03)  # 30ms
            return {"result": "agent"}
        
        # Measure both
        import time
        
        start = time.time()
        legacy_result = await mock_legacy_phase()
        legacy_time = time.time() - start
        
        start = time.time()
        agent_result = await mock_agent_phase()
        agent_time = time.time() - start
        
        # Log performance
        runner.metrics_logger.log_performance_metric(
            phase="TEST_PHASE",
            legacy_duration=legacy_time,
            agent_duration=agent_time,
            metric_type="phase_execution"
        )
        
        # Verify improvement
        metric = runner.metrics_logger.metrics[-1]
        assert metric["improvement_percent"] > 0
    
    def test_memory_usage_comparison(self):
        """Test comparing memory usage between implementations"""
        import psutil
        import os
        
        runner = ShadowModeRunner()
        process = psutil.Process(os.getpid())
        
        # Get baseline memory
        baseline_memory = process.memory_info().rss / 1024 / 1024  # MB
        
        # Simulate legacy workflow (memory intensive)
        legacy_data = ["item" * 1000 for _ in range(1000)]  # Large data
        legacy_memory = process.memory_info().rss / 1024 / 1024
        
        # Simulate agent workflow (optimized)
        agent_data = ["item" for _ in range(100)]  # Smaller footprint
        agent_memory = process.memory_info().rss / 1024 / 1024
        
        # Log memory comparison
        runner.metrics_logger.log_performance_metric(
            phase="MEMORY_USAGE",
            legacy_duration=legacy_memory - baseline_memory,
            agent_duration=agent_memory - baseline_memory,
            metric_type="memory_mb"
        )
        
        # Clean up
        del legacy_data, agent_data
    
    def test_throughput_comparison(self):
        """Test comparing throughput between implementations"""
        runner = ShadowModeRunner()
        
        # Simulate processing rates
        legacy_items_processed = 50
        legacy_time = 10.0  # seconds
        
        agent_items_processed = 50
        agent_time = 7.5  # seconds
        
        # Calculate throughput
        legacy_throughput = legacy_items_processed / legacy_time
        agent_throughput = agent_items_processed / agent_time
        
        runner.metrics_logger.log_performance_metric(
            phase="THROUGHPUT",
            legacy_duration=legacy_throughput,
            agent_duration=agent_throughput,
            metric_type="items_per_second"
        )
        
        metric = runner.metrics_logger.metrics[-1]
        assert metric["agent_duration"] > metric["legacy_duration"]


class TestShadowModeIntegration:
    """Test shadow mode integration with actual workflows"""
    
    @pytest.mark.asyncio
    async def test_weekly_review_shadow_mode(self):
        """Test shadow mode with weekly review workflow"""
        # Create workflows
        legacy_workflow = MagicMock()
        legacy_workflow.run = MagicMock(return_value={
            "success": True,
            "phases_completed": ["STARTUP", "MIND_SWEEP", "PROJECT_REVIEW"],
            "duration": 1800  # 30 minutes
        })
        
        agent_workflow = WeeklyReviewWorkflow(test_mode=True)
        
        # Mock agent workflow methods
        with patch.object(agent_workflow, 'run_full_review') as mock_run:
            mock_run.return_value = {
                "success": True,
                "phases_completed": ["STARTUP", "MIND_SWEEP", "PROJECT_REVIEW", "PRIORITIZATION", "WRAP_UP"],
                "duration": 1500  # 25 minutes
            }
            
            # Run shadow comparison
            runner = ShadowModeRunner()
            await runner.run_shadow_comparison(
                legacy_workflow=legacy_workflow,
                agent_workflow=agent_workflow,
                state=StateValidator.ensure_required_fields({})
            )
            
            # Verify metrics collected
            assert len(runner.metrics_logger.metrics) > 0
    
    @pytest.mark.asyncio
    async def test_daily_capture_shadow_mode(self):
        """Test shadow mode with daily capture workflow"""
        runner = ShadowModeRunner()
        
        # Create state with test data
        state = StateValidator.ensure_required_fields({
            "timing_entries": [
                {"project": "Email", "duration": 30},
                {"project": "Coding", "duration": 120}
            ],
            "focus_score": 65
        })
        
        # Mock workflows
        legacy_workflow = MagicMock()
        legacy_workflow.run = MagicMock(return_value={
            "captures": ["task1", "task2"],
            "processed": 2,
            "duration": 5.0
        })
        
        agent_workflow = DailyCaptureWorkflow(test_mode=True)
        
        with patch.object(agent_workflow, 'run') as mock_run:
            mock_run.return_value = {
                "captures": ["task1", "task2", "task3"],
                "processed": 3,
                "patterns_detected": ["context_switching"],
                "duration": 4.2
            }
            
            await runner.run_shadow_comparison(
                legacy_workflow=legacy_workflow,
                agent_workflow=agent_workflow,
                state=state
            )
            
            # Check for performance improvement
            perf_metrics = [m for m in runner.metrics_logger.metrics 
                           if m.get("metric_type") == "performance"]
            if perf_metrics:
                assert perf_metrics[0]["improvement_percent"] > 0
    
    def test_shadow_mode_error_handling(self):
        """Test shadow mode handles errors gracefully"""
        runner = ShadowModeRunner()
        
        # Create workflow that raises error
        error_workflow = MagicMock()
        error_workflow.run = MagicMock(side_effect=RuntimeError("Test error"))
        
        # Normal workflow
        normal_workflow = MagicMock()
        normal_workflow.run = MagicMock(return_value={"success": True})
        
        # Should handle error without crashing
        asyncio.run(runner.run_shadow_comparison(
            legacy_workflow=error_workflow,
            agent_workflow=normal_workflow,
            state={}
        ))
        
        # Should log error in metrics
        error_metrics = [m for m in runner.metrics_logger.metrics 
                        if m.get("error") is not None]
        assert len(error_metrics) > 0


class TestShadowModeReporting:
    """Test shadow mode reporting and analysis"""
    
    def test_generate_comparison_report(self):
        """Test generating detailed comparison report"""
        logger = MetricsLogger()
        
        # Add variety of metrics
        logger.log_performance_metric("STARTUP", 2.0, 1.5, "init")
        logger.log_performance_metric("CAPTURE", 10.0, 8.0, "capture")
        logger.log_decision_point("ROUTING", "path_a", "path_b", {"reason": "optimization"})
        logger.log_decision_point("PROCESSING", "batch", "stream", {"items": 100})
        
        # Generate report
        report = logger.generate_detailed_report()
        
        assert "performance_analysis" in report
        assert "decision_analysis" in report
        assert "recommendations" in report
        
        # Check performance analysis
        perf = report["performance_analysis"]
        assert perf["total_legacy_time"] == 12.0
        assert perf["total_agent_time"] == 9.5
        assert perf["overall_improvement"] > 0
        
        # Check decision analysis  
        decisions = report["decision_analysis"]
        assert decisions["total_decisions"] == 2
        assert decisions["agreement_rate"] == 0.0
    
    def test_identify_regression_areas(self):
        """Test identifying performance regressions"""
        logger = MetricsLogger()
        
        # Add metrics with some regressions
        logger.log_performance_metric("PHASE1", 5.0, 4.0, "good")  # Improvement
        logger.log_performance_metric("PHASE2", 3.0, 4.5, "regression")  # Regression
        logger.log_performance_metric("PHASE3", 10.0, 12.0, "regression")  # Regression
        
        regressions = logger.identify_regressions()
        
        assert len(regressions) == 2
        assert "PHASE2" in [r["phase"] for r in regressions]
        assert "PHASE3" in [r["phase"] for r in regressions]
    
    def test_export_metrics_for_analysis(self, tmp_path):
        """Test exporting metrics in various formats"""
        logger = MetricsLogger()
        
        # Add sample metrics
        for i in range(10):
            logger.log_performance_metric(f"PHASE{i}", 10 + i, 8 + i, "test")
        
        # Export as JSON
        json_file = tmp_path / "metrics.json"
        logger.export_json(str(json_file))
        assert json_file.exists()
        
        # Export as CSV
        csv_file = tmp_path / "metrics.csv"
        logger.export_csv(str(csv_file))
        assert csv_file.exists()
        
        # Verify CSV content
        import csv
        with open(csv_file) as f:
            reader = csv.DictReader(f)
            rows = list(reader)
            assert len(rows) == 10