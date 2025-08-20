#!/usr/bin/env python3
"""
Time Management Tools for GTD Agent (Version 2)
Refactored to work without InjectedState pattern.
Critical for ADHD users - maintains strict time boundaries.
"""

import logging
import subprocess
from typing import Dict, Optional
from datetime import datetime
from pathlib import Path

from langchain_core.tools import tool

logger = logging.getLogger(__name__)

# Global state manager (singleton pattern)
class StateManager:
    """Manages agent state globally for tools."""
    _instance = None
    _state = {}
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def get_state(self) -> Dict:
        """Get current state."""
        return self._state
    
    def set_state(self, state: Dict):
        """Update state."""
        self._state.update(state)
    
    def get(self, key: str, default=None):
        """Get state value."""
        return self._state.get(key, default)
    
    def set(self, key: str, value):
        """Set state value."""
        self._state[key] = value

# Global state manager instance
state_manager = StateManager()


@tool
def check_time_v2() -> str:
    """
    Check remaining time in current phase and overall session.
    Returns time status with appropriate urgency level.
    """
    state = state_manager.get_state()
    
    if not state.get("phase_start_time"):
        return "⚠️ Time tracking not started. Please initialize phase."
    
    current_phase = state.get("current_phase", "UNKNOWN")
    phase_limit = state.get("phase_time_limit", 5)
    
    # Calculate elapsed and remaining
    elapsed = (datetime.now() - state["phase_start_time"]).seconds / 60
    remaining = phase_limit - elapsed
    
    # Update state
    state_manager.set("total_elapsed", state.get("total_elapsed", 0) + elapsed)
    state_manager.set("last_time_check", datetime.now())
    
    # Determine urgency and response
    if remaining <= 0:
        state_manager.set("time_pressure_mode", True)
        state_manager.set("interaction_mode", "urgent")
        message = f"🚨 TIME'S UP for {current_phase}! Must transition immediately!"
        
    elif remaining < 1:
        state_manager.set("time_pressure_mode", True)
        state_manager.set("interaction_mode", "urgent")
        message = f"⚠️ FINAL MINUTE in {current_phase}! Wrap up NOW!"
        
    elif remaining < 2:
        state_manager.set("time_pressure_mode", True)
        message = f"⏰ {remaining:.1f} minutes left in {current_phase}. Speed up!"
        
    elif remaining < phase_limit * 0.2:  # Less than 20% time left
        message = f"⏱️ {remaining:.1f} minutes remaining. Time to wrap up {current_phase}."
        
    elif remaining < phase_limit * 0.5:  # Less than 50% time left
        message = f"⌚ {remaining:.0f} minutes left in {current_phase}. Halfway through!"
        
    else:
        state_manager.set("time_pressure_mode", False)
        message = f"✓ {remaining:.0f} minutes remaining in {current_phase}. Good pace!"
    
    # Add warning to history if needed
    time_warnings = state.get("time_warnings", [])
    if remaining < 2 and message not in time_warnings:
        time_warnings.append(message)
        state_manager.set("time_warnings", time_warnings)
    
    logger.info(f"Time check - Phase: {current_phase}, Remaining: {remaining:.1f}m")
    
    return message


@tool
def transition_phase_v2(next_phase: str) -> Dict:
    """
    Transition to the next phase of the GTD weekly review process.
    
    IMPORTANT: 'WEEKLY_REVIEW' is NOT a valid phase - it's the overall process name.
    The weekly review PROCESS consists of these 5 PHASES in order:
    1. STARTUP - Check in with user, assess readiness
    2. MIND_SWEEP - Capture everything on mind
    3. PROJECT_REVIEW - Review projects and next actions
    4. PRIORITIZATION - Set top 3 priorities for the week
    5. WRAP_UP - Save progress and celebrate
    
    Args:
        next_phase: Must be one of: STARTUP, MIND_SWEEP, PROJECT_REVIEW, PRIORITIZATION, or WRAP_UP
        
    Returns:
        Dictionary with transition status and new phase details
        
    Example:
        transition_phase_v2("MIND_SWEEP")  # Correct - transitions to mind sweep phase
        transition_phase_v2("WEEKLY_REVIEW")  # WRONG - this will error
    """
    state = state_manager.get_state()
    
    # Log the exact parameter received for debugging
    logger.info(f"transition_phase_v2 called with: '{next_phase}'")
    
    # Valid phases and their time limits
    PHASE_LIMITS = {
        'STARTUP': 2,
        'MIND_SWEEP': 10,
        'PROJECT_REVIEW': 12,
        'PRIORITIZATION': 5,
        'WRAP_UP': 3
    }
    
    # Check for common mistakes
    if next_phase == "WEEKLY_REVIEW":
        logger.error(f"Agent attempted to transition to 'WEEKLY_REVIEW' - this is the process name, not a phase")
        return {
            "success": False,
            "error": f"'WEEKLY_REVIEW' is not a valid phase - it's the name of the overall process. "
                    f"Please choose one of the 5 phases: {list(PHASE_LIMITS.keys())}. "
                    f"You are currently in {state.get('current_phase', 'STARTUP')} phase."
        }
    
    if next_phase not in PHASE_LIMITS:
        logger.error(f"Invalid phase requested: '{next_phase}'")
        return {
            "success": False,
            "error": f"Invalid phase: '{next_phase}'. Valid phases are: {list(PHASE_LIMITS.keys())}"
        }
    
    # Save duration of current phase
    if state.get("phase_start_time"):
        current_phase = state.get("current_phase", "UNKNOWN")
        duration = (datetime.now() - state["phase_start_time"]).seconds / 60
        
        phase_durations = state.get("phase_durations", {})
        phase_durations[current_phase] = duration
        state_manager.set("phase_durations", phase_durations)
        
        # Mark current phase as completed
        completed_phases = state.get("completed_phases", [])
        if current_phase not in completed_phases:
            completed_phases.append(current_phase)
            state_manager.set("completed_phases", completed_phases)
    
    # Update state for new phase
    state_manager.set("current_phase", next_phase)
    state_manager.set("phase_start_time", datetime.now())
    state_manager.set("phase_time_limit", PHASE_LIMITS[next_phase])
    state_manager.set("phase_changed", True)
    state_manager.set("time_pressure_mode", False)
    state_manager.set("time_warnings", [])
    state_manager.set("interaction_mode", "conversational")
    
    logger.info(f"Phase transition: {state.get('current_phase', 'UNKNOWN')} -> {next_phase} "
               f"({PHASE_LIMITS[next_phase]} minutes)")
    
    # Play transition sound if available
    try:
        send_alert_v2("phase_change")
    except Exception as e:
        logger.debug(f"Could not play transition sound: {e}")
    
    # Provide phase-specific guidance for agent's next action
    phase_actions = {
        'STARTUP': "Now use check_in_with_user_v2 to ask about energy level and readiness.",
        'MIND_SWEEP': "Now use wait_for_user_input_v2 to ask what's been on their mind.",
        'PROJECT_REVIEW': "Now use wait_for_user_input_v2 to review current projects.",
        'PRIORITIZATION': "Now use check_in_with_user_v2 to identify top 3 priorities.",
        'WRAP_UP': "Now use confirm_with_user_v2 to confirm session completion and save."
    }
    
    # Add flag to signal agent should continue conversation
    requires_user_input = next_phase in ['STARTUP', 'MIND_SWEEP', 'PROJECT_REVIEW', 'PRIORITIZATION']
    if requires_user_input:
        state_manager.set("awaiting_user_input", True)
        state_manager.set("next_questions", phase_actions.get(next_phase))
    
    return {
        "success": True,
        "new_phase": next_phase,
        "time_limit": PHASE_LIMITS[next_phase],
        "message": f"Transitioned to {next_phase} ({PHASE_LIMITS[next_phase]} minutes). {phase_actions.get(next_phase, 'Continue with this phase.')}",
        "requires_user_input": requires_user_input,
        "conversation_tool_hint": phase_actions.get(next_phase, "")
    }


@tool
def send_alert_v2(
    alert_type: str,
    custom_message: Optional[str] = None
) -> str:
    """
    Send audio or visual alert to user (critical for ADHD time awareness).
    
    Args:
        alert_type: Type of alert (warning, urgent, phase_change, completion)
        custom_message: Optional custom message to display
        
    Returns:
        Status message
    """
    # Define alert sounds (macOS specific)
    ALERT_SOUNDS = {
        "warning": "Ping",  # 50% time warning
        "urgent": "Sosumi",  # 20% time warning  
        "critical": "Basso",  # Time's up
        "phase_change": "Pop",  # Phase transition
        "completion": "Glass",  # Session complete
    }
    
    sound = ALERT_SOUNDS.get(alert_type, "Tink")
    
    # Try to play sound on macOS
    try:
        subprocess.run(
            ["afplay", f"/System/Library/Sounds/{sound}.aiff"],
            timeout=2,
            capture_output=True
        )
        logger.debug(f"Played alert sound: {sound}")
        
    except (subprocess.TimeoutExpired, subprocess.CalledProcessError, FileNotFoundError) as e:
        # Fallback to terminal bell if afplay not available
        print("\a", end="", flush=True)  # Terminal bell
        logger.debug(f"Fallback to terminal bell (afplay failed: {e})")
    
    # Display message if provided
    if custom_message:
        print(f"\n{'='*50}")
        print(f"🔔 ALERT: {custom_message}")
        print(f"{'='*50}\n")
    
    return f"Alert sent: {alert_type}"


@tool
def get_session_summary_v2() -> Dict:
    """
    Get comprehensive time summary for the session.
    
    Returns:
        Dictionary with time metrics and analysis
    """
    state = state_manager.get_state()
    
    # Calculate total elapsed time
    total_elapsed = state.get("total_elapsed", 0)
    
    # Get phase durations
    phase_durations = state.get("phase_durations", {})
    
    # Calculate time efficiency
    planned_total = sum([2, 10, 12, 5, 3])  # 32 minutes planned
    actual_total = sum(phase_durations.values())
    efficiency = (planned_total / actual_total * 100) if actual_total > 0 else 0
    
    # Identify phases that went over time
    over_time_phases = []
    PHASE_LIMITS = {'STARTUP': 2, 'MIND_SWEEP': 10, 'PROJECT_REVIEW': 12, 
                    'PRIORITIZATION': 5, 'WRAP_UP': 3}
    
    for phase, duration in phase_durations.items():
        if phase in PHASE_LIMITS and duration > PHASE_LIMITS[phase]:
            over_time_phases.append({
                "phase": phase,
                "planned": PHASE_LIMITS[phase],
                "actual": round(duration, 1),
                "overtime": round(duration - PHASE_LIMITS[phase], 1)
            })
    
    # Count time pressure incidents
    time_warnings_count = len(state.get("time_warnings", []))
    
    return {
        "total_elapsed_minutes": round(total_elapsed, 1),
        "phase_durations": {k: round(v, 1) for k, v in phase_durations.items()},
        "completed_phases": state.get("completed_phases", []),
        "time_efficiency_percent": round(efficiency, 1),
        "over_time_phases": over_time_phases,
        "time_warnings_given": time_warnings_count,
        "current_phase": state.get("current_phase", "UNKNOWN"),
        "session_complete": len(state.get("completed_phases", [])) == 5
    }


@tool  
def set_reminder_v2(
    minutes_from_now: int,
    reminder_message: str
) -> str:
    """
    Set a time-based reminder within the current phase.
    
    Args:
        minutes_from_now: Minutes until reminder triggers
        reminder_message: Message to show when reminder triggers
        
    Returns:
        Confirmation message
    """
    state = state_manager.get_state()
    
    reminder_time = datetime.now().timestamp() + (minutes_from_now * 60)
    
    # Store reminder in state
    pending_reminders = state.get("pending_reminders", [])
    pending_reminders.append({
        "trigger_time": reminder_time,
        "message": reminder_message,
        "created_at": datetime.now().isoformat()
    })
    state_manager.set("pending_reminders", pending_reminders)
    
    return f"Reminder set for {minutes_from_now} minutes: {reminder_message}"


def initialize_state_manager(initial_state: Dict):
    """
    Initialize the state manager with initial state.
    Should be called when starting the agent.
    
    Args:
        initial_state: Initial state dictionary
    """
    state_manager.set_state(initial_state)
    logger.info("State manager initialized for time tools")