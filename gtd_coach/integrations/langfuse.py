"""
Minimal Langfuse integration for GTD Coach
Provides drop-in OpenAI client replacement with observability
"""

import os
import logging

try:
    from langfuse.openai import OpenAI
    from langfuse import observe, get_client
    LANGFUSE_AVAILABLE = True
except ImportError as e:
    import sys
    logger = logging.getLogger(__name__)
    error_msg = (
        f"Langfuse import failed: {e}\n"
        "Langfuse is required for GTD Coach. Please install it:\n"
        "  pip install 'langfuse[openai]>=3.0.0'\n"
        "Or install all dependencies:\n"
        "  pip install -r requirements.txt"
    )
    logger.error(error_msg)
    # Re-raise with better error message
    raise ImportError(error_msg) from e

# Configuration - Update these with your Langfuse instance details
LANGFUSE_HOST = "http://langfuse-prod-langfuse-web-1.orb.local"
LANGFUSE_PUBLIC_KEY = "pk-lf-00689068-a85f-41a1-8e1e-37619595b0ed"
LANGFUSE_SECRET_KEY = "sk-lf-14e07bbb-ee5f-45a1-abd8-b63d21f95bb9"

# Set up logger
logger = logging.getLogger(__name__)

def get_langfuse_client():
    """
    Initialize and return a Langfuse-wrapped OpenAI client
    configured for LM Studio endpoint
    """
    try:
        # Set environment variables for Langfuse
        os.environ["LANGFUSE_HOST"] = LANGFUSE_HOST
        os.environ["LANGFUSE_PUBLIC_KEY"] = LANGFUSE_PUBLIC_KEY
        os.environ["LANGFUSE_SECRET_KEY"] = LANGFUSE_SECRET_KEY
        
        # Create OpenAI client with LM Studio endpoint
        client = OpenAI(
            base_url="http://localhost:1234/v1",
            api_key="lm-studio"  # LM Studio doesn't require real API key
        )
        
        logger.info("Langfuse client initialized successfully")
        return client
        
    except Exception as e:
        logger.warning(f"Failed to initialize Langfuse client: {e}")
        return None

def score_graphiti_operation(operation: str, success: bool, latency: float, 
                            episode_count: int = 1, cost_estimate: float = None):
    """
    Track Graphiti operations in Langfuse
    
    Args:
        operation: Operation type (add_episode, search, batch_flush)
        success: Whether operation succeeded
        latency: Operation latency in seconds
        episode_count: Number of episodes in operation
        cost_estimate: Estimated cost of operation in dollars
    """
    try:
        client = get_client()
        
        # Create observation for Graphiti operation
        # v3 API returns ID only, processes asynchronously
        score_id = client.score(
            name=f"graphiti_{operation}",
            value=1.0 if success else 0.0,
            data_type="BOOLEAN",
            comment=f"Episodes: {episode_count}, Latency: {latency:.3f}s"
        )
        logger.debug(f"Score created with ID: {score_id}")
        
        # Track cost if provided
        if cost_estimate:
            cost_score_id = client.score(
                name="graphiti_cost",
                value=cost_estimate,
                data_type="NUMERIC",
                comment=f"Operation: {operation}"
            )
            logger.debug(f"Cost score created with ID: {cost_score_id}")
        
        # Track performance metrics
        if latency > 1.0:  # Flag slow operations
            perf_score_id = client.score(
                name="graphiti_slow_operation",
                value=latency,
                data_type="NUMERIC", 
                comment=f"Slow {operation}: {latency:.3f}s"
            )
            logger.debug(f"Performance score created with ID: {perf_score_id}")
            
    except Exception as e:
        logger.debug(f"Failed to score Graphiti operation: {e}")

def score_response(phase: str, success: bool, response_time: float, session_id: str = None, trace_id: str = None):
    """
    Add quality scores to the current observation based on phase requirements
    
    Args:
        phase: Current GTD review phase
        success: Whether the LLM call succeeded
        response_time: Time taken for the response in seconds
        session_id: Optional session ID to associate with the trace
        trace_id: Optional trace ID to score
    """
    try:
        langfuse = get_client()
        
        # If session_id provided, ensure it's set on current trace
        if session_id and not trace_id:
            try:
                langfuse.update_current_trace(session_id=session_id)
            except Exception as e:
                logger.debug(f"Failed to set session_id on trace: {e}")
        
        # Score 1: Binary success/failure
        # v3 API returns ID only, processes asynchronously
        success_score_id = langfuse.score(
            trace_id=trace_id,
            name="success",
            value=1 if success else 0,
            comment=f"LLM call {'succeeded' if success else 'failed'}"
        )
        logger.debug(f"Success score created with ID: {success_score_id}")
        
        # Score 2: Quality based on phase-specific latency thresholds
        # These thresholds are calibrated for ADHD users who need quick responses
        latency_thresholds = {
            "STARTUP": 5.0,      # Welcome phase can be slightly slower
            "MIND_SWEEP": 3.0,   # Need quick responses during capture
            "PROJECT_REVIEW": 2.0,  # Critical for 45-second per project limit
            "PRIORITIZATION": 3.0,  # Decision support needs to be responsive
            "WRAP_UP": 4.0       # Celebration phase can be more relaxed
        }
        
        threshold = latency_thresholds.get(phase, 5.0)
        quality_score = 1 if response_time < threshold else 0
        
        quality_score_id = langfuse.score(
            trace_id=trace_id,
            name="quality",
            value=quality_score,
            comment=f"Phase: {phase}, Response: {response_time:.2f}s, Threshold: {threshold}s"
        )
        logger.debug(f"Quality score created with ID: {quality_score_id}")
        
        # Score 3: Phase-specific response appropriateness
        # This helps track if the coach is meeting phase requirements
        phase_score_id = langfuse.score(
            trace_id=trace_id,
            name="phase_appropriate",
            value=1,  # Will be manually reviewed in Langfuse UI
            comment=f"Review in UI for {phase} phase appropriateness"
        )
        logger.debug(f"Phase score created with ID: {phase_score_id}")
        
    except Exception as e:
        logger.debug(f"Failed to score response: {e}")
        # Don't fail the main flow if scoring fails

def validate_configuration():
    """
    Check if Langfuse is properly configured
    
    Returns:
        bool: True if configuration appears valid
    """
    if LANGFUSE_PUBLIC_KEY == "pk-lf-..." or LANGFUSE_SECRET_KEY == "sk-lf-...":
        logger.warning("Langfuse keys not configured - please update langfuse_tracker.py")
        return False
    
    if not LANGFUSE_HOST:
        logger.warning("Langfuse host not configured")
        return False
        
    return True
