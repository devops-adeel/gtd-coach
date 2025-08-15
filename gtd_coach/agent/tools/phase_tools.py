#!/usr/bin/env python3
"""
Phase-based tool loading for GTD Agent
Optimizes context usage by loading only relevant tools per phase
"""

from typing import List, Dict

# Define tool sets for each phase
PHASE_TOOL_MAPPING = {
    'STARTUP': [
        # Time tools for phase management
        'check_time_tool',
        'transition_phase_tool',
        'send_alert_tool',
        # Memory tools for context loading
        'load_context_tool',
        'assess_user_state_tool',
        # Interaction tools for setup
        'provide_encouragement_tool',
        'show_progress_tool',
    ],
    
    'MIND_SWEEP': [
        # Core capture tools
        'brain_dump_tool',
        'capture_item_tool',
        'quick_capture_tool',
        'scan_inbox_tool',
        # Pattern detection
        'detect_capture_patterns_tool',
        # Time management
        'check_time_tool',
        'send_alert_tool',
        # Interaction
        'structured_input_tool',
        'show_progress_tool',
    ],
    
    'PROJECT_REVIEW': [
        # GTD processing tools
        'clarify_items_tool',
        'organize_tool', 
        'create_project_tool',
        # Time management
        'check_time_tool',
        'transition_phase_tool',
        # Timing analysis
        'analyze_timing_tool',
        'review_uncategorized_tool',
        # Interaction
        'confirm_completion_tool',
        'show_progress_tool',
    ],
    
    'PRIORITIZATION': [
        # Priority tools
        'prioritize_actions_tool',
        'calculate_focus_alignment_tool',
        # Time management
        'check_time_tool',
        'transition_phase_tool',
        # Adaptive behavior
        'adjust_behavior_tool',
        'provide_intervention_tool',
        # Interaction
        'structured_input_tool',
        'show_progress_tool',
    ],
    
    'WRAP_UP': [
        # Memory and save tools
        'save_memory_tool',
        'update_user_context_tool',
        # Summary tools
        'get_session_time_summary_tool',
        # Pattern analysis
        'detect_patterns_tool',
        # Time management
        'check_time_tool',
        # Interaction
        'provide_encouragement_tool',
        'show_progress_tool',
    ]
}

def get_tools_for_phase(phase: str, all_tools: Dict) -> List:
    """
    Get the appropriate tools for the current phase
    
    Args:
        phase: Current phase name
        all_tools: Dictionary of all available tools
        
    Returns:
        List of tools appropriate for the phase
    """
    tool_names = PHASE_TOOL_MAPPING.get(phase, [])
    
    # Add essential tools that are always available
    essential_tools = [
        'check_time_tool',
        'send_alert_tool',
        'show_progress_tool',
    ]
    
    # Combine phase tools with essentials (deduplicated)
    combined_names = list(set(tool_names + essential_tools))
    
    # Get actual tool objects
    phase_tools = []
    for name in combined_names:
        if name in all_tools:
            phase_tools.append(all_tools[name])
    
    return phase_tools

def describe_phase_tools(phase: str) -> str:
    """
    Get a description of available tools for the phase
    
    Args:
        phase: Current phase name
        
    Returns:
        Description string for system prompt
    """
    tool_names = PHASE_TOOL_MAPPING.get(phase, [])
    
    descriptions = {
        'STARTUP': "time tracking, context loading, and encouragement tools",
        'MIND_SWEEP': "capture, inbox scanning, and pattern detection tools",
        'PROJECT_REVIEW': "GTD processing, project creation, and timing analysis tools",
        'PRIORITIZATION': "priority setting, focus alignment, and intervention tools",
        'WRAP_UP': "memory saving, summary generation, and celebration tools"
    }
    
    return descriptions.get(phase, "standard GTD tools")