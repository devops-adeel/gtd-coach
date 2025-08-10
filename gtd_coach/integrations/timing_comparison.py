#!/usr/bin/env python3
"""
Time Comparison Module for GTD Review
Compares actual time spent (from Timing) with intended priorities
"""

import json
import os
from pathlib import Path
from typing import List, Dict, Optional

def load_timing_analysis() -> Optional[Dict]:
    """Load the most recent Timing analysis data"""
    analysis_file = Path("data/timing_analysis.json")
    
    if not analysis_file.exists():
        return None
    
    try:
        with open(analysis_file, 'r') as f:
            return json.load(f)
    except Exception:
        return None

def compare_time_with_priorities(timing_projects: List[Dict], 
                                gtd_priorities: List[Dict],
                                timing_details: Optional[Dict] = None) -> Dict:
    """
    Compare time spent (from Timing) with GTD priorities using smart correlation
    
    Args:
        timing_projects: List of projects with time_spent from Timing API
        gtd_priorities: List of priorities from GTD review
        timing_details: Optional detailed timing analysis with focus metrics
    
    Returns:
        Comprehensive comparison analysis with insights
    """
    if not timing_projects or not gtd_priorities:
        return {
            'aligned_projects': [],
            'untracked_priorities': gtd_priorities,
            'time_sinks': timing_projects,
            'alignment_score': 0,
            'recommendations': []
        }
    
    # Enhanced keyword matching with scoring
    aligned = []
    untracked_priorities = []
    time_sinks = []
    matched_timing = set()
    
    # Build keyword sets for better matching
    for priority in gtd_priorities:
        priority_name = priority.get('task', priority.get('action', '')).lower()
        priority_keywords = set(priority_name.split()) - {'the', 'a', 'an', 'for', 'to', 'of'}
        best_match = None
        best_score = 0
        
        for tp in timing_projects:
            tp_name = tp['name'].lower()
            tp_keywords = set(tp_name.split()) - {'the', 'a', 'an', 'for', 'to', 'of'}
            
            # Calculate match score
            common_keywords = priority_keywords & tp_keywords
            if common_keywords:
                score = len(common_keywords) / max(len(priority_keywords), len(tp_keywords))
                
                # Boost score for exact substring matches
                if priority_name in tp_name or tp_name in priority_name:
                    score += 0.5
                
                if score > best_score and score > 0.3:  # Threshold for match
                    best_match = tp
                    best_score = score
        
        if best_match:
            aligned.append({
                'priority': priority.get('task', priority.get('action', '')),
                'timing_project': best_match['name'],
                'time_spent': best_match['time_spent'],
                'priority_level': priority.get('priority', 'C'),
                'match_confidence': round(best_score * 100, 1)
            })
            matched_timing.add(best_match['name'])
        else:
            untracked_priorities.append(priority)
    
    # Find time sinks with categorization
    for tp in timing_projects:
        if tp['name'] not in matched_timing:
            # Categorize the time sink
            category = _categorize_time_sink(tp['name'])
            time_sinks.append({
                **tp,
                'category': category,
                'is_productive': category not in ['distraction', 'communication']
            })
    
    # Calculate enhanced metrics
    total_time = sum(tp['time_spent'] for tp in timing_projects)
    aligned_time = sum(item['time_spent'] for item in aligned)
    alignment_score = (aligned_time / total_time * 100) if total_time > 0 else 0
    
    # Priority distribution analysis
    priority_time = {'A': 0, 'B': 0, 'C': 0}
    for item in aligned:
        priority_time[item['priority_level']] += item['time_spent']
    
    # Generate recommendations
    recommendations = _generate_alignment_recommendations(
        aligned, untracked_priorities, time_sinks, priority_time, total_time
    )
    
    # Add focus correlation if available
    focus_correlation = None
    if timing_details and timing_details.get('focus_metrics'):
        focus_score = timing_details['focus_metrics'].get('focus_score', 50)
        if alignment_score > 70 and focus_score > 70:
            focus_correlation = "High alignment + High focus = Optimal productivity"
        elif alignment_score > 70 and focus_score < 50:
            focus_correlation = "Good priorities but scattered execution"
        elif alignment_score < 50 and focus_score > 70:
            focus_correlation = "Focused work but on wrong priorities"
        else:
            focus_correlation = "Both alignment and focus need improvement"
    
    return {
        'aligned_projects': aligned,
        'untracked_priorities': untracked_priorities,
        'time_sinks': sorted(time_sinks, key=lambda x: x['time_spent'], reverse=True)[:10],
        'alignment_score': round(alignment_score, 1),
        'total_time_tracked': round(total_time, 1),
        'time_on_priorities': round(aligned_time, 1),
        'priority_distribution': priority_time,
        'recommendations': recommendations,
        'focus_correlation': focus_correlation
    }

def _categorize_time_sink(project_name: str) -> str:
    """Categorize a time sink project"""
    name_lower = project_name.lower()
    
    if any(x in name_lower for x in ['safari', 'chrome', 'firefox', 'browser']):
        return 'browsing'
    elif any(x in name_lower for x in ['mail', 'email', 'slack', 'discord', 'messages']):
        return 'communication'
    elif any(x in name_lower for x in ['youtube', 'netflix', 'spotify', 'music']):
        return 'entertainment'
    elif any(x in name_lower for x in ['code', 'xcode', 'terminal', 'docker', 'git']):
        return 'development'
    elif any(x in name_lower for x in ['word', 'docs', 'notion', 'obsidian', 'notes']):
        return 'documentation'
    elif any(x in name_lower for x in ['zoom', 'meet', 'teams', 'webex']):
        return 'meetings'
    else:
        return 'other'

def _generate_alignment_recommendations(aligned: List, untracked: List, 
                                       sinks: List, priority_time: Dict,
                                       total_time: float) -> List[str]:
    """Generate specific recommendations based on alignment analysis"""
    recommendations = []
    
    # Check A priority time
    a_percentage = (priority_time['A'] / total_time * 100) if total_time > 0 else 0
    if a_percentage < 20:
        recommendations.append(f"Only {a_percentage:.0f}% on A priorities - block time for important tasks")
    
    # Check untracked high priorities
    untracked_high = [p for p in untracked if p.get('priority') == 'A']
    if untracked_high:
        recommendations.append(f"{len(untracked_high)} A-priority items got no time - schedule these first")
    
    # Check time sinks
    distraction_time = sum(s['time_spent'] for s in sinks 
                          if s.get('category') in ['browsing', 'entertainment'])
    if distraction_time > total_time * 0.2:
        recommendations.append(f"{distraction_time:.1f}h on distractions - use website blockers")
    
    # Check communication overhead
    comm_time = sum(s['time_spent'] for s in sinks 
                   if s.get('category') == 'communication')
    if comm_time > total_time * 0.3:
        recommendations.append(f"{comm_time:.1f}h in communication - batch email/chat checking")
    
    # Positive feedback
    if a_percentage > 40:
        recommendations.append("Excellent focus on A priorities!")
    
    return recommendations

def generate_simple_time_summary(timing_projects: List[Dict]) -> str:
    """
    Generate a simple summary of time spent on projects
    Perfect for ADHD - just the essentials
    """
    if not timing_projects:
        return ""
    
    output = []
    output.append("\n📊 Your week in numbers:")
    
    total_hours = sum(p.get('time_spent', 0) for p in timing_projects)
    output.append(f"   Total tracked: {total_hours:.1f} hours")
    
    # Show top 3
    top_projects = sorted(timing_projects, key=lambda x: x.get('time_spent', 0), reverse=True)[:3]
    output.append("   Top 3 projects:")
    for p in top_projects:
        output.append(f"   • {p['name']}: {p['time_spent']:.1f}h")
    
    return "\n".join(output)

def suggest_time_adjustments(timing_analysis: Dict, priorities: List[Dict]) -> str:
    """
    Suggest simple time adjustments for next week based on comprehensive analysis
    ADHD-friendly: Clear, actionable suggestions
    """
    if not timing_analysis or not priorities:
        return ""
    
    suggestions = []
    suggestions.append("\n🎯 Time adjustments for next week:")
    
    # Get alignment recommendations if available
    if 'recommendations' in timing_analysis:
        for i, rec in enumerate(timing_analysis['recommendations'][:3], 1):
            suggestions.append(f"   {i}. {rec}")
    
    # Add focus-based suggestion
    if timing_analysis.get('focus_correlation'):
        correlation = timing_analysis['focus_correlation']
        if "scattered execution" in correlation:
            suggestions.append("   • Use Pomodoro technique for better focus")
        elif "wrong priorities" in correlation:
            suggestions.append("   • Review priorities - you're focused but on wrong tasks")
    
    # If no specific recommendations, provide generic one
    if len(suggestions) == 1:
        suggestions.append("   • Time-block your top priority first thing tomorrow")
    
    return "\n".join(suggestions)

def format_comparison_report(comparison_data: Dict) -> str:
    """
    Format the comparison data into an ADHD-friendly report
    
    Args:
        comparison_data: Results from compare_time_with_priorities
    
    Returns:
        Formatted string report
    """
    if not comparison_data:
        return "No timing data available for comparison"
    
    output = []
    output.append("\n" + "="*50)
    output.append("📊 TIME ALIGNMENT REPORT")
    output.append("="*50)
    
    # Overall alignment score
    score = comparison_data['alignment_score']
    emoji = "✅" if score > 70 else "⚠️" if score > 40 else "❌"
    output.append(f"\n{emoji} Alignment Score: {score}%")
    output.append(f"   Time on priorities: {comparison_data['time_on_priorities']:.1f}h")
    output.append(f"   Total tracked: {comparison_data['total_time_tracked']:.1f}h")
    
    # Priority distribution
    if comparison_data.get('priority_distribution'):
        dist = comparison_data['priority_distribution']
        output.append("\n⏱️ Time by Priority Level:")
        output.append(f"   A: {dist['A']:.1f}h | B: {dist['B']:.1f}h | C: {dist['C']:.1f}h")
    
    # Top aligned projects
    if comparison_data['aligned_projects']:
        output.append("\n✅ Aligned Projects:")
        for item in comparison_data['aligned_projects'][:3]:
            output.append(f"   • {item['priority']} → {item['timing_project']} ({item['time_spent']:.1f}h)")
    
    # Untracked priorities (warning)
    untracked_a = [p for p in comparison_data['untracked_priorities'] if p.get('priority') == 'A']
    if untracked_a:
        output.append("\n⚠️ A-Priorities with NO time:")
        for p in untracked_a[:3]:
            output.append(f"   • {p.get('task', p.get('action', 'Unknown'))}")
    
    # Major time sinks
    big_sinks = [s for s in comparison_data['time_sinks'] if s['time_spent'] > 2]
    if big_sinks:
        output.append("\n🕳️ Time Sinks (>2h, not in priorities):")
        for sink in big_sinks[:3]:
            cat = sink.get('category', 'other')
            output.append(f"   • {sink['name']} ({sink['time_spent']:.1f}h) - {cat}")
    
    # Focus correlation
    if comparison_data.get('focus_correlation'):
        output.append(f"\n💡 Insight: {comparison_data['focus_correlation']}")
    
    # Recommendations
    if comparison_data.get('recommendations'):
        output.append("\n📋 Actions:")
        for rec in comparison_data['recommendations'][:3]:
            output.append(f"   → {rec}")
    
    output.append("")
    return "\n".join(output)