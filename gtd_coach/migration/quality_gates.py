#!/usr/bin/env python3
"""
Quality Gates for GTD Coach Migration.
Defines thresholds and validation rules for safe migration and deletion.
Simplified for single-user deployment.
"""

from dataclasses import dataclass
from typing import Dict, List, Tuple, Optional
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class GateStatus(Enum):
    """Status of a quality gate check"""
    PASSED = "passed"
    WARNING = "warning"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass
class QualityGate:
    """Definition of a single quality gate"""
    name: str
    description: str
    query: str  # Prometheus query
    threshold: float
    operator: str  # <, >, <=, >=, ==
    severity: str  # critical, warning, info
    required_for_deletion: bool = False
    required_for_switch: bool = False


# Quality gates for single-user deployment
QUALITY_GATES = {
    # Critical gates for deletion
    "zero_legacy_usage_30d": QualityGate(
        name="Zero Legacy Usage (30 days)",
        description="No legacy invocations in the last 30 days",
        query='sum(increase(gtd_coach_legacy_usage_total{implementation="legacy"}[30d]))',
        threshold=0,
        operator="==",
        severity="critical",
        required_for_deletion=True
    ),
    
    "zero_legacy_usage_7d": QualityGate(
        name="Zero Legacy Usage (7 days)", 
        description="No legacy invocations in the last week",
        query='sum(increase(gtd_coach_legacy_usage_total{implementation="legacy"}[7d]))',
        threshold=0,
        operator="==",
        severity="warning",
        required_for_switch=True
    ),
    
    # Adoption gates
    "agent_adoption_95": QualityGate(
        name="95% Agent Adoption",
        description="At least 95% of usage is on agent implementation",
        query='''
        sum(rate(gtd_coach_legacy_usage_total{implementation="agent"}[24h])) /
        sum(rate(gtd_coach_legacy_usage_total[24h]))
        ''',
        threshold=0.95,
        operator=">=",
        severity="critical",
        required_for_deletion=True
    ),
    
    "agent_adoption_50": QualityGate(
        name="50% Agent Adoption",
        description="At least 50% of usage is on agent implementation",
        query='''
        sum(rate(gtd_coach_legacy_usage_total{implementation="agent"}[24h])) /
        sum(rate(gtd_coach_legacy_usage_total[24h]))
        ''',
        threshold=0.50,
        operator=">=",
        severity="warning",
        required_for_switch=True
    ),
    
    # Performance gates
    "error_rate_low": QualityGate(
        name="Low Error Rate",
        description="Error rate below 1%",
        query='''
        sum(rate(gtd_coach_migration_errors_total[1h])) /
        sum(rate(gtd_coach_legacy_usage_total[1h]))
        ''',
        threshold=0.01,
        operator="<",
        severity="critical",
        required_for_switch=True
    ),
    
    "p95_latency_acceptable": QualityGate(
        name="P95 Latency < 2s",
        description="95th percentile latency under 2 seconds",
        query='''
        histogram_quantile(0.95,
            sum(rate(gtd_coach_command_duration_bucket[5m])) by (le)
        )
        ''',
        threshold=2000,
        operator="<",
        severity="warning",
        required_for_switch=True
    ),
    
    "no_performance_regression": QualityGate(
        name="No Performance Regression",
        description="Agent not significantly slower than legacy",
        query='''
        (histogram_quantile(0.95, sum(rate(gtd_coach_command_duration_bucket{implementation="agent"}[5m])) by (le)) /
         histogram_quantile(0.95, sum(rate(gtd_coach_command_duration_bucket{implementation="legacy"}[5m])) by (le)))
        ''',
        threshold=1.5,  # Allow up to 50% slower
        operator="<",
        severity="warning",
        required_for_switch=True
    ),
    
    # Stability gates
    "migration_readiness_high": QualityGate(
        name="High Migration Readiness",
        description="Migration readiness score above 80%",
        query='avg(gtd_coach_migration_readiness)',
        threshold=80,
        operator=">=",
        severity="warning",
        required_for_deletion=True
    ),
    
    "quality_score_acceptable": QualityGate(
        name="Quality Score > 70",
        description="Overall quality score above 70",
        query='avg(gtd_coach_quality_score)',
        threshold=70,
        operator=">=",
        severity="info",
        required_for_switch=True
    )
}


class QualityGateChecker:
    """Checks quality gates for migration decisions"""
    
    def __init__(self, prometheus_client=None):
        self.prometheus = prometheus_client
        self.gates = QUALITY_GATES
    
    def check_gate(self, gate: QualityGate, value: float) -> GateStatus:
        """Check if a single gate passes"""
        
        operators = {
            "<": lambda x, y: x < y,
            ">": lambda x, y: x > y,
            "<=": lambda x, y: x <= y,
            ">=": lambda x, y: x >= y,
            "==": lambda x, y: x == y
        }
        
        op_func = operators.get(gate.operator)
        if not op_func:
            logger.error(f"Unknown operator: {gate.operator}")
            return GateStatus.SKIPPED
        
        passed = op_func(value, gate.threshold)
        
        if passed:
            return GateStatus.PASSED
        elif gate.severity == "critical":
            return GateStatus.FAILED
        else:
            return GateStatus.WARNING
    
    async def check_all_gates(self) -> Dict[str, Tuple[GateStatus, float]]:
        """Check all quality gates and return results"""
        
        results = {}
        
        for gate_id, gate in self.gates.items():
            try:
                # Query Prometheus for metric value
                if self.prometheus:
                    value = await self.prometheus.query(gate.query)
                else:
                    # Mock value for testing
                    value = 0.9 if "adoption" in gate_id else 0.005
                
                status = self.check_gate(gate, value)
                results[gate_id] = (status, value)
                
                logger.info(f"Gate '{gate.name}': {status.value} (value={value}, threshold={gate.threshold})")
                
            except Exception as e:
                logger.error(f"Failed to check gate '{gate.name}': {e}")
                results[gate_id] = (GateStatus.SKIPPED, 0)
        
        return results
    
    def can_delete_legacy(self, results: Dict[str, Tuple[GateStatus, float]]) -> Tuple[bool, List[str]]:
        """Check if legacy code can be safely deleted"""
        
        failures = []
        
        for gate_id, gate in self.gates.items():
            if gate.required_for_deletion:
                status, value = results.get(gate_id, (GateStatus.SKIPPED, 0))
                
                if status != GateStatus.PASSED:
                    failures.append(
                        f"{gate.name}: {status.value} (value={value:.2f}, required={gate.threshold})"
                    )
        
        return len(failures) == 0, failures
    
    def can_switch_default(self, results: Dict[str, Tuple[GateStatus, float]]) -> Tuple[bool, List[str]]:
        """Check if default can be switched to agent"""
        
        failures = []
        warnings = []
        
        for gate_id, gate in self.gates.items():
            if gate.required_for_switch:
                status, value = results.get(gate_id, (GateStatus.SKIPPED, 0))
                
                if status == GateStatus.FAILED:
                    failures.append(
                        f"{gate.name}: FAILED (value={value:.2f}, required={gate.threshold})"
                    )
                elif status == GateStatus.WARNING:
                    warnings.append(
                        f"{gate.name}: WARNING (value={value:.2f}, recommended={gate.threshold})"
                    )
        
        # For single user, allow switch with warnings
        can_switch = len(failures) == 0
        
        if warnings:
            logger.warning(f"Switching with warnings: {warnings}")
        
        return can_switch, failures + warnings
    
    def get_summary(self, results: Dict[str, Tuple[GateStatus, float]]) -> str:
        """Get human-readable summary of gate results"""
        
        passed = sum(1 for s, _ in results.values() if s == GateStatus.PASSED)
        warnings = sum(1 for s, _ in results.values() if s == GateStatus.WARNING)
        failed = sum(1 for s, _ in results.values() if s == GateStatus.FAILED)
        skipped = sum(1 for s, _ in results.values() if s == GateStatus.SKIPPED)
        
        total = len(results)
        
        summary = f"""
Quality Gates Summary:
=====================
✅ Passed:  {passed}/{total}
⚠️ Warning: {warnings}/{total}
❌ Failed:  {failed}/{total}
⏭️ Skipped: {skipped}/{total}

Overall Status: {'READY' if failed == 0 else 'NOT READY'}
"""
        
        # Add details for non-passing gates
        if failed > 0 or warnings > 0:
            summary += "\nNon-Passing Gates:\n"
            
            for gate_id, (status, value) in results.items():
                if status in [GateStatus.FAILED, GateStatus.WARNING]:
                    gate = self.gates[gate_id]
                    summary += f"  • {gate.name}: {status.value} (value={value:.2f}, threshold={gate.threshold})\n"
        
        return summary


def create_simple_gates() -> Dict[str, QualityGate]:
    """Create simplified gates for single-user quick decisions"""
    
    return {
        "can_delete": QualityGate(
            name="Can Delete",
            description="Safe to delete legacy code",
            query='sum(increase(gtd_coach_legacy_usage_total{implementation="legacy"}[30d]))',
            threshold=0,
            operator="==",
            severity="critical",
            required_for_deletion=True
        ),
        
        "should_switch": QualityGate(
            name="Should Switch",
            description="Ready to switch default to agent",
            query='''
            sum(rate(gtd_coach_legacy_usage_total{implementation="agent"}[7d])) /
            sum(rate(gtd_coach_legacy_usage_total[7d]))
            ''',
            threshold=0.8,
            operator=">=",
            severity="warning",
            required_for_switch=True
        )
    }


# Export public API
__all__ = [
    'QualityGate',
    'QualityGateChecker',
    'GateStatus',
    'QUALITY_GATES',
    'create_simple_gates'
]