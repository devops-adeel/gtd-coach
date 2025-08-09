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

def compare_time_with_priorities(priorities: List[Dict], timing_data: Optional[Dict] = None) -> str:
    """
    Compare prioritized actions with actual time spent
    Returns a simple, ADHD-friendly comparison
    """
    
    if not timing_data:
        timing_data = load_timing_analysis()
    
    if not timing_data or 'estimated_hours' not in timing_data:
        return ""  # No comparison available
    
    # Build comparison output
    output = []
    output.append("\n" + "="*50)
    output.append("📊 TIME REALITY CHECK")
    output.append("="*50)
    
    # Get total hours tracked
    total_hours = timing_data.get('total_hours', 0)
    output.append(f"\nLast week: {total_hours:.1f} hours tracked")
    output.append("\nTop time investments:")
    
    # Show top 3 by time
    estimated_hours = timing_data['estimated_hours']
    sorted_projects = sorted(estimated_hours.items(), key=lambda x: x[1], reverse=True)[:3]
    
    for project, hours in sorted_projects:
        # Clean up project name for display
        clean_name = project.replace('1. ', '').replace('2. ', '').replace('3. ', '')
        clean_name = clean_name.replace('4. ', '').replace('5. ', '')
        output.append(f"  • {clean_name}: {hours:.1f}h")
    
    # Simple insight
    output.append("\n💡 Quick insight:")
    
    # Check if priorities align with time spent
    priority_keywords = {
        'gtm': 'GTM Strategy Work',
        'bedrock': 'AI Factory Work',
        'arabic': 'Arabic Learning',
        'claude': 'Claude Development',
        'aws': 'AI Factory Work',
        'duolingo': 'Arabic Learning'
    }
    
    # Analyze priorities
    a_priorities = [p for p in priorities if p.get('priority') == 'A']
    
    if a_priorities:
        # Check if A priorities match high-time projects
        time_aligned = False
        for priority in a_priorities:
            action_lower = priority['action'].lower()
            for keyword, project_name in priority_keywords.items():
                if keyword in action_lower:
                    # Find if this project got significant time
                    for proj, hours in sorted_projects[:2]:  # Top 2 projects
                        if project_name in proj and hours > 2:
                            time_aligned = True
                            break
        
        if time_aligned:
            output.append("✅ Your priorities align with where you spent time!")
        else:
            output.append("🤔 Consider: Are your priorities matching your time investment?")
    
    output.append("")
    return "\n".join(output)

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

def suggest_time_adjustments(timing_data: Dict, priorities: List[Dict]) -> str:
    """
    Suggest simple time adjustments for next week
    ADHD-friendly: One concrete suggestion only
    """
    if not timing_data or not priorities:
        return ""
    
    # Find the highest priority that got the least time
    a_priorities = [p for p in priorities if p.get('priority') == 'A']
    if not a_priorities:
        return ""
    
    suggestion = "\n🎯 One thing to try next week:\n"
    
    # Simple heuristic: If you have an A priority about Arabic and 
    # Arabic got <2 hours, suggest time-blocking
    arabic_priority = any('arabic' in p['action'].lower() or 'duolingo' in p['action'].lower() 
                          for p in a_priorities)
    
    if arabic_priority:
        arabic_hours = timing_data.get('estimated_hours', {}).get('3. Arabic Learning', 0)
        if arabic_hours < 2:
            suggestion += "   Block 30 min daily for Arabic (you only did {:.1f}h last week)".format(arabic_hours)
        else:
            suggestion += "   Keep up the Arabic momentum! ({:.1f}h last week)".format(arabic_hours)
    else:
        # Generic suggestion
        suggestion += "   Time-block your top priority first thing tomorrow morning"
    
    return suggestion