#!/usr/bin/env python3
"""
Time Management Tools for GTD Agent
Critical for ADHD users - maintains strict time boundaries
"""

import logging
import subprocess
from typing import Dict, Annotated, Optional
from datetime import datetime
from pathlib import Path

from langchain_core.tools import tool
from langgraph.prebuilt import InjectedState

# Import state
import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from gtd_coach.agent.state import AgentState

logger = logging.getLogger(__name__)


@tool
def check_time_tool(
    state: Annotated[AgentState, InjectedState]
) -> str:
    """
    Check remaining time in current phase and overall session.
    Returns time status with appropriate urgency level.
    
    Args:
        state: Injected agent state
        
    Returns:
        Time status message with urgency indicators
    """
    if not state.get("phase_start_time"):
        return "⚠️ Time tracking not started. Please initialize phase."
    
    current_phase = state.get("current_phase", "UNKNOWN")
    phase_limit = state.get("phase_time_limit", 5)
    
    # Calculate elapsed and remaining
    elapsed = (datetime.now() - state["phase_start_time"]).seconds / 60
    remaining = phase_limit - elapsed
    
    # Update state
    state["total_elapsed"] = state.get("total_elapsed", 0) + elapsed
    state["last_time_check"] = datetime.now()
    
    # Determine urgency and response
    if remaining <= 0:
        state["time_pressure_mode"] = True
        state["interaction_mode"] = "urgent"
        message = f"🚨 TIME'S UP for {current_phase}! Must transition immediately!"
        
    elif remaining < 1:
        state["time_pressure_mode"] = True
        state["interaction_mode"] = "urgent"
        message = f"⚠️ FINAL MINUTE in {current_phase}! Wrap up NOW!"
        
    elif remaining < 2:
        state["time_pressure_mode"] = True
        message = f"⏰ {remaining:.1f} minutes left in {current_phase}. Speed up!"
        
    elif remaining < phase_limit * 0.2:  # Less than 20% time left
        message = f"⏱️ {remaining:.1f} minutes remaining. Time to wrap up {current_phase}."
        
    elif remaining < phase_limit * 0.5:  # Less than 50% time left
        message = f"⌚ {remaining:.0f} minutes left in {current_phase}. Halfway through!"
        
    else:
        state["time_pressure_mode"] = False
        message = f"✓ {remaining:.0f} minutes remaining in {current_phase}. Good pace!"
    
    # Add warning to history if needed
    if remaining < 2 and message not in state.get("time_warnings", []):
        state["time_warnings"] = state.get("time_warnings", []) + [message]
    
    # Log for debugging
    logger.info(f"Time check - Phase: {current_phase}, Remaining: {remaining:.1f}m")
    
    return message


@tool
def transition_phase_tool(
    next_phase: str,
    state: Annotated[AgentState, InjectedState]
) -> Dict:
    """
    Transition to the next phase with time reset and context management.
    
    Args:
        next_phase: Name of the phase to transition to
        state: Injected agent state
        
    Returns:
        Dictionary with transition status and new phase details
    """
    # Valid phases and their time limits
    PHASE_LIMITS = {
        'STARTUP': 2,
        'MIND_SWEEP': 10,
        'PROJECT_REVIEW': 12,
        'PRIORITIZATION': 5,
        'WRAP_UP': 3
    }
    
    if next_phase not in PHASE_LIMITS:
        return {
            "success": False,
            "error": f"Invalid phase: {next_phase}. Valid phases: {list(PHASE_LIMITS.keys())}"
        }
    
    # Save duration of current phase
    if state.get("phase_start_time"):
        current_phase = state.get("current_phase", "UNKNOWN")
        duration = (datetime.now() - state["phase_start_time"]).seconds / 60
        
        if "phase_durations" not in state:
            state["phase_durations"] = {}
        state["phase_durations"][current_phase] = duration
        
        # Mark current phase as completed
        if current_phase not in state.get("completed_phases", []):
            state["completed_phases"] = state.get("completed_phases", []) + [current_phase]
    
    # Update state for new phase
    state["current_phase"] = next_phase
    state["phase_start_time"] = datetime.now()
    state["phase_time_limit"] = PHASE_LIMITS[next_phase]
    state["phase_changed"] = True  # Trigger context reset in pre-model hook
    state["time_pressure_mode"] = False
    state["time_warnings"] = []  # Reset warnings for new phase
    state["interaction_mode"] = "conversational"  # Reset to normal mode
    
    # Log transition
    logger.info(f"Phase transition: {state.get('current_phase', 'UNKNOWN')} -> {next_phase} "
               f"({PHASE_LIMITS[next_phase]} minutes)")
    
    # Play transition sound if available
    try:
        send_alert_tool.invoke({"alert_type": "phase_change"}, state)
    except Exception as e:
        logger.debug(f"Could not play transition sound: {e}")
    
    return {
        "success": True,
        "new_phase": next_phase,
        "time_limit": PHASE_LIMITS[next_phase],
        "message": f"Transitioned to {next_phase} ({PHASE_LIMITS[next_phase]} minutes)"
    }


@tool
def send_alert_tool(
    alert_type: str,
    custom_message: Optional[str] = None,
    state: Annotated[AgentState, InjectedState] = None
) -> str:
    """
    Send audio or visual alert to user (critical for ADHD time awareness).
    
    Args:
        alert_type: Type of alert (warning, urgent, phase_change, completion)
        custom_message: Optional custom message to display
        state: Injected agent state
        
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
def get_session_time_summary_tool(
    state: Annotated[AgentState, InjectedState]
) -> Dict:
    """
    Get comprehensive time summary for the session.
    
    Args:
        state: Injected agent state
        
    Returns:
        Dictionary with time metrics and analysis
    """
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
def set_time_reminder_tool(
    minutes_from_now: int,
    reminder_message: str,
    state: Annotated[AgentState, InjectedState]
) -> str:
    """
    Set a time-based reminder within the current phase.
    
    Args:
        minutes_from_now: Minutes until reminder triggers
        reminder_message: Message to show when reminder triggers
        state: Injected agent state
        
    Returns:
        Confirmation message
    """
    # This is a simplified version - in production, you'd use asyncio tasks
    # or a proper scheduler to trigger reminders
    
    reminder_time = datetime.now().timestamp() + (minutes_from_now * 60)
    
    # Store reminder in state (would be checked by agent loop)
    if "pending_reminders" not in state:
        state["pending_reminders"] = []
    
    state["pending_reminders"].append({
        "trigger_time": reminder_time,
        "message": reminder_message,
        "created_at": datetime.now().isoformat()
    })
    
    return f"Reminder set for {minutes_from_now} minutes: {reminder_message}"