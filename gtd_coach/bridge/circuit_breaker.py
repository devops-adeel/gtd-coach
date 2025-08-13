#!/usr/bin/env python3
"""
Circuit breaker pattern for resilient agent calls with automatic fallback.
Prevents cascading failures and provides graceful degradation.
"""

import asyncio
import logging
import time
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Callable, Dict, Optional
from dataclasses import dataclass, field
import json
from pathlib import Path

logger = logging.getLogger(__name__)


class CircuitState(Enum):
    """Circuit breaker states"""
    CLOSED = "closed"  # Normal operation
    OPEN = "open"      # Failing, use fallback
    HALF_OPEN = "half_open"  # Testing recovery


@dataclass
class CircuitStats:
    """Statistics for circuit breaker monitoring"""
    total_calls: int = 0
    successful_calls: int = 0
    failed_calls: int = 0
    consecutive_failures: int = 0
    last_failure_time: Optional[datetime] = None
    last_success_time: Optional[datetime] = None
    total_latency_ms: float = 0.0
    state_changes: list = field(default_factory=list)


class AgentCircuitBreaker:
    """
    Circuit breaker for agent system calls with automatic fallback to legacy.
    
    States:
    - CLOSED: Normal operation, agent calls go through
    - OPEN: Circuit is tripped, all calls go to fallback (legacy)
    - HALF_OPEN: Testing if agent has recovered
    
    Transitions:
    - CLOSED -> OPEN: After threshold failures
    - OPEN -> HALF_OPEN: After cooldown period
    - HALF_OPEN -> CLOSED: If test succeeds
    - HALF_OPEN -> OPEN: If test fails
    """
    
    def __init__(self,
                 failure_threshold: int = 3,
                 error_rate_threshold: float = 0.5,
                 timeout_ms: int = 5000,
                 cooldown_seconds: int = 60,
                 half_open_max_calls: int = 3,
                 metrics_dir: Optional[Path] = None):
        """
        Initialize circuit breaker.
        
        Args:
            failure_threshold: Consecutive failures to trip circuit
            error_rate_threshold: Error rate (0-1) to trip circuit
            timeout_ms: Timeout for agent calls in milliseconds
            cooldown_seconds: Time to wait before testing recovery
            half_open_max_calls: Max calls to test in half-open state
            metrics_dir: Directory to save circuit metrics
        """
        self.failure_threshold = failure_threshold
        self.error_rate_threshold = error_rate_threshold
        self.timeout_ms = timeout_ms
        self.cooldown_seconds = cooldown_seconds
        self.half_open_max_calls = half_open_max_calls
        
        # State management
        self.state = CircuitState.CLOSED
        self.stats = CircuitStats()
        self.half_open_calls = 0
        self.last_state_change = datetime.now()
        
        # Metrics persistence
        self.metrics_dir = metrics_dir or Path.home() / "gtd-coach" / "data" / "circuit_metrics"
        self.metrics_dir.mkdir(parents=True, exist_ok=True)
        
        self.logger = logging.getLogger(__name__)
    
    async def call_agent(self,
                         agent_func: Callable,
                         fallback_func: Callable,
                         *args,
                         **kwargs) -> Any:
        """
        Call agent with circuit breaker protection.
        
        Args:
            agent_func: Async function to call agent system
            fallback_func: Sync/async function to call legacy system
            *args, **kwargs: Arguments to pass to functions
            
        Returns:
            Result from agent or fallback
        """
        # Check circuit state
        if self.state == CircuitState.OPEN:
            if self._should_attempt_reset():
                self._transition_to_half_open()
            else:
                self.logger.info("Circuit OPEN - using fallback")
                return await self._call_fallback(fallback_func, *args, **kwargs)
        
        # Try agent call
        try:
            start_time = time.perf_counter()
            
            # Add timeout protection
            result = await asyncio.wait_for(
                agent_func(*args, **kwargs),
                timeout=self.timeout_ms / 1000.0
            )
            
            elapsed_ms = (time.perf_counter() - start_time) * 1000
            
            # Record success
            self._record_success(elapsed_ms)
            
            # Handle half-open state
            if self.state == CircuitState.HALF_OPEN:
                self.half_open_calls += 1
                if self.half_open_calls >= self.half_open_max_calls:
                    # Enough successful calls, close circuit
                    self._transition_to_closed()
            
            return result
            
        except asyncio.TimeoutError:
            self.logger.warning(f"Agent call timed out after {self.timeout_ms}ms")
            self._record_failure("timeout")
            return await self._call_fallback(fallback_func, *args, **kwargs)
            
        except Exception as e:
            self.logger.error(f"Agent call failed: {e}")
            self._record_failure(str(e))
            return await self._call_fallback(fallback_func, *args, **kwargs)
    
    def call_agent_sync(self,
                       agent_func: Callable,
                       fallback_func: Callable,
                       *args,
                       **kwargs) -> Any:
        """
        Synchronous version for non-async contexts.
        
        Args:
            agent_func: Function to call agent system
            fallback_func: Function to call legacy system
            *args, **kwargs: Arguments to pass to functions
            
        Returns:
            Result from agent or fallback
        """
        # Check circuit state
        if self.state == CircuitState.OPEN:
            if self._should_attempt_reset():
                self._transition_to_half_open()
            else:
                self.logger.info("Circuit OPEN - using fallback")
                return fallback_func(*args, **kwargs)
        
        # Try agent call
        try:
            start_time = time.perf_counter()
            
            # Call with timeout (using threading for sync timeout)
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(agent_func, *args, **kwargs)
                result = future.result(timeout=self.timeout_ms / 1000.0)
            
            elapsed_ms = (time.perf_counter() - start_time) * 1000
            
            # Record success
            self._record_success(elapsed_ms)
            
            # Handle half-open state
            if self.state == CircuitState.HALF_OPEN:
                self.half_open_calls += 1
                if self.half_open_calls >= self.half_open_max_calls:
                    self._transition_to_closed()
            
            return result
            
        except concurrent.futures.TimeoutError:
            self.logger.warning(f"Agent call timed out after {self.timeout_ms}ms")
            self._record_failure("timeout")
            return fallback_func(*args, **kwargs)
            
        except Exception as e:
            self.logger.error(f"Agent call failed: {e}")
            self._record_failure(str(e))
            return fallback_func(*args, **kwargs)
    
    async def _call_fallback(self, fallback_func: Callable, *args, **kwargs) -> Any:
        """Call fallback function (handles both sync and async)"""
        if asyncio.iscoroutinefunction(fallback_func):
            return await fallback_func(*args, **kwargs)
        else:
            # Run sync function in executor
            loop = asyncio.get_event_loop()
            return await loop.run_in_executor(None, fallback_func, *args, **kwargs)
    
    def _record_success(self, latency_ms: float):
        """Record successful call"""
        self.stats.total_calls += 1
        self.stats.successful_calls += 1
        self.stats.consecutive_failures = 0
        self.stats.last_success_time = datetime.now()
        self.stats.total_latency_ms += latency_ms
        
        # Check if we should close circuit (in half-open state)
        if self.state == CircuitState.HALF_OPEN:
            self.logger.info(f"Successful call in HALF_OPEN state ({self.half_open_calls}/{self.half_open_max_calls})")
    
    def _record_failure(self, error: str):
        """Record failed call and check if circuit should open"""
        self.stats.total_calls += 1
        self.stats.failed_calls += 1
        self.stats.consecutive_failures += 1
        self.stats.last_failure_time = datetime.now()
        
        # Check if we should open circuit
        if self.state == CircuitState.CLOSED:
            # Check consecutive failures
            if self.stats.consecutive_failures >= self.failure_threshold:
                self._transition_to_open(f"Consecutive failures: {self.stats.consecutive_failures}")
                return
            
            # Check error rate (if we have enough samples)
            if self.stats.total_calls >= 10:
                error_rate = self.stats.failed_calls / self.stats.total_calls
                if error_rate >= self.error_rate_threshold:
                    self._transition_to_open(f"Error rate: {error_rate:.1%}")
                    return
        
        elif self.state == CircuitState.HALF_OPEN:
            # Failed in half-open, go back to open
            self._transition_to_open(f"Failed in HALF_OPEN state")
    
    def _should_attempt_reset(self) -> bool:
        """Check if enough time has passed to try recovery"""
        if self.state != CircuitState.OPEN:
            return False
        
        time_since_change = datetime.now() - self.last_state_change
        return time_since_change.total_seconds() >= self.cooldown_seconds
    
    def _transition_to_open(self, reason: str):
        """Transition to OPEN state (circuit tripped)"""
        self.logger.warning(f"⚠️ Circuit breaker OPEN: {reason}")
        self.state = CircuitState.OPEN
        self.last_state_change = datetime.now()
        self.stats.state_changes.append({
            'timestamp': self.last_state_change.isoformat(),
            'transition': f"{self.state.value} -> OPEN",
            'reason': reason
        })
        self._save_metrics()
    
    def _transition_to_closed(self):
        """Transition to CLOSED state (normal operation)"""
        self.logger.info("✅ Circuit breaker CLOSED: Agent recovered")
        previous_state = self.state
        self.state = CircuitState.CLOSED
        self.last_state_change = datetime.now()
        self.half_open_calls = 0
        self.stats.consecutive_failures = 0
        self.stats.state_changes.append({
            'timestamp': self.last_state_change.isoformat(),
            'transition': f"{previous_state.value} -> CLOSED",
            'reason': "Recovery successful"
        })
        self._save_metrics()
    
    def _transition_to_half_open(self):
        """Transition to HALF_OPEN state (testing recovery)"""
        self.logger.info("🔄 Circuit breaker HALF_OPEN: Testing recovery")
        self.state = CircuitState.HALF_OPEN
        self.last_state_change = datetime.now()
        self.half_open_calls = 0
        self.stats.state_changes.append({
            'timestamp': self.last_state_change.isoformat(),
            'transition': "OPEN -> HALF_OPEN",
            'reason': f"Cooldown period ({self.cooldown_seconds}s) elapsed"
        })
    
    def get_status(self) -> Dict[str, Any]:
        """Get current circuit breaker status"""
        error_rate = (
            self.stats.failed_calls / self.stats.total_calls
            if self.stats.total_calls > 0 else 0
        )
        
        avg_latency = (
            self.stats.total_latency_ms / self.stats.successful_calls
            if self.stats.successful_calls > 0 else 0
        )
        
        return {
            'state': self.state.value,
            'stats': {
                'total_calls': self.stats.total_calls,
                'successful_calls': self.stats.successful_calls,
                'failed_calls': self.stats.failed_calls,
                'error_rate': error_rate,
                'consecutive_failures': self.stats.consecutive_failures,
                'avg_latency_ms': avg_latency
            },
            'last_failure': self.stats.last_failure_time.isoformat() if self.stats.last_failure_time else None,
            'last_success': self.stats.last_success_time.isoformat() if self.stats.last_success_time else None,
            'time_in_current_state': (datetime.now() - self.last_state_change).total_seconds()
        }
    
    def reset(self):
        """Reset circuit breaker to initial state"""
        self.state = CircuitState.CLOSED
        self.stats = CircuitStats()
        self.half_open_calls = 0
        self.last_state_change = datetime.now()
        self.logger.info("Circuit breaker reset")
    
    def _save_metrics(self):
        """Save metrics to file for monitoring"""
        metrics_file = self.metrics_dir / f"circuit_{datetime.now().strftime('%Y%m%d')}.json"
        
        metrics = {
            'timestamp': datetime.now().isoformat(),
            'status': self.get_status(),
            'state_history': self.stats.state_changes[-20:]  # Keep last 20 transitions
        }
        
        # Append to daily file
        existing_data = []
        if metrics_file.exists():
            try:
                with open(metrics_file, 'r') as f:
                    existing_data = json.load(f)
            except:
                pass
        
        existing_data.append(metrics)
        
        with open(metrics_file, 'w') as f:
            json.dump(existing_data, f, indent=2, default=str)


def test_circuit_breaker():
    """Test circuit breaker functionality"""
    import asyncio
    
    # Create circuit breaker
    breaker = AgentCircuitBreaker(
        failure_threshold=2,
        timeout_ms=100,
        cooldown_seconds=1
    )
    
    # Mock functions
    async def failing_agent(*args):
        raise Exception("Agent failed")
    
    async def working_agent(*args):
        await asyncio.sleep(0.01)
        return "agent_result"
    
    def legacy_fallback(*args):
        return "legacy_result"
    
    async def run_tests():
        # Test 1: Circuit should open after failures
        result1 = await breaker.call_agent(failing_agent, legacy_fallback)
        assert result1 == "legacy_result"
        
        result2 = await breaker.call_agent(failing_agent, legacy_fallback)
        assert result2 == "legacy_result"
        
        # Circuit should be open now
        assert breaker.state == CircuitState.OPEN
        print(f"✅ Circuit opened after {breaker.failure_threshold} failures")
        
        # Test 2: Calls should go to fallback when open
        result3 = await breaker.call_agent(working_agent, legacy_fallback)
        assert result3 == "legacy_result"
        print("✅ Circuit open - using fallback")
        
        # Test 3: Wait for cooldown and test recovery
        await asyncio.sleep(1.1)
        
        # Should transition to half-open and test
        result4 = await breaker.call_agent(working_agent, legacy_fallback)
        assert result4 == "agent_result"
        assert breaker.state == CircuitState.HALF_OPEN
        print("✅ Circuit half-open - testing recovery")
        
        # More successful calls should close circuit
        for _ in range(breaker.half_open_max_calls - 1):
            await breaker.call_agent(working_agent, legacy_fallback)
        
        assert breaker.state == CircuitState.CLOSED
        print("✅ Circuit closed - recovery complete")
        
        # Print status
        status = breaker.get_status()
        print(f"\nFinal status: {json.dumps(status, indent=2, default=str)}")
    
    # Run async tests
    asyncio.run(run_tests())
    print("\n✅ All circuit breaker tests passed")


if __name__ == "__main__":
    test_circuit_breaker()