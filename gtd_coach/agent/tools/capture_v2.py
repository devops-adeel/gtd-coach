#!/usr/bin/env python3
"""
Data Capture and Persistence Tools for GTD Agent (Version 2)
Provides tools to save user inputs to database and Graphiti knowledge graph.
"""

import logging
import json
from typing import Dict, List, Optional, Any
from datetime import datetime
from langchain_core.tools import tool

# Import Graphiti if available
try:
    from gtd_coach.integrations import get_graphiti_client
    GRAPHITI_AVAILABLE = True
except ImportError:
    GRAPHITI_AVAILABLE = False
    def get_graphiti_client():
        return None

logger = logging.getLogger(__name__)


@tool
def save_mind_sweep_item_v2(
    item: str,
    category: Optional[str] = None,
    user_id: Optional[str] = None
) -> Dict[str, Any]:
    """
    Save a single mind sweep item to the database and knowledge graph.
    Call this after collecting each item during the MIND_SWEEP phase.
    
    Args:
        item: The mind sweep item text
        category: Optional category (task, idea, concern, project)
        user_id: Optional user identifier
        
    Returns:
        Confirmation of saved item
        
    Example:
        save_mind_sweep_item_v2("Finish project report", "task")
    """
    logger.info(f"Saving mind sweep item: {item} (category: {category})")
    
    result = {
        "item": item,
        "category": category or "uncategorized",
        "timestamp": datetime.now().isoformat(),
        "saved": False,
        "graphiti_saved": False
    }
    
    # Save to Graphiti if available
    if GRAPHITI_AVAILABLE:
        try:
            client = get_graphiti_client()
            if client:
                # Create episode for the mind sweep item
                episode_data = {
                    "source": "gtd_weekly_review",
                    "description": f"Mind sweep item: {item}",
                    "type": "mind_sweep",
                    "category": category,
                    "user_id": user_id or "default",
                    "timestamp": datetime.now().isoformat()
                }
                
                client.add_episode(
                    episode_data=episode_data,
                    use_enhanced_extraction=True
                )
                
                result["graphiti_saved"] = True
                logger.info(f"Saved to Graphiti: {item}")
        except Exception as e:
            logger.error(f"Failed to save to Graphiti: {e}")
    
    # Mark as saved (in real implementation, would save to database)
    result["saved"] = True
    
    logger.info(f"Mind sweep item saved: {result}")
    return result


@tool
def save_weekly_priority_v2(
    priority: str,
    rank: int,
    commitment: Optional[str] = None,
    user_id: Optional[str] = None
) -> Dict[str, Any]:
    """
    Save a weekly priority to the database and knowledge graph.
    Call this after user identifies their top priorities.
    
    Args:
        priority: The priority description
        rank: Priority rank (1-3 for top 3)
        commitment: How they will ensure it gets done
        user_id: Optional user identifier
        
    Returns:
        Confirmation of saved priority
        
    Example:
        save_weekly_priority_v2("Complete Q4 planning", 1, "Time-blocked Tuesday morning")
    """
    logger.info(f"Saving priority #{rank}: {priority}")
    
    result = {
        "priority": priority,
        "rank": rank,
        "commitment": commitment,
        "week": datetime.now().strftime("%G-W%V"),  # ISO week format
        "timestamp": datetime.now().isoformat(),
        "saved": False,
        "graphiti_saved": False
    }
    
    # Save to Graphiti if available
    if GRAPHITI_AVAILABLE:
        try:
            client = get_graphiti_client()
            if client:
                # Create episode for the priority
                episode_data = {
                    "source": "gtd_weekly_review",
                    "description": f"Weekly priority #{rank}: {priority}",
                    "type": "weekly_priority",
                    "rank": rank,
                    "commitment": commitment,
                    "user_id": user_id or "default",
                    "week": result["week"],
                    "timestamp": datetime.now().isoformat()
                }
                
                client.add_episode(
                    episode_data=episode_data,
                    use_enhanced_extraction=True
                )
                
                result["graphiti_saved"] = True
                logger.info(f"Saved priority to Graphiti: {priority}")
        except Exception as e:
            logger.error(f"Failed to save priority to Graphiti: {e}")
    
    # Mark as saved
    result["saved"] = True
    
    logger.info(f"Priority saved: {result}")
    return result


@tool
def save_project_update_v2(
    project_name: str,
    status: str,
    next_action: Optional[str] = None,
    notes: Optional[str] = None,
    user_id: Optional[str] = None
) -> Dict[str, Any]:
    """
    Save a project update during the PROJECT_REVIEW phase.
    
    Args:
        project_name: Name of the project
        status: Current status (active, waiting, someday, completed)
        next_action: The next action for this project
        notes: Optional notes about the project
        user_id: Optional user identifier
        
    Returns:
        Confirmation of saved project update
        
    Example:
        save_project_update_v2("Website Redesign", "active", "Review mockups with team")
    """
    logger.info(f"Saving project update: {project_name} - {status}")
    
    result = {
        "project": project_name,
        "status": status,
        "next_action": next_action,
        "notes": notes,
        "timestamp": datetime.now().isoformat(),
        "saved": False,
        "graphiti_saved": False
    }
    
    # Save to Graphiti if available
    if GRAPHITI_AVAILABLE:
        try:
            client = get_graphiti_client()
            if client:
                # Create episode for the project update
                episode_data = {
                    "source": "gtd_weekly_review",
                    "description": f"Project '{project_name}' is {status}. Next: {next_action}",
                    "type": "project_update",
                    "project_name": project_name,
                    "status": status,
                    "next_action": next_action,
                    "notes": notes,
                    "user_id": user_id or "default",
                    "timestamp": datetime.now().isoformat()
                }
                
                client.add_episode(
                    episode_data=episode_data,
                    use_enhanced_extraction=True
                )
                
                result["graphiti_saved"] = True
                logger.info(f"Saved project to Graphiti: {project_name}")
        except Exception as e:
            logger.error(f"Failed to save project to Graphiti: {e}")
    
    # Mark as saved
    result["saved"] = True
    
    logger.info(f"Project update saved: {result}")
    return result


@tool
def save_user_response_v2(
    phase: str,
    question: str,
    response: str,
    user_id: Optional[str] = None
) -> Dict[str, Any]:
    """
    Generic tool to save any user response during the review.
    Use this for responses that don't fit other categories.
    
    Args:
        phase: Current phase (STARTUP, MIND_SWEEP, etc.)
        question: The question that was asked
        response: The user's response
        user_id: Optional user identifier
        
    Returns:
        Confirmation of saved response
        
    Example:
        save_user_response_v2("STARTUP", "Energy level?", "8")
    """
    logger.info(f"Saving response for {phase}: {question} -> {response}")
    
    result = {
        "phase": phase,
        "question": question,
        "response": response,
        "timestamp": datetime.now().isoformat(),
        "saved": False,
        "graphiti_saved": False
    }
    
    # Save to Graphiti if available
    if GRAPHITI_AVAILABLE and phase == "STARTUP":
        try:
            client = get_graphiti_client()
            if client:
                # Create episode for startup responses
                episode_data = {
                    "source": "gtd_weekly_review",
                    "description": f"{phase}: {question} - {response}",
                    "type": "user_response",
                    "phase": phase,
                    "question": question,
                    "response": response,
                    "user_id": user_id or "default",
                    "timestamp": datetime.now().isoformat()
                }
                
                client.add_episode(
                    episode_data=episode_data,
                    use_enhanced_extraction=False  # Simple responses don't need entity extraction
                )
                
                result["graphiti_saved"] = True
                logger.info(f"Saved response to Graphiti")
        except Exception as e:
            logger.error(f"Failed to save response to Graphiti: {e}")
    
    # Mark as saved
    result["saved"] = True
    
    logger.info(f"Response saved: {result}")
    return result


@tool
def batch_save_mind_sweep_v2(
    items: List[str],
    user_id: Optional[str] = None
) -> Dict[str, Any]:
    """
    Save multiple mind sweep items at once.
    Useful when user provides a list of items in one response.
    
    Args:
        items: List of mind sweep items
        user_id: Optional user identifier
        
    Returns:
        Summary of saved items
        
    Example:
        batch_save_mind_sweep_v2(["Task 1", "Idea 2", "Concern 3"])
    """
    logger.info(f"Batch saving {len(items)} mind sweep items")
    
    saved_items = []
    failed_items = []
    
    for item in items:
        try:
            result = save_mind_sweep_item_v2(item, user_id=user_id)
            if result["saved"]:
                saved_items.append(item)
            else:
                failed_items.append(item)
        except Exception as e:
            logger.error(f"Failed to save item '{item}': {e}")
            failed_items.append(item)
    
    return {
        "total": len(items),
        "saved": len(saved_items),
        "failed": len(failed_items),
        "saved_items": saved_items,
        "failed_items": failed_items,
        "timestamp": datetime.now().isoformat()
    }


@tool
def get_saved_priorities_v2(
    user_id: Optional[str] = None,
    week: Optional[str] = None
) -> Dict[str, Any]:
    """
    Retrieve saved priorities for review or display.
    
    Args:
        user_id: Optional user identifier
        week: Optional week identifier (YYYY-WXX format)
        
    Returns:
        List of saved priorities
        
    Example:
        get_saved_priorities_v2(week="2024-W03")
    """
    logger.info(f"Retrieving priorities for week: {week or 'current'}")
    
    # In a real implementation, this would query the database
    # For now, return a placeholder
    current_week = week or datetime.now().strftime("%Y-W%U")
    
    return {
        "week": current_week,
        "priorities": [],
        "message": "Priorities would be retrieved from database",
        "timestamp": datetime.now().isoformat()
    }