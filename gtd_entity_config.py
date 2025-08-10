#!/usr/bin/env python3
"""
GTD Entity Configuration for Graphiti
Provides entity and edge type configurations for different episode types
"""

from typing import Dict, List, Tuple, Optional, Any
from pydantic import BaseModel
from gtd_entities import (
    GTDProject, GTDAction, GTDContext, GTDAreaOfFocus,
    ADHDPattern, MindsweepItem, WeeklyReview, TimingInsight,
    HasNextAction, RequiresContext, BelongsToArea, ProcessedInto,
    EDGE_TYPE_MAP
)


# Entity type dictionary for Graphiti
ENTITY_TYPES: Dict[str, type[BaseModel]] = {
    "GTDProject": GTDProject,
    "GTDAction": GTDAction,
    "GTDContext": GTDContext,
    "GTDAreaOfFocus": GTDAreaOfFocus,
    "ADHDPattern": ADHDPattern,
    "MindsweepItem": MindsweepItem,
    "WeeklyReview": WeeklyReview,
    "TimingInsight": TimingInsight,
}


# Edge type dictionary for Graphiti
EDGE_TYPES: Dict[str, type[BaseModel]] = {
    "HasNextAction": HasNextAction,
    "RequiresContext": RequiresContext,
    "BelongsToArea": BelongsToArea,
    "ProcessedInto": ProcessedInto,
}


# Episode types that should use custom entity extraction
ENTITY_EXTRACTION_EPISODE_TYPES = [
    "interaction",
    "mindsweep_capture",
    "session_summary",
    "timing_analysis",
]


# Episode types that should NOT use custom entity extraction
SKIP_ENTITY_EXTRACTION_EPISODE_TYPES = [
    "phase_transition",
    "behavior_pattern",
    "correlation_insight",
    "episode_batch",
    "user",
]


# Excluded entity types per episode type
# These entities will be skipped during extraction to improve performance
EXCLUDED_ENTITIES_BY_EPISODE: Dict[str, List[str]] = {
    "interaction": [
        "TimingInsight",  # Timing data comes separately
        "WeeklyReview",   # Review metadata not in interactions
    ],
    "mindsweep_capture": [
        "TimingInsight",  # No timing data during mind sweep
        "WeeklyReview",   # Review metadata not relevant
        "ADHDPattern",    # Patterns detected separately
    ],
    "session_summary": [
        "MindsweepItem",  # Already processed items
    ],
    "timing_analysis": [
        "MindsweepItem",  # Unrelated to timing
        "GTDAction",      # Actions already processed
        "GTDProject",     # Projects already processed
    ],
}


def should_use_custom_entities(episode_type: str) -> bool:
    """
    Determine if custom entity extraction should be used for this episode type
    
    Args:
        episode_type: Type of episode being added
        
    Returns:
        True if custom entities should be used, False otherwise
    """
    return episode_type in ENTITY_EXTRACTION_EPISODE_TYPES


def get_entity_config_for_episode(episode_type: str) -> Optional[Dict[str, Any]]:
    """
    Get entity configuration for a specific episode type
    
    Args:
        episode_type: Type of episode being added
        
    Returns:
        Dictionary with entity_types, edge_types, edge_type_map, and excluded_entity_types
        if custom entities should be used, None otherwise
    """
    if not should_use_custom_entities(episode_type):
        return None
    
    config = {
        "entity_types": ENTITY_TYPES,
        "edge_types": EDGE_TYPES,
        "edge_type_map": EDGE_TYPE_MAP,
    }
    
    # Add excluded entity types if configured for this episode type
    if episode_type in EXCLUDED_ENTITIES_BY_EPISODE:
        config["excluded_entity_types"] = EXCLUDED_ENTITIES_BY_EPISODE[episode_type]
    
    return config


def get_minimal_entity_config() -> Dict[str, Any]:
    """
    Get a minimal entity configuration for testing
    Uses only core GTD entities to reduce processing overhead
    
    Returns:
        Dictionary with minimal entity configuration
    """
    minimal_entities = {
        "GTDProject": GTDProject,
        "GTDAction": GTDAction,
        "GTDContext": GTDContext,
    }
    
    minimal_edges = {
        "HasNextAction": HasNextAction,
        "RequiresContext": RequiresContext,
    }
    
    minimal_edge_map = {
        ("GTDProject", "GTDAction"): ["HasNextAction"],
        ("GTDAction", "GTDContext"): ["RequiresContext"],
    }
    
    return {
        "entity_types": minimal_entities,
        "edge_types": minimal_edges,
        "edge_type_map": minimal_edge_map,
    }


def estimate_extraction_cost(episode_type: str, episode_length: int) -> float:
    """
    Estimate the cost of entity extraction for an episode
    
    Args:
        episode_type: Type of episode
        episode_length: Length of episode body in characters
        
    Returns:
        Estimated cost in USD
    """
    if not should_use_custom_entities(episode_type):
        # No custom extraction, minimal cost
        return 0.0001
    
    # Calculate effective number of entity types (total minus excluded)
    total_entities = len(ENTITY_TYPES)
    excluded_count = len(EXCLUDED_ENTITIES_BY_EPISODE.get(episode_type, []))
    effective_entities = total_entities - excluded_count
    
    # With custom entities, cost increases based on:
    # - Number of entity types being extracted
    # - Episode length
    # - Complexity of extraction
    
    # Rough estimate: $0.0001 per 1000 chars with custom entities
    base_cost = (episode_length / 1000) * 0.0003
    
    # Add multiplier for number of entity types
    entity_multiplier = effective_entities / 4  # Normalized to 4 as baseline
    
    return base_cost * entity_multiplier


def log_entity_extraction(episode_type: str, using_custom: bool) -> None:
    """
    Log entity extraction decision for debugging
    
    Args:
        episode_type: Type of episode
        using_custom: Whether custom entities are being used
    """
    import logging
    logger = logging.getLogger(__name__)
    
    if using_custom:
        excluded = EXCLUDED_ENTITIES_BY_EPISODE.get(episode_type, [])
        if excluded:
            logger.debug(f"Using custom GTD entities for {episode_type}, excluding: {', '.join(excluded)}")
        else:
            logger.debug(f"Using all custom GTD entities for {episode_type}")
    else:
        logger.debug(f"Skipping custom entities for episode type: {episode_type}")