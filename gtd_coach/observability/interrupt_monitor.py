#!/usr/bin/env python3
"""
Interrupt Monitor for GTD Coach
Provides detailed debugging and monitoring for LangGraph interrupt patterns
"""

import logging
import functools
import inspect
from typing import Any, Callable, Dict, Optional
from datetime import datetime

logger = logging.getLogger(__name__)

# Global tracer instance (set by runner)
_global_tracer = None


def set_global_tracer(tracer):
    """Set the global tracer instance for interrupt monitoring"""
    global _global_tracer
    _global_tracer = tracer
    logger.debug("Global tracer set for interrupt monitoring")


def get_global_tracer():
    """Get the global tracer instance"""
    return _global_tracer


def monitor_interrupt(tool_name: str = None):
    """
    Decorator to monitor interrupt calls within tools
    
    Args:
        tool_name: Optional tool name override
    """
    def decorator(func: Callable) -> Callable:
        actual_tool_name = tool_name or func.__name__
        
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            tracer = get_global_tracer()
            
            # Log tool invocation
            logger.debug(f"Tool {actual_tool_name} invoked with args: {args}, kwargs: {kwargs}")
            
            # Track tool start
            if tracer:
                tracer.trace_tool_call(actual_tool_name, kwargs, start=True)
            
            # Monkey-patch interrupt to track calls
            original_interrupt = None
            interrupt_called = False
            interrupt_value = None
            
            try:
                # Import interrupt from langgraph
                from langgraph.types import interrupt as original_interrupt_func
                original_interrupt = original_interrupt_func
                
                def tracked_interrupt(value):
                    nonlocal interrupt_called, interrupt_value
                    interrupt_called = True
                    interrupt_value = value
                    
                    logger.debug(f"INTERRUPT CALLED in {actual_tool_name}: {value}")
                    
                    # Track interrupt attempt
                    if tracer:
                        tracer.trace_interrupt_attempt(actual_tool_name, value)
                    
                    # Call original interrupt - this may raise GraphInterrupt
                    try:
                        result = original_interrupt_func(value)
                        # If we reach here, interrupt returned a value (resume case)
                        logger.debug(f"Interrupt returned value in {actual_tool_name}: {result}")
                        return result
                    except Exception as e:
                        # Check if this is a GraphInterrupt that should propagate
                        if "GraphInterrupt" in type(e).__name__ or "Interrupt" in type(e).__name__:
                            logger.info(f"GraphInterrupt raised in {actual_tool_name}, propagating...")
                            raise  # Let GraphInterrupt propagate normally
                        else:
                            # Handle other unexpected exceptions
                            logger.error(f"Unexpected error in interrupt: {e}")
                            raise
                
                # Replace interrupt in the function's globals
                if 'interrupt' in func.__globals__:
                    func.__globals__['interrupt'] = tracked_interrupt
                
                # Execute the function
                result = func(*args, **kwargs)
                
                # Check if interrupt was called but function completed (expected during resume)
                if interrupt_called:
                    # This is normal behavior when LangGraph resumes and returns cached values
                    logger.debug(f"Tool {actual_tool_name} completed with cached interrupt value during resume")
                    if tracer:
                        tracer.trace_event("interrupt.resumed", {
                            "tool": actual_tool_name,
                            "interrupt_value": str(interrupt_value),
                            "tool_result": str(result)[:100],
                            "note": "Normal behavior during LangGraph resume"
                        })
                
                # Track tool completion
                if tracer:
                    tracer.trace_tool_call(actual_tool_name, None, start=False)
                
                return result
                
            except Exception as e:
                # Check if this is a GraphInterrupt that should propagate
                # Import here to avoid circular dependency issues
                try:
                    from langgraph.errors import GraphInterrupt
                    if isinstance(e, GraphInterrupt):
                        logger.info(f"GraphInterrupt propagating from {actual_tool_name}")
                        raise  # Let GraphInterrupt propagate normally
                except ImportError:
                    # If we can't import GraphInterrupt, check by name
                    if "GraphInterrupt" in type(e).__name__ or "Interrupt" in type(e).__name__:
                        logger.info(f"Interrupt exception propagating from {actual_tool_name}")
                        raise
                
                # Log actual errors
                logger.error(f"Error in monitored tool {actual_tool_name}: {e}")
                if tracer:
                    tracer.trace_event("tool.error", {
                        "tool": actual_tool_name,
                        "error": str(e)
                    })
                raise
                
            finally:
                # Restore original interrupt if it was replaced
                if original_interrupt and 'interrupt' in func.__globals__:
                    func.__globals__['interrupt'] = original_interrupt
        
        return wrapper
    
    return decorator


def trace_interrupt_state(state: Dict, phase: str = "unknown"):
    """
    Trace the current state when an interrupt might occur
    
    Args:
        state: Current graph state
        phase: Current phase name
    """
    tracer = get_global_tracer()
    if not tracer:
        return
    
    state_info = {
        "phase": phase,
        "has_messages": "messages" in state,
        "message_count": len(state.get("messages", [])),
        "awaiting_input": state.get("awaiting_input", False),
        "interrupt_mode": state.get("interrupt_mode", None),
        "timestamp": datetime.now().isoformat()
    }
    
    tracer.trace_event("interrupt.state", state_info)
    logger.debug(f"Interrupt state traced: {state_info}")


class InterruptDebugger:
    """
    Context manager for detailed interrupt debugging
    """
    
    def __init__(self, context: str):
        """
        Initialize debugger context
        
        Args:
            context: Description of the current context
        """
        self.context = context
        self.start_time = None
        self.interrupt_count = 0
        self.events = []
    
    def __enter__(self):
        self.start_time = datetime.now()
        logger.debug(f"[INTERRUPT DEBUG] Entering context: {self.context}")
        
        tracer = get_global_tracer()
        if tracer:
            tracer.trace_event("debug.interrupt.start", {"context": self.context})
        
        return self
    
    def log_event(self, event: str, data: Dict = None):
        """Log an event during debugging"""
        self.events.append({
            "event": event,
            "data": data,
            "timestamp": datetime.now().isoformat()
        })
        
        logger.debug(f"[INTERRUPT DEBUG] {event}: {data}")
        
        tracer = get_global_tracer()
        if tracer:
            tracer.trace_event(f"debug.{event}", data)
    
    def check_interrupt_result(self, result: Any) -> bool:
        """
        Check if a result contains interrupt data
        
        Args:
            result: Result to check
            
        Returns:
            True if interrupt detected
        """
        has_interrupt = False
        
        if isinstance(result, dict) and '__interrupt__' in result:
            has_interrupt = True
            self.interrupt_count += 1
            self.log_event("interrupt_detected", {
                "interrupt_data": str(result['__interrupt__'])[:200],
                "count": self.interrupt_count
            })
        
        return has_interrupt
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        duration = (datetime.now() - self.start_time).total_seconds()
        
        summary = {
            "context": self.context,
            "duration_seconds": duration,
            "interrupt_count": self.interrupt_count,
            "event_count": len(self.events),
            "events": self.events[-5:] if self.events else []  # Last 5 events
        }
        
        logger.debug(f"[INTERRUPT DEBUG] Exiting context: {summary}")
        
        tracer = get_global_tracer()
        if tracer:
            tracer.trace_event("debug.interrupt.end", summary)
        
        # Log exception if present
        if exc_type:
            logger.debug(f"[INTERRUPT DEBUG] Exception in context: {exc_type.__name__}: {exc_val}")


def analyze_interrupt_failure(
    expected_interrupt: bool,
    actual_result: Any,
    tool_name: str = None,
    additional_context: Dict = None
):
    """
    Analyze why an interrupt might have failed
    
    Args:
        expected_interrupt: Whether an interrupt was expected
        actual_result: The actual result received
        tool_name: Name of the tool that should have interrupted
        additional_context: Additional context for debugging
    """
    analysis = {
        "expected_interrupt": expected_interrupt,
        "got_interrupt": isinstance(actual_result, dict) and '__interrupt__' in actual_result,
        "tool_name": tool_name,
        "result_type": type(actual_result).__name__,
        "result_keys": list(actual_result.keys()) if isinstance(actual_result, dict) else None,
        "context": additional_context or {}
    }
    
    # Analyze the failure
    if expected_interrupt and not analysis["got_interrupt"]:
        possible_causes = []
        
        # Check common issues
        if not analysis["result_keys"]:
            possible_causes.append("Result is not a dictionary")
        elif "messages" in analysis["result_keys"]:
            possible_causes.append("Got messages instead of interrupt - tool might have completed")
        
        if tool_name and "conversation" in tool_name.lower():
            possible_causes.append("Conversation tool might not be properly wrapped with interrupt")
        
        if not possible_causes:
            possible_causes.append("Unknown - interrupt() might not be raising properly")
        
        analysis["possible_causes"] = possible_causes
        
        logger.warning(f"INTERRUPT FAILURE ANALYSIS: {analysis}")
    else:
        logger.debug(f"Interrupt check passed: {analysis}")
    
    # Track in tracer
    tracer = get_global_tracer()
    if tracer:
        tracer.trace_event(
            "interrupt.analysis",
            analysis,
            1.0 if analysis["got_interrupt"] == expected_interrupt else 0.0
        )
    
    return analysis