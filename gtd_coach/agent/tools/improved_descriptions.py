#!/usr/bin/env python3
"""
Improved tool descriptions for better LLM tool selection
Optimized for xLAM-7b-fc-r model
"""

# Enhanced tool descriptions with clear "when to use" guidance
IMPROVED_TOOL_DESCRIPTIONS = {
    # Time Management Tools
    'check_time_tool': {
        'name': 'check_time_tool',
        'description': """Check remaining time in current phase and overall session.
        WHEN TO USE: Call this when user asks about time, when you need to decide if phase should end, or every 2-3 interactions to maintain time awareness.
        RETURNS: Time status with urgency level (minutes remaining, warnings if needed)."""
    },
    
    'transition_phase_tool': {
        'name': 'transition_phase_tool', 
        'description': """Transition to the next phase of GTD review.
        WHEN TO USE: Call this when current phase time is up, user requests moving forward, or all phase tasks are complete.
        INPUT: next_phase name (STARTUP, MIND_SWEEP, PROJECT_REVIEW, PRIORITIZATION, WRAP_UP)
        RETURNS: Success status and new phase details."""
    },
    
    # Capture Tools
    'brain_dump_tool': {
        'name': 'brain_dump_tool',
        'description': """Facilitate rapid capture of multiple items from user's mind.
        WHEN TO USE: During MIND_SWEEP phase when user needs to empty their head of all tasks, ideas, and commitments.
        INPUT: Optional category filter
        RETURNS: Capture prompts and storage confirmation."""
    },
    
    'capture_item_tool': {
        'name': 'capture_item_tool',
        'description': """Capture a single item with metadata and classification.
        WHEN TO USE: When user mentions a specific task, project, or commitment that needs to be recorded.
        INPUT: item_text (the task/idea), item_type (task/project/idea/reference), tags (optional)
        RETURNS: Confirmation of captured item with ID."""
    },
    
    # GTD Processing Tools
    'clarify_items_tool': {
        'name': 'clarify_items_tool',
        'description': """Process captured items through GTD clarification questions.
        WHEN TO USE: During PROJECT_REVIEW when items need to be converted to actionable next steps.
        INPUT: item_ids (list of items to clarify)
        RETURNS: Clarified items with next actions defined."""
    },
    
    'prioritize_actions_tool': {
        'name': 'prioritize_actions_tool',
        'description': """Apply priority methods (ABC, Eisenhower, RICE) to actions.
        WHEN TO USE: During PRIORITIZATION phase to rank tasks by importance and urgency.
        INPUT: method (ABC/eisenhower/RICE), actions (list of actions to prioritize)
        RETURNS: Prioritized list with rankings and rationale."""
    },
    
    # Memory Tools
    'save_memory_tool': {
        'name': 'save_memory_tool',
        'description': """Save session data to Graphiti knowledge graph.
        WHEN TO USE: During WRAP_UP phase or when important insights/decisions are made.
        INPUT: memory_type (session/insight/decision), content (what to save)
        RETURNS: Confirmation with memory ID."""
    },
    
    # Interaction Tools
    'structured_input_tool': {
        'name': 'structured_input_tool',
        'description': """Request specific structured input from user.
        WHEN TO USE: When you need user to provide information in a specific format (list, yes/no, rating).
        INPUT: prompt (question to ask), input_type (list/boolean/number/text), options (if choice)
        RETURNS: User's structured response."""
    },
    
    'show_progress_tool': {
        'name': 'show_progress_tool',
        'description': """Display visual progress of current phase and session.
        WHEN TO USE: After completing major steps, phase transitions, or when user needs motivation.
        INPUT: None required
        RETURNS: Progress visualization and stats."""
    },
    
    'provide_encouragement_tool': {
        'name': 'provide_encouragement_tool',
        'description': """Generate ADHD-appropriate encouragement and celebration.
        WHEN TO USE: After user completes tasks, at phase transitions, when detecting struggle or stress.
        INPUT: context (what to celebrate/encourage about)
        RETURNS: Personalized encouragement message."""
    }
}

def get_enhanced_tool_description(tool_name: str) -> str:
    """
    Get enhanced description for a tool
    
    Args:
        tool_name: Name of the tool
        
    Returns:
        Enhanced description string
    """
    tool_info = IMPROVED_TOOL_DESCRIPTIONS.get(tool_name, {})
    return tool_info.get('description', '')

def generate_tool_selection_hints(phase: str, context: Dict) -> str:
    """
    Generate hints for tool selection based on phase and context
    
    Args:
        phase: Current phase
        context: Current context (user state, time remaining, etc.)
        
    Returns:
        Tool selection hints for system prompt
    """
    hints = []
    
    # Time-based hints
    if context.get('time_remaining', 10) < 2:
        hints.append("Time is running out - use transition_phase_tool soon")
    elif context.get('time_remaining', 10) < 5:
        hints.append("Check time frequently with check_time_tool")
    
    # Phase-specific hints
    phase_hints = {
        'STARTUP': [
            "Use load_context_tool to get user history",
            "Use assess_user_state_tool to check energy/focus",
            "Use provide_encouragement_tool to set positive tone"
        ],
        'MIND_SWEEP': [
            "Use brain_dump_tool for rapid capture",
            "Use scan_inbox_tool for systematic review",
            "Use detect_capture_patterns_tool to identify themes"
        ],
        'PROJECT_REVIEW': [
            "Use clarify_items_tool to process captures",
            "Use create_project_tool for multi-step items",
            "Use analyze_timing_tool if time data available"
        ],
        'PRIORITIZATION': [
            "Use prioritize_actions_tool with ABC method",
            "Use calculate_focus_alignment_tool for validation",
            "Use structured_input_tool for user choices"
        ],
        'WRAP_UP': [
            "Use save_memory_tool to persist session",
            "Use get_session_time_summary_tool for metrics",
            "Use provide_encouragement_tool to celebrate"
        ]
    }
    
    hints.extend(phase_hints.get(phase, []))
    
    # Stress/struggle detection hints
    if context.get('stress_level', 0) > 0.7:
        hints.append("User seems stressed - use provide_intervention_tool")
    
    if context.get('items_captured', 0) < 3 and phase == 'MIND_SWEEP':
        hints.append("Few items captured - use brain_dump_tool with prompts")
    
    return " | ".join(hints) if hints else ""