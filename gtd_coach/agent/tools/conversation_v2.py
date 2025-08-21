#!/usr/bin/env python3
"""
Conversation Management Tools for GTD Agent (Version 2)
Uses LangGraph's interrupt pattern for human-in-the-loop interaction.
Enhanced with comprehensive observability and debugging.
"""

import logging
from typing import Dict, Optional
from langchain_core.tools import tool
from langgraph.types import interrupt

# Import observability if available
try:
    from gtd_coach.observability import monitor_interrupt, get_global_tracer
    OBSERVABILITY_AVAILABLE = True
except ImportError:
    OBSERVABILITY_AVAILABLE = False
    # Create no-op decorator if observability not available
    def monitor_interrupt(tool_name=None):
        def decorator(func):
            return func
        return decorator
    def get_global_tracer():
        return None

logger = logging.getLogger(__name__)

@tool
@monitor_interrupt("check_in_with_user_v2")
def check_in_with_user_v2(
    phase: str,
    questions: list[str]
) -> Dict:
    """
    Check in with the user by asking specific questions based on the current phase.
    This tool will pause execution and wait for user responses.
    
    Args:
        phase: Current phase (STARTUP, MIND_SWEEP, etc.)
        questions: List of questions to ask the user
        
    Returns:
        Dictionary with user responses
        
    Example:
        check_in_with_user_v2(
            "STARTUP",
            ["How's your energy level today (1-10)?", 
             "Any concerns before we begin?"]
        )
    """
    logger.info(f"Checking in with user in {phase} phase with {len(questions)} questions")
    
    # Get tracer for additional logging
    tracer = get_global_tracer()
    if tracer:
        tracer.trace_event("conversation.check_in.start", {
            "phase": phase,
            "question_count": len(questions)
        })
    
    responses = {}
    for i, question in enumerate(questions, 1):
        logger.debug(f"[INTERRUPT DEBUG] About to call interrupt with question {i}/{len(questions)}: {question}")
        
        # Use interrupt to pause and wait for user input
        user_response = interrupt(question)
        
        # If we reach here, interrupt didn't actually pause
        logger.warning(f"[INTERRUPT BYPASSED] Got immediate response: {user_response}")
        
        # Store response
        key = question.split('?')[0].lower().replace(' ', '_').replace("'", "")
        responses[key] = user_response
        
        logger.debug(f"User response to '{question}': {user_response}")
    
    result = {
        "success": True,
        "phase": phase,
        "responses": responses,
        "message": f"Collected {len(responses)} responses from user"
    }
    
    if tracer:
        tracer.trace_event("conversation.check_in.complete", result)
    
    return result

@tool
@monitor_interrupt("wait_for_user_input_v2")
def wait_for_user_input_v2(prompt: str) -> str:
    """
    Pause execution and wait for user input with a custom prompt.
    Use this when you need to ask the user a single question.
    
    Args:
        prompt: The prompt or question to show the user
        
    Returns:
        The user's response as a string
        
    Example:
        wait_for_user_input_v2("What would you like to focus on today?")
    """
    logger.debug(f"[INTERRUPT DEBUG] Waiting for user input with prompt: {prompt}")
    
    # Get tracer for additional logging
    tracer = get_global_tracer()
    if tracer:
        tracer.trace_event("conversation.wait_input.start", {"prompt": prompt})
    
    # Interrupt execution and wait for response
    logger.debug(f"[INTERRUPT DEBUG] About to call interrupt with prompt: {prompt}")
    response = interrupt(prompt)
    
    # If we reach here, interrupt didn't actually pause
    logger.warning(f"[INTERRUPT BYPASSED] Got immediate response: {response}")
    
    if tracer:
        tracer.trace_event("conversation.wait_input.complete", {
            "prompt": prompt,
            "response": str(response)[:100]
        })
    
    logger.debug(f"Received user response: {response}")
    return response

@tool
@monitor_interrupt("confirm_with_user_v2")
def confirm_with_user_v2(
    message: str,
    default: bool = True
) -> bool:
    """
    Ask the user for confirmation with a yes/no question.
    
    Args:
        message: The confirmation message to show
        default: Default value if user just presses enter
        
    Returns:
        True if user confirms, False otherwise
        
    Example:
        confirm_with_user_v2("Are you ready to start the mind sweep phase?")
    """
    logger.debug(f"[INTERRUPT DEBUG] Asking for confirmation: {message}")
    
    # Get tracer for additional logging
    tracer = get_global_tracer()
    if tracer:
        tracer.trace_event("conversation.confirm.start", {
            "message": message,
            "default": default
        })
    
    # Add default hint to message
    hint = " [Y/n]" if default else " [y/N]"
    full_prompt = message + hint
    
    # Interrupt and wait for response
    logger.debug(f"[INTERRUPT DEBUG] About to call interrupt with confirmation: {full_prompt}")
    response = interrupt(full_prompt)
    
    # If we reach here, interrupt didn't actually pause
    logger.warning(f"[INTERRUPT BYPASSED] Got immediate response: {response}")
    
    # Parse response
    if not response:
        result = default
    else:
        response_lower = response.lower().strip()
        if response_lower in ['y', 'yes', 'yeah', 'yep', 'sure', 'ok', 'okay']:
            result = True
        elif response_lower in ['n', 'no', 'nope', 'nah']:
            result = False
        else:
            # If unclear, use default
            logger.debug(f"Unclear response '{response}', using default: {default}")
            result = default
    
    if tracer:
        tracer.trace_event("conversation.confirm.complete", {
            "message": message,
            "response": str(response),
            "result": result
        })
    
    return result