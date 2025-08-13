#!/usr/bin/env python3
"""
GTD Processing Tools for GTD Agent
Tools for clarifying and organizing captured items
"""

import logging
from typing import Dict, List, Optional, Annotated
from datetime import datetime, timedelta
from langchain_core.tools import tool
from langgraph.prebuilt import InjectedState

# Import state and entities
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from gtd_coach.agent.state import AgentState, DailyCapture
from gtd_coach.integrations.gtd_entities import (
    GTDAction, GTDProject, Priority, Energy, ProjectStatus
)

logger = logging.getLogger(__name__)


@tool
def clarify_items_tool(
    items_to_clarify: Optional[List[Dict]] = None,
    state: Annotated[AgentState, InjectedState] = None
) -> Dict:
    """
    Clarifies captured items through GTD methodology.
    
    Args:
        items_to_clarify: Optional list of specific items to clarify
        state: Injected agent state with captures
    
    Returns:
        Dictionary with:
        - clarified_count: Number of items processed
        - actions: List of clarified next actions
        - projects: Any new projects identified
        - someday_maybe: Items deferred to someday/maybe
        - reference: Reference items to file
        - questions: Clarifying questions for ambiguous items
    """
    # Get items to process
    if items_to_clarify:
        items = items_to_clarify
    elif state and 'captures' in state:
        items = [c for c in state['captures'] if not c.get('clarified', False)]
    else:
        return {
            "error": "No items to clarify",
            "clarified_count": 0
        }
    
    clarified = {
        'actions': [],
        'projects': [],
        'someday_maybe': [],
        'reference': [],
        'trash': [],
        'questions': []
    }
    
    for item in items:
        content = item.get('content', '')
        source = item.get('source', 'unknown')
        
        # Run through GTD clarification process
        clarification = _clarify_single_item(content, source, state)
        
        # Sort into appropriate bucket
        if clarification['actionable']:
            if clarification['is_project']:
                clarified['projects'].append(clarification)
            else:
                clarified['actions'].append(clarification)
        elif clarification['category'] == 'someday':
            clarified['someday_maybe'].append(clarification)
        elif clarification['category'] == 'reference':
            clarified['reference'].append(clarification)
        elif clarification['category'] == 'trash':
            clarified['trash'].append(clarification)
        
        # Add any questions
        if clarification.get('needs_clarification'):
            clarified['questions'].append({
                'item': content,
                'question': clarification['clarifying_question']
            })
        
        # Mark item as processed in clarification result
        clarification['original_content'] = content
        clarification['processed'] = True
    
    # Generate insights
    insights = _generate_clarification_insights(clarified)
    
    return {
        "clarified_count": len(items),
        "actions": clarified['actions'],
        "projects": clarified['projects'],
        "someday_maybe": clarified['someday_maybe'],
        "reference": clarified['reference'],
        "trash": clarified['trash'],
        "questions": clarified['questions'],
        "insights": insights,
        "next_step": _suggest_next_step(clarified)
    }


@tool
def organize_tool(
    state: Annotated[AgentState, InjectedState] = None
) -> Dict:
    """
    Organizes clarified items into GTD system with priorities.
    
    Args:
        state: Injected agent state with clarified items
    
    Returns:
        Dictionary with organized items by context and priority
    """
    if not state or 'captures' not in state:
        return {
            "error": "No items to organize",
            "organized_count": 0
        }
    
    # Get clarified actionable items
    actionable_items = [
        c for c in state['captures']
        if c.get('clarified') and c.get('actionable')
    ]
    
    if not actionable_items:
        return {
            "message": "No actionable items to organize",
            "organized_count": 0
        }
    
    # Organize by context
    by_context = {}
    by_priority = {'A': [], 'B': [], 'C': []}
    by_energy = {'high': [], 'medium': [], 'low': []}
    quick_wins = []  # 2-minute rule items
    
    for item in actionable_items:
        context = item.get('context_required', '@anywhere')
        
        # Add to context list
        if context not in by_context:
            by_context[context] = []
        by_context[context].append(item)
        
        # Assign priority
        priority = _assign_priority(item, state)
        item['priority'] = priority
        by_priority[priority].append(item)
        
        # Sort by energy
        energy = item.get('energy_level', 'medium')
        by_energy[energy].append(item)
        
        # Check for quick wins
        if item.get('two_minute_rule') or item.get('time_estimate', 999) <= 5:
            quick_wins.append(item)
    
    # Create GTDAction entities for processed items
    processed_actions = []
    for item in actionable_items:
        action = GTDAction(
            description=item.get('next_action', item['content']),
            context=item.get('context_required', '@anywhere'),
            priority=Priority[item['priority']],
            energy_required=Energy[item.get('energy_level', 'MEDIUM').upper()],
            time_estimate=item.get('time_estimate', 30),
            created_date=datetime.now().isoformat(),
            project_id=item.get('project_id')
        )
        processed_actions.append(action.dict())
    
    # Return processed actions for state update
    
    # Generate organization summary
    summary = _generate_organization_summary(by_context, by_priority, quick_wins)
    
    return {
        "organized_count": len(actionable_items),
        "by_context": {k: len(v) for k, v in by_context.items()},
        "by_priority": {k: len(v) for k, v in by_priority.items()},
        "quick_wins": len(quick_wins),
        "contexts": list(by_context.keys()),
        "processed_actions": processed_actions,  # All processed actions for state update
        "next_actions": processed_actions[:5],  # Top 5 for display
        "summary": summary,
        "recommendations": _generate_organization_recommendations(by_priority, by_context, state)
    }


@tool
def create_project_tool(
    title: str,
    outcome: str,
    next_action: str,
    area_of_focus: Optional[str] = None,
    state: Annotated[AgentState, InjectedState] = None
) -> Dict:
    """
    Creates a new GTD project from captured items.
    
    Args:
        title: Project title
        outcome: Desired outcome/success criteria
        next_action: The immediate next action
        area_of_focus: Life area this relates to
        state: Injected agent state
    
    Returns:
        Dictionary with created project details
    """
    # Create project entity
    project = GTDProject(
        title=title,
        outcome=outcome,
        next_action=next_action,
        area_of_focus=area_of_focus or "Work",
        status=ProjectStatus.ACTIVE,
        created_date=datetime.now().isoformat()
    )
    
    # Generate project ID for linking
    project_id = f"proj_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    project_dict = project.dict()
    project_dict['project_id'] = project_id
    
    # Find related captures for linking
    related_captures = []
    if state and 'captures' in state:
        for capture in state.get('captures', []):
            if title.lower() in capture.get('content', '').lower():
                related_captures.append(capture.get('content'))
    
    return {
        "project": project_dict,
        "project_id": project_id,
        "related_captures": related_captures,
        "message": f"✓ Project created: {title}",
        "next_action": next_action,
        "suggested_milestones": _suggest_project_milestones(title, outcome)
    }


@tool
def prioritize_actions_tool(
    criteria: Optional[str] = "eisenhower",
    state: Annotated[AgentState, InjectedState] = None
) -> Dict:
    """
    Prioritizes actions using specified criteria.
    
    Args:
        criteria: Prioritization method (eisenhower, abc, energy)
        state: Injected agent state
    
    Returns:
        Dictionary with prioritized action list
    """
    if not state or 'processed_items' not in state:
        return {
            "error": "No actions to prioritize",
            "prioritized_count": 0
        }
    
    actions = state['processed_items']
    
    if criteria == "eisenhower":
        prioritized = _prioritize_eisenhower(actions)
    elif criteria == "abc":
        prioritized = _prioritize_abc(actions)
    elif criteria == "energy":
        prioritized = _prioritize_by_energy(actions, state)
    else:
        prioritized = actions  # No change
    
    # Return prioritized list for state update
    
    return {
        "prioritized_count": len(prioritized),
        "top_priorities": prioritized[:5],
        "method_used": criteria,
        "distribution": _get_priority_distribution(prioritized),
        "suggested_sequence": _suggest_action_sequence(prioritized, state)
    }


def _clarify_single_item(content: str, source: str, state: Optional[Dict]) -> Dict:
    """Clarify a single item through GTD questions"""
    result = {
        'original': content,
        'actionable': False,
        'is_project': False,
        'category': 'inbox',
        'needs_clarification': False
    }
    
    content_lower = content.lower()
    
    # Is it actionable?
    action_indicators = ['need to', 'have to', 'should', 'must', 'will', 'want to', 'plan to']
    if any(indicator in content_lower for indicator in action_indicators):
        result['actionable'] = True
        
        # Is it a project (multiple steps)?
        project_indicators = ['project', 'implement', 'organize', 'create', 'build', 'develop', 'launch']
        if any(indicator in content_lower for indicator in project_indicators) or len(content) > 100:
            result['is_project'] = True
            result['outcome'] = f"Complete: {content}"
            result['next_action'] = _extract_next_action(content)
        else:
            # Single action
            result['next_action'] = _extract_next_action(content)
            result['context'] = _determine_context(content)
            result['time_estimate'] = _estimate_time(content)
            result['energy'] = _determine_energy(content)
            
            # Check 2-minute rule
            if result['time_estimate'] <= 2:
                result['two_minute_rule'] = True
    else:
        # Not actionable - determine category
        if any(word in content_lower for word in ['someday', 'maybe', 'possibly', 'idea']):
            result['category'] = 'someday'
        elif any(word in content_lower for word in ['reference', 'info', 'note', 'fyi']):
            result['category'] = 'reference'
        elif any(word in content_lower for word in ['waiting', 'pending', 'need from']):
            result['category'] = 'waiting'
        elif len(content) < 10 or content_lower in ['ok', 'done', 'n/a', 'nothing']:
            result['category'] = 'trash'
        else:
            result['needs_clarification'] = True
            result['clarifying_question'] = f"Is '{content}' something you need to act on?"
    
    return result


def _extract_next_action(content: str) -> str:
    """Extract concrete next action from content"""
    # Remove common prefixes
    prefixes = ['need to', 'have to', 'should', 'must', 'want to', 'plan to']
    action = content.lower()
    for prefix in prefixes:
        if action.startswith(prefix):
            action = action[len(prefix):].strip()
            break
    
    # Ensure it starts with a verb
    if not action.startswith(('call', 'email', 'write', 'review', 'create', 'send', 'schedule')):
        action = f"Process: {action}"
    
    return action.capitalize()


def _determine_context(content: str) -> str:
    """Determine GTD context for action"""
    content_lower = content.lower()
    
    if any(word in content_lower for word in ['call', 'phone', 'dial']):
        return '@phone'
    elif any(word in content_lower for word in ['email', 'send', 'reply']):
        return '@computer'
    elif any(word in content_lower for word in ['meeting', 'discuss', 'talk']):
        return '@office'
    elif any(word in content_lower for word in ['buy', 'shop', 'pick up']):
        return '@errands'
    elif any(word in content_lower for word in ['home', 'house', 'apartment']):
        return '@home'
    else:
        return '@anywhere'


def _estimate_time(content: str) -> int:
    """Estimate time in minutes for action"""
    content_lower = content.lower()
    
    # Quick tasks
    if any(word in content_lower for word in ['quick', 'simple', 'just']):
        return 5
    # Communication tasks
    elif any(word in content_lower for word in ['email', 'call', 'message']):
        return 10
    # Review tasks
    elif any(word in content_lower for word in ['review', 'read', 'check']):
        return 20
    # Complex tasks
    elif any(word in content_lower for word in ['create', 'write', 'develop', 'analyze']):
        return 45
    else:
        return 15  # Default


def _determine_energy(content: str) -> str:
    """Determine energy level required"""
    content_lower = content.lower()
    
    if any(word in content_lower for word in ['create', 'analyze', 'design', 'write', 'develop']):
        return 'high'
    elif any(word in content_lower for word in ['review', 'organize', 'plan']):
        return 'medium'
    else:
        return 'low'


def _assign_priority(item: Dict, state: Optional[Dict]) -> str:
    """Assign ABC priority to item"""
    content = item.get('content', '').lower()
    
    # A priority indicators
    if any(word in content for word in ['urgent', 'asap', 'today', 'deadline', 'critical']):
        return 'A'
    # Check if related to current focus areas
    elif state and 'user_context' in state:
        focus_areas = state['user_context'].get('focus_areas', [])
        if any(area.lower() in content for area in focus_areas):
            return 'A'
    # B priority for normal work
    elif any(word in content for word in ['tomorrow', 'this week', 'soon']):
        return 'B'
    # C priority for everything else
    else:
        return 'C'


def _generate_clarification_insights(clarified: Dict) -> Dict:
    """Generate insights from clarification results"""
    total = sum(len(v) for v in clarified.values())
    actionable = len(clarified['actions']) + len(clarified['projects'])
    
    insights = {
        'actionable_rate': round(actionable / total * 100, 1) if total > 0 else 0,
        'project_count': len(clarified['projects']),
        'quick_wins': sum(1 for a in clarified['actions'] if a.get('two_minute_rule')),
        'needs_clarification': len(clarified['questions'])
    }
    
    # Add interpretation
    if insights['actionable_rate'] > 70:
        insights['interpretation'] = "High actionability - good concrete capture"
    elif insights['actionable_rate'] < 30:
        insights['interpretation'] = "Low actionability - mostly reference/someday items"
    else:
        insights['interpretation'] = "Balanced mix of actionable and reference items"
    
    return insights


def _suggest_next_step(clarified: Dict) -> str:
    """Suggest next step based on clarification results"""
    if clarified['questions']:
        return f"Answer {len(clarified['questions'])} clarifying questions"
    elif len(clarified['actions']) > 20:
        return "Prioritize your long action list"
    elif clarified['projects']:
        return f"Define next actions for {len(clarified['projects'])} new projects"
    else:
        return "Ready to organize into your system"


def _generate_organization_summary(by_context: Dict, by_priority: Dict, quick_wins: List) -> str:
    """Generate organization summary"""
    parts = []
    
    if quick_wins:
        parts.append(f"🚀 {len(quick_wins)} quick wins ready")
    
    if by_priority['A']:
        parts.append(f"🔴 {len(by_priority['A'])} high priority items")
    
    contexts = list(by_context.keys())
    if len(contexts) > 1:
        parts.append(f"📍 Organized across {len(contexts)} contexts")
    
    return " | ".join(parts) if parts else "Items organized successfully"


def _generate_organization_recommendations(by_priority: Dict, by_context: Dict, state: Optional[Dict]) -> List[str]:
    """Generate recommendations based on organization"""
    recommendations = []
    
    # Check for priority imbalance
    if len(by_priority['A']) > 10:
        recommendations.append("⚠️ Many high-priority items - consider if all are truly urgent")
    
    # Check for context batching opportunities
    for context, items in by_context.items():
        if len(items) >= 5:
            recommendations.append(f"💡 Batch {context} tasks - you have {len(items)} items")
    
    # Check energy levels if available
    if state and 'user_energy' in state:
        if state['user_energy'] == 'low' and len(by_priority['A']) > 3:
            recommendations.append("🔋 Low energy + high priority items - tackle just top 1-2")
    
    return recommendations[:3]  # Limit recommendations


def _suggest_project_milestones(title: str, outcome: str) -> List[str]:
    """Suggest project milestones"""
    # This would be enhanced with LLM in production
    return [
        "Define project scope and requirements",
        "Complete initial research/planning",
        "Execute main deliverables",
        f"Review and finalize: {outcome}"
    ]


def _prioritize_eisenhower(actions: List[Dict]) -> List[Dict]:
    """Prioritize using Eisenhower matrix"""
    # Simplified implementation
    return sorted(actions, key=lambda x: (
        x.get('priority', 'C'),
        -x.get('time_estimate', 999)
    ))


def _prioritize_abc(actions: List[Dict]) -> List[Dict]:
    """Prioritize using ABC method"""
    return sorted(actions, key=lambda x: x.get('priority', 'C'))


def _prioritize_by_energy(actions: List[Dict], state: Optional[Dict]) -> List[Dict]:
    """Prioritize based on current energy level"""
    current_energy = state.get('user_energy', 'medium') if state else 'medium'
    
    # Match tasks to energy
    if current_energy == 'high':
        # Do high energy tasks first
        return sorted(actions, key=lambda x: (
            {'high': 0, 'medium': 1, 'low': 2}.get(x.get('energy_level', 'medium'), 3),
            x.get('priority', 'C')
        ))
    else:
        # Do low energy tasks first
        return sorted(actions, key=lambda x: (
            {'low': 0, 'medium': 1, 'high': 2}.get(x.get('energy_level', 'medium'), 3),
            x.get('priority', 'C')
        ))


def _get_priority_distribution(actions: List[Dict]) -> Dict:
    """Get distribution of priorities"""
    distribution = {'A': 0, 'B': 0, 'C': 0}
    for action in actions:
        priority = action.get('priority', 'C')
        distribution[priority] += 1
    return distribution


def _suggest_action_sequence(actions: List[Dict], state: Optional[Dict]) -> List[str]:
    """Suggest optimal sequence for actions"""
    suggestions = []
    
    # Start with quick wins
    quick_wins = [a for a in actions if a.get('two_minute_rule')]
    if quick_wins:
        suggestions.append(f"Start with {len(quick_wins)} quick wins to build momentum")
    
    # Then high priority
    high_priority = [a for a in actions if a.get('priority') == 'A']
    if high_priority:
        suggestions.append(f"Then tackle your {len(high_priority)} high-priority items")
    
    # Context batching
    contexts = {}
    for action in actions:
        ctx = action.get('context', '@anywhere')
        if ctx not in contexts:
            contexts[ctx] = 0
        contexts[ctx] += 1
    
    for ctx, count in contexts.items():
        if count >= 3:
            suggestions.append(f"Batch {count} {ctx} tasks together")
    
    return suggestions[:3]