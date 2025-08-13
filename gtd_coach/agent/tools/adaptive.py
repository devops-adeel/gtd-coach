#!/usr/bin/env python3
"""
Adaptive Behavior Tools for GTD Agent
Tools for detecting patterns and adjusting coaching style
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
from gtd_coach.agent.state import AgentState

logger = logging.getLogger(__name__)


@tool
def detect_patterns_tool(
    state: Annotated[AgentState, InjectedState] = None
) -> Dict:
    """
    Detects ADHD patterns from current session behavior.
    
    Args:
        state: Injected agent state
    
    Returns:
        Dictionary with detected patterns and severity
    """
    if not state:
        return {
            "patterns": [],
            "severity": "unknown",
            "message": "No state available for pattern detection"
        }
    
    patterns = {}
    
    # Analyze captures for patterns
    if 'captures' in state:
        capture_patterns = _analyze_capture_patterns(state['captures'])
        patterns.update(capture_patterns)
    
    # Analyze timing data for focus patterns
    if state.get('focus_score') is not None:
        focus_patterns = _analyze_focus_patterns(
            state['focus_score'],
            state.get('context_switches', [])
        )
        patterns.update(focus_patterns)
    
    # Analyze tool usage patterns
    if 'tool_history' in state:
        tool_patterns = _analyze_tool_patterns(state['tool_history'])
        patterns.update(tool_patterns)
    
    # Analyze phase durations
    if 'phase_durations' in state:
        duration_patterns = _analyze_duration_patterns(state['phase_durations'])
        patterns.update(duration_patterns)
    
    # Calculate overall severity
    severity = _calculate_overall_severity(patterns)
    
    # Return patterns for state update
    new_patterns = [p for p in patterns.keys() 
                    if p not in state.get('adhd_patterns', [])] if state else list(patterns.keys())
    
    return {
        "patterns": patterns,
        "severity": severity,
        "pattern_count": len(patterns),
        "new_patterns": new_patterns,
        "pattern_details": patterns,
        "recommendations": _generate_pattern_recommendations(patterns, severity),
        "intervention_needed": severity in ['high', 'critical']
    }


@tool
def adjust_behavior_tool(
    reason: Optional[str] = None,
    state: Annotated[AgentState, InjectedState] = None
) -> Dict:
    """
    Adjusts coaching behavior based on detected patterns and user state.
    
    Args:
        reason: Optional specific reason for adjustment
        state: Injected agent state
    
    Returns:
        Dictionary with behavior adjustments
    """
    if not state:
        return {
            "adjusted": False,
            "message": "No state available for behavior adjustment"
        }
    
    current_mode = state.get('accountability_mode', 'adaptive')
    previous_mode = current_mode
    adjustments = []
    
    # Check patterns
    patterns = state.get('adhd_patterns', [])
    severity = state.get('pattern_analysis', {}).get('severity', 'medium')
    
    # Adjust based on severity
    if severity == 'critical':
        new_mode = 'firm'
        adjustments.append("Switching to firm mode due to critical patterns")
        adjustments.append("Implementing structure and clear boundaries")
    elif severity == 'high':
        if 'overwhelm' in patterns:
            new_mode = 'gentle'
            adjustments.append("Switching to gentle mode due to overwhelm")
            adjustments.append("Breaking tasks into smaller pieces")
        else:
            new_mode = 'firm'
            adjustments.append("Increasing structure to manage symptoms")
    elif severity == 'low':
        new_mode = 'gentle'
        adjustments.append("Light touch needed - patterns well managed")
    else:
        # Adaptive based on specific patterns
        if 'rapid_switching' in patterns:
            adjustments.append("Adding focus checkpoints")
        if 'procrastination' in patterns:
            adjustments.append("Emphasizing quick wins")
        if 'perfectionism' in patterns:
            adjustments.append("Encouraging 'good enough' approach")
        new_mode = 'adaptive'
    
    # Apply reason-based adjustments
    if reason:
        if 'timeout' in reason.lower():
            adjustments.append("Extending time limits")
        if 'confused' in reason.lower():
            adjustments.append("Providing clearer instructions")
        if 'overwhelmed' in reason.lower():
            new_mode = 'gentle'
            adjustments.append("Simplifying approach")
    
    # Create adjustment record for state update
    adjustment_record = {
        'timestamp': datetime.now().isoformat(),
        'from_mode': previous_mode,
        'to_mode': new_mode,
        'reason': reason or f"Pattern severity: {severity}",
        'adjustments': adjustments
    }
    
    return {
        "adjusted": new_mode != previous_mode,
        "previous_mode": previous_mode,
        "new_mode": new_mode,
        "adjustments": adjustments,
        "adjustment_record": adjustment_record,
        "message": _generate_adjustment_message(new_mode, adjustments)
    }


@tool
def provide_intervention_tool(
    intervention_type: str,
    state: Annotated[AgentState, InjectedState] = None
) -> Dict:
    """
    Provides real-time intervention for detected patterns.
    
    Args:
        intervention_type: Type of intervention needed
        state: Injected agent state
    
    Returns:
        Dictionary with intervention details
    """
    interventions = {
        'rapid_switching': {
            'message': "I notice you're jumping between topics. Let's pause and focus on one thing.",
            'action': "Pick your TOP priority right now. Just one.",
            'technique': 'grounding'
        },
        'overwhelm': {
            'message': "Feeling overwhelmed is okay. Let's make this manageable.",
            'action': "Take 3 deep breaths. Then we'll tackle just ONE small thing.",
            'technique': 'breathing'
        },
        'procrastination': {
            'message': "Starting is the hardest part. Let's find the tiniest first step.",
            'action': "What's the absolute smallest action you could take? Even 2 minutes counts.",
            'technique': 'micro_commitment'
        },
        'hyperfocus_risk': {
            'message': "Great focus! Remember to pace yourself.",
            'action': "Set a timer for 25 minutes, then take a short break.",
            'technique': 'pomodoro'
        },
        'perfectionism': {
            'message': "Progress over perfection. Good enough is good enough.",
            'action': "What would 'done' look like if it just needed to work?",
            'technique': 'satisficing'
        },
        'distraction': {
            'message': "Let's gently refocus.",
            'action': "Note the distraction, then return to your current task.",
            'technique': 'noting'
        }
    }
    
    intervention = interventions.get(intervention_type, {
        'message': "Let's take a moment to regroup.",
        'action': "What do you need right now to move forward?",
        'technique': 'check_in'
    })
    
    # Create intervention record for state update
    intervention_record = {
        'timestamp': datetime.now().isoformat(),
        'type': intervention_type,
        'technique': intervention['technique']
    }
    
    return {
        "intervention_type": intervention_type,
        "message": intervention['message'],
        "action": intervention['action'],
        "technique": intervention['technique'],
        "intervention_record": intervention_record,
        "follow_up": _suggest_follow_up(intervention_type)
    }


@tool
def assess_user_state_tool(
    state: Annotated[AgentState, InjectedState] = None
) -> Dict:
    """
    Assesses current user state based on session data.
    
    Args:
        state: Injected agent state
    
    Returns:
        Dictionary with user state assessment
    """
    if not state:
        return {
            "energy": "unknown",
            "focus": "unknown",
            "stress": "unknown",
            "recommendations": []
        }
    
    # Assess energy
    energy = _assess_energy(state)
    
    # Assess focus
    focus = _assess_focus(state)
    
    # Assess stress
    stress = _assess_stress(state)
    
    # Create state assessment for update
    state_assessment = {
        'user_energy': energy,
        'focus_level': focus,
        'stress_level': stress,
        'timestamp': datetime.now().isoformat()
    }
    
    # Generate recommendations
    recommendations = _generate_state_recommendations(energy, focus, stress)
    
    return {
        "energy": energy,
        "focus": focus, 
        "stress": stress,
        "recommendations": recommendations,
        "optimal_tasks": _suggest_optimal_tasks(energy, focus),
        "session_adjustments": _suggest_session_adjustments(energy, focus, stress),
        "state_assessment": state_assessment
    }


def _analyze_capture_patterns(captures: List[Dict]) -> Dict:
    """Analyze patterns in captured items"""
    patterns = {}
    
    if not captures:
        return patterns
    
    # Count topic switches
    topics = []
    for capture in captures:
        content = capture.get('content', '').lower()
        if 'work' in content or 'project' in content:
            topics.append('work')
        elif 'home' in content or 'personal' in content:
            topics.append('personal')
        else:
            topics.append('other')
    
    switches = sum(1 for i in range(1, len(topics)) if topics[i] != topics[i-1])
    
    if len(captures) > 5:
        switch_rate = switches / len(captures)
        if switch_rate > 0.6:
            patterns['rapid_switching'] = {
                'severity': 'high',
                'evidence': f"{switches} topic changes in {len(captures)} items"
            }
    
    # Check for overwhelm language
    overwhelm_count = sum(
        1 for c in captures
        if any(word in c.get('content', '').lower() 
               for word in ['everything', 'so much', 'overwhelming', 'cant'])
    )
    
    if overwhelm_count >= 3:
        patterns['overwhelm'] = {
            'severity': 'high',
            'evidence': f"{overwhelm_count} overwhelm indicators"
        }
    
    return patterns


def _analyze_focus_patterns(focus_score: float, context_switches: List) -> Dict:
    """Analyze focus-related patterns"""
    patterns = {}
    
    if focus_score < 30:
        patterns['poor_focus'] = {
            'severity': 'high',
            'evidence': f"Focus score: {focus_score}/100"
        }
    elif focus_score > 85:
        patterns['hyperfocus_risk'] = {
            'severity': 'medium',
            'evidence': f"Very high focus: {focus_score}/100"
        }
    
    if len(context_switches) > 20:
        patterns['excessive_switching'] = {
            'severity': 'high',
            'evidence': f"{len(context_switches)} context switches"
        }
    
    return patterns


def _analyze_tool_patterns(tool_history: List[Dict]) -> Dict:
    """Analyze tool usage patterns"""
    patterns = {}
    
    if not tool_history:
        return patterns
    
    # Check for repeated tool calls
    tool_counts = {}
    for entry in tool_history:
        tool = entry.get('tool', 'unknown')
        tool_counts[tool] = tool_counts.get(tool, 0) + 1
    
    # Check for stuck patterns
    for tool, count in tool_counts.items():
        if count > 5:
            patterns['repetitive_behavior'] = {
                'severity': 'medium',
                'evidence': f"{tool} called {count} times"
            }
    
    return patterns


def _analyze_duration_patterns(phase_durations: Dict) -> Dict:
    """Analyze phase duration patterns"""
    patterns = {}
    
    # Check for rushed phases
    for phase, duration in phase_durations.items():
        expected = {
            'timing_review': 120,  # 2 minutes
            'capture': 300,  # 5 minutes
            'clarify': 300,  # 5 minutes
        }.get(phase, 180)  # 3 minute default
        
        if duration < expected * 0.5:
            patterns['rushing'] = {
                'severity': 'medium',
                'evidence': f"{phase} completed in {duration}s (expected {expected}s)"
            }
        elif duration > expected * 2:
            patterns['stuck'] = {
                'severity': 'medium',
                'evidence': f"{phase} took {duration}s (expected {expected}s)"
            }
    
    return patterns


def _calculate_overall_severity(patterns: Dict) -> str:
    """Calculate overall severity from patterns"""
    if not patterns:
        return 'low'
    
    high_count = sum(1 for p in patterns.values() if p['severity'] == 'high')
    medium_count = sum(1 for p in patterns.values() if p['severity'] == 'medium')
    
    if high_count >= 3:
        return 'critical'
    elif high_count >= 2:
        return 'high'
    elif high_count >= 1 or medium_count >= 2:
        return 'medium'
    else:
        return 'low'


def _generate_pattern_recommendations(patterns: Dict, severity: str) -> List[str]:
    """Generate recommendations based on patterns"""
    recommendations = []
    
    if severity == 'critical':
        recommendations.append("⚠️ Multiple concerning patterns - consider shorter session")
    
    if 'rapid_switching' in patterns:
        recommendations.append("Try grouping similar items before processing")
    
    if 'overwhelm' in patterns:
        recommendations.append("Focus on just top 3 priorities today")
    
    if 'poor_focus' in patterns:
        recommendations.append("Consider a break or different time of day")
    
    if 'hyperfocus_risk' in patterns:
        recommendations.append("Set timers to maintain balance")
    
    return recommendations[:3]


def _generate_adjustment_message(mode: str, adjustments: List[str]) -> str:
    """Generate user-friendly adjustment message"""
    if mode == 'firm':
        return "Switching to structured mode to help you focus. " + (adjustments[0] if adjustments else "")
    elif mode == 'gentle':
        return "Taking a softer approach. " + (adjustments[0] if adjustments else "")
    else:
        return "Adapting to your needs. " + (adjustments[0] if adjustments else "")


def _suggest_follow_up(intervention_type: str) -> str:
    """Suggest follow-up for intervention"""
    follow_ups = {
        'rapid_switching': "After focusing, we'll review if other items still matter",
        'overwhelm': "We'll break everything into tiny, manageable pieces",
        'procrastination': "Once started, momentum will help carry you forward",
        'hyperfocus_risk': "I'll remind you to take breaks",
        'perfectionism': "Remember: done is better than perfect",
        'distraction': "It's okay - refocusing is a skill that improves with practice"
    }
    
    return follow_ups.get(intervention_type, "Let's check in again in a few minutes")


def _assess_energy(state: Dict) -> str:
    """Assess user energy level"""
    # Check time of day
    hour = datetime.now().hour
    
    # Check capture volume
    capture_count = len(state.get('captures', []))
    
    # Check response patterns
    if capture_count < 5 and hour > 14:
        return 'low'
    elif capture_count > 20:
        return 'high'
    else:
        return 'medium'


def _assess_focus(state: Dict) -> str:
    """Assess user focus level"""
    focus_score = state.get('focus_score')
    
    if focus_score is not None:
        if focus_score < 40:
            return 'scattered'
        elif focus_score > 70:
            return 'focused'
    
    # Check pattern indicators
    if 'rapid_switching' in state.get('adhd_patterns', []):
        return 'scattered'
    
    return 'moderate'


def _assess_stress(state: Dict) -> str:
    """Assess user stress level"""
    patterns = state.get('adhd_patterns', [])
    
    stress_indicators = ['overwhelm', 'rushing', 'excessive_switching']
    stress_count = sum(1 for p in patterns if p in stress_indicators)
    
    if stress_count >= 2:
        return 'high'
    elif stress_count == 1:
        return 'medium'
    else:
        return 'low'


def _generate_state_recommendations(energy: str, focus: str, stress: str) -> List[str]:
    """Generate recommendations based on user state"""
    recommendations = []
    
    if energy == 'low':
        recommendations.append("Consider quick wins and low-energy tasks")
    elif energy == 'high':
        recommendations.append("Good time for challenging tasks")
    
    if focus == 'scattered':
        recommendations.append("Try single-tasking with breaks")
    elif focus == 'focused':
        recommendations.append("Leverage this focus for deep work")
    
    if stress == 'high':
        recommendations.append("Prioritize calming and structure")
    
    return recommendations


def _suggest_optimal_tasks(energy: str, focus: str) -> List[str]:
    """Suggest optimal tasks for current state"""
    if energy == 'high' and focus == 'focused':
        return ['complex problem-solving', 'creative work', 'planning']
    elif energy == 'low' and focus == 'scattered':
        return ['email triage', 'simple filing', 'routine tasks']
    elif energy == 'high' and focus == 'scattered':
        return ['brainstorming', 'quick tasks', 'physical organization']
    else:
        return ['standard tasks', 'review work', 'communication']


def _suggest_session_adjustments(energy: str, focus: str, stress: str) -> Dict:
    """Suggest session adjustments"""
    adjustments = {}
    
    if stress == 'high':
        adjustments['session_length'] = 'shorter'
        adjustments['break_frequency'] = 'more frequent'
    
    if focus == 'scattered':
        adjustments['task_size'] = 'smaller'
        adjustments['structure'] = 'more rigid'
    
    if energy == 'low':
        adjustments['pace'] = 'slower'
        adjustments['expectations'] = 'adjusted'
    
    return adjustments