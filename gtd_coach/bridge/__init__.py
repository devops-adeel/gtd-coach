"""
Bridge components for incremental migration from legacy to LangGraph agent system.
Implements the Strangler Pattern for gradual replacement.
"""

from .state_converter import StateBridge
from .parallel_runner import ParallelRunner
from .circuit_breaker import AgentCircuitBreaker

__all__ = [
    'StateBridge',
    'ParallelRunner',
    'AgentCircuitBreaker',
]