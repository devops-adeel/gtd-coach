#!/usr/bin/env python3
"""
Shadow Mode Runner for A/B Testing
Lightweight comparison without full parallel execution
"""

import asyncio
import json
import logging
import time
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
    
    def __init__(self, data_dir: Optional[Path] = None):
        self.data_dir = data_dir or Path.home() / "gtd-coach" / "data" / "shadow_metrics"
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.session_metrics = []
        self.session_id = None
    
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


class ShadowModeRunner:
    """Runs workflows with shadow mode comparison"""
    
    def __init__(self):
        self.metrics_logger = MetricsLogger()
        self.legacy_coach = None
        self.agent_workflow = None
    
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