#!/usr/bin/env python3
"""
Clarify Decision Tools V3 - Single Interrupt Pattern
Tools for making keep/delete decisions on tasks with clean state management
"""

import logging
from typing import Dict, Optional
from langchain_core.tools import tool
from langgraph.types import interrupt

# Import monitoring
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from gtd_coach.observability.interrupt_monitor import monitor_interrupt

logger = logging.getLogger(__name__)


@tool
@monitor_interrupt("clarify_decision_v3")
def clarify_decision_v3(
    task_content: str,
    task_number: Optional[int] = None,
    total_tasks: Optional[int] = None
) -> str:
    """
    Get user's keep/delete decision for a single task.
    Uses single interrupt pattern to avoid state pollution.
    
    Args:
        task_content: The task description to decide on
        task_number: Current task number (for progress display)
        total_tasks: Total number of tasks (for progress display)
    
    Returns:
        "keep" or "delete" based on user response
    """
    # Build the prompt
    if task_number and total_tasks:
        prompt = f"\n[{task_number}/{total_tasks}] {task_content}\n  Keep? (y/n or Enter for yes): "
    else:
        prompt = f"\nTask: {task_content}\n  Keep? (y/n or Enter for yes): "
    
    # Single interrupt - clean state management
    logger.debug(f"Asking clarify decision for: {task_content[:50]}...")
    response = interrupt(prompt)
    
    # Process response
    response_lower = response.strip().lower()
    decision = "keep" if response_lower in ['', 'y', 'yes'] else "delete"
    
    logger.info(f"Decision for '{task_content[:30]}...': {decision}")
    return decision


@tool
@monitor_interrupt("batch_clarify_preview_v3")
def batch_clarify_preview_v3(
    task_count: int,
    sample_tasks: Optional[list] = None
) -> str:
    """
    Show preview of clarify session and get user confirmation to proceed.
    Uses single interrupt pattern.
    
    Args:
        task_count: Number of tasks to process
        sample_tasks: Optional list of first few tasks to preview
    
    Returns:
        "proceed" or "cancel" based on user response
    """
    # Build preview message
    message = f"\n📥 Found {task_count} items in inbox\n"
    message += "=" * 50 + "\n"
    
    if sample_tasks and len(sample_tasks) > 0:
        message += "\nFirst few items:\n"
        for i, task in enumerate(sample_tasks[:3], 1):
            task_text = task.get('content', str(task))[:60]
            message += f"  {i}. {task_text}...\n"
        if task_count > 3:
            message += f"  ... and {task_count - 3} more\n"
    
    message += "\n🎯 One decision per item: Keep or Delete?\n"
    message += "Ready to start? (y/n): "
    
    # Single interrupt
    response = interrupt(message)
    
    response_lower = response.strip().lower()
    decision = "proceed" if response_lower in ['y', 'yes'] else "cancel"
    
    logger.info(f"Batch clarify preview: {decision}")
    return decision


@tool
@monitor_interrupt("deep_work_confirmation_v3")
def deep_work_confirmation_v3(
    task_content: str,
    current_deep_count: int = 0
) -> str:
    """
    Confirm if a task should be scheduled as deep work.
    Uses single interrupt pattern.
    
    Args:
        task_content: The task to potentially mark as deep work
        current_deep_count: How many deep work blocks already scheduled
    
    Returns:
        "deep" or "regular" based on user response
    """
    remaining = 2 - current_deep_count
    
    prompt = f"\n🎯 Potential deep work task detected:\n"
    prompt += f"   '{task_content}'\n\n"
    
    if remaining > 0:
        prompt += f"Schedule as 2-hour deep work block? ({remaining} slots remaining)\n"
        prompt += "(y for deep work, n for regular task): "
    else:
        prompt += "Daily deep work limit reached (2 blocks). Add as regular task? (y/n): "
        
    # Single interrupt
    response = interrupt(prompt)
    
    response_lower = response.strip().lower()
    
    if remaining > 0:
        decision = "deep" if response_lower in ['y', 'yes'] else "regular"
    else:
        # If limit reached, only option is regular or skip
        decision = "regular" if response_lower in ['y', 'yes'] else "skip"
    
    logger.info(f"Deep work decision for '{task_content[:30]}...': {decision}")
    return decision


@tool
@monitor_interrupt("clarify_break_v3")
def clarify_break_v3(
    items_processed: int,
    items_remaining: int
) -> str:
    """
    Offer a break during clarify session to prevent decision fatigue.
    Uses single interrupt pattern.
    
    Args:
        items_processed: Number of items processed so far
        items_remaining: Number of items left to process
    
    Returns:
        "continue" or "pause" based on user response
    """
    prompt = f"\n--- Quick break! ---\n"
    prompt += f"Processed: {items_processed} items\n"
    prompt += f"Remaining: {items_remaining} items\n"
    prompt += "Take 30 seconds to rest your brain.\n"
    prompt += "Press Enter to continue or 'p' to pause session: "
    
    # Single interrupt
    response = interrupt(prompt)
    
    response_lower = response.strip().lower()
    decision = "pause" if response_lower in ['p', 'pause', 'stop'] else "continue"
    
    logger.info(f"Break decision after {items_processed} items: {decision}")
    return decision


@tool
def clarify_session_summary_v3(
    processed: int,
    deleted: int,
    deep_work: int,
    quick_tasks: int
) -> Dict:
    """
    Generate and display clarify session summary.
    No interrupt - just formats results.
    
    Args:
        processed: Total items processed
        deleted: Number of items deleted
        deep_work: Number of deep work blocks scheduled
        quick_tasks: Number of regular tasks added
    
    Returns:
        Dictionary with formatted summary and metrics
    """
    deletion_rate = (deleted / processed * 100) if processed > 0 else 0
    
    summary = "\n" + "=" * 50 + "\n"
    summary += "📊 CLARIFY COMPLETE!\n"
    summary += "=" * 50 + "\n\n"
    summary += f"✅ Processed: {processed} items\n"
    summary += f"🗑️  Deleted: {deleted} items\n"
    summary += f"🎯 Deep work blocks: {deep_work}\n"
    summary += f"📝 Quick tasks: {quick_tasks}\n"
    
    if deleted > 0:
        summary += f"\n💪 Deletion rate: {deletion_rate:.0f}% - Good job saying NO!\n"
    
    summary += "\n🎉 Inbox Zero achieved!"
    
    # Log the summary
    logger.info(f"Clarify session complete: {processed} processed, {deleted} deleted")
    
    return {
        "summary": summary,
        "metrics": {
            "processed": processed,
            "deleted": deleted,
            "deep_work": deep_work,
            "quick_tasks": quick_tasks,
            "deletion_rate": deletion_rate
        }
    }


# Export all tools
__all__ = [
    'clarify_decision_v3',
    'batch_clarify_preview_v3',
    'deep_work_confirmation_v3',
    'clarify_break_v3',
    'clarify_session_summary_v3'
]