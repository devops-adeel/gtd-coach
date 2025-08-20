#!/usr/bin/env python3
"""
Enhanced Langfuse Tracer for GTD Coach
Provides comprehensive observability for LangGraph agents with interrupt support
"""

import logging
import time
from typing import Dict, Any, Optional, List
from datetime import datetime
from contextlib import contextmanager

try:
    from langfuse import Langfuse, get_client
    from langfuse.langchain import CallbackHandler
    LANGFUSE_AVAILABLE = True
except ImportError:
    LANGFUSE_AVAILABLE = False
    CallbackHandler = object

logger = logging.getLogger(__name__)


class LangfuseTracer:
    """
    Enhanced tracer for comprehensive LangGraph observability
    Tracks interrupts, tool calls, state transitions, and stream lifecycle
    """
    
    def __init__(self, session_id: str, user_id: str = None, metadata: Dict = None):
        """
        Initialize the enhanced tracer
        
        Args:
            session_id: Unique session identifier
            user_id: User identifier for grouping sessions
            metadata: Additional metadata for the session
        """
        self.session_id = session_id
        self.user_id = user_id or "anonymous"
        self.metadata = metadata or {}
        
        # Track metrics
        self.metrics = {
            "interrupt_attempts": 0,
            "interrupt_captures": 0,
            "interrupt_resumes": 0,
            "tool_calls": 0,
            "tool_completions": 0,
            "stream_chunks": 0,
            "phase_transitions": 0,
            "context_overflows": 0,
            "memories_retrieved": 0,
            "memories_used": 0
        }
        
        # Track interrupt state
        self.interrupt_stack = []
        self.pending_interrupts = []
        
        # Initialize Langfuse handler
        self.handler = None
        self.langfuse_client = None
        
        if LANGFUSE_AVAILABLE:
            try:
                # Create handler without parameters - session_id will be passed via config metadata
                # This is the correct pattern for Langfuse v3 SDK per documentation
                # Reference: https://langfuse.com/docs/integrations/langchain/tracing
                self.handler = CallbackHandler()
                self.langfuse_client = get_client()
                logger.info(f"LangfuseTracer initialized for session {session_id}")
                logger.debug(f"Session ID {session_id} will be passed via config metadata")
            except Exception as e:
                logger.warning(f"Failed to initialize Langfuse handler: {e}")
    
    def get_handler(self) -> Optional[CallbackHandler]:
        """Get the Langfuse callback handler for LangChain integration"""
        return self.handler
    
    def trace_event(self, event_type: str, data: Dict = None, score: float = None):
        """
        Trace a custom event with optional scoring
        
        Args:
            event_type: Type of event (e.g., "interrupt.attempt", "tool.start", "memory.retrieved")
            data: Event data
            score: Optional score for the event
        """
        if not self.langfuse_client:
            return
        
        try:
            # Handle memory-specific events
            if event_type.startswith("memory."):
                if event_type == "memory.retrieved":
                    # Track how many memories were retrieved
                    count = data.get("count", 1) if data else 1
                    self.metrics["memories_retrieved"] += count
                    logger.debug(f"Retrieved {count} memories (total: {self.metrics['memories_retrieved']})")
                    
                elif event_type == "memory.used":
                    # Track when a retrieved memory is actually used in response
                    self.metrics["memories_used"] += 1
                    logger.debug(f"Memory used (total: {self.metrics['memories_used']})")
                    
                    # Calculate and score memory hit rate
                    if self.metrics["memories_retrieved"] > 0:
                        hit_rate = self.metrics["memories_used"] / self.metrics["memories_retrieved"]
                        self.langfuse_client.score(
                            name="memory_hit_rate",
                            value=hit_rate,
                            comment=f"Used {self.metrics['memories_used']} of {self.metrics['memories_retrieved']} retrieved memories",
                            data_type="NUMERIC"
                        )
                        logger.info(f"Memory hit rate: {hit_rate:.2%} ({self.metrics['memories_used']}/{self.metrics['memories_retrieved']})")
            
            # Create observation for the event (regular scoring)
            if score is not None:
                self.langfuse_client.score(
                    name=event_type,
                    value=score,
                    comment=str(data) if data else None,
                    data_type="NUMERIC"
                )
            
            # Log structured event data
            logger.debug(f"Traced event: {event_type} - {data}")
            
        except Exception as e:
            logger.debug(f"Failed to trace event {event_type}: {e}")
    
    def trace_interrupt_attempt(self, tool_name: str, prompt: Any):
        """
        Trace when an interrupt is attempted by a tool
        
        Args:
            tool_name: Name of the tool calling interrupt
            prompt: The prompt/question being interrupted for
        """
        self.metrics["interrupt_attempts"] += 1
        
        interrupt_data = {
            "tool": tool_name,
            "prompt": str(prompt),
            "timestamp": datetime.now().isoformat(),
            "attempt_number": self.metrics["interrupt_attempts"]
        }
        
        self.interrupt_stack.append(interrupt_data)
        self.trace_event("interrupt.attempt", interrupt_data, 1.0)
        
        logger.info(f"Interrupt attempted by {tool_name}: {prompt}")
    
    def trace_interrupt_captured(self, interrupt_data: Any):
        """
        Trace when an interrupt is successfully captured in the stream
        
        Args:
            interrupt_data: The interrupt data from __interrupt__ key
        """
        self.metrics["interrupt_captures"] += 1
        
        capture_data = {
            "interrupt_data": str(interrupt_data),
            "pending_count": len(self.interrupt_stack),
            "capture_number": self.metrics["interrupt_captures"]
        }
        
        self.trace_event("interrupt.captured", capture_data, 1.0)
        
        # Calculate success rate
        if self.metrics["interrupt_attempts"] > 0:
            success_rate = self.metrics["interrupt_captures"] / self.metrics["interrupt_attempts"]
            self.trace_event("interrupt.success_rate", {"rate": success_rate}, success_rate)
        
        logger.info(f"Interrupt captured: {interrupt_data}")
    
    @contextmanager
    def span_interrupt(self, interrupt_type: str, prompt: str = None):
        """
        Context manager for tracing interrupt operations with custom spans
        Following Langfuse documentation pattern
        
        Args:
            interrupt_type: Type of interrupt (e.g., "check_in", "confirmation", "input")
            prompt: Optional prompt being shown to user
            
        Example:
            with tracer.span_interrupt("check_in", prompt="Ready to continue?"):
                response = check_in_with_user()
        """
        if not self.langfuse_client:
            yield None
            return
        
        try:
            # Create custom span for interrupt
            from langfuse import Langfuse
            langfuse = Langfuse()
            
            with langfuse.start_as_current_span(
                name=f"🔔-interrupt-{interrupt_type}",
                trace_context={"trace_id": self.session_id}
            ) as span:
                span.update_trace(
                    input=prompt or f"Interrupt: {interrupt_type}",
                    metadata={
                        "interrupt_type": interrupt_type,
                        "session_id": self.session_id,
                        "timestamp": datetime.now().isoformat()
                    }
                )
                
                start_time = time.time()
                yield span
                
                # Update span with timing after completion
                response_time = time.time() - start_time
                span.update_trace(
                    output=f"Interrupt handled in {response_time:.2f}s",
                    metadata={"response_time_seconds": response_time}
                )
                
                # Score the interrupt response time
                span.score_trace(
                    name="interrupt_response_time",
                    value=response_time,
                    data_type="NUMERIC",
                    comment=f"{interrupt_type} interrupt"
                )
                
        except Exception as e:
            logger.debug(f"Failed to create interrupt span: {e}")
            yield None
    
    def trace_interrupt_resume(self, user_input: str):
        """
        Trace when execution resumes after an interrupt
        
        Args:
            user_input: The user input provided to resume
        """
        self.metrics["interrupt_resumes"] += 1
        
        resume_data = {
            "user_input": user_input,
            "resume_number": self.metrics["interrupt_resumes"],
            "pending_interrupts": len(self.interrupt_stack)
        }
        
        self.trace_event("interrupt.resume", resume_data, 1.0)
        
        # Pop from interrupt stack if available
        if self.interrupt_stack:
            completed = self.interrupt_stack.pop()
            self.trace_event("interrupt.completed", completed)
        
        logger.info(f"Interrupt resumed with: {user_input}")
    
    def trace_tool_call(self, tool_name: str, args: Dict = None, start: bool = True):
        """
        Trace tool call lifecycle
        
        Args:
            tool_name: Name of the tool
            args: Tool arguments
            start: True if tool is starting, False if completing
        """
        if start:
            self.metrics["tool_calls"] += 1
            self.trace_event("tool.start", {
                "name": tool_name,
                "args": args,
                "call_number": self.metrics["tool_calls"]
            })
        else:
            self.metrics["tool_completions"] += 1
            self.trace_event("tool.complete", {
                "name": tool_name,
                "completion_number": self.metrics["tool_completions"]
            })
            
            # Calculate completion rate
            if self.metrics["tool_calls"] > 0:
                completion_rate = self.metrics["tool_completions"] / self.metrics["tool_calls"]
                self.trace_event("tool.completion_rate", {"rate": completion_rate}, completion_rate)
    
    def trace_stream_chunk(self, chunk: Any, chunk_number: int = None):
        """
        Trace stream chunk processing
        
        Args:
            chunk: The stream chunk
            chunk_number: Optional chunk number
        """
        self.metrics["stream_chunks"] += 1
        
        # Check for interrupt in chunk
        has_interrupt = '__interrupt__' in chunk if isinstance(chunk, dict) else False
        
        chunk_data = {
            "chunk_number": chunk_number or self.metrics["stream_chunks"],
            "has_interrupt": has_interrupt,
            "chunk_keys": list(chunk.keys()) if isinstance(chunk, dict) else None
        }
        
        if has_interrupt:
            self.trace_interrupt_captured(chunk.get('__interrupt__'))
        
        self.trace_event("stream.chunk", chunk_data)
    
    def trace_phase_transition(self, from_phase: str, to_phase: str, duration: float = None):
        """
        Trace phase transitions with virtual agent context
        
        Args:
            from_phase: Previous phase
            to_phase: New phase
            duration: Duration of the previous phase
        """
        self.metrics["phase_transitions"] += 1
        
        transition_data = {
            "from": from_phase,
            "to": to_phase,
            "duration_seconds": duration,
            "transition_number": self.metrics["phase_transitions"]
        }
        
        self.trace_event("phase.transition", transition_data, 1.0)
        
        # Score phase duration if provided
        if duration:
            self.trace_event(f"phase.{from_phase.lower()}.duration", {"seconds": duration}, duration)
            
            # Add Langfuse score for phase completion
            self.score_phase_completion(
                phase=from_phase,
                completed=True,
                duration_seconds=duration
            )
        
        # Create virtual agent span for the new phase
        self._create_virtual_agent_span(to_phase)
    
    def score_phase_completion(self, phase: str, completed: bool, 
                              duration_seconds: float = None):
        """
        Score a phase completion using Langfuse's scoring API
        Following the pattern from the documentation
        
        Args:
            phase: Name of the phase
            completed: Whether phase was completed
            duration_seconds: Actual duration
        """
        if not self.langfuse_client:
            return
        
        try:
            # Get expected duration for this phase
            expected_durations = {
                "STARTUP": 120,  # 2 minutes
                "MIND_SWEEP": 600,  # 10 minutes
                "PROJECT_REVIEW": 720,  # 12 minutes
                "PRIORITIZATION": 300,  # 5 minutes
                "WRAP_UP": 180  # 3 minutes
            }
            expected_duration = expected_durations.get(phase, 300)
            
            # Calculate time adherence score
            time_score = 1.0
            if duration_seconds:
                # Perfect score if within time, declining as it goes over
                if duration_seconds <= expected_duration:
                    time_score = 1.0
                else:
                    # Reduce score based on how much over time
                    overtime_ratio = (duration_seconds - expected_duration) / expected_duration
                    time_score = max(0.0, 1.0 - (overtime_ratio * 0.5))  # 50% reduction per 100% overtime
            
            # Create phase completion score
            self.langfuse_client.create_score(
                trace_id=self.session_id,
                name=f"phase_{phase.lower()}_completion",
                value=1.0 if completed else 0.0,
                data_type="NUMERIC",
                comment=f"{phase} {'completed' if completed else 'incomplete'}"
            )
            
            # Create time adherence score if we have timing data
            if duration_seconds:
                self.langfuse_client.create_score(
                    trace_id=self.session_id,
                    name=f"phase_{phase.lower()}_time_adherence",
                    value=time_score,
                    data_type="NUMERIC",
                    comment=f"Expected: {expected_duration}s, Actual: {duration_seconds:.1f}s"
                )
            
            logger.debug(f"Scored phase {phase}: completion={completed}, time_score={time_score:.2f}")
            
        except Exception as e:
            logger.debug(f"Failed to score phase completion: {e}")
    
    def trace_graph_config(self, config: Dict):
        """
        Trace LangGraph configuration
        
        Args:
            config: Graph configuration including checkpointer, tools, etc.
        """
        config_data = {
            "has_checkpointer": "checkpointer" in config,
            "thread_id": config.get("configurable", {}).get("thread_id"),
            "recursion_limit": config.get("recursion_limit"),
            "stream_mode": config.get("stream_mode"),
            "tool_count": len(config.get("tools", []))
        }
        
        self.trace_event("graph.config", config_data)
        logger.info(f"Graph configuration traced: {config_data}")
    
    def score_conversation_flow(self):
        """
        Calculate and score the overall conversation flow quality
        """
        if not self.langfuse_client:
            return
        
        # Calculate key metrics
        interrupt_success = (
            self.metrics["interrupt_captures"] / self.metrics["interrupt_attempts"]
            if self.metrics["interrupt_attempts"] > 0 else 0
        )
        
        tool_completion = (
            self.metrics["tool_completions"] / self.metrics["tool_calls"]
            if self.metrics["tool_calls"] > 0 else 0
        )
        
        conversation_continuity = (
            self.metrics["interrupt_resumes"] / self.metrics["interrupt_captures"]
            if self.metrics["interrupt_captures"] > 0 else 0
        )
        
        # Create composite score
        overall_score = (interrupt_success + tool_completion + conversation_continuity) / 3
        
        # Submit scores
        scores = {
            "interrupt_success": interrupt_success,
            "tool_completion": tool_completion,
            "conversation_continuity": conversation_continuity,
            "overall_flow": overall_score
        }
        
        for name, value in scores.items():
            self.trace_event(f"flow.{name}", {"score": value}, value)
        
        logger.info(f"Conversation flow scores: {scores}")
        
        return scores
    
    @contextmanager
    def trace_scope(self, scope_name: str):
        """
        Context manager for tracing a scope of execution
        
        Args:
            scope_name: Name of the scope
        """
        start_time = time.time()
        self.trace_event(f"{scope_name}.start")
        
        try:
            yield self
        finally:
            duration = time.time() - start_time
            self.trace_event(f"{scope_name}.end", {"duration": duration}, duration)
    
    def get_metrics_summary(self) -> Dict:
        """Get a summary of all tracked metrics"""
        return {
            **self.metrics,
            "interrupt_success_rate": (
                self.metrics["interrupt_captures"] / self.metrics["interrupt_attempts"]
                if self.metrics["interrupt_attempts"] > 0 else 0
            ),
            "tool_completion_rate": (
                self.metrics["tool_completions"] / self.metrics["tool_calls"]
                if self.metrics["tool_calls"] > 0 else 0
            ),
            "memory_hit_rate": (
                self.metrics["memories_used"] / self.metrics["memories_retrieved"]
                if self.metrics["memories_retrieved"] > 0 else 0
            ),
            "pending_interrupts": len(self.interrupt_stack),
            "session_id": self.session_id
        }
    
    def _create_virtual_agent_span(self, phase: str):
        """
        Create a virtual agent span for specialized phase behavior
        
        Args:
            phase: The phase name to create virtual agent for
        """
        if not self.langfuse_client:
            return
        
        try:
            from langfuse import Langfuse
            langfuse = Langfuse()
            
            # Map phases to virtual agent types
            virtual_agents = {
                "STARTUP": {
                    "name": "🎯 Executive Function Agent",
                    "role": "Initialize focus and establish structure",
                    "skills": ["routine_establishment", "energy_assessment", "focus_calibration"]
                },
                "MIND_SWEEP": {
                    "name": "🧠 Capture Agent", 
                    "role": "Extract and organize thoughts without judgment",
                    "skills": ["rapid_capture", "non_judgmental_recording", "thought_clustering"]
                },
                "PROJECT_REVIEW": {
                    "name": "📊 Analysis Agent",
                    "role": "Review projects and identify patterns",
                    "skills": ["project_status_tracking", "pattern_recognition", "progress_assessment"]
                },
                "PRIORITIZATION": {
                    "name": "🎯 Decision Agent",
                    "role": "Apply GTD criteria for priority selection",
                    "skills": ["importance_scoring", "urgency_assessment", "capacity_matching"]
                },
                "WRAP_UP": {
                    "name": "✅ Completion Agent",
                    "role": "Ensure closure and prepare for next session",
                    "skills": ["summary_generation", "commitment_tracking", "next_action_setup"]
                }
            }
            
            agent_info = virtual_agents.get(phase)
            if not agent_info:
                return
            
            # Create a custom span for the virtual agent
            with langfuse.start_as_current_span(
                name=agent_info["name"],
                trace_context={"trace_id": self.session_id}
            ) as span:
                span.update_trace(
                    input=f"Activating {phase} phase",
                    metadata={
                        "agent_type": "virtual",
                        "phase": phase,
                        "role": agent_info["role"],
                        "skills": agent_info["skills"],
                        "session_id": self.session_id,
                        "timestamp": datetime.now().isoformat()
                    }
                )
                
                # Log virtual agent activation
                logger.info(f"Virtual agent activated: {agent_info['name']} for {phase}")
                
        except Exception as e:
            logger.debug(f"Failed to create virtual agent span: {e}")
    
    def flush(self):
        """Flush any pending events to Langfuse"""
        if self.langfuse_client:
            try:
                self.langfuse_client.flush()
                logger.debug("Flushed Langfuse events")
            except Exception as e:
                logger.debug(f"Failed to flush Langfuse: {e}")