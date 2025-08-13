#!/usr/bin/env python3
"""
Rich State Schema for GTD Agent
Defines the comprehensive state that flows through the hybrid workflow-agent system
"""

from typing import Annotated, Dict, List, Optional, Literal
from datetime import datetime
from typing_extensions import TypedDict
from pydantic import BaseModel, Field
from langgraph.graph.message import add_messages

# Import GTD entities from existing integrations
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from gtd_coach.integrations.gtd_entities import (
    MindsweepItem, GTDAction, GTDProject, Priority, Energy
)


class DailyCapture(MindsweepItem):
    """Extended mindsweep item for daily capture with rich metadata"""
    source: Literal["outlook", "physical", "beeper", "slack", "calendar", "timing", "voice"] = Field(
        ..., description="Where this item came from"
    )
    clarified: bool = Field(False, description="Has been through clarification")
    actionable: bool = Field(False, description="Is this actionable?")
    two_minute_rule: bool = Field(False, description="Can be done in 2 minutes?")
    project_id: Optional[str] = Field(None, description="Associated project UUID if applicable")
    context_required: Optional[str] = Field(None, description="GTD context needed")
    energy_level: Optional[Energy] = Field(None, description="Energy required")
    time_estimate: Optional[int] = Field(None, description="Estimated minutes")
    delegate_to: Optional[str] = Field(None, description="Person to delegate to")
    defer_until: Optional[str] = Field(None, description="When to revisit (ISO format)")
    ai_suggestions: Optional[List[str]] = Field(None, description="Coach's suggestions")


class AgentState(TypedDict):
    """
    Rich state schema for the GTD Agent.
    This state flows through the hybrid workflow-agent system.
    """
    # Core messaging (inherited from MessagesState pattern)
    messages: Annotated[list, add_messages]
    
    # Session management
    session_id: str
    workflow_type: Literal["daily_capture", "weekly_review", "ad_hoc", "quick_check"]
    started_at: str  # ISO format timestamp
    
    # User context (loaded from Graphiti at startup)
    user_context: Dict
    user_id: Optional[str]
    previous_session: Optional[Dict]
    recurring_patterns: Optional[List[str]]
    
    # ADHD & Adaptive behavior
    adhd_patterns: List[str]
    accountability_mode: Literal["gentle", "firm", "adaptive"]
    user_energy: Optional[Literal["low", "medium", "high"]]
    focus_level: Optional[Literal["scattered", "moderate", "focused"]]
    stress_indicators: List[str]
    
    # GTD data structures
    captures: List[Dict]  # Will be DailyCapture dicts
    processed_items: List[Dict]  # GTDAction dicts
    projects: List[Dict]  # GTDProject dicts
    weekly_priorities: Optional[List[str]]  # Top 3 priorities for the week
    
    # Timing integration data
    timing_data: Optional[Dict]
    focus_score: Optional[float]
    context_switches: Optional[List[Dict]]
    uncategorized_minutes: Optional[int]
    
    # Graphiti memory
    graphiti_episode_ids: List[str]
    memory_batch: List[Dict]  # Episodes to save
    
    # Workflow control
    current_phase: str
    completed_phases: List[str]
    available_tools: List[str]
    tool_history: List[Dict]  # Track which tools were called
    
    # Time management (CRITICAL for ADHD)
    phase_start_time: Optional[datetime]  # When current phase started
    phase_time_limit: int  # Minutes allocated for current phase
    total_elapsed: float  # Total session time in minutes
    time_warnings: List[str]  # Time warnings given
    last_time_check: Optional[datetime]  # Last time we checked time
    time_pressure_mode: bool  # True when running low on time
    
    # Interaction management
    interaction_mode: Literal["conversational", "structured", "urgent"]
    awaiting_input: bool  # True when waiting for user input
    input_timeout: Optional[int]  # Seconds to wait for input
    
    # Context window management (32K limit)
    context_usage: Dict[str, int]  # Tokens used per phase
    message_summary: str  # Compressed history between phases
    phase_summary: str  # Summary of completed phases
    phase_changed: bool  # Flag to trigger context reset
    context_overflow_count: int  # Number of times we hit limit
    
    # Error handling & resilience
    errors: List[Dict]
    retry_count: int
    last_checkpoint: Optional[str]  # For resumability
    
    # Metrics & evaluation
    phase_durations: Dict[str, float]
    tool_latencies: Dict[str, List[float]]
    llm_token_usage: Dict[str, int]
    
    # Feature flags & configuration
    skip_timing: bool
    voice_enabled: bool
    verbose_mode: bool
    test_mode: bool  # For testing with mocked APIs


class ToolInvocation(BaseModel):
    """Track tool invocations for debugging and metrics"""
    tool_name: str
    timestamp: datetime
    input_args: Dict
    output: Optional[Dict] = None
    error: Optional[str] = None
    latency_ms: Optional[float] = None
    token_usage: Optional[Dict] = None


class PhaseTransition(BaseModel):
    """Track phase transitions in the workflow"""
    from_phase: str
    to_phase: str
    timestamp: datetime
    reason: Optional[str] = None
    triggered_by: Literal["workflow", "agent", "user", "error"]


class StateValidator:
    """Validates state transitions and ensures consistency"""
    
    @staticmethod
    def validate_phase_transition(state: AgentState, next_phase: str) -> bool:
        """Validate that a phase transition is allowed"""
        # Define valid transitions
        valid_transitions = {
            "startup": ["timing_review", "inbox_scan", "capture"],
            "timing_review": ["inbox_scan", "capture"],
            "inbox_scan": ["capture", "clarify"],
            "capture": ["clarify", "organize"],
            "clarify": ["organize", "wrapup"],
            "organize": ["wrapup"],
            "wrapup": ["complete"]
        }
        
        current = state.get("current_phase", "startup")
        return next_phase in valid_transitions.get(current, [])
    
    @staticmethod
    def validate_state_consistency(state: AgentState) -> List[str]:
        """Check for state inconsistencies and return list of issues"""
        issues = []
        
        # Check session_id exists
        if not state.get("session_id"):
            issues.append("Missing session_id")
        
        # Check workflow_type is valid
        if state.get("workflow_type") not in ["daily_capture", "weekly_review", "ad_hoc", "quick_check"]:
            issues.append(f"Invalid workflow_type: {state.get('workflow_type')}")
        
        # Check accountability_mode is valid
        if state.get("accountability_mode") not in ["gentle", "firm", "adaptive"]:
            issues.append(f"Invalid accountability_mode: {state.get('accountability_mode')}")
        
        # Check that completed phases are in order
        expected_order = ["startup", "timing_review", "inbox_scan", "capture", "clarify", "organize", "wrapup"]
        completed = state.get("completed_phases", [])
        for i, phase in enumerate(completed):
            if phase not in expected_order:
                issues.append(f"Unknown phase in completed_phases: {phase}")
        
        return issues
    
    @staticmethod
    def ensure_required_fields(state: Dict) -> AgentState:
        """Ensure all required fields exist with defaults"""
        defaults = {
            "messages": [],
            "session_id": datetime.now().strftime("%Y%m%d_%H%M%S"),
            "workflow_type": "ad_hoc",
            "started_at": datetime.now().isoformat(),
            "user_context": {},
            "adhd_patterns": [],
            "accountability_mode": "adaptive",
            "captures": [],
            "processed_items": [],
            "projects": [],
            "graphiti_episode_ids": [],
            "memory_batch": [],
            "current_phase": "startup",
            "completed_phases": [],
            "available_tools": [],
            "tool_history": [],
            "errors": [],
            "retry_count": 0,
            "phase_durations": {},
            "tool_latencies": {},
            "llm_token_usage": {"prompt": 0, "completion": 0, "total": 0},
            "skip_timing": False,
            "voice_enabled": False,
            "verbose_mode": False,
            "test_mode": False
        }
        
        # Merge defaults with provided state
        for key, default_value in defaults.items():
            if key not in state:
                state[key] = default_value
        
        return state