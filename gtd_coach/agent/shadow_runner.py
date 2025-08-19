#!/usr/bin/env python3
"""
Shadow Mode Runner for A/B Testing
Lightweight comparison without full parallel execution
"""

import asyncio
import json
import logging
import time
import csv
from typing import Dict, Optional, Any, List
from datetime import datetime
from pathlib import Path
from dataclasses import dataclass, asdict

# Import feature flags
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))
from gtd_coach.config.features import should_use_agent, should_run_shadow, rollout_manager

logger = logging.getLogger(__name__)


@dataclass
class MetricPoint:
    """Single metric measurement"""
    timestamp: str
    phase: str
    metric_type: str
    value: Any
    metadata: Optional[Dict] = None


class MetricsLogger:
    """Logs metrics for comparison"""
    
    def __init__(self, data_dir: Optional[Path] = None, log_file: Optional[str] = None):
        # Support both data_dir and log_file parameters for compatibility
        if log_file:
            self.log_file = log_file
            self.data_dir = Path(log_file).parent
        else:
            self.data_dir = data_dir or Path.home() / "gtd-coach" / "data" / "shadow_metrics"
            self.log_file = None
        
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.session_metrics = []
        self.metrics = []  # For test compatibility
        self.session_id = datetime.now().strftime("%Y%m%d_%H%M%S")  # Default session ID
    
    def start_session(self, session_id: str, workflow_type: str):
        """Start a new metrics session"""
        self.session_id = session_id
        self.session_metrics = []
        self.log_metric("session_start", "meta", {
            "workflow_type": workflow_type,
            "timestamp": datetime.now().isoformat()
        })
    
    def log_metric(self, phase: str, metric_type: str, value: Any, metadata: Optional[Dict] = None):
        """Log a single metric"""
        metric = MetricPoint(
            timestamp=datetime.now().isoformat(),
            phase=phase,
            metric_type=metric_type,
            value=value,
            metadata=metadata
        )
        self.session_metrics.append(metric)
    
    def log_decision(self, decision_point: str, result: Any):
        """Log a key decision point"""
        self.log_metric(
            phase=decision_point,
            metric_type="decision",
            value=result,
            metadata={"decision_point": decision_point}
        )
    
    def log_phase_timing(self, phase: str, duration_seconds: float):
        """Log phase execution time"""
        self.log_metric(
            phase=phase,
            metric_type="timing",
            value=duration_seconds,
            metadata={"unit": "seconds"}
        )
    
    def log_agent_metrics(self, result: Dict):
        """Log metrics from agent execution"""
        self.log_metric(
            phase="complete",
            metric_type="agent_result",
            value={
                "captures": len(result.get('captures', [])),
                "processed_items": len(result.get('processed_items', [])),
                "patterns_detected": len(result.get('adhd_patterns', [])),
                "interventions": len(result.get('interventions', [])),
                "completed_phases": result.get('completed_phases', [])
            }
        )
    
    def save_session(self):
        """Save session metrics to file"""
        if not self.session_id:
            return
        
        file_path = self.data_dir / f"{self.session_id}_metrics.json"
        
        data = {
            "session_id": self.session_id,
            "metrics": [asdict(m) for m in self.session_metrics]
        }
        
        with open(file_path, 'w') as f:
            json.dump(data, f, indent=2, default=str)
        
        logger.info(f"Saved metrics to {file_path}")
    
    async def compare_sessions(self, legacy_session: str, agent_session: str) -> Dict:
        """Compare metrics between legacy and agent sessions"""
        legacy_file = self.data_dir / f"{legacy_session}_metrics.json"
        agent_file = self.data_dir / f"{agent_session}_metrics.json"
        
        if not legacy_file.exists() or not agent_file.exists():
            return {"error": "Missing session data"}
        
        with open(legacy_file) as f:
            legacy_data = json.load(f)
        
        with open(agent_file) as f:
            agent_data = json.load(f)
        
        comparison = {
            "session_ids": {
                "legacy": legacy_session,
                "agent": agent_session
            },
            "metric_counts": {
                "legacy": len(legacy_data['metrics']),
                "agent": len(agent_data['metrics'])
            },
            "differences": []
        }
        
        # Compare key metrics
        legacy_decisions = [m for m in legacy_data['metrics'] if m['metric_type'] == 'decision']
        agent_decisions = [m for m in agent_data['metrics'] if m['metric_type'] == 'decision']
        
        # Find differences in decisions
        for ld in legacy_decisions:
            matching_agent = next(
                (ad for ad in agent_decisions if ad['phase'] == ld['phase']),
                None
            )
            if matching_agent and ld['value'] != matching_agent['value']:
                comparison['differences'].append({
                    'decision_point': ld['phase'],
                    'legacy_value': ld['value'],
                    'agent_value': matching_agent['value']
                })
        
        return comparison
    
    # Compatibility methods for tests
    def log_decision_point(self, phase: str, legacy_decision: Any, agent_decision: Any, context: Dict):
        """Log a decision point comparison (test compatibility)"""
        metric = {
            "timestamp": datetime.now().isoformat(),
            "phase": phase,
            "legacy_decision": legacy_decision,
            "agent_decision": agent_decision,
            "context": context,
            "metric_type": "decision_point"
        }
        self.metrics.append(metric)
        self.log_metric(phase, "decision_point", {
            "legacy": legacy_decision,
            "agent": agent_decision
        }, context)
    
    def log_performance_metric(self, phase: str, legacy_duration: float, agent_duration: float, metric_type: str):
        """Log performance comparison (test compatibility)"""
        improvement_percent = ((legacy_duration - agent_duration) / legacy_duration * 100) if legacy_duration > 0 else 0
        
        metric = {
            "timestamp": datetime.now().isoformat(),
            "phase": phase,
            "legacy_duration": legacy_duration,
            "agent_duration": agent_duration,
            "metric_type": "performance",
            "improvement_percent": improvement_percent
        }
        self.metrics.append(metric)
        self.log_phase_timing(phase, agent_duration)
    
    def generate_summary(self) -> Dict:
        """Generate metrics summary (test compatibility)"""
        if not self.metrics:
            return {
                "total_metrics": 0,
                "performance_metrics": 0,
                "decision_points": 0,
                "average_improvement": 0,
                "decision_agreement_rate": 0
            }
        
        perf_metrics = [m for m in self.metrics if m.get("metric_type") == "performance"]
        decision_metrics = [m for m in self.metrics if m.get("metric_type") == "decision_point"]
        
        # Calculate average improvement
        improvements = [m.get("improvement_percent", 0) for m in perf_metrics]
        avg_improvement = sum(improvements) / len(improvements) if improvements else 0
        
        # Calculate decision agreement rate
        agreements = sum(
            1 for m in decision_metrics 
            if m.get("legacy_decision") == m.get("agent_decision")
        )
        agreement_rate = (agreements / len(decision_metrics) * 100) if decision_metrics else 0
        
        return {
            "total_metrics": len(self.metrics),
            "performance_metrics": len(perf_metrics),
            "decision_points": len(decision_metrics),
            "average_improvement": avg_improvement,
            "decision_agreement_rate": agreement_rate,
            "session_id": self.session_id
        }
    
    def generate_detailed_report(self) -> Dict:
        """Generate detailed comparison report (test compatibility)"""
        summary = self.generate_summary()
        
        perf_metrics = [m for m in self.metrics if m.get("metric_type") == "performance"]
        decision_metrics = [m for m in self.metrics if m.get("metric_type") == "decision_point"]
        
        # Calculate total times
        total_legacy_time = sum(m.get("legacy_duration", 0) for m in perf_metrics)
        total_agent_time = sum(m.get("agent_duration", 0) for m in perf_metrics)
        overall_improvement = ((total_legacy_time - total_agent_time) / total_legacy_time * 100) if total_legacy_time > 0 else 0
        
        return {
            "performance_analysis": {
                "total_legacy_time": total_legacy_time,
                "total_agent_time": total_agent_time,
                "overall_improvement": overall_improvement,
                "metrics_count": len(perf_metrics)
            },
            "decision_analysis": {
                "total_decisions": len(decision_metrics),
                "agreement_rate": summary["decision_agreement_rate"],
                "divergences": [
                    m for m in decision_metrics 
                    if m.get("legacy_decision") != m.get("agent_decision")
                ]
            },
            "recommendations": [
                "Agent shows performance improvements" if overall_improvement > 0 else "Legacy performs better",
                f"Decision agreement at {summary['decision_agreement_rate']:.1f}%"
            ]
        }
    
    def identify_regressions(self) -> List[Dict]:
        """Identify performance regressions (test compatibility)"""
        perf_metrics = [m for m in self.metrics if m.get("metric_type") == "performance"]
        
        regressions = []
        for metric in perf_metrics:
            if metric.get("agent_duration", 0) > metric.get("legacy_duration", 0):
                regressions.append({
                    "phase": metric.get("phase"),
                    "legacy_duration": metric.get("legacy_duration"),
                    "agent_duration": metric.get("agent_duration"),
                    "regression_percent": abs(metric.get("improvement_percent", 0))
                })
        
        return regressions
    
    def export_json(self, filepath: str):
        """Export metrics to JSON file (test compatibility)"""
        data = {
            "session_id": self.session_id,
            "metrics": self.metrics,
            "summary": self.generate_summary(),
            "timestamp": datetime.now().isoformat()
        }
        
        with open(filepath, 'w') as f:
            json.dump(data, f, indent=2, default=str)
    
    def export_csv(self, filepath: str):
        """Export metrics to CSV file (test compatibility)"""
        if not self.metrics:
            # Create empty CSV
            with open(filepath, 'w') as f:
                f.write("phase,metric_type,timestamp\n")
            return
        
        # Determine all unique keys
        all_keys = set()
        for metric in self.metrics:
            all_keys.update(metric.keys())
        
        # Write CSV
        with open(filepath, 'w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=sorted(all_keys))
            writer.writeheader()
            writer.writerows(self.metrics)
    
    def save(self):
        """Save metrics to file (test compatibility)"""
        if self.log_file:
            self.export_json(self.log_file)
        else:
            self.save_session()


class ShadowModeRunner:
    """Runs workflows with shadow mode comparison"""
    
    def __init__(self):
        self.metrics_logger = MetricsLogger()
        self.legacy_coach = None
        self.agent_workflow = None
        self.comparison_tasks = []  # For test compatibility
        self.is_running = False  # For test compatibility
    
    async def run_with_shadow(self, session_id: str, workflow_type: str = "weekly_review") -> Dict:
        """
        Run workflow with shadow mode based on feature flags
        
        Args:
            session_id: Unique session identifier
            workflow_type: Type of workflow to run
        
        Returns:
            Workflow result
        """
        start_time = time.time()
        
        # Determine execution path based on feature flags
        if should_use_agent(session_id):
            # Run agent and log metrics
            result = await self.run_agent_workflow(session_id, workflow_type)
            
            # Record performance
            duration = time.time() - start_time
            rollout_manager.record_session(
                used_agent=True,
                success=result.get('success', True),
                latency_ms=duration * 1000
            )
            
        else:
            # Run legacy with shadow logging
            result = await self.run_legacy_with_logging(session_id, workflow_type)
            
            # Record performance
            duration = time.time() - start_time
            rollout_manager.record_session(
                used_agent=False,
                success=result.get('success', True),
                latency_ms=duration * 1000
            )
            
            if should_run_shadow(session_id):
                # Async shadow comparison - doesn't block user
                asyncio.create_task(
                    self.compare_shadow_outputs(session_id, result)
                )
        
        return result
    
    async def run_agent_workflow(self, session_id: str, workflow_type: str) -> Dict:
        """Run agent workflow with metrics logging"""
        logger.info(f"Running agent workflow for session {session_id}")
        
        # Start metrics session
        self.metrics_logger.start_session(session_id, workflow_type)
        
        # Import and initialize workflow
        if workflow_type == "weekly_review":
            from gtd_coach.agent.workflows.weekly_review import WeeklyReviewWorkflow
            workflow = WeeklyReviewWorkflow()
        else:
            from gtd_coach.agent.workflows.daily_capture import DailyCaptureWorkflow
            workflow = DailyCaptureWorkflow()
        
        # Run workflow
        phase_start = time.time()
        
        try:
            result = workflow.run({"session_id": session_id})
            
            # Log completion metrics
            self.metrics_logger.log_agent_metrics(result)
            self.metrics_logger.log_phase_timing("total", time.time() - phase_start)
            
            result['success'] = True
            
        except Exception as e:
            logger.error(f"Agent workflow failed: {e}")
            result = {
                'success': False,
                'error': str(e),
                'session_id': session_id
            }
        
        # Save metrics
        self.metrics_logger.save_session()
        
        return result
    
    async def run_legacy_with_logging(self, session_id: str, workflow_type: str) -> Dict:
        """Run legacy workflow with metrics logging at key points"""
        logger.info(f"Running legacy workflow for session {session_id}")
        
        # Start metrics session
        self.metrics_logger.start_session(session_id, workflow_type)
        
        # Import legacy coach
        from gtd_coach.coach import GTDCoach
        coach = GTDCoach()
        
        # Hook into key methods to log decisions
        self._hook_legacy_methods(coach)
        
        # Run workflow
        phase_start = time.time()
        
        try:
            # Run the legacy review
            coach.run_review()
            
            # Extract result data
            result = {
                'success': True,
                'session_id': session_id,
                'captures': coach.review_data.get('mindsweep_items', []),
                'processed_items': coach.review_data.get('priorities', []),
                'completed_phases': coach.review_data.get('completed_phases', [])
            }
            
            # Log completion metrics
            self.metrics_logger.log_metric(
                phase="complete",
                metric_type="legacy_result",
                value={
                    "captures": len(result['captures']),
                    "processed_items": len(result['processed_items']),
                    "completed_phases": result['completed_phases']
                }
            )
            self.metrics_logger.log_phase_timing("total", time.time() - phase_start)
            
        except Exception as e:
            logger.error(f"Legacy workflow failed: {e}")
            result = {
                'success': False,
                'error': str(e),
                'session_id': session_id
            }
        
        # Save metrics
        self.metrics_logger.save_session()
        
        return result
    
    def _hook_legacy_methods(self, coach):
        """Hook into legacy methods to log key decisions"""
        
        # Hook mind sweep
        original_mind_sweep = coach.run_mind_sweep if hasattr(coach, 'run_mind_sweep') else None
        if original_mind_sweep:
            def logged_mind_sweep(*args, **kwargs):
                start = time.time()
                result = original_mind_sweep(*args, **kwargs)
                self.metrics_logger.log_phase_timing("mind_sweep", time.time() - start)
                self.metrics_logger.log_decision("mind_sweep", {
                    "item_count": len(coach.review_data.get('mindsweep_items', []))
                })
                return result
            coach.run_mind_sweep = logged_mind_sweep
        
        # Hook prioritization
        original_prioritize = coach.run_prioritization if hasattr(coach, 'run_prioritization') else None
        if original_prioritize:
            def logged_prioritize(*args, **kwargs):
                start = time.time()
                result = original_prioritize(*args, **kwargs)
                self.metrics_logger.log_phase_timing("prioritization", time.time() - start)
                priorities = coach.review_data.get('priorities', [])
                self.metrics_logger.log_decision("prioritization", {
                    "A_count": len([p for p in priorities if p.get('priority') == 'A']),
                    "B_count": len([p for p in priorities if p.get('priority') == 'B']),
                    "C_count": len([p for p in priorities if p.get('priority') == 'C'])
                })
                return result
            coach.run_prioritization = logged_prioritize
    
    async def compare_shadow_outputs(self, session_id: str, legacy_result: Dict):
        """Compare shadow outputs asynchronously"""
        logger.info(f"Running shadow comparison for session {session_id}")
        
        # Run agent in background (don't block user)
        shadow_session_id = f"{session_id}_shadow"
        
        try:
            # Run agent workflow
            agent_result = await self.run_agent_workflow(
                shadow_session_id, 
                "weekly_review"
            )
            
            # Compare results
            comparison = await self.metrics_logger.compare_sessions(
                session_id,
                shadow_session_id
            )
            
            # Log comparison results
            if comparison.get('differences'):
                logger.info(f"Shadow comparison found {len(comparison['differences'])} differences")
                
                # Save comparison
                comparison_file = self.metrics_logger.data_dir / f"{session_id}_comparison.json"
                with open(comparison_file, 'w') as f:
                    json.dump(comparison, f, indent=2, default=str)
            
        except Exception as e:
            logger.error(f"Shadow comparison failed: {e}")
    
    # Test compatibility methods
    async def run_shadow_comparison(self, legacy_workflow, agent_workflow, state: Dict):
        """Run shadow comparison for tests"""
        self.is_running = True
        
        # Create a comparison task
        async def compare():
            try:
                # Run legacy workflow
                if hasattr(legacy_workflow, 'run'):
                    legacy_result = legacy_workflow.run(state) if not asyncio.iscoroutinefunction(legacy_workflow.run) else await legacy_workflow.run(state)
                else:
                    legacy_result = {"success": True}
                
                # Run agent workflow  
                if hasattr(agent_workflow, 'run'):
                    agent_result = await agent_workflow.run(state) if asyncio.iscoroutinefunction(agent_workflow.run) else agent_workflow.run(state)
                else:
                    agent_result = {"success": True}
                
                # Log comparison
                self.metrics_logger.log_metric(
                    "comparison",
                    "result",
                    {
                        "legacy": legacy_result,
                        "agent": agent_result
                    }
                )
                
                return {"legacy": legacy_result, "agent": agent_result}
            finally:
                self.is_running = False
        
        # Create task and add to list
        task = asyncio.create_task(compare())
        self.comparison_tasks.append(task)
        return task
    
    def compare_results(self, legacy_result: Dict, agent_result: Dict) -> Dict:
        """Compare results between legacy and agent"""
        differences = {}
        
        # Compare captures
        if "captures" in legacy_result or "captures" in agent_result:
            legacy_captures = legacy_result.get("captures", [])
            agent_captures = agent_result.get("captures", [])
            differences["captures"] = {
                "legacy_count": len(legacy_captures),
                "agent_count": len(agent_captures),
                "difference": len(agent_captures) - len(legacy_captures)
            }
        
        # Compare priorities
        if "priorities" in legacy_result or "priorities" in agent_result:
            legacy_priorities = legacy_result.get("priorities", {})
            agent_priorities = agent_result.get("priorities", {})
            differences["priorities"] = {
                "different_a_items": legacy_priorities.get("A", []) != agent_priorities.get("A", []),
                "priority_mismatch": 0  # Simplified
            }
        
        # Compare performance
        if "duration" in legacy_result and "duration" in agent_result:
            legacy_duration = legacy_result["duration"]
            agent_duration = agent_result["duration"]
            differences["performance"] = {
                "legacy_duration": legacy_duration,
                "agent_duration": agent_duration,
                "improvement_percent": ((legacy_duration - agent_duration) / legacy_duration * 100) if legacy_duration > 0 else 0
            }
        
        return differences
    
    def should_notify_divergence(self, differences: Dict) -> bool:
        """Determine if divergence is significant enough to notify"""
        # Major capture difference
        if differences.get("captures", {}).get("difference", 0) > 5:
            return True
        
        # Priority mismatch
        if differences.get("priorities", {}).get("different_a_items"):
            return True
        
        # Performance regression
        if differences.get("performance", {}).get("improvement_percent", 0) < -20:
            return True
        
        return False


# Create singleton instance
shadow_runner = ShadowModeRunner()


async def run_workflow_with_shadow(session_id: str, workflow_type: str = "weekly_review") -> Dict:
    """
    Convenience function to run workflow with shadow mode
    
    Args:
        session_id: Unique session identifier
        workflow_type: Type of workflow to run
    
    Returns:
        Workflow result
    """
    return await shadow_runner.run_with_shadow(session_id, workflow_type)