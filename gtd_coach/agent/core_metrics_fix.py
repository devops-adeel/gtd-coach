#!/usr/bin/env python3
"""
Fix for token tracking with LM Studio integration.
Adds proper token counting from LM Studio responses.
"""

import logging
from typing import Dict, Optional, Any
from langchain_core.messages import BaseMessage, AIMessage

logger = logging.getLogger(__name__)


class TokenTracker:
    """
    Tracks token usage from LM Studio responses.
    LM Studio provides usage info in the response metadata.
    """
    
    def __init__(self):
        """Initialize token tracker"""
        self.total_tokens = 0
        self.prompt_tokens = 0
        self.completion_tokens = 0
        self.phase_tokens = {}
        
    def track_response(self, message: BaseMessage, phase: str = "UNKNOWN"):
        """
        Track tokens from an LLM response message.
        
        Args:
            message: The response message from LLM
            phase: Current phase for tracking
        """
        try:
            # Check if message has usage metadata (LM Studio provides this)
            if hasattr(message, 'response_metadata'):
                metadata = message.response_metadata
                
                # Debug log to see what's actually in the metadata
                if metadata:
                    logger.debug(f"Response metadata keys: {list(metadata.keys())}")
                
                # Check multiple possible locations for token usage
                usage = None
                
                # Try token_usage first (standard format)
                if 'token_usage' in metadata:
                    usage = metadata['token_usage']
                    logger.debug(f"Found token_usage: {usage}")
                # Try usage next (LM Studio format)
                elif 'usage' in metadata:
                    usage = metadata['usage']
                    logger.debug(f"Found usage: {usage}")
                # Try model_name with usage (some LM Studio versions)
                elif 'model_name' in metadata and hasattr(message, 'usage_metadata'):
                    usage = message.usage_metadata
                    logger.debug(f"Found usage_metadata: {usage}")
                
                # Additional check: LM Studio sometimes puts usage at top level
                if not usage and hasattr(message, 'usage'):
                    usage = message.usage
                    logger.debug(f"Found message.usage directly: {usage}")
                
                # Extract token counts if we found usage info
                if usage:
                    if isinstance(usage, dict):
                        prompt = usage.get('prompt_tokens', 0)
                        completion = usage.get('completion_tokens', 0)
                        total = usage.get('total_tokens', 0)
                    else:
                        # Handle object-like usage data
                        prompt = getattr(usage, 'prompt_tokens', 0)
                        completion = getattr(usage, 'completion_tokens', 0)
                        total = getattr(usage, 'total_tokens', 0)
                    
                    # If total is 0 but we have prompt and completion, calculate it
                    if total == 0 and (prompt > 0 or completion > 0):
                        total = prompt + completion
                    
                    if total > 0:
                        self.prompt_tokens += prompt
                        self.completion_tokens += completion
                        self.total_tokens += total
                        
                        # Track by phase
                        if phase not in self.phase_tokens:
                            self.phase_tokens[phase] = 0
                        self.phase_tokens[phase] += total
                        
                        logger.debug(f"Tracked {total} tokens for phase {phase} (prompt: {prompt}, completion: {completion})")
                    else:
                        logger.debug(f"No token counts found in usage data for phase {phase}")
            
            # Also check if message has direct usage attribute (some LangChain versions)
            elif hasattr(message, 'usage'):
                usage = message.usage
                logger.debug(f"Found direct message.usage: {usage}")
                if usage:
                    if isinstance(usage, dict):
                        prompt = usage.get('prompt_tokens', 0)
                        completion = usage.get('completion_tokens', 0)
                        total = usage.get('total_tokens', 0)
                    else:
                        prompt = getattr(usage, 'prompt_tokens', 0)
                        completion = getattr(usage, 'completion_tokens', 0)
                        total = getattr(usage, 'total_tokens', 0)
                    
                    if total == 0 and (prompt > 0 or completion > 0):
                        total = prompt + completion
                    
                    if total > 0:
                        self.prompt_tokens += prompt
                        self.completion_tokens += completion
                        self.total_tokens += total
                        
                        if phase not in self.phase_tokens:
                            self.phase_tokens[phase] = 0
                        self.phase_tokens[phase] += total
                        
                        logger.debug(f"Tracked {total} tokens from message.usage for phase {phase}")
            
            # Fallback: Estimate from message content if no metadata
            elif isinstance(message, AIMessage) and not self.total_tokens:
                # Rough estimation: 1 token ≈ 4 characters
                content_length = len(str(message.content)) if message.content else 0
                estimated_tokens = content_length // 4
                self.completion_tokens += estimated_tokens
                self.total_tokens += estimated_tokens
                
                if phase not in self.phase_tokens:
                    self.phase_tokens[phase] = 0
                self.phase_tokens[phase] += estimated_tokens
                
                logger.debug(f"Estimated {estimated_tokens} tokens from content length")
                
        except Exception as e:
            logger.warning(f"Error tracking tokens: {e}")
    
    def get_metrics(self) -> Dict[str, Any]:
        """
        Get current token metrics.
        
        Returns:
            Dictionary of token usage metrics
        """
        return {
            'total_tokens': self.total_tokens,
            'prompt_tokens': self.prompt_tokens,
            'completion_tokens': self.completion_tokens,
            'phase_tokens': self.phase_tokens.copy()
        }
    
    def reset(self):
        """Reset all token counters"""
        self.total_tokens = 0
        self.prompt_tokens = 0
        self.completion_tokens = 0
        self.phase_tokens = {}


def inject_token_tracking(agent_class):
    """
    Decorator to inject token tracking into GTDAgent.
    
    Args:
        agent_class: The GTDAgent class to enhance
        
    Returns:
        Enhanced class with token tracking
    """
    original_init = agent_class.__init__
    original_invoke = agent_class.invoke
    original_stream = agent_class.stream
    
    def new_init(self, *args, **kwargs):
        original_init(self, *args, **kwargs)
        self.token_tracker = TokenTracker()
        logger.info("Token tracking initialized for GTDAgent")
    
    def new_invoke(self, state, config=None):
        # Import Command to check instance
        from langgraph.types import Command
        
        # Call original invoke first
        result = original_invoke(self, state, config)
        
        # Track tokens from messages in result
        if isinstance(result, dict) and 'messages' in result:
            # Extract phase from multiple sources
            current_phase = 'UNKNOWN'
            
            # Try to get phase from state if it's a dict
            if isinstance(state, dict):
                current_phase = state.get('current_phase', 'UNKNOWN')
            # If state is a Command (resume operation), try to get phase from result
            elif isinstance(state, Command):
                # During resume, phase should be in the result state
                if isinstance(result, dict):
                    current_phase = result.get('current_phase', 'UNKNOWN')
            
            # If still unknown, try to get phase from context_metrics as last resort
            if current_phase == 'UNKNOWN' and hasattr(self, 'context_metrics'):
                current_phase = self.context_metrics.get('current_phase', 'UNKNOWN')
                
            # Track tokens for each message
            for message in result['messages']:
                if isinstance(message, AIMessage):
                    self.token_tracker.track_response(message, current_phase)
        
        # Update context_metrics with tracked tokens
        metrics = self.token_tracker.get_metrics()
        self.context_metrics['total_tokens'] = metrics['total_tokens']
        self.context_metrics['phase_tokens'] = metrics['phase_tokens']
        
        return result
    
    def new_stream(self, state, config=None, **kwargs):
        # Import Command to check instance
        from langgraph.types import Command
        
        # Determine phase before streaming starts
        current_phase = 'UNKNOWN'
        
        # Try to get phase from state if it's a dict
        if isinstance(state, dict):
            current_phase = state.get('current_phase', 'UNKNOWN')
        # If state is a Command, we'll get phase from streamed chunks
        elif isinstance(state, Command):
            # For Command objects, phase will be in the streamed state
            pass
        
        # If still unknown, try context_metrics
        if current_phase == 'UNKNOWN' and hasattr(self, 'context_metrics'):
            current_phase = self.context_metrics.get('current_phase', 'UNKNOWN')
        
        for chunk in original_stream(self, state, config, **kwargs):
            # Track tokens from streamed messages
            if isinstance(chunk, dict):
                # Update phase if available in chunk
                if 'current_phase' in chunk:
                    current_phase = chunk['current_phase']
                
                for key, value in chunk.items():
                    if key == 'messages' and isinstance(value, list):
                        for message in value:
                            if isinstance(message, AIMessage):
                                self.token_tracker.track_response(message, current_phase)
            
            yield chunk
        
        # Update context_metrics after streaming
        metrics = self.token_tracker.get_metrics()
        self.context_metrics['total_tokens'] = metrics['total_tokens']
        self.context_metrics['phase_tokens'] = metrics['phase_tokens']
    
    def new_get_context_metrics(self):
        """Enhanced context metrics with proper token tracking"""
        # Get base metrics
        metrics = self.context_metrics.copy()
        
        # Add token tracker metrics if available
        if hasattr(self, 'token_tracker'):
            token_metrics = self.token_tracker.get_metrics()
            metrics.update(token_metrics)
        
        return metrics
    
    # Replace methods
    agent_class.__init__ = new_init
    agent_class.invoke = new_invoke
    agent_class.stream = new_stream
    agent_class.get_context_metrics = new_get_context_metrics
    
    return agent_class