#!/usr/bin/env python3
"""
Graphiti Memory Tools for GTD Agent
Tools for saving and loading from knowledge graph
"""

import os
import json
import logging
from typing import Dict, List, Optional, Annotated
from datetime import datetime
from pathlib import Path
from langchain_core.tools import tool
from langgraph.prebuilt import InjectedState

# Import from existing integrations
import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from gtd_coach.integrations.graphiti import GraphitiMemory
from gtd_coach.agent.state import AgentState

logger = logging.getLogger(__name__)


@tool
def save_memory_tool(
    episode_type: str,
    episode_data: Dict,
    description: str,
    state: Annotated[AgentState, InjectedState] = None
) -> Dict:
    """
    Saves session data to Graphiti knowledge graph.
    
    Args:
        episode_type: Type of episode (session, pattern, insight)
        episode_data: Data to save
        description: Human-readable description
        state: Injected agent state
    
    Returns:
        Dictionary with save status and episode ID
    """
    # Get session_id from state or use a default
    session_id = state.get('session_id') if state else datetime.now().strftime('%Y%m%d_%H%M%S')
    memory = GraphitiMemory(session_id)
    
    if not memory.is_configured():
        # Fallback to JSON file storage
        return _save_to_json_fallback(episode_type, episode_data, description, state)
    
    try:
        # Enhance episode with session metadata
        if state:
            episode_data['session_id'] = state.get('session_id')
            episode_data['workflow_type'] = state.get('workflow_type')
            episode_data['timestamp'] = datetime.now().isoformat()
            
            # Add ADHD patterns if detected
            if state.get('adhd_patterns'):
                episode_data['adhd_patterns'] = state['adhd_patterns']
            
            # Add focus metrics if available
            if state.get('focus_score') is not None:
                episode_data['focus_metrics'] = {
                    'focus_score': state['focus_score'],
                    'context_switches': len(state.get('context_switches', []))
                }
        
        # Save to Graphiti
        episode_id = memory.add_episode(
            episode_data,
            description,
            episode_type=episode_type
        )
        
        logger.info(f"Saved episode {episode_id} to Graphiti")
        
        return {
            "success": True,
            "episode_id": episode_id,
            "message": f"✓ Saved to memory: {description[:50]}...",
            "episode_to_track": episode_id  # For state update
        }
        
    except Exception as e:
        logger.error(f"Failed to save to Graphiti: {e}")
        return _save_to_json_fallback(episode_type, episode_data, description, state)


@tool
def load_context_tool(
    user_id: Optional[str] = None,
    lookback_days: int = 7,
    state: Annotated[AgentState, InjectedState] = None
) -> Dict:
    """
    Loads user context from Graphiti including patterns and history.
    
    Args:
        user_id: User identifier
        lookback_days: How many days of history to load
        state: Injected agent state
    
    Returns:
        Dictionary with user context and patterns
    """
    # Get session_id from state or use a default
    session_id = state.get('session_id') if state else datetime.now().strftime('%Y%m%d_%H%M%S')
    memory = GraphitiMemory(session_id)
    
    if not memory.is_configured():
        return _load_from_json_fallback(user_id, state)
    
    try:
        # Get user context
        context = memory.get_user_context(user_id)
        
        # Search for recent patterns
        patterns = memory.search_nodes(
            query="ADHD patterns behavior focus",
            entity_type="ADHDPattern",
            max_nodes=10
        )
        
        # Search for recurring themes
        recurring = memory.search_facts(
            query="recurring weekly review capture",
            max_facts=20
        )
        
        # Extract key insights
        user_context = {
            'user_id': user_id or context.get('user_id'),
            'adhd_severity': context.get('adhd_severity', 'medium'),
            'preferred_accountability': context.get('preferred_accountability', 'adaptive'),
            'average_capture_count': context.get('average_capture_count', 10),
            'focus_trend': context.get('focus_trend'),
            'recurring_patterns': _extract_recurring_patterns(recurring),
            'recent_patterns': _extract_adhd_patterns(patterns),
            'last_session': context.get('last_session_date')
        }
        
        # Determine accountability mode
        if user_context['adhd_severity'] == 'high':
            recommended_mode = 'firm'
        elif user_context['adhd_severity'] == 'low':
            recommended_mode = 'gentle'
        else:
            recommended_mode = 'adaptive'
        
        return {
            "context_loaded": True,
            "user_id": user_context['user_id'],
            "patterns_found": len(user_context['recurring_patterns']),
            "adhd_insights": user_context['recent_patterns'],
            "recommended_mode": recommended_mode,
            "user_context": user_context,  # For state update
            "message": _generate_context_message(user_context)
        }
        
    except Exception as e:
        logger.error(f"Failed to load from Graphiti: {e}")
        return _load_from_json_fallback(user_id, state)


@tool
def search_memory_tool(
    query: str,
    search_type: str = "all",
    state: Annotated[AgentState, InjectedState] = None
) -> Dict:
    """
    Searches Graphiti memory for relevant information.
    
    Args:
        query: Search query
        search_type: Type of search (all, patterns, actions, projects)
        state: Injected agent state
    
    Returns:
        Dictionary with search results
    """
    # Get session_id from state or use a default
    session_id = state.get('session_id') if state else datetime.now().strftime('%Y%m%d_%H%M%S')
    memory = GraphitiMemory(session_id)
    
    if not memory.is_configured():
        return {
            "error": "Memory search not available",
            "results": []
        }
    
    try:
        results = {}
        
        if search_type in ["all", "patterns"]:
            # Search for behavior patterns
            patterns = memory.search_nodes(
                query=query,
                entity_type="ADHDPattern" if "pattern" in query.lower() else None,
                max_nodes=5
            )
            results['patterns'] = patterns
        
        if search_type in ["all", "actions"]:
            # Search for actions
            actions = memory.search_nodes(
                query=query,
                entity_type="GTDAction",
                max_nodes=10
            )
            results['actions'] = actions
        
        if search_type in ["all", "projects"]:
            # Search for projects
            projects = memory.search_nodes(
                query=query,
                entity_type="GTDProject",
                max_nodes=5
            )
            results['projects'] = projects
        
        # Search facts for relationships
        facts = memory.search_facts(
            query=query,
            max_facts=10
        )
        results['insights'] = _extract_insights_from_facts(facts)
        
        return {
            "query": query,
            "search_type": search_type,
            "results": results,
            "total_found": sum(len(v) for v in results.values() if isinstance(v, list)),
            "relevance_score": _calculate_relevance(results, query)
        }
        
    except Exception as e:
        logger.error(f"Search failed: {e}")
        return {
            "error": str(e),
            "results": {}
        }


@tool
def update_user_context_tool(
    updates: Dict,
    state: Annotated[AgentState, InjectedState] = None
) -> Dict:
    """
    Updates user context in Graphiti based on session insights.
    
    Args:
        updates: Dictionary of context updates
        state: Injected agent state
    
    Returns:
        Dictionary with update status
    """
    # Get session_id from state or use a default
    session_id = state.get('session_id') if state else datetime.now().strftime('%Y%m%d_%H%M%S')
    memory = GraphitiMemory(session_id)
    
    if not memory.is_configured():
        return _update_json_context(updates, state)
    
    try:
        # Prepare context update
        context_update = {
            'last_session': state.get('session_id') if state else None,
            'last_session_date': datetime.now().isoformat(),
            **updates
        }
        
        # Calculate ADHD severity from patterns
        if state and state.get('adhd_patterns'):
            severity = _calculate_adhd_severity(state['adhd_patterns'])
            context_update['adhd_severity'] = severity
        
        # Update focus trend
        if state and state.get('focus_score') is not None:
            context_update['focus_trend'] = state['focus_score']
        
        # Save as user context episode
        memory.add_user_context_episode(
            context_update,
            f"Context update from session {state.get('session_id') if state else 'unknown'}"
        )
        
        return {
            "success": True,
            "updates_applied": list(updates.keys()),
            "message": "User context updated successfully"
        }
        
    except Exception as e:
        logger.error(f"Failed to update context: {e}")
        return {
            "error": str(e),
            "success": False
        }


def _save_to_json_fallback(episode_type: str, episode_data: Dict, description: str, state: Optional[Dict]) -> Dict:
    """Fallback to JSON file storage"""
    data_dir = Path.home() / "gtd-coach" / "data" / "memory_fallback"
    data_dir.mkdir(parents=True, exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = data_dir / f"{episode_type}_{timestamp}.json"
    
    data = {
        "type": episode_type,
        "description": description,
        "data": episode_data,
        "timestamp": datetime.now().isoformat(),
        "session_id": state.get('session_id') if state else None
    }
    
    with open(filename, 'w') as f:
        json.dump(data, f, indent=2, default=str)
    
    logger.info(f"Saved to JSON fallback: {filename}")
    
    return {
        "success": True,
        "episode_id": f"json_{timestamp}",
        "message": f"✓ Saved to local storage: {description[:50]}...",
        "fallback": True
    }


def _load_from_json_fallback(user_id: Optional[str], state: Optional[Dict]) -> Dict:
    """Load context from JSON files"""
    data_dir = Path.home() / "gtd-coach" / "data"
    context_file = data_dir / "user_context.json"
    
    if context_file.exists():
        with open(context_file, 'r') as f:
            context = json.load(f)
    else:
        context = {
            'user_id': user_id or 'default',
            'adhd_severity': 'medium',
            'preferred_accountability': 'adaptive',
            'recurring_patterns': []
        }
    
    # Load recent patterns from mindsweep files
    patterns = []
    mindsweep_dir = data_dir / "mindsweep"
    if mindsweep_dir.exists():
        files = sorted(mindsweep_dir.glob("*.json"), reverse=True)[:5]
        for file in files:
            with open(file, 'r') as f:
                data = json.load(f)
                if 'patterns' in data:
                    patterns.extend(data['patterns'])
    
    context['recurring_patterns'] = list(set(patterns))[:5]
    
    # Don't modify state directly
    
    return {
        "context_loaded": True,
        "user_id": context['user_id'],
        "patterns_found": len(context['recurring_patterns']),
        "adhd_insights": [],
        "recommended_mode": 'adaptive',
        "message": "Loaded context from local storage",
        "fallback": True
    }


def _update_json_context(updates: Dict, state: Optional[Dict]) -> Dict:
    """Update JSON context file"""
    data_dir = Path.home() / "gtd-coach" / "data"
    context_file = data_dir / "user_context.json"
    
    if context_file.exists():
        with open(context_file, 'r') as f:
            context = json.load(f)
    else:
        context = {}
    
    context.update(updates)
    context['last_updated'] = datetime.now().isoformat()
    
    with open(context_file, 'w') as f:
        json.dump(context, f, indent=2, default=str)
    
    return {
        "success": True,
        "updates_applied": list(updates.keys()),
        "message": "Context updated in local storage",
        "fallback": True
    }


def _extract_recurring_patterns(facts: List[Dict]) -> List[str]:
    """Extract recurring patterns from facts"""
    patterns = []
    for fact in facts:
        if 'recurring' in fact.get('description', '').lower():
            patterns.append(fact.get('subject', ''))
    return list(set(patterns))[:5]


def _extract_adhd_patterns(nodes: List[Dict]) -> List[str]:
    """Extract ADHD patterns from nodes"""
    patterns = []
    for node in nodes:
        if node.get('type') == 'ADHDPattern':
            patterns.append(node.get('description', ''))
    return patterns[:5]


def _extract_insights_from_facts(facts: List[Dict]) -> List[str]:
    """Extract insights from fact relationships"""
    insights = []
    for fact in facts:
        insight = f"{fact.get('subject', 'Item')} → {fact.get('predicate', 'relates to')} → {fact.get('object', 'something')}"
        insights.append(insight)
    return insights[:5]


def _calculate_relevance(results: Dict, query: str) -> float:
    """Calculate relevance score for search results"""
    if not results:
        return 0.0
    
    total_items = sum(len(v) for v in results.values() if isinstance(v, list))
    if total_items == 0:
        return 0.0
    
    # Simple relevance based on result count
    return min(1.0, total_items / 10.0)


def _generate_context_message(context: Dict) -> str:
    """Generate user-friendly context message"""
    parts = []
    
    if context.get('last_session'):
        parts.append(f"Last session: {context['last_session']}")
    
    if context.get('recurring_patterns'):
        parts.append(f"{len(context['recurring_patterns'])} recurring themes")
    
    if context.get('focus_trend'):
        parts.append(f"Focus trend: {context['focus_trend']}/100")
    
    return " | ".join(parts) if parts else "Fresh start - no previous context"


def _calculate_adhd_severity(patterns: List[str]) -> str:
    """Calculate ADHD severity from patterns"""
    high_severity_patterns = ['rapid_switching', 'overwhelm', 'hyperfocus_crash']
    medium_severity_patterns = ['procrastination', 'moderate_switching', 'distraction']
    
    high_count = sum(1 for p in patterns if p in high_severity_patterns)
    medium_count = sum(1 for p in patterns if p in medium_severity_patterns)
    
    if high_count >= 2:
        return 'high'
    elif high_count >= 1 or medium_count >= 2:
        return 'medium'
    else:
        return 'low'