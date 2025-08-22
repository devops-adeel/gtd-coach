#!/usr/bin/env python3
"""
Deprecation decorator for legacy commands.
Applies telemetry tracking and warnings to deprecated functions.
"""

import os
import sys
from pathlib import Path
from functools import wraps
from typing import Callable, Any, Optional

# Add parent directory for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from gtd_coach.observability.deprecation_telemetry import (
    track_deprecation as telemetry_track,
    track_agent_usage as telemetry_agent,
    DeprecationConfig,
    update_migration_readiness,
    calculate_quality_score
)


def deprecate_command(
    command: str,
    alternative: Optional[str] = None,
    removal_date: str = "2026-02-22",
    warning_frequency: str = "daily"
) -> Callable:
    """
    Decorator to mark a command as deprecated.
    
    Args:
        command: Name of the command being deprecated
        alternative: Alternative command/workflow to use
        removal_date: Date when the command will be removed
        warning_frequency: How often to show warnings (always, daily, weekly, monthly)
    
    Example:
        @deprecate_command(
            "daily_clarify",
            alternative="gtd_coach.agent.workflows.daily_clarify",
            removal_date="2026-02-22"
        )
        def daily_clarify_command():
            pass
    """
    config = DeprecationConfig(
        command=command,
        deprecated_since="2025-08-22",
        removal_date=removal_date,
        alternative=alternative,
        warning_frequency=warning_frequency
    )
    
    return telemetry_track(config)


def track_agent_implementation(command: str) -> Callable:
    """
    Decorator to track agent implementation usage.
    Used for comparing with legacy implementation.
    
    Args:
        command: Name of the command
    
    Example:
        @track_agent_implementation("daily_clarify")
        async def daily_clarify_workflow():
            pass
    """
    return telemetry_agent(command)


# Specific deprecation decorators for known commands
def deprecate_daily_clarify(func: Callable) -> Callable:
    """Deprecation decorator specifically for daily_clarify command"""
    return deprecate_command(
        command="daily_clarify",
        alternative="gtd_coach.agent.workflows.daily_clarify.DailyClarifyWorkflow",
        removal_date="2026-02-22",
        warning_frequency="daily"
    )(func)


def deprecate_daily_capture(func: Callable) -> Callable:
    """Deprecation decorator specifically for daily_capture_legacy command"""
    return deprecate_command(
        command="daily_capture",
        alternative="gtd_coach.agent.workflows.daily_capture.DailyCaptureWorkflow",
        removal_date="2026-02-22",
        warning_frequency="daily"
    )(func)


def deprecate_daily_alignment(func: Callable) -> Callable:
    """Deprecation decorator specifically for daily_alignment command"""
    return deprecate_command(
        command="daily_alignment",
        alternative="gtd_coach.agent.workflows.daily_alignment.DailyAlignmentWorkflow",
        removal_date="2026-02-22",
        warning_frequency="daily"
    )(func)


def deprecate_parallel_runner(func: Callable) -> Callable:
    """Deprecation decorator for bridge/parallel_runner.py"""
    return deprecate_command(
        command="parallel_runner",
        alternative="Direct agent workflow usage",
        removal_date="2026-02-22",
        warning_frequency="weekly"
    )(func)


# Migration helper functions
def check_migration_feasibility(command: str) -> dict:
    """
    Check if a command is ready for migration based on telemetry.
    
    Returns:
        Dictionary with migration readiness metrics
    """
    # This would normally query Grafana/Prometheus
    # For now, return example metrics
    metrics = {
        "error_rate": 0.005,  # 0.5% error rate
        "p95_latency": 1500,  # 1.5 seconds
        "feature_parity": 0.95,  # 95% feature parity
        "adoption_rate": 0.75,  # 75% on agent
        "test_coverage": 0.90   # 90% test coverage
    }
    
    score = calculate_quality_score(command, metrics)
    update_migration_readiness(command, score)
    
    return {
        "command": command,
        "score": score,
        "metrics": metrics,
        "ready_for_migration": score >= 80,
        "ready_for_deletion": metrics["adoption_rate"] >= 0.95
    }


# Export public API
__all__ = [
    'deprecate_command',
    'track_agent_implementation',
    'deprecate_daily_clarify',
    'deprecate_daily_capture',
    'deprecate_daily_alignment',
    'deprecate_parallel_runner',
    'check_migration_feasibility',
    'DeprecationConfig'
]