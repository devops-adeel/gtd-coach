#!/usr/bin/env python3
"""
Human Interaction Tools for GTD Agent
Implements mixed-mode interaction: conversational with structured checkpoints
"""

import logging
from typing import Dict, List, Annotated, Optional, Any
from datetime import datetime

from langchain_core.tools import tool
from langgraph.prebuilt import InjectedState
from langgraph.types import interrupt

# Import state
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from gtd_coach.agent.state import AgentState

logger = logging.getLogger(__name__)


@tool
def structured_input_tool(
    prompt: str,
    input_type: str,
    options: Optional[List[str]] = None,
    required: bool = True,
    state: Annotated[AgentState, InjectedState] = None
) -> Dict:
    """
    Get structured input from user at critical checkpoints.
    Uses LangGraph's interrupt for human-in-the-loop.
    
    Args:
        prompt: Question or instruction for user
        input_type: Type of input expected (priority, confirmation, selection, text)
        options: Optional list of choices for selection
        required: Whether input is required (can't skip)
        state: Injected agent state
        
    Returns:
        Dictionary with user response
    """
    # Update state to show we're waiting
    state["awaiting_input"] = True
    state["interaction_mode"] = "structured"
    
    # Prepare interrupt context based on input type
    interrupt_context = {
        "prompt": prompt,
        "type": input_type,
        "required": required,
        "phase": state.get("current_phase", "UNKNOWN"),
        "time_remaining": _get_time_remaining(state)
    }
    
    if options:
        interrupt_context["options"] = options
    
    # Special handling for different input types
    if input_type == "priority":
        # Priority selection for weekly focus
        interrupt_context["suggestions"] = state.get("suggested_priorities", [])
        interrupt_context["instruction"] = "Select your TOP 3 priorities for this week"
        
    elif input_type == "confirmation":
        # Yes/no confirmation
        interrupt_context["options"] = ["yes", "no"]
        interrupt_context["default"] = "yes"
        
    elif input_type == "selection":
        # Multiple choice
        if not options:
            return {"error": "Selection type requires options list"}
        interrupt_context["allow_multiple"] = False
        
    elif input_type == "multi_selection":
        # Multiple selection
        if not options:
            return {"error": "Multi-selection type requires options list"}
        interrupt_context["allow_multiple"] = True
    
    # Use interrupt to pause and get input
    try:
        response = interrupt(interrupt_context)
        
        # Process response based on type
        if input_type == "priority":
            priorities = response.get("priorities", [])
            state["weekly_priorities"] = priorities[:3]  # Limit to top 3
            return {"priorities": priorities, "success": True}
            
        elif input_type == "confirmation":
            confirmed = response.get("confirmed", response.get("value", "").lower() == "yes")
            return {"confirmed": confirmed, "success": True}
            
        elif input_type in ["selection", "multi_selection"]:
            selected = response.get("selected", response.get("value", []))
            return {"selected": selected, "success": True}
            
        else:  # text input
            text = response.get("text", response.get("value", ""))
            return {"text": text, "success": True}
            
    except Exception as e:
        logger.error(f"Interrupt failed: {e}")
        # Fallback to basic input if interrupt fails
        return _fallback_input(prompt, input_type, options)
    
    finally:
        state["awaiting_input"] = False


@tool
def quick_capture_tool(
    prompt: str,
    allow_multiple: bool = True,
    state: Annotated[AgentState, InjectedState] = None
) -> List[str]:
    """
    Rapid capture mode for mind sweep - optimized for speed.
    Doesn't use interrupt to avoid overhead.
    
    Args:
        prompt: Initial prompt for capture
        allow_multiple: Whether to keep capturing until 'done'
        state: Injected agent state
        
    Returns:
        List of captured items
    """
    state["interaction_mode"] = "conversational"
    items = []
    
    print(f"\n{prompt}")
    
    if state.get("time_pressure_mode"):
        print("⏰ Quick capture mode - type fast, we're short on time!")
    
    if allow_multiple:
        print("Enter items one at a time. Type 'done' when finished.\n")
        
        while True:
            try:
                item = input("→ ").strip()
                
                if item.lower() in ['done', 'finished', 'stop', '']:
                    break
                    
                items.append(item)
                
                # Add to captures immediately
                if "captures" not in state:
                    state["captures"] = []
                    
                state["captures"].append({
                    "content": item,
                    "capture_time": datetime.now().isoformat(),
                    "source": "mind_sweep",
                    "clarified": False
                })
                
                # Quick acknowledgment
                print(f"✓ Captured ({len(items)} so far)")
                
            except KeyboardInterrupt:
                print("\n✓ Capture interrupted - saving what we have")
                break
                
    else:
        # Single item capture
        item = input("→ ").strip()
        if item:
            items.append(item)
            
    logger.info(f"Captured {len(items)} items in quick capture mode")
    return items


@tool
def confirm_completion_tool(
    phase: str,
    summary: str,
    state: Annotated[AgentState, InjectedState] = None
) -> bool:
    """
    Confirm phase completion with user before transitioning.
    
    Args:
        phase: Name of the phase to complete
        summary: Brief summary of what was accomplished
        state: Injected agent state
        
    Returns:
        Boolean indicating if user confirms completion
    """
    # Check if we're in time pressure mode
    if state.get("time_pressure_mode"):
        # Auto-confirm in urgent mode
        print(f"\n⏰ Auto-completing {phase} due to time pressure")
        print(f"Summary: {summary}")
        return True
    
    # Build confirmation prompt
    time_remaining = _get_time_remaining(state)
    
    prompt = f"""
Phase Complete: {phase}
{'-' * 40}
{summary}

Time remaining: {time_remaining} minutes

Ready to continue to next phase?"""
    
    # Use structured input for confirmation
    result = structured_input_tool.invoke({
        "prompt": prompt,
        "input_type": "confirmation",
        "required": True
    }, state)
    
    return result.get("confirmed", True)


@tool
def show_progress_tool(
    state: Annotated[AgentState, InjectedState]
) -> str:
    """
    Show current progress through the review.
    
    Args:
        state: Injected agent state
        
    Returns:
        Progress summary string
    """
    completed = state.get("completed_phases", [])
    current = state.get("current_phase", "UNKNOWN")
    
    all_phases = ["STARTUP", "MIND_SWEEP", "PROJECT_REVIEW", "PRIORITIZATION", "WRAP_UP"]
    
    progress_bar = []
    for phase in all_phases:
        if phase in completed:
            progress_bar.append(f"✅ {phase}")
        elif phase == current:
            progress_bar.append(f"🔄 {phase}")
        else:
            progress_bar.append(f"⬜ {phase}")
    
    # Calculate overall progress
    progress_pct = (len(completed) / len(all_phases)) * 100
    
    # Build summary
    summary = f"""
📊 Review Progress ({progress_pct:.0f}% complete)
{'=' * 50}
{' → '.join(progress_bar)}

Current: {current}
Completed: {len(completed)}/5 phases
Time elapsed: {state.get('total_elapsed', 0):.0f} minutes
"""
    
    # Add specific accomplishments
    if "captures" in state and len(state["captures"]) > 0:
        summary += f"📝 Captured: {len(state['captures'])} items\n"
    
    if "processed_items" in state and len(state["processed_items"]) > 0:
        summary += f"✅ Processed: {len(state['processed_items'])} actions\n"
        
    if "weekly_priorities" in state and state["weekly_priorities"]:
        summary += f"🎯 Priorities set: {len(state['weekly_priorities'])}\n"
    
    return summary


@tool
def provide_encouragement_tool(
    context: str,
    state: Annotated[AgentState, InjectedState] = None
) -> str:
    """
    Provide ADHD-friendly encouragement based on context.
    
    Args:
        context: Current situation (struggling, completed, timeout, etc)
        state: Injected agent state
        
    Returns:
        Encouraging message
    """
    mode = state.get("accountability_mode", "firm")
    
    encouragements = {
        "struggling": {
            "firm": "You've got this! One item at a time. What's the very next thing?",
            "gentle": "It's okay to feel overwhelmed. Let's take it slow. What feels manageable?"
        },
        "completed": {
            "firm": "Excellent work! You crushed that phase. Ready for the next challenge?",
            "gentle": "Beautiful job! You should feel proud. Let's keep this momentum going."
        },
        "timeout": {
            "firm": "Time's up but you did great! Moving on keeps us on track.",
            "gentle": "We're out of time for this phase, and that's perfectly fine! Progress, not perfection."
        },
        "halfway": {
            "firm": "Halfway there! You're doing great. Let's power through!",
            "gentle": "You're at the halfway point! Take a breath, you're doing wonderfully."
        },
        "final": {
            "firm": "Final push! You've done an amazing job. Let's bring it home!",
            "gentle": "Almost there! You've accomplished so much already."
        }
    }
    
    message = encouragements.get(context, {}).get(mode, "Keep going, you're doing great!")
    
    # Add emoji based on energy level
    energy = state.get("user_energy", "medium")
    if energy == "high":
        message = "🚀 " + message
    elif energy == "low":
        message = "💚 " + message
    else:
        message = "✨ " + message
    
    return message


def _get_time_remaining(state: Dict) -> float:
    """
    Helper to calculate time remaining in current phase.
    
    Args:
        state: Agent state
        
    Returns:
        Minutes remaining
    """
    if not state.get("phase_start_time"):
        return 0
    
    elapsed = (datetime.now() - state["phase_start_time"]).seconds / 60
    limit = state.get("phase_time_limit", 5)
    remaining = max(0, limit - elapsed)
    
    return round(remaining, 1)


def _fallback_input(prompt: str, input_type: str, options: Optional[List[str]]) -> Dict:
    """
    Fallback input method if interrupt fails.
    
    Args:
        prompt: User prompt
        input_type: Type of input
        options: Optional choices
        
    Returns:
        Response dictionary
    """
    print(f"\n{prompt}")
    
    if input_type == "confirmation":
        response = input("(yes/no): ").strip().lower()
        return {"confirmed": response in ["yes", "y"], "success": True}
        
    elif input_type == "selection" and options:
        print("Options:")
        for i, opt in enumerate(options, 1):
            print(f"  {i}. {opt}")
        try:
            idx = int(input("Select number: ")) - 1
            if 0 <= idx < len(options):
                return {"selected": options[idx], "success": True}
        except (ValueError, IndexError):
            pass
        return {"selected": options[0] if options else None, "success": False}
        
    else:
        response = input("→ ").strip()
        return {"text": response, "success": True}