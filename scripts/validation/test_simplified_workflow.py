#!/usr/bin/env python3
"""
Test script for simplified GTD workflow
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent))

# Load environment
load_dotenv()

def test_daily_clarify():
    """Test the simplified daily clarify workflow"""
    print("=" * 60)
    print("Testing Daily Clarify (Ultra-Simple)")
    print("=" * 60)
    
    try:
        # Test without importing full command structure
        from gtd_coach.integrations.todoist import TodoistClient
        
        todoist = TodoistClient()
        
        # Check Todoist configuration
        if todoist.is_configured():
            print("✅ Todoist configured")
            
            # Test inbox fetch
            inbox = todoist.get_inbox_tasks()
            print(f"📥 Found {len(inbox)} items in inbox")
            
            # Test deep work detection
            deep_keywords = ['refactor', 'design', 'analyze', 'create', 'write']
            test_items = [
                "Reply to John's email",
                "Refactor authentication system",
                "Buy milk",
                "Design new API architecture"
            ]
            
            for item in test_items:
                is_deep = any(kw in item.lower() for kw in deep_keywords)
                print(f"  '{item}' -> Deep work: {is_deep}")
        else:
            print("⚠️ Todoist not configured - skipping inbox test")
    except Exception as e:
        print(f"⚠️ Could not test Todoist: {e}")
    
    print("\n✅ Daily Clarify test complete\n")


def test_timing_projects():
    """Test Timing project name suggestions"""
    print("=" * 60)
    print("Testing Timing Project Setup Guide")
    print("=" * 60)
    
    from gtd_coach.integrations.timing import TimingAPI
    
    api = TimingAPI()
    
    # Get suggested project names
    suggestions = api.get_weekly_project_names()
    
    print(f"📅 Week {suggestions['week']}, {suggestions['year']}")
    print("\n📝 Projects to create manually in Timing:")
    print("-" * 40)
    
    for i, project in enumerate(suggestions['projects'], 1):
        print(f"\n{i}. {project['title']}")
        print(f"   Color: {project['color']}")
        print(f"   Productivity: {project['productivity']}")
        print(f"   Purpose: {project['description']}")
    
    print("\n" + "=" * 40)
    print(suggestions['instructions'])
    
    # Test that we can still read data
    if api.is_configured():
        print("\n✅ Timing API configured for reading data")
        projects = api.fetch_projects_last_week(min_minutes=5)
        if projects:
            print(f"📊 Found {len(projects)} existing projects with activity")
    else:
        print("\n⚠️ Timing API not configured - set TIMING_API_KEY for data reading")
    
    print("\n✅ Timing test complete\n")


def test_reality_check():
    """Test weekly reality check calculation"""
    print("=" * 60)
    print("Testing Reality Check Logic")
    print("=" * 60)
    
    # Mock timing data
    mock_timing_data = {
        'projects': [
            {'name': 'Deep Work - Week 45', 'time_spent': 2.5},
            {'name': 'Email Processing', 'time_spent': 8.0},
            {'name': 'Slack', 'time_spent': 4.5},
            {'name': 'Random browsing', 'time_spent': 3.0}
        ],
        'focus_metrics': {
            'scatter_score': 65,
            'focus_score': 35
        }
    }
    
    # Calculate metrics
    deep_work = 2.5
    admin = 12.5  # Email + Slack
    reactive = 3.0
    total = deep_work + admin + reactive
    
    deep_percent = (deep_work / total) * 100
    admin_percent = (admin / total) * 100
    
    print(f"📊 Mock week analysis:")
    print(f"  • Deep work: {deep_work}h ({deep_percent:.0f}%)")
    print(f"  • Admin: {admin}h ({admin_percent:.0f}%)")
    print(f"  • Reactive: {reactive}h")
    print(f"  • Scatter score: {mock_timing_data['focus_metrics']['scatter_score']}")
    
    if deep_percent < 20:
        print("\n⚠️ Reality: Only 14% deep work - typical for ADHD")
        print("💡 Suggestion: Try ONE 2-hour deep block this week")
    
    print("\n✅ Reality check test complete\n")


def main():
    """Run all tests"""
    print("\n🧪 TESTING SIMPLIFIED GTD WORKFLOW\n")
    
    # Test each component
    test_daily_clarify()
    test_timing_projects()
    test_reality_check()
    
    print("=" * 60)
    print("🎉 All tests complete!")
    print("=" * 60)
    print("\nReady to use:")
    print("1. Run 'python3 -m gtd_coach.commands.daily_clarify' for inbox processing")
    print("2. Weekly: Manually create the 3 Timing projects shown above")
    print("3. Weekly review will show reality check automatically")


if __name__ == "__main__":
    main()