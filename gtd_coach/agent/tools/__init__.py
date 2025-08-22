#!/usr/bin/env python3
"""
GTD Agent Tools Registry
Central registry for all agent tools with versioning support
"""

from typing import Dict, List, Any, Optional
import logging

# Import time management tools (V2 - No InjectedState)
from .time_manager_v2 import (
    check_time_v2 as check_time_tool,
    transition_phase_v2 as transition_phase_tool,
    send_alert_v2 as send_alert_tool,
    get_session_summary_v2 as get_session_time_summary_tool,
    set_reminder_v2 as set_time_reminder_tool,
    initialize_state_manager
)

# Import interaction tools (NEW)
from .interaction import (
    structured_input_tool,
    quick_capture_tool,
    confirm_completion_tool,
    show_progress_tool,
    provide_encouragement_tool
)

# Import conversation tools (V3 - Fixed single interrupt pattern)
from .conversation_v3 import (
    ask_question_v3,
    ask_yes_no_v3,
    startup_questions_v3,
    collect_mind_sweep_v3,
    collect_priorities_v3,
    # Legacy compatibility wrappers
    wait_for_user_input_v3,
    confirm_with_user_v3
)

# Import clarify tools (V3 - Single interrupt for decisions)
from .clarify_v3 import (
    clarify_decision_v3,
    batch_clarify_preview_v3,
    deep_work_confirmation_v3,
    clarify_break_v3,
    clarify_session_summary_v3
)

# Import Todoist integration tools
from .todoist import (
    get_inbox_tasks_tool,
    add_to_today_tool,
    mark_task_complete_tool,
    check_deep_work_limit_tool,
    analyze_task_for_deep_work_tool
)

# Import data capture tools (V2 - Data persistence)
from .capture_v2 import (
    save_mind_sweep_item_v2,
    save_weekly_priority_v2,
    save_project_update_v2,
    save_user_response_v2,
    batch_save_mind_sweep_v2,
    get_saved_priorities_v2
)

# Import all existing tools
from .timing import (
    analyze_timing_tool,
    review_uncategorized_tool,
    calculate_focus_alignment_tool
)
from .capture import (
    scan_inbox_tool,
    brain_dump_tool,
    capture_item_tool,
    detect_capture_patterns_tool
)
from .gtd import (
    clarify_items_tool,
    organize_tool,
    create_project_tool,
    prioritize_actions_tool
)
from .graphiti import (
    save_memory_tool,
    load_context_tool,
    search_memory_tool,
    update_user_context_tool
)
from .adaptive import (
    detect_patterns_tool,
    adjust_behavior_tool,
    provide_intervention_tool,
    assess_user_state_tool
)

logger = logging.getLogger(__name__)


class ToolRegistry:
    """
    Registry for managing tools with versioning and feature flags
    """
    
    def __init__(self):
        """Initialize the tool registry"""
        self.tools = {}
        self.versions = {}
        self.feature_flags = {}
        self._register_all_tools()
    
    def _register_all_tools(self):
        """Register all available tools with metadata"""
        
        # Timing tools
        self.register_tool(
            analyze_timing_tool,
            category="timing",
            version="1.0",
            description="Analyzes time tracking data from Timing app"
        )
        self.register_tool(
            review_uncategorized_tool,
            category="timing",
            version="1.0",
            description="Reviews uncategorized time blocks"
        )
        self.register_tool(
            calculate_focus_alignment_tool,
            category="timing",
            version="1.0",
            description="Calculates alignment between time and priorities"
        )
        
        # Capture tools
        self.register_tool(
            scan_inbox_tool,
            category="capture",
            version="1.0",
            description="Guides through inbox scanning"
        )
        self.register_tool(
            brain_dump_tool,
            category="capture",
            version="1.0",
            description="Facilitates brain dump capture"
        )
        self.register_tool(
            capture_item_tool,
            category="capture",
            version="1.0",
            description="Captures single item with metadata"
        )
        self.register_tool(
            detect_capture_patterns_tool,
            category="capture",
            version="1.0",
            description="Detects ADHD patterns in captures"
        )
        
        # GTD processing tools
        self.register_tool(
            clarify_items_tool,
            category="gtd",
            version="1.0",
            description="Clarifies items through GTD methodology"
        )
        self.register_tool(
            organize_tool,
            category="gtd",
            version="1.0",
            description="Organizes items into GTD system"
        )
        self.register_tool(
            create_project_tool,
            category="gtd",
            version="1.0",
            description="Creates GTD project from items"
        )
        self.register_tool(
            prioritize_actions_tool,
            category="gtd",
            version="1.0",
            description="Prioritizes actions using various methods"
        )
        
        # Memory tools
        self.register_tool(
            save_memory_tool,
            category="memory",
            version="1.0",
            description="Saves to Graphiti knowledge graph"
        )
        self.register_tool(
            load_context_tool,
            category="memory",
            version="1.0",
            description="Loads user context from memory"
        )
        self.register_tool(
            search_memory_tool,
            category="memory",
            version="1.0",
            description="Searches memory for information"
        )
        self.register_tool(
            update_user_context_tool,
            category="memory",
            version="1.0",
            description="Updates user context"
        )
        
        # Adaptive tools
        self.register_tool(
            detect_patterns_tool,
            category="adaptive",
            version="1.0",
            description="Detects ADHD behavior patterns"
        )
        self.register_tool(
            adjust_behavior_tool,
            category="adaptive",
            version="1.0",
            description="Adjusts coaching behavior"
        )
        self.register_tool(
            provide_intervention_tool,
            category="adaptive",
            version="1.0",
            description="Provides real-time interventions"
        )
        self.register_tool(
            assess_user_state_tool,
            category="adaptive",
            version="1.0",
            description="Assesses current user state"
        )
    
    def register_tool(self, tool, category: str, version: str, description: str):
        """Register a tool with metadata"""
        tool_name = tool.name
        
        # Store tool with metadata
        self.tools[tool_name] = {
            'tool': tool,
            'category': category,
            'version': version,
            'description': description,
            'enabled': True
        }
        
        # Track versions for A/B testing
        if tool_name not in self.versions:
            self.versions[tool_name] = {}
        self.versions[tool_name][version] = tool
        
        logger.debug(f"Registered tool: {tool_name} v{version}")
    
    def get_tool(self, name: str, version: Optional[str] = None):
        """Get a specific tool by name and optional version"""
        if name not in self.tools:
            raise ValueError(f"Tool {name} not registered")
        
        if version:
            if name in self.versions and version in self.versions[name]:
                return self.versions[name][version]
            else:
                raise ValueError(f"Version {version} not found for tool {name}")
        
        return self.tools[name]['tool']
    
    def get_tools_by_category(self, category: str) -> List:
        """Get all tools in a category"""
        return [
            meta['tool'] for name, meta in self.tools.items()
            if meta['category'] == category and meta['enabled']
        ]
    
    def get_tools_for_workflow(self, workflow_type: str) -> List:
        """Get tools needed for a specific workflow"""
        if workflow_type == "daily_capture":
            categories = ["timing", "capture", "gtd", "memory", "adaptive"]
        elif workflow_type == "weekly_review":
            categories = ["timing", "gtd", "memory", "adaptive"]
        elif workflow_type == "quick_check":
            categories = ["capture", "gtd", "adaptive"]
        else:
            categories = ["capture", "gtd", "memory", "adaptive"]
        
        tools = []
        for category in categories:
            tools.extend(self.get_tools_by_category(category))
        
        return tools
    
    def enable_tool(self, name: str):
        """Enable a tool"""
        if name in self.tools:
            self.tools[name]['enabled'] = True
    
    def disable_tool(self, name: str):
        """Disable a tool"""
        if name in self.tools:
            self.tools[name]['enabled'] = False
    
    def set_feature_flag(self, flag: str, value: bool):
        """Set a feature flag for conditional tool behavior"""
        self.feature_flags[flag] = value
        logger.info(f"Feature flag '{flag}' set to {value}")
    
    def get_all_tools(self) -> List:
        """Get all enabled tools"""
        return [
            meta['tool'] for meta in self.tools.values()
            if meta['enabled']
        ]
    
    def get_tool_info(self, name: str) -> Dict:
        """Get metadata about a tool"""
        if name not in self.tools:
            return {}
        return {
            k: v for k, v in self.tools[name].items()
            if k != 'tool'  # Don't return the tool object itself
        }


# Global registry instance
tool_registry = ToolRegistry()


def get_daily_capture_tools() -> List:
    """Get tools for daily capture workflow"""
    return tool_registry.get_tools_for_workflow("daily_capture")


def get_weekly_review_tools() -> List:
    """Get tools for weekly review workflow"""
    return tool_registry.get_tools_for_workflow("weekly_review")


def get_all_tools() -> List:
    """Get all available tools"""
    return tool_registry.get_all_tools()


# Export specific tool lists for convenience
TIMING_TOOLS = [
    analyze_timing_tool,
    review_uncategorized_tool,
    calculate_focus_alignment_tool
]

CAPTURE_TOOLS = [
    scan_inbox_tool,
    brain_dump_tool,
    capture_item_tool,
    detect_capture_patterns_tool
]

GTD_TOOLS = [
    clarify_items_tool,
    organize_tool,
    create_project_tool,
    prioritize_actions_tool
]

MEMORY_TOOLS = [
    save_memory_tool,
    load_context_tool,
    search_memory_tool,
    update_user_context_tool
]

ADAPTIVE_TOOLS = [
    detect_patterns_tool,
    adjust_behavior_tool,
    provide_intervention_tool,
    assess_user_state_tool
]

# Time management tools (NEW - Critical for ADHD)
TIME_TOOLS = [
    check_time_tool,
    transition_phase_tool,
    send_alert_tool,
    get_session_time_summary_tool,
    set_time_reminder_tool
]

# Interaction tools (NEW - Mixed-mode interaction)
INTERACTION_TOOLS = [
    structured_input_tool,
    quick_capture_tool,
    confirm_completion_tool,
    show_progress_tool,
    provide_encouragement_tool
]

# All tools for export
ALL_TOOLS = (TIME_TOOLS + INTERACTION_TOOLS + TIMING_TOOLS + 
            CAPTURE_TOOLS + GTD_TOOLS + MEMORY_TOOLS + ADAPTIVE_TOOLS)

# Conversation tools (V3 - Fixed single interrupt pattern)
CONVERSATION_TOOLS = [
    ask_question_v3,
    ask_yes_no_v3,
    startup_questions_v3,
    collect_mind_sweep_v3,
    collect_priorities_v3
]

# Data capture tools (V2 - Persistence)
DATA_CAPTURE_TOOLS = [
    save_mind_sweep_item_v2,
    save_weekly_priority_v2,
    save_project_update_v2,
    save_user_response_v2,
    batch_save_mind_sweep_v2,
    get_saved_priorities_v2
]

# Minimal essential tools for weekly review (to fit in 4096 token context)
ESSENTIAL_TOOLS = [
    # Core time management (2)
    check_time_tool,
    transition_phase_tool,
    # Core conversation (2) - V3: Fixed single interrupt
    ask_question_v3,
    ask_yes_no_v3,
    # Core data capture (4) - V2: Persistence
    save_user_response_v2,
    save_mind_sweep_item_v2,
    save_weekly_priority_v2,
    save_project_update_v2,
    # Core interaction (1)
    show_progress_tool,
    # Core memory (1)
    save_memory_tool,
]