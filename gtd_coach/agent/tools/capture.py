#!/usr/bin/env python3
"""
Capture Tools for GTD Agent
Tools for scanning inboxes and capturing items
"""

import logging
from typing import Dict, List, Optional, Annotated
from datetime import datetime
from langchain_core.tools import tool
from langgraph.prebuilt import InjectedState

# Import state
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from gtd_coach.agent.state import AgentState, DailyCapture

logger = logging.getLogger(__name__)


@tool
def scan_inbox_tool(
    inbox_type: str,
    state: Annotated[AgentState, InjectedState] = None
) -> Dict:
    """
    Guides user through scanning a specific inbox and captures items.
    
    Args:
        inbox_type: Type of inbox to scan (outlook, physical, beeper, slack, calendar)
        state: Injected agent state
    
    Returns:
        Dictionary with:
        - inbox_type: The inbox that was scanned
        - guidance: Instructions for the user
        - capture_prompt: What to ask the user
        - example_items: Examples of what to capture
    """
    guidance_map = {
        "outlook": {
            "guidance": "Open Outlook and scan your inbox. Focus on:",
            "prompts": [
                "• Emails requiring action or response",
                "• Meeting invites needing decision",
                "• Important updates to review",
                "• Attachments to process"
            ],
            "example_items": [
                "Reply to Sarah about project timeline",
                "Review Q4 budget spreadsheet",
                "Schedule 1:1 with team lead"
            ]
        },
        "physical": {
            "guidance": "Check your physical inbox, desk, and pockets. Look for:",
            "prompts": [
                "• Papers or sticky notes",
                "• Business cards to process",
                "• Receipts or bills",
                "• Handwritten notes or reminders"
            ],
            "example_items": [
                "Enter receipts into expense system",
                "File insurance paperwork",
                "Call number on business card"
            ]
        },
        "beeper": {
            "guidance": "Open Beeper/texts and check all messaging apps. Scan for:",
            "prompts": [
                "• Unread messages needing response",
                "• Shared links to review",
                "• Action items from conversations",
                "• Scheduling requests"
            ],
            "example_items": [
                "Reply to Mom about weekend plans",
                "Check link John sent about new tool",
                "Confirm dinner reservation"
            ]
        },
        "slack": {
            "guidance": "Check Slack for important messages. Focus on:",
            "prompts": [
                "• Direct messages and mentions",
                "• Important channel updates",
                "• Threads you're following",
                "• Shared documents or decisions"
            ],
            "example_items": [
                "Respond to PR review request",
                "Read product update in #announcements",
                "Follow up on deployment issue"
            ]
        },
        "calendar": {
            "guidance": "Review your calendar for the next week. Check for:",
            "prompts": [
                "• Meetings needing preparation",
                "• Deadlines approaching",
                "• Travel or logistics to arrange",
                "• Follow-ups from past meetings"
            ],
            "example_items": [
                "Prepare slides for Tuesday presentation",
                "Book flight for conference",
                "Send agenda for planning meeting"
            ]
        }
    }
    
    inbox_info = guidance_map.get(inbox_type, {
        "guidance": f"Check your {inbox_type}",
        "prompts": ["• Any items needing attention"],
        "example_items": []
    })
    
    # Format the response
    result = {
        "inbox_type": inbox_type,
        "guidance": inbox_info["guidance"],
        "prompts": inbox_info["prompts"],
        "example_items": inbox_info["example_items"],
        "capture_instruction": "List items one per line. Type 'done' when finished, or 'skip' to move on."
    }
    
    # Add tool invocation metadata
    result['tool_metadata'] = {
        'tool': 'scan_inbox_tool',
        'inbox': inbox_type,
        'timestamp': datetime.now().isoformat()
    }
    
    return result


@tool  
def brain_dump_tool(
    state: Annotated[AgentState, InjectedState] = None
) -> Dict:
    """
    Facilitates open-ended brain dump capture with ADHD pattern detection.
    
    Args:
        state: Injected agent state
    
    Returns:
        Dictionary with:
        - prompt: Brain dump prompt for the user
        - detected_patterns: Any ADHD patterns noticed
        - suggestions: Tips for effective capture
    """
    # Customize prompt based on user state
    prompts = []
    
    if state and state.get('accountability_mode') == 'gentle':
        prompts.append("What's on your mind? No judgment, just capture everything:")
    elif state and state.get('accountability_mode') == 'firm':
        prompts.append("Time to empty your brain. Be thorough - capture EVERYTHING:")
    else:
        prompts.append("Brain dump time! What's taking up mental space?")
    
    # Add contextual prompts based on patterns
    if state and state.get('adhd_patterns'):
        if 'task_switching' in state['adhd_patterns']:
            prompts.append("• Include all those half-finished tasks bouncing around")
        if 'perfectionism' in state['adhd_patterns']:
            prompts.append("• Don't edit yourself - capture now, clarify later")
    
    # Suggestions for effective capture
    suggestions = [
        "💡 Don't filter - capture everything",
        "💡 Include worries and 'shoulds'",
        "💡 Note any recurring thoughts",
        "💡 Capture even if unsure about action"
    ]
    
    # Tips based on time of day
    current_hour = datetime.now().hour
    if current_hour < 9:
        suggestions.append("☕ Morning capture - include today's concerns")
    elif current_hour > 17:
        suggestions.append("🌅 Evening capture - include tomorrow's prep")
    
    return {
        "prompt": "\n".join(prompts),
        "suggestions": suggestions,
        "capture_instruction": "Type thoughts as they come. Press Enter after each. Type 'done' when complete.",
        "voice_option": "Type 'voice' to switch to voice capture (if enabled)",
        "pattern_tracking": "I'll watch for patterns like rapid topic switching"
    }


@tool
def capture_item_tool(
    content: str,
    source: str,
    state: Annotated[AgentState, InjectedState] = None
) -> Dict:
    """
    Captures a single item with metadata and pattern detection.
    
    Args:
        content: The item to capture
        source: Where it came from (inbox type or 'brain_dump')
        state: Injected agent state
    
    Returns:
        Dictionary with:
        - captured: The processed capture
        - patterns_detected: Any patterns noticed
        - quick_categorization: Initial category suggestion
    """
    # Create capture object
    capture = DailyCapture(
        content=content,
        source=source,
        capture_time=datetime.now().isoformat(),
        category=None,  # Will be set during clarification
        processed=False
    )
    
    # Quick categorization based on keywords
    content_lower = content.lower()
    
    if any(word in content_lower for word in ['email', 'reply', 'respond', 'send']):
        capture.category = 'task'
        quick_category = 'communication'
    elif any(word in content_lower for word in ['meeting', 'call', 'schedule', 'appointment']):
        capture.category = 'task'
        quick_category = 'scheduling'
    elif any(word in content_lower for word in ['review', 'read', 'check', 'look at']):
        capture.category = 'task'
        quick_category = 'review'
    elif any(word in content_lower for word in ['buy', 'purchase', 'order', 'get']):
        capture.category = 'task'
        quick_category = 'shopping'
    elif any(word in content_lower for word in ['idea', 'maybe', 'could', 'should consider']):
        capture.category = 'someday'
        quick_category = 'idea'
    elif '?' in content:
        capture.category = 'waiting'
        quick_category = 'question'
    else:
        quick_category = 'uncategorized'
    
    # Pattern detection
    patterns = []
    
    # Check for overwhelm indicators
    if any(word in content_lower for word in ['everything', 'so much', 'overwhelming', 'too many']):
        patterns.append('overwhelm')
    
    # Check for procrastination indicators
    if any(word in content_lower for word in ['should have', 'need to finally', 'been putting off']):
        patterns.append('procrastination')
    
    # Check for anxiety indicators  
    if any(word in content_lower for word in ['worried', 'anxious', 'stressed', 'nervous']):
        patterns.append('anxiety')
    
    # Analyze rapid switching if we have state
    topic_switch_detected = False
    if state and state.get('captures'):
        if len(state['captures']) > 0:
            last_capture = state['captures'][-1]
            if quick_category != 'uncategorized':
                last_category = _get_quick_category(last_capture.get('content', ''))
                if last_category != quick_category:
                    topic_switch_detected = True
    
    return {
        "captured": capture.dict(),
        "quick_categorization": quick_category,
        "patterns_detected": patterns,
        "capture_count": len(state.get('captures', [])) + 1 if state else 1,
        "topic_switch_detected": topic_switch_detected,
        "message": f"✓ Captured: '{content[:50]}...'" if len(content) > 50 else f"✓ Captured: '{content}'"
    }


@tool
def detect_capture_patterns_tool(
    state: Annotated[AgentState, InjectedState] = None
) -> Dict:
    """
    Analyzes captured items for ADHD patterns and provides insights.
    
    Args:
        state: Injected agent state with captures
    
    Returns:
        Dictionary with pattern analysis and recommendations
    """
    if not state or not state.get('captures'):
        return {
            "patterns": [],
            "message": "No captures to analyze"
        }
    
    captures = state['captures']
    patterns = {}
    
    # Analyze topic switching
    topic_switches = 0
    last_category = None
    
    for capture in captures:
        category = _get_quick_category(capture.get('content', ''))
        if last_category and category != last_category:
            topic_switches += 1
        last_category = category
    
    if len(captures) > 5:
        switch_rate = topic_switches / len(captures)
        if switch_rate > 0.7:
            patterns['rapid_switching'] = {
                'severity': 'high',
                'description': 'Frequent topic changes detected',
                'recommendation': 'Consider grouping related items before processing'
            }
        elif switch_rate > 0.4:
            patterns['moderate_switching'] = {
                'severity': 'medium',
                'description': 'Some topic jumping noticed',
                'recommendation': 'Normal capture pattern - proceed with clarification'
            }
    
    # Check for overwhelm
    overwhelm_words = ['everything', 'so much', 'overwhelming', 'too many', 'cant keep up']
    overwhelm_count = sum(
        1 for c in captures
        if any(word in c.get('content', '').lower() for word in overwhelm_words)
    )
    
    if overwhelm_count >= 3:
        patterns['overwhelm'] = {
            'severity': 'high',
            'description': 'Multiple overwhelm indicators detected',
            'recommendation': 'Break down large items into smaller, concrete next actions'
        }
    
    # Check for procrastination patterns
    procrastination_words = ['should have', 'need to finally', 'been putting off', 'keep forgetting']
    procrastination_count = sum(
        1 for c in captures
        if any(word in c.get('content', '').lower() for word in procrastination_words)
    )
    
    if procrastination_count >= 2:
        patterns['procrastination'] = {
            'severity': 'medium',
            'description': 'Several overdue items identified',
            'recommendation': 'Identify quick wins and schedule specific times for harder tasks'
        }
    
    # Check capture volume
    if len(captures) > 20:
        patterns['high_volume'] = {
            'severity': 'medium',
            'description': f'{len(captures)} items captured',
            'recommendation': 'Good thorough capture! Take breaks during clarification'
        }
    elif len(captures) < 5:
        patterns['low_volume'] = {
            'severity': 'low',
            'description': f'Only {len(captures)} items captured',
            'recommendation': 'Consider if anything else is on your mind'
        }
    
    # Return pattern analysis for state update
    
    return {
        "total_captures": len(captures),
        "patterns": patterns,
        "topic_switches": topic_switches,
        "adaptive_recommendation": _get_adaptive_recommendation(patterns)
    }


def _get_quick_category(content: str) -> str:
    """Quick categorization helper"""
    content_lower = content.lower()
    
    if any(word in content_lower for word in ['email', 'reply', 'respond']):
        return 'communication'
    elif any(word in content_lower for word in ['meeting', 'call', 'schedule']):
        return 'scheduling'
    elif any(word in content_lower for word in ['review', 'read', 'check']):
        return 'review'
    elif any(word in content_lower for word in ['buy', 'purchase', 'order']):
        return 'shopping'
    elif any(word in content_lower for word in ['idea', 'maybe', 'could']):
        return 'idea'
    else:
        return 'general'


def _get_adaptive_recommendation(patterns: Dict) -> str:
    """Generate adaptive recommendation based on patterns"""
    if not patterns:
        return "Good capture session! Ready to clarify these items."
    
    high_severity = [p for p in patterns.values() if p['severity'] == 'high']
    
    if len(high_severity) >= 2:
        return "I notice several patterns. Let's take this clarification slowly and break things down into manageable pieces."
    elif 'overwhelm' in patterns:
        return "Seems like a lot on your plate. Remember: you don't have to do everything today, just capture and clarify."
    elif 'rapid_switching' in patterns:
        return "Your mind is quite active! Let's organize these thoughts into clear next actions."
    elif 'procrastination' in patterns:
        return "Some overdue items here. Let's identify the real next actions to get unstuck."
    else:
        return "Normal capture patterns detected. Let's process these efficiently."