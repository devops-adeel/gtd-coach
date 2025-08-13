#!/usr/bin/env python3
"""
Timing Integration Tools for GTD Agent
Extracted from workflow nodes to be reusable tools
"""

import os
import logging
from typing import Dict, List, Optional, Annotated
from datetime import datetime, timedelta
from langchain_core.tools import tool
from langgraph.prebuilt import InjectedState

# Import from existing integrations
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from gtd_coach.integrations.timing import TimingAPI
from gtd_coach.agent.state import AgentState

logger = logging.getLogger(__name__)


@tool
def analyze_timing_tool(
    date: str = "yesterday",
    state: Annotated[AgentState, InjectedState] = None
) -> Dict:
    """
    Analyzes time tracking data from Timing app and returns insights.
    
    Args:
        date: Date to analyze ("yesterday", "today", or YYYY-MM-DD format)
        state: Injected agent state
    
    Returns:
        Dictionary containing:
        - focus_score: 0-100 rating of focus
        - switches_per_hour: Context switch frequency
        - uncategorized_minutes: Time not categorized
        - top_projects: List of top 5 projects with time spent
        - hyperfocus_periods: Periods of deep focus
        - scatter_periods: Periods of rapid switching
        - time_sinks: Unproductive time categories
    """
    # Initialize Timing API with fallback
    timing_api = TimingAPI()
    if not timing_api.is_configured():
        # Return cached/mock data for demo
        return _get_fallback_timing_data(date, state)
    
    # Parse date
    if date == "yesterday":
        target_date = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
    elif date == "today":
        target_date = datetime.now().strftime("%Y-%m-%d")
    else:
        target_date = date
    
    try:
        # Fetch time entries
        entries = timing_api.fetch_time_entries_last_week(max_entries=500)
        
        # Filter to target date
        date_entries = [
            e for e in entries
            if e.get('start_time') and target_date in e['start_time']
        ]
        
        if not date_entries:
            return {
                "focus_score": None,
                "message": f"No time data for {target_date}",
                "uncategorized_minutes": 0,
                "top_projects": []
            }
        
        # Analyze context switches
        switch_analysis = timing_api.detect_context_switches(date_entries)
        
        # Calculate focus metrics
        focus_metrics = timing_api.calculate_focus_metrics(switch_analysis)
        
        # Get project summary
        projects = timing_api.fetch_projects_last_week(min_minutes=5)
        
        # Filter projects to target date
        date_projects = []
        for project in projects:
            # Calculate time for this project on target date
            project_time = sum(
                e.get('duration', 0) for e in date_entries
                if e.get('project') == project['name']
            )
            if project_time > 0:
                date_projects.append({
                    'name': project['name'],
                    'time_spent': round(project_time / 60, 1),  # Convert to hours
                    'percentage': round(project_time / sum(e.get('duration', 0) for e in date_entries) * 100, 1)
                })
        
        # Sort by time spent
        date_projects.sort(key=lambda x: x['time_spent'], reverse=True)
        
        # Calculate uncategorized time
        uncategorized_entries = [
            e for e in date_entries
            if 'uncategorized' in e.get('project', '').lower() or
               'misc' in e.get('project', '').lower() or
               not e.get('project')
        ]
        uncategorized_minutes = sum(e.get('duration', 0) for e in uncategorized_entries)
        
        # Identify time sinks (unproductive categories)
        time_sinks = []
        sink_keywords = ['social media', 'youtube', 'reddit', 'twitter', 'facebook', 'instagram', 'news']
        for entry in date_entries:
            app = entry.get('app', '').lower()
            project = entry.get('project', '').lower()
            if any(kw in app or kw in project for kw in sink_keywords):
                time_sinks.append({
                    'app': entry.get('app'),
                    'duration_minutes': entry.get('duration', 0),
                    'time_range': f"{entry.get('start_time', '').split('T')[1][:5]} - {entry.get('end_time', '').split('T')[1][:5]}"
                })
        
        # Prepare timing data for state update
        timing_update = {
            'timing_data': {
                'date': target_date,
                'entries': date_entries[:20],  # Keep limited for memory
                'projects': date_projects[:10]
            },
            'focus_score': focus_metrics['focus_score'],
            'context_switches': switch_analysis.get('switches', [])[:10],
            'uncategorized_minutes': uncategorized_minutes
        }
        
        return {
            "date_analyzed": target_date,
            "focus_score": focus_metrics['focus_score'],
            "switches_per_hour": focus_metrics['switches_per_hour'],
            "hyperfocus_score": focus_metrics['hyperfocus_score'],
            "interpretation": focus_metrics['interpretation'],
            "uncategorized_minutes": uncategorized_minutes,
            "uncategorized_percentage": round(uncategorized_minutes / sum(e.get('duration', 0) for e in date_entries) * 100, 1) if date_entries else 0,
            "top_projects": date_projects[:5],
            "total_hours": round(sum(e.get('duration', 0) for e in date_entries) / 60, 1),
            "time_sinks": time_sinks[:5],
            "recommendation": _generate_timing_recommendation(focus_metrics, uncategorized_minutes),
            "timing_update": timing_update
        }
        
    except TimeoutError as e:
        logger.warning(f"Timing API timeout: {e}")
        # Return fallback data on timeout
        return _get_fallback_timing_data(date, state)
    except Exception as e:
        logger.error(f"Error analyzing timing data: {e}")
        # Return fallback data on error
        return _get_fallback_timing_data(date, state)


@tool
def review_uncategorized_tool(
    time_blocks: List[Dict],
    state: Annotated[AgentState, InjectedState] = None
) -> Dict:
    """
    Reviews uncategorized time blocks and suggests categorization.
    
    Args:
        time_blocks: List of uncategorized time blocks to review
        state: Injected agent state
    
    Returns:
        Dictionary with categorization suggestions for each block
    """
    if not time_blocks:
        return {
            "message": "No uncategorized blocks to review",
            "suggestions": []
        }
    
    suggestions = []
    
    for block in time_blocks[:5]:  # Limit to 5 blocks for quick review
        # Extract app and time information
        apps = block.get('apps', 'Unknown')
        duration = block.get('duration_minutes', 0)
        time_range = block.get('time_range', 'Unknown time')
        
        # Generate suggestion based on app patterns
        suggestion = _suggest_category(apps)
        
        suggestions.append({
            "time_range": time_range,
            "duration_minutes": duration,
            "apps": apps,
            "suggested_category": suggestion['category'],
            "confidence": suggestion['confidence'],
            "reasoning": suggestion['reasoning']
        })
    
    # Prepare auto-categorizations for state update
    auto_categorizations = []
    for suggestion in suggestions:
        if suggestion['confidence'] == 'high':
            auto_categorizations.append({
                "content": f"Categorize {suggestion['apps']} time as {suggestion['suggested_category']}",
                "source": "timing",
                "category": "reference",
                "auto_categorized": True,
                "capture_time": datetime.now().isoformat()
            })
    
    return {
        "reviewed_blocks": len(suggestions),
        "suggestions": suggestions,
        "auto_categorized": sum(1 for s in suggestions if s['confidence'] == 'high'),
        "needs_review": sum(1 for s in suggestions if s['confidence'] in ['medium', 'low']),
        "auto_categorizations": auto_categorizations
    }


@tool
def calculate_focus_alignment_tool(
    priorities: List[str],
    state: Annotated[AgentState, InjectedState] = None
) -> Dict:
    """
    Calculates alignment between time spent and stated priorities.
    
    Args:
        priorities: List of current priority items/projects
        state: Injected agent state with timing_data
    
    Returns:
        Dictionary with alignment score and recommendations
    """
    if not state or not state.get('timing_data'):
        return {
            "error": "No timing data available in state",
            "alignment_score": 0,
            "recommendations": []
        }
    
    timing_data = state['timing_data']
    projects = timing_data.get('projects', [])
    
    if not projects or not priorities:
        return {
            "alignment_score": 0,
            "message": "Need both time data and priorities for alignment",
            "recommendations": []
        }
    
    # Calculate alignment
    aligned_projects = []
    untracked_priorities = []
    time_on_priorities = 0
    total_time = sum(p['time_spent'] for p in projects)
    
    for priority in priorities:
        # Find matching project in timing data
        matched = False
        for project in projects:
            if _fuzzy_match(priority, project['name']):
                aligned_projects.append({
                    'priority': priority,
                    'time_spent': project['time_spent'],
                    'percentage': project['percentage']
                })
                time_on_priorities += project['time_spent']
                matched = True
                break
        
        if not matched:
            untracked_priorities.append(priority)
    
    # Calculate alignment score (0-100)
    if total_time > 0:
        alignment_score = min(100, round((time_on_priorities / total_time) * 100))
    else:
        alignment_score = 0
    
    # Generate recommendations
    recommendations = []
    
    if alignment_score < 50:
        recommendations.append("⚠️ Less than half your time aligned with priorities")
    
    if untracked_priorities:
        recommendations.append(f"🎯 No time tracked on: {', '.join(untracked_priorities[:3])}")
    
    # Identify time sinks not in priorities
    non_priority_projects = [
        p for p in projects[:5]
        if not any(_fuzzy_match(priority, p['name']) for priority in priorities)
    ]
    if non_priority_projects:
        top_sink = non_priority_projects[0]
        recommendations.append(f"⏱️ {top_sink['time_spent']}h on '{top_sink['name']}' - intentional?")
    
    return {
        "alignment_score": alignment_score,
        "time_on_priorities_hours": round(time_on_priorities, 1),
        "total_tracked_hours": round(total_time, 1),
        "aligned_projects": aligned_projects,
        "untracked_priorities": untracked_priorities,
        "recommendations": recommendations,
        "interpretation": _interpret_alignment(alignment_score)
    }


def _generate_timing_recommendation(focus_metrics: Dict, uncategorized_minutes: int) -> str:
    """Generate actionable recommendation based on timing analysis"""
    recommendations = []
    
    # Focus-based recommendations
    if focus_metrics['focus_score'] < 50:
        if focus_metrics['switches_per_hour'] > 10:
            recommendations.append("Try 25-minute focus blocks with notifications off")
        else:
            recommendations.append("Consider batching similar tasks together")
    elif focus_metrics['hyperfocus_score'] > 80:
        recommendations.append("Great deep work! Schedule breaks to maintain energy")
    
    # Uncategorized time recommendations
    if uncategorized_minutes > 60:
        recommendations.append(f"Review {uncategorized_minutes} minutes of uncategorized time")
    
    return " | ".join(recommendations) if recommendations else "Good time tracking discipline!"


def _suggest_category(apps: str) -> Dict:
    """Suggest category based on app usage patterns"""
    apps_lower = apps.lower()
    
    # High confidence patterns
    if any(term in apps_lower for term in ['xcode', 'vscode', 'pycharm', 'intellij', 'sublime']):
        return {
            'category': 'Development',
            'confidence': 'high',
            'reasoning': 'Development tools detected'
        }
    elif any(term in apps_lower for term in ['slack', 'teams', 'zoom', 'meet']):
        return {
            'category': 'Communication',
            'confidence': 'high',
            'reasoning': 'Communication apps detected'
        }
    elif any(term in apps_lower for term in ['chrome', 'safari', 'firefox', 'edge']):
        # Medium confidence for browsers - could be many things
        return {
            'category': 'Research/Browsing',
            'confidence': 'medium',
            'reasoning': 'Web browser - needs context'
        }
    elif any(term in apps_lower for term in ['mail', 'outlook', 'gmail']):
        return {
            'category': 'Email',
            'confidence': 'high',
            'reasoning': 'Email client detected'
        }
    else:
        return {
            'category': 'Other',
            'confidence': 'low',
            'reasoning': 'Unknown app pattern'
        }


def _fuzzy_match(str1: str, str2: str) -> bool:
    """Simple fuzzy matching for project names"""
    str1_lower = str1.lower()
    str2_lower = str2.lower()
    
    # Exact match
    if str1_lower == str2_lower:
        return True
    
    # Substring match
    if str1_lower in str2_lower or str2_lower in str1_lower:
        return True
    
    # Key terms match
    str1_terms = set(str1_lower.split())
    str2_terms = set(str2_lower.split())
    
    # If significant overlap in terms
    overlap = str1_terms & str2_terms
    if len(overlap) >= min(len(str1_terms), len(str2_terms)) * 0.5:
        return True
    
    return False


def _interpret_alignment(score: int) -> str:
    """Interpret alignment score with ADHD-aware messaging"""
    if score >= 80:
        return "Excellent! Your time closely matches your priorities"
    elif score >= 60:
        return "Good alignment with room for improvement"
    elif score >= 40:
        return "Moderate alignment - some priority drift occurring"
    elif score >= 20:
        return "Low alignment - significant time on non-priorities"
    else:
        return "Very low alignment - time and priorities disconnected"


def _get_fallback_timing_data(date: str, state: Optional[Dict]) -> Dict:
    """Provide fallback timing data when API is unavailable"""
    logger.info("Using fallback timing data (API unavailable)")
    
    # Check if we have cached data in state
    if state and state.get('timing_data'):
        cached_data = state['timing_data']
        return {
            "date_analyzed": date,
            "focus_score": state.get('focus_score', 65),
            "switches_per_hour": 5,
            "hyperfocus_score": 40,
            "interpretation": "Using cached data - API temporarily unavailable",
            "uncategorized_minutes": state.get('uncategorized_minutes', 45),
            "uncategorized_percentage": 15,
            "top_projects": cached_data.get('projects', [])[:5],
            "total_hours": 7.5,
            "time_sinks": [],
            "recommendation": "Timing API unavailable - using last known data",
            "fallback_mode": True
        }
    
    # Return demo data if no cache
    return {
        "date_analyzed": date,
        "focus_score": 70,
        "switches_per_hour": 4,
        "hyperfocus_score": 45,
        "interpretation": "Demo mode - Timing API not configured",
        "uncategorized_minutes": 30,
        "uncategorized_percentage": 10,
        "top_projects": [
            {"name": "GTD Review", "time_spent": 2.5, "percentage": 33},
            {"name": "Development", "time_spent": 3.0, "percentage": 40},
            {"name": "Meetings", "time_spent": 1.5, "percentage": 20}
        ],
        "total_hours": 7.5,
        "time_sinks": [],
        "recommendation": "Configure Timing API for real focus tracking",
        "fallback_mode": True,
        "timing_update": {
            'timing_data': {'date': date, 'entries': [], 'projects': []},
            'focus_score': 70,
            'context_switches': [],
            'uncategorized_minutes': 30
        }
    }