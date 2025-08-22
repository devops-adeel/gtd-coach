#!/usr/bin/env python3
"""
Todoist Integration Tools for GTD Agent
Tools for interacting with Todoist API for task management
"""

import os
import logging
from typing import Dict, List, Optional
from datetime import datetime
from langchain_core.tools import tool

# Import Todoist client
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from gtd_coach.integrations.todoist import TodoistClient

logger = logging.getLogger(__name__)


@tool
def get_inbox_tasks_tool() -> List[Dict]:
    """
    Get all tasks from Todoist inbox.
    
    Returns:
        List of dictionaries containing:
        - id: Task ID
        - content: Task description
        - created_at: Creation timestamp
        - priority: Task priority (1-4)
        - labels: List of label names
    """
    try:
        client = TodoistClient()
        
        if not client.is_configured():
            return {
                "error": "Todoist not configured",
                "message": "Set TODOIST_API_KEY in environment",
                "tasks": []
            }
        
        tasks = client.get_inbox_tasks()
        logger.info(f"Retrieved {len(tasks)} tasks from inbox")
        
        return {
            "success": True,
            "count": len(tasks),
            "tasks": tasks
        }
        
    except Exception as e:
        logger.error(f"Failed to get inbox tasks: {e}")
        return {
            "error": str(e),
            "tasks": []
        }


@tool
def add_to_today_tool(
    content: str,
    is_deep_work: bool = False,
    priority: Optional[int] = None
) -> Dict:
    """
    Add a task to today's list in Todoist.
    
    Args:
        content: Task description
        is_deep_work: Whether this is a deep work task (adds 2h duration label)
        priority: Priority level (1=urgent/important, 4=low priority)
    
    Returns:
        Dictionary with:
        - success: Whether task was added successfully
        - task_id: ID of created task
        - message: Status message
    """
    try:
        client = TodoistClient()
        
        if not client.is_configured():
            return {
                "success": False,
                "message": "Todoist not configured. Set TODOIST_API_KEY"
            }
        
        # Add task with appropriate settings
        task_data = client.add_to_today(
            content=content,
            is_deep_work=is_deep_work
        )
        
        if task_data:
            logger.info(f"Added task to today: {content[:50]}...")
            return {
                "success": True,
                "task_id": task_data.get('id'),
                "message": f"Added {'deep work' if is_deep_work else 'task'}: {content}"
            }
        else:
            return {
                "success": False,
                "message": "Failed to add task"
            }
            
    except Exception as e:
        logger.error(f"Failed to add task: {e}")
        return {
            "success": False,
            "message": f"Error: {str(e)}"
        }


@tool
def mark_task_complete_tool(task_id: str) -> Dict:
    """
    Mark a Todoist task as complete.
    
    Args:
        task_id: The Todoist task ID to complete
    
    Returns:
        Dictionary with:
        - success: Whether task was completed successfully
        - message: Status message
    """
    try:
        client = TodoistClient()
        
        if not client.is_configured():
            return {
                "success": False,
                "message": "Todoist not configured"
            }
        
        result = client.mark_complete(task_id)
        
        if result:
            logger.info(f"Marked task {task_id} as complete")
            return {
                "success": True,
                "message": f"Completed task {task_id}"
            }
        else:
            return {
                "success": False,
                "message": f"Failed to complete task {task_id}"
            }
            
    except Exception as e:
        logger.error(f"Failed to mark task complete: {e}")
        return {
            "success": False,
            "message": f"Error: {str(e)}"
        }


@tool
def check_deep_work_limit_tool() -> Dict:
    """
    Check how many deep work tasks are already scheduled for today.
    
    Returns:
        Dictionary with:
        - deep_work_count: Number of deep work tasks today
        - can_add_more: Whether more deep work can be added (limit is 2)
        - message: Status message
    """
    try:
        client = TodoistClient()
        
        if not client.is_configured():
            return {
                "deep_work_count": 0,
                "can_add_more": False,
                "message": "Todoist not configured"
            }
        
        # Get today's tasks and count deep work
        today_tasks = client.get_tasks_for_date(datetime.now())
        deep_work_count = sum(
            1 for task in today_tasks 
            if any('deep_work' in label or '2h' in label 
                   for label in task.get('labels', []))
        )
        
        can_add_more = deep_work_count < 2
        
        return {
            "deep_work_count": deep_work_count,
            "can_add_more": can_add_more,
            "message": f"{deep_work_count}/2 deep work blocks used"
        }
        
    except Exception as e:
        logger.error(f"Failed to check deep work limit: {e}")
        return {
            "deep_work_count": 0,
            "can_add_more": False,
            "message": f"Error: {str(e)}"
        }


@tool
def analyze_task_for_deep_work_tool(content: str) -> Dict:
    """
    Analyze if a task should be classified as deep work.
    
    Args:
        content: Task description to analyze
    
    Returns:
        Dictionary with:
        - is_deep_work: Whether task appears to be deep work
        - confidence: Confidence score (0-1)
        - keywords_found: Keywords that matched
        - recommendation: Suggested handling
    """
    # Deep work keywords from original daily_clarify.py
    deep_keywords = [
        'refactor', 'design', 'analyze', 'create', 'write',
        'plan', 'research', 'build', 'architect', 'implement',
        'develop', 'optimize', 'debug', 'review', 'document'
    ]
    
    content_lower = content.lower()
    found_keywords = [kw for kw in deep_keywords if kw in content_lower]
    
    # Calculate confidence based on keyword matches
    confidence = min(len(found_keywords) * 0.3, 1.0)
    is_deep = len(found_keywords) > 0
    
    # Check for explicit time estimates
    if any(indicator in content_lower for indicator in ['2h', '2 hour', 'two hour', 'complex', 'major']):
        confidence = min(confidence + 0.3, 1.0)
        is_deep = True
    
    recommendation = "Schedule as 2-hour deep work block" if is_deep else "Add as regular task"
    
    return {
        "is_deep_work": is_deep,
        "confidence": confidence,
        "keywords_found": found_keywords,
        "recommendation": recommendation
    }


# Export all tools
__all__ = [
    'get_inbox_tasks_tool',
    'add_to_today_tool',
    'mark_task_complete_tool',
    'check_deep_work_limit_tool',
    'analyze_task_for_deep_work_tool'
]