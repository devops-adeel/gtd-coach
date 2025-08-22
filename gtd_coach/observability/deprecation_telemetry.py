#!/usr/bin/env python3
"""
OpenTelemetry instrumentation for deprecation tracking and migration monitoring.
Sends telemetry to Grafana via OTLP collector (Alloy).
"""

import os
import hashlib
from datetime import datetime, timedelta
from typing import Dict, Optional, Callable, Any
from functools import wraps
from dataclasses import dataclass

from opentelemetry import trace, metrics
from opentelemetry.exporter.otlp.proto.grpc.metric_exporter import OTLPMetricExporter
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
from opentelemetry.sdk.resources import Resource
from opentelemetry.semconv.resource import ResourceAttributes
from opentelemetry.trace import Status, StatusCode
from opentelemetry.metrics import CallbackOptions, Observation

# Configuration
OTLP_ENDPOINT = os.getenv("OTLP_ENDPOINT", "http://alloy.local:4317")
GRAFANA_ENDPOINT = os.getenv("GRAFANA_ENDPOINT", "http://grafana.local:3000")
GRAFANA_API_KEY = os.getenv("GRAFANA_API_KEY", "")
SERVICE_NAME = "gtd-coach"

# Initialize OpenTelemetry
resource = Resource.create({
    ResourceAttributes.SERVICE_NAME: SERVICE_NAME,
    ResourceAttributes.SERVICE_VERSION: "1.0.0",
    "deployment.environment": "production",
    "telemetry.sdk.language": "python",
})

# Setup tracing
trace_provider = TracerProvider(resource=resource)
trace_processor = BatchSpanProcessor(
    OTLPSpanExporter(endpoint=OTLP_ENDPOINT, insecure=True)
)
trace_provider.add_span_processor(trace_processor)
trace.set_tracer_provider(trace_provider)

# Setup metrics
metric_reader = PeriodicExportingMetricReader(
    exporter=OTLPMetricExporter(endpoint=OTLP_ENDPOINT, insecure=True),
    export_interval_millis=30000,  # Export every 30 seconds
)
metric_provider = MeterProvider(resource=resource, metric_readers=[metric_reader])
metrics.set_meter_provider(metric_provider)

# Get tracer and meter
tracer = trace.get_tracer(f"{SERVICE_NAME}.deprecation")
meter = metrics.get_meter(f"{SERVICE_NAME}.deprecation")

# Create metrics for deprecation tracking
legacy_usage_counter = meter.create_counter(
    "gtd_coach.legacy.usage",
    description="Count of legacy command invocations",
    unit="1"
)

deprecation_warnings_counter = meter.create_counter(
    "gtd_coach.deprecation.warnings",
    description="Count of deprecation warnings shown to users",
    unit="1"
)

migration_errors_counter = meter.create_counter(
    "gtd_coach.migration.errors",
    description="Errors encountered during migration",
    unit="1"
)

command_duration_histogram = meter.create_histogram(
    "gtd_coach.command.duration",
    description="Duration of command execution",
    unit="ms"
)

quality_score_histogram = meter.create_histogram(
    "gtd_coach.quality.score",
    description="Quality score comparison between implementations",
    unit="1"
)

# Observable gauges for migration readiness
migration_readiness_scores: Dict[str, float] = {}

def _get_migration_readiness(options: CallbackOptions) -> list[Observation]:
    """Callback for migration readiness gauge"""
    observations = []
    for command, score in migration_readiness_scores.items():
        observations.append(
            Observation(score, {"command": command})
        )
    return observations

migration_readiness_gauge = meter.create_observable_gauge(
    "gtd_coach.migration.readiness",
    callbacks=[_get_migration_readiness],
    description="Migration readiness percentage (0-100)",
    unit="%"
)

# Track active migrations
active_migrations: Dict[str, datetime] = {}

def _get_days_until_removal(options: CallbackOptions) -> list[Observation]:
    """Callback for days until removal gauge"""
    observations = []
    for command, removal_date in active_migrations.items():
        days_left = (removal_date - datetime.now()).days
        observations.append(
            Observation(max(0, days_left), {"command": command})
        )
    return observations

days_until_removal_gauge = meter.create_observable_gauge(
    "gtd_coach.deprecation.days_until_removal",
    callbacks=[_get_days_until_removal],
    description="Days until legacy code removal",
    unit="d"
)


@dataclass
class DeprecationConfig:
    """Configuration for deprecating a command"""
    command: str
    deprecated_since: str = "2025-08-22"
    removal_date: str = "2026-02-22"  # 6 months default
    alternative: Optional[str] = None
    warning_frequency: str = "daily"  # daily, weekly, always


def get_anonymous_user_id() -> str:
    """Get anonymous user ID from environment or generate one"""
    user = os.getenv("USER", "unknown")
    return hashlib.sha256(user.encode()).hexdigest()[:8]


def should_show_warning(command: str, frequency: str = "daily") -> bool:
    """Determine if deprecation warning should be shown"""
    # Simple implementation - can be enhanced with persistent storage
    import random
    
    frequencies = {
        "always": 1.0,
        "daily": 0.1,
        "weekly": 0.02,
        "monthly": 0.005
    }
    
    return random.random() < frequencies.get(frequency, 0.1)


def show_deprecation_warning(config: DeprecationConfig):
    """Display deprecation warning to user"""
    removal_date = datetime.fromisoformat(config.removal_date)
    days_left = (removal_date - datetime.now()).days
    
    warning = f"""
╔══════════════════════════════════════════════════════════════╗
║                    ⚠️  DEPRECATION WARNING                    ║
╠══════════════════════════════════════════════════════════════╣
║ The legacy {config.command} command is deprecated and will   ║
║ be removed on {config.removal_date}.                         ║
║                                                              ║
║ Days remaining: {days_left:3d}                                      ║
║                                                              ║"""
    
    if config.alternative:
        warning += f"""║ Please use: {config.alternative:<46}║
║                                                              ║"""
    
    warning += """║ To use the new agent-based implementation:                  ║
║   unset USE_LEGACY_{config.command.upper()}                 ║
║                                                              ║
║ View migration progress:                                     ║
║   http://grafana.local:3000/d/gtd-migration                 ║
╚══════════════════════════════════════════════════════════════╝
"""
    
    print(warning)


def track_deprecation(config: DeprecationConfig):
    """Decorator to track deprecated command usage"""
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            # Start trace span
            with tracer.start_as_current_span(f"legacy.{config.command}") as span:
                # Add span attributes
                span.set_attributes({
                    "gtd.legacy.command": config.command,
                    "gtd.legacy.removal_date": config.removal_date,
                    "gtd.legacy.alternative": config.alternative or "",
                    "gtd.user.id": get_anonymous_user_id(),
                    "gtd.implementation": "legacy"
                })
                
                # Track usage metric
                legacy_usage_counter.add(1, {
                    "command": config.command,
                    "implementation": "legacy"
                })
                
                # Show deprecation warning if appropriate
                if should_show_warning(config.command, config.warning_frequency):
                    show_deprecation_warning(config)
                    deprecation_warnings_counter.add(1, {
                        "command": config.command
                    })
                    span.add_event("deprecation_warning_shown")
                
                # Track removal date
                active_migrations[config.command] = datetime.fromisoformat(config.removal_date)
                
                # Measure execution time
                import time
                start_time = time.time()
                
                try:
                    # Execute original function
                    result = func(*args, **kwargs)
                    
                    # Record success
                    span.set_status(Status(StatusCode.OK))
                    
                    # Record duration
                    duration_ms = (time.time() - start_time) * 1000
                    command_duration_histogram.record(duration_ms, {
                        "command": config.command,
                        "implementation": "legacy",
                        "status": "success"
                    })
                    
                    return result
                    
                except Exception as e:
                    # Record error
                    span.record_exception(e)
                    span.set_status(Status(StatusCode.ERROR, str(e)))
                    
                    # Track migration errors
                    migration_errors_counter.add(1, {
                        "command": config.command,
                        "error_type": type(e).__name__
                    })
                    
                    # Record duration with error status
                    duration_ms = (time.time() - start_time) * 1000
                    command_duration_histogram.record(duration_ms, {
                        "command": config.command,
                        "implementation": "legacy",
                        "status": "error"
                    })
                    
                    raise
                    
        return wrapper
    return decorator


def track_agent_usage(command: str):
    """Decorator to track agent implementation usage for comparison"""
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            with tracer.start_as_current_span(f"agent.{command}") as span:
                span.set_attributes({
                    "gtd.command": command,
                    "gtd.implementation": "agent",
                    "gtd.user.id": get_anonymous_user_id()
                })
                
                # Track usage
                legacy_usage_counter.add(1, {
                    "command": command,
                    "implementation": "agent"
                })
                
                # Measure execution time
                import time
                start_time = time.time()
                
                try:
                    result = func(*args, **kwargs)
                    span.set_status(Status(StatusCode.OK))
                    
                    # Record duration
                    duration_ms = (time.time() - start_time) * 1000
                    command_duration_histogram.record(duration_ms, {
                        "command": command,
                        "implementation": "agent",
                        "status": "success"
                    })
                    
                    return result
                    
                except Exception as e:
                    span.record_exception(e)
                    span.set_status(Status(StatusCode.ERROR, str(e)))
                    
                    duration_ms = (time.time() - start_time) * 1000
                    command_duration_histogram.record(duration_ms, {
                        "command": command,
                        "implementation": "agent",
                        "status": "error"
                    })
                    
                    raise
                    
        return wrapper
    return decorator


def update_migration_readiness(command: str, score: float):
    """Update migration readiness score for a command"""
    migration_readiness_scores[command] = min(100, max(0, score))
    
    # Add trace event
    span = trace.get_current_span()
    if span:
        span.add_event("migration_readiness_updated", {
            "command": command,
            "score": score
        })


def calculate_quality_score(command: str, metrics: Dict[str, float]) -> float:
    """Calculate quality score based on multiple metrics"""
    weights = {
        "error_rate": 0.3,    # Lower is better
        "performance": 0.25,  # Lower is better
        "features": 0.25,     # Higher is better
        "adoption": 0.1,      # Higher is better
        "coverage": 0.1       # Higher is better
    }
    
    # Normalize metrics (0-100 scale)
    normalized = {
        "error_rate": max(0, 100 - metrics.get("error_rate", 0) * 10000),
        "performance": max(0, 100 - metrics.get("p95_latency", 0) / 20),
        "features": metrics.get("feature_parity", 0) * 100,
        "adoption": metrics.get("adoption_rate", 0) * 100,
        "coverage": metrics.get("test_coverage", 0) * 100
    }
    
    # Calculate weighted score
    score = sum(normalized[k] * weights[k] for k in weights)
    
    # Record quality score
    quality_score_histogram.record(score, {"command": command})
    
    return score


# Export public API
__all__ = [
    'track_deprecation',
    'track_agent_usage',
    'DeprecationConfig',
    'update_migration_readiness',
    'calculate_quality_score',
    'tracer',
    'meter'
]