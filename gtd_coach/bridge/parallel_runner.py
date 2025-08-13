#!/usr/bin/env python3
"""
Parallel execution framework for running both legacy and agent systems.
Enables comparison and validation during incremental migration.
"""

import asyncio
import json
import logging
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Tuple, Optional
import traceback
from dataclasses import dataclass, asdict

from gtd_coach.bridge.state_converter import StateBridge

logger = logging.getLogger(__name__)


@dataclass
class ExecutionResult:
    """Result from executing a system"""
    success: bool
    output: Any
    error: Optional[str]
    latency_ms: float
    memory_usage_mb: float
    phase_timings: Dict[str, float]


@dataclass
class ComparisonResult:
    """Result of comparing two system outputs"""
    identical: bool
    differences: List[Dict[str, Any]]
    similarity_score: float
    performance_delta: Dict[str, float]


class ParallelRunner:
    """
    Run both legacy and agent systems in parallel for comparison.
    Logs divergences and performance metrics.
    """
    
    def __init__(self, 
                 metrics_dir: Optional[Path] = None,
                 log_divergences: bool = True):
        self.bridge = StateBridge()
        self.metrics_dir = metrics_dir or Path.home() / "gtd-coach" / "data" / "parallel_metrics"
        self.metrics_dir.mkdir(parents=True, exist_ok=True)
        self.log_divergences = log_divergences
        self.logger = logging.getLogger(__name__)
        
        # Metrics collection
        self.comparison_results = []
        self.session_id = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    async def run_both(self, 
                       coach_instance: Any,
                       phase: str,
                       input_data: Dict[str, Any]) -> Tuple[ExecutionResult, ExecutionResult]:
        """
        Run both legacy and agent systems with the same input.
        
        Args:
            coach_instance: GTDCoach instance with both systems available
            phase: Phase to execute (startup, mind_sweep, etc.)
            input_data: Input data for the phase
            
        Returns:
            Tuple of (legacy_result, agent_result)
        """
        # Create tasks for parallel execution
        legacy_task = asyncio.create_task(
            self._run_legacy(coach_instance, phase, input_data)
        )
        agent_task = asyncio.create_task(
            self._run_agent(coach_instance, phase, input_data)
        )
        
        # Wait for both to complete
        legacy_result, agent_result = await asyncio.gather(
            legacy_task, agent_task,
            return_exceptions=True
        )
        
        # Handle exceptions
        if isinstance(legacy_result, Exception):
            legacy_result = ExecutionResult(
                success=False,
                output=None,
                error=str(legacy_result),
                latency_ms=0,
                memory_usage_mb=0,
                phase_timings={}
            )
        
        if isinstance(agent_result, Exception):
            agent_result = ExecutionResult(
                success=False,
                output=None,
                error=str(agent_result),
                latency_ms=0,
                memory_usage_mb=0,
                phase_timings={}
            )
        
        # Compare and log results
        comparison = self.compare_outputs(legacy_result, agent_result, phase)
        self._log_comparison(phase, comparison, legacy_result, agent_result)
        
        return legacy_result, agent_result
    
    async def _run_legacy(self, 
                         coach_instance: Any,
                         phase: str,
                         input_data: Dict[str, Any]) -> ExecutionResult:
        """Execute legacy system"""
        start_time = time.perf_counter()
        start_memory = self._get_memory_usage()
        
        try:
            # Map phase to legacy method
            phase_methods = {
                'startup': coach_instance.run_startup_phase,
                'mind_sweep': coach_instance.run_mindsweep_phase,
                'project_review': coach_instance.run_project_review_phase,
                'prioritization': coach_instance.run_prioritization_phase,
                'wrapup': coach_instance.run_wrapup_phase
            }
            
            method = phase_methods.get(phase)
            if not method:
                raise ValueError(f"Unknown phase: {phase}")
            
            # Run synchronously (legacy is sync)
            output = await asyncio.get_event_loop().run_in_executor(
                None, method
            )
            
            end_time = time.perf_counter()
            end_memory = self._get_memory_usage()
            
            return ExecutionResult(
                success=True,
                output=coach_instance.review_data,  # Get the updated state
                error=None,
                latency_ms=(end_time - start_time) * 1000,
                memory_usage_mb=end_memory - start_memory,
                phase_timings=coach_instance.review_data.get('phase_timings', {})
            )
            
        except Exception as e:
            self.logger.error(f"Legacy execution failed for {phase}: {e}")
            return ExecutionResult(
                success=False,
                output=None,
                error=str(e),
                latency_ms=0,
                memory_usage_mb=0,
                phase_timings={}
            )
    
    async def _run_agent(self,
                        coach_instance: Any,
                        phase: str,
                        input_data: Dict[str, Any]) -> ExecutionResult:
        """Execute agent system"""
        start_time = time.perf_counter()
        start_memory = self._get_memory_usage()
        
        try:
            if not coach_instance.agent_workflow:
                raise ValueError("Agent workflow not initialized")
            
            # Convert input to agent state
            agent_state = self.bridge.legacy_to_agent(input_data)
            agent_state['current_phase'] = phase
            
            # Map phase to agent node
            phase_nodes = {
                'startup': 'startup',
                'mind_sweep': 'mind_sweep',
                'project_review': 'project_review',
                'prioritization': 'prioritization',
                'wrapup': 'wrapup'
            }
            
            node = phase_nodes.get(phase)
            if not node:
                raise ValueError(f"Unknown phase: {phase}")
            
            # Execute the specific node
            config = {
                "configurable": {
                    "thread_id": coach_instance.session_id,
                    "checkpoint_ns": phase
                }
            }
            
            # Stream the graph execution for this phase
            result_state = None
            async for event in coach_instance.agent_workflow.graph.astream(
                agent_state,
                config,
                stream_mode="values"
            ):
                result_state = event
                # Break after first phase completes
                if event.get('current_phase') != phase:
                    break
            
            end_time = time.perf_counter()
            end_memory = self._get_memory_usage()
            
            return ExecutionResult(
                success=True,
                output=result_state,
                error=None,
                latency_ms=(end_time - start_time) * 1000,
                memory_usage_mb=end_memory - start_memory,
                phase_timings=result_state.get('phase_timings', {})
            )
            
        except Exception as e:
            self.logger.error(f"Agent execution failed for {phase}: {e}")
            return ExecutionResult(
                success=False,
                output=None,
                error=str(e),
                latency_ms=0,
                memory_usage_mb=0,
                phase_timings={}
            )
    
    def compare_outputs(self,
                       legacy_result: ExecutionResult,
                       agent_result: ExecutionResult,
                       phase: str) -> ComparisonResult:
        """
        Compare outputs from both systems.
        
        Args:
            legacy_result: Result from legacy system
            agent_result: Result from agent system
            phase: Phase being compared
            
        Returns:
            ComparisonResult with differences and metrics
        """
        differences = []
        
        # Both failed - different errors?
        if not legacy_result.success and not agent_result.success:
            if legacy_result.error != agent_result.error:
                differences.append({
                    'type': 'error_mismatch',
                    'legacy': legacy_result.error,
                    'agent': agent_result.error
                })
            return ComparisonResult(
                identical=False,
                differences=differences,
                similarity_score=0.0,
                performance_delta={'latency_ms': 0, 'memory_mb': 0}
            )
        
        # One failed
        if legacy_result.success != agent_result.success:
            differences.append({
                'type': 'success_mismatch',
                'legacy_success': legacy_result.success,
                'agent_success': agent_result.success
            })
            return ComparisonResult(
                identical=False,
                differences=differences,
                similarity_score=0.0,
                performance_delta={
                    'latency_ms': agent_result.latency_ms - legacy_result.latency_ms,
                    'memory_mb': agent_result.memory_usage_mb - legacy_result.memory_usage_mb
                }
            )
        
        # Both succeeded - compare outputs
        legacy_output = legacy_result.output or {}
        agent_output = agent_result.output or {}
        
        # Convert agent state to legacy format for comparison
        if isinstance(agent_output, dict) and 'workflow_type' in agent_output:
            agent_output = self.bridge.agent_to_legacy(agent_output)
        
        # Compare key fields based on phase
        comparison_fields = self._get_comparison_fields(phase)
        
        for field in comparison_fields:
            legacy_value = legacy_output.get(field)
            agent_value = agent_output.get(field)
            
            if not self._values_equal(legacy_value, agent_value, field):
                differences.append({
                    'type': 'field_mismatch',
                    'field': field,
                    'legacy': legacy_value,
                    'agent': agent_value
                })
        
        # Calculate similarity score
        total_fields = len(comparison_fields)
        matching_fields = total_fields - len([d for d in differences if d['type'] == 'field_mismatch'])
        similarity_score = matching_fields / total_fields if total_fields > 0 else 1.0
        
        # Performance comparison
        performance_delta = {
            'latency_ms': agent_result.latency_ms - legacy_result.latency_ms,
            'memory_mb': agent_result.memory_usage_mb - legacy_result.memory_usage_mb,
            'latency_improvement_pct': (
                (legacy_result.latency_ms - agent_result.latency_ms) / legacy_result.latency_ms * 100
                if legacy_result.latency_ms > 0 else 0
            )
        }
        
        return ComparisonResult(
            identical=len(differences) == 0,
            differences=differences,
            similarity_score=similarity_score,
            performance_delta=performance_delta
        )
    
    def _get_comparison_fields(self, phase: str) -> List[str]:
        """Get fields to compare based on phase"""
        base_fields = ['current_phase', 'session_id']
        
        phase_specific = {
            'startup': ['recurring_patterns'],
            'mind_sweep': ['mindsweep'],
            'project_review': ['projects'],
            'prioritization': ['priorities'],
            'wrapup': ['mindsweep', 'priorities', 'metrics']
        }
        
        return base_fields + phase_specific.get(phase, [])
    
    def _values_equal(self, val1: Any, val2: Any, field: str) -> bool:
        """Check if two values are functionally equivalent"""
        # Handle None
        if val1 is None and val2 is None:
            return True
        if val1 is None or val2 is None:
            return False
        
        # Lists - check contents ignoring order for some fields
        if isinstance(val1, list) and isinstance(val2, list):
            if field in ['mindsweep', 'projects']:
                # Order doesn't matter for these
                return set(str(v) for v in val1) == set(str(v) for v in val2)
            else:
                return val1 == val2
        
        # Dicts - recursive comparison
        if isinstance(val1, dict) and isinstance(val2, dict):
            if set(val1.keys()) != set(val2.keys()):
                return False
            return all(self._values_equal(val1[k], val2[k], f"{field}.{k}") 
                      for k in val1.keys())
        
        # Direct comparison
        return val1 == val2
    
    def _log_comparison(self,
                       phase: str,
                       comparison: ComparisonResult,
                       legacy_result: ExecutionResult,
                       agent_result: ExecutionResult):
        """Log comparison results for analysis"""
        result = {
            'timestamp': datetime.now().isoformat(),
            'session_id': self.session_id,
            'phase': phase,
            'identical': comparison.identical,
            'similarity_score': comparison.similarity_score,
            'differences': comparison.differences,
            'performance': {
                'legacy_latency_ms': legacy_result.latency_ms,
                'agent_latency_ms': agent_result.latency_ms,
                'latency_delta_ms': comparison.performance_delta['latency_ms'],
                'improvement_pct': comparison.performance_delta.get('latency_improvement_pct', 0)
            }
        }
        
        self.comparison_results.append(result)
        
        # Log divergences if configured
        if self.log_divergences and not comparison.identical:
            self.logger.warning(
                f"Divergence in {phase}: similarity={comparison.similarity_score:.2f}, "
                f"differences={len(comparison.differences)}"
            )
            for diff in comparison.differences[:3]:  # Log first 3 differences
                self.logger.debug(f"  - {diff}")
        
        # Save to file periodically
        if len(self.comparison_results) % 5 == 0:
            self.save_metrics()
    
    def save_metrics(self):
        """Save comparison metrics to file"""
        metrics_file = self.metrics_dir / f"parallel_run_{self.session_id}.json"
        
        summary = {
            'session_id': self.session_id,
            'timestamp': datetime.now().isoformat(),
            'total_comparisons': len(self.comparison_results),
            'identical_count': sum(1 for r in self.comparison_results if r['identical']),
            'average_similarity': (
                sum(r['similarity_score'] for r in self.comparison_results) / 
                len(self.comparison_results)
                if self.comparison_results else 0
            ),
            'comparisons': self.comparison_results
        }
        
        with open(metrics_file, 'w') as f:
            json.dump(summary, f, indent=2, default=str)
        
        self.logger.info(f"Saved parallel run metrics to {metrics_file}")
    
    def get_summary(self) -> Dict[str, Any]:
        """Get summary of all comparisons"""
        if not self.comparison_results:
            return {'message': 'No comparisons run yet'}
        
        total = len(self.comparison_results)
        identical = sum(1 for r in self.comparison_results if r['identical'])
        
        avg_legacy_latency = sum(r['performance']['legacy_latency_ms'] 
                                for r in self.comparison_results) / total
        avg_agent_latency = sum(r['performance']['agent_latency_ms'] 
                               for r in self.comparison_results) / total
        
        return {
            'total_comparisons': total,
            'identical_outputs': identical,
            'divergence_rate': (total - identical) / total if total > 0 else 0,
            'average_similarity': sum(r['similarity_score'] 
                                     for r in self.comparison_results) / total,
            'performance': {
                'avg_legacy_latency_ms': avg_legacy_latency,
                'avg_agent_latency_ms': avg_agent_latency,
                'agent_faster_by_pct': (
                    (avg_legacy_latency - avg_agent_latency) / avg_legacy_latency * 100
                    if avg_legacy_latency > 0 else 0
                )
            }
        }
    
    def _get_memory_usage(self) -> float:
        """Get current memory usage in MB"""
        try:
            import psutil
            process = psutil.Process()
            return process.memory_info().rss / 1024 / 1024
        except:
            return 0.0


def test_parallel_runner():
    """Test the parallel runner with mock data"""
    runner = ParallelRunner()
    
    # Test comparison logic
    legacy_result = ExecutionResult(
        success=True,
        output={'mindsweep': ['task1', 'task2'], 'current_phase': 'MIND_SWEEP'},
        error=None,
        latency_ms=100,
        memory_usage_mb=50,
        phase_timings={}
    )
    
    agent_result = ExecutionResult(
        success=True,
        output={'mindsweep': ['task2', 'task1'], 'current_phase': 'MIND_SWEEP'},
        error=None,
        latency_ms=80,
        memory_usage_mb=45,
        phase_timings={}
    )
    
    comparison = runner.compare_outputs(legacy_result, agent_result, 'mind_sweep')
    
    print(f"Comparison result: identical={comparison.identical}")
    print(f"Similarity score: {comparison.similarity_score}")
    print(f"Performance delta: {comparison.performance_delta}")
    
    assert comparison.identical or comparison.similarity_score > 0.5
    print("✅ Parallel runner tests passed")


if __name__ == "__main__":
    test_parallel_runner()