#!/usr/bin/env python3
"""
Conversation Management Tools for GTD Agent (Version 3)
Fixed to properly work with LangGraph's interrupt execution model.
Each tool handles exactly ONE interrupt to avoid state pollution.
"""

import logging
from typing import Dict, Optional, Any
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
@monitor_interrupt("ask_question_v3")
def ask_question_v3(question: str, context: Optional[str] = None) -> str:
    """
    Ask the user a single question and wait for their response.
    This tool properly handles LangGraph's interrupt pattern by only calling interrupt once.
    
    Args:
        question: The question to ask the user
        context: Optional context about why this question is being asked
        
    Returns:
        The user's response as a string
        
    Example:
        ask_question_v3("How's your energy level today on a scale of 1-10?", "STARTUP phase")
    """
    logger.info(f"Asking user: {question} (context: {context})")
    
    # Get tracer for additional logging
    tracer = get_global_tracer()
    if tracer:
        tracer.trace_event("conversation.ask_question.start", {
            "question": question,
            "context": context
        })
    
    # Single interrupt call - this is the key fix
    logger.debug(f"[INTERRUPT DEBUG] Calling interrupt with question: {question}")
    response = interrupt(question)
    
    # Log the response
    logger.info(f"User responded: {response}")
    
    if tracer:
        tracer.trace_event("conversation.ask_question.complete", {
            "question": question,
            "response": str(response)[:100],
            "context": context
        })
    
    return response


@tool
@monitor_interrupt("ask_yes_no_v3")
def ask_yes_no_v3(
    question: str,
    default: bool = True,
    context: Optional[str] = None
) -> bool:
    """
    Ask the user a yes/no question and return a boolean response.
    Handles only a single interrupt to work properly with LangGraph.
    
    Args:
        question: The yes/no question to ask
        default: Default value if user just presses enter
        context: Optional context about the question
        
    Returns:
        True if user confirms, False otherwise
        
    Example:
        ask_yes_no_v3("Are you ready to start the mind sweep phase?", True, "STARTUP")
    """
    logger.info(f"Asking yes/no: {question} (default: {default}, context: {context})")
    
    # Get tracer for additional logging
    tracer = get_global_tracer()
    if tracer:
        tracer.trace_event("conversation.ask_yes_no.start", {
            "question": question,
            "default": default,
            "context": context
        })
    
    # Add default hint to question
    hint = " [Y/n]" if default else " [y/N]"
    full_prompt = question + hint
    
    # Single interrupt call
    logger.debug(f"[INTERRUPT DEBUG] Calling interrupt with yes/no: {full_prompt}")
    response = interrupt(full_prompt)
    
    # Parse response
    if not response or response == "":
        result = default
        logger.info(f"Empty response, using default: {default}")
    else:
        response_lower = str(response).lower().strip()
        if response_lower in ['y', 'yes', 'yeah', 'yep', 'sure', 'ok', 'okay']:
            result = True
        elif response_lower in ['n', 'no', 'nope', 'nah']:
            result = False
        else:
            # If unclear, use default
            logger.info(f"Unclear response '{response}', using default: {default}")
            result = default
    
    logger.info(f"Yes/no result: {result}")
    
    if tracer:
        tracer.trace_event("conversation.ask_yes_no.complete", {
            "question": question,
            "response": str(response),
            "result": result,
            "context": context
        })
    
    return result


@tool
def startup_questions_v3() -> Dict[str, Any]:
    """
    Orchestrate the STARTUP phase questions.
    This tool does NOT use interrupts - it calls other tools that do.
    The agent should call this to coordinate the startup conversation.
    
    Returns:
        Dictionary with startup information
        
    Example:
        startup_questions_v3()
    """
    logger.info("Orchestrating STARTUP phase questions")
    
    # Note: This tool doesn't call interrupt directly
    # It returns instructions for the agent to call other tools
    return {
        "instructions": "Please ask these questions in order using ask_question_v3:",
        "questions": [
            "How's your energy level today on a scale of 1-10?",
            "Do you have any concerns or blockers before we begin?",
            "Are you ready to start the mind sweep phase?"
        ],
        "phase": "STARTUP",
        "note": "Call ask_question_v3 for each question separately"
    }


@tool
def collect_mind_sweep_v3() -> Dict[str, Any]:
    """
    Orchestrate the MIND_SWEEP phase data collection.
    This tool does NOT use interrupts - it provides instructions for the agent.
    
    Returns:
        Instructions for the mind sweep phase
        
    Example:
        collect_mind_sweep_v3()
    """
    logger.info("Orchestrating MIND_SWEEP phase")
    
    return {
        "instructions": "Ask the user to brain dump everything on their mind",
        "prompt": "What's been on your mind this week? (Share everything - tasks, concerns, ideas)",
        "phase": "MIND_SWEEP",
        "note": "Use ask_question_v3 to collect the response, then parse and save items"
    }


@tool
def collect_priorities_v3() -> Dict[str, Any]:
    """
    Orchestrate the PRIORITIZATION phase.
    This tool does NOT use interrupts - it provides instructions for the agent.
    
    Returns:
        Instructions for the prioritization phase
        
    Example:
        collect_priorities_v3()
    """
    logger.info("Orchestrating PRIORITIZATION phase")
    
    return {
        "instructions": "Help user identify their top 3 priorities",
        "questions": [
            "What are your top 3 priorities for the week?",
            "How will you ensure these tasks get done?"
        ],
        "phase": "PRIORITIZATION",
        "note": "Use ask_question_v3 for each question separately"
    }


# Compatibility wrapper for legacy code
@tool
def wait_for_user_input_v3(prompt: str) -> str:
    """
    Legacy compatibility wrapper. Use ask_question_v3 instead.
    
    Args:
        prompt: The prompt or question to show the user
        
    Returns:
        The user's response as a string
    """
    logger.warning("Using legacy wait_for_user_input_v3 - consider using ask_question_v3")
    return ask_question_v3(prompt, context="LEGACY")


@tool
def confirm_with_user_v3(message: str, default: bool = True) -> bool:
    """
    Legacy compatibility wrapper. Use ask_yes_no_v3 instead.
    
    Args:
        message: The confirmation message
        default: Default value
        
    Returns:
        Boolean confirmation
    """
    logger.warning("Using legacy confirm_with_user_v3 - consider using ask_yes_no_v3")
    return ask_yes_no_v3(message, default, context="LEGACY")